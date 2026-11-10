# Story data redesign — Phase 0 evidence

Status: measured 2026-11-09 on a clean detached worktree at HEAD
`2bb01bbcdb8343f48b371cd64c24abfe25a403d5`. Companion to
[the redesign plan](story-data-redesign-plan.md) and
[the concrete comparison](story-data-comparison.md). Tools are in
[story-data-phase0/](story-data-phase0/); each takes a repo root as its argument.

## Baseline and isolation

- All measurements ran in a detached worktree of HEAD, so the uncommitted edits in
  the main tree (arrival-glance wording in `knowledge.yaml`/`pacing.yaml`, one test,
  three Ringer files, one runbook line) are not in them. No source, test, or
  doc outside `.plans/` was changed.
- Environment: WSL2 Linux, 16 cores, 31 GB, Python 3.12.13, main `.venv` shared via
  symlink. `worldkeeper` imported from the main checkout's editable install (no
  uncommitted changes there). No coverage (`--no-cov`); no model or network calls.
- Story size: 9 scenes, 67 storylets, 97 realizations, 121 claims, 176 knowledge
  facts, 5 incidents, 557 KB across 9 source files (knowledge 175 KB, routes 149 KB).

## Performance baseline

| Measure | Result |
| --- | --- |
| Package load, uncached | 0.36 s median (6 runs 0.355–0.368 s; first run 0.85 s with imports) |
| Package load, cached call | 0.68 ms median (0.66 ms of it is the source fingerprint) |
| Package memory | 2.6 MiB retained, 3.2 MiB peak (tracemalloc) |
| Per-turn knowledge projection (`KnowledgeProjector.project`) | 3.2–6.4 ms across all 9 scenes × 4 inputs; 3 repeats agree within ~5% |
| `world_for` rebuild | 0.42 ms |
| Full suite, clean HEAD, `-n auto`, no coverage | 4346 passed, 36 skipped, 237 s |

Findings the plan did not have:

- **YAML parsing is not the load cost.** It is ~0.05 s of 0.36 s. About 0.34 s is
  validation, almost all of it `_validate_authored_handoffs` → `_delivery_internal_token`
  (97 calls, ~59,000 `re.search` calls with per-call `re.escape`/compile).
  `_validate_narration_term_traps` (projects every scene) is the other ~0.27 s share.
- Per-turn preparation is milliseconds against model latency of seconds. Runtime speed
  is not a reason to change storage. The case for the redesign is ownership and
  coupling (requirements 1, 2, 4), as the plan suspected.
- Proposed budgets (to confirm with Brandon): cold load ≤ 0.5 s, cached ≤ 2 ms,
  projection ≤ 10 ms per turn, retained package ≤ 5 MiB, no slower than today on any.
  They protect against regression; they are not targets to chase.
- A cheap load win (compile the delivery-token patterns once) exists independent of
  the redesign. Not done here.

## Representative edits

Each edit was applied in its own worktree and the full suite run (control: 0 failures).

| Edit | Source files touched | Copies / companion sites | Tests failing |
| --- | --- | --- | --- |
| A. Prose only: reword the marked pursuit passage (`pursuit_1b`) | 1 (`pacing.yaml`, 1 line) | 1 copied constant in `tests/test_1a_witnessed_recovery.py`; 1 Ringer manifest (`step3b`) quotes it | 1 (the test that copies the passage) |
| B. Effect: witnessed recovery stops marking Kristin | 2 (route operation list and claim `establishes`, in different files) + `storylets.md` line 376 still says it sets the mark (prose, not machine-checked) | Fact definitions and `pursuit_1b` consumer unchanged | 1 (the test that pins the mark) |
| C. Shared id: rename `kristin_marked_by_patrol` | 5 story files (world, routes ×2 sites, knowledge ×2 sites, pacing, storylets.md) | 3 test files, 3 Ringer manifests also hold the id | 4 in 2 test files, until the tests are edited too |

Observations:

- A and C failures are all coupling, not behaviour: A fails on a copied string, C on a
  literal id. B's failure is the intended behavioural guard and is correct.
- **B passes the loader with a dead consumer.** After the mark was removed nothing
  produces it, yet `pursuit_1b`'s marked passage still exists and the package loads.
  Only the independent test noticed. A producer/consumer check is a gap in every
  model, as the comparison predicted.
- Elapsed *authoring* time was not measured (it needs the author). Check time per
  full run was 3.6–3.9 min with 16 cores.

## Duplication measured over the whole story

(`dup_audit.py`, `copied_prose.py`; lower bounds, exact-match only.)

- Fact definitions: 121 facts are defined in both `storylet-routes.yaml` and
  `knowledge.yaml`, and all 176 are also listed in `world.yaml`. Of the 121, 97 have
  identical text and **24 differ** — some only in apostrophe style, some real drift
  (e.g. `continuity_initiative_known`, `official_interest_in_michelle_known`).
- Operation lists: 87 of 99 realization-sourced claims have `establishes` identical to
  their route's operation list; 12 are a strict subset. So "claim effects = route
  effects" is the rule but not a universal one, as the comparison cautioned.
  18 of 97 realizations repeat a sibling's operation list (e.g. `SL-2C-D-R1/R2`).
- Sibling claims on one storylet share on average 3.6 of the 9 search/disclosure
  fields.
