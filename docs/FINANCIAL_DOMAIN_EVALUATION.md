# Financial Domain Expert Evaluation: Deriv Fraud Detection System

## 1. Problem Accuracy -- Are These the Right Fraud Types?

### What you have (5 types):
- Wash Trading
- Spoofing
- Bonus Abuse
- Structuring
- Velocity Abuse

### Assessment: Partially correct, with recommendations

**Good choices:**
- **Wash Trading** -- Highly relevant. Core market manipulation offense under MAR (EU) and Commodity Exchange Act (US). For derivatives, manifests as offsetting positions through multiple accounts to inflate volume.
- **Bonus Abuse** -- Extremely relevant for Deriv. The CFTC and SEC have documented bonus manipulation in binary options. Detection of shared devices/IPs across accounts is the correct approach.
- **Structuring** -- Relevant but banking-oriented. For Deriv, thresholds should relate to position sizes, lot limits, or deposit monitoring limits per jurisdiction.

**Areas for improvement:**
- **Spoofing** -- Real spoofing requires Level 2 order book data. System should simulate order placement/cancellation events for realistic detection.
- **Velocity Abuse** -- More accurately called "latency arbitrage." Consider framing as a characteristic of other fraud types rather than standalone.

### Missing Fraud Types (for production roadmap):
1. **Front-Running / Insider Trading** -- Mandatory surveillance under MiFID II and MAR
2. **Price Manipulation via Synthetic Indices** -- Deriv-specific; exploiting the RNG
3. **Account Takeover (ATO)** -- Highest-volume fraud type at online trading platforms
4. **Affiliate Fraud** -- Fake sign-ups and self-referrals
5. **Withdrawal/Chargeback Fraud** -- Deposit with stolen credentials, withdraw to different method

---

## 2. Regulatory Context

### Applicable Regulations for Deriv

| Entity | Regulator | Key Requirements |
|--------|-----------|-----------------|
| Deriv Investments (Europe) Ltd | MFSA (Malta) | MiFID II, MAR, 4AMLD/5AMLD |
| Deriv (FX) Ltd | Labuan FSA (Malaysia) | LFSA Anti-Money Laundering Act |
| Deriv (BVI) Ltd | BVI FSC | AML/CFT requirements |
| Deriv (V) Ltd | VFSC (Vanuatu) | Minimal requirements |

### What the system provides for compliance:
- Transaction monitoring (MAR requirement)
- Pattern detection for wash trading (MAR market manipulation surveillance)
- Velocity monitoring (AML transaction monitoring)
- Audit trail via case creation and analyst labeling
- ML model versioning and explainability

### What production would need:
- Order-level surveillance (MiFID II requires monitoring orders, not just transactions)
- STOR/SAR generation capability
- 5-7 year data retention (ESMA requirement)
- Cross-asset surveillance
- Formal model risk management documentation

---

## 3. Real Fraud Patterns at Deriv-like Platforms

### Pattern 1: Multi-Account Bonus Farming
Single individual creates 5-20 accounts, deposits minimum, claims bonuses, meets volume requirements via offsetting trades, withdraws profit.

### Pattern 2: Platform Arbitrage / Price Feed Exploitation
Ultra-low-latency connections exploit delay between price feed updates and market movements. Especially prevalent with synthetic indices.

### Pattern 3: Deposit-and-Run (Chargeback Fraud)
Deposit using stolen cards, trade to look legitimate, withdraw to crypto wallet. When cardholder disputes, platform eats the loss. **Largest fraud cost by dollar volume** for most online brokers.

### Pattern 4: Coordinated Manipulation of Synthetic Indices
Groups placing large positions simultaneously to influence index behavior or exploit temporary mispricings.

### Pattern 5: Employee/Insider Abuse
Employee with access to pricing engine or client data trades on that information.

---

## 4. The Spoofing Challenge

### What real spoofing requires (per Dodd-Frank Section 747, MAR Article 12):
1. **Order book data** -- seeing all orders at all price levels
2. **Order lifecycle tracking** -- placement, modification, cancellation, fill
3. **Cancel-to-fill ratio analysis** -- spoofers have 90%+ cancellation rates
4. **Price impact correlation** -- did the order placement move prices?
5. **Intent inference** -- was the order ever intended to execute?

### Recommendation:
Either simulate order book data (more impressive to judges) or acknowledge the limitation proactively in the demo: "We model completed transactions; production would extend to the order book."

---

## 5. Business Impact

- **CFTC FY2024**: Highest-ever penalties including $920+ million JPMorgan spoofing case
- **BigOption/BinaryBook case (Jan 2025)**: $451 million in penalties for binary options fraud
- **Malta FIAU**: Fines up to 5 million EUR per breach for AML failings
- **License revocation risk**: MFSA can revoke Deriv's EU license for inadequate surveillance

### ROI for fraud detection at derivatives platforms:
A well-implemented system should save **5-20x its cost annually**, primarily through regulatory risk mitigation.

---

## 6. Regulatory Defensibility

### Current state: Demonstrates the right intent, not yet production-ready

**Strengths regulators would appreciate:**
- Automated transaction monitoring with multiple strategies (rules + ML)
- Graph-based pattern detection for wash trading rings
- Model versioning and explainability
- Human-in-the-loop design

**Production gaps:**
- No order-level surveillance
- No STOR/SAR filing capability
- No data retention compliance
- No formal model risk management documentation

---

## 7. Summary of Recommendations

| Area | Current State | Recommendation |
|------|---------------|----------------|
| Fraud types | 3/5 realistic | Add ATO, chargeback fraud for production |
| Spoofing | Simplified model | Add order book simulation or acknowledge limitation |
| Transaction model | Payment/banking model | Acknowledge in demo; add trade events for production |
| Regulatory mapping | Implicit | Add explicit mapping to MiFID II, MAR, 4AMLD |
| Missing fraud types | No ATO, chargeback | Add for production completeness |

---

## Sources

- [Deriv Regulatory Information](https://deriv.com/regulatory)
- [CFTC Binary Options Fraud](https://www.cftc.gov/BinaryOptionsFraud/index.htm)
- [CFTC FY 2024 Enforcement Results](https://www.cftc.gov/PressRoom/PressReleases/9011-24)
- [$451M Binary Options Fraud Judgment (January 2025)](https://www.cftc.gov/PressRoom/PressReleases/9040-25)
- [Spoofing Enforcement Cases (Patomak)](https://patomak.com/2025/10/14/spoofing-enforcement-cases-and-steps-to-protect-your-firm/)
- [MiFID II and Market Abuse (ComplyLog)](https://blog.complylog.com/mifid-ii/mifid-ii-market-abuse)
- [Trade Surveillance Under MAR (MAP FinTech)](https://mapfintech.com/solutions/trade-surveillance-mar/)
- [Spoofing Detection: Shallow Data Not Enough (Data Intellect)](https://dataintellect.com/blog/level-up-your-surveillance-why-shallow-data-isnt-enough-for-spoofing-detection/)
- [Understanding False Positives (Flagright)](https://www.flagright.com/post/understanding-false-positives-in-transaction-monitoring)
- [Dodd-Frank Act (CFTC)](https://www.cftc.gov/LawRegulation/DoddFrankAct/index.htm)
- [MiFID II (ESMA)](https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mifid-ii)
