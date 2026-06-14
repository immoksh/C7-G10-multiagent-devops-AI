"""Agent 4 - Cookbook Generator.

Turns the remediation into a short, checkable recovery checklist that a
junior engineer can follow step by step. Uses the LLM when available,
otherwise derives a sensible checklist from the detected root cause.
"""

from __future__ import annotations

from typing import Dict

from graph.state import IncidentState
from llm import complete

SYSTEM = (
    "You convert incident remediations into crisp, numbered recovery "
    "checklists for on-call engineers. Output GitHub-flavoured markdown only."
)

PROMPT_TEMPLATE = """Create a recovery checklist titled "# Recovery Checklist".

Incident: {summary}
Root cause: {root_cause}

Remediation details:
{fix}

Produce 4-7 numbered, verifiable steps. Each step must be a concrete action
(verify / check / restart / validate). End with a final validation step.
"""

# Reusable checklist templates keyed by root cause family.
FALLBACK_STEPS = {
    "memory_exhaustion": [
        "Check `kubectl get events` for `OOMKilled` on the affected pods",
        "Inspect memory limits with `kubectl describe pod <pod>`",
        "Increase memory requests/limits or fix the leak in the deployment",
        "Roll the deployment: `kubectl rollout restart deploy/<name>`",
        "Validate pod is `Running` and memory usage is stable",
    ],
    "pod_crashloop": [
        "Inspect crash logs: `kubectl logs <pod> --previous`",
        "Check `kubectl describe pod <pod>` for the restart reason",
        "Verify config maps / secrets / liveness probes are correct",
        "Apply the fix and `kubectl rollout restart deploy/<name>`",
        "Confirm the pod stops restarting and passes readiness",
    ],
    "upstream_timeout": [
        "Identify the slow upstream from the gateway/nginx logs",
        "Check upstream health and latency dashboards",
        "Increase the relevant timeout or scale the upstream",
        "Reload the proxy config (`nginx -s reload`) if changed",
        "Validate requests succeed and p99 latency recovers",
    ],
    "disk_pressure": [
        "Run `df -h` / check node DiskPressure conditions",
        "Identify and clear large logs or unused images",
        "Expand the volume or evict non-critical workloads",
        "Confirm the node leaves DiskPressure",
        "Validate workloads reschedule successfully",
    ],
}

GENERIC_STEPS = [
    "Confirm the scope and blast radius of the incident",
    "Review the most recent deploys and configuration changes",
    "Apply the recommended remediation from the runbook",
    "Monitor logs and dashboards for recovery",
    "Validate the service is healthy and close the incident",
]


def _fallback_cookbook(classification: Dict) -> str:
    root_cause = classification.get("root_cause", "")
    steps = FALLBACK_STEPS.get(root_cause, GENERIC_STEPS)
    body = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    return f"# Recovery Checklist\n\n{body}"


def run(state: IncidentState) -> IncidentState:
    classification = state.get("classification", {})
    remediation = state.get("remediation", {})

    generated = complete(
        PROMPT_TEMPLATE.format(
            summary=classification.get("summary", ""),
            root_cause=classification.get("root_cause", ""),
            fix=remediation.get("fix", "")[:3000],
        ),
        system=SYSTEM,
        model=state.get("llm_model"),
    )

    cookbook = generated.strip() if generated else _fallback_cookbook(classification)
    if not cookbook.lstrip().startswith("#"):
        cookbook = "# Recovery Checklist\n\n" + cookbook

    state["cookbook"] = cookbook
    state.setdefault("trace", []).append(
        f"Cookbook: generated checklist ({'llm' if generated else 'template'})"
    )
    return state
