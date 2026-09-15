# Narration prompt bench

`bench` is a development-only, local harness for trying prompt variations against the same Python runtime and Cloudflare narrator used by the app. It writes the exact turn records consumed by the existing JavaScript canon judge; it does not replace the hosted Playwright suite or deploy anything.

## Quick start

Run these commands from the repository root. The CLI loads `.env` if present; it needs `CLOUDFLARE_WORKER_URL`, `CLOUDFLARE_WORKER_TOKEN`, and `OPENAI_API_KEY` only for live commands.

```bash
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench --help
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench prompt \
  --scene 1A \
  --player-input "Search the kitchen and the back door for concrete signs of what happened here."
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench score \
  --run-dir /path/to/a/hosted/run
```

The `prompt` command makes no model request and prints only `{"system": ..., "user": ...}`. `score` is a deliberately stable fixture adapter and prints only the seven equally weighted boolean counts and their total out of 63.

Each turn record also carries delivery telemetry: `cue_fact_id` identifies a staged
missing fact, `cue_text` is that fact delivery's visible cue (or `null`),
`complication_text` is optional complication text (or `null`), and
`handoff_staged` says whether a deadline handoff was staged.

## Commands

`chat` starts a live session at the first scene. Each response is followed by the exact system and user prompt that produced it:

```bash
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench chat --variation bench/variations/example.json
```

`prompt` prints the exact system and user prompt the narrator would receive. It contacts no model and spends nothing, so it is the cheapest way to see what a prompt change actually did. It takes the story's own coordinates - a scene, optionally a beat, optionally the player's action - and needs no variation file:

Bench scenes use a bare arrival state by default, with only that scene's entry fact committed; they do not reconstruct optional earlier storylets. Set the variation's `entry_state` to `"thorough"` to play the story offline to the requested scene with the persona harness's thorough player. This costs no narration requests. Run summaries disclose the scene, `committed_knowledge_count` (the knowledge the narrator is shown at entry), `earned_knowledge_count` (the player-visible knowledge already earned), and `seeded_by` mode (`none` for bare, `thorough` for offline seeding), so safety failures can be read in context.

```bash
# the prompt that establishes scene 1A, as the player enters it
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench prompt --scene 1A --text

# a specific beat of that scene, with the player's action
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench prompt \
  --scene 1A --beat 1A.2 --text \
  --player-input "Search the drawers under her workstation."

# what beats does a scene have?
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench prompt --scene 1A --list-beats
```

The flags:

- `--scene` is a scene id as written in `plot.md` — `1A`, `1B`, `2A`, `3C`. The prompt is assembled as if the player had just entered that scene.
- `--beat` selects which beat to establish, by id (`1A.2`), ordinal (`2`), or anchor slug. Omit it to see the beat the scene's own pacing makes live on entry.

  Naming a beat reproduces the state a player would be in when they reach it: every earlier beat of that scene is **already established**, so its knowledge appears in `SCENE` rather than being offered again under `CONSTRAINTS`, and only the named beat's own reveals remain on offer. A storylet counts as earlier only when every beat it presents is earlier, so one spanning into the named beat stays live. Because beats are shared between storylets, naming a beat activates every storylet that presents it; use `--storylet` for the narrower view.
- `--storylet` shows one storylet alone, by id (`SL-1A-D`). Its earliest beat still fixes what the player has already been through, but no neighbouring storylet's beat details bleed in.
- `--player-input` is the player's typed action. Omit it for the prompt as the scene is entered, with no action yet; the `PLAYER` section is then absent rather than empty.
- `--list-beats` prints the scene's authored beats and its storylets, with the beats each storylet presents, then exits.
- `--text` prints the two prompts as readable text instead of one JSON line.
- `--package` selects the story package directory, defaulting to `data/stories/continuity-initiative`.
- `--variation` is optional and exists for comparing prompt configurations, e.g. `--variation bench/variations/no-output-example.json`. Omit it to see what the engine actually ships.
- `--turn` defaults to `1` and only `1` is accepted, because this command builds a fresh scene entry. A later turn's prompt depends on knowledge committed by earlier turns; reach it with `chat` or `run`.

`describe` resolves a variation, validates its effective story package, and prints its hashes and resolved prompt configuration without making model or network calls:

```bash
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench describe \
  --variation bench/variations/drawer-overlay.json --json
```

