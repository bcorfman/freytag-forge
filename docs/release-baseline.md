# Historical pre-V2 production baseline

This document is historical rollback evidence captured on 2026-08-10 from the
successful [production-promotion workflow](https://github.com/bcorfman/freytag-forge/actions/runs/31351185287).
It is not a current release target. Once the first V2 production promotion is
complete, record the replacement known-good target in
[production-promotion-record.md](production-promotion-record.md), then remove
this historical file in the same change.

| Record | Value |
| --- | --- |
| Historical production API commit | `1968f119793a11f38f22f6c80b9ad5e0a20e0862` |
| Railway production deployment | `3d2d38c6-47eb-4d8f-a400-c13d6d51695e` |
| Railway API origin | `https://freytag-forge-production.up.railway.app` |
| Pages production deployment | `bf21b0cd2352e075c4dfc25599c81c48b67bb5d1` |
| Pages deployment workflow | [run 31233023501](https://github.com/bcorfman/freytag-forge/actions/runs/31233023501) |
| Pages URL | `https://bcorfman.github.io/freytag-forge/` |
| Verified production workflow | [run 31351185287](https://github.com/bcorfman/freytag-forge/actions/runs/31351185287) |

If a first V2 promotion fails, stop the candidate promotion and restore the
recorded Railway deployment; restore the Pages artifact when needed; then run
the hosted-demo E2E against the restored root. Do not alter `/dev/` while
recovering production.
