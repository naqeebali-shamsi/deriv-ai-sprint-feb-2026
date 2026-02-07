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
