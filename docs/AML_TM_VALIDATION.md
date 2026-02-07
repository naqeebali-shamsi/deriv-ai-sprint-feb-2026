# AML TM VALIDATION: The Automation of Monotony

**To:** Deriv AI Hackathon Judges / Product Strategy
**Subject:** Validation of "Autonomous Agent" vs. Traditional AML Transaction Monitoring (TM) Level 1 Workflows

## 1. The Core Question
**Does this system replace the monotonous parts of a Modern AML TM System?**

**Verdict:** **YES, it replaces the Level 1 (L1) Triage backlog.**
It does not replace the Compliance Officer (L3), but it automates the "investigative grunt work" that consumes 80-90% of an analyst's day.

---

## 2. Mapping the Monotony

Traditional AML monitoring suffers from a 95%+ False Positive rate. The "monotonous part" is the manual review of these false positives.

| The Monotonous Task (Human L1 Analyst) | The Autonomous Agent Solution | Status in Demo |
|----------------------------------------|-------------------------------|----------------|
| **1. Data Gathering** (10-15 mins)<br>Querying SQL for user history, checking IP logs, looking up device IDs. | **Instant Context Injection**<br>`backend/main.py` automatically aggregates velocity (1h, 24h) and history before scoring. | ✅ Live |
| **2. Link Analysis** (20-30 mins)<br>Manually searching "Who else did this user send money to?" in Excel/Tableau. | **Auto-Graph Mining**<br>`patterns/miner.py` runs NetworkX algorithms to find rings and hubs instantly. No manual query needed. | ✅ Live |
| **3. Narrative Writing** (10-15 mins)<br>Writing the ticket: *"User A sent $5k to User B..."* | **LLM Reasoning**<br>`risk/explainer.py` drafts the "Risk Factors" and "Behavioral Analysis" summary automatically. | ✅ Live |
| **4. Decisioning** (5 mins)<br>Clicking "False Positive" or "Escalate". | **Auto-Labeling / Recommendation**<br>Agent proposes "BLOCK" or "APPROVE" with high confidence. Human validates, Agent learns. | ✅ Live |

---

## 3. Strategic Fit: Supplement vs. Replace

### Where it **REPLACES** (Automation)
*   **The L1 Triage Queue:** The agent effectively acts as an infinite-capacity L1 analyst. It filters the "obvious" noise and creates rich case files for the "real" alerts.
*   **Static Rule Maintenance:** Instead of humans manually tuning "Block if > $10k", the `risk/trainer.py` loop learns the effective threshold from feedback, replacing the monotony of rule governance.

### Where it **SUPPLEMENTS** (Augmentation)
*   **The SAR Filing (L2/L3):** The agent drafts the *content* (Reasoning, Evidence, Graph Links), but a specialized human (L2) validates the "Intent" before filing a Suspicious Activity Report (SAR) to regulators.
*   **New Typology Discovery:** While the graph miner finds *mathematical* anomalies, human intuition is still needed to define *new* crimes. The Agent surfaces the pattern; the Human names it.

---

## 4. The "Deriv" Specific Value
For a high-frequency trading platform like Deriv, the "Monotony" is often **Wash Trading** (users trading with themselves to generate volume/bonuses).
*   **Human way:** Extremely hard to spot in a list of million trades.
*   **Agent way:** The `patterns/miner.py` (Cycle Detection) finds `A -> B -> C -> A` loops mathematically. It turns a "Needle in a haystack" problem into a "Notification" problem.

## 5. Final Assessment
This solution **validates** as a robust **L1 Automation Layer**. It transforms the AML workflow from "Reviewing Transactions" (Monotonous) to "Reviewing Investigations" (High Value).
