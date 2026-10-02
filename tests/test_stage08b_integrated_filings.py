"""Stage 8B tests: SEBI integrated filings - banks and current results (architecture 40B step 7, 4, 4C, 5B, 9B).

From NSE's real files: results for quarters ended March 2025 onwards are published only as
SEBI integrated filings; bank files use their own line items; bank ratios in consolidated
reports are placeholder zeros; the file carries its own ISIN; the listing's column names
end with a space and a line break.
"""
import sqlite3

import pytest

from core.database import connect, migrate, rollback
from ingestion.nse_financial_results import INDAS_FIELDS, ResultsFileError, load_results_index, load_results_xbrl
from ingestion.source_registry import sync_sources
from provenance.availability import Availability, PitClaim
from provenance.pit_store import fact_as_of
from universe.entities import add_alias, add_entity

ISIN = "INE040A01034"
TCS_ISIN = "INE467B01029"
RETRIEVED = "2026-10-02T16:30:00+05:30"
CR = 10_000_000  # one crore

BANK = {  # a consistent bank quarter, in crore
    "InterestOrDiscountOnAdvancesOrBills": 600, "RevenueOnInvestments": 150,
    "InterestOnBalancesWithReserveBankOfIndiaAndOtherInterBankFunds": 20, "OtherInterest": 30,
    "InterestEarned": 800, "OtherIncome": 200, "Income": 1000, "InterestExpended": 450, "EmployeesCost": 100,
    "OtherOperatingExpenses": 150, "OperatingExpenses": 250, "ExpenditureExcludingProvisionsAndContingencies": 700,
    "OperatingProfitBeforeProvisionAndContingencies": 300, "ProvisionsOtherThanTaxAndContingencies": 60,
    "ExceptionalItems": 0, "ProfitLossFromOrdinaryActivitiesBeforeTax": 240, "TaxExpense": 60,
    "ProfitLossFromOrdinaryActivitiesAfterTax": 180, "ExtraordinaryItems": 0, "ProfitLossForThePeriod": 180,
    "PaidUpValueOfEquityShareCapital": 150, "GrossNonPerformingAssets": 40, "NonPerformingAssets": 12,
}
GROUP = {"ProfitLossOfMinorityInterest": 10, "ShareOfProfitLossOfAssociates": 5}   # consolidated only
RATIOS = {"PercentageOfGrossNpa": "0.012", "PercentageOfNpa": "0.0036", "CET1Ratio": "0.165",
          "ReturnOnAssets": "0.0047"}
PER_SHARE = {"FaceValueOfEquityShareCapital": "1", "BasicEarningsPerShareAfterExtraordinaryItems": "11.67",
             "DilutedEarningsPerShareAfterExtraordinaryItems": "11.65"}
INDAS = {"RevenueFromOperations": 700, "OtherIncome": 30, "Income": 730, "Expenses": 550,
         "ProfitBeforeExceptionalItemsAndTax": 180, "ExceptionalItemsBeforeTax": 0, "ProfitBeforeTax": 180,
         "TaxExpense": 45, "ProfitLossForPeriodFromContinuingOperations": 135, "ProfitLossForPeriod": 135,
         "ProfitOrLossAttributableToOwnersOfParent": 134, "ProfitOrLossAttributableToNonControllingInterests": 1,
         "PaidUpValueOfEquityShareCapital": 362}
QUARTER = {"OneD": (("2026-04-01", "2026-06-30"), ("2026-04-01", "2026-06-30"))}


