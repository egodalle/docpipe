from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from docpipe.bqlog import BqSink, default_bq_sink, query_log_row
from docpipe.config import (
    GENERATION_MODEL,
    HYBRID_RETRIEVAL,
    K_DEFAULT,
    K_MAX,
    QUESTION_MAX_CHARS,
    REFUSE_MIN_SCORE,
)
from docpipe.embed import EmbeddingClient, VertexEmbeddingClient
from docpipe.generate import Generator, VertexGenerator
from docpipe.licenses import license_for_uri
from docpipe.models import SearchHit, Source
from docpipe.retrieve import retrieve_hits
from docpipe.store import connect, insert_query_log


class AskValidationError(ValueError):
    pass


@dataclass
class Citation:
    uri: str
    chunk_id: str
    snippet: str
    score: float
    source: str = ""
    license: str | None = None


@dataclass
class AskAnswer:
    request_id: str
    question: str
    answer: str | None
    refused: bool
    citations: list[Citation]
    latency_ms: int
    model: str
    retrieval_mode: str = "vector"
    hits: list[SearchHit] = field(default_factory=list)


def snippet(body: str, limit: int = 240) -> str:
    text = " ".join(body.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def citations_from_hits(hits: list[SearchHit]) -> list[Citation]:
    citations: list[Citation] = []
    for hit in hits:
        licensed = license_for_uri(hit.uri)
        citations.append(
            Citation(
                uri=hit.uri,
                chunk_id=hit.chunk_id,
                snippet=snippet(hit.body),
                score=hit.score,
                source=hit.source,
                license=None if licensed is None else licensed.license,
            )
        )
    return citations


def validate_ask(
    question: str,
    k: int | None = None,
    source: str | None = None,
) -> tuple[str, int, str | None]:
    cleaned = " ".join((question or "").split())
    if not cleaned:
        raise AskValidationError("question is required")
    if len(cleaned) > QUESTION_MAX_CHARS:
        raise AskValidationError(
            f"question exceeds {QUESTION_MAX_CHARS} characters"
        )
    use_k = K_DEFAULT if k is None else int(k)
    if use_k < 1 or use_k > K_MAX:
        raise AskValidationError(f"k must be between 1 and {K_MAX}")
    use_source: str | None = None
    if source:
        try:
            use_source = Source(source).value
        except ValueError as exc:
            allowed = ", ".join(item.value for item in Source)
            raise AskValidationError(f"source must be one of: {allowed}") from exc
    return cleaned, use_k, use_source


def ask(
    question: str,
    *,
    k: int | None = None,
    source: str | None = None,
    request_id: str | None = None,
    database_url: str | None = None,
    embedding_client: EmbeddingClient | None = None,
    generator: Generator | None = None,
    bq: BqSink | None = None,
    hybrid: bool | None = None,
) -> AskAnswer:
    cleaned, use_k, use_source = validate_ask(question, k=k, source=source)
    embedder = embedding_client or VertexEmbeddingClient()
    gen = generator or VertexGenerator()
    sink = bq if bq is not None else default_bq_sink()
    req = request_id or str(uuid.uuid4())
    use_hybrid = HYBRID_RETRIEVAL if hybrid is None else hybrid
    started = time.perf_counter()
    vector = embedder.embed_query(cleaned)
    with connect(database_url) as conn:
        hits = retrieve_hits(
            conn,
            question=cleaned,
            query_embedding=vector,
            k=use_k,
            source=use_source,
            hybrid=use_hybrid,
        )
        top = hits[0].score if hits else 0.0
        refused = (not hits) or top < REFUSE_MIN_SCORE
        answer: str | None = None
        model = GENERATION_MODEL
        if not refused:
            answer = gen.generate(cleaned, hits)
            model = gen.model_name
        latency_ms = int((time.perf_counter() - started) * 1000)
        insert_query_log(
            conn,
            request_id=req,
            question=cleaned,
            chunk_ids=[hit.chunk_id for hit in hits],
            scores=[hit.score for hit in hits],
            latency_ms=latency_ms,
            model=model,
            refused=refused,
            answer=answer,
        )
    try:
        sink.write_query_log(
            query_log_row(
                request_id=req,
                question=cleaned,
                chunk_ids=[hit.chunk_id for hit in hits],
                scores=[hit.score for hit in hits],
                answer=answer,
                refused=refused,
                latency_ms=latency_ms,
                model=model,
            )
        )
    except Exception:
        # Postgres is the system of record. BQ copy must not fail the ask.
        pass
    return AskAnswer(
        request_id=req,
        question=cleaned,
        answer=answer,
        refused=refused,
        citations=citations_from_hits(hits),
        latency_ms=latency_ms,
        model=model,
        retrieval_mode="hybrid" if use_hybrid else "vector",
        hits=hits,
    )
