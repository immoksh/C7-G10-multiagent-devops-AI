from typing import TypedDict
from langgraph.graph import StateGraph, START, END

from agents.log_reader import read_log
from agents.classifier import classify
from agents.remediation import remediate
from agents.jira_agent import create_mock_ticket
from agents.slack_agent import build_mock_slack_card


class IncidentState(TypedDict):
    raw_log: str
    parsed: dict
    classification: dict
    remediation: dict
    jira_ticket: dict | None
    slack_card: dict
    completed_steps: list[str]
    error: str | None


def node_log_reader(state: IncidentState) -> dict:
    parsed = read_log(state["raw_log"])
    steps = state.get("completed_steps", []) + ["log_reader"]
    return {"parsed": parsed, "completed_steps": steps}


def node_classifier(state: IncidentState) -> dict:
    classification = classify(state["parsed"])
    steps = state.get("completed_steps", []) + ["classifier"]
    return {"classification": classification, "completed_steps": steps}


def node_remediation(state: IncidentState) -> dict:
    remediation = remediate(state["classification"])
    steps = state.get("completed_steps", []) + ["remediation"]
    return {"remediation": remediation, "completed_steps": steps}


def node_jira_agent(state: IncidentState) -> dict:
    ticket = create_mock_ticket(state["classification"], state["remediation"])
    steps = state.get("completed_steps", []) + ["jira_agent"]
    return {"jira_ticket": ticket, "completed_steps": steps}


def node_slack_agent(state: IncidentState) -> dict:
    card = build_mock_slack_card(
        state["classification"],
        state["remediation"],
        state.get("jira_ticket"),
    )
    steps = state.get("completed_steps", []) + ["slack_agent"]
    return {"slack_card": card, "completed_steps": steps}


def route_by_severity(state: IncidentState) -> str:
    severity = state["classification"].get("severity", "info")
    return "critical" if severity == "critical" else "non_critical"


def build_graph() -> StateGraph:
    graph = StateGraph(IncidentState)

    graph.add_node("log_reader", node_log_reader)
    graph.add_node("classifier", node_classifier)
    graph.add_node("remediation", node_remediation)
    graph.add_node("jira_agent", node_jira_agent)
    graph.add_node("slack_agent", node_slack_agent)

    graph.add_edge(START, "log_reader")
    graph.add_edge("log_reader", "classifier")
    graph.add_edge("classifier", "remediation")
    graph.add_conditional_edges(
        "remediation",
        route_by_severity,
        {"critical": "jira_agent", "non_critical": "slack_agent"},
    )
    graph.add_edge("jira_agent", "slack_agent")
    graph.add_edge("slack_agent", END)

    return graph.compile()


_compiled_graph = None


def run_pipeline(raw_log: str) -> dict:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()

    initial_state: IncidentState = {
        "raw_log": raw_log,
        "parsed": {},
        "classification": {},
        "remediation": {},
        "jira_ticket": None,
        "slack_card": {},
        "completed_steps": [],
        "error": None,
    }

    result = _compiled_graph.invoke(initial_state)
    return dict(result)
