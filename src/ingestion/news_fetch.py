"""Fetching news from GDELT's DOC 2.0 API (ADR-005) and SEBI's RSS feed (ADR-006).

This is the ONLY module in the project allowed to open a network connection, and it contacts
only the hosts in ALLOWED_HOSTS - on SEBI's site only the one feed address, SEBI_FEED. NSE data
is never fetched: NSE's terms forbid it (ADR-004). GDELT's terms allow any use, with citation,
and GDELT asks callers to space their requests. SEBI's feed asks readers to wait 60 minutes
between reads; a read sooner is refused before anything is sent.

Rules:
  - Requests are spaced at least MIN_INTERVAL seconds apart. When GDELT refuses (HTTP 429, or its
    'Please limit requests' notice with HTTP 200) the fetcher waits longer and tries again; after
    the last wait it gives up, nothing is stored, and it asks GDELT nothing more in that run - on
    02/03-Oct-2026 GDELT refused one computer for over an hour, and asking again only prolongs
    that. Redirects are never followed, so no other host can be reached.
  - Every response that is used is saved in data/fetched and kept as a raw file before it is
    read (gdelt_news.load_response).
  - GDELT returns at most 250 articles. A full response may be cut short, so it is not used: its
    window is split in two and both halves are fetched. A window too short to split is stored and
    recorded as incomplete (4E).
  - GDELT's DOC API searches only the last 3 months; an older window is refused.
  - Article links are never opened.
"""
import hashlib
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from data_quality.trust_chain import NoDataError
from ingestion.gdelt_news import MAX_ARTICLES, RATE_LIMIT_NOTICE, load_response, news_names, read_response
from ingestion.sebi_releases import load_feed, read_feed
from provenance.availability import parse_timestamp
from provenance.raw_store import ArtifactError

ALLOWED_HOSTS = frozenset({"api.gdeltproject.org", "www.sebi.gov.in"})
SEBI_FEED = "https://www.sebi.gov.in/sebirss.xml"   # the only address on SEBI's site ever asked for
SEBI_WAIT = timedelta(minutes=60)                   # the feed's own time-to-live (ttl 60)
API = "https://api.gdeltproject.org/api/v2/doc/doc"
USER_AGENT = "ai-equity-agent/1.0 (personal research, non-commercial)"
MIN_INTERVAL = 20.0                    # seconds between requests (GDELT asks for at least 5; it refuses in waves)
REFUSAL_WAITS = (60, 180, 300)         # seconds to wait after each refusal before trying again
TIMEOUT = 60
SEARCH_WINDOW = timedelta(days=90)     # GDELT's DOC API searches the last 3 months
MIN_SPLIT = timedelta(hours=1)
FIRST_FETCH = timedelta(days=7)
OVERLAP = timedelta(days=1)


class FetchError(Exception):
    """GDELT could not be used for this request. Nothing was stored."""


class RateLimited(FetchError):
    """GDELT kept refusing; the fetcher asks nothing more in this run. Nothing was stored."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None   # a redirect becomes an error: no host outside ALLOWED_HOSTS is ever reached


def _check_host(url):
    host = urllib.parse.urlsplit(url).hostname
    if host not in ALLOWED_HOSTS:
        raise FetchError(f"{url[:60]!r} is not an allowed host (ADR-005, ADR-006)")
    if host == "www.sebi.gov.in" and url != SEBI_FEED:
        raise FetchError(f"{url[:60]!r} is not an allowed address: only SEBI's feed is read (ADR-006)")


def http_get(url):
    """(HTTP status, body). The only network call in the project."""
    _check_host(url)
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(request, timeout=TIMEOUT) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise FetchError(f"GDELT could not be reached: {e}") from None


def query_for(names):
    """GDELT search text for a company's news names: each name as an exact phrase."""
    quoted = [f'"{name}"' for name in sorted(names)]
    return quoted[0] if len(quoted) == 1 else "(" + " OR ".join(quoted) + ")"


def request_url(query, start, end):
    params = {"query": query, "mode": "artlist", "format": "json", "maxrecords": str(MAX_ARTICLES),
              "sort": "datedesc", "startdatetime": start.strftime("%Y%m%d%H%M%S"),
              "enddatetime": end.strftime("%Y%m%d%H%M%S")}
    url = API + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    _check_host(url)
    return url


