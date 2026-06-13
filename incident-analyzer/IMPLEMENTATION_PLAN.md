# DevOps Incident Analyzer — Implementation Plan

## Context

Build an AI-powered multi-agent DevOps incident analysis platform as a portfolio project targeting senior SRE/DevOps engineers. The app accepts log file uploads, routes them through a LangGraph orchestrated multi-agent pipeline, and produces structured incident reports with mock Slack/Jira output — all visible in a Streamlit UI deployed on Hugging Face Spaces.

**Stack:** Streamlit · LangGraph · Qwen2.5-72B-Instruct (HF Inference API) · ChromaDB · LangChain · requirements.txt

---

## Folder Structure

```
incident-analyzer/
├── app.py                          # Streamlit entrypoint
├── requirements.txt
├── .env.example
├── BRD.md                          # Business Requirements Document
├── IMPLEMENTATION_PLAN.md          # This file
│
├── agents/
│   ├── __init__.py
│   ├── log_reader.py               # Regex/Grok parser — no LLM
│   ├── classifier.py               # HF model: severity + root cause + confidence
│   ├── remediation.py              # RAG over ChromaDB runbooks
│   ├── jira_agent.py               # Mock Jira ticket builder
│   └── slack_agent.py              # Mock Slack card builder
│
├── graph/
│   └── workflow.py                 # LangGraph StateGraph definition
│
├── vectorstore/
│   ├── ingest.py                   # One-time runbook ingestion script
│   └── chroma_db/                  # Persisted ChromaDB (gitignored large files)
│
├── prompts/
│   ├── classifier_prompt.txt
│   └── remediation_prompt.txt
│
├── data/
│   └── runbooks/                   # 5 real runbooks (markdown)
│       ├── k8s-crashloop.md
│       ├── k8s-oom.md
│       ├── nginx-503.md
│       ├── nginx-upstream-timeout.md
│       └── generic-db-connection.md
│
├── sample_logs/                    # Demo log files for reviewers
│   ├── k8s-events.log
│   ├── nginx-error.log
│   └── app-structured.json
│
└── tests/
    ├── test_log_reader.py          # 17 tests — no mocks
    ├── test_jira_agent.py          # 12 tests — pure functions
    ├── test_slack_agent.py         # 12 tests — pure functions
    ├── test_classifier.py          # 11 tests — mocked LLM
    ├── test_remediation.py         #  7 tests — mocked RAG + LLM
    └── test_workflow.py            #  9 tests — integration
```

---

## Implementation Phases

### Phase 1 — Project Scaffold ✅
- Create folder structure
- `requirements.txt`: `streamlit langgraph langchain langchain-huggingface langchain-text-splitters chromadb python-dotenv sentence-transformers`
- `.env.example` with `HF_TOKEN=`
- `.gitignore` excluding `.env` and `chroma_db/`
- Full `app.py` with 3-tab Streamlit UI

### Phase 2 — Log Reader Agent (`agents/log_reader.py`) ✅
- **No LLM.** Pure regex/string parsing.
- Detect format: Kubernetes (`CrashLoopBackOff`, `OOMKilled`, `LAST SEEN`), Nginx (status codes, `upstream timed out`), JSON (`json.loads`)
- Extract fields into normalized dict:
  ```python
  {
    "format": "kubernetes",
    "raw": "...",
    "line_count": 8,
    "extracted": {"service": "api", "error_type": "CrashLoopBackOff", "severity_hint": "critical"}
  }
  ```
- Support 3 formats: Kubernetes events, Nginx access/error, generic JSON structured logs
- Include 3 sample log files in `sample_logs/` — one per format

### Phase 3 — Classifier Agent (`agents/classifier.py`) ✅
- Uses `HuggingFaceEndpoint` with `Qwen/Qwen2.5-72B-Instruct`
- Prompt in `prompts/classifier_prompt.txt` — structured output request
- Returns:
  ```json
  {
    "severity": "critical",
    "root_cause": "pod_crashloop",
    "confidence": 0.91,
    "reasoning": "...",
    "affected_service": "api-deployment",
    "estimated_impact": "..."
  }
  ```
- JSON extraction with regex fallback if LLM returns invalid JSON
- Falls back to parser `severity_hint` and `error_type` on failure

### Phase 4 — Runbooks + ChromaDB (`vectorstore/`) ✅
- 5 real runbooks in `data/runbooks/`: k8s-crashloop, k8s-oom, nginx-503, nginx-upstream-timeout, generic-db-connection
- `ingest.py`: chunk runbooks with `MarkdownTextSplitter` → embed with `sentence-transformers/all-MiniLM-L6-v2` → persist to ChromaDB
- **Run once:** `python vectorstore/ingest.py` from `incident-analyzer/`
- Commit `chroma_db/` to repo (no re-ingestion needed for demo)

### Phase 5 — Remediation Agent (`agents/remediation.py`) ✅
- RAG: embed query from classifier output → retrieve top 3 runbook chunks from ChromaDB
- Pass chunks + incident summary to Qwen2.5 for synthesis
- Returns:
  ```json
  {
    "fix_steps": ["step1", "step2", "step3"],
    "source_runbook": "k8s-crashloop.md",
    "cited_chunk": "...",
    "estimated_resolution_time": "5-15 minutes",
    "escalation_needed": false
  }
  ```
- **Always cites source runbook** — key signal for senior engineer audience
- Gracefully handles missing ChromaDB (returns fallback steps)

### Phase 6 — Mock Agents ✅

