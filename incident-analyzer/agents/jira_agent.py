import random
from datetime import datetime, timezone


def _severity_to_priority(severity: str) -> str:
    return {"critical": "P1", "warning": "P2", "info": "P3"}.get(severity.lower(), "P2")


def create_mock_ticket(classification: dict, remediation: dict) -> dict | None:
    severity = classification.get("severity", "info")
    if severity not in ("critical", "warning"):
        return None

    root_cause = classification.get("root_cause", "unknown_issue")
    service = classification.get("affected_service", "unknown-service")
    ticket_id = f"OPS-{random.randint(100, 999)}"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    fix_preview = ""
    steps = remediation.get("fix_steps", [])
    if steps:
        fix_preview = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps[:3]))

    description = (
        f"*Incident detected via DevOps Incident Analyzer*\n\n"
        f"*Root Cause:* {root_cause}\n"
        f"*Service:* {service}\n"
        f"*Severity:* {severity.upper()}\n"
        f"*Detected:* {now}\n\n"
        f"*Reasoning:*\n{classification.get('reasoning', 'N/A')}\n\n"
        f"*Suggested Fix:*\n{fix_preview}\n\n"
        f"*Source Runbook:* {remediation.get('source_runbook', 'N/A')}\n"
        f"*Estimated Resolution:* {remediation.get('estimated_resolution_time', 'N/A')}"
    )

    return {
        "ticket_id": ticket_id,
        "priority": _severity_to_priority(severity),
        "summary": f"{root_cause.replace('_', ' ').title()} — {service}",
        "description": description,
        "assignee": "oncall-sre",
        "reporter": "devops-incident-analyzer",
        "created_at": now,
        "status": "Open",
        "labels": ["incident", "auto-generated", severity],
        "components": [service],
    }
