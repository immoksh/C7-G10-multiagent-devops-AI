import re
import json


def detect_format(raw: str) -> str:
    if re.search(r"\bCrashLoopBackOff\b|\bOOMKilled\b|\bkubectl\b|LAST SEEN.*REASON.*OBJECT", raw):
        return "kubernetes"
    if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}.*"(GET|POST|PUT|DELETE|HEAD)', raw) or \
       re.search(r"\[error\]|\[warn\]|upstream timed out|no live upstreams", raw, re.IGNORECASE):
        return "nginx"
    try:
        parsed = json.loads(raw.strip())
        if isinstance(parsed, (dict, list)):
            return "json"
    except (json.JSONDecodeError, ValueError):
        # try line-delimited JSON
        lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
        if lines and all(_is_json_obj(l) for l in lines[:5]):
            return "json"
    return "unknown"


def _is_json_obj(s: str) -> bool:
    try:
        v = json.loads(s)
        return isinstance(v, dict)
    except Exception:
        return False


def parse_kubernetes(raw: str) -> dict:
    extracted = {
        "service": None,
        "namespace": "default",
        "error_type": None,
        "severity_hint": "warning",
        "events": [],
    }

    # Extract namespace
    ns_match = re.search(r"namespace[=: ]+(\S+)", raw, re.IGNORECASE)
    if ns_match:
        extracted["namespace"] = ns_match.group(1)

    # Detect known error patterns
    error_patterns = [
        (r"CrashLoopBackOff", "CrashLoopBackOff", "critical"),
        (r"OOMKilled", "OOMKilled", "critical"),
        (r"Liveness probe failed", "liveness_probe_failure", "warning"),
        (r"Readiness probe failed", "readiness_probe_failure", "warning"),
        (r"Failed to pull image|ImagePullBackOff|ErrImagePull", "image_pull_failure", "warning"),
        (r"Evicted", "pod_eviction", "warning"),
        (r"FailedScheduling", "scheduling_failure", "warning"),
        (r"BackOff", "backoff", "warning"),
    ]
    for pattern, error_type, severity in error_patterns:
        if re.search(pattern, raw, re.IGNORECASE):
            extracted["error_type"] = error_type
            extracted["severity_hint"] = severity
            break

    # Extract pod/deployment name
    pod_match = re.search(r"pod[/ ]+([a-z0-9][a-z0-9\-\.]+)", raw, re.IGNORECASE)
    if pod_match:
        extracted["service"] = pod_match.group(1)
    else:
        dep_match = re.search(r"deployment[/ ]+([a-z0-9][a-z0-9\-\.]+)", raw, re.IGNORECASE)
        if dep_match:
            extracted["service"] = dep_match.group(1)

    # Collect event lines
    event_lines = [l.strip() for l in raw.splitlines() if l.strip() and not l.startswith("LAST")]
    extracted["events"] = event_lines[:20]

    return extracted


def parse_nginx(raw: str) -> dict:
    extracted = {
        "service": "nginx",
        "error_type": None,
        "severity_hint": "info",
        "status_codes": {},
        "errors": [],
    }

    # Count status codes
    status_matches = re.findall(r'" (\d{3}) ', raw)
    for code in status_matches:
        extracted["status_codes"][code] = extracted["status_codes"].get(code, 0) + 1

    # Detect error conditions
    if re.search(r"upstream timed out|upstream prematurely", raw, re.IGNORECASE):
        extracted["error_type"] = "upstream_timeout"
        extracted["severity_hint"] = "critical"
    elif re.search(r"no live upstreams|connect\(\) failed", raw, re.IGNORECASE):
        extracted["error_type"] = "upstream_unavailable"
        extracted["severity_hint"] = "critical"
    elif re.search(r"\[error\]", raw, re.IGNORECASE):
        extracted["error_type"] = "nginx_error"
        extracted["severity_hint"] = "warning"
    elif "503" in extracted["status_codes"] and extracted["status_codes"]["503"] > 0:
        extracted["error_type"] = "service_unavailable_503"
        extracted["severity_hint"] = "critical"
    elif "502" in extracted["status_codes"]:
        extracted["error_type"] = "bad_gateway_502"
        extracted["severity_hint"] = "warning"
    elif "499" in extracted["status_codes"]:
        extracted["error_type"] = "client_closed_request"
        extracted["severity_hint"] = "warning"

    # Collect error lines
    for line in raw.splitlines():
        if re.search(r"\[error\]|\[warn\]|5\d\d", line):
            extracted["errors"].append(line.strip())
    extracted["errors"] = extracted["errors"][:20]

    return extracted


def parse_json_log(raw: str) -> dict:
    extracted = {
        "service": None,
        "error_type": None,
        "severity_hint": "info",
        "entries": [],
    }

    entries = []
    raw = raw.strip()

    # Try single JSON object or array
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            entries = parsed
        elif isinstance(parsed, dict):
            entries = [parsed]
    except json.JSONDecodeError:
        # Line-delimited JSON
        for line in raw.splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    extracted["entries"] = entries[:50]

    # Infer service name
    for entry in entries[:5]:
        for key in ("service", "app", "component", "logger"):
            if key in entry:
                extracted["service"] = str(entry[key])
                break

    # Detect severity from common fields
    severity_counts = {"error": 0, "warn": 0, "info": 0}
    for entry in entries:
        level = str(entry.get("level", entry.get("severity", entry.get("log_level", "")))).lower()
        if "error" in level or "critical" in level or "fatal" in level:
            severity_counts["error"] += 1
        elif "warn" in level:
            severity_counts["warn"] += 1
        else:
            severity_counts["info"] += 1

        # Look for error type in message
        msg = str(entry.get("message", entry.get("msg", entry.get("error", ""))))
        if not extracted["error_type"] and msg:
            for pattern, etype in [
                (r"timeout", "timeout"),
                (r"connection refused", "connection_refused"),
                (r"out of memory|OOM", "oom"),
                (r"panic", "panic"),
                (r"exception", "exception"),
            ]:
                if re.search(pattern, msg, re.IGNORECASE):
                    extracted["error_type"] = etype
                    break

    if severity_counts["error"] > 0:
        extracted["severity_hint"] = "critical" if severity_counts["error"] > 5 else "warning"
    elif severity_counts["warn"] > 0:
        extracted["severity_hint"] = "warning"

    return extracted


def read_log(raw: str) -> dict:
    fmt = detect_format(raw)

    if fmt == "kubernetes":
        extracted = parse_kubernetes(raw)
    elif fmt == "nginx":
        extracted = parse_nginx(raw)
    elif fmt == "json":
        extracted = parse_json_log(raw)
    else:
        extracted = {"service": None, "error_type": "unknown", "severity_hint": "info"}

    return {
        "format": fmt,
        "raw": raw,
        "line_count": len(raw.splitlines()),
        "extracted": extracted,
    }
