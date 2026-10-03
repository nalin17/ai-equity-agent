"""Market time zones and session closes (architecture 5C, criteria 90-91).

Markets close at different hours: the US session ends after midnight India time, so a US close
dated 3 October did not exist during the Indian session of 3 October. A value is placed in time by
its session close in its own time zone, converted to UTC - never by its calendar date.

Python's zoneinfo has no time-zone database on Windows unless an extra package is installed, so the
few zones this project needs are declared here. Each rule was checked day by day against Windows'
own time-zone rules for 2007-2040. A zone that is not declared, a date before its rule applies, or a
time inside a daylight-saving changeover is refused - never guessed.

  America/New_York  UTC-5, and UTC-4 from the second Sunday of March to the first Sunday of
                    November (US rule since 2007)
  Asia/Tokyo        UTC+9, no daylight saving
  Asia/Kolkata      UTC+5:30, no daylight saving
  UTC
"""
import re
from datetime import date, datetime, time, timedelta, timezone

from core.dates import strict_iso_date

UTC = timezone.utc
US_RULE_FROM = date(2007, 3, 11)   # the US rule above applies from this date (Energy Policy Act 2005)
CHANGEOVER = (time(1, 0), time(3, 0))   # local times refused on a daylight-saving changeover day
HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

ZONES = {   # zone -> (standard offset, daylight-saving rule)
    "America/New_York": (timedelta(hours=-5), "us"),
    "Asia/Tokyo": (timedelta(hours=9), None),
    "Asia/Kolkata": (timedelta(hours=5, minutes=30), None),
    "UTC": (timedelta(0), None),
}


class SessionError(ValueError):
    """A time zone, date or session time cannot be placed in time safely."""


def _nth_sunday(year, month, n):
    first = date(year, month, 1)
    return first + timedelta(days=(6 - first.weekday()) % 7 + 7 * (n - 1))


def _us_changeovers(day):
    if day < US_RULE_FROM:
        raise SessionError(f"{day} is before {US_RULE_FROM}, when the current US daylight-saving rule began")
    return _nth_sunday(day.year, 3, 2), _nth_sunday(day.year, 11, 1)


def utc_offset(zone, day, clock=time(12, 0)):
    """The offset from UTC in force in zone at local time clock on day (a date or 'YYYY-MM-DD')."""
    if zone not in ZONES:
        raise SessionError(f"Time zone {zone!r} is not declared in core/sessions.py")
    day = strict_iso_date(day) if isinstance(day, str) else day
    standard, rule = ZONES[zone]
    if rule != "us":
        return standard
    start, end = _us_changeovers(day)
    if day in (start, end) and CHANGEOVER[0] <= clock < CHANGEOVER[1]:
        raise SessionError(f"{clock:%H:%M} on {day} falls inside a daylight-saving changeover in {zone}")
    daylight = (start < day or (day == start and clock >= CHANGEOVER[1])) and \
               (day < end or (day == end and clock < CHANGEOVER[0]))
    return standard + timedelta(hours=1) if daylight else standard


def local_to_utc(day, hhmm, zone):
    """The UTC moment of local time hhmm ('HH:MM') on day in zone."""
    if not isinstance(hhmm, str) or not HHMM.match(hhmm):
        raise SessionError(f"Not a time of day in HH:MM form: {hhmm!r}")
    day = strict_iso_date(day) if isinstance(day, str) else day
    clock = time(int(hhmm[:2]), int(hhmm[3:]))
    offset = utc_offset(zone, day, clock)
    return datetime.combine(day, clock, tzinfo=timezone(offset)).astimezone(UTC)
