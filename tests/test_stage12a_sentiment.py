"""Stage 12A tests: GDELT GKG headlines, filing directions, price echo, the liquidity gate and public sentiment in the
hub (architecture 40B step 10, 4B, 4D, 5B, 9A; ADR-013).

GKG rows are made up in GDELT's real shape (27 tab-separated fields, PAGE_TITLE in V2EXTRASXML, V1.5TONE with 7
values), measured on GDELT's files of 6 and 8 Nov 2026. Headlines name companies, never persons. Every
price-echo case below is the shape of a real headline in those files.
"""
import hashlib
import io
import sqlite3
import zipfile
from datetime import datetime, timedelta, timezone

import pytest

from core.config import PROJECT_ROOT
from core.database import connect, current_version, migrate, rollback
from core.status import load_acceptance_records
from data_quality.extraction_confidence import ExtractionConfidence
from data_quality.missing_data import MissingClass
from ingestion import news_fetch
from ingestion.gdelt_gkg import (GkgFileError, GkgNotReadError, extract, load_gkg, plain, read_gkg, read_lastupdate,
                                 slot_of, stories)
from ingestion.gdelt_news import sync_news_names
from ingestion.market_adapters import ingest_market_file
from ingestion.nse_announcements import load_announcements
from ingestion.source_registry import get_source, sync_sources
from knowledge.evidence import Attribution, Domain, GapNature
from knowledge.hub import NOT_BUILT, gather
from knowledge.sentiment import (CONFLICTING, NEGATIVE, POSITIVE, PRICE_ECHO, UNKNOWN, eligibility, filing_direction,
                                 liquidity, price_echo)
from provenance.availability import PitClaim
from test_stage07a_market_adapters import EQUITY_LIST, RELIANCE, TCS, udiff_text
from test_stage09_corporate_events import listing, row as filing
from universe.equity_list import load_equity_list

UTC = timezone.utc
CURRENT, REPLAY = PitClaim.CURRENT_DECISION, PitClaim.HISTORICAL_REPLAY
SLOT = datetime(2024, 3, 15, 4, 30, tzinfo=UTC)          # 10:00 India time
READ = SLOT + timedelta(hours=2)
DECIDE = datetime(2024, 3, 20, 6, 0, tzinfo=UTC)
TONE = "-1.5,2.1,3.6,5.7,20.4,0.3,310"
IN_PLACE = "4#Mumbai, Maharashtra, India#IN#IN16#18.975#72.8258#-2097138"
US_PLACE = "2#Texas, United States#US#USTX#31.106#-97.6475#TX"
NAMES = """companies:
  - symbol: RELIANCE
    isin: INE002A01018
    names: [Reliance Industries, RIL]
    valid_from: 1995-11-29
  - symbol: TCS
    isin: INE467B01029
    names: [Tata Consultancy Services, TCS]
    valid_from: 2004-08-25
"""
ORDER = ("https://news.example.in/business/reliance-industries-bags-rs-5000-crore-order/1.html",
         "Reliance Industries bags Rs 5,000 crore order from state power utility")


def gkg_row(url, title, site="news.example.in", places=IN_PLACE, tone=TONE, slot=SLOT, collection="1",
            record=None, stated=None, orgs=""):
    extras = (f"<PAGE_TITLE>{title}</PAGE_TITLE>" if title is not None else "") + (
        f"<PAGE_PRECISEPUBTIMESTAMP>{stated}</PAGE_PRECISEPUBTIMESTAMP>" if stated else "")
    fields = [""] * 27
    fields[0] = record or f"{slot:%Y%m%d%H%M%S}-{abs(hash(url)) % 1000}"
    fields[1], fields[2], fields[3], fields[4] = f"{slot:%Y%m%d%H%M%S}", collection, site, url
    fields[9], fields[13], fields[15], fields[26] = places, orgs, tone, extras
    return "\t".join(fields)


def gkg_zip(rows, slot=SLOT, member=None, extra=None):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(member or f"{slot:%Y%m%d%H%M%S}.gkg.csv", "\n".join(rows) + "\n")
        if extra:
            z.writestr(extra, "x")
    return out.getvalue()


def raw_zip(member, data):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(member, data)
    return out.getvalue()


def name(slot=SLOT):
    return f"{slot:%Y%m%d%H%M%S}.gkg.csv.zip"


def count(c, table):
    return c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


