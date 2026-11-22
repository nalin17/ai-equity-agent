"""Daily NSE equity candles from Zerodha's Kite Connect historical API (architecture 40B step 6a, 4C, 5B; ADR-014).

Input: answers of Kite Connect (api.kite.trade), fetched by the news fetcher - the only module allowed to use the
network - with the owner's own API key and a login the owner completes in a browser each day.

Rules, from Kite's documentation (read 22-Nov-2026) and its terms:
  - Kite's instrument list (a CSV, sometimes gzipped) has no ISIN. An NSE EQ instrument reaches a company only
    when its tradingsymbol is that company's NSE symbol in the registry on the day - or that symbol with the suffix
    -BE or -BZ, NSE's trade-for-trade series of the same shares (206 registry companies on 22-Nov-2026); any other
    suffix (-SM, -ST, -D1, -W1, bonds ...) is another instrument. Anything else is recorded as unmapped, never
    guessed. Two Kite symbols for one company are both refused.
  - Kite's daily candles are ADJUSTED by the vendor for corporate actions, and the whole history is re-adjusted
    after each new split or bonus. They are therefore never trusted_prices (raw, as traded): every answer is stored
    as its own vintage. A daily fetch overlaps the last stored days; if any overlapping day differs, the company's
    whole history is fetched again as a new vintage ('readjusted'), so a series is never stitched from two
    adjustments.
  - An answer is used whole or not at all: status success; every candle [timestamp, open, high, low, close,
    volume] with an India-time timestamp inside the asked range, dates never going back, positive finite prices
    with low <= open, close <= high, and a whole non-negative volume. Otherwise nothing is stored for that company
    in that run (4C: refuse, never repair). Two faults found in old SME-period history on the owner's first full
    run (22-Nov-2026) are set aside candle by candle instead (kt_problems), the rest of the answer being sound: a
    day candle stamped at another time than 00:00 (SVLL, OSWALSEEDS: 10:00), and two candles for one day
    (SONAMLTD, AHLADA) - both are set aside, never chosen between. The day stays missing.
  - Availability (5B): a vintage is known from our retrieval. The adjusted values were never published as such on
    the trade date, so under historical replay they are AVAILABILITY_REVIEW - withheld, never used.
  - The raw answers, the instrument list, the login answer (which carries the owner's name and email) and every
    token are never stored or logged; only the candles, the run's counts and sha256 digests are.
  - Kite's terms 4(b) restrict databases of API content unless Zerodha permits it. The owner chose on 22-Nov-2026
    to store while Zerodha's written answer is awaited; purge() removes every Kite row at once if it is refused.
"""
import csv
import gzip
import hashlib
import io
import json
import math
import re
from datetime import timedelta, timezone

from core.database import MIGRATIONS_DIR, now_utc, run_in_transaction
from core.dates import strict_iso_date
from ingestion.market_adapters import AdapterError
from ingestion.source_registry import get_source
from provenance.availability import Availability, PitClaim, disposition, parse_timestamp
from universe.entities import EntityError, resolve

SOURCE_ID = "kite_connect"
INSTRUMENT_COLUMNS = ("instrument_token", "exchange_token", "tradingsymbol", "name", "last_price", "expiry", "strike",
                      "tick_size", "lot_size", "instrument_type", "segment", "exchange")
DAY_STAMP = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})\+0530$")
SERIES_SUFFIXES = ("-BE", "-BZ")   # NSE trade-for-trade series: the same shares, the same ISIN
MAX_DAYS = 2000                 # days per request for day candles (Kite's limit for the day interval)
OVERLAP_DAYS = 10               # a daily fetch starts this many calendar days before the last stored day
PRICE_TOLERANCE = 0.005         # half a paisa: a larger difference on an overlapping day is a re-adjustment
BACKFILL_FROM = "2015-01-01"    # first fetch of a company starts here unless --from says otherwise
MIGRATIONS = ("0022_kite_prices", "0023_kite_problems")   # every Kite table - purge() drops and remakes them all


