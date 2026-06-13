import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

SAMPLE_DIR = Path(__file__).parent.parent / "sample_logs"

MOCK_CLASSIFICATION_CRITICAL = {
    "severity": "critical",
    "root_cause": "pod_crashloop",
    "affected_service": "api-deployment",
    "confidence": 0.93,
    "reasoning": "CrashLoopBackOff detected.",
    "estimated_impact": "Service unavailable",
}

MOCK_CLASSIFICATION_INFO = {
    "severity": "info",
    "root_cause": "deployment_scaling",
    "affected_service": "api",
    "confidence": 0.99,
    "reasoning": "Normal scaling event.",
    "estimated_impact": "None",
}

MOCK_REMEDIATION = {
    "fix_steps": ["kubectl logs --previous", "kubectl rollout restart deployment/api"],
    "source_runbook": "k8s-crashloop.md",
    "cited_chunk": "Restart the deployment using kubectl rollout restart.",
    "estimated_resolution_time": "5-15 minutes",
    "escalation_needed": False,
    "escalation_reason": "",
}


def _load(filename):
    return (SAMPLE_DIR / filename).read_text(encoding="utf-8")


@patch("graph.workflow.remediate", return_value=MOCK_REMEDIATION)
@patch("graph.workflow.classify", return_value=MOCK_CLASSIFICATION_CRITICAL)
def test_full_pipeline_critical_k8s(mock_classify, mock_remediate):
    from graph.workflow import run_pipeline
    result = run_pipeline(_load("k8s-events.log"))

    assert "parsed" in result
    assert "classification" in result
    assert "remediation" in result
    assert "slack_card" in result


@patch("graph.workflow.remediate", return_value=MOCK_REMEDIATION)
@patch("graph.workflow.classify", return_value=MOCK_CLASSIFICATION_CRITICAL)
def test_critical_pipeline_creates_jira_ticket(mock_classify, mock_remediate):
    from graph.workflow import run_pipeline
    result = run_pipeline(_load("k8s-events.log"))

    assert result["jira_ticket"] is not None


@patch("graph.workflow.remediate", return_value=MOCK_REMEDIATION)
@patch("graph.workflow.classify", return_value=MOCK_CLASSIFICATION_CRITICAL)
def test_critical_pipeline_completed_steps(mock_classify, mock_remediate):
    from graph.workflow import run_pipeline
    result = run_pipeline(_load("k8s-events.log"))

    steps = result["completed_steps"]
    assert "log_reader" in steps
    assert "classifier" in steps
    assert "remediation" in steps
    assert "jira_agent" in steps
    assert "slack_agent" in steps


@patch("graph.workflow.remediate", return_value=MOCK_REMEDIATION)
@patch("graph.workflow.classify", return_value=MOCK_CLASSIFICATION_INFO)
def test_non_critical_skips_jira(mock_classify, mock_remediate):
    from graph.workflow import run_pipeline
    result = run_pipeline(_load("k8s-events.log"))

    assert result["jira_ticket"] is None


@patch("graph.workflow.remediate", return_value=MOCK_REMEDIATION)
@patch("graph.workflow.classify", return_value=MOCK_CLASSIFICATION_INFO)
def test_non_critical_jira_not_in_steps(mock_classify, mock_remediate):
    from graph.workflow import run_pipeline
    result = run_pipeline(_load("k8s-events.log"))

    assert "jira_agent" not in result["completed_steps"]


@patch("graph.workflow.remediate", return_value=MOCK_REMEDIATION)
@patch("graph.workflow.classify", return_value=MOCK_CLASSIFICATION_CRITICAL)
def test_pipeline_state_has_all_keys(mock_classify, mock_remediate):
    from graph.workflow import run_pipeline
    result = run_pipeline(_load("nginx-error.log"))

    required_keys = ["parsed", "classification", "remediation", "jira_ticket", "slack_card", "completed_steps"]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"


@patch("graph.workflow.remediate", return_value=MOCK_REMEDIATION)
@patch("graph.workflow.classify", return_value=MOCK_CLASSIFICATION_CRITICAL)
def test_pipeline_slack_card_populated(mock_classify, mock_remediate):
    from graph.workflow import run_pipeline
    result = run_pipeline(_load("nginx-error.log"))

    assert isinstance(result["slack_card"], dict)
    assert len(result["slack_card"]) > 0


@patch("graph.workflow.remediate", return_value=MOCK_REMEDIATION)
@patch("graph.workflow.classify", return_value=MOCK_CLASSIFICATION_CRITICAL)
def test_pipeline_log_reader_detects_format(mock_classify, mock_remediate):
    from graph.workflow import run_pipeline
    result = run_pipeline(_load("k8s-events.log"))

    assert result["parsed"]["format"] == "kubernetes"


@patch("graph.workflow.remediate", return_value=MOCK_REMEDIATION)
@patch("graph.workflow.classify", return_value=MOCK_CLASSIFICATION_CRITICAL)
def test_pipeline_json_log(mock_classify, mock_remediate):
    from graph.workflow import run_pipeline
    result = run_pipeline(_load("app-structured.json"))

    assert result["parsed"]["format"] == "json"
    assert "completed_steps" in result
