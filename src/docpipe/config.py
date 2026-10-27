from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
LICENSES_CSV = DATA_DIR / "licenses.csv"
RAW_DIR = DATA_DIR / "raw"
QUARANTINE_DIR = DATA_DIR / "quarantine"

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://docpipe:docpipe@127.0.0.1:5433/docpipe",
)
GCS_BUCKET = os.environ.get("DOCS_BUCKET", "docpipe-p1-corpus-129492415939")
EMPTY_EXTRACT_FAIL = 0.05
USER_AGENT = "DocPipe/0.1 (https://github.com/egodalle/docpipe)"
