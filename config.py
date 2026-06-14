"""Central configuration for the Multi-Agent DevOps Incident Analyzer.

All settings are loaded from environment variables (optionally via a `.env`
file). Every external integration is optional: when its credentials are
absent the corresponding agent runs in a safe, degraded mode instead of
crashing. This keeps the project fully runnable for demos and CI.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional at runtime
    pass


BASE_DIR = Path(__file__).resolve().parent

# Curated OpenRouter chat models the user can pick from in the UI.
# Any other OpenRouter model id can be entered manually via the "Custom" option.
OPENROUTER_MODEL_CHOICES = [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "anthropic/claude-3.5-sonnet",
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.3-70b-instruct",
    "mistralai/mistral-large",
    "deepseek/deepseek-chat",
    "qwen/qwen-2.5-72b-instruct",
]


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass
class Settings:
    # --- LLM: OpenRouter (OpenAI-compatible, preferred) ---
    openrouter_api_key: str = field(default_factory=lambda: _get("OPENROUTER_API_KEY"))
    openrouter_base_url: str = field(
        default_factory=lambda: _get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    )
    openrouter_model: str = field(
        default_factory=lambda: _get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    )

    # --- LLM: Hugging Face (fallback alternative) ---
    hf_token: str = field(default_factory=lambda: _get("HF_TOKEN"))
    hf_model: str = field(default_factory=lambda: _get("HF_MODEL", "Qwen/Qwen2.5-72B-Instruct"))
    llm_temperature: float = field(default_factory=lambda: float(_get("LLM_TEMPERATURE", "0.2") or 0.2))

    # --- Embeddings / Vector store ---
    embedding_model: str = field(
        default_factory=lambda: _get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    )
    chroma_dir: str = field(default_factory=lambda: _get("CHROMA_DIR", "vectorstore/chroma_db"))

    # --- Slack ---
    slack_bot_token: str = field(default_factory=lambda: _get("SLACK_BOT_TOKEN"))
    slack_channel: str = field(default_factory=lambda: _get("SLACK_CHANNEL", "#incidents"))

    # --- Jira ---
    jira_server: str = field(default_factory=lambda: _get("JIRA_SERVER"))
    jira_email: str = field(default_factory=lambda: _get("JIRA_EMAIL"))
    jira_api_token: str = field(default_factory=lambda: _get("JIRA_API_TOKEN"))
    jira_project_key: str = field(default_factory=lambda: _get("JIRA_PROJECT_KEY", "OPS"))

    # --- Behaviour ---
    runbooks_dir: Path = field(default_factory=lambda: BASE_DIR / "data" / "runbooks")

    @property
    def llm_provider(self) -> str:
        """Which chat backend to use. OpenRouter takes priority when set."""
        if self.openrouter_api_key:
            return "openrouter"
        if self.hf_token:
            return "huggingface"
        return "none"

    @property
    def llm_enabled(self) -> bool:
        return self.llm_provider != "none"

    @property
    def active_model(self) -> str:
        if self.llm_provider == "openrouter":
            return self.openrouter_model
        if self.llm_provider == "huggingface":
            return self.hf_model
        return "rule-based fallback"

    @property
    def slack_enabled(self) -> bool:
        return bool(self.slack_bot_token)

    @property
    def jira_enabled(self) -> bool:
        return bool(self.jira_server and self.jira_email and self.jira_api_token)

    @property
    def chroma_path(self) -> Path:
        p = Path(self.chroma_dir)
        return p if p.is_absolute() else BASE_DIR / p


settings = Settings()
