from __future__ import annotations

import csv
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
