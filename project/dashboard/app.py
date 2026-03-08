"""
PROMPT-OPS Dashboard
====================

A multi-page Streamlit app that visualises the entire closed-loop system.

Pages:
  1. Dashboard Overview  — Hero metrics, requests by model, recent activity
  2. Model Monitoring    — Per-model stats, latency analysis, anomaly detection
  3. Prompt Management   — Create / view / optimise prompt versions
  4. Quality Evaluations — LLM-as-Judge score distributions & breakdowns
  5. Temperature Experiments — Quality & consistency vs temperature charts
  6. Cost Routing        — Tier distribution, savings, routing log
  7. Alerts & Anomalies  — Active / resolved alerts
  8. Settings            — Threshold config, DB management, system info

Usage:
    streamlit run dashboard/app.py
"""

import os
import sys
<<<<<<< HEAD
import time

=======
import json
import urllib.request
>>>>>>> 5edcce0d2c7c8aae652a9ab458063df896f7212f
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ── path setup ──────────────────────────────────────────────
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from config import settings, FREE_MODELS, MODEL_TIERS
from src.database import (
    db_manager, init_database,
    TelemetryLog, PromptVersion, Alert,
    EvaluationResult, TemperatureExperiment, CostRoutingLog,
)
from src.monitoring.monitor import ModelMonitor
from src.optimization.optimizer import PromptManager, PromptOptimizer, OptimizationGoal

monitor = ModelMonitor()
prompt_manager = PromptManager()

