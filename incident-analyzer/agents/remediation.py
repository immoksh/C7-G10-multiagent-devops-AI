import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DB_DIR = os.path.join(BASE_DIR, "vectorstore", "chroma_db")

def get_remediation_docs(classification: dict, parsed_log: dict) -> list:
    """
    Retrieves the most relevant runbooks for the incident from ChromaDB.
    """
    # If the vector store doesn't exist yet, return an empty list
    if not os.path.exists(CHROMA_DB_DIR):
        print("Vector store not found. Please run ingest.py first.")
        return []

    try:
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = Chroma(
            persist_directory=CHROMA_DB_DIR,
            embedding_function=embeddings
        )

        query = f"Service: {parsed_log.get('service')}. Error: {classification.get('root_cause')}. Raw Log: {parsed_log.get('raw')}"
        
        # Retrieve top 2 most relevant documents
        results = vectorstore.similarity_search(query, k=2)
        
        docs = [doc.page_content for doc in results]
        return docs
    except Exception as e:
        print(f"Remediation Agent Error: {e}")
        return []
