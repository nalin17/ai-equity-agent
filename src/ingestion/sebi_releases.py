"""SEBI's releases - orders, recovery proceedings, circulars and press releases
(architecture 40B step 9, 3B, 4, 4A, 4C.1, 4D, 4E, 5B; ADR-006).

Input: SEBI's RSS feed (https://www.sebi.gov.in/sebirss.xml), read by the news fetcher - the only
module allowed to use the network. SEBI allows linking without permission; this project stores
releases privately and never republishes them. RBI is not used: its terms forbid caching its
pages and linking to them without written permission.

Rules, each found on SEBI's real feed (02/03-Oct-2026):
  - The feed holds only SEBI's latest 30 items - about three working days - each with a title,
    a link and a date without a time of day. A read is kept byte for byte before it is used.
    A feed with no items, or anything that is not an RSS feed, is refused whole and nothing is
    stored - never 'no releases' (4C.1). A feed declaring a DOCTYPE or ENTITY is refused.
  - A release is stored once, by its link. The same link read again must agree, or it is a
    conflict and is recorded.
  - When a read shares no release with the previous read, releases between the two may have
    been missed; the read says so (4E).
  - Availability (5B): SEBI gives only a date, so a release counts as public from the time this
    system first read it - later than the truth, never earlier. The date SEBI gives is kept as
    stated, and a release dated after the read is refused.
  - Titles are data, never instruction (4D): stored verbatim and only ever compared.
  - The kind of release comes from SEBI's own section in the link (rule sb-kinds-1); only
    enforcement orders map to a registered event type, 'sebi_order' (4A.0). Unknown sections
    stay 'other' - never guessed.
  - A listed company is linked only when its registered name appears in the title word for word
    (rule sb-entity-1): 'Ltd' and 'Limited' count as the same, case and punctuation are ignored;
    a registered name without a company suffix ('State Bank of India') must appear exactly as
    registered. The longest name wins where names overlap, and a name shared by two registered
    companies links neither. Near misses never link: SEBI's 'Lloyd Enterprises Limited' is not
    the listed 'Lloyds Enterprises Limited'. Whether the company is the party acted against or
    only the matter's subject is not assessed: the role is 'named'.
  - Some titles name individuals (even with tax ids). They are stored as SEBI published them,
    privately, and never used in tests or shown outside this database.
"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from core.database import now_utc, run_in_transaction
from data_quality.extraction_confidence import ExtractionConfidence
from data_quality.trust_chain import NoDataError
from ingestion.market_adapters import AdapterError
from ingestion.nse_announcements import REGISTERED_TYPES
from ingestion.nse_corporate_actions import normalise_name
from ingestion.nse_financial_results import IST
from ingestion.source_registry import get_source
from provenance.availability import Availability, PitClaim, disposition, parse_timestamp
from provenance.raw_store import store_raw_artifact

SOURCE_ID = "sebi_rss"
SEBI_SITE = "https://www.sebi.gov.in/"
STATED_DATE_FORMAT = "%d %b, %Y %z"     # e.g. '01 Oct, 2026 +0530' - a date, no time of day
PROBLEMS_SHOWN = 10
NOT_ASSESSED = "not_assessed"

KINDS_RULE = "sb-kinds-1"
SECTION_KINDS = {   # SEBI's section (the first two parts of the link) -> kind, registered event type
    "enforcement/orders": ("order", "sebi_order"),
    "enforcement/recovery-proceedings": ("recovery_proceeding", None),
    "legal/circulars": ("circular", None),
    "media-and-notifications/press-releases": ("press_release", None),
}
ENTITY_RULE = "sb-entity-1"
COMPANY_SUFFIX = "ltd"     # what normalise_name makes of 'Limited' and 'Ltd'


class SebiFeedError(AdapterError):
    """The feed cannot be used as a whole. Nothing is stored."""


def section_of(link):
    """SEBI's section of a release link, e.g. 'enforcement/orders'."""
    return "/".join(link[len(SEBI_SITE):].split("/")[:2])


