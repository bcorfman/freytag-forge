# Narration prompt bench

`bench` is a development-only, local harness for trying prompt variations against the same Python runtime and Cloudflare narrator used by the app. It writes the exact turn records consumed by the existing JavaScript canon judge; it does not replace the hosted Playwright suite or deploy anything.

## Quick start

Run these commands from the repository root. The CLI loads `.env` if present; it needs `CLOUDFLARE_WORKER_URL`, `CLOUDFLARE_WORKER_TOKEN`, and `OPENAI_API_KEY` only for live commands.

```bash
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench --help
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench prompt \
  --variation bench/variations/arm-c.json --scene 1A --turn 1 \
  --player-input "I search the kitchen and the back door for concrete signs of what happened here."
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench score \
  --run-dir /home/bcorfman/bakeoff-data/arm-c/run1
```

The `prompt` command makes no model request and prints only `{"system": ..., "user": ...}`. `score` is a deliberately stable fixture adapter and prints only the seven equally weighted boolean counts and their total out of 63.

## Commands

`chat` starts a live session at the first scene. Each response is followed by the exact system and user prompt that produced it:

```bash
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench chat --variation bench/variations/arm-c.json
```

`prompt` assembles a turn without contacting Cloudflare. `--turn` is validated for a positive turn number; the current prompt-fidelity seam is intended for turn 1. Later-turn prompt content depends on the prior committed runtime state, so a later turn should be reached with `chat` or `run` rather than pretending a fresh state is later in a scene.

`run` plays one scene per command, then makes one judge call per completed replicate. The default is four replicates. An explicitly requested single replicate is allowed for the cheap iteration loop, but cannot estimate noise, so its standard deviation and confidence interval are reported as unavailable:

```bash
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench run \
  --variation bench/variations/arm-c.json --scene 1A --replicates 4 \
  --script e2e --out /tmp/bench-arm-c-1a
```

Without `--script`, every script declared for the scene is run `N` times. Use `--script` for a focused arm; the shipped Arm C variation has `e2e`, `oblique-investigation`, and `unexpected-wander` scripts for 1A. The scene is advanced until its authored transition or the runtime’s safe turn limit. A wandering script is retained as a valid result.

Artifacts include:

- `turn-records.json`: Python runtime records with exactly `player_input`, `narration`, `left_scene`, and `beats_projected` in each judge turn.
- `judgment.json`: the first completed replicate’s raw judge verdict, with all seven booleans at top level.
- `summary.json`: pooled and per-script means, sample standard deviations, 95% confidence intervals, empirical minimum detectable effect, comparison results, graded secondary metrics, and budget telemetry.

Pass `--baseline DIR` to add a two-sided Welch t-test against another bench `summary.json` or an archived `e2e-llm-canon.json`. The report explicitly says `this changed nothing detectable (difference is inside the observed noise)` when the p-value is at least 0.05. No result is presented as a bare score.

`describe` resolves a variation, validates its effective story package, and prints its hashes and resolved prompt configuration without making model or network calls:

```bash
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench describe \
  --variation bench/variations/arm-c-overlay.json --json
```

`log` reads `bench/results/ledger.jsonl` in append order. `--ledger PATH` selects an alternate JSONL ledger; the default is the tracked path. `--variation NAME` filters by variation name and `--limit N` keeps the newest N matching rows. `--json` prints only the JSON array; without it, a compact table is printed. Failed rows remain visible in both forms.

`compare` pools every `scores` entry from successful, known-scale ledger rows for each named variation and reports each arm's mean and sample standard deviation, the difference, the two-sided Welch t-test, and the minimum detectable effect at the smaller available arm size. `--ledger PATH` selects an alternate ledger:

```bash
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench compare arm-c arm-c-no-example
```

Comparison refuses to mix known-scale rows when their `scenes_scored` values differ, because a 1/7 scene score and a 9/63 traversal score are incommensurable. It also refuses to mix effective story packages when their `package_hash` values differ. Use `--allow-coverage-mismatch` or `--allow-package-mismatch` only when the corresponding confound is intentional; the output then warns that the relevant boundary was not held constant. Failed rows are excluded from these statistics. Rows with missing or null `scenes_scored` have an unknown scale: they remain visible in `log`, but `compare` and `run --baseline` exclude them from n, means, standard deviations, Welch tests, and minimum detectable effects, and print how many were skipped and why. The same scene-coverage guard applies to known-scale `run --baseline` data; an unknown-scale baseline is reported and omitted rather than guessed.

## Results ledger

Every successful `bench run` appends a status-`ok` JSON object to the tracked, append-only `bench/results/ledger.jsonl`. A replicate that cannot produce a judgeable result appends a status-`failed` row instead, with `failure_reason`; this includes repeated `INVALID_PROPOSAL`, quota stops, and a run or judge failure. Failed rows carry the same configuration/provenance and spend fields, have no score, remain visible in `log`, and are excluded from `compare` statistics. Existing lines are never rewritten or reordered. The row records:

