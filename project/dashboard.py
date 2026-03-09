    # -*- coding: utf-8 -*-
"""
PROMPT-OPS Dashboard
====================
Comprehensive Streamlit dashboard for the PROMPT-OPS closed-loop
LLM monitoring and optimisation system.

Run:
    uv run streamlit run dashboard.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta, timezone

from config import settings
from src.database import (
    db_manager, init_database,
    TelemetryLog, PromptVersion, ModelMetrics,
    Alert, OptimizationRun, EvaluationResult,
    TemperatureExperiment, CostRoutingLog,
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PROMPT-OPS",
    page_icon=":zap:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
div[data-testid="stMetric"] {
    background: #0f0f1a;
    border: 1px solid #2a2a3d;
    border-radius: 8px;
    padding: 12px 16px;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_db():
    init_database()
    return db_manager


def load_table(model_class, hours=None):
    """Load an ORM table into a DataFrame with optional time filter."""
    db = get_db()
    with db.session_scope() as session:
        q = session.query(model_class)
        if hours:
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
            for ts_col in ("timestamp", "triggered_at", "created_at", "evaluated_at"):
                if hasattr(model_class, ts_col):
                    q = q.filter(getattr(model_class, ts_col) >= cutoff)
                    break
        rows = q.all()
        if not rows:
            return pd.DataFrame()
        cols = [c.name for c in model_class.__table__.columns]
        return pd.DataFrame([{c: getattr(r, c) for c in cols} for r in rows])


def short(name):
    """Shorten a model name like 'provider/model:tag' -> 'model:tag'."""
    if not name or not isinstance(name, str):
        return name
    return name.split("/")[-1]


def sev_icon(s):
    return {"low": "GREEN", "medium": "YELLOW", "high": "RED", "critical": "CRITICAL"}.get(
        str(s).lower(), "?"
    )


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("PROMPT-OPS")
    st.caption("Closed-Loop LLM Monitoring")
    st.divider()

    time_window = st.selectbox(
        "Time window",
        [1, 6, 24, 48, 168],
        index=2,
        format_func=lambda h: {
            1: "Last 1 h", 6: "Last 6 h", 24: "Last 24 h",
            48: "Last 48 h", 168: "Last 7 days",
        }[h],
    )

    page = st.radio(
        "Navigate",
        [
            "Overview",
            "Playground",
            "Telemetry",
            "Model Stats",
            "Prompt Versions",
            "Evaluations",
            "Cost Routing",
            "Temperature Experiments",
            "Alerts",
            "Optimisation Runs",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()

    st.caption(f"DB: `{settings.database_url.split('///')[-1]}`")
    st.caption(f"Updated: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")


# ── Cached loaders ───────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def get_telemetry(h):
    return load_table(TelemetryLog, h)

@st.cache_data(ttl=30)
def get_evaluations():
    return load_table(EvaluationResult)

@st.cache_data(ttl=30)
def get_alerts(h):
    return load_table(Alert, h)

@st.cache_data(ttl=60)
def get_prompts():
    return load_table(PromptVersion)

@st.cache_data(ttl=60)
def get_opt_runs():
    return load_table(OptimizationRun)

@st.cache_data(ttl=60)
def get_temp_experiments():
    return load_table(TemperatureExperiment)

@st.cache_data(ttl=60)
def get_cost_routing():
    return load_table(CostRoutingLog)


# ============================================================================
#  PAGE: PLAYGROUND
# ============================================================================

def page_playground():
    st.header("Live Playground")
    st.caption(
        "Run a real LLM call through the full closed-loop pipeline — "
        "telemetry, evaluation, cost routing, and A/B testing all happen automatically."
    )

    if not settings.openrouter_api_key:
        st.error(
            "**OPENROUTER_API_KEY is not set.** "
            "Add it to your `.env` file and restart the dashboard."
        )
        return

    from config import FREE_MODELS

    # ── How It Works ─────────────────────────────────────────────────────────
    with st.expander("📖 How does this playground work?", expanded=False):
        st.markdown("""
When you click **Run Pipeline**, your prompt passes through the full PROMPT-OPS closed-loop system in **6 automatic steps**:

| # | Step | What happens |
|---|------|-------------|
| 1 | **Prompt Selection** | If a Prompt ID is set, A/B testing picks the best template version |
| 2 | **Temperature Selection** | Uses optimal temperature from past experiments (or 0.7 default) |
| 3 | **LLM Call** | Sends request to OpenRouter — optionally tries cheaper models first |
| 4 | **Telemetry Recording** | Latency, tokens, cost, model, version — all logged to the database |
| 5 | **Quality Evaluation** | A judge LLM scores the response on 5 dimensions (LLM-as-Judge) |
| 6 | **Metrics Update** | Prompt version stats are updated for future A/B decisions |

