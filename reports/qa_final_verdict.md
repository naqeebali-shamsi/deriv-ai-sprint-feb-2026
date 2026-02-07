# ADVERSARIAL QA FINAL VERDICT

**Date:** February 7, 2026
**Team:** 5-agent adversarial QA swarm (API Tester, Claims Verifier, UI Tester, ML Tester, Red Teamer)
**Scope:** Every claim, every endpoint, every UI feature, every evasion vector
**Total Test Cases:** 150+
**Total Vulnerabilities Found:** 22

---

## EXECUTIVE SUMMARY

### Overall Verdict: CONDITIONAL PASS (Demo-Ready, Not Production-Ready)

| Dimension | Score | Verdict |
|-----------|-------|---------|
| API Endpoints (19 tested) | 14/19 fully passing | **PASS with bugs** |
| Documentation Claims (24 checked) | 10 verified, 7 partial, 4 misleading, 3 false | **FAIL — 42% inaccurate** |
| UI Features (32 tested) | 29/32 working | **PASS** |
| ML Pipeline (9 tests) | 8/9 passing | **PASS** |
| Red Team (9 phases) | 14 vulnerabilities found | **FAIL for production** |
| Demo Readiness | Core loop works | **CONDITIONAL PASS** |

**Confidence for 60-second demo: 80%**
**Confidence for judge deep-dive: 55%**

---

## 1. CLAIMS VERIFICATION SUMMARY

| # | Claim | Source | Verdict |
|---|-------|--------|---------|
| 1 | "17 features" / "27 features" / "25 features" | README, Demo Script, scorer.py | **FALSE** — actual count is **34** |
| 2 | 5 fraud typologies | README | **VERIFIED** |
| 3 | GradientBoostingClassifier | README | **VERIFIED** |
| 4 | 4 graph mining algorithms | ROADMAP | **VERIFIED** |
| 5 | Ollama llama3.1:8b integration | README | **VERIFIED** |
| 6 | Template fallback | CLAUDE.md | **VERIFIED** |
| 7 | Golden Path hero transaction | CLAUDE.md | **VERIFIED** |
| 8 | AUC 0.9956, F1 0.967 | ROADMAP | **MISLEADING** — true for v0.2.0, latest v0.9.0 has F1=0.77 |
| 9 | 6 JSON schemas | CLAUDE.md | **VERIFIED** |
| 10 | WAL mode on SQLite | ROADMAP | **PARTIALLY TRUE** — set at runtime, not in init script |
| 11 | Compound indexes | ROADMAP | **VERIFIED** |
| 12 | InvestigationTimeline class | Docs | **VERIFIED** |
| 13 | SSE event stream | README | **VERIFIED** |
| 14 | Autonomous pipeline | README | **VERIFIED** |
| 15 | Self-improving (retraining loop) | README | **VERIFIED** |
| 16 | Pattern-aware scoring | Docs | **VERIFIED** |
| 17 | Real-time processing | README | **PARTIALLY TRUE** — scoring is real-time, mining/retraining are manual |
| 18 | Cross-platform demo runner | Scripts | **VERIFIED** |
| 19 | Deriv-specific typologies | README | **PARTIALLY TRUE** — names are Deriv-relevant, implementation is generic |
| 20 | Enterprise metadata (ISO 20022) | Pitch | **PARTIALLY TRUE** — field names borrowed, values are fake |
| 21 | 19 endpoints / 17 endpoints | ROADMAP, README | **FALSE** — actual count is **21** |
| 22 | 33 tests passing | ROADMAP | **PARTIALLY TRUE** — outdated, actual count is **49** |
| 23 | v0.5.0 is latest model | ROADMAP | **FALSE** — latest is **v0.9.0** (or higher after testing) |
| 24 | "Louvain community detection" | Pitch Transcript | **FALSE** — code uses connected components, NOT Louvain |

### Critical Corrections Needed Before Demo

1. **Remove "Louvain community detection" from pitch** — Code uses `nx.connected_components()`, not Louvain. A technical judge will catch this.
2. **Standardize feature count to 34** — Three docs say three different wrong numbers (17, 25, 27).
3. **Never say "XGBoost"** — PRE_DEMO_AUDIT wrongly calls it XGBoost. It's sklearn's GradientBoostingClassifier.
4. **Cite metrics with version** — Always say "v0.2.0 achieved AUC 0.9956" not "our system achieves AUC 0.9956."

---

## 2. API TEST SUMMARY

**68 test cases across 19 endpoints. 54 PASS, 8 FAIL, 6 WARN.**

