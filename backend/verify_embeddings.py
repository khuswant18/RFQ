#!/usr/bin/env python3
"""Verify that RAG files were embedded into ChromaDB."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.rag.chroma_client import ChromaClient

try:
    chroma = ChromaClient(persist_directory="data/chroma")
    
    # Check rag_documents collection
    collection = chroma.get_collection("rag_documents")
    
    if collection:
        count = collection.count()
        print(f"✅ ChromaDB initialized successfully!")
        print(f"📊 Total documents in 'rag_documents' collection: {count}")
        
        # Try a sample query
        if count > 0:
            results = chroma.query("rag_documents", ["steel rebar"], n_results=3)
            print(f"\n🔍 Sample query results for 'steel rebar':")
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0][:3], 1):
                    print(f"  {i}. {doc[:100]}...")
    else:
        print("⚠️  Collection 'rag_documents' not found")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
