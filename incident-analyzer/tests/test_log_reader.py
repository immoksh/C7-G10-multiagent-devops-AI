import pytest
from pathlib import Path
from agents.log_reader import read_log, detect_format

SAMPLE_DIR = Path(__file__).parent.parent / "sample_logs"


def _load(filename):
    return (SAMPLE_DIR / filename).read_text(encoding="utf-8")


# --- Format detection ---

def test_detects_kubernetes_format():
    raw = _load("k8s-events.log")
    result = read_log(raw)
    assert result["format"] == "kubernetes"


def test_detects_nginx_format():
    raw = _load("nginx-error.log")
    result = read_log(raw)
    assert result["format"] == "nginx"


def test_detects_json_format():
    raw = _load("app-structured.json")
    result = read_log(raw)
    assert result["format"] == "json"


def test_unknown_format_fallback():
    result = read_log("this is just some random plain text with no known patterns")
    assert result["format"] == "unknown"
    assert "extracted" in result


# --- Kubernetes parsing ---

def test_detects_crashloopbackoff():
    raw = _load("k8s-events.log")
    result = read_log(raw)
    assert result["extracted"]["error_type"] == "CrashLoopBackOff"
    assert result["extracted"]["severity_hint"] == "critical"


def test_kubernetes_extracts_service():
    raw = _load("k8s-events.log")
    result = read_log(raw)
    assert result["extracted"]["service"] is not None


def test_kubernetes_has_events_list():
    raw = _load("k8s-events.log")
    result = read_log(raw)
    assert isinstance(result["extracted"]["events"], list)
    assert len(result["extracted"]["events"]) > 0


def test_detects_oom_killed():
    raw = "Warning OOMKilled pod/worker-abc123 Container exceeded memory limit"
    result = read_log(raw)
    assert result["extracted"]["error_type"] == "OOMKilled"
    assert result["extracted"]["severity_hint"] == "critical"


# --- Nginx parsing ---

def test_detects_upstream_timeout():
    raw = _load("nginx-error.log")
    result = read_log(raw)
    assert result["extracted"]["error_type"] == "upstream_timeout"
    assert result["extracted"]["severity_hint"] == "critical"


def test_nginx_counts_status_codes():
    raw = _load("nginx-error.log")
    result = read_log(raw)
    codes = result["extracted"]["status_codes"]
    assert "503" in codes
    assert codes["503"] > 0


def test_nginx_collects_error_lines():
    raw = _load("nginx-error.log")
    result = read_log(raw)
    assert len(result["extracted"]["errors"]) > 0


def test_detects_503_without_error_log():
    raw = '10.0.0.1 - - [01/Jan/2024:00:00:00 +0000] "GET / HTTP/1.1" 503 182 "-" "curl/7"'
    result = read_log(raw)
    assert result["format"] == "nginx"
    assert result["extracted"]["severity_hint"] == "critical"


# --- JSON parsing ---

def test_json_extracts_service_name():
    raw = _load("app-structured.json")
    result = read_log(raw)
    assert result["extracted"]["service"] == "payment-service"


def test_json_detects_connection_refused():
    raw = _load("app-structured.json")
    result = read_log(raw)
    assert result["extracted"]["error_type"] == "connection_refused"


def test_json_severity_elevated_on_errors():
    raw = _load("app-structured.json")
    result = read_log(raw)
    assert result["extracted"]["severity_hint"] in ("warning", "critical")


def test_json_single_object():
    raw = '{"level": "error", "service": "api", "message": "timeout connecting to redis"}'
    result = read_log(raw)
    assert result["format"] == "json"
    assert result["extracted"]["service"] == "api"
    assert result["extracted"]["error_type"] == "timeout"


# --- Common fields ---

def test_result_has_line_count():
    raw = _load("k8s-events.log")
    result = read_log(raw)
    assert isinstance(result["line_count"], int)
    assert result["line_count"] > 0


def test_result_preserves_raw():
    raw = _load("nginx-error.log")
    result = read_log(raw)
    assert result["raw"] == raw
