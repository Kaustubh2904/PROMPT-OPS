"""
Streamlit Dashboard for Telemetry-Aware Model Monitoring

This is the main dashboard application that provides a web interface
for monitoring models, viewing metrics, and managing prompts.
"""

import os
import sys
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import List, Dict

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.monitoring import monitor
from src.optimization import prompt_manager, prompt_optimizer, OptimizationGoal
from src.database import init_database, TelemetryLog, PromptVersion, Alert, db_manager


# Page configuration
st.set_page_config(
    page_title="Telemetry-Aware Model Monitoring",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .alert-high {
        background-color: #ffebee;
        padding: 10px;
        border-left: 4px solid #f44336;
        margin: 5px 0;
    }
    .alert-medium {
        background-color: #fff3e0;
        padding: 10px;
        border-left: 4px solid #ff9800;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'db_initialized' not in st.session_state:
        init_database()
        st.session_state.db_initialized = True


def sidebar_navigation():
    """Render sidebar navigation."""
    st.sidebar.title("🔧 Navigation")
    
    page = st.sidebar.radio(
        "Select Page",
        [
            "📊 Dashboard Overview",
            "📈 Model Monitoring",
            "🔄 Prompt Management",
            "🚨 Alerts & Anomalies",
            "⚙️ Settings"
        ]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.info(
        "**Telemetry-Aware Model Monitoring**\n\n"
        "Real-time monitoring and optimization for LLM applications.\n\n"
        "Track performance, optimize prompts, and detect anomalies."
    )
    
    return page


def dashboard_overview():
    """Render the main dashboard overview page."""
    st.title("📊 Dashboard Overview")
    st.markdown("Real-time monitoring of your LLM models")
    
    # Time window selector
    col1, col2 = st.columns([3, 1])
    with col2:
        time_window = st.selectbox(
            "Time Window",
            options=[1, 6, 24, 168],  # 1h, 6h, 24h, 1week
            format_func=lambda x: f"{x}h" if x < 24 else f"{x//24}d",
            index=2
        )
    
    # Get all models summary
    models_summary = monitor.get_all_models_summary(time_window_hours=time_window)
    
    if not models_summary:
        st.warning("No telemetry data available. Start making LLM calls to see metrics.")
        return
    
    # Key metrics
    total_requests = sum(m.get("total_requests", 0) for m in models_summary)
    total_cost = sum(m.get("total_cost_usd", 0) for m in models_summary)
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
            value=f"${total_cost:.4f}",
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
    
    st.markdown("---")
    
    # Models comparison
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Requests by Model")
        if models_summary:
            df_requests = pd.DataFrame([
                {"Model": m["model_name"], "Requests": m["total_requests"]}
                for m in models_summary
            ])
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
                {"Model": m["model_name"], "Cost": m.get("total_cost_usd", 0)}
                for m in models_summary
            ])
            fig = px.pie(
                df_cost,
                names="Model",
                values="Cost",
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Recent activity
    st.subheader("🕒 Recent Activity")
    with db_manager.session_scope() as session:
        recent_logs = session.query(TelemetryLog).order_by(
            TelemetryLog.timestamp.desc()
        ).limit(10).all()
        
        if recent_logs:
            df_logs = pd.DataFrame([
                {
                    "Time": log.timestamp.strftime("%H:%M:%S"),
                    "Model": log.model_name,
                    "Latency (ms)": f"{log.latency_ms:.0f}" if log.latency_ms else "N/A",
                    "Tokens": log.total_tokens or "N/A",
                    "Cost": f"${log.cost_usd:.6f}" if log.cost_usd else "N/A",
                    "Status": "❌ Error" if log.is_error else "✅ Success"
                }
                for log in recent_logs
            ])
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
        else:
            st.info("No recent activity")


def model_monitoring():
    """Render the model monitoring page."""
    st.title("📈 Model Monitoring")
    
    # Model selector
    with db_manager.session_scope() as session:
        models = session.query(TelemetryLog.model_name).distinct().all()
        model_names = [m[0] for m in models]
    
    if not model_names:
        st.warning("No models found. Start making LLM calls to see monitoring data.")
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_model = st.selectbox("Select Model", model_names)
    
    with col2:
        time_window = st.selectbox(
            "Time Window",
            options=[1, 6, 24, 168],
            format_func=lambda x: f"{x}h" if x < 24 else f"{x//24}d",
            index=2
        )
    
    # Get model statistics
    stats = monitor.get_model_stats(selected_model, time_window_hours=time_window)
    
    if stats.get("total_requests", 0) == 0:
        st.info(f"No data available for {selected_model} in the selected time window.")
        return
    
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
            f"${stats['total_cost_usd']:.4f}",
            help="Total cost in USD"
        )
    
    # Latency distribution
    st.subheader("⏱️ Latency Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Latency percentiles
        latency_data = {
            "Percentile": ["P50", "P95", "P99", "Max"],
            "Latency (ms)": [
                stats.get("median_latency_ms", 0),
                stats.get("p95_latency_ms", 0),
                stats.get("p99_latency_ms", 0),
                stats.get("max_latency_ms", 0)
            ]
        }
        df_latency = pd.DataFrame(latency_data)
        fig = px.bar(
            df_latency,
            x="Percentile",
            y="Latency (ms)",
            color="Latency (ms)",
            color_continuous_scale="Reds"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Token usage
        st.markdown("**Token Usage**")
        token_data = {
            "Type": ["Input Tokens", "Output Tokens"],
            "Count": [
                stats.get("total_input_tokens", 0),
                stats.get("total_output_tokens", 0)
            ]
        }
        df_tokens = pd.DataFrame(token_data)
        fig = px.pie(
            df_tokens,
            names="Type",
            values="Count",
            hole=0.4,
            color_discrete_sequence=["#4CAF50", "#2196F3"]
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Anomaly detection
    st.subheader("🔍 Anomaly Detection")
    anomalies = monitor.detect_anomalies(selected_model, metric="latency_ms", sensitivity=2.0)
    
    if anomalies:
        st.warning(f"Found {len(anomalies)} anomalous requests")
        df_anomalies = pd.DataFrame(anomalies)
        df_anomalies['timestamp'] = pd.to_datetime(df_anomalies['timestamp'])
        
        fig = px.scatter(
            df_anomalies,
            x='timestamp',
            y='value',
            size='z_score',
            color='z_score',
            hover_data=['request_id'],
            labels={'value': 'Latency (ms)', 'timestamp': 'Time'},
            title="Anomalous Latency Values"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("No anomalies detected in the selected time window")


def prompt_management():
    """Render the prompt management page."""
    st.title("🔄 Prompt Management")
    
    tab1, tab2, tab3 = st.tabs(["📝 Create Prompt", "📊 View Prompts", "🚀 Optimize"])
    
    with tab1:
        st.subheader("Create New Prompt Version")
        
        with st.form("create_prompt_form"):
            prompt_id = st.text_input(
                "Prompt ID",
                help="Unique identifier for this prompt (e.g., 'summarization_v1')"
            )
            
            name = st.text_input(
                "Name",
                help="Human-readable name"
            )
            
            template = st.text_area(
                "Prompt Template",
                height=150,
                help="The actual prompt text"
            )
            
            description = st.text_area(
                "Description (optional)",
                height=100
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                is_default = st.checkbox("Set as default version")
                ab_test_group = st.text_input(
                    "A/B Test Group (optional)",
                    help="e.g., 'control', 'variant_a'"
                )
            
            with col2:
                traffic_weight = st.number_input(
                    "Traffic Weight",
                    min_value=0.0,
                    max_value=1.0,
                    value=1.0,
                    step=0.1,
                    help="Weight for traffic splitting (0-1)"
                )
            
            submitted = st.form_submit_button("Create Prompt Version")
            
            if submitted:
                if prompt_id and name and template:
                    try:
                        prompt_version = prompt_manager.create_prompt_version(
                            prompt_id=prompt_id,
                            template=template,
                            name=name,
                            description=description,
                            is_default=is_default,
                            ab_test_group=ab_test_group or None,
                            traffic_weight=traffic_weight
                        )
                        st.success(f"✅ Created prompt version: {prompt_id} v{prompt_version.version}")
                    except Exception as e:
                        st.error(f"Error creating prompt: {str(e)}")
                else:
                    st.error("Please fill in all required fields")
    
    with tab2:
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
                                st.metric("Avg Cost", f"${version.avg_cost_usd:.6f}")
                            if version.avg_quality_score:
                                st.metric("Avg Quality", f"{version.avg_quality_score:.2f}")
                        
                        if version.is_active:
                            if st.button(f"Deactivate v{version.version}"):
                                prompt_manager.deactivate_version(selected_prompt, version.version)
                                st.rerun()
        else:
            st.info("No prompts found. Create your first prompt in the 'Create Prompt' tab.")
    
    with tab3:
        st.subheader("Optimize Prompts")
        
        with db_manager.session_scope() as session:
            prompts = session.query(PromptVersion.prompt_id).distinct().all()
            prompt_ids = [p[0] for p in prompts]
        
        if prompt_ids:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                optimize_prompt = st.selectbox("Select Prompt to Optimize", prompt_ids, key="optimize")
            
            with col2:
                optimization_goal = st.selectbox(
                    "Optimization Goal",
                    options=[g.value for g in OptimizationGoal],
                    format_func=lambda x: x.title()
                )
            
            if st.button("🚀 Run Optimization"):
                with st.spinner("Analyzing prompt performance..."):
                    try:
                        goal_enum = OptimizationGoal(optimization_goal)
                        result = prompt_optimizer.run_optimization(optimize_prompt, goal_enum)
                        
                        if result["status"] == "success":
                            st.success("✅ Optimization completed!")
                            
                            recommendation = result["recommendation"]
                            st.markdown(f"**Recommended Version:** {recommendation['recommended_version']}")
                            st.markdown(f"**Version Name:** {recommendation['version_name']}")
                            st.markdown(f"**Score:** {recommendation['score']:.4f}")
                            
                            st.json(recommendation["metrics"])
                        else:
                            st.warning(result.get("message", "Optimization could not be completed"))
                    
                    except Exception as e:
                        st.error(f"Optimization failed: {str(e)}")
        else:
            st.info("No prompts available for optimization")


def alerts_anomalies():
    """Render the alerts and anomalies page."""
    st.title("🚨 Alerts & Anomalies")
    
    # Get active alerts
    active_alerts = monitor.get_active_alerts()
    
    if active_alerts:
        st.subheader(f"⚠️ Active Alerts ({len(active_alerts)})")
        
        for alert in active_alerts:
            severity_emoji = {
                "low": "ℹ️",
                "medium": "⚠️",
                "high": "🚨",
                "critical": "🔴"
            }
            
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(
                        f"{severity_emoji.get(alert.severity, '⚠️')} **{alert.alert_type.replace('_', ' ').title()}**"
                    )
                    st.markdown(f"{alert.message}")
                    st.caption(f"Triggered: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}")
                
                with col2:
                    if alert.model_name:
                        st.markdown(f"**Model:** {alert.model_name}")
                
                with col3:
                    if st.button("Resolve", key=f"resolve_{alert.id}"):
                        monitor.resolve_alert(alert.id)
                        st.rerun()
                
                st.markdown("---")
    else:
        st.success("✅ No active alerts")
    
    # Show resolved alerts
    st.subheader("📋 Recent Resolved Alerts")
    
    with db_manager.session_scope() as session:
        resolved_alerts = session.query(Alert).filter(
            Alert.is_resolved == True
        ).order_by(Alert.resolved_at.desc()).limit(10).all()
        
        if resolved_alerts:
            df_resolved = pd.DataFrame([
                {
                    "Type": alert.alert_type,
                    "Severity": alert.severity,
                    "Model": alert.model_name or "N/A",
                    "Triggered": alert.triggered_at.strftime("%Y-%m-%d %H:%M"),
                    "Resolved": alert.resolved_at.strftime("%Y-%m-%d %H:%M") if alert.resolved_at else "N/A"
                }
                for alert in resolved_alerts
            ])
            st.dataframe(df_resolved, use_container_width=True, hide_index=True)
        else:
            st.info("No resolved alerts")


def settings_page():
    """Render the settings page."""
    st.title("⚙️ Settings")
    
    st.subheader("Threshold Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.number_input(
            "Latency Threshold (ms)",
            value=2000,
            step=100,
            help="Alert when average latency exceeds this value"
        )
        
        st.number_input(
            "Cost Threshold (USD)",
            value=10.0,
            step=1.0,
            help="Alert when total cost exceeds this value"
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
    
    st.markdown("---")
    
    st.subheader("Database Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Aggregate Metrics"):
            with st.spinner("Aggregating metrics..."):
                monitor.aggregate_hourly_metrics(hours_back=24)
                st.success("✅ Metrics aggregated")
    
    with col2:
        if st.button("🗑️ Clear Old Data"):
            st.warning("This feature is not yet implemented")
    
    with col3:
        if st.button("📊 Export Data"):
            st.warning("This feature is not yet implemented")
    
    st.markdown("---")
    
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


def main():
    """Main application entry point."""
    init_session_state()
    
    # Sidebar navigation
    page = sidebar_navigation()
    
    # Route to appropriate page
    if page == "📊 Dashboard Overview":
        dashboard_overview()
    elif page == "📈 Model Monitoring":
        model_monitoring()
    elif page == "🔄 Prompt Management":
        prompt_management()
    elif page == "🚨 Alerts & Anomalies":
        alerts_anomalies()
    elif page == "⚙️ Settings":
        settings_page()


if __name__ == "__main__":
    main()
