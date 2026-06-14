import re

def parse_log(raw_log: str) -> dict:
    """
    Parses raw log strings using regex.
    In a production system, this could use Grok patterns or more complex logic.
    """
    parsed_data = {
        "service": "unknown",
        "severity": "unknown",
        "error_type": "unknown",
        "raw": raw_log
    }

    # Nginx 503 / 504 logs
    if re.search(r'50[34]', raw_log) or re.search(r'upstream', raw_log, re.IGNORECASE):
        parsed_data["service"] = "nginx"
        parsed_data["severity"] = "critical"
        parsed_data["error_type"] = "upstream_timeout"

    # Kubernetes CrashLoopBackOff / OOMKilled
    elif re.search(r'CrashLoopBackOff', raw_log, re.IGNORECASE) or re.search(r'OOMKilled', raw_log, re.IGNORECASE):
        parsed_data["service"] = "kubernetes"
        parsed_data["severity"] = "critical"
        parsed_data["error_type"] = "pod_crashloop"

    return parsed_data
