"""Stage 6a tests: NSE daily candles from Zerodha's Kite Connect (architecture 40B step 6a, 4C, 5B; ADR-014).

Kite's answers are made up in the shapes of Kite's documentation (read 22-Nov-2026): a CSV instrument list without
ISIN, day candles [timestamp +0530, open, high, low, close, volume], and a login answer that carries the account
holder's name and email - which must never be stored. No network is used: a fake Kite answers.
"""
import gzip
import hashlib
import json
import sqlite3
import urllib.parse
from datetime import datetime, timedelta, timezone

import pytest

from core.database import connect, current_version, migrate, rollback
from core.status import load_acceptance_records
from core.config import PROJECT_ROOT
from ingestion import news_fetch
from ingestion.kite_prices import (MAX_DAYS, KiteResponseError, load_fetch, map_instruments, plan_requests, purge,
                                   read_candles, read_instruments, readjusted, series, start_run)
from ingestion.source_registry import get_source, sync_sources
from knowledge.evidence import Domain, GapNature
from knowledge.hub import gather
from knowledge.sentiment import LIQUIDITY_RULE, liquidity
from provenance.availability import PitClaim
from test_stage07a_market_adapters import EQUITY_LIST, RELIANCE, TCS
from test_stage12a_sentiment import trade
from universe.entities import add_alias
from universe.equity_list import load_equity_list

UTC = timezone.utc
CURRENT, REPLAY = PitClaim.CURRENT_DECISION, PitClaim.HISTORICAL_REPLAY
KEY, SECRET, REQUEST, ACCESS = "testkey123", "testsecret456", "reqTOKEN789", "accessTOKEN321"
HEADER = "instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,instrument_type,segment,exchange"
WEEK = ["2024-03-11", "2024-03-12", "2024-03-13", "2024-03-14", "2024-03-15"]
RUN_AT = datetime(2024, 3, 15, 13, 0, tzinfo=UTC)      # 18:30 India time: 15-Mar's candle is final
DECIDE = datetime(2024, 3, 20, 6, 0, tzinfo=UTC)


def instruments(*extra, gz=False):
    rows = [HEADER, "738561,2885,RELIANCE,RELIANCE INDUSTRIES,0,,,0.05,1,EQ,NSE,NSE",
            "2953217,11536,TCS,TATA CONSULTANCY SERV LT,0,,,0.05,1,EQ,NSE,NSE",
            "1111,22,UNKNOWNCO,SOME COMPANY,0,,,0.05,1,EQ,NSE,NSE",
            "256265,1,NIFTY 50,NIFTY 50,0,,,0,0,EQ,INDICES,NSE",
            "5720322,22345,NIFTY24MARFUT,,0,2024-03-28,,0.05,50,FUT,NFO-FUT,NFO", *extra]
    body = ("\n".join(rows) + "\n").encode()
    return gzip.compress(body) if gz else body


def candle(day, close, volume=1_000_000, spread=10.0):
    return [f"{day}T00:00:00+0530", close, close + spread, close - spread, close, volume]


def answer(*candles):
    return json.dumps({"status": "success", "data": {"candles": list(candles)}}).encode()


@pytest.fixture
def env(tmp_path):
    c = connect(":memory:")
    migrate(c)
    sync_sources(c)
    (tmp_path / "EQUITY_L.csv").write_text(EQUITY_LIST, encoding="utf-8")
    load_equity_list(c, tmp_path / "EQUITY_L.csv", "2024-03-01T19:00:00+05:30", raw_dir=tmp_path / "raw")
    yield c
    c.close()


def run(c, token="738561"):
    return start_run(c, 3, [(RELIANCE, "RELIANCE", int(token))], [], b"list")


def store(c, days_closes, retrieved, run_id=None, reason="backfill", first="2024-03-01", last="2024-03-15"):
    run_id = run_id or run(c)
    body = answer(*[candle(d, p) for d, p in days_closes])
    return load_fetch(c, run_id, RELIANCE, "RELIANCE", 738561, first, last, body, retrieved, reason)


# ---- the instrument list ---------------------------------------------------------------------------------

