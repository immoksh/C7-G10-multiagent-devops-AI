"""Agent 2 - Incident Classifier.

Uses the Hugging Face LLM to reason about severity, the probable root
cause and a confidence score. When the LLM is unavailable it falls back
to a deterministic heuristic derived from the regex parse so the pipeline
keeps producing useful output.
"""

from __future__ import annotations

from typing import Dict

from graph.state import IncidentState
from llm import complete_json

SYSTEM = (
    "You are a senior Site Reliability Engineer with 20+ years of experience "
    "triaging production incidents. You are concise, precise, and always "
    "respond with a single valid JSON object and nothing else."
)

PROMPT_TEMPLATE = """Analyze the following operations log and its parsed metadata.

Parsed metadata:
{parsed}

Raw log:
```
{raw_log}
```

Determine the incident's severity, the probable root cause, a confidence
score between 0 and 1, and a one-sentence summary.

Respond with ONLY this JSON shape:
{{
  "severity": "critical|high|medium|low",
  "root_cause": "<short_snake_case_root_cause>",
  "confidence": 0.0,
  "summary": "<one sentence>"
}}
"""

# Map regex-detected error types to a heuristic root cause + severity.
HEURISTIC = {
    "oom_killed": ("memory_exhaustion", "critical"),
    "pod_crashloop": ("pod_crashloop", "critical"),
    "upstream_timeout": ("upstream_timeout", "high"),
    "service_unavailable": ("upstream_unavailable", "high"),
    "connection_refused": ("connection_refused", "high"),
    "disk_pressure": ("disk_pressure", "critical"),
    "auth_failure": ("auth_misconfiguration", "medium"),
    "db_error": ("database_contention", "high"),
    "rate_limited": ("rate_limiting", "medium"),
    "dns_failure": ("dns_resolution_failure", "high"),
    "tls_error": ("tls_misconfiguration", "medium"),
    "unknown": ("undetermined", "medium"),
}

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _heuristic_classification(parsed: Dict) -> Dict:
    error_type = parsed.get("error_type", "unknown")
    root_cause, severity = HEURISTIC.get(error_type, ("undetermined", "medium"))
    # Escalate if the parser already flagged critical.
    if parsed.get("severity") == "critical":
        severity = "critical"
    summary = (
        f"{parsed.get('service', 'unknown')} reported "
        f"{error_type.replace('_', ' ')}"
    )
    if parsed.get("http_status"):
        summary += f" (HTTP {parsed['http_status']})"
    return {
        "severity": severity,
        "root_cause": root_cause,
        "confidence": 0.6,
        "summary": summary,
        "source": "heuristic",
    }


def run(state: IncidentState) -> IncidentState:
    parsed = state.get("parsed", {})
    raw_log = state.get("raw_log", "")[:4000]

    result = complete_json(
        PROMPT_TEMPLATE.format(parsed=parsed, raw_log=raw_log),
        system=SYSTEM,
        model=state.get("llm_model"),
    )

    if result and "root_cause" in result:
        result.setdefault("severity", parsed.get("severity", "medium"))
        result.setdefault("confidence", 0.75)
        result.setdefault("summary", "")
        result["source"] = "llm"
    else:
        result = _heuristic_classification(parsed)

    # Normalise severity to known buckets.
    sev = str(result.get("severity", "medium")).lower()
    if sev not in SEVERITY_RANK:
        sev = "medium"
    result["severity"] = sev

    state["classification"] = result
    state["is_critical"] = SEVERITY_RANK.get(sev, 2) >= SEVERITY_RANK["high"]
    state.setdefault("trace", []).append(
        f"Classifier ({result['source']}): severity={sev} "
        f"root_cause={result.get('root_cause')} "
        f"confidence={result.get('confidence')}"
    )
    return state
