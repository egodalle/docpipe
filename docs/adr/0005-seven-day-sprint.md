# ADR 0005 — Compress P1 to a 7-day sprint

- Status: Accepted
- Date: 2026-10-26
- Deciders: Ed Godalle

## Context

The original plan was six weeks at 10–12 hours/week (~70 hours) with a 2026-12-06 ship date. Capacity is now unlimited hours and the sponsor wants v1.0 in one week. Cost cap is **$25**, not $90.

## Decision

- Ship window: **2026-10-26 → 2026-11-02**.
- Keep the charter outcome (Terraform, cited `/ask`, eval numbers, incremental no-op).
- Cut, do not defer into the same week: hybrid search, second chunk strategy as a served default, Streamlit, Pub/Sub, GKE, WIF-from-scratch if it blocks the tag (local + `gcloud` auth is acceptable for v1.0 CI).
- Cloud SQL `db-f1-micro`, no HA, public IP + Auth Proxy, `activation_policy` **NEVER** except while working or demoing.

## Consequences

- Daily milestones replace weekly ones. Eval is still the ship gate.
- Thanksgiving (week 5 of the old plan) is no longer on the critical path.
- Burnout is a risk; cut list is mandatory if a day slips.
