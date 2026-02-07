# Demo Script — Autonomous Fraud Detection Agent

**Format:** Live demo (no slides). Architecture diagram on screen first, then switch to live system.
**Total time:** 5-7 minutes (adjust pacing to your slot)
**Setup:** Run `python scripts/demo.py` 2 minutes before your turn. Confirm both URLs are live.

---

## Pre-Demo Checklist

```bash
# 2 minutes before your turn:
python scripts/demo.py

# Confirm these are live:
# http://localhost:8501  (Streamlit dashboard)
# http://localhost:8000/docs  (API docs — keep as backup tab)
```

Open two browser tabs:
1. **Tab 1:** Architecture diagram (the infographic you generated)
2. **Tab 2:** http://localhost:8501 (Streamlit dashboard)

---

## PART 1: The Problem (30 seconds)

> **[Show architecture diagram]**
>
> "Deriv processes thousands of financial transactions every day — deposits, withdrawals, transfers between trading accounts.
>
> Some of these are fraud — wash trading, spoofing, structuring, bonus abuse.
>
> The problem: fraud evolves. Static rules can't keep up. By the time you write a rule to catch yesterday's pattern, fraudsters have already moved on.
>
> So we built something different — a fraud detection agent that learns."

---

## PART 2: The Architecture (60 seconds)

> **[Still on architecture diagram]**
>
> "Here's how it works. Five components, one loop.
>
> **Transactions stream in** from trading activity — we simulate this with realistic synthetic data covering five fraud typologies.
>
> **Every transaction gets scored in real-time** by a machine learning model — not rules, not thresholds — an XGBoost model trained on 34 behavioral features including device reuse signals, IP geolocation risk, receiver-side inflow patterns, and card BIN risk scoring. We chose XGBoost specifically for its built-in L1/L2 regularization and native sparse data handling — critical when most fraud features are zeros. Things like: how many transactions did this sender make in the last hour? How many unique recipients? How fast are they going? What device are they on? Have we seen this IP before?
>
> **High-risk transactions automatically become cases** — no human triggers this. The system decides.
>
> **An analyst reviews the case** — they can ask our AI agent to explain WHY the transaction was flagged. The agent runs on Llama 3.1, locally, and gives a structured breakdown: risk factors, behavioral analysis, pattern connections, and a clear recommendation.
>
> **Here's the key part — the learning loop.** When the analyst labels a case as fraud or legitimate, that label feeds back into the training pipeline. The model retrains, gets smarter, and the next batch of transactions is scored by a better model. We track this — version 1 had an F1 of 0.57, version 2 jumped to 0.97.
>
> **On top of all this, a graph mining engine** analyzes the transaction network to find structural patterns — circular money rings, hub accounts, velocity spikes — things you can't see from individual transactions.
>
> Let me show you this running live."

---

## PART 3: Live Demo (3-4 minutes)

> **[Switch to Tab 2 — Streamlit dashboard]**

### 3a. The Stream (20 seconds)

> "You can see transactions flowing in real-time. Each one has been scored — green for approved, yellow for review, red for blocked. The risk scores are right here.
>
> Notice the simulator is running at 1 transaction per second — this is continuous, no one is pressing a button."

**[Point to the transaction stream table. Show the color-coded risk chips.]**

### 3b. The Cases (40 seconds)

> "Now let's look at what the system flagged automatically."

**[Click on the Cases section. Expand a high-risk case.]**

> "This case was opened automatically — $11,000 transfer via API, risk score 0.99, priority HIGH. No human asked for this to be created.
>
> Watch this — I'll ask the AI agent to explain why."

**[Click the "AI Explain" button. Wait ~5 seconds for Llama to respond.]**

> "The agent analyzed the transaction and found: elevated amount, API channel indicating automation, and behavioral patterns consistent with spoofing. It recommends BLOCK with 85% confidence, and tells us what additional data would improve its assessment.
>
> This isn't a template — this is Llama 3.1 reasoning about the specific evidence."

### 3c. The Learning Loop (60 seconds)

> "Here's where it gets interesting — the self-improving part."

**[Find an open case. Click the label button — mark it as "fraud".]**

> "I just labeled this case as fraud. That label is now stored. The system automatically checks if it has enough labeled data, and if so, retrains the model in the background — no button click needed.
>
> You can also trigger a manual retrain."

