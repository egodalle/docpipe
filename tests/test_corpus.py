from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from docpipe.api import app, get_bq, get_embedding_client, get_generator
from docpipe.corpus import (
    CorpusError,
    discover_corpus,
    reset_active_corpus,
    set_active_corpus,
    slugify_source,
)
from docpipe.index import index_corpus
from docpipe.store import connect
from tests.test_api import FakeGenerator, RecordingBq
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


def test_slugify_source_is_stable() -> None:
    assert slugify_source("Runbooks") == "runbooks"
    assert slugify_source("123 ops") == "corpus-123-ops"


def test_discover_flat_folder(tmp_path: Path) -> None:
    folder = tmp_path / "acme-docs"
    folder.mkdir()
    (folder / "oncall.md").write_text("# Oncall\n\nPage the owner.\n", encoding="utf-8")
    (folder / "ignore.pdf").write_text("nope", encoding="utf-8")
    corpus = discover_corpus(folder)
    assert corpus.layout == "flat"
    assert corpus.sources == ["acme-docs"]
    assert len(corpus.files) == 1
    assert corpus.files[0][0].file == "oncall.md"


def test_discover_tree_and_manifest(tmp_path: Path) -> None:
    tree = tmp_path / "company"
    (tree / "runbooks").mkdir(parents=True)
    (tree / "runbooks" / "pager.md").write_text("PagerDuty routing.\n", encoding="utf-8")
    (tree / "policies").mkdir(parents=True)
    (tree / "policies" / "pto.md").write_text("PTO policy.\n", encoding="utf-8")
    walked = discover_corpus(tree)
    assert walked.layout == "tree"
    assert set(walked.sources) == {"runbooks", "policies"}

    seed = Path(__file__).resolve().parents[1] / "data"
    if not (seed / "licenses.csv").is_file():
        pytest.skip("seed licenses.csv missing")
    if not (seed / "raw").is_dir():
        pytest.skip("seed data/raw missing")
    manifest = discover_corpus(seed)
    assert manifest.layout == "manifest"
    assert "postgres-docs" in manifest.sources
    assert "pgvector" in manifest.sources
    assert 20 <= len(manifest.files) <= 50


def test_missing_path_fails(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="does not exist"):
        discover_corpus(tmp_path / "nope")


def test_post_corpus_indexes_flat_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db: str) -> None:
    folder = tmp_path / "acme-docs"
    folder.mkdir()
    (folder / "oncall.md").write_text(
        "# Oncall\n\nPage the oncall owner in Slack.\n",
        encoding="utf-8",
    )
    prefix = folder.resolve().as_uri()
    _cleanup(prefix)
    embedder = FakeEmbeddingClient()
    gen = FakeGenerator()
    bq = RecordingBq()
    monkeypatch.setenv("DOCS_SKIP_BQ", "1")
    app.dependency_overrides[get_embedding_client] = lambda: embedder
    app.dependency_overrides[get_generator] = lambda: gen
    app.dependency_overrides[get_bq] = lambda: bq
    client = TestClient(app)
    try:
        listed = client.get("/corpus")
        assert listed.status_code == 200
        assert listed.json()["switch_allowed"] is True

        response = client.post("/corpus", json={"path": str(folder), "sync": True})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["files"] == 1
        assert body["layout"] == "flat"
        assert body["active"] is True
        assert body["documents"] == 1
        assert body["sync"]["inserted"] == 1
        assert body["sync"]["embedded"] >= 1

        asked = client.post(
            "/ask",
            json={"question": "Page the oncall owner in Slack."},
        )
        assert asked.status_code == 200
        payload = asked.json()
        assert payload["refused"] is False
        assert "oncall.md" in payload["citations"][0]["uri"]
    finally:
        app.dependency_overrides.clear()
        reset_active_corpus()
        _cleanup(prefix)


def test_corpus_switch_blocked_on_cloud_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("K_SERVICE", "docpipe-api")
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "a.md").write_text("hello\n", encoding="utf-8")
    client = TestClient(app)
    response = client.post("/corpus", json={"path": str(folder)})
    assert response.status_code == 403


def test_active_prefix_does_not_mix_old_docs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db: str
) -> None:
    seed_prefix = _seed_two_docs(tmp_path, monkeypatch, db)
    embedder = FakeEmbeddingClient()
    index_corpus(
        raw_dir=tmp_path / "raw",
        database_url=db,
        embedding_client=embedder,
    )
    other = tmp_path / "other-docs"
    other.mkdir()
    (other / "secret.md").write_text("# Secret\n\nOnly this folder.\n", encoding="utf-8")
    other_prefix = other.resolve().as_uri()
    _cleanup(other_prefix)
    corpus = discover_corpus(other)
    set_active_corpus(corpus)
    from docpipe.sync import sync_corpus

    try:
        sync_corpus(corpus=corpus, database_url=db, embedding_client=embedder)
        client_stats = None
        with connect(db) as conn:
            from docpipe.store import counts

            scoped = counts(conn, uri_prefix=corpus.uri_prefix)
            client_stats = scoped
        assert client_stats["documents"] == 1
    finally:
        reset_active_corpus()
        _cleanup(seed_prefix)
        _cleanup(other_prefix)
