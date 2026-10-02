"""Stage 8 tests: the fundamental data adapter (architecture 40B step 7, 4, 4C, 5B).

40B step 7 acceptance: consolidated and standalone never mix; basis is explicit on every fact.
Also, from NSE's real files: contexts whose dates disagree with the file's own period
fields are rejected; figures failing an accounting identity that nothing confirms are
stored as source_conflict; the listing's dissemination time is the proven publication time.
"""
import sqlite3

import pytest

from core.database import connect, migrate, rollback
from ingestion.nse_financial_results import ResultsFileError, load_results_index, load_results_xbrl
from ingestion.source_registry import sync_sources
from provenance.availability import Availability, PitClaim
from provenance.pit_store import fact_as_of
from provenance.raw_store import ArtifactError
from universe.entities import add_alias, add_entity

ISIN = "INE467B01029"
RETRIEVED = "2026-10-02T16:30:00+05:30"
FIN = "http://www.bseindia.com/xbrl/fin/2020-03-31/in-bse-fin"
CR = 10_000_000  # one crore

QUARTER = {  # a consistent quarter, in crore
    "RevenueFromOperations": 1000, "OtherIncome": 50, "Income": 1050, "Expenses": 850,
    "ProfitBeforeExceptionalItemsAndTax": 200, "ExceptionalItemsBeforeTax": 0, "ProfitBeforeTax": 200,
    "TaxExpense": 50, "ProfitLossForPeriodFromContinuingOperations": 150,
    "ProfitLossFromDiscontinuedOperationsAfterTax": 0,
    "ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod": 0,
    "NetMovementInRegulatoryDeferralAccountBalancesRelatedToProfitOrLossAndTheRelatedDeferredTaxMovement": 0,
    "ProfitLossForPeriod": 150, "ProfitOrLossAttributableToOwnersOfParent": 140,
    "ProfitOrLossAttributableToNonControllingInterests": 10, "PaidUpValueOfEquityShareCapital": 100,
}
PER_SHARE = {"FaceValueOfEquityShareCapital": "10", "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations": "15.00",
             "DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations": "14.90"}


def xbrl(basis="Consolidated", symbol="TCS", name="Tata Consultancy Services Limited", currency="INR",
         taxonomy=FIN, quarter=None, contexts=None, extra=""):
    """A results file shaped like NSE's real ones, including the FourD context that claims the
    quarter while its period fields (and figures) are year-to-date."""
    contexts = contexts or {"OneD": (("2024-10-01", "2024-12-31"), ("2024-10-01", "2024-12-31")),
                            "FourD": (("2024-10-01", "2024-12-31"), ("2024-04-01", "2024-12-31"))}
    figures = dict(QUARTER, **(quarter or {}))
    out = [f'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:fin="{taxonomy}" '
           'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:iso4217="http://www.xbrl.org/2003/iso4217">']
    for cid, ((start, end), _) in contexts.items():
        out.append(f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier scheme="x">{symbol}</xbrli:identifier>'
                   f'</xbrli:entity><xbrli:period><xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{end}'
                   '</xbrli:endDate></xbrli:period></xbrli:context>')
    out.append('<xbrli:unit id="INR"><xbrli:measure>iso4217:INR</xbrli:measure></xbrli:unit>'
               '<xbrli:unit id="shares"><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unit>'
               '<xbrli:unit id="INRPerShare"><xbrli:divide><xbrli:unitNumerator><xbrli:measure>iso4217:INR</xbrli:measure>'
               '</xbrli:unitNumerator><xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure>'
               '</xbrli:unitDenominator></xbrli:divide></xbrli:unit>')
    out.append(f'<fin:Symbol contextRef="OneD">{symbol}</fin:Symbol><fin:NameOfTheCompany contextRef="OneD">{name}'
               f'</fin:NameOfTheCompany><fin:DescriptionOfPresentationCurrency contextRef="OneD">{currency}'
               '</fin:DescriptionOfPresentationCurrency>')
    for cid, (_, (start, end)) in contexts.items():
        scale = 1 if cid == "OneD" else 3
        out.append(f'<fin:DateOfStartOfReportingPeriod contextRef="{cid}">{start}</fin:DateOfStartOfReportingPeriod>'
                   f'<fin:DateOfEndOfReportingPeriod contextRef="{cid}">{end}</fin:DateOfEndOfReportingPeriod>'
                   f'<fin:WhetherResultsAreAuditedOrUnaudited contextRef="{cid}">Unaudited</fin:WhetherResultsAreAuditedOrUnaudited>'
                   f'<fin:NatureOfReportStandaloneConsolidated contextRef="{cid}">{basis}</fin:NatureOfReportStandaloneConsolidated>')
        for tag, crore in figures.items():
            if basis == "Standalone" and "Attributable" in tag:
                continue
            out.append(f'<fin:{tag} contextRef="{cid}" unitRef="INR" decimals="-7">{crore * scale * CR:.2f}</fin:{tag}>')
        for tag, value in PER_SHARE.items():
            out.append(f'<fin:{tag} contextRef="{cid}" unitRef="INRPerShare" decimals="INF">{value}</fin:{tag}>')
    out.append(extra + "</xbrli:xbrl>")
    return "".join(out)


