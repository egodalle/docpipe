-- Hybrid retrieval: tsvector on chunk bodies. Safe to re-run.
-- Vector search_chunks() is unchanged. Python fuses ranks.

ALTER TABLE chunks ADD COLUMN IF NOT EXISTS body_tsv tsvector;

CREATE INDEX IF NOT EXISTS chunks_body_tsv_gin
    ON chunks USING GIN (body_tsv);

CREATE OR REPLACE FUNCTION chunks_body_tsv_update()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.body_tsv := to_tsvector('english', COALESCE(NEW.body, ''));
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS chunks_body_tsv_tg ON chunks;
CREATE TRIGGER chunks_body_tsv_tg
    BEFORE INSERT OR UPDATE OF body ON chunks
    FOR EACH ROW
    EXECUTE FUNCTION chunks_body_tsv_update();

UPDATE chunks
SET body_tsv = to_tsvector('english', body)
WHERE body_tsv IS NULL;
