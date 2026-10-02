"""Reader for NSE's corporate actions file (CF-CA-equities-*.csv) - architecture 6C.2.

NSE writes the terms of each action as free text in the PURPOSE column. Only
mechanically complete wordings produce a factor; everything else fails closed:

  - "Face Value Split (Sub-Division) - From Rs A/- Per Share To Rs B/- Per Share"
      -> split, A/B new shares per old share. The FACE VALUE column must equal
         A or B (NSE shows the old value before the ex-date and the new value
         after it); anything else is conflicting terms -> unknown (blocked).
  - "Bonus a:b"  -> simple bonus: a new shares for every b held.
  - Ordinary / interim dividends -> dividend; "Buy Back" -> buyback (no adjustment).
  - Any special dividend, rights, demerger, merger, other bonus forms -> blocked.
  - Any other wording, including NSE typos -> unknown (blocked). Never guessed.

The file has no ISIN column. Each row is attached to a company by its symbol AS
OF THE EX-DATE (Stage 3 resolver), and the company name must agree with the
registry; otherwise the row is rejected and recorded, never guessed.

Rows for the same company and ex-date are combined: one action per type, with
all source wordings kept. Contradictory factor terms become 'unknown'.
An action already recorded is never overwritten; a later file that contradicts
it is recorded as a conflict, and a contradicted factor also blocks the window.

This module never reads prices (criterion 64).
"""
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path

from core.database import now_utc, run_in_transaction
from data_quality.trust_chain import NoDataError
from ingestion.corporate_actions import POLICY, record_action
from ingestion.market_adapters import AdapterError, read_raw_table
from ingestion.source_registry import get_source
from provenance.raw_store import store_raw_artifact
from universe.entities import EntityError, resolve

SOURCE_ID = "nse_corporate_actions"
PARSER_VERSION = "nse-ca-parser-1"
REQUIRED_COLUMNS = ("SYMBOL", "COMPANY NAME", "SERIES", "PURPOSE", "FACE VALUE", "EX-DATE")
SCOPE_SERIES = frozenset({"EQ"})
EX_DATE_FORMAT = "%d-%b-%Y"  # e.g. 22-Sep-2026

AMOUNT = r"R[se]\.?\s*\d+(?:\.\d+)?"
DIVIDEND = re.compile(rf"(?:Interim |Final )?Dividend\s*-\s*{AMOUNT}\s*Per Sh(?:are)?", re.IGNORECASE)
SPLIT = re.compile(r"Face Value Split \(Sub-Division\) - From R[se]\.?\s*(\d+(?:\.\d+)?)/- Per Share"
                   r" To R[se]\.?\s*(\d+(?:\.\d+)?)/- Per Share", re.IGNORECASE)
BONUS = re.compile(r"Bonus (\d+):(\d+)", re.IGNORECASE)


class CaFileError(Exception):
    pass


def classify_purpose(purpose, face_value):
    """Return (action_type, shares_before, shares_after, note). Never guesses."""
    p = " ".join((purpose or "").split())
    if re.search(r"special dividend", p, re.IGNORECASE):
        return "special_dividend", None, None, ""
    if DIVIDEND.fullmatch(p):
        return "dividend", None, None, ""
    m = SPLIT.fullmatch(p)
    if m:
        old, new = Decimal(m.group(1)), Decimal(m.group(2))
        try:
            fv = Decimal((face_value or "").strip())
        except InvalidOperation:
            return "unknown", None, None, f"FACE VALUE {face_value!r} is not a number"
        if new <= 0 or old <= new:
            return "unknown", None, None, "split wording, but the face value does not fall"
        if fv not in (old, new):
            return "unknown", None, None, f"FACE VALUE {fv} matches neither 'from' {old} nor 'to' {new}"
        ratio = Fraction(old) / Fraction(new)           # new shares per old share
        return "split", ratio.denominator, ratio.numerator, ""
    m = BONUS.fullmatch(p)
    if m:
        new_shares, held = int(m.group(1)), int(m.group(2))
        if new_shares <= 0 or held <= 0:
            return "unknown", None, None, "bonus ratio with a zero"
        return "bonus", held, held + new_shares, ""
    if re.search(r"\bbonus\b", p, re.IGNORECASE):
        return "complex_bonus", None, None, ""
    if re.match(r"rights\b", p, re.IGNORECASE):
        return "rights", None, None, ""
    if re.fullmatch(r"demerger", p, re.IGNORECASE):
        return "demerger", None, None, ""
    if re.search(r"amalgamation|merger", p, re.IGNORECASE):
        return "merger", None, None, ""
    if re.fullmatch(r"buy ?back", p, re.IGNORECASE):
        return "buyback", None, None, ""
    return "unknown", None, None, "wording not recognised"


def normalise_name(name):
    name = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    name = re.sub(r"\blimited\b", "ltd", name)
    return " ".join(name.split())


