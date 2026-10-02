"""Strict calendar dates - the one date parser for the whole project.

Python's date.fromisoformat() also accepts '20240101' and '2024-W01-1'.
Dates are stored and compared as text, so a compact or week-form date sorts
wrongly ('20200101' comes AFTER '2020-06-01') and silently breaks every
point-in-time comparison. Only the canonical form YYYY-MM-DD is accepted.

Found during Stage 6; the static test in tests/test_static_rules.py keeps
every other module from parsing dates by itself (architecture 40D rule 3).
"""
import re
from datetime import date

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def strict_iso_date(value):
    """Return a date for a canonical 'YYYY-MM-DD' string, otherwise raise ValueError."""
    if not isinstance(value, str) or not ISO_DATE.match(value):
        raise ValueError(f"Not a YYYY-MM-DD date: {value!r}")
    return date.fromisoformat(value)
