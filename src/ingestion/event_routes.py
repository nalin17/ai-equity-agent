"""Routes from macro events to securities (architecture 40B step 9b, 4A rule 4, 4A rule 5, 3G rule 4, 9B, 9C;
ADR-010).

A macro, policy or geopolitical event carries its region, never an issuer. It reaches a security only
through a route that is declared and recorded - never through a name in a headline, the query that found
it, or a guess (4A rule 5, acceptance criterion 95). Three kinds of route exist in the architecture:

  read_across            a link declared by the owner in config/event_routes.yaml - for example an oil
                         supply shock to a company whose main input is crude. The evidence it carries is
                         tagged read-across, never a direct observation about the security (4A rule 4).
  sector_membership      needs a point-in-time sector classification (9B). None is registered, so this
                         route is refused - at declaration and in the database (3G rule 4).
  measured_sensitivity   needs a measured sensitivity of the security to the factor the event moves (9C,
                         ACR-106). None is measured yet, so this route is refused too.

Rules:
  - A route is recorded once and never silently changed; a changed declaration is refused whole.
  - A route counts for a decision only once it was recorded (under both claims - a route declared today
    never reaches back into a past decision) and from its valid_from date.
  - A route names an ISIN and the NSE symbol that resolves to it; a mismatch is refused, never guessed.
  - Attribution says how an event reached a security. It never says what the event will do: the effect is
    measured later as an event-response target, never assumed (4A rule 5, 4A rules 1 and 3).
"""
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from core.config import PROJECT_ROOT
from core.database import now_utc, run_in_transaction
from core.dates import strict_iso_date
from ingestion.macro_events import MACRO_TYPES, REGIONS, macro_events
from provenance.availability import PitClaim, parse_timestamp
from universe.entities import EntityError, resolve, validate_isin

ROUTES_FILE = PROJECT_ROOT / "config" / "event_routes.yaml"
ROUTE_RULE = "me-routes-1"
ROUTE_KINDS = ("read_across", "sector_membership", "measured_sensitivity")   # only read_across can be recorded
NOT_YET = {
    "sector_membership": ("no point-in-time sector classification is registered yet (3G rule 4, 9B) - a sector"
                          " route cannot be used until one is"),
    "measured_sensitivity": ("no measured sensitivity is registered yet (9C, ACR-106) - a sensitivity route"
                             " cannot be used until one is"),
}
RELATIONS = ("input_cost", "output_price", "export_revenue", "import_cost", "funding_cost", "demand",
             "regulated_entity", "supplier", "customer", "peer")
ROUTE_KEYS = {"route_key", "kind", "event_type", "region", "symbol", "isin", "relation", "rationale", "valid_from",
              "declared_on"}
ROUTE_REQUIRED = ROUTE_KEYS - {"region"}
ROUTE_KEY = re.compile(r"^[a-z0-9][a-z0-9_-]{2,60}$")
COLUMNS = ("route_key", "kind", "event_type", "region", "isin", "relation", "rationale", "valid_from", "declared_on")


class RouteError(Exception):
    """A route declaration is refused. Nothing is recorded."""


class NoRoute(Exception):
    """An event without an issuer has no declared, recorded route to this security: it is not attributed."""


def _date_text(value, field):
    if isinstance(value, datetime):
        raise RouteError(f"{field} must be a date (YYYY-MM-DD), not a date and time")
    if isinstance(value, date):
        return value.isoformat()
    try:
        return strict_iso_date(value).isoformat()
    except ValueError as e:
        raise RouteError(f"{field}: {e}") from None


def check_route(conn, entry, today):
    """One declared route as a canonical dict, or RouteError."""
    if not isinstance(entry, dict):
        raise RouteError(f"a route is not a mapping: {str(entry)[:60]}")
    key = entry.get("route_key")
    unknown, missing = sorted(set(entry) - ROUTE_KEYS), sorted(ROUTE_REQUIRED - set(entry))
    if unknown or missing:
        raise RouteError(f"{key}: unknown fields {unknown}, missing fields {missing}")
    if not isinstance(key, str) or not ROUTE_KEY.match(key):
        raise RouteError(f"{key!r}: route_key must be 3-61 lower-case letters, digits, - or _")
    if entry["kind"] not in ROUTE_KINDS:
        raise RouteError(f"{key}: kind must be one of {', '.join(ROUTE_KINDS)}")
    if entry["kind"] in NOT_YET:
        raise RouteError(f"{key}: {NOT_YET[entry['kind']]}")
    if entry["event_type"] not in MACRO_TYPES:
        raise RouteError(f"{key}: {entry['event_type']!r} is not a registered macro event type (4A.0)")
    region = entry.get("region")
    if region is not None and region not in REGIONS:
        raise RouteError(f"{key}: region must be one of {', '.join(REGIONS)}")
    if entry["relation"] not in RELATIONS:
        raise RouteError(f"{key}: relation must be one of {', '.join(RELATIONS)}")
    rationale = entry["rationale"]
    if not isinstance(rationale, str) or not 20 <= len(rationale.strip()) <= 300 or "\n" in rationale:
        raise RouteError(f"{key}: rationale must be one line of 20 to 300 characters - why this event reaches"
                         " this company")
    valid_from = _date_text(entry["valid_from"], f"{key}: valid_from")
    declared_on = _date_text(entry["declared_on"], f"{key}: declared_on")
    if declared_on > today.isoformat():
        raise RouteError(f"{key}: declared_on is after today ({today})")
    isin = entry["isin"]
    try:
        validate_isin(isin)
        found = resolve(conn, entry["symbol"], declared_on, alias_type="nse_symbol")
    except (EntityError, TypeError) as e:
        raise RouteError(f"{key}: {e}") from None
    if found != isin:
        raise RouteError(f"{key}: symbol {entry['symbol']} is {found} on {declared_on}, not {isin}")
    return {"route_key": key, "kind": entry["kind"], "event_type": entry["event_type"], "region": region,
            "isin": isin, "relation": entry["relation"], "rationale": rationale.strip(), "valid_from": valid_from,
            "declared_on": declared_on}


