from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docpipe.config import RAW_DIR
from docpipe.corpus import Corpus
from docpipe.embed import EmbeddingClient
from docpipe.index import IndexReport, index_corpus
from docpipe.ingest import IngestReport, ingest_corpus


@dataclass
class SyncReport:
    ingest: IngestReport
    index: IndexReport


def sync_corpus(
    raw_dir: Path | None = None,
    quarantine_dir: Path | None = None,
    database_url: str | None = None,
    embedding_client: EmbeddingClient | None = None,
    corpus: Corpus | None = None,
) -> SyncReport:
    """Hash-sync documents then chunk/embed only what changed."""
    ingest = ingest_corpus(
        raw_dir=None if corpus is not None else (raw_dir or RAW_DIR),
        quarantine_dir=quarantine_dir,
        database_url=database_url,
        corpus=corpus,
    )
    index = index_corpus(
        raw_dir=None if corpus is not None else (raw_dir or RAW_DIR),
        database_url=database_url,
        embedding_client=embedding_client,
        corpus=corpus,
    )
    return SyncReport(ingest=ingest, index=index)
