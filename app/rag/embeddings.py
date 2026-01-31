"""Embedding generation using sentence-transformers for local vector embeddings."""

from typing import List, Optional
import logging

from sentence_transformers import SentenceTransformer

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings using sentence-transformers (local)."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the embedding generator.

        Args:
            model_name: Name of the sentence-transformer model to use.
                       Defaults to value from settings.
        """
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self.embedding_dimension = settings.embedding_dimension

        # Initialize sentence-transformer model (local, no API key needed)
        logger.info(f"Loading sentence-transformer model: {self.model_name}")
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Successfully loaded model with dimension: {self.embedding_dimension}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise RuntimeError(f"Failed to initialize embedding model: {e}")

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List[float]: Embedding vector

        Raises:
            ValueError: If text is empty
            RuntimeError: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")

        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}")

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once

        Returns:
            List[List[float]]: List of embedding vectors

        Raises:
            ValueError: If texts list is empty
            RuntimeError: If embedding generation fails
        """
        if not texts:
            raise ValueError("Cannot generate embeddings for empty text list")

        # Filter out empty texts and keep track of indices
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            raise ValueError("All texts in the list are empty")

        try:
            # Generate embeddings in batches
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=False
            )

            # Convert to list format
            embedding_list = [emb.tolist() for emb in embeddings]

            # Create result list with None for empty texts
            result = [None] * len(texts)
            for i, embedding in zip(valid_indices, embedding_list):
                result[i] = embedding

            # Remove None values
            result = [emb for emb in result if emb is not None]

            return result

        except Exception as e:
            logger.error(f"Failed to generate embeddings in batch: {e}")
            raise RuntimeError(f"Batch embedding generation failed: {e}")

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.

        Returns:
            int: Embedding dimension
        """
        return self.embedding_dimension


# Global instance
_embedding_generator: Optional[EmbeddingGenerator] = None


def get_embedding_generator() -> EmbeddingGenerator:
    """
    Get or create global embedding generator instance.

    Returns:
        EmbeddingGenerator: The embedding generator
    """
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator
