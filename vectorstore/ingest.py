"""Runbook vector store: ingestion + retrieval.

Loads the markdown runbooks in ``data/runbooks/`` into a persistent
ChromaDB collection using sentence-transformer embeddings. A keyword
based fallback retriever is provided so the Remediation agent still works
when ChromaDB / sentence-transformers are not installed or the store has
not been built yet.

Run as a script to (re)build the index:

    python -m vectorstore.ingest
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from config import settings

COLLECTION_NAME = "runbooks"


# --- Document loading ---------------------------------------------------

def _split_markdown(text: str, source: str) -> List[Dict]:
    """Split a markdown runbook into chunks on H1/H2 headings."""
    sections = re.split(r"\n(?=#{1,2}\s)", text)
    chunks = []
    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
        heading_match = re.match(r"#{1,2}\s*(.+)", section)
        heading = heading_match.group(1).strip() if heading_match else f"section {i}"
        chunks.append(
            {
                "id": f"{source}::{i}",
                "text": section,
                "source": source,
                "heading": heading,
            }
        )
    return chunks


def load_runbook_chunks() -> List[Dict]:
    chunks: List[Dict] = []
    runbooks_dir = settings.runbooks_dir
    if not runbooks_dir.exists():
        return chunks
    for path in sorted(runbooks_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        chunks.extend(_split_markdown(text, path.name))
    return chunks


# --- ChromaDB build -----------------------------------------------------

def build_index() -> int:
    """Build / refresh the Chroma collection. Returns number of chunks."""
    import chromadb
    from chromadb.utils import embedding_functions

    chunks = load_runbook_chunks()
    if not chunks:
        print("[ingest] No runbooks found in", settings.runbooks_dir)
        return 0

    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.chroma_path))

    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.embedding_model
    )

    # Recreate the collection from scratch for a clean rebuild.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME, embedding_function=embed_fn
    )

    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"], "heading": c["heading"]} for c in chunks],
    )
    print(f"[ingest] Indexed {len(chunks)} runbook chunks into {settings.chroma_path}")
    return len(chunks)


# --- Retrieval ----------------------------------------------------------

def _chroma_retrieve(query: str, k: int) -> List[Dict]:
    import chromadb
    from chromadb.utils import embedding_functions

    if not settings.chroma_path.exists():
        return []
    client = chromadb.PersistentClient(path=str(settings.chroma_path))
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.embedding_model
    )
    try:
        collection = client.get_collection(COLLECTION_NAME, embedding_function=embed_fn)
    except Exception:
        return []

    res = collection.query(query_texts=[query], n_results=k)
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0] if res.get("distances") else [None] * len(docs)
    out = []
    for doc, meta, dist in zip(docs, metas, dists):
        out.append(
            {
                "text": doc,
                "source": (meta or {}).get("source", "runbook"),
                "heading": (meta or {}).get("heading", ""),
                "score": round(1 - dist, 3) if isinstance(dist, (int, float)) else None,
            }
        )
    return out


def _keyword_retrieve(query: str, k: int) -> List[Dict]:
    """Fallback: simple token-overlap ranking over runbook chunks."""
    chunks = load_runbook_chunks()
    if not chunks:
        return []
    query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    scored = []
    for c in chunks:
        text_tokens = set(re.findall(r"[a-z0-9]+", c["text"].lower()))
        overlap = len(query_tokens & text_tokens)
        if overlap:
            scored.append((overlap, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for overlap, c in scored[:k]:
        out.append(
            {
                "text": c["text"],
                "source": c["source"],
                "heading": c["heading"],
                "score": overlap,
            }
        )
    return out


def retrieve(query: str, k: int = 5) -> List[Dict]:
    """Return the top-k runbook chunks for a query, with graceful fallback."""
    try:
        results = _chroma_retrieve(query, k)
        if results:
            return results
    except Exception as exc:  # pragma: no cover - optional dependency
        print(f"[ingest] Chroma retrieval unavailable, using keyword fallback: {exc}")
    return _keyword_retrieve(query, k)


if __name__ == "__main__":
    build_index()
