import streamlit as st
from dotenv import load_dotenv
import os
import json

load_dotenv()

st.set_page_config(
    page_title="DevOps Incident Analyzer",
    page_icon="🚨",
    layout="wide",
)

st.title("🚨 DevOps Incident Analyzer")
st.caption("AI-powered multi-agent incident analysis · LangGraph · Qwen2.5 · ChromaDB")

st.divider()

col1, col2 = st.columns([2, 1])

with col1:
    uploaded_file = st.file_uploader(
        "Upload a log file",
        type=["log", "txt", "json"],
        help="Supports Kubernetes events, Nginx access/error logs, and structured JSON logs",
    )

with col2:
    st.markdown("**Supported formats**")
    st.markdown("- Kubernetes events (`kubectl get events`)")
    st.markdown("- Nginx access / error logs")
    st.markdown("- Structured JSON logs")
    st.markdown("")
    st.markdown("📂 Try a [sample log](#) from `sample_logs/`")

if uploaded_file:
    raw_log = uploaded_file.read().decode("utf-8", errors="replace")

    with st.expander("📄 Raw log input", expanded=False):
        st.code(raw_log[:3000] + ("..." if len(raw_log) > 3000 else ""), language="text")

    if st.button("🔍 Run Analysis", type="primary", use_container_width=True):
        with st.spinner("Running multi-agent pipeline..."):
            try:
                from graph.workflow import run_pipeline
                result = run_pipeline(raw_log)
                st.session_state["result"] = result
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.stop()

if "result" in st.session_state:
    result = st.session_state["result"]

    tab1, tab2, tab3 = st.tabs(["🔁 Pipeline View", "📋 Incident Report", "🔔 Integrations"])

    with tab1:
        st.subheader("Agent Pipeline")
        steps = [
            ("log_reader", "Log Reader", "Parsed log format and extracted fields"),
            ("classifier", "Classifier", "Determined severity and root cause"),
            ("remediation", "Remediation", "Retrieved runbooks and synthesized fix"),
            ("jira_agent", "Jira Agent", "Created mock ticket"),
            ("slack_agent", "Slack Agent", "Built notification card"),
        ]
        for key, label, desc in steps:
            if key in result.get("completed_steps", []):
                st.success(f"✅ **{label}** — {desc}")
            else:
                st.info(f"⏭️ **{label}** — skipped")

        with st.expander("🔧 Full pipeline state (JSON)", expanded=False):
            st.json(result)

    with tab2:
        classification = result.get("classification", {})
        remediation = result.get("remediation", {})
        parsed = result.get("parsed", {})

        severity = classification.get("severity", "unknown")
        severity_color = {"critical": "🔴", "warning": "🟡", "info": "🟢"}.get(severity, "⚪")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Severity", f"{severity_color} {severity.upper()}")
        with col_b:
            st.metric("Log Format", parsed.get("format", "unknown").upper())
        with col_c:
            confidence = classification.get("confidence", 0)
            st.metric("Confidence", f"{int(confidence * 100)}%")

        st.progress(float(classification.get("confidence", 0)), text="Model confidence")

        st.subheader("Root Cause")
        st.markdown(f"**{classification.get('root_cause', 'N/A')}**")
        if classification.get("reasoning"):
            with st.expander("Model reasoning"):
                st.write(classification["reasoning"])

        st.subheader("Recommended Fix")
        fix_steps = remediation.get("fix_steps", [])
        for i, step in enumerate(fix_steps, 1):
            st.markdown(f"{i}. {step}")

        source = remediation.get("source_runbook")
        cited = remediation.get("cited_chunk")
        if source:
            with st.expander(f"📖 Source runbook: `{source}`"):
                st.markdown(cited or "_No chunk available_")

        with st.expander("🔧 Raw classification JSON"):
            st.json(classification)
        with st.expander("🔧 Raw remediation JSON"):
            st.json(remediation)

    with tab3:
        col_slack, col_jira = st.columns(2)

        with col_slack:
            slack_card = result.get("slack_card", {})
            st.markdown("### 📨 MOCK SLACK")
            st.markdown(f"**Channel:** `{slack_card.get('channel', '#incidents')}`")
            emoji = slack_card.get("emoji", "⚠️")
            st.markdown(f"""
<div style="background:#1a1d21;border-left:4px solid {'#e01e5a' if severity=='critical' else '#ecb22e'};padding:12px;border-radius:4px;font-family:monospace;color:#d1d2d3">
{emoji} <strong>Incident Alert</strong><br><br>
<strong>Root Cause:</strong> {classification.get('root_cause','N/A')}<br>
<strong>Severity:</strong> {severity.upper()}<br>
<strong>Fix:</strong> {fix_steps[0] if fix_steps else 'See report'}<br>
<strong>Runbook:</strong> {source or 'N/A'}<br>
<strong>Jira:</strong> {result.get('jira_ticket',{}).get('ticket_id','N/A')}
</div>
""", unsafe_allow_html=True)

            with st.expander("🔧 Raw Slack card JSON"):
                st.json(slack_card)

        with col_jira:
            jira = result.get("jira_ticket")
            st.markdown("### 🎫 MOCK JIRA")
            if jira:
                priority_color = {"P1": "🔴", "P2": "🟠", "P3": "🟡"}.get(jira.get("priority", "P2"), "⚪")
                st.markdown(f"**Ticket:** `{jira.get('ticket_id')}`")
                st.markdown(f"**Priority:** {priority_color} {jira.get('priority')}")
                st.markdown(f"**Summary:** {jira.get('summary')}")
                st.markdown(f"**Assignee:** `{jira.get('assignee')}`")
                st.markdown(f"**Status:** `Open`")
                with st.expander("🔧 Raw Jira ticket JSON"):
                    st.json(jira)
            else:
                st.info("No Jira ticket created — incident not classified as critical.")
