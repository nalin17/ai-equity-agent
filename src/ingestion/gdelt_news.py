"""News from GDELT: articles, the companies they name, and copies of one story
(architecture 40B step 9, 3B, 4, 4A, 4B.4, 4D, 5B; ADR-005).

Input: responses of GDELT's DOC 2.0 API in article-list mode (JSON), fetched by the news fetcher -
the only module allowed to use the network. GDELT's terms allow any use,
with citation. Each article gives its link, headline, site, language, country and the time GDELT
first saw it. Article links are never opened and article text is never read (ADR-005).

Rules, each found on GDELT's real responses:
  - A response is kept byte for byte before it is read. An empty response, GDELT's 'Please limit
    requests' notice, or anything else that is not an article list, is refused whole and nothing
    is stored - never 'no news' (4C.1, 4B.5).
  - GDELT returns at most 250 articles per response, so a full response may have been cut short.
    It is recorded as incomplete (4E); the fetcher splits the window to avoid that.
  - Availability (5B): GDELT records the time it first saw an article in 15-minute steps. An
    article is taken as public 15 minutes after that time, or at our retrieval if that is
    earlier - never sooner.
  - An article is stored once, by its link. The same link returned again must agree, or it is a
    conflict and is recorded.
  - Headlines are data, never instruction (4D): stored verbatim and only ever compared.
  - Which company an article is about is an extraction (rule nw-entity-1) with its own extraction
    confidence, never investment confidence (4A rule 4). Only names a person declared for a
    company (config/news_names.yaml), and that company's registered name, are looked for. A
    company is an article's subject only when its name is in both the headline and the link, it
    is not one item of a comma list, and no other listed company is recognised in the headline -
    by a registered name of two or more words, or an NSE symbol of three or more letters written
    in capitals. Otherwise it is a mention, and an article naming no declared company is
    unassigned - never guessed (4B.4). Real headlines show why: a search for 'HDFC Bank' returns
    market round-ups, deposit-rate tables and lists of stocks ('Stocks in news : Infosys , HDFC
    Bank , Jio Financial , IRFC , NCC and Blue Dart'; 'SBI Life , Max Fin , HDFC Life , LIC share
    price targets'). Recognising another company only ever withholds 'subject'.
  - One story, many copies (4A rule 2, rule nw-dedup-1). Real responses carry wire stories on
    several sites, one site's story in two sections, print editions beside web ones, and one tips
    site republishing the same article under about ten addresses over 33 hours. Articles are
    copies of one story when their headlines are the same word for word (letters and digits of any
    script, ignoring case and punctuation), the headline is long enough to be distinctive, and each
    copy was available within 72 hours of the story's first copy. Only the headline is used, so
    merging identical headlines can never make information look public earlier than it was.
    Headlines in other scripts keep their letters: a first draft that kept only Latin letters made
    two different Gujarati headlines look identical. Stories are derived from what was known at
    the decision time, so a late copy can never date a story earlier.
  - Direction, materiality, event type and expected horizon are not assessed in this stage; each
    is reported as not assessed, never invented.
"""
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from core.config import PROJECT_ROOT
from core.database import now_utc, run_in_transaction
from core.dates import strict_iso_date
from data_quality.extraction_confidence import ExtractionConfidence
from data_quality.trust_chain import NoDataError
from ingestion.market_adapters import AdapterError
from ingestion.source_registry import get_source
from provenance.availability import Availability, PitClaim, disposition, parse_timestamp
from provenance.raw_store import store_raw_artifact
from universe.entities import EntityError, add_alias, resolve

SOURCE_ID = "gdelt_doc_news"
MAX_ARTICLES = 250                     # GDELT's cap per response
SEEN_FORMAT = "%Y%m%dT%H%M%SZ"         # e.g. 20261002T094500Z, in UTC
SEEN_STEP = timedelta(minutes=15)      # GDELT updates every 15 minutes
ARTICLE_KEYS = ("url", "title", "seendate", "domain", "language", "sourcecountry")
RATE_LIMIT_NOTICE = "Please limit requests"
PROBLEMS_SHOWN = 10

ENTITY_RULE = "nw-entity-1"
DEDUP_RULE = "nw-dedup-1"
DEDUP_WINDOW = timedelta(hours=72)
MIN_DISTINCTIVE_WORDS = 6
MIN_DISTINCTIVE_CHARS = 30
NOT_ASSESSED = "not_assessed"

