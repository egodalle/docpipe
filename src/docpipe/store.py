from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Sequence
from uuid import UUID

import psycopg

from docpipe.config import (
    CHUNK_STRATEGY,
    DATABASE_URL,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    SQL_DIR,
)
from docpipe.chunker import ChunkDraft
from docpipe.models import ExtractResult, SearchHit, Status


@contextmanager
def connect(url: str | None = None) -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(url or DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def live_by_uri(conn: psycopg.Connection, uri: str) -> tuple[str, str] | None:
    row = conn.execute(
        "SELECT id::text, content_hash FROM documents WHERE uri = %s AND status = 'live'",
        (uri,),
    ).fetchone()
    if row is None:
        return None
    return str(row[0]), str(row[1])


def list_live_documents(conn: psycopg.Connection) -> list[tuple[str, str, str]]:
    rows = conn.execute(
        "SELECT id::text, uri, content_hash FROM documents WHERE status = 'live'"
    ).fetchall()
    return [(str(row[0]), str(row[1]), str(row[2])) for row in rows]


def tombstone_document(conn: psycopg.Connection, document_id: str) -> None:
    """Mark live→tombstoned and drop chunks/embeddings (FK cascade from chunks)."""
    conn.execute("DELETE FROM chunks WHERE document_id = %s::uuid", (document_id,))
    conn.execute(
        "UPDATE documents SET status = 'tombstoned' WHERE id = %s::uuid AND status = 'live'",
        (document_id,),
    )


def insert_document(conn: psycopg.Connection, result: ExtractResult, status: Status) -> str:
    row = conn.execute(
        """
        INSERT INTO documents (source, uri, content_hash, status, bytes, char_count)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id::text
        """,
        (
            result.source.value,
            result.uri,
            result.content_hash,
            status.value,
            result.bytes,
            result.char_count,
        ),
    ).fetchone()
    assert row is not None
    return str(row[0])


def apply_d3_schema(conn: psycopg.Connection) -> None:
    script = (SQL_DIR / "002_hnsw.sql").read_text(encoding="utf-8")
    for statement in _sql_statements(script):
        conn.execute(statement)


def apply_hybrid_schema(conn: psycopg.Connection) -> None:
    script = (SQL_DIR / "003_hybrid.sql").read_text(encoding="utf-8")
    for statement in _sql_statements(script):
        conn.execute(statement)


def apply_citation_schema(conn: psycopg.Connection) -> None:
    script = (SQL_DIR / "004_citation_ok.sql").read_text(encoding="utf-8")
    for statement in _sql_statements(script):
        conn.execute(statement)


def document_is_indexed(
    conn: psycopg.Connection,
    document_id: str,
    strategy: str = CHUNK_STRATEGY,
    model: str = EMBEDDING_MODEL,
) -> bool:
    row = conn.execute(
        """
        SELECT
            EXISTS (
                SELECT 1 FROM chunks
                WHERE document_id = %s::uuid AND strategy = %s
            ) AS has_chunks,
            EXISTS (
                SELECT 1 FROM chunks c
                LEFT JOIN embeddings e
                    ON e.chunk_id = c.id AND e.model = %s
                WHERE c.document_id = %s::uuid
                  AND c.strategy = %s
                  AND e.chunk_id IS NULL
            ) AS missing_embeddings
        """,
        (document_id, strategy, model, document_id, strategy),
    ).fetchone()
    if row is None:
        return False
    has_chunks, missing_embeddings = bool(row[0]), bool(row[1])
    return has_chunks and not missing_embeddings


def document_has_chunks(
    conn: psycopg.Connection,
    document_id: str,
    strategy: str = CHUNK_STRATEGY,
) -> bool:
    row = conn.execute(
        "SELECT EXISTS (SELECT 1 FROM chunks WHERE document_id = %s::uuid AND strategy = %s)",
        (document_id, strategy),
    ).fetchone()
    return bool(row and row[0])


def insert_chunks(
    conn: psycopg.Connection,
    document_id: str,
    drafts: Sequence[ChunkDraft],
) -> list[str]:
    ids: list[str] = []
    for draft in drafts:
        row = conn.execute(
            """
            INSERT INTO chunks (document_id, ordinal, body, token_count, strategy, metadata)
            VALUES (%s::uuid, %s, %s, %s, %s, %s::jsonb)
            RETURNING id::text
            """,
            (
                document_id,
                draft.ordinal,
                draft.body,
                draft.token_count,
                draft.strategy,
                _json(draft.metadata or {}),
            ),
        ).fetchone()
        assert row is not None
        ids.append(str(row[0]))
    return ids


def chunks_missing_embeddings(
    conn: psycopg.Connection,
    model: str = EMBEDDING_MODEL,
) -> list[tuple[str, str]]:
    rows = conn.execute(
        """
        SELECT c.id::text, c.body
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        LEFT JOIN embeddings e ON e.chunk_id = c.id AND e.model = %s
        WHERE d.status = 'live' AND e.chunk_id IS NULL
        ORDER BY d.ingested_at, c.ordinal
        """,
        (model,),
    ).fetchall()
    return [(str(row[0]), str(row[1])) for row in rows]


def insert_embedding(
    conn: psycopg.Connection,
    chunk_id: str,
    vector: Sequence[float],
    model: str = EMBEDDING_MODEL,
    dim: int = EMBEDDING_DIM,
) -> None:
    conn.execute(
        """
        INSERT INTO embeddings (chunk_id, embedding, model, dim)
        VALUES (%s::uuid, %s::vector, %s, %s)
        ON CONFLICT (chunk_id) DO NOTHING
        """,
        (chunk_id, _vector_literal(vector), model, dim),
    )


def search_chunks(
    conn: psycopg.Connection,
    query_embedding: Sequence[float],
    k: int = 5,
    source: str | None = None,
) -> list[SearchHit]:
    if k <= 0:
        raise ValueError("k must be > 0")
    vec = _vector_literal(query_embedding)
    if source:
        rows = conn.execute(
            """
            SELECT c.id, c.document_id, d.uri, d.source, c.ordinal, c.body,
                   (1 - (e.embedding <=> %s::vector))::double precision AS score
            FROM embeddings e
            JOIN chunks c ON c.id = e.chunk_id
            JOIN documents d ON d.id = c.document_id
            WHERE d.status = 'live' AND d.source = %s
            ORDER BY e.embedding <=> %s::vector
            LIMIT %s
            """,
            (vec, source, vec, k),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT chunk_id, document_id, uri, source, ordinal, body, score "
            "FROM search_chunks(%s::vector, %s)",
            (vec, k),
        ).fetchall()
    hits: list[SearchHit] = []
    for row in rows:
        hits.append(
            SearchHit(
                chunk_id=_as_text(row[0]),
                document_id=_as_text(row[1]),
                uri=str(row[2]),
                source=str(row[3]),
                ordinal=int(row[4]),
                body=str(row[5]),
                score=float(row[6]),
            )
        )
    return hits


def search_chunks_lexical(
    conn: psycopg.Connection,
    question: str,
    k: int = 5,
    source: str | None = None,
) -> list[SearchHit]:
    if k <= 0:
        raise ValueError("k must be > 0")
    cleaned = " ".join((question or "").split())
    if not cleaned:
        return []
    empty = conn.execute("SELECT plainto_tsquery('english', %s)::text", (cleaned,)).fetchone()
    if empty is None or not str(empty[0] or "").strip():
        return []
    if source:
        rows = conn.execute(
            """
            SELECT c.id, c.document_id, d.uri, d.source, c.ordinal, c.body,
                   ts_rank_cd(c.body_tsv, plainto_tsquery('english', %s))::double precision AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.status = 'live'
              AND d.source = %s
              AND c.body_tsv @@ plainto_tsquery('english', %s)
            ORDER BY score DESC, c.ordinal
            LIMIT %s
            """,
            (cleaned, source, cleaned, k),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT c.id, c.document_id, d.uri, d.source, c.ordinal, c.body,
                   ts_rank_cd(c.body_tsv, plainto_tsquery('english', %s))::double precision AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.status = 'live'
              AND c.body_tsv @@ plainto_tsquery('english', %s)
            ORDER BY score DESC, c.ordinal
            LIMIT %s
            """,
            (cleaned, cleaned, k),
        ).fetchall()
    hits: list[SearchHit] = []
    for row in rows:
        hits.append(
            SearchHit(
                chunk_id=_as_text(row[0]),
                document_id=_as_text(row[1]),
                uri=str(row[2]),
                source=str(row[3]),
                ordinal=int(row[4]),
                body=str(row[5]),
                score=float(row[6]),
            )
        )
    return hits


def query_log_metrics(conn: psycopg.Connection) -> dict:
    apply_citation_schema(conn)
    row = conn.execute(
        """
        SELECT
            (SELECT count(*) FROM query_logs) AS asks,
            (SELECT count(*) FROM query_logs WHERE refused) AS refused,
            (
                SELECT percentile_cont(0.50) WITHIN GROUP (ORDER BY latency_ms)
                FROM query_logs
                WHERE latency_ms IS NOT NULL
            ) AS latency_p50,
            (
                SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)
                FROM query_logs
                WHERE latency_ms IS NOT NULL
            ) AS latency_p95
        """
    ).fetchone()
    assert row is not None
    asks = int(row[0] or 0)
    refused = int(row[1] or 0)
    p50 = row[2]
    p95 = row[3]
    integrity = conn.execute(
        """
        SELECT
            count(*) FILTER (WHERE NOT refused AND citation_ok IS NOT NULL),
            count(*) FILTER (WHERE NOT refused AND citation_ok)
        FROM query_logs
        """
    ).fetchone()
    checked = int(integrity[0] or 0) if integrity else 0
    ok = int(integrity[1] or 0) if integrity else 0
    return {
        "asks": asks,
        "refused": refused,
        "refuse_rate": (refused / asks) if asks else 0.0,
        "latency_p50_ms": None if p50 is None else int(round(float(p50))),
        "latency_p95_ms": None if p95 is None else int(round(float(p95))),
        "citation_ok_rate": (ok / checked) if checked else None,
    }


def insert_query_log(
    conn: psycopg.Connection,
    *,
    request_id: str,
    question: str,
    chunk_ids: Sequence[str],
    scores: Sequence[float],
    latency_ms: int,
    model: str,
    refused: bool = False,
    answer: str | None = None,
    citation_ok: bool | None = None,
) -> None:
    apply_citation_schema(conn)
    conn.execute(
        """
        INSERT INTO query_logs (
            request_id, question, chunk_ids, scores, answer, refused,
            latency_ms, model, citation_ok
        )
        VALUES (%s, %s, %s::uuid[], %s, %s, %s, %s, %s, %s)
        """,
        (
            request_id,
            question,
            [UUID(value) for value in chunk_ids],
            list(scores),
            answer,
            refused,
            latency_ms,
            model,
            citation_ok,
        ),
    )


def insert_eval_result(
    conn: psycopg.Connection,
    *,
    run_id: str,
    question_id: str,
    recall_at_5: bool,
    citation_hit: bool,
    latency_ms: int,
) -> None:
    conn.execute(
        """
        INSERT INTO eval_results (run_id, question_id, recall_at_5, citation_hit, latency_ms)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (run_id, question_id, recall_at_5, citation_hit, latency_ms),
    )