def listing(rows):
    head = ('"COMPANY NAME","AUDITED / UNAUDITED","CUMULATIVE / NON-CUMULATIVE","CONSOLIDATED / NON-CONSOLIDATED",'
            '"IND AS/ NON IND AS","PERIOD","PERIOD ENDED","RELATING TO","** XBRL","Exchange Received Time",'
            '"Exchange Dissemination Time","Time Taken"')
    lines = [head]
    for file_name, basis, ended, disseminated in rows:
        lines.append(f'"Tata Consultancy Services Limited","Un-Audited","Non-cumulative","{basis}","Ind-AS New",'
                     f'"Quarterly","{ended}","Third Quarter","https://nsearchives.nseindia.com/corporate/xbrl/{file_name}",'
                     f'"{disseminated}","{disseminated}","00:00:10"')
    return "\ufeff" + "\n".join(lines) + "\n"


@pytest.fixture
def env(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    add_entity(c, ISIN, "Tata Consultancy Services Limited")
    add_alias(c, ISIN, "nse_symbol", "TCS", "2004-08-25")

    def put(name, text):
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        return path

    def load(name, text):
        return load_results_xbrl(c, put(name, text), RETRIEVED, raw_dir=tmp_path / "raw")

    def load_listing(name, text):
        return load_results_index(c, put(name, text), RETRIEVED, raw_dir=tmp_path / "raw")

    yield c, load, load_listing
    c.close()


def value(c, field, basis, end="2024-12-31", when=RETRIEVED, claim=PitClaim.CURRENT_DECISION):
    return fact_as_of(c, ISIN, field, basis, end, when, claim)


def count(c, table):
    return c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# ---- 40B step 7 acceptance ----

def test_consolidated_and_standalone_never_mix(env):
    c, load, _ = env
    load("INDAS_1_cons.xml", xbrl("Consolidated"))
    load("INDAS_2_std.xml", xbrl("Standalone", quarter={"RevenueFromOperations": 800, "Income": 850, "Expenses": 650}))
    assert value(c, "revenue_from_operations_3m", "consolidated").value == 1000 * CR
    assert value(c, "revenue_from_operations_3m", "standalone").value == 800 * CR
    bases = {r[0] for r in c.execute("SELECT DISTINCT basis FROM pit_facts")}
    assert bases == {"consolidated", "standalone"}
    assert c.execute("SELECT COUNT(*) FROM pit_facts WHERE basis IS NULL OR basis = ''").fetchone()[0] == 0
    # Owners/minority exist only for the consolidated report.
    assert value(c, "net_profit_owners_3m", "standalone").availability == Availability.NOT_ELIGIBLE


# ---- periods: the FourD trap ----

def test_a_context_whose_dates_disagree_is_rejected_not_guessed(env):
    c, load, _ = env
    report = load("INDAS_1.xml", xbrl())
    assert report["periods"] == ["2024-12-31 (3m)"]
    assert any(p.startswith("context_rejected: FourD") for p in report["problems"])
    # The year-to-date figures (3x) never reached the store under the quarter's key.
    assert value(c, "revenue_from_operations_3m", "consolidated").value == 1000 * CR


def test_a_consistent_twelve_month_period_is_stored_separately(env):
    c, load, _ = env
    contexts = {"OneD": (("2025-01-01", "2025-03-31"), ("2025-01-01", "2025-03-31")),
                "FourD": (("2024-04-01", "2025-03-31"), ("2024-04-01", "2025-03-31"))}
    report = load("INDAS_1.xml", xbrl(contexts=contexts))
    assert report["periods"] == ["2025-03-31 (12m)", "2025-03-31 (3m)"]
    assert value(c, "revenue_from_operations_3m", "consolidated", "2025-03-31").value == 1000 * CR
    assert value(c, "revenue_from_operations_12m", "consolidated", "2025-03-31").value == 3000 * CR


def test_other_period_lengths_are_out_of_scope(env):
    c, load, _ = env
    contexts = {"OneD": (("2024-10-01", "2024-12-31"), ("2024-10-01", "2024-12-31")),
                "FourD": (("2024-04-01", "2024-12-31"), ("2024-04-01", "2024-12-31"))}
    report = load("INDAS_1.xml", xbrl(contexts=contexts))
    assert report["periods"] == ["2024-12-31 (3m)"]
    assert any("9-month period is not stored" in p for p in report["problems"])


# ---- accounting identities (4, 4C) ----

def test_placeholder_zeros_become_source_conflict_but_confirmed_profit_is_kept(env):
    c, load, _ = env
    report = load("INDAS_1.xml", xbrl(quarter={"ProfitOrLossAttributableToOwnersOfParent": 0,
                                               "ProfitOrLossAttributableToNonControllingInterests": 0}))
    assert report["marked_source_conflict"] == 2
    owners = value(c, "net_profit_owners_3m", "consolidated")
    assert (owners.value, owners.missing_class) == (None, "source_conflict")
    assert value(c, "net_profit_3m", "consolidated").value == 150 * CR   # confirmed by other identities


def test_a_figure_no_identity_confirms_is_not_trusted(env):
    c, load, _ = env
    load("INDAS_1.xml", xbrl(quarter={"OtherIncome": 70}))   # income no longer = revenue + other income
    assert value(c, "other_income_3m", "consolidated").missing_class == "source_conflict"
    assert value(c, "revenue_from_operations_3m", "consolidated").missing_class == "source_conflict"
    assert value(c, "total_income_3m", "consolidated").value == 1050 * CR  # confirmed: income - expenses


# ---- 5B: the listing gives the proven publication time ----

def test_listed_filing_is_replay_eligible_from_its_dissemination_time(env):
    c, load, load_listing = env
    load_listing("CF-FR.csv", listing([("INDAS_9.xml", "Consolidated", "31-Dec-2024", "15-Jan-2025 17:18:42")]))
    report = load("INDAS_9.xml", xbrl())
    assert report["publication_proven"]
    field = "net_profit_3m"
    assert value(c, field, "consolidated", when="2025-01-15T17:00:00+05:30",
                 claim=PitClaim.HISTORICAL_REPLAY).availability == Availability.NOT_ELIGIBLE
    assert value(c, field, "consolidated", when="2025-01-15T17:30:00+05:30",
                 claim=PitClaim.HISTORICAL_REPLAY).availability == Availability.ELIGIBLE


def test_unlisted_filing_is_never_replay_eligible(env):
    c, load, _ = env
    report = load("INDAS_9.xml", xbrl())
    assert not report["publication_proven"]
    assert value(c, "net_profit_3m", "consolidated", when="2026-01-01T00:00:00+05:30",
                 claim=PitClaim.HISTORICAL_REPLAY).availability == Availability.AVAILABILITY_REVIEW


@pytest.mark.parametrize("row, message", [
    (("INDAS_9.xml", "Non-Consolidated", "31-Dec-2024", "15-Jan-2025 17:18:42"), "listing says"),
    (("INDAS_9.xml", "Consolidated", "30-Sep-2024", "15-Jan-2025 17:18:42"), "period ended"),
])
def test_a_file_that_disagrees_with_its_listing_is_refused(env, row, message):
    c, load, load_listing = env
    load_listing("CF-FR.csv", listing([row]))
    with pytest.raises(ResultsFileError, match=message):
        load("INDAS_9.xml", xbrl())
    assert count(c, "pit_facts") == 0 and count(c, "fr_loads") == 0


def test_listing_rows_that_cannot_be_trusted_are_rejected_and_recorded(env):
    c, _, load_listing = env
    report = load_listing("CF-FR.csv", listing([
        ("INDAS_1.xml", "Consolidated", "31-Dec-2024", "15-Jan-2025 17:18:42"),
        ("INDAS_2.xml", "Consolidated", "31-Dec-2024", "15-Jan-2099 17:18:42"),   # after we obtained the file
        ("INDAS_3.xml", "Partly", "31-Dec-2024", "15-Jan-2025 17:18:42"),         # unknown basis
    ]))
    assert report["filings_recorded"] == 1 and len(report["problems"]) == 2
    again = load_listing("CF-FR-2.csv", listing([("INDAS_1.xml", "Consolidated", "31-Dec-2024", "15-Jan-2025 17:18:42")]))
    assert (again["filings_recorded"], again["already_present"]) == (0, 1)


# ---- whole-file refusals: nothing stored ----

@pytest.mark.parametrize("kwargs, message", [
    ({"symbol": "NOSUCH"}, "not attached"),
    ({"name": "Someone Else Limited"}, "registry has"),
    ({"currency": "USD"}, "INR"),
    ({"taxonomy": "http://www.bseindia.com/xbrl/banking/2020-03-31/in-bse-bank"}, "not the non-financial"),
    ({"basis": "Partly"}, "neither Consolidated nor Standalone"),
    ({"contexts": {"OneD": (("2024-10-01", "2024-12-31"), ("2024-07-01", "2024-12-31"))}}, "no period context"),
])
def test_unusable_files_are_refused_whole(env, kwargs, message):
    c, load, _ = env
    with pytest.raises(ResultsFileError, match=message):
        load("INDAS_1.xml", xbrl(**kwargs))
    assert count(c, "pit_facts") == 0 and count(c, "raw_artifacts") == 0


def test_wrong_units_and_empty_values_are_not_stored(env):
    c, load, _ = env
    extra = ('<fin:FinanceCosts contextRef="OneD" unitRef="shares" decimals="-7">5</fin:FinanceCosts>'
             '<fin:DepreciationDepletionAndAmortisationExpense contextRef="OneD" xsi:nil="true" unitRef="INR"/>')
    report = load("INDAS_1.xml", xbrl(extra=extra))
    assert any(p.startswith("unit_mismatch") for p in report["problems"])
    assert any(p.startswith("empty_value") for p in report["problems"])
    assert value(c, "finance_costs_3m", "consolidated").availability == Availability.NOT_ELIGIBLE


# ---- re-filings: never overwrite ----

def test_the_same_file_twice_is_refused(env):
    _, load, _ = env
    load("INDAS_1.xml", xbrl())
    with pytest.raises(ArtifactError):
        load("INDAS_1.xml", xbrl())


def test_a_refiling_with_the_same_figures_changes_nothing(env):
    c, load, _ = env
    load("INDAS_1.xml", xbrl())
    report = load("INDAS_2.xml", xbrl() + " ")
    assert report["facts_recorded"] == 0 and report["already_present"] == len(QUARTER) + len(PER_SHARE)


def test_a_refiling_with_different_figures_is_a_conflict_and_the_original_stays(env):
    c, load, _ = env
    load("INDAS_1.xml", xbrl())
    report = load("INDAS_2.xml", xbrl(quarter={"PaidUpValueOfEquityShareCapital": 101}))
    assert any(p.startswith("conflicts_with_recorded_fact") for p in report["problems"])
    assert value(c, "paid_up_equity_capital_3m", "consolidated").value == 100 * CR
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        c.execute("DELETE FROM fr_loads")


# ---- migration and acceptance record ----

def test_results_migration_rolls_back_cleanly():
    c = connect(":memory:")
    migrate(c)
    rollback(c, 10)
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
    assert not {"fr_filings", "fr_loads", "fr_problems"} & names and "identity_bridges" in names
    c.close()


def test_stage_8_acceptance_record_is_valid():
    from core.status import load_acceptance_records
    record = load_acceptance_records()["STAGE_08_acceptance.yaml"]
    assert record["status"] == "ACCEPTED_FUNDAMENTALS_BASELINE"
    assert record["negative_assertions"]["consolidated and standalone figures mixed"] is False
