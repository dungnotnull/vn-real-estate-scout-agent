"""ChromaDB vector store for semantic deduplication and RAG."""
from typing import Optional, List, Dict, Any
import logging
import chromadb
from chromadb.config import Settings
from src.config import chromadb

logger = logging.getLogger(__name__)


class ChromaDBStore:
    """ChromaDB wrapper for listing embeddings and semantic search."""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, collection_name: Optional[str] = None):
        """Initialize ChromaDB client.

        Args:
            host: ChromaDB host. Defaults to config.chromadb.host
            port: ChromaDB port. Defaults to config.chromadb.port
            collection_name: Collection name. Defaults to config.chromadb.collection_name
        """
        self.host = host or chromadb.host
        self.port = port or chromadb.port
        self.collection_name = collection_name or chromadb.collection_name
        self.client: Optional[chromadb.Client] = None
        self.collection: Optional[chromadb.Collection] = None

    def connect(self) -> bool:
        """Establish connection to ChromaDB.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            self.client = chromadb.HttpClient(
                host=self.host,
                port=self.port,
                settings=Settings(
                    chroma_client_auth_provider="chromadb.auth.token.TokenAuthClientProvider",
                    chroma_client_auth_credentials=""
                )
            )
            logger.info(f"Connected to ChromaDB at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            return False

    def initialize_collection(self) -> bool:
        """Initialize or get the collection.

        Returns:
            True if successful, False otherwise.
        """
        if not self.client:
            logger.error("Not connected to ChromaDB")
            return False

        try:
            # Try to get existing collection
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Using existing collection: {self.collection_name}")
            return True
        except Exception:
            # Create new collection if doesn't exist
            try:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Created new collection: {self.collection_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to create collection: {e}")
                return False

    def add_listing(self, listing_id: str, embedding: List[float], metadata: Dict[str, Any]) -> bool:
        """Add a listing embedding to the collection.

        Args:
            listing_id: Unique listing identifier
            embedding: 768-dim embedding vector from sentence-transformers
            metadata: Listing metadata (platform, price, area, location, etc.)

        Returns:
            True if added successfully, False otherwise
        """
        if not self.collection:
            logger.error("Collection not initialized")
            return False

        try:
            self.collection.add(
                ids=[listing_id],
                embeddings=[embedding],
                metadatas=[metadata]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add listing: {e}")
            return False

    def batch_add_listings(self, listings: List[Dict[str, Any]]) -> int:
        """Add multiple listings in batch.

        Args:
            listings: List of dicts with keys: id, embedding, metadata

        Returns:
            Number of successfully added listings
        """
        if not self.collection:
            logger.error("Collection not initialized")
            return 0

        try:
            ids = [item['id'] for item in listings]
            embeddings = [item['embedding'] for item in listings]
            metadatas = [item['metadata'] for item in listings]

            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas
            )
            return len(listings)
        except Exception as e:
            logger.error(f"Batch add failed: {e}")
            return 0

    def find_similar_listings(self, embedding: List[float], n_results: int = 5, similarity_threshold: float = 0.92) -> List[Dict[str, Any]]:
        """Find semantically similar listings.

        Args:
            embedding: Query embedding vector
            n_results: Maximum number of results to return
            similarity_threshold: Minimum cosine similarity (0-1)

        Returns:
            List of similar listings with metadata and similarity scores
        """
        if not self.collection:
            logger.error("Collection not initialized")
            return []

        try:
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=n_results
            )

            similar_listings = []
            if results['ids'] and results['ids'][0]:
                for i, listing_id in enumerate(results['ids'][0]):
                    # ChromaDB returns distance, convert to similarity for cosine space
                    # For cosine space: similarity = 1 - distance
                    distance = results['distances'][0][i]
                    similarity = 1 - distance

                    if similarity >= similarity_threshold:
                        similar_listings.append({
                            'id': listing_id,
                            'similarity': similarity,
                            'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
                        })

            return similar_listings
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

    def check_duplicate_by_embedding(self, embedding: List[float], threshold: float = 0.95) -> Optional[str]:
        """Check if listing is a duplicate based on embedding similarity.

        Args:
            embedding: Listing embedding vector
            threshold: Similarity threshold for duplicate detection

        Returns:
            Duplicate listing ID if found, None otherwise
        """
        similar = self.find_similar_listings(embedding, n_results=1, similarity_threshold=threshold)
        return similar[0]['id'] if similar else None

    def get_listing_by_id(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Get a listing by ID.

        Args:
            listing_id: Listing identifier

        Returns:
            Listing data if found, None otherwise
        """
        if not self.collection:
            logger.error("Collection not initialized")
            return None

        try:
            results = self.collection.get(ids=[listing_id], include=['metadatas', 'embeddings'])
            if results['ids'] and results['ids'][0]:
                return {
                    'id': results['ids'][0],
                    'metadata': results['metadatas'][0] if results['metadatas'] else {},
                    'embedding': results['embeddings'][0] if results['embeddings'] else []
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get listing: {e}")
            return None

    def delete_listing(self, listing_id: str) -> bool:
        """Delete a listing from the collection.

        Args:
            listing_id: Listing identifier

        Returns:
            True if deleted, False otherwise
        """
        if not self.collection:
            logger.error("Collection not initialized")
            return False

        try:
            self.collection.delete(ids=[listing_id])
            return True
        except Exception as e:
            logger.error(f"Failed to delete listing: {e}")
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics.

        Returns:
            Dict with count and metadata
        """
        if not self.collection:
            logger.error("Collection not initialized")
            return {}

        try:
            count = self.collection.count()
            return {'count': count, 'name': self.collection_name}
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        self.initialize_collection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # ChromaDB HTTP client doesn't need explicit close
        pass
