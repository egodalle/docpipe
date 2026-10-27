from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path

from docpipe.config import DATA_DIR, RAW_DIR
from docpipe.extract import EXTRACT_SUFFIXES
from docpipe.licenses import load_licenses
from docpipe.models import LicenseRow, normalize_source, source_value

MAX_CORPUS_FILES = 200
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "quarantine",
    "dist",
    "build",
}
_SOURCE_START = re.compile(r"^[a-z]")

_lock = threading.Lock()
_active: Corpus | None = None


class CorpusError(ValueError):
    pass


@dataclass(frozen=True)
class Corpus:
    root: Path
    layout: str
    files: tuple[tuple[LicenseRow, Path], ...]

    @property
    def sources(self) -> list[str]:
        return sorted({source_value(row.source) for row, _path in self.files})

    @property
    def files_root(self) -> Path:
        if self.layout == "manifest":
            raw = self.root / "raw"
            if raw.is_dir():
                return raw.resolve()
        return self.root.resolve()

    @property
    def uri_prefix(self) -> str:
        return self.files_root.as_uri().rstrip("/") + "/"

    def path_for(self, row: LicenseRow) -> Path:
        source = source_value(row.source)
        for item, path in self.files:
            if source_value(item.source) == source and item.file == row.file:
                return path
        raise CorpusError(f"corpus has no {source}/{row.file}")


def default_corpus_root() -> Path:
    env = os.environ.get("DOCS_CORPUS")
    if env:
        return Path(env).expanduser()
    return DATA_DIR


def corpus_switch_allowed() -> bool:
    if os.environ.get("K_SERVICE"):
        return False
    flag = os.environ.get("DOCS_ALLOW_CORPUS_SWITCH", "1").strip().lower()
    return flag not in {"0", "false", "no"}


def peek_active_corpus() -> Corpus | None:
    with _lock:
        return _active


def get_active_corpus() -> Corpus:
    current = peek_active_corpus()
    if current is not None:
        return current
    return discover_corpus(default_corpus_root())


def set_active_corpus(corpus: Corpus | None) -> None:
    global _active
    with _lock:
        _active = corpus
    from docpipe.licenses import licenses_by_file

    licenses_by_file.cache_clear()


def reset_active_corpus() -> None:
    set_active_corpus(None)


def active_uri_prefix() -> str | None:
    current = peek_active_corpus()
    if current is None:
        return None
    return current.uri_prefix


def discover_corpus(path: str | Path) -> Corpus:
    root = Path(path).expanduser().resolve()
    if not root.exists():
        raise CorpusError(f"path does not exist: {root}")
    if not root.is_dir():
        raise CorpusError(f"not a directory: {root}")
    licenses_csv = root / "licenses.csv"
    if licenses_csv.is_file():
        return _from_manifest(root, licenses_csv)
    return _from_walk(root)


def corpus_status(corpus: Corpus | None = None) -> dict:
    current = corpus or peek_active_corpus()
    discovered = current
    error: str | None = None
    if discovered is None:
        try:
            discovered = discover_corpus(default_corpus_root())
        except CorpusError as exc:
            error = str(exc)
    payload = {
        "path": str(discovered.root) if discovered else str(default_corpus_root().expanduser()),
        "layout": None if discovered is None else discovered.layout,
        "sources": [] if discovered is None else discovered.sources,
        "files": 0 if discovered is None else len(discovered.files),
        "switch_allowed": corpus_switch_allowed(),
        "default_path": str(default_corpus_root().expanduser().resolve())
        if default_corpus_root().exists()
        else str(default_corpus_root()),
        "active": peek_active_corpus() is not None,
        "raw_dir": str(RAW_DIR),
    }
    if error:
        payload["error"] = error
    return payload


def slugify_source(name: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    if not text or not _SOURCE_START.match(text):
        text = f"corpus-{text}" if text else "corpus"
    text = text[:63].rstrip("-") or "corpus"
    if not _SOURCE_START.match(text):
        text = f"corpus-{text}"[:63]
    return normalize_source(text)


def _from_manifest(root: Path, licenses_csv: Path) -> Corpus:
    rows = load_licenses(licenses_csv)
    files: list[tuple[LicenseRow, Path]] = []
    missing: list[str] = []
    for row in rows:
        path = _manifest_path(root, row)
        if path is None:
            missing.append(f"{source_value(row.source)}/{row.file}")
            continue
        files.append((row, path.resolve()))
    if missing:
        raise CorpusError("missing corpus files: " + ", ".join(missing[:8]))
    if not files:
        raise CorpusError(f"no licensed files under {root}")
    if len(files) > MAX_CORPUS_FILES:
        raise CorpusError(f"corpus has {len(files)} files; max is {MAX_CORPUS_FILES}")
    return Corpus(root=root, layout="manifest", files=tuple(files))


def _manifest_path(root: Path, row: LicenseRow) -> Path | None:
    source = source_value(row.source)
    for candidate in (
        root / "raw" / source / row.file,
        root / source / row.file,
        root / row.file,
    ):
        if candidate.is_file():
            return candidate
    return None


def _from_walk(root: Path) -> Corpus:
    found: list[tuple[LicenseRow, Path]] = []
    seen: set[tuple[str, str]] = set()
    for path in _iter_extractable(root):
        rel = path.relative_to(root)
        if len(rel.parts) == 1:
            source = slugify_source(root.name)
        else:
            source = slugify_source("-".join(rel.parts[:-1]))
        key = (source, path.name)
        if key in seen:
            source = slugify_source(f"{source}-{path.stem}")
            key = (source, path.name)
        if key in seen:
            raise CorpusError(f"duplicate basename {path.name} under {source}")
        seen.add(key)
        row = LicenseRow(
            file=path.name,
            source=source,
            license="Unspecified",
            license_url="",
            origin_url=path.resolve().as_uri(),
        )
        found.append((row, path.resolve()))
        if len(found) > MAX_CORPUS_FILES:
            raise CorpusError(f"corpus has more than {MAX_CORPUS_FILES} files")
    if not found:
        raise CorpusError(
            f"no html/markdown/text files in {root}. "
            "Add files or point at a folder that has licenses.csv + raw/"
        )
    layout = "flat" if all(path.parent == root for _row, path in found) else "tree"
    return Corpus(root=root, layout=layout, files=tuple(found))


def _iter_extractable(root: Path):
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [
            name
            for name in sorted(dirnames)
            if name not in SKIP_DIRS and not name.startswith(".")
        ]
        for name in sorted(filenames):
            if name.startswith("."):
                continue
            path = Path(dirpath) / name
            if path.suffix.lower() in EXTRACT_SUFFIXES and path.is_file():
                yield path
