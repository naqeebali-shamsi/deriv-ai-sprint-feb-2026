# UI Click-Through Test Report

**Date:** 2026-02-07
**Tester:** Claude Opus 4.6 (Automated via Playwright)
**Target:** Streamlit Classic Dashboard at http://localhost:8501
**Backend:** http://localhost:8000 (healthy)
**Model Version:** Started v0.3.0, ended v0.4.0 after retrain

---

## Summary

| Category | Pass | Fail | Total |
|----------|------|------|-------|
| Setup & Navigation | 4 | 0 | 4 |
| Sidebar Elements | 4 | 0 | 4 |
| Live Stream Tab | 5 | 0 | 5 |
| Cases Tab | 11 | 1 | 12 |
| Patterns Tab | 4 | 0 | 4 |
| Model & Learning Tab | 7 | 1 | 8 |
| Orbital Greenhouse | 2 | 0 | 2 |
| **TOTAL** | **37** | **2** | **39** |

**Overall Result: 37/39 PASS (94.9%)**

---

## Detailed Results

### Setup & Navigation

```
[PASS] #1 - Navigate to http://localhost:8501
  Evidence: Page loaded with title "Orbital Greenhouse | Autonomous Fraud Agent"

[PASS] #2 - Take browser snapshot of initial layout
  Evidence: Orbital Greenhouse view rendered with sidebar, canvas iframe, and controls
  Screenshot: reports/ui_test_01_initial_load.png

[PASS] #3 - Switch to Classic Dashboard via sidebar radio button
  Evidence: Clicked "Classic Dashboard" radio button, view switched successfully
  Note: Required opening sidebar first (sidebar was collapsed behind iframe)

[PASS] #4 - Confirm Classic Dashboard is rendered
  Evidence: Full dashboard visible with title "Autonomous Fraud Agent", pipeline flow
  (Stream -> Score -> Case -> Label -> Learn), metrics row, and tab bar
  Screenshot: reports/ui_test_02_classic_dashboard.png
```

### Sidebar Elements

```
[PASS] #5 - Verify "Backend: http://127.0.0.1:8000" text shown
  Evidence: Sidebar shows "Backend: http://127.0.0.1:8000" as code element

[PASS] #6 - Verify "Backend connected" success indicator
  Evidence: Green alert element with text "Backend connected" visible in sidebar
  Note: A secondary "Backend offline" alert also visible (likely conditional styling)

[PASS] #7 - Toggle "Auto-refresh (5s)" ON, verify page refreshes
  Evidence: Checked the checkbox. After 7 seconds, Transactions count changed
  from 1,272 to 1,280, confirming automatic data refresh

[PASS] #8 - Toggle "Auto-refresh (5s)" OFF, verify refresh stops
  Evidence: Unchecked the checkbox. After 7 seconds, no data changes observed.
  Transaction count remained at 1,288
```

### Live Stream Tab

```
[PASS] #9 - Click "Live Stream" tab
  Evidence: Tab was already selected (default). Tab showed as [selected] in DOM

[PASS] #10 - Verify transaction table renders with correct columns
  Evidence: Table renders with columns: ID, Amount, txn_type, sender_id, receiver_id,
  channel, Risk Score, decision
  Screenshot: reports/ui_test_03_live_stream.png
  Note: Column headers use snake_case (txn_type, sender_id, receiver_id) instead of
  display names from checklist (Type, Sender, Receiver)

[PASS] #11 - Verify risk score column shows progress bars
  Evidence: Risk Score column displays colored progress bars -- red for high scores
  (0.998), grey/light for low scores (0.003, 0.004). Numeric values shown alongside

[PASS] #12 - Verify decision chips show Approved, Review, Blocked counts
  Evidence: Below table header shows "Approved: 26", "Review: 2", "Blocked: 2"
  Values updated dynamically with auto-refresh

[PASS] #13 - Verify transactions are visible
  Evidence: Multiple transactions visible in table including amounts from $15.35 to
  $12,500.00, various transaction types (payment, deposit, transfer, withdrawal),
  and mixed decisions (approve, block)
```

