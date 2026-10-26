# Data contract — DocPipe P1

| Field | Value |
| --- | --- |
| Document | DOC-003 |
| Version | 1.0 |
| Status | Frozen for P1 |
| Date | 2026-10-26 |

Postgres is the system of record. BigQuery holds analytics copies, not a second truth. Schema v1 is applied by `sql/001_init.sql` (to be written in week 1). Practice tables in schema `day2` are **not** this contract.

## Document (source file)

A document is eligible for ingest when all of the following hold:

| Field | Rule |
| --- | --- |
| `source` | One of: `postgres-docs`, `pgvector` |
| `uri` | Stable GCS URI `gs://…` or `file://` in local dev |
| `content_hash` | SHA-256 of extracted text, hex, unique among **live** rows |
| `ingested_at` | Set by the job (timestamptz, UTC) |
| `license` | Recorded in `licenses.csv`; redistributable |
| Extracted text | Non-empty after boilerplate strip; else quarantine |

No private, employer, or unlicensed files.

## Tables (Postgres)

### `documents`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | uuid pk | Generated |
| `source` | text not null | See enum above |
| `uri` | text not null | Unique with live rows |
| `content_hash` | text not null | Unique among live rows |
| `ingested_at` | timestamptz not null | |
| `status` | text not null | `live` \| `tombstoned` \| `quarantined` |
| `bytes` | int | Original object size |
| `char_count` | int | Extracted text |

### `chunks`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | uuid pk | |
| `document_id` | uuid fk | On delete cascade from tombstone job |
| `ordinal` | int not null | Order in document |
| `body` | text not null | `length(trim(body)) > 0` |
| `token_count` | int not null | `> 0` |
| `strategy` | text not null | Default `recursive_400_80` |
| `metadata` | jsonb | `source`, `uri`, `section`, `page` if known |

### `embeddings`

| Column | Type | Notes |
| --- | --- | --- |
| `chunk_id` | uuid pk/fk | 1:1 with chunk for v1 |
| `embedding` | vector(n) | `n` frozen in config |
| `model` | text not null | Frozen name |
| `dim` | int not null | Must equal config |
| `embedded_at` | timestamptz | |

### `query_logs`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | uuid pk | |
| `request_id` | text not null | From API |
| `question` | text not null | |
| `chunk_ids` | uuid[] | |
| `scores` | float[] | Same order |
| `answer` | text | Null if refused |
| `refused` | boolean not null | |
| `latency_ms` | int | |
| `model` | text | LLM name |
| `created_at` | timestamptz | |

### `eval_results`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | uuid pk | |
| `run_id` | text not null | |
| `question_id` | text not null | From golden set |
| `recall_at_5` | boolean | Expected URI in top 5 |
| `citation_hit` | boolean | |
| `latency_ms` | int | |
| `created_at` | timestamptz | |

## Pipeline tests (fail the job)

1. No live chunk with empty `body`
2. Every embedding `dim` equals config
3. Duplicate live `content_hash` count = 0
4. `token_count` within bounds (e.g. 20–800 for default strategy)
5. Orphan embeddings = 0
6. Empty-extract rate < 5% for the run

## Serving contract (`POST /ask`)

Request: `{ "question": string, "source"?: string }`  
Response: `{ "request_id", "answer", "refused", "citations": [{ "uri", "chunk_id", "snippet", "score" }], "latency_ms" }`  
Never return a stack trace. Cap question length. Cap `k`.
