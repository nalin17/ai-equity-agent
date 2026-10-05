"""Intake of hand-downloaded NSE files and a download checklist (architecture 4, 5B.2, ADR-004).

NSE's Terms of Use prohibit systematic or automated data collection, so every NSE file
is downloaded by a person (ADR-004). This module only removes the clerical work around
that, and it never contacts any website:
  - collect_downloads: move recognised NSE files from the browser's download folder into
    the inbox, undoing the browser's ' (1)' renaming. A newer download of a file whose name
    NSE reuses (the equity list, listings) is kept beside the old one under a content tag;
  - ingest_inbox: load every inbox file not ingested yet, in dependency order - equity
    list, corporate actions, announcements, prices by trade date, results listings, then results files
    in the order NSE published them, then FII/DII flow files in the order they were downloaded. A results file whose listing row is not loaded waits:
    once stored without it, its publication time could never be proven (5B);
  - checklist_items / write_checklist: from listings already downloaded, one page of links
    to the results files (and price files for missing weekdays) not in the inbox or database.
A file is 'ingested' when its exact bytes are in raw_artifacts (section 4).
"""
import html
import re
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from core.dates import strict_iso_date
from ingestion.market_adapters import ingest_market_file, read_raw_table
from ingestion.nse_announcements import load_announcements
from ingestion.nse_corporate_actions import load_corporate_actions, normalise_name
from ingestion.nse_financial_results import NSE_ARCHIVE, load_results_index, load_results_xbrl
from ingestion.nse_flows import load_flows
from provenance.raw_store import sha256_bytes
from universe.equity_list import load_equity_list

BROWSER_COPY = re.compile(r" \(\d+\)(?=\.[^.]+$)")   # 'file (1).xml' -> 'file.xml'
BHAVCOPY_URL = NSE_ARCHIVE + "content/cm/BhavCopy_NSE_CM_0_0_0_{}_F_0000.csv.zip"

# (kind, file-name pattern, load order). Anything else is left alone.
KINDS = (
    ("equity_list", re.compile(r"^EQUITY_L(__[0-9a-f]{8})?\.csv$"), 1),
    ("corporate_actions", re.compile(r"^CF-CA-equities-.+\.csv$"), 2),
    ("announcements", re.compile(r"^CF-AN-.+\.csv$"), 3),
    ("prices", re.compile(r"^BhavCopy_NSE_CM_0_0_0_(\d{8})_F_0000\.csv(\.zip)?$"), 4),
    ("results_listing", re.compile(r"^CF-(FR|Integrated-Filing)-.+\.csv$"), 5),
    ("results", re.compile(r"^(INDAS|INTEGRATED_FILING)_[A-Za-z0-9_]+\.xml$"), 6),
    ("flows", re.compile(r"^fii-dii-(nse|combined)-latest(__[0-9a-f]{8})?\.csv$"), 7),
)
REUSED_NAMES = {"equity_list", "corporate_actions", "announcements", "results_listing", "flows"}   # NSE reuses these names
LOADERS = {
    "equity_list": load_equity_list,
    "corporate_actions": load_corporate_actions,
    "announcements": load_announcements,
    "prices": ingest_market_file,
    "results_listing": load_results_index,
    "results": load_results_xbrl,
    "flows": load_flows,
}


def clean_name(name):
    return BROWSER_COPY.sub("", name)


def kind_of(name):
    """(kind, match) for a recognised NSE file name, else (None, None)."""
    for kind, pattern, _ in KINDS:
        match = pattern.match(name)
        if match:
            return kind, match
    return None, None


def collect_downloads(downloads_dir, inbox_dir):
    """Move recognised NSE files into the inbox. Nothing is overwritten or deleted.
    Returns {'moved': [...], 'already_in_inbox': [...], 'name_clash': [...]}."""
    downloads_dir, inbox_dir = Path(downloads_dir), Path(inbox_dir)
    inbox_dir.mkdir(parents=True, exist_ok=True)
    report = {"moved": [], "already_in_inbox": [], "name_clash": []}
    for path in sorted(p for p in downloads_dir.iterdir() if p.is_file()):
        name = clean_name(path.name)
        kind = kind_of(name)[0]
        if kind is None:
            continue
        target, sha = inbox_dir / name, sha256_bytes(path.read_bytes())
        if target.exists() and sha256_bytes(target.read_bytes()) != sha and kind in REUSED_NAMES:
            target = target.with_name(f"{target.stem}__{sha[:8]}{target.suffix}")
        if not target.exists():
            shutil.move(str(path), str(target))
            report["moved"].append(target.name)
        elif sha256_bytes(target.read_bytes()) == sha:
            report["already_in_inbox"].append(path.name)
        else:
            report["name_clash"].append(path.name)
    return report


