from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from docpipe.evalrun import (
    GOLDEN_PATH,
    expected_in_hits,
    load_golden,
    pick_topk,
    run_eval,
    uri_basename,
)
from docpipe.index import index_corpus
from docpipe.models import SearchHit
from docpipe.store import connect
from tests.test_index import FakeEmbeddingClient, _cleanup, _seed_two_docs

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://docpipe:docpipe@127.0.0.1:5433/docpipe",
)


def _hit(uri: str, score: float = 0.8) -> SearchHit:
    return SearchHit(
        chunk_id="c",
        document_id="d",
        uri=uri,
        source="pgvector",
        ordinal=0,
        body="body",
        score=score,
    )


def test_golden_set_size_and_basenames() -> None:
    items = load_golden()
    assert 20 <= len(items) <= 30
    assert GOLDEN_PATH.exists()
    for item in items:
        assert item.question
        assert item.expected_uris
        assert all("/" not in name for name in item.expected_uris)


def test_uri_basename_and_hit() -> None:
    assert uri_basename("file:///tmp/raw/postgres-docs/datatype-json.html") == (
        "datatype-json.html"
    )
    hits = [
        _hit("file:///x/datatype-json.html", 0.9),
        _hit("file:///x/gin.html", 0.7),
    ]
    assert expected_in_hits(["datatype-json.html"], hits) is True
    assert expected_in_hits(["mvcc.html"], hits) is False


def test_pick_topk_unique_documents() -> None:
    hits = [
        _hit("a.md", 0.9),
        _hit("a.md", 0.85),
        _hit("a.md", 0.8),
        _hit("b.md", 0.7),
        _hit("c.md", 0.6),
        _hit("d.md", 0.5),
        _hit("e.md", 0.4),
    ]
    raw = pick_topk(hits, k=5, unique_documents=False)
    assert [h.uri for h in raw] == ["a.md", "a.md", "a.md", "b.md", "c.md"]
    unique = pick_topk(hits, k=5, unique_documents=True)
    assert [h.uri for h in unique] == ["a.md", "b.md", "c.md", "d.md", "e.md"]


@pytest.fixture
def db() -> str:
    try:
        with connect(DATABASE_URL) as conn:
            conn.execute("SELECT 1")
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"postgres unavailable: {exc}")
    return DATABASE_URL


def test_run_eval_scores_seeded_docs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db: str
) -> None:
    monkeypatch.setenv("DOCS_SKIP_BQ", "1")
    prefix = _seed_two_docs(tmp_path, monkeypatch, db)
    embedder = FakeEmbeddingClient()
    index_corpus(
        raw_dir=tmp_path / "raw",
        database_url=db,
        embedding_client=embedder,
    )
    golden = tmp_path / "golden.json"
    items = []
    for i in range(10):
        items.append(
            {
                "id": f"hnsw-{i}",
                "question": "HNSW indexes support cosine distance in pgvector.",
                "expected_uris": ["a.md"],
            }
        )
        items.append(
            {
                "id": f"jsonb-{i}",
                "question": "JSONB stores JSON in PostgreSQL as a binary format.",
                "expected_uris": ["b.md"],
            }
        )
    golden.write_text(json.dumps({"items": items}), encoding="utf-8")
    try:
        report = run_eval(
            unique_documents=False,
            k=5,
            database_url=db,
            embedding_client=embedder,
            golden_path=golden,
            persist=True,
            run_id="eval-test-local",
        )
        assert report.n == 20
        assert report.recall_at_5 >= 0.70
        with connect(db) as conn:
            count = conn.execute(
                "SELECT count(*) FROM eval_results WHERE run_id = %s",
                ("eval-test-local",),
            ).fetchone()
            assert count is not None
            assert count[0] == 20
    finally:
        with connect(db) as conn:
            conn.execute("DELETE FROM eval_results WHERE run_id = %s", ("eval-test-local",))
        _cleanup(prefix)