- Authored passages: 244 passages, 324 sentences ≥ 45 characters; 67 of those
  sentences are copied verbatim into 36 of 375 test files (touching 46 passages).
- `.replace(` appears in 43 test files; 47 write story copies; 72 name story files.

## Ownership map

Live = edited today. Frozen = evidence that must not follow edits.

| Concept | Defined or restated in (live) | Consumers |
| --- | --- | --- |
| Fact | `world.yaml` name list (+ `on_assert` world effects), `storylet-routes.yaml` `new_fact_ids` (+ hand-kept `used_by_*`), `knowledge.yaml` `facts` | pacing, transitions, claims, 41 test files for the busiest fact |
| Storylet | `storylet-routes.yaml` (activation, operations, completion), `storylets.md` (prose + effects in words), `plot.md` anchors | claims, incidents, tests |
| Claim / delivery passage | `knowledge.yaml`; its source effects restate the route's operations | prompt projection, tests, Ringer manifests, browser E2E |
| Pacing event / pass-through passage | `pacing.yaml` | tests copying text; Ringer manifests |
| Transition | `pacing.yaml`; routes `helps_transition_triggers`; `plot.md` | |
| Incident (outcomes, costs, recovery) | `incidents.yaml` pointing into routes, knowledge, pacing; costs also in `handoffs.yaml` | `_validate_incidents`, 7 incident test files |
| Scene text and placements | `plot.md` front matter + beats; `world.yaml` | |
| Handoff / fallback producer | `handoffs.yaml` (can also assert recovery facts) | |

Consumers that read the **raw source files themselves**, not the loader:
`frontend/e2e/authored-spans.js`, `knowledge-available.js`, `roleplay-judge.test.js`
(JavaScript YAML parsers), `scripts/disclosure_matrix.py`,
`scripts/generate_spine_expected_reveals.py`, plus 72 Python tests. A format change
must keep or replace each of these; the loader adapter alone is not enough.

Frozen, not competing definitions: 16 snapshots in `bench/frozen/`,
`tests/fixtures/continuity_initiative_pre_3c_adoption/`, `tests/fixtures/narration_corpus.json`,
987 JSON files under `scripts/ringer/` (experiment history; some use old meanings of ids).
Migration must not rewrite these.

## Second slice: 2C incident (cost and recovery)

`i_2c_rebecca_corridor` joins `SL-2C-D` (4 realizations), `SL-2C-E` (recovery),
`purge_window_2c`, `purge_nudge_2c`, `t_2c_3a`, and two cost facts across 6 files.

- R1 and R2 have **no claims** and identical operation lists; R3/R4 carry the choice
  (transmit → sectors seal; rescue → evidence unsent). Variants without claims are
  mechanical-only, so a reveal block must allow commit-only variants.
- `incidents.yaml` restates each outcome's advantage and cost fact ids, which already
  appear in the realization operations. The incident could derive them from the
  variant it names rather than restate them (`_validate_incidents` already rejects an outcome fact its variant does not assert, so the restatement is a checked copy).
- Cost facts appear in `world.yaml`, `handoffs.yaml`, `incidents.yaml`, routes,
  knowledge; `purge_nudge_2c` waits on the two commitment facts. A dependency view
  is needed to answer "who needs this commitment?".
- The recommended direction held: declarative reveal block with commit-only variants,
  an incident block naming variants, and generated dependency views. The 2C slice adds
  one requirement, that an incident cost/advantage be derived, not restated.

## Readable-view prototype

[reveal-view-prototype.md](story-data-phase0/reveal-view-prototype.md) is generated,
read-only, from the *current* sources by `render_reveal.py` for `SL-1A-E` and
`SL-2C-D`: purpose, window, variants with claims and delivery text, commits, fact
purposes, and each fact's consumers and tests. It proves that the reading view is
derivable today. It is **not** the proposed authoring format and nothing edits it.

**Author verdict, 2026-11-09: not acceptable.** Organized by storylet, it could not
be used to trace a story gap (neither the author nor the drafter could follow what
a situation leads to or what the next scene needs). Superseded for gap-tracing by
[situation-trace-reyes-card.md](story-data-phase0/situation-trace-reyes-card.md),
generated by `render_trace.py` from the current sources only. It is organized
by situation, shows what the story text promises beside what the engine checks,
runs four responses through the real engine, and lists story gaps (section 5). Each gap is a probe that appears only if its check
fails and quotes the sources by file and line. The earlier hand-written review
overlay was removed on 2026-11-09 (author: not helpful; it held opinion, not evidence).
Not yet reviewed by the author.

## Story-gap rules

Moved to [docs/story-gap-guide.md](../docs/story-gap-guide.md) on 2026-11-09 (author-set
rules: custody, co-location, no strand). Status here: unproven until run blind on a
second situation.

## What remains open (needs Brandon)

1. Review the prototype view: can he follow, edit, and trace a consequence in it?
   This is the author gate; no model should be selected before it.
2. ~~Pick the representative pilot scene.~~ Decided 2026-11-09: **1A**, once the
   arrival-glance edits are committed.
3. ~~Confirm the performance budgets above.~~ Accepted as listed, 2026-11-09.
4. Replace the plan's conditional sketch with the chosen model, then pick storage.
