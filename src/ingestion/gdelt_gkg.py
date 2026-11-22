"""Headlines from GDELT's bulk GKG 2.1 files: India-relevant articles, the companies their headlines name, and
copies of one story (architecture 40B step 10, 4B, 4D, 5B; ADR-013).

Input: one GKG file (YYYYMMDDHHMMSS.gkg.csv.zip, 15 minutes of the world's news), fetched by the news fetcher -
the only module allowed to use the network - from data.gdeltproject.org. GDELT's terms allow any use, with
citation (ADR-005). Article links are never opened and article text is never read: only the link, the page
title GDELT recorded (PAGE_TITLE in V2EXTRASXML), the outlet's site, GDELT's time and GDELT's tone are used.

Rules, each found on GDELT's real files (5 files of 6 and 8 Nov 2026, data/handover/research/gkg_sample):
  - The raw file is not kept (about 0.4 GB a day): the file's name, size, md5 and sha256 are recorded, with
    GDELT's own md5 when lastupdate.txt listed it - a different md5 refuses the file. Only India-relevant rows
    are stored (rule gk-keep-1): located in India (a V1LOCATIONS entry with country code IN), from an Indian
    outlet (a declared list of sites), or with a declared news name in the headline.
  - A file is used whole or not at all: it must be a zip holding exactly one member, <slot>.gkg.csv, of UTF-8
    text whose every row has 27 tab-separated fields and GDELT's DATE equal to the file's slot. Otherwise the
    format has changed and nothing is stored (4C: refuse, never repair).
  - A row without a web link, a headline or a readable tone is refused and recorded; a link is stored once,
    from the first file carrying it. The same link later with another headline is a conflict, recorded.
  - Availability (5B): GDELT's DATE is the 15-minute slot in which it processed the article; an article is taken
    as public 15 minutes after it, or at our retrieval if that is earlier - never sooner (as for the DOC API).
    The page's own timestamp (PAGE_PRECISEPUBTIMESTAMP) is kept as a claim, never as proof.
  - Headlines are data, never instruction (4D): stored verbatim (HTML entities as GDELT wrote them) and only
    ever compared, after decoding the entities.
  - Which company a headline is about is rule nw-entity-1 of Stage 10 (gdelt_news.EntityReader), unchanged:
    'subject' only when a declared news name is in both the headline and the link, alone and not one item of a
    list; otherwise 'mentioned' or 'unassigned' - never guessed (4B.4).
  - One story is one vote (rule nw-dedup-1 of Stage 10, unchanged): copies share a distinctive headline word
    for word and arrive within 72 hours of the first copy.
  - GDELT's tone (V1.5TONE) is the tone of the whole article. It is stored as article tone and never used as
    sentiment toward a company (4B.5).
"""
import hashlib
import html
import io
import math
import re
import zipfile
from datetime import datetime, timedelta, timezone

from core.database import now_utc, run_in_transaction
from ingestion.gdelt_news import (DEDUP_RULE, DEDUP_WINDOW, ENTITY_RULE, EntityReader, distinctive_headline,
                                  words)
from ingestion.market_adapters import AdapterError
from ingestion.source_registry import get_source
from provenance.availability import Availability, PitClaim, disposition, parse_timestamp