class Fetcher:
    """Makes GDELT requests no closer together than MIN_INTERVAL, waiting longer after refusals."""

    def __init__(self, get=http_get, sleep=time.sleep, clock=time.monotonic,
                 now=lambda: datetime.now(timezone.utc), on_wait=None):
        self.get, self.sleep, self.clock, self.now = get, sleep, clock, now
        self.on_wait = on_wait or (lambda seconds, reason: None)
        self.last = None
        self.requests = self.refusals = 0
        self.gave_up = False

    def fetch(self, url):
        """(body, retrieved_at) of one successful response, or FetchError."""
        if self.gave_up:
            raise RateLimited("GDELT kept refusing earlier in this run, so it was not asked again - nothing"
                              " stored; try again later")
        for wait in (0,) + REFUSAL_WAITS:
            if wait:
                self.on_wait(wait, "GDELT refused the last request (rate limit)")
                self.sleep(wait)
            if self.last is not None and self.clock() - self.last < MIN_INTERVAL:
                gap = MIN_INTERVAL - (self.clock() - self.last)
                self.on_wait(gap, "spacing requests as GDELT asks")
                self.sleep(gap)
            self.last = self.clock()
            self.requests += 1
            status, body = self.get(url)
            retrieved = self.now()
            if status == 429 or body.lstrip().startswith(RATE_LIMIT_NOTICE.encode()):
                self.refusals += 1
                continue
            if status != 200:
                raise FetchError(f"GDELT answered HTTP {status} - nothing stored")
            return body, retrieved
        self.gave_up = True
        raise RateLimited(f"GDELT refused {len(REFUSAL_WAITS) + 1} requests in a row (rate limit) - nothing"
                          " stored; try again later")


def default_window(conn, isin, now):
    """From a day before the end of the last stored window (or FIRST_FETCH back), to now."""
    last = conn.execute("SELECT MAX(window_end) FROM nw_responses WHERE isin = ?", [isin]).fetchone()[0]
    start = parse_timestamp(last) - OVERLAP if last else now - FIRST_FETCH
    return max(start, now - SEARCH_WINDOW + timedelta(hours=1)), now


def fetch_company(conn, fetcher, isin, symbol, start, end, out_dir, raw_dir=None):
    """Fetch and store one company's news for [start, end]. Returns a list of reports, one per window."""
    names = [name for isin_, name, _, valid_to in news_names(conn) if isin_ == isin and valid_to is None]
    if not names:
        raise FetchError(f"{symbol} has no news names - add it to config/news_names.yaml")
    now = fetcher.now()
    if start < now - SEARCH_WINDOW:
        raise FetchError("GDELT searches only the last 3 months - choose a later start")
    if not start < end <= now:
        raise FetchError("The window must end after it starts, and not in the future")
    start, end = start.replace(microsecond=0), end.replace(microsecond=0)
    reports = []
    _fetch_window(conn, fetcher, isin, symbol, query_for(names), start, end, Path(out_dir), raw_dir, reports)
    return reports


def _fetch_window(conn, fetcher, isin, symbol, query, start, end, out_dir, raw_dir, reports):
    body, retrieved = fetcher.fetch(request_url(query, start, end))
    window = f"{start:%Y-%m-%d %H:%M} to {end:%Y-%m-%d %H:%M} UTC"
    try:
        articles = read_response(body)
    except NoDataError:
        reports.append({"window": window, "articles": 0, "note": "no articles in this window - nothing stored"})
        return
    if len(articles) >= MAX_ARTICLES and end - start >= 2 * MIN_SPLIT:
        middle = start + (end - start) / 2
        middle = middle.replace(microsecond=0)
        _fetch_window(conn, fetcher, isin, symbol, query, start, middle, out_dir, raw_dir, reports)
        _fetch_window(conn, fetcher, isin, symbol, query, middle, end, out_dir, raw_dir, reports)
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"gdelt_{symbol}_{start:%Y%m%d%H%M%S}_{end:%Y%m%d%H%M%S}.json"
    if path.exists() and path.read_bytes() != body:
        path = path.with_name(f"{path.stem}__{hashlib.sha256(body).hexdigest()[:8]}.json")
    path.write_bytes(body)
    try:
        report = load_response(conn, path, isin, query, start, end, retrieved, raw_dir=raw_dir)
    except ArtifactError:
        report = {"articles": len(articles), "note": "identical to a response already stored - nothing new"}
    reports.append({"window": window, **{k: v for k, v in report.items() if k != "problems"},
                    "problems": report.get("problems", [])})


def fetch_sebi(conn, out_dir, get=http_get, now=lambda: datetime.now(timezone.utc), raw_dir=None):
    """Read SEBI's feed once and store its releases (ADR-006). Returns the load report."""
    last = conn.execute("SELECT MAX(a.retrieved_at) FROM sb_reads r JOIN raw_artifacts a"
                        " ON a.artifact_id = r.artifact_id").fetchone()[0]
    if last and now() - parse_timestamp(last) < SEBI_WAIT:
        raise FetchError(f"SEBI's feed was last read at {last[:16]} UTC and asks readers to wait"
                         f" {SEBI_WAIT.seconds // 60} minutes between reads - try again later; nothing sent")
    status, body = get(SEBI_FEED)
    retrieved = now()
    if status != 200:
        raise FetchError(f"SEBI answered HTTP {status} - nothing stored")
    items = read_feed(body)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"sebi_{retrieved:%Y%m%d%H%M%S}.xml"
    path.write_bytes(body)
    try:
        return load_feed(conn, path, retrieved, raw_dir=raw_dir)
    except ArtifactError:
        return {"items": len(items), "note": "identical to a read already stored - nothing new", "problems": []}
