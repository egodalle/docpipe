-- P1 schema v1. System of record for documents, chunks, embeddings,
-- query logs, and eval results. Practice tables in schema day2 are unrelated.
-- Requires: CREATE EXTENSION vector;

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS documents (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source        text        NOT NULL,
    uri           text        NOT NULL,
    content_hash  text        NOT NULL,
    ingested_at   timestamptz NOT NULL DEFAULT now(),
    status        text        NOT NULL DEFAULT 'live'
                  CHECK (status IN ('live', 'tombstoned', 'quarantined')),
    bytes         integer,
    char_count    integer
);

CREATE UNIQUE INDEX IF NOT EXISTS documents_live_uri_uidx
    ON documents (uri) WHERE status = 'live';

CREATE UNIQUE INDEX IF NOT EXISTS documents_live_hash_uidx
    ON documents (content_hash) WHERE status = 'live';

CREATE INDEX IF NOT EXISTS documents_source_ingested_idx
    ON documents (source, ingested_at DESC);

CREATE TABLE IF NOT EXISTS chunks (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id   uuid        NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    ordinal       integer     NOT NULL,
    body          text        NOT NULL CHECK (length(trim(body)) > 0),
    token_count   integer     NOT NULL CHECK (token_count > 0),
    strategy      text        NOT NULL DEFAULT 'recursive_400_80',
    metadata      jsonb       NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks (document_id);

-- dim is frozen in application config (D3). 768 is a safe default for
-- text-embedding-004 / gemini embedding text models; ALTER if the pinned
-- model differs, and record it in ADR 0003.
CREATE TABLE IF NOT EXISTS embeddings (
    chunk_id      uuid PRIMARY KEY REFERENCES chunks (id) ON DELETE CASCADE,
    embedding     vector(768) NOT NULL,
    model         text        NOT NULL,
    dim           integer     NOT NULL CHECK (dim = 768),
    embedded_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS query_logs (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id    text        NOT NULL,
    question      text        NOT NULL,
    chunk_ids     uuid[]      NOT NULL DEFAULT '{}',
    scores        double precision[] NOT NULL DEFAULT '{}',
    answer        text,
    refused       boolean     NOT NULL DEFAULT false,
    latency_ms    integer,
    model         text,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS query_logs_created_at_idx ON query_logs (created_at DESC);

CREATE TABLE IF NOT EXISTS eval_results (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id        text        NOT NULL,
    question_id   text        NOT NULL,
    recall_at_5   boolean,
    citation_hit  boolean,
    latency_ms    integer,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS eval_results_run_id_idx ON eval_results (run_id);