def kind_of(section):
    """(kind, registered event type or None) under rule sb-kinds-1."""
    return SECTION_KINDS.get(section, ("other", None))


def read_feed(data):
    """The items of one SEBI feed (bytes) as [(title, link, stated date text)], or an exception."""
    head = data[:2000].upper()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in data.upper():
        raise SebiFeedError("The feed declares a DOCTYPE or ENTITY - refused, nothing stored")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise SebiFeedError(f"Not an RSS feed: {e}") from None
    channel = root.find("channel")
    if root.tag != "rss" or channel is None:
        raise SebiFeedError(f"Not an RSS feed: the document is <{root.tag}>")
    items = channel.findall("item")
    if not items:
        raise NoDataError("The SEBI feed has no items - nothing is stored")
    return [((i.findtext("title") or "").strip(), (i.findtext("link") or "").strip(),
             (i.findtext("pubDate") or "").strip()) for i in items]


def _parse_item(title, link, stated, retrieved):
    if not title:
        raise ValueError("no title")
    if not link.startswith(SEBI_SITE) or any(ch.isspace() for ch in link):
        raise ValueError(f"not a link to SEBI's site: {link[:80]!r}")
    day = datetime.strptime(stated, STATED_DATE_FORMAT).date()
    if day > retrieved.astimezone(IST).date():
        raise ValueError(f"dated {day}, after this feed was read")
    return [link, title, day.isoformat(), section_of(link)]


