"""Stage 11 tests: the Knowledge/Event Hub - every domain normalised to one point-in-time evidence object
(architecture 40B step 11, 3B, 3C, 3G, 4A rule 5, 4B rules 3 and 5, 4C, 4E, 5A.2, 5B, 30A; ADR-012).

The data goes in through each domain's own loader, with the samples of the earlier stages' tests (HDFC Bank's
board outcome filed four times, NSE's FII/DII file of 01-Oct-2026, the Fed's FOMC statement of 16-Sep-2026,
SEBI's feed, FRED's CPI, MoSPI's CPI, FRED's release calendar, NSE's bhavcopy, GDELT's articles); reported
figures and routes are made up for the tests.
"""
import math
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import yaml

from core.database import connect, migrate
from ingestion.corporate_actions import record_action
from data_quality.extraction_confidence import ExtractionConfidence
from data_quality.missing_data import MissingClass
from ingestion.event_routes import sync_routes
from ingestion.gdelt_news import load_response, sync_news_names
from ingestion.india_macro import load_mospi_pages, requests_to_fetch, sync_india_series
from ingestion.macro_context import sync_series
from ingestion.macro_events import load_feed, load_release_dates
from ingestion.market_adapters import ingest_market_file
from ingestion.nse_announcements import load_announcements
from ingestion.nse_flows import load_flows
from ingestion.sebi_releases import load_feed as load_sebi_feed
from ingestion.source_registry import sync_sources
from knowledge.evidence import Attribution, Bundle, Domain, Evidence, EvidenceError, GapNature
from knowledge.hub import HUB_VERSION, NOT_BUILT, clamp_window, gather
from provenance.availability import PitClaim
from provenance.pit_store import record_fact
from provenance.raw_store import store_raw_artifact
from test_stage07a_market_adapters import EQUITY_LIST, RELIANCE, udiff_text
from test_stage09_corporate_events import BOARD_OUTCOME, RETRIEVED as FILINGS_READ, listing
from test_stage10_news import COMPANIES as NEWS_COMPANIES, END as NEWS_END, NAMES, REAL, START as NEWS_START
from test_stage10_news import RETRIEVED as NEWS_READ, article, response
from test_stage10d_macro_events import (COMPANIES, CPI, CPI_DATES, FOMC_SEP, HDFC, READ, TODAY, calendar_answer,
                                        fred, mospi_page, opec_route, rss, sebi_item)
from test_stage10e_flows import NSE, READ as FLOWS_READ, text as flows_text
from universe.entities import add_alias, add_entity
from universe.equity_list import load_equity_list

UTC = timezone.utc
CURRENT, REPLAY = PitClaim.CURRENT_DECISION, PitClaim.HISTORICAL_REPLAY
AFTER = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)      # everything below was loaded by then
MID = datetime(2026, 10, 4, 15, 0, tzinfo=UTC)        # after the macro reads, before the flows file
EARLY = datetime(2026, 10, 4, 13, 0, tzinfo=UTC)      # after the filings, before the macro reads
SEBI_NAMED = "Circular on the enhanced disclosures of HDFC Bank Limited"
JAGROOK = ("Display of investor awareness messages by stock brokers on their trading apps and websites, under"
           " Project Jagrook")


