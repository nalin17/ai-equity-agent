"""Stage 8D tests: NBFCs, life insurers and revised filings (architecture 40B step 7, 4, 4C, 5, 5B, 9B).

From NSE's real files: NBFC results add lending lines (interest, fees, impairment) to the
Ind AS layout; life insurers file a policyholders' and a shareholders' account with
solvency and persistency ratios; a year can be audited while its quarter is not; and a
revised filing is listed as 'Revision' with no broadcast time, a revision time and a remark.
"""
import pytest

from core.database import connect, migrate, rollback
from ingestion.nse_financial_results import load_results_index, load_results_xbrl
from ingestion.source_registry import sync_sources
from provenance.availability import Availability, PitClaim
from provenance.pit_store import fact_as_of
from universe.entities import add_alias, add_entity

NBFC_ISIN, LI_ISIN = "INE296A01032", "INE795G01014"
CR = 10_000_000  # one crore
ORIGINAL_SEEN, REVISION_SEEN = "2026-07-20T10:00:00+05:30", "2026-07-25T10:00:00+05:30"
QUARTER = {"OneD": ("2026-04-01", "2026-06-30")}

NBFC = {  # a consistent NBFC quarter, in crore
    "InterestEarned": 800, "DividendIncome": 0, "RentalIncome": 0, "FeesAndCommissionIncome": 100,
    "NetGainOnFairValueChanges": 10, "NetGainOnDerecognitionOfFinancialInstrumentsUnderAmortisedCostCategory": 0,
    "RevenueFromSaleOfProduct": 0, "RevenueFromSaleOfServices": 5, "OtherRevenueFromOperations": 85,
    "RevenueFromOperations": 1000, "OtherIncome": 2, "Income": 1002, "CostOfMaterialsConsumed": 0,
    "PurchasesOfStockInTrade": 0, "ChangesInInventoriesOfFinishedGoodsWorkInProgressAndStockInTrade": 0,
    "EmployeeBenefitExpense": 120, "FinanceCosts": 350, "DepreciationDepletionAndAmortisationExpense": 30,
    "FeesAndCommissionExpense": 50, "NetLossOnFairValueChanges": 0,
    "NetLossOnDerecognitionOfFinancialInstrumentsUnderAmortisedCostCategory": 0,
    "ImpairmentOnFinancialInstruments": 90, "OtherExpenses": 60, "Expenses": 700,
    "ProfitBeforeExceptionalItemsAndTax": 302, "ExceptionalItemsBeforeTax": 0, "ProfitBeforeTax": 302,
    "TaxExpense": 77, "ProfitLossForPeriodFromContinuingOperations": 225, "ProfitLossFromDiscontinuedOperationsAfterTax": 0,
    "ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod": 5, "ProfitLossForPeriod": 230,
    "ProfitOrLossAttributableToOwnersOfParent": 220, "ProfitOrLossAttributableToNonControllingInterests": 10,
    "PaidUpValueOfEquityShareCapital": 62,
}
NBFC_PER_SHARE = {"FaceValueOfEquityShareCapital": "1",
                  "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations": "3.55",
                  "DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations": "3.54"}
