import re
import pytest
from agents.jira_agent import create_mock_ticket

CLASSIFICATION_CRITICAL = {
    "severity": "critical",
    "root_cause": "pod_crashloop",
    "affected_service": "api-deployment",
    "reasoning": "Container repeatedly crashing with CrashLoopBackOff.",
    "confidence": 0.92,
}

CLASSIFICATION_WARNING = {
    "severity": "warning",
    "root_cause": "upstream_timeout",
    "affected_service": "nginx",
    "reasoning": "Upstream timing out intermittently.",
    "confidence": 0.75,
}

CLASSIFICATION_INFO = {
    "severity": "info",
    "root_cause": "deployment_scaling",
    "affected_service": "api",
    "reasoning": "Normal scaling event.",
    "confidence": 0.99,
}

REMEDIATION = {
    "fix_steps": [
        "kubectl logs api-deployment --previous",
        "kubectl rollout restart deployment/api-deployment",
        "kubectl rollout status deployment/api-deployment",
    ],
    "source_runbook": "k8s-crashloop.md",
    "estimated_resolution_time": "5-15 minutes",
}


def test_critical_creates_ticket():
    ticket = create_mock_ticket(CLASSIFICATION_CRITICAL, REMEDIATION)
    assert ticket is not None


def test_critical_priority_is_p1():
    ticket = create_mock_ticket(CLASSIFICATION_CRITICAL, REMEDIATION)
    assert ticket["priority"] == "P1"


def test_warning_creates_ticket():
    ticket = create_mock_ticket(CLASSIFICATION_WARNING, REMEDIATION)
    assert ticket is not None


def test_warning_priority_is_p2():
    ticket = create_mock_ticket(CLASSIFICATION_WARNING, REMEDIATION)
    assert ticket["priority"] == "P2"


def test_info_returns_none():
    ticket = create_mock_ticket(CLASSIFICATION_INFO, REMEDIATION)
    assert ticket is None


def test_ticket_has_required_fields():
    ticket = create_mock_ticket(CLASSIFICATION_CRITICAL, REMEDIATION)
    for field in ("ticket_id", "summary", "assignee", "status", "description", "priority"):
        assert field in ticket, f"Missing field: {field}"


def test_ticket_id_format():
    ticket = create_mock_ticket(CLASSIFICATION_CRITICAL, REMEDIATION)
    assert re.match(r"OPS-\d{3}", ticket["ticket_id"])


def test_ticket_assignee_is_oncall():
    ticket = create_mock_ticket(CLASSIFICATION_CRITICAL, REMEDIATION)
    assert ticket["assignee"] == "oncall-sre"


def test_ticket_status_is_open():
    ticket = create_mock_ticket(CLASSIFICATION_CRITICAL, REMEDIATION)
    assert ticket["status"] == "Open"


def test_ticket_summary_contains_service():
    ticket = create_mock_ticket(CLASSIFICATION_CRITICAL, REMEDIATION)
    assert "api-deployment" in ticket["summary"]


def test_ticket_description_contains_root_cause():
    ticket = create_mock_ticket(CLASSIFICATION_CRITICAL, REMEDIATION)
    assert "pod_crashloop" in ticket["description"]


def test_ticket_description_contains_runbook():
    ticket = create_mock_ticket(CLASSIFICATION_CRITICAL, REMEDIATION)
    assert "k8s-crashloop.md" in ticket["description"]
