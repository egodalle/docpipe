from __future__ import annotations

import csv
import hashlib
import math
import os
from pathlib import Path

import pytest

from docpipe.config import EMBEDDING_DIM, EMBEDDING_MODEL
from docpipe.index import index_corpus
from docpipe.ingest import ingest_corpus
from docpipe.licenses import load_licenses
from docpipe.models import Source
from docpipe.quality import QualityError, assert_index_quality
from docpipe.search import ask_neighbors, search_chunks
from docpipe.store import connect, insert_embedding

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://docpipe:docpipe@127.0.0.1:5433/docpipe",
)


class FakeEmbeddingClient:
    def __init__(self, dim: int = EMBEDDING_DIM, model_name: str = EMBEDDING_MODEL) -> None:
        self.dim = dim
        self.model_name = model_name
        self.document_calls: list[list[str]] = []
        self.query_calls: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls.append(list(texts))
        return [_hash_vector(text, self.dim) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        self.query_calls.append(text)
        return _hash_vector(text, self.dim)


def _hash_vector(text: str, dim: int) -> list[float]:
    values = [0.0] * dim
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        values[index] += 1.0
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


@pytest.fixture
def db() -> str:
    try:
        with connect(DATABASE_URL) as conn:
            conn.execute("SELECT 1")
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"postgres unavailable: {exc}")
    return DATABASE_URL


def _write_licenses(path: Path, files: list[tuple[str, str]]) -> None:
    rows = [
        {
            "file": name,
            "source": source,
            "license": "PostgreSQL",
            "license_url": "https://example.com/license",
            "origin_url": f"https://example.com/{name}",
        }
        for name, source in files
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["file", "source", "license", "license_url", "origin_url"],
        )
        writer.writeheader()
        writer.writerows(rows)


def _cleanup(prefix: str) -> None:
    with connect(DATABASE_URL) as conn:
        conn.execute("DELETE FROM documents WHERE uri LIKE %s", (prefix + "%",))


def _seed_two_docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db: str) -> str:
    raw = tmp_path / "raw" / Source.pgvector.value
    raw.mkdir(parents=True)
    (raw / "a.md").write_text(
        "# HNSW\n\nHNSW indexes support cosine distance in pgvector.\n",
        encoding="utf-8",
    )
    (raw / "b.md").write_text(
        "# JSONB\n\nJSONB stores JSON in PostgreSQL as a binary format.\n",
        encoding="utf-8",
    )
    licenses = tmp_path / "licenses.csv"
    _write_licenses(licenses, [("a.md", "pgvector"), ("b.md", "pgvector")])
    monkeypatch.setattr("docpipe.ingest.load_licenses", lambda: load_licenses(licenses))
    monkeypatch.setattr("docpipe.index.load_licenses", lambda: load_licenses(licenses))
    prefix = tmp_path.resolve().as_uri()
    _cleanup(prefix)
    ingest_corpus(
        raw_dir=tmp_path / "raw",
        quarantine_dir=tmp_path / "quarantine",
        database_url=db,
    )
    return prefix


def test_index_skip_known_hash_and_dim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db: str
) -> None:
    prefix = _seed_two_docs(tmp_path, monkeypatch, db)
    client = FakeEmbeddingClient()
    try:
        first = index_corpus(
            raw_dir=tmp_path / "raw",
            database_url=db,
            embedding_client=client,
        )
        assert first.chunked == 2
        assert first.embedded == first.chunk_rows
        assert first.embedded > 0
        assert first.skipped == 0
        with connect(db) as conn:
            dims = conn.execute(
                "SELECT DISTINCT dim, vector_dims(embedding), model FROM embeddings e "
                "JOIN chunks c ON c.id = e.chunk_id "
                "JOIN documents d ON d.id = c.document_id "
                "WHERE d.uri LIKE %s",
                (prefix + "%",),
            ).fetchall()
            assert dims == [(EMBEDDING_DIM, EMBEDDING_DIM, EMBEDDING_MODEL)]
            assert_index_quality(conn)
        first_calls = len(client.document_calls)
        first_embedded = first.embedded
        second = index_corpus(
            raw_dir=tmp_path / "raw",
            database_url=db,
            embedding_client=client,
        )
        assert second.skipped == 2
        assert second.chunked == 0
        assert second.embedded == 0
        assert len(client.document_calls) == first_calls
        with connect(db) as conn:
            count = conn.execute(
                "SELECT count(*) FROM embeddings e "
                "JOIN chunks c ON c.id = e.chunk_id "
                "JOIN documents d ON d.id = c.document_id "
                "WHERE d.uri LIKE %s",
                (prefix + "%",),
            ).fetchone()
            assert count is not None
            assert count[0] == first_embedded
    finally:
        _cleanup(prefix)


