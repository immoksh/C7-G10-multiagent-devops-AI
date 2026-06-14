"""Agent 5 - Jira Agent.

Creates a Jira ticket for critical/high severity incidents via the Jira
REST API. No LLM is involved. When Jira credentials are not configured it
runs in dry-run mode and returns the ticket payload it *would* have
created, so the rest of the pipeline (and the demo) keeps working.
"""

from __future__ import annotations

from typing import Dict

from config import settings
from graph.state import IncidentState


def _build_summary(state: IncidentState) -> str:
    cls = state.get("classification", {})
    parsed = state.get("parsed", {})
    service = parsed.get("service", "service")
    root_cause = cls.get("root_cause", "incident")
    return f"[{cls.get('severity', 'high').upper()}] {service}: {root_cause}"


def _build_description(state: IncidentState) -> str:
    cls = state.get("classification", {})
    parsed = state.get("parsed", {})
    remediation = state.get("remediation", {})
    cookbook = state.get("cookbook", "")
    return (
        f"*Summary*: {cls.get('summary', '')}\n\n"
        f"*Severity*: {cls.get('severity')}\n"
        f"*Root cause*: {cls.get('root_cause')}\n"
        f"*Confidence*: {cls.get('confidence')}\n"
        f"*Service*: {parsed.get('service')}\n"
        f"*Error type*: {parsed.get('error_type')}\n\n"
        f"h3. Remediation\n{remediation.get('fix', '')}\n\n"
        f"h3. Recovery Checklist\n{cookbook}\n"
    )


def preview(state: IncidentState) -> Dict:
    """Build the ticket payload that *would* be filed, without creating it.

    Used by the UI to show the human reviewer exactly what will be sent to
    Jira before they approve the dispatch.
    """
    return {
        "summary": _build_summary(state),
        "description": _build_description(state),
        "project": settings.jira_project_key,
        "issue_type": "Bug",
        "live": settings.jira_enabled,
    }


def _create_real_ticket(summary: str, description: str) -> Dict:
    from jira import JIRA

    client = JIRA(
        server=settings.jira_server,
        basic_auth=(settings.jira_email, settings.jira_api_token),
    )
    issue = client.create_issue(
        fields={
            "project": {"key": settings.jira_project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Bug"},
        }
    )
    url = f"{settings.jira_server.rstrip('/')}/browse/{issue.key}"
    return {"created": True, "dry_run": False, "key": issue.key, "url": url}


def run(state: IncidentState) -> IncidentState:
    summary = _build_summary(state)
    description = _build_description(state)

    if not settings.jira_enabled:
        state["jira"] = {
            "created": False,
            "dry_run": True,
            "key": "OPS-DRYRUN",
            "summary": summary,
            "message": "Jira not configured - dry run. Set JIRA_* env vars to enable.",
        }
        state.setdefault("trace", []).append("Jira: dry-run (no credentials)")
        return state

    try:
        result = _create_real_ticket(summary, description)
        result["summary"] = summary
        state["jira"] = result
        state.setdefault("trace", []).append(f"Jira: created {result['key']}")
    except Exception as exc:
        state["jira"] = {
            "created": False,
            "dry_run": False,
            "error": str(exc),
            "summary": summary,
            "message": "Jira ticket creation failed.",
        }
        state.setdefault("errors", []).append(f"Jira error: {exc}")
        state.setdefault("trace", []).append("Jira: creation failed")
    return state