**Jira (`agents/jira_agent.py`)** — pure data builder, no LLM:
```python
def create_mock_ticket(classification, remediation) -> dict | None:
    # Returns None for info severity
    # P1 for critical, P2 for warning
    return {
      "ticket_id": f"OPS-{random.randint(100,999)}",
      "priority": severity_to_priority(severity),
      "summary": f"{root_cause} — {service}",
      "description": "...",
      "assignee": "oncall-sre"
    }
```

**Slack (`agents/slack_agent.py`)** — builds formatted card dict, no LLM:
```python
def build_mock_slack_card(classification, remediation, jira_ticket) -> dict:
    # critical → #incidents, warning → #sre-alerts
    return {
      "channel": "#incidents",
      "emoji": "🚨",
      "color": "#e01e5a",
      "blocks": [...]
    }
```

### Phase 7 — LangGraph Orchestrator (`graph/workflow.py`) ✅
```python
class IncidentState(TypedDict):
    raw_log: str
    parsed: dict
    classification: dict
    remediation: dict
    jira_ticket: dict | None   # None if not critical/warning
    slack_card: dict
    completed_steps: list[str]
    error: str | None

graph = StateGraph(IncidentState)
graph.add_node("log_reader", node_log_reader)
graph.add_node("classifier", node_classifier)
graph.add_node("remediation", node_remediation)
graph.add_node("jira_agent", node_jira_agent)
graph.add_node("slack_agent", node_slack_agent)

graph.add_edge(START, "log_reader")
graph.add_edge("log_reader", "classifier")
graph.add_edge("classifier", "remediation")
graph.add_conditional_edges("remediation", route_by_severity,
    {"critical": "jira_agent", "non_critical": "slack_agent"})
graph.add_edge("jira_agent", "slack_agent")
graph.add_edge("slack_agent", END)
```

### Phase 8 — Streamlit UI (`app.py`) ✅

3-tab layout:

```
[Upload Log] ──► [Run Analysis]

Tab 1: Pipeline View
  • Agent step progress (✅ completed / ⏭️ skipped)
  • Full pipeline state JSON expander

Tab 2: Incident Report
  • Severity badge (color-coded metric)
  • Confidence progress bar
  • Root cause + model reasoning expander
  • Fix steps (numbered)
  • Source runbook citation (expander with cited chunk)
  • Raw JSON toggles for classification + remediation

Tab 3: Integrations
  • [MOCK SLACK] dark-themed formatted card
  • [MOCK JIRA] ticket panel with priority badge
  • Raw JSON toggles for both
```

Key UI decisions for senior engineer audience:
- Raw JSON toggle on every output panel
- RAG transparency: cited runbook chunk always visible
- Confidence score as `st.progress()` bar

### Phase 9 — HF Spaces Deployment ✅

`README.md` frontmatter:
```yaml
---
title: DevOps Incident Analyzer
emoji: 🚨
colorFrom: red
colorTo: orange
sdk: streamlit
sdk_version: 1.35.0
app_file: app.py
pinned: false
---
```

- Add `HF_TOKEN` as HF Space secret (Settings → Variables and secrets)
- Commit `vectorstore/chroma_db/` so no re-ingestion needed on Space startup
- `.gitignore` excludes `.env` but not `chroma_db/`

---

## Build Order

| Step | Task | Status |
|---|---|---|
| 1 | Scaffold + `app.py` stub | ✅ Done |
| 2 | Log reader + 3 sample log files | ✅ Done |
| 3 | Runbooks (5) + ChromaDB ingest script | ✅ Done |
| 4 | Classifier agent + prompt | ✅ Done |
| 5 | Remediation agent + prompt | ✅ Done |
| 6 | Mock Jira + Slack agents | ✅ Done |
| 7 | LangGraph workflow wiring | ✅ Done |
| 8 | Full Streamlit UI (3 tabs) | ✅ Done |
| 9 | HF Spaces README + deployment config | ✅ Done |
| 10 | Test suite (68 tests across 5 files) | ✅ Done |

---

## Setup Instructions

```bash
# 1. Install dependencies
cd incident-analyzer
python -m pip install -r requirements.txt

# 2. Set HF token
cp .env.example .env
# Edit .env and add: HF_TOKEN=hf_your_token_here

# 3. Ingest runbooks into ChromaDB (run once)
python vectorstore/ingest.py

# 4. Run the app
python -m streamlit run app.py

# 5. Run tests
python -m pytest tests/ -v --tb=short
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Target user | Senior SRE | No cookbook UX; raw JSON + citations instead |
| UI framework | Streamlit | HF Spaces native; fastest to build |
| LLM | Qwen2.5-72B-Instruct | Best reasoning on HF Inference API |
| Log formats | K8s + Nginx + JSON | Covers 90% of real DevOps incidents |
| Slack/Jira | Mocked | Portfolio demo — realistic UI, no credentials |
| Cookbook agent | Excluded | Not relevant for senior engineer audience |
| Auto-remediation | Excluded | Scope risk without human approval gate |
| ChromaDB | Committed to repo | Eliminates re-ingestion for demo reviewers |

---

## Verification Checklist

- [ ] Upload `k8s-events.log` → format=kubernetes, severity=critical, Jira ticket created
- [ ] Upload `nginx-error.log` → format=nginx, remediation cites nginx runbook
- [ ] Upload `app-structured.json` → format=json, service=payment-service extracted
- [ ] Critical incident → all 5 agents show ✅ in Pipeline View
- [ ] Non-critical incident → Jira Agent shows ⏭️ skipped, `jira_ticket` is None
- [ ] Raw JSON toggle visible and correct on all panels
- [ ] Confidence score renders as progress bar
- [ ] Cited runbook chunk visible in expander
- [ ] `python -m pytest tests/ -v` — all tests pass
- [ ] HF Spaces loads without local `.env` (uses Space secrets)
