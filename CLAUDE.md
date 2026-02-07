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
- `demo`: `python scripts/demo.py` (full end-to-end loop)

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

## Documentation Navigation

All project documentation is indexed at [`docs/INDEX.md`](docs/INDEX.md) with categories:
- **Architecture & Technical** — system design, decisions, schema changelog
- **Business & Domain** — ROI, compliance, domain validation
- **Demo & Presentation** — demo script, pitch, infographic, pre-flight audit
- **Assessments & Analysis** — panel reports, feasibility studies
- **Research** — technique analyses not yet implemented

QA reports: [`reports/`](reports/) (7 adversarial QA test reports).
Planning docs: [`.planning/`](.planning/) (PROJECT.md, ROADMAP.md).
Schemas: [`schemas/`](schemas/) (6 JSON contracts — single source of truth).

Key documents for quick reference:
- Architecture: [`docs/DESIGN_DECISIONS.md`](docs/DESIGN_DECISIONS.md)
- Demo script: [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md)
- Demo hosting: [`docs/DEMO_HOSTING_GUIDE.md`](docs/DEMO_HOSTING_GUIDE.md)
- QA verdict: [`reports/qa_final_verdict.md`](reports/qa_final_verdict.md)
- Roadmap: [`.planning/ROADMAP.md`](.planning/ROADMAP.md)

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
  See: [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md) Section 5 (ML Model Design)
- [2026-02-05] Simulator flaw -> Fraud=$5K-50K, legit=$10-2K is trivially separable -> Add overlapping distributions + 3 fraud typologies.
- [2026-02-05] Red team finding -> Amount-only detection bypassed by structuring in <5 min -> Velocity features are mandatory.
- [2026-02-05] Deriv context -> Hackathon is Drishpex (derivatives platform) -> Frame fraud as wash trading, spoofing, bonus abuse.
- [2026-02-05] Phase 1 (wire scorer) blocks everything else -> Do this first, no exceptions.
- [2026-02-05] Demo strategy -> Probability of LLM failure is non-zero -> Implemented "Golden Path" (mocked perfect response for hero transactions) to guarantee 100% demo reliability.
- [2026-02-06] AWS Bedrock AgentCore evaluation -> 4-specialist panel (Architect/Builder/Demo Director/Red Team) unanimously said SKIP for hackathon -> Stole 3 patterns: streaming LLM, investigation timeline, threshold rationale. Mention AgentCore in Q&A only. Revisit for Phase 7+ after GA.
  See: [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md) Section 6 (LLM Integration)