def test_only_nse_eq_instruments_are_read_plain_or_gzipped():
    expected = [("RELIANCE", 738561), ("TCS", 2953217), ("UNKNOWNCO", 1111)]
    assert read_instruments(instruments()) == expected == read_instruments(instruments(gz=True))


@pytest.mark.parametrize("body", [
    b"symbol,token\nRELIANCE,1\n",                                                    # header changed
    (HEADER.replace("tradingsymbol,name", "name,tradingsymbol")
     + "\n738561,2885,RELIANCE INDUSTRIES,RELIANCE,0,,,0.05,1,EQ,NSE,NSE\n").encode(),   # same columns, new order
    (HEADER + "\nx1,1,RELIANCE,R,0,,,0.05,1,EQ,NSE,NSE\n").encode(),                  # token not a number
    (HEADER + "\n1,1,RELIANCE,R,0,,,0.05,1,EQ,NSE,NSE\n2,2,RELIANCE,R,0,,,0.05,1,EQ,NSE,NSE\n").encode(),   # twice
    (HEADER + "\n5720322,22345,NIFTY24MARFUT,,0,2024-03-28,,0.05,50,FUT,NFO-FUT,NFO\n").encode(),   # no NSE EQ
    (HEADER + "\n1,1,RELIANCE,R,0\n").encode(),                                        # short row
    b"\x1f\x8b not gzip",
])
def test_an_unreadable_instrument_list_is_refused_whole(body):
    with pytest.raises(KiteResponseError):
        read_instruments(body)


def test_a_kite_symbol_reaches_a_company_only_through_its_nse_symbol(env):
    mapped, unmapped = map_instruments(env, read_instruments(instruments()), "2024-03-15")
    assert mapped == sorted([(RELIANCE, "RELIANCE", 738561), (TCS, "TCS", 2953217)])
    assert [s for s, _ in unmapped] == ["UNKNOWNCO"]
    add_alias(env, RELIANCE, "nse_symbol", "RELIND", "2000-01-01")   # a second Kite symbol for the same company
    mapped, unmapped = map_instruments(env, read_instruments(instruments("9,9,RELIND,R,0,,,0.05,1,EQ,NSE,NSE")),
                                       "2024-03-15")
    assert [m[1] for m in mapped] == ["TCS"] and {"RELIANCE", "RELIND"} <= {s for s, _ in unmapped}


def test_the_trade_for_trade_series_of_a_company_reaches_it_and_nothing_else_does(env):
    # found live on 22-Nov-2026: 206 registry companies trade as -BE or -BZ (FELDVR-BZ, RTSPOWR-BE ...)
    listing = (HEADER + "\n11,1,TCS-BE,TCS,0,,,0.05,1,EQ,NSE,NSE\n12,2,RELIANCE-BZ,R,0,,,0.05,1,EQ,NSE,NSE\n"
               "13,3,RELIANCE-D1,R,0,,,0.05,1,EQ,NSE,NSE\n14,4,TCS-SM,T,0,,,0.05,1,EQ,NSE,NSE\n").encode()
    mapped, unmapped = map_instruments(env, read_instruments(listing), "2024-03-15")
    assert mapped == sorted([(RELIANCE, "RELIANCE-BZ", 12), (TCS, "TCS-BE", 11)])
    assert sorted(s for s, _ in unmapped) == ["RELIANCE-D1", "TCS-SM"]
    both = (HEADER + "\n11,1,TCS-BE,TCS,0,,,0.05,1,EQ,NSE,NSE\n15,5,TCS,TCS,0,,,0.05,1,EQ,NSE,NSE\n").encode()
    mapped, unmapped = map_instruments(env, read_instruments(both), "2024-03-15")
    assert mapped == [] and sorted(s for s, _ in unmapped) == ["TCS", "TCS-BE"]   # two series at once: refused


# ---- candles: used whole or not at all -------------------------------------------------------------------

def test_day_candles_are_read_with_their_india_date():
    body = answer(candle("2024-03-14", 2940.25), candle("2024-03-15", 2950.0, volume=1.0e6))
    assert read_candles(body, "2024-03-01", "2024-03-15") == ([
        ("2024-03-14", 2940.25, 2950.25, 2930.25, 2940.25, 1000000),
        ("2024-03-15", 2950.0, 2960.0, 2940.0, 2950.0, 1000000)], [])