`log` reads `bench/results/ledger.jsonl` in append order. `--ledger PATH` selects an alternate JSONL ledger; the default is the tracked path. `--variation NAME` filters by variation name and `--limit N` keeps the newest N matching rows. `--json` prints only the JSON array; without it, a compact table is printed. Failed rows remain visible in both forms.

`compare` pools every `scores` entry from successful, known-scale ledger rows for each named variation and reports each arm's mean and sample standard deviation, the difference, the two-sided Welch t-test, and the minimum detectable effect at the smaller available arm size. `--ledger PATH` selects an alternate ledger:

```bash
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench compare example no-output-example
```

Comparison refuses to mix known-scale rows when their `scenes_scored` values differ, because a 1/7 scene score and a 9/63 traversal score are incommensurable. It also refuses to mix effective story packages when their `package_hash` values differ. Use `--allow-coverage-mismatch` or `--allow-package-mismatch` only when the corresponding confound is intentional; the output then warns that the relevant boundary was not held constant. Failed rows are excluded from these statistics. Rows with missing or null `scenes_scored` have an unknown scale: they remain visible in `log`, but `compare` and `run --baseline` exclude them from n, means, standard deviations, Welch tests, and minimum detectable effects, and print how many were skipped and why. The same scene-coverage guard applies to known-scale `run --baseline` data; an unknown-scale baseline is reported and omitted rather than guessed.

## Results ledger

Every successful `bench run` appends a status-`ok` JSON object to the tracked, append-only `bench/results/ledger.jsonl`. A replicate that cannot produce a judgeable result appends a status-`failed` row instead, with `failure_reason`; this includes repeated `INVALID_PROPOSAL`, quota stops, and a run or judge failure. Failed rows carry the same configuration/provenance and spend fields, have no score, remain visible in `log`, and are excluded from `compare` statistics. Existing lines are never rewritten or reordered. The row records:

