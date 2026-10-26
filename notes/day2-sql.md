# Day 2 — SQL primer (through window functions)

Source: [Select Star SQL](https://selectstarsql.com/) (SELECT → aggregates → GROUP BY → joins) and the [PostgreSQL tutorial](https://www.postgresql.org/docs/current/tutorial.html) (tables, joins, aggregates, [window functions](https://www.postgresql.org/docs/current/tutorial-window.html)). Practice lives in `sql/practice.sql` against `day2.documents` / `day2.chunks`.

DocPipe stores documents, chunks, embeddings, and eval runs in Postgres — not in notebooks. Today is the language, not the frozen schema (that is Day 4).

## Query shape

```sql
SELECT ...          -- what you want
FROM ...            -- a table, a join, or a CTE
WHERE ...           -- row filter (before grouping)
GROUP BY ...        -- collapse rows
HAVING ...          -- filter after grouping
WINDOW ...          -- named OVER() definitions (optional)
ORDER BY ...
LIMIT ...;
```

`WHERE` filters rows. `HAVING` filters groups. Window functions are not allowed in `WHERE` / `GROUP BY`; wrap them in a subquery or CTE and filter after.

## SELECT and JOINs

- `INNER JOIN` keeps matches only.
- `LEFT JOIN` keeps every left row; right-side columns are NULL when nothing matches. That is how you find documents with zero chunks.
- Join on keys (`document_id`), not on text.

## Aggregates and GROUP BY

`COUNT`, `SUM`, `AVG`, `MIN`, `MAX` collapse a group to one row. `COUNT(*)` counts rows; `COUNT(column)` skips NULLs. Anything in `SELECT` that is not an aggregate must be in `GROUP BY`.

## CTEs

`WITH name AS (SELECT ...)` names a result so the next statement can read it. Use a CTE when you would otherwise nest a subquery (latest-per-source, then join chunk counts).

## Window functions

A window function computes across related rows **without collapsing them**. Always `OVER (...)`.

- `PARTITION BY col` — peer group (like GROUP BY, but rows stay).
- `ORDER BY col` inside `OVER` — order inside the partition. Default frame with `ORDER BY` is “start of partition through current row.”
- `ROW_NUMBER() OVER (PARTITION BY source, uri ORDER BY ingested_at DESC)` — latest version of a file.
- `AVG(token_count) OVER (PARTITION BY document_id)` — compare one chunk to its siblings.
- `SUM(x) OVER (ORDER BY ingested_at)` — running total.

Postgres shortcut for “latest row per key”: `DISTINCT ON (source) ... ORDER BY source, ingested_at DESC`.

## Indexes

An index is a lookup structure, not a second copy of the table you query instead of SQL. Create them for filters and joins you will repeat:

- `documents(content_hash)` — duplicate / idempotent ingest checks
- `documents(source, ingested_at DESC)` — latest-by-source
- `chunks(document_id)` — chunk counts per document

Confirm with `EXPLAIN`: look for `Index Scan` / `Index Only Scan`, not a sequential scan of a large table. Today’s sample is tiny, so EXPLAIN is the lesson, not a speed demo.

## What this is not

No Spark, no Kafka, no warehouse modeling. No `pgvector` yet (Day 6). No frozen `documents` / `chunks` / `embeddings` schema yet (Day 4). Practice tables live in schema `day2` so Week 1 migrations can land in `public` later.
