# Prompts

Prompt templates are colocated with the agents that use them (each agent
defines its `SYSTEM` and `PROMPT_TEMPLATE` constants) so the prompt always
travels with its parsing/fallback logic:

- Classifier prompt → `agents/classifier.py`
- Remediation (RAG) prompt → `agents/remediation.py`
- Cookbook prompt → `agents/cookbook.py`

This folder is reserved for any future externalized / versioned prompts.