def test_odd_old_candles_are_set_aside_one_by_one_and_never_chosen_between(env):
    # found live on 22-Nov-2026 in SME-period history: SVLL 26-Jun-2018 stamped 10:00; AHLADA 19-Oct-2018 twice
    odd = ["2024-03-12T10:00:00+0530", 100, 110, 90, 100, 5]
    body = answer(candle("2024-03-11", 100), odd, candle("2024-03-13", 100), candle("2024-03-13", 101),
                  candle("2024-03-14", 100))
    kept, aside = read_candles(body, "2024-03-01", "2024-03-15")
    assert [c[0] for c in kept] == ["2024-03-11", "2024-03-14"]
    assert aside == [("2024-03-12", "time_not_midnight", aside[0][2]), ("2024-03-13", "duplicate_day", aside[1][2])]
    fetch_id, n, set_aside = load_fetch(env, run(env), RELIANCE, "RELIANCE", 738561, "2024-03-01", "2024-03-15", body,
                                        RUN_AT, "backfill")
    assert (n, set_aside) == (2, 2)
    assert env.execute("SELECT trade_date, kind FROM kt_problems ORDER BY trade_date").fetchall() == [
        ("2024-03-12", "time_not_midnight"), ("2024-03-13", "duplicate_day")]


@pytest.mark.parametrize("bad", [
    json.dumps({"status": "error", "message": "Invalid token", "error_type": "TokenException"}),
    json.dumps({"status": "success", "data": {}}),
    json.dumps({"status": "success", "data": {"candles": [["2024-03-14T00:00:00+0000", 1, 2, 1, 1, 5]]}}),  # not IST
    json.dumps({"status": "success", "data": {"candles": [["2024-03-14 00:00:00", 1, 2, 1, 1, 5]]}}),       # no zone
    json.dumps({"status": "success", "data": {"candles": [["2024-02-01T00:00:00+0530", 1, 2, 1, 1, 5]]}}),  # outside
    json.dumps({"status": "success", "data": {"candles": [candle("2024-03-14", 100), candle("2024-03-13", 100)]}}),
    json.dumps({"status": "success", "data": {"candles": [["2024-03-14T00:00:00+0530", 10, 9, 8, 10, 5]]}}),  # high<close
    json.dumps({"status": "success", "data": {"candles": [["2024-03-14T00:00:00+0530", 0, 1, 0, 1, 5]]}}),  # zero price
    json.dumps({"status": "success", "data": {"candles": [["2024-03-14T00:00:00+0530", 1, 2, 1, 1, -5]]}}),  # volume<0
    json.dumps({"status": "success", "data": {"candles": [["2024-03-14T00:00:00+0530", 1, 2, 1, 1, 5.5]]}}),
    json.dumps({"status": "success", "data": {"candles": [["2024-03-14T00:00:00+0530", 1, 2, 1, 1, True]]}}),
    json.dumps({"status": "success", "data": {"candles": [["2024-03-14T00:00:00+0530", 1, 2, 1, "1", 5]]}}),
    "not json",
])
def test_an_unusable_candle_answer_is_refused_whole(bad):
    with pytest.raises(KiteResponseError):
        read_candles(bad.encode(), "2024-03-01", "2024-03-15")


def test_history_is_asked_for_in_chunks_then_from_ten_days_before_the_last_stored_day(env):
    plan = plan_requests(env, RELIANCE, "2024-03-15", "2018-01-01")
    assert plan[0] == ("2018-01-01", "2023-06-23", "backfill") and plan[-1][1] == "2024-03-15"
    assert all((datetime.fromisoformat(t) - datetime.fromisoformat(f)).days < MAX_DAYS for f, t, _ in plan)
    assert len(plan) == 2
    store(env, [(d, 100.0) for d in WEEK], RUN_AT)
    assert plan_requests(env, RELIANCE, "2024-03-18", "2018-01-01") == [("2024-03-05", "2024-03-18", "daily")]


# ---- vintages, availability, purge ---------------------------------------------------------------------

