# QA API Test Report - Autonomous Fraud Agent Backend

**Date:** 2026-02-07
**Tester:** Adversarial QA Agent
**Backend URL:** http://localhost:8000
**Total Endpoints Tested:** 19
**Total Test Cases:** 68

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Total test cases | 68 |
| PASS | 54 |
| FAIL (bugs found) | 8 |
| WARN (acceptable but notable) | 6 |
| Endpoints fully passing | 14/19 |
| Critical bugs | 3 |
| Medium bugs | 3 |
| Low bugs | 2 |

---

## Critical Bugs

### BUG-1: Negative amount causes 500 Internal Server Error (CRITICAL)
- **Endpoint:** `POST /transactions`
- **Input:** `{"amount": -500, ...}`
- **Expected:** 422 Validation Error (reject negative amounts)
- **Actual:** 500 Internal Server Error (`ValueError`)
- **Impact:** Unhandled crash in scoring pipeline. Negative transactions could corrupt data.

### BUG-2: NaN amount causes 500 IntegrityError (CRITICAL)
- **Endpoint:** `POST /transactions`
- **Input:** `{"amount": NaN, ...}`
- **Expected:** 422 Validation Error
- **Actual:** 500 Internal Server Error (`IntegrityError`)
- **Impact:** DB integrity error. JSON `NaN` is non-standard but accepted by some parsers.

### BUG-3: Infinity amount causes 500 ValueError (CRITICAL)
- **Endpoint:** `POST /transactions`
- **Input:** `{"amount": Infinity, ...}`
- **Expected:** 422 Validation Error
- **Actual:** 500 Internal Server Error (`ValueError`)
- **Impact:** Crashes scoring pipeline.

### BUG-4: No validation on label `decision` field (MEDIUM)
- **Endpoint:** `POST /cases/{id}/label`
- **Input:** `{"decision": "INVALID_DECISION", ...}`
- **Expected:** 422 Validation Error (only `fraud`, `not_fraud`, `needs_info` accepted)
- **Actual:** 200 OK, stores arbitrary string, sets status to `in_review`
- **Impact:** Garbage labels pollute training data. SQL injection strings are stored as decisions.

### BUG-5: Negative `limit` returns all records (MEDIUM)
- **Endpoint:** `GET /transactions`, `GET /cases`, `GET /patterns`, `GET /metric-snapshots`
- **Input:** `?limit=-1`
- **Expected:** 422 Validation Error or empty result
- **Actual:** Returns ALL records (SQLite `LIMIT -1` means no limit)
- **Impact:** Potential DoS on large datasets. Information disclosure.

### BUG-6: Boolean coerced to amount (MEDIUM)
- **Endpoint:** `POST /transactions`
- **Input:** `{"amount": true, ...}`
- **Expected:** 422 Validation Error
- **Actual:** 200 OK, amount stored as 1.0
- **Impact:** Pydantic coerces `true` to `1.0`. Could mask data quality issues.

### BUG-7: XSS payloads stored without sanitization (LOW)
- **Endpoint:** `POST /transactions`
- **Input:** `sender_id: "<script>alert(1)</script>"`
- **Expected:** Sanitized or rejected
- **Actual:** 200 OK, stored and returned verbatim
- **Impact:** If rendered in browser without escaping, XSS is possible. Streamlit likely escapes, but raw API consumers may not.

### BUG-8: Null bytes accepted in string fields (LOW)
- **Endpoint:** `POST /transactions`
- **Input:** `sender_id: "\u0000\u0001\u0002NULLBYTES"`
- **Expected:** Rejected or sanitized
- **Actual:** 200 OK, stored with null bytes
- **Impact:** Null bytes can cause issues in downstream systems.

---

## Full Test Results

### 1. GET /health

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 1 | Happy path | `GET /health` | 200 with status:ok | 200 `{"status":"ok","timestamp":"..."}` | PASS |
| 2 | Wrong method | `DELETE /health` | 405 | 405 `{"detail":"Method Not Allowed"}` | PASS |

### 2. GET /ready

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 3 | Happy path | `GET /ready` | 200 with checks | 200 `{"status":"ready","checks":{"db":true,"model":true},"model_version":"v0.6.0"}` | PASS |