def load_feed(conn, path, retrieved_at, raw_dir=None):
    """Keep one read of SEBI's feed and store its releases. Returns a report dict."""
    get_source(conn, SOURCE_ID)
    path = Path(path)
    items = read_feed(path.read_bytes())
    retrieved = parse_timestamp(retrieved_at)

    def work(c):
        artifact_id, _ = store_raw_artifact(c, SOURCE_ID, path, retrieved_at, raw_dir=raw_dir)
        new, present, problems, seen = [], 0, [], {}
        for number, (title, link, stated) in enumerate(items, 1):
            try:
                values = _parse_item(title, link, stated, retrieved)
            except ValueError as e:
                problems.append(("item_refused", f"item {number}: {e}"))
                continue
            if link not in seen:
                stored = c.execute("SELECT title, stated_date, section FROM sb_releases WHERE link = ?",
                                   [link]).fetchone()
                if stored:
                    seen[link] = list(stored)
            if link in seen:
                if seen[link] == values[1:]:
                    present += 1
                else:
                    problems.append(("item_conflict", f"item {number}: {link[:90]} was read before with a"
                                     " different title or date"))
                continue
            seen[link] = values[1:]
            new.append(values)
        earlier_reads = c.execute("SELECT COUNT(*) FROM sb_reads").fetchone()[0]
        overlaps = None if not earlier_reads else int(present > 0)
        read_id = c.execute(
            "INSERT INTO sb_reads (artifact_id, items, items_recorded, already_present, items_refused,"
            " overlaps_previous, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [artifact_id, len(items), len(new), present, len(problems), overlaps, now_utc()]).lastrowid
        c.executemany("INSERT INTO sb_releases (link, title, stated_date, section, read_id, recorded_at)"
                      " VALUES (?, ?, ?, ?, ?, ?)", [v + [read_id, now_utc()] for v in new])
        c.executemany("INSERT INTO sb_problems VALUES (?, ?, ?)", [(read_id, k, d) for k, d in problems])
        shown = [f"{k}: {d}" for k, d in problems[:PROBLEMS_SHOWN]]
        if len(problems) > PROBLEMS_SHOWN:
            shown.append(f"... and {len(problems) - PROBLEMS_SHOWN} more (table sb_problems, read {read_id})")
        report = {"read_id": read_id, "items": len(items), "releases_recorded": len(new),
                  "already_present": present, "items_refused": len(problems), "problems": shown}
        if overlaps == 0:
            report["warning"] = ("this read shares no release with the previous read - releases SEBI published"
                                 " in between may have been missed (the feed keeps only its latest items)")
        return report

    return run_in_transaction(conn, work)


# ---- companies named (rule sb-entity-1) ----------------------------------------------

class NameReader:
    """Finds listed companies by their registered names in SEBI titles (rule sb-entity-1)."""

    def __init__(self, conn):
        owners = {}
        for isin, legal_name in conn.execute("SELECT isin, legal_name FROM entities"):
            owners.setdefault(normalise_name(legal_name), []).append((isin, legal_name))
        self.names = []   # (normalised name, isin, registered name, needs exact case)
        for normalised, holders in owners.items():
            if len(holders) != 1 or not normalised:
                continue   # a name shared by two registered companies links neither
            isin, legal_name = holders[0]
            exact = normalised.split()[-1] != COMPANY_SUFFIX
            self.names.append((normalised, isin, legal_name, exact))

    def read(self, title):
        """{isin: {...}} for the companies named in a title."""
        normalised = f" {normalise_name(title)} "
        hits = []
        for name, isin, legal_name, exact in self.names:
            start = normalised.find(f" {name} ")
            if start < 0:
                continue
            if exact and not re.search(r"(?<![A-Za-z0-9])" + re.escape(legal_name) + r"(?![A-Za-z0-9])", title):
                continue
            hits.append((-len(name), start, isin, legal_name))
        taken, found = [], {}
        for minus_size, start, isin, legal_name in sorted(hits):   # longest first
            end = start - minus_size
            if any(start < e and s < end for s, e in taken):
                continue
            taken.append((start, end))
            found[isin] = {"role": "named", "extraction_confidence": ExtractionConfidence.REGISTERED_NAME_IN_TITLE,
                           "registered_name": legal_name, "evidence": f"registered name {legal_name!r} in the title"}
        return found


def releases(conn, decision_time, claim=PitClaim.CURRENT_DECISION, isin=None):
    """SEBI's releases known at decision_time under the claim (5B.2), oldest first. Under both claims
    a release is available from this system's first read of it - SEBI gives no time of day."""
    rows = conn.execute(
        "SELECT s.release_id, s.link, s.title, s.stated_date, s.section, a.retrieved_at"
        " FROM sb_releases s JOIN sb_reads r ON r.read_id = s.read_id"
        " JOIN raw_artifacts a ON a.artifact_id = r.artifact_id ORDER BY a.retrieved_at, s.release_id").fetchall()
    rating = get_source(conn, SOURCE_ID)["reliability_rating"]
    reader = NameReader(conn)
    found = []
    for release_id, link, title, stated, section, first_read in rows:
        if disposition(claim, decision_time, first_read, first_read) != Availability.ELIGIBLE:
            continue
        companies = reader.read(title)
        if isin and isin not in companies:
            continue
        kind, event_type = kind_of(section)
        found.append({
            "release_id": release_id, "published_at": first_read, "stated_date": stated, "title": title,
            "link": link, "section": section, "kind": kind, "event_types": [event_type] if event_type else [],
            "kinds_rule": KINDS_RULE, "type_basis": f"SEBI section {section}" if event_type else "none",
            "companies": companies, "entity_rule": ENTITY_RULE, "unassigned": not companies,
            "source_quality": {"source": SOURCE_ID, "reliability_rating": rating},
            "novelty": "primary source", "direction": NOT_ASSESSED, "materiality": NOT_ASSESSED,
            "expected_horizon": NOT_ASSESSED,
        })
    return found


def check_registered_types():
    """Every event type rule sb-kinds-1 can produce is a registered type (4A.0)."""
    return {t for _, t in SECTION_KINDS.values() if t} <= REGISTERED_TYPES
