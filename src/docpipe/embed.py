from __future__ import annotations

import time
from typing import Protocol

from docpipe.config import (
    EMBEDDING_BATCH,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    GCP_LOCATION,
    GCP_PROJECT,
)
from docpipe.quality import QualityError

# text-embedding-004 request cap is 20k input tokens across the batch.
_MAX_BATCH_INPUT_TOKENS = 16000


class DimMismatchError(QualityError):
    pass


class EmbeddingClient(Protocol):
    model_name: str
    dim: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...


def _retryable(exc: BaseException) -> bool:
    text = str(exc).lower()
    return (
        "429" in text
        or "resource exhausted" in text
        or "unavailable" in text
        or "deadline" in text
        or "reset" in text
    )


class VertexEmbeddingClient:
    def __init__(
        self,
        model_name: str | None = None,
        dim: int | None = None,
        project: str | None = None,
        location: str | None = None,
        batch_size: int | None = None,
    ) -> None:
        self.model_name = model_name or EMBEDDING_MODEL
        self.dim = dim if dim is not None else EMBEDDING_DIM
        if self.dim != EMBEDDING_DIM:
            raise DimMismatchError(
                f"client dim {self.dim} != config {EMBEDDING_DIM}"
            )
        self.project = project or GCP_PROJECT
        self.location = location or GCP_LOCATION
        self.batch_size = batch_size or EMBEDDING_BATCH
        self._model = None

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self._ensure()
        out: list[list[float]] = []
        for batch in _pack_batches(texts, self.batch_size, _MAX_BATCH_INPUT_TOKENS):
            out.extend(self._embed_batch(batch, task_type="RETRIEVAL_DOCUMENT"))
        return out

    def embed_query(self, text: str) -> list[float]:
        vectors = self._embed_batch([text], task_type="RETRIEVAL_QUERY")
        return vectors[0]

    def _ensure(self) -> None:
        if self._model is not None:
            return
        import vertexai
        from vertexai.language_models import TextEmbeddingModel

        vertexai.init(project=self.project, location=self.location)
        self._model = TextEmbeddingModel.from_pretrained(self.model_name)

    def _embed_batch(self, texts: list[str], task_type: str) -> list[list[float]]:
        self._ensure()
        from vertexai.language_models import TextEmbeddingInput

        inputs: list[object] = [
            TextEmbeddingInput(text=text, task_type=task_type) for text in texts
        ]
        last_exc: BaseException | None = None
        for attempt in range(5):
            try:
                embeddings = self._model.get_embeddings(inputs)
                values = [list(item.values) for item in embeddings]
                self._check_dims(values)
                return values
            except DimMismatchError:
                raise
            except Exception as exc:  # pragma: no cover - live API
                last_exc = exc
                if attempt == 0 and "task_type" in str(exc).lower():
                    inputs = list(texts)
                    continue
                if not _retryable(exc) or attempt == 4:
                    raise
                time.sleep(2**attempt)
        raise RuntimeError(f"embed failed: {last_exc}")

    def _check_dims(self, values: list[list[float]]) -> None:
        for vector in values:
            if len(vector) != self.dim:
                raise DimMismatchError(
                    f"live model {self.model_name} returned dim {len(vector)}, "
                    f"config/sql frozen at {self.dim}; ALTER + ADR 0003 required"
                )


def _estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def _pack_batches(texts: list[str], batch_size: int, max_tokens: int) -> list[list[str]]:
    batches: list[list[str]] = []
    current: list[str] = []
    tokens = 0
    for text in texts:
        cost = _estimate_tokens(text)
        overflow = current and (
            len(current) >= batch_size or tokens + cost > max_tokens
        )
        if overflow:
            batches.append(current)
            current = []
            tokens = 0
        current.append(text)
        tokens += cost
    if current:
        batches.append(current)
    return batches

