-- Day 2 practice tables. Isolated in schema day2 so Day 4 can create
-- the real public.documents / public.chunks without a name clash.
-- Re-runnable: drops and recreates the schema.

CREATE SCHEMA IF NOT EXISTS day2;

DROP TABLE IF EXISTS day2.chunks;
DROP TABLE IF EXISTS day2.documents;

CREATE TABLE day2.documents (
    id            INTEGER PRIMARY KEY,
    source        TEXT        NOT NULL,
    uri           TEXT        NOT NULL,
    content_hash  TEXT        NOT NULL,
    ingested_at   TIMESTAMPTZ NOT NULL
);

CREATE TABLE day2.chunks (
    id            INTEGER PRIMARY KEY,
    document_id   INTEGER     NOT NULL REFERENCES day2.documents (id),
    body          TEXT        NOT NULL,
    token_count   INTEGER     NOT NULL CHECK (token_count > 0)
);

INSERT INTO day2.documents (id, source, uri, content_hash, ingested_at) VALUES
    (1, 'postgres-docs', 'file://intro.md',   'aaa111', '2026-09-01 10:00:00+00'),
    (2, 'postgres-docs', 'file://intro.md',   'aaa111', '2026-09-10 10:00:00+00'),
    (3, 'postgres-docs', 'file://queries.md', 'bbb222', '2026-09-10 11:00:00+00'),
    (4, 'pgvector',      'file://readme.md',  'ccc333', '2026-09-01 09:00:00+00'),
    (5, 'pgvector',      'file://readme.md',  'ddd444', '2026-09-12 09:00:00+00'),
    (6, 'handbook',      'file://oncall.md',  'eee555', '2026-09-08 08:00:00+00'),
    (7, 'handbook',      'file://empty.md',   'fff666', '2026-09-08 08:30:00+00'),
    (8, 'postgres-docs', 'file://queries.md', 'bbb222', '2026-09-20 12:00:00+00');

INSERT INTO day2.chunks (id, document_id, body, token_count) VALUES
    (1,  1, 'Postgres stores data in tables.', 6),
    (2,  1, 'SQL is the query language.', 5),
    (3,  2, 'Postgres stores data in tables.', 6),
    (4,  2, 'SQL is the query language.', 5),
    (5,  3, 'SELECT lists columns.', 4),
    (6,  3, 'JOIN combines tables.', 4),
    (7,  3, 'GROUP BY collapses rows.', 5),
    (8,  4, 'pgvector adds a vector type.', 6),
    (9,  5, 'pgvector adds a vector type.', 6),
    (10, 5, 'HNSW is the default ANN index.', 7),
    (11, 5, 'Use cosine distance for embeddings.', 6),
    (12, 5, 'Keep metadata next to the vector.', 7),
    (13, 6, 'Page the on-call engineer at night.', 7),
    (14, 6, 'Severity 1 means a user-facing outage.', 8);
-- document 7 (empty.md) has no chunks on purpose
-- document 8 reuses hash bbb222; give it one chunk so latest-by-source still has text

INSERT INTO day2.chunks (id, document_id, body, token_count) VALUES
    (15, 8, 'SELECT lists columns (re-ingest).', 5);

CREATE INDEX day2_documents_content_hash_idx
    ON day2.documents (content_hash);

CREATE INDEX day2_documents_source_ingested_idx
    ON day2.documents (source, ingested_at DESC);

CREATE INDEX day2_chunks_document_id_idx
    ON day2.chunks (document_id);