NEWS_NAMES_FILE = PROJECT_ROOT / "config" / "news_names.yaml"
NAME_SHAPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 &.'-]{1,58}[A-Za-z0-9.]$")
NAME_ENTRY_KEYS = {"symbol", "isin", "names", "valid_from"}


class NewsResponseError(AdapterError):
    """A GDELT response cannot be used as a whole. Nothing is stored."""


class RateLimitNotice(NewsResponseError):
    """GDELT answered with its 'Please limit requests' notice instead of articles."""


class NewsNamesError(Exception):
    """config/news_names.yaml is invalid or disagrees with what is recorded."""


class NewsNotReadError(Exception):
    """The articles have not been read with the current news names yet - run extract()."""


# ---- words and names -------------------------------------------------------------

def words(text, fold=True, commas=False):
    """Words of letters and digits in any script, lower-cased unless fold is False. Indian vowel signs
    stay inside words. With commas, each comma is kept as a word of its own."""
    found, current = [], []
    for ch in (text.casefold() if fold else text):
        if unicodedata.category(ch)[0] in "LMN":
            current.append(ch)
            continue
        if current:
            found.append("".join(current))
            current = []
        if commas and ch == ",":
            found.append(",")
    if current:
        found.append("".join(current))
    return found


def list_comma(tokens, i):
    """True when tokens[i] is a comma separating items of a list - not one inside a number like 13,000."""
    if not 0 <= i < len(tokens) or tokens[i] != ",":
        return False
    return not (0 < i < len(tokens) - 1 and tokens[i - 1].isdigit() and tokens[i + 1].isdigit())


def link_words(url):
    """Words of a link's path - the part after the site name."""
    rest = url.split("://", 1)[-1]
    return words(rest.split("/", 1)[1]) if "/" in rest else []


def news_names(conn):
    """Every declared news name: (isin, name, valid_from, valid_to)."""
    return conn.execute("SELECT isin, alias_value, valid_from, valid_to FROM entity_aliases"
                        " WHERE alias_type = 'news_name' ORDER BY isin, alias_value, valid_from").fetchall()


def load_news_names_file(path=NEWS_NAMES_FILE):
    with open(Path(path), encoding="utf-8-sig") as f:
        data = yaml.safe_load(f) or {}
    return data.get("companies") or []


def sync_news_names(conn, path=NEWS_NAMES_FILE, today=None):
    """Record every news name in the file that is not recorded yet. A recorded name must still be in
    the file: names are never silently changed. Returns the names added."""
    today = today or now_utc()[:10]
    wanted, owner, registered = set(), {}, {}
    for isin, legal_name in conn.execute("SELECT isin, legal_name FROM entities"):
        registered.setdefault(tuple(registry_name_words(legal_name)), set()).add(isin)
    for entry in load_news_names_file(path):
        if not isinstance(entry, dict) or set(entry) != NAME_ENTRY_KEYS:
            raise NewsNamesError(f"Each company needs exactly {sorted(NAME_ENTRY_KEYS)}: {entry!r}")
        symbol, isin, valid_from = str(entry["symbol"]), str(entry["isin"]), str(entry["valid_from"])
        try:
            strict_iso_date(valid_from)
        except (TypeError, ValueError):
            raise NewsNamesError(f"{symbol}: valid_from must be a YYYY-MM-DD date") from None
        try:
            found = resolve(conn, symbol, today, alias_type="nse_symbol")
        except EntityError as e:
            raise NewsNamesError(f"{symbol} is not a company in the registry: {e}") from None
        if found != isin:
            raise NewsNamesError(f"{symbol} is {found} in the registry, not {isin}")
        names = entry["names"]
        if not isinstance(names, list) or not names:
            raise NewsNamesError(f"{symbol}: names must be a list with at least one name")
        for name in names:
            if not isinstance(name, str) or not NAME_SHAPE.match(name):
                raise NewsNamesError(f"{symbol}: {name!r} is not a usable news name"
                                     " (3-60 letters, digits, spaces, & . ' -)")
            key = tuple(words(name))
            if owner.setdefault(key, isin) != isin:
                raise NewsNamesError(f"The news name {name!r} is declared for two companies; a name must identify one")
            if registered.get(key, set()) - {isin}:
                raise NewsNamesError(f"{symbol}: {name!r} is the registered name of another company"
                                     f" {sorted(registered[key] - {isin})}")
            wanted.add((isin, name, valid_from))
    recorded = conn.execute("SELECT isin, alias_value, valid_from, valid_to FROM entity_aliases"
                            " WHERE alias_type = 'news_name'").fetchall()
    for isin, name, valid_from, valid_to in recorded:
        key = tuple(words(name))
        if owner.get(key, isin) != isin:
            raise NewsNamesError(f"The news name {name!r} is already recorded for {isin}")
    gone = sorted({(i, n, f) for i, n, f, _ in recorded} - wanted)
    if gone or any(r[3] is not None for r in recorded):
        raise NewsNamesError(f"Recorded news names are missing from the file or changed: {gone}. "
                             "News names are never silently changed.")
    added = sorted(wanted - {(i, n, f) for i, n, f, _ in recorded})

    def work(c):
        for isin, name, valid_from in added:
            add_alias(c, isin, "news_name", name, valid_from)

    run_in_transaction(conn, work)
    return [name for _, name, _ in added]


