import logging
import os
from gitingest import ingest
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Suppress verbose logging from transformers and sentence_transformers
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

def initialize_rag_pipeline(repo_path):
    """
    Ingests repository content, chunks it, and creates a FAISS vector store.
    
    Args:
        repo_path (str): The absolute path to the local repository.
        
    Returns:
        FAISS: The initialized vector store.
    """
    # Use gitingest on local directory
    exclude_patterns = {".claude", ".gitnexus", "AGENTS.md", "CLAUDE.md"}
    summary, tree, content = ingest(repo_path, exclude_patterns=exclude_patterns)

    # Optional: Keep console logs for debugging
    print("Summary length:", len(summary))
    print("Tree length:", len(tree))
    print("Content length:", len(content))
    
    # Batch string into chunks suitable for indexing
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
    combined_text = f"Repository Summary:\n{summary}\n\nRepository Structure:\n{tree}\n\nCodebase Files:\n{content}"
    chunks = text_splitter.split_text(combined_text)
    
    # Embed using local HF model
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.from_texts(chunks, embeddings)
    
    return vectorstore
