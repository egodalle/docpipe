from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg

from docpipe.config import DATABASE_URL
from docpipe.models import ExtractResult, Status


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
