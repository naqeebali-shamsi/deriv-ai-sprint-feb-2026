# System Stats — Technical Deep Dive

> Every number on this page is traceable to source code. Nothing is estimated or projected.

---

## 1. ML Model: 35 Features | 5-Fold Stratified CV | F1 = 0.97

**Model:** XGBClassifier with L1/L2 regularization (`reg_alpha`, `reg_lambda`), class imbalance handling via `scale_pos_weight = 6.69`.

**Validation:** Stratified 5-fold cross-validation (`StratifiedKFold(n_splits=5)` via `cross_val_score`). Not a single train/test split.

| Metric | Value |
|--------|-------|
| CV F1 (mean +/- std) | 0.97 +/- 0.04 |
| CV F1 per fold | 1.00, 0.90, 1.00, 1.00, 0.95 |
| Holdout Precision | 0.981 |
| Holdout Recall | 1.000 |
| Holdout AUC-ROC | 1.000 |
| Training samples | 400 (52 fraud, 348 legit) |

**35 engineered features** (28 core + 7 pattern-derived):

| Category | Features | Count |
|----------|----------|-------|
| Amount | `amount_normalized`, `amount_log`, `amount_high`, `amount_small` | 4 |
| Transaction type | `is_transfer`, `is_withdrawal`, `is_deposit`, `is_payment`, `is_small_deposit` | 5 |
| Channel | `channel_web`, `channel_api` | 2 |
| Time | `hour_sin`, `hour_cos` (cyclical encoding), `is_weekend`, `hour_risky` | 4 |
| Sender velocity | `sender_txn_count_1h`, `sender_txn_count_24h`, `sender_amount_sum_1h`, `sender_unique_receivers_24h`, `time_since_last_txn_minutes` | 5 |
| Device/IP | `device_reuse_count_24h`, `ip_reuse_count_24h` | 2 |
| Receiver velocity | `receiver_txn_count_24h`, `receiver_amount_sum_24h`, `receiver_unique_senders_24h` | 3 |
| Counterparty | `first_time_counterparty` | 1 |
| Risk indicators | `ip_country_risk`, `card_bin_risk` | 2 |
| Graph-derived (pattern) | `sender_in_ring`, `sender_is_hub`, `sender_in_velocity_cluster`, `sender_in_dense_cluster`, `receiver_in_ring`, `receiver_is_hub`, `pattern_count_sender` | 7 |

**Top 3 features by importance:** `time_since_last_txn_minutes` (0.612), `pattern_count_sender` (0.153), `sender_amount_sum_1h` (0.119).

**Source:** `risk/scorer.py:compute_features()`, `risk/trainer.py`, `models/metrics_v0.1.0.json`

---

## 2. Graph Algorithms: 4 Algorithms x 5 Fraud Typologies

**Pattern detection** uses four textbook graph algorithms, not hand-rolled heuristics:

| Algorithm | What it finds | Implementation |
|-----------|---------------|----------------|
| Tarjan's SCC | Wash trading rings (circular fund flows) | `networkx.strongly_connected_components()` |
| HITS | Hub accounts (money mule networks) | `networkx.hits()` |
| Sliding window two-pointer | Velocity bursts (rapid-fire transactions) | Custom O(n) with sorted timestamps |
| SCC + flow-weighted density | Dense subgraphs (coordinated fraud clusters) | `networkx.strongly_connected_components()` + edge-weight density |

**5 fraud typologies** with adversarial evasion strategies:

| Typology | Evasion strategy | Generator state |
|----------|-----------------|-----------------|
| Wash trading | Persistent circular ID pools | Stateful (ring reuse) |
| Structuring | BSA-threshold amounts ($5K-$9.9K) | Stateful (recurring senders) |
| Velocity burst | Rapid-fire from same device/IP | Stateful (device pools) |
| Account takeover | Channel/device switching | Stateless |
| Unauthorized transfer | Amount overlap with legitimate range | Stateful (recurring senders) |