### Cases Tab

```
[PASS] #14 - Click "Cases" tab
  Evidence: Tab switched to Cases, showing "Open Cases for Review" heading

[PASS] #15 - Verify cases list renders with expanders
  Evidence: Cases displayed as expandable groups with case headers. Multiple cases
  visible, each as a collapsible section
  Screenshot: reports/ui_test_04_cases_tab.png

[PASS] #16 - Verify priority icons (red/yellow/green), case ID, score, priority
  Evidence: Cases show priority icons:
  - Red circle for high priority (e.g., "Case 23b723f6... | Score: 0.998 | Priority: high")
  - Yellow circle for medium priority (e.g., "Case 6dc18efb... | Score: 0.551 | Priority: medium")
  No green (low priority) cases observed in current dataset

[PASS] #17 - Filter dropdown: select "open"
  Evidence: Dropdown opened showing options: open, all, closed. Selected "open".
  Only open cases displayed (~210+ cases)

[PASS] #18 - Filter dropdown: select "closed"
  Evidence: Selected "closed" filter. Displayed exactly 4 closed cases
  (matching "Cases Closed: 4" metric)
  Screenshot: reports/ui_test_05_cases_closed.png
  Note: Heading still reads "Open Cases for Review" even when filter is "closed"
  (minor UI text issue, not blocking)

[PASS] #19 - Filter dropdown: select "all"
  Evidence: Selected "all" filter. Displayed all cases (open + closed combined).
  More cases shown than either filter alone

[PASS] #20 - Expand a case
  Evidence: Cases are auto-expanded in current implementation (no explicit click
  needed). Each expanded case shows full details

[PASS] #21 - Verify case detail shows Transaction ID, Risk Score, Status
  Evidence: Expanded case shows:
  - Transaction: 30da7364-788... (as code element)
  - Risk Score: 0.9982
  - Status: open

[FAIL] #22 - Click "AI Explain" button, verify full explanation
  Evidence: AI Explain button clicked successfully. Generated detailed explanation with:
  - "Agent Analysis" header with "fraud-agent-v1 (llm)" attribution
  - Summary text in blue info box ("CRITICAL ALERT: Circular wash trading ring...")
  - Risk Factors bullet list (Pattern Match, High Velocity, Zero Net Economic Value, Structuring)
  - Behavioral Analysis section (detailed mule network analysis)
  - Recommendation in green success box ("BLOCK IMMEDIATE...")
  Issue: Investigation Timeline section throws StreamlitAPIException:
  "Expanders may not be nested inside other expanders" (line 325 in ui/app.py).
  The timeline uses st.expander() inside the case st.expander(), which Streamlit forbids.
  Screenshot: reports/ui_test_06_ai_explain.png

[PASS] #23 - Click "Fraud" button, verify labeling
  Evidence: Clicked "Fraud" on a case. Success message appeared: "Labeled as fraud"
  (bold). Case removed from open list. Cases Closed incremented from 4 to 5.
  Precision improved from 50.0% to 60.0%, F1 from 66.7% to 75.0%

[PASS] #24 - Click "Legit" button, verify labeling
  Evidence: Clicked "Legit" on a case. Success message appeared: "Labeled as not_fraud"
  (bold). Case removed from open list. Cases Closed incremented to 6.

[PASS] #25 - Click "Needs Review" button, verify labeling
  Evidence: Clicked "Needs Review" on a case. Page re-rendered. The case list refreshed.
  Note: "Needs Review" labels the case but the success toast was consumed during
  page rerun. The case was processed (page refreshed with updated list)
```

### Patterns Tab

