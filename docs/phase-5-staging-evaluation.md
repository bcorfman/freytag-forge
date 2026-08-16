# Phase 5 staging evaluation

The automated Phase 5 gate is `V2 staging evaluation and promotion gate` in
the main deployment workflow. It runs only after the candidate SHA is deployed
to the isolated staging API and the hosted browser E2E has passed.

It starts one session for each compiled fixture (mystery, fantasy, sci-fi, and
relationship), plays these seven generic styles in each session, then verifies
save/load: investigate, travel, social, avoidant, adversarial, repeated
failure, and unexpected action. This is automated engine-regression coverage,
not a requirement to manually review four player-facing releases. The evaluator verifies the API version response
is `staging` and exactly the candidate SHA; reports one-call and repair rates,
p95 request latency, typed fail-closed errors, protected-revelation text,
continuity checks, completion rate, and user-facing session failures; and
writes `staging-evaluation.json` as a SHA-named workflow artifact.

The deployment workflow also stamps each Pages bundle with a channel/SHA
`deployment.json` and blocks staging until the deployed `/dev/deployment.json`
and staging API health response both match the candidate. Identity reconciliation
is automated; it is not a human-review task.

For every package that declares an opening document briefing, the evaluator
also derives a direct NPC question from that package's `npc_disclosures` data.
It rejects an opening that already exposes the document-only value, then
requires the question's reply to render the declared fact value and the API
state projection to include its committed key in `known_facts`. A missing
commit, repeated public-only briefing, 503, protected leak, continuity break,
or SHA mismatch fails the promotion gate. When that disclosure check fails, the
SHA-bound report retains up to 500 characters of the rendered reply so the
candidate can be diagnosed without replaying the staging session.

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
no protected revelation or state-continuity violation is observed, the p95
ordinary-turn latency is below ten seconds, and the hosted E2E passes. The
workflow status `staging-deployment` is published only after this gate, so
production promotion continues to reject untested SHAs. The full-coverage job
is a prerequisite of staging deployment and retains the project-wide 90%
coverage floor; each evaluated turn must report one or two model calls, so the
same gate also rejects an unbounded recovery path.

## Baseline comparison

`staging-evaluation.json` is the immutable candidate-side comparison record.
It records the Phase 0 measures from the
[V2 migration acceptance scorecard](v2-acceptance-scorecard.md): one-call and
repair rates, typed failures, p95 latency, revelation leaks, continuity,
completion, and user-facing failures. The historical V1 measurements are
comparison-only because they used in-process stubs rather than a live provider;
the actionable Phase 5 comparisons are therefore the preserved two-request
recovery cap, zero integrity failures, the under-ten-second p95 target, and
the upstream 90% coverage gate. Reviewers compare the candidate artifact with
the baseline scorecard before issuing their SHA-specific approval.

Completion rate remains a recorded scorecard measure, not a required scripted
ending: the seven styles are deliberately agency probes, not a prescribed
solution. The automated report retains their transcripts as diagnostic evidence;
the human reviewer assesses the currently shipped story rather than treating
each engine fixture as a separate release.

## Human review and approval

After the workflow succeeds, use the staged SHA from its artifact and follow
this review without changing prompts, pacing thresholds, or fixtures in place:

1. Visit `https://bcorfman.github.io/freytag-forge/dev/`, confirm the
   non-production badge, and play one short unscripted Elias Wren session. Make
   several ordinary freeform moves, use `/save <slot>`, make another move, then
   `/load <slot>`. Record brief notes on narrative flow, agency, clarity, and
   whether the restored location and turn index are correct.
2. To **approve**, open the GitHub Actions workflow **Promote staged SHA to
   production** and run it with the SHA input blank. It resolves the newest
   successful staging candidate on `main`; provide a full SHA only to promote a
   deliberate older candidate. Approve the protected `freytag-forge /
   production` environment when GitHub pauses the run. That environment
   approval is the SHA-bound decision and audit record. To **reject**, do not
   dispatch the promotion workflow; retain the staging evidence and, if useful,
   record the reason in the workflow or issue.
3. If pacing or prompt guidance changes, increment the relevant compiled-story
   fixture version, rerun the full regression suite and staging gate, then
   review the new SHA. Do not repair a finding with deterministic incidents or
   genre-specific runtime logic.

The protected-environment approval in the SHA-pinned production-promotion
workflow is the remaining Phase 5 exit criterion. Complete
`production-promotion-record.md` only after that workflow succeeds.