def test_every_fetch_is_a_vintage_and_the_newest_known_one_is_given(env):
    store(env, [(d, 100.0) for d in WEEK], RUN_AT)
    store(env, [(d, 50.0) for d in WEEK], RUN_AT + timedelta(days=2), reason="readjusted")   # after a 1:2 split
    newest, _ = series(env, RELIANCE, DECIDE, CURRENT)
    assert {d: c["close"] for d, c in newest.items()} == {d: 50.0 for d in WEEK}
    before, _ = series(env, RELIANCE, RUN_AT + timedelta(days=1), CURRENT)
    assert {c["close"] for c in before.values()} == {100.0}
    assert series(env, RELIANCE, RUN_AT - timedelta(minutes=1), CURRENT) == ({}, 0)
    assert series(env, RELIANCE, DECIDE, REPLAY) == ({}, 5)   # never public as such on the trade date


def test_a_changed_overlapping_day_means_the_vendor_readjusted(env):
    store(env, [(d, 100.0) for d in WEEK], RUN_AT)
    same = [(d, 100.0, 110.0, 90.0, 100.0, 1000000) for d in WEEK[-2:]]
    rounding = [(d, 100.004, 110.0, 90.0, 100.004, 1000000) for d in WEEK[-2:]]
    changed = [(WEEK[-1], 50.0, 55.0, 45.0, 50.0, 2000000)]
    assert not readjusted(env, RELIANCE, same) and not readjusted(env, RELIANCE, rounding)
    assert readjusted(env, RELIANCE, changed)
    assert not readjusted(env, RELIANCE, [("2024-03-18", 50.0, 55.0, 45.0, 50.0, 1)])   # a new day overlaps nothing


def test_kite_tables_are_append_only_and_purge_removes_everything_at_once(env):
    store(env, [(d, 100.0) for d in WEEK], RUN_AT)
    for sql in ("UPDATE kt_candles SET close = 1", "DELETE FROM kt_candles", "DELETE FROM kt_fetches",
                "UPDATE kt_fetches SET reason = 'daily'", "DELETE FROM kt_runs"):
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            env.execute(sql)
    env.execute("INSERT INTO kt_problems VALUES (1, '2024-03-12', 'duplicate_day', 'x')")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        env.execute("DELETE FROM kt_problems")
    version = current_version(env)
    assert purge(env) == 5
    assert env.execute("SELECT COUNT(*) FROM kt_problems").fetchone()[0] == 0
    assert [env.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("kt_runs", "kt_fetches", "kt_candles")] == [0, 0, 0]
    assert current_version(env) == version
    store(env, [(WEEK[0], 100.0)], RUN_AT)   # the tables are back, empty and append-only
    with pytest.raises(sqlite3.IntegrityError):
        env.execute("DELETE FROM kt_candles")


# ---- the fetcher: addresses, secrets, login ----------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "https://api.kite.trade/instruments",
    "https://api.kite.trade/instruments/BSE",
    "https://api.kite.trade/quote?i=NSE:INFY",
    "https://api.kite.trade/orders",
    "https://api.kite.trade/user/profile",
    "https://api.kite.trade/instruments/historical/738561/minute?from=2024-03-01",
    "https://api.kite.trade/instruments/historical/738561/day?from=a&api_key=x",
    "https://api.kite.trade/instruments/historical/738561/day?from=a&from=b",
    "https://kite.zerodha.com/connect/login?v=3&api_key=x",
    "http://api.kite.trade/session/token",
])
def test_the_fetcher_asks_kite_only_for_the_session_the_nse_list_and_daily_history(url):
    with pytest.raises(news_fetch.FetchError, match="not an allowed"):
        news_fetch.http_get(url)


def test_the_allowed_kite_addresses_pass_the_check():
    for url in (news_fetch.KITE_SESSION, news_fetch.KITE_INSTRUMENTS,
                news_fetch.kite_history_url(738561, "2024-03-01", "2024-03-15")):
        news_fetch._check_host(url)
    assert "api.kite.trade" in news_fetch.ALLOWED_HOSTS and "kite.zerodha.com" not in news_fetch.ALLOWED_HOSTS


