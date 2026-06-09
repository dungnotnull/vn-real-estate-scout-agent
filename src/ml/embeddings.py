"""Embedding generation for semantic deduplication using ChromaDB."""
from typing import List, Optional, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for listing descriptions using sentence-transformers."""

    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2", device: Optional[str] = None):
        """Initialize embedding generator."""
        self.model_name = model_name
        self.device = device or ('cuda' if __import__('torch').cuda.is_available() else 'cpu')
        self.model = None

    def load_model(self) -> bool:
        """Load the sentence transformer model."""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info("Embedding model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            return False

    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Encode texts to embeddings.

        Args:
            texts: List of texts to encode
            batch_size: Batch size for encoding

        Returns:
            NumPy array of embeddings (shape: [len(texts), 768])
        """
        if not self.model:
            logger.error("Model not loaded")
            return np.zeros((len(texts), 768))

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            return embeddings
        except Exception as e:
            logger.error(f"Encoding failed: {e}")
            return np.zeros((len(texts), 768))

    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text.

        Args:
            text: Text to encode

        Returns:
            Embedding vector (shape: [768])
        """
        return self.encode([text])[0]

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0-1)
        """
        from sklearn.metrics.pairwise import cosine_similarity
        return cosine_similarity([embedding1], [embedding2])[0][0]

    def find_duplicates(
        self,
        embeddings: np.ndarray,
        threshold: float = 0.95,
        texts: Optional[List[str]] = None
    ) -> List[tuple]:
        """Find duplicate texts based on embedding similarity.

        Args:
            embeddings: Array of embeddings
            threshold: Similarity threshold for duplicate detection
            texts: Optional list of texts for debugging

        Returns:
            List of (index1, index2, similarity) tuples for duplicates
        """
        from sklearn.metrics.pairwise import cosine_similarity

        similarity_matrix = cosine_similarity(embeddings)

        duplicates = []
        n = len(embeddings)

        for i in range(n):
            for j in range(i + 1, n):
                if similarity_matrix[i][j] >= threshold:
                    duplicates.append((i, j, similarity_matrix[i][j]))

        return duplicates

    def batch_encode_listings(self, listings: List[Dict[str, Any]]) -> Dict[str, np.ndarray]:
        """Encode multiple listings for batch processing.

        Args:
            listings: List of listing dictionaries

        Returns:
            Dict mapping listing_id to embedding vector
        """
        texts = []
        ids = []

        for listing in listings:
            listing_id = listing.get('listing_id', listing.get('id', ''))
            description = listing.get('description', '')
            title = listing.get('title', '')

            # Combine title and description
            text = f"{title}. {description}" if title and description else (title or description)

            if text:
                ids.append(listing_id)
                texts.append(text)

        embeddings = self.encode(texts)

        return {listing_id: emb for listing_id, emb in zip(ids, embeddings)}

    def __enter__(self):
        self.load_model()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.model:
            del self.model
