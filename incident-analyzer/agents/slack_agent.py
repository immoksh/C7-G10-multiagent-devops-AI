from datetime import datetime, timezone


def build_mock_slack_card(
    classification: dict,
    remediation: dict,
    jira_ticket: dict | None,
) -> dict:
    severity = classification.get("severity", "info")
    root_cause = classification.get("root_cause", "unknown")
    service = classification.get("affected_service", "unknown")
    confidence = classification.get("confidence", 0)
    fix_steps = remediation.get("fix_steps", [])
    source_runbook = remediation.get("source_runbook", "N/A")
    eta = remediation.get("estimated_resolution_time", "unknown")

    emoji = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(severity, "⚠️")
    color = {"critical": "#e01e5a", "warning": "#ecb22e", "info": "#2eb67d"}.get(severity, "#ecb22e")
    channel = "#incidents" if severity == "critical" else "#sre-alerts"

    jira_ref = jira_ticket["ticket_id"] if jira_ticket else "N/A (non-critical)"

    fix_text = "\n".join(f"• {step}" for step in fix_steps[:3]) if fix_steps else "See incident report"

    blocks = [
        {
            "type": "header",
            "text": f"{emoji} Incident Alert — {severity.upper()}",
        },
        {
            "type": "section",
            "fields": [
                {"label": "Root Cause", "value": root_cause.replace("_", " ").title()},
                {"label": "Service", "value": service},
                {"label": "Confidence", "value": f"{int(confidence * 100)}%"},
                {"label": "Est. Resolution", "value": eta},
            ],
        },
        {
            "type": "section",
            "text": f"*Suggested Fix:*\n{fix_text}",
        },
        {
            "type": "context",
            "elements": [
                f"Runbook: `{source_runbook}`",
                f"Jira: `{jira_ref}`",
                f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            ],
        },
    ]

    return {
        "channel": channel,
        "emoji": emoji,
        "color": color,
        "severity": severity,
        "text": f"{emoji} [{severity.upper()}] {root_cause} detected in {service}",
        "blocks": blocks,
    }