LI = {  # a consistent life-insurer quarter, in crore
    "IncomeFirstYearPremium": 2700, "IncomeRenewalPremium": 9000, "IncomeSinglePremium": 5400,
    "GrossPremiumIncome": 17100, "NetPremiumIncome": 16500, "IncomeFromInvestmentsNet": 16600,
    "PolicyholdersAccountOtherIncome": 90, "TransferOfFundsFromShareholdersAccount": 20, "Income": 33210,
    "CommissionFirstYearPremium": 950, "CommissionRenewalPremium": 170, "CommissionSinglePremium": 980,
    "Commission": 2100, "NetCommission": 2100, "EmployeesRemunerationAndWelfareExpenses": 900,
    "AdministrationExpenses": 0, "AdvertisementAndPublicity": 0, "OtherOperatingExpenses": 850,
    "OperatingExpensesRelatedToInsuranceBusiness": 1750, "ExpensesOfManagement": 3850,
    "ProvisionsForDoubtfulDebtsIncludingBadDebtsWrittenOff": 0, "ProvisionsForDiminutionInValueOfInvestments": -40,
    "GoodsAndServiceTaxChargeOnLinkedCharges": 10, "ProvisionForTax": 50, "BenefitsPaidNet": 8100,
    "ChangeInActuarialLiability": 20930, "Expenses": 32900, "NetSurplusDeficit": 310,
    "TransferredToShareholdersAccount": 360, "FundsForFutureAppropriation": -50,
    "TransferFromPolicyholdersAccount": 360, "InvestmentIncome": 340, "ShareholdersAccountOtherIncome": 4,
    "IncomeUnderShareholdersAccount": 344, "ShareholdersAccountIncome": 704,
    "ExpensesOtherThanThoseRelatedToInsuranceBusiness": 74, "TransferOfFundsToPolicyholdersAccount": 20,
    "ProvisionsForDoubtfulDebtsIncludingWriteOff": 0, "ShareholdersAccountProvisionsForDiminutionInValueOfInvestments": -6,
    "ShareholdersAccountExpenses": 88, "ProfitLossBeforeTax": 616, "ProvisionsForTaxes": 15,
    "ProfitLossAfterTaxBeforeExtraordinaryItems": 601, "ExtraordinaryItemsNetOfTaxExpenses": 0,
    "ProfitLossAfterTaxAndExtraordinaryItems": 601,
}
LI_RATIOS = {"SolvencyRatio": "1.85", "ExpensesOfManagementRatio": "0.2255", "PersistencyRatio13ThMonth": "0.80",
             "PersistencyRatio25ThMonth": "0.73", "PersistencyRatio37ThMonth": "0.76", "PersistencyRatio49ThMonth": "0.67",
             "PersistencyRatio61ThMonth": "0.65", "ConservationRatio": "0.89"}
LI_PER_SHARE = {"BasicAndDilutedEPSAfterExtraordinaryItemsNetOfTaxExpenseForThePeriodNotToBeAnnualized": "2.79"}


