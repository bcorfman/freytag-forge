# Staging evaluation and promotion gate

The `V2 staging evaluation and promotion gate` runs only after the tested SHA
has deployed to the isolated staging API and the hosted browser E2E succeeds.
It writes SHA-bound staging evidence; it is not a second runtime authority.

## Automated gate

The workflow verifies the staging API and `/dev/deployment.json` identify the
same immutable SHA and staging channel, then runs
`tests/test_runtime_v2.py` and `tests/test_web_demo_v2.py`. It writes the
SHA-bound `v2-staging-evidence-v1` artifact with the API URL and verification
slice. Required coverage and hosted browser E2E are prerequisites.

The gate fails on identity mismatch or a failed prerequisite/test slice. A
successful run publishes the `staging-deployment` status required by production
promotion. The [acceptance matrix](v2-acceptance-matrix.md) is the broader
manual evidence checklist; the [scorecard](v2-acceptance-scorecard.md) defines
metrics for an expanded evaluator rather than fields in the current artifact.
The hosted E2E retries one uncommitted `/turn` request only when the runtime has
already exhausted its bounded model recovery and returns `503 runtime_failure`;
identity errors, client errors, and a repeated runtime failure still fail the
gate.

## Human approval

After staging passes, play a short unscripted session at
`https://bcorfman.github.io/freytag-forge/dev/`; check the non-production badge,
freeform flow, and save/load continuity. To approve, dispatch **Promote staged
SHA to production** with no SHA to select the newest successful staged commit,
or supply a deliberate older full SHA, then approve the protected production
environment. To reject, do not dispatch the workflow; retain staging evidence.

Record the completed promotion in
[production-promotion-record.md](production-promotion-record.md). Any prompt,
pacing, fixture, or package change requires a new SHA, full test run, staging
gate, and approval.
