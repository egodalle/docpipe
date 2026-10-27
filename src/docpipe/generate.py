from __future__ import annotations

import time
from typing import Protocol

from docpipe.config import (
    GENERATION_LOCATION,
    GENERATION_MODEL,
    GCP_PROJECT,
    MAX_CONTEXT_CHARS,
)
from docpipe.models import SearchHit


class Generator(Protocol):
    model_name: str

    def generate(self, question: str, hits: list[SearchHit]) -> str:
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


def build_prompt(question: str, hits: list[SearchHit], max_chars: int = MAX_CONTEXT_CHARS) -> str:
    parts: list[str] = []
    used = 0
    for hit in hits:
        body = " ".join(hit.body.split())
        block = f"[chunk_id={hit.chunk_id} uri={hit.uri}]\n{body}\n"
        if parts and used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    context = "\n".join(parts) if parts else "(no passages)"
    return (
        "You answer questions using ONLY the passages below. "
        "If the passages are insufficient, say you do not know. "
        "Cite chunk_id values in square brackets for each claim. "
        "Do not use outside knowledge. Do not call tools.\n\n"
        f"Question: {question}\n\n"
        f"Passages:\n{context}\n"
    )


class VertexGenerator:
    """Gemini Flash via the Google Gen AI SDK. Separate location from embeddings."""

    def __init__(
        self,
        model_name: str | None = None,
        project: str | None = None,
        location: str | None = None,
    ) -> None:
        self.model_name = model_name or GENERATION_MODEL
        self.project = project or GCP_PROJECT
        self.location = location or GENERATION_LOCATION
        self._client = None

    def generate(self, question: str, hits: list[SearchHit]) -> str:
        client = self._ensure()
        prompt = build_prompt(question, hits)
        last_exc: BaseException | None = None
        for attempt in range(5):
            try:
                from google.genai import types

                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=2048,
                    ),
                )
                text = getattr(response, "text", None) or ""
                return text.strip()
            except Exception as exc:  # pragma: no cover - live API
                last_exc = exc
                if not _retryable(exc) or attempt == 4:
                    raise
                time.sleep(2**attempt)
        raise RuntimeError(f"generate failed: {last_exc}")

    def _ensure(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(
                vertexai=True,
                project=self.project,
                location=self.location,
            )
        return self._client