SOURCE_ID = "gdelt_gkg"
KEEP_RULE = "gk-keep-1"
FILE_NAME = re.compile(r"^(\d{14})\.gkg\.csv\.zip$")
SLOT = timedelta(minutes=15)
MIN_AGE = timedelta(minutes=75)     # Google's cache keeps a 404 for up to an hour for a file asked for too early
FIELDS = 27
MAX_ZIP_BYTES = 60_000_000          # GDELT's GKG files measured 3-8 MB zipped
MAX_TEXT_BYTES = 250_000_000        # and 8-13 MB unzipped
WEB_COLLECTION = "1"                # SourceCollectionIdentifier 1 = the web
TITLE = re.compile(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>", re.S)
STATED = re.compile(r"<PAGE_PRECISEPUBTIMESTAMP>(\d{14})</PAGE_PRECISEPUBTIMESTAMP>")
MD5 = re.compile(r"^[0-9a-f]{32}$")
PROBLEMS_SHOWN = 10
# Indian outlets (rule gk-keep-1): a site ending in .in, or one of these sites or a sub-site of one.
INDIAN_SITES = frozenset({
    "indiatimes.com", "livemint.com", "business-standard.com", "moneycontrol.com", "thehindu.com",
    "thehindubusinessline.com", "ndtv.com", "ndtvprofit.com", "financialexpress.com", "hindustantimes.com",
    "news18.com", "cnbctv18.com", "zeebiz.com", "indianexpress.com", "newindianexpress.com", "deccanherald.com",
    "deccanchronicle.com", "firstpost.com", "outlookindia.com", "outlookbusiness.com", "telegraphindia.com",
    "tribuneindia.com", "dnaindia.com", "mid-day.com", "thestatesman.com", "dailypioneer.com", "thequint.com",
    "republicworld.com", "wionews.com", "asianage.com", "siasat.com", "freepressjournal.in", "bqprime.com",
})


class GkgFileError(AdapterError):
    """A GKG file cannot be used as a whole. Nothing is stored."""


class GkgNotReadError(Exception):
    """The stored headlines have not been read with the current news names yet - run extract()."""


# ---- files and rows ------------------------------------------------------------------------------------

def slot_of(file_name):
    """The UTC slot of a GKG file name, or GkgFileError."""
    match = FILE_NAME.match(file_name or "")
    if not match:
        raise GkgFileError(f"{file_name!r} is not a GKG file name (YYYYMMDDHHMMSS.gkg.csv.zip)")
    try:
        slot = datetime.strptime(match[1], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError:
        raise GkgFileError(f"{file_name!r} does not name a real time") from None
    if slot.minute % 15 or slot.second:
        raise GkgFileError(f"{file_name!r} is not on a 15-minute slot")
    return slot


def file_name_for(slot):
    return f"{slot:%Y%m%d%H%M%S}.gkg.csv.zip"


def read_lastupdate(body):
    """{file_name: (size, md5)} of the GKG files GDELT's lastupdate.txt lists, or GkgFileError."""
    try:
        text = body.decode("ascii")
    except UnicodeDecodeError:
        raise GkgFileError("lastupdate.txt is not plain text") from None
    listed = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 3:
            if line.strip():
                raise GkgFileError(f"lastupdate.txt line not 'size md5 url': {line[:80]!r}")
            continue
        size, md5, url = parts
        name = url.rsplit("/", 1)[-1]
        if not name.endswith(".gkg.csv.zip"):
            continue
        if not size.isdigit() or not MD5.match(md5) or not url.startswith(("http://data.gdeltproject.org/gdeltv2/",
                                                                           "https://data.gdeltproject.org/gdeltv2/")):
            raise GkgFileError(f"lastupdate.txt GKG line unreadable: {line[:80]!r}")
        slot_of(name)
        listed[name] = (int(size), md5)
    if not listed:
        raise GkgFileError("lastupdate.txt lists no GKG file")
    return listed


def read_gkg(data, file_name):
    """The rows (lists of 27 texts) of one GKG file (bytes), or GkgFileError - nothing in between."""
    slot = slot_of(file_name)
    if len(data) > MAX_ZIP_BYTES:
        raise GkgFileError(f"{file_name} is {len(data):,} bytes, more than the {MAX_ZIP_BYTES:,} allowed")
    member = file_name.removesuffix(".zip")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            infos = z.infolist()
            if [i.filename for i in infos] != [member]:
                raise GkgFileError(f"{file_name} must hold exactly one file, {member}")
            if infos[0].file_size > MAX_TEXT_BYTES:
                raise GkgFileError(f"{member} unzips to {infos[0].file_size:,} bytes - refused")
            raw = z.read(member)   # checks the zip's CRC
    except (zipfile.BadZipFile, zipfile.LargeZipFile, EOFError, ValueError) as e:
        raise GkgFileError(f"{file_name} is not a readable zip: {e}") from None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise GkgFileError(f"{member} is not UTF-8 text") from None
    stamp = f"{slot:%Y%m%d%H%M%S}"
    rows = []
    for number, line in enumerate(text.split("\n"), 1):
        if not line:
            continue
        row = line.split("\t")
        if len(row) != FIELDS:
            raise GkgFileError(f"{member} row {number} has {len(row)} fields, not {FIELDS} - the format has changed")
        if row[1] != stamp:
            raise GkgFileError(f"{member} row {number} is dated {row[1][:20]!r}, not the file's slot {stamp}")
        rows.append(row)
    if not rows:
        raise GkgFileError(f"{member} has no rows")
    return rows


def india_located(locations):
    """True when a V1LOCATIONS entry (type#name#country#adm1#lat#long#feature) has country code IN."""
    for entry in filter(None, locations.split(";")):
        parts = entry.split("#")
        if len(parts) >= 3 and parts[2] == "IN":
            return True
    return False


def indian_outlet(site):
    site = site.strip().lower()
    return site.endswith(".in") or any(site == s or site.endswith("." + s) for s in INDIAN_SITES)


def headline_of(extras):
    """The page title GDELT recorded, verbatim, or None."""
    match = TITLE.search(extras)
    return match[1].strip() if match and plain(match[1]) else None


def plain(title):
    """A stored headline with its HTML entities decoded - for comparing and showing, never for storing."""
    return " ".join(html.unescape(title).split())


def _tone(text):
    parts = text.split(",")
    if len(parts) < 7:
        raise ValueError(f"tone {text[:40]!r} has {len(parts)} values, not 7")
    value = float(parts[0])
    if not math.isfinite(value):
        raise ValueError("tone is not a finite number")
    return value


def parse_row(row, slot, retrieved):
    """[record_id, url, title, site, seen_at, available_at, stated, tone, tone_text] of one row, or ValueError."""
    if row[2] != WEB_COLLECTION:
        raise ValueError(f"collection {row[2][:10]!r} is not the web")
    url = row[4].strip()
    if not url.startswith(("https://", "http://")) or any(ch.isspace() for ch in url):
        raise ValueError(f"not a web link: {url[:80]!r}")
    title = headline_of(row[26])
    if title is None:
        raise ValueError(f"no headline: {url[:80]}")
    site = row[3].strip()
    if not site:
        raise ValueError(f"no site: {url[:80]}")
    tone = _tone(row[15])
    stated = STATED.search(row[26])
    available = min(slot + SLOT, retrieved)
    return [row[0].strip(), url, title, site, slot.isoformat(), available.isoformat(), stated[1] if stated else None,
            tone, row[15].strip()]


# ---- storing one file ---------------------------------------------------------------------------------

def load_gkg(conn, file_name, data, retrieved_at, md5_listed=None):
    """Store the India-relevant rows of one GKG file (bytes) and read their headlines. Returns a report dict.
    Nothing is stored unless the whole file passes its checks."""
    get_source(conn, SOURCE_ID)
    slot = slot_of(file_name)
    retrieved = parse_timestamp(retrieved_at).astimezone(timezone.utc)   # every stored time in UTC: they sort as text
    if retrieved < slot:
        raise GkgFileError(f"{file_name} cannot have been obtained before its own slot")
    md5, sha256 = hashlib.md5(data).hexdigest(), hashlib.sha256(data).hexdigest()
    if md5_listed is not None and md5_listed != md5:
        raise GkgFileError(f"{file_name}: md5 {md5} differs from GDELT's listing {md5_listed} - nothing stored")
    stored = conn.execute("SELECT sha256 FROM gk_files WHERE file_name = ?", [file_name]).fetchone()
    if stored:
        if stored[0] == sha256:
            return {"file": file_name, "note": "already stored - nothing new", "problems": []}
        raise GkgFileError(f"{file_name} was stored before with other bytes - nothing stored")
    rows = read_gkg(data, file_name)
    reader = EntityReader(conn)

    def work(c):
        kept, present, problems, earlier = [], 0, [], {}
        for number, row in enumerate(rows, 1):
            located, outlet = india_located(row[9]), indian_outlet(row[3])
            title = headline_of(row[26])
            declared = bool(title) and any(d for _, _, d, _, _ in reader.find(words(plain(title)), slot.date().isoformat()))
            if not (located or outlet or declared):
                continue
            try:
                values = parse_row(row, slot, retrieved)
            except ValueError as e:
                problems.append(("row_refused", f"row {number}: {e}"))
                continue
            url = values[1]
            if url in earlier:
                problems.append(("row_refused", f"row {number}: {url[:90]} appears twice in the file"))
                continue
            known = c.execute("SELECT title, source_name FROM gk_articles WHERE url = ?", [url]).fetchone()
            if known:
                if list(known) == [values[2], values[3]]:
                    present += 1
                else:
                    problems.append(("article_conflict", f"row {number}: {url[:90]} was stored before with a"
                                     " different headline or site"))
                continue
            earlier[url] = True
            kept.append(values + [int(located), int(outlet), int(declared)])
        file_id = c.execute(
            "INSERT INTO gk_files (file_name, slot_at, size_bytes, md5, md5_listed, sha256, retrieved_at, rows_total,"
            " rows_kept, rows_present, rows_refused, keep_rule, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [file_name, slot.isoformat(), len(data), md5, md5_listed, sha256, retrieved.isoformat(), len(rows),
             len(kept), present, len(problems), KEEP_RULE, now_utc()]).lastrowid
        for record_id, url, title, site, seen, available, stated, tone, tone_text, located, outlet, declared in kept:
            c.execute("INSERT INTO gk_articles (file_id, record_id, url, title, source_name, seen_at, available_at,"
                      " stated_published, india_located, indian_outlet, names_declared, article_tone, tone_text,"
                      " recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      [file_id, record_id, url, title, site, seen, available, stated, located, outlet, declared, tone,
                       tone_text, now_utc()])
        c.executemany("INSERT INTO gk_problems VALUES (?, ?, ?)", [(file_id, k, d) for k, d in problems])
        extract(c, reader)
        shown = [f"{k}: {d}" for k, d in problems[:PROBLEMS_SHOWN]]
        if len(problems) > PROBLEMS_SHOWN:
            shown.append(f"... and {len(problems) - PROBLEMS_SHOWN} more (table gk_problems, file {file_id})")
        return {"file": file_name, "rows": len(rows), "kept": len(kept), "already_present": present,
                "refused": len(problems), "md5_checked": md5_listed is not None, "problems": shown}

    return run_in_transaction(conn, work)


