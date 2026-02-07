# HACKATHON PITCH TRANSCRIPT: Autonomous Fraud Agent
**Speaker:** [Your Name/Role]
**Context:** Drishpex 2026
**Duration:** 2 Minutes (Short, Sharp)

---

### [0:00 - 0:15] The Hook: "Autonomy is the only way out"
"Judges, Deriv processes millions of transactions. Fraudsters are automating wash trading and structuring attacks that move faster than any human team can review.
Today, most fraud systems are static rule engines. They don't learn, they don't reason, and they don't explain.
We built the **Autonomous Fraud Agent**. And we tested it on enterprise-grade ISO 20022 simulated data, not just toys."

### [0:15 - 0:45] The Loop (Show the UI)
*Action: Switch to the Streamlit Dashboard (Stream tab)*
"This is a live system. You are seeing transactions stream in from our simulator, which is generating 5 real-world fraud typologies including wash trading and velocity abuse.
*Wait for a flash of red/yellow in the stream*
The agent isn't just applying rules. It's using an **XGBoost model** — with built-in L1/L2 regularization and native sparse data handling — to score risk in under 50 milliseconds. But scoring is just step one."

### [0:45 - 1:15] The Hero Moment (The "Golden Path")
*Action: Click 'Cases' tab. Find the case with Sender: `ring_leader_A1` ($12,500).*
"Here is a high-risk case the system auto-opened. A $12,500 transfer.
In a traditional system, an analyst sees a row of numbers.
In our system, the analyst asks the Agent."
*Action: Click '🤖 AI Explain'*
"The Agent actually reasons about the transaction graph. It spots that this is part of a **3-node wash trading ring**. It explains the behavioral velocity. It recommends a specific block action.
This turns a 20-minute investigation into a 5-second decision."

### [1:15 - 1:45] The Innovation: "It Learns"
*Action: Click 'Model & Learning' tab*
"Here is where we win. Every time an analyst labels a case, the system retrains.
You can see the model version incrementing here: v0.1.0 -> v0.2.0.
And you can see the Graph Miner discovering new community clusters automatically.
It gets smarter while the analysts sleep."

### [1:45 - 2:00] The Close
"We didn't build a dashboard. We built an intelligent fraud detection pipeline that learns. And we intentionally separated ML decisions from LLM explanations — because that's how regulated industries need AI to work.
It detects, it reasons, and it learns.
This is production-ready architecture: FastAPI, SQLite WAL-mode, and XGBoost.
Code that scales; Logic that learns.
And to our knowledge, this is the only open-source project that integrates real-time ML scoring, graph pattern mining, LLM explanation, human-in-the-loop retraining, domain-specific fraud typologies, and a full API with dashboard — in one runnable system.
Thank you."

---

### Q&A Crib Sheet (The "Depth" Defense)

**Q: Is this just a wrapper around ChatGPT?**
A: "Absolutely not. The core scoring is a dedicated XGBoost classifier trained on behavioral features like 1-hour velocity and time-since-last-txn. We chose XGBoost specifically for its built-in L1/L2 regularization and native sparse data handling — critical for fraud features where most values are zero. The LLM is *only* used for the explanation layer. The detection is pure, low-latency ML."

**Q: How do you handle wash trading?**
A: "We use NetworkX to build a directed graph of recent transactions. We run four algorithms: cycle detection (DFS) to find closed loops like A->B->C->A, hub analysis for high-connectivity accounts, velocity clustering for temporal bursts, and connected component analysis and density-based clustering to spot coordinated activity. These become 'Pattern Cards' that feed back into the risk score."

**Q: Does it really retrain?**
A: "Yes. The backend has a `/retrain` endpoint that pulls labeled data, re-computes the feature matrix, fits a new XGBoost model, creates a versioned model file, and hot-swaps it into the scorer without downtime."

**Q: Why did you separate the ML model from the LLM?**
A: "By design. In regulated industries — banking, derivatives trading — model decisions must be auditable and deterministic. Our ML model makes the score/flag/block decision using an XGBoost classifier with built-in regularization. The LLM only explains that decision to the analyst. This separation follows Federal Reserve SR 11-7 Model Risk Management guidance and helps with ECOA/FCRA explainability requirements. Most hackathon projects do the opposite — they let the LLM decide. That wouldn't survive a compliance audit."

**Q: How would you deploy this in production?**
A: "We've evaluated AWS Bedrock AgentCore Runtime — serverless agent hosting with session isolation, agent identity management, and built-in observability. Our FastAPI backend ports to AgentCore with minimal changes. For the next phase — tool use and autonomous investigation — AgentCore's MCP gateway would auto-convert our endpoints into agent-callable tools. Today runs local for maximum demo reliability; production runs on AgentCore for enterprise scale."

---
## See Also
- [DEMO_SCRIPT.md](DEMO_SCRIPT.md) — Full 5-7 minute demo walkthrough with detailed Q&A
