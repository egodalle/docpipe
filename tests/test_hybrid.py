from __future__ import annotations

import os

import pytest

from docpipe.index import index_corpus
from docpipe.retrieve import retrieve_hits
from docpipe.store import apply_hybrid_schema, connect, search_chunks_lexical
from tests.test_index import FakeEmbeddingClient, _cleanup, _seed_two_docs

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://docpipe:docpipe@127.0.0.1:5433/docpipe",
)


@pytest.fixture
def db() -> str:
    try:
        with connect(DATABASE_URL) as conn:
            conn.execute("SELECT 1")
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"postgres unavailable: {exc}")
    return DATABASE_URL


def test_lexical_and_hybrid_retrieve_seeded_docs(
    tmp_path, monkeypatch: pytest.MonkeyPatch, db: str
) -> None:
    monkeypatch.setenv("DOCS_SKIP_BQ", "1")
    prefix = _seed_two_docs(tmp_path, monkeypatch, db)
    embedder = FakeEmbeddingClient()
    try:
        index_corpus(
            raw_dir=tmp_path / "raw",
            database_url=db,
            embedding_client=embedder,
        )
        vector = embedder.embed_query("HNSW indexes support cosine distance in pgvector.")
        with connect(db) as conn:
            apply_hybrid_schema(conn)
            lexical = search_chunks_lexical(
                conn, "HNSW indexes support cosine distance in pgvector.", k=5
            )
            assert lexical
            assert any("a.md" in hit.uri for hit in lexical)
            hybrid = retrieve_hits(
                conn,
                question="HNSW indexes support cosine distance in pgvector.",
                query_embedding=vector,
                k=5,
                hybrid=True,
                unique_documents=True,
                pool_k=8,
            )
            vector_only = retrieve_hits(
                conn,
                question="HNSW indexes support cosine distance in pgvector.",
                query_embedding=vector,
                k=5,
                hybrid=False,
                unique_documents=True,
                pool_k=8,
            )
        assert hybrid
        assert vector_only
        assert any("a.md" in hit.uri for hit in hybrid)
        assert any("a.md" in hit.uri for hit in vector_only)
    finally:
        _cleanup(prefix)