# ---- reading headlines (rule nw-entity-1) --------------------------------------------------------------

def current_run(conn, reader=None):
    """The extraction run for the news names and registry recorded now, or None if not applied yet."""
    reader = reader or EntityReader(conn)
    row = conn.execute("SELECT run_id FROM gk_extraction_runs WHERE rule = ? AND reader_version = ?",
                       [ENTITY_RULE, reader.version]).fetchone()
    return row[0] if row else None


def extract(conn, reader=None):
    """Read every stored headline not yet read under rule nw-entity-1 with the current news names and registry.
    A change of either starts a new run over all articles; earlier runs stay as history. Returns the run id."""
    reader = reader or EntityReader(conn)
    run_id = current_run(conn, reader)
    if run_id is None:
        run_id = conn.execute(
            "INSERT INTO gk_extraction_runs (rule, reader_version, names_count, started_at) VALUES (?, ?, ?, ?)",
            [ENTITY_RULE, reader.version, len(reader.declared), now_utc()]).lastrowid
    todo = conn.execute(
        "SELECT article_id, title, url, seen_at FROM gk_articles a WHERE NOT EXISTS"
        " (SELECT 1 FROM gk_extractions x WHERE x.run_id = ? AND x.article_id = a.article_id) ORDER BY article_id",
        [run_id]).fetchall()
    when = now_utc()
    for article_id, title, url, seen_at in todo:
        for isin, role, confidence, evidence in reader.read(plain(title), url, seen_at[:10]):
            conn.execute("INSERT INTO gk_extractions VALUES (?, ?, ?, ?, ?, ?, ?)",
                         [run_id, article_id, isin, role, confidence.value, evidence, when])
    return run_id


