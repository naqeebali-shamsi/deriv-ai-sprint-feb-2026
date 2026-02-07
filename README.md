# Autonomous Fraud Detection Agent

**Deriv AI Talent Sprint 2026** | Self-improving ML + Graph Pattern Mining + LLM Reasoning

An autonomous agent that detects financial fraud in real-time, learns from analyst feedback, and discovers new fraud patterns — all without manual intervention.

## Architecture

```
Simulator ──→ FastAPI Backend ──→ Risk Scorer (ML) ──→ Cases
                    │                    │                │
                    │              Pattern Miner      Analyst Labels
                    │              (Graph Mining)         │
                    │                    │                │
                    └──── Retrain ←──────┴────────────────┘
                              │
                         Model Update
```

**Pipeline:** Stream → Score (27 core features + 7 pattern-derived = 34 total) → Case → Label → Learn → Pattern Discovery

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + uvicorn |
| UI | Streamlit + HTML5 Canvas |
| Database | SQLite (WAL mode) |
| ML Model | XGBClassifier (XGBoost) |
| Graph Mining | networkx |
| LLM | Ollama (llama3.1:8b) |
| Simulator | 5 fraud typologies (wash trading, spoofing, bonus abuse, structuring, velocity abuse) |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the full demo (init DB + bootstrap model + backend + UI + simulator)
python scripts/demo.py
```

Then open:
- **UI:** http://localhost:8501
- **API Docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health

## Docker

```bash
# Build and run
docker compose up --build

# With DB init and seed data
docker compose --profile setup up --build
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/transactions` | Ingest and score a transaction |
| GET | `/transactions` | List recent transactions |
| GET | `/transactions/{id}` | Get transaction detail |
| GET | `/cases` | List cases (filterable by status) |
| POST | `/cases/{id}/label` | Analyst labels a case |
| GET | `/cases/suggested` | Active learning — most uncertain cases |
| GET | `/cases/{id}/explain` | AI-powered case explanation |
| GET | `/cases/{id}/explain-stream` | Streaming explanation (SSE) |
| GET | `/metrics` | System metrics (precision/recall/F1) |
| GET | `/metric-snapshots` | Model performance history |
| POST | `/retrain` | Retrain model from analyst labels |
| POST | `/retrain-from-ground-truth` | Retrain from simulator ground truth |
| POST | `/mine-patterns` | Trigger pattern mining |
| GET | `/patterns` | List discovered patterns |
| GET | `/stream/events` | SSE event stream for real-time UI |
| GET | `/simulator/status` | Get simulator config and state |
| POST | `/simulator/start` | Start embedded simulator |
| POST | `/simulator/stop` | Stop simulator |
| POST | `/simulator/configure` | Configure fraud types and rate |
| GET | `/health` | Health check |
| GET | `/ready` | Readiness probe |

## Configuration

Copy `.env.example` to `.env` and adjust:

```bash
cp .env.example .env
```

Key settings: `BACKEND_PORT`, `DATABASE_PATH`, `OLLAMA_URL`, `FRAUD_RATE`, `LOG_LEVEL`

## Development

```bash
python scripts/bootstrap_model.py --force  # Required before scoring
pytest tests/ -q                           # Run tests
ruff check .                               # Lint
ruff format .                              # Format
python scripts/validate_schemas.py         # Validate schemas
```

## Key Technical Features

- **Multi-Agent LLM Explanations** -- When `LLM_MULTI_AGENT=true`, 3 specialist analysts (Behavioral, Network/Pattern, Compliance) produce parallel analyses, synthesized by a 4th Lead Analyst into a single investigation report.
- **Active Learning** -- `GET /cases/suggested` returns cases sorted by model uncertainty (risk score closest to 0.5), prioritizing the most informative cases for analyst labeling.
- **Auto-Retrain** -- After each analyst label, the system checks if minimum sample thresholds are met and automatically retrains the model in the background. Manual retrain via `POST /retrain` is also available.
- **Investigation Timeline** -- Every case explanation includes a timestamped step-by-step investigation timeline tracking features, patterns, LLM calls, and synthesis with millisecond precision.
- **Pattern-to-ML Feedback Loop** -- 7 graph-derived features (`sender_in_ring`, `sender_is_hub`, `sender_in_velocity_cluster`, `sender_in_dense_cluster`, `receiver_in_ring`, `receiver_is_hub`, `pattern_count_sender`) flow from pattern mining back into the ML scorer at scoring time.
- **SSE Real-Time Events** -- Server-Sent Events stream (`GET /stream/events`) with 7 event types (`transaction`, `case_created`, `case_labeled`, `retrain`, `pattern`, `simulator_*`, `heartbeat`) and 15-second keepalive heartbeats. Events fire from the core POST /transactions endpoint regardless of whether the embedded or external simulator is used.
- **Hero Transaction Golden Path** -- Transactions with `metadata.demo_hero` receive a score floor of 0.92 and a pre-canned LLM explanation, guaranteeing 100% demo reliability for the critical demo flow.
- **Adversarial Testing Suite** -- 5 evasion-strategy generators in `sim/adversarial.py` (`generate_subtle_structuring`, `generate_stealth_wash_trade`, `generate_slow_velocity_abuse`, `generate_legit_looking_fraud`, `generate_bonus_abuse_evasion`) for red-team evaluation.

## Project Structure

```
├── backend/     # FastAPI + DB layer
├── risk/        # ML scorer, trainer, LLM explainer
├── patterns/    # Graph mining + pattern cards
├── sim/         # Transaction simulator (5 fraud types)
├── ui/          # Streamlit dashboard
├── schemas/     # JSON Schema contracts
├── scripts/     # Demo runner, DB init, validation
├── tests/       # Schema + pipeline tests
├── models/      # Trained ML models (gitignored)
└── docs/        # Demo script, architecture, Q&A
```
