"""Market calendars: which days a market traded (architecture 5C rule 4; ADR-009).

A missing foreign value on an Indian trading day is a classified absence - structurally absent when
that market was closed - never a carried-forward value presented as fresh. FRED's own listing cannot
prove a closure: on real data it shows the Nasdaq Composite on Good Friday 19-Apr-2019 and the Nikkei
225 on 1-Oct-2020 (the Tokyo exchange's all-day outage), each the previous close repeated. So the
markets whose closes are used are described by declared calendars in config/market_calendars.yaml,
generated from the exchange_calendars library (Apache License 2.0) and checked against NSE's official
holiday list and real FRED data.

Rules:
  - A calendar lists, between coverage_from and coverage_to, the weekdays without a session and the
    weekend days with one. Every other weekday is a session; every other weekend day is not.
  - Outside its coverage a calendar knows nothing: asking raises CalendarError - never guessed.
  - The file is checked whole before use: canonical dates, sorted, no repeats, closed days on
    weekdays, weekend sessions on weekends, all inside coverage, time zones declared in
    core/sessions.py. series_calendars names which calendar decides for which macro series.
"""
from functools import lru_cache
from pathlib import Path

import yaml

from core.config import PROJECT_ROOT
from core.dates import strict_iso_date
from core.sessions import ZONES

CALENDARS_FILE = PROJECT_ROOT / "config" / "market_calendars.yaml"
CALENDAR_KEYS = {"calendar_id", "name", "time_zone", "coverage_from", "coverage_to", "closed_weekdays",
                 "weekend_sessions"}


class CalendarError(ValueError):
    """A calendar file is invalid, or a date lies outside what a calendar covers."""


class Calendar:
    def __init__(self, calendar_id, name, time_zone, coverage_from, coverage_to, closed_weekdays, weekend_sessions):
        self.calendar_id, self.name, self.time_zone = calendar_id, name, time_zone
        self.coverage_from, self.coverage_to = coverage_from, coverage_to
        self.closed_weekdays, self.weekend_sessions = frozenset(closed_weekdays), frozenset(weekend_sessions)

    def covers(self, day):
        return self.coverage_from <= _day(day) <= self.coverage_to

    def is_session(self, day):
        """True when the market traded on day; CalendarError outside the coverage."""
        day = _day(day)
        if not self.covers(day):
            raise CalendarError(f"{self.calendar_id} covers {self.coverage_from} to {self.coverage_to}, not {day}")
        if day.weekday() >= 5:
            return day in self.weekend_sessions
        return day not in self.closed_weekdays


def _day(day):
    return strict_iso_date(day) if isinstance(day, str) else day


def _dates(values, label):
    if not isinstance(values, list):
        raise CalendarError(f"{label} must be a list of YYYY-MM-DD dates")
    try:
        days = [strict_iso_date(v) for v in values]
    except ValueError as e:
        raise CalendarError(f"{label}: {e}") from None
    if days != sorted(set(days)):
        raise CalendarError(f"{label} must be sorted without repeats")
    return days


def check_calendar(entry):
    if not isinstance(entry, dict) or set(entry) != CALENDAR_KEYS:
        raise CalendarError(f"Each calendar needs exactly {sorted(CALENDAR_KEYS)}")
    cid = entry["calendar_id"]
    if not isinstance(cid, str) or not cid.isalnum() or not cid.isupper():
        raise CalendarError(f"{cid!r} is not a calendar id like XNYS")
    if entry["time_zone"] not in ZONES:
        raise CalendarError(f"{cid}: time zone {entry['time_zone']!r} is not declared in core/sessions.py")
    try:
        first, last = strict_iso_date(entry["coverage_from"]), strict_iso_date(entry["coverage_to"])
    except ValueError as e:
        raise CalendarError(f"{cid}: coverage: {e}") from None
    if first > last:
        raise CalendarError(f"{cid}: coverage_from is after coverage_to")
    closed = _dates(entry["closed_weekdays"], f"{cid} closed_weekdays")
    weekend = _dates(entry["weekend_sessions"], f"{cid} weekend_sessions")
    if any(d.weekday() >= 5 for d in closed):
        raise CalendarError(f"{cid}: closed_weekdays may only hold Monday-Friday dates")
    if any(d.weekday() < 5 for d in weekend):
        raise CalendarError(f"{cid}: weekend_sessions may only hold Saturday or Sunday dates")
    if any(not first <= d <= last for d in closed + weekend):
        raise CalendarError(f"{cid}: a listed date lies outside the coverage")
    return Calendar(cid, str(entry["name"]), entry["time_zone"], first, last, closed, weekend)


def load_calendars(path=CALENDARS_FILE):
    """({calendar_id: Calendar}, {series_id: calendar_id}) from the calendar file, checked whole."""
    path = Path(path)
    return _load(str(path), path.stat().st_mtime_ns)


@lru_cache(maxsize=4)
def _load(path, _mtime):
    with open(path, encoding="utf-8-sig") as f:
        data = yaml.safe_load(f) or {}
    if set(data) != {"calendars", "series_calendars"}:
        raise CalendarError("The calendar file needs exactly 'calendars' and 'series_calendars'")
    calendars = {}
    for entry in data["calendars"] or []:
        cal = check_calendar(entry)
        if cal.calendar_id in calendars:
            raise CalendarError(f"{cal.calendar_id} is declared twice")
        calendars[cal.calendar_id] = cal
    mapping = data["series_calendars"] or {}
    if not isinstance(mapping, dict):
        raise CalendarError("series_calendars must map series ids to calendar ids")
    for series_id, cid in mapping.items():
        if cid not in calendars:
            raise CalendarError(f"{series_id} is mapped to an unknown calendar {cid!r}")
    return calendars, dict(mapping)
