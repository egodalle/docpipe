from __future__ import annotations

from docpipe.citations import citation_ok, cited_chunk_ids
from docpipe.models import SearchHit


def _hit(chunk_id: str) -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id,
        document_id="d",
        uri="a.md",
        source="pgvector",
        ordinal=0,
        body="body",
        score=0.8,
    )


def test_cited_chunk_ids_are_unique_and_ordered() -> None:
    cid = "116df1e7-8efb-4b98-b0f4-15b6e3ef4a1d"
    text = f"JSONB is binary [{cid}] and [{cid.upper()}]."
    assert cited_chunk_ids(text) == [cid]


def test_citation_ok_refuse_requires_no_answer() -> None:
    assert citation_ok(refused=True, answer=None, hits=[]) is True
    assert citation_ok(refused=True, answer="no", hits=[]) is False


def test_citation_ok_answer_must_cite_retrieved_ids() -> None:
    good = "116df1e7-8efb-4b98-b0f4-15b6e3ef4a1d"
    other = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    hits = [_hit(good)]
    assert citation_ok(refused=False, answer=f"Stored as binary [{good}].", hits=hits)
    assert not citation_ok(refused=False, answer="Stored as binary.", hits=hits)
    assert not citation_ok(
        refused=False, answer=f"Outside knowledge [{other}].", hits=hits
    )