```json
{
  "timestamp": "2026-09-03T18:20:00Z",
  "variation_name": "arm-c",
  "variation_hash": "sha256 of resolved rules and prompt switches",
  "package_hash": "sha256 of effective package files",
  "git_sha": "repository HEAD",
  "git_dirty": true,
  "scene": "1A",
  "scripts": ["e2e"],
  "replicates": 1,
  "status": "ok",
  "scenes_scored": 1,
  "max_score": 7,
  "score_metric": "7-point record: seven equally weighted boolean criteria across 1 scene",
  "scores": [2],
  "example_leakage": 0,
  "mean": 2.0,
  "sd": null,
  "per_criterion": {"canon_consistent": 0, "scene_local": 1, "progressive": 0, "rich": 0, "protected_safe": 1, "exit_motivated": 0, "rewards_investigation": 0},
  "missing_or_wrong": {"total": 2, "per_criterion_where_attributable": {}, "unattributed": 2},
  "spend": {"neurons": 88.0, "judge_calls": 1},
  "model": "@cf/meta/llama-3.1-8b-instruct-fast"
}
```

`scenes_scored` is the number of distinct scenes actually judged in the row and `max_score` is `scenes_scored * 7`. Thus a focused Scene 1A row has a maximum of 7, while a nine-scene row has a maximum of 63. A failed row has `scenes_scored: 0`, `max_score: 0`, `scores: []`, and a non-empty `failure_reason`.

Older successful rows may predate the `scenes_scored` field, and a row may also explicitly contain `"scenes_scored": null`. Both forms have an unknown denominator. The bench never infers their scale from `scene`, `max_score`, or any other field: they are real runs retained by the append-only ledger and marked `legacy/unknown-scale` or `unknown-scale (null)` in the human-readable log, while statistics skip them with an explanatory message. New successful rows always record the known scene denominator.

`example_leakage` counts successful narration turns containing a distinctive span from the example used by that variation. A distinctive span is eight or more consecutive words shared by narration and example, case-insensitively after whitespace normalisation. Short common phrases do not count; a configuration with no example records zero. `variation_hash` hashes the resolved prompt rules, resolved output example, inclusion switch, and beat-delivery mode, not the variation filename. `package_hash` hashes every effective package file, including overlay changes. Neurons are the existing request-based estimate; exact Workers AI billing is not returned by the Worker.

## Variations

Variations are JSON data, not engine edits. The supported shape is:

```json
{
  "name": "example",
  "story_package": "data/stories/continuity-initiative",
  "system_prompt": {
    "rules": ["..."],
    "include_output_example": true,
    "output_example": "{\"segments\":[...],\"selected_knowledge_ids\":[]}"
  },
  "user_prompt": {"beat_delivery": "details"},
  "scripts": {
    "1A": [{"name": "my-script", "inputs": ["..."]}]
  }
}
```

`beat_delivery` is `details` for `<beat_detail>` noun phrases or `prose` for the authored `<beat>` block. `rules` replaces the normal rules block, while the runtime still supplies turn-specific candidate and handoff rules. `include_output_example: false` omits the block; `true` or omission uses today's default. A string `output_example` supplies the block contents verbatim and implies inclusion, even if the boolean is false. Non-string values are rejected. `story_package` may be any package path accepted by `load_story_package`; the live judge uses the same scene-local canon shape for arbitrary packages, while the archived hosted fixtures remain the continuity-initiative baseline.

An optional `overrides` object patches package files in a temporary effective copy. The source package is never modified. Targeted replacements use a relative filename and exact one-occurrence string replacements:

```json
{
  "overrides": {
    "plot.md": {
      "replacements": [
        {"old": "KMS initials in drawer", "new": "KMS initials carved beneath the drawer"}
      ]
    }
  }
}
```

Whole-file replacement is also accepted by supplying a string as the file's override value. The effective copy is what the runtime loads and sends to the narrator, and its content is what `package_hash` records.

The three shipped example configurations are:

- `variations/arm-c.json`: the measured Arm C, with beat details, all three prohibition rules, and today's drawer-imagery output example. Its first-turn system prompt is byte-identical to the archived Arm C fixture.
- `variations/arm-c-no-example.json`: the same prompt configuration with the example omitted. Removing it entirely has been observed to break response validity: the narrator repeatedly returned `INVALID_PROPOSAL` and produced no score.
- `variations/arm-c-neutral-example.json`: the same configuration with the JSON response shape retained but story-copyable prose replaced by neutral instructions. This separates the example's formatting job from its content leakage.

The leakage metric is calculated against the resolved example actually sent in the turn system prompt, so it works for arbitrary custom examples rather than only the shipped drawer text.

For example, run the two prompt-only experiment arms, then run one focused live replicate of each and compare their real ledger rows:

```bash
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench describe --variation bench/variations/arm-c.json --json
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench describe --variation bench/variations/arm-c-no-example.json --json
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench describe --variation bench/variations/arm-c-neutral-example.json --json
set -a && . /home/bcorfman/dev/freytag-forge/.env && set +a
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench run --variation bench/variations/arm-c.json --scene 1A --replicates 1 --script e2e --out /tmp/bench-arm-c --confirm
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench run --variation bench/variations/arm-c-no-example.json --scene 1A --replicates 1 --script e2e --out /tmp/bench-arm-c-no-example --confirm
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench compare arm-c arm-c-no-example
```