**[If auto-retrain hasn't fired yet, click the "Retrain" button in the Model panel.]**

> "Watch the model version — it just incremented. The new model was trained on the analyst's feedback. Next time a similar transaction comes in, it'll be scored by this better model.
>
> Look at the metrics trend — you can see precision and F1 improving across model versions. The system literally gets smarter the more you use it."

### 3d. Pattern Discovery (40 seconds)

> "One more thing — individual transaction scoring isn't enough. Sophisticated fraud involves networks."

**[Scroll to the Patterns section.]**

> "Our graph mining engine built a transaction network and found these patterns automatically — circular rings where money flows A to B to C back to A, hub accounts connected to an unusual number of counterparties, and velocity spikes.
>
> These pattern cards are generated from actual graph analysis using NetworkX — cycle detection, degree centrality, community detection. Each one has a confidence score and the accounts involved."

---

## PART 4: Why This Matters (30 seconds)

> "So what makes this different from a rule engine?
>
> **It runs end-to-end** — transactions stream in, get scored, cases open, patterns are discovered — no human in the loop until review time.
>
> **It learns** — analyst feedback retrains the model. We went from F1 of 0.57 to 0.97 in two training cycles.
>
> **It explains itself** — a local LLM provides structured reasoning, not black-box scores.
>
> **It finds networks** — graph mining catches what individual transaction analysis misses.
>
> **It's compliance-aware** — ML decides, LLM explains. That's how regulated industries need AI to work.
>
> **It's complete** — to our knowledge, no other open-source project integrates all six components: real-time ML scoring, graph mining, LLM explanation, human-in-the-loop retraining, fraud typologies, and full API/dashboard.
>
> This is a working prototype of what intelligent fraud detection looks like for a derivatives trading platform."

---

## Judge Q&A — Prepared Answers

### "What ML model do you use?"
> "XGBClassifier from XGBoost, trained on 34 features across five categories: amount signals, velocity features, device/IP reuse indicators, receiver-side inflow patterns, and geo/BIN risk scores. The most important features are sender velocity — transaction count and cumulative amount in the last hour — which account for about 80% of the model's predictive power. We chose XGBoost over sklearn's GradientBoosting because it has built-in L1/L2 regularization (reg_alpha and reg_lambda) to prevent overfitting, and native sparse data handling — critical for fraud features where most values are zero."

### "How does the LLM integration work?"
> "We run Llama 3.1 (8B parameters) locally through Ollama. When an analyst clicks Explain, we query the database for the transaction, its features, risk score, and any related patterns. We format that into a structured prompt and ask the LLM to analyze it. The LLM produces a case report with six sections. If Ollama is unavailable, we fall back to deterministic template-based explanations — same format, just less nuanced."

### "Is this truly autonomous?"
> "The pipeline runs end-to-end without human intervention: scoring, case creation, pattern mining. The human is in the loop for case review and labeling — which is exactly right for a regulated environment. We also have active learning: the model identifies its most uncertain predictions and suggests those to analysts first. That's genuine intelligent behavior — the system decides what to ask the human."

### "How would this scale?"
> "Currently SQLite with async I/O and indexed queries — handles hundreds of transactions per second on a laptop. For production, we've evaluated **AWS Bedrock AgentCore Runtime** as our deployment target — it provides serverless agent hosting with session isolation via microVMs, IAM-backed agent identity, and OpenTelemetry observability built in. Our architecture ports to AgentCore with minimal changes — just an `@app.entrypoint` annotation and containerization. On the data side: swap SQLite for PostgreSQL, add a message queue (Kafka/Redis Streams) between ingestion and scoring, and shard velocity queries by account ID. The architecture is already modular — each component is a separate Python module."

### "What about false positives?"
> "Our model at v0.2.0 has precision of 0.957 — meaning 95.7% of flagged transactions are actually fraud. The remaining 4.3% are false positives that go to analyst review. The learning loop is designed to reduce this over time — every analyst label makes the next model more precise. And our active learning system prioritizes the most uncertain cases for analyst review, which means human effort is focused where it matters most."

### "What fraud types can it detect?"
> "Five typologies: structuring (breaking large amounts into small ones to avoid thresholds), velocity abuse (rapid-fire transactions), wash trading (circular money flows), spoofing (rapid order placement and cancellation), and bonus abuse (multiple accounts claiming promotions). The graph mining specifically catches wash trading rings that individual transaction scoring would miss."

### "What's the tech stack?"
> "Python end-to-end. FastAPI backend, Streamlit dashboard, SQLite database, XGBoost for ML, NetworkX for graph analysis, Ollama with Llama 3.1 for AI explanations. Everything runs locally — no cloud dependencies, no API keys needed."

### "Why separate ML from LLM?"
> "Regulatory compliance. In derivatives trading, model decisions must be auditable, deterministic, and reproducible. Our XGBoost model makes the approve/review/block decision — it's fast, explainable, and version-controlled. The LLM only generates the analyst-facing explanation. This follows Federal Reserve SR 11-7 guidance on model risk management. Most AI projects let the LLM decide everything — that wouldn't survive a compliance audit in financial services."

### "Doesn't retraining on every label risk degrading the model?"
> "Good question — we don't do online learning where each label nudges the model. Every retrain builds a fresh model from scratch on the full labeled dataset. So one bad label can't snowball. We also gate on minimum sample counts — the system won't retrain with fewer than 10 samples per class — and every model version saves its metrics so you can see if performance degrades. The system auto-retrains in the background once sufficient labels accumulate, so analysts never have to think about it. In production you'd add three things: a validation holdout that the new model must beat before promotion, automatic rollback if live precision drops, and a label review workflow where a second analyst confirms high-impact labels. But the key insight is that the system can retrain at all from analyst feedback — most fraud platforms require a data science team to do that offline."

### "What would you build next?"
> "Tool use for the LLM. Right now, we pre-fetch all data and hand it to Llama as a report. The next step is giving the LLM tools — let it query the database, explore the transaction graph, check account history — and drive its own investigation loop. We'd deploy this on AWS Bedrock AgentCore Runtime, which provides the agent execution environment, MCP-compatible tool gateway, and cross-session memory we'd need. That takes it from a narrator to a true investigative agent."

---

## Emergency Fallbacks

| Problem | Fix |
|---------|-----|
| Backend crashed | `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000` |
| No transactions showing | Check simulator: `python -m sim.main --tps 1` |
| Ollama not responding | Explanations will use template fallback — still works, mention "we also have an LLM mode" |
| UI frozen | Refresh browser. Streamlit auto-reconnects. |
| Empty database | `python scripts/seed_demo.py --count 200` |
| Port 8000 in use | `netstat -ano \| grep 8000` then `taskkill //F //PID <pid>` |

---
## See Also
- [PITCH_TRANSCRIPT.md](PITCH_TRANSCRIPT.md) — 2-minute condensed pitch version
- [PRE_DEMO_AUDIT.md](PRE_DEMO_AUDIT.md) — Pre-flight readiness check
- [ARCHITECTURE.mmd](ARCHITECTURE.mmd) — Diagram shown during demo
