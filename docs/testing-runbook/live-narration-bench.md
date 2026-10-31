# Live narration bench

Part of [the testing runbook](../testing-runbook.md).

## 4. Live narration bench (billed)

**Purpose:** Measure prompt, package, or runtime changes against the real
Cloudflare narrator without deploying. Quality and integration evidence only;
section 1 remains authoritative.

**Cost:** The continuity judge makes OpenAI judge calls, while the fact judge
makes Cloudflare Jev requests. Jev is paid from AI Gateway credit, not the
Workers AI allowance, and needs `CLOUDFLARE_ACCOUNT_ID` and
`CLOUDFLARE_AI_TOKEN` in `.env`. Set `BENCH_FACT_JUDGE=luna` to switch the fact
judge back to OpenAI.

**Run:** Live runs go through Ringer, because a sandboxed worker cannot reach the
network or write `bench/results/`:

```bash
cd /home/bcorfman/dev/ringer && ./ringer.py run /home/bcorfman/dev/freytag-forge/bench/manifests/phase7-live-bench.json
```

The underlying command shape, for writing a new manifest:

### Stage 7 door probe

Free first: `PYTHONPATH=$PWD TMPDIR=/tmp .venv/bin/python scripts/ringer/stage7/door_probe.py --n 12 --experiment <door|source|completion|grounded|transition|details> --dry-run --out <dir>`, then `scripts/ringer/stage7/check_door_probe.py <dir> 12 --mode dry --experiment <same>` (the `door` experiment has no `--experiment` flag). Experiments: `door`, `source` and `completion` are two-command wording screens; `grounded` is the two-command panel screen with named-reveal scoring and clarification forwarding; `transition` and `details` run a full 2B continuation per row (raw player, 20-command cap) and count `earned_exit`, `timer_exit` and `no_exit` from the runtime's `transition_cause`, which is the adoption measure (earned exits at least 80%). `details` compares a frozen baseline package with the current one under identical 2A prompts. `scripts/ringer/stage7/payload_2b.py --out <dir>` rebuilds the 2B turn-1 prompts offline for both `details` arms and prints their diff. Live smoke and full runs are Ringer tasks that require `--confirm`, source `.env` only inside Ringer, check with `--mode artifacts`, and preserve partial artifacts without retries, replacement samples or pooling. Write the preregistration (arms, caps, keep rule) in `.plans/` before any billed run. These are source screens on a replayed 2A and a fresh 2B state, not hosted validation.

```bash
uv run python -m bench run --variation bench/variations/authored-handoff-phase1.json \
  --scene 1A --replicates 4 --script candidate-selection-repro --out /tmp/bench-1a --confirm
uv run python -m bench compare <baseline-variation> <candidate-variation>
uv run python -m bench.candidate_selection_report --in /tmp/bench-1a/all-turn-records.json \
  --out-json /tmp/bench-1a/report.json --out-md /tmp/bench-1a/report.md
```

**Pass / interpretation:**

- Read `summary.json`: `failed_replicates` and the verbatim `failure_reason`
  strings distinguish a failed run from one that never executed.
- `all-turn-records.json` keeps every turn, including failed replicates.
  `authored_handoff_candidate_id` is bench-only telemetry; a non-null value on
  an action that should not earn a reveal is a false positive.
- `model_selected_knowledge_ids` empty with `selected_knowledge_ids` non-empty
  means the runtime, not the model, owned the reveal.
- Use at least four replicates. Within-variation variance is as large as most
  between-variation gaps; `bench compare` reports whether arms are
  distinguishable. Never report a one- or two-point difference as real.
- Bench scenes start from a bare arrival state (only the entry fact committed),
  so a mid-story scene can fail safety checks a real playthrough would not.

For the live-baseline / hidden-clues smoke report, `narration_attempts` is the logical count, `narration_http_prompts` is the raw HTTP count, late completions are listed under `late_completions_after_turn`, and the drain section is labelled `drain outcomes`.

**Stop conditions:** HTTP 429 with `X-Narration-Error-Code: AI_QUOTA_EXCEEDED`
or `AI_DAILY_BUDGET_EXCEEDED` is a daily model limit; stop until 00:00 UTC.
`{"detail":"rate limit exceeded"}` is the app limiter and is retried automatically.

**Cleanup:** Outputs under `/tmp` are disposable. Never rewrite or delete
ledger lines.
