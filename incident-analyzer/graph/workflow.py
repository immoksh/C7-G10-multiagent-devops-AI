from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from agents.log_reader import parse_log
from agents.classifier import classify_incident
from agents.remediation import get_remediation_docs
from agents.cookbook import generate_cookbook
from agents.jira_agent import create_jira_ticket
from agents.slack_agent import send_slack_notification

# Define State
class IncidentState(TypedDict):
    raw_log: str
    parsed_log: Optional[dict]
    classification: Optional[dict]
    remediation_docs: Optional[list]
    cookbook: Optional[str]
    ticket_id: Optional[str]
    slack_status: Optional[str]

# Node Functions
def log_reader_node(state: IncidentState):
    parsed = parse_log(state["raw_log"])
    return {"parsed_log": parsed}

def classifier_node(state: IncidentState):
    classification = classify_incident(state["parsed_log"])
    return {"classification": classification}

def remediation_node(state: IncidentState):
    docs = get_remediation_docs(state["classification"], state["parsed_log"])
    return {"remediation_docs": docs}

def cookbook_node(state: IncidentState):
    cookbook = generate_cookbook(state["classification"], state["remediation_docs"])
    return {"cookbook": cookbook}

def jira_node(state: IncidentState):
    ticket_id = create_jira_ticket(state["classification"], state["cookbook"])
    return {"ticket_id": ticket_id}

def slack_node(state: IncidentState):
    status = send_slack_notification(state["classification"], state.get("ticket_id"), state["cookbook"])
    return {"slack_status": status}

# Conditional Logic
def route_after_cookbook(state: IncidentState):
    severity = state["classification"].get("severity", "info").lower()
    if severity == "critical":
        return "jira_node"
    return "slack_node"

# Build Graph
def create_workflow():
    workflow = StateGraph(IncidentState)

    # Add Nodes
    workflow.add_node("log_reader_node", log_reader_node)
    workflow.add_node("classifier_node", classifier_node)
    workflow.add_node("remediation_node", remediation_node)
    workflow.add_node("cookbook_node", cookbook_node)
    workflow.add_node("jira_node", jira_node)
    workflow.add_node("slack_node", slack_node)

    # Set Entry Point
    workflow.set_entry_point("log_reader_node")

    # Add Edges
    workflow.add_edge("log_reader_node", "classifier_node")
    workflow.add_edge("classifier_node", "remediation_node")
    workflow.add_edge("remediation_node", "cookbook_node")

    # Conditional Routing
    workflow.add_conditional_edges(
        "cookbook_node",
        route_after_cookbook,
        {
            "jira_node": "jira_node",
            "slack_node": "slack_node"
        }
    )

    # End paths
    workflow.add_edge("jira_node", "slack_node")
    workflow.add_edge("slack_node", END)

    # Compile
    return workflow.compile()
