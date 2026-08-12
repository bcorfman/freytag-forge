# Production promotion record

Complete this record immediately after the SHA-pinned production workflow
succeeds. This repository cannot populate it automatically because deployment
IDs, production model revisions, and the human approval are operator-owned.

| Field | Value |
| --- | --- |
| Candidate SHA | _pending_ |
| Staging evaluation artifact URL | _pending_ |
| Human reviewer and approval timestamp | _pending_ |
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
