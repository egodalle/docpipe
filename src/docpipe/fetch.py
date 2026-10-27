from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path

from docpipe.config import RAW_DIR, USER_AGENT
from docpipe.licenses import load_licenses
from docpipe.models import LicenseRow


def fetch_corpus(raw_dir: Path | None = None, timeout: int = 30) -> list[Path]:
    dest_root = raw_dir or RAW_DIR
    written: list[Path] = []
    dest_root.mkdir(parents=True, exist_ok=True)
    for row in load_licenses():
        written.append(_download(row, dest_root, timeout=timeout))
    return written


def _download(row: LicenseRow, dest_root: Path, timeout: int) -> Path:
    dest = dest_root / row.source.value / row.file
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    request = urllib.request.Request(row.origin_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            if response.status != 200:
                raise RuntimeError(f"{row.origin_url} -> HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"fetch failed {row.origin_url}: HTTP {exc.code}") from exc
    if not body:
        raise RuntimeError(f"empty download: {row.origin_url}")
    dest.write_bytes(body)
    return dest
