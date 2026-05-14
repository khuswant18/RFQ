"""ChromaDB client for RAG."""
import os
from typing import List, Dict, Any

# ChromaDB is required for RAG operations
try:
    import chromadb
    from chromadb import PersistentClient
    CHROMADB_AVAILABLE = True
except ImportError:  # pragma: no cover
    CHROMADB_AVAILABLE = False
    PersistentClient = None  # type: ignore[assignment]


class ChromaClient:
    """Wrapper for ChromaDB vector store operations."""

    def __init__(self, persist_directory: str = "data/chroma"):
        if not CHROMADB_AVAILABLE:
            raise ImportError("chromadb is not installed. Install it with: pip install chromadb")

        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        # Use PersistentClient for ChromaDB 1.5+
        self.client = PersistentClient(path=persist_directory)

        # Create collections if they don't exist
        self.collections: Dict[str, Any] = {}
        for collection_name in ["is_codes", "material_synonyms", "hsn_gst_rules", "weight_formulas", "agent_capabilities", "external_rag_files"]:
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
            raise RuntimeError(f"Chroma collection not initialized: {collection}")

        results = self.collections[collection].query(
            query_texts=query_texts,
            n_results=n_results
        )

        return results

    def get_collection(self, collection: str):
        """Get a collection by name."""
        return self.collections.get(collection)
