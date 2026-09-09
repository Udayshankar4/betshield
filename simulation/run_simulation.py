"""
Entry point: run the simulation and dump results to data/generated/.

Usage:
    python simulation/run_simulation.py
"""
import csv
import os
import random

from agents import NormalPlayer, BotAgent, MuleAgent

# Population sizes, calibrated to roughly mirror PaySim's real fraud
# ratio (~0.13% of transactions are fraud) while still giving us enough
# positive examples to train/evaluate detection on later.
N_NORMAL_PLAYERS = 150
N_BOTS = 8
N_MULES = 4
N_TICKS = 10000
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "generated", "transactions.csv")


MULE_ROUTING_PROB = 0.03  # fraction of normal-player payments that get
                           # funneled through a mule instead of leaving
                           # the system directly (simulates unwitting or
                           # complicit senders feeding a laundering account)


def main():
    normal_players = [NormalPlayer() for _ in range(N_NORMAL_PLAYERS)]
    bots = [BotAgent() for _ in range(N_BOTS)]
    mules = [MuleAgent() for _ in range(N_MULES)]
    agents = normal_players + bots + mules

    transactions = []
    for tick in range(N_TICKS):
        for agent in agents:
            if not agent.should_transact(tick):
                continue
            txn = agent.generate_transaction(tick)

            # Fan-in: route some normal-player payments through a mule.
            # This is what actually feeds MuleAgent.balance so its own
            # threshold-triggered forward-out transaction can fire later.
            if agent.agent_type == "normal_player" and random.random() < MULE_ROUTING_PROB:
                mule = random.choice(mules)
                mule.receive(txn["amount"])
                txn["receiver"] = mule.id

            transactions.append(txn)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["sender", "receiver", "amount", "tick", "agent_type", "txn_type"]
        )
        writer.writeheader()
        writer.writerows(transactions)

    print(f"Generated {len(transactions)} transactions -> {OUTPUT_PATH}")
    by_type = {}
    for t in transactions:
        by_type[t["agent_type"]] = by_type.get(t["agent_type"], 0) + 1
    print("Breakdown by agent_type:", by_type)


if __name__ == "__main__":
    main()