def test_the_key_and_secret_come_only_from_the_environment_and_are_never_shown():
    assert news_fetch.kite_credentials({"KITE_API_KEY": KEY, "KITE_API_SECRET": SECRET}) == (KEY, SECRET)
    for environ in ({}, {"KITE_API_KEY": KEY}, {"KITE_API_KEY": KEY, "KITE_API_SECRET": "has space"}):
        with pytest.raises(news_fetch.FetchError) as e:
            news_fetch.kite_credentials(environ)
        assert KEY not in str(e.value) and SECRET not in str(e.value)


def test_the_request_token_is_taken_from_the_pasted_address():
    pasted = f"http://127.0.0.1:5000/kite?action=login&type=login&status=success&request_token={REQUEST}"
    assert news_fetch.kite_request_token(pasted) == REQUEST == news_fetch.kite_request_token(f"  {REQUEST} ")
    for bad in ("", "http://127.0.0.1:5000/kite?status=success", "http://127.0.0.1:5000/kite?status=failed&request_token=x1234567"):
        with pytest.raises(news_fetch.FetchError):
            news_fetch.kite_request_token(bad)


class FakeKite:
    """Answers like Kite: the login, the instrument list and day candles from a table {token: {day: close}}."""

    def __init__(self, closes, refuse=None):
        self.closes, self.refuse, self.calls = closes, refuse or {}, []

    def __call__(self, url, method="GET", headers=None, data=None):
        news_fetch._check_host(url)
        self.calls.append((url, method, dict(headers or {}), data))
        parts = urllib.parse.urlsplit(url)
        if url in self.refuse:
            return self.refuse[url]
        if parts.path == "/session/token":
            form = dict(urllib.parse.parse_qsl(data.decode()))
            if form["checksum"] != hashlib.sha256((KEY + form["request_token"] + SECRET).encode()).hexdigest():
                return 403, b'{"status": "error", "message": "Invalid checksum", "error_type": "TokenException"}'
            return 200, json.dumps({"status": "success", "data": {"user_name": "Test Account Holder",
                                    "email": "holder@example.com", "user_id": "AB1234", "access_token": ACCESS}}).encode()
        if headers.get("Authorization") != f"token {KEY}:{ACCESS}":
            return 403, b'{"status": "error", "message": "Incorrect api_key or access_token", "error_type": "TokenException"}'
        if parts.path == "/instruments/NSE":
            return 200, instruments(gz=True)
        token = parts.path.split("/")[3]
        query = dict(urllib.parse.parse_qsl(parts.query))
        first, last = query["from"][:10], query["to"][:10]
        if token in self.refuse:
            return 200, self.refuse[token]
        days = sorted(d for d in self.closes.get(token, {}) if first <= d <= last)
        return 200, answer(*[candle(d, self.closes[token][d]) for d in days])


def client(fake, now=RUN_AT):
    ticks = iter(range(0, 10**6))
    return news_fetch.KiteClient(KEY, SECRET, request=fake, sleep=lambda s: None, clock=lambda: next(ticks), now=lambda: now)


def test_login_signs_with_the_checksum_and_keeps_tokens_and_personal_data_in_memory_only(env):
    fake = FakeKite({"738561": {d: 100.0 for d in WEEK}, "2953217": {d: 4000.0 for d in WEEK}})
    kite = client(fake)
    with pytest.raises(news_fetch.FetchError, match="not logged in"):
        kite.fetch(news_fetch.KITE_INSTRUMENTS)
    kite.login(REQUEST)
    report = news_fetch.fetch_kite(env, kite, "2024-01-01")
    assert (report["mapped"], report["unmapped"], report["companies"], report["candles"]) == (2, 1, 2, 10)
    url, method, headers, data = fake.calls[0]
    assert method == "POST" and b"checksum=" in data and "Authorization" not in headers
    assert all(h.get("Authorization") == f"token {KEY}:{ACCESS}" and ACCESS not in u for u, _, h, _ in fake.calls[1:])
    dump = "\n".join(env.iterdump())
    for secret in (KEY, SECRET, REQUEST, ACCESS, "Test Account Holder", "holder@example.com", "AB1234"):
        assert secret not in dump
    assert env.execute("SELECT tradingsymbol, reason FROM kt_unmapped").fetchall()[0][0] == "UNKNOWNCO"


