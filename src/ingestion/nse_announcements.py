"""NSE corporate announcements and the events they describe (architecture 40B step 8, 4, 4A, 4D, 5B).

Input: NSE's Corporate Announcements listing (CF-AN-equities-*.csv), downloaded by a person
(ADR-004). One row per filing: symbol, company, subject, details, receipt and dissemination
times, and the link to the attached document.

Rules, each found on NSE's real files:
  - Identity first (4): the company is found by NSE symbol as of the filing date and its name
    must match the registry; otherwise the row is refused and recorded, never guessed.
  - The exchange's dissemination time is the filing's proven publication time (5B).
  - A filing is stored once: the same row in two downloads is already present.
  - Text is data, never instruction (4D): subject and details are stored verbatim and only
    ever compared, never acted on.
  - One release, one event (4A rule 2). Companies often file one document several times under
    different subjects (HDFC Bank, 18-Apr-2026: one board outcome filed four times in 23
    minutes). Rule an-dedup-1 treats filings as one release only when the company and the
    attachment's original file name agree, the name is distinctive, and each filing falls
    within 60 minutes of the release's first filing. Generic names ('intimation.pdf', a bare
    symbol) never merge, and neither does a name reused later: real files reuse both for
    different documents, and a wrong merge would date later information too early.
  - Events are derived from the stored filings by the versioned rule, never stored. Filings
    not yet known at the decision time are left out before grouping, so a later
    republication can never move an event earlier.
  - Event types come from NSE's subject through a versioned mapping (an-types-1) to the
    registered types (4A.0). Subjects without one meaning stay unclassified - never guessed.
    Extraction confidence describes only that mapping and is never investment confidence
    (4A rule 4).
"""
import re
from datetime import datetime, timedelta

from core.database import now_utc, run_in_transaction
from data_quality.trust_chain import NoDataError
from ingestion.market_adapters import AdapterError, read_raw_table
from ingestion.nse_corporate_actions import normalise_name
from ingestion.nse_financial_results import IST, NSE_ARCHIVE
from ingestion.source_registry import get_source
from provenance.availability import Availability, PitClaim, disposition, parse_timestamp
from provenance.raw_store import store_raw_artifact
from universe.entities import EntityError, resolve

SOURCE_ID = "nse_announcements"
COLUMNS = ("SYMBOL", "COMPANY NAME", "SUBJECT", "DETAILS", "RECEIPT", "DISSEMINATION", "ATTACHMENT")
RECEIPT_FORMAT = "%Y-%m-%d %H:%M:%S"          # e.g. 2026-10-01 18:23:52, India time
DISSEMINATION_FORMAT = "%d-%b-%Y %H:%M:%S"    # e.g. 01-Oct-2026 18:23:53, India time
ATTACHMENT_FILE = re.compile(r"^(?P<uploader>.+?)_(?P<stamp>\d{14})_(?P<name>.+)$")   # UPLOADER_ddmmyyyyhhmmss_name
PROBLEMS_SHOWN = 10

DEDUP_RULE = "an-dedup-1"
DEDUP_WINDOW = timedelta(minutes=60)
MIN_DISTINCTIVE_CHARS = 12
GENERIC_NAMES = frozenset({
    "intimation", "intimationsigned", "seintimation", "intimationtose", "intimationtostockexchange", "outcome",
    "outcomeofboardmeeting", "disclosure", "upload", "result", "results", "letter", "coveringletter", "filing",
    "document", "scan", "file", "attachment", "signed", "announcement", "proceedings", "votingresults",
    "scrutinizerreport", "reg30", "regulation30", "tradingwindow", "tradingwindowclosure", "closureoftradingwindow",
    "newspaperpublication", "newspaperadvertisement",
})

