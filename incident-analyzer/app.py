import os
import sys
import asyncio
import streamlit as st

# Fix for asyncio ConnectionResetError on Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# UI Settings MUST be the first Streamlit command
st.set_page_config(
    page_title="Multi-Agent Incident Analyzer",
    page_icon="🚨",
    layout="wide"
)

from dotenv import load_dotenv
load_dotenv()

# ── Page Header ──────────────────────────────────────────────────────────────
st.title("🚨 Multi-Agent DevOps Incident Analyzer")
st.markdown(
    "Upload ops logs or paste them below to trigger the **LangGraph AI workflow**. "
    "Agents will **read → classify → fetch remediation → synthesize a cookbook → notify Slack/Jira**."
)
st.divider()

# ── Sidebar: API Config ───────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")

    st.subheader("🤖 LLM")
    openrouter_key = st.text_input("OpenRouter API Key", type="password",
                                   value=os.getenv("OPENROUTER_API_KEY", ""))
    hf_token = st.text_input("Hugging Face Token", type="password",
                              value=os.getenv("HF_TOKEN", ""))

    st.subheader("💬 Slack")
    slack_token = st.text_input("Slack Bot Token", type="password",
                                value=os.getenv("SLACK_BOT_TOKEN", ""))
    slack_channel = st.text_input("Slack Channel ID",
                                  value=os.getenv("SLACK_CHANNEL_ID", ""))

    st.subheader("🎫 Jira")
    jira_url = st.text_input("Jira Server URL",
                              value=os.getenv("JIRA_SERVER_URL", ""),
                              placeholder="https://your-site.atlassian.net")
    jira_email = st.text_input("Jira User Email",
                                value=os.getenv("JIRA_USER_EMAIL", ""))
    jira_token = st.text_input("Jira API Token", type="password",
                                value=os.getenv("JIRA_API_TOKEN", ""))
    jira_project = st.text_input("Jira Project Key",
                                  value=os.getenv("JIRA_PROJECT_KEY", "OPS"),
                                  placeholder="OPS")

    if st.button("💾 Apply Settings"):
        if openrouter_key:
            os.environ["OPENROUTER_API_KEY"] = openrouter_key
        if hf_token:
            os.environ["HF_TOKEN"] = hf_token
        if slack_token:
            os.environ["SLACK_BOT_TOKEN"] = slack_token
        if slack_channel:
            os.environ["SLACK_CHANNEL_ID"] = slack_channel
        if jira_url:
            os.environ["JIRA_SERVER_URL"] = jira_url
        if jira_email:
            os.environ["JIRA_USER_EMAIL"] = jira_email
        if jira_token:
            os.environ["JIRA_API_TOKEN"] = jira_token
        if jira_project:
            os.environ["JIRA_PROJECT_KEY"] = jira_project
        st.success("✅ All settings applied!")

# ── Log Input ─────────────────────────────────────────────────────────────────
col_input, col_sample = st.columns([3, 1])
with col_input:
    log_input = st.text_area(
        "📋 Paste Raw Log Here:",
        height=200,
        placeholder="e.g. 503 Service Unavailable / Upstream Timeout from nginx"
    )

with col_sample:
    st.markdown("**🧪 Sample Logs**")
    if st.button("Load Nginx 503"):
        st.session_state["sample_log"] = (
            "2024-01-15 10:23:01 [error] 1234#0: *456 upstream timed out (110: Connection timed out) "
            "while reading response header from upstream, client: 10.0.0.1, server: api.example.com, "
            "request: 'GET /api/data HTTP/1.1', upstream: 'http://127.0.0.1:8080/api/data', "
            "host: 'api.example.com' HTTP 503 Service Unavailable"
        )
    if st.button("Load K8s CrashLoop"):
        st.session_state["sample_log"] = (
            "Warning BackOff 5m kubelet Back-off restarting failed container "
            "nginx-deployment-5d8d4d7b9f-xk2p9 in pod nginx-deployment-5d8d4d7b9f-xk2p9_default "
            "CrashLoopBackOff OOMKilled exit code 137"
        )

