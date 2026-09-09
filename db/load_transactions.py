"""
Load simulation output (data/generated/transactions.csv) into Postgres.

Usage:
    python db/load_transactions.py

Requires: docker compose up -d  (Postgres must already be running)
"""
import os

import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://postgres:devpass@localhost:5432/betshield"
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "generated", "transactions.csv")


def main():
    engine = create_engine(DB_URL)
    df = pd.read_csv(CSV_PATH)

    print(f"Loaded {len(df)} rows from {CSV_PATH}")

    # --- 1. Build the accounts table from unique senders ---
    # Each unique sender UUID becomes one row in `accounts`, tagged with
    # its agent_type (this IS our ground truth label).
    accounts = (
        df[["sender", "agent_type"]]
        .drop_duplicates(subset="sender")
        .rename(columns={"sender": "account_id"})
    )
    print(f"Found {len(accounts)} unique accounts")

    with engine.begin() as conn:
        # Clear existing data so this script is safely re-runnable
        conn.execute(text("TRUNCATE TABLE alerts, transactions, accounts RESTART IDENTITY CASCADE"))

        accounts.to_sql("accounts", conn, if_exists="append", index=False,
                         method="multi", chunksize=1000)

        # --- 2. Load transactions ---
        # sender maps to accounts.account_id (FK).
        # receiver is only populated for mule-routed transactions in this
        # simulation; leave as NULL otherwise (external/unmodeled recipient).
        txns = df.rename(columns={
            "sender": "sender_account",
            "receiver": "receiver_account",
            "txn_type": "channel",
        })[["sender_account", "receiver_account", "amount", "tick", "channel"]]

        # receiver_account must be a real account_id or NULL (FK constraint) —
        # mule UUIDs are already in `accounts` since they're senders too, so
        # this is safe as-is.
        txns.to_sql("transactions", conn, if_exists="append", index=False,
                     method="multi", chunksize=1000)

    print("Load complete.")

    # --- 3. Quick sanity check ---
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT a.agent_type, COUNT(*) FROM transactions t "
            "JOIN accounts a ON t.sender_account = a.account_id "
            "GROUP BY a.agent_type"
        ))
        print("\nRows in DB by agent_type:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")


if __name__ == "__main__":
    main()
