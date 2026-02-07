# QA Demo Flow & Schema Compliance Report

**Date:** 2026-02-07
**Tester:** Red Team Agent (Schema & Demo QA)
**Target:** Autonomous Fraud Agent Demo (http://localhost:8000, http://localhost:8501)

---

## Executive Summary

Schema validation infrastructure passes (all 6 schema files are valid JSON Schema Draft-7). However, **all 6 API responses have schema drift** -- the API returns different field sets than the schemas define. The demo flow works end-to-end but has several minor issues: a step numbering bug, a feature count discrepancy in the demo script (claims 27, actual is 34), and metric claims (F1 0.57->0.97) that depend on a fresh DB state.

**Overall:** Demo is functional and impressive. Schema drift is cosmetic (API works fine, schemas just don't match API responses). No blocking issues for demo day.

---

## 1. Schema Validation Script

**Command:** `python scripts/validate_schemas.py`

**Result:** PASSED -- All 6 schemas valid

```
[OK] analyst_label.schema.json: OK
[OK] case.schema.json: OK
[OK] metric_snapshot.schema.json: OK
[OK] pattern_card.schema.json: OK
[OK] risk_result.schema.json: OK
[OK] transaction.schema.json: OK
PASSED: All 6 schemas valid
```

**Note:** This script only validates that the schema files themselves are valid JSON Schema. It does NOT validate API responses against the schemas. This is a validation gap.

---

## 2. Schema Compliance: API Responses vs Schema Definitions

### 2.1 transaction.schema.json vs GET /transactions

| Category | Fields |
|---|---|
| In schema but NOT in API | `ip_address`, `is_fraud_ground_truth`, `metadata`, `device_id` |
| In API but NOT in schema | `decision`, `risk_score` |
| Schema validation | **FAIL** -- `additionalProperties: false` rejects `decision` and `risk_score` |

**Root Cause:** `GET /transactions` returns `TransactionOut` (Pydantic model) which includes `risk_score` and `decision` from the risk result join. The schema defines the raw transaction without scoring info. The API omits nullable fields that are null.

**Severity:** Medium -- Schema drift. The schema is the "storage contract" not the "API response contract". These are different shapes.

### 2.2 case.schema.json vs GET /cases

| Category | Fields |
|---|---|
| In schema but NOT in API | `closed_at`, `updated_at`, `assigned_to`, `matched_patterns` |
| Schema validation | **PASS** (missing fields are not `required`) |

**Root Cause:** `GET /cases` returns `CaseOut` which only includes 6 fields (case_id, txn_id, status, created_at, priority, risk_score). Optional fields like `closed_at` and `assigned_to` are not returned even when they have values.

**Severity:** Low -- Optional fields simply omitted from API response model.

### 2.3 pattern_card.schema.json vs GET /patterns

| Category | Fields |
|---|---|
| In schema but NOT in API | `related_txn_ids`, `stats`, `detection_rule` |
| Schema validation | **PASS** (missing fields are not `required`) |

**Root Cause:** Pattern API returns only core fields. The schema defines optional subobjects (`stats`, `detection_rule`, `related_txn_ids`) that are stored in DB but not exposed in the list endpoint.

**Severity:** Low -- Schema is broader than API response.

### 2.4 metric_snapshot.schema.json vs GET /metric-snapshots

| Category | Fields |
|---|---|
| In schema but NOT in API | `metrics` (required!) |
| In API but NOT in schema | `test_samples`, `feature_importance`, `fraud_samples`, `train_samples`, `precision`, `auc_roc`, `legit_samples`, `f1`, `recall` |
| Schema validation | **FAIL** -- `metrics` is a required property but the API flattens metrics into the top level |

**Root Cause:** The API endpoint `list_metric_snapshots()` at `backend/main.py:911-935` unpacks the `metrics` JSON blob into the top-level response object using `**metrics`. The schema expects `metrics` as a nested object. This is a structural mismatch.

**Severity:** High -- Schema requires `metrics` as nested object, API flattens it. This is a genuine contract violation.

### 2.5 risk_result.schema.json vs Transaction Detail

| Category | Fields |
|---|---|
| Present in `/transactions/{id}` | `txn_id`, `timestamp`, `risk_score`, `features`, `matched_patterns`, `model_version` |
| Missing from `/transactions/{id}` | `threshold_used`, `flagged` |

**Note:** `risk_result` is not exposed as a standalone API endpoint. It is embedded within the transaction detail response. The schema is a DB/internal contract, not an API contract.

**Severity:** Low -- Intentional design; risk_result is internal.

### 2.6 analyst_label.schema.json vs POST /cases/{id}/label response

| Category | Fields |
|---|---|
| In schema but NOT in response | `txn_id`, `fraud_type`, `labeled_by`, `labeled_at`, `confidence`, `decision`, `notes` (7 of 8 schema fields missing) |
| In response but NOT in schema | `new_status` |
| Schema validation | **FAIL** -- `decision` is required but not returned |

**Root Cause:** The label endpoint returns a summary response `{label_id, case_id, new_status}` not the full analyst_label object. The schema defines the stored object, not the API response.

**Severity:** Medium -- The API response and schema describe completely different shapes. The API returns a confirmation, the schema defines the stored record.

### Schema Compliance Summary

| Schema | Validation | API Match | Severity |
|---|---|---|---|
| transaction.schema.json | Schema valid | **DRIFT** -- extra fields in API | Medium |
| case.schema.json | Schema valid | **PARTIAL** -- optional fields omitted | Low |
| pattern_card.schema.json | Schema valid | **PARTIAL** -- optional fields omitted | Low |
| metric_snapshot.schema.json | Schema valid | **FAIL** -- structural mismatch (flattened vs nested) | High |
| risk_result.schema.json | Schema valid | N/A -- no standalone API endpoint | Low |
| analyst_label.schema.json | Schema valid | **FAIL** -- response is a summary, not full object | Medium |

---

## 3. Demo Flow Verification

### 3.1 demo.py Step Analysis

| Step | Description | Status | Notes |
|---|---|---|---|
| [1/6] | Init database | Works | **BUG:** Says [1/6] but there are 7 steps (should be [1/7]) |
| [2/7] | Validate schemas | Works | All 6 schemas pass validation |
| [3/7] | Bootstrap ML model | Works | Creates initial model from synthetic data |
| [4/7] | Start backend | Works | uvicorn on port 8000 |
| [5/7] | Seed demo data | Works | Sends 200 + 50 post-training = 250 total |
| [6/7] | Start Streamlit UI | Works | Port 8501, headless mode |
| [7/7] | Start simulator | Works | 1 TPS continuous |

**Bug Found:** Step 1 says `[1/6]` but all other steps use `/7` denominator. Should be `[1/7]`.

### 3.2 Service Health (Live Verification)

| Service | Status | URL |
|---|---|---|
| Backend API | Running (HTTP 200) | http://localhost:8000 |
| Streamlit UI | Running (HTTP 200) | http://localhost:8501 |
| Ollama LLM | Running (llama3.1:8b loaded) | http://localhost:11434 |
| Simulator | Configurable via API | /simulator/status |

All 9 tested API endpoints returned HTTP 200.

### 3.3 Database State

| Table | Rows | Expected |
|---|---|---|
| transactions | 304 | 250+ (seed + test txns) |
| risk_results | 304 | Matches transactions |
| cases | 118 | ~30-40% of flagged txns |
| analyst_labels | 37 | From labeling tests |
| pattern_cards | 16 | From mining |
| metric_snapshots | 12 | From retrain cycles |

All 6 required tables present. `model_state` extra table also present (from init_db.py but not in schemas).

### 3.4 Index Coverage

All expected indexes present:
- `idx_txn_sender_ts` (velocity queries)
- `idx_txn_receiver` (receiver queries)
- `idx_transactions_timestamp` (time range queries)
- `idx_cases_status` (case filtering)
- `idx_risk_results_flagged` (flagged filtering)

---

## 4. DEMO_SCRIPT.md Claim Verification

### Claim: "27 behavioral features"
**Actual:** 34 features
**Verdict:** INACCURATE -- Feature count increased from 27 to 34 (7 pattern-derived features were added: `sender_in_ring`, `sender_is_hub`, `sender_in_velocity_cluster`, `sender_in_dense_cluster`, `receiver_in_ring`, `receiver_is_hub`, `pattern_count_sender`). Demo script needs updating.

### Claim: "F1 of 0.57, version 2 jumped to 0.97"
**Actual:** Current F1 values range from 0.40 to 0.83 across versions
**Verdict:** NOT VERIFIABLE in current state -- These numbers likely apply to a clean demo run. The DB has been modified by QA testing (label poisoning from red team). A fresh `demo.py` run would need to be tested to verify. The claim is plausible but not confirmed.

### Claim: "precision of 0.957"
**Actual:** Precision values range from 0.50 to 1.0 across snapshots
**Verdict:** PARTIALLY VERIFIED -- Some snapshots show precision=1.0 which exceeds 0.957. The specific 0.957 value was not observed.

### Claim: "5 fraud typologies"
**Actual:** 5 types configured: structuring, velocity_abuse, wash_trading, spoofing, bonus_abuse
**Verdict:** VERIFIED

### Claim: "Active learning - model identifies most uncertain predictions"
**Actual:** `/cases/suggested` returns cases sorted by uncertainty (distance from 0.5)
**Verdict:** VERIFIED -- Top suggested case has uncertainty=0.009 (risk_score=0.509, very close to 0.5)

### Claim: "AI agent explains WHY with Llama 3.1"
**Actual:** `/cases/{id}/explain` returns structured explanation with 13 sections
**Verdict:** VERIFIED -- Response includes: summary, risk_factors, behavioral_analysis, pattern_context, recommendation, confidence_note, investigation_timeline, full_explanation, agent identifier

### Claim: "Gradient Boosting model trained on 27 behavioral features"
**Actual:** GradientBoostingClassifier with 34 features (FEATURE_NAMES in trainer.py)
**Verdict:** PARTIALLY ACCURATE -- Model type is correct, feature count is outdated (34 not 27)

### Claim: "Pattern cards: circular rings, hub accounts, velocity spikes"
**Actual:** 10 patterns found including ring patterns (graph), velocity spikes, and high-activity sender hubs
**Verdict:** VERIFIED

| Claim | Verdict |
|---|---|
| 27 features | INACCURATE (34) |
| F1 0.57->0.97 | NOT VERIFIABLE (dirty DB state) |
| Precision 0.957 | NOT OBSERVED (but plausible) |
| 5 fraud typologies | VERIFIED |
| Active learning | VERIFIED |
| AI explain with Llama | VERIFIED |
| GradientBoosting | VERIFIED (feature count wrong) |
| Pattern cards | VERIFIED |
| Color-coded risk chips | PARTIALLY (no "review" txns in last 10) |

---

## 5. Edge Case Testing

### Edge Case 1: Port 8000 already in use
**Test:** Code analysis of demo.py
**Finding:** `demo.py` does NOT check if port 8000 is in use before starting uvicorn. If the port is occupied:
- uvicorn subprocess will fail to bind (error in stderr)
- `wait_for_backend()` will retry 15 times then print "WARNING: Backend may not be ready"
- Demo continues anyway (seed_demo.py will fail on HTTP connection)
- No graceful exit or "port in use" error message
**Severity:** Medium -- Demo operator would see confusing errors without clear cause

### Edge Case 2: app.db locked by another process
**Test:** Code analysis
**Finding:** demo.py deletes `app.db` before init. If another process (e.g., prior demo) has the DB open:
- `db_path.unlink()` will raise `PermissionError` on Windows
- demo.py does not catch this exception
- Demo would crash with unhelpful traceback
**Severity:** Medium -- Windows-specific issue, would block demo start

### Edge Case 3: Ollama not running
**Test:** Live API verification
**Finding:** The explain endpoint (`/cases/{id}/explain`) uses `explain_case()` from `risk/explainer.py` which has a fallback to deterministic template-based explanations if Ollama is unreachable.
- Response includes `agent: "fraud-agent-llm (llama3.1:8b)"` or `agent: "fraud-agent-deterministic"`
- Demo works fully without Ollama
**Severity:** None -- Well-handled fallback. Demo script mentions this: "Explanations will use template fallback"

### Edge Case 4: Running demo.py twice simultaneously
**Test:** Code analysis
**Finding:** Second instance would:
1. Delete app.db (data loss for first instance)
2. Fail to bind port 8000 (already used by first instance)
3. Try to start another Streamlit on port 8501 (would conflict)
- No lockfile or PID check to prevent double-start
**Severity:** Low -- Unlikely in demo context, but destructive if it happens

### Edge Case 5: Seed count discrepancy
**Test:** Code analysis
**Finding:** `demo.py` calls `seed_demo.py --count 200`, but `seed_demo.py` also sends 50 more transactions after retraining (lines 104-120). Total seeded: 250, not 200.
**Severity:** Low -- Cosmetic, doesn't affect demo quality

### Edge Case 6: Step numbering bug
**Test:** Code analysis of demo.py line 91 vs lines 98+
**Finding:** Step 1 says `[1/6]` but there are 7 steps. All other steps correctly say `/7`.
**Severity:** Low -- Cosmetic typo

---

## 6. Demo 60-Second Clarity Checklist

From CLAUDE.md, the UI must visually show:

| Signal | Present | Notes |
|---|---|---|
| Stream flowing | YES | Transactions via SSE + simulator |
| Cases opening automatically | YES | High-risk txns auto-create cases |
| Analyst labels applied | YES | Label endpoint works |
| "Learning update" animation/event | YES | Retrain endpoint works, SSE publishes retrain events |
| Metric trend improving | PARTIAL | Trend data exists, but not always monotonically improving |
| New pattern card appearing | YES | 10+ patterns discovered from graph mining |

---

## 7. Findings Summary

### Critical Issues (0)
None -- no demo-blocking issues.

### High Issues (1)
1. **metric_snapshot schema structural mismatch** -- API flattens `metrics` into top-level, schema expects nested object. Breaks runtime validation if anyone uses the schema against API responses.

### Medium Issues (4)
2. **transaction schema drift** -- API adds `risk_score` and `decision` not in schema; schema has `additionalProperties: false`
3. **analyst_label response mismatch** -- API returns summary `{label_id, case_id, new_status}`, schema defines full stored record
4. **Demo claim "27 features"** -- Actually 34 features (7 pattern features added)
5. **Port conflict handling** -- No graceful error if port 8000 is already used

### Low Issues (5)
6. **case schema optional fields** -- Several optional fields not returned in API
7. **pattern_card optional fields** -- `stats`, `detection_rule`, `related_txn_ids` not exposed
8. **Step numbering bug** -- demo.py says [1/6] instead of [1/7]
9. **Seed count 250 not 200** -- seed_demo.py sends extra 50 post-training
10. **F1 0.57->0.97 claim** -- Not verifiable in current DB state (may work on fresh run)

---

## 8. Recommendations

### For Demo Day (Quick Fixes)
1. Update DEMO_SCRIPT.md: change "27 features" to "34 features" (or "30+ features")
2. Fix demo.py step 1: change `[1/6]` to `[1/7]`
3. Consider softening F1 claims: "F1 improved significantly across training cycles" vs specific numbers

### For Schema Compliance
4. Create separate "API response schemas" vs "storage schemas" -- they serve different purposes
5. Fix metric_snapshot API to return `{..., metrics: {...}}` nested structure matching schema
6. Or update schema to match the flattened API response

### For Robustness
7. Add port-in-use check in demo.py before starting uvicorn
8. Add try/except around `db_path.unlink()` in demo.py for Windows compatibility
9. Add a lockfile to prevent double-start

---

## Appendix: Test Commands

```bash
# Validate schemas
python scripts/validate_schemas.py

# Check all API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/transactions?limit=1
curl http://localhost:8000/cases?limit=1
curl http://localhost:8000/patterns?limit=1
curl http://localhost:8000/metrics
curl http://localhost:8000/metric-snapshots?limit=1

# Run full demo
python scripts/demo.py
```