# ---- extraction (rule nw-entity-1) --------------------------------------------------

def registry_name_words(legal_name):
    """Words of a registered company name without a closing 'Limited' or 'Ltd'."""
    found = words(legal_name)
    while found and found[-1] in ("limited", "ltd"):
        found.pop()
    return found


class EntityReader:
    """Rule nw-entity-1 with one set of declared news names and one state of the company registry.

    Declared names (and a declared company's own registered name) can make a company an
    article's subject. Other listed companies are recognised only to stop that: by a registered
    name of two or more words, or by an NSE symbol of three or more letters written in capitals.
    Recognising another company never links an article to it - it only withholds 'subject'."""

    def __init__(self, conn):
        self.declared = news_names(conn)
        registry = conn.execute("SELECT isin, legal_name FROM entities ORDER BY isin").fetchall()
        symbols = conn.execute("SELECT isin, alias_value, valid_from, valid_to FROM entity_aliases"
                               " WHERE alias_type = 'nse_symbol' ORDER BY isin, alias_value, valid_from").fetchall()
        text = repr((self.declared, registry, symbols))
        self.version = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        declared_from = {}   # a declared company's registered name counts from its first declared name
        for isin, _, valid_from, _ in self.declared:
            declared_from[isin] = min(valid_from, declared_from.get(isin, valid_from))
        self.index = {}
        for isin, name, valid_from, valid_to in self.declared:
            self._add(words(name), isin, name, True, valid_from, valid_to)
        for isin, legal_name in registry:
            name_words = registry_name_words(legal_name)
            if isin in declared_from:
                self._add(name_words, isin, legal_name, True, declared_from[isin], None)
            elif len(name_words) >= 2:
                self._add(name_words, isin, legal_name, False, None, None)
        self.symbols = {}
        for isin, symbol, valid_from, valid_to in symbols:
            if symbol.isalpha() and symbol.isupper() and len(symbol) >= 3:
                self.symbols.setdefault(symbol, []).append((isin, valid_from, valid_to))

    def _add(self, name_words, isin, label, declared, valid_from, valid_to):
        if name_words:
            self.index.setdefault(name_words[0], []).append((name_words, isin, label, declared, valid_from, valid_to))

    @staticmethod
    def _valid(day, valid_from, valid_to):
        return valid_from is None or (valid_from <= day and (valid_to is None or day < valid_to))

    def find(self, text_words, day):
        """[(isin, label, declared, start, end)] of the names in text_words; where names overlap the
        longest wins, and a declared name wins a tie."""
        hits = []
        for i, word in enumerate(text_words):
            for name_words, isin, label, declared, valid_from, valid_to in self.index.get(word, ()):
                if self._valid(day, valid_from, valid_to) and text_words[i:i + len(name_words)] == name_words:
                    hits.append((-len(name_words), i, not declared, isin, label, declared))
        taken, found = set(), []
        for minus_size, i, _, isin, label, declared in sorted(hits):   # longest first, then leftmost
            size = -minus_size
            span = set(range(i, i + size))
            if not span & taken:
                taken |= span
                found.append((isin, label, declared, i, i + size))
        return found

    def capital_symbols(self, title, day):
        """{isin: symbol} for NSE symbols written in capitals as whole words of the headline."""
        found = {}
        for word in words(title, fold=False):
            for isin, valid_from, valid_to in self.symbols.get(word, ()):
                if self._valid(day, valid_from, valid_to):
                    found[isin] = word
        return found

    def read(self, title, url, day):
        """[(isin or None, role, extraction confidence, evidence)] for one article."""
        tokens = words(title, commas=True)
        in_headline, in_link = self.find(tokens, day), self.find(link_words(url), day)
        named_headline = {isin: label for isin, label, declared, _, _ in in_headline if declared}
        named_link = {isin: label for isin, label, declared, _, _ in in_link if declared}
        listed = {isin for isin, _, declared, start, end in in_headline
                  if declared and (list_comma(tokens, start - 1) or list_comma(tokens, end))}
        named = sorted(set(named_headline) | set(named_link))
        if not named:
            return [(None, "unassigned", ExtractionConfidence.NO_NAME_FOUND,
                     "no declared news name in the headline or the link")]
        others = {isin: label for isin, label, declared, _, _ in in_headline if not declared}
        others.update({isin: symbol for isin, symbol in self.capital_symbols(title, day).items()
                       if isin not in others})
        for isin in named:
            others.pop(isin, None)
        other_text = f"; other companies in the headline: {', '.join(sorted(others.values()))}" if others else ""
        found = []
        for isin in named:
            in_list = " (one item of a list)" if isin in listed else ""
            evidence = (f"headline: {named_headline.get(isin, '-')}{in_list}; link: {named_link.get(isin, '-')}"
                        + other_text)
            if len(named) > 1 or others:
                role, confidence = "mentioned", ExtractionConfidence.SEVERAL_COMPANIES_NAMED
            elif isin in listed:
                role, confidence = "mentioned", ExtractionConfidence.NAME_IN_A_LIST
            elif isin in named_headline and isin in named_link:
                role, confidence = "subject", ExtractionConfidence.NAME_IN_HEADLINE_AND_LINK
            elif isin in named_headline:
                role, confidence = "mentioned", ExtractionConfidence.NAME_IN_HEADLINE_ONLY
            else:
                role, confidence = "mentioned", ExtractionConfidence.NAME_IN_LINK_ONLY
            found.append((isin, role, confidence, evidence))
        return found


