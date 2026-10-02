"""NSE financial results: the filing listing and XBRL files (architecture 40B step 7, 4, 4C, 5B).

Two inputs, loaded in this order:
  1. the results LISTING (CF-FR-*.csv): one row per filing with its XBRL link and
     NSE's exact dissemination time - the proven publication time (5B);
  2. the XBRL files themselves (INDAS_*.xml) with the reported figures.

Rules, each found on NSE's real files:
  - Basis is read from the file ("Consolidated" / "Standalone") and stored on
    every fact; consolidated and standalone never mix (40B step 7).
  - A period context is used only if its dates AGREE with the file's own
    reporting-period fields. NSE's 'FourD' context claims the quarter while
    holding year-to-date figures; such contexts are rejected, never guessed.
  - Only 3-month and 12-month periods are stored, as <field>_3m / <field>_12m.
  - Accounting identities are checked. A figure in a failing identity that no
    passing identity confirms is stored as missing: source_conflict (4C) -
    never as the zero or number the file shows.
  - The file has no ISIN: the company is found by NSE symbol as of the period
    end, and its name must match the registry.
  - When the listing has the filing, its basis, period and company must agree
    with the file, and the dissemination time becomes the published time.
  - Units are checked (INR, INR per share); values are stored as filed.
  - Only the non-financial Ind AS format is read; banks, insurers and NBFCs
    use other formats and are refused loudly.
Nothing here is ever repaired; every skipped item is recorded with a reason.
"""
import json
import xml.etree.ElementTree as ET
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from core.database import now_utc, run_in_transaction
from core.dates import strict_iso_date
from data_quality.missing_data import MissingClass
from data_quality.trust_chain import NoDataError
from ingestion.market_adapters import AdapterError, read_raw_table
from ingestion.nse_corporate_actions import normalise_name
from ingestion.source_registry import get_source
from provenance.availability import parse_timestamp
from provenance.pit_store import PitConflictError, record_fact
from provenance.raw_store import store_raw_artifact
from universe.entities import EntityError, resolve

INDEX_SOURCE = "nse_financial_results_index"
XBRL_SOURCE = "nse_financial_results_xbrl"
PARSER_VERSION = "nse-results-xbrl-1"
IST = timezone(timedelta(hours=5, minutes=30))
XBRLI = "{http://www.xbrl.org/2003/instance}"
XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"
TAXONOMY_PREFIX = "http://www.bseindia.com/xbrl/fin/"

INDEX_COLUMNS = ("COMPANY NAME", "AUDITED / UNAUDITED", "CUMULATIVE / NON-CUMULATIVE",
                 "CONSOLIDATED / NON-CONSOLIDATED", "PERIOD", "PERIOD ENDED", "** XBRL",
                 "Exchange Received Time", "Exchange Dissemination Time")
INDEX_TIME_FORMAT = "%d-%b-%Y %H:%M:%S"   # e.g. 30-Jul-2026 17:18:42, India time
LISTING_BASIS = {"Consolidated": "consolidated", "Non-Consolidated": "standalone"}
FILE_BASIS = {"consolidated": "consolidated", "standalone": "standalone"}
UNIT_MEASURES = {"INR": "iso4217:INR", "INR_per_share": "iso4217:INR/xbrli:shares"}
DURATIONS = {3: "3m", 12: "12m"}

