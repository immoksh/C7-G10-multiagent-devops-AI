"""Agent 6 - Slack Notification Agent.

Posts a formatted incident summary (root cause, fix, Jira link) to a Slack
channel using the Slack SDK. No LLM is involved. When no Slack token is
configured it runs in dry-run mode and returns the message it *would* have
sent so the workflow always completes.
"""

from __future__ import annotations

from typing import Dict

from config import settings
from graph.state import IncidentState

SEVERITY_EMOJI = {
    "critical": "🚨",
    "high": "🔴",
    "medium": "🟠",
    "low": "🟡",
}


def build_message(state: IncidentState) -> str:
    cls = state.get("classification", {})
    parsed = state.get("parsed", {})
    remediation = state.get("remediation", {})
    jira = state.get("jira", {})

    severity = cls.get("severity", "medium")
    emoji = SEVERITY_EMOJI.get(severity, "⚠️")

    fix = remediation.get("fix", "See runbook.")
    # Keep the Slack message compact.
    fix_short = fix if len(fix) < 800 else fix[:800] + " …"

    jira_line = ""
    if jira:
        if jira.get("created"):
            jira_line = f"\n*Jira*: <{jira.get('url')}|{jira.get('key')}>"
        elif jira.get("dry_run"):
            jira_line = f"\n*Jira*: {jira.get('key')} (dry-run)"

    return (
        f"{emoji} *{severity.upper()} Incident* — {parsed.get('service', 'service')}\n\n"
        f"*Root Cause*: {cls.get('root_cause', 'unknown')}\n"
        f"*Summary*: {cls.get('summary', '')}\n"
        f"*Confidence*: {cls.get('confidence', 'n/a')}\n\n"
        f"*Suggested Fix*:\n{fix_short}"
        f"{jira_line}"
    )


def run(state: IncidentState) -> IncidentState:
    message = build_message(state)

    if not settings.slack_enabled:
        state["slack"] = {
            "sent": False,
            "dry_run": True,
            "channel": settings.slack_channel,
            "message": message,
            "note": "Slack not configured - dry run. Set SLACK_BOT_TOKEN to enable.",
        }
        state.setdefault("trace", []).append("Slack: dry-run (no token)")
        return state

    try:
        from slack_sdk import WebClient

        client = WebClient(token=settings.slack_bot_token)
        resp = client.chat_postMessage(
            channel=settings.slack_channel, text=message
        )
        state["slack"] = {
            "sent": True,
            "dry_run": False,
            "channel": settings.slack_channel,
            "ts": resp.get("ts"),
            "message": message,
        }
        state.setdefault("trace", []).append(
            f"Slack: posted to {settings.slack_channel}"
        )
    except Exception as exc:
        state["slack"] = {
            "sent": False,
            "dry_run": False,
            "channel": settings.slack_channel,
            "error": str(exc),
            "message": message,
        }
        state.setdefault("errors", []).append(f"Slack error: {exc}")
        state.setdefault("trace", []).append("Slack: post failed")
    return state
