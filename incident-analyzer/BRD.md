# Business Requirements Document
## AI-Powered Multi-Agent DevOps Incident Analysis Platform

**Project Name:** DevOps Incident Analyzer
**Version:** 1.0
**Date:** 2026-06-13
**Status:** Approved

---

## 1. Executive Summary

The DevOps Incident Analyzer is an AI-powered platform that automates incident triage and remediation for DevOps and SRE teams. Users upload operational logs which are routed through a multi-agent pipeline orchestrated by LangGraph. The system classifies incidents, retrieves relevant runbooks, synthesizes fix steps, and delivers structured output via mock Slack and Jira integrations — all visible in a Streamlit UI deployed on Hugging Face Spaces.

**Positioning:** "AI-Powered Multi-Agent DevOps Incident Analysis Platform using LangGraph, Hugging Face, ChromaDB, Slack, and Jira"

---

## 2. Business Objectives

| Objective | Description |
|---|---|
| Automate incident triage | Reduce time from log upload to actionable remediation from hours to seconds |
| Demonstrate multi-agent AI | Showcase LangGraph orchestration, RAG, and LLM integration in a single end-to-end solution |
| Portfolio showcase | Demonstrate AI engineering, DevOps, RAG, workflow orchestration, and cloud deployment |
| Reduce MTTR | Provide senior SRE engineers with structured, traceable remediation recommendations |

---

## 3. Target Users

**Primary User:** Senior SRE / DevOps Engineer

**User Profile:**
- Deep operational expertise (Kubernetes, Nginx, cloud infrastructure)
- Expects structured, traceable output with evidence — not hand-holding
- Values: confidence scores, model reasoning, RAG citation transparency, raw JSON access
- Does not need step-by-step checklists; needs fast, authoritative incident context

**Out of Scope Users:**
- Junior engineers (cookbook/checklist UX not prioritized)
- Non-technical stakeholders

---

## 4. Scope

### 4.1 In Scope

| Feature | Description |
|---|---|
| Log file upload | Upload via Streamlit UI (`.log`, `.txt`, `.json`) |
| Multi-format log parsing | Kubernetes events, Nginx access/error logs, structured JSON |
| AI incident classification | Severity, root cause, confidence score, reasoning |
| RAG-based remediation | Retrieval from ChromaDB runbooks + LLM synthesis |
| Runbook citation | Always cite source runbook and retrieved chunk |
| Mock Slack notification | Formatted card rendered in UI — no real credentials needed |
| Mock Jira ticket | Structured ticket panel rendered in UI — no real credentials needed |
| LangGraph orchestration | Full stateful pipeline with conditional routing |
| Sample log files | 3 demo files (one per format) included in repo |
| HF Spaces deployment | One-click deployment to Hugging Face Spaces |

### 4.2 Out of Scope (Current Version)

| Feature | Reason Excluded |
|---|---|
| Auto-remediation (kubectl exec) | Scope risk; requires human approval gate not yet designed |
| Real Slack/Jira API integration | Portfolio demo — mocked for simplicity |
| Observability pull (Prometheus/Grafana) | Adds infrastructure dependency |
| Similar incident search | Future enhancement |
| Executive summary agent | Future enhancement |
| Runbook feedback loop | Requires persistence layer |
| AWS CloudTrail / Windows Event Log parsing | Wrong audience; scope risk |

---

## 5. Functional Requirements

### 5.1 Log Ingestion

| ID | Requirement |
|---|---|
| FR-01 | System SHALL accept log file uploads in `.log`, `.txt`, and `.json` formats |
| FR-02 | System SHALL auto-detect log format: Kubernetes, Nginx, or JSON |
| FR-03 | System SHALL fall back gracefully to `unknown` format without crashing |
| FR-04 | System SHALL provide 3 sample log files (one per format) for demo use |

### 5.2 Log Reader Agent

| ID | Requirement |
|---|---|
| FR-05 | Agent SHALL parse logs using regex only — no LLM calls |
| FR-06 | Agent SHALL detect Kubernetes error types: CrashLoopBackOff, OOMKilled, ImagePullBackOff, liveness probe failure, eviction |
| FR-07 | Agent SHALL detect Nginx error types: upstream timeout, 503/502 status codes, no live upstreams |
| FR-08 | Agent SHALL detect JSON log error types: timeout, connection refused, OOM, panic, exception |
| FR-09 | Agent SHALL output a normalized dict with: `format`, `raw`, `line_count`, `extracted` fields |

### 5.3 Classifier Agent