def sebi_file(family, basis="Standalone", changes=None, contexts=None, audited=None):
    """A SEBI integrated filing for an NBFC (Bajaj Finance) or a life insurer (HDFC Life), shaped like NSE's."""
    contexts = contexts or QUARTER
    audited = audited or {}
    if family == "NBFC":
        symbol, isin, name = "BAJFINANCE", NBFC_ISIN, "BAJAJ FINANCE LIMITED"
        amounts, ratios, per_share = dict(NBFC), {}, dict(NBFC_PER_SHARE)
        if basis == "Standalone":
            for tag in ("ProfitOrLossAttributableToOwnersOfParent", "ProfitOrLossAttributableToNonControllingInterests"):
                del amounts[tag]
    else:
        symbol, isin, name = "HDFCLIFE", LI_ISIN, "HDFC Life Insurance Company Limited"
        amounts, ratios, per_share = dict(LI), dict(LI_RATIOS), dict(LI_PER_SHARE)
    for key, value in (changes or {}).items():
        (ratios if key in ratios else per_share if key in per_share else amounts)[key] = value
    tax = "http://www.sebi.gov.in/xbrl/2026-01-31/in-capmkt"
    ent = f"http://www.sebi.gov.in/xbrl/IntegratedFinance_{family}/2026-01-31/in-capmkt/in-capmkt-ent"
    out = [f'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:in-capmkt="{tax}" '
           f'xmlns:in-capmkt-ent="{ent}" xmlns:iso4217="http://www.xbrl.org/2003/iso4217">']
    for cid, (start, end) in contexts.items():
        out.append(f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier>'
                   f'</xbrli:entity><xbrli:period><xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{end}'
                   '</xbrli:endDate></xbrli:period></xbrli:context>')
    out.append('<xbrli:unit id="INR"><xbrli:measure>iso4217:INR</xbrli:measure></xbrli:unit>'
               '<xbrli:unit id="pure"><xbrli:measure>xbrli:pure</xbrli:measure></xbrli:unit>'
               '<xbrli:unit id="INRPerShare"><xbrli:divide><xbrli:unitNumerator><xbrli:measure>iso4217:INR'
               '</xbrli:measure></xbrli:unitNumerator><xbrli:unitDenominator><xbrli:measure>xbrli:shares'
               '</xbrli:measure></xbrli:unitDenominator></xbrli:divide></xbrli:unit>')
    out.append(f'<in-capmkt:Symbol contextRef="OneD">{symbol}</in-capmkt:Symbol>'
               f'<in-capmkt:ISIN contextRef="OneD">{isin}</in-capmkt:ISIN>'
               f'<in-capmkt:NameOfTheCompany contextRef="OneD">{name}</in-capmkt:NameOfTheCompany>'
               '<in-capmkt:DescriptionOfPresentationCurrency contextRef="OneD">INR</in-capmkt:DescriptionOfPresentationCurrency>')
    for cid, (start, end) in contexts.items():
        scale = 1 if cid == "OneD" else 4
        out.append(f'<in-capmkt:DateOfStartOfReportingPeriod contextRef="{cid}">{start}</in-capmkt:DateOfStartOfReportingPeriod>'
                   f'<in-capmkt:DateOfEndOfReportingPeriod contextRef="{cid}">{end}</in-capmkt:DateOfEndOfReportingPeriod>'
                   f'<in-capmkt:WhetherResultsAreAuditedOrUnaudited contextRef="{cid}">{audited.get(cid, "Unaudited")}'
                   '</in-capmkt:WhetherResultsAreAuditedOrUnaudited>'
                   f'<in-capmkt:NatureOfReportStandaloneConsolidated contextRef="{cid}">{basis}</in-capmkt:NatureOfReportStandaloneConsolidated>')
        for tag, crore in amounts.items():
            out.append(f'<in-capmkt:{tag} contextRef="{cid}" unitRef="INR" decimals="-5">{crore * scale * CR:.2f}</in-capmkt:{tag}>')
        for tag, value in ratios.items():
            out.append(f'<in-capmkt:{tag} contextRef="{cid}" unitRef="pure" decimals="INF">{value}</in-capmkt:{tag}>')
        for tag, value in per_share.items():
            out.append(f'<in-capmkt:{tag} contextRef="{cid}" unitRef="INRPerShare" decimals="INF">{value}</in-capmkt:{tag}>')
    out.append("</xbrli:xbrl>")
    return "".join(out)


def listing(rows):
    """NSE's integrated-filing listing exactly as written for HDFC Life's real revision: the
    revision row has a blank broadcast time, a revision time in capitals and a remark."""
    names = ["SYMBOL", "COMPANY NAME", "QUARTER END DATE", "TYPE OF SUBMISSION", "AUDITED / UNAUDITED",
             "CONSOLIDATED / STANDALONE", "DETAILS", "XBRL", "BROADCAST DATE/TIME", "REVISED DATE/TIME",
             "REVISION REMARKS", "EXCHANGE DISSEMINATION TIME", "TIME TAKEN"]
    lines = [",".join(f'"{n} \n"' for n in names)]
    for file_name, submission, broadcast, revised, remark, disseminated in rows:
        lines.append(f'"HDFCLIFE","HDFC Life Insurance Company Limited","30-JUN-2026","{submission}","Un-Audited",'
                     f'"Standalone","https://nsearchives.nseindia.com/corporate/ixbrl/x.html",'
                     f'"https://nsearchives.nseindia.com/corporate/xbrl/{file_name}","{broadcast}","{revised}",'
                     f'"{remark}","{disseminated}","00:00:37"')
    return chr(0xFEFF) + "\n".join(lines) + "\n"