```json
{
  "timestamp": "2026-09-03T18:20:00Z",
  "variation_name": "example",
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
  "entry_state": "bare",
  "escalation_judge": true,
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

`escalation_judge` is an optional boolean and defaults to `false`. When true,
the bench makes a separate judge call for each successful replicate. It reports
these three criteria as `yes`, `no`, or `not_applicable`:

Runs are always judged against the canon of the package they ran.

- `cue_points_to_missing_thread`
- `complication_creates_pressure_without_unearned_knowledge`
- `no_pre_reveal_disclosure`

The escalation judge is separate from the seven-criterion metric of record. Its
counts appear in an `escalation` block in `summary.json` and the ledger row:

```json
"escalation": {
  "cue_points_to_missing_thread": {"yes": 1, "no": 0, "not_applicable": 0},
  "complication_creates_pressure_without_unearned_knowledge": {"yes": 0, "no": 0, "not_applicable": 1},
  "no_pre_reveal_disclosure": {"yes": 1, "no": 0, "not_applicable": 0},
  "judge_calls": 1
}
```

`continuity_judge` is an optional boolean and defaults to `false`. When true,
the bench makes one extra judge call per successful replicate and judges every
turn. It checks `contradicts_stated_fact` (the narration conflicts with known
facts), `protagonist_acts_beyond_command` (the player character does more than
commanded), and `restarts_scene` (the scene or its opening is started again).
For each criterion, `yes` means the defect is present. Results appear as a
`continuity` block in `summary.json` and the ledger row with yes/no counts,
`turns_judged`, and `judge_calls`. See
`bench/variations/continuity-1a.json` for the `phone-bag-door` Scene 1A script.

`beat_delivery` is `details` for beat noun phrases or `prose` for the authored beat paragraph. `rules` replaces the normal rules block, while the runtime still supplies turn-specific candidate and handoff rules. `include_output_example: false` omits the block; `true` or omission uses today's default. A string `output_example` supplies the block contents verbatim and implies inclusion, even if the boolean is false. Non-string values are rejected. `story_package` may be any package path accepted by `load_story_package`; the live judge uses the same scene-local canon shape for arbitrary packages, while the archived hosted fixtures remain the continuity-initiative baseline.

`entry_state` is optional and accepts `"bare"` (the default) or `"thorough"`. Bare starts directly at the requested scene with its entry fact. Thorough uses the persona harness's deterministic thorough player to reach that scene before live narration begins; the offline seeding makes no narration request. Each run's `entry_state` record includes `committed_knowledge_count` (the knowledge the narrator is shown at entry), `earned_knowledge_count` (the player-visible knowledge already earned), and `seeded_by`: `none` for bare and `thorough` for seeded runs.

## Item facts

An `item_facts` variation option tracks plain facts about named things:

```json
"item_facts": {
  "mode": "single_call",
  "seed": {
    "the lantern": {"where": "on the table", "condition": ["lit"]},
    "the gate": {"where": "at the garden path", "condition": ["closed"]}
  }
}
```

Each thing has one `where` phrase and zero to two `condition` phrases. The provider adds a `THINGS` section to every opening and turn prompt, in seed order. Each line has the shape `- <name>. Where: <where>. Condition: <c1, c2>.`; an empty condition list is rendered as `Condition: none.` `single_call` asks the narrator to return `item_facts` beside its normal proposal. `second_call` makes one extra request after each accepted narration to read the command and finished story. Opening facts are ignored because the opening establishes the scene.

Replies list only the things the story changed. A valid entry replaces that thing's `where` and `condition` entirely. Omitted things stay unchanged with no issue. Malformed entries keep their previous facts, unknown names are dropped, and more than two conditions are trimmed to the first two. Phrases are trimmed to 80 characters for `where` and 40 characters for each condition. These repairs are listed in `item_facts_issues`. Rejected turns do not change facts. Turn records contain `item_facts_before`, `item_facts_after`, `item_facts_raw`, `item_facts_issues`, and `item_facts_source`; the replicate also contains `item_facts_final`.

Set `seed_from_package` to `true` to seed placements and parseable setting facts from the story package; an optional hand-written `seed` is appended after those things. Seed problems are recorded as `item_facts_seed_issues`. `continue_to` can play a second scene with its own `scene`, `fixed_turns`, and script name. Its facts carry over, package-seeded things are added, and no second opening is narrated. Accepted turns include `scene_id`; cross-scene runs include `scene_transitions`.

The trial arms are `item-facts-single.json`, `item-facts-single-minimal.json`, `item-facts-second.json`, `item-facts-package-two-scene.json`, and `item-facts-package-long.json`.

## Fact-tracking judge

Set `fact_tracking_judge` to `true` to judge each turn's `item_facts_before`, narration, and `item_facts_after`. The judge checks whether facts after the turn are correct, whether a narrated change was missed, whether a change was invented, whether narration conflicts with the facts it received, and whether a true condition was dropped. It also records shown changes by `command` or `narrator` cause.

The `fact_tracking` block in `summary.json` and the ledger contains yes/no counts for those five checks, `changes_by_cause`, `turns_judged`, and `judge_calls`. The judge is opt-in and adds its calls to spend.

`fixed_turns` is an optional positive integer. It plays exactly that many turns without requiring the scene to be left. A turn the runtime rejects is recorded in `rejected_turns` with its turn number, input, rejection code, and reason, then play continues as it would for a player; a narration provider outage still fails the replicate. Accepted turns carry `turn_number`, and judges see only accepted turns. `continuity-1a.json` uses 12 fixed turns.

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

The shipped example configurations are:

- `variations/example.json`: the shipped configuration with beat details and the default output example, plus a Scene 1A script. Use it as the starting point for a new arm.
- `variations/no-output-example.json`: the same configuration with the response example omitted. Removing it entirely has been observed to break response validity: the narrator repeatedly returned `INVALID_PROPOSAL` and produced no score.
- `variations/drawer-overlay.json`: a package override, showing how a variation edits authored text in a temporary effective copy.

For candidate-selection work, `variations/candidate-selection-baseline.json`
replays four authored Scene 1A actions. Run it
with four replicates, then report against `all-turn-records.json`; that file
keeps the per-turn offered and selected IDs even when a scene fails before the
judgeable `turn-records.json` output is written. The committed baseline report
keeps the same redacted per-turn fields without model narration:

```bash
uv run python -m bench run --variation bench/variations/candidate-selection-baseline.json \
  --scene 1A --script candidate-selection-repro --replicates 4 \
  --out /tmp/candidate-selection-baseline --confirm
uv run python -m bench.candidate_selection_report \
  --in /tmp/candidate-selection-baseline/all-turn-records.json \
  --out-json /tmp/candidate-selection-baseline/report.json \
  --out-md /tmp/candidate-selection-baseline/report.md
