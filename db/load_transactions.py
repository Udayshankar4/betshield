"""
Load simulation output (transactions.csv + merchants.csv) into Postgres.

Usage:
    python db/load_transactions.py

Requires: docker compose up -d  (Postgres must already be running)
"""
import os

import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://postgres:devpass@localhost:5432/betshield"
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "generated", "transactions.csv")
MERCHANTS_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "generated", "merchants.csv")


def main():
    engine = create_engine(DB_URL)
    df = pd.read_csv(CSV_PATH)
    merchants_df = pd.read_csv(MERCHANTS_CSV_PATH).rename(
        columns={"id": "merchant_id", "name": "merchant_name"}
    )

    print(f"Loaded {len(df)} rows from {CSV_PATH}")
    print(f"Loaded {len(merchants_df)} merchants from {MERCHANTS_CSV_PATH}")

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
        conn.execute(text(
            "TRUNCATE TABLE alerts, transactions, accounts, merchants RESTART IDENTITY CASCADE"
        ))

        merchants_df.to_sql("merchants", conn, if_exists="append", index=False,
                             method="multi", chunksize=1000)

        accounts.to_sql("accounts", conn, if_exists="append", index=False,
                         method="multi", chunksize=1000)

        # --- 2. Load transactions ---
        # sender maps to accounts.account_id (FK). receiver is only
        # populated for mule-routed transactions; merchant_id is only
        # populated for merchant-payment transactions. Both are NULL
        # otherwise.
        txns = df.rename(columns={
            "sender": "sender_account",
            "receiver": "receiver_account",
            "txn_type": "channel",
        })[["sender_account", "receiver_account", "amount", "tick", "channel", "merchant_id"]]

        txns["merchant_id"] = txns["merchant_id"].where(txns["merchant_id"].notna(), None)

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

        result = conn.execute(text(
            "SELECT m.merchant_name, m.is_blacklisted, COUNT(*) FROM transactions t "
            "JOIN merchants m ON t.merchant_id = m.merchant_id "
            "GROUP BY m.merchant_name, m.is_blacklisted"
        ))
        print("\nTransactions by merchant:")
        for row in result:
            print(f"  {row[0]} (blacklisted={row[1]}): {row[2]}")


if __name__ == "__main__":
    main()
