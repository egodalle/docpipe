from __future__ import annotations

import psycopg

from docpipe.config import EMBEDDING_DIM, SQL_DIM


class QualityError(RuntimeError):
    pass


def assert_index_quality(conn: psycopg.Connection, dim: int = EMBEDDING_DIM) -> None:
    """Fail the job on empty bodies, dim mismatch, duplicate live hashes, or orphans."""
    if dim != SQL_DIM:
        raise QualityError(
            f"config dim {dim} != sql vector({SQL_DIM}); ALTER + ADR 0003 required"
        )
    empty = conn.execute(
        "SELECT count(*) FROM chunks WHERE length(trim(body)) = 0"
    ).fetchone()
    if empty is not None and empty[0] > 0:
        raise QualityError(f"empty chunk body count={empty[0]}")

    bad_dim = conn.execute(
        """
        SELECT count(*) FROM embeddings
        WHERE dim <> %s OR vector_dims(embedding) <> %s
        """,
        (dim, dim),
    ).fetchone()
    if bad_dim is not None and bad_dim[0] > 0:
        raise QualityError(f"embedding dim mismatch count={bad_dim[0]} expected={dim}")

    dupes = conn.execute(
        """
        SELECT count(*) FROM (
            SELECT content_hash
            FROM documents
            WHERE status = 'live'
            GROUP BY content_hash
            HAVING count(*) > 1
        ) d
        """
    ).fetchone()
    if dupes is not None and dupes[0] > 0:
        raise QualityError(f"duplicate live content_hash groups={dupes[0]}")

    orphan_embeddings = conn.execute(
        """
        SELECT count(*) FROM embeddings e
        LEFT JOIN chunks c ON c.id = e.chunk_id
        WHERE c.id IS NULL
        """
    ).fetchone()
    if orphan_embeddings is not None and orphan_embeddings[0] > 0:
        raise QualityError(f"orphan embeddings count={orphan_embeddings[0]}")

    stale_chunks = conn.execute(
        """
        SELECT count(*) FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE d.status <> 'live'
        """
    ).fetchone()
    if stale_chunks is not None and stale_chunks[0] > 0:
        raise QualityError(f"chunks on non-live documents count={stale_chunks[0]}")
