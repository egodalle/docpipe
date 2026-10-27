from __future__ import annotations

from collections.abc import Sequence

from docpipe.config import EVAL_POOL_K, HYBRID_RETRIEVAL, RRF_K, UNIQUE_DOCUMENTS
from docpipe.models import SearchHit
from docpipe.store import apply_hybrid_schema, search_chunks, search_chunks_lexical


def uri_basename(uri: str) -> str:
    return uri.rstrip("/").rsplit("/", 1)[-1]


def pick_topk(
    hits: list[SearchHit],
    k: int = 5,
    unique_documents: bool = False,
) -> list[SearchHit]:
    if not unique_documents:
        return hits[:k]
    seen: set[str] = set()
    picked: list[SearchHit] = []
    for hit in hits:
        name = uri_basename(hit.uri)
        if name in seen:
            continue
        seen.add(name)
        picked.append(hit)
        if len(picked) >= k:
            break
    return picked


def rrf_fuse(
    vector_hits: Sequence[SearchHit],
    lexical_hits: Sequence[SearchHit],
    rrf_k: int = RRF_K,
) -> list[SearchHit]:
    """Reciprocal rank fusion. Returned `score` stays cosine so refuse_min_score is unchanged."""
    by_id: dict[str, SearchHit] = {hit.chunk_id: hit for hit in vector_hits}
    vector_ids = set(by_id)
    for hit in lexical_hits:
        by_id.setdefault(hit.chunk_id, hit)
    vec_rank = {hit.chunk_id: index for index, hit in enumerate(vector_hits, start=1)}
    lex_rank = {hit.chunk_id: index for index, hit in enumerate(lexical_hits, start=1)}
    fused: list[tuple[float, SearchHit]] = []
    for chunk_id, hit in by_id.items():
        rank_score = 0.0
        if chunk_id in vec_rank:
            rank_score += 1.0 / (rrf_k + vec_rank[chunk_id])
        if chunk_id in lex_rank:
            rank_score += 1.0 / (rrf_k + lex_rank[chunk_id])
        if chunk_id in vector_ids:
            scored = hit
        else:
            scored = hit.model_copy(update={"score": 0.0})
        fused.append((rank_score, scored))
    fused.sort(key=lambda item: item[0], reverse=True)
    return [hit for _score, hit in fused]


def retrieve_hits(
    conn,
    *,
    question: str,
    query_embedding: Sequence[float],
    k: int,
    source: str | None = None,
    hybrid: bool | None = None,
    unique_documents: bool | None = None,
    pool_k: int | None = None,
    rrf_k: int | None = None,
) -> list[SearchHit]:
    apply_hybrid_schema(conn)
    use_hybrid = HYBRID_RETRIEVAL if hybrid is None else hybrid
    use_unique = UNIQUE_DOCUMENTS if unique_documents is None else unique_documents
    fetch_k = pool_k if pool_k is not None else (EVAL_POOL_K if use_unique else k)
    fetch_k = max(int(fetch_k), int(k))
    vector_hits = search_chunks(conn, query_embedding, k=fetch_k, source=source)
    if not use_hybrid:
        return pick_topk(vector_hits, k=k, unique_documents=use_unique)
    lexical_hits = search_chunks_lexical(conn, question, k=fetch_k, source=source)
    fused = rrf_fuse(vector_hits, lexical_hits, rrf_k=rrf_k or RRF_K)
    return pick_topk(fused, k=k, unique_documents=use_unique)