## Cost and safety

There are two independent budgets:

- Cloudflare Workers AI: the observed planning rate is about 330 neurons per 30 narration requests, or about 11 neurons per request. A full 30-turn traversal is therefore roughly 330 neurons. A nine-scene, four-replicate comparison is roughly 1,320 neurons, before any recovery requests; it fits comfortably below the 10,000-neuron daily free allocation, but fewer than eight such comparisons should be planned in one UTC day.
- OpenAI judge: one call per reached scene. A one-scene bench run makes exactly one call per completed replicate; a nine-scene, four-replicate comparison makes 36 calls.

Before a live run, the CLI prints projected neurons to stderr. Above `BENCH_CONFIRM_THRESHOLD_NEURONS` (default 500), it requires `--confirm` or an interactive yes. The estimate includes the declared scripts and one opening request per replicate. Actual worker neuron usage is not returned by the Worker, so `summary.json` reports exact narration request/turn counts and a clearly labeled request-based neuron estimate, plus exact judge-call count. It never claims that estimate is provider billing telemetry.

The Worker’s `429` quota response is distinguished by `X-Narration-Error-Code: AI_QUOTA_EXCEEDED` and stops the batch with completed/planned counts; it is not retried, and the interrupted replicate is recorded as failed. The application limiter’s `{"detail":"rate limit exceeded"}` is classified as `RATE_LIMITED` and retried using `BENCH_RATE_LIMIT_RETRIES` and `BENCH_RATE_LIMIT_RETRY_SECONDS`.

The seven booleans remain the metric of record and are weighted equally despite differing enormously in difficulty. The judge’s `missing_or_wrong` entries are also counted as a graded leading indicator: fewer is better, with an unattributed total and per-criterion counts only where the judge supplies an attribution. This secondary metric is clearly separate from the 63-point score; it does not silently change the score.

## Acceptance evidence

Verified locally on 2026-09-03:

- `bench score --run-dir /home/bcorfman/bakeoff-data/arm-c/run1` printed total **12**, `canon_consistent` **0**, and `protected_safe` **5**. The full count was `canon_consistent: 0`, `scene_local: 2`, `progressive: 0`, `rich: 1`, `protected_safe: 5`, `exit_motivated: 2`, `rewards_investigation: 2`.
- Arm C `bench prompt` for archived Scene 1A turn 1 produced a system prompt of **2,018 bytes**, byte-for-byte equal to `fixture_armc_system.txt`. Its user prompt matched the archived user prompt, contained all **five** `<beat_detail>` lines, and contained no `<beat>` prose block.
- The archived Arm C run itself contains 106 `missing_or_wrong` entries across nine scenes. `canon_consistent` is false in all 108 archived graded scenes, as expected; this is why the graded leading indicator is included.

The supplied benchmark evidence is also the statistical guardrail: twelve hosted runs had within-arm standard deviation 2.24 on the 63-point scale; the three measured configurations scored means 13.75, 13.00, and 12.25 and were statistically indistinguishable. The four-run empirical minimum detectable effect is therefore reported as **3.87 points**, scaled as `3.87 * sqrt(4/N)` for the N actually used. A result below that noise floor must be described as nothing detectable.

## Package clock finding

The in-process bench calls `RuntimeEngine.turn(input)` without injecting `clock_seconds`. That matches the runtime’s default: `clock_seconds=None` uses the proposal’s `narrative_seconds` (60 for the normal provider contract), while pacing gates themselves use `turn_index - scene_entered_at_turn`.

This was settled by deterministic local evidence against the archived Arm C timing records, not by assuming that seconds and turns were interchangeable: the archive records Scene 1A at relative turns 1, 2, 3, 4 and resets to 0 on entry to 1B at global turn 5; the local engine tests assert the same reset and turn-relative activation, and assert that an injected seconds value cannot bypass the minimum-turn floor. The frontend package-clock tests independently reject `target_seconds` and require `target_turn`. Thus no schedule is invented or injected by the bench.

What was not verified here is a fresh live, stochastic bench traversal against staging; that is intentionally out of scope and would spend both budgets. The archived hosted run proves the observed controller schedule, and the local runtime/clock tests prove the in-process schedule. Exact future model outputs, neuron billing telemetry, and a fresh hosted equivalence run remain unverified.

## Neutral-example live result

On 2026-09-03, the requested neutral run completed 9 script-replicates across
the three declared Scene 1A scripts. Five produced judgeable output with scores
`[0, 1, 1, 1, 1]` (4 total points on the 7-point scene scale), while four
failed with `INVALID_PROPOSAL`; all five successful runs had
`example_leakage: 0`. The no-example control produced three failed
`INVALID_PROPOSAL` replicates, no judgeable output, and no score. Thus the
neutral example did produce valid, judgeable output where removing the example
did not, but it was not failure-free in this batch. No quota-specific 429 was
returned.