def ifxbrl(family="Banking", basis="Standalone", symbol="HDFCBANK", isin=ISIN, name="HDFC Bank Limited",
           changes=None, contexts=None, extra="", taxonomy_date="2026-01-31"):
    """A SEBI integrated-filing results file shaped like NSE's real ones. In consolidated bank
    reports the ratio and NPA fields carry zeros, as they do on NSE."""
    contexts = contexts or QUARTER
    tax = f"http://www.sebi.gov.in/xbrl/{taxonomy_date}/in-capmkt"
    ent = f"http://www.sebi.gov.in/xbrl/IntegratedFinance_{family}/{taxonomy_date}/in-capmkt/in-capmkt-ent"
    if family == "Banking":
        amounts, ratios, name_element = dict(BANK), dict(RATIOS), "NameOfBank"
        if basis == "Consolidated":
            amounts.update(GROUP)
            amounts["ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates"] = 175
            amounts.update(GrossNonPerformingAssets=0, NonPerformingAssets=0)
            ratios = {k: "0" for k in ratios}
        else:
            amounts["ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates"] = 180
    else:
        amounts, ratios, name_element = dict(INDAS), {}, "NameOfTheCompany"
    per_share = dict(PER_SHARE)
    if family != "Banking":
        per_share = {"FaceValueOfEquityShareCapital": "1",
                     "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations": "37.00",
                     "DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations": "37.00"}
    for key, value in (changes or {}).items():
        target = ratios if key in ratios else per_share if key in per_share else amounts
        target[key] = value
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?><!--IF test-->'
           f'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:in-capmkt="{tax}" '
           f'xmlns:in-capmkt-ent="{ent}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xmlns:iso4217="http://www.xbrl.org/2003/iso4217" xmlns:other="http://example.com/other">']
    for cid, ((start, end), _) in contexts.items():
        out.append(f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier scheme="x">500180</xbrli:identifier>'
                   f'</xbrli:entity><xbrli:period><xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{end}'
                   '</xbrli:endDate></xbrli:period></xbrli:context>')
    out.append('<xbrli:unit id="INR"><xbrli:measure>iso4217:INR</xbrli:measure></xbrli:unit>'
               '<xbrli:unit id="pure"><xbrli:measure>xbrli:pure</xbrli:measure></xbrli:unit>'
               '<xbrli:unit id="INRPerShare"><xbrli:divide><xbrli:unitNumerator><xbrli:measure>iso4217:INR'
               '</xbrli:measure></xbrli:unitNumerator><xbrli:unitDenominator><xbrli:measure>xbrli:shares'
               '</xbrli:measure></xbrli:unitDenominator></xbrli:divide></xbrli:unit>')
    out.append(f'<in-capmkt:Symbol contextRef="OneD">{symbol}</in-capmkt:Symbol>'
               f'<in-capmkt:ISIN contextRef="OneD">{isin}</in-capmkt:ISIN>'
               f'<in-capmkt:{name_element} contextRef="OneD">{name}</in-capmkt:{name_element}>'
               '<in-capmkt:DescriptionOfPresentationCurrency contextRef="OneD">INR</in-capmkt:DescriptionOfPresentationCurrency>')
    for cid, (_, (start, end)) in contexts.items():
        scale = 1 if cid == "OneD" else 3
        out.append(f'<in-capmkt:DateOfStartOfReportingPeriod contextRef="{cid}">{start}</in-capmkt:DateOfStartOfReportingPeriod>'
                   f'<in-capmkt:DateOfEndOfReportingPeriod contextRef="{cid}">{end}</in-capmkt:DateOfEndOfReportingPeriod>'
                   f'<in-capmkt:WhetherResultsAreAuditedOrUnaudited contextRef="{cid}">Unaudited</in-capmkt:WhetherResultsAreAuditedOrUnaudited>'
                   f'<in-capmkt:NatureOfReportStandaloneConsolidated contextRef="{cid}">{basis}</in-capmkt:NatureOfReportStandaloneConsolidated>')
        for tag, crore in amounts.items():
            out.append(f'<in-capmkt:{tag} contextRef="{cid}" unitRef="INR" decimals="-5">{crore * scale * CR:.2f}</in-capmkt:{tag}>')
        for tag, value in ratios.items():
            out.append(f'<in-capmkt:{tag} contextRef="{cid}" unitRef="pure" decimals="INF">{value}</in-capmkt:{tag}>')
        for tag, value in per_share.items():
            out.append(f'<in-capmkt:{tag} contextRef="{cid}" unitRef="INRPerShare" decimals="INF">{value}</in-capmkt:{tag}>')
    out.append(extra + "</xbrli:xbrl>")
    return "".join(out)


