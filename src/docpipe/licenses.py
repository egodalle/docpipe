from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from docpipe.config import LICENSES_CSV
from docpipe.models import LicenseRow


def load_licenses(path: Path | None = None) -> list[LicenseRow]:
    csv_path = path or LICENSES_CSV
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = [LicenseRow.model_validate(row) for row in csv.DictReader(handle)]
    if not rows:
        raise ValueError(f"empty licenses file: {csv_path}")
    keys = [(row.source, row.file) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate source/file in licenses.csv")
    return rows


@lru_cache(maxsize=1)
def licenses_by_file(path: str | None = None) -> dict[str, LicenseRow]:
    try:
        rows = load_licenses(Path(path) if path else None)
    except Exception:
        return {}
    return {row.file: row for row in rows}


def license_for_uri(uri: str) -> LicenseRow | None:
    name = uri.rstrip("/").rsplit("/", 1)[-1]
    from docpipe.corpus import peek_active_corpus

    corpus = peek_active_corpus()
    if corpus is not None:
        for row, path in corpus.files:
            if path.resolve().as_uri() == uri:
                return row
        for row, path in corpus.files:
            if row.file == name or path.name == name:
                return row
        return None
    return licenses_by_file().get(name)