def test_refusals_stop_the_run_and_messages_carry_no_secret(env):
    kite = client(FakeKite({}, refuse={news_fetch.KITE_SESSION: (500, json.dumps(
        {"status": "error", "message": f"bad {SECRET} and {REQUEST}"}).encode())}))
    with pytest.raises(news_fetch.FetchError) as e:
        kite.login(REQUEST)
    assert SECRET not in str(e.value) and REQUEST not in str(e.value) and "<hidden>" in str(e.value)
    with pytest.raises(news_fetch.RateLimited):
        kite.login(REQUEST)   # nothing more asked in this run
    limited = client(FakeKite({}, refuse={news_fetch.KITE_INSTRUMENTS: (429, b'{"message": "Too many requests"}')}))
    limited.login(REQUEST)
    with pytest.raises(news_fetch.RateLimited):
        news_fetch.fetch_kite(env, limited, "2024-01-01")
    expired = client(FakeKite({}, refuse={news_fetch.KITE_INSTRUMENTS: (403, b'{"message": "expired"}')}))
    expired.login(REQUEST)
    with pytest.raises(news_fetch.FetchError, match="6 AM"):
        news_fetch.fetch_kite(env, expired, "2024-01-01")


class Dropping:
    """Kite behind a connection that is reset for the first `drops` downloads (found live on 22-Nov-2026)."""

    def __init__(self, fake, drops, on_login=False):
        self.fake, self.drops, self.on_login = fake, drops, on_login

    def __call__(self, url, method="GET", headers=None, data=None):
        if self.drops and (method == "GET" or self.on_login):
            self.drops -= 1
            raise news_fetch.FetchError("api.kite.trade could not be reached: [WinError 10054] connection reset")
        return self.fake(url, method, headers, data)


def test_a_dropped_download_is_asked_again_after_waiting_then_the_run_stops(env):
    waits = []
    fake = FakeKite({"738561": {d: 100.0 for d in WEEK}})
    kite = news_fetch.KiteClient(KEY, SECRET, request=Dropping(fake, 2), sleep=waits.append, clock=lambda: 10**6,
                                 now=lambda: RUN_AT)
    kite.login(REQUEST)
    report = news_fetch.fetch_kite(env, kite, "2024-01-01", symbols=["RELIANCE"])
    assert report["companies"] == 1 and kite.retries == 2 and [w for w in waits if w >= 1] == [5, 20]
    hopeless = news_fetch.KiteClient(KEY, SECRET, request=Dropping(fake, 99), sleep=lambda s: None,
                                     clock=lambda: 10**6, now=lambda: RUN_AT)
    hopeless.login(REQUEST)
    with pytest.raises(news_fetch.FetchError, match="4 tries"):
        hopeless.fetch(news_fetch.KITE_INSTRUMENTS)
    assert hopeless.gave_up and hopeless.retries == 3
    once = news_fetch.KiteClient(KEY, SECRET, request=Dropping(fake, 1, on_login=True), sleep=lambda s: None)
    with pytest.raises(news_fetch.FetchError, match="1 tries"):
        once.login(REQUEST)   # the login's request token works once: never asked again


class Gateway:
    """Kite whose gateway answers a server error for the first `errors` downloads (found live: HTTP 502)."""

    def __init__(self, fake, errors, status=502):
        self.fake, self.errors, self.status = fake, errors, status

    def __call__(self, url, method="GET", headers=None, data=None):
        if self.errors and method == "GET":
            self.errors -= 1
            return self.status, b"<html>502 Bad Gateway</html>"
        return self.fake(url, method, headers, data)


