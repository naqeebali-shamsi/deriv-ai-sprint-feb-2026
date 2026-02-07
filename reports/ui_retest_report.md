# UI Regression Test Report
Date: 2026-02-07

## Bug Fix Verification

### Bug 1: Nested Expander -> PASS
**Test:** Clicked "AI Explain" on Case e295c8a5 (Score: 0.984, Priority: high) in the Cases tab.

**Evidence:** The full AI explanation rendered successfully WITHOUT crashing. All required components are present:

- **Agent Analysis** header with model attribution ("fraud-agent-llm (llama3.1:8b)")
- **Summary** in blue info box: "Critical risk transaction detected: $61.56 deposit from bonus_5 to platform_bonus_1 via mobile. Risk score: 0.9840 (BLOCK)."
- **Risk Factors** as bullet list (5 items: Rapid succession, Shared device, Shared IP, Small deposit with shared device/IP, Higher-risk card BIN)
- **Behavioral Analysis**: "Sender bonus_5 has normal transaction frequency."
- **Recommendation** in green box: "BLOCK recommended. Multiple risk factors indicate potential fraud. Escalate to senior analyst."
- **Investigation Timeline** rendered as inline caption paragraphs with checkmark icons -- NOT as a nested expander. Steps shown: start, features, patterns, llm_call, llm_response, complete (with timing data).

No `StreamlitAPIException` was thrown. No crash occurred. The fix correctly replaced the nested `st.expander()` with inline `st.caption()`-style paragraph elements.

Screenshots: `reports/ui_retest_04_ai_explain.png`, `reports/ui_retest_05_investigation_timeline.png`

### Bug 2: Feature Chart NaN -> FAIL
**Test:** Navigated to "Model & Learning" tab, verified chart rendering, and checked browser console warnings.

**Evidence:** The "Top Feature Importances" bar chart visually renders correctly, showing 8 features (amount_high, amount_log, amount_normalized, channel_api, device_reuse_co..., ip_reuse_count_..., is_small_deposit, is_transfer) with valid importance values.

However, the console still logs Vega warnings:
```
WARN Infinite extent for field "Importance_start": [Infinity, -Infinity]
WARN Infinite extent for field "Importance_end": [Infinity, -Infinity]
WARN Infinite extent for field "value--p5bJXXpQgvPz6yvQMFiy": [Infinity, -Infinity]
```

These warnings appear each time the page renders (observed 3 times across tab switches, totaling 7+ Vega warnings in a single session).

**Root cause analysis:** The Python-side NaN/Inf filter (lines 418-420 in `ui/app.py`) is correctly implemented, but the actual API data from `/metric-snapshots` contains NO NaN or Inf values -- all feature importance values are valid floats. The "Infinite extent" warnings originate from Vega-Lite's internal chart rendering, possibly due to:
1. Vega-Lite version mismatch (spec v5.20.1 vs runtime v5.14.0)
2. Streamlit's internal data transformation for the bar_chart/line_chart components
3. Edge cases in how Vega handles zero-valued data points or sparse data

The Python filter is a no-op because the data was never invalid at that level. The fix needs to address the Vega rendering layer, not the Python data layer.

Screenshot: `reports/ui_retest_07_feature_importance.png`

## Smoke Test
- Live Stream tab: **PASS** -- Transaction table renders with columns (ID, Amount, txn_type, sender_id, receiver_id, channel, Risk Score, decision). Shows Approved: 26, Review: 0, Blocked: 4.
- Patterns tab: **PASS** -- 13+ fraud pattern cards render correctly, including Graph patterns (High-Activity Senders/Receivers, Circular Flow Rings) and Velocity patterns (Velocity Spikes), each with confidence levels and progress bars.
- Orbital Greenhouse: **PASS** -- Canvas renders with space-themed visualization, sidebar controls (Scenario Presets, Fraud Types, Fraud Rate, Transactions/Sec), Garden Intelligence panel, Inspection Queue, Discovered Patterns, Learning Log, and Event Feed.

Screenshots: `reports/ui_retest_08_live_stream.png`, `reports/ui_retest_09_patterns.png`, `reports/ui_retest_10_orbital_greenhouse.png`

## Verdict: REGRESSION FOUND

Bug 1 (Nested Expander Crash) is fully fixed -- PASS.
Bug 2 (Feature Chart NaN/Inf Warning) is NOT fixed -- FAIL. The Python-side filter was applied to data that was already clean. The Vega console warnings persist because the root cause is in the charting library layer, not in the data pipeline. The chart renders visually, but the console warnings remain.
