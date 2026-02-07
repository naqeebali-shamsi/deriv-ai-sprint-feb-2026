"""Streamlit dashboard for Autonomous Fraud Agent demo.

Primary view: Orbital Greenhouse — immersive HTML5 Canvas with pixel art
aesthetic, real-time SSE data stream, and full analyst workflow.

Fallback: Classic tabbed dashboard for direct API interaction, case
management, model retraining, and pattern discovery.
"""
import json
import time
from datetime import datetime
from pathlib import Path

import httpx
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_settings

API_URL = get_settings().backend_url
ASSETS_DIR = Path(__file__).parent / "assets"


# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Orbital Greenhouse | Autonomous Fraud Agent",
    page_icon="\U0001F331",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =============================================================================
# ORBITAL GREENHOUSE — IMMERSIVE CANVAS UI
# =============================================================================

@st.cache_data(ttl=3600)
def _load_asset(filename: str) -> str:
    """Read a UI asset file with caching."""
    path = ASSETS_DIR / filename
    if not path.exists():
        # Try subdirectory
        path = ASSETS_DIR / "stitch" / filename
    return path.read_text(encoding="utf-8")


def build_orbital_html(backend_url: str) -> str:
    """Assemble the Orbital Greenhouse HTML with all JS inlined."""
    layout = _load_asset("stitch/code.html")
    sprites = _load_asset("pixel_sprites.js")
    engine = _load_asset("orbital_engine.js")
    data_layer = _load_asset("orbital_data.js")

    init_script = f"""
    (function() {{
      var BACKEND_URL = "{backend_url}";

      function boot() {{
        var canvas = document.getElementById('greenhouse-canvas');
        if (!canvas) {{
          console.error('[OG] Canvas element not found');
          return;
        }}

        // Create animation engine
        var engine = new OrbitalEngine(canvas);

        // Create data layer (SSE + REST + DOM bridge)
        var dataLayer = new OrbitalDataLayer(BACKEND_URL, engine);

        // Wire controls (buttons, sliders, checkboxes)
        dataLayer.wireControls();

        // Expose for debugging
        window.__engine = engine;
        window.__data = dataLayer;

        // Fetch initial state
        dataLayer.getMetrics();
        dataLayer.getPatterns();
        dataLayer.getSimulatorStatus().then(function(status) {{
          if (status && status.running) {{
            var startBtn = document.getElementById('btn-start');
            var stopBtn = document.getElementById('btn-stop');
            if (startBtn) startBtn.style.display = 'none';
            if (stopBtn) stopBtn.style.display = 'block';
          }}
        }});

        console.log('[OG] Orbital Greenhouse initialized', {{ backend: BACKEND_URL }});
      }}

      if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', boot);
      }} else {{
        boot();
      }}
    }})();
    """

    scripts_block = (
        "<script>\n" + sprites + "\n</script>\n"
        "<script>\n" + engine + "\n</script>\n"
        "<script>\n" + data_layer + "\n</script>\n"
        "<script>\n" + init_script + "\n</script>\n"
    )

    return layout.replace("</body>", scripts_block + "</body>")


