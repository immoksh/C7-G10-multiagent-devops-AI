"""Shared state object that flows through the LangGraph workflow.

Each agent reads from and writes to this typed dictionary. Using a single
state object keeps the orchestration declarative and makes every step's
contribution traceable in the UI.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class IncidentState(TypedDict, total=False):
    # --- Raw input ---
    raw_log: str

    # --- Run configuration ---
    llm_model: Optional[str]          # user-selected model for this analysis

    # --- Agent 1: Log Reader ---
    parsed: Dict[str, Any]            # structured fields extracted via regex

    # --- Agent 2: Classifier ---
    classification: Dict[str, Any]    # severity, root_cause, confidence, summary

    # --- Agent 3: Remediation (RAG) ---
    runbook_matches: List[Dict[str, Any]]  # top-k retrieved runbook chunks
    remediation: Dict[str, Any]            # synthesized fix + rationale

    # --- Agent 4: Cookbook ---
    cookbook: str                      # markdown recovery checklist

    # --- Agent 5: Jira ---
    jira: Dict[str, Any]               # {created, key, url, dry_run, message}

    # --- Agent 6: Slack ---
    slack: Dict[str, Any]             # {sent, channel, dry_run, message}

    # --- Routing / bookkeeping ---
    is_critical: bool
    trace: List[str]                   # human-readable step log for the UI
    errors: List[str]


def new_state(raw_log: str, llm_model: Optional[str] = None) -> IncidentState:
    return IncidentState(
        raw_log=raw_log,
        llm_model=llm_model,
        parsed={},
        classification={},
        runbook_matches=[],
        remediation={},
        cookbook="",
        jira={},
        slack={},
        is_critical=False,
        trace=[],
        errors=[],
    )