def load_routes_file(path=ROUTES_FILE):
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict) or set(data) - {"routes"} or not isinstance(data.get("routes") or [], list):
        raise RouteError(f"{Path(path).name} must hold one list named 'routes'")
    return data.get("routes") or []


def sync_routes(conn, path=ROUTES_FILE, today=None):
    """Record new routes. Every route is checked before anything is written; a recorded route is never
    silently changed. Returns {"recorded": [...], "already_present": n, "not_in_file": [...]}."""
    today = today or datetime.now(timezone.utc).date()
    checked = [check_route(conn, r, today) for r in load_routes_file(path)]
    keys = [r["route_key"] for r in checked]
    if len(set(keys)) != len(keys):
        raise RouteError("a route_key is declared twice")
    stored = {r[0]: r[1] for r in conn.execute("SELECT route_key, entry FROM me_routes")}
    new = []
    for route in checked:
        text = json.dumps(route, sort_keys=True)
        if route["route_key"] in stored:
            if stored[route["route_key"]] != text:
                raise RouteError(f"{route['route_key']} was recorded differently - recorded routes are never"
                                 " silently changed; declare a new route_key instead")
            continue
        new.append(route)

    def work(c):
        c.executemany(f"INSERT INTO me_routes ({', '.join(COLUMNS)}, entry, recorded_at)"
                      f" VALUES ({', '.join('?' for _ in COLUMNS)}, ?, ?)",
                      [[r[k] for k in COLUMNS] + [json.dumps(r, sort_keys=True), now_utc()] for r in new])

    run_in_transaction(conn, work)
    return {"recorded": [r["route_key"] for r in new], "already_present": len(checked) - len(new),
            "not_in_file": sorted(set(stored) - set(keys))}


def attribute(conn, event, isin, decision_time):
    """How one macro event reaches one security at decision_time: the recorded routes it travels, or NoRoute.
    The evidence is tagged by its route and is never a direct observation about the security."""
    if event.get("issuer") is not None:
        raise RouteError(f"{event['event_id']} has an issuer: it is that company's own event, not a macro event")
    decision = parse_timestamp(decision_time)
    if parse_timestamp(event["available_at"]) > decision:
        raise NoRoute(f"{event['event_id']} was not known at {decision.isoformat()}")
    routes = []
    for row in conn.execute(f"SELECT {', '.join(COLUMNS)}, recorded_at FROM me_routes WHERE isin = ? ORDER BY route_key",
                            [isin]):
        r = dict(zip(COLUMNS + ("recorded_at",), row))
        if (r["event_type"] in event["event_types"]
                and (r["region"] is None or r["region"] == event["region"])
                and parse_timestamp(r["recorded_at"]) <= decision and r["valid_from"] <= decision.date().isoformat()):
            routes.append({"route_key": r["route_key"], "kind": r["kind"], "relation": r["relation"],
                           "rationale": r["rationale"], "recorded_at": r["recorded_at"]})
    if not routes:
        raise NoRoute(f"{event['event_id']} has no declared, recorded route to {isin} at {decision.isoformat()}"
                      " (4A rule 5) - it is not attributed")
    return {"event_id": event["event_id"], "isin": isin, "decision_time": decision.isoformat(),
            "evidence_kind": "read_across", "direct_observation": False, "routes": routes, "route_rule": ROUTE_RULE,
            "effect": "not_assessed: measured later as an event-response target, never assumed (4A rule 5)"}


def events_for(conn, isin, decision_time, claim=PitClaim.CURRENT_DECISION, start=None, end=None):
    """The macro events that reach one security at decision_time through recorded routes, each with its
    attribution. Events without a route are left out - never attributed."""
    found = []
    for event in macro_events(conn, decision_time, claim, start=start, end=end):
        try:
            found.append({**attribute(conn, event, isin, decision_time), "event": event})
        except NoRoute:
            continue
    return found
