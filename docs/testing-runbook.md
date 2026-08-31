# Testing runbook

## Opening narration location-name leakage

**Purpose:** Determine whether a location label can appear in the generated
opening continuation, rather than in the authored opening paragraph.

**Setup / seed:** Load the `continuity_initiative` package; Scene 1A uses the
`mcgehee_home` location entity.

**Safe actions:** Read the package data, transport payload construction, and
transport-payload tests only.

**Destructive or external actions:** None.

**Steps:**

1. Inspect `world.yaml` for the location entity's human-facing `name`.
2. Inspect `CloudflareTurnProvider._scene_entry` and the opening payload test.
3. Contrast `_scene_entry` with `_scene_setting`, which is used for ordinary
   player turns.

**Verify:**

```bash
rg -n -C 4 'name: McGehee home|"location": location.name|scene_setting' \
  data/stories/continuity-initiative/world.yaml storygame/runtime/cloudflare.py
```

Expected: the opening payload assigns `location.name` to `scene_entry.location`;
ordinary turns send only the authored `entry_text` in `scene_setting`.

**Cleanup:** None.

**Notes:** Verified 2026-08-29. `McGehee home` is the package location entity's
display name, not a Markdown tag name; it can inform the model's generated
opening continuation. “Eerie silence” is not verbatim package prose: the
opening's `knowledge_context.player.scene_frame` supplies “The house is quiet,”
so it is a model embellishment of the validated Scene 1A frame rather than a
location label or tag. The opening-payload test derives the expected location
display name from the package rather than pinning `McGehee home`; verified on
2026-08-29 with `TMPDIR=/tmp uv run pytest -q` (123 passed; 90.97% coverage).

## Scene 1A reveal-to-transition continuity — fixed 2026-08-30

**Purpose:** Record why a move to Scene 1B could follow a drawer search without
the player being shown the memory-card files or any reason to visit the park,
and what now prevents it.

**Setup / seed:** A Scene 1A session, investigating Michelle's workstation
through free-text drawer searches until a reveal is selected.

**Safe actions:** Inspect package routes, knowledge statements, and the
resolver/engine code. The regression is covered by the local suite, so no
hosted session is needed to exercise it.

**Destructive or external actions:** None.

**Diagnosis (2026-08-30, from a player transcript).** Two independent defects
produced one symptom. `SelectedRevealResolver.resolve` proved only that the
selected knowledge ID appeared in some segment's `grounding_ids`; it never
compared the segment prose with the knowledge statement, so a model could
select the memory-card reveal, narrate only its broadcast-warning half, and
still commit `michelle_lead_actionable`. Separately, `k_sl_1a_b_r1` asserted
that fact while its own statement named no lead and no place, so even a
faithful narration of it told the player nothing about where to go. The
reported transcript was a correct rendering of a defective statement.

**Fix.** Knowledge definitions now carry authored `must_convey` synonym groups,
and both commit paths check the narration against them before anything is
applied: `SelectedRevealResolver.resolve` raises before validation and before
`apply_proposal`, and `CloudflareTurnProvider._parse_eligible_proposal` mirrors
the rule so a miss spends the transport's one guided recovery instead of the
player's turn. The loader refuses to load a package in which a selectable,
trigger-establishing reveal declares no groups. `k_sl_1a_b_r1` was rewritten to
name the memory card, the damaged recording, and the dead drop at the park
bench, and `SL-1A-B-R1`'s `dramatic_intent` was brought into agreement.

