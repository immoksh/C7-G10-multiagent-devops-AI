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

# 🚨 DevOps Incident Analyzer

AI-powered multi-agent DevOps incident analysis platform built with LangGraph, Qwen2.5-72B, ChromaDB, and Streamlit.

## Architecture

```
Log Upload (Streamlit)
       │
       ▼
LangGraph Orchestrator
       │
       ├── Log Reader Agent    (Regex parser — no LLM)
       ├── Classifier Agent    (Qwen2.5-72B via HF Inference API)
       ├── Remediation Agent   (RAG over ChromaDB runbooks)
       ├── Jira Agent          (Mock ticket — no LLM)
       └── Slack Agent         (Mock card — no LLM)
```

## Supported Log Formats

| Format | Example |
|--------|---------|
| Kubernetes events | `kubectl get events -n <ns>` output |
| Nginx access/error logs | `/var/log/nginx/error.log` |
| Structured JSON logs | Line-delimited or array JSON |

Sample log files are in `sample_logs/` — use them to demo the app.

## Setup (Local)

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your HF_TOKEN to .env

# Ingest runbooks into ChromaDB (run once)
python vectorstore/ingest.py

# Start the app
streamlit run app.py
```

## HF Spaces Deployment

1. Push this repo to a Hugging Face Space (Streamlit SDK)
2. Add `HF_TOKEN` as a Space secret (Settings → Variables and secrets)
3. Run `vectorstore/ingest.py` locally and commit the `vectorstore/chroma_db/` directory
   (or add an `ingest` step to your Space startup — see `scripts/` if added)

## Stack

- **UI**: Streamlit
- **Orchestration**: LangGraph
- **LLM**: Qwen2.5-72B-Instruct (Hugging Face Inference API)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Vector Store**: ChromaDB (persisted)
- **Integrations**: Mock Slack + Mock Jira (portfolio demo)
