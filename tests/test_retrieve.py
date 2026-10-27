from __future__ import annotations

from docpipe.models import SearchHit
from docpipe.retrieve import pick_topk, rrf_fuse, uri_basename


def _hit(chunk_id: str, uri: str, score: float) -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id,
        document_id="d",
        uri=uri,
        source="pgvector",
        ordinal=0,
        body="body",
        score=score,
    )


def test_rrf_prefers_items_in_both_lists() -> None:
    vector = [
        _hit("v1", "a.md", 0.9),
        _hit("both", "b.md", 0.8),
        _hit("v3", "c.md", 0.7),
    ]
    lexical = [
        _hit("both", "b.md", 0.4),
        _hit("lex", "d.md", 0.3),
    ]
    fused = rrf_fuse(vector, lexical, rrf_k=60)
    assert fused[0].chunk_id == "both"
    assert fused[0].score == 0.8
    ids = [hit.chunk_id for hit in fused]
    assert ids == ["both", "v1", "lex", "v3"]
    assert next(hit.score for hit in fused if hit.chunk_id == "lex") == 0.0
    assert next(hit.score for hit in fused if hit.chunk_id == "both") == 0.8


def test_pick_topk_unique_and_basename() -> None:
    assert uri_basename("file:///tmp/raw/a.md") == "a.md"
    hits = [
        _hit("1", "a.md", 0.9),
        _hit("2", "a.md", 0.8),
        _hit("3", "b.md", 0.7),
    ]
    unique = pick_topk(hits, k=2, unique_documents=True)
    assert [hit.uri for hit in unique] == ["a.md", "b.md"]
