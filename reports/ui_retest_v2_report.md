# UI Regression Test Report v2

**Date:** 2026-02-07
**Tester:** Automated (Claude Code)
**Target:** Streamlit Classic Dashboard at http://localhost:8501
**System State:** Backend running (http://localhost:8000), 2,300+ transactions, 379+ open cases, model v0.4.0

---

## TEST 1: AI Explain -- Investigation Timeline (was nested expander crash)

**Status: PASS**

### Steps Performed
1. Navigated to http://localhost:8501
2. Switched to "Classic Dashboard" via sidebar radio button
3. Clicked "Cases" tab
4. First case (eef89f0f, Score: 0.999, Priority: high) was already expanded
5. Clicked "AI Explain" button on that case
6. Waited for LLM response to render

### Evidence
The AI Explain response rendered successfully with the following sections, all inline (no nested expanders, no crash):

- **Agent Analysis** header with attribution "fraud-agent-v1 (llm)"
- **Critical Alert** (green info box): "Step ID: 74 CRITICAL ALERT: Circular wash trading ring detected involving 3 accounts moving $12,500."
- **Risk Factors** (4 bullet points):
  - Pattern Match: 'Circular Flow Ring (3 members)' detected with 95% confidence
  - High Velocity: Sender moved funds <2 minutes after receiving them
  - Zero Net Economic Value: Funds round-tripped back to origin source (A->B->C->A)
  - Structuring: Amounts slightly varied ($4,950, $4,980) to evade round-number detection
- **Behavioral Analysis** (inline paragraph): Classic 'layering' behavior description
- **Recommendation** (green alert box): BLOCK IMMEDIATE with specific action items
- **Investigation Timeline** rendered as **inline caption paragraphs** (not nested expanders):
  - `start` -- Analyzing txn $12,500.00 from ring_leader_A1 (0ms)
  - `pattern_match` -- Known scenario detected: wash_trading_hero (0ms)
  - `complete` -- Cached pattern response served (0ms)

### Verdict
The Investigation Timeline renders correctly as inline captions with checkmark icons and bold step labels. No nested expander crash. No errors in console. **FIX CONFIRMED.**

---

## TEST 2: Feature Importance Chart (was Vega "Infinite extent" warning)

**Status: FAIL**

### Steps Performed
1. Clicked "Model & Learning" tab
2. Scrolled to "Top Feature Importances" bar chart
3. Verified chart renders visually with 8 non-zero features (amount_high, amount_log, amount_normall..., channel_api, device_reuse_co..., ip_reuse_count_..., is_small_deposit, is_transfer)
4. Checked console messages at warning level

### Evidence -- Chart Rendering
The bar chart renders and displays only non-zero features. The data filtering code at `ui/app.py` lines 418-420 correctly removes zero/NaN/Inf values before creating the DataFrame:
```python
clean = {k: v for k, v in importance.items()
         if isinstance(v, (int, float)) and v > 0 and v == v and abs(v) != float("inf")}
```

### Evidence -- Console Warnings (STILL PRESENT)
Console log shows the following "Infinite extent" warnings:

**From Feature Importances bar chart:**
```
WARN Infinite extent for field "Importance_start": [Infinity, -Infinity]
WARN Infinite extent for field "Importance_end": [Infinity, -Infinity]
```

**From Model Performance Over Time line chart:**
```
WARN Infinite extent for field "value--p5bJXXpQgvPz6yvQMFiy": [Infinity, -Infinity]
```

These warnings appear on every render cycle (observed at ~31s and ~91s in the session). The warnings come from Vega-Lite's internal scale domain computation, not from the raw data. Even though the input data contains only valid non-zero floats, Streamlit's `st.bar_chart()` and `st.line_chart()` generate Vega-Lite specs where aggregate fields (`_start`, `_end`) produce infinite extents.

### Root Cause Analysis
The data-level filtering (removing zero values) is necessary but not sufficient. The "Infinite extent" warnings persist because:
1. `st.bar_chart()` internally uses stacked bar encoding which creates `_start` and `_end` aggregate fields that trigger the warning in Vega-Lite
2. `st.line_chart()` also triggers a similar warning for its value field encoding
3. This is a Streamlit/Vega-Lite rendering pipeline issue, not a data issue

### Verdict
The chart renders visually and shows correct non-zero-only data, but the "Infinite extent" console warnings are **still present**. The fix addressed the data filtering but did not eliminate the Vega-Lite warnings. **FIX NOT FULLY VERIFIED.**

---

## Summary

| Test | Description | Status |
|------|------------|--------|
| TEST 1 | AI Explain -- Investigation Timeline renders as inline captions (no nested expander crash) | **PASS** |
| TEST 2 | Feature Importance Chart -- Vega "Infinite extent" warnings eliminated | **FAIL** |

### Recommendations for TEST 2 Fix
To fully eliminate the "Infinite extent" warnings, consider:
1. Switch from `st.bar_chart()` to `st.altair_chart()` with explicit axis domain configuration (e.g., `alt.Y('Importance:Q', scale=alt.Scale(domain=[0, max_val]))`)
2. The `st.line_chart()` for Model Performance Over Time also needs the same treatment
3. Alternatively, suppress the warnings at the Vega-Lite level by setting `{"config": {"logger": {"level": "error"}}}` if Streamlit supports custom Vega config
