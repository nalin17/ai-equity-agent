"""The Knowledge/Event Hub: everything known at a decision time, from every domain, as one evidence object
(architecture 40B step 11, 3B, 3C, 3G, 4A rule 5, 4B rules 3 and 5, 4C, 4E, 5A.2, 5B, 5C, 30A; ADR-012).

gather(conn, decision_time, claim, isin=None, start=None, end=None) -> Bundle

Rules it follows:
- It reads only: each domain's own point-in-time query decides availability (5B) - the hub never re-derives
  it, never repairs, fills or carries a value forward (4C), and never writes to the database.
- The window is enforced, not requested (5A.2): its end clamps to the decision date; a window lying wholly
  after it moves back with its span kept; an unreadable or missing bound falls back to the decision date
  (default 30 days back). Prices, events, news, flows and series observations are bounded by it; reported
  figures are not (each period is its own fact); corporate actions and scheduled releases may lie ahead of
  it, because their dates were known in advance.
- For a security: its prices, reported figures, announcements (one release = one event), corporate actions,
  SEBI releases naming it, news stories proven to name it (a story only returned by a search for it is left
  out - 4B rule 3) and the events without an issuer that reach it through declared, recorded routes (4A rule 5).
- For everyone: context - FRED and MoSPI series, the FII/DII flows, central-bank, data-release, regulation and
  declared events, and the release calendar. Context is never attributed to a security (3G); an event that
  reaches the security by a route appears once, as routed, not again as context (4B rule 5: one vote).
- Whatever cannot be given is said, as a gap (4E, 30A.2): domains with no adapter yet (public sentiment,
  derivatives positioning, alternative data), evidence withheld for want of proven availability, trading days
  with no file, a component that could not run, and what was deliberately left out.
"""
from datetime import timedelta
from types import SimpleNamespace

from core.calendars import CalendarError, load_calendars
from core.dates import strict_iso_date
from data_quality.extraction_confidence import ExtractionConfidence
from data_quality.missing_data import MissingClass
from ingestion.event_routes import events_for
from ingestion.gdelt_news import NewsNotReadError, stories
from ingestion.india_macro import (SOURCE_ID as MOSPI, india_latest, india_observations, india_series_info,
                                   registered_india_series)
from ingestion.macro_context import latest, observations, registered_series, series_info
from ingestion.macro_events import macro_events, scheduled_releases
from ingestion.nse_announcements import events as announcements
from ingestion.nse_financial_results import IST
from ingestion.nse_flows import CALENDAR, SCOPE_TITLES, STATUS, UNIT, flows, missing_days
from ingestion.sebi_releases import releases
from knowledge.evidence import Attribution, Bundle, Domain, Evidence, EvidenceGap, GapNature, withheld
from provenance.availability import Availability, PitClaim, disposition, parse_timestamp, price_availability
from provenance.pit_store import fact_as_of
from universe.entities import validate_isin

HUB_VERSION = "hub-1"
DEFAULT_DAYS = 30
FRED, FRED_CALENDAR = "fred_alfred", "fred_release_calendar"
NOT_BUILT = {
    Domain.PUBLIC_SENTIMENT: "no adapter yet - 40B step 10 (4B); news stories are given, their tone is not",
    Domain.DERIVATIVES_POSITIONING: "no adapter yet (3D) - no licensed source of F&O positioning has been approved",
    Domain.ALTERNATIVE_DATA: "deferred by the architecture (3B rule 2)",
}
SHOWN = 10   # dates listed in a gap; the count is always whole


# ---- the window (5A.2) ---------------------------------------------------------------------------------