# XBRL element -> (our field, unit). The one place this mapping lives.
FIELDS = {
    "RevenueFromOperations": ("revenue_from_operations", "INR"),
    "OtherIncome": ("other_income", "INR"),
    "Income": ("total_income", "INR"),
    "Expenses": ("total_expenses", "INR"),
    "FinanceCosts": ("finance_costs", "INR"),
    "DepreciationDepletionAndAmortisationExpense": ("depreciation", "INR"),
    "ProfitBeforeExceptionalItemsAndTax": ("profit_before_exceptional_items_and_tax", "INR"),
    "ExceptionalItemsBeforeTax": ("exceptional_items", "INR"),
    "ProfitBeforeTax": ("profit_before_tax", "INR"),
    "TaxExpense": ("tax_expense", "INR"),
    "ProfitLossForPeriodFromContinuingOperations": ("profit_from_continuing_operations", "INR"),
    "ProfitLossFromDiscontinuedOperationsAfterTax": ("profit_from_discontinued_operations", "INR"),
    "ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod": ("share_of_associates_and_jvs", "INR"),
    "NetMovementInRegulatoryDeferralAccountBalancesRelatedToProfitOrLossAndTheRelatedDeferredTaxMovement":
        ("regulatory_deferral_movement", "INR"),
    "ProfitLossForPeriod": ("net_profit", "INR"),
    "ProfitOrLossAttributableToOwnersOfParent": ("net_profit_owners", "INR"),
    "ProfitOrLossAttributableToNonControllingInterests": ("net_profit_minority", "INR"),
    "PaidUpValueOfEquityShareCapital": ("paid_up_equity_capital", "INR"),
    "FaceValueOfEquityShareCapital": ("face_value_per_share", "INR_per_share"),
    "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations": ("eps_basic", "INR_per_share"),
    "DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations": ("eps_diluted", "INR_per_share"),
}

# (name, total field, [(component field, sign)]) - checked only when every field is present.
IDENTITIES = [
    ("income = revenue + other income", "total_income",
     [("revenue_from_operations", 1), ("other_income", 1)]),
    ("PBT = pre-exceptional profit + exceptional items", "profit_before_tax",
     [("profit_before_exceptional_items_and_tax", 1), ("exceptional_items", 1)]),
    ("pre-exceptional profit = income - expenses", "profit_before_exceptional_items_and_tax",
     [("total_income", 1), ("total_expenses", -1)]),
    ("continuing profit = PBT - tax", "profit_from_continuing_operations",
     [("profit_before_tax", 1), ("tax_expense", -1)]),
    ("profit = continuing + discontinued + associates + regulatory", "net_profit",
     [("profit_from_continuing_operations", 1), ("profit_from_discontinued_operations", 1),
      ("share_of_associates_and_jvs", 1), ("regulatory_deferral_movement", 1)]),
    ("owners + minority = profit", "net_profit",
     [("net_profit_owners", 1), ("net_profit_minority", 1)]),
]


class ResultsFileError(AdapterError):
    """The file cannot be used as a whole. Nothing is stored."""


# ---- the listing ----------------------------------------------------------

def _ist(text):
    return datetime.strptime(text.strip(), INDEX_TIME_FORMAT).replace(tzinfo=IST)


