import logging
import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Wrapper for sentence-transformers model with lazy loading"""

    def __init__(self):
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info(f"Loading embedding model: {settings.embedding_model_name}")
            self._model = SentenceTransformer(settings.embedding_model_name)
            logger.info("Embedding model loaded successfully")
        return self._model

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([])

        # Convert to embeddings
        embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True  # Better for cosine similarity
        )
        return embeddings

    def embed_single(self, text: str) -> np.ndarray:
        """Convenience method for single text embedding"""
        return self.embed_texts([text])[0]

    @property
    def dimension(self) -> int:
        """Get embedding dimension"""
        return self.model.get_sentence_embedding_dimension()


# Global singleton
_embedding_model = None


def get_embedding_model() -> EmbeddingModel:
    """Get or create the global embedding model instance"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model