def counts(conn: psycopg.Connection) -> dict[str, int]:
    row = conn.execute(
        """
        SELECT
            (SELECT count(*) FROM documents WHERE status = 'live') AS documents,
            (SELECT count(*) FROM chunks) AS chunks,
            (SELECT count(*) FROM embeddings) AS embeddings,
            (SELECT count(*) FROM query_logs) AS query_logs
        """
    ).fetchone()
    assert row is not None
    return {
        "documents": int(row[0]),
        "chunks": int(row[1]),
        "embeddings": int(row[2]),
        "query_logs": int(row[3]),
    }


def _vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(repr(float(value)) for value in vector) + "]"


def _json(value: object) -> str:
    import json

    return json.dumps(value)


def _as_text(value: object) -> str:
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def _sql_statements(script: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    index = 0
    while index < len(script):
        if script.startswith("$$", index):
            end = script.find("$$", index + 2)
            if end < 0:
                raise ValueError("unterminated dollar quote in SQL")
            buf.append(script[index : end + 2])
            index = end + 2
            continue
        char = script[index]
        if char == "-" and index + 1 < len(script) and script[index + 1] == "-":
            newline = script.find("\n", index)
            if newline < 0:
                break
            index = newline + 1
            continue
        if char == ";":
            stmt = "".join(buf).strip()
            if stmt and not all(
                line.strip().startswith("--") or not line.strip()
                for line in stmt.splitlines()
            ):
                statements.append(stmt)
            buf = []
            index += 1
            continue
        buf.append(char)
        index += 1
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements
