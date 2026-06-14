---
title: Multi-Agent DevOps Incident Analyzer
emoji: 🛠️
colorFrom: indigo
colorTo: red
sdk: streamlit
sdk_version: 1.36.0
app_file: app.py
pinned: false
---

# 🛠️ AI-Powered Multi-Agent DevOps Incident Analysis Platform

Upload ops logs and let a team of collaborating AI agents parse them,
classify the incident, retrieve the right runbooks (RAG), synthesize a fix,
generate a recovery checklist, file a Jira ticket for critical issues, and
notify Slack — all orchestrated with **LangGraph**.

> **Stack:** LangGraph · Hugging Face Inference · ChromaDB · Slack SDK · Jira REST · Streamlit

---

## Architecture

```text
        ┌──────────────────────────┐
        │  Streamlit UI (HF Space) │
        └─────────────┬────────────┘
                      ▼
        ┌──────────────────────────┐
        │  LangGraph Orchestrator  │
        └─────────────┬────────────┘
                      ▼
  1. Log Reader  →  2. Classifier  →  3. Remediation (RAG)
        →  4. Cookbook  →  (critical?) → 5. Jira → 6. Slack → END

   LLM: OpenRouter (gpt-4o-mini) — or Hugging Face (Qwen2.5 / Llama 3)
   RAG: ChromaDB over data/runbooks/
   Out: Slack notification + Jira ticket
```

### The six agents

| # | Agent | Role | LLM? |
|---|-------|------|------|
| 1 | **Log Reader** | Regex/Grok field extraction (service, severity, error type) | No |
| 2 | **Classifier** | Severity, probable root cause, confidence | Yes (+ heuristic fallback) |
| 3 | **Remediation** | RAG over runbooks → synthesized fix + rationale | Yes (+ runbook fallback) |
| 4 | **Cookbook** | Actionable recovery checklist | Yes (+ template fallback) |
| 5 | **Jira** | Creates a ticket for critical/high incidents | No (dry-run if unconfigured) |
| 6 | **Slack** | Posts root cause + fix + Jira link | No (dry-run if unconfigured) |

**Graceful degradation:** every external integration is optional. With no
credentials the app still runs end-to-end using deterministic fallbacks and
dry-run notifications — ideal for demos, CI, and the free HF tier.

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) configure integrations
cp .env.example .env   # then fill in HF_TOKEN, SLACK_*, JIRA_*

# 3. (Optional) build the runbook vector index
python -m vectorstore.ingest

# 4. Run the UI
streamlit run app.py
```

Open the app, pick a sample log (or paste your own), and click
**Analyze Incident**.

### Run the workflow headless

```bash
python -m graph.workflow
```

---

## Configuration

All settings live in environment variables (see `.env.example`):

| Variable | Purpose | Required |
|----------|---------|----------|
| `OPENROUTER_API_KEY` | OpenRouter API key (preferred LLM) | Optional (LLM) |
| `OPENROUTER_MODEL` | Chat model (default `openai/gpt-4o-mini`) | Optional |
| `HF_TOKEN` / `HF_MODEL` | Hugging Face fallback LLM (used only if no OpenRouter key) | Optional |
| `SLACK_BOT_TOKEN` / `SLACK_CHANNEL` | Slack notifications | Optional |
| `JIRA_SERVER` / `JIRA_EMAIL` / `JIRA_API_TOKEN` / `JIRA_PROJECT_KEY` | Jira tickets | Optional |
| `EMBEDDING_MODEL` | Local sentence-transformer for RAG | Optional |

**LLM provider priority:** `OPENROUTER_API_KEY` → `HF_TOKEN` → rule-based fallback.

> **Embeddings note:** OpenRouter does not expose an embeddings endpoint, so
> the runbook RAG embeddings run locally via `sentence-transformers` (free,
> offline). Only the chat/reasoning agents use OpenRouter.

On Hugging Face Spaces, set these as **Secrets** in the Space settings.

---

## Project structure

```text
.
├── app.py                  # Streamlit UI
├── config.py               # Env-driven settings + feature flags
├── llm.py                  # Hugging Face LLM wrapper (graceful fallback)
├── agents/
│   ├── log_reader.py       # Agent 1 — regex parser
│   ├── classifier.py       # Agent 2 — incident classifier
│   ├── remediation.py      # Agent 3 — RAG remediation
│   ├── cookbook.py         # Agent 4 — recovery checklist
│   ├── jira_agent.py       # Agent 5 — Jira ticket
│   └── slack_agent.py      # Agent 6 — Slack notification
├── graph/
│   ├── state.py            # Shared IncidentState
│   └── workflow.py         # LangGraph orchestrator
├── vectorstore/
│   └── ingest.py           # Build + query the Chroma runbook index
├── data/
│   ├── runbooks/           # Knowledge base for RAG
│   └── sample_logs/        # Demo logs
└── requirements.txt
```

---

## How remediation RAG works

1. The query is built from the classified root cause + parsed fields.
2. ChromaDB returns the top-5 runbook chunks (embedded with a
   sentence-transformer). If ChromaDB isn't built/installed, a keyword
   overlap fallback is used instead.
3. The LLM synthesizes a grounded fix citing the retrieved runbooks.

Add your own runbooks as markdown files in `data/runbooks/` and rerun
`python -m vectorstore.ingest`.

---

## License

MIT — for educational / portfolio use.
