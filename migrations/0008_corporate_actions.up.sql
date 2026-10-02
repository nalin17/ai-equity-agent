-- Corporate actions (architecture 6C, 6C.1, 6C.2, 40A item 13).
--
-- Each action is recorded with the policy treatment it received:
--   factor         split / simple bonus: back-adjust on the verified share ratio
--   no_adjustment  ordinary cash dividend, buyback
--   blocked        everything else: the security's window fails closed
-- A factor is ONLY ever built from a verified share ratio, never from prices.

CREATE TABLE corporate_actions (
    action_id      INTEGER PRIMARY KEY,
    isin           TEXT NOT NULL REFERENCES entities(isin),
    action_type    TEXT NOT NULL,
    ex_date        TEXT NOT NULL,
    treatment      TEXT NOT NULL CHECK (treatment IN ('factor', 'no_adjustment', 'blocked')),
    shares_before  INTEGER,        -- e.g. a 1-to-5 split: 1 share before ...
    shares_after   INTEGER,        -- ... becomes 5 shares after
    terms_text     TEXT NOT NULL,  -- the source wording, kept exactly as received
    evidence       TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    artifact_id    INTEGER NOT NULL REFERENCES raw_artifacts(artifact_id),
    recorded_at    TEXT NOT NULL,
    UNIQUE (isin, action_type, ex_date),
    -- Only factor actions carry a ratio, and every factor action must.
    CHECK ((treatment = 'factor') = (shares_before IS NOT NULL AND shares_after IS NOT NULL)),
    CHECK (shares_before IS NULL OR (shares_before > 0 AND shares_after > 0 AND shares_before <> shares_after))
) STRICT;

CREATE INDEX idx_corporate_actions ON corporate_actions (isin, ex_date);

CREATE TRIGGER corporate_actions_no_update BEFORE UPDATE ON corporate_actions
BEGIN SELECT RAISE(ABORT, 'corporate_actions is append-only'); END;
CREATE TRIGGER corporate_actions_no_delete BEFORE DELETE ON corporate_actions
BEGIN SELECT RAISE(ABORT, 'corporate_actions is append-only'); END;