def if_listing(rows, symbol="HDFCBANK", company="HDFC Bank Limited"):
    """NSE's integrated-filing listing, with its real quirk: column names end in a space and a line break."""
    names = ["SYMBOL", "COMPANY NAME", "QUARTER END DATE", "TYPE OF SUBMISSION", "AUDITED / UNAUDITED",
             "CONSOLIDATED / STANDALONE", "DETAILS", "XBRL", "BROADCAST DATE/TIME", "REVISED DATE/TIME",
             "REVISION REMARKS", "EXCHANGE DISSEMINATION TIME", "TIME TAKEN"]
    lines = [",".join(f'"{n} \n"' for n in names)]
    for file_name, basis, ended, disseminated, submission, revised in rows:
        revision = f'"{revised}","Typo corrected"' if revised else ","
        lines.append(f'"{symbol}","{company}","{ended}","{submission}","Un-Audited","{basis}",'
                     f'"https://nsearchives.nseindia.com/corporate/ixbrl/x.html",'
                     f'"https://nsearchives.nseindia.com/corporate/xbrl/{file_name}","{disseminated}",'
                     f'{revision},'
                     f'"{disseminated}","00:00:10"')
    return chr(0xFEFF) + "\n".join(lines) + "\n"   # NSE files start with a byte-order mark


