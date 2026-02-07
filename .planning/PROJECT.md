# PROJECT.md — Autonomous Fraud Detection Agent

## Project Identity

- **Name:** Autonomous Fraud Detection Agent
- **Type:** Hackathon MVP (Deriv AI Talent Sprint, Feb 6-8, 2026)
- **Stack:** Python, FastAPI, Streamlit, SQLite, XGBoost (XGBClassifier), networkx
- **Goal:** Ship a functional autonomous fraud-agent demo that wins/places at hackathon

## Context

This project was assessed by a 7-specialist panel on 2026-02-05. Full report at `docs/FEASIBILITY_REPORT.md`.

### Current State (Post-Assessment)

| Component | Status | Notes |
|-----------|--------|-------|
| Directory structure | Done | Clean separation: /sim, /backend, /risk, /patterns, /ui, /schemas |
| JSON schemas (6) | Done | All validated, Draft-07 compliant |
| Backend API | Done | FastAPI with CRUD endpoints for txns, cases, labels, metrics, patterns |
| UI dashboard | Done | Streamlit with 3 tabs (Live Stream, Cases, Patterns) |
| Risk scorer | Done | XGBClassifier with 34 features (27 core + 7 pattern-derived), wired into pipeline |
| Pattern miner | Done | 4 graph algorithms: ring detection, hub analysis, velocity clusters, dense subgraphs |
| Simulator | Done | 5 fraud typologies with overlapping log-normal distributions, ISO 20022 metadata |
| ML model | Done | XGBClassifier (XGBoost), versioned models, hot-reload on retrain |
| LLM integration | Done | Ollama llama3.1:8b with 3-tier fallback (Golden Path / LLM / Template) |
| Retraining loop | Done | /retrain endpoint, analyst labels drive model improvement |
| Velocity features | Done | 11 velocity SQL queries per transaction |
| Tests | Done | 49 passing (schema + pipeline + API + ML tests) |

### Panel Verdict

**CONDITIONAL NO** — credible path to YES. Current hackathon success: 55-65%. With fixes: 75-85%.

### Top 5 Priorities (Panel Consensus)

1. Wire risk scorer into pipeline (2-4h)
2. Add LLM integration for case reasoning (8-12h)
3. Implement retraining loop (4-8h)
4. Fix simulator with realistic distributions (4-6h)
5. Add velocity-based features (2-4h)

## Success Criteria (Hackathon)

- [ ] Demo runs end-to-end in 60 seconds showing the full loop
- [ ] Risk scorer returns real scores (not None)
- [ ] At least one LLM integration point (case summary or risk explanation)
- [ ] Retraining loop visibly improves metrics
- [ ] Pattern cards generated from actual graph mining
- [ ] Simulator generates non-trivially-separable data
- [ ] UI shows: stream flowing, cases opening, labels applied, learning update, pattern cards

## Constraints

- Language: Python (type hints required)
- Backend: FastAPI
- UI: Streamlit
- DB: SQLite (single file app.db)
- ML: XGBoost (XGBClassifier)
- Graph: networkx
- No external infrastructure
- No distributed systems
- Synthetic data only (no real PII)

## Key Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Dev OS governance, modes, toolbelt, rules |
| `docs/FEASIBILITY_REPORT.md` | Full 7-specialist panel assessment |
| `docs/SCHEMA_CHANGES.md` | Schema change log |
| `schemas/*.schema.json` | Contract source of truth (6 schemas) |
| `backend/main.py` | FastAPI endpoints |
| `backend/db.py` | Async SQLite connection + table definitions |
| `risk/scorer.py` | Risk scoring (currently placeholder) |
| `patterns/miner.py` | Pattern mining (currently placeholder) |
| `sim/main.py` | Transaction simulator |
| `ui/app.py` | Streamlit dashboard |
| `scripts/demo.py` | One-command demo runner |
