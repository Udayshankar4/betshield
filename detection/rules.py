"""
Phase 2 — Rule Engine

Pure SQL/threshold-based detection, no ML. This is the fast, cheap first
pass in BetShield's pipeline: catches obvious patterns before anything
gets to the (more expensive) ML layer in Phase 3.

Each rule is a SQL query that returns flagged (account_id, reason, score)
rows. Results are written into the `alerts` table.

Usage:
    python detection/rules.py
"""
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://postgres:devpass@localhost:5432/betshield"

# ---------------------------------------------------------------------
# Rule 0: Blacklist / MCC match
# Direct match against known illegal betting merchants. This is the
# cheapest, fastest rule -- and deliberately a blunt instrument: it
# flags EVERYONE who transacts with a blacklisted merchant, whether
# they're an automated bot or a genuine human bettor. It cannot tell
# the two apart on its own -- that distinction is what Rule 2 (timing
# regularity) is for. Reporting both side by side is intentional: it's
# the evidence for why a single rule-layer isn't enough.
# ---------------------------------------------------------------------
RULE_BLACKLIST_MATCH = text("""
    SELECT t.sender_account AS account_id,
           'blacklist_match' AS alert_type,
           COUNT(*) AS evidence_count
    FROM transactions t
    JOIN merchants m ON t.merchant_id = m.merchant_id
    WHERE m.is_blacklisted = TRUE
    GROUP BY t.sender_account
""")

# ---------------------------------------------------------------------
# Rule 1: Round-amount frequency (bot signature)
# Scripted deposits tend to use "clean" round numbers repeatedly.
# Flag accounts with >= 5 transactions at round amounts.
# ---------------------------------------------------------------------
RULE_ROUND_AMOUNTS = text("""
    SELECT sender_account AS account_id,
           'round_amount_frequency' AS alert_type,
           COUNT(*) AS evidence_count
    FROM transactions
    WHERE amount IN (100, 200, 500, 1000, 2000, 5000)
    GROUP BY sender_account
    HAVING COUNT(*) >= 5
""")

# ---------------------------------------------------------------------
# Rule 2: Timing regularity (bot signature)
# Real humans have irregular gaps between transactions. Bots don't.
# Flag accounts whose tick-gap standard deviation is very low
# (near-fixed interval), among accounts with enough transactions to
# measure variance meaningfully.
# ---------------------------------------------------------------------
RULE_TIMING_REGULARITY = text("""
    WITH gaps AS (
        SELECT sender_account,
               tick - LAG(tick) OVER (PARTITION BY sender_account ORDER BY tick) AS gap
        FROM transactions
    ),
    stats AS (
        SELECT sender_account,
               COUNT(gap) AS n_gaps,
               STDDEV(gap) AS gap_stddev,
               AVG(gap) AS gap_avg
        FROM gaps
        WHERE gap IS NOT NULL
        GROUP BY sender_account
        HAVING COUNT(gap) >= 5
    )
    SELECT sender_account AS account_id,
           'timing_regularity' AS alert_type,
           n_gaps AS evidence_count
    FROM stats
    WHERE gap_stddev < 5  -- near-fixed interval; real humans are far noisier
""")

# ---------------------------------------------------------------------
# Rule 3: Fan-in then fast forward-out (mule / layering signature)
# An account receiving from >= 3 distinct senders, which then makes a
# TRANSFER/CASH_OUT within 20 ticks of *any* incoming payment, matches
# classic layering. Checked per-outgoing-event (not just first/last
# overall) since a mule can cycle through many receive-then-forward
# rounds rather than a single burst.
# ---------------------------------------------------------------------
RULE_FAN_IN_FORWARD = text("""
    WITH sender_counts AS (
        SELECT receiver_account AS account_id,
               COUNT(DISTINCT sender_account) AS distinct_senders
        FROM transactions
        WHERE receiver_account IS NOT NULL
        GROUP BY receiver_account
        HAVING COUNT(DISTINCT sender_account) >= 3
    ),
    outgoing_events AS (
        SELECT sender_account AS account_id, tick AS out_tick
        FROM transactions
        WHERE channel IN ('TRANSFER', 'CASH_OUT')
    ),
    incoming_events AS (
        SELECT receiver_account AS account_id, tick AS in_tick
        FROM transactions
        WHERE receiver_account IS NOT NULL
    )
    SELECT DISTINCT sc.account_id,
           'fan_in_fast_forward' AS alert_type,
           sc.distinct_senders AS evidence_count
    FROM sender_counts sc
    JOIN outgoing_events oe ON oe.account_id = sc.account_id
    JOIN incoming_events ie ON ie.account_id = sc.account_id
        AND ie.in_tick <= oe.out_tick
        AND ie.in_tick >= oe.out_tick - 20
""")

# ---------------------------------------------------------------------
# Rule 4: Large single TRANSFER/CASH_OUT (high-value layering move)
# ---------------------------------------------------------------------
RULE_LARGE_TRANSFER = text("""
    SELECT sender_account AS account_id,
           'large_transfer' AS alert_type,
           1 AS evidence_count
    FROM transactions
    WHERE channel IN ('TRANSFER', 'CASH_OUT')
      AND amount >= 4500
""")

RULES = [
    ("blacklist_match", RULE_BLACKLIST_MATCH, 0.5),
    ("round_amount_frequency", RULE_ROUND_AMOUNTS, 0.4),
    ("timing_regularity", RULE_TIMING_REGULARITY, 0.5),
    ("fan_in_fast_forward", RULE_FAN_IN_FORWARD, 0.8),
    ("large_transfer", RULE_LARGE_TRANSFER, 0.3),
]


def main():
    engine = create_engine(DB_URL)

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM alerts WHERE alert_type LIKE 'rule:%'"))

        total_alerts = 0
        for name, query, base_score in RULES:
            rows = conn.execute(query).fetchall()
            print(f"[{name}] {len(rows)} accounts flagged")

            for row in rows:
                account_id = row.account_id
                evidence = row.evidence_count
                # simple scaling: more evidence -> higher confidence, capped at 1.0
                risk_score = min(1.0, base_score + 0.05 * evidence)

                conn.execute(text("""
                    INSERT INTO alerts (txn_id, alert_type, risk_score, status)
                    SELECT txn_id, :alert_type, :risk_score, 'open'
                    FROM transactions
                    WHERE sender_account = :account_id
                    ORDER BY tick DESC
                    LIMIT 1
                """), {
                    "alert_type": f"rule:{name}",
                    "risk_score": risk_score,
                    "account_id": account_id,
                })
                total_alerts += 1

    print(f"\nTotal alerts written: {total_alerts}")

    # --- Summary: how well did the rules do against ground truth? ---
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT a.agent_type,
                   COUNT(DISTINCT al.txn_id) AS n_alerts
            FROM alerts al
            JOIN transactions t ON al.txn_id = t.txn_id
            JOIN accounts a ON t.sender_account = a.account_id
            WHERE al.alert_type LIKE 'rule:%'
            GROUP BY a.agent_type
        """))
        print("\nAlerts by true agent_type (sanity check against ground truth):")
        for row in result:
            print(f"  {row[0]}: {row[1]}")


if __name__ == "__main__":
    main()
