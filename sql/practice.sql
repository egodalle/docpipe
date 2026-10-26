-- Day 2 practice queries.
-- Run after sql/seed.sql:
--   PGPASSWORD=docpipe psql -h 127.0.0.1 -p 5433 -U docpipe -d docpipe -f sql/seed.sql
--   PGPASSWORD=docpipe psql -h 127.0.0.1 -p 5433 -U docpipe -d docpipe -f sql/practice.sql
--
-- Covers SELECT, JOINs, GROUP BY, CTEs, window functions, and indexes.
-- Required shapes: duplicates, latest-by-source, chunk counts per document.

\echo '--- 1. SELECT: postgres-docs rows, newest first ---'
SELECT id, source, uri, content_hash, ingested_at
FROM day2.documents
WHERE source = 'postgres-docs'
ORDER BY ingested_at DESC;

\echo '--- 2. JOIN: each chunk with its document uri ---'
SELECT c.id AS chunk_id, d.uri, c.token_count, c.body
FROM day2.chunks AS c
INNER JOIN day2.documents AS d ON d.id = c.document_id
ORDER BY d.uri, c.id;

\echo '--- 3. GROUP BY: chunk counts per document ---'
SELECT
    d.id,
    d.uri,
    COUNT(c.id) AS chunk_count,
    COALESCE(SUM(c.token_count), 0) AS token_sum
FROM day2.documents AS d
LEFT JOIN day2.chunks AS c ON c.document_id = d.id
GROUP BY d.id, d.uri
ORDER BY chunk_count DESC, d.id;

\echo '--- 4. Duplicates: content_hash appearing more than once ---'
SELECT
    content_hash,
    COUNT(*) AS ingest_count,
    ARRAY_AGG(id ORDER BY ingested_at) AS document_ids
FROM day2.documents
GROUP BY content_hash
HAVING COUNT(*) > 1
ORDER BY ingest_count DESC, content_hash;

\echo '--- 5. Latest-by-source: DISTINCT ON (Postgres idiom) ---'
SELECT DISTINCT ON (source)
    source,
    id,
    uri,
    content_hash,
    ingested_at
FROM day2.documents
ORDER BY source, ingested_at DESC, id DESC;

\echo '--- 6. Window: latest row per (source, uri) via ROW_NUMBER ---'
WITH ranked AS (
    SELECT
        id,
        source,
        uri,
        content_hash,
        ingested_at,
        ROW_NUMBER() OVER (
            PARTITION BY source, uri
            ORDER BY ingested_at DESC, id DESC
        ) AS rn
    FROM day2.documents
)
SELECT id, source, uri, content_hash, ingested_at
FROM ranked
WHERE rn = 1
ORDER BY source, uri;

\echo '--- 7. CTE: latest-per-source joined to chunk counts ---'
WITH latest AS (
    SELECT DISTINCT ON (source)
        id,
        source,
        uri,
        ingested_at
    FROM day2.documents
    ORDER BY source, ingested_at DESC, id DESC
)
SELECT
    latest.source,
    latest.uri,
    latest.ingested_at,
    COUNT(c.id) AS chunk_count
FROM latest
LEFT JOIN day2.chunks AS c ON c.document_id = latest.id
GROUP BY latest.source, latest.uri, latest.ingested_at
ORDER BY latest.source;

\echo '--- 8. Window: each chunk vs its document average token_count ---'
SELECT
    c.document_id,
    c.id AS chunk_id,
    c.token_count,
    ROUND(AVG(c.token_count) OVER (PARTITION BY c.document_id), 2) AS avg_tokens_in_doc,
    c.token_count
        - AVG(c.token_count) OVER (PARTITION BY c.document_id) AS vs_doc_avg
FROM day2.chunks AS c
ORDER BY c.document_id, c.id;

\echo '--- 9. LEFT JOIN: documents with zero chunks ---'
SELECT d.id, d.source, d.uri
FROM day2.documents AS d
LEFT JOIN day2.chunks AS c ON c.document_id = d.id
WHERE c.id IS NULL
ORDER BY d.id;

\echo '--- 10. Indexes: EXPLAIN a duplicate-hash lookup ---'
-- Eight rows is small enough that the planner prefers a seq scan.
-- Disable seq scan so the lesson is the index, not the cost model.
SET enable_seqscan = off;
EXPLAIN (FORMAT TEXT)
SELECT id, uri, ingested_at
FROM day2.documents
WHERE content_hash = 'aaa111';
SET enable_seqscan = on;