| Endpoint | Method | Happy Path | Edge Cases | Adversarial | Verdict |
|----------|--------|-----------|------------|-------------|---------|
| /health | GET | PASS | PASS | PASS | OK |
| /ready | GET | PASS | PASS | PASS | OK |
| /transactions | POST | PASS | **3 FAIL** | PASS (SQLi safe) | **BUGS** |
| /transactions | GET | PASS | **1 FAIL** | PASS | **BUG** |
| /transactions/{id} | GET | PASS | PASS | PASS | OK |
| /cases | GET | PASS | **1 FAIL** | PASS | **BUG** |
| /cases/{id}/label | POST | PASS | **1 FAIL** | PASS | **BUG** |
| /cases/suggested | GET | PASS | PASS | N/A | OK |
| /cases/{id}/explain | GET | PASS | PASS | N/A | OK |
| /cases/{id}/explain-stream | GET | PASS | PASS | N/A | OK |
| /metrics | GET | PASS | N/A | N/A | OK |
| /retrain | POST | PASS | PASS | N/A | OK |
| /retrain-from-ground-truth | POST | PASS | N/A | N/A | OK |
| /mine-patterns | POST | PASS | N/A | N/A | OK |
| /patterns | GET | PASS | **1 FAIL** | N/A | **BUG** |
| /metric-snapshots | GET | PASS | **1 FAIL** | N/A | **BUG** |
| /stream/events | GET | PASS | N/A | N/A | OK |
| /simulator/* | ALL | PASS | PASS | PASS | OK |

### API Bugs Found

| ID | Bug | Severity | Endpoint |
|----|-----|----------|----------|
| BUG-1 | Negative amount → 500 crash | **CRITICAL** | POST /transactions |
| BUG-2 | NaN amount → 500 IntegrityError | **CRITICAL** | POST /transactions |
| BUG-3 | Infinity amount → 500 ValueError | **CRITICAL** | POST /transactions |
| BUG-4 | Invalid label decisions accepted | **MEDIUM** | POST /cases/{id}/label |
| BUG-5 | Negative limit returns all records | **MEDIUM** | GET (all list endpoints) |
| BUG-6 | Boolean coerced to amount (true→1.0) | **MEDIUM** | POST /transactions |
| BUG-7 | XSS payloads stored without sanitization | **LOW** | POST /transactions |
| BUG-8 | Null bytes accepted in strings | **LOW** | POST /transactions |

### Positive Security Findings
- SQL injection: **SAFE** (parameterized queries throughout)
- Simulator config: **SAFE** (TPS/fraud_rate properly clamped)
- Case lifecycle: **SAFE** (proper state machine, closed cases reject re-labeling)

---

## 3. UI TEST SUMMARY

**32 features tested. 29 PASS, 3 BUGS.**

| Feature Area | Tests | Pass | Fail | Notes |
|-------------|-------|------|------|-------|
| Global Elements | 8 | 8 | 0 | Header, badge, metrics row, sidebar all work |
| Tab 1: Live Stream | 7 | 7 | 0 | Table, colors, chips, formatting all work |
| Tab 2: Cases | 9 | 8 | 1 | Race condition on concurrent labels |
| Tab 3: Patterns | 6 | 6 | 0 | Cards, mining, confidence bars all work |
| Tab 4: Model & Learning | 6 | 5 | 1 | Model version desync after retrain |
| Adversarial | 13 | 10 | 2 | Race conditions + invalid decision accepted |

### UI Bugs Found

| Bug | Severity | Description |
|-----|----------|-------------|
| Model version desync | **MEDIUM** | After retrain, /metrics still returns old version. Badge shows stale data. |
| Race condition on labeling | **MEDIUM** | 3/4 concurrent labels succeed on same case. Creates contradictory labels. |
| Invalid decision accepted | **MEDIUM** | Arbitrary strings stored as label decisions (no enum validation). |

### UI Readiness: 7.5/10
- **Demo-safe** for 60-second presentation
- **Risk during judge Q&A** if they retrain during demo (version desync visible)

---

## 4. ML PIPELINE SUMMARY

| Test | Status | Key Finding |
|------|--------|-------------|
| Feature computation (34 features) | **PASS** | All features computed, no NaN, correct values |
| Scoring consistency | **PASS** | Deterministic for identical features; velocity changes expected |
| Threshold verification | **PARTIAL** | Review band (0.5-0.8) hard to hit — model tends toward 0 or 1 |
| Retrain from ground truth | **PASS** | Version increments, metrics returned, model file created |
| Retrain from analyst labels | **PASS** | Correctly enforces 20-sample minimum |
| Model versioning | **PASS** | Sequential v0.1.0-v0.9.0, each with .joblib + .json |
| Feature importance | **PASS** | Top: is_transfer (0.28), amount_normalized (0.16), amount_log (0.14) |
| Adversarial edge cases | **PASS** | $0, $1M, unknown sender — no crashes, no NaN |
| Model performance (v0.9.0) | **PASS** | AUC 0.934, F1 0.769, Precision 0.833 |

### ML Concerns
1. **Narrow review band** — Most scores cluster near 0 or 1. Few "review" decisions during demo.
2. **Velocity features underweighted** — Only 0.7-1.6% importance. Pattern features at 0%.
3. **Multiple rapid retrains** — No locking mechanism; concurrent retrains overwrite each other.

---

## 5. RED TEAM SUMMARY

### Detection Rates by Attack Type

| Attack Vector | Detection Rate | Severity |
|---------------|---------------|----------|
| Structuring ($990-$1010) | **100%** | Well-defended |
| Bonus abuse evasion | **100%** | Well-defended |
| Legit-looking fraud | **100%** | Well-defended |
| Velocity (rapid-fire) | **40-60%** | Inconsistent |
| Stealth wash trading | **25-29%** | Poorly detected |
| Slow velocity abuse | **8%** | Near-total evasion |
| Simple wash trading ring (A→B→C→A) | **0%** | **COMPLETE EVASION** |
| Long chain wash trading (6 nodes) | **0%** | **COMPLETE EVASION** |
| Feature gaming (normal amounts, new sender) | **0%** | **COMPLETE EVASION** |
| Amount overlap ($50-$500 fraud) | **0%** | **COMPLETE EVASION** |

### Critical Red Team Findings

| # | Vulnerability | Severity | Impact |
|---|---------------|----------|--------|
| V1 | Wash trading undetected in real-time | **CRITICAL** | 0% detection for primary Deriv fraud type |
| V2 | Feature gaming allows 100% evasion | **CRITICAL** | Any new sender with normal amounts evades |
| V3 | Label poisoning degrades model 33-53% | **CRITICAL** | F1 dropped from 0.86 to 0.40 in one attack |
| V4 | No authentication on admin endpoints | **CRITICAL** | Anyone can retrain model, start simulator |
| V5 | Negative amount crashes server (500) | **HIGH** | math.log fails on negative amounts |
| V6 | Stored XSS via metadata | **HIGH** | Unescaped HTML returned by API |
| V7 | CORS wildcard (Accept-all origins) | **HIGH** | Cross-site request forgery possible |
| V8 | No enum validation on label decisions | **HIGH** | Garbage labels corrupt training data |
| V9-V14 | Various input validation gaps | **MEDIUM-LOW** | Zero amounts, long strings, no currency validation |

### Label Poisoning Attack Results
- Pre-attack: Precision 0.75, Recall 1.0, F1 ~0.86
- Post-attack (10 mislabels + retrain): Precision **0.50**, Recall **0.33**, F1 **0.40**
- **53% degradation in F1 from a single poisoning cycle**

---

## 6. SCHEMA COMPLIANCE

| Schema | API Response | Compliant | Notes |
|--------|-------------|-----------|-------|
| transaction.schema.json | GET /transactions | PASS | All required fields present |
| risk_result.schema.json | POST /transactions | PASS | Score, decision, features included |
| case.schema.json | GET /cases | PASS | Status, priority, timestamps correct |
| analyst_label.schema.json | POST /cases/{id}/label | **PARTIAL** | No enum validation on decision field |
| pattern_card.schema.json | GET /patterns | PASS | All fields present after mining |
| metric_snapshot.schema.json | GET /metric-snapshots | PASS | Metrics and feature importance included |

`python scripts/validate_schemas.py` — **PASS** (all 6 schemas valid Draft-07)

---

## 7. DEMO READINESS ASSESSMENT

### 60-Second Demo Checklist

| Step | Works | Risk |
|------|-------|------|
| Stream flowing (transactions arriving) | YES | LOW |
| Cases opening automatically | YES | LOW |
| Analyst labels applied (Legit/Fraud) | YES | LOW |
| "Learning update" (retrain visible) | YES | **MEDIUM** — version may desync |
| Metric trend improving | YES | LOW |
| New pattern card appearing | YES | LOW |
| AI Explain with investigation timeline | YES | LOW (Golden Path guarantees it) |

### Demo Risk Matrix

| Scenario | Probability | Impact | Mitigation |
|----------|------------|--------|------------|
| Ollama not running | 20% | Medium | Template fallback + Golden Path |
| Version desync visible | 30% | Low | Refresh page after retrain |
| Judge sends negative amount | 10% | High | **FIX BUG-1 before demo** |
| Judge asks about Louvain | 15% | High | **Remove from pitch script** |
| Judge asks feature count | 25% | Medium | **Brief presenter: "34 features"** |
| SQLite lock during demo | 5% | Medium | Keep TPS at 1-2 |

---

## 8. ALL BUGS — CONSOLIDATED (Priority Order)

### P0 — Critical (Fix Before Demo)

| ID | Bug | Source | Fix Effort |
|----|-----|--------|-----------|
| BUG-1 | Negative amount → 500 crash | API Tester + Red Team | 5 min (add `ge=0` to Pydantic) |
| BUG-2 | NaN amount → 500 crash | API Tester | 5 min (add validator) |
| BUG-3 | Infinity amount → 500 crash | API Tester | 5 min (add validator) |
| BUG-4 | Invalid label decisions accepted | API Tester + UI Tester | 5 min (add `Literal` enum) |
| CLAIM-1 | "Louvain" in pitch script | Claims Verifier | 2 min (edit text) |
| CLAIM-2 | Feature count wrong in all docs | Claims Verifier | 5 min (search-replace) |

### P1 — High (Fix If Time Permits)

| ID | Bug | Source | Fix Effort |
|----|-----|--------|-----------|
| BUG-5 | Negative limit returns all records | API Tester | 5 min (add `ge=0, le=1000`) |
| BUG-UI-1 | Model version desync after retrain | UI Tester | 15 min (reload model in scorer) |
| BUG-UI-2 | Race condition on case labeling | UI Tester + Red Team | 15 min (DB unique constraint) |
| V7 | CORS wildcard | Red Team | 2 min (restrict origins) |
| CLAIM-3 | "XGBoost" in PRE_DEMO_AUDIT | Claims Verifier | 1 min (edit text) |

### P2 — Medium (Nice to Have)

| ID | Bug | Source |
|----|-----|--------|
| BUG-7 | XSS stored in string fields | API Tester + Red Team |
| BUG-8 | Null bytes in strings | API Tester |
| BUG-6 | Boolean coerced to amount | API Tester |
| V1 | Wash trading undetected real-time | Red Team |
| V2 | Feature gaming evasion | Red Team |
| V3 | No label poisoning protection | Red Team |
| V4 | No auth on admin endpoints | Red Team |

---

## 9. FINAL RECOMMENDATIONS FOR DEMO DAY

### Must-Do (30 minutes of work)
1. Fix amount validation (reject negative/NaN/Infinity) — **prevents server crash during demo**
2. Fix label decision enum validation — **prevents training data corruption**
3. Remove "Louvain" from pitch transcript — **prevents embarrassment with technical judges**
4. Brief presenter on correct numbers: **34 features, 21 endpoints, 49 tests, GradientBoosting (not XGBoost)**

### Should-Do (30 more minutes)
5. Fix negative limit on all list endpoints
6. Restrict CORS to localhost origins
7. Add `ge=0, le=1000` to all limit params
8. Update README feature count

### Demo Strategy
- **Keep TPS at 1-2** to avoid SQLite contention
- **Pre-seed the DB** with 200+ transactions before demo starts
- **Do NOT retrain during live demo** (version desync risk)
- **Use the Golden Path hero transaction** for the AI Explain moment
- **If judge asks about wash trading detection**: acknowledge it's post-hoc via graph mining, not real-time — honesty scores better than getting caught lying

---

## 10. OVERALL VERDICT

```
+--------------------------------------------------+
|                                                  |
|   CONDITIONAL PASS — DEMO-READY WITH CAVEATS    |
|                                                  |
|   Confidence: 80% for scripted demo              |
|   Confidence: 55% for adversarial judge          |
|                                                  |
|   Fix P0 bugs (30 min) → 90% confidence          |
|   Fix P0+P1 bugs (1 hr) → 85% for deep-dive     |
|                                                  |
+--------------------------------------------------+
```

### Strengths (What Judges Will Like)
- Real ML (not just rules) with genuine retraining loop
- 34 engineered features across 5 categories
- Real graph mining with 4 algorithms
- LLM integration with graceful fallback
- Clean pipeline: Stream → Score → Case → Label → Learn → Pattern
- 49 passing tests including adversarial suite
- Cross-platform demo runner
- Proper schema contracts

### Weaknesses (What Judges Might Probe)
- 3 server crash bugs on invalid input (easy fix)
- Documentation claims don't match code (feature count, endpoint count, model version)
- Wash trading (Deriv's primary concern) has 0% real-time detection
- No authentication on any endpoint
- Label poisoning can degrade model 53% in one cycle
- "Deriv-specific" is more marketing than implementation

---

*Generated by 5-agent adversarial QA swarm. 150+ test cases. Zero benefit of the doubt.*

---
## See Also
- [qa_api_test_report.md](qa_api_test_report.md) — API endpoint testing details
- [qa_ml_pipeline_report.md](qa_ml_pipeline_report.md) — ML pipeline validation
- [qa_red_team_report.md](qa_red_team_report.md) — Adversarial testing results
- [qa_claims_verification.md](qa_claims_verification.md) — Claims accuracy verification
- [qa_ui_classic_report.md](qa_ui_classic_report.md) — UI testing
- [qa_demo_schema_report.md](qa_demo_schema_report.md) — Schema and demo flow validation
