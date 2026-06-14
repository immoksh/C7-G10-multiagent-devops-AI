"""LLM provider wrapper around the Hugging Face Inference API.

Design goals:
  * Lazily initialise the endpoint so importing this module is cheap.
  * Never crash the pipeline: if no HF token is configured (or the call
    fails) we return ``None`` and let each agent fall back to its
    deterministic, rule-based behaviour.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Optional

from config import settings


def _get_client(model: Optional[str] = None):
    """Return a chat client for the requested model, or None.

    Priority: OpenRouter (OpenAI-compatible, e.g. gpt-4o-mini) -> Hugging Face.
    The ``model`` argument lets callers (e.g. the UI) override the configured
    default at runtime so users can pick which model performs the analysis.
    """
    provider = settings.llm_provider
    if provider == "openrouter":
        return _build_openrouter(model or settings.openrouter_model)
    if provider == "huggingface":
        return _build_huggingface(model or settings.hf_model)
    return None


@lru_cache(maxsize=16)
def _build_openrouter(model: str):
    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            temperature=settings.llm_temperature,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            max_tokens=1024,
            default_headers={
                "HTTP-Referer": "https://huggingface.co/spaces",
                "X-Title": "Multi-Agent DevOps Incident Analyzer",
            },
        )
    except Exception as exc:  # pragma: no cover - network/dependency issues
        print(f"[llm] Could not initialise OpenRouter client: {exc}")
        return None


@lru_cache(maxsize=16)
def _build_huggingface(model: str):
    try:
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

        endpoint = HuggingFaceEndpoint(
            repo_id=model,
            temperature=settings.llm_temperature,
            max_new_tokens=1024,
            huggingfacehub_api_token=settings.hf_token,
        )
        return ChatHuggingFace(llm=endpoint)
    except Exception as exc:  # pragma: no cover - network/dependency issues
        print(f"[llm] Could not initialise Hugging Face endpoint: {exc}")
        return None


def llm_available() -> bool:
    return _get_client() is not None


def complete(prompt: str, system: Optional[str] = None, model: Optional[str] = None) -> Optional[str]:
    """Run a single-turn completion. Returns None when the LLM is unavailable."""
    llm = _get_client(model)
    if llm is None:
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))
        response = llm.invoke(messages)
        return getattr(response, "content", str(response))
    except Exception as exc:  # pragma: no cover - network issues
        print(f"[llm] completion failed: {exc}")
        return None


def complete_json(
    prompt: str, system: Optional[str] = None, model: Optional[str] = None
) -> Optional[dict]:
    """Run a completion expected to return JSON and parse it defensively."""
    raw = complete(prompt, system=system, model=model)
    if not raw:
        return None
    return _extract_json(raw)


def _extract_json(text: str) -> Optional[dict]:
    """Pull the first JSON object out of an LLM response."""
    # Strip ```json fences if present.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = brace.group(0) if brace else None
    if candidate is None:
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None