def current_run(conn, reader=None):
    """The extraction run for the news names and registry recorded now, or None if not applied yet."""
    reader = reader or EntityReader(conn)
    row = conn.execute("SELECT run_id FROM nw_extraction_runs WHERE rule = ? AND reader_version = ?",
                       [ENTITY_RULE, reader.version]).fetchone()
    return row[0] if row else None


def extract(conn):
    """Read every article not yet read under rule nw-entity-1 with the current news names and
    registry. A change of either starts a new run over all articles; earlier runs stay as history.
    Returns the run id."""
    reader = EntityReader(conn)
    run_id = current_run(conn, reader)
    if run_id is None:
        run_id = conn.execute(
            "INSERT INTO nw_extraction_runs (rule, reader_version, names_count, started_at) VALUES (?, ?, ?, ?)",
            [ENTITY_RULE, reader.version, len(reader.declared), now_utc()]).lastrowid
    todo = conn.execute(
        "SELECT article_id, title, url, seen_at FROM nw_articles a WHERE NOT EXISTS"
        " (SELECT 1 FROM nw_extractions x WHERE x.run_id = ? AND x.article_id = a.article_id) ORDER BY article_id",
        [run_id]).fetchall()
    when = now_utc()
    for article_id, title, url, seen_at in todo:
        for isin, role, confidence, evidence in reader.read(title, url, seen_at[:10]):
            conn.execute("INSERT INTO nw_extractions VALUES (?, ?, ?, ?, ?, ?, ?)",
                         [run_id, article_id, isin, role, confidence.value, evidence, when])
    return run_id


# ---- responses ---------------------------------------------------------------------