**Source:** `patterns/miner.py`, `patterns/features.py`, `sim/fraud_typologies.py`

---

## 3. Autonomous Actions: 7 Agent Behaviors, Zero Human Trigger

Every action below fires without any analyst clicking a button:

| # | Action | Trigger | Source |
|---|--------|---------|--------|
| 1 | Score every transaction | POST `/transactions` | `backend/main.py` |
| 2 | Open case if flagged | Risk score > threshold | `backend/main.py` |
| 3 | Generate LLM explanation | Case created (background task) | `backend/main.py:_auto_explain_case()` |
| 4 | Publish SSE events | Every pipeline stage | `backend/main.py:_publish_event()` |
| 5 | Mine patterns on schedule | APScheduler / asyncio loop | `backend/main.py` |
| 6 | Guardian decides retrain/skip/rollback | Label count + drift thresholds | `risk/guardian.py` |
| 7 | Threshold self-adjustment | After model retrain | `risk/trainer.py` |

The analyst's only inputs: click "Explain" (optional — auto-generated) and "Label" (confirm/reject).

**Source:** `backend/main.py`, `risk/guardian.py`, `risk/trainer.py`

---

## 4. API Surface: 25 Endpoints | 10 SSE Event Types | 9 DB Indexes

**25 REST endpoints** covering the full fraud lifecycle:

| Category | Endpoints |
|----------|-----------|
| Transactions | POST + GET list + GET detail |
| Cases | GET list + GET suggested + POST label + GET explain + GET explain-stream |
| Model | POST retrain + POST retrain-from-ground-truth + GET metrics + GET metric-snapshots |
| Patterns | POST mine-patterns + GET patterns |
| Simulator | GET status + POST start + POST stop + POST configure |
| System | GET health + GET ready + GET stream/events |

**10 SSE event types** for real-time UI:

`transaction`, `case_created`, `case_explained`, `case_labeled`, `pattern`, `retrain`, `simulator_started`, `simulator_stopped`, `simulator_configured`, `agent_decision`

**9 compound database indexes** optimized for velocity queries:

| Index | Purpose |
|-------|---------|
| `idx_txn_sender_ts` | Sender velocity (1h/24h windows) |
| `idx_txn_receiver` | Receiver lookups |
| `idx_txn_receiver_ts` | Receiver velocity windows |
| `idx_txn_sender_receiver` | Counterparty pair queries |
| `idx_txn_device_ts` | Device reuse detection |
| `idx_txn_ip_ts` | IP reuse detection |
| `idx_cases_status` | Case queue filtering |
| `idx_risk_results_flagged` | Flagged transaction lookups |
| `idx_agent_decisions_ts` | Guardian decision history |

Velocity query consolidation reduced 11 serial SQL queries to 5 using CASE WHEN aggregation.

**Source:** `backend/main.py`, `backend/db.py`

---

## 5. Codebase: 7,033 Lines Python | 3,962 Lines JS/HTML/CSS | 59 Tests | 7 Docker Services

| Metric | Value |
|--------|-------|
| Python (backend, risk, patterns, sim, scripts, tests) | 6,525 lines |
| Python (UI layer) | 508 lines |
| **Total Python** | **7,033 lines** |
| Frontend (JS + HTML + CSS) | 3,962 lines |
| Test functions | 59 |
| JSON Schema contracts | 6 |
| Docker services | 7 (backend, ui, ollama, ollama-pull, init-db, bootstrap-model, seed-data) |
| Docker named volumes | 3 (app-data, app-models, ollama-data) |
| CI/CD | GitHub Actions (bootstrap -> pytest -> SCP deploy to AWS Lightsail) |

**Self-improvement demonstrated:**

| Version | Trigger | F1 | Precision |
|---------|---------|-----|-----------|
| v0.1.0 (bootstrap) | Synthetic data | 0.57 | 0.54 |
| v0.2.0+ (retrained) | Analyst labels | 0.97 | 0.98 |

**Source:** `docker-compose.yml`, `.github/workflows/deploy.yml`, `tests/`, `models/`
