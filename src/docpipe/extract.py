from __future__ import annotations

import hashlib
import re
from pathlib import Path

from bs4 import BeautifulSoup

from docpipe.models import ExtractResult, source_value

EXTRACT_SUFFIXES = {".html", ".htm", ".md", ".markdown", ".txt"}

_FRONT_MATTER = re.compile(r"^---\r?\n.*?\r?\n---\r?\n", re.DOTALL)
_MULTI_NL = re.compile(r"\n{3,}")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    raw = path.read_bytes()
    if suffix in {".html", ".htm"}:
        return _from_html(raw)
    if suffix in {".md", ".markdown", ".txt", ""}:
        return _from_text(raw)
    raise ValueError(f"unsupported extract type: {path.suffix}")


def extract_file(path: Path, source: str, uri: str) -> ExtractResult:
    original_bytes = path.stat().st_size
    text = extract_text(path)
    empty = len(text.strip()) == 0
    return ExtractResult(
        uri=uri,
        source=source_value(source),
        text=text,
        content_hash=sha256_text(text),
        bytes=original_bytes,
        char_count=len(text),
        empty=empty,
    )


def _from_text(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    text = _FRONT_MATTER.sub("", text, count=1)
    return _clean(text)


def _from_html(raw: bytes) -> str:
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    node = soup.select_one("#docContent") or soup.select_one("#pgContentWrap") or soup.body or soup
    return _clean(node.get_text("\n"))


def _clean(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    collapsed = "\n".join(line for line in lines if line)
    return _MULTI_NL.sub("\n\n", collapsed).strip()
