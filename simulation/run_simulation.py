"""
Entry point: run the simulation and dump results to data/generated/.

Usage:
    python simulation/run_simulation.py
"""
import csv
import os
import random

from agents import NormalPlayer, BotAgent, MuleAgent
from merchants import MERCHANTS, BLACKLISTED_MERCHANTS, LEGIT_MERCHANTS

# Population sizes, calibrated to roughly mirror PaySim's real fraud
# ratio (~0.13% of transactions are fraud) while still giving us enough
# positive examples to train/evaluate detection on later.
N_NORMAL_PLAYERS = 150
N_BOTS = 8
N_MULES = 4
N_TICKS = 10000

TXN_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "generated", "transactions.csv")
MERCHANT_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "generated", "merchants.csv")

MULE_ROUTING_PROB = 0.03  # fraction of normal-player payments that get
                           # funneled through a mule instead of leaving
                           # the system directly (simulates unwitting or
                           # complicit senders feeding a laundering account)

GENUINE_BETTOR_PROB = 0.05  # fraction of normal players who occasionally
                             # deposit into a blacklisted betting merchant
                             # themselves (i.e. a real human bettor, not
                             # a bot). This is what makes the blacklist
                             # rule and the bot-timing rule catch
                             # different, overlapping-but-distinct sets.


def main():
    normal_players = [NormalPlayer() for _ in range(N_NORMAL_PLAYERS)]
    bots = [BotAgent() for _ in range(N_BOTS)]
    mules = [MuleAgent() for _ in range(N_MULES)]
    agents = normal_players + bots + mules

    # Decide ONCE per player whether they're an occasional genuine bettor
    # (a real human who bets sometimes) -- NOT a per-transaction coin flip,
    # since with ~200 transactions per player over the run, a per-transaction
    # roll would make almost every player trigger it at least once.
    genuine_bettors = {
        p.id for p in normal_players if random.random() < GENUINE_BETTOR_PROB
    }

    transactions = []
    for tick in range(N_TICKS):
        for agent in agents:
            if not agent.should_transact(tick):
                continue
            txn = agent.generate_transaction(tick)
            txn["merchant_id"] = None

            if agent.agent_type == "bot":
                # every bot deposit goes to a known illegal betting merchant
                txn["merchant_id"] = random.choice(BLACKLISTED_MERCHANTS)["id"]

            elif agent.agent_type == "normal_player":
                if agent.id in genuine_bettors and random.random() < 0.3:
                    # this player is a real human bettor; roughly 30% of
                    # their transactions go to a betting merchant, the
                    # rest are ordinary purchases
                    txn["merchant_id"] = random.choice(BLACKLISTED_MERCHANTS)["id"]
                else:
                    txn["merchant_id"] = random.choice(LEGIT_MERCHANTS)["id"]

                if random.random() < MULE_ROUTING_PROB:
                    mule = random.choice(mules)
                    mule.receive(txn["amount"])
                    txn["receiver"] = mule.id
                    txn["merchant_id"] = None  # this is an account-to-account
                                                # transfer, not a merchant payment

            # MuleAgent transactions: no merchant_id -- these are
            # TRANSFER/CASH_OUT moves between accounts, not merchant payments

            transactions.append(txn)

    os.makedirs(os.path.dirname(TXN_OUTPUT_PATH), exist_ok=True)

    with open(TXN_OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["sender", "receiver", "amount", "tick", "agent_type", "txn_type", "merchant_id"]
        )
        writer.writeheader()
        writer.writerows(transactions)

    with open(MERCHANT_OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "name", "mcc_code", "payment_gateway_id", "is_blacklisted", "app_package_name"]
        )
        writer.writeheader()
        writer.writerows(MERCHANTS)

    print(f"Generated {len(transactions)} transactions -> {TXN_OUTPUT_PATH}")
    print(f"Wrote {len(MERCHANTS)} merchants -> {MERCHANT_OUTPUT_PATH}")

    by_type = {}
    for t in transactions:
        by_type[t["agent_type"]] = by_type.get(t["agent_type"], 0) + 1
    print("Breakdown by agent_type:", by_type)

    blacklisted_txns = sum(
        1 for t in transactions
        if t["merchant_id"] in {m["id"] for m in BLACKLISTED_MERCHANTS}
    )
    print(f"Transactions to blacklisted merchants: {blacklisted_txns}")


if __name__ == "__main__":
    main()
