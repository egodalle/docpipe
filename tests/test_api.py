from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from docpipe.api import app, get_bq, get_embedding_client, get_generator
from docpipe.ask import AskValidationError, validate_ask
from docpipe.config import K_MAX, QUESTION_MAX_CHARS, REFUSE_MIN_SCORE
from docpipe.index import index_corpus
from docpipe.store import connect
from tests.test_index import FakeEmbeddingClient, _cleanup, _seed_two_docs

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://docpipe:docpipe@127.0.0.1:5433/docpipe",
)


class FakeGenerator:
    model_name = "gemini-3-flash-preview"

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    def generate(self, question: str, hits) -> str:
        self.calls.append((question, [hit.chunk_id for hit in hits]))
        return f"Cited answer about {hits[0].body.split()[0]}"


class RecordingBq:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def write_query_log(self, row: dict) -> None:
        self.rows.append(row)


@pytest.fixture
def db() -> str:
    try:
        with connect(DATABASE_URL) as conn:
            conn.execute("SELECT 1")
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"postgres unavailable: {exc}")
    return DATABASE_URL


@pytest.fixture
def api(tmp_path, monkeypatch: pytest.MonkeyPatch, db: str):
    monkeypatch.setenv("DOCS_SKIP_BQ", "1")
    prefix = _seed_two_docs(tmp_path, monkeypatch, db)
    embedder = FakeEmbeddingClient()
    index_corpus(
        raw_dir=tmp_path / "raw",
        database_url=db,
        embedding_client=embedder,
    )
    gen = FakeGenerator()
    bq = RecordingBq()
    app.dependency_overrides[get_embedding_client] = lambda: embedder
    app.dependency_overrides[get_generator] = lambda: gen
    app.dependency_overrides[get_bq] = lambda: bq
    try:
        yield TestClient(app), gen, bq, prefix
    finally:
        app.dependency_overrides.clear()
        _cleanup(prefix)


def test_health_and_stats(api) -> None:
    client, _gen, _bq, _prefix = api
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True
    stats = client.get("/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["documents"] >= 2
    assert body["chunks"] >= 2
    assert body["embeddings"] >= 2
    assert body["embedding_dim"] == 768
    assert "query_logs" in body


def test_ask_returns_citations(api) -> None:
    client, gen, bq, prefix = api
    response = client.post(
        "/ask",
        json={"question": "HNSW indexes support cosine distance in pgvector."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is False
    assert body["answer"]
    assert body["citations"]
    assert "a.md" in body["citations"][0]["uri"]
    assert body["citations"][0]["score"] >= REFUSE_MIN_SCORE
    assert gen.calls
    assert bq.rows and bq.rows[0]["refused"] is False
    with connect() as conn:
        row = conn.execute(
            "SELECT answer, refused FROM query_logs WHERE request_id = %s",
            (body["request_id"],),
        ).fetchone()
        assert row is not None
        assert row[1] is False
        assert row[0]


def test_off_topic_questions_are_refused(api) -> None:
    client, gen, bq, _prefix = api
    questions = [
        "What is the weather in Paris tomorrow?",
        "How do I bake sourdough bread at home?",
    ]
    gen.calls.clear()
    for question in questions:
        response = client.post("/ask", json={"question": question})
        assert response.status_code == 200
        body = response.json()
        assert body["refused"] is True
        assert body["answer"] is None
    assert gen.calls == []
    assert all(row["refused"] is True for row in bq.rows[-2:])


def test_question_length_and_k_caps(api) -> None:
    client, gen, _bq, _prefix = api
    too_long = client.post("/ask", json={"question": "x" * (QUESTION_MAX_CHARS + 1)})
    assert too_long.status_code == 422
    too_wide = client.post("/ask", json={"question": "What is JSONB?", "k": K_MAX + 1})
    assert too_wide.status_code == 422
    blank = client.post("/ask", json={"question": "   "})
    assert blank.status_code == 422
    assert gen.calls == []


def test_invalid_source_is_rejected(api) -> None:
    client, _gen, _bq, _prefix = api
    response = client.post(
        "/ask",
        json={"question": "What is JSONB?", "source": "wikipedia"},
    )
    assert response.status_code == 422


def test_validate_ask_bounds() -> None:
    with pytest.raises(AskValidationError):
        validate_ask("")
    with pytest.raises(AskValidationError):
        validate_ask("ok", k=0)
    cleaned, k, source = validate_ask("  JSONB  ", k=3, source="pgvector")
    assert cleaned == "JSONB"
    assert k == 3
    assert source == "pgvector"