def test_a_temporary_server_error_is_asked_again_but_a_refusal_is_not(env):
    fake = FakeKite({"738561": {d: 100.0 for d in WEEK}})
    waits = []
    kite = news_fetch.KiteClient(KEY, SECRET, request=Gateway(fake, 3), sleep=waits.append, clock=lambda: 10**6,
                                 now=lambda: RUN_AT)
    kite.login(REQUEST)
    assert news_fetch.fetch_kite(env, kite, "2024-01-01", symbols=["RELIANCE"])["companies"] == 1
    assert kite.retries == 3 and [w for w in waits if w >= 1] == [5, 20, 60]
    stuck = news_fetch.KiteClient(KEY, SECRET, request=Gateway(fake, 99, 503), sleep=lambda s: None,
                                  clock=lambda: 10**6, now=lambda: RUN_AT)
    stuck.login(REQUEST)
    with pytest.raises(news_fetch.FetchError, match="HTTP 503"):
        stuck.fetch(news_fetch.KITE_INSTRUMENTS)
    for status, error in ((429, news_fetch.RateLimited), (400, news_fetch.FetchError)):   # refusals: never again
        refused = news_fetch.KiteClient(KEY, SECRET, request=Gateway(fake, 1, status), sleep=lambda s: None,
                                        clock=lambda: 10**6, now=lambda: RUN_AT)
        refused.login(REQUEST)
        with pytest.raises(error):
            refused.fetch(news_fetch.KITE_INSTRUMENTS)
        assert refused.retries == 0


def test_a_refused_company_is_reported_at_once_not_only_at_the_end(env):
    bad = json.dumps({"status": "success", "data": {"candles": [["2024-03-14T00:00:00+0530", 10, 9, 8, 10, 5]]}})
    heard = []
    kite = client(FakeKite({"738561": {d: 100.0 for d in WEEK}}, refuse={"2953217": bad.encode()}))
    kite.login(REQUEST)
    news_fetch.fetch_kite(env, kite, "2024-01-01", on_refused=heard.append)
    assert len(heard) == 1 and heard[0].startswith("TCS:")


def test_a_refused_answer_stores_nothing_for_that_company_and_the_run_goes_on(env):
    bad = json.dumps({"status": "success", "data": {"candles": [["2024-03-14T00:00:00+0530", 10, 9, 8, 10, 5]]}})
    kite = client(FakeKite({"738561": {d: 100.0 for d in WEEK}}, refuse={"2953217": bad.encode()}))
    kite.login(REQUEST)
    report = news_fetch.fetch_kite(env, kite, "2024-01-01")
    assert report["companies"] == 1 and len(report["refused"]) == 1 and report["refused"][0].startswith("TCS")
    assert env.execute("SELECT DISTINCT isin FROM kt_candles").fetchall() == [(RELIANCE,)]


def test_daily_runs_add_new_days_and_a_readjusted_history_is_fetched_again_whole(env):
    closes = {"738561": {d: 100.0 for d in WEEK}}
    first = client(FakeKite(closes))
    first.login(REQUEST)
    report = news_fetch.fetch_kite(env, first, "2018-01-01", symbols=["RELIANCE"])
    assert report["requests"] == 2 and first.requests == 4   # two history chunks back to 2018; plus login and list
    closes["738561"]["2024-03-18"] = 101.0
    later = RUN_AT + timedelta(days=3)
    second = client(FakeKite(closes), now=later)
    second.login(REQUEST)
    report = news_fetch.fetch_kite(env, second, "2018-01-01", symbols=["RELIANCE"])
    assert report["readjusted"] == [] and report["candles"] == 6
    closes["738561"] = {d: c / 2 for d, c in closes["738561"].items()}   # Zerodha re-adjusts after a 1:2 split
    third = client(FakeKite(closes), now=later + timedelta(hours=1))
    third.login(REQUEST)
    report = news_fetch.fetch_kite(env, third, "2018-01-01", symbols=["RELIANCE"])
    assert report["readjusted"] == ["RELIANCE"]
    reasons = [r[0] for r in env.execute("SELECT reason FROM kt_fetches ORDER BY fetch_id")]
    assert reasons == ["backfill", "backfill", "daily", "readjusted", "readjusted"]
    newest, _ = series(env, RELIANCE, later + timedelta(days=1), CURRENT)
    assert {c["close"] for c in newest.values()} == {50.0, 50.5}


def test_todays_candle_is_kept_only_after_six_in_the_evening_india_time():
    assert news_fetch.kite_last_day(datetime(2024, 3, 15, 12, 29, tzinfo=UTC)) == "2024-03-14"   # 17:59 IST
    assert news_fetch.kite_last_day(datetime(2024, 3, 15, 12, 30, tzinfo=UTC)) == "2024-03-15"   # 18:00 IST


