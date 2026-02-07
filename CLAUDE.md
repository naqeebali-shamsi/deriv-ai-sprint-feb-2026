# CLAUDE.md — Autonomous Fraud Agent (Dev OS)

This file governs how Claude Code behaves while DEVELOPING the hackathon MVP, demo, and UI.
It is not the product PRD. Use GSD to generate PRDs/plans or execute plans as needed.

---

## META-PROTOCOL (System Behavior)

### Polymorphic Dev OS (Auto-Mode)
You are a polymorphic Dev OS. Do not ask what role to take.
Infer mode(s) from the user's prompt using the Trigger Map.
If multiple triggers apply, run them in this order:
ARCHITECT → BUILDER → REVIEWER → DEMO DIRECTOR → RED TEAM.

### Memory-Check (Mandatory)
Before writing code or giving build advice:
1) Scan `## Memory Bank` for relevant lessons.
2) If a past lesson conflicts with the new request, flag it and propose the least risky path.

### Output Discipline (Hard Rule)
- For build work: output file edits (diffs or file lists), plus commands to run.
- For planning work: output a task board with owners and acceptance checks.
- Never produce long prose. Prefer actionable artifacts.

### Golden Rule (Hard Rule)
LLM does orchestration and explanations, not math.
- Logic/math/scoring → Python/SQL
- Decisions/explanations/summaries → LLM

---

## Trigger Map (Auto-Select Mode)

### 1) ARCHITECT MODE
**Trigger:** database changes, schema definitions, API contracts, system boundaries, queues, storage, data model.
**Behavior:**
- Protect integrity of `/schemas` and contracts.
- Prefer simplest stable interfaces.
- Minimize tech debt that breaks demo stability.
**Outputs:** schema changes, API contracts, migration notes, integration plan.

### 2) BUILDER MODE
**Trigger:** "write code", "implement", "fix", "add feature", "wire", "run", terminal commands, bugs.
**Behavior:**
- Use GSD end-to-end: implement smallest shippable slice.
- Keep code minimal, typed, testable.
- Run `check-schema` and `test` frequently.
**Outputs:** code + commands + test results.

### 3) REVIEWER MODE
**Trigger:** "review", "audit", "refactor", "clean up", "why failing", "stability", "CI".
**Behavior:**
- Be strict. Find regressions, schema drift, brittle logic.
- Enforce acceptance gates and quality checks.
**Outputs:** punch-list + required fixes + verification commands.

### 4) DEMO DIRECTOR MODE
**Trigger:** UI layout, storytelling, animation, "make it obvious", "judges", "demo", "60 sec".
**Behavior:**
- Optimize for 60-second clarity with minimal explanation.
- Prefer counters, status chips, event animations.
- Ensure the loop is visible: stream → case → label → update → pattern card.
**Outputs:** UI changes, demo script, visual feedback loop improvements.

### 5) RED TEAM MODE
**Trigger:** "break this", edge cases, security checks, adversarial sequences, bypass attempts.
**Behavior:**
- Think like a fraudster.
- Generate adversarial sequences for simulator.
- Try to force false negatives and false positives.
**Outputs:** adversarial test cases + mitigations + regression checks.

---

## Swarm Protocol (Specialist Subagents)

### When to Spawn a Swarm
Spawn a swarm when:
- task spans ≥2 domains (backend + UI + ML + demo)
- the decision is high leverage (schemas, storage, event model)
- there is ambiguity that could cause rework
- red teaming would catch failures early

### Default Swarm (roles)
- PM: orchestration, task board, convergence, termination
- Architect: boundaries, schemas, contracts
- Builder: implementation
- Reviewer: QA, tests, schema validation
- Demo Director: UI + narrative clarity
- Red Team: adversarial sequences and bypass testing
Add Researcher only when external intel is required (libraries, best practices, baselines).

### Swarm Rules (Hard)
- Single owner per task (PM assigns).
- Max 2 iterations per disputed decision → PM decides.
- Specialists must output concise artifacts:
  - “Decision / Patch / Test / Next step”
- Synthesis step is mandatory: PM produces one merged plan.

---

## Toolbelt (Repo Commands)

### Setup
- `install`: `pip install -r requirements.txt`

### Run
- `run-sim`: `python -m sim.main`
- `run-backend`: `uvicorn backend.main:app --reload`
- `run-ui`: `streamlit run ui/app.py`
- `demo`: `bash scripts/demo.sh` (full end-to-end loop)

### Test & Validate
- `test`: `pytest tests/ -q`
- `lint`: `ruff check .`
- `format`: `ruff format .`
- `typecheck`: `mypy .`
- `check-schema`: `python scripts/validate_schemas.py`

### DB Utilities (SQLite MVP)
- `db-reset`: `rm -f app.db && python scripts/init_db.py`

### Metrics / Debug
- `tail-events`: `python scripts/tail_events.py` (optional)
- `snapshot`: `python scripts/snapshot_metrics.py` (optional)

---

## Build Guidelines & Stack (Locked for Hackathon)

- Language: Python latest (type hints required)
- Backend: FastAPI
- UI: Streamlit (speed > polish)
- DB: SQLite (single file `app.db`)
- ML: XGBoost (XGBClassifier — L1/L2 regularization + native sparse handling)
- Graph: networkx
- Scheduler: APScheduler or simple asyncio loop
- Schemas: JSON Schema in `/schemas` (single source of truth)
- Storage: local files + SQLite only (no external infra unless necessary)
- Data: faker or kaggle datasets

Constraints:
- No distributed systems. Autonomy is behavior, not Kubernetes.