def _ingested(conn):
    return {r[0] for r in conn.execute("SELECT sha256 FROM raw_artifacts")}


def _published_order(conn, name):
    """When NSE disseminated this results file, per a loaded listing ('~' sorts unknown last)."""
    row = conn.execute("SELECT disseminated_at FROM if_filings WHERE xbrl_file_name = ? UNION ALL"
                       " SELECT disseminated_at FROM fr_filings WHERE xbrl_file_name = ?", [name, name]).fetchone()
    return row[0] if row else "~"


def ingest_inbox(conn, inbox_dir, raw_dir=None, now=None, require_listing=True):
    """Load every recognised inbox file whose bytes are not in the database yet. Returns a list
    of (file name, kind, outcome, detail); outcome is loaded, failed, waiting or skipped."""
    now = now or (lambda: datetime.now(timezone.utc))
    inbox_dir = Path(inbox_dir)
    ingested = _ingested(conn)
    pending, results = {}, []
    for path in sorted(p for p in inbox_dir.iterdir() if p.is_file()):
        kind, match = kind_of(path.name)
        if kind is None:
            results.append((path.name, None, "skipped", "not a recognised NSE file name"))
        elif sha256_bytes(path.read_bytes()) in ingested:
            results.append((path.name, kind, "skipped", "already ingested"))
        else:
            pending.setdefault(kind, []).append((path, match))
    for kind, _, _ in sorted(KINDS, key=lambda k: k[2]):
        files = pending.get(kind, [])
        if kind == "prices":
            files.sort(key=lambda f: f[1].group(1))
        elif kind == "results":
            files.sort(key=lambda f: (_published_order(conn, f[0].name), f[0].name))
        elif kind == "flows":   # download order only orders the loading; availability is the ingestion (5B)
            files.sort(key=lambda f: (f[0].stat().st_mtime, f[0].name))
        for path, _ in files:
            if kind == "results" and require_listing and _published_order(conn, path.name) == "~":
                results.append((path.name, kind, "waiting", "its listing row is not loaded - download the"
                                " listing first (or load it without one using --without-listing)"))
                continue
            try:
                outcome = LOADERS[kind](conn, path, now(), raw_dir=raw_dir)
                results.append((path.name, kind, "loaded", outcome))
            except Exception as e:  # report and carry on; each loader stores nothing partial
                results.append((path.name, kind, "failed", f"{type(e).__name__}: {e}"))
    return results


# ---- the checklist ----------------------------------------------------------

def _listing_links(path):
    """(symbol or company, period, basis, submission, XBRL link) for every row of a results listing."""
    header, rows = read_raw_table(path)
    integrated = "XBRL" in header and "SYMBOL" in header
    if not integrated and "** XBRL" not in header:
        raise ValueError(f"{Path(path).name}: not an NSE results listing")
    for _, row in rows:
        url = (row.get("XBRL" if integrated else "** XBRL") or "").strip()
        if not (url.startswith(NSE_ARCHIVE) and url.lower().endswith(".xml")):
            continue
        yield {
            "who": row["SYMBOL"].strip() if integrated else row["COMPANY NAME"].strip(),
            "symbol": row["SYMBOL"].strip() if integrated else None,
            "company": row["COMPANY NAME"].strip(),
            "period": (row.get("QUARTER END DATE") or row.get("PERIOD ENDED") or "").strip(),
            "basis": (row.get("CONSOLIDATED / STANDALONE") or row.get("CONSOLIDATED / NON-CONSOLIDATED") or "").strip(),
            "submission": (row.get("TYPE OF SUBMISSION") or "Original").strip(),
            "url": url,
            "file": url.rsplit("/", 1)[1],
        }