MAPPING_VERSION = "an-types-1"
EVENT_TYPES = {   # registered event types (4A.0), by group
    "results_and_guidance": {"results", "guidance_issue", "guidance_revision", "pre_quarter_update"},
    "operations": {"order_win", "capex_announcement", "capacity_commissioning", "plant_shutdown", "price_revision"},
    "corporate_actions": {"dividend", "bonus", "split", "buyback", "rights_issue", "qip", "preferential_allotment",
                          "warrant_conversion", "demerger", "delisting"},
    "ma_and_structure": {"acquisition", "divestment", "joint_venture", "restructuring", "promoter_stake_change"},
    "governance": {"auditor_change", "qualified_opinion", "kmp_departure", "board_change", "management_change",
                   "related_party_transaction", "accounting_policy_change"},
    "credit_and_distress": {"rating_action", "outlook_change", "default", "debt_restructuring", "nclt_admission",
                            "ibc_proceeding"},
    "legal_and_regulatory": {"sebi_order", "tax_dispute", "litigation", "environmental_action", "licence_change"},
    "index_and_market_structure": {"index_change", "fo_segment_change", "surveillance_stage", "circuit_or_ban"},
}
REGISTERED_TYPES = frozenset().union(*EVENT_TYPES.values())
SUBJECT_TYPES = {   # NSE subject -> registered type; only subjects with one meaning
    "Dividend": "dividend", "Bonus": "bonus", "Stock split": "split", "Buyback": "buyback",
    "Post Buyback Public Announcement": "buyback", "Closure of Buy Back": "buyback", "Rights Issue": "rights_issue",
    "Qualified Institutional Placement": "qip", "Preferential issue": "preferential_allotment", "Demerger": "demerger",
    "Acquisition": "acquisition", "Sale or disposal": "divestment", "Amalgamation/Merger": "restructuring",
    "Scheme of Arrangement": "restructuring", "Other Restructuring": "restructuring",
    "Disclosure under SEBI Takeover Regulations": "promoter_stake_change",
    "Public Announcement-Open Offer": "promoter_stake_change",
    "Bagging/Receiving of orders/contracts": "order_win", "Awarding of order(s)/contract(s)": "order_win",
    "Commencement of commercial production/operations": "capacity_commissioning",
    "Capacity addition": "capacity_commissioning", "Disruption of Operations": "plant_shutdown",
    "Strikes/Lockouts/Disturbances": "plant_shutdown", "Monthly Business Updates": "pre_quarter_update",
    "Integrated Filing- Financial": "results", "Change in Auditors": "auditor_change",
    "Resignation of Statutory Auditor": "auditor_change", "Resignation of Director/KMP/SMP": "kmp_departure",
    "Resignation": "kmp_departure", "Resignation of Independent director": "kmp_departure",
    "Cessation": "kmp_departure", "Retirement": "kmp_departure", "Change in Director(s)": "board_change",
    "Appointment": "management_change", "Change in Management": "management_change",
    "Change in Company Secretary/Compliance Officer": "management_change",
    "Credit Rating": "rating_action", "Credit Rating- New": "rating_action", "Credit Rating- Revision": "rating_action",
    "Credit Rating- Others": "rating_action", "Defaults on Payment of Interest/Principal": "default",
    "Corporate Insolvency Resolution Process": "ibc_proceeding",
    "Pendency of Litigation(s)/dispute(s) or the outcome impacting the Company": "litigation",
    "Granting/withdrawal/surrender/cancellation/suspension of key licenses/ regulatory approvals": "licence_change",
}
ROUTINE_SUBJECTS = frozenset({
    "Trading Window", "Shareholders meeting", "Copy of Newspaper Publication",
    "Analysts/Institutional Investor Meet/Con. Call Updates", "Investor Presentation",
    "Certificate under SEBI (Depositories and Participants) Regulations, 2018", "Committee Meeting Updates",
    "Structural Digital Database", "Trading Plan under PIT", "Registrar & Share Transfer Agent Update",
    "Issue of Duplicate Share Certificate", "Loss of Share Certificates", "ESOP/ESOS/ESPS", "Record Date",
    "Statement of deviation(s) or variation(s) under Reg. 32",
})
EXCHANGE_QUERY_SUBJECTS = frozenset({"News Verification", "Spurt in Volume", "Price movement",
                                     "Rumour Verification - Regulation 30(11)"})