```

The leakage metric is calculated against the resolved example actually sent in the turn system prompt, so it works for arbitrary custom examples rather than only the shipped drawer text.

For the authored reveal handoff, use `variations/authored-handoff-phase1.json`.
Each turn record adds `authored_handoff_candidate_id` as bench-only telemetry;
it is not part of the narrator or player API. Verify the exact recording action
first, then run the established Scene 1A script and an unrelated Scene 1B run.
New turn records omit the retired `preselected_knowledge_id` field because no
runtime path can set it. Existing records under `bench/results/` are historical
and remain unchanged.

For example, run the two prompt-only experiment arms, then run one focused live replicate of each and compare their real ledger rows:

```bash
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench describe --variation bench/variations/example.json --json
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench describe --variation bench/variations/no-output-example.json --json
set -a && . /home/bcorfman/dev/freytag-forge/.env && set +a
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench run --variation bench/variations/example.json --scene 1A --replicates 1 --script e2e --out /tmp/bench-example --confirm
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench run --variation bench/variations/no-output-example.json --scene 1A --replicates 1 --script e2e --out /tmp/bench-no-example --confirm
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench compare example no-output-example
```

## Cost and safety

Live benchmark runs go through Ringer using `bench/manifests/phase7-live-bench.json`:

```bash
cd /home/bcorfman/dev/ringer && ./ringer.py run /home/bcorfman/dev/freytag-forge/bench/manifests/phase7-live-bench.json
```

The task declares `full_access` because a live run needs network access and must write `bench/results/`, which the default worker sandbox forbids. `bench/checks/no_source_drift.py` replaces that sandbox by failing the task if any tracked file outside `bench/results/` changed. `bench/checks/live_bench.py` judges the produced artifacts rather than trusting the worker's own summary.

There are two independent budgets:

- Cloudflare Workers AI: the observed planning rate is about 330 neurons per 30 narration requests, or about 11 neurons per request. A full 30-turn traversal is therefore roughly 330 neurons. A nine-scene, four-replicate comparison is roughly 1,320 neurons, before any recovery requests; it fits comfortably below the 10,000-neuron daily free allocation, but fewer than eight such comparisons should be planned in one UTC day.
- OpenAI judge: one call per reached scene. A one-scene bench run makes exactly one call per completed replicate; a nine-scene, four-replicate comparison makes 36 calls.

Before a live run, the CLI prints projected neurons to stderr. Above `BENCH_CONFIRM_THRESHOLD_NEURONS` (default 500), it requires `--confirm` or an interactive yes. The estimate includes the declared scripts and one opening request per replicate. Actual worker neuron usage is not returned by the Worker, so `summary.json` reports exact narration request/turn counts and a clearly labeled request-based neuron estimate, plus exact judge-call count. It never claims that estimate is provider billing telemetry.

The Worker’s `429` quota response is distinguished by `X-Narration-Error-Code: AI_QUOTA_EXCEEDED` and stops the batch with completed/planned counts; it is not retried, and the interrupted replicate is recorded as failed. The application limiter’s `{"detail":"rate limit exceeded"}` is classified as `RATE_LIMITED` and retried using `BENCH_RATE_LIMIT_RETRIES` and `BENCH_RATE_LIMIT_RETRY_SECONDS`.

The seven booleans remain the metric of record and are weighted equally despite differing enormously in difficulty. The judge’s `missing_or_wrong` entries are also counted as a graded leading indicator: fewer is better, with an unattributed total and per-criterion counts only where the judge supplies an attribution. This secondary metric is clearly separate from the 63-point score; it does not silently change the score.

## Package clock finding

The in-process bench calls `RuntimeEngine.turn(input)` without injecting `clock_seconds`. That matches the runtime’s default: `clock_seconds=None` uses the proposal’s `narrative_seconds` (60 for the normal provider contract), while pacing gates themselves use `turn_index - scene_entered_at_turn`.

This was settled by deterministic local evidence against the archived Arm C timing records, not by assuming that seconds and turns were interchangeable: the archive records Scene 1A at relative turns 1, 2, 3, 4 and resets to 0 on entry to 1B at global turn 5; the local engine tests assert the same reset and turn-relative activation, and assert that an injected seconds value cannot bypass the minimum-turn floor. The frontend package-clock tests independently reject `target_seconds` and require `target_turn`. Thus no schedule is invented or injected by the bench.

What was not verified here is a fresh live, stochastic bench traversal against staging; that is intentionally out of scope and would spend both budgets. The archived hosted run proves the observed controller schedule, and the local runtime/clock tests prove the in-process schedule. Exact future model outputs, neuron billing telemetry, and a fresh hosted equivalence run remain unverified.