def clamp_window(start, end, decision_time, days=DEFAULT_DAYS):
    """(start, end, note) as YYYY-MM-DD in India time: the window as enforced for a decision (5A.2)."""
    run_day = parse_timestamp(decision_time).astimezone(IST).date()
    notes = []

    def read(value, name):
        if value is None or value == "":
            return None
        try:
            return strict_iso_date(value) if isinstance(value, str) else strict_iso_date(value.isoformat())
        except (AttributeError, TypeError, ValueError):
            notes.append(f"{name} {value!r} unreadable - the decision date is used")
            return None
    s, e = read(start, "start"), read(end, "end")
    e = e or run_day
    s = s or e - timedelta(days=days)
    if s > e:
        raise ValueError(f"the window starts ({s}) after it ends ({e})")
    if s > run_day:
        span = e - s
        s, e = run_day - span, run_day
        notes.append(f"the window lay after the decision date - moved back to end on {run_day}, span kept")
    elif e > run_day:
        e = run_day
        notes.append(f"the window's end clamped to the decision date {run_day}")
    return s.isoformat(), e.isoformat(), "; ".join(notes) or None


# ---- helpers -------------------------------------------------------------------------------------------

def _day(timestamp):
    return parse_timestamp(timestamp).astimezone(IST).date().isoformat()


def _inside(ctx, day, open_ended=False):
    return day >= ctx.start and (open_ended or day <= ctx.end)


def _basis(ctx, retrieved, published):
    """The time that proves availability under the claim (5B.2)."""
    return retrieved if ctx.claim == PitClaim.CURRENT_DECISION else published


def _earliest(stamps):
    return min(stamps, key=parse_timestamp)


def _add(ctx, **fields):
    ctx.evidence.append(Evidence(claim=ctx.claim, **fields))


def _missing_trading_days(ctx, have, component, domain):
    cal = load_calendars()[0][CALENDAR]
    day, last, gaps = strict_iso_date(ctx.start), strict_iso_date(ctx.end), []
    while day <= last:
        try:
            traded = cal.is_session(day)
        except CalendarError:
            ctx.gaps.append(EvidenceGap(domain, GapNature.DEGRADED, component,
                                        f"the {CALENDAR} calendar does not cover {day} - trading days after it are"
                                        " not judged"))
            break
        if traded and day.isoformat() not in have:
            gaps.append(day.isoformat())
        day += timedelta(days=1)
    if gaps:
        ctx.gaps.append(EvidenceGap(domain, GapNature.MISSING, component, "NSE trading days with nothing stored",
                                    count=len(gaps), items=gaps[:SHOWN], missing_class=MissingClass.EXTRACTION_FAILURE))


# ---- the security's own evidence -----------------------------------------------------------------------

def _prices(ctx):
    review, have = 0, set()
    for price_id, day, o, h, low, close, volume in ctx.conn.execute(
            "SELECT price_id, trade_date, open_price, high_price, low_price, close_price, volume FROM trusted_prices"
            " WHERE isin = ? AND trade_date >= ? AND trade_date <= ? ORDER BY trade_date", [ctx.isin, ctx.start, ctx.end]):
        state = price_availability(ctx.conn, price_id, ctx.decision, ctx.claim)
        if state == Availability.AVAILABILITY_REVIEW:
            review += 1
        if state != Availability.ELIGIBLE:
            continue
        rows = ctx.conn.execute(
            "SELECT a.source_id, a.retrieved_at, a.published_at FROM price_provenance p JOIN ingestion_runs r"
            " ON r.run_id = p.run_id JOIN raw_artifacts a ON a.artifact_id = r.artifact_id WHERE p.price_id = ?",
            [price_id]).fetchall()
        stamps = [_basis(ctx, r[1], r[2]) for r in rows if _basis(ctx, r[1], r[2]) is not None]
        first = _earliest(stamps)
        have.add(day)
        _add(ctx, evidence_id=f"trusted_prices:{price_id}", domain=Domain.MARKET, kind="daily_price",
             subject=ctx.isin, attribution=Attribution.DIRECT, observed=day, available_at=first, value=close,
             unit="INR", source_id=next(r[0] for r in rows if _basis(ctx, r[1], r[2]) == first),
             details={"open": o, "high": h, "low": low, "volume": volume,
                      "series": "raw - not adjusted for corporate actions"})
    if review:
        ctx.gaps.append(withheld(Domain.MARKET, "prices", review, "no proven publication time - AVAILABILITY_REVIEW"
                                 " for historical replay (5B.1)"))
    if ctx.claim == PitClaim.CURRENT_DECISION:
        _missing_trading_days(ctx, have, "prices", Domain.MARKET)


