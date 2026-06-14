"""Agent 1 - Log Reader / Parser.

Deterministic, regex-based field extraction. No LLM is used here which
keeps inference costs down and makes the first stage fast and reliable.

It scans a (possibly multi-line) log blob and extracts:
  * service          - the component that emitted the log
  * severity         - critical | error | warning | info
  * error_type       - a normalised category (e.g. upstream_timeout)
  * http_status      - HTTP status code if present
  * timestamp        - first ISO-ish timestamp found
  * key_lines        - the most relevant lines for downstream agents
"""

from __future__ import annotations

import re
from typing import Dict, List

from graph.state import IncidentState

# --- Pattern catalogues -------------------------------------------------

SEVERITY_PATTERNS = [
    ("critical", re.compile(r"\b(crit|critical|fatal|panic|emergency|oomkilled|crashloop)\b", re.I)),
    ("error", re.compile(r"\b(error|err|exception|failed|failure|5\d{2})\b", re.I)),
    ("warning", re.compile(r"\b(warn|warning|deprecat|retry|throttl)\b", re.I)),
    ("info", re.compile(r"\b(info|notice|debug)\b", re.I)),
]

ERROR_TYPE_PATTERNS = [
    ("oom_killed", re.compile(r"\b(oomkilled|out of memory|memory limit|cannot allocate memory)\b", re.I)),
    ("pod_crashloop", re.compile(r"\b(crashloopbackoff|crashloop|back-?off restarting)\b", re.I)),
    ("upstream_timeout", re.compile(r"\b(upstream timed out|upstream timeout|gateway time-?out|504)\b", re.I)),
    ("service_unavailable", re.compile(r"\b(503|service unavailable|no live upstreams)\b", re.I)),
    ("connection_refused", re.compile(r"\b(connection refused|econnrefused|could not connect)\b", re.I)),
    ("disk_pressure", re.compile(r"\b(no space left|disk pressure|diskfull|evicted)\b", re.I)),
    ("auth_failure", re.compile(r"\b(401|403|unauthorized|forbidden|permission denied|access denied)\b", re.I)),
    ("db_error", re.compile(r"\b(deadlock|too many connections|sqlstate|could not serialize|database is locked)\b", re.I)),
    ("rate_limited", re.compile(r"\b(429|rate limit|too many requests|throttled)\b", re.I)),
    ("dns_failure", re.compile(r"\b(name or service not known|no such host|dns resolution|servfail)\b", re.I)),
    ("tls_error", re.compile(r"\b(certificate|x509|tls handshake|ssl error)\b", re.I)),
]

SERVICE_PATTERNS = [
    ("nginx", re.compile(r"\bnginx\b", re.I)),
    ("kubernetes", re.compile(r"\b(kube|kubelet|k8s|pod|deployment|namespace)\b", re.I)),
    ("postgres", re.compile(r"\b(postgres|psql|postgresql|sqlstate)\b", re.I)),
    ("mysql", re.compile(r"\b(mysql|mariadb)\b", re.I)),
    ("redis", re.compile(r"\bredis\b", re.I)),
    ("kafka", re.compile(r"\bkafka\b", re.I)),
    ("docker", re.compile(r"\bdocker\b", re.I)),
    ("aws", re.compile(r"\b(aws|ec2|s3|rds|lambda|cloudwatch)\b", re.I)),
]

HTTP_STATUS_RE = re.compile(r"\b([45]\d{2})\b")
TIMESTAMP_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\b"
)


def _first_match(patterns, text: str, default: str) -> str:
    for label, pattern in patterns:
        if pattern.search(text):
            return label
    return default


def _key_lines(text: str, limit: int = 5) -> List[str]:
    """Return lines that look most relevant (errors first)."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    scored = []
    for ln in lines:
        score = 0
        for _, pattern in SEVERITY_PATTERNS[:2]:  # critical/error
            if pattern.search(ln):
                score += 2
        for _, pattern in ERROR_TYPE_PATTERNS:
            if pattern.search(ln):
                score += 1
        scored.append((score, ln))
    scored.sort(key=lambda x: x[0], reverse=True)
    relevant = [ln for score, ln in scored if score > 0][:limit]
    return relevant or lines[:limit]


def parse_log(raw_log: str) -> Dict:
    text = raw_log or ""
    severity = _first_match(SEVERITY_PATTERNS, text, "info")
    error_type = _first_match(ERROR_TYPE_PATTERNS, text, "unknown")
    service = _first_match(SERVICE_PATTERNS, text, "unknown")

    http_status = None
    m = HTTP_STATUS_RE.search(text)
    if m:
        http_status = m.group(1)

    timestamp = None
    tm = TIMESTAMP_RE.search(text)
    if tm:
        timestamp = tm.group(1)

    return {
        "service": service,
        "severity": severity,
        "error_type": error_type,
        "http_status": http_status,
        "timestamp": timestamp,
        "key_lines": _key_lines(text),
        "line_count": len([l for l in text.splitlines() if l.strip()]),
    }


def run(state: IncidentState) -> IncidentState:
    parsed = parse_log(state.get("raw_log", ""))
    state["parsed"] = parsed
    state.setdefault("trace", []).append(
        f"Log Reader: service={parsed['service']} "
        f"severity={parsed['severity']} type={parsed['error_type']}"
    )
    return state
