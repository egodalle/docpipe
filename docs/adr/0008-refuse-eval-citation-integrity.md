# ADR 0008 — Refuse eval and citation integrity

- Status: Accepted
- Date: 2026-10-27
- Deciders: Ed Godalle

## Context

Charter eval numbers are recall@5 **and citation hit rate**. `citation_hit` in D6 was a copy of recall@5 (the expected file appeared in top-5). The refuse path was proven with two ad-hoc curls, not a golden set. A hiring manager can ask: “when do you not call the LLM?” and “did the model cite a chunk you did not retrieve?”

## Decision

1. **Refuse golden set** (`eval/refuse.json`, 8 off-corpus questions). `docpipe eval --refuse` embeds and retrieves only — **no Gemini**. A hit is `refused == expect_refused`. Bar: **1.00**.
2. **Citation integrity** on every `/ask`: parse `[uuid]` cites in the answer; they must all be retrieved chunk ids. Refused asks must have `answer is null`. Store `query_logs.citation_ok`. Surface on `/ask` and `/stats`.

Do not add a second LLM judge (cost, flakiness). Do not change `refuse_min_score`.

## Consequences

- **Good:** The product contract is measured, not only retrieval recall. Cheap (refuse eval is embeddings only).
- **Bad:** Integrity is syntactic (cited ids ⊆ retrieved ids), not semantic faithfulness of the prose.
- **Not chosen:** NLI/groundedness model, LLM-as-judge, expanding Dataform this pass.