class KiteResponseError(AdapterError):
    """A Kite answer cannot be used as a whole. Nothing is stored from it."""


# ---- the instrument list -----------------------------------------------------------------------------------

def read_instruments(body):
    """[(tradingsymbol, instrument_token)] of the NSE EQ instruments in Kite's instrument list (bytes)."""
    if body[:2] == b"\x1f\x8b":
        try:
            body = gzip.decompress(body)
        except (OSError, EOFError) as e:
            raise KiteResponseError(f"Kite's instrument list is not readable gzip: {e}") from None
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise KiteResponseError("Kite's instrument list is not UTF-8 text") from None
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or tuple(c.strip() for c in rows[0]) != INSTRUMENT_COLUMNS:
        raise KiteResponseError(f"Kite's instrument list header changed: {rows[0][:12] if rows else 'empty'}")
    found, seen = [], set()
    for number, row in enumerate(rows[1:], 2):
        if not row:
            continue
        if len(row) != len(INSTRUMENT_COLUMNS):
            raise KiteResponseError(f"instrument list row {number} has {len(row)} fields")
        values = dict(zip(INSTRUMENT_COLUMNS, (c.strip() for c in row)))
        if (values["exchange"], values["segment"], values["instrument_type"]) != ("NSE", "NSE", "EQ"):
            continue
        if not values["instrument_token"].isdigit() or not values["tradingsymbol"]:
            raise KiteResponseError(f"instrument list row {number}: unreadable token or symbol")
        if values["tradingsymbol"] in seen:
            raise KiteResponseError(f"instrument list lists NSE {values['tradingsymbol']} twice")
        seen.add(values["tradingsymbol"])
        found.append((values["tradingsymbol"], int(values["instrument_token"])))
    if not found:
        raise KiteResponseError("Kite's instrument list has no NSE EQ instrument")
    return found


def map_instruments(conn, instruments, day):
    """([(isin, tradingsymbol, token)], [(tradingsymbol, reason)]): Kite symbols matched to registry companies by
    their NSE symbol on day (or that symbol with -BE or -BZ); two symbols for one company are both refused."""
    hits, unmapped = {}, []
    for symbol, token in instruments:
        base = next((symbol[:-len(s)] for s in SERIES_SUFFIXES if symbol.endswith(s)), symbol)
        try:
            isin = resolve(conn, base, day, alias_type="nse_symbol")
        except EntityError as e:
            unmapped.append((symbol, f"no registry company with this NSE symbol on {day} ({type(e).__name__})"))
            continue
        hits.setdefault(isin, []).append((symbol, token))
    mapped = []
    for isin, pairs in sorted(hits.items()):
        if len(pairs) > 1:
            unmapped += [(s, f"one of {len(pairs)} Kite symbols for {isin} - refused") for s, _ in pairs]
            continue
        mapped.append((isin, pairs[0][0], pairs[0][1]))
    return mapped, sorted(unmapped)


# ---- candles ----------------------------------------------------------------------------------------------

