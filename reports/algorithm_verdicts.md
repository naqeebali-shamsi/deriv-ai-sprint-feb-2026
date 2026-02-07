# Algorithm Verdict Report — Staff Engineer Synthesis

**Autonomous Fraud Detection Agent — Deriv AI Talent Sprint 2026**
**Date:** 2026-02-07
**Method:** 4 specialist audits (Pattern Detection, Risk Scoring, Backend Systems, Simulator) synthesized by Staff Engineer
**Scope:** Every static function and algorithm in the codebase evaluated for: correctness, complexity, and whether to REWRITE with proper algorithms or REPLACE with LLM agents

---

## Verdict Legend

| Verdict | Meaning |
|---------|---------|
| **REWRITE** | Replace with specific named algorithm/data structure (LeetCode-level) |
| **LLM_AGENT** | Replace static logic with LLM agent call (reasoning task, not computable) |
| **PATCH** | Keep algorithm, fix specific bug or add guard |
| **KEEP** | Acceptable as-is for hackathon scope |

---

## Master Verdict Table

### P0 — Critical (Demo correctness or fundamental algorithmic failure)

| # | Function | File | Current State | Verdict | Specific Algorithm/Approach |
|---|----------|------|--------------|---------|---------------------------|
| 1 | `detect_velocity_clusters` | `patterns/miner.py:179` | **`window_minutes` is dead code.** Counts total txns, not rate. This is NOT velocity detection. | **REWRITE** | **Sliding Window Two-Pointer** (LC #239 family). Sort by timestamp, two pointers define window of `window_minutes` width. Track `max_count` across all positions. O(T log T) sort + O(T) scan. |
| 2 | `compute_pattern_features` | `patterns/features.py:53` | **Substring matching bug.** `sender_id in desc` matches `user_1` inside `user_10`, `user_100`. False positive pattern associations + false negatives for IDs >12 chars (truncated in descriptions). | **REWRITE** | **Inverted Index.** Add `member_ids: list[str]` to PatternCard. Build `dict[str, list[PatternCard]]` at mining time. O(1) lookup per entity. Use `detection_rule["type"]` for classification instead of description parsing. |
| 3 | `compute_features` / `compute_training_features` | `scorer.py:32` / `trainer.py:111` | **Two near-identical implementations.** Training-serving feature skew — if one changes and other doesn't, model trains on different features than it serves. Classic ML production bug. | **REWRITE** | **Delete `compute_training_features` entirely.** Use `compute_features()` as single source of truth for both training and serving. Zero tolerance for duplication in feature pipelines. |
| 4 | `train_model` (bootstrap metrics) | `trainer.py:192` + `bootstrap_model.py` | **v0.1.0 reports 1.0/1.0/1.0/1.0.** Bootstrap velocity injection creates zero-overlap distributions. `pattern_count_sender` is non-zero only for fraud → trivially separable. Model learns a useless decision boundary. | **REWRITE** | Add `pattern_count_sender = random.uniform(0, 0.5)` for 20% of legit samples (power users flagged by patterns innocuously). Add more velocity overlap between fraud and legit distributions. Target bootstrap metrics: F1 0.85-0.95 (not 1.0). |

### P1 — High (Significant algorithmic improvement, defensibility under judge scrutiny)

| # | Function | File | Current State | Verdict | Specific Algorithm/Approach |
|---|----------|------|--------------|---------|---------------------------|
| 5 | `detect_rings` | `patterns/miner.py:60` | `list(nx.simple_cycles(G, length_bound=6))` materializes ALL cycles → combinatorial explosion on dense graphs. Confidence formula inverted (longer = higher, should be lower). | **REWRITE** | **Tarjan's SCC + bounded DFS.** Use `nx.strongly_connected_components(G)` (O(V+E)) to find SCCs. Report SCCs of size >=3 as ring indicators. Optionally extract one representative cycle per SCC via bounded DFS. Rank by total flow weight. Invert confidence: shorter cycles = higher confidence. |
| 6 | `detect_hubs` | `patterns/miner.py:112` | Absolute threshold `degree >= 5` is non-adaptive. Ignores edge weights. | **REWRITE** | **Z-score on weighted degree** OR **HITS algorithm.** Option A: Compute mean/std of degree distribution, flag nodes > mean + 2*std. Also compute weighted degree (strength). Option B: `nx.hits(G)` produces hub/authority scores natively — textbook algorithm for this exact problem. O(V+E) per iteration. |
| 7 | `detect_dense_subgraphs` | `patterns/miner.py:220` | Converts to undirected graph → loses directionality. A→B→C looks same as A↔B↔C. | **REWRITE** | **Tarjan's SCC + flow-weighted density.** Replace `G.to_undirected()` + `connected_components()` with `nx.strongly_connected_components(G)`. Within each SCC, compute directed density AND total flow weight. Rank by `density * log(total_flow + 1)`. |
| 8 | 11 serial velocity queries | `backend/main.py:207-324` | 11 sequential SQL queries per transaction. 3 queries have NO index support. ~5.5ms latency per txn from serial round-trips alone. | **REWRITE** | **Query consolidation + indexes.** Combine sender queries 1-4+11 into 1 query with conditional aggregation (CASE WHEN). Combine receiver queries 5-7 into 1 query. Add 4 missing indexes: `idx_txn_receiver_ts(receiver_id, timestamp)`, `idx_txn_sender_receiver(sender_id, receiver_id)`, `idx_txn_device_ts(device_id, timestamp)`, `idx_txn_ip_ts(ip_address, timestamp)`. Reduces 11 queries → 3-4 queries, latency 5.5ms → ~1.5ms. |
| 9 | `train_model` (validation) | `trainer.py:192` | Single 80/20 split, no cross-validation. 6 test samples in v0.5.0 → metrics statistically meaningless. No `scale_pos_weight`. | **REWRITE** | **Stratified k-fold CV + class weights.** Add `scale_pos_weight = legit_count / fraud_count` to XGBClassifier. Use `StratifiedKFold(n_splits=5)` and report mean +/- std metrics. Add `early_stopping_rounds=10` with validation set. Raise `MIN_SAMPLES_PER_CLASS` to 30+. |
| 10 | Reasons generation | `scorer.py:277-313` | Hardcoded feature thresholds (0.5, 0.3, 0.4) completely decoupled from model. A feature with 0.0 model importance can still generate a reason. | **LLM_AGENT** | **SHAP-informed LLM reasoning.** Compute SHAP values per prediction (XGBoost has native TreeSHAP, O(T*L*D)). Pass top-5 SHAP contributors to LLM agent with prompt: "Given these features drove the risk score, explain why this transaction is suspicious." This replaces static threshold rules with model-aware, contextual reasoning. Fallback: if no LLM available, rank features by abs(SHAP value) and use templates. |
| 11 | Normalization constants | `scorer.py:32-209` | All 15+ normalization divisors are hardcoded magic numbers (10000, 50001, 20, 100, 50000, etc.). Not derived from data. | **REWRITE** | **FeatureConfig dataclass with percentile-derived bounds.** At each retrain, compute P99 of each raw feature from training data. Store in `models/feature_config_vX.Y.Z.json`. Load at scoring time. Replace `min(amount / 10000, 1.0)` with `min(amount / config.amount_p99, 1.0)`. Note: XGBoost is invariant to monotonic transforms, so this primarily fixes the reasons system and makes the pipeline self-calibrating. |
| 12 | Structuring threshold | `sim/main.py:113` | Amount range $200-$950. BSA reporting threshold is $10,000. This models normal small payments, not structuring. | **REWRITE** | Change to `truncated_normal(mean=9500, std=300, low=8000, high=9900)`. This clusters amounts just below the $10K reporting threshold — which is how real structuring works. |

### P2 — Medium (Correctness improvement, production readiness)

| # | Function | File | Current State | Verdict | Specific Algorithm/Approach |
|---|----------|------|--------------|---------|---------------------------|
| 13 | Explain-stream | `backend/main.py:708-772` | `list(_call_ollama_stream(prompt))` materializes ALL chunks before yielding. Defeats purpose of streaming. | **REWRITE** | **Async queue bridge.** Use `asyncio.Queue` between sync Ollama iterator (in executor thread) and async generator. Thread pushes chunks to queue, async generator yields from queue. True chunk-by-chunk streaming to client. |
| 14 | Metrics computation | `backend/main.py:777-823` | Loads ALL labels into Python memory, iterates 5x with list comprehensions. | **REWRITE** | **Single SQL aggregation.** Replace with one query using conditional `SUM(CASE WHEN ...)` for TP, FP, total_fraud, total_flagged, total_labels. O(1) memory. |
| 15 | Spoofing generator | `sim/main.py:199` | Generates completed transfers, not order-place-cancel. Fundamentally mismodels spoofing. | **REWRITE** | **Rename to `generate_unauthorized_transfer`.** Adjust amount to `lognormal(mean=3000, sigma=0.8)` for more overlap with legit. If ambitious: add order lifecycle model with place/cancel events. |
| 16 | Adversarial generators (3 broken) | `sim/adversarial.py` | `stealth_wash_trade`, `subtle_structuring`, `slow_velocity_abuse` use new random IDs per call → no patterns form, don't test what they claim. | **REWRITE** | **Stateful batch generation.** `generate_mixed_evasion_batch()` creates persistent ID pools at batch start. Wash trade: create 4-6 IDs, generate circular flows among them. Velocity: create 5 IDs, generate burst sequences (10 txns from same sender). Structuring: create 3 IDs, generate sequences of sub-threshold amounts from same sender. |
| 17 | `hour_of_day` encoding | `scorer.py:106` | Linear `hour / 23.0` makes hour 0 and hour 23 maximally distant (0.0 vs 1.0). They're actually 1 hour apart. | **REWRITE** | **Cyclical encoding:** `hour_sin = sin(2*pi*hour/24)`, `hour_cos = cos(2*pi*hour/24)`. Replaces 1 feature with 2 features but correctly represents cyclical time. Add to FEATURE_NAMES. |
| 18 | `_get_ml_model` / `reload_model` | `scorer.py:212-231` | Function attribute caching not thread-safe. Race condition during reload: scoring requests see None between cache clear and reload. | **REWRITE** | **Atomic swap with lock.** Load new model into temp variable first, then swap reference under `threading.Lock`. Never expose None state. Better: `ModelRegistry` class with `get()` and `swap(new_model)` methods. |
| 19 | Named fraud pools | `sim/main.py` | 3-5 accounts per fraud type. Model memorizes sender velocity as proxy for sender identity. | **REWRITE** | Increase to 10-15 accounts per type. Randomly select 3-5 per simulation run for variety. This breaks the velocity-as-identity proxy. |
| 20 | First-time counterparty query | `backend/main.py:267-273` | No time bound, no composite index. Full scan grows with total transactions. | **REWRITE** | Add composite index `(sender_id, receiver_id)`. Optionally add 90-day time bound to prevent unbounded growth. |
| 21 | Pattern dedup in `run_mining_job_async` | `patterns/miner.py:332` | Name-based dedup. Two different 3-member rings get same name → second silently dropped. | **REWRITE** | **Structural signature dedup.** Hash sorted `member_ids` tuple: `dedup_key = hash(tuple(sorted(pattern.member_ids)))`. Two structurally identical patterns dedup; structurally different ones don't collide. |

### P3 — Low (Tech debt, nice-to-have)

| # | Function | File | Current State | Verdict | Specific Algorithm/Approach |
|---|----------|------|--------------|---------|---------------------------|
| 22 | SSE subscriber list | `backend/main.py:1109-1154` | Unbounded list, O(S) removal, silent drops | **PATCH** | Add `MAX_SUBSCRIBERS = 50` guard. Log on `QueueFull` drops. Use `set` instead of `list` for O(1) removal. |
| 23 | Auto-retrain debouncing | `backend/main.py:542-562` | Every label spawns background task with COUNT queries. No cooldown. | **PATCH** | Add `_last_retrain_time` global. Skip if < 60s since last retrain. |
| 24 | `ip_country_risk` hardcoded map | `scorer.py:146-157` | Only 7 countries, discriminatory defaults, not data-derived. | **PATCH** | Expand to 20+ countries from public fraud rate data. Change default from 0.4 to 0.2. Add comment citing data source. Long-term: derive from platform's historical fraud rates per-country. |
| 25 | `card_bin_risk` arbitrary ranges | `scorer.py:159-171` | BIN ranges 460000-499999 = 0.7 is meaningless. Not how BIN risk works. | **PATCH** | Either remove entirely (set to 0.0) or replace with a 10-entry lookup from public chargeback rate data. Don't pretend arbitrary ranges are risk scores. |
| 26 | Redundant PRAGMA per connection | `backend/db.py:11-21` | `PRAGMA journal_mode=WAL` set on every connection (persistent per DB file). | **PATCH** | Set WAL once at init time. Set `synchronous=NORMAL` per connection at pool level if using pool. |
| 27 | Pydantic field stripping in adversarial | `sim/adversarial.py` | `time_since_last_txn_minutes` and `txn_id` set but stripped by Pydantic. Dead code. | **PATCH** | Remove dead field assignments. Document that velocity is computed server-side. |
| 28 | Pattern confidence formulas | `patterns/miner.py` | All confidence formulas are arbitrary linear functions. | **KEEP** | Acceptable for hackathon. Document as "placeholder confidence — not calibrated." |
| 29 | `build_transaction_graph` | `patterns/miner.py:33` | O(T) construction, already optimal. | **KEEP** | No change needed. |
| 30 | `generate_legit_transaction` | `sim/main.py:83` | lognormal(200, 1.2), good overlap. | **KEEP** | Solid distribution choice. |
| 31 | `generate_wash_trading_transaction` | `sim/main.py:167` | Best generator. Correct circular flows. | **KEEP** | Crown jewel of simulator. |
| 32 | `generate_bonus_abuse_transaction` | `sim/main.py:226` | Correct device/IP sharing model. | **KEEP** | Second best generator. |
| 33 | `generate_hero_transaction` | `sim/main.py:263` | Demo reliability mechanism. | **KEEP** | Essential for golden path. |

---

## LLM_AGENT vs REWRITE Decision Framework

The Staff Engineer verdict on the central question: **when should static algorithms be replaced by LLM agents?**

### Use LLM Agents When:
- The output is **natural language** (explanations, summaries, recommendations)
- The task requires **contextual reasoning** across heterogeneous data (features + patterns + history)
- There is **no computable optimal answer** (judgment calls, risk narratives)
- Latency tolerance is **>1 second** (not in the scoring hot path)

### Use Algorithms When:
- The operation is **mathematically defined** (cycle detection, sliding windows, z-scores)
- The output is **numeric or boolean** (feature values, cluster membership, scores)
- It's in the **hot path** (<50ms budget per transaction)
- **Correctness is verifiable** (you can write a unit test for the expected output)

### Specific LLM_AGENT Verdicts:

| Component | Verdict | Reasoning |
|-----------|---------|-----------|
| **Reasons generation** (#10) | **LLM_AGENT** | Current: hardcoded threshold rules decoupled from model. Optimal: SHAP values identify which features drove the score, then LLM generates contextual human-readable explanation. This is inherently a NL generation task — an algorithm can rank features by importance but cannot explain *why* high velocity from Nigeria at 3am on a weekend is suspicious in the context of a derivatives platform. |
| **Pattern confidence scoring** | **KEEP (data) + LLM_AGENT (enrichment)** | Confidence scores should remain algorithmic (flow weight, cycle length, density). But the pattern card *description* and *investigation recommendation* should be LLM-generated from the structural data. |
| **ip_country_risk** | **NOT LLM_AGENT** | Must be <1ms per transaction. Use data-derived lookup table, not LLM. |
| **Spoofing detection** | **NOT LLM_AGENT** | Order lifecycle is a data modeling problem, not a reasoning problem. Either model the data correctly or rename the fraud type. |
| **Adversarial test generation** | **LLM_AGENT (optional)** | An LLM could generate novel evasion strategies by reasoning about the feature space. But for the hackathon, fixing the stateful batch generation is higher ROI. |

---

## Implementation Roadmap (Ordered by Hackathon Impact)

### Wave 1: Critical Fixes (1-2 hours, biggest demo/correctness impact)

1. **Delete `compute_training_features`**, use `compute_features` everywhere (#3) — 15 min
2. **Fix velocity cluster sliding window** (#1) — 30 min
3. **Fix pattern feature substring matching** → inverted index (#2) — 30 min
4. **Add bootstrap overlap** for `pattern_count_sender` in legit samples (#4) — 15 min

### Wave 2: Algorithm Upgrades (2-3 hours, defensibility under judge scrutiny)

5. **Ring detection → Tarjan's SCC** (#5) — 45 min
6. **Hub detection → z-score or HITS** (#6) — 30 min
7. **Dense subgraph → SCC + flow-weighted** (#7) — 30 min
8. **Velocity query consolidation** + 4 indexes (#8) — 45 min
9. **Stratified k-fold CV + scale_pos_weight** (#9) — 30 min

### Wave 3: Polish (1-2 hours, production readiness signals)

10. **Reasons → SHAP + LLM agent** (#10) — 60 min
11. **FeatureConfig with percentile normalization** (#11) — 45 min
12. **True async streaming for explain** (#13) — 30 min
13. **Cyclical time encoding** (#17) — 15 min
14. **Fix structuring threshold** (#12) — 10 min
15. **Rename spoofing** (#15) — 10 min

### Wave 4: Simulator Hardening (1 hour, if time permits)

16. **Stateful adversarial batch generation** (#16) — 45 min
17. **Increase fraud account pools** (#19) — 15 min
18. **Remove dead code in adversarial generators** (#27) — 10 min

---

## Aggregate Statistics

| Category | Total Items | REWRITE | LLM_AGENT | PATCH | KEEP |
|----------|------------|---------|-----------|-------|------|
| Pattern Detection | 7 | 5 | 0 | 1 | 1 |
| Risk Scoring | 11 | 7 | 1 | 2 | 1 |
| Backend Systems | 10 | 5 | 0 | 3 | 2 |
| Simulator | 9 | 4 | 0 | 1 | 4 |
| **Total** | **37** | **21** | **1** | **7** | **8** |

**57% of algorithms need rewriting.** Only 1 component (reasons generation) should be an LLM agent — everything else is a pure algorithm problem with known optimal solutions.

---

## The Staff Engineer's Bottom Line

This codebase has the **right architecture** (feature pipeline → ML model → graph mining → LLM explanation) but **naive implementations** at nearly every algorithmic level. The good news: every fix has a well-known textbook algorithm. There are no research problems here — it's all engineering.

The single most impactful change is **#1 (velocity cluster sliding window)** because it fixes a feature that is literally non-functional — the system claims to detect velocity but doesn't. Combined with #2 (pattern feature substring fix) and #3 (training-serving skew), these three P0 fixes would transform the system from "demo that works by accident" to "demo with defensible algorithms."

The LLM agent verdict is narrow by design: **only the reasons/explanation layer benefits from LLM reasoning.** Everything in the scoring hot path — feature computation, normalization, pattern detection, graph mining — should be deterministic algorithms. This aligns with the project's own golden rule: "LLM does orchestration and explanations, not math."

---

*Synthesized from 4 specialist audits: Pattern Detection (algo-patterns), Risk Scoring (algo-scoring), Backend Systems (algo-backend), Simulator Fraud Algorithms (algo-simulator). All findings cross-validated against the codebase at commit 77b4760.*
