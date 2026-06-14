"""Agent 3 - Remediation Agent (RAG).

1. Builds a retrieval query from the parsed log + classification.
2. Pulls the top-k matching runbook chunks from the Chroma vector store.
3. Synthesizes a concrete fix + rationale with the LLM, grounded in the
   retrieved runbooks. Falls back to surfacing the best runbook chunk
   verbatim when no LLM is configured.
"""

from __future__ import annotations

from typing import Dict, List

from graph.state import IncidentState
from llm import complete
from vectorstore.ingest import retrieve

SYSTEM = (
    "You are a principal DevOps/SRE engineer. Using ONLY the runbook context "
    "provided, produce a precise remediation. Be specific and actionable, "
    "cite the runbook names you used, and never invent commands that are not "
    "supported by the context."
)

PROMPT_TEMPLATE = """Incident summary: {summary}
Root cause: {root_cause}
Service: {service}
Error type: {error_type}

Relevant runbook context:
{context}

Write a remediation with these sections (markdown):
**Recommended Fix** - the concrete steps to resolve the incident.
**Rationale** - why this fix addresses the root cause.
**Sources** - the runbook names you relied on.
Keep it under 250 words.
"""


def _build_query(parsed: Dict, classification: Dict) -> str:
    parts = [
        classification.get("root_cause", ""),
        parsed.get("error_type", ""),
        parsed.get("service", ""),
        classification.get("summary", ""),
    ]
    return " ".join(p for p in parts if p)


def _format_context(matches: List[Dict]) -> str:
    blocks = []
    for m in matches:
        blocks.append(f"[{m['source']} :: {m.get('heading', '')}]\n{m['text']}")
    return "\n\n---\n\n".join(blocks) if blocks else "No runbooks matched."


def run(state: IncidentState) -> IncidentState:
    parsed = state.get("parsed", {})
    classification = state.get("classification", {})

    query = _build_query(parsed, classification)
    matches = retrieve(query, k=5)
    state["runbook_matches"] = matches

    context = _format_context(matches)
    synthesized = complete(
        PROMPT_TEMPLATE.format(
            summary=classification.get("summary", ""),
            root_cause=classification.get("root_cause", ""),
            service=parsed.get("service", ""),
            error_type=parsed.get("error_type", ""),
            context=context[:6000],
        ),
        system=SYSTEM,
        model=state.get("llm_model"),
    )

    if synthesized:
        remediation = {"fix": synthesized.strip(), "source": "llm"}
    else:
        # Fallback: present the top runbook chunk(s) directly.
        top = matches[0]["text"] if matches else (
            "No runbook match found. Investigate manually: review recent "
            "deploys, check resource limits, and inspect upstream health."
        )
        sources = ", ".join(sorted({m["source"] for m in matches})) or "n/a"
        remediation = {
            "fix": f"**Recommended Fix (from runbook)**\n\n{top}\n\n"
            f"**Sources**: {sources}",
            "source": "runbook_fallback",
        }

    remediation["sources"] = sorted({m["source"] for m in matches})
    state["remediation"] = remediation
    state.setdefault("trace", []).append(
        f"Remediation ({remediation['source']}): "
        f"{len(matches)} runbook chunk(s) retrieved"
    )
    return state
