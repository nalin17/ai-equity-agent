"""Stage 8C tests: intake of hand-downloaded files and the download checklist (ADR-004, 4, 5B.2).

NSE's terms of use prohibit automated data collection, so nothing here may contact a
website: the tools only move, order and load files a person downloaded, and list the
links a person still has to click.
"""
import re
from datetime import date

import pytest

from core.config import PROJECT_ROOT
from core.database import connect, migrate
from ingestion.intake import checklist_items, collect_downloads, ingest_inbox, kind_of, write_checklist
from ingestion.source_registry import sync_sources
from test_stage08b_integrated_filings import ISIN, if_listing, ifxbrl
from universe.entities import add_alias, add_entity

NOW = "2026-10-02T16:30:00+05:30"
LISTING = "CF-Integrated-Filing-equities-Integrated Filing- Financials-HDFCBANK-02-Oct-2026.csv"
MARCH = {"OneD": (("2026-01-01", "2026-03-31"), ("2026-01-01", "2026-03-31"))}


@pytest.fixture
def env(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    add_entity(c, ISIN, "HDFC Bank Limited")
    add_alias(c, ISIN, "nse_symbol", "HDFCBANK", "1995-11-08")
    inbox, downloads = tmp_path / "inbox", tmp_path / "Downloads"
    inbox.mkdir()
    downloads.mkdir()

    def put(folder, name, text):
        (folder / name).write_text(text, encoding="utf-8")

    def run(**kwargs):
        return ingest_inbox(c, inbox, raw_dir=tmp_path / "raw", now=lambda: NOW, **kwargs)

    yield c, inbox, downloads, put, run
    c.close()


def listing_rows():
    return [("INTEGRATED_FILING_BANKING_1.xml", "Standalone", "30-JUN-2026", "18-Jul-2026 16:01:37", "Original", ""),
            ("INTEGRATED_FILING_BANKING_2.xml", "Standalone", "31-MAR-2026", "18-Apr-2026 19:28:37", "Original", ""),
            ("INTEGRATED_FILING_BANKING_3.xml", "Standalone", "31-DEC-2025", "17-Jan-2026 21:26:17", "Original", "")]


# ---- collecting downloads ----

def test_browser_copies_are_renamed_and_other_files_left_alone(env):
    _, inbox, downloads, put, _ = env
    put(downloads, "INTEGRATED_FILING_BANKING_9_WEB (1).xml", "x")
    put(downloads, "BhavCopy_NSE_CM_0_0_0_20261001_F_0000.csv (2).zip", "y")
    put(downloads, "holiday photos.txt", "z")
    report = collect_downloads(downloads, inbox)
    assert sorted(report["moved"]) == ["BhavCopy_NSE_CM_0_0_0_20261001_F_0000.csv.zip",
                                       "INTEGRATED_FILING_BANKING_9_WEB.xml"]
    assert [p.name for p in downloads.iterdir()] == ["holiday photos.txt"]


def test_nothing_is_ever_overwritten(env):
    _, inbox, downloads, put, _ = env
    put(inbox, "INTEGRATED_FILING_BANKING_9.xml", "original bytes")
    put(downloads, "INTEGRATED_FILING_BANKING_9.xml", "different bytes")
    put(inbox, "INTEGRATED_FILING_BANKING_8.xml", "same")
    put(downloads, "INTEGRATED_FILING_BANKING_8 (1).xml", "same")
    report = collect_downloads(downloads, inbox)
    assert report == {"moved": [], "already_in_inbox": ["INTEGRATED_FILING_BANKING_8 (1).xml"],
                      "name_clash": ["INTEGRATED_FILING_BANKING_9.xml"]}
    assert (inbox / "INTEGRATED_FILING_BANKING_9.xml").read_text(encoding="utf-8") == "original bytes"
    assert len(list(downloads.iterdir())) == 2


def test_a_newer_file_under_a_reused_nse_name_is_kept_beside_the_old_one(env):
    _, inbox, downloads, put, _ = env
    put(inbox, "EQUITY_L.csv", "old list")
    put(downloads, "EQUITY_L (1).csv", "new list")
    moved = collect_downloads(downloads, inbox)["moved"]
    assert len(moved) == 1 and re.fullmatch(r"EQUITY_L__[0-9a-f]{8}\.csv", moved[0])
    assert kind_of(moved[0])[0] == "equity_list"
    assert (inbox / "EQUITY_L.csv").read_text(encoding="utf-8") == "old list"


# ---- loading the inbox ----

def test_listings_load_first_and_results_in_the_order_nse_published_them(env):
    c, inbox, _, put, run = env
    put(inbox, LISTING, if_listing(listing_rows()))
    put(inbox, "INTEGRATED_FILING_BANKING_1.xml", ifxbrl())
    put(inbox, "INTEGRATED_FILING_BANKING_2.xml", ifxbrl(contexts=MARCH))
    results = run()
    assert [(name, outcome) for name, _, outcome, _ in results] == [
        (LISTING, "loaded"), ("INTEGRATED_FILING_BANKING_2.xml", "loaded"), ("INTEGRATED_FILING_BANKING_1.xml", "loaded")]
    assert all(detail["publication_proven"] for name, kind, _, detail in results if kind == "results")


def test_a_results_file_waits_for_its_listing(env):
    c, inbox, _, put, run = env
    put(inbox, "INTEGRATED_FILING_BANKING_1.xml", ifxbrl())
    [(name, kind, outcome, detail)] = run()
    assert outcome == "waiting" and "listing" in detail
    assert c.execute("SELECT COUNT(*) FROM raw_artifacts").fetchone()[0] == 0   # nothing stored
    [(_, _, outcome, detail)] = run(require_listing=False)
    assert outcome == "loaded" and not detail["publication_proven"]


def test_ingested_files_are_skipped_and_one_failure_does_not_stop_the_rest(env):
    c, inbox, _, put, run = env
    put(inbox, LISTING, if_listing(listing_rows()))
    put(inbox, "INTEGRATED_FILING_BANKING_1.xml", ifxbrl())
    put(inbox, "BhavCopy_NSE_CM_0_0_0_20260105_F_0000.csv", "not a bhavcopy\n1,2\n")
    put(inbox, "BhavCopy_NSE_CM_0_0_0_20260102_F_0000.csv", "not a bhavcopy either\n1,2\n")
    put(inbox, "readme.txt", "notes")
    first = run()
    outcomes = [(name, outcome) for name, _, outcome, _ in first]
    assert outcomes == [("readme.txt", "skipped"),
                        ("BhavCopy_NSE_CM_0_0_0_20260102_F_0000.csv", "failed"),   # prices in trade-date order
                        ("BhavCopy_NSE_CM_0_0_0_20260105_F_0000.csv", "failed"),
                        (LISTING, "loaded"), ("INTEGRATED_FILING_BANKING_1.xml", "loaded")]
    second = {(name, outcome, detail) for name, _, outcome, detail in run() if outcome == "skipped"}
    assert (LISTING, "skipped", "already ingested") in second
    assert ("INTEGRATED_FILING_BANKING_1.xml", "skipped", "already ingested") in second


# ---- the checklist ----

def test_the_checklist_lists_only_what_is_still_missing(env, tmp_path):
    c, inbox, _, put, run = env
    put(inbox, LISTING, if_listing(listing_rows()))
    put(inbox, "INTEGRATED_FILING_BANKING_1.xml", ifxbrl())
    run()
    put(inbox, "INTEGRATED_FILING_BANKING_2.xml", ifxbrl(contexts=MARCH))
    tcs = tmp_path / "tcs.csv"
    tcs.write_text(if_listing([("INTEGRATED_FILING_INDAS_7.xml", "Consolidated", "30-JUN-2026",
                                "09-Jul-2026 18:36:20", "Original", "")], symbol="TCS",
                              company="Tata Consultancy Services Limited"), encoding="utf-8")
    items = checklist_items(c, [inbox / LISTING, tcs], inbox, symbols=["hdfcbank"])
    assert {i["file"]: i["status"] for i in items} == {
        "INTEGRATED_FILING_BANKING_1.xml": "in database",
        "INTEGRATED_FILING_BANKING_2.xml": "in inbox, not loaded yet",
        "INTEGRATED_FILING_BANKING_3.xml": "to download"}
    assert len(checklist_items(c, [inbox / LISTING], inbox, since="2026-03-31")) == 2
    page = tmp_path / "checklist.html"
    assert write_checklist(items, page) == 1
    text = page.read_text(encoding="utf-8")
    assert text.count("<a href=") == 1
    assert 'href="https://nsearchives.nseindia.com/corporate/xbrl/INTEGRATED_FILING_BANKING_3.xml"' in text


def test_the_checklist_lists_missing_weekday_price_files(env):
    c, inbox, _, _, _ = env
    items = checklist_items(c, [], inbox, prices_from="2026-09-21", today=date(2026, 9, 28))
    assert [i["period"] for i in items] == ["2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25"]
    assert items[0]["url"] == ("https://nsearchives.nseindia.com/content/cm/"
                               "BhavCopy_NSE_CM_0_0_0_20260921_F_0000.csv.zip")


# ---- ADR-004: no automated collection ----

def test_no_code_contacts_a_website():
    # ADR-004: NSE's terms of use prohibit automated collection. No module may open a network connection,
    # except the GDELT news fetcher allowed by ADR-005 (its limits are tested in test_stage10_news.py).
    pattern = re.compile(r"^\s*(import|from)\s+(urllib|requests|http|httpx|aiohttp|socket|selenium|playwright"
                         r"|mechanize|scrapy|ftplib|smtplib)\b", re.M)
    files = list((PROJECT_ROOT / "src").rglob("*.py")) + [PROJECT_ROOT / "manage.py"]
    fetcher = PROJECT_ROOT / "src" / "ingestion" / "news_fetch.py"
    offenders = [str(p) for p in files if p != fetcher and pattern.search(p.read_text(encoding="utf-8"))]
    assert offenders == []


def test_stage_8c_acceptance_record_is_valid():
    from core.status import load_acceptance_records
    record = load_acceptance_records()["STAGE_08C_acceptance.yaml"]
    assert record["status"] == "ACCEPTED_MANUAL_INTAKE_BASELINE"
    assert record["negative_assertions"]["automated collection from NSE"] is False