def render_orbital_greenhouse():
    """Render the immersive Orbital Greenhouse canvas UI."""
    # Hide Streamlit chrome for immersive feel
    st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {
            padding-top: 0.25rem !important;
            padding-bottom: 0 !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            max-width: 100% !important;
        }
        /* Make iframe fill available space */
        iframe[title="streamlit_app.static.streamlit.components.v1"] {
            border: none !important;
        }
    </style>
    """, unsafe_allow_html=True)

    html = build_orbital_html(API_URL)
    components.html(html, height=870, scrolling=False)


# =============================================================================
# CLASSIC DASHBOARD (fallback)
# =============================================================================

# --- Custom CSS for classic view ---
CLASSIC_CSS = """
<style>
    .chip-approve { background: #10b981; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 600; }
    .chip-review { background: #f59e0b; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 600; }
    .chip-block { background: #ef4444; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 600; }
    .chip-model { background: #6366f1; color: white; padding: 3px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 600; }
    .loop-step { display: inline-block; padding: 4px 12px; margin: 2px; border-radius: 16px; font-size: 0.8em; font-weight: 600; }
    .loop-active { background: #10b981; color: white; }
    .loop-idle { background: #374151; color: #9ca3af; }
</style>
"""


def fetch_api(endpoint: str, method: str = "GET", json_data: dict | None = None):
    """Fetch data from backend API."""
    try:
        if method == "POST":
            resp = httpx.post(f"{API_URL}{endpoint}", json=json_data, timeout=10)
        else:
            resp = httpx.get(f"{API_URL}{endpoint}", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        return None
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def render_header():
    """Render the header with branding and model status."""
    col_title, col_status = st.columns([3, 1])
    with col_title:
        st.markdown("# Autonomous Fraud Agent")
        st.caption("Real-time fraud detection for Deriv | Self-improving ML + Graph Pattern Mining")
    with col_status:
        metrics = fetch_api("/metrics")
        if metrics:
            ver = metrics.get("model_version", "missing")
            is_ml = "rules" not in ver
            badge = "ML" if is_ml else "Rules"
            chip = "approve" if is_ml else "review"
            st.markdown(
                f'<div style="text-align:right; margin-top:12px;">'
                f'<span class="chip-model">Model: {ver}</span> '
                f'<span class="chip-{chip}">{badge}</span></div>',
                unsafe_allow_html=True,
            )
    return metrics


def render_metrics(metrics: dict | None):
    """Render the top metrics row."""
    if not metrics:
        st.warning("Backend not reachable. Start with: `uvicorn backend.main:app --reload`")
        return
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Transactions", f"{metrics['total_txns']:,}")
    c2.metric("Flagged", f"{metrics['flagged_txns']:,}",
              delta=f"{metrics['flagged_txns']/max(metrics['total_txns'],1)*100:.1f}%" if metrics['total_txns'] > 0 else None)
    c3.metric("Cases Open", metrics["cases_open"])
    c4.metric("Cases Closed", metrics["cases_closed"])
    prec = metrics.get("precision")
    rec = metrics.get("recall")
    f1 = metrics.get("f1")
    c5.metric("Precision", f"{prec:.1%}" if prec is not None else "\u2014")
    c6.metric("Recall", f"{rec:.1%}" if rec is not None else "\u2014")
    c7.metric("F1 Score", f"{f1:.1%}" if f1 is not None else "\u2014")


def render_autonomy_loop(metrics: dict | None):
    """Show the autonomy loop steps as a visual pipeline."""
    if not metrics:
        return
    has_txns = metrics["total_txns"] > 0
    has_cases = metrics["cases_open"] > 0 or metrics["cases_closed"] > 0
    has_labels = metrics.get("precision") is not None
    is_ml = "rules" not in metrics.get("model_version", "rules")
    steps = [("Stream", has_txns), ("Score", has_txns), ("Case", has_cases),
             ("Label", has_labels), ("Learn", is_ml)]
    html = '<div style="text-align:center; margin: 8px 0;">'
    for i, (name, active) in enumerate(steps):
        cls = "loop-active" if active else "loop-idle"
        html += f'<span class="loop-step {cls}">{name}</span>'
        if i < len(steps) - 1:
            html += '<span style="color:#6b7280;"> \u2192 </span>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_live_stream():
    """Render the live transaction stream tab."""
    st.subheader("Recent Transactions")
    txns = fetch_api("/transactions?limit=30")
    if not txns:
        st.info("No transactions yet. Start the simulator.")
        return
    df = pd.DataFrame(txns)
    if df.empty:
        return
    display_cols = [c for c in ["txn_id", "amount", "txn_type", "sender_id",
                                "receiver_id", "channel", "risk_score", "decision"]
                    if c in df.columns]
    df_display = df[display_cols].copy()
    if "txn_id" in df_display.columns:
        df_display["txn_id"] = df_display["txn_id"].str[:8] + "..."
    for col in ("sender_id", "receiver_id"):
        if col in df_display.columns:
            df_display[col] = df_display[col].str[:15]
    st.dataframe(
        df_display, use_container_width=True, hide_index=True,
        column_config={
            "txn_id": st.column_config.TextColumn("ID", width="small"),
            "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
            "risk_score": st.column_config.ProgressColumn("Risk Score", min_value=0, max_value=1, format="%.3f"),
        },
        height=450,
    )
    if "decision" in df.columns:
        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<span class="chip-approve">Approved: {len(df[df["decision"]=="approve"])}</span>', unsafe_allow_html=True)
        c2.markdown(f'<span class="chip-review">Review: {len(df[df["decision"]=="review"])}</span>', unsafe_allow_html=True)
        c3.markdown(f'<span class="chip-block">Blocked: {len(df[df["decision"]=="block"])}</span>', unsafe_allow_html=True)


def render_cases():
    """Render the case management tab with analyst labeling."""
    col_header, col_action = st.columns([3, 1])
    with col_header:
        st.subheader("Open Cases for Review")
    with col_action:
        case_filter = st.selectbox("Filter", ["open", "all", "closed"], index=0, label_visibility="collapsed")
    status_param = None if case_filter == "all" else case_filter
    endpoint = f"/cases?limit=20" + (f"&status={status_param}" if status_param else "")
    cases = fetch_api(endpoint)
    if not cases:
        st.success("No open cases. All caught up!")
        return
    for case in cases:
        score = case.get("risk_score", 0) or 0
        priority = case.get("priority", "medium")
        priority_icon = {"high": "\U0001F534", "medium": "\U0001F7E1", "low": "\U0001F7E2"}.get(priority, "\u26AA")
        with st.expander(
            f"{priority_icon} Case {case['case_id'][:8]}... | Score: {score:.3f} | Priority: {priority}",
            expanded=(case.get("status") == "open"),
        ):
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Transaction:** `{case['txn_id'][:12]}...`")
            c2.write(f"**Risk Score:** {score:.4f}")
            c3.write(f"**Status:** {case.get('status', 'open')}")
            if case.get("status") == "open":
                st.markdown("**Analyst Decision:**")
                btn_cols = st.columns(4)
                if btn_cols[0].button("Legit", key=f"legit_{case['case_id']}", use_container_width=True):
                    _label_case(case["case_id"], "not_fraud")
                if btn_cols[1].button("Fraud", key=f"fraud_{case['case_id']}", use_container_width=True):
                    _label_case(case["case_id"], "fraud")
                if btn_cols[2].button("Needs Review", key=f"unc_{case['case_id']}", use_container_width=True):
                    _label_case(case["case_id"], "needs_info")
            if st.button("AI Explain", key=f"explain_{case['case_id']}", use_container_width=True):
                with st.spinner("Generating AI case analysis..."):
                    explanation = fetch_api(f"/cases/{case['case_id']}/explain")
                    if explanation:
                        st.markdown("---")
                        st.markdown(f"**Agent Analysis** \u2014 *{explanation.get('agent', 'fraud-agent')}*")
                        st.info(explanation.get("summary", ""))
                        factors = explanation.get("risk_factors", [])
                        if factors:
                            st.markdown("**Risk Factors:**")
                            for f in factors:
                                st.markdown(f"- {f}")
                        behavioral = explanation.get("behavioral_analysis", "")
                        if behavioral:
                            st.markdown(f"**Behavioral Analysis:** {behavioral}")
                        rec = explanation.get("recommendation", "")
                        if rec:
                            st.success(f"**Recommendation:** {rec}")
                        timeline = explanation.get("investigation_timeline", [])
                        if timeline:
                            st.markdown("**Investigation Timeline**")
                            for step in timeline:
                                icon = {"ok": "\u2705", "fallback": "\u26A0\uFE0F"}.get(step.get("status", ""), "\u2022")
                                st.caption(f"{icon} **{step['step']}** \u2014 {step.get('detail', '')} ({step.get('elapsed_ms', 0):.0f}ms)")


def render_patterns():
    """Render discovered pattern cards."""
    col_header, col_action = st.columns([3, 1])
    with col_header:
        st.subheader("Discovered Fraud Patterns")
    with col_action:
        if st.button("Run Mining", use_container_width=True):
            with st.spinner("Mining patterns..."):
                result = fetch_api("/mine-patterns", method="POST")
                if result:
                    st.success(f"Found {result['patterns_found']} patterns!")
                    st.rerun()
    patterns = fetch_api("/patterns?limit=15")
    if not patterns:
        st.info("No patterns discovered yet.")
        return
    for p in patterns:
        confidence = p.get("confidence", 0) or 0
        ptype = p.get("pattern_type", "unknown")
        type_icon = {"graph": "Graph", "velocity": "Velocity", "behavioral": "Behavioral"}.get(ptype, ptype)
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"**[{type_icon}] {p['name']}**")
                st.caption(p.get("description", "No description")[:200])
            with c2:
                st.metric("Confidence", f"{confidence:.0%}")
            st.progress(confidence)


def render_model_panel():
    """Render the ML model management panel."""
    st.subheader("Model & Learning")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Actions**")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Retrain (Ground Truth)", use_container_width=True):
                with st.spinner("Training on ground truth..."):
                    result = fetch_api("/retrain-from-ground-truth", method="POST")
                    if result and result.get("trained"):
                        m = result.get("metrics", {})
                        st.success(f"Model {result['version']} trained! AUC={m.get('auc_roc', 'N/A')}")
                        time.sleep(1)
                        st.rerun()
                    elif result:
                        st.warning(result.get("error", "Training skipped"))
        with col_b:
            if st.button("Retrain (Analyst Labels)", use_container_width=True):
                with st.spinner("Training on analyst labels..."):
                    result = fetch_api("/retrain", method="POST")
                    if result and result.get("trained"):
                        m = result.get("metrics", {})
                        st.success(f"Model {result['version']} trained! AUC={m.get('auc_roc', 'N/A')}")
                        time.sleep(1)
                        st.rerun()
                    elif result:
                        st.warning(result.get("error", "Training skipped"))
    with c2:
        st.markdown("**Scoring Thresholds**")
        st.markdown(
            "| Threshold | Value | Rationale |\n"
            "|-----------|-------|-----------|\n"
            "| Review | >= 0.50 | Balances analyst workload vs missed fraud |\n"
            "| Block  | >= 0.80 | High-confidence auto-block |"
        )


def render_metrics_trend():
    """Render metric trend chart from snapshots."""
    st.markdown("**Model Performance Over Time**")
    snapshots = fetch_api("/metric-snapshots?limit=20")
    if not snapshots:
        st.info("No training snapshots yet.")
        return
    rows = [{"Version": s.get("model_version", "?"),
             "Precision": s.get("precision", 0), "Recall": s.get("recall", 0),
             "F1": s.get("f1", 0), "AUC-ROC": s.get("auc_roc", 0)}
            for s in snapshots]
    df = pd.DataFrame(rows)
    if not df.empty:
        st.line_chart(df.set_index("Version")[["Precision", "Recall", "F1", "AUC-ROC"]], height=250)
    latest = snapshots[-1] if snapshots else {}
    importance = latest.get("feature_importance", {})
    if importance:
        st.markdown("**Top Feature Importances**")
        # Filter out NaN/Inf values before charting
        clean = {k: v for k, v in importance.items()
                 if isinstance(v, (int, float)) and not (v != v) and abs(v) != float("inf")}
        if clean:
            imp_df = pd.DataFrame(sorted(clean.items(), key=lambda x: -x[1])[:8],
                                  columns=["Feature", "Importance"])
            st.bar_chart(imp_df.set_index("Feature"), height=200)


def _label_case(case_id: str, decision: str):
    """Submit label for a case."""
    result = fetch_api(f"/cases/{case_id}/label", method="POST",
                       json_data={"decision": decision, "labeled_by": "demo_analyst"})
    if result:
        st.success(f"Labeled as **{decision}**")
        time.sleep(0.5)
        st.rerun()


def render_classic_dashboard():
    """The original tabbed dashboard view."""
    st.markdown(CLASSIC_CSS, unsafe_allow_html=True)
    metrics = render_header()
    render_autonomy_loop(metrics)
    render_metrics(metrics)
    st.divider()
    tab_stream, tab_cases, tab_patterns, tab_model = st.tabs([
        "Live Stream", "Cases", "Patterns", "Model & Learning",
    ])
    with tab_stream:
        render_live_stream()
    with tab_cases:
        render_cases()
    with tab_patterns:
        render_patterns()
    with tab_model:
        render_model_panel()
        st.divider()
        render_metrics_trend()


# =============================================================================
# MAIN
# =============================================================================
def main():
    with st.sidebar:
        st.markdown("### Orbital Greenhouse")
        view = st.radio("View", ["Orbital Greenhouse", "Classic Dashboard"],
                        index=0, label_visibility="collapsed")
        st.divider()
        st.markdown(f"**Backend:** `{API_URL}`")
        try:
            resp = httpx.get(f"{API_URL}/health", timeout=2)
            st.success("Backend connected") if resp.status_code == 200 else st.error("Backend error")
        except Exception:
            st.error("Backend offline")
        st.divider()
        if view == "Classic Dashboard":
            auto_refresh = st.toggle("Auto-refresh (5s)", value=False)
        else:
            auto_refresh = False
        st.caption("Drishpex 2026")

    if view == "Orbital Greenhouse":
        render_orbital_greenhouse()
    else:
        render_classic_dashboard()
        if auto_refresh:
            time.sleep(5)
            st.rerun()


if __name__ == "__main__":
    main()