@pytest.fixture
def world(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    for isin, name, symbol in COMPANIES:
        add_entity(c, isin, name)
        add_alias(c, isin, "nse_symbol", symbol, "1995-01-01")
    raw = tmp_path / "raw"
    (tmp_path / "CF-AN-equities-1.csv").write_text(listing(*BOARD_OUTCOME), encoding="utf-8")
    load_announcements(c, tmp_path / "CF-AN-equities-1.csv", FILINGS_READ, raw_dir=raw)
    (tmp_path / "flows").mkdir()
    (tmp_path / "flows" / "fii-dii-nse-latest.csv").write_bytes(flows_text(NSE).encode("utf-8"))
    load_flows(c, tmp_path / "flows" / "fii-dii-nse-latest.csv", FLOWS_READ, raw_dir=raw)
    (tmp_path / "fed.xml").write_bytes(rss(FOMC_SEP))
    load_feed(c, "fed_monetary_feed", tmp_path / "fed.xml", READ, raw_dir=raw)
    (tmp_path / "sebi.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>SEBI</title>'
        + sebi_item(JAGROOK, "legal/circulars", 104858) + sebi_item(SEBI_NAMED, "legal/circulars", 104859)
        + sebi_item("Adjudication Order in the matter of a broker", "enforcement/orders", 104860)
        + "</channel></rss>", encoding="utf-8")
    load_sebi_feed(c, tmp_path / "sebi.xml", READ, raw_dir=raw)
    env = SimpleNamespace(c=c, tmp=tmp_path)
    sync_series(c)
    fred(env, "CPIAUCSL", CPI, "2026-09-11 08:37:49-05")
    sync_india_series(c)
    request = next(r for d, r in requests_to_fetch(c) if d == "cpi" and r.get("series") == "Current")
    (tmp_path / "p1.json").write_bytes(mospi_page(("August", "108.74", "4.82"), ("July", "108.30", "4.50")))
    load_mospi_pages(c, "cpi", request, [(tmp_path / "p1.json", READ)], raw_dir=raw)
    (tmp_path / "cal.json").write_bytes(calendar_answer(10, CPI_DATES))
    load_release_dates(c, 10, tmp_path / "cal.json", READ, raw_dir=raw)
    for n, (basis, value, missing, published) in enumerate([
            ("consolidated", 1000.0, None, "2026-04-18T14:45:47+05:30"),
            ("standalone", None, MissingClass.NOT_DISCLOSED, None)]):
        (tmp_path / f"figures{n}.xml").write_text(f"figures {n}", encoding="utf-8")
        artifact, _ = store_raw_artifact(c, "nse_financial_results_xbrl", tmp_path / f"figures{n}.xml", FILINGS_READ,
                                         published, "exchange dissemination time" if published else None, raw_dir=raw)
        record_fact(c, HDFC, "revenue_3m", basis, "2026-03-31", value, "INR_crore", artifact, missing_class=missing)
    (tmp_path / "CF-CA-equities.csv").write_text("actions", encoding="utf-8")
    artifact, _ = store_raw_artifact(c, "nse_corporate_actions", tmp_path / "CF-CA-equities.csv", FILINGS_READ,
                                     raw_dir=raw)
    for ex_date, terms in (("2026-06-01", "Dividend - Rs 19.50 per share"), ("2026-10-20", "Dividend - Rs 11 per share")):
        record_action(c, HDFC, "dividend", ex_date, terms, artifact, "made up for the tests")

    def route(*entries):
        (tmp_path / "routes.yaml").write_text(yaml.safe_dump({"routes": list(entries)}), encoding="utf-8")
        return sync_routes(c, tmp_path / "routes.yaml", today=TODAY)

    yield SimpleNamespace(c=c, route=route)
    c.close()


@pytest.fixture
def market(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    read = "2024-03-15T19:00:00+05:30"
    (tmp_path / "EQUITY_L.csv").write_text(EQUITY_LIST, encoding="utf-8")
    load_equity_list(c, tmp_path / "EQUITY_L.csv", read, raw_dir=tmp_path / "raw")
    path = tmp_path / "BhavCopy_NSE_CM_0_0_0_20240314_F_0000.csv"
    path.write_text(udiff_text(), encoding="utf-8")
    ingest_market_file(c, path, read, raw_dir=tmp_path / "raw")
    yield c
    c.close()


@pytest.fixture
def news(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    for isin, name, symbol, listed in NEWS_COMPANIES:
        add_entity(c, isin, name)
        add_alias(c, isin, "nse_symbol", symbol, listed)
    (tmp_path / "news_names.yaml").write_text(NAMES, encoding="utf-8")
    sync_news_names(c, tmp_path / "news_names.yaml", today="2026-10-02")
    generic = article(url="https://economictimes.indiatimes.com/markets/stocks/news/sensex-ends-higher/articleshow/1.cms",
                      title="Sensex ends higher as markets gain", seen="20261001T101500Z")
    (tmp_path / "gdelt.json").write_text(response(article("srivatsan_banking"), generic), encoding="utf-8")
    load_response(c, tmp_path / "gdelt.json", HDFC, '"HDFC Bank"', NEWS_START, NEWS_END, NEWS_READ,
                  raw_dir=tmp_path / "raw")
    yield c
    c.close()


def kinds(bundle):
    return {e.kind for e in bundle.evidence}


def one(bundle, **match):
    found = [e for e in bundle.evidence if all(getattr(e, k) == v for k, v in match.items())]
    assert len(found) == 1, found
    return found[0]


def record(**changes):
    fields = dict(evidence_id="fl_flows:nse:2026-10-01:DII@x", domain=Domain.OWNERSHIP_FLOWS, kind="investor_flow_net",
                  subject="context:flows:nse", attribution=Attribution.CONTEXT, observed="2026-10-01",
                  available_at="2026-10-04T17:39:00+00:00", claim=CURRENT, value=9633.63, unit="INR crore",
                  source_id="nse_fii_dii")
    fields.update(changes)
    return Evidence(**fields)


# ---- 40B step 11: one evidence object for every domain ---------------------------------------------------

def test_every_domain_built_so_far_arrives_as_one_evidence_object(world):
    bundle = gather(world.c, AFTER, CURRENT, HDFC, start="2026-03-01")
    assert {"corporate_announcement", "regulator_release", "reported_figure", "macro_event", "scheduled_release",
            "macro_observation", "india_macro_observation", "investor_flow_net"} <= kinds(bundle)
    assert all(type(e) is Evidence and e.claim == CURRENT for e in bundle.evidence)
    assert set(bundle.counts()) == set(Domain) and bundle.hub_version == HUB_VERSION
    assert all(datetime.fromisoformat(e.available_at) <= AFTER for e in bundle.evidence)
    assert len({e.evidence_id for e in bundle.evidence}) == len(bundle.evidence)


def test_nothing_known_after_the_decision_time_enters(world):
    mid = gather(world.c, MID, CURRENT, HDFC, start="2026-03-01")
    assert "investor_flow_net" not in kinds(mid) and {"macro_event", "macro_observation"} <= kinds(mid)
    early = gather(world.c, EARLY, CURRENT, HDFC, start="2026-03-01")
    assert kinds(early) == {"corporate_announcement", "reported_figure", "corporate_action"}   # macro reads came later
    assert gather(world.c, datetime(2026, 10, 1, tzinfo=UTC), CURRENT, HDFC, start="2026-03-01").evidence == ()


def test_the_hub_only_reads(world):
    before = world.c.total_changes
    for claim in PitClaim:
        gather(world.c, AFTER, claim, HDFC, start="2026-03-01")
        gather(world.c, AFTER, claim)
    assert world.c.total_changes == before


def test_every_record_names_the_stored_row_it_comes_from(world):
    bundle = gather(world.c, AFTER, CURRENT, HDFC, start="2026-03-01")
    tables = {e.evidence_id.split(":")[0] for e in bundle.evidence}
    assert tables <= {"trusted_prices", "pit_facts", "an_filings", "corporate_actions", "sb_releases", "nw_articles",
                      "macro_event", "me_calendar_dates", "mc_vintages", "mo_values", "fl_flows"}
    for e in bundle.evidence:
        table, key = e.evidence_id.split(":", 1)
        if table in ("pit_facts", "an_filings", "sb_releases"):
            column = {"pit_facts": "fact_id", "an_filings": "filing_id", "sb_releases": "release_id"}[table]
            assert world.c.execute(f"SELECT 1 FROM {table} WHERE {column} = ?", [int(key)]).fetchone()


# ---- the security's own evidence -------------------------------------------------------------------------

def test_one_release_filed_four_times_is_one_event_of_its_issuer(world):
    bundle = gather(world.c, AFTER, CURRENT, HDFC, start="2026-03-01")
    event = one(bundle, kind="corporate_announcement")
    assert (event.subject, event.attribution, event.domain) == (HDFC, Attribution.DIRECT, Domain.CORPORATE_EVENTS)
    assert len(event.details["filings"]) == 4 and event.observed == "2026-04-18"
    assert event.available_at == datetime.fromisoformat(FILINGS_READ).isoformat()   # known from our retrieval
    replay = one(gather(world.c, AFTER, REPLAY, HDFC, start="2026-03-01"), kind="corporate_announcement")
    assert replay.available_at.startswith("2026-04-18")   # under replay: NSE's own dissemination time
    assert one(gather(world.c, AFTER, CURRENT, HDFC), kind="reported_figure", value=1000.0)   # figures: no window
    assert "corporate_announcement" not in kinds(gather(world.c, AFTER, CURRENT, HDFC))   # April is outside


def test_reported_figures_keep_their_basis_and_their_missing_class(world):
    bundle = gather(world.c, AFTER, CURRENT, HDFC)
    shown = one(bundle, kind="reported_figure", value=1000.0)
    absent = one(bundle, kind="reported_figure", value=None)
    assert shown.details["basis"] == "consolidated" and shown.missing_class is None and shown.unit == "INR_crore"
    assert absent.details["basis"] == "standalone" and absent.missing_class == MissingClass.NOT_DISCLOSED
    replay = gather(world.c, AFTER, REPLAY, HDFC)
    assert [e.value for e in replay.of(Domain.FUNDAMENTAL)] == [1000.0]   # the other has no proven publication
    [gap] = replay.gaps_of(Domain.FUNDAMENTAL)
    assert (gap.nature, gap.count) == (GapNature.WITHHELD, 1)


def test_an_announced_corporate_action_counts_even_when_its_date_lies_ahead(world):
    action = one(gather(world.c, AFTER, CURRENT, HDFC), kind="corporate_action")   # June's is outside the window
    assert (action.observed, action.value, action.details["treatment"]) == (
        "2026-10-20", "Dividend - Rs 11 per share", "no_adjustment")
    replay = gather(world.c, AFTER, REPLAY, HDFC)
    assert "corporate_action" not in kinds(replay)
    assert [(g.nature, g.count) for g in replay.gaps_of(Domain.CORPORATE_EVENTS)] == [(GapNature.WITHHELD, 2)]


def test_prices_are_market_evidence_and_unproven_publication_is_withheld(market):
    when = datetime(2024, 3, 20, tzinfo=UTC)
    bundle = gather(market, when, CURRENT, RELIANCE)
    price = one(bundle, kind="daily_price")
    assert (price.observed, price.value, price.domain, price.unit) == ("2024-03-14", 2940.25, Domain.MARKET, "INR")
    assert price.details["series"].startswith("raw")
    assert datetime.fromisoformat(price.available_at) == datetime(2024, 3, 15, 13, 30, tzinfo=UTC)   # our retrieval
    [missing] = gather(market, when, CURRENT, RELIANCE, start="2024-03-11").gaps_of(Domain.MARKET)
    assert (missing.nature, missing.missing_class) == (GapNature.MISSING, MissingClass.EXTRACTION_FAILURE)
    assert missing.items == ("2024-03-11", "2024-03-12", "2024-03-13", "2024-03-15", "2024-03-18", "2024-03-19",
                             "2024-03-20")   # the weekend of 16-17 March is no gap
    replay = gather(market, when, REPLAY, RELIANCE)
    assert replay.of(Domain.MARKET) == [] and [(g.nature, g.count) for g in replay.gaps_of(Domain.MARKET)] == [
        (GapNature.WITHHELD, 1)]


def test_news_reaches_a_company_only_when_proven_to_name_it(news, world):
    bundle = gather(news, datetime(2026, 10, 3, 4, 30, tzinfo=UTC), CURRENT, HDFC)
    story = one(bundle, kind="news_story")
    assert story.value == REAL["srivatsan_banking"][1] and story.attribution == Attribution.DIRECT
    assert story.extraction_confidence == ExtractionConfidence.NAME_IN_HEADLINE_AND_LINK
    [excluded] = bundle.gaps_of(Domain.NEWS_EXTERNAL)
    assert (excluded.nature, excluded.count) == (GapNature.EXCLUDED, 1)   # found by the search, never named
    [degraded] = gather(world.c, AFTER, CURRENT, HDFC).gaps_of(Domain.NEWS_EXTERNAL)
    assert degraded.nature == GapNature.DEGRADED   # no article read yet: said, not a crash (4E)


def test_a_sebi_release_naming_the_company_is_its_own_and_a_circular_is_context(world):
    bundle = gather(world.c, AFTER, CURRENT, HDFC)
    named = one(bundle, kind="regulator_release")
    assert named.value == SEBI_NAMED and named.extraction_confidence == ExtractionConfidence.REGISTERED_NAME_IN_TITLE
    regulation = [e for e in bundle.evidence if e.kind == "macro_event" and e.source_id == "sebi_rss"]
    assert [e.value for e in regulation] == [JAGROOK] and regulation[0].attribution == Attribution.CONTEXT
    assert not [e for e in bundle.evidence if "Adjudication" in str(e.value)]   # names no company, no circular


# ---- events without an issuer and context -------------------------------------------------------------

def test_an_event_without_an_issuer_reaches_a_security_only_by_a_recorded_route(world):
    now = datetime.now(UTC) + timedelta(minutes=1)
    before = gather(world.c, now, CURRENT, HDFC, start="2026-09-01")
    fomc = one(before, kind="macro_event", source_id="fed_monetary_feed")
    assert fomc.subject == "context:macro_events:monetary_policy_and_rates" and fomc.attribution == Attribution.CONTEXT
    world.route(opec_route())
    after = gather(world.c, now, CURRENT, HDFC, start="2026-09-01")
    routed = one(after, kind="macro_event", source_id="fed_monetary_feed")
    assert (routed.subject, routed.attribution, routed.routes) == (HDFC, Attribution.ROUTE, ("fomc-to-hdfc-bank",))
    assert routed.details["relations"] == ["funding_cost"] and routed.evidence_id == fomc.evidence_id
    assert len(after.evidence) == len(before.evidence)   # given once, as routed - not again as context (4B rule 5)
    context_only = gather(world.c, now, CURRENT, start="2026-09-01")
    assert one(context_only, kind="macro_event", source_id="fed_monetary_feed").attribution == Attribution.CONTEXT


def test_flows_are_context_known_from_their_ingestion_and_withheld_under_replay(world):
    bundle = gather(world.c, AFTER, CURRENT, HDFC)
    dii = one(bundle, kind="investor_flow_net", value=9633.63)
    assert (dii.subject, dii.attribution, dii.observed) == ("context:flows:nse", Attribution.CONTEXT, "2026-10-01")
    assert dii.available_at == FLOWS_READ.isoformat() and dii.details["category"] == "DII"
    replay = gather(world.c, AFTER, REPLAY, HDFC)
    assert replay.of(Domain.OWNERSHIP_FLOWS) == []
    assert [(g.nature, g.count) for g in replay.gaps_of(Domain.OWNERSHIP_FLOWS)] == [(GapNature.WITHHELD, 2)]


def test_trading_days_without_a_flows_file_are_a_gap_never_a_value(world):
    [gap] = gather(world.c, AFTER, CURRENT).gaps_of(Domain.OWNERSHIP_FLOWS)
    assert gap.nature == GapNature.MISSING and gap.missing_class == MissingClass.EXTRACTION_FAILURE
    # 05-Sep to 05-Oct: 20 NSE trading days (14-Sep and 02-Oct are holidays); 01-Oct has its file
    assert gap.count == 18 and gap.items[:2] == ("2026-09-07", "2026-09-08") and len(gap.items) == 10
    assert not {"2026-09-05", "2026-09-06", "2026-09-14"} & set(gap.items)   # a weekend, an NSE holiday


def test_series_keep_their_own_date_vintage_and_unit(world):
    bundle = gather(world.c, AFTER, CURRENT)
    cpi = one(bundle, subject="context:fred:CPIAUCSL")   # older than the window: the newest value, under its date
    assert (cpi.observed, cpi.value, cpi.details["vintage"]) == ("2026-08-01", 334.131, "2026-09-11")
    assert cpi.evidence_id == "mc_vintages:CPIAUCSL:2026-08-01@2026-09-11" and cpi.unit
    india = one(bundle, subject="context:mospi:IN_CPI24_GEN_INDEX")
    assert (india.observed, india.value, india.available_at) == ("2026-08-01", 108.74, READ.isoformat())
    replay = gather(world.c, AFTER, REPLAY)
    assert not [e for e in replay.evidence if e.kind == "india_macro_observation"]
    assert [g.nature for g in replay.gaps_of(Domain.SECTOR_MACRO)] == [GapNature.WITHHELD]
    assert one(replay, subject="context:fred:CPIAUCSL").observed == "2026-08-01"   # FRED's release time is proven


def test_release_dates_known_in_advance_may_lie_ahead_of_the_window(world):
    bundle = gather(world.c, AFTER, CURRENT)
    days = sorted(e.observed for e in bundle.evidence if e.kind == "scheduled_release")
    assert "2026-10-14" in days and days[0] >= bundle.start
    assert all(e.available_at == READ.isoformat() for e in bundle.evidence if e.kind == "scheduled_release")


def test_domains_without_an_adapter_are_always_named_as_missing(world):
    bundle = gather(world.c, AFTER, CURRENT)
    not_built = {g.domain for g in bundle.gaps if g.nature == GapNature.NOT_BUILT}
    assert not_built == set(NOT_BUILT) == {Domain.PUBLIC_SENTIMENT, Domain.DERIVATIVES_POSITIONING,
                                           Domain.ALTERNATIVE_DATA}
    assert bundle.counts()[Domain.PUBLIC_SENTIMENT] == 0


# ---- 5A.2: the window is enforced, not requested -----------------------------------------------------------

def test_the_window_is_enforced_not_requested():
    run = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
    assert clamp_window(None, None, run) == ("2026-09-05", "2026-10-05", None)
    start, end, note = clamp_window("2026-09-01", "2026-12-31", run)
    assert (start, end) == ("2026-09-01", "2026-10-05") and "clamped" in note
    start, end, note = clamp_window("2026-11-01", "2026-11-11", run)   # wholly after: moved back, span kept
    assert (start, end) == ("2026-09-25", "2026-10-05") and "moved back" in note
    start, end, note = clamp_window("2026-9-1", "yesterday", run)
    assert (start, end) == ("2026-09-05", "2026-10-05") and "unreadable" in note
    assert clamp_window(None, None, datetime(2026, 10, 5, 20, 0, tzinfo=UTC))[1] == "2026-10-06"   # India's date
    with pytest.raises(ValueError):
        clamp_window("2026-10-02", "2026-10-01", run)
    assert gather(_empty(), run, CURRENT, end="2027-01-01").end == "2026-10-05"


def _empty():
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    return c


# ---- the evidence object refuses what breaks its rules -----------------------------------------------------

def test_a_value_and_a_missing_class_never_travel_together():
    assert record(value=None, missing_class=MissingClass.EXTRACTION_FAILURE).value is None
    for bad in (dict(value=None), dict(missing_class=MissingClass.NOT_DISCLOSED), dict(value=True),
                dict(value=math.nan), dict(value="  "), dict(value=[1])):
        with pytest.raises(EvidenceError):
            record(**bad)


def test_context_is_never_a_security_and_routes_are_never_implied():
    route = dict(subject=HDFC, attribution=Attribution.ROUTE, domain=Domain.NEWS_EXTERNAL, kind="macro_event",
                 evidence_id="macro_event:fed:1")
    assert record(**route, routes=("fomc-to-hdfc-bank",)).routes == ("fomc-to-hdfc-bank",)
    for bad in (dict(domain=Domain.MARKET), dict(subject=HDFC), dict(subject="context:Flows nse"),
                dict(**route), dict(**{**route, "domain": Domain.CORPORATE_EVENTS}, routes=("r",)),
                dict(subject=HDFC, attribution=Attribution.DIRECT, routes=("r",)),
                dict(subject="INE040A01035", attribution=Attribution.DIRECT)):
        with pytest.raises(EvidenceError):
            record(**bad)


def test_times_dates_names_and_readings_must_be_well_formed():
    assert record(extraction_confidence="issuer_title").extraction_confidence == ExtractionConfidence.ISSUER_TITLE
    for bad in (dict(available_at="2026-10-04T17:39:00"), dict(observed="20261001"), dict(observed="2026-10-1"),
                dict(extraction_confidence=0.9), dict(domain="sentiment"), dict(evidence_id="no-table"),
                dict(kind="Investor Flow"), dict(source_id=""), dict(claim=None)):
        with pytest.raises(EvidenceError):
            record(**bad)


def test_a_bundle_refuses_evidence_known_after_its_decision():
    late = record(available_at="2026-10-06T00:00:00+00:00")
    with pytest.raises(EvidenceError):
        Bundle(None, "2026-10-05T12:00:00+00:00", CURRENT, "2026-09-05", "2026-10-05", None, (late,), (), HUB_VERSION)
    with pytest.raises(EvidenceError):
        Bundle(None, "2026-10-07T12:00:00+00:00", REPLAY, "2026-09-05", "2026-10-05", None, (late,), (), HUB_VERSION)