# ---- the liquidity band and the hub -------------------------------------------------------------------

def test_the_band_counts_vendor_days_nse_files_lack(env, tmp_path):
    assert not liquidity(env, RELIANCE, DECIDE, CURRENT)["admitted"]
    store(env, [(d, 2500.0) for d in WEEK], RUN_AT)   # 2500 x 1,000,000 = Rs 250 crore a day
    gate = liquidity(env, RELIANCE, DECIDE, CURRENT)
    assert (gate["admitted"], gate["sessions"], gate["vendor_sessions"], gate["rule"]) == (True, 5, 5, LIQUIDITY_RULE)
    assert LIQUIDITY_RULE == "se-liquidity-2"
    trade(env, tmp_path, WEEK[:2], [("RELIANCE", RELIANCE, "2940.00", "1000000")])   # NSE's own files come first
    gate = liquidity(env, RELIANCE, DECIDE, CURRENT)
    assert (gate["sessions"], gate["vendor_sessions"]) == (5, 3)
    replay = liquidity(env, RELIANCE, DECIDE, REPLAY)
    assert not replay["admitted"] and replay["withheld"] >= 5


def test_the_hub_gives_vendor_days_labelled_and_never_twice(env, tmp_path):
    trade(env, tmp_path, WEEK[:2], [("RELIANCE", RELIANCE, "2940.00", "1000000")])
    store(env, [(d, 2500.0) for d in WEEK], RUN_AT)
    bundle = gather(env, DECIDE, CURRENT, RELIANCE, start="2024-03-11", end="2024-03-15")
    market = bundle.of(Domain.MARKET)
    assert sorted((e.observed, e.kind) for e in market) == sorted(
        [(d, "daily_price") for d in WEEK[:2]] + [(d, "vendor_daily_price") for d in WEEK[2:]])
    vendor = [e for e in market if e.kind == "vendor_daily_price"]
    assert all("adjusted" in e.details["series"] and e.source_id == "kite_connect" for e in vendor)
    assert not [g for g in bundle.gaps_of(Domain.MARKET) if g.nature == GapNature.MISSING]   # every day covered
    replay = gather(env, DECIDE, REPLAY, RELIANCE, start="2024-03-11", end="2024-03-15")
    assert not [e for e in replay.of(Domain.MARKET) if e.kind == "vendor_daily_price"]
    assert any(g.component == "vendor prices" and g.nature == GapNature.WITHHELD for g in replay.gaps_of(Domain.MARKET))


# ---- registry, schema, record ---------------------------------------------------------------------------

def test_kite_is_registered_with_its_terms(env):
    source = get_source(env, "kite_connect")
    assert "4(b)" in source["license"] and "ADR-014" in source["license"] and "purge-kite" in source["license"]


def test_schema_22_migrates_and_rolls_back_cleanly():
    c = connect(":memory:")
    assert migrate(c) >= 22
    rollback(c, 21)
    assert current_version(c) == 21 and not [r for r in c.execute(
        "SELECT name FROM sqlite_master WHERE name LIKE 'kt_%'")]
    assert migrate(c) >= 22


def test_the_acceptance_record_says_what_is_not_claimed():
    record = load_acceptance_records()["STAGE_06A_acceptance.yaml"]
    assert all(v is False for v in record["negative_assertions"].values())
    assert record["not_claimed"]["prices of delisted companies (Kite has none)"] is False


def test_new_stage_6a_files_are_plain_ascii():
    for path in ("src/ingestion/kite_prices.py", "tests/test_stage6a_kite_prices.py", "stages/STAGE_06A_acceptance.yaml",
                 "migrations/0022_kite_prices.up.sql", "migrations/0022_kite_prices.down.sql",
                 "migrations/0023_kite_problems.up.sql", "migrations/0023_kite_problems.down.sql",
                 "docs/decisions/ADR-014-kite-connect-daily-prices.md"):
        (PROJECT_ROOT / path).read_bytes().decode("ascii")
