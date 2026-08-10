# V1 production release baseline

This document is the immutable rollback record for the V1 production service while the V2 migration is developed on the future staging channel. It was captured on 2026-08-10 from the successful [production-promotion workflow](https://github.com/bcorfman/freytag-forge/actions/runs/31351185287).

| Record | Value |
| --- | --- |
| V1 production API commit | `1968f119793a11f38f22f6c80b9ad5e0a20e0862` |
| Railway production deployment | `3d2d38c6-47eb-4d8f-a400-c13d6d51695e` |
| Railway API origin | `https://freytag-forge-production.up.railway.app` |
| Pages production deployment | `bf21b0cd2352e075c4dfc25599c81c48b67bb5d1` |
| Pages deployment workflow | [run 31233023501](https://github.com/bcorfman/freytag-forge/actions/runs/31233023501) |
| Pages URL | `https://bcorfman.github.io/freytag-forge/` |
| Verified production workflow | [run 31351185287](https://github.com/bcorfman/freytag-forge/actions/runs/31351185287) |

The Pages bundle predates the API deployment because the frontend did not change. Those identifiers are intentionally recorded separately: a rollback must restore the API and Pages artifact appropriate to the incident.

## Rollback instructions

1. Stop the candidate promotion; do not deploy a replacement from `main`.
2. In Railway, redeploy deployment `3d2d38c6-47eb-4d8f-a400-c13d6d51695e` to the production environment, then verify `GET /api/v1/health` at the recorded API origin.
3. If the browser artifact also needs rollback, re-run the Pages deployment from commit `bf21b0cd2352e075c4dfc25599c81c48b67bb5d1` and confirm the root URL serves that artifact.
4. Run the hosted-demo E2E against the restored production API with the root Pages origin, and record the restoration deployment IDs in the incident.

Phase 1 will replace this single-channel process with SHA-pinned production promotion while leaving this V1 target intact until the first V2 promotion.