# ── page config ─────────────────────────────────────────────
st.set_page_config(
<<<<<<< HEAD
    page_title="PROMPT-OPS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── global styles ───────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 0; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #667eea11 0%, #764ba211 100%);
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 12px 16px;
    }
    [data-testid="stMetric"] label { font-size: 0.8rem !important; }
    .section-hdr {
        font-size: 1.2rem;
        font-weight: 700;
        margin: 1.5rem 0 0.5rem 0;
        padding-bottom: 4px;
        border-bottom: 2px solid #667eea;
        display: inline-block;
=======
    page_title="Telemetry-Aware Model Monitoring",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Modern Custom CSS
st.markdown("""
<style>
    /* Hide the sidebar expand button for a cleaner app experience */
    [data-testid="collapsedControl"] {
        display: none;
>>>>>>> 5edcce0d2c7c8aae652a9ab458063df896f7212f
    }

    /* Global UI Tweaks */
    .block-container {
        padding-top: 2rem !important;
        max-width: 1400px;
    }
    
    /* Metric Cards */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        text-color: #000000;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #f0f2f6;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    
    /* Alert Boxes */
    .alert-high {
        background-color: #fff0f0;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
        margin: 10px 0;
        color: #bd1515;
        font-weight: 500;
    }
    .alert-medium {
        background-color: #fff8e6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ffa421;
        margin: 10px 0;
        color: #b56b00;
        font-weight: 500;
    }
    
    /* Charts Backgrounds */
    .js-plotly-plot {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        border: 1px solid #f0f2f6;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #1f2937;
        font-family: inherit;
        font-weight: 700 !important;
    }
    
    /* Style radio to look like pills when horizontal fallback */
    div[data-testid="stRadio"] > div {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }
    div[data-testid="stRadio"] > div > label {
        background-color: #ffffff;
        padding: 10px 20px;
        border-radius: 12px;
        border: 1px solid #e0e6ed;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
        cursor: pointer;
        transition: all 0.2s ease-in-out;
    }
    div[data-testid="stRadio"] > div > label:hover {
        border-color: #b0c4de;
        background-color: #f8fafc;
        transform: translateY(-1px);
    }
    div[data-testid="stRadio"] > div > label > div:first-child {
        display: none;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
</style>
""", unsafe_allow_html=True)

# Load Currency Map
currency_map_path = os.path.join(os.path.dirname(__file__), "currency_map.json")
try:
    with open(currency_map_path, "r", encoding="utf-8") as f:
        CURRENCY_MAP = json.load(f)
except Exception:
    CURRENCY_MAP = {}


# ── helpers ─────────────────────────────────────────────────
def _init():
    if "db_ok" not in st.session_state:
        init_database()
<<<<<<< HEAD
        st.session_state.db_ok = True


def _hdr(text: str):
    st.markdown(f'<div class="section-hdr">{text}</div>', unsafe_allow_html=True)
=======
        st.session_state.db_initialized = True
    if 'currency' not in st.session_state:
        st.session_state.currency = 'USD'
    if 'exchange_rate' not in st.session_state:
        st.session_state.exchange_rate = 1.0

@st.cache_data(ttl=3600)
def fetch_exchange_rates():
    """Fetch live exchange rates from public API."""
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get("rates", {"USD": 1.0})
    except Exception:
        return {"USD": 1.0}


def render_header_and_nav():
    """Render the top header, currency selection, and modern navigation."""
    col_logo, col_title, col_gap, col_currency = st.columns([0.3, 3.5, 2, 2.2])
    
    with col_logo:
        st.markdown("<h1 style='margin:0; padding:0; font-size:2.5rem;'>🤖</h1>", unsafe_allow_html=True)
        
    with col_title:
        st.markdown("<h2 style='margin:0; padding:0; line-height:2.5rem;'>Telemetry-Aware Monitoring</h2>", unsafe_allow_html=True)
        
    with col_currency:
        rates = fetch_exchange_rates()
        currencies = list(rates.keys())
        if not currencies:
            currencies = ["USD"]
            
        try:
            default_idx = currencies.index(st.session_state.currency)
        except ValueError:
            default_idx = 0
            
        def format_currency(curr_code):
            return CURRENCY_MAP.get(curr_code, f"{curr_code}")

        selected_currency = st.selectbox(
            "Currency",
            currencies,
            index=default_idx,
            format_func=format_currency,
            label_visibility="collapsed"
        )
        
        if selected_currency != st.session_state.currency:
            st.session_state.currency = selected_currency
            st.session_state.exchange_rate = rates.get(selected_currency, 1.0)
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    pages = [
        "📊 Dashboard Overview",
        "📈 Model Monitoring",
        "🔄 Prompt Management",
        "🚨 Alerts & Anomalies",
        "⚙️ Settings"
    ]
    
    if hasattr(st, "segmented_control"):
        page = st.segmented_control("Navigation", pages, default=pages[0], label_visibility="collapsed")
    elif hasattr(st, "pills"):
        page = st.pills("Navigation", pages, default=pages[0], label_visibility="collapsed")
    else:
        page = st.radio("Navigation", pages, horizontal=True, label_visibility="collapsed")
    
    if not page:
        page = pages[0]
        
    st.markdown("---")
    return page
>>>>>>> 5edcce0d2c7c8aae652a9ab458063df896f7212f


def _rows_to_dicts(rows):
    """Convert SQLAlchemy ORM rows to plain dicts so they survive session close."""
    from sqlalchemy import inspect as sa_inspect
    result = []
    for obj in rows:
        mapper = sa_inspect(obj.__class__)
        d = {}
        for col in mapper.column_attrs:
            d[col.key] = getattr(obj, col.key)
        result.append(d)
    return result


# ═══════════════════════════════════════════════════════════
#  PAGE: DASHBOARD OVERVIEW
# ═══════════════════════════════════════════════════════════
def page_dashboard_overview():
    st.markdown("## ⚡ PROMPT-OPS — Dashboard Overview")
    st.caption("Closed-loop telemetry-aware prompt optimization")

    with db_manager.session_scope() as s:
        total_reqs = s.query(TelemetryLog).count()
        total_evals = s.query(EvaluationResult).count()
        active_alerts = s.query(Alert).filter(Alert.is_resolved == False).count()

        avg_quality = None
        if total_evals > 0:
            from sqlalchemy import func
            avg_quality = s.query(func.avg(EvaluationResult.composite_score)).scalar()

        prompt_count = s.query(PromptVersion).filter(PromptVersion.is_active == True).count()
        experiment_count = s.query(TemperatureExperiment).filter(
            TemperatureExperiment.status == "completed"
        ).count()
        routing_count = s.query(CostRoutingLog).count()

    # Hero metrics
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Requests", f"{total_reqs:,}")
    c2.metric("Avg Quality", f"{avg_quality:.2f}" if avg_quality else "—")
    c3.metric("Evaluations", f"{total_evals:,}")
    c4.metric("Active Prompts", prompt_count)
    c5.metric("Temp Experiments", experiment_count)
    c6.metric("Routing Decisions", routing_count)

    if total_reqs == 0:
        st.info(
            "👋 **No data yet!** Run `python run.py` in your terminal to feed "
            "the system with real LLM calls, then come back here."
        )
        return
<<<<<<< HEAD

=======
    
    # Key metrics
    total_requests = sum(m.get("total_requests", 0) for m in models_summary)
    total_cost_usd = sum(m.get("total_cost_usd", 0) for m in models_summary)
    total_cost = total_cost_usd * st.session_state.exchange_rate
    avg_latency = sum(m.get("avg_latency_ms", 0) for m in models_summary) / len(models_summary) if models_summary else 0
    avg_error_rate = sum(m.get("error_rate", 0) for m in models_summary) / len(models_summary) if models_summary else 0
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Requests",
            value=f"{total_requests:,}",
            delta=None
        )
    
    with col2:
        st.metric(
            label="Total Cost",
            value=f"{st.session_state.currency} {total_cost:.4f}",
            delta=None
        )
    
    with col3:
        st.metric(
            label="Avg Latency",
            value=f"{avg_latency:.0f}ms",
            delta=None
        )
    
    with col4:
        st.metric(
            label="Error Rate",
            value=f"{avg_error_rate:.2%}",
            delta=None
        )
    
>>>>>>> 5edcce0d2c7c8aae652a9ab458063df896f7212f
    st.markdown("---")

    # Models summary chart
    summaries = monitor.get_all_models_summary(time_window_hours=24)
    if summaries:
        col1, col2 = st.columns(2)
        with col1:
            _hdr("📊 Requests by Model")
            df = pd.DataFrame([
                {"Model": m["model_name"], "Requests": m["total_requests"]}
                for m in summaries
            ])
<<<<<<< HEAD
            fig = px.bar(df, x="Model", y="Requests", color="Requests",
                         color_continuous_scale="Blues")
            fig.update_layout(showlegend=False, height=300, margin=dict(t=10, b=10))
            st.plotly_chart(fig, width='stretch')

        with col2:
            _hdr("💰 Cost by Model")
            df = pd.DataFrame([
                {"Model": m["model_name"], "Cost": m.get("total_cost_usd", 0)}
                for m in summaries
            ])
            fig = px.pie(df, names="Model", values="Cost", hole=0.4)
            fig.update_layout(height=300, margin=dict(t=10, b=10))
            st.plotly_chart(fig, width='stretch')

