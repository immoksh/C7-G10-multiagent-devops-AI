import pytest
from unittest.mock import patch, MagicMock
from agents.remediation import remediate, _extract_json

CLASSIFICATION_CRITICAL = {
    "severity": "critical",
    "root_cause": "pod_crashloop",
    "affected_service": "api-deployment",
    "reasoning": "CrashLoopBackOff detected in kubernetes events.",
    "confidence": 0.92,
}

CLASSIFICATION_WARNING = {
    "severity": "warning",
    "root_cause": "upstream_timeout",
    "affected_service": "nginx",
    "reasoning": "Nginx upstream timing out.",
    "confidence": 0.80,
}

VALID_LLM_RESPONSE = """{
  "fix_steps": [
    "kubectl logs api-deployment --previous -n default",
    "kubectl describe pod api-deployment -n default",
    "kubectl rollout restart deployment/api-deployment -n default",
    "kubectl rollout status deployment/api-deployment"
  ],
  "estimated_resolution_time": "5-15 minutes",
  "escalation_needed": false,
  "escalation_reason": ""
}"""

MOCK_DOC_1 = MagicMock()
MOCK_DOC_1.page_content = "Check pod logs with kubectl logs --previous. Restart with kubectl rollout restart."
MOCK_DOC_1.metadata = {"source_file": "k8s-crashloop.md"}

MOCK_DOC_2 = MagicMock()
MOCK_DOC_2.page_content = "Verify OOMKilled exit code 137 and increase memory limits."
MOCK_DOC_2.metadata = {"source_file": "k8s-oom.md"}


def _mock_llm(response_text):
    mock = MagicMock()
    response = MagicMock()
    response.content = response_text
    mock.invoke.return_value = response
    return mock


def _mock_vectorstore(docs):
    mock = MagicMock()
    mock.similarity_search.return_value = docs
    return mock


@patch("agents.remediation._get_llm")
@patch("agents.remediation.Chroma")
@patch("agents.remediation.CHROMA_DIR")
def test_returns_fix_steps_list(mock_dir, mock_chroma_cls, mock_get_llm):
    mock_dir.exists.return_value = True
    mock_chroma_cls.return_value = _mock_vectorstore([MOCK_DOC_1, MOCK_DOC_2])
    mock_get_llm.return_value = _mock_llm(VALID_LLM_RESPONSE)

    result = remediate(CLASSIFICATION_CRITICAL)
    assert isinstance(result["fix_steps"], list)
    assert len(result["fix_steps"]) > 0


@patch("agents.remediation._get_llm")
@patch("agents.remediation.Chroma")
@patch("agents.remediation.CHROMA_DIR")
def test_cites_source_runbook(mock_dir, mock_chroma_cls, mock_get_llm):
    mock_dir.exists.return_value = True
    mock_chroma_cls.return_value = _mock_vectorstore([MOCK_DOC_1, MOCK_DOC_2])
    mock_get_llm.return_value = _mock_llm(VALID_LLM_RESPONSE)

    result = remediate(CLASSIFICATION_CRITICAL)
    assert result["source_runbook"].endswith(".md")


@patch("agents.remediation._get_llm")
@patch("agents.remediation.Chroma")
@patch("agents.remediation.CHROMA_DIR")
def test_cited_chunk_is_string(mock_dir, mock_chroma_cls, mock_get_llm):
    mock_dir.exists.return_value = True
    mock_chroma_cls.return_value = _mock_vectorstore([MOCK_DOC_1])
    mock_get_llm.return_value = _mock_llm(VALID_LLM_RESPONSE)

    result = remediate(CLASSIFICATION_CRITICAL)
    assert isinstance(result["cited_chunk"], str)
    assert len(result["cited_chunk"]) > 0


@patch("agents.remediation._get_llm")
@patch("agents.remediation.CHROMA_DIR")
def test_handles_missing_chroma_db(mock_dir, mock_get_llm):
    mock_dir.exists.return_value = False
    mock_get_llm.return_value = _mock_llm(VALID_LLM_RESPONSE)

    result = remediate(CLASSIFICATION_CRITICAL)
    assert isinstance(result["fix_steps"], list)
    assert len(result["fix_steps"]) > 0


@patch("agents.remediation._get_llm")
@patch("agents.remediation.Chroma")
@patch("agents.remediation.CHROMA_DIR")
def test_fix_steps_are_strings(mock_dir, mock_chroma_cls, mock_get_llm):
    mock_dir.exists.return_value = True
    mock_chroma_cls.return_value = _mock_vectorstore([MOCK_DOC_1])
    mock_get_llm.return_value = _mock_llm(VALID_LLM_RESPONSE)

    result = remediate(CLASSIFICATION_CRITICAL)
    for step in result["fix_steps"]:
        assert isinstance(step, str)


@patch("agents.remediation._get_llm")
@patch("agents.remediation.Chroma")
@patch("agents.remediation.CHROMA_DIR")
def test_returns_estimated_resolution_time(mock_dir, mock_chroma_cls, mock_get_llm):
    mock_dir.exists.return_value = True
    mock_chroma_cls.return_value = _mock_vectorstore([MOCK_DOC_1])
    mock_get_llm.return_value = _mock_llm(VALID_LLM_RESPONSE)

    result = remediate(CLASSIFICATION_CRITICAL)
    assert "estimated_resolution_time" in result