### 3. POST /transactions

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 4 | Happy path (basic) | amount=100.50, sender/receiver/type | 200 with txn_id, risk_score | 200, risk_score=0.1264, decision=approve | PASS |
| 5 | Happy path (all fields) | All optional fields + metadata | 200 | 200, risk_score=0.9036, decision=block | PASS |
| 6 | Minimal fields | amount + sender + receiver only | 200 (defaults applied) | 200, currency=USD, txn_type=transfer, channel=web | PASS |
| 7 | Missing amount | No amount field | 422 | 422 `"Field required"` | PASS |
| 8 | Missing sender_id | No sender_id | 422 | 422 `"Field required"` | PASS |
| 9 | Empty body | `{}` | 422 | 422 (3 missing fields) | PASS |
| 10 | Invalid JSON | `"not json"` | 422 | 422 `"JSON decode error"` | PASS |
| 11 | No Content-Type | form data | 422 | 422 | PASS |
| 12 | **Negative amount** | amount=-500 | 422 | **500 ValueError** | **FAIL** |
| 13 | Zero amount | amount=0 | 200 | 200, risk_score=0.0229 | PASS |
| 14 | Huge amount | amount=999999999999999 | 200 | 200, risk_score=0.9989, decision=block | PASS |
| 15 | String amount | amount="not_a_number" | 422 | 422 `"unable to parse string as a number"` | PASS |
| 16 | SQL injection in sender_id | `'; DROP TABLE transactions; --` | No crash / data safe | 200 OK, stored safely (parameterized queries) | PASS |
| 17 | XSS in sender_id | `<script>alert(1)</script>` | Sanitized or rejected | 200 OK, **stored verbatim** | **WARN** |
| 18 | Very long sender_id (10K chars) | 10,000 'A' characters | Should reject or handle | 200 OK, stored | **WARN** |
| 19 | **NaN amount** | `NaN` | 422 | **500 IntegrityError** | **FAIL** |
| 20 | **Infinity amount** | `Infinity` | 422 | **500 ValueError** | **FAIL** |
| 21 | **Boolean amount** | `true` | 422 | **200 OK, amount=1.0** | **WARN** |
| 22 | Null amount | `null` | 422 | 422 `"Input should be a valid number"` | PASS |
| 23 | Array amount | `[1,2,3]` | 422 | 422 | PASS |
| 24 | Unicode/null bytes | sender_id with \u0000 | Reject or sanitize | 200 OK, stored with null bytes | **WARN** |
| 25 | Float overflow (1e308) | amount=1e308 | Handle or reject | 200 OK, risk_score=0.9987 | **WARN** |
| 26 | Extra unknown fields | `UNKNOWN_FIELD`, `admin` | Ignored | 200 OK, extra fields silently ignored | PASS |
| 27 | Wrong method (PUT) | `PUT /transactions` | 405 | 405 | PASS |

### 4. GET /transactions

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 28 | Happy path | `GET /transactions` | 200, list of txns | 200, 50 transactions returned | PASS |
| 29 | limit=0 | `?limit=0` | 200, empty list | 200, `[]` | PASS |
| 30 | **limit=-1** | `?limit=-1` | 422 or empty | **200, returns ALL records** | **FAIL** |
| 31 | limit=abc | `?limit=abc` | 422 | 422 `"unable to parse string as an integer"` | PASS |

### 5. GET /transactions/{id}

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 32 | Happy path | Valid txn_id | 200 with full detail | 200, includes features, risk_score, case info | PASS |
| 33 | Non-existent ID | `00000000-...` | 404 | 404 `"Transaction not found"` | PASS |
| 34 | SQL injection in path | URL-encoded SQL | 404 | 404 `"Transaction not found"` | PASS |

### 6. GET /cases

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 35 | Happy path (no filter) | `GET /cases` | 200 with cases | 200, list of open+closed cases | PASS |
| 36 | status=open | `?status=open` | 200, only open | 200, all open cases | PASS |
| 37 | status=closed | `?status=closed` | 200, only closed | 200, closed cases | PASS |
| 38 | status=nonexistent | `?status=nonexistent` | 200, empty | 200, `[]` | PASS |
| 39 | SQL injection in status | `?status=%27%3B+DROP+TABLE+cases%3B--` | Safe | 200, `[]` (parameterized query) | PASS |
| 40 | limit=abc | `?limit=abc` | 422 | 422 | PASS |
| 41 | **limit=-1** | `?limit=-1` | 422 or empty | **200, returns ALL records** | **FAIL** |

### 7. POST /cases/{id}/label

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 42 | Happy path (fraud) | `decision: "fraud"` | 200, case closed | 200, `new_status: "closed"` | PASS |
| 43 | Re-label closed case | Same case again | 400 | 400 `"Case already closed"` | PASS |
| 44 | Non-existent case | `00000000-...` | 404 | 404 `"Case not found"` | PASS |
| 45 | **Invalid decision** | `decision: "INVALID_DECISION"` | 422 | **200 OK, stored, status=in_review** | **FAIL** |
| 46 | Missing decision | No decision field | 422 | 422 `"Field required"` | PASS |
| 47 | Empty body | `{}` | 422 | 422 `"Field required"` | PASS |
| 48 | SQL injection in decision | `fraud'; DROP TABLE cases;--` | Safe | 200 OK, stored as string (safe but bad data) | **WARN** |
| 49 | needs_info | `decision: "needs_info"` | 200, status=in_review | 200, `new_status: "in_review"` | PASS |