def _figures(ctx):
    review = 0
    for field, basis, period_end in ctx.conn.execute(
            "SELECT DISTINCT field, basis, period_end FROM pit_facts WHERE isin = ? ORDER BY period_end, field, basis",
            [ctx.isin]).fetchall():
        found = fact_as_of(ctx.conn, ctx.isin, field, basis, period_end, ctx.decision, ctx.claim)
        if found.availability == Availability.AVAILABILITY_REVIEW:
            review += 1
        if found.availability != Availability.ELIGIBLE:
            continue
        unit, source, retrieved, published = ctx.conn.execute(
            "SELECT f.unit, a.source_id, a.retrieved_at, a.published_at FROM pit_facts f JOIN raw_artifacts a"
            " ON a.artifact_id = f.artifact_id WHERE f.fact_id = ?", [found.fact_id]).fetchone()
        _add(ctx, evidence_id=f"pit_facts:{found.fact_id}", domain=Domain.FUNDAMENTAL, kind="reported_figure",
             subject=ctx.isin, attribution=Attribution.DIRECT, observed=period_end,
             available_at=_basis(ctx, retrieved, published), value=found.value, unit=unit, source_id=source,
             missing_class=found.missing_class, details={"field": field, "basis": basis, "version": found.version})
    if review:
        ctx.gaps.append(withheld(Domain.FUNDAMENTAL, "reported figures", review, "a version's availability is not"
                                 " proven under this claim - AVAILABILITY_REVIEW (5B.1)"))


def _announcements(ctx):
    for event in announcements(ctx.conn, ctx.decision, ctx.claim, isin=ctx.isin):
        day = _day(event["published_at"])
        if not _inside(ctx, day):
            continue
        marks = ", ".join("?" * len(event["filings"]))
        source, retrieved = ctx.conn.execute(
            f"SELECT MIN(a.source_id), MIN(a.retrieved_at) FROM an_filings f JOIN raw_artifacts a"
            f" ON a.artifact_id = f.artifact_id WHERE f.filing_id IN ({marks})", event["filings"]).fetchone()
        _add(ctx, evidence_id=f"an_filings:{event['event_id']}", domain=Domain.CORPORATE_EVENTS,
             kind="corporate_announcement", subject=ctx.isin, attribution=Attribution.DIRECT, observed=day,
             available_at=_basis(ctx, retrieved, event["published_at"]), value="; ".join(event["subjects"]),
             unit=None, source_id=source,
             details={"event_types": event["event_types"], "kind": event["kind"], "filings": event["filings"],
                      "type_basis": event["extraction_confidence"], "dedup_rule": event["dedup_rule"],
                      "mapping_version": event["mapping_version"]})


def _corporate_actions(ctx):
    review = 0
    for action_id, kind, ex_date, treatment, terms, source, retrieved, published in ctx.conn.execute(
            "SELECT c.action_id, c.action_type, c.ex_date, c.treatment, c.terms_text, a.source_id, a.retrieved_at,"
            " a.published_at FROM corporate_actions c JOIN raw_artifacts a ON a.artifact_id = c.artifact_id"
            " WHERE c.isin = ? ORDER BY c.ex_date, c.action_id", [ctx.isin]):
        state = disposition(ctx.claim, ctx.decision, retrieved, published)
        if state == Availability.AVAILABILITY_REVIEW:
            review += 1
        if state != Availability.ELIGIBLE or not _inside(ctx, ex_date, open_ended=True):
            continue
        _add(ctx, evidence_id=f"corporate_actions:{action_id}", domain=Domain.CORPORATE_EVENTS,
             kind="corporate_action", subject=ctx.isin, attribution=Attribution.DIRECT, observed=ex_date,
             available_at=_basis(ctx, retrieved, published), value=(terms or "").strip() or kind, unit=None,
             source_id=source,
             details={"action_type": kind, "treatment": treatment})
    if review:
        ctx.gaps.append(withheld(Domain.CORPORATE_EVENTS, "corporate actions", review, "no proven publication"
                                 " time - AVAILABILITY_REVIEW for historical replay (5B.1)"))


