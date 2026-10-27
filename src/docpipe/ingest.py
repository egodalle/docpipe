from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from docpipe.config import EMPTY_EXTRACT_FAIL, QUARANTINE_DIR, RAW_DIR
from docpipe.extract import extract_file
from docpipe.licenses import load_licenses
from docpipe.models import LicenseRow, Status
from docpipe.store import connect, insert_document, live_by_uri


class EmptyExtractRateError(RuntimeError):
    pass


@dataclass
class IngestReport:
    inserted: int = 0
    skipped: int = 0
    quarantined: int = 0
    uris: list[str] = field(default_factory=list)

    @property
    def processed(self) -> int:
        return self.inserted + self.skipped + self.quarantined

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
) -> IngestReport:
    raw = raw_dir or RAW_DIR
    quarantine = quarantine_dir or QUARANTINE_DIR
    quarantine.mkdir(parents=True, exist_ok=True)
    rows = load_licenses()
    report = IngestReport()
    with connect(database_url) as conn:
        for row in rows:
            _ingest_one(conn, row, raw, quarantine, report)
    if report.processed == 0:
        raise RuntimeError("no files ingested; run `docpipe fetch` first")
    if report.empty_extract_rate >= fail_rate:
        raise EmptyExtractRateError(
            f"empty-extract rate {report.empty_extract_rate:.2%} >= {fail_rate:.0%}"
        )
    return report


def _ingest_one(
    conn,
    row: LicenseRow,
    raw: Path,
    quarantine: Path,
    report: IngestReport,
) -> None:
    path = raw / row.source.value / row.file
    if not path.exists():
        raise FileNotFoundError(f"missing corpus file {path}; run `docpipe fetch`")
    uri = path.resolve().as_uri()
    result = extract_file(path, row.source, uri)
    if result.empty:
        dest = quarantine / row.source.value / row.file
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        insert_document(conn, result, Status.quarantined)
        report.quarantined += 1
        report.uris.append(uri)
        return
    existing = live_by_uri(conn, uri)
    if existing and existing[1] == result.content_hash:
        report.skipped += 1
        return
    insert_document(conn, result, Status.live)
    report.inserted += 1
    report.uris.append(uri)