### 8. GET /cases/suggested

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 50 | Happy path | `GET /cases/suggested` | 200 with uncertainty | 200, sorted by uncertainty ASC | PASS |
| 51 | limit=0 | `?limit=0` | 200, empty | 200, `[]` | PASS |

### 9. GET /cases/{id}/explain

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 52 | Happy path | Valid case_id | 200 with explanation | 200, full LLM explanation with timeline | PASS |
| 53 | Non-existent case | `00000000-...` | 404 | 404 `"Case not found"` | PASS |

### 10. GET /cases/{id}/explain-stream

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 54 | Happy path | Valid case_id | SSE stream with tokens | SSE stream: `data: {"text": "...", "done": false}` | PASS |
| 55 | Non-existent case | `00000000-...` | 404 | 404 `"Case not found"` | PASS |

### 11. GET /metrics

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 56 | Happy path | `GET /metrics` | 200 with counts | 200, total_txns, flagged, precision, recall, f1 | PASS |

### 12. POST /retrain

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 57 | Insufficient data | Not enough labels | 200 with error msg | 200, `trained: false, "Need at least 20"` | PASS |

### 13. POST /retrain-from-ground-truth

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 58 | Happy path | Enough ground truth data | 200 with model metrics | 200, `trained: true, version: "v0.8.0"` | PASS |

### 14. POST /mine-patterns

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 59 | Happy path | `POST /mine-patterns` | 200 with patterns | 200, 8 patterns found | PASS |

### 15. GET /patterns

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 60 | Happy path | `GET /patterns` | 200 with pattern cards | 200, list of pattern cards | PASS |
| 61 | **limit=-5** | `?limit=-5` | 422 or empty | **200, returns ALL records** | **FAIL** |

### 16. GET /metric-snapshots

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 62 | Happy path | `GET /metric-snapshots` | 200 with history | 200, 4 snapshots with metrics | PASS |
| 63 | **limit=-1** | `?limit=-1` | 422 or empty | **200, returns ALL records** | **FAIL** |

### 17. GET /stream/events

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 64 | Happy path | SSE connection | Connected event + heartbeats | `data: {"type": "connected", ...}` | PASS |

### 18. GET /simulator/status & POST start/stop

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 65 | Status (stopped) | `GET /simulator/status` | 200 | 200, `running: false` | PASS |
| 66 | Start | `POST /simulator/start` | 200, started | 200, `status: "started"` | PASS |
| 67 | Start (already running) | `POST /simulator/start` | 200, already_running | 200, `status: "already_running"` | PASS |
| 68 | Stop | `POST /simulator/stop` | 200, stopped | 200, `status: "stopped"` | PASS |
| 69 | Stop (already stopped) | `POST /simulator/stop` | 200, not_running | 200, `status: "not_running"` | PASS |

### 19. POST /simulator/configure

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 70 | Happy path | `tps:2, fraud_rate:0.1` | 200 | 200, configured | PASS |
| 71 | Extreme TPS (99999) | `tps: 99999` | Clamped | 200, tps clamped to 10.0 | PASS |
| 72 | Negative TPS | `tps: -5` | Clamped | 200, tps clamped to 0.1 | PASS |
| 73 | fraud_rate > 1 | `fraud_rate: 99.9` | Clamped | 200, clamped to 1.0 | PASS |
| 74 | fraud_rate negative | `fraud_rate: -0.5` | Clamped | 200, clamped to 0.0 | PASS |
| 75 | Empty body | `{}` | 200 (defaults) | 200, uses defaults | PASS |
| 76 | With fraud_types | Partial fraud_types | 200, merged | 200, only specified types updated | PASS |
| 77 | Start with config | `POST /start` with body | 200 | 200, config applied | PASS |

### Miscellaneous

| # | Test Type | Input | Expected | Actual | Status |
|---|-----------|-------|----------|--------|--------|
| 78 | Unknown path | `GET /nonexistent` | 404 | 404 `"Not Found"` | PASS |

---

## Positive Findings

1. **SQL Injection: SAFE** -- All queries use parameterized statements. SQL injection payloads in sender_id, status filters, and path params are handled safely.
2. **CORS configured** -- Middleware present with configurable origins.
3. **Request logging** -- All requests logged with method, path, status, and latency.
4. **Global exception handler** -- Unhandled errors return 500 with type info (no stack traces leaked to client).
5. **Simulator clamping** -- TPS and fraud_rate are properly clamped to safe ranges (0.1-10 TPS, 0.0-1.0 fraud_rate).
6. **Idempotent start/stop** -- Simulator handles double-start and double-stop gracefully.
7. **Case lifecycle** -- Proper state machine: open -> in_review/closed. Closed cases reject re-labeling.
8. **Active learning** -- Suggested cases sorted by model uncertainty (distance from 0.5).
9. **SSE streaming** -- Both event stream and explain-stream work correctly with proper SSE format.
10. **Pydantic validation** -- Missing fields, wrong types, invalid JSON all return proper 422 errors.

