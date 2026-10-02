"""NSE financial results: filing listings and XBRL files (architecture 40B step 7, 4, 4C, 5B, 9B).

NSE publishes results in two places, and both are read here:
  - the OLD 'Financial Results' page (periods up to December 2024): listing CF-FR-*.csv
    and INDAS_*.xml files in BSE's Ind AS taxonomy - non-financial companies only;
  - the 'Integrated Filing - Financials' page (quarters ended March 2025 onwards, SEBI
    format): listing CF-Integrated-Filing-*.csv and INTEGRATED_FILING_*.xml files -
    Ind AS companies and banks.
Load a listing before its XBRL files: the listing holds the proven publication time (5B).

Rules, each found on NSE's real files:
  - Basis is read from the file and stored on every fact; consolidated and standalone
    never mix (40B step 7).
  - A period context is used only if its dates AGREE with the file's own reporting-period
    fields. The old format's 'FourD' context claims the quarter while holding year-to-date
    figures; such contexts are rejected, never guessed.
  - Only 3-month and 12-month periods are stored, as <field>_3m / <field>_12m.
  - Accounting identities are checked for each format. A figure in a failing identity that
    no passing identity confirms is stored as missing: source_conflict (4C).
  - The company is found by NSE symbol as of the period end and its name must match the
    registry; in the SEBI format the file's own ISIN must also be that company's ISIN.
  - Bank asset-quality, capital and return ratios are measures of the bank itself: they are
    taken from the standalone report only (consolidated reports carry placeholder zeros).
  - Paid-up capital, face value and CET1 can never be zero or negative: such a value is a
    placeholder and is not stored.
  - Units are checked (INR, INR per share, ratio); values are stored as filed.
  - A listing row marked 'Revised' does not prove a publication time: no revised filing
    has been checked on real data yet, so it fails closed (5B).
Nothing here is ever repaired; every skipped item is recorded with a reason.
"""
import re
import xml.etree.ElementTree as ET
from calendar import monthrange
from dataclasses import dataclass
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
IF_INDEX_SOURCE = "nse_integrated_filing_index"
IF_XBRL_SOURCE = "nse_integrated_filing_xbrl"
IST = timezone(timedelta(hours=5, minutes=30))
XBRLI = "{http://www.xbrl.org/2003/instance}"
XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"
TAXONOMY_PREFIX = "http://www.bseindia.com/xbrl/fin/"
SEBI_ENTRY = re.compile(r"^http://www\.sebi\.gov\.in/xbrl/IntegratedFinance_([A-Za-z]+)/\d{4}-\d{2}-\d{2}/in-capmkt/in-capmkt-ent$")
SEBI_TAXONOMY = re.compile(r"^http://www\.sebi\.gov\.in/xbrl/\d{4}-\d{2}-\d{2}/in-capmkt$")
NSE_ARCHIVE = "https://nsearchives.nseindia.com/"

INDEX_COLUMNS = ("COMPANY NAME", "AUDITED / UNAUDITED", "CUMULATIVE / NON-CUMULATIVE",
                 "CONSOLIDATED / NON-CONSOLIDATED", "PERIOD", "PERIOD ENDED", "** XBRL",
                 "Exchange Received Time", "Exchange Dissemination Time")
IF_INDEX_COLUMNS = ("SYMBOL", "COMPANY NAME", "QUARTER END DATE", "TYPE OF SUBMISSION", "AUDITED / UNAUDITED",
                    "CONSOLIDATED / STANDALONE", "XBRL", "BROADCAST DATE/TIME", "REVISED DATE/TIME",
                    "REVISION REMARKS", "EXCHANGE DISSEMINATION TIME")
INDEX_TIME_FORMAT = "%d-%b-%Y %H:%M:%S"   # e.g. 30-Jul-2026 17:18:42, India time
LISTING_BASIS = {"Consolidated": "consolidated", "Non-Consolidated": "standalone"}
IF_LISTING_BASIS = {"Consolidated": "consolidated", "Standalone": "standalone"}
SUBMISSION_TYPES = {"Original", "Revised"}
FILE_BASIS = {"consolidated": "consolidated", "standalone": "standalone"}
UNIT_MEASURES = {"INR": "iso4217:INR", "INR_per_share": "iso4217:INR/xbrli:shares", "ratio": "xbrli:pure"}
DURATIONS = {3: "3m", 12: "12m"}
MUST_BE_POSITIVE = {"paid_up_equity_capital", "face_value_per_share", "cet1_ratio"}

