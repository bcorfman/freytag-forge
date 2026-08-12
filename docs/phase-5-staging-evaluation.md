# Phase 5 staging evaluation

The automated Phase 5 gate is `V2 staging evaluation and promotion gate` in
the main deployment workflow. It runs only after the candidate SHA is deployed
to the isolated staging API and the hosted browser E2E has passed.

It starts one session for each compiled fixture (mystery, fantasy, sci-fi, and
relationship), plays these seven generic styles in each session, then verifies
save/load: investigate, travel, social, avoidant, adversarial, repeated
failure, and unexpected action. The evaluator verifies the API version response
is `staging` and exactly the candidate SHA; reports one-call and repair rates,
p95 request latency, typed fail-closed errors, protected-revelation text,
continuity checks, completion rate, and user-facing session failures; and
writes `staging-evaluation.json` as a SHA-named workflow artifact.

The Pages build also publishes `/dev/deployment.json`, containing its channel
and immutable SHA. The gate compares that metadata with `/api/v1/version`
before it evaluates a turn, so a deployed API and browser bundle cannot be
mistakenly treated as one candidate.

The evaluator uses the same public staging API contract as a browser. It needs
no evaluation credential or special Railway variable. If the ordinary per-IP
rate limit is reached, it waits once for the existing one-minute rate window
and retries the blocked request. This keeps staging evaluation behavior aligned
with the public hosted surface while remaining bounded.

The candidate must also have a configured V2 `TurnModel` provider. The default
hosted construction deliberately fails closed with `service_unavailable` when
no provider is injected; that is a correct evaluator failure, not evidence of
passing freeform play. Configure and verify that provider before requesting a
Phase 5 candidate evaluation.

## Promotion gate

A candidate passes automatically only when all fixture/style turns finish, the
staging identity matches the immutable SHA, no typed fail-closed error occurs,
no protected revelation or state-continuity violation is observed, and the
hosted E2E passes. The workflow status `staging-deployment` is published only
after this gate, so production promotion continues to reject untested SHAs.

Completion rate remains a recorded scorecard measure, not a required scripted
ending: the seven styles are deliberately agency probes, not a prescribed
solution. A human reviewer assesses completion and qualitative pacing from the
transcripts before approval.

## Human review and approval

After the workflow succeeds, use the staged SHA from its artifact and follow
this review without changing prompts, pacing thresholds, or fixtures in place:

1. Visit `https://bcorfman.github.io/freytag-forge/dev/` and confirm the
   non-production badge is visible.
2. Start and freely play one unscripted session in each of the four genres.
   Record the URL, SHA, reviewer, and short notes on narrative flow, agency,
   clarity, and genre fit.
3. In one session, use a freeform move, `/save <slot>`, another move, and
   `/load <slot>`.
   Confirm the displayed location and turn index restore; trigger one harmless
   error (for example an invalid/expired session in a separate browser tab) and
   confirm the client presents a safe error rather than raw provider text.
4. Review `staging-evaluation.json`, the hosted E2E result, and the transcript
   notes. Explicitly record **approve** or **reject** for that exact SHA.
5. If pacing or prompt guidance changes, increment the relevant compiled-story
   fixture version, rerun the full regression suite and staging gate, then
   review the new SHA. Do not repair a finding with deterministic incidents or
   genre-specific runtime logic.

The explicit human approval is the remaining Phase 5 exit criterion and is the
authorization to invoke the separate SHA-pinned production-promotion workflow.
