import os
import glob
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Directory setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNBOOKS_DIR = os.path.join(BASE_DIR, "data", "runbooks")
CHROMA_DB_DIR = os.path.join(BASE_DIR, "vectorstore", "chroma_db")

def ingest_runbooks():
    print(f"Loading runbooks from {RUNBOOKS_DIR}...")
    runbook_files = glob.glob(os.path.join(RUNBOOKS_DIR, "*.md"))
    
    if not runbook_files:
        print("No runbooks found.")
        return

    documents = []
    for file_path in runbook_files:
        loader = TextLoader(file_path)
        documents.extend(loader.load())

    print(f"Loaded {len(documents)} runbooks.")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks.")

    # Using HuggingFace embeddings
    print("Initializing HuggingFace embeddings (all-MiniLM-L6-v2)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    print(f"Creating vector store at {CHROMA_DB_DIR}...")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DB_DIR
    )
    
    print("Ingestion complete!")

if __name__ == "__main__":
    ingest_runbooks()
