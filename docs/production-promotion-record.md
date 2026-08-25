# Production promotion record

Complete this operator-owned record immediately after a SHA-pinned production
workflow succeeds. Deployment IDs, model revisions, approval, and the
observation outcome cannot be populated by repository automation. See
[Railway staging and production promotion](railway-production-promotion.md).

| Field | Value |
| --- | --- |
| Candidate SHA | _pending_ |
| Staging evaluation artifact URL | _pending_ |
| Human reviewer, approval timestamp, and shipped-story smoke-test notes | _pending_ |
| Railway production deployment ID | _pending_ |
| Pages production deployment ID | _pending_ |
| Model / prompt revision | _pending_ |
| Prior known-good rollback target | _pending_ |
| New known-good rollback target | _pending_ |
| Observation window and outcome | _pending_ |

Do not remove the historical pre-V2 baseline until this record is complete and
the agreed observation window has passed. If production verification fails, keep
production on its prior deployment, leave `/dev/` unchanged, and record the
failure in the workflow or incident log.
