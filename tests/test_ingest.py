from __future__ import annotations

import csv
import os
from pathlib import Path

import pytest

from docpipe.ingest import EmptyExtractRateError, ingest_corpus
from docpipe.licenses import load_licenses
from docpipe.models import Source
from docpipe.store import connect

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


def test_ingest_nonempty_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db: str) -> None:
    raw = tmp_path / "raw" / Source.pgvector.value
    raw.mkdir(parents=True)
    (raw / "a.md").write_text("# A\n\nHNSW index.\n", encoding="utf-8")
    (raw / "b.md").write_text("# B\n\nIVFFlat index.\n", encoding="utf-8")
    licenses = tmp_path / "licenses.csv"
    _write_licenses(licenses, [("a.md", "pgvector"), ("b.md", "pgvector")])
    monkeypatch.setattr("docpipe.ingest.load_licenses", lambda: load_licenses(licenses))
    prefix = tmp_path.resolve().as_uri()
    _cleanup(prefix)
    try:
        report = ingest_corpus(
            raw_dir=tmp_path / "raw",
            quarantine_dir=tmp_path / "quarantine",
            database_url=db,
        )
        assert report.inserted == 2
        assert report.quarantined == 0
        assert report.empty_extract_rate == 0.0
        with connect(db) as conn:
            count = conn.execute(
                "SELECT count(*) FROM documents WHERE uri LIKE %s AND status = 'live'",
                (prefix + "%",),
            ).fetchone()
            assert count is not None
            assert count[0] == 2
        again = ingest_corpus(
            raw_dir=tmp_path / "raw",
            quarantine_dir=tmp_path / "quarantine",
            database_url=db,
        )
        assert again.skipped == 2
        assert again.inserted == 0
    finally:
        _cleanup(prefix)


def test_quarantine_and_fail_rate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db: str) -> None:
    raw = tmp_path / "raw" / Source.postgres_docs.value
    raw.mkdir(parents=True)
    (raw / "ok.md").write_text("Postgres JSONB.\n", encoding="utf-8")
    (raw / "empty.md").write_text("\n\n", encoding="utf-8")
    licenses = tmp_path / "licenses.csv"
    _write_licenses(
        licenses,
        [("ok.md", "postgres-docs"), ("empty.md", "postgres-docs")],
    )
    monkeypatch.setattr("docpipe.ingest.load_licenses", lambda: load_licenses(licenses))
    prefix = tmp_path.resolve().as_uri()
    _cleanup(prefix)
    try:
        with pytest.raises(EmptyExtractRateError):
            ingest_corpus(
                raw_dir=tmp_path / "raw",
                quarantine_dir=tmp_path / "quarantine",
                database_url=db,
                fail_rate=0.05,
            )
        assert (tmp_path / "quarantine" / "postgres-docs" / "empty.md").exists()
        with connect(db) as conn:
            statuses = {
                row[0]
                for row in conn.execute(
                    "SELECT status FROM documents WHERE uri LIKE %s",
                    (prefix + "%",),
                ).fetchall()
            }
            assert "live" in statuses
            assert "quarantined" in statuses
    finally:
        _cleanup(prefix)