@pytest.fixture
def env(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    (tmp_path / "EQUITY_L.csv").write_text(EQUITY_LIST, encoding="utf-8")
    load_equity_list(c, tmp_path / "EQUITY_L.csv", "2024-03-01T19:00:00+05:30", raw_dir=tmp_path / "raw")
    (tmp_path / "names.yaml").write_text(NAMES, encoding="utf-8")
    sync_news_names(c, tmp_path / "names.yaml", today="2024-03-01")
    yield c
    c.close()


def trade(c, tmp_path, days, rows):
    """One NSE bhavcopy per day, each read the evening of its day: rows = [(symbol, isin, close, volume)]."""
    for day in days:
        text = udiff_text([(s, "EQ", isin, day, close, close, close, close, volume) for s, isin, close, volume in rows])
        path = tmp_path / f"BhavCopy_NSE_CM_0_0_0_{day.replace('-', '')}_F_0000.csv"
        path.write_text(text, encoding="utf-8")
        ingest_market_file(c, path, f"{day}T19:00:00+05:30", raw_dir=tmp_path / "raw")


WEEK = ["2024-03-11", "2024-03-12", "2024-03-13", "2024-03-14", "2024-03-15"]


# ---- reading a GKG file: whole or nothing ---------------------------------------------------------------

def test_a_gkg_file_name_names_a_15_minute_slot():
    assert slot_of("20240315043000.gkg.csv.zip") == SLOT
    for bad in ("20240315043100.gkg.csv.zip", "20240315043000.export.CSV.zip", "20241315043000.gkg.csv.zip",
                "masterfilelist.txt", "../20240315043000.gkg.csv.zip", None):
        with pytest.raises(GkgFileError):
            slot_of(bad)


def test_lastupdate_lists_the_gkg_file_with_its_size_and_md5():
    md5 = "0" * 31 + "a"
    body = (f"100 {md5} http://data.gdeltproject.org/gdeltv2/20240315043000.export.CSV.zip\n"
            f"200 {md5} http://data.gdeltproject.org/gdeltv2/20240315043000.mentions.CSV.zip\n"
            f"300 {md5} http://data.gdeltproject.org/gdeltv2/20240315043000.gkg.csv.zip\n").encode()
    assert read_lastupdate(body) == {"20240315043000.gkg.csv.zip": (300, md5)}
    for bad in (b"", b"300 nothex http://data.gdeltproject.org/gdeltv2/20240315043000.gkg.csv.zip\n",
                b"300 " + md5.encode() + b" http://elsewhere.example/20240315043000.gkg.csv.zip\n", b"just text\n",
                f"100 {md5} http://data.gdeltproject.org/gdeltv2/20240315043000.export.CSV.zip\n".encode()):
        with pytest.raises(GkgFileError):
            read_lastupdate(bad)


def test_a_file_is_used_whole_or_not_at_all(env):
    good = gkg_row(*ORDER)
    short = good.rsplit("\t", 1)[0]
    bad_files = {
        "two members": gkg_zip([good], extra="readme.txt"),
        "wrong member": gkg_zip([good], member="other.csv"),
        "26 fields": gkg_zip([good, short]),
        "other slot": gkg_zip([good, gkg_row("https://x.example.in/a", "A headline", slot=SLOT + timedelta(minutes=15))]),
        "not zip": b"PK not really a zip",
        "not utf-8": raw_zip("20240315043000.gkg.csv", b"\xff\xfe" + good.encode()),
        "empty": gkg_zip([]),
    }
    for why, data in bad_files.items():
        with pytest.raises(GkgFileError):
            load_gkg(env, name(), data, READ)
        assert count(env, "gk_files") == 0, why
    with pytest.raises(GkgFileError, match="more than"):
        load_gkg(env, name(), b"0" * 60_000_001, READ)
    assert count(env, "gk_files") == count(env, "gk_articles") == count(env, "gk_problems") == 0


def test_only_india_relevant_rows_are_stored_and_the_raw_file_is_not_kept(env):
    rows = [gkg_row(*ORDER, site="news.example.in", places=US_PLACE),                       # Indian outlet
            gkg_row("https://world.example.com/asia/mumbai-port-reopens", "Mumbai port reopens after storm",
                    site="world.example.com"),                                                 # located in India
            gkg_row("https://world.example.com/tech/tata-consultancy-services-wins-deal",
                    "Tata Consultancy Services wins bank deal in Texas", site="world.example.com",
                    places=US_PLACE),                                                         # declared name
            gkg_row("https://world.example.com/us/texas-rain", "Texas braces for heavy rain", site="world.example.com",
                    places=US_PLACE, orgs="reliance industries")]                              # none of these
    data = gkg_zip(rows)
    report = load_gkg(env, name(), data, READ)
    assert (report["rows"], report["kept"], report["refused"]) == (4, 3, 0)
    flags = env.execute("SELECT india_located, indian_outlet, names_declared FROM gk_articles ORDER BY article_id").fetchall()
    assert flags == [(0, 1, 1), (1, 0, 0), (0, 0, 1)]
    md5, sha, size = env.execute("SELECT md5, sha256, size_bytes FROM gk_files").fetchone()
    assert (md5, sha, size) == (hashlib.md5(data).hexdigest(), hashlib.sha256(data).hexdigest(), len(data))
    assert env.execute("SELECT COUNT(*) FROM raw_artifacts WHERE source_id = 'gdelt_gkg'").fetchone()[0] == 0


def test_rows_without_a_link_headline_or_tone_are_refused_and_recorded(env):
    rows = [gkg_row(*ORDER),
            gkg_row("https://news.example.in/a", None),                                 # no PAGE_TITLE
            gkg_row("https://news.example.in/b", "&#xA0; "),                            # a title of nothing
            gkg_row("https://news.example.in/c", "A headline here", collection="2"),    # not the web
            gkg_row("news.example.in/d", "A headline there"),                           # not a link
            gkg_row("https://news.example.in/e", "Another headline", tone="1.2,3")]     # 2 tone values, not 7
    report = load_gkg(env, name(), gkg_zip(rows), READ)
    assert (report["kept"], report["refused"]) == (1, 5)
    assert count(env, "gk_problems") == 5 and all(p.startswith("row_refused") for p in report["problems"])


def test_the_file_must_match_gdelts_md5_when_listed(env):
    data = gkg_zip([gkg_row(*ORDER)])
    with pytest.raises(GkgFileError, match="md5"):
        load_gkg(env, name(), data, READ, md5_listed="f" * 32)
    assert count(env, "gk_files") == 0
    assert load_gkg(env, name(), data, READ, md5_listed=hashlib.md5(data).hexdigest())["md5_checked"]


def test_a_file_read_twice_stores_nothing_new_and_other_bytes_under_its_name_are_refused(env):
    data = gkg_zip([gkg_row(*ORDER)])
    load_gkg(env, name(), data, READ)
    assert "already stored" in load_gkg(env, name(), data, READ + timedelta(hours=1))["note"]
    with pytest.raises(GkgFileError, match="other bytes"):
        load_gkg(env, name(), gkg_zip([gkg_row(*ORDER), gkg_row("https://x.example.in/z", "Some other news")]), READ)
    assert count(env, "gk_files") == 1 and count(env, "gk_articles") == 1


def test_a_link_is_stored_once_and_a_changed_headline_is_a_recorded_conflict(env):
    later = SLOT + timedelta(minutes=15)
    load_gkg(env, name(), gkg_zip([gkg_row(*ORDER)]), READ)
    again = load_gkg(env, name(later), gkg_zip([gkg_row(*ORDER, slot=later)], slot=later), READ)
    assert (again["kept"], again["already_present"], again["refused"]) == (0, 1, 0)
    slot = later + timedelta(minutes=15)
    changed = load_gkg(env, name(slot), gkg_zip([gkg_row(ORDER[0], "Reliance Industries order cancelled", slot=slot)],
                                                slot=slot), READ)
    assert changed["refused"] == 1 and "article_conflict" in changed["problems"][0]
    assert env.execute("SELECT title FROM gk_articles").fetchall() == [(ORDER[1],)]


def test_availability_is_fifteen_minutes_after_gdelts_slot_or_our_retrieval_if_earlier(env):
    load_gkg(env, name(), gkg_zip([gkg_row(*ORDER, stated="20240315040000")]), READ)
    seen, available, stated = env.execute("SELECT seen_at, available_at, stated_published FROM gk_articles").fetchone()
    assert (seen, available, stated) == (SLOT.isoformat(), (SLOT + timedelta(minutes=15)).isoformat(), "20240315040000")
    slot = SLOT + timedelta(minutes=15)
    early = slot + timedelta(minutes=5)
    load_gkg(env, name(slot), gkg_zip([gkg_row("https://x.example.in/q", "Quick news item here", slot=slot)], slot=slot),
             early)
    assert env.execute("SELECT available_at FROM gk_articles WHERE url LIKE '%/q'").fetchone()[0] == early.isoformat()
    with pytest.raises(GkgFileError, match="before its own slot"):
        load_gkg(env, name(SLOT + timedelta(hours=1)), gkg_zip([gkg_row(*ORDER)], slot=SLOT + timedelta(hours=1)), READ - timedelta(hours=2))


def test_gkg_tables_are_append_only(env):
    load_gkg(env, name(), gkg_zip([gkg_row(*ORDER), gkg_row("https://news.example.in/untitled", None)]), READ)
    for sql in ("UPDATE gk_files SET rows_kept = 0", "DELETE FROM gk_files", "UPDATE gk_articles SET title = 'x'",
                "DELETE FROM gk_articles", "DELETE FROM gk_extractions", "UPDATE gk_extraction_runs SET rule = 'x'",
                "DELETE FROM gk_problems", "UPDATE gk_problems SET kind = 'x'", "UPDATE gk_extractions SET role = 'x'",
                "DELETE FROM gk_extraction_runs"):
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            env.execute(sql)


def test_headlines_are_stored_verbatim_and_compared_with_entities_decoded(env):
    title = "Reliance Industries &amp; partners bag &#x20B9;5,000 crore order"
    load_gkg(env, name(), gkg_zip([gkg_row(ORDER[0], title)]), READ)
    assert env.execute("SELECT title FROM gk_articles").fetchone()[0] == title
    assert plain(title) == "Reliance Industries & partners bag " + chr(0x20B9) + "5,000 crore order"
    [story] = stories(env, DECIDE, RELIANCE)
    assert story["headline"] == plain(title) and story["role"] == "subject"


# ---- who a headline is about (rule nw-entity-1) ----------------------------------------------------------

def test_a_company_is_the_subject_only_when_named_in_the_headline_and_the_link(env):
    rows = [gkg_row(*ORDER),
            gkg_row("https://news.example.in/markets/order-book-update/2.html",
                    "Reliance Industries order book grows on new energy contracts"),             # headline only
            gkg_row("https://news.example.in/markets/ril-tcs-results/3.html",
                    "Reliance Industries and Tata Consultancy Services report results today"),   # two companies
            gkg_row("https://news.example.in/policy/power-tariff-order/4.html",
                    "State regulator issues power tariff order", orgs="reliance industries")]   # body only
    load_gkg(env, name(), gkg_zip(rows), READ)
    roles = env.execute("SELECT a.article_id, x.isin, x.role, x.extraction_confidence FROM gk_extractions x"
                        " JOIN gk_articles a USING (article_id) ORDER BY a.article_id, x.isin").fetchall()
    assert roles == [(1, RELIANCE, "subject", "name_in_headline_and_link"),
                     (2, RELIANCE, "mentioned", "name_in_headline_only"),
                     (3, RELIANCE, "mentioned", "several_companies_named"),
                     (3, TCS, "mentioned", "several_companies_named"),
                     (4, None, "unassigned", "no_name_found")]   # an organisation in the body is never read


def test_changed_news_names_start_a_new_reading_and_until_then_stories_say_so(env, tmp_path):
    load_gkg(env, name(), gkg_zip([gkg_row(*ORDER)]), READ)
    (tmp_path / "names2.yaml").write_text(NAMES.replace("[Reliance Industries, RIL]", "[Reliance Industries, RIL,"
                                                        " Reliance Inds]"), encoding="utf-8")
    sync_news_names(env, tmp_path / "names2.yaml", today="2024-03-16")
    with pytest.raises(GkgNotReadError):
        stories(env, DECIDE, RELIANCE)
    bundle = gather(env, DECIDE, CURRENT, RELIANCE)
    assert any(g.nature == GapNature.DEGRADED and g.component == "GKG headlines" for g in bundle.gaps)
    extract(env)
    assert count(env, "gk_extraction_runs") == 2 and len(stories(env, DECIDE, RELIANCE)) == 1


# ---- one story, one vote (rule nw-dedup-1) -------------------------------------------------------------

def test_copies_of_one_headline_are_one_story_within_72_hours(env):
    later, much_later = SLOT + timedelta(hours=5), SLOT + timedelta(hours=80)
    copy = ("https://other.example.in/biz/reliance-industries-bags-rs-5000-crore-order", ORDER[1])
    load_gkg(env, name(), gkg_zip([gkg_row(*ORDER)]), READ)
    load_gkg(env, name(later), gkg_zip([gkg_row(*copy, site="other.example.in", slot=later)], slot=later),
             later + timedelta(hours=2))
    [story] = stories(env, DECIDE, RELIANCE)
    assert len(story["copies"]) == 2 and story["sites"] == ["news.example.in", "other.example.in"]
    assert story["published_at"] == (SLOT + timedelta(minutes=15)).isoformat()
    third = ("https://third.example.in/reliance-industries-bags-rs-5000-crore-order", ORDER[1])
    load_gkg(env, name(much_later), gkg_zip([gkg_row(*third, site="third.example.in", slot=much_later)],
                                            slot=much_later), much_later + timedelta(hours=1))
    assert [len(s["copies"]) for s in stories(env, DECIDE + timedelta(days=5), RELIANCE)] == [2, 1]


def test_a_story_is_known_only_from_its_availability_under_each_claim(env):
    late_read = SLOT + timedelta(days=2)
    load_gkg(env, name(), gkg_zip([gkg_row(*ORDER)]), late_read)
    between = SLOT + timedelta(days=1)
    assert stories(env, between, RELIANCE, CURRENT) == []                  # we had not read it yet
    assert len(stories(env, between, RELIANCE, REPLAY)) == 1               # GDELT had published it
    assert stories(env, SLOT + timedelta(minutes=10), RELIANCE, REPLAY) == []


# ---- the rules: price echo, filing direction, eligibility (se-echo-1, an-direction-1, se-eligible-1) -------

@pytest.mark.parametrize("headline", [
    "Sensex jumps 2,009 points, Nifty hits 3-month high",
    "Sensex opens in red day after 2,000-point spike; rout in global markets",
    "Stock to buy today: Coromandel International (&#x20B9;1,907.45)",
    "PI Industries hits 52 week low, stock in downtrend for period up to five years; what's next?",
    "Day Trading Guide for November 6, 2026: Intraday supports, resistances for Nifty50 stocks",
    "LIC shares fall 4% as Q2 VNB misses estimates; APE growth remains weak",
    "Groww Stock Slumps Nearly 7% After Nine-Day Rally",
    "3M India profit falls on weaker rupee and rising input costs, shares tumble",
    "Airtel gains 3%, nears record high as ARPU growth drives Q2 revenue by 17%",     # found by the trial on real files
    "Titan surges 2.5% on strong Q2 results; brokerages divided on upside",           # found by the trial on real files
    "Top gainers and losers today: Reliance Industries, TCS lead",
])
def test_headlines_restating_a_price_move_are_price_echo(headline):
    assert price_echo(plain(headline))


@pytest.mark.parametrize("headline", [
    "Godrej Agrovet Q2 profit jumps 22% on strong animal nutrition, oil palm sales",
    "Premier Energies Q2 net profit rises 31% to Rs 462.4 crore",
    "Automobile retail sales fall 24% in October on high base effect a year ago",
    "IGX gas trading volumes surge 326% YoY to 13.28 million MMBtu in October",
    "Healthcare Global Enterprises Q2 net profit declines 55% to Rs 9.25 cr",
    "Reliance Industries bags Rs 5,000 crore order from state power utility",
    "Tata Consultancy Services informs stock exchange about new US contract",
])
def test_business_news_is_not_price_echo(headline):
    assert price_echo(headline) == []


def test_a_filing_has_a_direction_only_when_its_subject_has_one():
    assert filing_direction({"Bagging/Receiving of orders/contracts"}) == POSITIVE
    assert filing_direction({"Resignation of Statutory Auditor"}) == NEGATIVE
    assert filing_direction({"Defaults on Payment of Interest/Principal"}) == NEGATIVE
    for unknown in ("Credit Rating", "Credit Rating- Revision", "Change in Auditors", "Awarding of order(s)/contract(s)",
                    "Action(s) taken or orders passed", "Outcome of Board Meeting", "Product launch", "Something new"):
        assert filing_direction({unknown}) == UNKNOWN, unknown
    assert filing_direction({"Spurt in Volume"}) == PRICE_ECHO
    assert filing_direction({"Capacity addition", "Disruption of Operations"}) == CONFLICTING   # never netted
    assert filing_direction({"Credit Rating", "Bagging/Receiving of orders/contracts"}) == POSITIVE
    assert filing_direction({"Price movement", "Capacity addition"}) == POSITIVE


def test_a_story_is_sentiment_eligible_only_as_the_subject_and_never_as_price_echo():
    story = {"headline": ORDER[1], "role": "subject", "extraction_confidence": "name_in_headline_and_link"}
    assert eligibility(story)[0]
    assert not eligibility({**story, "role": "mentioned", "extraction_confidence": "name_in_headline_only"})[0]
    assert not eligibility({**story, "headline": "Reliance Industries shares jump 4% on order win"})[0]


# ---- the liquidity gate (se-liquidity-1, 4B.2 rule 1) ----------------------------------------------------

def test_sentiment_is_admitted_only_above_rs_25_crore_from_at_least_5_sessions(env, tmp_path):
    trade(env, tmp_path, WEEK[:4], [("RELIANCE", RELIANCE, "1000.00", "250000"), ("TCS", TCS, "4000.00", "10000")])
    gate = liquidity(env, RELIANCE, DECIDE, CURRENT)
    assert (gate["admitted"], gate["sessions"]) == (False, 4) and "at least 5" in gate["reason"]
    trade(env, tmp_path, WEEK[4:], [("RELIANCE", RELIANCE, "1000.00", "250000"), ("TCS", TCS, "4000.00", "10000")])
    gate = liquidity(env, RELIANCE, DECIDE, CURRENT)
    assert (gate["admitted"], gate["sessions"], gate["median_crore"]) == (True, 5, 25.0)   # exactly at the line
    tcs = liquidity(env, TCS, DECIDE, CURRENT)
    assert (tcs["admitted"], tcs["median_crore"]) == (False, 4.0) and "not down-weighted" in tcs["reason"]
    assert not liquidity(env, RELIANCE, datetime(2024, 3, 14, 6, 0, tzinfo=UTC), CURRENT)["admitted"]   # 3 known then
    stale = liquidity(env, RELIANCE, datetime(2024, 7, 10, 6, 0, tzinfo=UTC), CURRENT)   # 11-Mar is 121 days back
    assert (stale["admitted"], stale["sessions"]) == (False, 4) and "last 120 days" in stale["reason"]
    replay = liquidity(env, RELIANCE, DECIDE, REPLAY)
    assert not replay["admitted"] and replay["withheld"] == 5 and "withheld" in replay["reason"]


# ---- public sentiment in the hub ---------------------------------------------------------------------------

@pytest.fixture
def market(env, tmp_path):
    trade(env, tmp_path, WEEK, [("RELIANCE", RELIANCE, "2940.25", "1000000"), ("TCS", TCS, "4000.00", "10000")])
    rows = [filing("2024-03-12 10:00:00", "Bagging/Receiving of orders/contracts", "OrderWinMarch2024.pdf",
                   symbol="RELIANCE", company="Reliance Industries Limited"),
            filing("2024-03-13 11:00:00", "Credit Rating", "RatingLetterMarch2024.pdf", symbol="RELIANCE",
                   company="Reliance Industries Limited"),
            filing("2024-03-14 12:00:00", "Price movement", "ClarificationPriceMove.pdf", symbol="RELIANCE",
                   company="Reliance Industries Limited")]
    (tmp_path / "CF-AN-equities-1.csv").write_text(listing(*rows), encoding="utf-8")
    load_announcements(env, tmp_path / "CF-AN-equities-1.csv", "2024-03-15T20:00:00+05:30", raw_dir=tmp_path / "raw")
    news = [gkg_row(*ORDER),
            gkg_row("https://news.example.in/markets/reliance-industries-shares-jump-4/5.html",
                    "Reliance Industries shares jump 4% on order win"),
            gkg_row("https://news.example.in/markets/order-book-update/6.html",
                    "Reliance Industries order book grows on new energy contracts"),
            gkg_row("https://news.example.in/tech/tata-consultancy-services-signs-deal/7.html",
                    "Tata Consultancy Services signs cloud deal with European lender")]
    load_gkg(env, name(), gkg_zip(news), READ)
    return env


def test_public_sentiment_has_an_adapter_now():
    assert Domain.PUBLIC_SENTIMENT not in NOT_BUILT


def test_above_the_band_the_hub_gives_filing_directions_and_eligible_headlines_unscored(market):
    bundle = gather(market, DECIDE, CURRENT, RELIANCE)
    found = {(e.kind, e.value) for e in bundle.of(Domain.PUBLIC_SENTIMENT)}
    assert found == {("filing_direction", POSITIVE), ("headline_story", ORDER[1])}
    assert all(e.attribution == Attribution.DIRECT and e.subject == RELIANCE for e in bundle.of(Domain.PUBLIC_SENTIMENT))
    headline = next(e for e in bundle.of(Domain.PUBLIC_SENTIMENT) if e.kind == "headline_story")
    assert headline.extraction_confidence == ExtractionConfidence.NAME_IN_HEADLINE_AND_LINK
    assert "not scored" in headline.details["polarity"] and "article_tone" not in headline.details   # 4B.5
    assert headline.available_at == READ.isoformat()
    news = [e for e in bundle.of(Domain.NEWS_EXTERNAL) if e.source_id == "gdelt_gkg"]
    assert len(news) == 3 and sorted(e.details["sentiment_eligible"] for e in news) == [False, False, True]
    assert all(e.details["article_tone"] == -1.5 for e in news)   # whole-article tone, given as news only
    excluded = {g.reason.split(" - ")[0]: g.count for g in bundle.gaps_of(Domain.PUBLIC_SENTIMENT)
                if g.nature == GapNature.EXCLUDED}
    assert sorted(excluded.values()) == [1, 1, 2]   # unknown rating, price-movement query, 2 headlines not eligible
    degraded = {g.component for g in bundle.gaps_of(Domain.PUBLIC_SENTIMENT) if g.nature == GapNature.DEGRADED}
    assert degraded == {"headline polarity", "sentiment features"}
    ids = [e.evidence_id for e in bundle.evidence]
    assert len(ids) == len(set(ids))


def test_below_the_band_sentiment_is_refused_while_its_news_stays_attention(market):
    bundle = gather(market, DECIDE, CURRENT, TCS)
    assert bundle.of(Domain.PUBLIC_SENTIMENT) == []
    [refused] = bundle.gaps_of(Domain.PUBLIC_SENTIMENT)
    assert refused.nature == GapNature.EXCLUDED and "Rs 4.00 crore" in refused.reason and "se-liquidity-2" in refused.reason
    [story] = [e for e in bundle.of(Domain.NEWS_EXTERNAL) if e.source_id == "gdelt_gkg"]
    assert story.details["sentiment_eligible"]   # eligible as text, refused by the band


def test_no_filing_and_no_headline_is_a_recorded_gap_never_neutral(env, tmp_path):
    trade(env, tmp_path, WEEK, [("RELIANCE", RELIANCE, "2940.25", "1000000")])
    bundle = gather(env, DECIDE, CURRENT, RELIANCE)
    assert bundle.of(Domain.PUBLIC_SENTIMENT) == []
    missing = [g for g in bundle.gaps_of(Domain.PUBLIC_SENTIMENT) if g.nature == GapNature.MISSING]
    assert len(missing) == 1 and "never neutral" in missing[0].reason


def test_unread_gkg_slots_are_named_as_missing_never_as_no_news(market):
    bundle = gather(market, DECIDE, CURRENT, RELIANCE, start="2024-03-15", end="2024-03-15")
    [gap] = [g for g in bundle.gaps_of(Domain.NEWS_EXTERNAL) if g.component == "GKG headlines"]
    assert gap.count == 95 and "1 of 96 read" in gap.reason and gap.missing_class == MissingClass.EXTRACTION_FAILURE


def test_under_replay_sentiment_is_refused_when_prices_are_not_proven(market):
    bundle = gather(market, DECIDE, REPLAY, RELIANCE)
    assert bundle.of(Domain.PUBLIC_SENTIMENT) == []
    assert any("withheld" in g.reason for g in bundle.gaps_of(Domain.PUBLIC_SENTIMENT))
    assert [e for e in bundle.of(Domain.NEWS_EXTERNAL) if e.source_id == "gdelt_gkg"]   # GDELT's time is proof


def test_the_hub_still_only_reads(market):
    before = market.total_changes
    gather(market, DECIDE, CURRENT, RELIANCE)
    gather(market, DECIDE, REPLAY, RELIANCE)
    assert market.total_changes == before


# ---- fetching GKG files (ADR-013) -----------------------------------------------------------------------

class FakeGdelt:
    def __init__(self, files, missing=(), refuse=None, listed=None):
        self.files, self.missing, self.refuse, self.asked = files, set(missing), refuse, []
        self.listed = listed

    def __call__(self, url):
        news_fetch._check_host(url)
        self.asked.append(url)
        if url == news_fetch.GKG_LASTUPDATE:
            return 200, self.listed
        file = url.rsplit("/", 1)[1]
        if self.refuse and file == self.refuse[0]:
            return self.refuse[1], b"<html>refused</html>"
        if file in self.missing or file not in self.files:
            return 404, b""
        return 200, self.files[file]


def client(get, now):
    ticks = iter(range(0, 100000, 5))
    return news_fetch.GkgClient(get=get, sleep=lambda s: None, clock=lambda: next(ticks), now=lambda: now)


def lastupdate(newest, data=b""):
    md5 = hashlib.md5(data).hexdigest()
    return f"{len(data)} {md5} http://data.gdeltproject.org/gdeltv2/{name(newest)}\n".encode()


def test_the_fetcher_reaches_only_lastupdate_and_gkg_files_on_gdelts_data_host():
    for url in ("https://data.gdeltproject.org/gdeltv2/masterfilelist.txt",
                "https://data.gdeltproject.org/gdeltv2/20240315043000.export.CSV.zip",
                "https://data.gdeltproject.org/gdeltv2/20240315043000.gkg.csv.zip?x=1",
                "https://data.gdeltproject.org/gkg/20240315043000.gkg.csv.zip",
                "http://data.gdeltproject.org/gdeltv2/20240315043000.gkg.csv.zip",
                "https://data.gdeltproject.org:8443/gdeltv2/lastupdate.txt"):
        with pytest.raises(news_fetch.FetchError, match="not an allowed"):
            news_fetch.http_get(url)
    assert "data.gdeltproject.org" in news_fetch.ALLOWED_HOSTS


def test_fetch_reads_due_slots_oldest_first_and_a_404_is_not_yet(env):
    now = SLOT + timedelta(hours=2)          # 06:30 UTC: slots up to 05:15 are at least 75 minutes old
    slots = [SLOT + timedelta(minutes=15 * i) for i in range(4)]
    files = {name(s): gkg_zip([gkg_row(f"https://news.example.in/{i}", f"News item number {i} here", slot=s)], slot=s)
             for i, s in enumerate(slots)}
    get = FakeGdelt(files, missing={name(slots[2])}, listed=lastupdate(slots[3], files[name(slots[3])]))
    report = news_fetch.fetch_gkg(env, client(get, now), start=SLOT)
    assert get.asked[0] == news_fetch.GKG_LASTUPDATE
    assert [u.rsplit("/", 1)[1] for u in get.asked[1:]] == [name(s) for s in slots]   # 05:30 is too young
    assert (report["read"], report["not_yet"], report["refused"]) == (3, [name(slots[2])], [])
    assert env.execute("SELECT md5_listed IS NOT NULL FROM gk_files ORDER BY slot_at").fetchall() == [(0,), (0,), (1,)]
    get2 = FakeGdelt(files, listed=lastupdate(slots[3]))
    again = news_fetch.fetch_gkg(env, client(get2, now + timedelta(minutes=5)), start=SLOT)
    assert [u.rsplit("/", 1)[1] for u in get2.asked[1:]] == [name(slots[2])] and again["read"] == 1


def test_slots_younger_than_75_minutes_are_never_asked_for(env):
    now = SLOT + timedelta(minutes=74)
    assert news_fetch.gkg_slots(env, now, start=SLOT) == []
    assert news_fetch.gkg_slots(env, now + timedelta(minutes=1), start=SLOT) == [SLOT]
    assert news_fetch.gkg_slots(env, now + timedelta(hours=3), start=SLOT, newest=SLOT + timedelta(minutes=15)) == [
        SLOT, SLOT + timedelta(minutes=15)]


def test_the_first_run_reads_the_last_day_and_later_runs_fill_unread_slots_of_the_last_week(env):
    now = SLOT + timedelta(hours=26)
    due = news_fetch.gkg_slots(env, now)
    assert due[0] == SLOT + timedelta(hours=2) and due[-1] == now - timedelta(minutes=75) and len(due) == 92
    load_gkg(env, name(), gkg_zip([gkg_row(*ORDER)]), READ)
    due = news_fetch.gkg_slots(env, now)
    assert due[0] == SLOT + timedelta(minutes=15)   # from the first slot read, without it
    long_after = SLOT + timedelta(days=30)
    assert news_fetch.gkg_slots(env, long_after)[0] == long_after - news_fetch.GKG_LOOKBACK   # no further than a week


def test_a_refusal_stops_the_run_and_a_refused_file_stores_nothing_while_the_run_goes_on(env):
    now = SLOT + timedelta(hours=2)
    slots = [SLOT + timedelta(minutes=15 * i) for i in range(3)]
    files = {name(s): gkg_zip([gkg_row(f"https://news.example.in/{i}", f"News item number {i} here", slot=s)], slot=s)
             for i, s in enumerate(slots)}
    files[name(slots[0])] = b"not a zip"
    listed = lastupdate(slots[2], files[name(slots[2])])
    report = news_fetch.fetch_gkg(env, client(FakeGdelt(files, listed=listed), now), start=SLOT, max_files=3)
    assert report["read"] == 2 and len(report["refused"]) == 1 and count(env, "gk_files") == 2
    get = FakeGdelt(files, refuse=(name(slots[0]), 503), listed=lastupdate(slots[2]))
    c2 = client(get, now)
    with pytest.raises(news_fetch.FetchError, match="503"):
        news_fetch.fetch_gkg(env, c2, start=SLOT)
    with pytest.raises(news_fetch.RateLimited):
        c2.fetch(news_fetch.GKG_LASTUPDATE)   # nothing more is asked in this run
    get429 = FakeGdelt(files, refuse=(name(slots[0]), 429), listed=lastupdate(slots[2]))
    with pytest.raises(news_fetch.RateLimited):
        news_fetch.fetch_gkg(env, client(get429, now), start=SLOT)


# ---- registry, schema and the code's own rules -----------------------------------------------------------

def test_gkg_is_registered_with_gdelts_licence(env):
    source = get_source(env, "gdelt_gkg")
    assert "cite the GDELT Project" in source["license"] and "ADR-013" in source["license"]


def test_schema_21_migrates_and_rolls_back_cleanly():
    c = connect(":memory:")
    assert migrate(c) >= 21
    rollback(c, 20)
    tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert current_version(c) == 20 and not {t for t in tables if t.startswith("gk_")}
    assert migrate(c) >= 21


def test_article_tone_never_reaches_the_sentiment_rules():
    text = (PROJECT_ROOT / "src" / "knowledge" / "sentiment.py").read_text(encoding="utf-8")
    assert "tone" not in text


def test_the_acceptance_record_claims_no_polarity_and_no_tone_as_sentiment():
    record = load_acceptance_records()["STAGE_12A_acceptance.yaml"]
    assert record["not_claimed"]["headline polarity (FinBERT scorer, Stage 12B)"] is False
    assert record["negative_assertions"]["GDELT tone used as company sentiment"] is False
    assert all(value is False for value in record["negative_assertions"].values())


def test_new_stage_12a_files_are_plain_ascii():
    for path in ("src/ingestion/gdelt_gkg.py", "src/knowledge/sentiment.py", "tests/test_stage12a_sentiment.py",
                 "migrations/0021_gkg_headlines.up.sql", "migrations/0021_gkg_headlines.down.sql",
                 "stages/STAGE_12A_acceptance.yaml", "docs/decisions/ADR-013-gdelt-gkg-and-company-sentiment.md"):
        (PROJECT_ROOT / path).read_bytes().decode("ascii")
