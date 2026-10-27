from __future__ import annotations

from docpipe.chunker import chunk_text, count_tokens
from docpipe.config import CHUNK_OVERLAP, CHUNK_SIZE, CHUNK_STRATEGY


def test_chunker_skips_empty_and_whitespace() -> None:
    assert chunk_text("") == []
    assert chunk_text(" \n\n ") == []


def test_short_text_is_one_chunk() -> None:
    text = "HNSW indexes support cosine distance."
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0].body == text
    assert chunks[0].strategy == CHUNK_STRATEGY
    assert chunks[0].ordinal == 0
    assert chunks[0].token_count == count_tokens(text)
    assert chunks[0].token_count > 0


def test_recursive_split_respects_paragraphs_and_size() -> None:
    paragraphs = [f"Paragraph {i} " + ("jsonb " * 40) for i in range(12)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, size=80, overlap=16)
    assert len(chunks) > 1
    assert all(chunk.body.strip() for chunk in chunks)
    assert all(chunk.token_count > 0 for chunk in chunks)
    assert all(chunk.strategy == CHUNK_STRATEGY for chunk in chunks)
    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.token_count <= 80 + 16 for chunk in chunks)


def test_overlap_shares_tokens_across_neighbors() -> None:
    tokens = [f"tok{i:03d}" for i in range(50)]
    text = " ".join(tokens)
    chunks = chunk_text(text, size=20, overlap=5)
    assert len(chunks) >= 2
    first = chunks[0].body.split()
    second = chunks[1].body.split()
    assert first[-5:] == second[:5]


def test_default_strategy_name_and_bounds() -> None:
    text = "Postgres " * 900
    chunks = chunk_text(text)
    assert chunks
    assert all(c.strategy == "recursive_400_80" for c in chunks)
    assert CHUNK_SIZE == 400
    assert CHUNK_OVERLAP == 80
    assert all(c.token_count <= CHUNK_SIZE + CHUNK_OVERLAP for c in chunks)
