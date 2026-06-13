import pytest
from agents.slack_agent import build_mock_slack_card

CLASSIFICATION_CRITICAL = {
    "severity": "critical",
    "root_cause": "pod_crashloop",
    "affected_service": "api-deployment",
    "confidence": 0.92,
    "reasoning": "CrashLoopBackOff detected.",
}

CLASSIFICATION_WARNING = {
    "severity": "warning",
    "root_cause": "upstream_timeout",
    "affected_service": "nginx",
    "confidence": 0.75,
    "reasoning": "Upstream timing out.",
}

REMEDIATION = {
    "fix_steps": [
        "kubectl logs api-deployment --previous",
        "kubectl rollout restart deployment/api-deployment",
    ],
    "source_runbook": "k8s-crashloop.md",
    "estimated_resolution_time": "5-15 minutes",
}

JIRA_TICKET = {
    "ticket_id": "OPS-342",
    "priority": "P1",
    "summary": "Pod Crashloop — api-deployment",
    "assignee": "oncall-sre",
    "status": "Open",
}


def test_critical_routes_to_incidents_channel():
    card = build_mock_slack_card(CLASSIFICATION_CRITICAL, REMEDIATION, JIRA_TICKET)
    assert card["channel"] == "#incidents"


def test_warning_routes_to_sre_alerts_channel():
    card = build_mock_slack_card(CLASSIFICATION_WARNING, REMEDIATION, None)
    assert card["channel"] == "#sre-alerts"


def test_card_has_blocks():
    card = build_mock_slack_card(CLASSIFICATION_CRITICAL, REMEDIATION, JIRA_TICKET)
    assert isinstance(card["blocks"], list)
    assert len(card["blocks"]) > 0


def test_card_has_required_fields():
    card = build_mock_slack_card(CLASSIFICATION_CRITICAL, REMEDIATION, JIRA_TICKET)
    for field in ("channel", "emoji", "color", "severity", "text", "blocks"):
        assert field in card, f"Missing field: {field}"


def test_critical_uses_alarm_emoji():
    card = build_mock_slack_card(CLASSIFICATION_CRITICAL, REMEDIATION, JIRA_TICKET)
    assert card["emoji"] == "🚨"


def test_warning_uses_warning_emoji():
    card = build_mock_slack_card(CLASSIFICATION_WARNING, REMEDIATION, None)
    assert card["emoji"] == "⚠️"


def test_includes_jira_ticket_id():
    card = build_mock_slack_card(CLASSIFICATION_CRITICAL, REMEDIATION, JIRA_TICKET)
    card_str = str(card)
    assert "OPS-342" in card_str


def test_no_jira_shows_na():
    card = build_mock_slack_card(CLASSIFICATION_CRITICAL, REMEDIATION, None)
    card_str = str(card)
    assert "N/A" in card_str


def test_text_contains_root_cause():
    card = build_mock_slack_card(CLASSIFICATION_CRITICAL, REMEDIATION, JIRA_TICKET)
    assert "pod_crashloop" in card["text"]


def test_text_contains_service():
    card = build_mock_slack_card(CLASSIFICATION_CRITICAL, REMEDIATION, JIRA_TICKET)
    assert "api-deployment" in card["text"]


def test_critical_color_is_red():
    card = build_mock_slack_card(CLASSIFICATION_CRITICAL, REMEDIATION, JIRA_TICKET)
    assert card["color"] == "#e01e5a"


def test_warning_color_is_yellow():
    card = build_mock_slack_card(CLASSIFICATION_WARNING, REMEDIATION, None)
    assert card["color"] == "#ecb22e"