---

## North Star & Priorities

Goal: ship an autonomous fraud-agent demo.

Autonomy optics must be obvious:
1) Autonomous: transactions stream in without prompts
2) Self-improving: analyst labels visibly change thresholds/precision
3) Pattern-aware: pattern cards appear from mining jobs

If work does not improve autonomy optics, learning optics, pattern optics, or demo clarity, deprioritize.

---

## Directory Structure (Enforced)

- `/sim`       : transaction generation + fraud typologies + ground truth
- `/backend`   : FastAPI + orchestrator + endpoints + persistence
- `/risk`      : deterministic features + scoring + model training
- `/patterns`  : graph mining + pattern card generation
- `/ui`        : Streamlit dashboard for demo and analyst labeling
- `/schemas`   : JSON schemas (contracts). Any change requires `check-schema`
- `/scripts`   : demo runner + init + validation utilities
- `/tests`     : tests (minimum: schema + pipeline smoke tests)
- `/docs`      : demo script + architecture diagram notes + judge Q/A
- `/reports`   : daily build logs, metric snapshots

---

## Schema Contract Rules (Hard)

- `/schemas` is the single source of truth.
- Producers and consumers must validate against schemas at runtime in dev mode.
- Any schema change requires:
  - update all impacted modules in the same change
  - update tests
  - update `/docs/SCHEMA_CHANGES.md`

Minimum schemas:
- `transaction.schema.json`
- `risk_result.schema.json`
- `case.schema.json`
- `analyst_label.schema.json`
- `pattern_card.schema.json`
- `metric_snapshot.schema.json`

---

## Acceptance Gates (Hard)

Before claiming “done” on any feature:
- `check-schema` passes
- `test` passes
- `demo` runs end-to-end (if feature impacts pipeline/UI)
- UI shows the loop (if feature is user-facing)
- failure mode handled minimally (no crashes on empty data)

---

## Memory Bank (Self-Updating Knowledge)

Claude: append here automatically when you learn a durable lesson.
Format: `[YYYY-MM-DD] Context -> Lesson -> Actionable Rule`

- [2026-02-05] Tooling choice -> Streamlit chosen over React to save ~2 days -> Default UI stays Streamlit.
- [2026-02-05] Contract discipline -> Schemas are the API contract -> Never change code outputs without updating schema first.
- [2026-02-05] 7-specialist feasibility panel completed -> Full report at `docs/FEASIBILITY_REPORT.md` -> Verdict: CONDITIONAL NO (today), credible path to YES.
- [2026-02-05] Panel consensus -> Current hackathon success: 55-65%, with 5 fixes: 75-85% -> Execute phases in `.planning/ROADMAP.md`.
- [2026-02-05] "Autonomous" framing -> Zero agent criteria met without LLM -> MUST add at least one LLM integration point (case reasoning).
- [2026-02-05] ML assessment -> 3 hardcoded features is not ML -> Use XGBClassifier with 10-15 features minimum.
- [2026-02-07] ML migration -> Switched from sklearn GradientBoostingClassifier to XGBoost XGBClassifier -> XGBoost handles L1/L2 regularization (reg_alpha, reg_lambda) and sparse data natively, critical for fraud features where most values are zero.
- [2026-02-05] Simulator flaw -> Fraud=$5K-50K, legit=$10-2K is trivially separable -> Add overlapping distributions + 3 fraud typologies.
- [2026-02-05] Red team finding -> Amount-only detection bypassed by structuring in <5 min -> Velocity features are mandatory.
- [2026-02-05] Deriv context -> Hackathon is Deriv AI Talent Sprint (derivatives platform) -> Frame fraud as wash trading, spoofing, bonus abuse.
- [2026-02-05] Phase 1 (wire scorer) blocks everything else -> Do this first, no exceptions.
- [2026-02-05] Demo strategy -> Probability of LLM failure is non-zero -> Implemented "Golden Path" (mocked perfect response for hero transactions) to guarantee 100% demo reliability.
- [2026-02-06] AWS Bedrock AgentCore evaluation -> 4-specialist panel (Architect/Builder/Demo Director/Red Team) unanimously said SKIP for hackathon -> Stole 3 patterns: streaming LLM, investigation timeline, threshold rationale. Mention AgentCore in Q&A only. Revisit for Phase 7+ after GA.

---

## Self-Update Protocol (Meta)

### Update CLAUDE.md when
- the same failure occurs twice (add guardrail)
- a faster workflow is proven (codify as command or rule)
- a new script/skill becomes standard (add to Toolbelt)
- a demo clarity improvement is discovered (add as Demo rule)

### How to update
- Keep changes small.
- Append a line to `## Memory Bank`.
- If adding new commands, ensure scripts exist under `/scripts`.

---

## Development Workflow (GSD)

1) Analyze:
   - auto-select mode(s)
   - memory-check
2) Plan:
   - decompose into smallest shippable steps
   - identify schemas/contracts first if needed
3) Execute:
   - implement
   - run `check-schema` + `test` frequently
4) Verify:
   - run `demo`
   - confirm UI shows autonomy + learning + pattern discovery
5) Document:
   - update Memory Bank with any durable lesson

---

## Demo OS (Hard)

### One-command demo
`scripts/demo.sh` must:
- init db
- start backend
- start UI
- start simulator stream
- start pattern miner scheduler
- print local URLs and “expected visible signals”

### 60-second clarity checklist
The UI must visually show:
- stream flowing
- cases opening automatically
- analyst labels applied
- “learning update” animation/event
- metric trend improving
- new pattern card appearing
