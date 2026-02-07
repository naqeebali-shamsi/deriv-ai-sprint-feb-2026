# Documentation Changelog

## 2026-02-07: Documentation Audit and Restructuring

### Overview
A full documentation audit was performed by a 6-agent team: doc-auditor, gap-detector, doc-architect, doc-consolidator, claude-md-updater, and cleanup-verifier. The audit covered all files in `docs/`, `reports/`, `.planning/`, and `CLAUDE.md`.

### Files Created
- `docs/INDEX.md` — Central documentation index with categories, descriptions, and status markers
- `docs/DOCS_CHANGELOG.md` — This file

### Files Renamed (2)
- `docs/text_vs_general_embedding_tricks_analysis.md` -> `docs/EMBEDDING_RESEARCH.md` (naming convention alignment)
- `reports/QA_FINAL_VERDICT.md` -> `reports/qa_final_verdict.md` (naming convention alignment)

### Historical Markers Added (3)
- `docs/FEASIBILITY_REPORT.md` — "HISTORICAL DOCUMENT (Feb 5, 2026)" banner with forward links to current state
- `docs/PRE_DEMO_AUDIT.md` — "HISTORICAL DOCUMENT (Feb 5, 2026)" banner with forward link to QA verdict
- `docs/EMBEDDING_RESEARCH.md` — "RESEARCH NOTE (Not Implemented)" banner noting Phase 7+ scope

### Cross-References Added (9)
"See Also" sections appended to:
- `docs/DESIGN_DECISIONS.md` — Links to ARCHITECTURE.mmd, FEASIBILITY_REPORT.md, ADVERSARIAL_PANEL_REPORT.md
- `docs/FEASIBILITY_REPORT.md` — Link to DESIGN_DECISIONS.md
- `docs/ADVERSARIAL_PANEL_REPORT.md` — Links to FEASIBILITY_REPORT.md, DESIGN_DECISIONS.md
- `docs/DEMO_SCRIPT.md` — Links to PITCH_TRANSCRIPT.md, PRE_DEMO_AUDIT.md, ARCHITECTURE.mmd
- `docs/PITCH_TRANSCRIPT.md` — Link to DEMO_SCRIPT.md
- `docs/BUSINESS_CASE.md` — Links to FINANCIAL_DOMAIN_EVALUATION.md, AML_TM_VALIDATION.md, DESIGN_DECISIONS.md
- `docs/FINANCIAL_DOMAIN_EVALUATION.md` — Links to BUSINESS_CASE.md, AML_TM_VALIDATION.md
- `docs/AML_TM_VALIDATION.md` — Links to BUSINESS_CASE.md, FINANCIAL_DOMAIN_EVALUATION.md
- `reports/qa_final_verdict.md` — Links to all 6 individual QA reports

### Inconsistencies Fixed
- `.planning/PROJECT.md` — Updated ML stack reference from "scikit-learn" to "XGBoost (XGBClassifier)" to match codebase
- `.planning/PROJECT.md` — Updated demo script reference from `scripts/demo.sh` to `scripts/demo.py`
- `docs/PITCH_TRANSCRIPT.md` — Removed incorrect "Louvain" algorithm reference; replaced with actual algorithms used (cycle detection, hub analysis, velocity clustering, connected component analysis)
- `CLAUDE.md` — Updated demo command from `bash scripts/demo.sh` to `python scripts/demo.py` to match actual script
- `CLAUDE.md` — Added cross-references after XGBoost and AgentCore Memory Bank entries pointing to DESIGN_DECISIONS.md
- `docs/INDEX.md` — Added DOCS_CHANGELOG.md entry (was missing from index after creation)

### Content Updates
- `CLAUDE.md` — Added "Documentation Navigation" section linking to `docs/INDEX.md` with category summaries and key document quick links
- `CLAUDE.md` — Added 3 Memory Bank entries: documentation audit lesson, naming conventions lesson, schema divergence finding
- `CLAUDE.md` — Updated "Demo OS" section to reference `scripts/demo.py`

### Audit Findings Summary
Three audit reports were produced during the process:
1. **DOC_OVERLAP_AUDIT.md** — Found overlapping content between DESIGN_DECISIONS.md, FEASIBILITY_REPORT.md, and ADVERSARIAL_PANEL_REPORT.md; resolved via historical markers and cross-references rather than content deletion
2. **UNDOCUMENTED_FEATURES.md** — Identified 14 HIGH-priority undocumented features in the codebase (e.g., 3-tier LLM fallback, golden path demo mode, WAL-mode SQLite, model hot-reload)
3. **STRUCTURE_PLAN.md** — Proposed taxonomy and naming conventions; established per-directory naming rules (UPPER_SNAKE in docs/, lower_snake in reports/)

### Cleanup
- Removed `docs/_audit/` working directory (3 intermediate audit files)