def _number(value, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise KiteResponseError(f"{what} {value!r} is not a finite number")
    return float(value)


def read_candles(body, from_date, to_date):
    """([(trade_date, open, high, low, close, volume)], [(trade_date, kind, detail)]) of one day-candle answer
    (bytes): the candles kept and the candles set aside - or KiteResponseError for the whole answer."""
    try:
        answer = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise KiteResponseError("Kite's answer is not JSON") from None
    if not isinstance(answer, dict) or answer.get("status") != "success" or not isinstance(answer.get("data"), dict):
        raise KiteResponseError(f"Kite's answer is not a success: {str(answer)[:120]}")
    candles = answer["data"].get("candles")
    if not isinstance(candles, list):
        raise KiteResponseError("Kite's answer has no candle list")
    out, aside, last, doubled = [], [], None, set()
    for number, candle in enumerate(candles, 1):
        if not isinstance(candle, list) or len(candle) not in (6, 7):
            raise KiteResponseError(f"candle {number} is not [time, open, high, low, close, volume]")
        match = DAY_STAMP.match(str(candle[0]))
        if not match:
            raise KiteResponseError(f"candle {number} time {str(candle[0])[:30]!r} is not an India-time timestamp")
        day = strict_iso_date(match[1]).isoformat()
        if not from_date <= day <= to_date:
            raise KiteResponseError(f"candle {number} is dated {day}, outside {from_date} to {to_date}")
        if last is not None and day < last:
            raise KiteResponseError(f"candle {number} ({day}) goes back before {last}")
        if day == last:   # two candles for one day: both set aside, never chosen between
            doubled.add(day)
            continue
        last = day
        o, h, low, c = (_number(v, f"candle {number}") for v in candle[1:5])
        volume = candle[5]
        if isinstance(volume, float) and volume.is_integer():
            volume = int(volume)
        if isinstance(volume, bool) or not isinstance(volume, int) or volume < 0:
            raise KiteResponseError(f"candle {number} volume {volume!r} is not a whole number >= 0")
        if min(o, h, low, c) <= 0 or not (low <= min(o, c) and h >= max(o, c)):
            raise KiteResponseError(f"candle {number} ({day}) breaks low <= open, close <= high")
        if match[2] != "00:00:00":
            aside.append((day, "time_not_midnight", f"candle {number} stamped {match[2]}, not 00:00 - not a day candle"
                                                    " as documented"))
            continue
        out.append((day, o, h, low, c, volume))
    aside += [(day, "duplicate_day", "two candles for one day - both set aside") for day in sorted(doubled)]
    return [c for c in out if c[0] not in doubled], aside


def plan_requests(conn, isin, last_day, backfill_from=BACKFILL_FROM):
    """[(from, to, reason)] for one company up to last_day: the whole history in chunks of MAX_DAYS if nothing is
    stored ('backfill'), otherwise from OVERLAP_DAYS before the last stored day ('daily')."""
    stored = conn.execute("SELECT MAX(c.trade_date) FROM kt_candles c WHERE c.isin = ?", [isin]).fetchone()[0]
    end = strict_iso_date(last_day)
    if stored:
        start = max(strict_iso_date(stored) - timedelta(days=OVERLAP_DAYS), strict_iso_date(backfill_from))
        return [(start.isoformat(), end.isoformat(), "daily")] if start <= end else []
    return chunks(backfill_from, last_day, "backfill")


def chunks(first, last, reason):
    start, end, out = strict_iso_date(first), strict_iso_date(last), []
    while start <= end:
        stop = min(start + timedelta(days=MAX_DAYS - 1), end)
        out.append((start.isoformat(), stop.isoformat(), reason))
        start = stop + timedelta(days=1)
    return out


def newest_values(conn, isin, days):
    """{trade_date: (open, high, low, close, volume)} of the newest stored vintage of each of days."""
    marks = ", ".join("?" * len(days))
    rows = conn.execute(
        f"SELECT c.trade_date, c.open, c.high, c.low, c.close, c.volume FROM kt_candles c"
        f" JOIN kt_fetches f ON f.fetch_id = c.fetch_id WHERE c.isin = ? AND c.trade_date IN ({marks})"
        f" ORDER BY f.retrieved_at, c.fetch_id", [isin, *days]).fetchall() if days else []
    return {r[0]: r[1:] for r in rows}   # later vintages overwrite earlier ones in the dict


def readjusted(conn, isin, candles):
    """True when an overlapping day differs from the newest stored vintage - the vendor re-adjusted the series."""
    stored = newest_values(conn, isin, [c[0] for c in candles])
    for day, *values in candles:
        if day in stored:
            old = stored[day]
            if any(abs(a - b) > PRICE_TOLERANCE for a, b in zip(values[:4], old[:4])) or values[4] != old[4]:
                return True
    return False


# ---- storing ----------------------------------------------------------------------------------------------

def start_run(conn, instruments_listed, mapped, unmapped, instruments_body):
    get_source(conn, SOURCE_ID)

    def work(c):
        run_id = c.execute("INSERT INTO kt_runs (started_at, instruments_listed, instruments_mapped, instruments_sha256,"
                           " recorded_at) VALUES (?, ?, ?, ?, ?)",
                           [now_utc(), instruments_listed, len(mapped), hashlib.sha256(instruments_body).hexdigest(),
                            now_utc()]).lastrowid
        c.executemany("INSERT INTO kt_unmapped VALUES (?, ?, ?)", [(run_id, s, r) for s, r in unmapped])
        return run_id

    return run_in_transaction(conn, work)


def load_fetch(conn, run_id, isin, symbol, token, from_date, to_date, body, retrieved_at, reason):
    """Store one checked answer as a vintage, with the candles it set aside. Returns (fetch_id, candles, aside)."""
    candles, aside = read_candles(body, from_date, to_date)
    retrieved = parse_timestamp(retrieved_at).astimezone(timezone.utc).isoformat()   # UTC: sorts as text

    def work(c):
        fetch_id = c.execute(
            "INSERT INTO kt_fetches (run_id, isin, tradingsymbol, instrument_token, from_date, to_date, retrieved_at,"
            " candles, reason, sha256, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [run_id, isin, symbol, token, from_date, to_date, retrieved, len(candles), reason,
             hashlib.sha256(body).hexdigest(), now_utc()]).lastrowid
        c.executemany("INSERT INTO kt_candles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      [(fetch_id, isin, *candle) for candle in candles])
        c.executemany("INSERT INTO kt_problems VALUES (?, ?, ?, ?)", [(fetch_id, *problem) for problem in aside])
        return fetch_id, len(candles), len(aside)

    return run_in_transaction(conn, work)


def purge(conn):
    """Remove ALL Kite data at once (Kite terms 9(b), or a refusal by Zerodha): every Kite table is dropped and made
    again, empty. The schema version is unchanged. Returns the number of candles removed."""
    read = lambda name: (MIGRATIONS_DIR / name).read_text(encoding="utf-8-sig")  # noqa: E731
    down = "\n".join(read(f"{m}.down.sql") for m in reversed(MIGRATIONS))
    up = "\n".join(read(f"{m}.up.sql") for m in MIGRATIONS)
    removed = conn.execute("SELECT COUNT(*) FROM kt_candles").fetchone()[0]
    conn.execute("BEGIN")
    try:
        conn.executescript(down + "\n" + up)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return removed


# ---- reading ----------------------------------------------------------------------------------------------

def series(conn, isin, decision_time, claim=PitClaim.CURRENT_DECISION, start=None, end=None):
    """({trade_date: candle dict}, withheld): for each day, the newest vintage known at decision_time. Under
    historical replay nothing is given - the vendor's adjusted values were not public as such - and the count of
    days withheld is returned."""
    rows = conn.execute(
        "SELECT c.trade_date, c.open, c.high, c.low, c.close, c.volume, f.fetch_id, f.retrieved_at FROM kt_candles c"
        " JOIN kt_fetches f ON f.fetch_id = c.fetch_id WHERE c.isin = ? AND c.trade_date >= ? AND c.trade_date <= ?"
        " ORDER BY f.retrieved_at, f.fetch_id", [isin, start or "0000-00-00", end or "9999-99-99"]).fetchall()
    found, withheld = {}, set()
    for day, o, h, low, c, volume, fetch_id, retrieved in rows:
        state = disposition(claim, decision_time, retrieved, None)
        if state == Availability.ELIGIBLE:
            found[day] = {"open": o, "high": h, "low": low, "close": c, "volume": volume, "fetch_id": fetch_id,
                          "retrieved_at": retrieved}
        elif state == Availability.AVAILABILITY_REVIEW:
            withheld.add(day)
    return found, len(withheld - set(found))
