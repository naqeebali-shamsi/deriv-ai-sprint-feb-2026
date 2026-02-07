# Schema Changes Log

Track all changes to `/schemas` here. Every schema change requires:
1. Update impacted modules
2. Update tests
3. Add entry below

---

## [2026-02-05] Initial Schema Set

**Added:**
- `transaction.schema.json` - Core transaction model
- `risk_result.schema.json` - Risk scoring output
- `case.schema.json` - Investigation case model
- `analyst_label.schema.json` - Human feedback labels
- `pattern_card.schema.json` - Discovered fraud patterns
- `metric_snapshot.schema.json` - System metrics

**Notes:**
- All schemas use JSON Schema Draft-07
- UUID format for all IDs
- ISO 8601 datetime strings

---

## [2026-02-05] Pattern Card Schema Extended

**Modified:** `pattern_card.schema.json`
- Added `pattern_type` enum: `velocity`, `graph`, `behavioral`, `amount`, `custom`
- Added `detection_rule` object (field, operator, threshold)
- Added `stats` object (matches_total, true_positives, false_positives, precision)
- Added `related_txn_ids` array

**Impacted modules:** `patterns/miner.py`, `backend/main.py`

---

## [2026-02-07] Risk Result — Uncertainty Field (Code-Only, Schema Pending)

**Code change:** `risk/scorer.py` now computes `uncertainty = abs(risk_score - 0.5)` for every scored transaction. Stored in `risk_results` table column and returned in API responses.

**Schema status:** `risk_result.schema.json` does NOT yet include `uncertainty` field. This is a known drift.

**Impacted modules:** `risk/scorer.py`, `backend/main.py`

---

## [2026-02-07] ML Migration — sklearn to XGBoost

**No schema change.** The ML model was migrated from `sklearn.GradientBoostingClassifier` to `xgboost.XGBClassifier`. Model artifacts changed format but no schema fields were affected.

**Impacted modules:** `risk/scorer.py`, `risk/trainer.py`, `scripts/bootstrap_model.py`

---

## [2026-02-07] Pattern-Derived Features Added to Scoring

**No schema change.** 7 new features derived from pattern cards are computed at scoring time by `patterns/features.py` and included in the `features` object of `risk_result`. The `features` property uses `additionalProperties: true`, so new feature keys are schema-compliant.

**Impacted modules:** `patterns/features.py`, `risk/scorer.py`, `backend/main.py`

---

## Known Schema Drift (as of 2026-02-07)

| Issue | Severity | Notes |
|-------|----------|-------|
| `risk_result.schema.json` missing `uncertainty` field | Low | Field is optional; `additionalProperties: false` may reject it at validation time |
| `model_state` table in `init_db.py` has no JSON schema | Low | Table is created but never read/written by any code — candidate for removal |
| `init_db.py` vs `backend/db.py` schema divergence | Medium | Two different table definitions exist; `db.py` is the runtime source of truth |
