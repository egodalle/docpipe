from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from docpipe.chunker import ChunkDraft, chunk_text
from docpipe.config import (
    CHUNK_STRATEGY,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    RAW_DIR,
)
from docpipe.embed import EmbeddingClient, VertexEmbeddingClient
from docpipe.extract import extract_file
from docpipe.licenses import load_licenses
from docpipe.models import LicenseRow
from docpipe.quality import QualityError, assert_index_quality
from docpipe.store import (
    apply_d3_schema,
    chunks_missing_embeddings,
    connect,
    counts,
    document_has_chunks,
    document_is_indexed,
    insert_chunks,
    insert_embedding,
    live_by_uri,
)


class EmptyChunkError(QualityError):
    pass


@dataclass
class IndexReport:
    chunked: int = 0
    chunk_rows: int = 0
    embedded: int = 0
    skipped: int = 0
    documents: int = 0
    chunks: int = 0
    embeddings: int = 0
    model: str = EMBEDDING_MODEL
    dim: int = EMBEDDING_DIM
    uris: list[str] = field(default_factory=list)


def chunk_corpus(
    raw_dir: Path | None = None,
    database_url: str | None = None,
) -> IndexReport:
    raw = raw_dir or RAW_DIR
    report = IndexReport()
    rows = load_licenses()
    with connect(database_url) as conn:
        apply_d3_schema(conn)
        for row in rows:
            _chunk_one(conn, row, raw, report)
        totals = counts(conn)
        report.documents = totals["documents"]
        report.chunks = totals["chunks"]
        report.embeddings = totals["embeddings"]
        assert_index_quality(conn)
    return report


def embed_corpus(
    database_url: str | None = None,
    embedding_client: EmbeddingClient | None = None,
) -> IndexReport:
    client = embedding_client or VertexEmbeddingClient()
    _assert_client_dim(client)
    report = IndexReport(model=client.model_name, dim=client.dim)
    with connect(database_url) as conn:
        apply_d3_schema(conn)
        pending = chunks_missing_embeddings(conn, model=client.model_name)
        _embed_pending(conn, client, pending, report)
        totals = counts(conn)
        report.documents = totals["documents"]
        report.chunks = totals["chunks"]
        report.embeddings = totals["embeddings"]
        assert_index_quality(conn, dim=client.dim)
    return report


def index_corpus(
    raw_dir: Path | None = None,
    database_url: str | None = None,
    embedding_client: EmbeddingClient | None = None,
) -> IndexReport:
    raw = raw_dir or RAW_DIR
    client = embedding_client or VertexEmbeddingClient()
    _assert_client_dim(client)
    report = IndexReport(model=client.model_name, dim=client.dim)
    rows = load_licenses()
    with connect(database_url) as conn:
        apply_d3_schema(conn)
        for row in rows:
            _chunk_one(conn, row, raw, report)
        pending = chunks_missing_embeddings(conn, model=client.model_name)
        _embed_pending(conn, client, pending, report)
        totals = counts(conn)
        report.documents = totals["documents"]
        report.chunks = totals["chunks"]
        report.embeddings = totals["embeddings"]
        assert_index_quality(conn, dim=client.dim)
    return report


def _chunk_one(
    conn,
    row: LicenseRow,
    raw: Path,
    report: IndexReport,
) -> None:
    path = raw / row.source.value / row.file
    if not path.exists():
        raise FileNotFoundError(f"missing corpus file {path}; run `docpipe fetch`")
    uri = path.resolve().as_uri()
    existing = live_by_uri(conn, uri)
    if existing is None:
        return
    document_id, content_hash = existing
    if document_is_indexed(conn, document_id):
        report.skipped += 1
        return
    if document_has_chunks(conn, document_id):
        return
    result = extract_file(path, row.source, uri)
    if result.empty:
        raise EmptyChunkError(f"empty extract for live document {uri}")
    if result.content_hash != content_hash:
        raise QualityError(
            f"content_hash drift for {uri}: db={content_hash} file={result.content_hash}"
        )
    drafts = chunk_text(
        result.text,
        metadata={"source": row.source.value, "uri": uri},
    )
    _assert_drafts(drafts, uri)
    inserted = insert_chunks(conn, document_id, drafts)
    report.chunked += 1
    report.chunk_rows += len(inserted)
    report.uris.append(uri)


def _embed_pending(
    conn,
    client: EmbeddingClient,
    pending: list[tuple[str, str]],
    report: IndexReport,
) -> None:
    if not pending:
        return
    bodies = [body for _, body in pending]
    vectors = client.embed_documents(bodies)
    if len(vectors) != len(pending):
        raise QualityError(
            f"embed count {len(vectors)} != pending chunks {len(pending)}"
        )
    for (chunk_id, _body), vector in zip(pending, vectors, strict=True):
        if len(vector) != EMBEDDING_DIM:
            raise QualityError(
                f"embedding dim {len(vector)} != config {EMBEDDING_DIM}"
            )
        insert_embedding(
            conn,
            chunk_id,
            vector,
            model=client.model_name,
            dim=client.dim,
        )
        report.embedded += 1


def _assert_drafts(drafts: list[ChunkDraft], uri: str) -> None:
    if not drafts:
        raise EmptyChunkError(f"chunker produced no chunks for {uri}")
    for draft in drafts:
        if not draft.body.strip() or draft.token_count <= 0:
            raise EmptyChunkError(f"empty chunk body for {uri} ordinal={draft.ordinal}")
        if draft.strategy != CHUNK_STRATEGY:
            raise QualityError(
                f"unexpected strategy {draft.strategy} (frozen {CHUNK_STRATEGY})"
            )


def _assert_client_dim(client: EmbeddingClient) -> None:
    if client.dim != EMBEDDING_DIM:
        raise QualityError(f"client dim {client.dim} != config {EMBEDDING_DIM}")
