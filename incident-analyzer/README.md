# Multi-Agent DevOps Incident Analysis Platform

An AI-powered multi-agent system designed to analyze operations logs, classify incidents, recommend remediations, synthesize cookbooks, and automatically generate Jira tickets and Slack notifications.

## Architecture

This project leverages:
- **LangGraph:** Orchestrates the multi-agent workflow.
- **Hugging Face / OpenRouter:** LLM backend for classification and synthesis.
- **ChromaDB:** Vector store for the Retrieval-Augmented Generation (RAG) Remediation Agent.
- **Streamlit:** Frontend UI.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   cp .env.example .env
   ```
3. Ingest sample runbooks into the vector store:
   ```bash
   python vectorstore/ingest.py
   ```
4. Run the Streamlit application:
   ```bash
   streamlit run app.py
   ```