def read_response(data):
    """The article list of one GDELT response (bytes), or an exception - nothing in between."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise NewsResponseError("The GDELT response is not UTF-8 text - nothing is stored") from None
    if text.lstrip().startswith(RATE_LIMIT_NOTICE):
        raise RateLimitNotice("GDELT answered 'Please limit requests' instead of articles - nothing is stored")
    try:
        parsed = json.loads(text)
    except ValueError:
        raise NewsResponseError(f"Not a GDELT article list: {text.strip()[:120]!r}") from None
    if not isinstance(parsed, dict) or set(parsed) - {"articles"} or not isinstance(parsed.get("articles", []), list):
        raise NewsResponseError(f"Not a GDELT article list: {text.strip()[:120]!r}")
    if not parsed.get("articles"):
        raise NoDataError("The GDELT response has no articles - nothing is stored")
    return parsed["articles"]


def _parse_article(article, start, end, retrieved):
    if not isinstance(article, dict):
        raise ValueError("not an article")
    missing = [k for k in ARTICLE_KEYS if not isinstance(article.get(k), str) or not article[k].strip()]
    if missing:
        raise ValueError(f"missing {missing}")
    url = article["url"].strip()
    if not url.startswith(("https://", "http://")) or any(ch.isspace() for ch in url):
        raise ValueError(f"not a web link: {url[:80]!r}")
    seen = datetime.strptime(article["seendate"].strip(), SEEN_FORMAT).replace(tzinfo=timezone.utc)
    if seen > retrieved:
        raise ValueError("seen by GDELT after this response was obtained")
    if not start - SEEN_STEP <= seen <= end + SEEN_STEP:
        raise ValueError(f"seen {seen.isoformat()}, outside the requested window")
    available = min(seen + SEEN_STEP, retrieved)
    return [url, article["title"].strip(), article["domain"].strip(), article["language"].strip(),
            article["sourcecountry"].strip(), seen.isoformat(), available.isoformat()]


def load_response(conn, path, isin, query, window_start, window_end, retrieved_at, raw_dir=None):
    """Keep one GDELT response and store its articles. Returns a report dict."""
    get_source(conn, SOURCE_ID)
    path = Path(path)
    articles = read_response(path.read_bytes())
    start, end, retrieved = (parse_timestamp(window_start), parse_timestamp(window_end),
                             parse_timestamp(retrieved_at))
    if not start < end <= retrieved:
        raise NewsResponseError("The window must end after it starts, and not after the response was obtained")
    if not conn.execute("SELECT 1 FROM entities WHERE isin = ?", [isin]).fetchone():
        raise NewsResponseError(f"No company {isin} in the registry")

    def work(c):
        artifact_id, _ = store_raw_artifact(c, SOURCE_ID, path, retrieved_at, raw_dir=raw_dir)
        new, present, present_count, problems = [], set(), 0, []
        earlier = {}   # url -> (("new", index) or ("stored", article_id), fields)
        for number, article in enumerate(articles, 1):
            try:
                values = _parse_article(article, start, end, retrieved)
            except (ValueError, KeyError) as e:
                problems.append(("article_refused", f"article {number}: {e}"))
                continue
            if values[0] not in earlier:
                stored = c.execute("SELECT article_id, title, domain, language, source_country, seen_at"
                                   " FROM nw_articles WHERE url = ?", [values[0]]).fetchone()
                if stored:
                    earlier[values[0]] = (("stored", stored[0]), list(stored[1:]))
            if values[0] in earlier:
                ref, fields = earlier[values[0]]
                if fields == values[1:6]:
                    present.add(ref)
                    present_count += 1
                else:
                    problems.append(("article_conflict", f"article {number}: {values[0][:90]} was returned"
                                     " before with a different headline, site or time"))
                continue
            earlier[values[0]] = (("new", len(new)), values[1:6])
            new.append(values)
        response_id = c.execute(
            "INSERT INTO nw_responses (artifact_id, isin, query, window_start, window_end, articles, complete,"
            " articles_recorded, already_present, articles_refused, recorded_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [artifact_id, isin, query, start.isoformat(), end.isoformat(), len(articles),
             int(len(articles) < MAX_ARTICLES), len(new), present_count, len(problems), now_utc()]).lastrowid
        ids = []
        for values in new:
            ids.append(c.execute(
                "INSERT INTO nw_articles (url, title, domain, language, source_country, seen_at, available_at,"
                " response_id, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                values + [response_id, now_utc()]).lastrowid)
        returned = set(ids) | {ids[i] if kind == "new" else i for kind, i in present}
        c.executemany("INSERT INTO nw_retrievals VALUES (?, ?)", [(response_id, a) for a in sorted(returned)])
        c.executemany("INSERT INTO nw_problems VALUES (?, ?, ?)", [(response_id, k, d) for k, d in problems])
        extract(c)
        shown = [f"{k}: {d}" for k, d in problems[:PROBLEMS_SHOWN]]
        if len(problems) > PROBLEMS_SHOWN:
            shown.append(f"... and {len(problems) - PROBLEMS_SHOWN} more (table nw_problems, response {response_id})")
        return {"response_id": response_id, "articles": len(articles), "complete": len(articles) < MAX_ARTICLES,
                "articles_recorded": len(new), "already_present": present_count, "articles_refused": len(problems),
                "problems": shown}

    return run_in_transaction(conn, work)


# ---- stories (rule nw-dedup-1) ------------------------------------------------------

def distinctive_headline(headline_words):
    """True when a headline is long enough to identify one story."""
    return len(headline_words) >= MIN_DISTINCTIVE_WORDS and len(" ".join(headline_words)) >= MIN_DISTINCTIVE_CHARS


def stories(conn, decision_time, claim=PitClaim.CURRENT_DECISION, isin=None):
    """The news stories known at decision_time under the claim (5B.2), oldest first. Each story is one
    or more copies of the same headline, with the companies it names and how sure the reading is
    (extraction confidence). With isin, only stories naming that company or returned by a search
    for it."""
    run_id = current_run(conn)
    if run_id is None:
        raise NewsNotReadError("The articles have not been read with the current news names - run extract()")
    rows = conn.execute(
        "SELECT a.article_id, a.url, a.title, a.domain, a.language, a.available_at, f.retrieved_at"
        " FROM nw_articles a JOIN nw_responses r ON r.response_id = a.response_id"
        " JOIN raw_artifacts f ON f.artifact_id = r.artifact_id").fetchall()
    known = [r for r in rows if disposition(claim, decision_time, r[6], r[5]) == Availability.ELIGIBLE]
    known.sort(key=lambda r: (r[5], r[0]))
    found = {}
    for article_id, isin_, role, confidence, evidence in conn.execute(
            "SELECT article_id, isin, role, extraction_confidence, evidence FROM nw_extractions WHERE run_id = ?",
            [run_id]):
        found.setdefault(article_id, []).append((isin_, role, confidence, evidence))
    searched = {}
    for article_id, isin_ in conn.execute("SELECT t.article_id, r.isin FROM nw_retrievals t"
                                          " JOIN nw_responses r ON r.response_id = t.response_id"):
        searched.setdefault(article_id, set()).add(isin_)
    groups, open_story = [], {}
    for article_id, url, title, domain, language, available, _ in known:
        when = parse_timestamp(available)
        headline = words(title)
        key = " ".join(headline) if distinctive_headline(headline) else None
        current = open_story.get(key) if key else None
        copy = {"article_id": article_id, "domain": domain, "available_at": available, "url": url}
        if current is not None and when - current["first"] <= DEDUP_WINDOW:
            current["copies"].append(copy)
            continue
        story = {"first": when, "headline": title, "language": language, "copies": [copy]}
        groups.append(story)
        if key:
            open_story[key] = story
    rating = get_source(conn, SOURCE_ID)["reliability_rating"]
    result = [_story(s, found, searched, rating) for s in groups]
    if isin:
        result = [s for s in result if isin in s["companies"] or isin in s["searched_for"]]
    return result


def _story(story, found, searched, rating):
    companies, best = {}, {"subject": 0, "mentioned": 1}
    searched_for = set()
    for copy in story["copies"]:
        searched_for |= searched.get(copy["article_id"], set())
        for isin, role, confidence, evidence in found.get(copy["article_id"], []):
            if isin is None:
                continue
            held = companies.get(isin)
            if held is None or best[role] < best[held["role"]]:
                companies[isin] = {"role": role, "extraction_confidence": confidence, "evidence": evidence,
                                   "article_id": copy["article_id"]}
    first = story["copies"][0]
    return {
        "story_id": first["article_id"], "published_at": first["available_at"], "headline": story["headline"],
        "language": story["language"], "copies": story["copies"], "companies": companies,
        "unassigned": not companies, "searched_for": sorted(searched_for),
        "novelty": {"copies": len(story["copies"]), "sites": len({c["domain"] for c in story["copies"]}),
                    "rule": DEDUP_RULE, "repeats_an_exchange_filing": NOT_ASSESSED},
        "source_quality": {"source": SOURCE_ID, "reliability_rating": rating, "site_quality": NOT_ASSESSED},
        "event_type": NOT_ASSESSED, "direction": NOT_ASSESSED, "materiality": NOT_ASSESSED,
        "expected_horizon": NOT_ASSESSED, "entity_rule": ENTITY_RULE,
    }