def _sebi_named(ctx):
    for r in releases(ctx.conn, ctx.decision, ctx.claim, isin=ctx.isin):
        if not _inside(ctx, r["stated_date"]):
            continue
        _add(ctx, evidence_id=f"sb_releases:{r['release_id']}", domain=Domain.CORPORATE_EVENTS,
             kind="regulator_release", subject=ctx.isin, attribution=Attribution.DIRECT, observed=r["stated_date"],
             available_at=r["published_at"], value=r["title"], unit=None, source_id=r["source_quality"]["source"],
             extraction_confidence=ExtractionConfidence.REGISTERED_NAME_IN_TITLE,
             details={"section": r["section"], "kind": r["kind"], "event_types": r["event_types"], "link": r["link"],
                      "entity_rule": r["entity_rule"]})


def _news(ctx):
    try:
        found = stories(ctx.conn, ctx.decision, ctx.claim, isin=ctx.isin)
    except NewsNotReadError as e:
        ctx.gaps.append(EvidenceGap(Domain.NEWS_EXTERNAL, GapNature.DEGRADED, "news", str(e)))
        return
    searched_only = 0
    for story in found:
        day = _day(story["published_at"])
        if not _inside(ctx, day):
            continue
        company = story["companies"].get(ctx.isin)
        if company is None:   # returned by a search for the company, but not proven to name it (4B rule 3)
            searched_only += 1
            continue
        ids = [c["article_id"] for c in story["copies"]]
        source, retrieved = ctx.conn.execute(
            f"SELECT MIN(f.source_id), MIN(f.retrieved_at) FROM nw_articles a JOIN nw_responses r"
            f" ON r.response_id = a.response_id JOIN raw_artifacts f ON f.artifact_id = r.artifact_id"
            f" WHERE a.article_id IN ({', '.join('?' * len(ids))})", ids).fetchone()
        _add(ctx, evidence_id=f"nw_articles:{story['story_id']}", domain=Domain.NEWS_EXTERNAL, kind="news_story",
             subject=ctx.isin, attribution=Attribution.DIRECT, observed=day,
             available_at=_basis(ctx, retrieved, story["published_at"]), value=story["headline"], unit=None,
             source_id=source, extraction_confidence=company["extraction_confidence"],
             details={"role": company["role"], "copies": len(ids), "sites": story["novelty"]["sites"],
                      "language": story["language"], "dedup_rule": story["novelty"]["rule"]})
    if searched_only:
        ctx.gaps.append(EvidenceGap(Domain.NEWS_EXTERNAL, GapNature.EXCLUDED, "news", "returned by a search for the"
                                    " company but not proven to name it - never attributed (4B rule 3)",
                                    count=searched_only))


def _event_fields(event):
    return dict(domain=Domain.NEWS_EXTERNAL, kind="macro_event", observed=event["happened_on"],
                available_at=event["available_at"], value=event["title"], unit=None, source_id=event["source_id"],
                extraction_confidence=event["extraction_confidence"],
                details={"group": event["group"], "event_types": event["event_types"], "region": event["region"],
                         "institution": event.get("institution"), "type_basis": event.get("type_basis"),
                         "links": event["links"]})


