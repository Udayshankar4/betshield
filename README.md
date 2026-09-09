# BetShield

A behavioral analysis engine that detects transactions linked to illegal betting
platforms and bot-driven money-laundering activity layered on top of them —
built and tested inside a self-contained simulated economy (fake in-game
currency) instead of real financial data.

NOTE FOR MEMBERS:
Add teammates: repo Settings → Collaborators → add their GitHub usernames (needed since it's private)
On another machine: git clone https://github.com/Udayshankar4/betshield.git, then same setup (venv, pip install -r requirements.txt, Docker for Postgres)
One thing to flag: your data/raw/ (PaySim CSV) is .gitignore'd — anyone cloning won't get that file automatically, they'd need to download it themselves from Kaggle separately. Worth a line in your README noting this.


## Project structure

```
betshield/
├── simulation/        # Agent-based fake economy (Phase 1)
│   ├── agents.py       # NormalPlayer, BotAgent, MuleAgent, BettingMerchant
│   ├── engine.py        # Tick-based simulation loop
│   └── run_simulation.py
├── data/
│   ├── raw/             # Reference datasets (PaySim, IBM AMLSim) — for calibration only, not committed
│   └── generated/       # Output of the simulator (transactions.csv, ground_truth.csv)
├── db/
│   └── schema.sql       # Postgres schema
├── detection/          # Rule engine + ML models (Phase 2-3)
├── notebooks/
│   └── 01_eda_calibration.ipynb
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Setup

```bash
# 1. Clone and enter
git clone <your-repo-url>
cd betshield

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start Postgres
docker compose up -d

# 5. Load schema
psql -h localhost -U postgres -d betshield -f db/schema.sql

# 6. Run the simulation
python simulation/run_simulation.py
```

## Build phases

| Phase | Focus | Status |
|---|---|---|
| 1 | Data foundation — agent-based simulator, DB schema | 🔲 in progress |
| 2 | Rule engine — blacklist/threshold matching | 🔲 |
| 3 | ML detection — betting classifier, bot detector, AML graph analysis | 🔲 |
| 4 | Discovery bot — simulated app/merchant crawler | 🔲 |
| 5 | Dashboard + API — FastAPI backend, React frontend | 🔲 |
| 6 | Integration — Docker Compose, tests, polish | 🔲 |

## Team

- Lakshita Babbilwar — BE A 104
- Shruti Borde — BE A 108
- Gaurav Kene — BE A 125
- Udayshankar Sajith — BE A 150

Guide: Prof. Dr. Snehal Junnarkar