def _weekdays(start, end):
    day = start
    while day <= end:
        if day.weekday() < 5:
            yield day
        day += timedelta(days=1)


def _period_date(text):
    return datetime.strptime(text, "%d-%b-%Y").date()


def checklist_items(conn, listing_paths, inbox_dir, symbols=None, since=None, prices_from=None, today=None):
    """Every file a person still has to download, with its status. Returns a list of dicts."""
    inbox = {p.name for p in Path(inbox_dir).iterdir() if p.is_file()} if Path(inbox_dir).exists() else set()
    in_db = {r[0] for r in conn.execute("SELECT original_name FROM raw_artifacts")}
    wanted = {s.strip().upper() for s in symbols} if symbols else None
    names = None
    if wanted:
        names = {normalise_name(r[0]) for r in conn.execute(
            "SELECT e.legal_name FROM entities e JOIN entity_aliases a ON a.isin = e.isin"
            f" WHERE a.alias_type = 'nse_symbol' AND a.alias_value IN ({', '.join('?' * len(wanted))})",
            sorted(wanted))}
    items, seen = [], set()
    for path in listing_paths:
        for link in _listing_links(path):
            if link["file"] in seen:
                continue
            if wanted and not (link["symbol"] in wanted if link["symbol"] else normalise_name(link["company"]) in names):
                continue
            if since and _period_date(link["period"]) < strict_iso_date(since):
                continue
            seen.add(link["file"])
            link["status"] = ("in database" if link["file"] in in_db else
                              "in inbox, not loaded yet" if link["file"] in inbox else "to download")
            items.append(link)
    if prices_from:
        last = (today or date.today()) - timedelta(days=1)
        for day in _weekdays(strict_iso_date(prices_from), last):
            name = f"BhavCopy_NSE_CM_0_0_0_{day:%Y%m%d}_F_0000.csv.zip"
            items.append({"who": "prices", "symbol": None, "company": "NSE bhavcopy", "period": day.isoformat(),
                          "basis": "", "submission": "", "url": BHAVCOPY_URL.format(f"{day:%Y%m%d}"), "file": name,
                          "status": ("in database" if name in in_db else
                                     "in inbox, not loaded yet" if name in inbox else "to download")})
    return items


def write_checklist(items, out_path):
    """A plain local HTML page of links for a person to click. Returns the number still to download."""
    todo = [i for i in items if i["status"] == "to download"]
    rows = []
    for i in sorted(items, key=lambda i: (i["status"] != "to download", i["who"], i["period"], i["file"])):
        link = (f'<a href="{html.escape(i["url"])}">{html.escape(i["file"])}</a>' if i["status"] == "to download"
                else html.escape(i["file"]))
        rows.append(f'<tr class="{"todo" if i["status"] == "to download" else "done"}"><td>{html.escape(i["who"])}</td>'
                    f'<td>{html.escape(i["period"])}</td><td>{html.escape(i["basis"])}</td>'
                    f'<td>{html.escape(i["submission"])}</td><td>{link}</td><td>{html.escape(i["status"])}</td></tr>')
    page = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>NSE download checklist</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; background: #fff; color: #222; }}
table {{ border-collapse: collapse; }} td, th {{ border: 1px solid #ccc; padding: 4px 8px; text-align: left; }}
tr.done td {{ color: #888; }} a:visited {{ color: #888; }}
</style></head><body>
<h1>NSE download checklist</h1>
<p><b>{len(todo)}</b> file(s) to download, {len(items) - len(todo)} already in the inbox or database.</p>
<p>Hold <b>Alt</b> and click each link to save it straight to Downloads (Chrome and Edge),
or right-click it and choose <i>Save link as</i>. Clicked links turn grey.
Weekday price files for exchange holidays do not exist - skip any that fail.</p>
<p>Then run: <code>python manage.py ingest-inbox</code></p>
<table><tr><th>Company / file</th><th>Period</th><th>Basis</th><th>Submission</th><th>File</th><th>Status</th></tr>
{chr(10).join(rows)}
</table></body></html>
"""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(page, encoding="utf-8")
    return len(todo)
