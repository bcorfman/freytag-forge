# Testing runbook

How to verify freytag-forge: which command checks which boundary, what it
costs, what passing looks like, and how to clean up. This is an operating
manual, not a results log.

**Keeping this file short.** Edit an existing entry in place when a procedure
changes; add an entry only for a new verification boundary. Never append dated
observations, test counts, coverage figures, phase evidence, or diagnosis
narratives. Those belong in the plan, PR, commit message, or `bench/results/`.
Earlier history is in git.

Related: [test-suite guide](test-suite-performance-guide.md) (markers, tiers,
CI jobs) and [`bench/README.md`](../bench/README.md) (bench flags, ledger,
variations).

## Conventions for every command

- Run from the repository root. Pytest needs `TMPDIR=/tmp` (WSL); use
  `uv run python`, never bare `python`.
- Coverage is off unless `--cov` is given. Focused pytest runs need no extra
  flag; use the full suite with `--cov` as the coverage check of record.
- Never pin collection counts in tests or in this file.
- Hosted checks run against staging only, never a local API. Staging deploys
  only from `main`.

## Detail index

- [Local deterministic and focused checks](testing-runbook/local-checks.md): read this when you need the authoritative local suite or a focused test for a code boundary.
- [Prompt inspection](testing-runbook/prompt-inspection.md): read this when you need to inspect narrator payloads, saved artifacts, or runtime-composed player text.
- [Live narration bench](testing-runbook/live-narration-bench.md): read this when you need billed model-based evidence or a Stage 7 door probe.
- [Staged deployment and hosted E2E](testing-runbook/hosted-e2e.md): read this when you need to deploy to staging or run hosted browser categories.
- [Hosted canon, clock, and timeline probes](testing-runbook/hosted-probes.md): read this when you need the canon judge, staging test clock, or knowledge-timeline probe.
- [Worker source check and hosted failure diagnosis](testing-runbook/worker-and-failures.md): read this when you need to check the Worker contract or interpret a hosted failure.
