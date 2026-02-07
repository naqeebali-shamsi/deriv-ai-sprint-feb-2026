# PROJECT.md — Autonomous Fraud Detection Agent

## Project Identity

- **Name:** Autonomous Fraud Detection Agent
- **Type:** Hackathon MVP (Deriv AI Talent Sprint, Feb 6-8, 2026)
- **Stack:** Python, FastAPI, Streamlit, SQLite, scikit-learn, networkx
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
| Risk scorer | Placeholder | 3 hardcoded features, NOT wired into pipeline, returns None |
| Pattern miner | Placeholder | Checks amount > 5000 only, no graph analysis |
| Simulator | Partial | Generates data but trivially separable (fraud=$5K-50K, legit=$10-2K) |
| ML model | Missing | No trained model, no training loop, no evaluation |
| LLM integration | Missing | Zero LLM calls despite "agent" framing |
| Retraining loop | Missing | Labels stored but never used for learning |
| Velocity features | Missing | No per-user temporal aggregations |
| Tests | Done | 22 passing (schema validation + pipeline smoke tests) |

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
- ML: scikit-learn
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
| `scripts/demo.sh` | One-command demo runner |
