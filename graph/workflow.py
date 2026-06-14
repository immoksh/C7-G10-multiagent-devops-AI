"""LangGraph orchestrator.

The pipeline is split into two phases so a human can review the analysis
before anything is sent to external systems:

    Phase 1 (analysis):
        START -> log_reader -> classifier -> remediation -> cookbook -> END

    --- human approval gate (handled in the UI) ---

    Phase 2 (dispatch):
        START -> (critical?) --yes--> jira --> slack --> END
                             --no---------------> slack --> END

The orchestrator manages the shared ``IncidentState`` between agents and
performs conditional routing: only critical/high incidents create a Jira
ticket. Slack always fires so on-call always gets a notification — but only
after a human approves the dispatch.
"""

from __future__ import annotations

from typing import Callable

from langgraph.graph import END, START, StateGraph

from agents import (
    classifier,
    cookbook,
    jira_agent,
    log_reader,
    remediation,
    slack_agent,
)
from graph.state import IncidentState, new_state


def _route_after_cookbook(state: IncidentState) -> str:
    """Send critical/high incidents to Jira, otherwise straight to Slack."""
    return "jira" if state.get("is_critical") else "slack"


def _dispatch_entry(state: IncidentState) -> IncidentState:
    """No-op entry node so the dispatch graph can branch conditionally."""
    return state


def build_analysis_graph():
    """Phase 1: read, classify, remediate and build the recovery cookbook.

    Stops before any external system is touched so a human can review.
    """
    graph = StateGraph(IncidentState)

    graph.add_node("log_reader", log_reader.run)
    graph.add_node("classifier", classifier.run)
    graph.add_node("remediation", remediation.run)
    graph.add_node("cookbook", cookbook.run)

    graph.add_edge(START, "log_reader")
    graph.add_edge("log_reader", "classifier")
    graph.add_edge("classifier", "remediation")
    graph.add_edge("remediation", "cookbook")
    graph.add_edge("cookbook", END)

    return graph.compile()


def build_dispatch_graph():
    """Phase 2: file Jira (critical only) and notify Slack.

    Runs only after a human approves the analysis in the UI.
    """
    graph = StateGraph(IncidentState)

    graph.add_node("dispatch_entry", _dispatch_entry)
    graph.add_node("jira", jira_agent.run)
    graph.add_node("slack", slack_agent.run)

    graph.add_edge(START, "dispatch_entry")
    graph.add_conditional_edges(
        "dispatch_entry",
        _route_after_cookbook,
        {"jira": "jira", "slack": "slack"},
    )
    graph.add_edge("jira", "slack")
    graph.add_edge("slack", END)

    return graph.compile()


# Compile once and reuse.
_ANALYSIS_APP = None
_DISPATCH_APP = None


def get_analysis_app():
    global _ANALYSIS_APP
    if _ANALYSIS_APP is None:
        _ANALYSIS_APP = build_analysis_graph()
    return _ANALYSIS_APP


def get_dispatch_app():
    global _DISPATCH_APP
    if _DISPATCH_APP is None:
        _DISPATCH_APP = build_dispatch_graph()
    return _DISPATCH_APP


def analyze(
    raw_log: str,
    model: str | None = None,
    progress: Callable[[str], None] | None = None,
) -> IncidentState:
    """Run the analysis phase (agents 1-4) over a raw log blob.

    This stops *before* Jira/Slack so the result can be presented for human
    approval. Call :func:`dispatch` afterwards to notify external systems.

    ``model`` optionally overrides the configured default LLM so the user can
    choose which model performs the analysis.
    """
    app = get_analysis_app()
    state = new_state(raw_log, llm_model=model)
    result = app.invoke(state)
    if progress:
        for line in result.get("trace", []):
            progress(line)
    return result


def dispatch(
    state: IncidentState,
    progress: Callable[[str], None] | None = None,
) -> IncidentState:
    """Run the dispatch phase (Jira + Slack) on an approved analysis state."""
    app = get_dispatch_app()
    before = len(state.get("trace", []))
    result = app.invoke(state)
    if progress:
        for line in result.get("trace", [])[before:]:
            progress(line)
    return result


if __name__ == "__main__":
    sample = "2024-05-01T10:22:31Z nginx [error] 502 upstream timed out (110: Connection timed out)"
    out = analyze(sample)
    out = dispatch(out)
    import json

    print(json.dumps({k: v for k, v in out.items() if k != "raw_log"}, indent=2, default=str))