# ---- stories (rule nw-dedup-1) -------------------------------------------------------------------------

def stories(conn, decision_time, isin, claim=PitClaim.CURRENT_DECISION, since=None):
    """The headline stories naming the company isin, known at decision_time under the claim (5B.2), oldest first.
    A story is one or more copies of the same headline (rule nw-dedup-1). since (UTC ISO) bounds GDELT's time;
    copies up to 72 hours earlier are read so that a story is dated by its first copy."""
    run_id = current_run(conn)
    if run_id is None:
        if conn.execute("SELECT 1 FROM gk_articles LIMIT 1").fetchone() is None:
            return []   # nothing stored, so nothing left unread
        raise GkgNotReadError("The stored GKG headlines have not been read with the current news names - run"
                              " fetch-gkg (it reads them again)")
    floor = (parse_timestamp(since) - DEDUP_WINDOW).astimezone(timezone.utc).isoformat() if since else ""
    rows = conn.execute(
        "SELECT a.article_id, a.url, a.title, a.source_name, a.available_at, f.retrieved_at, a.article_tone,"
        " a.india_located, a.indian_outlet, x.role, x.extraction_confidence, x.evidence FROM gk_extractions x"
        " JOIN gk_articles a ON a.article_id = x.article_id JOIN gk_files f ON f.file_id = a.file_id"
        " WHERE x.run_id = ? AND x.isin = ? AND a.seen_at >= ?", [run_id, isin, floor]).fetchall()
    known = [r for r in rows if disposition(claim, decision_time, r[5], r[4]) == Availability.ELIGIBLE]
    known.sort(key=lambda r: (r[4], r[0]))
    groups, open_story = [], {}
    rank = {"subject": 0, "mentioned": 1}
    for article_id, url, title, site, available, retrieved, tone, located, outlet, role, confidence, evidence in known:
        when = parse_timestamp(available)
        headline = plain(title)
        key = " ".join(words(headline))
        key = key if distinctive_headline(key.split()) else None
        copy = {"article_id": article_id, "site": site, "available_at": available, "retrieved_at": retrieved,
                "url": url, "article_tone": tone, "india_located": bool(located), "indian_outlet": bool(outlet)}
        current = open_story.get(key) if key else None
        if current is not None and when - current["first"] <= DEDUP_WINDOW:
            current["copies"].append(copy)
            if rank[role] < rank[current["role"]]:
                current.update(role=role, extraction_confidence=confidence, evidence=evidence)
            continue
        story = {"first": when, "headline": headline, "copies": [copy], "role": role,
                 "extraction_confidence": confidence, "evidence": evidence}
        groups.append(story)
        if key:
            open_story[key] = story
    return [_story(s) for s in groups]


def _story(story):
    first = story["copies"][0]
    return {"story_id": first["article_id"], "published_at": first["available_at"],
            "retrieved_at": min((c["retrieved_at"] for c in story["copies"]), key=parse_timestamp),
            "headline": story["headline"], "copies": story["copies"],
            "role": story["role"], "extraction_confidence": story["extraction_confidence"],
            "evidence": story["evidence"], "sites": sorted({c["site"] for c in story["copies"]}),
            "article_tone": first["article_tone"], "entity_rule": ENTITY_RULE, "dedup_rule": DEDUP_RULE}


def stored_slots(conn, decision_time, claim, since, until):
    """The UTC slots (ISO) of the GKG files read and known at decision_time under the claim, since <= slot < until."""
    since, until = (parse_timestamp(t).astimezone(timezone.utc).isoformat() for t in (since, until))
    rows = conn.execute("SELECT slot_at, retrieved_at FROM gk_files WHERE slot_at >= ? AND slot_at < ?",
                        [since, until]).fetchall()
    return {slot for slot, retrieved in rows
            if disposition(claim, decision_time, retrieved, (parse_timestamp(slot) + SLOT).isoformat())
            == Availability.ELIGIBLE}
