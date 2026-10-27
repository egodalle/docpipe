-- Citation integrity flag on query_logs. Safe to re-run.

ALTER TABLE query_logs
    ADD COLUMN IF NOT EXISTS citation_ok boolean;