=======
            fig = px.bar(
                df_requests,
                x="Model",
                y="Requests",
                color="Requests",
                color_continuous_scale="Blues"
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💰 Cost by Model")
        if models_summary:
            df_cost = pd.DataFrame([
                {"Model": m["model_name"], f"Cost ({st.session_state.currency})": m.get("total_cost_usd", 0) * st.session_state.exchange_rate}
                for m in models_summary
            ])
            fig = px.pie(
                df_cost,
                names="Model",
                values=f"Cost ({st.session_state.currency})",
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)
    
>>>>>>> 5edcce0d2c7c8aae652a9ab458063df896f7212f
    # Recent activity
    st.markdown("---")
    _hdr("📋 Recent Activity")
    with db_manager.session_scope() as s:
        recent = _rows_to_dicts(
            s.query(TelemetryLog).order_by(
                TelemetryLog.timestamp.desc()
            ).limit(20).all()
        )

    if recent:
        st.dataframe(
            pd.DataFrame([
                {
<<<<<<< HEAD
                    "Time": r["timestamp"].strftime("%H:%M:%S") if r["timestamp"] else "—",
                    "Model": r["model_name"] or "—",
                    "Prompt": r["prompt_id"] or "—",
                    "Latency": f"{r['latency_ms']:.0f} ms" if r["latency_ms"] else "—",
                    "Tokens": r["total_tokens"] or "—",
                    "Quality": f"{r['quality_score']:.2f}" if r["quality_score"] else "—",
                    "Status": "❌" if r["is_error"] else "✅",
=======
                    "Time": log.timestamp.strftime("%H:%M:%S"),
                    "Model": log.model_name,
                    "Latency (ms)": f"{log.latency_ms:.0f}" if log.latency_ms else "N/A",
                    "Tokens": log.total_tokens or "N/A",
                    "Cost": f"{st.session_state.currency} {log.cost_usd * st.session_state.exchange_rate:.6f}" if log.cost_usd else "N/A",
                    "Status": "❌ Error" if log.is_error else "✅ Success"
>>>>>>> 5edcce0d2c7c8aae652a9ab458063df896f7212f
                }
                for r in recent
            ]),
            width="stretch", hide_index=True,
        )


# ═══════════════════════════════════════════════════════════
#  PAGE: MODEL MONITORING
# ═══════════════════════════════════════════════════════════
def page_model_monitoring():
    st.markdown("## 📈 Model Monitoring")

    with db_manager.session_scope() as s:
        models = [m[0] for m in s.query(TelemetryLog.model_name).distinct().all()]

    if not models:
        st.warning("No models found. Run the pipeline first.")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        selected_model = st.selectbox("Select Model", models)
    with col2:
        time_window = st.selectbox(
            "Time Window",
            options=[1, 6, 24, 168],
            format_func=lambda x: f"{x}h" if x < 24 else f"{x // 24}d",
            index=2,
        )

    stats = monitor.get_model_stats(selected_model, time_window_hours=time_window)

    if stats.get("total_requests", 0) == 0:
        st.info(f"No data for {selected_model} in this window.")
        return
<<<<<<< HEAD

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Requests", f"{stats['total_requests']:,}")
    c2.metric("Success Rate", f"{stats['success_rate']:.1%}")
    c3.metric("Avg Latency", f"{stats['avg_latency_ms']:.0f} ms" if stats.get("avg_latency_ms") else "—")
    c4.metric("Total Cost", f"${stats['total_cost_usd']:.4f}" if stats.get("total_cost_usd") else "$0")

    st.markdown("---")
=======
    
    # Display metrics
    st.subheader("📊 Performance Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Requests",
            f"{stats['total_requests']:,}",
            help="Total number of API calls"
        )
    
    with col2:
        st.metric(
            "Success Rate",
            f"{stats['success_rate']:.1%}",
            delta=f"{stats['success_rate']-0.95:.1%}",
            help="Percentage of successful requests"
        )
    
    with col3:
        st.metric(
            "Avg Latency",
            f"{stats['avg_latency_ms']:.0f}ms",
            help="Average response time"
        )
    
    with col4:
        st.metric(
            "Total Cost",
            f"{st.session_state.currency} {stats['total_cost_usd'] * st.session_state.exchange_rate:.4f}",
            help=f"Total cost in {st.session_state.currency}"
        )
    
    # Latency distribution
    st.subheader("⏱️ Latency Analysis")
    
>>>>>>> 5edcce0d2c7c8aae652a9ab458063df896f7212f
    col1, col2 = st.columns(2)
    with col1:
        _hdr("⏱️ Latency Percentiles")
        latency_data = {
            "Percentile": ["P50", "P95", "P99", "Max"],
            "Latency (ms)": [
                stats.get("median_latency_ms", 0),
                stats.get("p95_latency_ms", 0),
                stats.get("p99_latency_ms", 0),
                stats.get("max_latency_ms", 0),
            ],
        }
        fig = px.bar(pd.DataFrame(latency_data), x="Percentile", y="Latency (ms)",
                     color="Latency (ms)", color_continuous_scale="Reds")
        fig.update_layout(height=300, margin=dict(t=10, b=10))
        st.plotly_chart(fig, width='stretch')

    with col2:
        _hdr("🔢 Token Usage")
        token_data = {
            "Type": ["Input Tokens", "Output Tokens"],
            "Count": [
                stats.get("total_input_tokens", 0),
                stats.get("total_output_tokens", 0),
            ],
        }
        fig = px.pie(pd.DataFrame(token_data), names="Type", values="Count",
                     hole=0.4, color_discrete_sequence=["#4CAF50", "#2196F3"])
        fig.update_layout(height=300, margin=dict(t=10, b=10))
        st.plotly_chart(fig, width='stretch')

    # Anomaly detection
    st.markdown("---")
    _hdr("🔍 Anomaly Detection")
    anomalies = monitor.detect_anomalies(selected_model, metric="latency_ms", sensitivity=2.0)
    if anomalies:
        st.warning(f"Found {len(anomalies)} anomalous requests")
        df = pd.DataFrame(anomalies)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        fig = px.scatter(df, x="timestamp", y="value", size="z_score", color="z_score",
                         hover_data=["request_id"],
                         labels={"value": "Latency (ms)", "timestamp": "Time"},
                         title="Anomalous Latency Values")
        st.plotly_chart(fig, width='stretch')
    else:
        st.success("No anomalies detected in the selected time window")


# ═══════════════════════════════════════════════════════════
#  PAGE: LIVE PLAYGROUND
# ═══════════════════════════════════════════════════════════
def page_live_playground():
    st.markdown("## 🧪 Live Playground — Before / After Optimization")
    st.caption(
        "Type any prompt. The system calls the LLM **twice**: once with naive "
        "defaults, then with the optimized settings it has learned."
    )

    with st.form("playground_form"):
        user_prompt = st.text_area(
            "Your prompt",
            value="Explain how a car engine works in 3 bullet points.",
            height=80,
        )
        col_a, col_b = st.columns(2)
        with col_a:
            before_model = st.selectbox("Before model", FREE_MODELS, index=0)
        with col_b:
            after_model = st.selectbox(
                "After model (system picks best)",
                FREE_MODELS,
                index=min(3, len(FREE_MODELS) - 1),
            )
        run_btn = st.form_submit_button("⚡ Run comparison", width='stretch')

    if run_btn and user_prompt.strip():
        from src.pipeline.orchestrator import PromptOpsPipeline
        from src.optimization.temperature_optimizer import TemperatureOptimizer

        pipe = PromptOpsPipeline()

        col_before, col_after = st.columns(2)

        # BEFORE
        with col_before:
            st.markdown("#### 🔴 Before optimization")
            with st.spinner("Calling LLM with defaults…"):
                resp_before = pipe.run(
                    user_input=user_prompt,
                    model=before_model,
                    temperature=0.7,
                    enable_cost_routing=False,
                    enable_evaluation=True,
                    ab_testing=False,
                    tags=["playground", "before"],
                )
            st.markdown(f"**Model:** `{resp_before.model}`")
            st.markdown(f"**Temperature:** 0.7 (default)")
            st.markdown(f"**Latency:** {resp_before.latency_ms:.0f} ms")
            if resp_before.quality_score is not None:
                st.markdown(f"**Quality:** {resp_before.quality_score:.2f}")
            st.text_area("Response", resp_before.content, height=200, key="before_resp", disabled=True)

            if resp_before.evaluation_details:
                d = resp_before.evaluation_details
                fig = go.Figure(go.Scatterpolar(
                    r=[d.get("relevance", 0), d.get("accuracy", 0),
                       d.get("completeness", 0), d.get("format_compliance", 0),
                       d.get("safety", 0)],
                    theta=["Relevance", "Accuracy", "Completeness", "Format", "Safety"],
                    fill="toself", fillcolor="rgba(255,107,107,0.2)",
                    line_color="#ff6b6b", name="Before",
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                    showlegend=False, height=260, margin=dict(t=30, b=20, l=40, r=40),
                )
                st.plotly_chart(fig, width='stretch')

        # AFTER
        with col_after:
            st.markdown("#### 🟢 After optimization")
            temp_opt = TemperatureOptimizer()
            best_temp = temp_opt.get_recommended_temperature("default", after_model)
            use_temp = best_temp if best_temp is not None else 0.4

            with st.spinner("Calling LLM with optimized settings…"):
                resp_after = pipe.run(
                    user_input=user_prompt,
                    model=after_model,
                    temperature=use_temp,
                    enable_cost_routing=False,
                    enable_evaluation=True,
                    ab_testing=False,
                    tags=["playground", "after"],
                )
            st.markdown(f"**Model:** `{resp_after.model}`")
            st.markdown(f"**Temperature:** {use_temp} {'(learned)' if best_temp is not None else '(tuned default)'}")
            st.markdown(f"**Latency:** {resp_after.latency_ms:.0f} ms")
            if resp_after.quality_score is not None:
                st.markdown(f"**Quality:** {resp_after.quality_score:.2f}")
            st.text_area("Response", resp_after.content, height=200, key="after_resp", disabled=True)

            if resp_after.evaluation_details:
                d = resp_after.evaluation_details
                fig = go.Figure(go.Scatterpolar(
                    r=[d.get("relevance", 0), d.get("accuracy", 0),
                       d.get("completeness", 0), d.get("format_compliance", 0),
                       d.get("safety", 0)],
                    theta=["Relevance", "Accuracy", "Completeness", "Format", "Safety"],
                    fill="toself", fillcolor="rgba(81,207,102,0.2)",
                    line_color="#51cf66", name="After",
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                    showlegend=False, height=260, margin=dict(t=30, b=20, l=40, r=40),
                )
                st.plotly_chart(fig, width='stretch')

        # Delta summary
        if resp_before.quality_score and resp_after.quality_score:
            delta = resp_after.quality_score - resp_before.quality_score
            sign = "+" if delta >= 0 else ""
            color = "#51cf66" if delta >= 0 else "#ff6b6b"
            st.markdown(
                f"<div style='text-align:center; margin:12px 0; font-size:1.1rem;'>"
                f"Quality change: <span style='color:{color}; font-weight:700;'>"
                f"{sign}{delta:.2f}</span> &nbsp;|&nbsp; "
                f"Latency change: <span style='font-weight:600;'>"
                f"{resp_after.latency_ms - resp_before.latency_ms:+.0f} ms</span>"
                f"</div>",
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════════
#  PAGE: PROMPT MANAGEMENT
# ═══════════════════════════════════════════════════════════
def page_prompt_management():
    st.markdown("## 🔄 Prompt Management")

    tab1, tab2, tab3 = st.tabs(["📝 Create Prompt", "📊 View / A-B Test", "🚀 Optimize"])

    # ── Create ──────────────────────────────────────────────
    with tab1:
        with st.form("create_prompt_form"):
            prompt_id = st.text_input("Prompt ID", help="e.g. 'summarize'")
            name = st.text_input("Name")
            template = st.text_area("Template", height=150, help="Use {input} as placeholder")
            description = st.text_area("Description (optional)", height=80)
            c1, c2 = st.columns(2)
            with c1:
                is_default = st.checkbox("Set as default version")
                ab_test_group = st.text_input("A/B Test Group", help="e.g. control, variant_a")
            with c2:
                traffic_weight = st.number_input("Traffic Weight", 0.0, 1.0, 1.0, 0.1)
            submitted = st.form_submit_button("Create Prompt Version")

        if submitted:
            if prompt_id and name and template:
                try:
                    pv = prompt_manager.create_prompt_version(
                        prompt_id=prompt_id, template=template, name=name,
                        description=description, is_default=is_default,
                        ab_test_group=ab_test_group or None,
                        traffic_weight=traffic_weight,
                    )
                    st.success(f"✅ Created {prompt_id} v{pv.version}")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Please fill in Prompt ID, Name, and Template.")

    # ── View / A-B test ─────────────────────────────────────
    with tab2:
<<<<<<< HEAD
        with db_manager.session_scope() as s:
            prompt_ids = [r[0] for r in s.query(PromptVersion.prompt_id).distinct().all()]

        if not prompt_ids:
            st.info("No prompts yet — create one in the Create tab.")
=======
        st.subheader("View Prompt Versions")
        
        with db_manager.session_scope() as session:
            prompts = session.query(PromptVersion.prompt_id).distinct().all()
            prompt_ids = [p[0] for p in prompts]
        
        if prompt_ids:
            selected_prompt = st.selectbox("Select Prompt", prompt_ids)
            
            versions = prompt_manager.get_prompt_versions(selected_prompt)
            
            if versions:
                for version in versions:
                    with st.expander(
                        f"Version {version.version} - {version.name} "
                        f"{'✅ (Active)' if version.is_active else '❌ (Inactive)'}"
                    ):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"**Template:**")
                            st.code(version.template, language=None)
                            
                            if version.description:
                                st.markdown(f"**Description:** {version.description}")
                        
                        with col2:
                            st.markdown("**Metrics:**")
                            st.metric("Total Calls", version.total_calls or 0)
                            if version.avg_latency_ms:
                                st.metric("Avg Latency", f"{version.avg_latency_ms:.0f}ms")
                            if version.avg_cost_usd:
                                st.metric("Avg Cost", f"{st.session_state.currency} {version.avg_cost_usd * st.session_state.exchange_rate:.6f}")
                            if version.avg_quality_score:
                                st.metric("Avg Quality", f"{version.avg_quality_score:.2f}")
                        
                        if version.is_active:
                            if st.button(f"Deactivate v{version.version}"):
                                prompt_manager.deactivate_version(selected_prompt, version.version)
                                st.rerun()
>>>>>>> 5edcce0d2c7c8aae652a9ab458063df896f7212f
        else:
            for pid in prompt_ids:
                versions = prompt_manager.get_prompt_versions(pid, active_only=True)
                if not versions:
                    continue
                with st.expander(
                    f"**{pid}** — {len(versions)} active version(s)", expanded=len(prompt_ids) <= 3
                ):
                    rows = []
                    for v in versions:
                        rows.append({
                            "Version": f"v{v.version}",
                            "Name": v.name,
                            "Calls": v.total_calls or 0,
                            "Avg Quality": f"{v.avg_quality_score:.2f}" if v.avg_quality_score else "—",
                            "Avg Latency": f"{v.avg_latency_ms:.0f} ms" if v.avg_latency_ms else "—",
                            "Traffic %": f"{v.traffic_weight * 100:.0f}%",
                            "Default": "✅" if v.is_default else "",
                        })
                    st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

                    q_data = [
                        {"Version": f"v{v.version} — {v.name}", "Quality": v.avg_quality_score or 0}
                        for v in versions
                    ]
                    if any(d["Quality"] > 0 for d in q_data):
                        fig = px.bar(pd.DataFrame(q_data), x="Version", y="Quality",
                                     color="Quality", color_continuous_scale="Greens",
                                     range_y=[0, 1], height=250)
                        fig.update_layout(margin=dict(t=10, b=10))
                        st.plotly_chart(fig, width='stretch')

    # ── Optimize ────────────────────────────────────────────
    with tab3:
        with db_manager.session_scope() as s:
            prompt_ids_opt = [r[0] for r in s.query(PromptVersion.prompt_id).distinct().all()]

        if not prompt_ids_opt:
            st.info("No prompts available for optimization.")
        else:
            opt_pid = st.selectbox("Select Prompt to Optimize", prompt_ids_opt, key="opt_pid")
            opt_goal = st.selectbox(
                "Goal", [g.value for g in OptimizationGoal],
                format_func=lambda x: x.title(),
            )
            if st.button("🚀 Run Optimization"):
                with st.spinner("Analyzing…"):
                    try:
                        optimizer = PromptOptimizer()
                        result = optimizer.run_optimization(opt_pid, OptimizationGoal(opt_goal))
                        if result["status"] == "success":
                            rec = result["recommendation"]
                            st.success(
                                f"✅ Best = v{rec['recommended_version']} "
                                f"({rec['version_name']}) score={rec['score']:.3f}"
                            )
                            st.json(rec["metrics"])
                        else:
                            st.warning(result.get("message", "Need more data"))
                    except Exception as e:
                        st.error(f"Optimization failed: {e}")


# ═══════════════════════════════════════════════════════════
#  PAGE: QUALITY EVALUATIONS
# ═══════════════════════════════════════════════════════════
def page_quality_evaluations():
    st.markdown("## ⭐ Quality Evaluations (LLM-as-Judge)")

    with db_manager.session_scope() as s:
        evals = _rows_to_dicts(
            s.query(EvaluationResult).order_by(
                EvaluationResult.evaluated_at.desc()
            ).limit(200).all()
        )

    if not evals:
        st.info("No evaluations yet. Run the pipeline with `enable_evaluation=True`.")
        return

    scores = [e["composite_score"] for e in evals if e["composite_score"]]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Evaluations", len(evals))
    c2.metric("Avg Quality", f"{sum(scores) / len(scores):.2f}" if scores else "—")
    c3.metric("High Quality (≥0.7)", f"{sum(1 for s in scores if s >= 0.7)}/{len(scores)}")
    judge_costs = [e["judge_cost_usd"] for e in evals if e["judge_cost_usd"]]
    c4.metric("Eval Cost", f"${sum(judge_costs):.4f}")

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        _hdr("Score Distribution")
        if scores:
            fig = px.histogram(
                pd.DataFrame({"Quality Score": scores}),
                x="Quality Score", nbins=20,
                color_discrete_sequence=["#667eea"],
            )
            fig.update_layout(height=300, margin=dict(t=10, b=10))
            st.plotly_chart(fig, width='stretch')

    with col2:
        _hdr("Average by Dimension")
        dims = {
            "Relevance": [e["relevance"] for e in evals if e["relevance"] is not None],
            "Accuracy": [e["accuracy"] for e in evals if e["accuracy"] is not None],
            "Completeness": [e["completeness"] for e in evals if e["completeness"] is not None],
            "Format": [e["format_compliance"] for e in evals if e["format_compliance"] is not None],
            "Safety": [e["safety"] for e in evals if e["safety"] is not None],
        }
        avgs = {k: sum(v) / len(v) if v else 0 for k, v in dims.items()}
        fig = px.bar(
            pd.DataFrame({"Dimension": avgs.keys(), "Avg Score": avgs.values()}),
            x="Dimension", y="Avg Score",
            color="Avg Score", color_continuous_scale="Greens",
            range_y=[0, 1],
        )
        fig.update_layout(height=300, margin=dict(t=10, b=10))
        st.plotly_chart(fig, width='stretch')

    # Table
    _hdr("Recent Evaluations")
    st.dataframe(
        pd.DataFrame([
            {
                "Time": e["evaluated_at"].strftime("%H:%M:%S") if e["evaluated_at"] else "—",
                "Model": e["model_name"] or "—",
                "Prompt": e["prompt_id"] or "—",
                "Quality": f"{e['composite_score']:.2f}" if e["composite_score"] else "—",
                "Relevance": f"{e['relevance']:.2f}" if e["relevance"] else "—",
                "Accuracy": f"{e['accuracy']:.2f}" if e["accuracy"] else "—",
                "Judge": e["judge_model"] or "—",
            }
            for e in evals[:20]
        ]),
        width="stretch", hide_index=True,
    )


# ═══════════════════════════════════════════════════════════
#  PAGE: TEMPERATURE EXPERIMENTS
# ═══════════════════════════════════════════════════════════
def page_temperature_experiments():
    st.markdown("## 🌡️ Temperature Optimization")
    st.caption(
        "Controlled experiments across the temperature range to find "
        "the best quality × consistency for each prompt."
    )

    with db_manager.session_scope() as s:
        experiments = _rows_to_dicts(
            s.query(TemperatureExperiment).filter(
                TemperatureExperiment.status == "completed"
            ).order_by(TemperatureExperiment.completed_at.desc()).limit(10).all()
        )

    if not experiments:
        st.info("No experiments yet. Run `temperature_optimizer.run_experiment()`.")
        return

    for exp in experiments:
        with st.expander(
            f"**{exp['prompt_id']}** on `{exp['model_name']}` → best temp = "
            f"{exp['best_temperature']:.1f} (quality {exp['best_quality_score']:.2f})",
            expanded=True,
        ):
            c1, c2, c3 = st.columns(3)
            c1.metric("Best Temperature", f"{exp['best_temperature']:.1f}")
            c2.metric("Quality Score", f"{exp['best_quality_score']:.2f}")
            c3.metric("Trials Run", exp["total_trials"] or 0)

            if exp["results_json"]:
                temps = sorted(exp["results_json"].keys(), key=lambda x: float(x))
                df = pd.DataFrame([
                    {
                        "Temperature": float(t),
                        "Quality": exp["results_json"][t].get("avg_quality", 0),
                        "Consistency": exp["results_json"][t].get("consistency", 0),
                    }
                    for t in temps
                ])
                fig = px.line(
                    df, x="Temperature", y=["Quality", "Consistency"],
                    markers=True, height=300,
                    color_discrete_sequence=["#667eea", "#ffa94d"],
                )
                fig.update_layout(
                    title="Quality & Consistency vs Temperature",
                    margin=dict(t=40, b=20),
                )
                st.plotly_chart(fig, width='stretch')


# ═══════════════════════════════════════════════════════════
#  PAGE: COST ROUTING
# ═══════════════════════════════════════════════════════════
def page_cost_routing():
    st.markdown("## 💰 Smart Model Routing")
    st.caption(
        "The router tries the weakest (cheapest) model first. If quality is "
        "too low, it escalates. Simple questions stay on cheap models."
    )

    with db_manager.session_scope() as s:
        routes = _rows_to_dicts(
            s.query(CostRoutingLog).order_by(
                CostRoutingLog.created_at.desc()
            ).limit(100).all()
        )

    if not routes:
        st.info("No routing data yet. Use `enable_cost_routing=True` in the pipeline.")
        return

    total = len(routes)
    downgraded = sum(1 for r in routes if not r["escalated"])
    total_saved = sum(r["cost_saved_usd"] for r in routes if r["cost_saved_usd"])
    avg_quality = sum(r["quality_score"] for r in routes if r["quality_score"]) / max(
        1, sum(1 for r in routes if r["quality_score"])
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Routed", total)
    c2.metric("Downgraded", f"{downgraded} ({downgraded / total * 100:.0f}%)" if total else "0")
    c3.metric("Money Saved", f"${total_saved:.4f}")
    c4.metric("Avg Quality", f"{avg_quality:.2f}")

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        _hdr("Tier Distribution")
        tier_counts = {}
        for r in routes:
            tier_counts[r["tier_used"] or "unknown"] = tier_counts.get(r["tier_used"] or "unknown", 0) + 1
        fig = px.pie(
            pd.DataFrame({"Tier": tier_counts.keys(), "Count": tier_counts.values()}),
            names="Tier", values="Count", hole=0.45, height=300,
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig, width='stretch')

    with col2:
        _hdr("Actual Model Used")
        model_counts = {}
        for r in routes:
            model_counts[r["routed_model"] or "?"] = model_counts.get(r["routed_model"] or "?", 0) + 1
        fig = px.bar(
            pd.DataFrame({"Model": model_counts.keys(), "Count": model_counts.values()}),
            x="Model", y="Count", color="Count",
            color_continuous_scale="Blues", height=300,
        )
        fig.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig, width='stretch')

    _hdr("Routing Log")
    st.dataframe(
        pd.DataFrame([
            {
                "Time": r["created_at"].strftime("%H:%M:%S") if r["created_at"] else "—",
                "Requested": r["original_model"] or "—",
                "Routed To": r["routed_model"] or "—",
                "Tier": r["tier_used"] or "—",
                "Quality": f"{r['quality_score']:.2f}" if r["quality_score"] else "—",
                "Escalated": "⬆️ Yes" if r["escalated"] else "No",
            }
            for r in routes[:15]
        ]),
        width="stretch", hide_index=True,
    )


# ═══════════════════════════════════════════════════════════
#  PAGE: ALERTS & ANOMALIES
# ═══════════════════════════════════════════════════════════
def page_alerts():
    st.markdown("## 🚨 Alerts & Anomalies")

    active_alerts = monitor.get_active_alerts()
    if active_alerts:
        st.subheader(f"⚠️ Active Alerts ({len(active_alerts)})")
        for alert in active_alerts:
            severity_emoji = {"low": "ℹ️", "medium": "⚠️", "high": "🚨", "critical": "🔴"}
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(
                    f"{severity_emoji.get(alert.severity, '⚠️')} "
                    f"**{alert.alert_type.replace('_', ' ').title()}**"
                )
                st.markdown(alert.message)
                st.caption(f"Triggered: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}")
            with c2:
                if alert.model_name:
                    st.markdown(f"**Model:** {alert.model_name}")
            with c3:
                if st.button("Resolve", key=f"resolve_{alert.id}"):
                    monitor.resolve_alert(alert.id)
                    st.rerun()
            st.markdown("---")
    else:
        st.success("✅ No active alerts")

    # Resolved
    st.subheader("📋 Recent Resolved Alerts")
    with db_manager.session_scope() as s:
        resolved = _rows_to_dicts(
            s.query(Alert).filter(
                Alert.is_resolved == True
            ).order_by(Alert.resolved_at.desc()).limit(10).all()
        )

    if resolved:
        st.dataframe(
            pd.DataFrame([
                {
                    "Type": a["alert_type"],
                    "Severity": a["severity"],
                    "Model": a["model_name"] or "—",
                    "Triggered": a["triggered_at"].strftime("%Y-%m-%d %H:%M") if a["triggered_at"] else "—",
                    "Resolved": a["resolved_at"].strftime("%Y-%m-%d %H:%M") if a["resolved_at"] else "—",
                }
                for a in resolved
            ]),
            width="stretch", hide_index=True,
        )
    else:
        st.info("No resolved alerts")


<<<<<<< HEAD
# ═══════════════════════════════════════════════════════════
#  PAGE: SETTINGS
# ═══════════════════════════════════════════════════════════
def page_settings():
    st.markdown("## ⚙️ Settings")

    _hdr("Threshold Configuration")
    c1, c2 = st.columns(2)
    with c1:
        st.number_input("Latency Threshold (ms)", value=int(settings.latency_threshold_ms), step=100)
        st.number_input("Cost Threshold (USD)", value=settings.cost_threshold_usd, step=1.0)
    with c2:
        st.number_input("Error Rate Threshold", value=settings.error_rate_threshold,
                        min_value=0.0, max_value=1.0, step=0.01, format="%.2f")

=======
def settings_page():
    """Render the settings page."""
    st.title("⚙️ Settings")
    
    st.subheader("Threshold Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.number_input(
            "Maximum Latency (ms)",
            value=2000,
            step=100,
            help="Alert when average latency exceeds this maximum latency threshold"
        )
        
        st.number_input(
            f"Cost Threshold ({st.session_state.currency})",
            value=10.0 * st.session_state.exchange_rate,
            step=1.0 * st.session_state.exchange_rate,
            help=f"Alert when total cost exceeds this value in {st.session_state.currency}"
        )
    
    with col2:
        st.number_input(
            "Error Rate Threshold",
            value=0.05,
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            format="%.2f",
            help="Alert when error rate exceeds this percentage"
        )
    
>>>>>>> 5edcce0d2c7c8aae652a9ab458063df896f7212f
    st.markdown("---")
    _hdr("Database Management")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Aggregate Metrics"):
            with st.spinner("Aggregating…"):
                monitor.aggregate_hourly_metrics(hours_back=24)
                st.success("✅ Metrics aggregated")
    with c2:
        if st.button("📊 Export Data"):
            st.warning("Export feature coming soon")

    st.markdown("---")
<<<<<<< HEAD
    _hdr("System Information")
    with db_manager.session_scope() as s:
        c1, c2, c3 = st.columns(3)
        c1.metric("Telemetry Logs", f"{s.query(TelemetryLog).count():,}")
        c2.metric("Prompt Versions", f"{s.query(PromptVersion).count():,}")
        c3.metric("Alerts", f"{s.query(Alert).count():,}")

    # ── Explainer ───────────────────────────────────────────
    st.markdown("---")
    _hdr("❓ What is this system?")
    st.markdown("""
**PROMPT-OPS** is a closed-loop optimization system for LLM applications.

Most LLM apps today are **open-loop** — you send a prompt, get a response, and hope it's good.
This system **closes the loop**: every response is automatically evaluated for quality,
and the system uses that data to pick better prompts, temperatures, and models next time.

```
Your prompt → LLM call → Response
                            ↓
                    Auto-evaluate quality (LLM-as-Judge)
                            ↓
                    Store quality + telemetry in database
                            ↓
                    System LEARNS:
                      • Which prompt version scores highest
                      • Which temperature produces best quality
                      • Which model tier is sufficient for which task
                            ↓
                    Next request uses better settings ← LOOP CLOSED
```
""")
=======
    
    st.subheader("System Information")
    
    with db_manager.session_scope() as session:
        total_logs = session.query(TelemetryLog).count()
        total_prompts = session.query(PromptVersion).count()
        total_alerts = session.query(Alert).count()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Telemetry Logs", f"{total_logs:,}")
    
    with col2:
        st.metric("Total Prompt Versions", f"{total_prompts:,}")
    
    with col3:
        st.metric("Total Alerts", f"{total_alerts:,}")
        
    st.markdown("---")
    st.subheader("ℹ️ About")
    st.info(
        "**Telemetry-Aware Model Monitoring**\n\n"
        "Real-time monitoring and optimization for LLM applications.\n\n"
        "Track performance, optimize prompts, and detect anomalies."
    )
>>>>>>> 5edcce0d2c7c8aae652a9ab458063df896f7212f


# ═══════════════════════════════════════════════════════════
#  SIDEBAR + ROUTING
# ═══════════════════════════════════════════════════════════
def main():
<<<<<<< HEAD
    _init()

    st.sidebar.title("⚡ PROMPT-OPS")

    page = st.sidebar.radio(
        "Navigate",
        [
            "📊 Dashboard Overview",
            "📈 Model Monitoring",
            "🧪 Live Playground",
            "🔄 Prompt Management",
            "⭐ Quality Evaluations",
            "🌡️ Temperature Experiments",
            "💰 Cost Routing",
            "🚨 Alerts & Anomalies",
            "⚙️ Settings",
        ],
    )

    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh data"):
        st.rerun()
    st.sidebar.caption("PROMPT-OPS v1.0 • Final Year Project 2025–26")

    # Route
=======
    """Main application entry point."""
    init_session_state()
    
    # Header and navigation
    page = render_header_and_nav()
    
    # Route to appropriate page
>>>>>>> 5edcce0d2c7c8aae652a9ab458063df896f7212f
    if page == "📊 Dashboard Overview":
        page_dashboard_overview()
    elif page == "📈 Model Monitoring":
        page_model_monitoring()
    elif page == "🧪 Live Playground":
        page_live_playground()
    elif page == "🔄 Prompt Management":
        page_prompt_management()
    elif page == "⭐ Quality Evaluations":
        page_quality_evaluations()
    elif page == "🌡️ Temperature Experiments":
        page_temperature_experiments()
    elif page == "💰 Cost Routing":
        page_cost_routing()
    elif page == "🚨 Alerts & Anomalies":
        page_alerts()
    elif page == "⚙️ Settings":
        page_settings()


if __name__ == "__main__":
    main()