def _routed_events(ctx):
    for found in events_for(ctx.conn, ctx.isin, ctx.decision, ctx.claim, start=ctx.start, end=ctx.end):
        event = found["event"]
        ctx.routed.add(event["event_id"])
        fields = _event_fields(event)
        fields["details"] = {**fields["details"], "relations": [r["relation"] for r in found["routes"]],
                             "route_rule": found["route_rule"], "effect": found["effect"]}
        _add(ctx, evidence_id=f"macro_event:{event['event_id']}", subject=ctx.isin, attribution=Attribution.ROUTE,
             routes=tuple(r["route_key"] for r in found["routes"]), **fields)


# ---- context ---------------------------------------------------------------------------------------------

def _macro_events(ctx):
    for event in macro_events(ctx.conn, ctx.decision, ctx.claim, start=ctx.start, end=ctx.end):
        if event["event_id"] in ctx.routed:   # already given once, as routed (4B rule 5)
            continue
        _add(ctx, evidence_id=f"macro_event:{event['event_id']}", subject=f"context:macro_events:{event['group']}",
             attribution=Attribution.CONTEXT, **_event_fields(event))
    if ctx.claim == PitClaim.HISTORICAL_REPLAY and ctx.conn.execute("SELECT COUNT(*) FROM me_declared").fetchone()[0]:
        ctx.gaps.append(withheld(Domain.NEWS_EXTERNAL, "declared events", None, "declared by the owner with no proven"
                                 " publication time - AVAILABILITY_REVIEW for historical replay (5B.1)"))


def _schedule(ctx):
    for r in scheduled_releases(ctx.conn, ctx.decision, ctx.claim, start=ctx.start):
        _add(ctx, evidence_id=f"me_calendar_dates:{r['release_id']}:{r['date']}@{r['as_of']}",
             domain=Domain.SECTOR_MACRO, kind="scheduled_release", subject="context:release_calendar",
             attribution=Attribution.CONTEXT, observed=r["date"], available_at=r["as_of"], value=r["release"],
             unit=None, source_id=FRED_CALENDAR,
             details={"release_id": r["release_id"], "region": r["region"], "series_id": r["series_id"],
                      "time_of_day": r["time_of_day"]})


def _fred(ctx):
    for sid in registered_series(ctx.conn):
        rows = {r["date"]: r for r in observations(ctx.conn, sid, ctx.decision, ctx.claim, ctx.start, ctx.end)}
        newest = latest(ctx.conn, sid, ctx.decision, ctx.claim)
        if newest is not None:   # the newest value, under its own date, even when older than the window
            rows.setdefault(newest["date"], newest)
        info = series_info(ctx.conn, sid)
        for day in sorted(rows):
            r = rows[day]
            _add(ctx, evidence_id=f"mc_vintages:{sid}:{day}@{r['realtime_start']}", domain=Domain.SECTOR_MACRO,
                 kind="macro_observation", subject=f"context:fred:{sid}", attribution=Attribution.CONTEXT,
                 observed=day, available_at=r["available_at"], value=r["value"], unit=info["fred_units"],
                 source_id=FRED, missing_class=r["missing_class"], value_text=r["value_text"],
                 details={"title": info["title"], "region": info["region"], "frequency": info["frequency"],
                          "vintage": r["realtime_start"], "reason": r.get("reason")})


def _mospi(ctx):
    if ctx.claim == PitClaim.HISTORICAL_REPLAY:
        stored = ctx.conn.execute("SELECT COUNT(*) FROM mo_values").fetchone()[0]
        if stored:
            ctx.gaps.append(withheld(Domain.SECTOR_MACRO, "India macro (MoSPI)", stored, "MoSPI gives no publication"
                                     " time - AVAILABILITY_REVIEW for historical replay (5A.1, 5B.2)"))
        return
    for sid in registered_india_series(ctx.conn):
        rows = {r["period"]: r for r in india_observations(ctx.conn, sid, ctx.decision, ctx.claim, ctx.start, ctx.end)}
        newest = india_latest(ctx.conn, sid, ctx.decision, ctx.claim)
        if newest is not None:
            rows.setdefault(newest["period"], newest)
        title = india_series_info(ctx.conn, sid)["title"]
        for period in sorted(rows):
            r = rows[period]
            _add(ctx, evidence_id=f"mo_values:{sid}:{period}@{r['known_from']}", domain=Domain.SECTOR_MACRO,
                 kind="india_macro_observation", subject=f"context:mospi:{sid}", attribution=Attribution.CONTEXT,
                 observed=period, available_at=r["known_from"], value=r["value"], unit=r["unit"], source_id=MOSPI,
                 value_text=r["value_text"], details={"title": title, "status": r["status"]})


