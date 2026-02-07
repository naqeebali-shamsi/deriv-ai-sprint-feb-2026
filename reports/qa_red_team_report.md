# QA Red Team Adversarial Testing Report

**Date:** 2026-02-07
**Tester:** Red Team Agent (Automated Adversarial QA)
**Target:** Autonomous Fraud Agent (http://localhost:8000)
**Model Version at Start:** v0.9.0 (GradientBoostingClassifier)

---

## Executive Summary

The fraud detection system was subjected to 9 phases of adversarial testing covering evasion techniques, input validation, race conditions, and label poisoning. **14 distinct vulnerabilities** were identified, including **4 Critical**, **4 High**, **4 Medium**, and **2 Low** severity issues.

**Most dangerous findings:**
1. Feature gaming allows 100% evasion with crafted normal-looking transactions
2. Wash trading (circular fund flows) goes completely undetected in real-time
3. Label poisoning degraded model precision from 75% to 50% in one attack
4. No authentication on any administrative endpoint (retrain, mine-patterns, simulator)

---

## Phase 1: Existing Adversarial Test Suite

**Command:**
```bash
python -m pytest tests/test_adversarial.py -v -s
```

**Results:**

| Strategy | Detection Rate | Flagged/Total |
|---|---|---|
| Subtle Structuring | 35% | 7/20 |
| Stealth Wash Trade | 25% | 5/20 |
| Slow Velocity Abuse | 30% | 6/20 |
| Legit-Looking Fraud | 100% | 20/20 |
| Bonus Abuse Evasion | 100% | 20/20 |

**Adversarial vs Standard Comparison:**
- Standard fraud detection: 62% (31/50)
- Adversarial fraud detection: 54% (27/50)
- Detection gap: 8%

**Per-strategy breakdown (50-txn mixed batch):**
| Strategy | Rate | Flagged/Total |
|---|---|---|
| bonus_abuse_evasion | 100% | 6/6 |
| legit_looking_fraud | 100% | 12/12 |
| slow_velocity_abuse | 8% | 1/12 |
| stealth_wash_trade | 29% | 2/7 |
| subtle_structuring | 46% | 6/13 |

**Verdict:** Slow velocity abuse (8% detection) and stealth wash trades (29% detection) are critically under-detected by the offline scorer. The scorer lacks DB context for velocity features in unit tests, which partially explains low rates. However, the live system also shows gaps (see Phases 3-4).

---

## Phase 2: Structuring Evasion

**Attack:** 10 transactions of $990-$1010 each from the same sender (`structurer_qa_1`) to different receivers.

**Command:**
```python
for i in range(1, 11):
    amt = 990 + (i * 2)
    POST /transactions {amount: amt, sender_id: "structurer_qa_1", receiver_id: f"receiver_qa_{i}"}
```

**Results:**

| Txn | Amount | Score | Decision |
|---|---|---|---|
| 1 | $992 | 0.9454 | block |
| 2 | $994 | 0.9526 | block |
| 3 | $996 | 0.9526 | block |
| 4 | $998 | 0.9526 | block |
| 5 | $1000 | 0.9368 | block |
| 6 | $1002 | 0.9368 | block |
| 7 | $1004 | 0.9368 | block |
| 8 | $1006 | 0.9368 | block |
| 9 | $1008 | 0.9154 | block |
| 10 | $1010 | 0.7712 | review |

**Detection Rate:** 10/10 (100%)

**Analysis:** Velocity features (sender_txn_count_1h, sender_unique_receivers_24h) accumulate correctly and escalate scores. The $1000 amount range also triggers amount_normalized. Structuring at this amount level is well-detected.

**Severity:** Low (well-defended)

---

## Phase 3: Velocity Evasion

### Part A: Rapid-Fire (20 transactions, no delay)

**Sender:** `velocity_qa_rapid`, amounts $150-$1050

**Results (partial - timeout after txn 17):**
- First 5 txns: 4/5 flagged (scores escalate quickly)
- Txns 6-11: 0/6 flagged (scores DROP after initial spike)
- Txns 12-15: 4/4 flagged (scores spike again)
- Txns 16-17: 0/2 flagged
- **Server timed out on txn 18** (5s timeout)

**Finding:** Scores oscillate unpredictably under rapid load. Some batches of transactions evade despite high velocity. The ML model (v0.9.0) appears to produce inconsistent scores for velocity features.

**Severity:** Medium -- velocity detection is present but inconsistent under rapid submission.

### Part B: Spaced Out (10 transactions, 3s apart)

**Sender:** `velocity_qa_slow2`, amounts $150-$600

| Txn | Amount | Score | Decision |
|---|---|---|---|
| 1 | $150 | 0.0593 | approve |
| 2 | $200 | 0.4982 | approve |
| 3 | $250 | 0.5754 | review |
| 4 | $300 | 0.5307 | review |
| 5 | $350 | 0.7888 | review |
| 6 | $400 | 0.3702 | approve |
| 7 | $450 | 0.3271 | approve |
| 8 | $500 | 0.5605 | review |
| 9 | $550 | 0.7866 | review |
| 10 | $600 | 0.8942 | block |

**Detection Rate:** 6/10 (60%)

**Finding:** Even with 3-second spacing, scores oscillate. Transactions 6-7 dropped to approve despite the sender already having 5 prior transactions in the same session. The ML model does not consistently weight cumulative velocity.

**Severity:** Medium -- spaced-out velocity abuse partially evades detection.

---

## Phase 4: Wash Trading Evasion

### Simple Circular: A -> B -> C -> A

| Flow | Amount | Score | Decision |
|---|---|---|---|
| A -> B | $500 | 0.1952 | approve |
| B -> C | $490 | 0.2345 | approve |
| C -> A | $480 | 0.0270 | approve |

**Detection Rate:** 0/3 (0%)

### With Intermediaries: A -> X -> B -> Y -> C -> A

| Flow | Amount | Score | Decision |
|---|---|---|---|
| A -> X | $1000 | 0.9578 | block |
| X -> B | $980 | 0.9578 | block |
| B -> Y | $960 | 0.1345 | approve |
| Y -> C | $940 | 0.1345 | approve |
| C -> A | $920 | 0.1345 | approve |

**Detection Rate:** 2/5 (40%) -- but only the first two hops detected (likely amount-based, not pattern-based)

### Long Chain (6 nodes): A -> B -> C -> D -> E -> F -> A

| Flow | Amount | Score | Decision |
|---|---|---|---|
| A -> B | $2000 | 0.0887 | approve |
| B -> C | $1980 | 0.0887 | approve |
| C -> D | $1960 | 0.0887 | approve |
| D -> E | $1940 | 0.0887 | approve |
| E -> F | $1920 | 0.0887 | approve |
| F -> A | $1900 | 0.0887 | approve |

**Detection Rate:** 0/6 (0%)

**Critical Finding:** Circular fund flows are COMPLETELY UNDETECTED in real-time scoring. The pattern mining (`/mine-patterns`) can detect rings post-hoc, but real-time transaction scoring has no awareness of circular flow patterns. Each individual hop looks like a normal transaction. Even $2000 amounts in a 6-node ring scored only 0.0887.

**Severity:** CRITICAL -- Wash trading is the primary fraud type for a derivatives platform (Deriv context) and is completely undetected in real-time.

**Recommended Fix:** Implement real-time graph lookback: before scoring, check if the receiver has sent funds to the sender's prior senders within a time window.

---

## Phase 5: Amount Overlap Exploitation

**Attack:** Send transactions with normal amounts ($50-$500) from unique senders.

| Amount | Score | Decision |
|---|---|---|
| $50 | 0.0129 | approve |
| $75 | 0.0129 | approve |
| $100 | 0.0129 | approve |
| $150 | 0.0593 | approve |
| $200 | 0.0593 | approve |
| $250 | 0.0589 | approve |
| $300 | 0.0418 | approve |
| $350 | 0.2323 | approve |
| $400 | 0.0454 | approve |
| $450 | 0.0450 | approve |
| $500 | 0.1952 | approve |

**Detection Rate:** 0/11 (0%)

**Critical Finding:** Any fraudulent transaction with a normal amount ($50-$500) from a new sender with no velocity history is COMPLETELY INVISIBLE to the system. All scores are far below the 0.5 review threshold.

**Severity:** CRITICAL -- first-time fraudsters with normal amounts have 0% detection rate.

**Root Cause:** The scoring heavily depends on amount features and velocity history. A cold-start sender with normal amounts triggers zero high-weight features.

---

## Phase 6: Feature Gaming

**Attack:** Craft transactions that minimize every feature: normal amount, payment type, web channel, unique sender/device.

| Amount | Type | Score | Decision |
|---|---|---|---|
| $200 | payment | 0.0017 | approve |
| $150 | payment | 0.0017 | approve |
| $300 | payment | 0.0012 | approve |
| $85 | payment | 0.0017 | approve |
| $450 | payment | 0.0012 | approve |
| $500 | deposit | 0.0011 | approve |
| $25 | payment | 0.0019 | approve |

**Detection Rate:** 0/7 (0%)

**Critical Finding:** Scores as low as 0.0011. A fraudster who uses: payment type, web channel, normal amount (<$500), unique sender ID, no prior history -- gets a risk score of effectively ZERO. The model has no behavioral signals for first-time actors with benign-looking transactions.

**Severity:** CRITICAL -- complete evasion possible with trivial feature gaming.

**Recommended Fix:**
1. Add external signals (device fingerprinting, behavioral biometrics)
2. Implement "new account" risk premium
3. Consider ensemble with anomaly detection (isolation forest)

---

## Phase 7: Input Validation Attacks

### SQL Injection
**Payload:** `sender_id: "'; DROP TABLE transactions; --"`
**Result:** Status 200, payload stored as string. SQL injection NOT exploitable due to parameterized queries (aiosqlite).
**Severity:** Low (defended by parameterized queries)

### Stored XSS
**Payload:** `metadata.note: "<script>alert(1)</script>"`
**Result:** Status 200. Payload stored in DB and returned UNESCAPED via `GET /transactions/{id}`.
```json
{"metadata": {"note": "<script>alert(1)</script>"}}
```
**Severity:** HIGH -- if the Streamlit UI renders metadata without escaping, XSS is exploitable. Even if Streamlit auto-escapes, the raw API returns unescaped HTML/JS.

### Negative Amount
**Payload:** `amount: -5000.0`
**Result:** **Status 500 (Internal Server Error)** -- `ValueError` crash
**Payload:** `amount: -1.0`
**Result:** **Status 500 (Internal Server Error)** -- `ValueError` crash
**Severity:** HIGH -- negative amounts crash the server. The `math.log(amount + 1)` in `compute_features` fails for amounts < -1 (log of negative number). Even -1 < amount < 0 produces math domain error. No input validation on amount range.

### Zero Amount
**Payload:** `amount: 0.0`
**Result:** Status 200, score=0.0129, decision=approve
**Severity:** Medium -- zero-amount transactions should be rejected. They could be used for account enumeration or padding velocity stats.

### Extremely Long String
**Payload:** `sender_id: "A" * 10000`
**Result:** Status 200, stored successfully.
**Severity:** Medium -- no length validation on string fields. Could cause DB bloat, memory issues, or UI rendering problems.

### Invalid Currency
**Payload:** `currency: "FAKE_MONEY"`
**Result:** Status 200, accepted.
**Severity:** Medium -- no currency enum validation. Could corrupt analytics.

### Missing Required Fields
**Payload:** `{amount: 100}` (missing sender_id, receiver_id)
**Result:** Status 422 with proper Pydantic validation error.
**Severity:** Low (properly handled)

### Self-Transfer
**Payload:** `sender_id == receiver_id`
**Result:** Status 200, score=0.9578, decision=block (high score likely from ML model features)
**Severity:** Low -- the high score is coincidental (from model), not from explicit self-transfer detection. Should have explicit validation.

### CORS Wildcard
**Test:** OPTIONS request with `Origin: http://evil-site.com`
**Result:** `Access-Control-Allow-Origin: http://evil-site.com`
**Severity:** HIGH -- CORS is set to `*` (accept all origins). Any website can make API calls to the backend. In production, this enables cross-site request forgery.

---

## Phase 8: Race Condition Testing

**Attack:** 50 simultaneous transactions from the same sender via 50 threads.

**Results:**
- Successes: 50/50
- Server errors: 0
- Timeouts: 0
- Elapsed: 3.50s
- Score range: 0.0418 - 0.9979
- Decisions: approve=20, review=8, block=22
- No duplicate txn_ids

**Analysis:** The system handles concurrent load well. SQLite WAL mode provides adequate concurrent write support for demo scale. UUID4 generation is safe from collisions. However, velocity features may not be perfectly consistent under concurrent writes (some transactions may not see their concurrent siblings).

**Severity:** Low -- no crashes, but velocity scoring accuracy degrades under concurrency.

---

## Phase 9: Label Poisoning

### Attack Execution
1. Retrieved 20 open cases (all with risk_score > 0.95)
2. Labeled 10 high-confidence fraud cases as `not_fraud` with `confidence: high`
3. Triggered `/retrain` endpoint (no authentication required)

### Pre-Poisoning Metrics
- Precision: 0.75
- Recall: 1.0
- Model: v0.9.0

### Post-Poisoning Retrain Result
- **Precision dropped: 0.75 -> 0.50** (33% degradation)
- **Recall dropped: maintained at 0.33 on test set** (from 1.0)
- **F1 dropped: from ~0.86 -> 0.40** (53% degradation)
- New model: v0.10.0

### Additional Findings
- **No authentication on `/retrain`** -- anyone can trigger model retraining
- **No authentication on `/retrain-from-ground-truth`** -- anyone can retrain from ground truth
- **No authentication on `/mine-patterns`** -- anyone can trigger pattern mining
- **No authentication on `/simulator/start|stop|configure`** -- anyone can control the simulator
- **No enum validation on label decision** -- `"DEFINITELY_FAKE_LABEL"` accepted with status 200
- **No identity verification on `labeled_by`** -- any string accepted

**Severity:** CRITICAL -- An adversary can:
1. Label fraud cases as legitimate (no auth required)
2. Trigger model retraining (no auth required)
3. Degrade model performance by 33-53% in a single attack cycle
4. Repeat indefinitely to continuously degrade the model

---

## Vulnerability Summary

| # | Vulnerability | Severity | Phase | Detection Rate Impact |
|---|---|---|---|---|
| V1 | Wash trading completely undetected (real-time) | CRITICAL | 4 | 0% for simple rings |
| V2 | Feature gaming allows 100% evasion | CRITICAL | 5,6 | 0% for crafted txns |
| V3 | Label poisoning degrades model 33-53% | CRITICAL | 9 | Model-wide degradation |
| V4 | No authentication on admin endpoints | CRITICAL | 9 | Enables V3 |
| V5 | Negative amount causes server crash (500) | HIGH | 7 | Server availability |
| V6 | Stored XSS via metadata field | HIGH | 7 | Security breach vector |
| V7 | CORS wildcard allows any origin | HIGH | 7 | Cross-site attacks |
| V8 | No enum validation on label decisions | HIGH | 9 | Data integrity |
| V9 | Zero amount transactions accepted | MEDIUM | 7 | Account enumeration |
| V10 | No string length validation | MEDIUM | 7 | DB bloat, DoS |
| V11 | No currency code validation | MEDIUM | 7 | Data integrity |
| V12 | Slow velocity abuse evades (8% detection) | MEDIUM | 1,3 | 92% evasion rate |
| V13 | Stealth wash trades evade (25-29% detection) | LOW | 1 | 71-75% evasion rate |
| V14 | Score oscillation under rapid fire | LOW | 3 | Inconsistent scoring |

---

## Recommended Fixes (Priority Order)

### P0 - Must Fix for Demo

1. **Input Validation (V5, V9, V10, V11):** Add Pydantic validators:
   - `amount: float = Field(gt=0, le=1_000_000)`
   - `currency: str = Field(pattern="^[A-Z]{3}$")`
   - `sender_id: str = Field(max_length=256)`
   - `sender_id != receiver_id` cross-field validation

2. **Label Enum Validation (V8):** Restrict `LabelIn.decision` to `Literal["fraud", "not_fraud", "needs_info"]`

3. **Metadata Sanitization (V6):** Strip HTML tags from metadata values before storage, or escape on output.

### P1 - Should Fix for Judges

4. **Authentication on Admin Endpoints (V4):** Add API key or session auth to `/retrain`, `/mine-patterns`, `/simulator/*`. Even a simple header-based key blocks casual attacks.

5. **Real-time Wash Trade Detection (V1):** Before scoring, query the transaction graph for circular flow indicators:
   ```sql
   SELECT 1 FROM transactions
   WHERE sender_id = :receiver_id AND receiver_id IN (
     SELECT sender_id FROM transactions WHERE receiver_id = :sender_id
   ) AND timestamp >= datetime('now', '-24 hours')
   ```

6. **New Account Risk Premium (V2):** Add a `sender_age_hours` feature. First-time senders within 1 hour get a risk boost of 0.1-0.2.

### P2 - Nice to Have

7. **Label Poisoning Mitigation (V3):** Track label disagreement rate per analyst. Flag analysts whose labels consistently disagree with model predictions. Require multiple analyst consensus for high-confidence labels.

8. **CORS Restriction (V7):** Set `CORS_ORIGINS` to specific allowed domains instead of `*`.

9. **Rate Limiting:** Add rate limiting to all endpoints to prevent abuse.

10. **Velocity Score Stabilization (V12, V14):** Review ML model feature importance for velocity features. Consider adding a moving average smoothing to velocity scores.

---

## Test Commands Reference

```bash
# Run existing adversarial tests
python -m pytest tests/test_adversarial.py -v -s

# Structuring evasion
curl -X POST http://localhost:8000/transactions -H "Content-Type: application/json" \
  -d '{"amount":1000,"currency":"USD","sender_id":"structurer","receiver_id":"recv_1","txn_type":"transfer"}'

# Negative amount crash
curl -X POST http://localhost:8000/transactions -H "Content-Type: application/json" \
  -d '{"amount":-5000,"currency":"USD","sender_id":"test","receiver_id":"test2","txn_type":"transfer"}'

# XSS injection
curl -X POST http://localhost:8000/transactions -H "Content-Type: application/json" \
  -d '{"amount":100,"currency":"USD","sender_id":"test","receiver_id":"test2","txn_type":"transfer","metadata":{"note":"<script>alert(1)</script>"}}'

# Label poisoning
curl -X POST http://localhost:8000/cases/{case_id}/label -H "Content-Type: application/json" \
  -d '{"decision":"not_fraud","confidence":"high","labeled_by":"adversary"}'

# Unauthenticated retrain
curl -X POST http://localhost:8000/retrain
```

---

## Overall Risk Assessment

**System Security Posture: WEAK**

The fraud detection system has strong foundations (parameterized queries, proper error handling, concurrent stability) but critical gaps in:
1. **Detection coverage** -- wash trading and feature-gamed transactions evade completely
2. **Input validation** -- negative amounts crash the server; no field-level constraints
3. **Authentication** -- zero authentication on any endpoint including model retraining
4. **Model integrity** -- label poisoning can degrade the model with no guardrails

For a hackathon demo, the most impactful quick wins are P0 fixes (input validation, enum restriction) which can be done in ~30 minutes and eliminate the crash + data integrity issues. The detection gaps (V1, V2) require more substantial feature engineering work.
