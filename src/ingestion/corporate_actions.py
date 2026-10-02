"""Corporate-action adjustment policy and recording (architecture 6C, 6C.2).

The policy is a frozen, versioned, human-owned contract. It states BOTH what
it intends and what is actually implemented - the gap is the point (6C).
Changing it is a new POLICY_VERSION, never an edit to an old one.

A factor is built ONLY from a verified share ratio (shares before -> shares
after). It is never inferred from an observed price jump (criterion 64).
"""
from core.database import now_utc
from core.dates import strict_iso_date

POLICY_VERSION = "corporate-action-policy-1"

# action_type -> (policy intent, implemented treatment)
POLICY = {
    "split":            ("Back-adjust on verified official ratio (also reverse split)", "factor"),
    "bonus":            ("Simple equity bonus: back-adjust on verified ratio", "factor"),
    "dividend":         ("Ordinary cash dividend: price return, no adjustment", "no_adjustment"),
    "buyback":          ("No adjustment by default", "no_adjustment"),
    "rights":           ("Official factor, or TERP only with verified ratio, price and ex-date", "blocked"),
    "special_dividend": ("Price-index-consistent treatment", "blocked"),
    "merger":           ("No automatic successor splice", "blocked"),
    "demerger":         ("Authoritative reference-price treatment", "blocked"),
    "complex_bonus":    ("No approximation", "blocked"),
    "unknown":          ("Unknown or conflicting terms: quarantine", "blocked"),
}


class CorporateActionError(Exception):
    """An action cannot be recorded under the policy."""


def treatment_of(action_type):
    if action_type not in POLICY:
        raise CorporateActionError(f"action_type must be one of {sorted(POLICY)}, got {action_type!r}")
    return POLICY[action_type][1]


def record_action(conn, isin, action_type, ex_date, terms_text, artifact_id, evidence,
                  shares_before=None, shares_after=None):
    """Record one corporate action with its policy treatment. Returns action_id."""
    treatment = treatment_of(action_type)
    if not conn.execute("SELECT 1 FROM entities WHERE isin = ?", [isin]).fetchone():
        raise CorporateActionError(f"No entity with ISIN {isin}")
    try:
        strict_iso_date(ex_date)
    except ValueError:
        raise CorporateActionError(f"ex_date must be YYYY-MM-DD, got {ex_date!r}") from None
    if not terms_text or not terms_text.strip():
        raise CorporateActionError("The source wording of the terms must be kept")
    if not evidence or not evidence.strip():
        raise CorporateActionError("A corporate action must cite its evidence")
    if not conn.execute("SELECT 1 FROM raw_artifacts WHERE artifact_id = ?", [artifact_id]).fetchone():
        raise CorporateActionError(f"Unknown raw artifact {artifact_id}; every action needs its source file")

    if treatment == "factor":
        if not all(isinstance(n, int) and not isinstance(n, bool) and n > 0
                   for n in (shares_before, shares_after)):
            raise CorporateActionError(
                f"A {action_type} needs a verified whole-number share ratio (shares_before, shares_after)"
            )
        if shares_before == shares_after:
            raise CorporateActionError("A share ratio of 1:1 changes nothing - check the terms")
        if action_type == "bonus" and shares_after < shares_before:
            raise CorporateActionError("A bonus issue can only increase the number of shares")
    elif shares_before is not None or shares_after is not None:
        raise CorporateActionError(
            f"A {action_type} is treated as '{treatment}'; it must not carry a share ratio"
        )

    existing = conn.execute(
        "SELECT action_id FROM corporate_actions WHERE isin = ? AND action_type = ? AND ex_date = ?",
        [isin, action_type, ex_date],
    ).fetchone()
    if existing:
        raise CorporateActionError(
            f"{action_type} for {isin} on {ex_date} is already recorded (action {existing[0]}); never overwritten"
        )
    return conn.execute(
        "INSERT INTO corporate_actions (isin, action_type, ex_date, treatment, shares_before, shares_after,"
        " terms_text, evidence, policy_version, artifact_id, recorded_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [isin, action_type, ex_date, treatment, shares_before, shares_after, terms_text.strip(),
         evidence.strip(), POLICY_VERSION, artifact_id, now_utc()],
    ).lastrowid
