from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from docpipe.config import EMPTY_EXTRACT_FAIL, QUARANTINE_DIR, RAW_DIR
from docpipe.corpus import Corpus, peek_active_corpus
from docpipe.extract import extract_file
from docpipe.licenses import load_licenses
from docpipe.models import LicenseRow, Status, source_value
from docpipe.store import (
    connect,
    insert_document,
    list_live_documents,
    live_by_uri,
    tombstone_document,
)


class EmptyExtractRateError(RuntimeError):
    pass


@dataclass
class IngestReport:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    quarantined: int = 0
    tombstoned: int = 0
    uris: list[str] = field(default_factory=list)

    @property
    def processed(self) -> int:
        return self.inserted + self.updated + self.skipped + self.quarantined

    @property
    def empty_extract_rate(self) -> float:
        if self.processed == 0:
            return 0.0
        return self.quarantined / self.processed


def ingest_corpus(
    raw_dir: Path | None = None,
    quarantine_dir: Path | None = None,
    database_url: str | None = None,
    fail_rate: float = EMPTY_EXTRACT_FAIL,
    corpus: Corpus | None = None,
) -> IngestReport:
    quarantine = quarantine_dir or QUARANTINE_DIR
    quarantine.mkdir(parents=True, exist_ok=True)
    pairs, tombstone_root = _ingest_pairs(raw_dir, corpus)
    report = IngestReport()
    seen: set[str] = set()
    with connect(database_url) as conn:
        for row, path in pairs:
            uri = _ingest_one(conn, row, path, quarantine, report)
            if uri:
                seen.add(uri)
        _tombstone_missing(conn, seen, tombstone_root, report)
    if report.processed == 0:
        raise RuntimeError("no files ingested; run `docpipe fetch` first")
    if report.empty_extract_rate >= fail_rate:
        raise EmptyExtractRateError(
            f"empty-extract rate {report.empty_extract_rate:.2%} >= {fail_rate:.0%}"
        )
    return report


def _ingest_pairs(
    raw_dir: Path | None,
    corpus: Corpus | None,
) -> tuple[list[tuple[LicenseRow, Path]], Path]:
    if corpus is not None:
        return list(corpus.files), corpus.files_root
    active = peek_active_corpus()
    if raw_dir is None and active is not None:
        return list(active.files), active.files_root
    raw = raw_dir or RAW_DIR
    rows = load_licenses()
    return [
        (row, raw / source_value(row.source) / row.file) for row in rows
    ], raw


def _ingest_one(
    conn,
    row: LicenseRow,
    path: Path,
    quarantine: Path,
    report: IngestReport,
) -> str | None:
    uri = path.resolve().as_uri() if path.exists() else path.as_uri()
    source = source_value(row.source)
    if not path.exists():
        existing = live_by_uri(conn, uri)
        if existing:
            tombstone_document(conn, existing[0])
            report.tombstoned += 1
            return uri
        raise FileNotFoundError(f"missing corpus file {path}; run `docpipe fetch`")
    result = extract_file(path, source, uri)
    if result.empty:
        dest = quarantine / source / row.file
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        existing = live_by_uri(conn, uri)
        if existing:
            tombstone_document(conn, existing[0])
            report.tombstoned += 1
        insert_document(conn, result, Status.quarantined)
        report.quarantined += 1
        report.uris.append(uri)
        return uri
    existing = live_by_uri(conn, uri)
    if existing and existing[1] == result.content_hash:
        report.skipped += 1
        return uri
    if existing:
        tombstone_document(conn, existing[0])
        insert_document(conn, result, Status.live)
        report.updated += 1
        report.uris.append(uri)
        return uri
    insert_document(conn, result, Status.live)
    report.inserted += 1
    report.uris.append(uri)
    return uri


def _tombstone_missing(
    conn, seen: set[str], raw: Path, report: IngestReport
) -> None:
    prefix = raw.resolve().as_uri().rstrip("/") + "/"
    for document_id, uri, _hash in list_live_documents(conn):
        if not uri.startswith(prefix):
            continue
        if uri in seen:
            continue
        tombstone_document(conn, document_id)
        report.tombstoned += 1
