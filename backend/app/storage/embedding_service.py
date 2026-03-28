"""
EmbeddingService — local embedding via Ollama API

Replaces Zep Cloud's built-in embedding with local nomic-embed-text model.
Uses Ollama's /api/embed endpoint for vector generation (768 dimensions).
"""

import time
import logging
from typing import List, Optional
from functools import lru_cache

import requests

from ..config import Config

logger = logging.getLogger('pitchy.embedding')


class EmbeddingService:
    """Generate embeddings using local Ollama server."""

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 30,
    ):
        self.model = model or Config.EMBEDDING_MODEL
        self.base_url = (base_url or Config.EMBEDDING_BASE_URL).rstrip('/')
        self.max_retries = max_retries
        self.timeout = timeout

        # Detect if it's an OpenAI-compatible provider (RouterAI, etc.)
        # Usually base_url contains /v1, openai, routerai or model is text-embedding-*
        self.is_openai = (
            "/v1" in self.base_url.lower() or 
            "openai" in self.base_url.lower() or
            "routerai" in self.base_url.lower() or
            "text-embedding" in self.model.lower()
        )
        
        if self.is_openai:
            # For OpenAI-compatible, we ensure it ends with /embeddings
            if not self.base_url.endswith("/embeddings"):
                self._embed_url = f"{self.base_url}/embeddings"
            else:
                self._embed_url = self.base_url
        else:
            # Default Ollama /api/embed
            self._embed_url = f"{self.base_url}/api/embed"

        logger.info(f"EmbeddingService initialized: model={self.model}, is_openai={self.is_openai}, url={self._embed_url}")

        # Simple in-memory cache (text -> embedding vector)
        self._cache: dict[str, List[float]] = {}
        self._cache_max_size = 2000

    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            768-dimensional float vector (forced size for Neo4j compatibility)

        Raises:
            EmbeddingError: If Ollama/OpenAI request fails after retries
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text")

        text = text.strip()

        # Check cache
        if text in self._cache:
            return self._cache[text]

        vectors = self._request_embeddings([text])
        if not vectors:
            raise EmbeddingError("No embeddings returned from service")
            
        vector = vectors[0]

        # Cache result
        self._cache_put(text, vector)

        return vector

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Processes in batches to avoid overwhelming the service.

        Args:
            texts: List of input texts
            batch_size: Number of texts per request

        Returns:
            List of embedding vectors (same order as input)
        """
        if not texts:
            return []

        results: List[Optional[List[float]]] = [None] * len(texts)
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []

        # Check cache first
        for i, text in enumerate(texts):
            text = text.strip() if text else ""
            if text in self._cache:
                results[i] = self._cache[text]
            elif text:
                uncached_indices.append(i)
                uncached_texts.append(text)
            else:
                # Empty text — zero vector (768 fits current Neo4j schema)
                results[i] = [0.0] * 768

        # Batch-embed uncached texts
        if uncached_texts:
            all_vectors: List[List[float]] = []
            for start in range(0, len(uncached_texts), batch_size):
                batch = uncached_texts[start:start + batch_size]
                vectors = self._request_embeddings(batch)
                all_vectors.extend(vectors)

            # Place results and cache
            for idx, vec, text in zip(uncached_indices, all_vectors, uncached_texts):
                results[idx] = vec
                self._cache_put(text, vec)

        return results  # type: ignore

    def _request_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Make HTTP request to embedding endpoint with retry.
        Supports both Ollama (/api/embed) and OpenAI (/embeddings) formats.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if self.is_openai:
            # OpenAI /embeddings format
            payload = {
                "model": self.model,
                "input": texts,
            }
            # For text-embedding-3-* models, we can request 768 dimensions directly
            if "text-embedding-3" in self.model:
                payload["dimensions"] = 768
        else:
            # Ollama /api/embed format
            payload = {
                "model": self.model,
                "input": texts,
            }

        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self._embed_url,
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()

                if self.is_openai:
                    # data = {"data": [{"embedding": [...]}, ...]}
                    embeddings_data = data.get("data", [])
                    # Sort by index if provided, though typically they are in order
                    embeddings_data.sort(key=lambda x: x.get("index", 0))
                    embeddings = [item["embedding"] for item in embeddings_data]
                else:
                    # data = {"embeddings": [[...], ...]}
                    embeddings = data.get("embeddings", [])

                if len(embeddings) != len(texts):
                    raise EmbeddingError(
                        f"Expected {len(texts)} embeddings, got {len(embeddings)}"
                    )

                return embeddings

            except requests.exceptions.ConnectionError as e:
                last_error = e
                logger.warning(
                    f"Embedding connection failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
            except requests.exceptions.Timeout as e:
                last_error = e
                logger.warning(
                    f"Embedding request timed out (attempt {attempt + 1}/{self.max_retries})"
                )
            except requests.exceptions.HTTPError as e:
                last_error = e
                logger.error(f"Embedding HTTP error: {e.response.status_code} - {e.response.text} URL: {self._embed_url}")
                if e.response.status_code >= 500:
                    # Server error — retry
                    pass
                else:
                    # Client error (4xx) — don't retry
                    raise EmbeddingError(f"Embedding failed: {e}") from e
            except (KeyError, ValueError) as e:
                raise EmbeddingError(f"Invalid embedding response: {e}") from e

            # Exponential backoff
            if attempt < self.max_retries - 1:
                wait = 2 ** attempt
                logger.info(f"Retrying in {wait}s...")
                time.sleep(wait)

        raise EmbeddingError(
            f"Embedding failed after {self.max_retries} retries: {last_error}"
        )

    def _cache_put(self, text: str, vector: List[float]) -> None:
        """Add to cache, evicting oldest entries if full."""
        if len(self._cache) >= self._cache_max_size:
            # Remove ~10% of oldest entries
            keys_to_remove = list(self._cache.keys())[:self._cache_max_size // 10]
            for key in keys_to_remove:
                del self._cache[key]
        self._cache[text] = vector

    def health_check(self) -> bool:
        """Check if Ollama embedding endpoint is reachable."""
        try:
            vec = self.embed("health check")
            return len(vec) > 0
        except Exception:
            return False


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""
    pass