@pytest.fixture
def env(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    add_entity(c, ISIN, "HDFC Bank Limited")
    add_alias(c, ISIN, "nse_symbol", "HDFCBANK", "1995-11-08")
    add_entity(c, TCS_ISIN, "Tata Consultancy Services Limited")
    add_alias(c, TCS_ISIN, "nse_symbol", "TCS", "2004-08-25")

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


def value(c, field, basis, end="2026-06-30", when=RETRIEVED, claim=PitClaim.CURRENT_DECISION, isin=ISIN):
    return fact_as_of(c, isin, field, basis, end, when, claim)


def count(c, table):
    return c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# ---- banks: basis, bank ratios, identities ----

def test_bank_consolidated_and_standalone_never_mix(env):
    c, load, _ = env
    load("INTEGRATED_FILING_BANKING_1.xml", ifxbrl(basis="Consolidated", changes={"InterestEarned": 810,
         "InterestOrDiscountOnAdvancesOrBills": 610, "Income": 1010, "OperatingProfitBeforeProvisionAndContingencies": 310,
         "ProvisionsOtherThanTaxAndContingencies": 70}))
    load("INTEGRATED_FILING_BANKING_2.xml", ifxbrl(basis="Standalone"))
    assert value(c, "interest_earned_3m", "consolidated").value == 810 * CR
    assert value(c, "interest_earned_3m", "standalone").value == 800 * CR
    assert value(c, "net_profit_owners_3m", "consolidated").value == 175 * CR
    assert c.execute("SELECT COUNT(*) FROM pit_facts WHERE basis NOT IN ('consolidated', 'standalone')").fetchone()[0] == 0


def test_bank_ratios_come_from_the_standalone_report_only(env):
    c, load, _ = env
    cons = load("INTEGRATED_FILING_BANKING_1.xml", ifxbrl(basis="Consolidated"))
    load("INTEGRATED_FILING_BANKING_2.xml", ifxbrl(basis="Standalone"))
    assert any(p.startswith("standalone_only: OneD") and "cet1_ratio=0" in p for p in cons["problems"])
    for field in ("gross_npa_3m", "net_npa_3m", "gross_npa_ratio_3m", "net_npa_ratio_3m", "cet1_ratio_3m",
                  "return_on_assets_3m"):
        assert value(c, field, "consolidated").availability == Availability.NOT_ELIGIBLE   # zero never stored
    assert value(c, "gross_npa_ratio_3m", "standalone").value == pytest.approx(0.012)
    assert value(c, "cet1_ratio_3m", "standalone").value == pytest.approx(0.165)
    assert value(c, "gross_npa_3m", "standalone").value == 40 * CR


def test_bank_identities_are_checked(env):
    c, load, _ = env
    report = load("INTEGRATED_FILING_BANKING_1.xml", ifxbrl(changes={"InterestEarned": 810}))
    assert any("interest earned = advances" in p for p in report["problems"])
    assert value(c, "interest_earned_3m", "standalone").missing_class == "source_conflict"
    assert value(c, "other_income_3m", "standalone").missing_class == "source_conflict"   # nothing confirms it
    assert value(c, "total_income_3m", "standalone").value == 1000 * CR   # confirmed: income - expenditure
    assert value(c, "net_profit_owners_3m", "standalone").value == 180 * CR


def test_values_that_cannot_be_zero_are_placeholders_and_not_stored(env):
    c, load, _ = env
    report = load("INTEGRATED_FILING_BANKING_1.xml", ifxbrl(changes={"CET1Ratio": "0",
                                                                     "PaidUpValueOfEquityShareCapital": 0}))
    assert sum(p.startswith("implausible_value") for p in report["problems"]) == 2
    assert value(c, "cet1_ratio_3m", "standalone").availability == Availability.NOT_ELIGIBLE
    assert value(c, "paid_up_equity_capital_3m", "standalone").availability == Availability.NOT_ELIGIBLE
    assert value(c, "gross_npa_ratio_3m", "standalone").value == pytest.approx(0.012)


def test_facts_outside_the_sebi_taxonomy_are_ignored(env):
    c, load, _ = env
    load("INTEGRATED_FILING_BANKING_1.xml",
         ifxbrl(extra='<other:InterestEarned contextRef="OneD" unitRef="INR" decimals="-5">1.00</other:InterestEarned>'))
    assert value(c, "interest_earned_3m", "standalone").value == 800 * CR


# ---- periods ----

def test_an_honest_nine_month_context_is_out_of_scope_and_a_year_is_kept(env):
    c, load, _ = env
    nine = {"OneD": (("2025-10-01", "2025-12-31"), ("2025-10-01", "2025-12-31")),
            "FourD": (("2025-04-01", "2025-12-31"), ("2025-04-01", "2025-12-31"))}
    report = load("INTEGRATED_FILING_BANKING_1.xml", ifxbrl(contexts=nine))
    assert report["periods"] == ["2025-12-31 (3m)"]
    assert any("9-month period is not stored" in p for p in report["problems"])
    year = {"OneD": (("2026-01-01", "2026-03-31"), ("2026-01-01", "2026-03-31")),
            "FourD": (("2025-04-01", "2026-03-31"), ("2025-04-01", "2026-03-31"))}
    report = load("INTEGRATED_FILING_BANKING_2.xml", ifxbrl(contexts=year))
    assert report["periods"] == ["2026-03-31 (12m)", "2026-03-31 (3m)"]
    assert value(c, "interest_earned_12m", "standalone", "2026-03-31").value == 2400 * CR


# ---- identity of the company ----

def test_the_files_own_isin_must_be_the_companys(env):
    c, load, _ = env
    with pytest.raises(ResultsFileError, match="the file's ISIN INE999A01011"):
        load("INTEGRATED_FILING_BANKING_1.xml", ifxbrl(isin="INE999A01011"))
    assert count(c, "pit_facts") == 0 and count(c, "raw_artifacts") == 0


@pytest.mark.parametrize("kwargs, message", [
    ({"family": "GI"}, "'GI' companies is not supported yet"),
    ({"name": "Some Other Bank Limited"}, "registry has"),
    ({"symbol": "NOSUCH"}, "not attached"),
])
def test_unusable_integrated_files_are_refused_whole(env, kwargs, message):
    c, load, _ = env
    with pytest.raises(ResultsFileError, match=message):
        load("INTEGRATED_FILING_X_1.xml", ifxbrl(**kwargs))
    assert count(c, "pit_facts") == 0 and count(c, "raw_artifacts") == 0


def test_ind_as_companies_keep_the_same_fields_as_the_old_format(env):
    c, load, _ = env
    report = load("INTEGRATED_FILING_INDAS_1.xml", ifxbrl(family="IndAS", basis="Consolidated", symbol="TCS",
                                                          isin=TCS_ISIN, name="Tata Consultancy Services Limited"))
    assert report["format"] == "SEBI Ind AS" and report["marked_source_conflict"] == 0
    stored = {r[0] for r in c.execute("SELECT field FROM pit_facts WHERE isin = ?", [TCS_ISIN])}
    assert stored <= {f"{field}_3m" for field, _ in INDAS_FIELDS.values()}
    assert value(c, "revenue_from_operations_3m", "consolidated", isin=TCS_ISIN).value == 700 * CR


# ---- 5B: the integrated listing ----

def test_integrated_listing_proves_publication_time(env):
    c, load, load_listing = env
    listed = load_listing("CF-Integrated.csv", if_listing([
        ("INTEGRATED_FILING_BANKING_9.xml", "Standalone", "30-JUN-2026", "18-Jul-2026 16:01:37", "Original", "")]))
    assert (listed["listing"], listed["filings_recorded"]) == ("integrated", 1)
    report = load("INTEGRATED_FILING_BANKING_9.xml", ifxbrl())
    assert report["publication_proven"]
    assert count(c, "if_load_filings") == 1
    field = "net_profit_owners_3m"
    assert value(c, field, "standalone", when="2026-07-18T16:00:00+05:30",
                 claim=PitClaim.HISTORICAL_REPLAY).availability == Availability.NOT_ELIGIBLE
    assert value(c, field, "standalone", when="2026-07-18T16:05:00+05:30",
                 claim=PitClaim.HISTORICAL_REPLAY).availability == Availability.ELIGIBLE


def test_integrated_listing_rows_that_cannot_be_trusted_are_rejected(env):
    c, _, load_listing = env
    report = load_listing("CF-Integrated.csv", if_listing([
        ("INTEGRATED_FILING_BANKING_1.xml", "Standalone", "30-JUN-2026", "18-Jul-2026 16:01:37", "Original", ""),
        ("INTEGRATED_FILING_BANKING_2.xml", "Standalone", "30-JUN-2026", "18-Jul-2026 16:01:37", "Revision", ""),
        ("INTEGRATED_FILING_BANKING_3.xml", "Standalone", "30-JUN-2026", "18-Jul-2026 16:01:37", "Draft", ""),
        ("INTEGRATED_FILING_BANKING_4.xml", "Partly", "30-JUN-2026", "18-Jul-2026 16:01:37", "Original", ""),
        ("INTEGRATED_FILING_BANKING_5.xml", "Standalone", "30-JUN-2026", "18-Jul-2099 16:01:37", "Original", ""),
    ]))
    assert report["filings_recorded"] == 1 and len(report["problems"]) == 4
    assert any("must carry its revision time" in p for p in report["problems"])


@pytest.mark.parametrize("listing_kwargs, row, message", [
    ({"symbol": "HDFC"}, ("Standalone", "30-JUN-2026"), "listing names symbol HDFC"),
    ({}, ("Consolidated", "30-JUN-2026"), "listing says Consolidated"),
    ({}, ("Standalone", "31-MAR-2026"), "period ended 2026-03-31"),
])
def test_a_file_that_disagrees_with_its_integrated_listing_is_refused(env, listing_kwargs, row, message):
    c, load, load_listing = env
    basis, ended = row
    load_listing("CF-Integrated.csv", if_listing([("INTEGRATED_FILING_BANKING_9.xml", basis, ended,
                                                   "18-Jul-2026 16:01:37", "Original", "")], **listing_kwargs))
    with pytest.raises(ResultsFileError, match=message):
        load("INTEGRATED_FILING_BANKING_9.xml", ifxbrl())
    assert count(c, "pit_facts") == 0 and count(c, "fr_loads") == 0


# ---- migration and acceptance record ----

def test_integrated_filing_tables_are_append_only(env):
    c, load, load_listing = env
    load_listing("CF-Integrated.csv", if_listing([
        ("INTEGRATED_FILING_BANKING_9.xml", "Standalone", "30-JUN-2026", "18-Jul-2026 16:01:37", "Original", "")]))
    load("INTEGRATED_FILING_BANKING_9.xml", ifxbrl())
    for sql in ("UPDATE if_filings SET symbol = 'X'", "DELETE FROM if_filings", "DELETE FROM if_load_filings"):
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            c.execute(sql)


def test_integrated_filing_migration_rolls_back_cleanly():
    c = connect(":memory:")
    migrate(c)
    rollback(c, 11)
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
    assert not {"if_filings", "if_load_filings"} & names and "fr_loads" in names
    c.close()


def test_stage_8b_acceptance_record_is_valid():
    from core.status import load_acceptance_records
    record = load_acceptance_records()["STAGE_08B_acceptance.yaml"]
    assert record["status"] == "ACCEPTED_BANK_AND_INTEGRATED_RESULTS_BASELINE"
    assert record["negative_assertions"]["bank ratio stored from a consolidated report"] is False