| ID | Requirement |
|---|---|
| FR-10 | Agent SHALL use Qwen2.5-72B-Instruct via Hugging Face Inference API |
| FR-11 | Agent SHALL return: `severity` (critical/warning/info), `root_cause`, `confidence` (0.0–1.0), `reasoning`, `affected_service`, `estimated_impact` |
| FR-12 | Agent SHALL fall back to parser-extracted `severity_hint` and `error_type` if LLM returns invalid JSON |
| FR-13 | Confidence score SHALL be displayed as a visual progress bar in the UI |
| FR-14 | Model reasoning SHALL be available via UI expander |

### 5.4 Remediation Agent

| ID | Requirement |
|---|---|
| FR-15 | Agent SHALL retrieve top 3 relevant runbook chunks from ChromaDB using semantic search |
| FR-16 | Agent SHALL synthesize fix steps using Qwen2.5-72B-Instruct with retrieved chunks as context |
| FR-17 | Agent SHALL always return `source_runbook` (filename) and `cited_chunk` (retrieved text) |
| FR-18 | Agent SHALL return `estimated_resolution_time` and `escalation_needed` flag |
| FR-19 | Agent SHALL function gracefully if ChromaDB is absent (fallback fix steps) |
| FR-20 | UI SHALL display the cited runbook chunk in an expander for RAG transparency |

### 5.5 Runbook Knowledge Base

| ID | Requirement |
|---|---|
| FR-21 | System SHALL include minimum 5 real runbooks covering: K8s CrashLoopBackOff, K8s OOMKilled, Nginx 503, Nginx upstream timeout, DB connection refused |
| FR-22 | Runbooks SHALL be stored as Markdown in `data/runbooks/` |
| FR-23 | System SHALL embed runbooks using `sentence-transformers/all-MiniLM-L6-v2` and persist to ChromaDB |

### 5.6 Jira Agent (Mock)

| ID | Requirement |
|---|---|
| FR-24 | Agent SHALL create a mock ticket for `critical` and `warning` severity incidents only |
| FR-25 | Agent SHALL return `None` for `info` severity |
| FR-26 | Ticket SHALL include: `ticket_id` (OPS-NNN format), `priority` (P1/P2/P3), `summary`, `description`, `assignee`, `status` |
| FR-27 | Ticket SHALL be rendered as a formatted panel in the Streamlit UI |

### 5.7 Slack Agent (Mock)

| ID | Requirement |
|---|---|
| FR-28 | Agent SHALL build a mock Slack card with channel, emoji, color, text, and blocks |
| FR-29 | Critical incidents SHALL route to `#incidents`; warnings to `#sre-alerts` |
| FR-30 | Card SHALL include: root cause, severity, fix preview (first step), runbook reference, Jira ticket ID |
| FR-31 | Card SHALL be rendered with dark Slack-style formatting in the Streamlit UI |

### 5.8 LangGraph Orchestrator

| ID | Requirement |
|---|---|
| FR-32 | Orchestrator SHALL implement a `StateGraph` with typed state: `IncidentState` |
| FR-33 | Pipeline order SHALL be: Log Reader → Classifier → Remediation → [Jira if critical] → Slack |
| FR-34 | Orchestrator SHALL use conditional edges to route `critical` → Jira Agent, `non_critical` → Slack Agent directly |
| FR-35 | Orchestrator SHALL track `completed_steps` list for UI pipeline visualization |

### 5.9 Streamlit UI

| ID | Requirement |
|---|---|
| FR-36 | UI SHALL provide a file uploader supporting `.log`, `.txt`, `.json` |
| FR-37 | UI SHALL show 3-tab layout: Pipeline View, Incident Report, Integrations |
| FR-38 | Pipeline View SHALL display each agent step with pass/skip status |
| FR-39 | Incident Report SHALL show severity badge (color-coded), confidence progress bar, root cause, fix steps, runbook citation |
| FR-40 | Integrations tab SHALL show mock Slack card and mock Jira ticket panel side-by-side |
| FR-41 | Raw JSON toggle SHALL be available on every output panel |
| FR-42 | UI SHALL display supported log formats and link to sample logs |

---

## 6. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | **Deployment:** App SHALL be deployable to Hugging Face Spaces with zero infrastructure setup |
| NFR-02 | **Security:** `HF_TOKEN` SHALL be stored as a Space secret — never in code or committed files |
| NFR-03 | **Cost:** Log Reader and mock agents SHALL require no LLM calls to minimize inference cost |
| NFR-04 | **Resilience:** All agents SHALL handle errors gracefully without crashing the pipeline |
| NFR-05 | **Reproducibility:** ChromaDB SHALL be committed to the repo so the app works without re-ingestion |
| NFR-06 | **Portability:** `requirements.txt` SHALL pin all dependencies for reproducible installs |

---

## 7. System Architecture

