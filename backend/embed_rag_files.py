#!/usr/bin/env python3
"""
Script to embed all RAG files into ChromaDB vector database.
Supports PDF and TXT files.
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.rag.chroma_client import ChromaClient
from app.core.rag.embedder import Embedder


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file."""
    try:
        import PyPDF2
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    except ImportError:
        print(f"Warning: PyPDF2 not installed. Skipping PDF: {pdf_path}")
        return ""
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return ""


def extract_text_from_txt(txt_path: str) -> str:
    """Extract text from TXT file."""
    try:
        with open(txt_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading {txt_path}: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks."""
    if not text:
        return []
    
    chunks = []
    words = text.split()
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    
    return chunks


def process_rag_files(rag_dir: str) -> Tuple[List[str], List[str], List[Dict]]:
    """Process all files in RAG directory and return documents, IDs, and metadata."""
    documents = []
    ids = []
    metadatas = []
    
    rag_path = Path(rag_dir)
    file_counter = 0
    
    for file_path in sorted(rag_path.glob("*")):
        if file_path.is_file():
            file_name = file_path.name
            print(f"Processing: {file_name}...", end=" ")
            
            text = ""
            if file_path.suffix.lower() == ".pdf":
                text = extract_text_from_pdf(str(file_path))
            elif file_path.suffix.lower() == ".txt":
                text = extract_text_from_txt(str(file_path))
            else:
                print("SKIPPED (unsupported format)")
                continue
            
            if not text:
                print("SKIPPED (no text extracted)")
                continue
            
            # Chunk the text
            chunks = chunk_text(text)
            print(f"OK ({len(chunks)} chunks)")
            
            # Add chunks to documents
            for chunk_idx, chunk in enumerate(chunks):
                file_counter += 1
                doc_id = f"rag_{file_counter:04d}"
                documents.append(chunk)
                ids.append(doc_id)
                metadatas.append({
                    "source": file_name,
                    "chunk": chunk_idx,
                    "total_chunks": len(chunks)
                })
    
    return documents, ids, metadatas


def main():
    """Main function to embed RAG files."""
    rag_dir = "/Users/mitulbhatia/Desktop/RFQ/RAGFiles"
    
    print("=" * 60)
    print("RAG Files Embedding Script")
    print("=" * 60)
    print(f"RAG Directory: {rag_dir}")
    print()
    
    # Check if directory exists
    if not os.path.exists(rag_dir):
        print(f"Error: RAG directory not found: {rag_dir}")
        sys.exit(1)
    
    # Process files
    print("Step 1: Processing RAG files...")
    print("-" * 60)
    documents, ids, metadatas = process_rag_files(rag_dir)
    
    if not documents:
        print("No documents to embed!")
        sys.exit(1)
    
    print(f"\nTotal documents to embed: {len(documents)}")
    print()
    
    # Initialize ChromaDB and Embedder
    print("Step 2: Initializing ChromaDB and Embedder...")
    print("-" * 60)
    try:
        chroma = ChromaClient(persist_directory="data/chroma")
        print("✓ ChromaDB initialized")
    except ImportError as e:
        print(f"Error: {e}")
        print("Install chromadb with: pip install chromadb sentence-transformers")
        sys.exit(1)
    
    embedder = Embedder()
    print("✓ Embedder initialized")
    print()
    
    # Embed and add to ChromaDB
    print("Step 3: Embedding and adding documents to ChromaDB...")
    print("-" * 60)
    
    # Create a new collection for RAG files
    collection_name = "rag_documents"
    
    try:
        # Add documents in batches to avoid memory issues
        batch_size = 50
        for i in range(0, len(documents), batch_size):
            batch_end = min(i + batch_size, len(documents))
            batch_docs = documents[i:batch_end]
            batch_ids = ids[i:batch_end]
            batch_metas = metadatas[i:batch_end]
            
            print(f"Adding batch {i//batch_size + 1} ({batch_end - i} documents)...", end=" ")
            chroma.add_documents(
                collection=collection_name,
                documents=batch_docs,
                ids=batch_ids,
                metadatas=batch_metas
            )
            print("✓")
        
        print()
        print("=" * 60)
        print("✅ Embedding Complete!")
        print("=" * 60)
        print(f"Total documents embedded: {len(documents)}")
        print(f"Collection: {collection_name}")
        print(f"ChromaDB location: data/chroma")
        print()
        
    except Exception as e:
        print(f"Error during embedding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