def load_results_index(conn, path, retrieved_at, raw_dir=None):
    """Load NSE's financial-results listing. Returns a report dict."""
    get_source(conn, INDEX_SOURCE)
    header, rows = read_raw_table(path)
    missing = [c for c in INDEX_COLUMNS if c not in header]
    if missing:
        raise ResultsFileError(f"Not an NSE results listing: missing columns {missing}")
    if not rows:
        raise NoDataError("The results listing has no rows - nothing is stored")
    retrieved = parse_timestamp(retrieved_at)

    def work(c):
        artifact_id, _ = store_raw_artifact(c, INDEX_SOURCE, path, retrieved_at, raw_dir=raw_dir)
        counts, problems = {"recorded": 0, "already_present": 0}, []
        for row_number, row in rows:
            url = (row.get("** XBRL") or "").strip()
            try:
                if not (url.startswith("https://nsearchives.nseindia.com/") and url.lower().endswith(".xml")):
                    raise ValueError(f"XBRL link is not an NSE archive .xml: {url!r}")
                received, disseminated = _ist(row["Exchange Received Time"]), _ist(row["Exchange Dissemination Time"])
                if disseminated < received or disseminated > retrieved:
                    raise ValueError("dissemination time is before receipt or after this file was obtained")
                period_ended = datetime.strptime(row["PERIOD ENDED"].strip(), "%d-%b-%Y").date().isoformat()
                if row["CONSOLIDATED / NON-CONSOLIDATED"].strip() not in LISTING_BASIS:
                    raise ValueError(f"unknown basis {row['CONSOLIDATED / NON-CONSOLIDATED']!r}")
            except (ValueError, KeyError) as e:
                problems.append(("listing_row_rejected", f"row {row_number}: {e}"))
                continue
            values = [url.rsplit("/", 1)[1], row["COMPANY NAME"].strip(), row["AUDITED / UNAUDITED"].strip(),
                      row["CUMULATIVE / NON-CUMULATIVE"].strip(), row["CONSOLIDATED / NON-CONSOLIDATED"].strip(),
                      row["PERIOD"].strip(), period_ended, url, received.isoformat(), disseminated.isoformat()]
            existing = c.execute(
                "SELECT company_name, audited, cumulative, consolidated, period, period_ended, xbrl_url, received_at,"
                " disseminated_at FROM fr_filings WHERE xbrl_file_name = ?", [values[0]]).fetchone()
            if existing:
                if list(existing) == values[1:]:
                    counts["already_present"] += 1
                else:
                    problems.append(("listing_conflict", f"row {row_number}: {values[0]} already listed differently"))
                continue
            c.execute("INSERT INTO fr_filings (xbrl_file_name, company_name, audited, cumulative, consolidated, period,"
                      " period_ended, xbrl_url, received_at, disseminated_at, artifact_id, recorded_at)"
                      " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values + [artifact_id, now_utc()])
            counts["recorded"] += 1
        c.executemany("INSERT INTO fr_problems VALUES (NULL, ?, ?)", problems)
        return {"rows_in_file": len(rows), "filings_recorded": counts["recorded"],
                "already_present": counts["already_present"], "problems": [p[1] for p in problems]}

    return run_in_transaction(conn, work)


# ---- the XBRL file --------------------------------------------------------

def _decimal(text):
    try:
        return Decimal((text or "").strip())
    except InvalidOperation:
        return None


def _months(start, end):
    """Whole calendar months from the 1st of a month to the last day of a month, else None."""
    s, e = strict_iso_date(start), strict_iso_date(end)
    if s.day != 1 or e.day != monthrange(e.year, e.month)[1] or e < s:
        return None
    return (e.year - s.year) * 12 + e.month - s.month + 1


def parse_results_xbrl(path):
    """Read an XBRL results file into plain data. Raises ResultsFileError for unusable files."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        raise ResultsFileError(f"{Path(path).name}: not valid XML ({e})") from None
    contexts = {}
    for ctx in root.findall(f"{XBRLI}context"):
        period = ctx.find(f"{XBRLI}period")
        contexts[ctx.get("id")] = {
            "start": (period.findtext(f"{XBRLI}startDate") or "").strip(),
            "end": (period.findtext(f"{XBRLI}endDate") or "").strip(),
            "dimensional": ctx.find(f"{XBRLI}scenario") is not None,
        }
    units = {}
    for unit in root.findall(f"{XBRLI}unit"):
        measures = [m.text.strip() for m in unit.iter(f"{XBRLI}measure")]
        units[unit.get("id")] = "/".join(measures)
    facts = []
    for el in root:
        if not el.get("contextRef") or "}" not in el.tag:
            continue
        namespace, local = el.tag[1:].split("}", 1)
        facts.append({"namespace": namespace, "name": local, "context": el.get("contextRef"),
                      "unit": units.get(el.get("unitRef")), "decimals": el.get("decimals"),
                      "nil": el.get(XSI_NIL) == "true", "text": (el.text or "").strip()})
    if not any(f["namespace"].startswith(TAXONOMY_PREFIX) and f["name"] == "RevenueFromOperations" for f in facts):
        raise ResultsFileError(f"{Path(path).name}: not the non-financial Ind AS results format "
                               "(banks, insurers and NBFCs use other formats; not supported yet)")
    return contexts, facts


def _one_value(facts, name):
    values = {f["text"] for f in facts if f["name"] == name and f["text"]}
    if len(values) != 1:
        raise ResultsFileError(f"'{name}' must appear with exactly one value, found {sorted(values)}")
    return values.pop()


def _tolerance(decimals):
    return Decimal(0) if decimals in (None, "INF") else Decimal(10) ** (-int(decimals))


def load_results_xbrl(conn, path, retrieved_at, raw_dir=None):
    """Load one NSE results XBRL file into the point-in-time store. Returns a report dict."""
    get_source(conn, XBRL_SOURCE)
    contexts, facts = parse_results_xbrl(path)
    symbol = _one_value(facts, "Symbol")
    company = _one_value(facts, "NameOfTheCompany")
    if _one_value(facts, "DescriptionOfPresentationCurrency") != "INR":
        raise ResultsFileError("Only results presented in INR are read")
    basis = FILE_BASIS.get(_one_value(facts, "NatureOfReportStandaloneConsolidated").lower())
    if basis is None:
        raise ResultsFileError("NatureOfReportStandaloneConsolidated is neither Consolidated nor Standalone")
    audited = _one_value(facts, "WhetherResultsAreAuditedOrUnaudited")
    problems = []

    # Periods: a context is used only if its dates agree with the file's own period fields.
    declared = {}
    for f in facts:
        if f["name"] in ("DateOfStartOfReportingPeriod", "DateOfEndOfReportingPeriod"):
            declared.setdefault(f["context"], {})[f["name"]] = f["text"]
    periods = {}
    for ctx_id, ctx in contexts.items():
        if ctx["dimensional"] or not ctx["start"]:
            continue
        stated = declared.get(ctx_id, {})
        claim = (stated.get("DateOfStartOfReportingPeriod"), stated.get("DateOfEndOfReportingPeriod"))
        if claim != (ctx["start"], ctx["end"]):
            problems.append(("context_rejected", f"{ctx_id}: context says {ctx['start']}..{ctx['end']} but the "
                                                 f"file's period fields say {claim[0]}..{claim[1]}"))
            continue
        months = _months(ctx["start"], ctx["end"])
        if months not in DURATIONS:
            problems.append(("out_of_scope", f"{ctx_id}: {months}-month period is not stored (3m and 12m only)"))
            continue
        periods[ctx_id] = (ctx["end"], DURATIONS[months])
    if not periods:
        raise ResultsFileError(f"{Path(path).name}: no period context can be used; nothing is stored")

    # Identity: by NSE symbol as of the period end, and the name must match.
    period_end = min(end for end, _ in periods.values())
    try:
        strict_iso_date(period_end)
        isin = resolve(conn, symbol, period_end, alias_type="nse_symbol")
    except (ValueError, EntityError) as e:
        raise ResultsFileError(f"{symbol}: not attached to a company as of {period_end}: {e}") from None
    legal_name = conn.execute("SELECT legal_name FROM entities WHERE isin = ?", [isin]).fetchone()[0]
    if normalise_name(legal_name) != normalise_name(company):
        raise ResultsFileError(f"{symbol}: file names {company!r} but the registry has {legal_name!r}")

    # Listing: cross-check and take the proven publication time.
    filing = conn.execute("SELECT filing_id, company_name, consolidated, period_ended, disseminated_at, artifact_id"
                          " FROM fr_filings WHERE xbrl_file_name = ?", [Path(path).name]).fetchone()
    published_at = evidence = None
    if filing:
        filing_id, listed_name, listed_basis, listed_end, disseminated_at, listing_artifact = filing
        if LISTING_BASIS[listed_basis] != basis:
            raise ResultsFileError(f"The listing says {listed_basis} but the file says {basis}")
        if listed_end not in {end for end, _ in periods.values()}:
            raise ResultsFileError(f"The listing says period ended {listed_end}; the file's periods disagree")
        if normalise_name(listed_name) != normalise_name(company):
            raise ResultsFileError(f"The listing names {listed_name!r}; the file names {company!r}")
        if parse_timestamp(disseminated_at) > parse_timestamp(retrieved_at):
            raise ResultsFileError("The listing's dissemination time is after this file was obtained")
        published_at = disseminated_at
        evidence = f"NSE results listing (artifact {listing_artifact}): exchange dissemination time {disseminated_at}"
    else:
        filing_id = None
        problems.append(("no_listing", "file not in a loaded results listing: publication time not proven (5B)"))

    # Figures per usable period, with unit checks.
    values = {}
    for ctx_id in periods:
        found = {}
        for f in facts:
            if f["context"] != ctx_id or f["name"] not in FIELDS:
                continue
            field, unit = FIELDS[f["name"]]
            amount = _decimal(f["text"])
            if f["nil"] or amount is None:
                problems.append(("empty_value", f"{ctx_id} {f['name']}: no value in the file - not stored"))
            elif f["unit"] != UNIT_MEASURES[unit]:
                problems.append(("unit_mismatch", f"{ctx_id} {f['name']}: unit {f['unit']}, expected {UNIT_MEASURES[unit]}"))
            elif field in found:
                problems.append(("duplicate", f"{ctx_id} {f['name']}: appears more than once - not stored"))
                found[field] = None
            else:
                found[field] = (amount, unit, f["decimals"])
        values[ctx_id] = {k: v for k, v in found.items() if v is not None}

    # Accounting identities.
    conflicted = {}
    for ctx_id, found in values.items():
        failing, passing = set(), set()
        for name, total, parts in IDENTITIES:
            fields = [total] + [p for p, _ in parts]
            if not all(f in found for f in fields):
                continue
            rhs = sum(found[p][0] * sign for p, sign in parts)
            tolerance = sum(_tolerance(found[f][2]) for f in fields)
            if abs(found[total][0] - rhs) <= tolerance:
                passing.update(fields)
            else:
                failing.update(fields)
                problems.append(("identity_failed", f"{ctx_id}: {name} fails ({found[total][0]} vs {rhs})"))
        conflicted[ctx_id] = failing - passing

    def work(c):
        artifact_id, _ = store_raw_artifact(c, XBRL_SOURCE, path, retrieved_at, published_at, evidence, raw_dir)
        counts = {"recorded": 0, "already_present": 0, "marked_conflict": 0}
        for ctx_id, (end, duration) in periods.items():
            for field, (amount, unit, _) in values[ctx_id].items():
                key = f"{field}_{duration}"
                existed = c.execute("SELECT 1 FROM pit_facts WHERE isin = ? AND field = ? AND basis = ? AND"
                                    " period_end = ?", [isin, key, basis, end]).fetchone()
                try:
                    if field in conflicted[ctx_id]:
                        record_fact(c, isin, key, basis, end, None, unit, artifact_id,
                                    missing_class=MissingClass.SOURCE_CONFLICT)
                        counts["marked_conflict"] += 1
                    else:
                        record_fact(c, isin, key, basis, end, float(amount), unit, artifact_id)
                    counts["already_present" if existed else "recorded"] += 1
                except PitConflictError as e:
                    problems.append(("conflicts_with_recorded_fact", f"{key} {end}: {e}"))
        load_id = c.execute(
            "INSERT INTO fr_loads (artifact_id, parser_version, isin, symbol, basis, audited, filing_id, facts_recorded,"
            " facts_already_present, facts_marked_conflict, problems, recorded_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [artifact_id, PARSER_VERSION, isin, symbol, basis, audited, filing_id, counts["recorded"],
             counts["already_present"], counts["marked_conflict"], len(problems), now_utc()]).lastrowid
        c.executemany("INSERT INTO fr_problems VALUES (?, ?, ?)", [(load_id, k, d) for k, d in problems])
        return {"load_id": load_id, "symbol": symbol, "isin": isin, "basis": basis,
                "periods": sorted(f"{end} ({d})" for end, d in periods.values()),
                "publication_proven": published_at is not None, "facts_recorded": counts["recorded"],
                "already_present": counts["already_present"], "marked_source_conflict": counts["marked_conflict"],
                "problems": [f"{k}: {d}" for k, d in problems]}

    return run_in_transaction(conn, work)
