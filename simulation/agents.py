"""
Agent definitions for the BetShield simulated economy.

Start with NormalPlayer only. Add BotAgent, MuleAgent, BettingMerchant
one at a time once this works end-to-end.
"""
import random
import uuid


class NormalPlayer:
    """A regular user with irregular, human-like transaction timing."""

    agent_type = "normal_player"

    def __init__(self, transact_prob=0.02):
        self.id = str(uuid.uuid4())
        self.balance = 1000.0
        self.transact_prob = transact_prob

    def should_transact(self, tick: int) -> bool:
        return random.random() < self.transact_prob

    def generate_transaction(self, tick: int) -> dict:
        # log-normal amount roughly matches typical PaySim-style skew
        amount = round(random.lognormvariate(4, 1), 2)
        return {
            "sender": self.id,
            "receiver": None,
            "amount": amount,
            "tick": tick,
            "agent_type": self.agent_type,
            "txn_type": "PAYMENT",
        }


class BotAgent:
    """
    Simulates a scripted, automated bettor.

    Calibration notes (from PaySim EDA):
    - Real humans transact at irregular, Poisson-like intervals.
    - Bots are the inverse signal: near-fixed interval with very low
      timing variance, and a preference for round-number amounts
      (common in scripted betting-deposit behavior).
    """

    agent_type = "bot"

    def __init__(self, interval_ticks=50, jitter=2):
        self.id = str(uuid.uuid4())
        self.balance = 1000.0
        self.interval_ticks = interval_ticks
        self.jitter = jitter  # small jitter so it's not *perfectly* robotic
        self._next_tick = random.randint(0, interval_ticks)

    def should_transact(self, tick: int) -> bool:
        if tick >= self._next_tick:
            self._next_tick = tick + self.interval_ticks + random.randint(
                -self.jitter, self.jitter
            )
            return True
        return False

    def generate_transaction(self, tick: int) -> dict:
        # round-number amounts are a classic scripted-deposit signature
        amount = random.choice([100, 200, 500, 1000, 2000])
        return {
            "sender": self.id,
            "receiver": None,
            "amount": amount,
            "tick": tick,
            "agent_type": self.agent_type,
            "txn_type": "PAYMENT",  # deposits into the betting merchant
        }


class MuleAgent:
    """
    Simulates a money-laundering mule account.

    Calibration notes (from PaySim EDA):
    - Fraud in PaySim is concentrated almost entirely in TRANSFER
      (0.77% fraud rate) and CASH_OUT (0.18%) transaction types;
      CASH_IN / DEBIT / PAYMENT show ~0% fraud.
    - This mirrors real layering behavior: a mule receives funds from
      several sources (fan-in), then forwards the balance out quickly
      once it crosses a threshold, almost always via TRANSFER/CASH_OUT.
    """

    agent_type = "mule"

    def __init__(self, forward_threshold=5000):
        self.id = str(uuid.uuid4())
        self.balance = 0.0
        self.forward_threshold = forward_threshold

    def receive(self, amount: float):
        """Called externally when another agent sends this mule funds."""
        self.balance += amount

    def should_transact(self, tick: int) -> bool:
        # forwards funds out as soon as it crosses the threshold
        return self.balance >= self.forward_threshold

    def generate_transaction(self, tick: int) -> dict:
        amount = round(self.balance, 2)
        self.balance = 0.0
        return {
            "sender": self.id,
            "receiver": None,
            "amount": amount,
            "tick": tick,
            "agent_type": self.agent_type,
            "txn_type": random.choice(["TRANSFER", "CASH_OUT"]),
        }
