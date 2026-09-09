"""Tick-based simulation loop."""


class Simulation:
    def __init__(self, agents, ticks=10000):
        self.agents = agents
        self.ticks = ticks
        self.transaction_log = []

    def run(self):
        for t in range(self.ticks):
            for agent in self.agents:
                if agent.should_transact(t):
                    txn = agent.generate_transaction(t)
                    self.transaction_log.append(txn)
        return self.transaction_log
