import os
import re
import json
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.messages import HumanMessage


PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "remediation_prompt.txt"
PROMPT_TEMPLATE = PROMPT_PATH.read_text()
CHROMA_DIR = Path(__file__).parent.parent / "vectorstore" / "chroma_db"


def _get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )


def _get_llm():
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise ValueError("HF_TOKEN environment variable not set")
    endpoint = HuggingFaceEndpoint(
        repo_id="Qwen/Qwen2.5-72B-Instruct",
        task="conversational",
        temperature=0.1,
        max_new_tokens=768,
        huggingfacehub_api_token=token,
    )
    return ChatHuggingFace(llm=endpoint)


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def remediate(classification: dict) -> dict:
    root_cause = classification.get("root_cause", "unknown")
    affected_service = classification.get("affected_service", "unknown")
    severity = classification.get("severity", "warning")
    reasoning = classification.get("reasoning", "")

    # Build search query from classification
    query = f"{root_cause} {affected_service} {severity} {reasoning}"

    # RAG retrieval
    source_runbook = "unknown"
    cited_chunk = ""
    top_chunks_text = "No runbook documentation available."

    if CHROMA_DIR.exists():
        try:
            embeddings = _get_embeddings()
            vectorstore = Chroma(
                persist_directory=str(CHROMA_DIR),
                embedding_function=embeddings,
                collection_name="runbooks",
            )
            docs = vectorstore.similarity_search(query, k=3)
            if docs:
                source_runbook = docs[0].metadata.get("source_file", "unknown")
                cited_chunk = docs[0].page_content
                top_chunks_text = "\n\n---\n\n".join(
                    f"[Source: {d.metadata.get('source_file', 'unknown')}]\n{d.page_content}"
                    for d in docs
                )
        except Exception:
            pass

    prompt = PROMPT_TEMPLATE.format(
        severity=severity,
        root_cause=root_cause,
        affected_service=affected_service,
        reasoning=reasoning,
        runbook_chunks=top_chunks_text,
    )

    llm = _get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    result = _extract_json(response.content)

    if not result.get("fix_steps"):
        result["fix_steps"] = ["Review logs and escalate to on-call engineer"]

    result["source_runbook"] = source_runbook
    result["cited_chunk"] = cited_chunk

    return result
