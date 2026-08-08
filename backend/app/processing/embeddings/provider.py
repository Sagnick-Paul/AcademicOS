"""Sentence Transformers embedding provider implementation."""
from __future__ import annotations

from typing import List
import anyio
from app.core.config import settings
from app.processing.exceptions import EmbeddingGenerationFailed
from app.processing.embeddings.base import BaseEmbeddingProvider


class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    """Local Sentence Transformers embedding provider."""

    def __init__(self, model_name: str | None = None, dimension: int | None = None) -> None:
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.dimension = dimension or settings.EMBEDDING_DIMENSION
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except Exception as exc:
                raise EmbeddingGenerationFailed(
                    f"Failed to load sentence-transformers model {self.model_name}: {exc}"
                ) from exc
        return self._model

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # If in test mode, return deterministic dummy embeddings to avoid download/GPU overhead in CI/CD
        if settings.ENVIRONMENT == "test":
            import numpy as np
            embeddings = []
            for text in texts:
                # Deterministic fake embedding based on string contents
                char_sum = sum(ord(c) for c in text)
                np.random.seed(char_sum % (2**32 - 1))
                vec = np.random.uniform(-1.0, 1.0, self.dimension).tolist()
                embeddings.append(vec)
            return embeddings

        try:
            model = self._get_model()
            # Encode blocking call run in a thread
            embeddings = await anyio.to_thread.run_sync(model.encode, texts)
            return [x.tolist() for x in embeddings]
        except Exception as exc:
            raise EmbeddingGenerationFailed(f"Failed to generate embeddings: {exc}") from exc

    async def generate_embedding(self, text: str) -> List[float]:
        embeddings = await self.generate_embeddings([text])
        if not embeddings:
            raise EmbeddingGenerationFailed("Generated empty embedding list")
        return embeddings[0]


def get_embedding_provider(provider_name: str) -> BaseEmbeddingProvider:
    """Factory function to get embedding provider by name."""
    provider_name_lower = provider_name.lower()
    if provider_name_lower in ("local", "sentence-transformers"):
        return SentenceTransformerEmbeddingProvider()
    elif provider_name_lower in ("gemini", "openai", "voyage", "jina"):
        raise ValueError(f"Provider {provider_name} is not implemented yet.")
    else:
        raise ValueError(f"Unsupported embedding provider: {provider_name}")

