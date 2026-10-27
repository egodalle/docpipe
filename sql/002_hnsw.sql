-- D3: unique chunk ordinals, HNSW, and search_chunks.
-- Safe to re-run. Fresh installs also get these from 001_init.sql.

CREATE UNIQUE INDEX IF NOT EXISTS chunks_document_ordinal_strategy_uidx
    ON chunks (document_id, ordinal, strategy);

CREATE INDEX IF NOT EXISTS embeddings_hnsw
    ON embeddings USING hnsw (embedding vector_cosine_ops);

CREATE OR REPLACE FUNCTION search_chunks(
    query_embedding vector(768),
    k integer DEFAULT 5
)
RETURNS TABLE (
    chunk_id uuid,
    document_id uuid,
    uri text,
    source text,
    ordinal integer,
    body text,
    score double precision
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        c.id AS chunk_id,
        c.document_id,
        d.uri,
        d.source,
        c.ordinal,
        c.body,
        (1 - (e.embedding <=> query_embedding))::double precision AS score
    FROM embeddings e
    JOIN chunks c ON c.id = e.chunk_id
    JOIN documents d ON d.id = c.document_id
    WHERE d.status = 'live'
    ORDER BY e.embedding <=> query_embedding
    LIMIT k;
$$;