class AnnouncementsFileError(AdapterError):
    """The file cannot be used as a whole. Nothing is stored."""


def _attachment_name(url):
    """The company's original file name from an NSE attachment link, or None."""
    if not url.startswith(NSE_ARCHIVE + "corporate/"):
        return None
    match = ATTACHMENT_FILE.match(url.rsplit("/", 1)[1])
    return match["name"] if match else None


def distinctive(name, symbol):
    """True when a file name could identify one document: long enough, not generic, not a bare symbol."""
    if not name:
        return False
    stem = re.sub(r"[^a-z0-9]", "", re.sub(r"\.[a-z0-9]+$", "", name.lower()))
    bare_symbol = re.sub(r"[^a-z0-9]", "", symbol.lower())
    return (len(stem) >= MIN_DISTINCTIVE_CHARS and stem not in GENERIC_NAMES
            and not re.fullmatch(re.escape(bare_symbol) + r"\d*", stem))


def subject_class(subject):
    """(event type or None, kind) for one NSE subject under mapping an-types-1."""
    if subject in SUBJECT_TYPES:
        return SUBJECT_TYPES[subject], "typed"
    if subject in EXCHANGE_QUERY_SUBJECTS:
        return None, "exchange_query"
    if subject in ROUTINE_SUBJECTS:
        return None, "routine"
    return None, "unclassified"


def _parse_row(conn, row, retrieved):
    symbol, company, subject = row["SYMBOL"].strip(), row["COMPANY NAME"].strip(), row["SUBJECT"].strip()
    if not symbol or not subject:
        raise ValueError("no symbol or no subject")
    received = datetime.strptime(row["RECEIPT"].strip(), RECEIPT_FORMAT).replace(tzinfo=IST)
    disseminated = datetime.strptime(row["DISSEMINATION"].strip(), DISSEMINATION_FORMAT).replace(tzinfo=IST)
    if disseminated < received or disseminated > retrieved:
        raise ValueError("dissemination time is before receipt or after this file was obtained")
    try:
        isin = resolve(conn, symbol, received.date().isoformat(), alias_type="nse_symbol")
    except EntityError as e:
        raise ValueError(f"{symbol} is not a company in the registry on {received.date()}: {e}") from None
    legal_name = conn.execute("SELECT legal_name FROM entities WHERE isin = ?", [isin]).fetchone()[0]
    if normalise_name(legal_name) != normalise_name(company):
        raise ValueError(f"{symbol}: the file names {company!r} but the registry has {legal_name!r}")
    url = row["ATTACHMENT"].strip()
    url = "" if url in ("", "-") else url
    return [isin, symbol, company, subject, row["DETAILS"].strip(), received.isoformat(), disseminated.isoformat(),
            url, _attachment_name(url)]


FILING_COLUMNS = ("isin", "symbol", "company_name", "subject", "details", "received_at", "disseminated_at",
                  "attachment_url", "attachment_name")


