# Documentation Index

> **Quick links:** [README](../README.md) | [CLAUDE.md](../CLAUDE.md) | [Schemas](../schemas/) | [QA Reports](../reports/)

---

## Architecture & Technical

| Document | Description | Status |
|----------|-------------|--------|
| [ARCHITECTURE.mmd](ARCHITECTURE.mmd) | Mermaid diagram: 5-layer pipeline (ingest, score, case, learn, patterns) | Current |
| [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) | 7-specialist panel: ML model, LLM integration, graph mining, self-learning, systems architecture tradeoffs | Current |
| [SCHEMA_CHANGES.md](SCHEMA_CHANGES.md) | Changelog for JSON Schema contracts in `/schemas` | Active log |
| [DOCS_CHANGELOG.md](DOCS_CHANGELOG.md) | Documentation audit and restructuring changelog | Active log |

## Business & Domain

| Document | Description | Status |
|----------|-------------|--------|
| [BUSINESS_CASE.md](BUSINESS_CASE.md) | ROI quantification ($2M-$30M fraud prevented), competitive analysis, market sizing | Current |
| [AML_TM_VALIDATION.md](AML_TM_VALIDATION.md) | Maps system to real AML Level 1 analyst workflows; validates as L1 automation layer | Current |
| [FINANCIAL_DOMAIN_EVALUATION.md](FINANCIAL_DOMAIN_EVALUATION.md) | Fraud typology accuracy, Deriv regulatory mapping (MFSA/MiFID II), domain gaps | Current |

## Demo & Presentation

| Document | Description | Status |
|----------|-------------|--------|
| [DEMO_SCRIPT.md](DEMO_SCRIPT.md) | Full 5-7 minute live demo walkthrough with judge Q&A prepared answers | Current |
| [PITCH_TRANSCRIPT.md](PITCH_TRANSCRIPT.md) | 2-minute pitch script with Q&A crib sheet | Current |
| [INFOGRAPHIC_PROMPT.md](INFOGRAPHIC_PROMPT.md) | Nanobanaa Pro prompt for generating ByteByteGo-style architecture diagram | Asset |
| [PRE_DEMO_AUDIT.md](PRE_DEMO_AUDIT.md) | Pre-demo adversarial readiness check | Historical (Feb 5) |

## Assessments & Analysis

| Document | Description | Status |
|----------|-------------|--------|
| [FEASIBILITY_REPORT.md](FEASIBILITY_REPORT.md) | Original 7-specialist panel assessment: "CONDITIONAL NO, credible path to YES" | Historical (Feb 5 baseline) |
| [ADVERSARIAL_PANEL_REPORT.md](ADVERSARIAL_PANEL_REPORT.md) | 5-agent innovation assessment: not novel individually, combination is uncommon | Current |

## Research

| Document | Description | Status |
|----------|-------------|--------|
| [EMBEDDING_RESEARCH.md](EMBEDDING_RESEARCH.md) | LLM embedding feature engineering analysis (semantic anchors, cross-modal fusion) | Not implemented |

---

## QA Reports (in [`/reports`](../reports/))

| Report | Description |
|--------|-------------|
| [qa_final_verdict.md](../reports/qa_final_verdict.md) | Consolidated verdict: CONDITIONAL PASS (150+ tests, 22 vulnerabilities) |
| [qa_api_test_report.md](../reports/qa_api_test_report.md) | 19 endpoints, 68 test cases, 3 critical bugs |
| [qa_claims_verification.md](../reports/qa_claims_verification.md) | 24 claims checked: 58% fully accurate, 42% inaccurate |
| [qa_ml_pipeline_report.md](../reports/qa_ml_pipeline_report.md) | Feature computation, retraining, model versioning tests |
| [qa_red_team_report.md](../reports/qa_red_team_report.md) | 9 adversarial phases, 14 vulnerabilities, 4 critical |
| [qa_ui_classic_report.md](../reports/qa_ui_classic_report.md) | 32 UI features tested, 29/32 passing |
| [qa_demo_schema_report.md](../reports/qa_demo_schema_report.md) | Schema compliance + demo flow validation |

---

## Planning (in [`.planning/`](../.planning/))

| Document | Description |
|----------|-------------|
| [PROJECT.md](../.planning/PROJECT.md) | Project identity, current status, success criteria |
| [ROADMAP.md](../.planning/ROADMAP.md) | Sprint execution plan with 7 phases |

---

## Status Legend

| Marker | Meaning |
|--------|---------|
| **Current** | Reflects latest codebase state; actively maintained |
| **Historical** | Point-in-time snapshot; valuable for context but may not reflect current state |
| **Active log** | Append-only document; updated whenever relevant events occur |
| **Asset** | Supporting material (prompts, templates, diagrams) |
| **Not implemented** | Research or proposals not yet reflected in code |