def _flows(ctx):
    if ctx.claim == PitClaim.HISTORICAL_REPLAY:
        stored = ctx.conn.execute("SELECT COUNT(*) FROM fl_flows").fetchone()[0]
        if stored:
            ctx.gaps.append(withheld(Domain.OWNERSHIP_FLOWS, "FII/DII flows", stored, "NSE gives no publication time"
                                     " - AVAILABILITY_REVIEW for historical replay (3C rule 1, 5B.1)"))
        return
    for scope in SCOPE_TITLES:
        for r in flows(ctx.conn, ctx.decision, ctx.claim, scope, ctx.start, ctx.end):
            _add(ctx, evidence_id=f"fl_flows:{scope}:{r['trade_date']}:{r['category']}@{r['known_from']}",
                 domain=Domain.OWNERSHIP_FLOWS, kind="investor_flow_net", subject=f"context:flows:{scope}",
                 attribution=Attribution.CONTEXT, observed=r["trade_date"], available_at=r["known_from"],
                 value=r["net_crore"], unit=UNIT, source_id="nse_fii_dii", value_text=r["value_text"],
                 details={"category": r["category"], "buy_crore": r["buy_crore"], "sell_crore": r["sell_crore"],
                          "status": STATUS, "market": SCOPE_TITLES[scope]})
    gaps = missing_days(ctx.conn, ctx.decision, ctx.claim, "nse", ctx.start, ctx.end)
    if gaps:
        ctx.gaps.append(EvidenceGap(Domain.OWNERSHIP_FLOWS, GapNature.MISSING, "FII/DII flows", gaps[0]["reason"],
                                    count=len(gaps), items=[g["trade_date"] for g in gaps[:SHOWN]],
                                    missing_class=gaps[0]["missing_class"]))


SECURITY = (_prices, _figures, _announcements, _corporate_actions, _sebi_named, _news, _routed_events)
CONTEXT = (_macro_events, _schedule, _fred, _mospi, _flows)


def gather(conn, decision_time, claim=PitClaim.CURRENT_DECISION, isin=None, start=None, end=None):
    """Everything known at decision_time under the claim: for the security isin (its own evidence and the
    events routed to it) and the context, or the context alone without isin. Reads only."""
    decision = parse_timestamp(decision_time)
    claim = PitClaim(claim)
    if isin is not None:
        validate_isin(isin)
        if not conn.execute("SELECT 1 FROM entities WHERE isin = ?", [isin]).fetchone():
            raise ValueError(f"{isin} is not a known entity")
    s, e, note = clamp_window(start, end, decision)
    ctx = SimpleNamespace(conn=conn, decision=decision, claim=claim, isin=isin, start=s, end=e, evidence=[],
                          gaps=[], routed=set())
    for adapter in (SECURITY if isin else ()) + CONTEXT:
        adapter(ctx)
    ctx.gaps += [EvidenceGap(d, GapNature.NOT_BUILT, d.value, why) for d, why in NOT_BUILT.items()]
    ordered = sorted(ctx.evidence, key=lambda x: (list(Domain).index(x.domain), x.subject, x.observed, x.evidence_id))
    return Bundle(subject=isin, decision_time=decision.isoformat(), claim=claim, start=s, end=e, window_note=note,
                  evidence=tuple(ordered), gaps=tuple(ctx.gaps), hub_version=HUB_VERSION)