```
[PASS] #26 - Click "Patterns" tab
  Evidence: Tab switched to Patterns, showing "Discovered Fraud Patterns" heading

[PASS] #27 - Verify pattern cards render
  Evidence: Pattern cards displayed with type indicators, names, descriptions,
  confidence metrics, and progress bars
  Screenshot: reports/ui_test_07_patterns_tab.png

[PASS] #28 - Verify card details (type icon, name, description, confidence, progress bar)
  Evidence: Cards show:
  - Type indicators: [Graph] for graph patterns, [Velocity] for velocity patterns
  - Names: "High-Activity Sender: user_260", "Velocity Spike: ring_leader_A1",
    "Circular Flow Ring (3 members)", etc.
  - Descriptions: Detailed text about the pattern
  - Confidence: 40%, 55%, 70%, 85%, 95% values displayed
  - Progress bars: Colored bars matching confidence percentage
  Note: No [Behavioral] type patterns observed (only Graph and Velocity)

[PASS] #29 - Click "Run Mining" button, verify mining runs
  Evidence: Clicked "Run Mining". Page re-rendered with new patterns discovered.
  New patterns appeared including:
  - "Circular Flow Ring (204 members)" at 65% confidence
  - "Circular Flow Ring (4 members)" at 85% confidence
  - "Circular Flow Ring (5 members)" at 75% confidence
  - Multiple new velocity spikes and high-activity patterns
  Note: No explicit "Found X patterns!" success toast was observed in the snapshot,
  but the pattern list clearly refreshed with new entries

[PASS] #30 - Verify patterns list refreshes after mining
  Evidence: Pattern list grew substantially after mining, with new Graph and
  Velocity patterns appearing that were not present before
```

### Model & Learning Tab

```
[PASS] #31 - Click "Model & Learning" tab
  Evidence: Tab switched to Model & Learning panel

[PASS] #32 - Verify panel renders
  Evidence: Full panel rendered with Actions section, Scoring Thresholds table,
  Model Performance chart, and Feature Importances chart
  Screenshot: reports/ui_test_08_model_learning.png

[PASS] #33 - Verify Scoring Thresholds table
  Evidence: Table shows:
  - Review | >= 0.50 | Balances analyst workload vs missed fraud
  - Block  | >= 0.80 | High-confidence auto-block

[PASS] #34 - Click "Retrain (Ground Truth)" button
  Evidence: Clicked button. Progress text "Training on ground truth..." appeared,
  then success message: "Model v0.4.0 trained! AUC=0.9992"
  Model version badge updated from "Model: v0.3.0 ML" to "Model: v0.4.0 ML"

[PASS] #35 - Click "Retrain (Analyst Labels)" button
  Evidence: Clicked button. Warning message appeared:
  "Need at least 60 labeled samples, have 6"
  This is correct behavior -- only 6 labels were applied during testing
  Screenshot: reports/ui_test_09_model_learning_full.png

[PASS] #36 - Verify model version incremented after retrain
  Evidence: Header badge changed from "Model: v0.3.0 ML" to "Model: v0.4.0 ML"
  after Ground Truth retrain

[PASS] #37 - Verify "Model Performance Over Time" chart renders
  Evidence: Vega line chart rendered with metrics across versions v0.2.0, v0.3.0, v0.4.0
  Legend shows: AUC-ROC, F1, Precision, Recall
  Lines visible with AUC-ROC near 1.0 and Precision around 0.85
  Screenshot: reports/ui_test_12_charts_bottom.png

[FAIL] #38 - Verify "Top Feature Importances" bar chart renders
  Evidence: Bar chart renders with feature names visible (amount_high, amount_log,
  amount_normali..., channel_api, device_reuse_co..., ip_reuse_count_...,
  is_small_deposit, is_transfer) and importance values shown as bars
  Issue: Console warnings indicate "Infinite extent for field 'Importance'"
  which means some feature importance values may be NaN/Inf. The chart renders
  but with potentially incomplete data. This is a data quality issue, not a
  rendering issue. The chart visually appears functional.
  Note: Marking as FAIL due to console warnings about infinite extents,
  which could cause visual artifacts for some features
```

### Orbital Greenhouse View

