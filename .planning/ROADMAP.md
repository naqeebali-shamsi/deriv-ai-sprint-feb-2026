# ROADMAP.md — Hackathon Sprint Execution Plan

## Milestone: Hackathon MVP (Deriv AI Talent Sprint)

**Goal:** Transform the blueprint into a functional autonomous fraud agent demo.
**Success metric:** 60-second demo showing the full autonomy loop.
**Panel-estimated success probability after completion:** 75-85%

---

## Phase 1: Wire the Pipeline (CRITICAL PATH)
**Priority:** P0 — Nothing else matters until this works
**Estimated effort:** 2-4 hours
**Status:** DONE

### Objective
Make the risk scorer actually score transactions end-to-end. Currently `POST /transactions` stores the transaction but returns `risk_score=None`. After this phase, every transaction gets a real score, and high-risk transactions auto-create cases.

### Tasks
- [ ] 1.1 Connect `risk/scorer.py` to `backend/main.py` — call `score_transaction()` inside `create_transaction()`
- [ ] 1.2 Store risk results in `risk_results` table after scoring
- [ ] 1.3 Auto-create cases for transactions scoring above threshold (>= 0.5 review, >= 0.8 block)
- [ ] 1.4 Return real `risk_score` and `decision` in the `TransactionOut` response
- [ ] 1.5 Update `GET /transactions` to include risk_score from risk_results join
- [ ] 1.6 Verify end-to-end: POST transaction -> score computed -> risk_result stored -> case created -> visible in UI

### Acceptance
- `POST /transactions` returns a non-null `risk_score`
- High-risk transactions appear in Cases tab automatically
- `GET /metrics` shows non-zero `flagged_txns`

---

## Phase 2: Realistic Simulator + Features (CREDIBILITY)
**Priority:** P0
**Estimated effort:** 4-6 hours
**Status:** DONE

### Objective
Fix the simulator to generate non-trivially-separable data and add velocity features so the model has to actually work (not just threshold on amount).

### Tasks
- [ ] 2.1 Redesign simulator distributions — overlapping amounts (legit can be high, fraud can be low)
- [ ] 2.2 Add fraud typologies: structuring (many small txns), velocity abuse (rapid-fire), cross-account rings
- [ ] 2.3 Add Deriv-specific patterns: wash trading, spoofing/layering, bonus abuse
- [ ] 2.4 Implement velocity features in scorer: txn_count_1h, txn_count_24h, amount_sum_1h per sender
- [ ] 2.5 Add temporal features: hour_of_day, is_weekend, time_since_last_txn
- [ ] 2.6 Add amount statistics: z_score_vs_sender_mean, percentile_rank
- [ ] 2.7 Expand feature set to 10-15 features total
- [ ] 2.8 Update tests for new simulator patterns and features

### Acceptance
- Simulator generates 3+ distinct fraud typologies
- A simple amount threshold no longer achieves >90% accuracy
- Scorer uses 10+ features
- Red team cannot trivially bypass detection with structuring

---

## Phase 3: ML Training Loop (SELF-IMPROVING)
**Priority:** P0
**Estimated effort:** 4-8 hours
**Status:** DONE

### Objective
Implement the learning loop: train a real model on labeled data, retrain periodically, show metrics improving over time. This is the "self-improving" claim made visible.

### Tasks
- [ ] 3.1 Create `risk/trainer.py` — train GradientBoostingClassifier on labeled transactions
- [ ] 3.2 Implement feature computation for training data (join transactions + analyst_labels)
- [ ] 3.3 Save trained model with joblib, version it (v0.1.0, v0.2.0, etc.)
- [ ] 3.4 Load trained model in scorer instead of hardcoded weights
- [ ] 3.5 Create `/retrain` endpoint or scheduled job (every N labels received)
- [ ] 3.6 Compute real precision/recall/F1 from labels vs predictions, store in metric_snapshots
- [ ] 3.7 Update `GET /metrics` to return real precision/recall values
- [ ] 3.8 Add model version display in UI
- [ ] 3.9 Show before/after metrics to demonstrate improvement
- [ ] 3.10 Handle cold start: use rule-based scoring until enough labels exist (min ~50 per class)

### Acceptance
- A real sklearn model is trained and used for scoring
- Metrics endpoint returns real precision/recall/F1
- After N analyst labels + retrain, metrics visibly improve
- Model version increments on retrain
- UI shows the learning happening

---

## Phase 4: LLM Agent Integration (AUTONOMOUS)
**Priority:** P1 — Makes "agent" claim defensible
**Estimated effort:** 8-12 hours
**Status:** DONE (Ollama llama3.1:8b + template fallback)

### Objective
Add at least one LLM integration point that makes the system genuinely agentic: the LLM reasons about cases, explains decisions, and generates pattern descriptions.

