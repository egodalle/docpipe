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
    names = [row.file for row in rows]
    if len(names) != len(set(names)):
        raise ValueError("duplicate file names in licenses.csv")
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
    return licenses_by_file().get(name)
