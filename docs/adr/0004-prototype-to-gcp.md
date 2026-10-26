# ADR 0004 — Lift the v0 prototype; do not restart

- Status: Accepted
- Date: 2026-10-26
- Deciders: Ed Godalle

## Context

A 30-day local roadmap produced a GitHub repo, a frozen v0 brief, Docker Postgres on 5433, and practice SQL in schema `day2`. A later career plan chose GCP for portfolio evidence. Restarting from a Vertex notebook would throw away the data-contract thinking.

## Decision

Continue in **this repo** (`egodalle/docpipe`). Keep `day2` as a sandbox. The P1 schema lives in `public` via `sql/001_init.sql`. The v0 brief is historical; [CHARTER.md](../CHARTER.md) is the executing document.

## Consequences

- Practice queries stay valid against `day2`.
- Port 5433 local Postgres remains the default dev database.
- README must describe both local dev and GCP demo, not only the 30-day diary.