def test_index_fails_on_dim_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db: str
) -> None:
    prefix = _seed_two_docs(tmp_path, monkeypatch, db)
    try:
        with pytest.raises(QualityError, match="dim"):
            index_corpus(
                raw_dir=tmp_path / "raw",
                database_url=db,
                embedding_client=FakeEmbeddingClient(dim=32),
            )

        class WrongLengthClient(FakeEmbeddingClient):
            def embed_documents(self, texts: list[str]) -> list[list[float]]:
                self.document_calls.append(list(texts))
                return [[0.1, 0.2, 0.3] for _ in texts]

        with pytest.raises(QualityError, match="dim"):
            index_corpus(
                raw_dir=tmp_path / "raw",
                database_url=db,
                embedding_client=WrongLengthClient(),
            )
    finally:
        _cleanup(prefix)


def test_empty_chunk_body_rejected_by_schema(db: str) -> None:
    uri = "file:///tmp/docpipe-empty-chunk-test"
    with connect(db) as conn:
        conn.execute("DELETE FROM documents WHERE uri = %s", (uri,))
        doc_id = conn.execute(
            """
            INSERT INTO documents (source, uri, content_hash, status, bytes, char_count)
            VALUES ('pgvector', %s, 'abc', 'live', 1, 1)
            RETURNING id::text
            """,
            (uri,),
        ).fetchone()
        assert doc_id is not None
    try:
        with pytest.raises(Exception):
            with connect(db) as conn:
                conn.execute(
                    """
                    INSERT INTO chunks (document_id, ordinal, body, token_count, strategy)
                    VALUES (%s::uuid, 0, '   ', 1, 'recursive_400_80')
                    """,
                    (doc_id[0],),
                )
        with connect(db) as conn:
            assert_index_quality(conn)
    finally:
        with connect(db) as conn:
            conn.execute("DELETE FROM documents WHERE uri = %s", (uri,))


def test_duplicate_live_hash_fails_the_job(db: str) -> None:
    uri_a = "file:///tmp/docpipe-dupe-a"
    uri_b = "file:///tmp/docpipe-dupe-b"
    with connect(db) as conn:
        conn.execute("DELETE FROM documents WHERE uri IN (%s, %s)", (uri_a, uri_b))
        conn.execute(
            """
            INSERT INTO documents (source, uri, content_hash, status, bytes, char_count)
            VALUES ('pgvector', %s, 'deadbeef', 'live', 1, 1)
            """,
            (uri_a,),
        )
    try:
        with pytest.raises(Exception):
            with connect(db) as conn:
                conn.execute(
                    """
                    INSERT INTO documents (source, uri, content_hash, status, bytes, char_count)
                    VALUES ('pgvector', %s, 'deadbeef', 'live', 1, 1)
                    """,
                    (uri_b,),
                )
        with connect(db) as conn:
            assert_index_quality(conn)
    finally:
        with connect(db) as conn:
            conn.execute("DELETE FROM documents WHERE uri IN (%s, %s)", (uri_a, uri_b))


def test_search_chunks_returns_self_neighbor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db: str
) -> None:
    prefix = _seed_two_docs(tmp_path, monkeypatch, db)
    client = FakeEmbeddingClient()
    try:
        index_corpus(
            raw_dir=tmp_path / "raw",
            database_url=db,
            embedding_client=client,
        )
        question = "HNSW indexes support cosine distance in pgvector."
        result = ask_neighbors(
            question,
            k=3,
            database_url=db,
            embedding_client=client,
            log=True,
        )
        assert result.hits
        assert "a.md" in result.hits[0].uri
        assert "HNSW" in result.hits[0].body
        with connect(db) as conn:
            hits = search_chunks(_hash_vector(question, EMBEDDING_DIM), k=1)
            assert hits[0].chunk_id == result.hits[0].chunk_id
            logged = conn.execute(
                "SELECT question FROM query_logs WHERE request_id = %s",
                (result.request_id,),
            ).fetchone()
            assert logged is not None
            assert logged[0] == question
    finally:
        _cleanup(prefix)


def test_insert_embedding_rejects_wrong_vector_width(db: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prefix = _seed_two_docs(tmp_path, monkeypatch, db)
    client = FakeEmbeddingClient()
    try:
        index_corpus(
            raw_dir=tmp_path / "raw",
            database_url=db,
            embedding_client=client,
        )
        with connect(db) as conn:
            row = conn.execute(
                "SELECT c.id::text FROM chunks c JOIN documents d ON d.id = c.document_id "
                "WHERE d.uri LIKE %s LIMIT 1",
                (prefix + "%",),
            ).fetchone()
            assert row is not None
            with pytest.raises(Exception):
                insert_embedding(conn, row[0], [0.1, 0.2, 0.3], dim=768)
    finally:
        _cleanup(prefix)