---

## Recommendations (Priority Order)

### P0 - Fix Before Demo
1. **Add amount validation**: Reject negative, NaN, Infinity, and extremely large values. Add `ge=0` and `le=1e12` to Pydantic model.
2. **Validate label decisions**: Add enum validation to `LabelIn.decision` field (`Literal["fraud", "not_fraud", "needs_info"]`).

### P1 - Fix Soon
3. **Validate limit params**: Add `ge=0, le=1000` to all `limit` query parameters across all list endpoints.
4. **Reject boolean coercion**: Use `strict=True` on the Pydantic `amount` field to prevent `true` -> `1.0`.

### P2 - Nice to Have
5. **Sanitize string inputs**: Strip null bytes, control characters. Consider length limits on sender_id/receiver_id.
6. **Add rate limiting**: No rate limiting exists on any endpoint.
7. **XSS output encoding**: While Streamlit likely escapes, API responses should note that string fields are unsanitized.

---

## Reproducible Curl Commands

```bash
# BUG-1: Negative amount -> 500
curl -s -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"amount": -500, "currency": "USD", "sender_id": "neg_test", "receiver_id": "neg_recv", "txn_type": "transfer"}'

# BUG-2: NaN amount -> 500
curl -s -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"amount": NaN, "currency": "USD", "sender_id": "nan_test", "receiver_id": "nan_recv", "txn_type": "transfer"}'

# BUG-3: Infinity amount -> 500
curl -s -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"amount": Infinity, "currency": "USD", "sender_id": "inf_test", "receiver_id": "inf_recv", "txn_type": "transfer"}'

# BUG-4: Invalid decision accepted
curl -s -X POST http://localhost:8000/cases/{CASE_ID}/label \
  -H "Content-Type: application/json" \
  -d '{"decision": "INVALID_GARBAGE", "labeled_by": "attacker"}'

# BUG-5: Negative limit returns all records
curl -s "http://localhost:8000/transactions?limit=-1"
curl -s "http://localhost:8000/cases?limit=-1"
curl -s "http://localhost:8000/patterns?limit=-5"
curl -s "http://localhost:8000/metric-snapshots?limit=-1"

# BUG-6: Boolean coerced to amount
curl -s -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"amount": true, "currency": "USD", "sender_id": "bool_test", "receiver_id": "bool_recv", "txn_type": "transfer"}'

# BUG-7: XSS stored
curl -s -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "currency": "USD", "sender_id": "<script>alert(1)</script>", "receiver_id": "test", "txn_type": "transfer"}'

# BUG-8: Null bytes in strings
curl -s -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "currency": "USD", "sender_id": "\u0000NULLBYTES", "receiver_id": "test", "txn_type": "transfer"}'

# Happy path reference (all endpoints)
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready
curl -s http://localhost:8000/metrics
curl -s http://localhost:8000/transactions
curl -s http://localhost:8000/transactions/{TXN_ID}
curl -s http://localhost:8000/cases
curl -s "http://localhost:8000/cases?status=open"
curl -s http://localhost:8000/cases/suggested
curl -s http://localhost:8000/cases/{CASE_ID}/explain
curl -s http://localhost:8000/cases/{CASE_ID}/explain-stream
curl -s http://localhost:8000/patterns
curl -s http://localhost:8000/metric-snapshots
curl -s http://localhost:8000/stream/events
curl -s http://localhost:8000/simulator/status
curl -s -X POST http://localhost:8000/simulator/start
curl -s -X POST http://localhost:8000/simulator/stop
curl -s -X POST http://localhost:8000/simulator/configure \
  -H "Content-Type: application/json" -d '{"tps": 2, "fraud_rate": 0.1}'
curl -s -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "currency": "USD", "sender_id": "s1", "receiver_id": "r1", "txn_type": "transfer"}'
curl -s -X POST http://localhost:8000/retrain
curl -s -X POST http://localhost:8000/retrain-from-ground-truth
curl -s -X POST http://localhost:8000/mine-patterns
```

---

## Verdict

**Backend is DEMO-READY with caveats.** The core pipeline works correctly. SQL injection is handled. The 3 critical bugs (negative/NaN/Infinity amounts) are unlikely during a controlled demo but should be fixed to avoid embarrassment if a judge tests edge cases. The label validation bug (BUG-4) could cause training data corruption if arbitrary labels are submitted.

**Risk for demo:** LOW (if only using the UI, which constrains inputs)
**Risk for production:** HIGH (multiple input validation gaps)