- [2026-02-07] Documentation audit -> 14 HIGH-priority undocumented features found, 9 inconsistencies fixed -> Always update docs when code changes; refer to docs/INDEX.md for navigation.
- [2026-02-07] Naming conventions -> docs/ uses UPPER_SNAKE.md, reports/ uses lower_snake.md -> Follow per-directory naming convention for new files.
- [2026-02-07] Schema divergence (RESOLVED) -> init_db.py and backend/db.py had different schemas -> Fixed: backend/db.py is now the single source of truth; init_db.py is a thin wrapper.
- [2026-02-07] Expert review (4-agent audit) -> SSE events only fired from embedded simulator, not from POST /transactions -> Always publish SSE events from the core endpoint, not the caller.
- [2026-02-07] Bootstrap model recall -> 22% recall when velocity features are all zeros in training data -> bootstrap_model.py must inject synthetic velocity/pattern context; use _inject_velocity_context().
- [2026-02-07] ML model caching -> reload_model() deleted attributes instead of nulling them, causing AttributeError -> Set _cache = None, never delete function attributes.
- [2026-02-07] Auto-retrain -> Manual retrain button was only "self-improving" mechanism -> Added background auto-retrain after label endpoint when min samples per class are met.
- [2026-02-07] Hero transaction reliability -> Demo hero txn could score below threshold if model changed -> Added score floor (0.92) for metadata.demo_hero in scorer.py.
- [2026-02-07] XSS in Orbital Greenhouse -> innerHTML from SSE data was unescaped -> Added _esc() HTML entity sanitizer in orbital_data.js for all dynamic content.
- [2026-02-07] Explain-stream blocking -> Synchronous Ollama call froze entire event loop -> Wrapped in asyncio run_in_executor() for non-blocking LLM streaming.
- [2026-02-07] Retrain Guardian agent -> Implemented LLM-powered autonomous model lifecycle agent (risk/guardian.py) -> Guardian decides retrain/skip, evaluates new models, rolls back if quality drops. Deterministic fallback always available. Key safety: asyncio.Lock prevents concurrent retrains, rollback renames (not deletes), 3-failure backoff. SKIP events silent in SSE.
- [2026-02-07] Version sort bug -> `sorted(glob("model_v*.joblib"))` put v0.10.0 before v0.9.0 (lexicographic) -> Added `_version_sort_key()` in trainer.py for numeric semver sorting. Always use numeric tuple sort for version strings, never lexicographic.
- [2026-02-07] Guardian loop retrigger -> Guardian kept retraining because `labels_since` reset to 0 after each retrain but drift remained high -> Ensure retrain conditions use `labels_since` as primary trigger; drift alone with 0 new labels should not retrigger immediately.
- [2026-02-07] Zombie processes -> Multiple uvicorn instances on same port caused guardian to appear dead (`running: False`) -> Always `pkill -f uvicorn` and verify port is free before restarting backend during development.
- [2026-02-07] Algorithm audit (4-agent team) -> 37 algorithms audited, 21 needed rewriting, velocity_clusters window_minutes was dead code -> See `reports/algorithm_verdicts.md` for full verdicts. Always verify parameters are actually used in function bodies.
- [2026-02-07] Pattern detection rewrites -> Replaced naive implementations with textbook algorithms -> Ring detection: Tarjan's SCC (nx.strongly_connected_components). Hub detection: HITS algorithm (nx.hits). Velocity clusters: sliding window two-pointer. Dense subgraphs: SCC + flow-weighted density. Use networkx built-in algorithms, don't hand-roll.
- [2026-02-07] Pattern feature substring bug -> `sender_id in description` matched user_1 inside user_10 -> Replaced with inverted index keyed by member_ids. Never use substring matching for entity membership checks.
- [2026-02-07] Training-serving feature skew -> Duplicate compute_features in scorer.py and trainer.py caused silent divergence -> Deleted duplicate. Single source of truth: `risk.scorer.compute_features()` used by both training and serving.
- [2026-02-07] Trivially separable bootstrap -> Metrics 1.0/1.0/1.0/1.0 meant model learned useless boundary -> Added pattern_count_sender overlap for legit power users. Target bootstrap F1: 0.85-0.95, not 1.0. Perfect metrics = red flag.
- [2026-02-07] ML validation -> Single 80/20 split with 6 test samples is statistically meaningless -> Added stratified 5-fold CV with cross_val_score. Report mean±std. Added scale_pos_weight for class imbalance.
- [2026-02-07] Cyclical time -> Linear hour/23 makes 0 and 23 maximally distant -> Replaced with sin/cos encoding: hour_sin, hour_cos (34→35 features).
- [2026-02-07] Velocity query consolidation -> 11 serial SQL queries per transaction -> Consolidated to 5 with CASE WHEN aggregation + 4 new indexes. Latency ~5.5ms → ~1.5ms.
- [2026-02-07] Structuring threshold -> $200-$950 was wrong; BSA threshold is $10,000 -> Fixed to gauss(9500, 300) clamped [5000, 9900].
- [2026-02-07] Spoofing mismodeled -> Generates completed transfers, not order-place-cancel -> Renamed to "unauthorized_transfer" with realistic amount overlap.
- [2026-02-07] Adversarial generators stateless -> 3 of 5 used new random IDs per call, no patterns formed -> Added persistent ID pools with circular flows for wash trade, recurring senders for structuring/velocity.
- [2026-02-07] DB schema divergence (resolved) -> init_db.py and backend/db.py had different tables (model_state vs agent_decisions), different column order, different indexes -> Unified: backend/db.py is now single source of truth; init_db.py is a thin async wrapper. Never duplicate schema definitions.
- [2026-02-07] init_db.py wrong DB path -> Hardcoded `Path(__file__).parent.parent / "app.db"` ignored DATABASE_PATH env var, wrote to wrong location in Docker -> Fixed by making init_db.py a wrapper around backend.db.init_db_tables() which reads DATABASE_PATH from config.
- [2026-02-07] Docker infra audit (3-agent team) -> 34 findings: PEM files in Docker image, seed-data can't reach backend, UI healthcheck wrong, .env.example breaks Ollama, Ollama publicly exposed, no non-root user -> All fixed. See docs/DEMO_HOSTING_GUIDE.md for current deployment guide.
- [2026-02-07] Docker compose setup ordering -> seed-data depended on backend but not bootstrap-model; init-db and backend raced -> Fixed with depends_on chain: init-db -> bootstrap-model -> seed-data (via service_completed_successfully conditions).
- [2026-02-07] Ollama should NOT be public -> Backend accesses Ollama via Docker internal network (ollama:11434) -> Removed public port mapping from compose and firewall. Never expose LLM endpoints without auth.

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
`scripts/demo.py` must:
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
