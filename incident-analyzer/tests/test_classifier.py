import pytest
from unittest.mock import patch, MagicMock
from agents.classifier import classify, _extract_json

PARSED_K8S = {
    "format": "kubernetes",
    "raw": "Warning CrashLoopBackOff pod/api-deployment Back-off restarting failed container",
    "line_count": 1,
    "extracted": {
        "service": "api-deployment",
        "error_type": "CrashLoopBackOff",
        "severity_hint": "critical",
        "events": [],
    },
}

PARSED_NGINX = {
    "format": "nginx",
    "raw": "upstream timed out (110) while reading response header from upstream",
    "line_count": 1,
    "extracted": {
        "service": "nginx",
        "error_type": "upstream_timeout",
        "severity_hint": "critical",
        "status_codes": {"503": 3},
        "errors": [],
    },
}

VALID_LLM_RESPONSE = """{
  "severity": "critical",
  "root_cause": "pod_crashloop",
  "confidence": 0.93,
  "reasoning": "Container is in CrashLoopBackOff, indicating repeated startup failure.",
  "affected_service": "api-deployment",
  "estimated_impact": "Service unavailable for all users"
}"""

GARBAGE_LLM_RESPONSE = "I'm sorry, I cannot analyze that log."


def _mock_llm(response_text):
    mock = MagicMock()
    response = MagicMock()
    response.content = response_text
    mock.invoke.return_value = response
    return mock


# --- JSON extraction utility ---

def test_extract_json_from_clean_string():
    result = _extract_json('{"key": "value", "num": 1}')
    assert result == {"key": "value", "num": 1}


def test_extract_json_from_markdown_block():
    text = "Here is the result:\n```json\n{\"severity\": \"critical\"}\n```"
    result = _extract_json(text)
    assert result.get("severity") == "critical"


def test_extract_json_returns_empty_on_garbage():
    result = _extract_json("no json here at all")
    assert result == {}


# --- Classifier with mocked LLM ---

@patch("agents.classifier._get_llm")
def test_returns_severity_field(mock_get_llm):
    mock_get_llm.return_value = _mock_llm(VALID_LLM_RESPONSE)
    result = classify(PARSED_K8S)
    assert result["severity"] in ("critical", "warning", "info")


@patch("agents.classifier._get_llm")
def test_returns_confidence_float(mock_get_llm):
    mock_get_llm.return_value = _mock_llm(VALID_LLM_RESPONSE)
    result = classify(PARSED_K8S)
    assert isinstance(result["confidence"], float)
    assert 0.0 <= result["confidence"] <= 1.0


@patch("agents.classifier._get_llm")
def test_returns_root_cause(mock_get_llm):
    mock_get_llm.return_value = _mock_llm(VALID_LLM_RESPONSE)
    result = classify(PARSED_K8S)
    assert result.get("root_cause") == "pod_crashloop"


@patch("agents.classifier._get_llm")
def test_returns_reasoning(mock_get_llm):
    mock_get_llm.return_value = _mock_llm(VALID_LLM_RESPONSE)
    result = classify(PARSED_K8S)
    assert isinstance(result.get("reasoning"), str)
    assert len(result["reasoning"]) > 0


@patch("agents.classifier._get_llm")
def test_falls_back_severity_on_garbage_response(mock_get_llm):
    mock_get_llm.return_value = _mock_llm(GARBAGE_LLM_RESPONSE)
    result = classify(PARSED_K8S)
    # Falls back to severity_hint from parser
    assert result["severity"] == "critical"


@patch("agents.classifier._get_llm")
def test_falls_back_root_cause_on_garbage_response(mock_get_llm):
    mock_get_llm.return_value = _mock_llm(GARBAGE_LLM_RESPONSE)
    result = classify(PARSED_K8S)
    assert result["root_cause"] == "CrashLoopBackOff"


@patch("agents.classifier._get_llm")
def test_falls_back_confidence_on_garbage_response(mock_get_llm):
    mock_get_llm.return_value = _mock_llm(GARBAGE_LLM_RESPONSE)
    result = classify(PARSED_K8S)
    assert result["confidence"] == 0.5


@patch("agents.classifier._get_llm")
def test_nginx_classification(mock_get_llm):
    nginx_response = """{
      "severity": "critical",
      "root_cause": "upstream_timeout",
      "confidence": 0.88,
      "reasoning": "Multiple upstream timeout errors in nginx logs.",
      "affected_service": "nginx",
      "estimated_impact": "All requests returning 503"
    }"""
    mock_get_llm.return_value = _mock_llm(nginx_response)
    result = classify(PARSED_NGINX)
    assert result["severity"] == "critical"
    assert result["root_cause"] == "upstream_timeout"