**Every run improves the system** — quality scores feed back into routing and prompt selection.
        """)

    st.divider()

    # ── Step 1: Write your prompt ─────────────────────────────────────────────
    st.subheader("① Write your prompt")

    col_inp, col_cfg = st.columns([3, 2])

    with col_inp:
        user_input = st.text_area(
            "Your prompt / question",
            value="Explain what a closed-loop LLM system is and why it matters.",
            height=130,
            help="This is the raw text sent to the LLM. If you pick a Prompt ID below, it will be inserted into that template.",
        )
        system_prompt = st.text_input(
            "System prompt (optional)",
            value="You are a helpful, concise assistant.",
            help="Sets the persona/behaviour of the LLM before your prompt. Leave blank to use no system context.",
        )

    # ── Step 2: Configure the pipeline ───────────────────────────────────────
    with col_cfg:
        st.markdown("**② Configure the pipeline**")

        # Prompt ID selector — pull live versions from DB
        prompts_df = get_prompts()
        prompt_ids = (
            ["(none)"] + sorted(prompts_df["prompt_id"].dropna().unique().tolist())
            if not prompts_df.empty else ["(none)"]
        )
        sel_pid = st.selectbox(
            "Prompt ID (A/B versioning)",
            prompt_ids,
            help=(
                "Select a saved prompt template. The system will inject your input into the "
                "template and A/B-test across its versions. Leave as '(none)' to send your "
                "prompt directly with no template."
            ),
        )
        prompt_id = None if sel_pid == "(none)" else sel_pid

        # Show template preview when a prompt ID is selected
        if prompt_id and not prompts_df.empty:
            versions_for_pid = prompts_df[prompts_df["prompt_id"] == prompt_id].sort_values("version")
            if not versions_for_pid.empty:
                with st.expander(f"📋 Template preview — {len(versions_for_pid)} version(s)", expanded=False):
                    for _, vrow in versions_for_pid.iterrows():
                        st.markdown(
                            f"**v{int(vrow['version'])}** — {vrow.get('name', '')} "
                            f"{'✅ default' if vrow.get('is_default') else ''} "
                            f"(weight: {vrow.get('traffic_weight', 1.0):.1f})"
                        )
                        tmpl = vrow.get("template", "")
                        preview = tmpl.replace("{input}", "**[your prompt]**").replace("{text}", "**[your prompt]**")
                        st.markdown(
                            f"<div style='background:#0d1117;border:1px solid #30363d;border-radius:6px;"
                            f"padding:10px 14px;font-size:0.82rem;white-space:pre-wrap;'>{preview}</div>",
                            unsafe_allow_html=True,
                        )

        model = st.selectbox(
            "Model",
            FREE_MODELS,
            index=2,
            help="The LLM to call. If Cost Routing is ON, the system may use a cheaper model from a lower tier if quality is sufficient.",
        )
        temperature = st.slider(
            "Temperature",
            0.0, 1.5, 0.7, 0.05,
            help="Controls randomness. 0 = deterministic, 1.5 = most creative. The system learns optimal temperature per prompt via experiments.",
        )

        st.markdown("**③ Toggle features**")
        c1, c2, c3 = st.columns(3)
        enable_eval = c1.toggle(
            "Evaluate",
            value=True,
            help="Runs LLM-as-Judge after the main call. A second LLM scores the response on 5 quality dimensions (0-1). Adds ~1-2s latency.",
        )
        enable_routing = c2.toggle(
            "Cost Routing",
            value=False,
            help="Tries cheaper models first (Tier 1 to Tier 4) before using your selected model. Accepts the cheapest model whose quality score meets the threshold (default 0.6).",
        )
        ab_testing = c3.toggle(
            "A/B Testing",
            value=True,
            help="When a Prompt ID is set, randomly selects between versions based on their traffic weights. Disabled = always uses the default version.",
        )

    st.divider()

    # ── Run button ───────────────────────────────────────────────────────────
    run_col, _ = st.columns([1, 4])
    run_clicked = run_col.button("Run Pipeline", type="primary", use_container_width=True)

    if run_clicked:
        if not user_input.strip():
            st.warning("Please enter a prompt first.")
            return

        with st.spinner("Running closed-loop pipeline..."):
            try:
                from src.pipeline.orchestrator import PromptOpsPipeline
                _pipe = PromptOpsPipeline()
                response = _pipe.run(
                    user_input=user_input,
                    prompt_id=prompt_id,
                    model=model,
                    temperature=temperature,
                    system_prompt=system_prompt or None,
                    enable_cost_routing=enable_routing,
                    enable_evaluation=enable_eval,
                    ab_testing=ab_testing,
                    tags=["playground"],
                )
            except Exception as exc:
                st.error(f"Pipeline error: {exc}")
                return

        st.success("Pipeline completed!")
        st.cache_data.clear()   # refresh cached tables so new record shows up

        # ── Pipeline trace ───────────────────────────────────────────────────
        with st.expander("Pipeline trace — what happened step by step?", expanded=True):
            # Step 1: Prompt
            if response.prompt_id and response.prompt_version:
                st.markdown(f"✅ **Step 1 — Prompt selected:** `{response.prompt_id}` v{response.prompt_version} (A/B test picked this version)")
            elif response.prompt_id:
                st.markdown(f"✅ **Step 1 — Prompt selected:** `{response.prompt_id}` (default version)")
            else:
                st.markdown("✅ **Step 1 — Prompt:** Sent directly (no Prompt ID / no template applied)")

            # Step 2: Temperature
            st.markdown(
                f"✅ **Step 2 — Temperature:** `{response.temperature}` "
                + ("(from experiment)" if response.temperature != 0.7 else "(default — no experiment data yet)")
            )

            # Step 3: LLM call
            if response.was_cost_routed:
                st.markdown(
                    f"✅ **Step 3 — LLM call (Cost Routing ON):** Tried cheaper tiers first → "
                    f"settled on `{short(response.model)}` "
                    f"(originally requested `{short(response.original_model)}`)"
                )
            else:
                st.markdown(f"✅ **Step 3 — LLM call:** `{short(response.model)}` — took **{response.latency_ms:.0f} ms**")

            # Step 4: Telemetry
            st.markdown(
                f"✅ **Step 4 — Telemetry recorded:** `{response.request_id}` — "
                f"{response.input_tokens + response.output_tokens:,} tokens | "
                f"cost ${response.cost_usd:.6f}"
            )

            # Step 5: Evaluation
            if response.quality_score is not None:
                q = response.quality_score
                q_color = "#22c55e" if q >= 0.7 else "#f59e0b" if q >= 0.5 else "#ef4444"
                q_label = "Good" if q >= 0.7 else "Fair" if q >= 0.5 else "Poor"
                st.markdown(
                    f"✅ **Step 5 — Quality evaluated:** composite score "
                    f"<span style='color:{q_color};font-weight:700;'>{q:.3f} ({q_label})</span> "
                    f"via LLM-as-Judge",
                    unsafe_allow_html=True,
                )
            elif enable_eval:
                st.markdown("⚠️ **Step 5 — Evaluation:** Judge model returned no score (API issue or rate limit)")
            else:
                st.markdown("⬜ **Step 5 — Evaluation:** Skipped (toggle was OFF)")

            # Step 6: Metrics update
            if response.prompt_id:
                st.markdown(f"✅ **Step 6 — Metrics updated:** `{response.prompt_id}` v{response.prompt_version} stats recalculated")
            else:
                st.markdown("⬜ **Step 6 — Metrics update:** Skipped (no Prompt ID set)")

        st.divider()

        # ── KPI metrics ──────────────────────────────────────────────────────
        st.subheader("Results at a glance")

        q_val = response.quality_score
        if q_val is not None:
            q_color = "#22c55e" if q_val >= 0.7 else "#f59e0b" if q_val >= 0.5 else "#ef4444"
            q_label = f"{q_val:.3f}"
        else:
            q_color = "#888"
            q_label = "—"

        r1, r2, r3, r4, r5 = st.columns(5)
        r1.metric("Latency",       f"{response.latency_ms:.0f} ms")
        r2.metric("Tokens",        f"{response.input_tokens + response.output_tokens:,}")
        r3.metric("Cost",          f"${response.cost_usd:.6f}")
        r4.metric("Quality Score", q_label)
        r5.metric("Cost Saved",    f"${response.cost_saved_usd:.6f}")

        # Color badge for quality
        if q_val and q_val >= 0.7:
            badge_text = "Quality: Good"
            badge_icon = "✅"
        elif q_val and q_val >= 0.5:
            badge_text = "Quality: Fair"
            badge_icon = "⚠️"
        elif q_val:
            badge_text = "Quality: Poor"
            badge_icon = "❌"
        else:
            badge_text = "Quality: Not evaluated"
            badge_icon = "⚪"
        st.markdown(
            f"<div style='display:inline-block;background:{q_color}22;border:1px solid {q_color};"
            f"border-radius:20px;padding:3px 14px;font-size:0.82rem;color:{q_color};margin-bottom:8px;'>"
            f"{badge_icon} {badge_text}</div>",
            unsafe_allow_html=True,
        )

        st.divider()

        # ── Side-by-side: response + radar ───────────────────────────────────
        left, right = st.columns([3, 2])

        with left:
            st.subheader("Response")

            info_parts = [f"Model: `{short(response.model)}`"]
            if response.prompt_id:
                info_parts.append(f"Prompt: `{response.prompt_id}` v{response.prompt_version}")
            if response.was_cost_routed:
                info_parts.append(f"Routed from `{short(response.original_model)}` (cost saving)")
            st.caption("  |  ".join(info_parts))

            st.markdown(
                f"""<div style="
                    background:#0d1117;
                    border:1px solid #30363d;
                    border-radius:8px;
                    padding:16px 20px;
                    font-size:0.95rem;
                    line-height:1.6;
                    white-space:pre-wrap;
                ">{response.content}</div>""",
                unsafe_allow_html=True,
            )

            if not response.success:
                st.error(f"Error: {response.error}")

        with right:
            st.subheader("Quality Breakdown")

            eval_details = response.evaluation_details or {}
            dims = {
                "Relevance":    eval_details.get("relevance",         None),
                "Accuracy":     eval_details.get("accuracy",          None),
                "Completeness": eval_details.get("completeness",      None),
                "Format":       eval_details.get("format_compliance", None),
                "Safety":       eval_details.get("safety",            None),
            }
            filled = {k: v for k, v in dims.items() if v is not None}

            if filled:
                categories = list(filled.keys())
                values     = list(filled.values())
                fig = go.Figure(go.Scatterpolar(
                    r=values + [values[0]],
                    theta=categories + [categories[0]],
                    fill="toself",
                    line_color="#7c3aed",
                    fillcolor="rgba(124,58,237,0.2)",
                    name="Quality",
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(range=[0, 1], tickfont=dict(size=9))),
                    height=260,
                    margin=dict(l=20, r=20, t=20, b=20),
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

                dim_help = {
                    "Relevance":    "Does the response directly answer the question?",
                    "Accuracy":     "Is the information factually correct?",
                    "Completeness": "Are the key points sufficiently covered?",
                    "Format":       "Does it follow length / format instructions?",
                    "Safety":       "Free from harmful or inappropriate content?",
                }
                for dim, val in filled.items():
                    bar_color = "#22c55e" if val >= 0.7 else "#f59e0b" if val >= 0.5 else "#ef4444"
                    st.markdown(
                        f"""<div style="margin-bottom:6px;" title="{dim_help.get(dim, '')}">
                            <div style="display:flex;justify-content:space-between;
                                        font-size:0.82rem;margin-bottom:2px;">
                                <span>{dim}</span>
                                <span style="font-weight:600;color:{bar_color};">{val:.2f}</span>
                            </div>
                            <div style="background:#1e1e2e;border-radius:4px;height:7px;">
                                <div style="width:{val*100:.1f}%;background:{bar_color};
                                            height:7px;border-radius:4px;"></div>
                            </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                judge_model_name = eval_details.get("judge_model", "")
                judge_ms         = eval_details.get("judge_latency_ms")
                judge_info       = f"Judge: `{short(judge_model_name)}`"
                if judge_ms:
                    judge_info += f" — {judge_ms:.0f} ms"
                st.caption(judge_info)

                if eval_details.get("reasoning"):
                    with st.expander("Judge reasoning"):
                        st.caption(eval_details["reasoning"])
            else:
                if enable_eval:
                    st.info("Evaluation data not returned by this model.")
                else:
                    st.info("Enable the **Evaluate** toggle to see quality breakdown.")

        # ── What did the system do? ───────────────────────────────────────────
        with st.expander("What did the system actually do? (plain English)", expanded=False):
            parts = []

            if response.prompt_id:
                parts.append(
                    f"Your input was wrapped in the **`{response.prompt_id}`** prompt template "
                    f"(version {response.prompt_version}, selected by A/B traffic weighting)."
                )
            else:
                parts.append("Your input was sent directly to the LLM with no template applied.")

            if response.was_cost_routed:
                parts.append(
                    f"The Cost Router tried cheaper models first and found that "
                    f"**`{short(response.model)}`** produced acceptable quality, "
                    f"saving **${response.cost_saved_usd:.6f}** vs your originally requested model."
                )
            else:
                parts.append(f"The request was sent to **`{short(response.model)}`** directly (cost routing was off).")

            parts.append(
                f"Temperature was set to **{response.temperature}** "
                + ("based on previous optimization experiments for this prompt."
                   if response.temperature != 0.7
                   else "(the default — run a temperature experiment to find the optimal value).")
            )

            if response.quality_score is not None:
                q = response.quality_score
                verdict = (
                    "above the quality threshold — this is a good response." if q >= 0.7
                    else "below the quality threshold — consider refining the prompt." if q < 0.5
                    else "borderline — acceptable but could be improved."
                )
                parts.append(f"The LLM-as-Judge scored this response **{q:.3f}/1.0**, which is {verdict}")

            parts.append(
                f"All metrics (latency, tokens, cost, quality) were saved to the database under "
                f"request ID `{response.request_id}`. You can see this entry on the **Telemetry** page."
            )

            for p in parts:
                st.markdown(f"- {p}")

        # ── Request metadata ─────────────────────────────────────────────────
        with st.expander("Raw request metadata (debug)"):
            st.json(response.to_dict())


# ============================================================================
#  PAGE: OVERVIEW
# ============================================================================

def page_overview():
    st.header("System Overview")

    tele = get_telemetry(time_window)
    alerts_df = get_alerts(time_window)

    # KPIs
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    if tele.empty:
        total_req = success_rate = avg_lat = total_cost = avg_quality = 0
    else:
        total_req    = len(tele)
        success_rate = (1 - tele["is_error"].mean()) * 100
        avg_lat      = tele["latency_ms"].dropna().mean()
        total_cost   = tele["cost_usd"].dropna().sum()
        avg_quality  = tele["quality_score"].dropna().mean() if "quality_score" in tele.columns else 0.0

    open_alerts = 0 if alerts_df.empty else int((~alerts_df["is_resolved"]).sum())

    c1.metric("Total Requests",  f"{total_req:,}")
    c2.metric("Success Rate",    f"{success_rate:.1f}%")
    c3.metric("Avg Latency",     f"{avg_lat:.0f} ms"  if avg_lat else "—")
    c4.metric("Total Cost",      f"${total_cost:.4f}")
    c5.metric("Avg Quality",     f"{avg_quality:.3f}" if avg_quality else "—")
    c6.metric("Open Alerts",     str(open_alerts))

    st.divider()

    cl, cr = st.columns(2)

    with cl:
        st.subheader("Requests over time")
        if not tele.empty:
            df = tele.copy()
            df["hour"] = pd.to_datetime(df["timestamp"]).dt.floor("h")
            df["status"] = df["is_error"].map({True: "Error", False: "Success"})
            grp = df.groupby(["hour", "status"]).size().reset_index(name="count")
            fig = px.bar(
                grp, x="hour", y="count", color="status", barmode="stack",
                color_discrete_map={"Success": "#22c55e", "Error": "#ef4444"},
                labels={"hour": "", "count": "Requests"},
            )
            fig.update_layout(height=270, margin=dict(l=0,r=0,t=6,b=0),
                              legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No telemetry data in the selected window.")

    with cr:
        st.subheader("Requests by model")
        if not tele.empty:
            mc = tele["model_name"].map(short).value_counts().reset_index()
            mc.columns = ["model", "count"]
            fig = px.pie(mc, names="model", values="count", hole=0.45,
                         color_discrete_sequence=px.colors.qualitative.Vivid)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(height=270, margin=dict(l=0,r=0,t=6,b=0),
                              showlegend=False)
            st.plotly_chart(fig, width='stretch')

    cl2, cr2 = st.columns(2)

    with cl2:
        st.subheader("Latency distribution")
        if not tele.empty and tele["latency_ms"].notna().any():
            fig = px.histogram(
                tele.dropna(subset=["latency_ms"]),
                x="latency_ms", nbins=40,
                color_discrete_sequence=["#7c3aed"],
                labels={"latency_ms": "Latency (ms)"},
            )
            fig.update_layout(height=260, margin=dict(l=0,r=0,t=6,b=0), showlegend=False)
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No latency data.")

    with cr2:
        st.subheader("Quality scores over time")
        if not tele.empty and tele["quality_score"].notna().any():
            qdf = tele.dropna(subset=["quality_score"]).copy()
            qdf["ts"] = pd.to_datetime(qdf["timestamp"])
            fig = px.scatter(
                qdf.sort_values("ts"), x="ts", y="quality_score",
                color=qdf.sort_values("ts")["model_name"].map(short),
                opacity=0.7,
                labels={"ts": "", "quality_score": "Quality"},
            )
            fig.add_hline(y=0.7, line_dash="dash", line_color="orange",
                          annotation_text="Target 0.70")
            fig.update_layout(height=260, margin=dict(l=0,r=0,t=6,b=0),
                              legend_title="Model")
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No quality score data yet.")


# ============================================================================
#  PAGE: TELEMETRY
# ============================================================================

def page_telemetry():
    st.header("Raw Telemetry Logs")

    tele = get_telemetry(time_window)
    if tele.empty:
        st.warning("No telemetry records in the selected time window.")
        return

    # Filters
    f1, f2, f3 = st.columns(3)
    models = ["All"] + sorted(tele["model_name"].dropna().unique().tolist())
    sel_model  = f1.selectbox("Model", models)
    sel_status = f2.selectbox("Status", ["All", "Success", "Error"])
    search     = f3.text_input("Search request ID / prompt")

    df = tele.copy()
    if sel_model != "All":
        df = df[df["model_name"] == sel_model]
    if sel_status == "Success":
        df = df[df["is_error"] == False]
    elif sel_status == "Error":
        df = df[df["is_error"] == True]
    if search:
        mask = (
            df["request_id"].str.contains(search, na=False, case=False) |
            df["prompt_text"].str.contains(search, na=False, case=False)
        )
        df = df[mask]

    st.caption(f"Showing **{len(df):,}** of **{len(tele):,}** records")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Records",      f"{len(df):,}")
    c2.metric("Avg Latency",  f"{df['latency_ms'].mean():.0f} ms"  if df["latency_ms"].notna().any() else "—")
    c3.metric("Total Tokens", f"{df['total_tokens'].sum():,.0f}"    if "total_tokens" in df.columns and df["total_tokens"].notna().any() else "—")
    c4.metric("Errors",       f"{int(df['is_error'].sum()):,}")

    ca, cb = st.columns(2)
    with ca:
        st.subheader("Latency over time")
        ldf = df.dropna(subset=["latency_ms"]).copy()
        ldf["ts"] = pd.to_datetime(ldf["timestamp"])
        if not ldf.empty:
            fig = px.line(ldf.sort_values("ts"), x="ts", y="latency_ms",
                          color=ldf.sort_values("ts")["model_name"].map(short),
                          labels={"ts": "", "latency_ms": "ms"})
            fig.update_layout(height=240, margin=dict(l=0,r=0,t=6,b=0))
            st.plotly_chart(fig, width='stretch')

    with cb:
        st.subheader("Token usage over time")
        tok = df.dropna(subset=["total_tokens"]).copy()
        tok["ts"] = pd.to_datetime(tok["timestamp"])
        if not tok.empty:
            fig = px.area(tok.sort_values("ts"), x="ts", y="total_tokens",
                          color=tok.sort_values("ts")["model_name"].map(short),
                          labels={"ts": "", "total_tokens": "Tokens"})
            fig.update_layout(height=240, margin=dict(l=0,r=0,t=6,b=0))
            st.plotly_chart(fig, width='stretch')

    st.subheader("Log entries")
    show_cols = ["timestamp", "request_id", "model_name", "provider",
                 "latency_ms", "input_tokens", "output_tokens", "cost_usd",
                 "quality_score", "is_error", "error_type", "prompt_id"]
    show_cols = [c for c in show_cols if c in df.columns]
    out = df[show_cols].copy()
    out["model_name"] = out["model_name"].map(short)
    out = out.sort_values("timestamp", ascending=False).reset_index(drop=True)
    st.dataframe(out, width='stretch', height=420)


# ============================================================================
#  PAGE: MODEL STATS
# ============================================================================

def page_model_stats():
    st.header("Model Performance Stats")

    tele = get_telemetry(time_window)
    if tele.empty:
        st.warning("No telemetry data available.")
        return

    agg = (
        tele.groupby("model_name")
        .agg(
            requests    = ("id",            "count"),
            errors      = ("is_error",      "sum"),
            avg_latency = ("latency_ms",    "mean"),
            p95_latency = ("latency_ms",    lambda x: x.quantile(0.95)),
            avg_tokens  = ("total_tokens",  "mean"),
            total_tokens= ("total_tokens",  "sum"),
            total_cost  = ("cost_usd",      "sum"),
            avg_quality = ("quality_score", "mean"),
        )
        .reset_index()
    )
    agg["success_pct"] = ((agg["requests"] - agg["errors"]) / agg["requests"] * 100).round(1)
    agg["error_pct"]   = (agg["errors"] / agg["requests"] * 100).round(1)
    agg["model_short"] = agg["model_name"].map(short)

    # Summary table
    st.subheader("Per-model summary")
    tbl = agg[["model_short", "requests", "success_pct", "error_pct",
               "avg_latency", "p95_latency", "avg_tokens", "total_cost", "avg_quality"]].copy()
    tbl.columns = ["Model", "Requests", "Success %", "Error %",
                   "Avg Lat (ms)", "P95 Lat (ms)", "Avg Tokens", "Cost $", "Avg Quality"]
    for col in ["Avg Lat (ms)", "P95 Lat (ms)", "Avg Tokens"]:
        tbl[col] = tbl[col].map(lambda x: f"{x:.0f}" if pd.notna(x) else "—")
    tbl["Cost $"]      = tbl["Cost $"].map(lambda x: f"${x:.6f}" if pd.notna(x) else "—")
    tbl["Avg Quality"] = tbl["Avg Quality"].map(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
    st.dataframe(tbl.reset_index(drop=True), width='stretch')

    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Avg latency by model")
        fig = px.bar(
            agg.sort_values("avg_latency"),
            x="model_short", y="avg_latency",
            color="avg_latency", color_continuous_scale="RdYlGn_r",
            labels={"model_short": "Model", "avg_latency": "Avg Latency (ms)"},
        )
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=6,b=0), coloraxis_showscale=False)
        st.plotly_chart(fig, width='stretch')

    with c2:
        st.subheader("Success rate by model")
        fig = px.bar(
            agg.sort_values("success_pct"),
            x="model_short", y="success_pct",
            color="success_pct", color_continuous_scale="RdYlGn", range_color=[0, 100],
            labels={"model_short": "Model", "success_pct": "Success Rate (%)"},
        )
        fig.add_hline(y=90, line_dash="dot", line_color="orange", annotation_text="90%")
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=6,b=0), coloraxis_showscale=False)
        st.plotly_chart(fig, width='stretch')

    c3, c4 = st.columns(2)

    with c3:
        st.subheader("Latency vs quality")
        if agg["avg_quality"].notna().any():
            fig = px.scatter(
                agg.dropna(subset=["avg_quality"]),
                x="avg_latency", y="avg_quality",
                size="requests", color="model_short",
                hover_name="model_short",
                labels={"avg_latency": "Avg Latency (ms)", "avg_quality": "Avg Quality"},
            )
            fig.update_layout(height=290, margin=dict(l=0,r=0,t=6,b=0))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No quality data yet.")

    with c4:
        st.subheader("Total tokens by model")
        fig = px.bar(
            agg.sort_values("total_tokens", ascending=False),
            x="model_short", y="total_tokens",
            color_discrete_sequence=["#7c3aed"],
            labels={"model_short": "Model", "total_tokens": "Total Tokens"},
        )
        fig.update_layout(height=290, margin=dict(l=0,r=0,t=6,b=0))
        st.plotly_chart(fig, width='stretch')


# ============================================================================
#  PAGE: PROMPT VERSIONS
# ============================================================================

def page_prompts():
    st.header("Prompt Versions & A/B Testing")

    df = get_prompts()
    if df.empty:
        st.warning("No prompt versions found.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Versions",   len(df))
    c2.metric("Unique Prompts",   df["prompt_id"].nunique())
    c3.metric("Active Versions",  int(df["is_active"].sum()))
    c4.metric("Default Versions", int(df["is_default"].sum()))

    st.divider()

    prompt_ids = ["All"] + sorted(df["prompt_id"].dropna().unique().tolist())
    sel_pid = st.selectbox("Filter by Prompt ID", prompt_ids)
    show = df if sel_pid == "All" else df[df["prompt_id"] == sel_pid]

    cl, cr = st.columns([3, 2])

    with cl:
        st.subheader("Versions table")
        tbl_cols = ["prompt_id", "version", "name", "ab_test_group",
                    "traffic_weight", "is_default", "is_active",
                    "total_calls", "avg_quality_score", "success_rate", "avg_latency_ms"]
        tbl_cols = [c for c in tbl_cols if c in show.columns]
        st.dataframe(show[tbl_cols].reset_index(drop=True), width='stretch', height=340)

    with cr:
        st.subheader("A/B group split")
        gc = show["ab_test_group"].value_counts().reset_index()
        gc.columns = ["group", "count"]
        if not gc.empty:
            fig = px.pie(gc, names="group", values="count", hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Safe)
            fig.update_layout(height=300, margin=dict(l=0,r=0,t=6,b=0))
            st.plotly_chart(fig, width='stretch')

    st.subheader("Template inspector")
    if sel_pid != "All":
        sel_ver = st.selectbox("Select version", sorted(show["version"].tolist()))
        row = show[show["version"] == sel_ver].iloc[0]
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("A/B Group",    str(row.get("ab_test_group", "—")))
        mc2.metric("Total Calls",  str(int(row.get("total_calls", 0))))
        mc3.metric("Avg Quality",  f"{row['avg_quality_score']:.3f}" if row.get("avg_quality_score") else "—")
        st.code(row.get("template", ""), language="text")
    else:
        st.info("Select a specific Prompt ID above to inspect its template.")


# ============================================================================
#  PAGE: EVALUATIONS
# ============================================================================

def page_evaluations():
    st.header("LLM-as-Judge Evaluations")

    df = get_evaluations()
    if df.empty:
        st.warning("No evaluation records found.")
        return

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Evaluations", len(df))
    for metric_col, label, col_widget in [
        ("composite_score", "Avg Composite", c2),
        ("relevance",       "Avg Relevance", c3),
        ("accuracy",        "Avg Accuracy",  c4),
        ("completeness",    "Avg Complete",  c5),
    ]:
        val = df[metric_col].mean() if metric_col in df.columns and df[metric_col].notna().any() else None
        col_widget.metric(label, f"{val:.3f}" if val is not None else "—")

    st.divider()
    cl, cr = st.columns(2)

    with cl:
        st.subheader("Composite score distribution")
        if "composite_score" in df.columns and df["composite_score"].notna().any():
            fig = px.histogram(
                df.dropna(subset=["composite_score"]),
                x="composite_score", nbins=30,
                color_discrete_sequence=["#a78bfa"],
                labels={"composite_score": "Composite Score"},
            )
            fig.add_vline(x=0.7, line_dash="dash", line_color="orange",
                          annotation_text="Target 0.70")
            fig.update_layout(height=270, margin=dict(l=0,r=0,t=6,b=0))
            st.plotly_chart(fig, width='stretch')

    with cr:
        st.subheader("Score dimensions per model (radar)")
        dims = [d for d in ["relevance","accuracy","completeness","format_compliance","safety"]
                if d in df.columns]
        if dims and "model_name" in df.columns:
            rdf = df.groupby("model_name")[dims].mean().reset_index()
            fig = go.Figure()
            for _, row in rdf.iterrows():
                fig.add_trace(go.Scatterpolar(
                    r=[row[d] for d in dims], theta=dims,
                    fill="toself", name=short(row["model_name"]),
                ))
            fig.update_layout(
                polar=dict(radialaxis=dict(range=[0, 1])),
                height=290, margin=dict(l=20,r=20,t=20,b=20),
            )
            st.plotly_chart(fig, width='stretch')

    st.subheader("Composite score over time")
    if "evaluated_at" in df.columns and df["composite_score"].notna().any():
        edf = df.dropna(subset=["composite_score"]).copy()
        edf["ts"] = pd.to_datetime(edf["evaluated_at"])
        fig = px.scatter(
            edf.sort_values("ts"), x="ts", y="composite_score",
            color=edf.sort_values("ts")["model_name"].map(short) if "model_name" in edf else None,
            opacity=0.65,
            labels={"ts": "", "composite_score": "Composite Score"},
        )
        fig.add_hline(y=0.7, line_dash="dash", line_color="orange")
        fig.update_layout(height=280, margin=dict(l=0,r=0,t=6,b=0))
        st.plotly_chart(fig, width='stretch')

    with st.expander("Full evaluation table"):
        show_cols = ["evaluated_at","model_name","prompt_id","composite_score",
                     "relevance","accuracy","completeness","format_compliance",
                     "safety","judge_model","judge_latency_ms"]
        show_cols = [c for c in show_cols if c in df.columns]
        st.dataframe(df[show_cols].sort_values("evaluated_at", ascending=False)
                     .reset_index(drop=True), width='stretch', height=350)


# ============================================================================
#  PAGE: COST ROUTING
# ============================================================================

def page_cost_routing():
    st.header("Cost-Aware Routing")

    df = get_cost_routing()
    if df.empty:
        st.warning("No cost routing records found.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Routings",   len(df))
    c2.metric("Escalations",      int(df["escalated"].sum()))
    c3.metric("Escalation Rate",  f"{df['escalated'].mean()*100:.1f}%")
    c4.metric("Total Cost Saved", f"${df['cost_saved_usd'].sum():.6f}")

    st.divider()
    cl, cr = st.columns(2)

    with cl:
        st.subheader("Routing destination")
        flow = df.groupby(["original_model","routed_model"]).size().reset_index(name="count")
        flow["orig"]   = flow["original_model"].map(short)
        flow["routed"] = flow["routed_model"].map(short)
        fig = px.bar(flow, x="routed", y="count", color="orig",
                     barmode="group",
                     labels={"routed": "Routed To", "count": "Count", "orig": "Original"})
        fig.update_layout(height=290, margin=dict(l=0,r=0,t=6,b=0))
        st.plotly_chart(fig, width='stretch')

    with cr:
        st.subheader("Tier usage")
        tc = df["tier_used"].value_counts().reset_index()
        tc.columns = ["tier", "count"]
        fig = px.pie(tc, names="tier", values="count", hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(height=290, margin=dict(l=0,r=0,t=6,b=0))
        st.plotly_chart(fig, width='stretch')

    st.subheader("Quality after routing (box plot)")
    if df["quality_score"].notna().any():
        qdf = df.dropna(subset=["quality_score"]).copy()
        qdf["routed_short"] = qdf["routed_model"].map(short)
        fig = px.box(qdf, x="routed_short", y="quality_score", color="escalated",
                     color_discrete_map={True: "#ef4444", False: "#22c55e"},
                     labels={"routed_short": "Model", "quality_score": "Quality"})
        fig.update_layout(height=290, margin=dict(l=0,r=0,t=6,b=0))
        st.plotly_chart(fig, width='stretch')

    with st.expander("Full routing log"):
        show_cols = ["created_at","prompt_id","original_model","routed_model",
                     "tier_used","quality_score","escalated","cost_saved_usd","latency_ms"]
        show_cols = [c for c in show_cols if c in df.columns]
        out = df[show_cols].copy()
        out["original_model"] = out["original_model"].map(short)
        out["routed_model"]   = out["routed_model"].map(short)
        st.dataframe(out.sort_values("created_at", ascending=False)
                     .reset_index(drop=True), width='stretch', height=300)


# ============================================================================
#  PAGE: TEMPERATURE EXPERIMENTS
# ============================================================================

def page_temperature():
    st.header("Temperature Optimisation Experiments")

    df = get_temp_experiments()
    if df.empty:
        st.warning("No temperature experiments found.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Experiments",    len(df))
    c2.metric("Completed",      int((df["status"] == "completed").sum()))
    c3.metric("Avg Best Temp",  f"{df['best_temperature'].mean():.2f}"    if df["best_temperature"].notna().any() else "—")
    c4.metric("Avg Best Quality", f"{df['best_quality_score'].mean():.3f}" if df["best_quality_score"].notna().any() else "—")

    st.divider()
    cl, cr = st.columns(2)

    with cl:
        st.subheader("Best temperature distribution")
        if df["best_temperature"].notna().any():
            fig = px.histogram(df.dropna(subset=["best_temperature"]),
                               x="best_temperature", nbins=15,
                               color_discrete_sequence=["#f59e0b"],
                               labels={"best_temperature": "Best Temperature"})
            fig.update_layout(height=270, margin=dict(l=0,r=0,t=6,b=0))
            st.plotly_chart(fig, width='stretch')

    with cr:
        st.subheader("Best temperature vs quality")
        valid = df.dropna(subset=["best_temperature","best_quality_score"])
        if not valid.empty:
            valid = valid.copy()
            valid["model_short"] = valid["model_name"].map(short)
            fig = px.scatter(valid, x="best_temperature", y="best_quality_score",
                             color="model_short", size="total_trials",
                             hover_data=["prompt_id"],
                             labels={"best_temperature": "Best Temp",
                                     "best_quality_score": "Quality"})
            fig.update_layout(height=270, margin=dict(l=0,r=0,t=6,b=0))
            st.plotly_chart(fig, width='stretch')

    st.subheader("Experiment drill-down")
    sel_exp = st.selectbox("Select experiment", ["—"] + df["experiment_id"].tolist())
    if sel_exp != "—":
        row = df[df["experiment_id"] == sel_exp].iloc[0]
        ec1, ec2, ec3, ec4 = st.columns(4)
        ec1.metric("Prompt ID",  str(row.get("prompt_id", "—")))
        ec2.metric("Model",      short(str(row.get("model_name", ""))))
        ec3.metric("Best Temp",  f"{row.get('best_temperature', 0):.2f}")
        ec4.metric("Status",     str(row.get("status", "—")))

        results = row.get("results_json")
        if results and isinstance(results, dict):
            rdf = pd.DataFrame([
                {"temperature": k,
                 "avg_quality": v.get("avg_quality", 0) if isinstance(v, dict) else v}
                for k, v in results.items()
            ])
            fig = px.line(rdf, x="temperature", y="avg_quality", markers=True,
                          color_discrete_sequence=["#f59e0b"],
                          labels={"temperature": "Temperature", "avg_quality": "Avg Quality"})
            fig.update_layout(height=240, margin=dict(l=0,r=0,t=6,b=0))
            st.plotly_chart(fig, width='stretch')

    with st.expander("All experiments table"):
        show_cols = ["experiment_id","prompt_id","model_name","best_temperature",
                     "best_quality_score","total_trials","total_cost_usd",
                     "status","started_at","completed_at"]
        show_cols = [c for c in show_cols if c in df.columns]
        out = df[show_cols].copy()
        out["model_name"] = out["model_name"].map(short)
        st.dataframe(out.reset_index(drop=True), width='stretch', height=300)


# ============================================================================
#  PAGE: ALERTS
# ============================================================================

def page_alerts():
    st.header("Alerts & Threshold Violations")

    df = get_alerts(time_window)
    if df.empty:
        st.success("No alerts in the selected time window.")
        return

    open_df     = df[df["is_resolved"] == False]
    resolved_df = df[df["is_resolved"] == True]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Alerts",     len(df))
    c2.metric("Open",             len(open_df))
    c3.metric("Resolved",         len(resolved_df))
    sev = df["severity"].value_counts()
    c4.metric("Critical + High",  int(sev.get("critical", 0)) + int(sev.get("high", 0)))

    st.divider()
    tab_open, tab_resolved, tab_trend = st.tabs(["Open", "Resolved", "Trend"])

    with tab_open:
        if open_df.empty:
            st.success("No open alerts.")
        else:
            for _, row in open_df.sort_values("triggered_at", ascending=False).iterrows():
                sev_label = str(row.get("severity", "low")).upper()
                st.markdown(
                    f"**[{sev_label}]** "
                    f"**{str(row.get('alert_type','—')).replace('_',' ').title()}**  "
                    f"— `{short(str(row.get('model_name','')))}` "
                    f"  ·  _{row.get('triggered_at','')}_"
                )
                st.caption(str(row.get("message", "")))
                if row.get("threshold_value") and row.get("actual_value"):
                    st.caption(
                        f"Threshold: {row['threshold_value']:.2f}  "
                        f"| Actual: {row['actual_value']:.2f}"
                    )
                st.divider()

    with tab_resolved:
        if resolved_df.empty:
            st.info("No resolved alerts.")
        else:
            show_cols = ["triggered_at","resolved_at","alert_type","severity","model_name","message"]
            show_cols = [c for c in show_cols if c in resolved_df.columns]
            st.dataframe(resolved_df[show_cols].sort_values("triggered_at", ascending=False)
                         .reset_index(drop=True), width='stretch')

    with tab_trend:
        st.subheader("Alert frequency over time")
        adf = df.copy()
        adf["day"] = pd.to_datetime(adf["triggered_at"]).dt.date
        trend = adf.groupby(["day","severity"]).size().reset_index(name="count")
        if not trend.empty:
            fig = px.bar(trend, x="day", y="count", color="severity",
                         barmode="stack",
                         color_discrete_map={
                             "low":"#22c55e","medium":"#f59e0b",
                             "high":"#ef4444","critical":"#9333ea",
                         },
                         labels={"day": "Date", "count": "Alerts"})
            fig.update_layout(height=290, margin=dict(l=0,r=0,t=6,b=0))
            st.plotly_chart(fig, width='stretch')

    st.subheader("Alert type breakdown")
    tc = df["alert_type"].value_counts().reset_index()
    tc.columns = ["type", "count"]
    fig = px.bar(tc, x="type", y="count",
                 color_discrete_sequence=["#7c3aed"],
                 labels={"type": "Alert Type", "count": "Count"})
    fig.update_layout(height=250, margin=dict(l=0,r=0,t=6,b=0))
    st.plotly_chart(fig, width='stretch')


# ============================================================================
#  PAGE: OPTIMISATION RUNS
# ============================================================================

def page_optimisation():
    st.header("Prompt Optimisation Runs")

    df = get_opt_runs()
    if df.empty:
        st.warning("No optimisation runs found.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Runs",      len(df))
    c2.metric("Completed",       int((df["status"] == "completed").sum()))
    c3.metric("Running",         int((df["status"] == "running").sum()))
    imp = df["improvement_percentage"].dropna()
    c4.metric("Avg Improvement", f"{imp.mean():.1f}%" if not imp.empty else "—")

    st.divider()
    cl, cr = st.columns(2)

    with cl:
        st.subheader("Improvement % by goal")
        idf = df.dropna(subset=["improvement_percentage"])
        if not idf.empty:
            fig = px.box(idf, x="optimization_goal", y="improvement_percentage",
                         color="optimization_goal",
                         color_discrete_sequence=px.colors.qualitative.Safe,
                         labels={"optimization_goal": "Goal",
                                 "improvement_percentage": "Improvement (%)"})
            fig.update_layout(height=290, margin=dict(l=0,r=0,t=6,b=0), showlegend=False)
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No completed runs with improvement data.")

    with cr:
        st.subheader("Run status")
        sc = df["status"].value_counts().reset_index()
        sc.columns = ["status", "count"]
        fig = px.pie(sc, names="status", values="count", hole=0.4,
                     color_discrete_map={
                         "completed":"#22c55e","failed":"#ef4444","running":"#f59e0b"
                     })
        fig.update_layout(height=290, margin=dict(l=0,r=0,t=6,b=0))
        st.plotly_chart(fig, width='stretch')

    st.subheader("Baseline vs optimised score")
    scored = df.dropna(subset=["baseline_score","optimized_score"])
    if not scored.empty:
        fig = go.Figure()
        for _, row in scored.iterrows():
            fig.add_trace(go.Scatter(
                x=[row["baseline_score"], row["optimized_score"]],
                y=[row["run_id"][-8:], row["run_id"][-8:]],
                mode="lines+markers",
                line=dict(color="#7c3aed"),
                marker=dict(size=10, color=["#94a3b8","#22c55e"]),
                showlegend=False,
            ))
        fig.update_layout(
            height=max(200, len(scored) * 42),
            xaxis_title="Score", yaxis_title="Run (last 8 chars)",
            margin=dict(l=0,r=0,t=6,b=0),
        )
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("No completed runs with score data.")

    with st.expander("All runs table"):
        show_cols = ["run_id","prompt_id","optimization_goal","strategy_used",
                     "baseline_score","optimized_score","improvement_percentage",
                     "status","started_at","completed_at"]
        show_cols = [c for c in show_cols if c in df.columns]
        st.dataframe(df[show_cols].sort_values("started_at", ascending=False)
                     .reset_index(drop=True), width='stretch', height=350)


# ============================================================================
#  ROUTER
# ============================================================================

dispatch = {
    "Overview":                  page_overview,
    "Playground":                page_playground,
    "Telemetry":                 page_telemetry,
    "Model Stats":               page_model_stats,
    "Prompt Versions":           page_prompts,
    "Evaluations":               page_evaluations,
    "Cost Routing":              page_cost_routing,
    "Temperature Experiments":   page_temperature,
    "Alerts":                    page_alerts,
    "Optimisation Runs":         page_optimisation,
}

dispatch[page]()