```
┌─────────────────────────┐
│   Hugging Face Spaces   │
│     (Streamlit UI)      │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  LangGraph Orchestrator │
└──────┬──────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│          Multi-Agent Pipeline        │
│                                      │
│  1. Log Reader Agent   (no LLM)      │
│  2. Classifier Agent   (Qwen2.5)     │
│  3. Remediation Agent  (RAG + LLM)   │
│  4. Jira Agent         (no LLM)      │
│  5. Slack Agent        (no LLM)      │
└──────────────┬───────────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
┌────────────┐  ┌──────────────────┐
│  HF Infer  │  │  ChromaDB        │
│  Qwen2.5   │  │  (Runbooks RAG)  │
└────────────┘  └──────────────────┘
```

---

## 8. Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| UI | Streamlit | HF Spaces native, fastest to build for portfolio |
| Orchestration | LangGraph | Stateful multi-agent graph with conditional routing |
| LLM | Qwen2.5-72B-Instruct (HF) | Strong reasoning, best for incident analysis |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 | Fast, CPU-compatible, no extra API cost |
| Vector Store | ChromaDB (persisted) | No external DB needed for demo; committable to repo |
| LLM Framework | LangChain + langchain-huggingface | Standard integration layer |
| Deployment | Hugging Face Spaces | Free tier, Streamlit native, one-click deploy |
| Dependencies | requirements.txt | HF Spaces default, widest compatibility |

---

## 9. Supported Log Formats

| Format | Detection Method | Sample File |
|---|---|---|
| Kubernetes events | Regex: `CrashLoopBackOff`, `OOMKilled`, `LAST SEEN.*REASON` | `sample_logs/k8s-events.log` |
| Nginx access/error | Regex: status codes, `upstream timed out`, `[error]` | `sample_logs/nginx-error.log` |
| Structured JSON | `json.loads()` — single object, array, or line-delimited | `sample_logs/app-structured.json` |

---

## 10. Decision Log

| Decision | Choice | Rationale |
|---|---|---|
| UI framework | Streamlit | Fastest to build; HF Spaces native |
| LLM provider | Hugging Face (not OpenAI) | Free tier available; portfolio demonstrates HF ecosystem |
| Primary model | Qwen2.5-72B-Instruct | Strongest reasoning for incident analysis |
| Slack/Jira | Mocked (no real credentials) | Portfolio demo — realistic UI without setup complexity |
| Log formats | K8s + Nginx + JSON only | 3 formats cover 90% of real-world DevOps incidents |
| Cookbook agent | Deprioritized | Target user is senior SRE — checklists add no value |
| Auto-remediation | Excluded | Scope risk; human approval gate not designed |
| ChromaDB persistence | Commit to repo | Eliminates re-ingestion step for demo reviewers |
| Dependency format | requirements.txt | HF Spaces default; simpler than pyproject.toml |

---

## 11. Project Structure

```
incident-analyzer/
├── app.py                        # Streamlit entrypoint
├── requirements.txt
├── .env.example
├── BRD.md                        # This document
├── README.md                     # HF Spaces deployment config
├── agents/
│   ├── log_reader.py             # Regex parser — no LLM
│   ├── classifier.py             # Qwen2.5 classification
│   ├── remediation.py            # RAG + LLM synthesis
│   ├── jira_agent.py             # Mock ticket builder
│   └── slack_agent.py            # Mock card builder
├── graph/
│   └── workflow.py               # LangGraph StateGraph
├── vectorstore/
│   ├── ingest.py                 # One-time ChromaDB ingestion
│   └── chroma_db/                # Persisted vector store
├── prompts/
│   ├── classifier_prompt.txt
│   └── remediation_prompt.txt
├── data/
│   └── runbooks/                 # 5 Markdown runbooks
├── sample_logs/                  # 3 demo log files
└── tests/                        # Pytest test suite
    ├── test_log_reader.py        # 17 tests — no mocks
    ├── test_jira_agent.py        # 12 tests — pure functions
    ├── test_slack_agent.py       # 12 tests — pure functions
    ├── test_classifier.py        # 11 tests — mocked LLM
    ├── test_remediation.py       #  7 tests — mocked RAG + LLM
    └── test_workflow.py          #  9 tests — integration
```

---

## 12. Acceptance Criteria

| Scenario | Expected Result |
|---|---|
| Upload `k8s-events.log` | Format detected as `kubernetes`, severity=critical, Jira ticket created |
| Upload `nginx-error.log` | Format detected as `nginx`, remediation cites `nginx-503.md` or `nginx-upstream-timeout.md` |
| Upload `app-structured.json` | Format detected as `json`, service=`payment-service` extracted |
| Critical incident | All 5 agents appear in Pipeline View as completed |
| Non-critical incident | Jira Agent shows as skipped in Pipeline View |
| Any incident | Raw JSON toggle visible and correct on all panels |
| HF Spaces deployment | App loads without local `.env` (uses Space secrets) |
| No HF token set | Clear error message, no silent crash |

---

*Generated from design session on 2026-06-13.*
