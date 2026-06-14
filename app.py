"""Streamlit UI for the Multi-Agent DevOps Incident Analysis Platform.

Upload (or paste) ops logs and watch six collaborating agents parse,
classify, retrieve runbooks, synthesize a fix, build a recovery checklist,
file a Jira ticket (critical only) and notify Slack — orchestrated by
LangGraph. Designed to run on Hugging Face Spaces.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from agents import jira_agent
from agents.slack_agent import build_message as build_slack_message
from config import OPENROUTER_MODEL_CHOICES, settings
from graph.workflow import analyze, dispatch

st.set_page_config(
    page_title="Multi-Agent DevOps Incident Analyzer",
    page_icon="🛠️",
    layout="wide",
)

SAMPLE_DIR = Path(__file__).resolve().parent / "data" / "sample_logs"


@st.cache_resource(show_spinner="Building runbook index…")
def _ensure_runbook_index() -> bool:
    """Build the ChromaDB runbook index once per server boot.

    On managed hosts (e.g. Hugging Face Spaces) the persisted index is not
    committed to git, so it must be (re)built at startup. Failures are
    swallowed: retrieval falls back to keyword search automatically.
    """
    try:
        if not settings.chroma_path.exists():
            from vectorstore.ingest import build_index

            build_index()
        return True
    except Exception as exc:  # pragma: no cover - optional dependency/runtime
        print(f"[app] Runbook index build skipped ({exc}); using keyword fallback.")
        return False


_ensure_runbook_index()

SEVERITY_COLORS = {
    "critical": "#d7263d",
    "high": "#f46036",
    "medium": "#f4a261",
    "low": "#2a9d8f",
}


def _badge(label: str, ok: bool) -> str:
    color = "#2a9d8f" if ok else "#9aa0a6"
    return (
        f"<span style='background:{color};color:white;padding:2px 10px;"
        f"border-radius:10px;font-size:0.8rem'>{label}</span>"
    )


# ----------------------------------------------------------------------
# Agent activity timeline — show each agent's completed step + message
# ----------------------------------------------------------------------
def _analysis_steps(result: dict) -> list[tuple[str, str]]:
    parsed = result.get("parsed", {})
    cls = result.get("classification", {})
    rem = result.get("remediation", {})
    cookbook = result.get("cookbook", "")
    n_chunks = len(result.get("runbook_matches", []))
    return [
        (
            "📥 Log Reader Agent",
            f"Parsed **{parsed.get('service', '—')}** · severity `{parsed.get('severity', '—')}` · "
            f"error type `{parsed.get('error_type', '—')}` · {parsed.get('line_count', '?')} log lines.",
        ),
        (
            "🧪 Classifier Agent",
            f"Severity **{str(cls.get('severity', '—')).upper()}** · root cause "
            f"`{cls.get('root_cause', '—')}` · confidence `{cls.get('confidence', '—')}` "
            f"· _source: {cls.get('source', '—')}_\n\n{cls.get('summary', '')}",
        ),
        (
            "🔧 Remediation Agent (RAG)",
            f"Synthesised a fix grounded in **{n_chunks}** runbook chunk(s) "
            f"· _source: {rem.get('source', '—')}_.",
        ),
        (
            "✅ Cookbook Agent",
            f"Built a step-by-step recovery checklist "
            f"({len([l for l in cookbook.splitlines() if l.strip()])} lines).",
        ),
    ]


def _dispatch_steps(result: dict) -> list[tuple[str, str]]:
    jira = result.get("jira", {})
    slack = result.get("slack", {})
    steps: list[tuple[str, str]] = []

    if result.get("is_critical"):
        if jira.get("created"):
            steps.append(("🎫 Jira Agent", f"Created ticket **[{jira.get('key')}]({jira.get('url')})**."))
        elif jira.get("dry_run"):
            steps.append(("🎫 Jira Agent", f"Dry-run ticket `{jira.get('key')}` (no credentials configured)."))
        elif jira.get("error"):
            steps.append(("🎫 Jira Agent", f"⚠️ Ticket creation failed: {jira.get('error')}"))
    else:
        steps.append(("🎫 Jira Agent", "Skipped — non-critical incident (no ticket needed)."))

    if slack.get("sent"):
        steps.append(("📣 Slack Agent", f"Posted incident notification to `{slack.get('channel')}`."))
    elif slack.get("dry_run"):
        steps.append(("📣 Slack Agent", f"Dry-run to `{slack.get('channel')}` (no bot token configured)."))
    elif slack.get("error"):
        steps.append(("📣 Slack Agent", f"⚠️ Post failed: {slack.get('error')}"))

    return steps


def render_timeline(steps: list[tuple[str, str]], *, done: bool = True) -> None:
    mark = "✅" if done else "⏳"
    for title, msg in steps:
        with st.container(border=True):
            st.markdown(f"{mark} **{title}**")
            st.markdown(msg)


def render_dispatch_preview(result: dict) -> None:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 📣 Slack — message preview")
        st.caption(
            f"Target channel `{settings.slack_channel}` · "
            f"{'live send' if settings.slack_enabled else 'dry-run (no token)'}"
        )
        st.code(build_slack_message(result))
        if result.get("is_critical"):
            st.caption("A Jira link is appended automatically once the ticket is created.")
    with c2:
        st.markdown("### 🎫 Jira — ticket preview")
        if not result.get("is_critical"):
            st.info("Non-critical incident — no Jira ticket will be created.")
        else:
            jp = jira_agent.preview(result)
            st.caption(
                f"Project `{jp['project']}` · type `{jp['issue_type']}` · "
                f"{'live create' if jp['live'] else 'dry-run (no credentials)'}"
            )
            st.markdown(f"**Summary:** {jp['summary']}")
            with st.expander("Ticket description"):
                st.code(jp["description"])


def render_integration_results(result: dict) -> None:
    jira = result.get("jira", {})
    slack = result.get("slack", {})
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 📣 Slack")
        if slack.get("dry_run"):
            st.info(f"Dry-run → channel `{slack.get('channel')}`")
        elif slack.get("sent"):
            st.success(f"Posted to `{slack.get('channel')}`")
        elif slack.get("error"):
            st.error(slack.get("error"))
        st.code(slack.get("message", ""))
    with c2:
        st.markdown("### 🎫 Jira")
        if not result.get("is_critical"):
            st.info("Non-critical incident — Jira ticket skipped by orchestrator.")
        elif jira.get("dry_run"):
            st.info(f"Dry-run ticket: `{jira.get('key')}`")
            st.write(jira.get("summary", ""))
        elif jira.get("created"):
            st.success(f"Created [{jira.get('key')}]({jira.get('url')})")
        elif jira.get("error"):
            st.error(jira.get("error"))


# ----------------------------------------------------------------------
# Sidebar — configuration & status
# ----------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Integration Status")
    st.markdown(
        _badge(f"LLM: {'on' if settings.llm_enabled else 'fallback'}", settings.llm_enabled)
        + " "
        + _badge(f"Slack: {'on' if settings.slack_enabled else 'dry-run'}", settings.slack_enabled)
        + " "
        + _badge(f"Jira: {'on' if settings.jira_enabled else 'dry-run'}", settings.jira_enabled),
        unsafe_allow_html=True,
    )
    st.caption(
        "Unconfigured integrations run in safe fallback / dry-run mode so the "
        "full pipeline always completes. Set credentials in a `.env` file to go live."
    )
    st.divider()
    st.subheader("🧠 Analysis Model")
    selected_model = None
    if settings.llm_enabled:
        st.caption(f"Provider: `{settings.llm_provider}`")
        # Ensure the configured default is offered and pre-selected.
        choices = list(dict.fromkeys([settings.active_model, *OPENROUTER_MODEL_CHOICES]))
        choices.append("Custom…")
        picked = st.selectbox("Model for analysis", choices, index=0)
        if picked == "Custom…":
            custom = st.text_input(
                "Custom model id",
                placeholder="e.g. openai/gpt-4o or anthropic/claude-3.5-sonnet",
            )
            selected_model = custom.strip() or None
        else:
            selected_model = picked
        st.caption(f"Using: `{selected_model or settings.active_model}`")
    else:
        st.info(
            "No LLM key set — running in rule-based fallback mode. Add "
            "`OPENROUTER_API_KEY` to `.env` to enable model selection."
        )

    st.divider()
    st.subheader("📚 Runbooks")
    st.caption(
        "Remediation uses RAG over the markdown runbooks in `data/runbooks/`. "
        "Rebuild the vector index after editing them:"
    )
    st.code("python -m vectorstore.ingest", language="bash")


# ----------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------
st.title("🛠️ Multi-Agent DevOps Incident Analyzer")
st.caption(
    "LangGraph · Hugging Face · ChromaDB · Slack · Jira — upload ops logs for "
    "live multi-agent incident analysis and automated remediation."
)

# ----------------------------------------------------------------------
# Input
# ----------------------------------------------------------------------
col_in, col_samples = st.columns([3, 1])

with col_samples:
    st.markdown("**Try a sample**")
    sample_choice = "— none —"
    if SAMPLE_DIR.exists():
        samples = ["— none —"] + sorted(p.name for p in SAMPLE_DIR.glob("*.log"))
        sample_choice = st.selectbox("Sample log", samples, label_visibility="collapsed")

sample_text = ""
if sample_choice and sample_choice != "— none —":
    sample_text = (SAMPLE_DIR / sample_choice).read_text(encoding="utf-8")

with col_in:
    uploaded = st.file_uploader("Upload an ops log file", type=["log", "txt", "json"])
    default_text = ""
    if uploaded is not None:
        default_text = uploaded.read().decode("utf-8", errors="replace")
    elif sample_text:
        default_text = sample_text

    log_text = st.text_area(
        "…or paste log content",
        value=default_text,
        height=220,
        placeholder="Paste raw ops logs here (nginx, kubernetes, postgres, aws …)",
    )

run = st.button("🚀 Analyze Incident", type="primary", use_container_width=True)


# ----------------------------------------------------------------------
# Phase 1 — run the analysis agents (stops before Jira/Slack)
# ----------------------------------------------------------------------
if run:
    if not log_text.strip():
        st.warning("Please upload or paste a log first.")
        st.stop()

    with st.status("Running analysis agents…", expanded=True) as status:
        if selected_model:
            st.write(f"Using model: `{selected_model}`")
        st.write("Orchestrating analysis agents via LangGraph…")
        result = analyze(log_text, model=selected_model)
        for line in result.get("trace", []):
            st.write("• " + line)
        status.update(label="Analysis complete — awaiting your approval ⏸️", state="complete")

    # Persist across reruns so the approval buttons work, and reset any prior run.
    st.session_state.analysis_result = result
    st.session_state.final_result = None
    st.session_state.stage = "awaiting_approval"


# ----------------------------------------------------------------------
# Render results (driven by session state so approval survives reruns)
# ----------------------------------------------------------------------
result = st.session_state.get("final_result") or st.session_state.get("analysis_result")

if result:
    stage = st.session_state.get("stage", "awaiting_approval")
    dispatched = st.session_state.get("final_result") is not None

    parsed = result.get("parsed", {})
    cls = result.get("classification", {})
    remediation = result.get("remediation", {})
    cookbook = result.get("cookbook", "")
    matches = result.get("runbook_matches", [])

    severity = cls.get("severity", "medium")
    sev_color = SEVERITY_COLORS.get(severity, "#888")

    # --- Top-level metrics ---
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(
        f"<div style='padding:8px 0'><b>Severity</b><br>"
        f"<span style='color:{sev_color};font-size:1.6rem;font-weight:700'>"
        f"{severity.upper()}</span></div>",
        unsafe_allow_html=True,
    )
    m2.metric("Service", parsed.get("service", "—"))
    m3.metric("Root Cause", cls.get("root_cause", "—"))
    m4.metric("Confidence", f"{cls.get('confidence', '—')}")

    st.divider()

    # --- Agent activity timeline: every completed step + its message ---
    st.subheader("🧭 Agent Activity")
    render_timeline(_analysis_steps(result))
    if dispatched:
        render_timeline(_dispatch_steps(result))

    st.divider()

    tab_overview, tab_fix, tab_cookbook, tab_runbooks, tab_raw = st.tabs(
        ["📋 Overview", "🔧 Remediation", "✅ Cookbook", "📚 Runbooks", "🧩 Raw State"]
    )

    with tab_overview:
        st.subheader("Incident summary")
        st.write(cls.get("summary", "—"))
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Parsed fields**")
            st.json(
                {
                    "service": parsed.get("service"),
                    "severity": parsed.get("severity"),
                    "error_type": parsed.get("error_type"),
                    "http_status": parsed.get("http_status"),
                    "timestamp": parsed.get("timestamp"),
                }
            )
        with c2:
            st.markdown("**Classification**")
            st.json(cls)
        if parsed.get("key_lines"):
            st.markdown("**Key log lines**")
            st.code("\n".join(parsed["key_lines"]))

    with tab_fix:
        st.subheader("Recommended remediation")
        st.caption(f"Source: {remediation.get('source', 'n/a')}")
        st.markdown(remediation.get("fix", "_No remediation produced._"))

    with tab_cookbook:
        st.subheader("Recovery checklist")
        st.markdown(cookbook or "_No checklist produced._")

    with tab_runbooks:
        st.subheader(f"Retrieved runbooks ({len(matches)})")
        if not matches:
            st.info("No runbook chunks matched. Try `python -m vectorstore.ingest`.")
        for m in matches:
            with st.expander(f"{m['source']} — {m.get('heading', '')}  (score: {m.get('score')})"):
                st.markdown(m["text"])

    with tab_raw:
        st.json({k: v for k, v in result.items() if k != "raw_log"})

    st.divider()

    # ------------------------------------------------------------------
    # Human-in-the-loop approval gate for Slack / Jira dispatch
    # ------------------------------------------------------------------
    st.subheader("🛂 Human Approval — Slack & Jira")

    if stage == "dispatched":
        st.success("Dispatch approved and completed.")
        render_integration_results(result)

    else:
        if stage == "rejected":
            st.warning(
                "🚫 Dispatch was rejected — nothing was sent to Slack or Jira. "
                "Review the preview below and approve if you change your mind."
            )
        else:
            st.info(
                "⏸️ Review what will be sent. The Slack & Jira agents run **only** "
                "after you approve. Nothing has been sent yet."
            )

        render_dispatch_preview(result)

        c_ok, c_no = st.columns(2)
        approve = c_ok.button("✅ Approve & Send", type="primary", use_container_width=True)
        reject = c_no.button("🚫 Reject", use_container_width=True)

        if reject:
            st.session_state.stage = "rejected"
            st.rerun()

        if approve:
            analysis_state = st.session_state.analysis_result
            with st.status("Dispatching to Jira & Slack…", expanded=True) as status:
                final = dispatch(
                    analysis_state,
                    progress=lambda line: st.write("• " + line),
                )
                status.update(label="Dispatch complete ✅", state="complete")
            st.session_state.final_result = final
            st.session_state.stage = "dispatched"
            st.rerun()

    if result.get("errors"):
        st.error("Errors: " + "; ".join(result["errors"]))
