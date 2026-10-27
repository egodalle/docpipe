# ADR 0009 — Dynamic corpus path

- Status: Accepted
- Date: 2026-10-27
- Deciders: Ed Godalle

## Context

Ingest and `/ask` were pinned to `data/licenses.csv` + `data/raw/<source>/<file>`, and `source` was a two-value enum. Someone cloning the repo could not point the local demo at their own html/markdown/text folder without editing code. A second corpus in the UI needs a path, not a rewrite of the pipeline.

## Decision

1. **Discover a directory.** `licenses.csv` + `raw/` stays the seed layout. A folder of `.html` / `.md` / `.txt` (flat or nested) is also a corpus; sources are slugs from folder names.
2. **Local switch only.** `GET/POST /corpus` and the demo path field. Disabled when `K_SERVICE` is set (Cloud Run). Do not upload other people’s files to the P1 GCS bucket.
3. **Hash-skip sync.** Switching runs `docpipe sync` on that path. Unchanged hashes skip. Retrieval filters to the active URI prefix so the previous corpus stays in Postgres but is not mixed into `/ask`.
4. **`source` is a slug**, not a closed enum. Seed licenses are unchanged.

## Consequences

- **Good:** Clone, paste a path, index, ask. No copy into `data/raw`. Switching back to `data/` reuses existing embeddings.
- **Bad:** Nested trees cap at 200 files; PDF is still unsupported. Golden/refuse eval still describe the seed corpus until rewritten.
- **Follow-up:** None for P1. Cloud Run stays authenticated and SQL stays stopped.
