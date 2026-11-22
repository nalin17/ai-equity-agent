"""Fixed, versioned rules that decide what may count as sentiment toward a company (architecture 40B step 10, 4B,
9A; ADR-013). They are written before any outcome is seen; a change is a new rule id, never an edit of the old one.

  an-direction-1  the direction of a company's own exchange filing, from NSE's subject alone. NSE's 'details'
                  text is boilerplate ('X has informed the Exchange about Credit Rating') - whether a rating went
                  up or down, or why an auditor changed, is only in the attached PDF, which is never read here. So
                  only subjects with one direction are given one; every other subject is 'unknown', never guessed.
                  A release whose subjects point both ways is 'conflicting' - never netted.
  se-echo-1       a headline that restates a price or market move - market round-ups, gainers and losers, stock
                  tips, 52-week highs and lows, a stock's own move - is a price echo: it only repeats the price we
                  already have, so it is never sentiment (attention only). A move with a percentage and no stock
                  word counts when the word before the move is not a business figure: 'Airtel gains 3%' is an
                  echo, 'Q2 profit jumps 22%' and 'retail sales fall 24%' are not (found on GDELT's real files of
                  6-Nov-2026; every new case found becomes a named test).
  se-eligible-1   a headline story is sentiment-eligible for a company only when rule nw-entity-1 makes the
                  company its subject (declared name in the headline and the link, alone, not a list item) and it is
                  not a price echo; a story that only mentions the company is attention-eligible only (4B.4).
  se-liquidity-1  sentiment is admitted only for a company whose median daily traded value (close x volume) over
                  its last stored sessions known at the decision (up to 60, none older than 120 days) is at least
                  Rs 25 crore, from at least 5 sessions.
                  Below it, or with fewer sessions, sentiment is refused - never down-weighted (4B.2 rule 1).
"""
import re
import statistics
from datetime import timedelta

from core.dates import strict_iso_date
from ingestion.nse_financial_results import IST
from provenance.availability import Availability, parse_timestamp, price_availability

DIRECTION_RULE = "an-direction-1"
ECHO_RULE = "se-echo-1"
ELIGIBILITY_RULE = "se-eligible-1"
LIQUIDITY_RULE = "se-liquidity-1"

POSITIVE, NEGATIVE, UNKNOWN, CONFLICTING, PRICE_ECHO = "positive", "negative", "unknown", "conflicting", "price_echo"
SUBJECT_DIRECTIONS = {   # NSE subject -> direction under an-direction-1; only subjects with one meaning
    "Bagging/Receiving of orders/contracts": POSITIVE,
    "Commencement of commercial production/operations": POSITIVE,
    "Capacity addition": POSITIVE,
    "Defaults on Payment of Interest/Principal": NEGATIVE,
    "Corporate Insolvency Resolution Process": NEGATIVE,
    "Disruption of Operations": NEGATIVE,
    "Strikes/Lockouts/Disturbances": NEGATIVE,
    "Resignation of Statutory Auditor": NEGATIVE,
    "Postponement of commercial production/operations": NEGATIVE,
    "Spurt in Volume": PRICE_ECHO,        # the exchange asks the company about its own price or volume
    "Price movement": PRICE_ECHO,
}

_MOVE = (r"(?:jump|jumps|jumped|surge|surges|surged|soar|soars|soared|rally|rallies|rallied|rise|rises|rose|gain"
         r"|gains|gained|climb|climbs|climbed|zoom|zooms|zoomed|spurt|spurts|fall|falls|fell|drop|drops|dropped|slump"
         r"|slumps|slumped|plunge|plunges|plunged|tank|tanks|tanked|crash|crashes|crashed|slide|slides|slid|decline"
         r"|declines|declined|sink|sinks|sank|tumble|tumbles|tumbled|skid|skids|skidded|dip|dips|dipped|recover"
         r"|recovers|recovered|rebound|rebounds|rebounded|trade higher|trades higher|trade lower|trades lower)")
_STOCK = r"(?:shares?|stocks?|scrips?|m-?cap|market cap|market capitali[sz]ation)"
ECHO_PATTERNS = (   # rule se-echo-1, on the headline with HTML entities decoded, case-folded
    ("market_roundup", re.compile(r"\b(?:sensex|nifty|bank nifty|dalal street|d-street|closing bell|opening bell"
                                  r"|stock markets? (?:today|live|update|wrap|closing|opening)|markets? (?:today|live|wrap)"
                                  r"|market wrap|share market (?:today|live|update))\b")),
    ("gainers_losers", re.compile(r"\b(?:top )?(?:gainers|losers)\b")),
    ("stock_tip", re.compile(r"\b(?:stocks? to (?:buy|sell|watch|bet on)|buzzing stocks?|stocks? in (?:news|focus"
                             r"|spotlight)|trading guide|day trading|intraday|technical picks?|stock picks?"
                             r"|stock recommendations?|multibaggers?|penny stocks?|price targets?|target price"
                             r"|share price target|buy or sell)\b")),
    ("range_or_circuit", re.compile(r"\b(?:52[- ]week (?:high|low)|upper circuit|lower circuit|all[- ]time (?:high|low)"
                                    r" (?:for|on) (?:the )?(?:shares?|stocks?))\b")),
    ("stock_move", re.compile(r"\b" + _STOCK + r"\b(?:\W+\w+){0,6}?\W+" + _MOVE + r"\b")),
    ("move_of_stock", re.compile(r"\b" + _MOVE + r"\b(?:\W+\w+){0,2}?\W+(?:in |on )?" + _STOCK + r"\b")),
)
BARE_MOVE = re.compile(r"(\w+)\W+" + _MOVE + r"\W+(?:by\W+)?(?:nearly\W+|over\W+|about\W+|almost\W+|up\W+to\W+)?"
                       r"\d+(?:\.\d+)?\s?(?:%|per\s?cent)")
