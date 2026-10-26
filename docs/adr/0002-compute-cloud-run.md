# ADR 0002 — Compute: Cloud Run job + service

- Status: Accepted
- Date: 2026-10-26
- Deciders: Ed Godalle

## Context

Ingest is batch. Serving is request/response with a latency budget of a few seconds. Options: GKE, Cloud Functions, Cloud Run, a VM.

## Decision

- **Cloud Run job** `docpipe-ingest` for extract → test → embed.
- **Cloud Run service** `docpipe-api` for HTTP.
- **Cloud Scheduler** triggers the job nightly. Event-driven GCS→Pub/Sub is Project 3.

## Consequences

- **Good:** No cluster. Scale-to-zero on the API. Same container image locally via Docker.
- **Bad:** Job timeout and memory must be set explicitly for PDF extract + embed batches.
- **Not chosen:** GKE (ops theater at this size); Cloud Functions (worse for long ingest).