if "sample_log" in st.session_state and not log_input:
    log_input = st.session_state["sample_log"]
    st.text_area("📋 Loaded Sample Log:", value=log_input, height=150, disabled=True)

uploaded_file = st.file_uploader("Or Upload a Log File (.txt / .log)", type=["txt", "log"])
if uploaded_file is not None:
    log_input = uploaded_file.read().decode("utf-8")
    st.success(f"Loaded file: {uploaded_file.name}")

# ── Run Workflow ──────────────────────────────────────────────────────────────
if st.button("🚀 Analyze Incident", type="primary", use_container_width=True):
    if not log_input or not log_input.strip():
        st.error("Please provide a log snippet to analyze.")
    else:
        # Import workflow lazily so UI always renders even if there's an import error
        try:
            from graph.workflow import create_workflow
        except Exception as import_err:
            st.error(f"❌ Failed to load workflow: {import_err}")
            st.stop()

        st.divider()
        st.subheader("🔄 Agent Pipeline Execution")

        initial_state = {
            "raw_log": log_input,
            "parsed_log": None,
            "classification": None,
            "remediation_docs": None,
            "cookbook": None,
            "ticket_id": None,
            "slack_status": None
        }

        progress = st.progress(0, text="Starting agents...")
        status_box = st.empty()
        steps = [
            "log_reader_node",
            "classifier_node",
            "remediation_node",
            "cookbook_node",
            "jira_node / skipped",
            "slack_node"
        ]
        step_labels = {
            "log_reader_node":  "📄 Log Reader",
            "classifier_node":  "🔍 Classifier",
            "remediation_node": "📚 Remediation RAG",
            "cookbook_node":    "📝 Cookbook Generator",
            "jira_node":        "🎫 Jira Ticket",
            "slack_node":       "💬 Slack Notification",
        }

        final_state = dict(initial_state)
        step_idx = 0

        try:
            app = create_workflow()
            for output in app.stream(initial_state):
                for node_name, node_value in output.items():
                    step_idx += 1
                    pct = min(int((step_idx / 6) * 100), 100)
                    label = step_labels.get(node_name, node_name)
                    progress.progress(pct, text=f"Running: {label}")
                    status_box.info(f"✅ Completed: **{label}**")
                    final_state.update(node_value)

            progress.progress(100, text="All agents complete!")
            status_box.success("✅ Workflow finished successfully!")

        except Exception as e:
            st.error(f"❌ Workflow failed: {e}")
            st.exception(e)
            st.stop()

        st.divider()

        # ── Results ─────────────────────────────────────────────────────────
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("1️⃣ Parsed Log")
            st.json(final_state.get("parsed_log") or {})

            st.subheader("2️⃣ Incident Classification")
            classification = final_state.get("classification") or {}
            severity = classification.get("severity", "unknown").lower()
            badge = "🔴" if severity == "critical" else "🟡" if severity == "warning" else "🟢"
            st.json(classification)
            st.markdown(f"**Severity:** {badge} `{severity.upper()}`")

        with c2:
            st.subheader("3️⃣ Notifications & Ticketing")
            ticket_id = final_state.get("ticket_id")
            if ticket_id:
                st.info(f"🎫 **Jira Ticket Created:** `{ticket_id}`")
            else:
                st.info("🎫 **Jira Ticket:** Skipped (not critical)")
            slack_status = final_state.get("slack_status", "Not sent")
            st.success(f"💬 **Slack:** {slack_status}")

            st.subheader("📚 Remediation Context")
            docs = final_state.get("remediation_docs") or []
            if docs:
                for i, doc in enumerate(docs, 1):
                    with st.expander(f"Runbook Chunk #{i}"):
                        st.markdown(doc)
            else:
                st.warning("No runbooks retrieved from vector store.")

        st.divider()
        st.subheader("4️⃣ Generated Recovery Cookbook")
        cookbook = final_state.get("cookbook", "")
        if cookbook:
            st.markdown(cookbook)
        else:
            st.warning("No cookbook was generated.")
