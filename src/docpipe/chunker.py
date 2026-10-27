from __future__ import annotations

import re
from dataclasses import dataclass, field

from docpipe.config import CHUNK_OVERLAP, CHUNK_SIZE, CHUNK_STRATEGY

_TOKEN = re.compile(r"\S+")
_SEPARATORS = ("\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", "")


def count_tokens(text: str) -> int:
    return len(_TOKEN.findall(text))


@dataclass(frozen=True)
class ChunkDraft:
    ordinal: int
    body: str
    token_count: int
    strategy: str = CHUNK_STRATEGY
    metadata: dict[str, str] = field(default_factory=dict)


def chunk_text(
    text: str,
    *,
    size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    strategy: str = CHUNK_STRATEGY,
    metadata: dict[str, str] | None = None,
) -> list[ChunkDraft]:
    """Recursive splitter targeting `size` tokens with `overlap` shared tokens."""
    if size <= 0:
        raise ValueError("chunk size must be > 0")
    if overlap < 0 or overlap >= size:
        raise ValueError("chunk overlap must be >= 0 and < size")
    bodies = _apply_overlap(_split_recursive(text.strip(), size, _SEPARATORS), overlap)
    meta = metadata or {}
    drafts: list[ChunkDraft] = []
    for ordinal, body in enumerate(bodies):
        cleaned = body.strip()
        if not cleaned:
            continue
        n = count_tokens(cleaned)
        if n <= 0:
            continue
        drafts.append(
            ChunkDraft(
                ordinal=ordinal,
                body=cleaned,
                token_count=n,
                strategy=strategy,
                metadata=dict(meta),
            )
        )
    return drafts


def _split_recursive(text: str, size: int, separators: tuple[str, ...]) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if count_tokens(text) <= size:
        return [text]

    separator = ""
    rest: tuple[str, ...] = ()
    for index, candidate in enumerate(separators):
        if candidate == "":
            separator = ""
            rest = ()
            break
        if candidate in text:
            separator = candidate
            rest = separators[index + 1 :]
            break

    if separator == "":
        return _hard_wrap(text, size)

    pieces = [piece.strip() for piece in text.split(separator) if piece.strip()]
    chunks: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            chunks.append(separator.join(buf).strip())
            buf.clear()

    for piece in pieces:
        if count_tokens(piece) > size:
            flush()
            if rest:
                chunks.extend(_split_recursive(piece, size, rest))
            else:
                chunks.extend(_hard_wrap(piece, size))
            continue
        trial = buf + [piece]
        if buf and count_tokens(separator.join(trial)) > size:
            flush()
            buf.append(piece)
        else:
            buf.append(piece)
    flush()
    return [chunk for chunk in chunks if chunk.strip()]


def _hard_wrap(text: str, size: int) -> list[str]:
    tokens = _TOKEN.findall(text)
    return [
        " ".join(tokens[index : index + size])
        for index in range(0, len(tokens), size)
        if tokens[index : index + size]
    ]


def _apply_overlap(chunks: list[str], overlap: int) -> list[str]:
    if overlap <= 0 or len(chunks) <= 1:
        return chunks
    out: list[str] = []
    previous = ""
    for index, chunk in enumerate(chunks):
        if index == 0:
            out.append(chunk)
            previous = chunk
            continue
        tail = _token_tail(previous, overlap)
        if tail and not chunk.startswith(tail):
            body = f"{tail} {chunk}".strip()
        else:
            body = chunk
        out.append(body)
        previous = body
    return out


def _token_tail(text: str, n: int) -> str:
    matches = list(_TOKEN.finditer(text))
    if not matches or n <= 0:
        return ""
    start = matches[max(0, len(matches) - n)].start()
    return text[start:].strip()