### Tasks
- [ ] 4.1 Choose LLM provider (Deriv API / OpenAI / Anthropic / local Ollama)
- [ ] 4.2 Create `backend/agent.py` — LLM-powered case investigation
- [ ] 4.3 Implement case summarization: LLM analyzes transaction + features + risk score -> natural language summary
- [ ] 4.4 Implement risk explanation: LLM explains *why* a transaction was flagged with specific evidence
- [ ] 4.5 Implement pattern description generation: LLM describes discovered patterns in analyst-friendly language
- [ ] 4.6 Add agent reasoning to case creation workflow (observe -> reason -> act)
- [ ] 4.7 Create `/cases/{id}/summary` endpoint for LLM-generated summaries
- [ ] 4.8 Display LLM summaries in UI Cases tab
- [ ] 4.9 Add SHAP/feature importance visualization (even simple bar chart)
- [ ] 4.10 Ensure LLM calls are async and don't block the scoring pipeline

### Acceptance
- Cases have LLM-generated natural language summaries
- Risk explanations cite specific features and evidence
- Pattern cards have LLM-generated descriptions
- A judge asking "where is the AI?" gets a concrete answer
- System satisfies at least 2 of Andrew Ng's 4 agentic patterns

---

## Phase 5: Graph Pattern Mining (PATTERN DISCOVERY)
**Priority:** P1
**Estimated effort:** 4-6 hours
**Status:** DONE

### Objective
Implement actual graph-based pattern mining using networkx. Build sender-receiver transaction graphs, detect communities, find fraud rings, and generate meaningful pattern cards.

### Tasks
- [ ] 5.1 Build sender-receiver graph from transactions using networkx
- [ ] 5.2 Run connected component analysis to find transaction clusters
- [ ] 5.3 Implement community detection (Louvain algorithm)
- [ ] 5.4 Detect dense subgraphs (potential fraud rings)
- [ ] 5.5 Implement cycle detection for round-tripping funds
- [ ] 5.6 Generate pattern cards from graph analysis results
- [ ] 5.7 Store pattern cards in database with proper schema fields
- [ ] 5.8 Schedule pattern mining to run periodically (every N minutes)
- [ ] 5.9 Display pattern cards in UI with graph visualization (if time permits)
- [ ] 5.10 Feed discovered patterns back into scoring as features

### Acceptance
- Pattern miner builds and analyzes real graphs
- At least 2 pattern types discovered (rings, hubs, velocity clusters)
- Pattern cards appear in UI Patterns tab with meaningful descriptions
- Patterns feed back into the detection pipeline

---

## Phase 6: Demo Polish + Story (PRESENTATION)
**Priority:** P1
**Estimated effort:** 3-4 hours
**Status:** PARTIAL — Technical demo works, demo script + arch diagram + speech still needed

### Objective
Polish the demo for 60-second clarity. Ensure judges see the full autonomous loop without explanation needed.