ORIGINAL_ROW = ("INTEGRATED_FILING_LI_1.xml", "Original", "15-Jul-2026 17:51:12", "", "", "15-Jul-2026 17:51:20")
REVISION_ROW = ("INTEGRATED_FILING_LI_2.xml", "Revision", "", "24-JUL-2026 16:48:18",
                "Inadvertent error in mentioning certain numbers", "24-Jul-2026 16:48:55")


@pytest.fixture
def env(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    add_entity(c, NBFC_ISIN, "Bajaj Finance Limited")
    add_alias(c, NBFC_ISIN, "nse_symbol", "BAJFINANCE", "2003-04-01")
    add_entity(c, LI_ISIN, "HDFC Life Insurance Company Limited")
    add_alias(c, LI_ISIN, "nse_symbol", "HDFCLIFE", "2017-11-17")

    def put(name, text):
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        return path

    def load(name, text, retrieved=REVISION_SEEN):
        return load_results_xbrl(c, put(name, text), retrieved, raw_dir=tmp_path / "raw")

    def load_listing(text):
        return load_results_index(c, put("CF-Integrated.csv", text), REVISION_SEEN, raw_dir=tmp_path / "raw")

    yield c, load, load_listing
    c.close()


def value(c, isin, field, basis="standalone", end="2026-06-30", when=REVISION_SEEN, claim=PitClaim.CURRENT_DECISION):
    return fact_as_of(c, isin, field, basis, end, when, claim)


# ---- NBFCs ----

def test_nbfc_results_are_read_with_their_lending_lines(env):
    c, load, _ = env
    report = load("INTEGRATED_FILING_NBFC_INDAS_1.xml", sebi_file("NBFC", "Consolidated"))
    assert report["format"] == "SEBI NBFC" and report["marked_source_conflict"] == 0
    assert value(c, NBFC_ISIN, "impairment_on_financial_instruments_3m", "consolidated").value == 90 * CR
    assert value(c, NBFC_ISIN, "interest_earned_3m", "consolidated").value == 800 * CR
    assert value(c, NBFC_ISIN, "net_profit_owners_3m", "consolidated").value == 220 * CR
    assert value(c, NBFC_ISIN, "net_profit_3m", "consolidated").value == 230 * CR


def test_nbfc_revenue_and_expense_breakdowns_are_checked(env):
    c, load, _ = env
    report = load("INTEGRATED_FILING_NBFC_INDAS_1.xml", sebi_file("NBFC", changes={"ImpairmentOnFinancialInstruments": 95}))
    assert any("expenses = materials" in p for p in report["problems"])
    assert value(c, NBFC_ISIN, "impairment_on_financial_instruments_3m").missing_class == "source_conflict"
    assert value(c, NBFC_ISIN, "total_expenses_3m").value == 700 * CR   # confirmed: income - expenses


# ---- life insurers ----

def test_life_insurer_accounts_and_ratios_are_read(env):
    c, load, _ = env
    report = load("INTEGRATED_FILING_LI_1.xml", sebi_file("LI"))
    assert report["format"] == "SEBI Life Insurance" and report["marked_source_conflict"] == 0
    assert value(c, LI_ISIN, "gross_premium_3m").value == 17100 * CR
    assert value(c, LI_ISIN, "profit_after_tax_3m").value == 601 * CR
    assert value(c, LI_ISIN, "solvency_ratio_3m").value == pytest.approx(1.85)
    assert value(c, LI_ISIN, "persistency_13th_month_3m").value == pytest.approx(0.80)
    assert value(c, LI_ISIN, "eps_basic_3m").value == pytest.approx(2.79)


def test_insurer_ratios_come_from_the_standalone_report_only(env):
    c, load, _ = env
    report = load("INTEGRATED_FILING_LI_1.xml", sebi_file("LI", "Consolidated"))
    assert any(p.startswith("standalone_only: OneD") and "solvency_ratio=1.85" in p for p in report["problems"])
    assert value(c, LI_ISIN, "solvency_ratio_3m", "consolidated").availability == Availability.NOT_ELIGIBLE
    assert value(c, LI_ISIN, "gross_premium_3m", "consolidated").value == 17100 * CR


def test_insurer_identities_are_checked(env):
    c, load, _ = env
    load("INTEGRATED_FILING_LI_1.xml", sebi_file("LI", changes={"BenefitsPaidNet": 8200}))
    assert value(c, LI_ISIN, "benefits_paid_3m").missing_class == "source_conflict"
    assert value(c, LI_ISIN, "policyholders_total_expenses_3m").value == 32900 * CR   # confirmed by the surplus


def test_zero_solvency_is_a_placeholder(env):
    c, load, _ = env
    report = load("INTEGRATED_FILING_LI_1.xml", sebi_file("LI", changes={"SolvencyRatio": "0"}))
    assert any(p.startswith("implausible_value") and "SolvencyRatio" in p for p in report["problems"])
    assert value(c, LI_ISIN, "solvency_ratio_3m").availability == Availability.NOT_ELIGIBLE


def test_a_year_can_be_audited_while_its_quarter_is_not(env):
    c, load, _ = env
    year = {"OneD": ("2026-01-01", "2026-03-31"), "FourD": ("2025-04-01", "2026-03-31")}
    report = load("INTEGRATED_FILING_LI_1.xml", sebi_file("LI", contexts=year, audited={"FourD": "Audited"}))
    assert report["periods"] == ["2026-03-31 (12m)", "2026-03-31 (3m)"]
    assert c.execute("SELECT audited FROM fr_loads").fetchone()[0] == "Audited, Unaudited"


# ---- revised filings ----

def test_a_revision_row_as_nse_writes_it_is_accepted(env):
    c, _, load_listing = env
    report = load_listing(listing([ORIGINAL_ROW, REVISION_ROW]))
    assert report["filings_recorded"] == 2 and report["problems"] == []
    row = c.execute("SELECT submission_type, received_at, revised_at, disseminated_at, revision_remarks FROM if_filings"
                    " WHERE submission_type = 'Revision'").fetchone()
    assert row == ("Revision", "2026-07-24T16:48:18+05:30", "2026-07-24T16:48:18+05:30",
                   "2026-07-24T16:48:55+05:30", "Inadvertent error in mentioning certain numbers")


def test_a_revision_with_the_same_figures_changes_nothing(env):
    c, load, load_listing = env
    load_listing(listing([ORIGINAL_ROW, REVISION_ROW]))
    load("INTEGRATED_FILING_LI_1.xml", sebi_file("LI"), ORIGINAL_SEEN)
    report = load("INTEGRATED_FILING_LI_2.xml", sebi_file("LI") + " ", REVISION_SEEN)
    assert report["publication_proven"] and report["facts_recorded"] == 0
    assert report["corrected_by_revision"] == 0 and report["already_present"] > 0
    evidence = c.execute("SELECT publication_evidence FROM raw_artifacts WHERE original_name = ?",
                         ["INTEGRATED_FILING_LI_2.xml"]).fetchone()[0]
    assert "revised filing - remark: Inadvertent error" in evidence


def test_a_revision_that_changes_a_figure_is_a_dated_correction(env):
    c, load, load_listing = env
    load_listing(listing([ORIGINAL_ROW, REVISION_ROW]))
    load("INTEGRATED_FILING_LI_1.xml", sebi_file("LI"), ORIGINAL_SEEN)
    report = load("INTEGRATED_FILING_LI_2.xml", sebi_file("LI", changes={"PersistencyRatio13ThMonth": "0.81"}), REVISION_SEEN)
    assert report["corrected_by_revision"] == 1
    assert c.execute("SELECT facts_corrected FROM fr_loads ORDER BY load_id DESC").fetchone()[0] == 1
    now = value(c, LI_ISIN, "persistency_13th_month_3m")
    assert (now.value, now.version) == (pytest.approx(0.81), 2)
    field, replay = "persistency_13th_month_3m", PitClaim.HISTORICAL_REPLAY
    assert value(c, LI_ISIN, field, when="2026-07-20T12:00:00+05:30", claim=replay).value == pytest.approx(0.80)
    assert value(c, LI_ISIN, field, when="2026-07-24T17:00:00+05:30", claim=replay).value == pytest.approx(0.81)
    evidence = c.execute("SELECT correction_evidence FROM pit_facts WHERE version = 2").fetchone()[0]
    assert "Inadvertent error" in evidence


def test_different_figures_under_an_original_row_stay_a_conflict(env):
    c, load, load_listing = env
    second = ("INTEGRATED_FILING_LI_3.xml", "Original", "16-Jul-2026 10:00:00", "", "", "16-Jul-2026 10:00:05")
    load_listing(listing([ORIGINAL_ROW, second]))
    load("INTEGRATED_FILING_LI_1.xml", sebi_file("LI"), ORIGINAL_SEEN)
    report = load("INTEGRATED_FILING_LI_3.xml", sebi_file("LI", changes={"PersistencyRatio13ThMonth": "0.81"}), REVISION_SEEN)
    assert report["corrected_by_revision"] == 0
    assert any(p.startswith("conflicts_with_recorded_fact") for p in report["problems"])
    assert value(c, LI_ISIN, "persistency_13th_month_3m").value == pytest.approx(0.80)


def test_a_revised_figure_that_fails_an_identity_is_not_applied(env):
    c, load, load_listing = env
    load_listing(listing([ORIGINAL_ROW, REVISION_ROW]))
    load("INTEGRATED_FILING_LI_1.xml", sebi_file("LI"), ORIGINAL_SEEN)
    report = load("INTEGRATED_FILING_LI_2.xml", sebi_file("LI", changes={"BenefitsPaidNet": 8200}), REVISION_SEEN)
    assert any(p.startswith("revision_not_applied") and "benefits_paid_3m" in p for p in report["problems"])
    assert value(c, LI_ISIN, "benefits_paid_3m").value == 8100 * CR


@pytest.mark.parametrize("row, message", [
    (("INTEGRATED_FILING_LI_2.xml", "Revision", "", "", "x", "24-Jul-2026 16:48:55"), "must carry its revision time"),
    (("INTEGRATED_FILING_LI_2.xml", "Original", "15-Jul-2026 17:51:12", "24-JUL-2026 16:48:18", "", "24-Jul-2026 16:48:55"),
     "must not carry a revision time"),
    (("INTEGRATED_FILING_LI_2.xml", "Revision", "", "24-JUL-2026 16:50:00", "x", "24-Jul-2026 16:48:55"),
     "before receipt"),
    (("INTEGRATED_FILING_LI_2.xml", "Revision", "24-Jul-2026 16:40:00", "24-JUL-2026 16:50:00", "x", "24-Jul-2026 16:48:55"),
     "revision time is after the dissemination time"),
    (("INTEGRATED_FILING_LI_2.xml", "Revised", "", "24-JUL-2026 16:48:18", "x", "24-Jul-2026 16:48:55"),
     "unknown type of submission"),
])
def test_revision_rows_that_cannot_be_trusted_are_rejected(env, row, message):
    c, _, load_listing = env
    report = load_listing(listing([row]))
    assert report["filings_recorded"] == 0 and message in report["problems"][0]


# ---- migration and acceptance record ----

def test_revision_corrections_migration_rolls_back_cleanly():
    c = connect(":memory:")
    migrate(c)
    rollback(c, 12)
    columns = {r[1] for r in c.execute("PRAGMA table_info(fr_loads)")}
    assert "facts_corrected" not in columns and "facts_marked_conflict" in columns
    triggers = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'fr_loads'")}
    assert triggers == {"fr_loads_no_update", "fr_loads_no_delete"}   # still append-only
    c.close()


def test_stage_8d_acceptance_record_is_valid():
    from core.status import load_acceptance_records
    record = load_acceptance_records()["STAGE_08D_acceptance.yaml"]
    assert record["status"] == "ACCEPTED_NBFC_INSURER_AND_REVISION_BASELINE"
    assert record["negative_assertions"]["recorded figure overwritten by a revision"] is False
