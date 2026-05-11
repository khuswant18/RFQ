"""ChromaDB client for RAG."""
import os
from typing import List, Dict, Any

from chromadb import Client, Settings
from chromadb.config import Settings as ChromaSettings


class ChromaClient:
    """Wrapper for ChromaDB vector store operations."""
    
    def __init__(self, persist_directory: str = "data/chroma"):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        self.client = Client(
            ChromaSettings(
                persist_directory=persist_directory,
                anonymized_telemetry=False
            )
        )
        
        # Create collections if they don't exist
        self.collections = {}
        for collection_name in ["is_codes", "material_synonyms", "hsn_gst_rules", "weight_formulas", "agent_capabilities"]:
            self.collections[collection_name] = self.client.get_or_create_collection(collection_name)
    
    def add_documents(self, collection: str, documents: List[str], 
                      ids: List[str], metadatas: List[Dict[str, Any]] = None):
        """Add documents to a collection."""
        if collection not in self.collections:
            self.collections[collection] = self.client.get_or_create_collection(collection)
        
        self.collections[collection].add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )
    
    def query(self, collection: str, query_texts: List[str], 
              n_results: int = 5) -> Dict[str, Any]:
        """Query a collection for similar documents."""
        if collection not in self.collections:
            return {"documents": [[]], "distances": [[]], "metadatas": [[]]}
        
        results = self.collections[collection].query(
            query_texts=query_texts,
            n_results=n_results
        )
        
        return results
    
    def get_collection(self, collection: str):
        """Get a collection by name."""
        return self.collections.get(collection)
