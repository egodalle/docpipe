from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from docpipe.config import EMBEDDING_MODEL
from docpipe.embed import EmbeddingClient, VertexEmbeddingClient
from docpipe.models import SearchHit
from docpipe.store import connect, insert_query_log, search_chunks as store_search_chunks

EXAMPLE_QUERIES = [
    "What is an HNSW index in pgvector?",
    "How does JSONB store JSON in PostgreSQL?",
    "What is MVCC in Postgres?",
    "How do I create an index in PostgreSQL?",
    "What is write-ahead logging (WAL)?",
]


@dataclass
class SearchResult:
    question: str
    request_id: str
    hits: list[SearchHit]
    latency_ms: int
    model: str


def search_chunks(
    query_embedding: list[float],
    k: int = 5,
    database_url: str | None = None,
    source: str | None = None,
) -> list[SearchHit]:
    with connect(database_url) as conn:
        return store_search_chunks(conn, query_embedding, k=k, source=source)


def ask_neighbors(
    question: str,
    k: int = 5,
    database_url: str | None = None,
    embedding_client: EmbeddingClient | None = None,
    log: bool = True,
) -> SearchResult:
    client = embedding_client or VertexEmbeddingClient()
    started = time.perf_counter()
    vector = client.embed_query(question)
    with connect(database_url) as conn:
        hits = store_search_chunks(conn, vector, k=k)
        latency_ms = int((time.perf_counter() - started) * 1000)
        request_id = str(uuid.uuid4())
        if log:
            insert_query_log(
                conn,
                request_id=request_id,
                question=question,
                chunk_ids=[hit.chunk_id for hit in hits],
                scores=[hit.score for hit in hits],
                latency_ms=latency_ms,
                model=client.model_name,
                refused=False,
            )
    return SearchResult(
        question=question,
        request_id=request_id,
        hits=hits,
        latency_ms=latency_ms,
        model=client.model_name or EMBEDDING_MODEL,
    )


def run_example_queries(
    k: int = 5,
    database_url: str | None = None,
    embedding_client: EmbeddingClient | None = None,
) -> list[SearchResult]:
    client = embedding_client or VertexEmbeddingClient()
    return [
        ask_neighbors(
            question,
            k=k,
            database_url=database_url,
            embedding_client=client,
            log=True,
        )
        for question in EXAMPLE_QUERIES
    ]
