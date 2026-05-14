"""External RAG client.

Talks to the pitchy.pro RAG endpoint (``MAIN_SERVER_RAG_URL``) to enrich
profile generation and report writing with real market context for the
Russian startup ecosystem (gov-funds, marketplaces, regulatory docs, etc.).

Supports two response shapes:

1. **Legacy**: ``{"context": "<joined string>"}``
2. **Extended** (after the dev.pitchy.pro upgrade): ``{"context": "...", "chunks": [{"text", "score", "metadata"}], "count": N}``

Callers can use either ``get_market_context()`` for the simple text-only path
or ``search()`` to get back full ``RagSearchResult`` with chunk scores and
metadata for downstream attribution.
"""

import httpx
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('pitchy.rag_service')


@dataclass
class RagChunk:
    """One retrieved chunk with its similarity score and source metadata."""
    text: str
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "score": self.score, "metadata": self.metadata}

    def source_label(self) -> str:
        """Best-effort human-readable source label for attribution in reports."""
        src = self.metadata.get("source") or self.metadata.get("url") or ""
        coll = self.metadata.get("collection") or self.metadata.get("category") or ""
        if src and coll:
            return f"{coll}: {src}"
        return src or coll or ""


@dataclass
class RagSearchResult:
    """Full RAG response — keeps chunks separately from the joined context.

    `context` is convenient for stuffing directly into an LLM prompt;
    `chunks` lets the caller cite individual sources.
    """
    context: str = ""
    chunks: List[RagChunk] = field(default_factory=list)
    count: int = 0

    @property
    def is_empty(self) -> bool:
        return not self.context.strip() and not self.chunks

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context": self.context,
            "chunks": [c.to_dict() for c in self.chunks],
            "count": self.count,
        }


class RagService:
    """Client for the external Pitchy RAG endpoint.

    Both methods are safe by design: any network error, auth failure, or
    unexpected payload shape returns an empty result rather than raising,
    so RAG outages never block profile generation or report writing.
    """

    DEFAULT_TIMEOUT_SECONDS = 30.0

    @staticmethod
    def _build_headers() -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if Config.RAG_API_KEY:
            headers["Authorization"] = f"Bearer {Config.RAG_API_KEY}"
        return headers

    @classmethod
    async def search(
        cls,
        query: str,
        top_k: int = 5,
        categories: Optional[List[str]] = None,
        chunks_only: bool = False,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> RagSearchResult:
        """Run a RAG search and return ``RagSearchResult``.

        ``top_k``, ``categories`` and ``chunks_only`` are passed to the
        extended endpoint when available; legacy endpoints ignore them
        silently because they read only the ``query`` field.
        """
        if not Config.MAIN_SERVER_RAG_URL:
            logger.warning("MAIN_SERVER_RAG_URL not configured, skipping RAG lookup")
            return RagSearchResult()

        # Cap top_k to the endpoint's documented range (1..20)
        try:
            top_k_int = max(1, min(20, int(top_k)))
        except (TypeError, ValueError):
            top_k_int = 5

        payload: Dict[str, Any] = {"query": query, "top_k": top_k_int}
        if categories:
            payload["categories"] = [c for c in categories if c]
        if chunks_only:
            payload["chunks_only"] = True

        logger.info(
            f"RAG search → {Config.MAIN_SERVER_RAG_URL} "
            f"(top_k={top_k_int}, categories={categories or '∅'}, q='{query[:60]}…')"
        )

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    Config.MAIN_SERVER_RAG_URL,
                    json=payload,
                    headers=cls._build_headers(),
                )

            if response.status_code != 200:
                # Truncate body in logs — auth failures sometimes return
                # large HTML pages from upstream load balancers.
                logger.error(
                    f"RAG service HTTP {response.status_code}: {response.text[:200]}"
                )
                return RagSearchResult()

            data: Any = response.json()
        except httpx.ConnectError:
            logger.error("RAG: connection error")
            return RagSearchResult()
        except httpx.TimeoutException:
            logger.error(f"RAG: timed out after {timeout}s")
            return RagSearchResult()
        except Exception as e:
            logger.error(f"RAG: unexpected error: {e}")
            return RagSearchResult()

        return cls._parse_response(data)

    @classmethod
    def _parse_response(cls, data: Any) -> RagSearchResult:
        """Tolerant parser for both legacy and extended response shapes."""
        if not isinstance(data, dict):
            # Some old endpoints returned a bare string
            if isinstance(data, str) and data.strip():
                return RagSearchResult(context=data, count=1)
            return RagSearchResult()

        # 1. Extract free-form context string from any plausible field
        context = ""
        for key in ("context", "result", "answer", "content"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                context = val
                break

        # Some servers wrap payload under "data"
        if not context and isinstance(data.get("data"), dict):
            inner = data["data"]
            for key in ("context", "result", "answer", "content"):
                val = inner.get(key)
                if isinstance(val, str) and val.strip():
                    context = val
                    break

        # 2. Extract structured chunks if endpoint supports them
        chunks: List[RagChunk] = []
        raw_chunks = data.get("chunks")
        if isinstance(raw_chunks, list):
            for raw in raw_chunks:
                if not isinstance(raw, dict):
                    continue
                text = raw.get("text") or raw.get("content") or ""
                if not text:
                    continue
                try:
                    score = float(raw.get("score") or 0.0)
                except (TypeError, ValueError):
                    score = 0.0
                metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
                chunks.append(RagChunk(text=str(text), score=score, metadata=metadata))

        # If we got chunks but no joined context, synthesise one so the
        # legacy `get_market_context()` callers still work.
        if not context and chunks:
            context = "\n\n".join(c.text for c in chunks)

        try:
            count = int(data.get("count") or len(chunks))
        except (TypeError, ValueError):
            count = len(chunks)

        result = RagSearchResult(context=context, chunks=chunks, count=count)
        if result.is_empty:
            logger.info("RAG returned empty result (no hits for this query)")
        else:
            logger.info(
                f"RAG OK: {len(chunks)} chunks, {len(context)} chars context"
            )
        return result

    @classmethod
    async def get_market_context(
        cls, startup_description: str, top_k: int = 5
    ) -> str:
        """Backwards-compatible helper — returns joined context string only.

        Existing callers (profile generator, report agent) use this and
        don't need chunk-level metadata yet.
        """
        result = await cls.search(query=startup_description, top_k=top_k)
        return result.context
