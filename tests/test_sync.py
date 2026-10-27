from __future__ import annotations

import os
from pathlib import Path

import pytest

from docpipe.index import index_corpus
from docpipe.ingest import ingest_corpus
from docpipe.licenses import load_licenses
from docpipe.quality import QualityError, assert_index_quality
from docpipe.store import connect
from docpipe.sync import sync_corpus
from tests.test_index import FakeEmbeddingClient, _cleanup, _seed_two_docs, _write_licenses

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


def test_one_file_edit_reindexes_only_that_doc(
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
        (tmp_path / "raw" / "pgvector" / "a.md").write_text(
            "# HNSW\n\nHNSW indexes support cosine distance in pgvector. Edited.\n",
            encoding="utf-8",
        )
        client.document_calls.clear()
        report = sync_corpus(
            raw_dir=tmp_path / "raw",
            quarantine_dir=tmp_path / "quarantine",
            database_url=db,
            embedding_client=client,
        )
        assert report.ingest.updated == 1
        assert report.ingest.skipped == 1
        assert report.ingest.inserted == 0
        assert report.ingest.tombstoned == 0
        assert report.index.chunked == 1
        assert report.index.skipped == 1
        assert report.index.embedded == report.index.chunk_rows
        assert len(client.document_calls) == 1
        with connect(db) as conn:
            live = conn.execute(
                "SELECT count(*) FROM documents WHERE uri LIKE %s AND status = 'live'",
                (prefix + "%",),
            ).fetchone()
            tomb = conn.execute(
                "SELECT count(*) FROM documents WHERE uri LIKE %s AND status = 'tombstoned'",
                (prefix + "%",),
            ).fetchone()
            a_chunks = conn.execute(
                """
                SELECT count(*) FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE d.status = 'live' AND d.uri LIKE %s
                """,
                (prefix + "%/a.md",),
            ).fetchone()
            b_chunks = conn.execute(
                """
                SELECT count(*) FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE d.status = 'live' AND d.uri LIKE %s
                """,
                (prefix + "%/b.md",),
            ).fetchone()
            assert live is not None and live[0] == 2
            assert tomb is not None and tomb[0] == 1
            assert a_chunks is not None and a_chunks[0] == report.index.embedded
            assert b_chunks is not None and b_chunks[0] >= 1
            assert_index_quality(conn)
    finally:
        _cleanup(prefix)


def test_removed_file_is_tombstoned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db: str
) -> None:
    prefix = _seed_two_docs(tmp_path, monkeypatch, db)
    try:
        (tmp_path / "raw" / "pgvector" / "b.md").unlink()
        licenses = tmp_path / "licenses.csv"
        _write_licenses(licenses, [("a.md", "pgvector")])
        monkeypatch.setattr("docpipe.ingest.load_licenses", lambda: load_licenses(licenses))
        report = ingest_corpus(
            raw_dir=tmp_path / "raw",
            quarantine_dir=tmp_path / "quarantine",
            database_url=db,
        )
        assert report.skipped == 1
        assert report.tombstoned == 1
        with connect(db) as conn:
            statuses = dict(
                conn.execute(
                    "SELECT split_part(uri, '/', -1), status FROM documents "
                    "WHERE uri LIKE %s",
                    (prefix + "%",),
                ).fetchall()
            )
            assert statuses["a.md"] == "live"
            assert statuses["b.md"] == "tombstoned"
            leftover = conn.execute(
                "SELECT count(*) FROM chunks c JOIN documents d ON d.id = c.document_id "
                "WHERE d.uri LIKE %s AND d.status = 'tombstoned'",
                (prefix + "%",),
            ).fetchone()
            assert leftover is not None and leftover[0] == 0
            assert_index_quality(conn)
    finally:
        _cleanup(prefix)


def test_chunks_on_tombstoned_docs_fail_the_job(db: str) -> None:
    uri = "file:///tmp/docpipe-stale-chunk"
    with connect(DATABASE_URL) as conn:
        conn.execute("DELETE FROM documents WHERE uri = %s", (uri,))
        doc = conn.execute(
            """
            INSERT INTO documents (source, uri, content_hash, status, bytes, char_count)
            VALUES ('pgvector', %s, 'stale-hash', 'live', 1, 1)
            RETURNING id::text
            """,
            (uri,),
        ).fetchone()
        assert doc is not None
        conn.execute(
            """
            INSERT INTO chunks (document_id, ordinal, body, token_count, strategy)
            VALUES (%s::uuid, 0, 'stale body still attached', 4, 'recursive_400_80')
            """,
            (doc[0],),
        )
        conn.execute(
            "UPDATE documents SET status = 'tombstoned' WHERE id = %s::uuid",
            (doc[0],),
        )
    try:
        with connect(db) as conn:
            with pytest.raises(QualityError, match="non-live"):
                assert_index_quality(conn)
    finally:
        with connect(db) as conn:
            conn.execute("DELETE FROM documents WHERE uri = %s", (uri,))