def load_announcements(conn, path, retrieved_at, raw_dir=None):
    """Load one NSE corporate announcements listing. Returns a report dict."""
    get_source(conn, SOURCE_ID)
    header, rows = read_raw_table(path)
    missing = [c for c in COLUMNS if c not in header]
    if missing:
        raise AnnouncementsFileError(f"Not an NSE announcements listing: missing columns {missing}")
    if not rows:
        raise NoDataError("The announcements listing has no rows - nothing is stored")
    retrieved = parse_timestamp(retrieved_at)

    def work(c):
        artifact_id, _ = store_raw_artifact(c, SOURCE_ID, path, retrieved_at, raw_dir=raw_dir)
        counts, problems = {"recorded": 0, "already_present": 0}, []
        for row_number, row in rows:
            try:
                values = _parse_row(c, row, retrieved)
            except (ValueError, KeyError) as e:
                problems.append(("row_refused", f"row {row_number}: {e}"))
                continue
            existing = c.execute(
                f"SELECT {', '.join(FILING_COLUMNS)} FROM an_filings WHERE symbol = ? AND received_at = ? AND subject = ?"
                " AND attachment_url = ? AND details = ?", [values[1], values[5], values[3], values[7], values[4]]).fetchone()
            if existing:
                if list(existing) == values:
                    counts["already_present"] += 1
                else:
                    problems.append(("listing_conflict", f"row {row_number}: this filing is already recorded differently"))
                continue
            c.execute(f"INSERT INTO an_filings ({', '.join(FILING_COLUMNS)}, artifact_id, recorded_at)"
                      " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values + [artifact_id, now_utc()])
            counts["recorded"] += 1
        load_id = c.execute(
            "INSERT INTO an_loads (artifact_id, rows_in_file, filings_recorded, already_present, rows_refused,"
            " recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
            [artifact_id, len(rows), counts["recorded"], counts["already_present"], len(problems), now_utc()]).lastrowid
        c.executemany("INSERT INTO an_problems VALUES (?, ?, ?)", [(load_id, k, d) for k, d in problems])
        shown = [f"{k}: {d}" for k, d in problems[:PROBLEMS_SHOWN]]
        if len(problems) > PROBLEMS_SHOWN:
            shown.append(f"... and {len(problems) - PROBLEMS_SHOWN} more (table an_problems, load {load_id})")
        return {"load_id": load_id, "rows_in_file": len(rows), "filings_recorded": counts["recorded"],
                "already_present": counts["already_present"], "rows_refused": len(problems), "problems": shown}

    return run_in_transaction(conn, work)


# ---- events -------------------------------------------------------------------

def events(conn, decision_time, claim=PitClaim.CURRENT_DECISION, isin=None):
    """The events known at decision_time under the claim (5B.2), oldest first. Each event is one
    release: its filings, every subject with the time it was first disseminated, the mapped types,
    and the versions of the rule and the mapping that produced it."""
    sql = ("SELECT f.filing_id, f.isin, f.symbol, f.subject, f.disseminated_at, f.attachment_name, a.retrieved_at"
           " FROM an_filings f JOIN raw_artifacts a ON a.artifact_id = f.artifact_id")
    rows = conn.execute(sql + (" WHERE f.isin = ?" if isin else ""), [isin] if isin else []).fetchall()
    known = [r for r in rows if disposition(claim, decision_time, r[6], r[4]) == Availability.ELIGIBLE]
    known.sort(key=lambda r: (r[1], parse_timestamp(r[4]), r[0]))
    releases, open_release = [], {}
    for filing_id, isin_, symbol, subject, disseminated, name, _ in known:
        when = parse_timestamp(disseminated)
        key = (isin_, name.lower()) if distinctive(name, symbol) else None
        current = open_release.get(key) if key else None
        if current is not None and when - current["first"] <= DEDUP_WINDOW:
            current["filings"].append((filing_id, subject, disseminated))
            continue
        release = {"first": when, "isin": isin_, "symbol": symbol, "filings": [(filing_id, subject, disseminated)]}
        releases.append(release)
        if key:
            open_release[key] = release
    return [_event(r) for r in sorted(releases, key=lambda r: (r["first"], r["filings"][0][0]))]


def _event(release):
    subjects = {}
    for _, subject, disseminated in release["filings"]:
        subjects.setdefault(subject, disseminated)
    classes = [subject_class(s) for s in subjects]
    types = sorted({t for t, _ in classes if t})
    kinds = {k for _, k in classes}
    kind = next(k for k in ("typed", "exchange_query", "unclassified", "routine") if k in kinds)
    return {"event_id": release["filings"][0][0], "isin": release["isin"], "symbol": release["symbol"],
            "published_at": release["filings"][0][2], "filings": [f[0] for f in release["filings"]],
            "subjects": subjects, "event_types": types, "kind": kind,
            "extraction_confidence": "exchange subject" if types else "none",
            "dedup_rule": DEDUP_RULE, "mapping_version": MAPPING_VERSION}
