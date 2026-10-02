"""Entity resolution (architecture Section 4).

1. ISIN is the primary key, never the trading symbol.
2. Symbol, BSE scrip code, vendor ids and names are aliases, each valid
   from one date until another.
3. resolve() returns exactly one ISIN or raises. It never guesses, never
   picks a "best" match and never does fuzzy name matching.
4. Renames, mergers and demergers are events with effective dates, not
   overwrites.
5. ISIN itself can change (architecture 6D). An ISIN change is recorded as a
   dated event linking two entities. It NEVER makes the two ISINs
   interchangeable: there is no global ISIN equivalence. Event-scoped
   identity bridges for corporate actions are a later stage.

Dates are ISO text: "YYYY-MM-DD". An alias is valid on a date when
valid_from <= date < valid_to (valid_to empty means still valid).
"""
from core.database import now_utc, run_in_transaction
from core.dates import strict_iso_date

ALIAS_TYPES = {"nse_symbol", "bse_code", "vendor_id", "company_name"}
EVENT_TYPES = {
    "listing", "rename", "symbol_change", "isin_change",
    "merger", "demerger", "delisting", "suspension",
}


class EntityError(Exception):
    """Base class for identity problems."""


class InvalidIsinError(EntityError):
    """Not a well-formed ISIN (wrong shape or wrong check digit)."""


class UnknownEntityError(EntityError):
    """The identifier does not resolve to any entity on that date."""


class AmbiguousIdentityError(EntityError):
    """The identifier resolves to more than one entity on that date."""


def check_date(value):
    try:
        strict_iso_date(value)
    except (TypeError, ValueError):
        raise EntityError(f"Not a valid YYYY-MM-DD date: {value!r}") from None
    return value


def validate_isin(isin):
    """Check shape (2 letters, 9 letters/digits, 1 check digit) and the check digit."""
    if not isinstance(isin, str) or len(isin) != 12 or not isin.isalnum() or not isin.isupper():
        raise InvalidIsinError(f"Not a valid ISIN: {isin!r}")
    if not isin[:2].isalpha() or not isin[-1].isdigit():
        raise InvalidIsinError(f"Not a valid ISIN: {isin!r}")
    # Check digit: letters become numbers (A=10 ... Z=35), then the Luhn rule.
    digits = "".join(str(int(ch, 36)) for ch in isin[:-1])
    total = 0
    for position, ch in enumerate(reversed(digits)):
        n = int(ch)
        if position % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    if (10 - total % 10) % 10 != int(isin[-1]):
        raise InvalidIsinError(f"ISIN check digit is wrong: {isin!r}")
    return isin


def add_entity(conn, isin, legal_name):
    validate_isin(isin)
    if not legal_name or not legal_name.strip():
        raise EntityError("legal_name is required")
    if conn.execute("SELECT 1 FROM entities WHERE isin = ?", [isin]).fetchone():
        raise EntityError(f"Entity {isin} already exists; entities are never overwritten")
    conn.execute("INSERT INTO entities VALUES (?, ?, ?)", [isin, legal_name.strip(), now_utc()])


def _require_entity(conn, isin):
    if not conn.execute("SELECT 1 FROM entities WHERE isin = ?", [isin]).fetchone():
        raise UnknownEntityError(f"No entity with ISIN {isin}")


def add_alias(conn, isin, alias_type, alias_value, valid_from, valid_to=None):
    _require_entity(conn, isin)
    if alias_type not in ALIAS_TYPES:
        raise EntityError(f"alias_type must be one of {sorted(ALIAS_TYPES)}")
    if not alias_value or not alias_value.strip():
        raise EntityError("alias_value is required")
    check_date(valid_from)
    if valid_to is not None and check_date(valid_to) <= valid_from:
        raise EntityError("valid_to must be after valid_from")
    conn.execute(
        "INSERT INTO entity_aliases (isin, alias_type, alias_value, valid_from, valid_to, recorded_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [isin, alias_type, alias_value.strip(), valid_from, valid_to, now_utc()],
    )


def record_event(conn, isin, event_type, effective_date, details, related_isin=None):
    _require_entity(conn, isin)
    if related_isin is not None:
        _require_entity(conn, related_isin)
    if event_type not in EVENT_TYPES:
        raise EntityError(f"event_type must be one of {sorted(EVENT_TYPES)}")
    check_date(effective_date)
    conn.execute(
        "INSERT INTO entity_events (isin, event_type, related_isin, effective_date, details, recorded_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [isin, event_type, related_isin, effective_date, details, now_utc()],
    )


def change_symbol(conn, isin, old_symbol, new_symbol, effective_date):
    """Close the old NSE symbol and open the new one on effective_date, as one event."""
    check_date(effective_date)

    def work(c):
        updated = c.execute(
            "UPDATE entity_aliases SET valid_to = ? WHERE isin = ? AND alias_type = 'nse_symbol'"
            " AND alias_value = ? AND valid_to IS NULL AND valid_from < ?",
            [effective_date, isin, old_symbol, effective_date],
        ).rowcount
        if updated != 1:
            raise EntityError(f"{isin} has no open NSE symbol {old_symbol!r} before {effective_date}")
        add_alias(c, isin, "nse_symbol", new_symbol, effective_date)
        record_event(c, isin, "symbol_change", effective_date, f"{old_symbol} -> {new_symbol}")

    run_in_transaction(conn, work)


def record_isin_change(conn, old_isin, new_isin, effective_date, evidence):
    """Record that a security moved from old_isin to new_isin (architecture 6D).

    Both ISINs stay separate entities. Nothing is rewritten, and resolve()
    never treats one as the other.
    """
    validate_isin(old_isin)
    validate_isin(new_isin)
    if old_isin == new_isin:
        raise EntityError("An ISIN change needs two different ISINs")
    if not evidence or not evidence.strip():
        raise EntityError("An ISIN change must cite its evidence")
    record_event(conn, old_isin, "isin_change", effective_date,
                 f"{old_isin} -> {new_isin}; evidence: {evidence.strip()}",
                 related_isin=new_isin)


def resolve(conn, identifier, as_of, alias_type=None):
    """Return the one ISIN that identifier meant on date as_of, or raise."""
    check_date(as_of)
    identifier = (identifier or "").strip()
    if not identifier:
        raise UnknownEntityError("Empty identifier")

    # An exact ISIN of a known entity resolves to itself.
    if alias_type is None and len(identifier) == 12:
        try:
            validate_isin(identifier)
        except InvalidIsinError:
            pass
        else:
            _require_entity(conn, identifier)
            return identifier

    sql = (
        "SELECT DISTINCT isin FROM entity_aliases WHERE alias_value = ?"
        " AND valid_from <= ? AND (valid_to IS NULL OR ? < valid_to)"
    )
    params = [identifier, as_of, as_of]
    if alias_type is not None:
        sql += " AND alias_type = ?"
        params.append(alias_type)
    matches = [r[0] for r in conn.execute(sql, params).fetchall()]

    if not matches:
        raise UnknownEntityError(f"{identifier!r} does not identify any entity on {as_of}")
    if len(matches) > 1:
        raise AmbiguousIdentityError(f"{identifier!r} matches {sorted(matches)} on {as_of}")
    return matches[0]