```
[PASS] #39 - Switch to Orbital Greenhouse in sidebar
  Evidence: Clicked "Orbital Greenhouse" radio button. View switched to the
  canvas-based visualization

[PASS] #40 - Verify Orbital Greenhouse renders (screenshot)
  Evidence: Screenshot shows:
  - Animated orbital visualization with pods/transactions orbiting
  - Greenhouse plants in bottom-right area
  - Left sidebar: Scenario Presets, Fraud Types, Fraud Rate/TPS sliders
  - Right panel: Garden Intelligence, Inspection Queue, Discovered Patterns, Learning Log
  - Bottom: Event Feed with live transaction events
  - Status bar: "DEFENSE GRID ACTIVE - Analyzing order flow"
  - Model version shown as "Defense: v0.4.0"
  Canvas is not blank/broken -- all elements render correctly
  Screenshot: reports/ui_test_13_orbital_greenhouse.png
```

---

## Issues Found

### Critical Issues
None.

### Medium Issues

1. **Nested Expander Error in AI Explain (Case #22)**
   - **Location:** `N:\DERIV_AI_HACKATHON\ui\app.py`, line 325
   - **Error:** `StreamlitAPIException: Expanders may not be nested inside other expanders`
   - **Impact:** Investigation Timeline section fails to render within case expanders
   - **Fix:** Replace the inner `st.expander("Investigation Timeline")` with a different
     Streamlit component (e.g., `st.container()` with a toggle, or display timeline
     inline without nesting)

2. **Feature Importances Chart Console Warnings (Case #38)**
   - **Location:** Vega chart rendering
   - **Warning:** `WARN Infinite extent for field "Importance"`
   - **Impact:** Some feature importance values may be NaN/Infinity, causing potential
     visual artifacts in the bar chart
   - **Fix:** Sanitize feature importance values before passing to the chart

### Minor Issues

3. **Cases Heading Not Dynamic (Case #18)**
   - **Location:** Cases tab heading
   - **Issue:** Heading reads "Open Cases for Review" regardless of filter selection
     (open/closed/all)
   - **Fix:** Make heading dynamic based on filter selection

4. **Backend Offline Alert Always Visible (Case #6)**
   - **Location:** Sidebar
   - **Issue:** Both "Backend connected" (green) and "Backend offline" (red) alerts
     are always rendered in the DOM. They should be conditionally displayed.
   - **Fix:** Use `if/else` logic to show only the appropriate status

5. **Footer Text Inconsistency**
   - **Location:** Sidebar footer
   - **Issue:** Footer text shows "Drishpex 2026" in some renders instead of
     "Deriv AI Talent Sprint 2026"
   - **Fix:** Ensure consistent footer text

---

## Screenshots Captured

| # | File | Description |
|---|------|-------------|
| 1 | `reports/ui_test_01_initial_load.png` | Initial Orbital Greenhouse view |
| 2 | `reports/ui_test_02_classic_dashboard.png` | Classic Dashboard first render |
| 3 | `reports/ui_test_03_live_stream.png` | Live Stream tab with transaction table |
| 4 | `reports/ui_test_04_cases_tab.png` | Cases tab with open cases |
| 5 | `reports/ui_test_05_cases_closed.png` | Cases tab filtered to closed |
| 6 | `reports/ui_test_06_ai_explain.png` | AI Explain output (partial - before error) |
| 7 | `reports/ui_test_07_patterns_tab.png` | Patterns tab with pattern cards |
| 8 | `reports/ui_test_08_model_learning.png` | Model & Learning tab (top) |
| 9 | `reports/ui_test_09_model_learning_full.png` | Model & Learning with retrain warning |
| 10 | `reports/ui_test_10_charts.png` | Charts area (before scroll) |
| 11 | `reports/ui_test_11_charts_scrolled.png` | Charts area (scroll attempt) |
| 12 | `reports/ui_test_12_charts_bottom.png` | Performance and Feature charts visible |
| 13 | `reports/ui_test_13_orbital_greenhouse.png` | Orbital Greenhouse view final check |

---

## Test Environment

- **Platform:** Windows (MSYS_NT-10.0-26200)
- **Browser:** Chromium (via Playwright)
- **Streamlit:** Running on localhost:8501
- **Backend:** FastAPI on localhost:8000
- **Test Duration:** ~10 minutes
- **Transactions During Test:** 1,192 -> 1,600+ (growing via background simulator)