FIGURE_WORDS = frozenset({   # a move after one of these is a business figure, not the share price
    "profit", "profits", "revenue", "revenues", "sales", "income", "margin", "margins", "ebitda", "earnings", "pat",
    "loss", "losses", "volume", "volumes", "order", "orders", "deposits", "deposit", "loans", "advances", "nii", "aum",
    "arpu", "output", "production", "exports", "imports", "dividend", "guidance", "bookings", "deliveries",
    "despatches", "dispatches", "shipments", "subscribers", "users", "premium", "premiums", "collections",
    "disbursements", "npa", "npas", "gnpa", "debt", "borrowings", "capex", "cost", "costs", "expenses", "ebit",
    "turnover", "growth", "book", "inflows", "outflows", "registrations", "traffic", "footfalls", "throughput",
})

LIQUIDITY_MIN_CRORE = 25.0
LIQUIDITY_MIN_SESSIONS = 5
LIQUIDITY_SESSIONS = 60     # the most recent sessions known at the decision that are looked at
LIQUIDITY_MAX_AGE_DAYS = 120   # and none older than this before the decision: a stale band is not a band
CRORE = 10_000_000


def price_echo(headline):
    """The names of the se-echo-1 patterns a headline matches (empty when it is not a price echo)."""
    text = headline.casefold()
    found = [name for name, pattern in ECHO_PATTERNS if pattern.search(text)]
    if any(m[1] not in FIGURE_WORDS for m in BARE_MOVE.finditer(text)):
        found.append("bare_move")
    return found


def filing_direction(subjects):
    """Direction of one release (its NSE subjects) under an-direction-1: positive, negative, conflicting,
    price_echo or unknown."""
    found = {SUBJECT_DIRECTIONS.get(s, UNKNOWN) for s in subjects}
    if POSITIVE in found and NEGATIVE in found:
        return CONFLICTING
    for direction in (POSITIVE, NEGATIVE, PRICE_ECHO):
        if direction in found:
            return direction
    return UNKNOWN


def eligibility(story):
    """(sentiment-eligible?, reason) for one headline story about one company under se-eligible-1."""
    echo = price_echo(story["headline"])
    if echo:
        return False, f"price echo ({', '.join(echo)}) - restates a price move (rule {ECHO_RULE})"
    if story["role"] != "subject":
        return False, f"the headline does not make the company its subject ({story['extraction_confidence']})"
    return True, f"the company is the headline's subject and it is not a price echo (rule {ELIGIBILITY_RULE})"


def liquidity(conn, isin, decision_time, claim):
    """The liquidity gate of 4B.2 rule 1 under se-liquidity-1, from the prices known at decision_time under the
    claim: {'admitted', 'median_crore', 'sessions', 'withheld', 'reason', 'rule'}."""
    today = parse_timestamp(decision_time).astimezone(IST).date()
    oldest = (today - timedelta(days=LIQUIDITY_MAX_AGE_DAYS)).isoformat()
    rows = conn.execute("SELECT price_id, trade_date, close_price, volume FROM trusted_prices WHERE isin = ?"
                        " AND trade_date <= ? AND trade_date >= ? ORDER BY trade_date DESC, price_id",
                        [isin, today.isoformat(), oldest]).fetchall()
    values, withheld, dates = [], 0, set()
    for price_id, trade_date, close, volume in rows:
        if len(values) >= LIQUIDITY_SESSIONS:
            break
        state = price_availability(conn, price_id, decision_time, claim)
        if state != Availability.ELIGIBLE:
            withheld += state == Availability.AVAILABILITY_REVIEW
            continue
        if close is None or volume is None or trade_date in dates:
            continue
        strict_iso_date(trade_date)
        dates.add(trade_date)
        values.append(float(close) * float(volume) / CRORE)
    found = {"sessions": len(values), "withheld": withheld, "rule": LIQUIDITY_RULE,
             "threshold_crore": LIQUIDITY_MIN_CRORE, "min_sessions": LIQUIDITY_MIN_SESSIONS}
    if len(values) < LIQUIDITY_MIN_SESSIONS:
        why = (f"only {len(values)} trading sessions with a known close and volume in the last"
               f" {LIQUIDITY_MAX_AGE_DAYS} days")
        if withheld:
            why += f" ({withheld} withheld: no proven publication time under this claim)"
        return {**found, "admitted": False, "median_crore": None,
                "reason": f"{why}; at least {LIQUIDITY_MIN_SESSIONS} are needed - sentiment refused (4B.2 rule 1)"}
    median = statistics.median(values)
    admitted = median >= LIQUIDITY_MIN_CRORE
    return {**found, "admitted": admitted, "median_crore": round(median, 2),
            "reason": (f"median traded value Rs {median:,.2f} crore/day over {len(values)} sessions"
                       + ("" if admitted else f", below Rs {LIQUIDITY_MIN_CRORE:g} crore - sentiment refused, not"
                          " down-weighted (4B.2 rule 1)"))}
