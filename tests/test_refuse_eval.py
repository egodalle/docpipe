from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from docpipe.evalrun import load_refuse, run_refuse_eval
from docpipe.index import index_corpus
from docpipe.store import connect
from tests.test_index import FakeEmbeddingClient, _cleanup, _seed_two_docs

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://docpipe:docpipe@127.0.0.1:5433/docpipe",
)


def test_refuse_set_size() -> None:
    items = load_refuse()
    assert len(items) >= 5
    assert all(item.expect_refused for item in items)


@pytest.fixture
def db() -> str:
    try:
        with connect(DATABASE_URL) as conn:
            conn.execute("SELECT 1")
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"postgres unavailable: {exc}")
    return DATABASE_URL


def test_refuse_eval_off_topic_on_seeded_docs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db: str
) -> None:
    monkeypatch.setenv("DOCS_SKIP_BQ", "1")
    prefix = _seed_two_docs(tmp_path, monkeypatch, db)
    embedder = FakeEmbeddingClient()
    refuse = tmp_path / "refuse.json"
    refuse.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "weather",
                        "question": "What is the weather in Paris tomorrow?",
                        "expect_refused": True,
                    },
                    {
                        "id": "bread",
                        "question": "How do I bake sourdough bread at home?",
                        "expect_refused": True,
                    },
                    {
                        "id": "poem",
                        "question": "Write a poem about my cat named Miso.",
                        "expect_refused": True,
                    },
                    {
                        "id": "tire",
                        "question": "How do I change a flat tire on my car?",
                        "expect_refused": True,
                    },
                    {
                        "id": "stocks",
                        "question": "What will the stock market do tomorrow?",
                        "expect_refused": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    try:
        index_corpus(
            raw_dir=tmp_path / "raw",
            database_url=db,
            embedding_client=embedder,
        )
        report = run_refuse_eval(
            k=5,
            database_url=db,
            embedding_client=embedder,
            refuse_path=refuse,
            persist=True,
            run_id="refuse-test-local",
            hybrid=False,
        )
        assert report.n == 5
        assert report.refuse_accuracy == 1.0
        assert report.meets_bar
    finally:
        with connect(db) as conn:
            conn.execute(
                "DELETE FROM eval_results WHERE run_id = %s", ("refuse-test-local",)
            )
        _cleanup(prefix)