The investigation behind the fix found three further defects that would have
made the obvious repair fail elsewhere; all are now addressed. Bridge events
activated on a full conjunction of facts, so a player who explored differently
could be permanently stuck — they now support a threshold rule. Pacing was
measured in absolute story-seconds against a global clock, so an ordinary player
entered every scene from 2B onward already overdue — it is now counted in turns
since scene entry. And a player short of a scene's exit had no way forward — a
declared `FactDelivery` per player-safe fact now lets the runtime hint first and
then stage an in-world handoff, which is committed atomically with its costs and
the transition.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q
npm --prefix frontend test
```

Expected on 2026-08-30: 177 passed, 91.29% coverage; frontend 30 passed, 0
failed. `tests/test_must_convey.py` covers the matcher,
`tests/test_scene_progression_phase4.py` holds the reported transcript's exact
shape — select `k_sl_1a_b_r1`, ground it, narrate only the broadcast-warning
half, and assert nothing commits and the scene does not move — and
`tests/test_pacing_handoff.py` covers the hint, the handoff, the guided
recovery, and the authored fallback.

**Cleanup:** None.

**Notes:** This entry records local evidence only. Nothing here has been
re-run against a deployment since the fix landed, and the hosted observations
recorded elsewhere in this runbook predate it. Replaying the reported
transcript against staging — searching the drawer in 1A and confirming the
narration names the memory card *and* the bench before the park paragraph, and
that a partial narration is retried rather than silently advancing — is still
outstanding.

## Hosted canon judge — verified state (2026-08-31)

**Purpose:** Record what a full hosted playthrough now proves, and what it does
not, so the next session does not re-derive it.

**Setup / seed:** Staging on the merged SHA, verified through
`/api/v1/health` before running. `.env` supplies `E2E_API_BASE_URL`,
`OPENAI_API_KEY` and the worker credentials.

**Safe actions:** Read-only against staging, plus the billed judge calls named
below.

**Destructive or external actions:** The `@llm-canon` run spends TWO independent
budgets, and only the first is obvious from the command.

- **OpenAI**, one judge call per reached scene — nine on a full traversal.
- **Cloudflare Workers AI neurons**, one narration call per turn, plus another
  for every turn that spends its recovery. This is the budget that runs out
  first in practice.

The Workers AI free allocation is 10,000 neurons per day and **resets at 00:00
UTC** — 8:00 PM Eastern during daylight time, 7:00 PM Eastern in winter.

Exhausting it does not look like a quota problem from the outside. The turn
endpoint answers `HTTP 429` with `{"detail": "narration service is at capacity"}`
and the header `X-Narration-Error-Code: AI_QUOTA_EXCEEDED`. Check that header
before assuming a request-rate limit: the app's own
`FREYTAG_RATE_LIMIT_PER_MINUTE` limiter returns `{"detail": "rate limit
exceeded"}` instead, and `/api/v1/health` keeps answering either way, so a green
health check proves nothing here.

On 2026-08-31 a day of debugging exhausted the allocation, because narration was
occasionally rambling past 4,000 characters and output costs 34,868 neurons per
million tokens against 4,119 for input — a rambling turn ran roughly 50 to 70
neurons where a well-behaved one costs about 11. With the 3,600-character budget
now in the turn instruction, a full 30-turn playthrough is around 330 neurons, so
the free allocation covers roughly thirty of them a day.

**Steps:**

```bash
source .env && cd frontend && E2E_TURN_TIMEOUT_MS=90000 npm run test:e2e -- --grep @spine
source .env && cd frontend && E2E_PACKAGE_CLOCK=1 E2E_TURN_TIMEOUT_MS=90000 npm run test:e2e -- --grep @llm-canon
```

`E2E_TURN_TIMEOUT_MS=90000` is required. The default is 30 seconds, and a turn
that spends its recovery makes two model calls, which legitimately exceeds it.

**Verify:** `@spine` passed in 1.8 minutes. `@llm-canon` traversed all nine
scenes in order — 1A through 3C — and judged every one.

**Observed 2026-08-31.** Every scene FAILS the canon judge on narration
quality. Passing counts across the nine judged scenes:

| Criterion | Passing |
| --- | --- |
| `protected_safe` | 9/9 |
| `exit_motivated` | 3/9 |
| `rewards_investigation` | 2/9 |
| `scene_local` | 1/9 |
| `progressive` | 1/9 |
| `canon_consistent` | 0/9 |
| `rich` | 0/9 |

`protected_safe` passing on every scene is the load-bearing result: no scene
leaked JANUS, Brandon's role, or any phase-two secret. The state machine holds.
The failures are prose, not plumbing.

The judge's Scene 1A criticisms are representative and actionable: the canon
calls for concrete physical evidence — the phone on the kitchen floor, the
missing laptop and work bag, the overturned chair, the forced back door, the
carved KMS drawer — and the narration only glances at it; an apt second search
dead-ended on an invented empty compartment when the memory card was
canonically available; and one turn collapsed the card discovery, the Continuity
Initiative exposition, the park-bench lead and the scene exit into a single
abrupt summary.

**Delivery telemetry from the same session's `@spine` run**, written to
`artifacts/e2e-spine.json`:

```
total_turns 37 | turns_with_misses 7 | recovery_turns 17 | fallback_turns 6
```

Six fallback turns means six turns where a player read authored fallback prose
instead of narration shaped to what they did. That is the delivery system's
health metric, and it is the number to watch when widening `must_convey` groups.
The report also carries a per-fact miss tally naming which reveals missed.

**Cleanup:** None.

**Notes.** Measured narration runs about 350 characters, roughly 60 words,
against a plan that assumed about 100 words per turn. The model is bimodal in
length as well as in behaviour: usually far thinner than the game wants, and
occasionally rambling past 4,000 characters, which is what the 3,600-character
budget in the turn instruction now bounds. There is a ceiling on narration
length and no floor, and the judge's `rich` criterion fails on all nine scenes.
That is the most likely single cause of the quality verdicts and the first thing
to try.

## Full-journey acceptance — verified state (2026-08-29)

**Purpose:** Record what the hosted canon playthrough proves and what it does
not, so the next session does not re-derive it.

**Deterministic evidence (no model calls, runs in CI):**

```bash
TMPDIR=/tmp uv run pytest -q
```

- `tests/test_canon_journey.py` drives two complete 1A→3C playthroughs with a
  scripted provider — one on the package clock, one at the default 60-second
  cadence — and asserts `resolution_complete`, every pacing event, and the
  30-minute budget. The budget was raised from 20 minutes on 2026-08-30 when
  pacing became turn-based: the per-scene handoff allowance sums to 30 turns,
  which at 60 story-seconds per turn is exactly 1800 seconds.
- `test_no_single_reveal_can_strand_a_scene_exit` audits every transition
  against every realization. It exists because playing Michelle's damaged
  recording before finding her memory card used to consume Scene 1A's only
  source of `michelle_lead_actionable`, leaving the opening scene unwinnable.
- `test_request_size_stays_flat_as_the_story_accumulates` caps the narration
  request, which grew to 44 KB by Scene 3C and timed out Act 3 turns.
- `test_a_reveal_the_narration_never_delivers_cannot_commit_or_move_the_scene`
  holds the rule that a selected reveal must ground the segment that tells it.
  A play session selected Scene 1A's memory-card reveal while narrating only
  "a faint scratch on the floor and a few loose screws": the fact committed
  silently, the canonical bridge fired, and Kristin arrived at the park bench
  the player had never been told about. The scripted providers in
  `tests/test_canon_journey.py` now ground their selections for the same
  reason, so the canonical journey exercises the rule on every turn.

**Hosted evidence (billed, staging):**

```bash
source .env && cd frontend && E2E_PACKAGE_CLOCK=1 npm run test:e2e -- --grep @llm-canon
```

Observed on 2026-08-29 against staging: the playthrough walks all nine scenes
in authored order, fires all four pacing events in their own scenes, commits a
reveal on close to every turn, and reaches the independent judge. Runs vary
between roughly 22 and 28 turns.

**That observation was superseded on 2026-08-31 by the run recorded below.** It
was taken before pacing became turn-based, so its turn counts were measured
against the old absolute-seconds windows and the old 20-minute budget.

**Known open items:**

- The canon judge fails every scene on narration quality. Its recurring
  criticisms are thin sensory establishment and narration that does not answer
  the player's specific action; it separately confirms on each scene that
  protected knowledge is correctly withheld and that beat ordering is right.
  An ordinary turn now carries the scene's authored entry paragraph, but not
  its beat prose, because Scene 2B's first beat and the `JANUS archive`
  location name both carry knowledge the player has not yet earned. Widening
  that further needs an authoring decision about the trade.
- Staging intermittently returns HTTP 503 for a single turn, which ends a run.
  The transport already retries once on a connection failure; a repeat means
  the Worker was unavailable for both attempts. Rerun before investigating.
- `SL-3C-D` and `SL-3C-E` are unreachable: the canonical resolution events set
  every fact they establish on the turn the player enters 3C, so the projector
  always filters them as already established. The game completes correctly
  without them.
- The canon judge used to file a departure turn under the scene it arrived in,
  so no scene was ever graded on the turn that left it. Turns are now recorded
  against the scene the player acted in, and only the appended authored
  `entry_text` opens the scene it entered. The judge grades `exit_motivated`
  and `rewards_investigation` alongside its existing criteria. Both are new and
  have not yet been observed against staging.

## Phase 3 provider knowledge-context cutover

**Purpose:** Verify the Worker receives only fact-derived player and speaker
projections, and that its sole reveal authority is one eligible knowledge ID;
the runtime must derive the source and fact effects atomically.

**Setup / seed:**

- Python 3.12 dependencies installed with `uv sync --group dev`.
- Run from the repository root; pytest temporary files belong under `/tmp`.

**Safe actions:** Local transport tests intercept the Worker request; no
network request is made.

**Destructive or external actions:** The optional browser probe creates a
disposable staging session and may make billed model calls.

**Steps:**

1. Run the full suite after changing the provider contract or proposal schema.
2. After the implementation revision deploys to staging, run the persistent
   knowledge-timeline probe and retain its redacted payload-ID artifact.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q
source .env && cd frontend && E2E_KNOWLEDGE_TIMELINE=1 npm run test:e2e -- --grep @knowledge-timeline
```

Expected: the intercepted request excludes plot prose, route prose, source IDs,
fact effects, future JANUS terms, raw narrative history, and unrevealed warning
text; after the recording route becomes eligible it includes only that local
candidate. The deterministic API fixture proves valid selection commits the
authored damaged-warning route before grounded narration is returned, while
future, duplicate, and unavailable IDs leave facts, events, records, and the
saved session unchanged. The staged probe retains the same reveal timeline.

**Cleanup:** Delete ignored `artifacts/e2e-knowledge-timeline.{json,md}` when
the staged evidence is no longer needed.

**Notes:** Last verified locally on 2026-08-27: `TMPDIR=/tmp uv run pytest -q`
passed with 92 tests after the resolver cutover. The transport fixture captures
the payload and proves the opening has no candidate, while an activated
`SL-1A-B` drawer turn exposes only the damaged-recording candidate, not its
source or effects. `test_phase3_api_timeline_resolves_only_an_eligible_recording_selection`
records the API-level selection, route effect, rejected future ID, and SQLite
snapshot check. Record the deployed SHA and observed browser result here; do
not treat this undeployed local run as staging evidence.

The first staging probe exposed a migration-era E2E assumption: a valid accepted
`action` segment was rejected because the helper looked only for `narration`.
The timeline harness now accepts text from all supported structured segment
kinds; rerun the staged command after this revision deploys.

An August 27 staging trace showed a provider selecting a knowledge ID outside
the candidate IDs supplied for the third timeline turn. The actual cause was
that the package exposed `SL-1A-B` on the first turn and `SL-1A-C` on the
second, consuming the recording route before its intended input. The routes now
sequence physical evidence (0–60s), the recording (at 120s), then patrol
pressure after the warning; Scene 1A remains eligible through the fourth
60-second test turn. The Cloudflare transport also performs its single allowed
recovery for an out-of-candidate provider selection, and fired storylet
realizations are removed from later candidate projections. The deterministic
`test_scene_1a_route_windows_preserve_the_recording_timeline` locks this
availability sequence. Run the full suite, then rerun the staged timeline only
after the implementation revision deploys.

The browser probe keeps its broad free-text investigation intent—Sarah's
research or a damaged recording. Its assertion accepts either authored
`SL-1A-B` outcome, while the preceding turns still prove the warning cannot
appear early.


A later staging attempt reported a browser CORS failure. Direct checks of the
current staging revision's `OPTIONS /api/v1/turn` and cross-origin invalid
`POST /api/v1/turn` both returned `Access-Control-Allow-Origin: *`; rerun the
probe before changing CORS configuration, and record the deployed SHA if it
recurs.

## Phase 2 fact-derived shadow projection

**Purpose:** Verify the legacy provider context remains unchanged while the
runtime and Cloudflare adapter build an ID-observable, fact-only shadow view.

**Setup / seed:**

- Python 3.12 dependencies installed with `uv sync --group dev`.
- Run from the repository root; pytest temporary files belong under `/tmp`.

**Safe actions:** Local deterministic tests use the checked-in package and a
temporary SQLite snapshot only.

**Destructive or external actions:** The staged browser probe creates a
disposable session and may make billed model calls; do not run it before the
implementation revision is deployed.

**Steps:**

1. Run the full suite after changing projection, state, provider-shadow, or
   persistence code.
2. After staging deploys, run the persistent knowledge-timeline probe and keep
   its redacted artifact.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q
source .env && cd frontend && E2E_KNOWLEDGE_TIMELINE=1 npm run test:e2e -- --grep @knowledge-timeline
```

Expected: the deterministic fixture keeps Sarah's warning out of committed
knowledge until its exact recording route commits, keeps patrol knowledge out
until patrol-route activation, excludes future input and transcript prose, and
reproduces the same shadow projection after save/load. The browser probe must
retain the same timeline evidence without treating its judge as runtime
authority.

**Cleanup:** Delete ignored `artifacts/e2e-knowledge-timeline.{json,md}` when
the staged evidence is no longer needed.

**Notes:** Last verified locally on 2026-08-27: `uv run ruff check --fix .`,
`uv run ruff format .`, and `TMPDIR=/tmp uv run pytest -q` passed with 95 tests
and 91.26% coverage. The staging probe is pending deployment; it is not
evidence for this local revision.

## Phase 1 knowledge-catalog migration and Scene 1A timeline

**Purpose:** Verify the declarative catalog covers every Continuity Initiative
fact and executable realization, rejects malformed ownership/visibility, and
keeps the Scene 1A opening and unrecovered warning distinct.

**Setup / seed:**

- Python 3.12 dependencies installed with `uv sync --group dev`.
- Run from the repository root; pytest temporary files belong under `/tmp`.

**Safe actions:**

- The tests load the checked-in package and copy it into pytest temporary
  directories before corrupting fixtures.

**Destructive or external actions:**

- None for the deterministic suite. The optional browser command creates a
  disposable staging session and may make billed model calls.

**Steps:**

1. Run the focused package and Phase 1 persistence tests while editing the
   catalog, loader, or save compatibility.
2. Run the full suite after formatting.
3. After the implementation revision is deployed to staging, run the opt-in
   browser timeline probe; retain its redacted artifact.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q
source .env && cd frontend && E2E_KNOWLEDGE_TIMELINE=1 npm run test:e2e -- --grep @knowledge-timeline
```

Expected: deterministic tests prove that opening entry knowledge is committed,
the warning is absent until its source is selected, and malformed catalogs fail
closed. The staged probe records each turn and rejects early warning/JANUS,
unearned patrol tape, and generic repeated follow-up narration.

**Cleanup:** Delete ignored `artifacts/e2e-knowledge-timeline.{json,md}` when
the evidence is no longer needed.

**Notes:** The browser probe is intentionally not run against an undeployed
local schema change. Record its observed revision and outcome here after the
staging run; this regression contract carries through Phases 2–5.

Last verified locally: 2026-08-27 — `uv run ruff check --fix .`, `uv run ruff
format .`, and `TMPDIR=/tmp uv run pytest -q` passed with 89 tests and 90.86%
coverage. The staged browser command remains pending deployment of this
revision; do not treat local schema evidence as a staging result.

## Declarative knowledge package loading

**Purpose:** Verify the Phase 0 knowledge catalog, safe scene frames, immutable
indexes, and fail-closed source/effect validation without changing provider
context behavior.

**Setup / seed:**

- Python 3.12 dependencies installed with `uv sync --group dev`.
- Run from the repository root; use `/tmp` for pytest temporary files.

**Safe actions:**

- Tests copy the Continuity Initiative package into pytest temporary paths.

**Destructive or external actions:**

- None.

**Steps:**

1. Run the full Python suite after editing knowledge models, loader validation,
   or `knowledge.yaml`.
2. Apply Ruff autofix and formatting, then rerun the full suite.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q
```

Expected: all tests pass with repository coverage at or above 90%.

**Cleanup:** None; pytest temporary files are under `/tmp`.

**Notes:** A focused `tests/test_markdown_story_package.py` run passed all 16
tests on 2026-08-27 but exited nonzero solely because the global 90% coverage
gate measured 31.67%; use the full suite for a passing verification.

Verified 2026-08-29: `TMPDIR=/tmp uv run pytest -q --no-cov
tests/test_markdown_story_package.py::test_a_scene_without_a_first_beat_fails_to_load`
passed. The fixture removes the `### Scene 1A.1` heading by stable beat ID so
renaming the authored beat title does not invalidate the test setup. After
Ruff check and formatting passed, `TMPDIR=/tmp uv run pytest -q --no-cov -m
authoring_quality` passed 33 tests with 90 deselected.

After merged SHA `fb49aea9a7bcae79c20c53bb6f13f7fc72b647b4` completed the
staging deployment, the opt-in browser gate passed: `source .env && cd
frontend && E2E_KNOWLEDGE_TIMELINE=1 npm run test:e2e -- --grep
@knowledge-timeline` ran one Chromium test successfully in 10.3 seconds on
2026-08-27. It wrote ignored local evidence to
`artifacts/e2e-knowledge-timeline.{json,md}`. This remote run creates a staging
session and may make billed model calls; retain the artifacts while evaluating
the phase and delete them when no longer needed. Chrome DevTools MCP was not
available in the verification session, so Playwright supplied the browser
evidence.

## Route-backed continuity-initiative progression

**Purpose:** Verify that the revised five-file story package loads with executable storylet routes, activates only eligible scene-local guidance, and rejects durable effects that are not route-authorized.

**Setup / seed:**

- Python 3.12 dependencies installed with `uv sync --group dev`.
- Run from the repository root with `/tmp` as pytest's temporary directory.

**Safe actions:**

- Tests use copied package fixtures and local SQLite temporary files only.

**Destructive or external actions:**

- None.

**Steps:**

1. Run the Markdown-package, context, and progression tests after changing the story package or route validator.
2. Run the full suite before handoff because the coverage gate is repository-wide.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q
```

Expected: all tests pass with the project coverage gate at or above 90%.

**Cleanup:** None; pytest temporary files are under `/tmp`.

**Notes:** Durable LLM effects must be submitted as an active `SL-*` event with a route realization ID and the exact reviewed operations. `entry_text` opens the scene verbatim as the opening's first segment; the provider only continues it from the scene's first authored beat, and neither is the full scene prose.

Last verified: 2026-08-26 — `TMPDIR=/tmp uv run pytest -q` completed with 58 passing tests and 90.17% coverage; Ruff autofix and formatting also passed.

Verified locally on 2026-08-28: `TMPDIR=/tmp uv run pytest -q` passed 98 tests
with 90.56% coverage after removing a withdrawn Scene 1A.1 opening-beat test.
`uv run ruff check --fix .` remains blocked by pre-existing E501 lines in
`tests/test_knowledge_projection.py:69` and
`tests/test_scene_progression_phase4.py:24`; neither unrelated file was changed.

## Frontend structured-turn rendering unit tests

**Purpose:** Verify that the browser renderer preserves accepted structured
narration, speech, and action blocks, while retaining the legacy `lines`
fallback for non-interaction turns.

**Setup / seed:**

- Node.js and the frontend dependencies installed with `npm ci` or `npm install`
  from `frontend/`.
- No network, credentials, seed data, or deployed service required.

**Safe actions:**

- Running the Node unit tests is read-only apart from normal local test caches.

**Destructive or external actions:**

- None.

**Steps:**

1. Change into `frontend/`.
2. Run the focused unit-test command.

**Verify:**

```bash
cd frontend && npm test
```

Expected: Node reports three passing `turn_rendering` tests and exits with code
0.

Last verified: 2026-08-26 — 3 passing tests, exit code 0.

**Cleanup:** None.

**Notes:** This is a renderer-only smoke test. It does not call FastAPI,
Cloudflare, or Workers AI.

## Fast unit and component feedback

**Purpose:** Verify the deterministic unit and component contracts used by the
CI fast-feedback job without invoking the repository-wide coverage gate.

**Setup / seed:**

- Python 3.12 dependencies installed with `uv sync --group dev`.
- Run from the repository root with pytest temporary files under `/tmp`.

**Safe actions:** Tests use local fixtures and injected transport responses.

**Destructive or external actions:** None; no live provider credentials are
required.

**Steps:**

1. Run the marker-selected fast-feedback suite from the repository root.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q --no-cov -m "unit or component"
```

Expected: all selected tests pass; quality-suite collection counts remain
informational.

**Cleanup:** None; pytest temporary files are under `/tmp`.

**Notes:** Last verified 2026-08-29 — 65 passed and 39 deselected. This suite
includes the Cloudflare opening-prompt transport contract.

## Full Markdown scene-runtime suite

**Purpose:** Verify package loading, context scoping, fact-backed progression,
game-break persistence, FastAPI behavior, Cloudflare transport contracts, and
concept-level scene-roleplay checks.

**Setup / seed:**

- Python 3.12 dependencies installed with `uv sync --group dev`.
- Use `/tmp` for pytest temporary files in this WSL environment.

**Safe actions:**

- The suite uses temporary SQLite files and local package fixtures only.

**Destructive or external actions:**

- None. Do not set Cloudflare credentials for this suite; its transport tests
  use injected responses.

**Steps:**

1. Run the full Python suite from the repository root.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q
```

Expected: all tests pass and the project-wide coverage gate remains at or above
90%.

Last verified: 2026-08-26 — 53 passed, 91.04% coverage.

**Cleanup:** None; pytest temporary files are under `/tmp`.

**Notes:** A focused pytest invocation can exit nonzero solely because the
global 90% coverage gate applies. Use the full suite for a passing coverage
verification.

## Frontend production build

**Purpose:** Verify that the Vite bundle builds from the current React/browser
source and package lock.

**Setup / seed:**

- Node.js and frontend dependencies installed from `frontend/`.

**Safe actions:**

- Produces a local ignored `frontend/dist/` build artifact.

**Destructive or external actions:**

- The build overwrites local `frontend/dist/`; do not treat that directory as
  hand-authored source.

**Steps:**

1. Change into `frontend/`.
2. Build the bundle.

**Verify:**

```bash
cd frontend && npm run build
```

Expected: Vite reports a successful build and writes `dist/index.html` plus
hashed assets.

Last verified: 2026-08-26 — build completed successfully.

**Cleanup:** Remove `frontend/dist/` only when a clean local workspace is
needed; it is regenerated by the command.

**Notes:** This does not call the deployed FastAPI service.

## Manual Chromium scene-runtime E2E categories

**Purpose:** Exercise the real frontend and Cloudflare-backed scene API by
category: smoke, spine, storylets, NPC knowledge, world-state follow-up, and
safety.

**Setup / seed:**

- Run `npx playwright install chromium` once from `frontend/`.
- From the repository root, load `.env` before changing into `frontend/`; it
  exports `E2E_API_BASE_URL` and `E2E_DEPLOYMENT_CHANNEL` for the staging
  deployment. There is no `frontend/.env` (only an example file).
- Set `E2E_API_BASE_URL` to a deployed FastAPI service that reports
  `runtime: "scene-v1"` from `/api/v1/version`.
- Set `E2E_DEPLOYMENT_CHANNEL` to the matching deployment channel.

**Safe actions:**

- `--list` validates E2E discovery without opening a browser or calling the
  deployed API.

**Destructive or external actions:**

- A real E2E run creates remote sessions and makes billed Cloudflare AI calls.
  Use only the intended environment and review ignored `artifacts/e2e-*.{json,md}`.

**Steps:**

1. Confirm the API version reports `scene-v1`.
2. Run all E2E tests or select one category with `--grep @<tag>`.

If Playwright's automatic Vite startup stalls, start Vite separately from the
repository root after loading `.env`; pass the corresponding public Vite
variables explicitly, then run Playwright in a second terminal:

```bash
source .env
cd frontend
VITE_API_BASE_URL="$E2E_API_BASE_URL" VITE_DEPLOYMENT_CHANNEL="$E2E_DEPLOYMENT_CHANNEL" npm run dev -- --host 127.0.0.1 --port 4173
```

The Vite server must be restarted after changing these variables. A manually
started server without them renders `VITE_API_BASE_URL is not configured.`

**Verify:**

```bash
source .env && cd frontend && npm run test:e2e -- --grep @spine
```

Expected: Chromium completes the selected category and writes an
`artifacts/e2e-spine.{json,md}` evaluation report. The `@smoke` category also
writes `artifacts/e2e-smoke-loaded.png` as loaded-page visual evidence.

Last verified safely: 2026-08-26 — Playwright discovered six tagged tests using
`E2E_API_BASE_URL=http://127.0.0.1:9999 npx playwright test --list`; no live
target was configured before the root `.env` was loaded.

**Cleanup:** Delete ignored `artifacts/e2e-*.json`, `artifacts/e2e-*.md`, and
Playwright trace artifacts when they are no longer needed.

**Notes:** The production service observed on 2026-08-26 reported `runtime:
"v2"` and rejected scene-runtime `player_input` requests. It is not a valid
target until the scene-v1 FastAPI deployment is promoted. On 2026-08-26,
running from `frontend/` before sourcing the root `.env` failed before browser
launch because `E2E_API_BASE_URL` was unset; source from the repository root.
After sourcing it, the staging version endpoint reported `api: "v1"`,
`runtime: "scene-v1"`, and `channel: "staging"`, but the focused `@smoke`
run failed: session creation and the opening rendered, then the submitted turn
returned `{}` and the UI showed `narration service rejected the turn`. Evidence:
`artifacts/e2e-smoke.json`, `artifacts/e2e-smoke-loaded.png`, and the retained
Playwright trace. A direct reproduction returned Railway HTTP 502 with the
same safe detail; the deployed API does not expose the Worker error code or
headers needed to classify the cause.

The source adapter now retries exactly once without `response_format` when the
Worker returns its documented `AI_JSON_MODE_REJECTED` code, while preserving
fail-closed behavior for all other Worker errors. `TMPDIR=/tmp uv run pytest
-q` passed on 2026-08-26 (55 passed, 90.69% coverage). The JSON-mode fallback
was deployed to staging, but did not resolve the failure. A manually configured
Vite server confirmed the frontend environment fix on 2026-08-26; staging then
failed in 767 ms with the original empty turn payload.

The staging revision was subsequently verified to match the JSON-mode fallback
source SHA, yet the same 502 remained. This confirms a different typed Worker
failure. The next source revision returns its safe Worker code in the
`X-Narration-Error-Code` response header; after deploying it, repeat the direct
session/turn probe and use that header to correct the Worker portal setting or
upstream AI condition. `TMPDIR=/tmp uv run pytest -q` then passed with 56 tests
and 90.83% coverage.

The deployment dashboard can be newer than the API's reported SHA because that
endpoint reads an environment value. The next diagnostic revision always emits
`X-Narration-Error-Code: UNKNOWN` for an untyped Worker HTTP failure and
forwards `X-Trace-ID` and `X-Worker-Revision` when the Worker supplies them.
This distinguishes an active adapter with a nonconforming Worker/upstream error
from an older deployed adapter. `TMPDIR=/tmp uv run pytest -q` passed with 57
tests and 91.11% coverage.

The confirmed cause is Cloudflare edge error 1010, not a Worker or Workers AI
error: the real 4,419-byte scene-context request sent by Python `urllib`
received HTTP 403, plain text `error code: 1010`, and no Worker headers before
the Worker executed. A small request using the same credentials succeeded,
including with `response_format`. Cloudflare documents 1010 as Browser
Integrity Check rejecting a client signature. The adapter now sends a standard
browser `User-Agent`; the same real scene-context call then succeeded directly
against the configured Worker. Do not disable Browser Integrity Check or alter
Worker credentials for this failure. A focused transport run has 7 passing
tests but intentionally exits nonzero under the repository's whole-project
coverage gate; use the full suite below for the passing coverage result.

## LLM scene-canon E2E acceptance

**Purpose:** Judge each reached scene’s narration against its scene-local plot, storylet guidance/routes, pacing, and world canon.

**Setup / seed:**

- A working scene-v1 API target plus `OPENAI_API_KEY` for the independent judge.
- The test reads the five story sources locally and sends only the current scene’s canon to the judge.

**Safe actions:**

- Creates a remote game session and makes model/judge calls; it does not alter package sources or a deployed configuration.

**Destructive or external actions:**

- Billed external model calls. Run deliberately against the intended environment.

**Steps:**

1. Configure `E2E_API_BASE_URL`, `E2E_DEPLOYMENT_CHANNEL`, and `OPENAI_API_KEY`.
2. Run the opt-in full-spine acceptance category.

**Verify:**

```bash
source .env && cd frontend && npm run test:e2e -- --grep @llm-canon
```

Expected: every reached scene receives a passing verdict for canon consistency, scene locality, progressive revelation, richness, and protected-knowledge safety; `artifacts/e2e-llm-canon.{json,md}` records the evidence.

**Cleanup:** Remove generated ignored E2E artifacts if they are no longer useful.

**Notes:** This is intentionally separate from deterministic state assertions. It
skips when `OPENAI_API_KEY` is absent. Use the package-driven clock recipe
below; each turn is bounded by `E2E_TURN_TIMEOUT_MS` (default 30000) and
partial progress is written to
`artifacts/e2e-llm-canon-progress.{json,md}`. This recipe creates a disposable
session and makes billed narration and judge calls; it is not part of ordinary
CI.

Last verified: 2026-08-27 — after staging reported runtime `scene-v1` for the merged SHA, `source .env && cd frontend && npm run test:e2e -- --grep @llm-canon` completed all eight turns and reached the independent judge. The judge failed scene `1A`: narration leaked JANUS and broader system purpose, rushed into later-scene beats, and did not consistently respond to the player action from the Thomas home. Treat this as a scene-context/prompt safety defect, not a transport or fact-validation failure. Preserve freeform LLM-proposed new facts; canonical package facts remain route-authorized, and repeated identical canonical assertions are no-ops.

On 2026-08-27, the same command again reached the judge but failed at scene `1A`. Its eight recorded turns remained in `1A` while accepting future-scene player requests, including a dead drop, facility entry, JANUS, a purge clock, and a relay. The source prompt now states that the scene object is exhaustive and that player input cannot authorize future names, places, objectives, or plot beats; deploy that revision before treating the live acceptance check as resolved.

## Hosted E2E pacing clock — timed events

**Purpose:** Trigger declared pacing pressure in the hosted staging browser
test without waiting for wall-clock time.

**Setup / seed:**

- Source the repository-root `.env` before changing into `frontend/`; it sets
  `E2E_API_BASE_URL` to the deployed staging service and
  `E2E_DEPLOYMENT_CHANNEL=staging`.
- Staging deliberately enables the gated test clock with
  `FREYTAG_ALLOW_TEST_CLOCK=1`. Production does not enable it.
- The staging service must have `FREYTAG_TEST_CLOCK_TOKEN` configured before
  this change is deployed. Never enable the clock anywhere without this shared
  secret; do not write its value into this runbook.

**Safe actions:**

- The scalar opt-in is Playwright-side and exercises the ordinary application
  request path; it does not start a local API.

**Destructive or external actions:**

- A real E2E run creates a disposable staging session and may make billed
  narration calls.

**Steps:**

1. Confirm the root `.env` points the browser at staging.
2. Run this recipe alone; do not combine it with the package-driven recipe.

**Verify:**

```bash
source .env && cd frontend && E2E_TEST_CLOCK_SECONDS=120 npm run test:e2e -- --grep @timed-events
```

Expected: `pressure_1a` fires without a two-minute wait. The harness refuses a
run with both clock opt-ins set.

**Cleanup:** Delete ignored `artifacts/e2e-*.{json,md}` and Playwright trace
artifacts when they are no longer needed; the remote session is disposable.

**Notes:** The API accepts `test_clock_seconds` only while
`FREYTAG_ALLOW_TEST_CLOCK=1` is set. A correct `FREYTAG_TEST_CLOCK_TOKEN`, sent
as the `test_clock_token` JSON field or the
`X-Freytag-Test-Clock-Token` header, advances story time. A wrong or missing
token returns HTTP 403. If the clock is enabled but
`FREYTAG_TEST_CLOCK_TOKEN` is not configured, the request fails closed with
HTTP 503. A turn without a clock request is unaffected. If
`FREYTAG_ALLOW_TEST_CLOCK` is absent, the clock field is ignored entirely and
does not produce an error. The staging secret must exist before deployment or
every clock request returns 503 and this recipe fails.

## Hosted E2E pacing clock — package-driven canon

**Purpose:** Exercise authored pacing milestones at their exact irregular
timestamps during the hosted `@llm-canon` browser acceptance test.

**Setup / seed:**

- Source the repository-root `.env` before changing into `frontend/`; it sets
  `E2E_API_BASE_URL` to the deployed staging service and
  `E2E_DEPLOYMENT_CHANNEL=staging`.
- Staging deliberately enables the gated test clock with
  `FREYTAG_ALLOW_TEST_CLOCK=1`; production does not.
- Configure `FREYTAG_TEST_CLOCK_TOKEN` on staging before deployment. Clients
  send the shared secret as `test_clock_token` or
  `X-Freytag-Test-Clock-Token`; never write the secret value here.

**Safe actions:**

- `E2E_PACKAGE_CLOCK=1` is a Playwright-side opt-in. Playwright reads the story
  package's `pacing.yaml`, names authored milestones semantically, and computes
  each delta from the last elapsed value returned by the API. It is not
  forwarded to Vite and does not affect application bundles.

**Destructive or external actions:**

- This command creates a disposable staging session and makes billed narration
  and judge calls. It is not part of ordinary CI.

**Steps:**

1. Confirm the root `.env` points the browser at staging.
2. Run this recipe alone; do not combine it with the scalar recipe.

**Verify:**

```bash
source .env && cd frontend && E2E_PACKAGE_CLOCK=1 npm run test:e2e -- --grep @llm-canon
```

Expected: the package-driven clock hits each authored milestone without
waiting for wall-clock time. A wrong or missing clock token returns HTTP 403;
an enabled staging clock with no configured `FREYTAG_TEST_CLOCK_TOKEN` fails
closed with HTTP 503. Without `FREYTAG_ALLOW_TEST_CLOCK`, the clock field is
ignored and does not error. The harness refuses a run with both clock opt-ins
set.

**Cleanup:** Delete ignored `artifacts/e2e-llm-canon-progress.{json,md}` and
`artifacts/e2e-llm-canon.{json,md}` when the evidence is no longer needed; the
remote session is disposable.

**Notes:** Partial progress is written to
`artifacts/e2e-llm-canon-progress.{json,md}` and final evidence to
`artifacts/e2e-llm-canon.{json,md}`. Each turn is bounded by
`E2E_TURN_TIMEOUT_MS` (default 30000). Run this separately from the scalar
`@timed-events` recipe.

## Story Feed root page — local Playwright QA

**Purpose:** Verify the root Story Feed UI's loading, loaded, and service-error
states; its command form's valid, blank, and long-input behavior; and its
desktop/mobile layout without creating a remote session.

**Setup / seed:**

- Node dependencies installed in `frontend/`; Chromium installed with
  `npx playwright install chromium`.
- The test intercepts the service identity, session, and turn requests with
  local fixtures. It does not need a test account, seed data, or a deployed API.

**Safe actions:**

- Starts a local Vite server and writes ignored screenshot evidence under
  `artifacts/`. No external API call or state change occurs.

**Destructive or external actions:**

- None. The command overwrites its generated local evidence files.

**Steps:**

1. Run the focused `@page-qa` Playwright test from `frontend/`.
2. Review the loading, loaded desktop, loaded mobile, and error screenshots.

**Verify:**

```bash
cd frontend && E2E_API_BASE_URL=http://127.0.0.1:9999 npm run test:e2e -- --grep @page-qa
```

Expected: one passing Chromium test; screenshots at
`artifacts/e2e-page-qa-{loading-1440,loaded-1440,loaded-375,error-375}.png`.

Last verified: 2026-08-26 — one Chromium test passed in 3.5 seconds using
`E2E_API_BASE_URL=http://127.0.0.1:9999 E2E_DEPLOYMENT_CHANNEL=production
npm run test:e2e -- --grep @page-qa --timeout=60000` from `frontend/`.

**Cleanup:** Keep the ignored evidence while it is useful; remove only the
generated `artifacts/e2e-page-qa-*.png` files when no longer needed.

**Notes:** The page has no user-auth UI boundary; authentication/authorization
must be verified against the deployed service separately. The responsive form
switches to a single column at 720px. Blank input is ignored client-side;
long input is passed through to the service contract without a client limit.

## Story Feed staging browser audit

**Purpose:** Audit the deployed Story Feed page with Chrome DevTools evidence
at desktop, tablet, and mobile sizes, including console, network, and cold-load
performance signals.

**Setup / seed:**

- The global `chrome-devtools` MCP server must be configured with a usable local
  Chromium executable.
- The page creates a staging session during initialization; no player turn is
  submitted for this audit.

**Safe actions:**

- Navigate and inspect the staging page, capture screenshots/traces, and read
  console/network activity. The normal page initialization creates a remote
  staging session.

**Destructive or external actions:**

- Does not deploy or alter story state, but does call the staging session API.

**Steps:**

1. Open the staging page with Chrome DevTools MCP.
2. Capture full-page screenshots at 1440px, 768px, and 375px widths.
3. Inspect console errors, document/style/script/fetch requests, and collect a
   cold-load trace.

**Verify:**

Expected: no console errors or failed requests; LCP under 2.5 s and CLS under
0.1. INP requires a user interaction and is not available from this load-only
trace.

Last verified: 2026-08-26 — screenshots saved as
`artifacts/browser-qa-staging-{desktop,tablet,mobile}.png`; console had no
errors; all ten observed document, asset, version, and session requests were
200/304. The cold-load trace recorded LCP 130 ms and CLS 0.01 in
`artifacts/browser-qa-staging-trace.json.gz`.

**Cleanup:** Keep ignored `artifacts/browser-qa-staging-*` evidence while it is
useful; remove it when the audit record is no longer needed.

**Notes:** Lighthouse initially failed only `meta-description` (SEO score 91),
because `frontend/index.html` had no description meta tag. The local source now
defines it. On 2026-08-26, `cd frontend && npm run build` passed and a local
Chrome DevTools check of the built page returned the description text. Local
Lighthouse no longer flagged `meta-description`; its remaining independent
failures were `robots-txt` and `llms-txt`. The staging result remains pending a
frontend deployment, so do not mark the live SEO finding resolved yet.

## Cloudflare narration Worker source audit

**Purpose:** Check the portal-exported Worker against the Railway adapter's
request and typed-error contract without changing the deployed Worker.

**Setup / seed:** `.plans/cloudflare.js` is a portal copy. Source the root
`.env`, which supplies `CLOUDFLARE_WORKER_URL` and
`CLOUDFLARE_WORKER_TOKEN`; never print either value.

**Safe actions:** Static inspection and JavaScript syntax validation only.

**Destructive or external actions:** A direct Worker request invokes Workers
AI. Use a bounded prompt and do not send real player or protected story data.

**Steps:**

1. Confirm the Worker accepts the adapter's `system`, `user`, `max_tokens`,
   and optional `response_format` fields.
2. Confirm every Worker failure includes the JSON `code` and diagnostic
   headers required by the contract.

**Verify:**

```bash
node --check .plans/cloudflare.js
```

Expected: no output and exit status 0. Last verified 2026-08-26: passed. The
portal copy accepts the adapter payload and returns typed JSON error bodies,
but `errorJson()` omits the contract-required
`X-Narration-Error-Code: <code>` header. This reduces diagnosis fidelity; it
does not by itself explain a generic 502 because the Railway adapter also
parses the JSON error body. Add that header before the next Worker portal
upload. A direct unauthenticated request to the configured Worker endpoint
returned HTTP 401 with JSON code `UNAUTHORIZED`, `X-Trace-ID`, and
`X-Worker-Revision`, confirming that the public endpoint reaches this Worker.
With the credentials sourced locally, small ordinary and `response_format`
requests both returned HTTP 200. The production-size scene-context request was
initially blocked at the Cloudflare edge with HTTP 403 / error 1010 because
Python urllib's default user agent triggered Browser Integrity Check; the same
request passed after the adapter supplied its browser user agent.

## Hosted free-text roleplay quality evaluation

**Purpose:** Verify that a real player action receives a responsive, progressive
roleplay narration rather than a repeated opening, while allowing creative
consequences that the runtime validates through proposed state effects.

**Setup / seed:** Source the root `.env` with `E2E_API_BASE_URL`,
`E2E_DEPLOYMENT_CHANNEL`, and `OPENAI_API_KEY`. The optional
`E2E_JUDGE_MODEL` selects the OpenAI judge; it defaults to `gpt-5.4`. Do not
print or commit credentials.

**Safe actions:** The staged test creates a disposable remote session and two
turns. The judge uses the OpenAI Responses API with `store: false` and writes
only its structured verdict and reasons to ignored `artifacts/` evidence.

**Destructive or external actions:** Invokes the staged narration model and two
paid OpenAI judge calls. It does not deploy, change credentials, or mutate
canonical state outside the disposable session.

**Steps:**

1. Start a session and submit two distinct free-text actions.
2. Assert neither narration repeats the opening and that the two narrations
   differ.
3. Ask the OpenAI judge whether each narration responds directly, progresses,
   and remains coherent with the supplied grounding. Creative additions are
   explicitly allowed; story-beat/state-effect validity remains the runtime's
   deterministic responsibility.

**Verify:**

```bash
source .env && cd frontend && npm run test:e2e -- --grep @llm-judge
```

Expected: both OpenAI structured verdicts are `pass` and
`artifacts/e2e-llm-judge.{json,md}` records the narrations plus reasons. This
is an explicit, paid manual evaluation; ordinary `@smoke`, `npm test`, pulls,
pushes, and PR checks do not call OpenAI. Last
verified locally on 2026-08-26: the judge returned `fail` for the known defect
where the opening text was returned verbatim for `Look at the phone`.

**Cleanup:** The generated `artifacts/e2e-llm-judge.*` files are ignored; remove
them when no longer useful. The remote test session is disposable.

**Notes:** As of 2026-08-26, the existing `@spine` E2E only reports whether
its fixed policy reached `3C`; it does not assert it. `@storylets` only checks
that any observed IDs have the `SL-` prefix, so an empty set passes. The
current `pacing.yaml` declares one outgoing transition from each of `1A`
through `3B` and a single terminal `3C`; it has no alternate transition or
ending branches. Do not claim live E2E proof of complete storylet coverage,
branch coverage, or multiple endings until package-declared coverage oracles
and repeated policy runs are implemented.

The loader reads only `data/stories/continuity-initiative/{plot.md,storylets.md,
pacing.yaml,world.yaml}`; `.plans/` copies are not runtime inputs. The loaded
`storylets.md` defines optional scene-local storylets and supplies their prose
sections to the model context, but it does not compile `Effects`, `Completion`,
or `Abort` prose into transition edges. Actual scene branches and endings must
be declared as additional `pacing.yaml` transitions and listed in the source
scene's `transition_ids` frontmatter.

After the adapter change was deployed, two staging `@smoke` retries still
timed out after 120 seconds in `page.waitForResponse()` for `POST
/api/v1/turn`. The page snapshot showed `Failed to fetch` for both the session
feed and submitted action, and no browser-observable turn response arrived.
Restarting the local Vite server did not change that result. Treat this as a
browser/API transport (likely CORS or deployed API reachability) failure, not
as evidence that the Worker user-agent fix is ineffective; the direct
authenticated full-context Worker call succeeded. Evidence is the retained
Playwright trace and error context under
`frontend/test-results/scene-runtime-starts-a-sce-758f8-ts-freeform-narration-smoke-chromium/`.

The direct staging session/turn probe then returned Railway HTTP 500, which
was reproduced locally: the Worker returns a successful envelope containing
JSON text in `narration` plus metadata, but the adapter passed that outer
envelope to strict `TurnProposal` validation. The adapter now unwraps and
parses `narration`, keeps the metadata non-canonical, uses the Worker-supported
2,048-token ceiling after observing a 1,024-token truncated JSON response, and
sends an explicit schema-and-no-echo prompt. A real local Worker plus runtime
turn then succeeded. This revision still needs Railway deployment before
rerunning the staging smoke test.

**Cleanup:** None.
