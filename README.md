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

**Pipeline:** Stream → Score (17 features) → Case → Label → Learn → Pattern Discovery

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + uvicorn |
| UI | Streamlit + HTML5 Canvas |
| Database | SQLite (WAL mode) |
| ML Model | GradientBoostingClassifier (scikit-learn) |
| Graph Mining | networkx |
| LLM | Ollama (llama3.1:8b) |
| Simulator | 5 fraud typologies (wash trading, spoofing, bonus abuse, structuring, velocity abuse) |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the full demo (init DB + backend + UI + simulator)
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
| GET | `/cases/{id}/explain` | AI-powered case explanation |
| GET | `/cases/{id}/explain-stream` | Streaming explanation (SSE) |
| GET | `/metrics` | System metrics (precision/recall/F1) |
| POST | `/retrain` | Retrain model from analyst labels |
| POST | `/mine-patterns` | Trigger pattern mining |
| GET | `/patterns` | List discovered patterns |
| GET | `/stream/events` | SSE event stream for real-time UI |
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
pytest tests/ -q          # Run tests
ruff check .              # Lint
ruff format .             # Format
python scripts/validate_schemas.py  # Validate schemas
```

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
