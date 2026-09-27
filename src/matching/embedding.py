"""
SIH26099 Neural Dense Embedding Service
Provides cached, singleton-managed embedding generation using all-MiniLM-L6-v2.
Generates L2-normalized embeddings for fast cosine similarity and candidate retrieval.
"""

import numpy as np
from typing import Optional, Union
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    _instance: Optional["EmbeddingService"] = None
    _model: Optional[SentenceTransformer] = None
    _model_name: str = "all-MiniLM-L6-v2"

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance._init_model()
        return cls._instance

    def _init_model(self) -> None:
        """Initialize and cache the sentence-transformers model."""
        if self._model is None:
            # Load all-MiniLM-L6-v2 once
            self._model = SentenceTransformer(self._model_name)

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._init_model()
        return self._model

    def encode(self, texts: Union[str, list[str]], batch_size: int = 32) -> np.ndarray:
        """
        Generate L2-normalized dense embeddings for a text or batch of texts.
        Returns: numpy array of shape (N, 384) or (384,)
        """
        is_single = isinstance(texts, str)
        input_list = [texts] if is_single else texts

        if not input_list:
            return np.zeros((0, 384), dtype=np.float32)

        embeddings = self.model.encode(
            input_list,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return embeddings[0] if is_single else embeddings

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """Compute cosine similarity between two texts using their dense embeddings."""
        emb_a = self.encode(text_a)
        emb_b = self.encode(text_b)
        # For L2-normalized vectors, cosine similarity equals the dot product
        cos_sim = float(np.dot(emb_a, emb_b))
        return max(0.0, min(1.0, round(cos_sim, 4)))

    def compute_similarity_matrix(self, embeddings_a: np.ndarray, embeddings_b: np.ndarray) -> np.ndarray:
        """Compute cosine similarity matrix between two sets of L2-normalized embeddings."""
        return np.dot(embeddings_a, embeddings_b.T)


# Global singleton instance
embedding_service = EmbeddingService()


def get_embedding_service() -> EmbeddingService:
    """Retrieve global EmbeddingService singleton."""
    return embedding_service