def load_corporate_actions(conn, path, retrieved_at, raw_dir=None):
    """Load one downloaded NSE corporate actions file. Returns a report dict."""
    get_source(conn, SOURCE_ID)
    header, rows = read_raw_table(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise AdapterError(f"Not an NSE corporate actions file: missing columns {missing}")
    if not rows:
        raise NoDataError("The corporate actions file has no rows - nothing is stored")
    file_name = Path(path).name

    def work(c):
        artifact_id, _ = store_raw_artifact(c, SOURCE_ID, path, retrieved_at, raw_dir=raw_dir)
        out_of_scope, problems, groups = 0, [], {}
        for row_number, row in rows:
            if (row.get("SERIES") or "").strip() not in SCOPE_SERIES:
                out_of_scope += 1
                continue
            raw = json.dumps(row, sort_keys=True)
            try:
                ex_date = datetime.strptime((row.get("EX-DATE") or "").strip(), EX_DATE_FORMAT).date().isoformat()
            except ValueError:
                problems.append((row_number, "rejected", f"EX-DATE is not DD-Mon-YYYY: {row.get('EX-DATE')!r}", raw))
                continue
            symbol = (row.get("SYMBOL") or "").strip()
            try:
                isin = resolve(c, symbol, ex_date, alias_type="nse_symbol")
            except EntityError as e:
                problems.append((row_number, "rejected", f"symbol not attached to a company: {e}", raw))
                continue
            known = c.execute("SELECT legal_name FROM entities WHERE isin = ?", [isin]).fetchone()[0]
            if normalise_name(known) != normalise_name(row.get("COMPANY NAME")):
                problems.append((row_number, "rejected",
                                 f"company name differs from the registry ({known!r}); possible symbol reuse", raw))
                continue
            action_type, before, after, note = classify_purpose(row.get("PURPOSE"), row.get("FACE VALUE"))
            groups.setdefault((isin, ex_date), []).append(
                (row_number, (row.get("PURPOSE") or "").strip(), action_type, before, after, note))

        counts = {"recorded": 0, "already_present": 0}
        by_treatment = {}
        for (isin, ex_date), items in groups.items():
            by_type = {}
            for item in items:
                by_type.setdefault(item[2], []).append(item)
            for action_type, same in by_type.items():
                terms = " | ".join(dict.fromkeys(i[1] for i in same))
                rows_cited = ", ".join(str(i[0]) for i in same)
                notes = "; ".join(i[5] for i in same if i[5])
                ratios = {(i[3], i[4]) for i in same}
                before, after = next(iter(ratios))
                if POLICY[action_type][1] == "factor" and len(ratios) > 1:
                    action_type, before, after, notes = "unknown", None, None, "contradictory ratios on the same day"
                evidence = f"{file_name} row(s) {rows_cited}; {PARSER_VERSION}" + (f"; {notes}" if notes else "")
                existing = c.execute(
                    "SELECT terms_text, shares_before, shares_after FROM corporate_actions"
                    " WHERE isin = ? AND action_type = ? AND ex_date = ?", [isin, action_type, ex_date]).fetchone()
                if existing:
                    if existing == (terms, before, after):
                        counts["already_present"] += 1
                        continue
                    problems.append((same[0][0], "conflict",
                                     f"{action_type} for {isin} on {ex_date} already recorded as {existing}; "
                                     f"this file says {(terms, before, after)}", json.dumps(terms)))
                    if POLICY[action_type][1] == "factor" and not c.execute(
                            "SELECT 1 FROM corporate_actions WHERE isin = ? AND action_type = 'unknown'"
                            " AND ex_date = ?", [isin, ex_date]).fetchone():
                        record_action(c, isin, "unknown", ex_date, terms, artifact_id,
                                      f"{evidence}; contradicts the recorded {action_type}")
                        counts["recorded"] += 1
                    continue
                record_action(c, isin, action_type, ex_date, terms, artifact_id, evidence, before, after)
                counts["recorded"] += 1
                treatment = POLICY[action_type][1]
                by_treatment[treatment] = by_treatment.get(treatment, 0) + 1

        rejected = sum(1 for p in problems if p[1] == "rejected")
        conflicts = sum(1 for p in problems if p[1] == "conflict")
        load_id = c.execute(
            "INSERT INTO ca_file_loads (artifact_id, parser_version, rows_in_file, rows_out_of_scope,"
            " actions_recorded, already_present, rejected, conflicts, recorded_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [artifact_id, PARSER_VERSION, len(rows), out_of_scope, counts["recorded"],
             counts["already_present"], rejected, conflicts, now_utc()],
        ).lastrowid
        c.executemany("INSERT INTO ca_file_rejections VALUES (?, ?, ?, ?, ?)",
                      [(load_id, n, kind, reason, raw) for n, kind, reason, raw in problems])
        return {
            "load_id": load_id,
            "rows_in_file": len(rows),
            "rows_out_of_scope": out_of_scope,
            "actions_recorded": counts["recorded"],
            "already_present": counts["already_present"],
            "recorded_by_treatment": by_treatment,
            "rejected": rejected,
            "conflicts": conflicts,
            "first_problems": [(n, reason) for n, _, reason, _ in problems[:5]],
        }

    return run_in_transaction(conn, work)
