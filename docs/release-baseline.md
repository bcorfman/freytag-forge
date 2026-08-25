# Historical V1 production rollback record

This immutable record predates V2 cutover. Use it only when restoring the
historical V1 deployment; current V2 promotion is documented in
[Railway staging and production promotion](railway-production-promotion.md).
It was captured on 2026-08-10 from the successful
[production-promotion workflow](https://github.com/bcorfman/freytag-forge/actions/runs/31351185287).

| Record | Value |
| --- | --- |
| V1 production API commit | `1968f119793a11f38f22f6c80b9ad5e0a20e0862` |
| Railway production deployment | `3d2d38c6-47eb-4d8f-a400-c13d6d51695e` |
| Railway API origin | `https://freytag-forge-production.up.railway.app` |
| Pages production deployment | `bf21b0cd2352e075c4dfc25599c81c48b67bb5d1` |
| Pages deployment workflow | [run 31233023501](https://github.com/bcorfman/freytag-forge/actions/runs/31233023501) |
| Pages URL | `https://bcorfman.github.io/freytag-forge/` |
| Verified production workflow | [run 31351185287](https://github.com/bcorfman/freytag-forge/actions/runs/31351185287) |

The Pages bundle predates the API deployment because the frontend did not
change. Restore the matching API and Pages artifacts together when needed.

## Rollback instructions

1. Stop promotion and do not deploy a replacement from `main`.
2. Redeploy the recorded Railway deployment and verify `GET /api/v1/health`.
3. If needed, redeploy the recorded Pages commit and verify the root URL.
4. Run hosted E2E and record restoration deployment IDs in the incident.