### Tasks
- [ ] 6.1 Create demo seed script: pre-populate DB with ~200 labeled transactions for warm start
- [ ] 6.2 Add visual indicators in UI: "Learning Update" animation when model retrains
- [ ] 6.3 Add metric trend charts (precision/recall over time)
- [ ] 6.4 Add "new pattern discovered" notification/animation
- [ ] 6.5 Write 60-second demo script (what to show, in what order)
- [ ] 6.6 Frame for Deriv: rename fraud types to trading-specific (wash trading, spoofing, etc.)
- [ ] 6.7 Ensure `scripts/demo.sh` starts everything with one command
- [ ] 6.8 Test full demo end-to-end 3 times
- [ ] 6.9 Prepare judge Q&A responses (what's the model? how does it learn? what about scale?)
- [ ] 6.10 Clean up code for review (hackathon fast-tracks to interviews)

### Acceptance
- One-command demo works
- 60-second walkthrough shows full loop: stream -> score -> case -> label -> learn -> pattern
- Deriv-specific framing throughout
- No crashes on empty data or edge cases

---

---
---

# MILESTONE 2: Level 3 Autonomy — LLM Tool Use (Post-Hackathon)

**Goal:** Upgrade from "LLM as narrator" (Level 2) to "LLM as investigator" (Level 3).
The LLM drives its own investigation loop — querying data, discovering patterns, and recommending actions dynamically.

**Current state:** LLM receives a pre-formatted text report and writes an analysis.
**Target state:** LLM decides what data it needs, queries for it, reasons over results, and takes action.

---

## Phase 7: Tool Registry + Execution Engine
**Priority:** P0 — Foundation for all tool use
**Estimated effort:** 2-3 weeks
**Status:** NOT STARTED

### Objective
Build a tool execution framework that lets the LLM call Python functions by name with structured arguments, receive results, and continue reasoning.

### Tasks
- [ ] 7.1 Design tool schema format (name, description, parameters JSON Schema, return type)
- [ ] 7.2 Build `agent/tool_registry.py` — register, validate, and dispatch tool calls
- [ ] 7.3 Build `agent/executor.py` — ReAct loop (Reason → Act → Observe → Repeat)
- [ ] 7.4 Implement turn budget (max 10 tool calls per investigation to prevent runaway)
- [ ] 7.5 Implement tool call logging (every call stored in `agent_actions` table for audit)
- [ ] 7.6 Add permission levels: read-only tools (safe) vs write tools (need approval)
- [ ] 7.7 Build sandbox: tool errors don't crash the system, LLM gets error message and adapts
- [ ] 7.8 Test with a simple 2-tool investigation (query_transaction + query_sender_history)

### Acceptance
- LLM can call registered tools and receive structured results
- ReAct loop terminates within budget
- All tool calls are logged and auditable
- Tool errors are handled gracefully

---

## Phase 8: Investigation Tools (Read-Only)
**Priority:** P0
**Estimated effort:** 1-2 weeks
**Status:** NOT STARTED

### Objective
Equip the LLM with read-only tools to investigate cases autonomously. These are safe — they only query data, never modify it.

### Tools to Implement
- [ ] 8.1 `query_transaction(txn_id)` — Get full transaction details
- [ ] 8.2 `query_sender_history(sender_id, hours=24)` — Recent transactions from a sender
- [ ] 8.3 `query_receiver_history(receiver_id, hours=24)` — Recent transactions to a receiver
- [ ] 8.4 `get_account_stats(account_id)` — Aggregate stats (total volume, frequency, unique counterparties)
- [ ] 8.5 `find_related_cases(account_id)` — Past cases involving this account
- [ ] 8.6 `query_graph_neighbors(account_id, depth=2)` — Who is this account connected to?
- [ ] 8.7 `detect_patterns_for_account(account_id)` — Run pattern detection focused on one account
- [ ] 8.8 `get_risk_features(txn_id)` — Detailed feature breakdown for a scored transaction
- [ ] 8.9 `search_similar_transactions(amount, txn_type, time_range)` — Find transactions matching a profile

### Acceptance
- LLM can autonomously investigate a case using 3+ tools in sequence
- Investigation produces richer, more specific explanations than the current pre-formatted approach
- No data modification occurs

---

## Phase 9: Action Tools (Write — Human Approval Required)
**Priority:** P1
**Estimated effort:** 2-3 weeks
**Status:** NOT STARTED

### Objective
Give the LLM the ability to take action — but with mandatory human approval for anything that modifies state.

### Tools to Implement
- [ ] 9.1 `propose_account_freeze(account_id, reason)` — Queues a freeze for analyst approval
- [ ] 9.2 `propose_case_escalation(case_id, severity, reason)` — Escalate to senior analyst
- [ ] 9.3 `draft_sar(case_id, findings)` — Draft a Suspicious Activity Report
- [ ] 9.4 `link_cases(case_id_1, case_id_2, relationship)` — Connect related cases
- [ ] 9.5 `update_risk_score(txn_id, adjustment, reason)` — Propose score override with justification
- [ ] 9.6 `send_alert(channel, message, severity)` — Notify compliance team via Slack/email

### Approval Flow
```
LLM proposes action → Stored in pending_actions table → Analyst reviews in UI
    → Approved: action executes
    → Rejected: LLM notified, can propose alternative
```

### Tasks
- [ ] 9.7 Create `pending_actions` table (action_type, args, proposed_by, status, reviewed_by)
- [ ] 9.8 Build approval UI in Streamlit (pending actions queue with approve/reject)
- [ ] 9.9 Implement action execution on approval
- [ ] 9.10 Feed rejection reasons back to LLM for learning

### Acceptance
- LLM can propose actions that appear in analyst queue
- No action executes without human approval
- Full audit trail of proposed vs executed actions

---

## Phase 10: Agentic Investigation Loop
**Priority:** P1
**Estimated effort:** 2-3 weeks
**Status:** NOT STARTED

### Objective
Wire it all together: when a case is opened, the LLM automatically investigates using tools, builds an evidence chain, and proposes actions — all before a human even looks at it.

### Tasks
- [ ] 10.1 Trigger agent investigation on case creation (async background task)
- [ ] 10.2 Build investigation prompt with case context + available tools
- [ ] 10.3 Implement evidence chain: each tool result is appended to the investigation log
- [ ] 10.4 LLM produces structured verdict: {confidence, risk_level, evidence_summary, proposed_actions}
- [ ] 10.5 Store investigation results in `case_investigations` table
- [ ] 10.6 Display investigation timeline in UI (tool calls + reasoning + verdict)
- [ ] 10.7 A/B test: compare LLM-investigated cases vs current pre-formatted explanations
- [ ] 10.8 Add investigation quality metrics (did analyst agree with LLM verdict?)

### Example Investigation Flow
```
Case opened: $45,000 transfer from acct_772 to acct_339
    ↓
LLM: query_sender_history("acct_772", hours=24)
    → 47 transactions, $312K total volume
LLM: query_graph_neighbors("acct_772", depth=2)
    → Connected to acct_339, acct_441, acct_772 (circular!)
LLM: detect_patterns_for_account("acct_772")
    → Circular ring detected, confidence 0.92
LLM: find_related_cases("acct_441")
    → 2 prior fraud cases involving acct_441
LLM: propose_account_freeze("acct_772", "Circular ring with repeat offender acct_441")
LLM: draft_sar(case_id, "Wash trading ring: acct_772 ↔ acct_339 ↔ acct_441")
    ↓
Verdict: HIGH RISK (confidence: 94%)
  Evidence: 5 tool calls, circular ring, prior fraud history
  Actions: freeze proposed, SAR drafted, pending analyst approval
```

### Acceptance
- Cases are automatically investigated within 60 seconds of creation
- Investigation uses 3+ tools dynamically (not hardcoded sequence)
- Analyst sees full investigation timeline with evidence chain
- At least 70% of LLM verdicts align with analyst decisions

---

## Phase 11: Memory + Learning From Investigations
**Priority:** P2
**Estimated effort:** 3-4 weeks
**Status:** NOT STARTED

### Objective
The agent remembers past investigations and gets better over time. When it encounters a pattern it's seen before, it references the precedent.

### Tasks
- [ ] 11.1 Build investigation memory: embed past verdicts + outcomes in a vector store
- [ ] 11.2 On new investigation, retrieve similar past cases as context
- [ ] 11.3 Track investigation accuracy over time (LLM verdict vs analyst decision)
- [ ] 11.4 Fine-tune tool selection based on which tools were most useful in past investigations
- [ ] 11.5 Implement "investigation playbooks" — learned sequences for known fraud types
- [ ] 11.6 Add confidence calibration: if LLM says 90% but is right only 60% of the time, recalibrate

### Acceptance
- Agent references similar past cases in new investigations
- Investigation accuracy improves measurably over 100+ cases
- Agent develops specialized strategies for different fraud types

---

## Post-Hackathon Execution Order

```
Phase 7 (Tool Registry) ──→ Phase 8 (Read Tools) ──→ Phase 10 (Investigation Loop)
                                     │                          │
                                     └──→ Phase 9 (Write Tools) ┘
                                                                │
                                                    Phase 11 (Memory + Learning)
```

**Level 2 → Level 3 transition:** Phases 7-8 (LLM can investigate)
**Level 3 → Level 3.5 transition:** Phases 9-10 (LLM can propose actions)
**Level 3.5 → Level 4 path:** Phase 11 (LLM learns from experience)

---

## Hackathon Execution Order (ALL DONE)

```
Phase 1 (Wire Pipeline) ──────────────────┐
                                           ├─> Phase 3 (ML Training Loop)    ALL
Phase 2 (Simulator + Features) ───────────┘         │                       DONE
                                                     ├─> Phase 4 (LLM Agent)  ✓
                                                     │
Phase 5 (Graph Mining) ──────────────────────────────┘
                                                     │
                                           Phase 6 (Demo Polish)  ✓
```

## Hackathon Deliverables Summary

| Deliverable | Status | Key Metric |
|-------------|--------|------------|
| End-to-end scoring pipeline | DONE | Every txn scored in <100ms |
| 5 fraud typologies in simulator | DONE | structuring, velocity, wash trading, spoofing, bonus abuse |
| ML training loop with versioning | DONE | v0.2.0: AUC 0.9956, F1 0.967 |
| Ollama LLM case explanations | DONE | llama3.1:8b with template fallback |
| Graph pattern mining (4 algorithms) | DONE | rings, hubs, velocity spikes, dense subgraphs |
| One-command demo | DONE | `python scripts/demo.py` |
| Test suite | DONE | 33 tests passing, 6 schemas valid |

## Risk Register

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| LLM API not available at hackathon | Blocks Phase 4 | Used local Ollama + template fallback | MITIGATED |
| Model accuracy too low with realistic data | Undermines demo credibility | GBClassifier achieves 0.97 F1 | MITIGATED |
| Demo crashes during presentation | Fatal | Tested end-to-end, added DB indexes for perf | MITIGATED |
| Judge probes ML depth | Credibility damage | Feature importance available, versioned models | MITIGATED |
| Time runs out before Phase 4 | "Agent" claim unsupported | All 6 phases completed | RESOLVED |
| DB performance degrades under load | Seed script timeouts | Added compound indexes + WAL mode | MITIGATED |
