"""
Run once to ingest runbooks into ChromaDB.
Usage: python vectorstore/ingest.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import MarkdownTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

RUNBOOKS_DIR = Path(__file__).parent.parent / "data" / "runbooks"
CHROMA_DIR = Path(__file__).parent / "chroma_db"


def ingest():
    print(f"Loading runbooks from {RUNBOOKS_DIR}...")
    loader = DirectoryLoader(
        str(RUNBOOKS_DIR),
        glob="*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()
    print(f"Loaded {len(docs)} runbook files")

    splitter = MarkdownTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks")

    # Add source filename metadata to each chunk
    for chunk in chunks:
        source = Path(chunk.metadata.get("source", "")).name
        chunk.metadata["source_file"] = source

    print("Embedding and storing in ChromaDB...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name="runbooks",
    )
    vectorstore.persist()
    print(f"Done. {len(chunks)} chunks stored in {CHROMA_DIR}")


if __name__ == "__main__":
    ingest()
