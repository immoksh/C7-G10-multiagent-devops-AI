import os
import re
import json
from pathlib import Path

from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.messages import HumanMessage


PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "classifier_prompt.txt"
PROMPT_TEMPLATE = PROMPT_PATH.read_text()


def _get_llm():
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise ValueError("HF_TOKEN environment variable not set")
    endpoint = HuggingFaceEndpoint(
        repo_id="Qwen/Qwen2.5-72B-Instruct",
        task="conversational",
        temperature=0.1,
        max_new_tokens=512,
        huggingfacehub_api_token=token,
    )
    return ChatHuggingFace(llm=endpoint)


def _extract_json(text: str) -> dict:
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Extract JSON block from markdown or surrounding text
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def classify(parsed: dict) -> dict:
    extracted = parsed.get("extracted", {})
    raw_excerpt = parsed.get("raw", "")[:1500]

    prompt = PROMPT_TEMPLATE.format(
        log_format=parsed.get("format", "unknown"),
        extracted_fields=json.dumps(extracted, indent=2),
        raw_excerpt=raw_excerpt,
    )

    llm = _get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    result = _extract_json(response.content)

    # Merge severity hint from parser as fallback
    if not result.get("severity"):
        result["severity"] = extracted.get("severity_hint", "info")
    if not result.get("root_cause"):
        result["root_cause"] = extracted.get("error_type", "unknown")
    if "confidence" not in result:
        result["confidence"] = 0.5
    if not result.get("affected_service"):
        result["affected_service"] = extracted.get("service", "unknown")

    return result
