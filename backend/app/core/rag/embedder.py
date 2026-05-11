"""Embedder for generating text embeddings."""
import os
from typing import List


class Embedder:
    """Text embedding generator using sentence-transformers."""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name
        self.model = None
        
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except ImportError:
            print("Warning: sentence-transformers not installed. Using mock embeddings.")
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if self.model is None:
            # Return mock embeddings
            return [[0.0] * 384 for _ in texts]
        
        return self.model.encode(texts).tolist()