# XBRL element -> (our field, unit), one map per format family.
INDAS_FIELDS = {
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
BANK_FIELDS = {
    "InterestOrDiscountOnAdvancesOrBills": ("interest_on_advances", "INR"),
    "RevenueOnInvestments": ("income_on_investments", "INR"),
    "InterestOnBalancesWithReserveBankOfIndiaAndOtherInterBankFunds": ("interest_on_rbi_and_interbank_balances", "INR"),
    "OtherInterest": ("other_interest", "INR"),
    "InterestEarned": ("interest_earned", "INR"),
    "OtherIncome": ("other_income", "INR"),
    "Income": ("total_income", "INR"),
    "InterestExpended": ("interest_expended", "INR"),
    "EmployeesCost": ("employee_cost", "INR"),
    "OtherOperatingExpenses": ("other_operating_expenses", "INR"),
    "OperatingExpenses": ("operating_expenses", "INR"),
    "ExpenditureExcludingProvisionsAndContingencies": ("expenditure_excluding_provisions", "INR"),
    "OperatingProfitBeforeProvisionAndContingencies": ("operating_profit_before_provisions", "INR"),
    "ProvisionsOtherThanTaxAndContingencies": ("provisions_and_contingencies", "INR"),
    "ExceptionalItems": ("exceptional_items_deducted", "INR"),
    "ProfitLossFromOrdinaryActivitiesBeforeTax": ("profit_before_tax", "INR"),
    "TaxExpense": ("tax_expense", "INR"),
    "ProfitLossFromOrdinaryActivitiesAfterTax": ("profit_after_tax_ordinary", "INR"),
    "ExtraordinaryItems": ("extraordinary_items_deducted", "INR"),
    "ProfitLossForThePeriod": ("profit_before_minority_and_associates", "INR"),
    "ShareOfProfitLossOfAssociates": ("share_of_associates", "INR"),
    "ProfitLossOfMinorityInterest": ("net_profit_minority", "INR"),
    "ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates": ("net_profit_owners", "INR"),
    "PaidUpValueOfEquityShareCapital": ("paid_up_equity_capital", "INR"),
    "FaceValueOfEquityShareCapital": ("face_value_per_share", "INR_per_share"),
    "BasicEarningsPerShareAfterExtraordinaryItems": ("eps_basic", "INR_per_share"),
    "DilutedEarningsPerShareAfterExtraordinaryItems": ("eps_diluted", "INR_per_share"),
    "GrossNonPerformingAssets": ("gross_npa", "INR"),
    "NonPerformingAssets": ("net_npa", "INR"),
    "PercentageOfGrossNpa": ("gross_npa_ratio", "ratio"),
    "PercentageOfNpa": ("net_npa_ratio", "ratio"),
    "CET1Ratio": ("cet1_ratio", "ratio"),
    "ReturnOnAssets": ("return_on_assets", "ratio"),
}
BANK_STANDALONE_ONLY = frozenset({"gross_npa", "net_npa", "gross_npa_ratio", "net_npa_ratio", "cet1_ratio",
                                  "return_on_assets"})

# (name, total field, [(component field, sign)]) - checked only when every field is present.
INDAS_IDENTITIES = [
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
BANK_IDENTITIES = [
    ("interest earned = advances + investments + RBI/inter-bank + other interest", "interest_earned",
     [("interest_on_advances", 1), ("income_on_investments", 1), ("interest_on_rbi_and_interbank_balances", 1),
      ("other_interest", 1)]),
    ("income = interest earned + other income", "total_income", [("interest_earned", 1), ("other_income", 1)]),
    ("operating expenses = employee cost + other operating expenses", "operating_expenses",
     [("employee_cost", 1), ("other_operating_expenses", 1)]),
    ("expenditure = interest expended + operating expenses", "expenditure_excluding_provisions",
     [("interest_expended", 1), ("operating_expenses", 1)]),
    ("operating profit = income - expenditure", "operating_profit_before_provisions",
     [("total_income", 1), ("expenditure_excluding_provisions", -1)]),
    ("PBT = operating profit - provisions - exceptional items", "profit_before_tax",
     [("operating_profit_before_provisions", 1), ("provisions_and_contingencies", -1),
      ("exceptional_items_deducted", -1)]),
    ("ordinary profit = PBT - tax", "profit_after_tax_ordinary", [("profit_before_tax", 1), ("tax_expense", -1)]),
    ("profit = ordinary profit - extraordinary items", "profit_before_minority_and_associates",
     [("profit_after_tax_ordinary", 1), ("extraordinary_items_deducted", -1)]),
    ("owners' profit = profit - minority + associates", "net_profit_owners",
     [("profit_before_minority_and_associates", 1), ("net_profit_minority", -1), ("share_of_associates", 1)]),
]


@dataclass(frozen=True)
class ResultsFormat:
    name: str
    source_id: str
    parser_version: str
    name_element: str
    fields: dict
    identities: list
    standalone_only: frozenset = frozenset()


OLD_INDAS = ResultsFormat("old Ind AS", XBRL_SOURCE, "nse-results-xbrl-2", "NameOfTheCompany",
                          INDAS_FIELDS, INDAS_IDENTITIES)
SEBI_FORMATS = {
    "IndAS": ResultsFormat("SEBI Ind AS", IF_XBRL_SOURCE, "sebi-if-indas-1", "NameOfTheCompany",
                           INDAS_FIELDS, INDAS_IDENTITIES),
    "Banking": ResultsFormat("SEBI Banking", IF_XBRL_SOURCE, "sebi-if-banking-1", "NameOfBank",
                             BANK_FIELDS, BANK_IDENTITIES, BANK_STANDALONE_ONLY),
}


class ResultsFileError(AdapterError):
    """The file cannot be used as a whole. Nothing is stored."""


# ---- the listings ---------------------------------------------------------

def _ist(text):
    return datetime.strptime(text.strip(), INDEX_TIME_FORMAT).replace(tzinfo=IST)


def _archive_link(url):
    if not (url.startswith(NSE_ARCHIVE) and url.lower().endswith(".xml")):
        raise ValueError(f"XBRL link is not an NSE archive .xml: {url!r}")
    return url.rsplit("/", 1)[1]


def _old_listing_row(row, retrieved):
    url = (row.get("** XBRL") or "").strip()
    file_name = _archive_link(url)
    received, disseminated = _ist(row["Exchange Received Time"]), _ist(row["Exchange Dissemination Time"])
    if disseminated < received or disseminated > retrieved:
        raise ValueError("dissemination time is before receipt or after this file was obtained")
    period_ended = datetime.strptime(row["PERIOD ENDED"].strip(), "%d-%b-%Y").date().isoformat()
    if row["CONSOLIDATED / NON-CONSOLIDATED"].strip() not in LISTING_BASIS:
        raise ValueError(f"unknown basis {row['CONSOLIDATED / NON-CONSOLIDATED']!r}")
    return [file_name, row["COMPANY NAME"].strip(), row["AUDITED / UNAUDITED"].strip(),
            row["CUMULATIVE / NON-CUMULATIVE"].strip(), row["CONSOLIDATED / NON-CONSOLIDATED"].strip(),
            row["PERIOD"].strip(), period_ended, url, received.isoformat(), disseminated.isoformat()]


def _if_listing_row(row, retrieved):
    url = (row.get("XBRL") or "").strip()
    file_name = _archive_link(url)
    symbol = row["SYMBOL"].strip()
    if not symbol:
        raise ValueError("no symbol")
    received, disseminated = _ist(row["BROADCAST DATE/TIME"]), _ist(row["EXCHANGE DISSEMINATION TIME"])
    if disseminated < received or disseminated > retrieved:
        raise ValueError("dissemination time is before receipt or after this file was obtained")
    quarter_end = datetime.strptime(row["QUARTER END DATE"].strip(), "%d-%b-%Y").date().isoformat()
    basis, submission = row["CONSOLIDATED / STANDALONE"].strip(), row["TYPE OF SUBMISSION"].strip()
    if basis not in IF_LISTING_BASIS:
        raise ValueError(f"unknown basis {basis!r}")
    if submission not in SUBMISSION_TYPES:
        raise ValueError(f"unknown type of submission {submission!r}")
    revised_text = row["REVISED DATE/TIME"].strip()
    revised = _ist(revised_text) if revised_text else None
    if submission == "Revised" and revised is None:
        raise ValueError("a revised filing must carry its revision time")
    if revised is not None and (revised < received or revised > retrieved):
        raise ValueError("revision time is before receipt or after this file was obtained")
    return [file_name, symbol, row["COMPANY NAME"].strip(), quarter_end, submission,
            row["AUDITED / UNAUDITED"].strip(), basis, url, received.isoformat(), disseminated.isoformat(),
            revised.isoformat() if revised else None, row["REVISION REMARKS"].strip() or None]


LISTINGS = {
    "old": (INDEX_SOURCE, INDEX_COLUMNS, "fr_filings", _old_listing_row,
            ("xbrl_file_name", "company_name", "audited", "cumulative", "consolidated", "period", "period_ended",
             "xbrl_url", "received_at", "disseminated_at")),
    "integrated": (IF_INDEX_SOURCE, IF_INDEX_COLUMNS, "if_filings", _if_listing_row,
                   ("xbrl_file_name", "symbol", "company_name", "quarter_end", "submission_type", "audited",
                    "consolidated", "xbrl_url", "received_at", "disseminated_at", "revised_at", "revision_remarks")),
}


def load_results_index(conn, path, retrieved_at, raw_dir=None):
    """Load one NSE results listing (old page or integrated filing). Returns a report dict."""
    header, rows = read_raw_table(path)
    kind = next((k for k, spec in LISTINGS.items() if all(c in header for c in spec[1])), None)
    if kind is None:
        missing = [c for c in INDEX_COLUMNS if c not in header]
        raise ResultsFileError(f"Not an NSE results listing: missing columns {missing}")
    source_id, _, table, parse_row, columns = LISTINGS[kind]
    get_source(conn, source_id)
    if not rows:
        raise NoDataError("The results listing has no rows - nothing is stored")
    retrieved = parse_timestamp(retrieved_at)

    def work(c):
        artifact_id, _ = store_raw_artifact(c, source_id, path, retrieved_at, raw_dir=raw_dir)
        counts, problems = {"recorded": 0, "already_present": 0}, []
        for row_number, row in rows:
            try:
                values = parse_row(row, retrieved)
            except (ValueError, KeyError) as e:
                problems.append(("listing_row_rejected", f"row {row_number}: {e}"))
                continue
            existing = c.execute(f"SELECT {', '.join(columns[1:])} FROM {table} WHERE xbrl_file_name = ?",
                                 [values[0]]).fetchone()
            if existing:
                if list(existing) == values[1:]:
                    counts["already_present"] += 1
                else:
                    problems.append(("listing_conflict", f"row {row_number}: {values[0]} already listed differently"))
                continue
            c.execute(f"INSERT INTO {table} ({', '.join(columns)}, artifact_id, recorded_at)"
                      f" VALUES ({', '.join('?' * (len(columns) + 2))})", values + [artifact_id, now_utc()])
            counts["recorded"] += 1
        c.executemany("INSERT INTO fr_problems VALUES (NULL, ?, ?)", problems)
        return {"listing": kind, "rows_in_file": len(rows), "filings_recorded": counts["recorded"],
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
    """Read an XBRL results file into plain data: (format, contexts, facts in that format's taxonomy).
    Raises ResultsFileError for files that are not a supported results format."""
    name = Path(path).name
    try:
        declared = {uri for _, (_, uri) in ET.iterparse(path, events=("start-ns",))}
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        raise ResultsFileError(f"{name}: not valid XML ({e})") from None
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
    families = {m.group(1) for m in map(SEBI_ENTRY.match, declared) if m}
    if families:
        if len(families) != 1:
            raise ResultsFileError(f"{name}: declares more than one SEBI filing family {sorted(families)}")
        family = families.pop()
        fmt = SEBI_FORMATS.get(family)
        if fmt is None:
            raise ResultsFileError(f"{name}: SEBI integrated filing for '{family}' companies is not supported yet "
                                   f"(supported: {', '.join(sorted(SEBI_FORMATS))})")
        facts = [f for f in facts if SEBI_TAXONOMY.match(f["namespace"])]
    elif any(f["namespace"].startswith(TAXONOMY_PREFIX) and f["name"] == "RevenueFromOperations" for f in facts):
        fmt = OLD_INDAS
        facts = [f for f in facts if f["namespace"].startswith(TAXONOMY_PREFIX)]
    else:
        raise ResultsFileError(f"{name}: not the non-financial Ind AS results format or a supported SEBI integrated "
                               "filing (old-format banks, insurers and NBFCs are not supported)")
    if not facts:
        raise ResultsFileError(f"{name}: no facts in the {fmt.name} taxonomy")
    return fmt, contexts, facts


def _one_value(facts, name):
    values = {f["text"] for f in facts if f["name"] == name and f["text"]}
    if len(values) != 1:
        raise ResultsFileError(f"'{name}' must appear with exactly one value, found {sorted(values)}")
    return values.pop()


def _tolerance(decimals):
    return Decimal(0) if decimals in (None, "INF") else Decimal(10) ** (-int(decimals))


def _listing_row(conn, fmt, file_name):
    """The listing row for this XBRL file as (filing_id, symbol, company, basis, period end,
    disseminated_at, listing artifact, submission type, revised_at), or None."""
    if fmt is OLD_INDAS:
        sql = ("SELECT filing_id, NULL, company_name, consolidated, period_ended, disseminated_at, artifact_id,"
               " 'Original', NULL FROM fr_filings WHERE xbrl_file_name = ?")
    else:
        sql = ("SELECT filing_id, symbol, company_name, consolidated, quarter_end, disseminated_at, artifact_id,"
               " submission_type, revised_at FROM if_filings WHERE xbrl_file_name = ?")
    return conn.execute(sql, [file_name]).fetchone()


def load_results_xbrl(conn, path, retrieved_at, raw_dir=None):
    """Load one NSE results XBRL file (old or SEBI format) into the point-in-time store. Returns a report dict."""
    fmt, contexts, facts = parse_results_xbrl(path)
    get_source(conn, fmt.source_id)
    symbol = _one_value(facts, "Symbol")
    company = _one_value(facts, fmt.name_element)
    if _one_value(facts, "DescriptionOfPresentationCurrency") != "INR":
        raise ResultsFileError("Only results presented in INR are read")
    basis = FILE_BASIS.get(_one_value(facts, "NatureOfReportStandaloneConsolidated").lower())
    if basis is None:
        raise ResultsFileError("NatureOfReportStandaloneConsolidated is neither Consolidated nor Standalone")
    audited = _one_value(facts, "WhetherResultsAreAuditedOrUnaudited")
    file_isin = None if fmt is OLD_INDAS else _one_value(facts, "ISIN")
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

    # Identity: by NSE symbol as of the period end; the name (and ISIN, when filed) must match.
    period_end = min(end for end, _ in periods.values())
    try:
        strict_iso_date(period_end)
        isin = resolve(conn, symbol, period_end, alias_type="nse_symbol")
    except (ValueError, EntityError) as e:
        raise ResultsFileError(f"{symbol}: not attached to a company as of {period_end}: {e}") from None
    if file_isin is not None and file_isin != isin:
        raise ResultsFileError(f"{symbol}: the file's ISIN {file_isin} is not {isin}, the company this symbol "
                               f"named on {period_end}")
    legal_name = conn.execute("SELECT legal_name FROM entities WHERE isin = ?", [isin]).fetchone()[0]
    if normalise_name(legal_name) != normalise_name(company):
        raise ResultsFileError(f"{symbol}: file names {company!r} but the registry has {legal_name!r}")

    # Listing: cross-check and take the proven publication time.
    filing = _listing_row(conn, fmt, Path(path).name)
    published_at = evidence = filing_id = None
    if filing:
        filing_id, listed_symbol, listed_name, listed_basis, listed_end, disseminated_at, listing_artifact, \
            submission, revised_at = filing
        if {**LISTING_BASIS, **IF_LISTING_BASIS}[listed_basis] != basis:
            raise ResultsFileError(f"The listing says {listed_basis} but the file says {basis}")
        if listed_end not in {end for end, _ in periods.values()}:
            raise ResultsFileError(f"The listing says period ended {listed_end}; the file's periods disagree")
        if listed_symbol is not None and listed_symbol != symbol:
            raise ResultsFileError(f"The listing names symbol {listed_symbol}; the file says {symbol}")
        if normalise_name(listed_name) != normalise_name(company):
            raise ResultsFileError(f"The listing names {listed_name!r}; the file names {company!r}")
        if parse_timestamp(disseminated_at) > parse_timestamp(retrieved_at):
            raise ResultsFileError("The listing's dissemination time is after this file was obtained")
        if submission == "Revised":
            problems.append(("publication_not_proven", f"the listing marks this filing Revised (revised {revised_at});"
                             " publication times of revised filings are not proven yet (5B)"))
        else:
            published_at = disseminated_at
            evidence = (f"NSE results listing (artifact {listing_artifact}): exchange dissemination time "
                        f"{disseminated_at}")
    else:
        problems.append(("no_listing", "file not in a loaded results listing: publication time not proven (5B)"))

    # Figures per usable period, with unit and plausibility checks.
    values = {}
    for ctx_id in periods:
        found, standalone_only = {}, []
        for f in facts:
            if f["context"] != ctx_id or f["name"] not in fmt.fields:
                continue
            field, unit = fmt.fields[f["name"]]
            amount = _decimal(f["text"])
            if f["nil"] or amount is None:
                problems.append(("empty_value", f"{ctx_id} {f['name']}: no value in the file - not stored"))
            elif f["unit"] != UNIT_MEASURES[unit]:
                problems.append(("unit_mismatch", f"{ctx_id} {f['name']}: unit {f['unit']}, expected {UNIT_MEASURES[unit]}"))
            elif field in fmt.standalone_only and basis != "standalone":
                standalone_only.append(f"{field}={f['text']}")
            elif field in MUST_BE_POSITIVE and amount <= 0:
                problems.append(("implausible_value", f"{ctx_id} {f['name']} = {f['text']}: cannot be zero or "
                                                      "negative - a placeholder, not stored"))
            elif field in found:
                problems.append(("duplicate", f"{ctx_id} {f['name']}: appears more than once - not stored"))
                found[field] = None
            else:
                found[field] = (amount, unit, f["decimals"])
        if standalone_only:
            problems.append(("standalone_only", f"{ctx_id}: bank ratios are taken from the standalone report only - "
                                                f"not stored from this {basis} report: {', '.join(standalone_only)}"))
        values[ctx_id] = {k: v for k, v in found.items() if v is not None}

    # Accounting identities.
    conflicted = {}
    for ctx_id, found in values.items():
        failing, passing = set(), set()
        for name, total, parts in fmt.identities:
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
        artifact_id, _ = store_raw_artifact(c, fmt.source_id, path, retrieved_at, published_at, evidence, raw_dir)
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
            [artifact_id, fmt.parser_version, isin, symbol, basis, audited, filing_id if fmt is OLD_INDAS else None,
             counts["recorded"], counts["already_present"], counts["marked_conflict"], len(problems),
             now_utc()]).lastrowid
        if filing_id is not None and fmt is not OLD_INDAS:
            c.execute("INSERT INTO if_load_filings VALUES (?, ?)", [load_id, filing_id])
        c.executemany("INSERT INTO fr_problems VALUES (?, ?, ?)", [(load_id, k, d) for k, d in problems])
        return {"load_id": load_id, "format": fmt.name, "symbol": symbol, "isin": isin, "basis": basis,
                "periods": sorted(f"{end} ({d})" for end, d in periods.values()),
                "publication_proven": published_at is not None, "facts_recorded": counts["recorded"],
                "already_present": counts["already_present"], "marked_source_conflict": counts["marked_conflict"],
                "problems": [f"{k}: {d}" for k, d in problems]}

    return run_in_transaction(conn, work)
