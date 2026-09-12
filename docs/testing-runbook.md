# Testing runbook

## Authored reveal handoff prompt contract

**Purpose:** Verify that a matcher-backed authored reveal is delivered by the
runtime while the narrator sees only ordinary scene material, including after
malformed-response recovery. Legacy candidate prompts remain unchanged.

**Setup / seed:** The checked-in `continuity-initiative` package and the
authored-handoff fixture in `tests/test_cloudflare_transport.py`.

**Safe actions:** Run the focused local regression tests. No worker request is
made; tests use a stub response.

**Destructive or external actions:** None.

**Steps:**

1. Run the authored-handoff and transport prompt tests.
2. Run the full suite and Ruff before accepting the change.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q tests/test_cloudflare_transport.py
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix .
uv run ruff format .
```

Expected: the focused assertions pass; its process may exit nonzero only on the
repository-wide coverage gate. The handoff prompt contains no candidate ID,
candidate statement, delivery text, `must_convey`, or grounding instructions;
a malformed reply recovers without restoring those details; the composed result
contains the exact authored delivery and uses the normal commit path. The full
suite reaches the coverage threshold.

**Cleanup:** None.

**Notes:** Added 2026-09-12 for Phase 4 of
`.plans/authored-reveal-handoff.md`. The selection prepass is skipped for an
authored handoff. Legacy candidates retain their prompt contract. Observed
2026-09-12: the focused module passed all 82 assertions and exited only on its
64.12% subset coverage; the full suite passed 378 tests at 91.63% coverage.
Ruff check and formatting passed.

## Narration candidate-selection baseline

**Purpose:** Measure how often the narrator selects an offered Scene 1A reveal
when the player's action clearly asks for it. This is a local bench baseline;
it does not validate a prompt fix or a hosted deployment.

**Setup / seed:** The checked-in `continuity-initiative` package and
`bench/variations/candidate-selection-baseline.json`; live runs require the
environment variables documented in `bench/README.md`.

**Safe actions:** Inspect the assembled prompt and run the mechanical report
against a saved bench record.

**Destructive or external actions:** `bench run` calls Cloudflare Workers AI
and the OpenAI judge. It is billed and writes an append-only ledger row. Use
the default four replicates per batch; delete only disposable output under
`/tmp`.

**Steps:**

1. Preview the configured Scene 1A prompt and confirm the effective rules.
2. Run four replicates of the exact four-action sequence. Repeat the batch if
   the clear target window is reached too few times. The bench repeats the
   first action if the scene remains stuck on a fifth turn.
3. Run `bench.candidate_selection_report` against `all-turn-records.json`,
   which includes failed/stuck runs as well as completed runs.

**Verify:**

```bash
uv run python -m bench prompt --variation bench/variations/candidate-selection-baseline.json --scene 1A --player-input "Search the kitchen and the back door for concrete signs of what happened here - the overturned chair, the forced lock, her phone left on the floor." --text
uv run python -m bench run --variation bench/variations/candidate-selection-baseline.json --scene 1A --script candidate-selection-repro --replicates 4 --out /tmp/bench-candidate-selection-baseline --confirm
uv run python -m bench.candidate_selection_report --in /tmp/bench-candidate-selection-baseline/all-turn-records.json --out-json /tmp/bench-candidate-selection-baseline/report.json --out-md /tmp/bench-candidate-selection-baseline/report.md
```

Expected: the report's `turn1_position0_match_rate` and
`turn3_position2_match_rate` are the baseline measures for the two clear
selection windows. Its `per_turn` list must retain the input, replicate,
`selected_knowledge_ids`, `grounding_ids`, and `candidates_offered` for every
recorded turn, including failed runs, without storing narration text. The
grounding list is the union of IDs attached to the accepted turn's segments.

**Cleanup:** None required. Keep the `/tmp` output while comparing a later
candidate; do not add raw model transcripts to the repository.

**Notes:** Added 2026-09-11 for Phase 1 of
`.plans/narration-candidate-selection-reliability.md`. The report measures
actual model selections mechanically; deciding that the two windows are clear
matches is an authored benchmark judgment recorded by the plan.

**Phase 2 diagnosis 2026-09-11:** A further four-replicate baseline batch
produced 0/4 first-turn selections, extending the same-script baseline to 12
replicates, 21 offered turns, and 0 selections. The prose varied on each
request, but the model always left `selected_knowledge_ids` empty; each run
later failed on the unrelated `narration_known_term_leak` check. The assembled
first-turn prompt was 5,013 characters. It placed two overlapping Scene 1A
candidate statements before the rule block; those candidates have no
`must_convey` groups, so statement overlap cannot safely identify one. A
four-replicate wording probe (`bench/variations/candidate-selection-phase2-rule.json`)
added direct-selection rules and produced 0/16 selections, so prompt wording
was not accepted as the Phase 3 fix. The Phase 3 candidate is a deterministic
bridge limited to exactly one eligible candidate whose complete non-empty
`must_convey` groups appear in the response. Ambiguous candidates and partial
or vague prose remain unselected, and the ordinary resolver still validates
all effects before commit.

**Phase 2 commands:**

```bash
uv run python -m bench run --variation bench/variations/candidate-selection-baseline.json --scene 1A --script candidate-selection-repro --replicates 4 --out /tmp/bench-candidate-selection-phase2-baseline --confirm
uv run python -m bench.candidate_selection_report --in /tmp/bench-candidate-selection-phase2-baseline/all-turn-records.json --out-json /tmp/bench-candidate-selection-phase2-baseline/report.json --out-md /tmp/bench-candidate-selection-phase2-baseline/report.md
uv run python -m bench run --variation bench/variations/candidate-selection-phase2-rule.json --scene 1A --script candidate-selection-repro --replicates 4 --out /tmp/bench-candidate-selection-phase2-rule --confirm
uv run python -m bench.candidate_selection_report --in /tmp/bench-candidate-selection-phase2-rule/all-turn-records.json --out-json /tmp/bench-candidate-selection-phase2-rule/report.json --out-md /tmp/bench-candidate-selection-phase2-rule/report.md
```

Expected: the baseline report records 0/4 first-turn matches and the wording
probe records 0/4 first-turn plus 0/4 third-turn matches. The live runs are
billed and write append-only ledger rows; the reports and raw transcripts stay
under `/tmp`.

**Instrumentation update 2026-09-11:** `bench` now records the union of
accepted segment `grounding_ids` beside `selected_knowledge_ids`. It also
records the model's raw `selected_knowledge_ids` and `grounding_ids` before the
harness repairs either field. The candidate-selection report preserves all
four fields. The focused
regression check passed 107 tests:

```bash
TMPDIR=/tmp uv run pytest -q --no-cov tests/test_cloudflare_transport.py tests/test_bench.py tests/test_candidate_selection_report.py
```

One fresh baseline replicate then recorded four accepted turns. Selection was
empty on all four. Grounding was `k_scene_1a_entry` on turns 1, 3, and 4, and
empty on turn 2. This proves the LLM was grounding narration on already-known
scene facts while still selecting no new candidate; the benchmark no longer
needs to infer that distinction. A fresh run with the corrected grouped rule
recorded `selected_knowledge_ids: []`, `model_grounding_ids: []`, and final
`grounding_ids: ["k_scene_1a_entry"]` on its one accepted turn. The final ID
was added by the harness, not returned by the LLM.

**Rule-layout comparison 2026-09-11:** The same four-input script was run
with the selection duty as three separate bullets and as one grouped bullet.
The separate version recorded 0/4 first-turn selections and 0/4 selections on
offered turns. The grouped version recorded 0/4 first-turn selections, 0/2
third-turn matches, and 0/9 selections on offered turns. It reached more
accepted turns before its later leak failure, but it did not improve selection.
In the grouped run, all nine accepted turns had empty `model_grounding_ids`;
the final grounding list contained only the harness-added known scene fact on
some turns. The line grouping is therefore not the root fix.

```bash
uv run python -m bench run --variation bench/variations/candidate-selection-phase2-separate.json --scene 1A --script candidate-selection-repro --replicates 4 --out /tmp/bench-candidate-selection-phase2-separate --confirm
uv run python -m bench run --variation bench/variations/candidate-selection-phase2-grouped.json --scene 1A --script candidate-selection-repro --replicates 4 --out /tmp/bench-candidate-selection-phase2-grouped --confirm
uv run python -m bench.candidate_selection_report --in /tmp/bench-candidate-selection-phase2-separate/all-turn-records.json --out-json /tmp/bench-candidate-selection-phase2-separate/report.json --out-md /tmp/bench-candidate-selection-phase2-separate/report.md
uv run python -m bench.candidate_selection_report --in /tmp/bench-candidate-selection-phase2-grouped/all-turn-records.json --out-json /tmp/bench-candidate-selection-phase2-grouped/report.json --out-md /tmp/bench-candidate-selection-phase2-grouped/report.md
```

**Harness comparison 2026-09-11:** The first controlled comparison used the
same grouped prompt and four-input script. The baseline disabled the new
deterministic selection bridge; the candidate enabled it. Both arms produced
0/7 selections on offered turns across four replicates, reached no judgeable
scene, and therefore produced no score. The negative result is expected when
the model's prose is vague or incomplete: the bridge must not guess a reveal.
The unit test separately proves the intended positive case: when the model
describes all required facts for exactly one offered candidate but returns an
empty selection, the harness adds that candidate and the existing validator
still decides whether it can commit.

```bash
uv run python -m bench run --variation bench/variations/candidate-selection-phase3-harness-baseline.json --scene 1A --script candidate-selection-repro --replicates 4 --out /tmp/candidate-selection-phase3-harness-baseline --confirm
uv run python -m bench run --variation bench/variations/candidate-selection-phase3-harness-candidate.json --scene 1A --script candidate-selection-repro --replicates 4 --out /tmp/candidate-selection-phase3-harness-candidate --confirm
uv run python -m bench.candidate_selection_report --in /tmp/candidate-selection-phase3-harness-baseline/all-turn-records.json --out-json /tmp/candidate-selection-phase3-harness-baseline/report.json --out-md /tmp/candidate-selection-phase3-harness-baseline/report.md
uv run python -m bench.candidate_selection_report --in /tmp/candidate-selection-phase3-harness-candidate/all-turn-records.json --out-json /tmp/candidate-selection-phase3-harness-candidate/report.json --out-md /tmp/candidate-selection-phase3-harness-candidate/report.md
```

The per-turn records now preserve both `model_selected_knowledge_ids` and the
final `selected_knowledge_ids`, so a non-empty final value with an empty model
value is direct evidence of a harness repair.

**Random-choice prompt comparison 2026-09-11:** The new single-rule prompt was
run with the harness disabled and enabled. The baseline recorded 0/13 final
selections on offered turns across four replicates and the candidate recorded
0/16. Both arms reached no judgeable scene. The candidate reached three more
accepted narration turns, but the LLM returned no selections in either arm and
the harness repaired none because no response fully proved exactly one
candidate. This prompt change therefore has no measured selection-rate gain.

The final full Python suite passed 338 tests with 91.35% coverage. Ruff check
and formatting also passed with no changes required.

**Observed 2026-09-11:** Two four-replicate batches used 396 estimated
Workers AI neurons across 36 narration requests and produced 8 failed runs,
17 recorded turns, 17 offered-candidate turns, and 0 selections. The first
clear window was 0/8; the third-turn clear window was 0/3. Every run hit a
known-term safety rejection before scene completion, but the all-turn records
preserved the selection observations. The focused verification command passed
all 41 tests but exited on the repository coverage threshold (51.65% for the
focused subset); the full suite is the coverage check of record.
`TMPDIR=/tmp uv run pytest -q` passed 337 tests with 91.35% total coverage.
From `frontend`, `npm test` passed 35 tests and `npm run build` completed
successfully.

## Candidate selection cue and positive-example regression

**Purpose:** Verify that an eligible reveal can carry a player-safe earning cue
and that turns with offered candidates use a coupled selection/grounding JSON
example rather than the old empty-selection discovery example.

**Setup / seed:** Use the checked-in `continuity-initiative` package. Scene
1A's `SL-1A-B` must be active to expose its two recording candidates.

**Safe actions:** Run local tests and inspect the assembled prompt. No model
request or state-changing action is required.

**Destructive or external actions:** None.

**Steps:**

1. Run the focused Cloudflare transport test module.
2. Run the full suite before accepting a change; the focused command alone is
   expected to miss the repository-wide coverage gate.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q tests/test_cloudflare_transport.py -x
TMPDIR=/tmp uv run pytest -q
```

Expected: the focused module's assertions pass; its process may exit nonzero
only because the focused subset is below 90% total coverage. The full suite
must pass the coverage gate. The assembled offered-candidate prompt names the
cue and shows the same offered ID in both `selected_knowledge_ids` and the
delivering segment's `grounding_ids`.

**Cleanup:** None.

**Notes:** Added 2026-09-11. This is a prompt/data affordance only. The normal
resolver still decides whether selection, narration, grounding, package
effects, and resulting facts can commit.

Observed 2026-09-11: the focused transport module passed all 71 assertions,
then exited only on the expected focused-subset coverage gate (62.32%). The
full parallel suite passed 344 tests with 91.45% coverage. `uv run ruff check
--fix .` and `uv run ruff format .` both completed with no changes.

The four-replicate live cue/positive-example probe used 220 estimated Workers
AI neurons. It recorded 1 selected candidate out of 10 offered turns (10%),
with 1/4 first-window matches and 0/2 third-window matches. The one selection
was returned by the model and passed normal grounding checks; it was not a
harness repair. This is not enough to accept the prompt/data change as a
reliability fix. The run also demonstrated why a positive example must be
limited to a cue-matching action: an initial preview would otherwise show the
first offered candidate for an unrelated action.

**Selection-only probe 2026-09-11:** The one-call
`candidate-selection-phase5-selection-only` variation removed every
model-facing candidate-grounding rule and asked only for a selected ID plus
reveal prose; the existing resolver remained responsible for deriving
grounding after validated delivery. Four live replicates used an estimated 220
Workers AI neurons and recorded 0 selected candidates on 15 offered turns.
Both clear windows were 0/4. This rejects the hypothesis that the model was
abstaining because it had to coordinate `grounding_ids` with
`selected_knowledge_ids`. Do not enable this prompt variant for ordinary play.

**Matcher isolation 2026-09-11:** `tests/test_candidate_matcher.py` defines
the pre-integration safety contract for a future high-precision matcher. It
must return one candidate only when every authored phrase group is present;
declared paraphrases may match, while partial, unrelated, negated, empty, and
ambiguous inputs return no candidate. The matcher is intentionally unused by
the package loader, prompt, provider, resolver, and state mutation paths until
these tests are expanded with package-specific evidence data and reviewed.

**Matcher shadow telemetry 2026-09-11:** The first package evidence is limited
to the two Scene 1A memory-card outcomes. `CloudflareTurnProvider` records
`shadow_matched_candidate_id` after projection, and `bench` records that ID
per turn. The evidence is not serialized into the prompt and the value does
not alter candidates, selection, grounding, narration, effects, or commits.
Verify this boundary with `tests/test_candidate_matcher.py`,
`tests/test_cloudflare_transport.py`, and `tests/test_bench.py` before any
future proposal to use the telemetry for prompt narrowing.

The first four-replicate live shadow run used the unchanged baseline prompt and
220 estimated Workers AI neurons. It recorded ten accepted turns. On both
surviving third-turn recording actions, the matcher uniquely reported
`k_sl_1a_b_r2`; the model selected no candidate and the final selection stayed
empty. All other recorded turns reported no match. This proves the matcher can
identify the intended recording candidate without changing the model-visible
context or committing any fact; it does not yet prove that prompt narrowing or
automatic delivery would be safe or effective.

**Shadow-narrowing probe 2026-09-11:** The one-call
`candidate-selection-phase7-shadow-narrowing` variation used the matcher only
to reduce the narrator-visible candidate list when exactly one shadow match
existed. The resolver still received the complete eligible projection. Four
live replicates used 231 estimated Workers AI neurons across 21 narration
requests and recorded ten turns. Both surviving recording turns had shadow
match `k_sl_1a_b_r2` and showed only that ID to the narrator, but both model
and final selections stayed empty. This rejects candidate-list ambiguity as
the cause of the observed abstention. Do not enable narrowing for ordinary
play.

**Selection-only JSON diagnostic 2026-09-11:** `python -m bench
selection-probe` builds the ordinary safe projection for one isolated storylet,
then sends a 32-token request containing only the player action, offered IDs,
and their statements. The reply has one allowed key,
`selected_knowledge_ids`. It is diagnostic telemetry only: it does not enter
the resolver and cannot select, ground, narrate, apply effects, or commit a
fact. The transport test verifies that no narration, segment, or grounding
work reaches this request.

For `SL-1A-B` and `Recover Michelle's damaged recording and listen to it.`,
four one-option probes (the shadow-narrowing variation) returned
`k_sl_1a_b_r2` four times. This establishes that the 8B model can emit an
offered candidate ID when the story-generation contract is absent. It does not
make direct selection safe: with the full two-option list, all four probes
returned the wrong `k_sl_1a_b_r1`; with the unrelated action `Search the office
drawers for a spare key.`, all four returned the unearned `k_sl_1a_b_r2`.
The failure is therefore not JSON syntax or the ID token itself. It is the
model's unreliable semantic decision when more than one option is visible,
and it can also fabricate a selection without evidence. Keep this tool out of
the game path and do not use its answer for commits.

**Two-pass candidate delivery probe 2026-09-11:**

**Purpose:** Test whether a short selection call followed by ordinary narration
can make an evidence-backed reveal survive the normal validator. This is
benchmark-only; it never commits a turn.

**Setup / seed:** Use
`bench/variations/candidate-selection-phase8-two-pass.json`, Scene 1A,
`SL-1A-B`, and the interrupted-recording action. The selector runs only when
the exact authored matcher returns one candidate. A tie, no match, malformed
selector reply, or a different ID forces an empty selection.

**Safe actions:** The isolated probe builds temporary state and calls the
provider without an engine, so it cannot apply effects or facts.

**Destructive or external actions:** The provider calls Workers AI and consumes
model capacity; use a small replicate count.

**Verify:**

```bash
uv run python -m bench two-pass-probe \
  --variation bench/variations/candidate-selection-phase8-two-pass.json \
  --scene 1A --storylet SL-1A-B \
  --player-input "Try to recover the interrupted message she was recording, and listen to whatever survives of it." \
  --replicates 1
```

Expected success signal for the handoff is the same nonempty ID in
`preselected_knowledge_id`, `model_selected_knowledge_ids`, and
`final_selected_knowledge_ids`. The first two fields alone are not success:
the final field must have passed narration, grounding derivation, and normal
validation.

**Cleanup:** None.

**Observed:** The four-replicate full-scene run made 18 narration requests but
all replicates failed before the recording action on existing narration safety
leaks, so it cannot measure this change. Six isolated recording probes then
selected `k_sl_1a_b_r2` in the evidence-gated first pass (6/6); the narration
model named it in 5/6 final drafts, but did not state the required warning in
any draft. Its recovery therefore returned an empty final selection in 6/6.
The normal validator prevented every unsupported commit. This two-pass design
does not improve accepted candidate selection and must remain disabled in
ordinary play.

## Optional-storylet pacing permutation audit

**Purpose:** Determine whether authored optional-storylet windows and pacing
events remain playable when optional storylets are realized in different
orders, and whether the resulting scene turn counts fit their scene-local
windows.

**Setup / seed:** The checked-in `continuity_initiative` package under
`data/stories/continuity-initiative`; no model, credentials, or hosted session
are required for the deterministic audit.

**Safe actions:** Read package declarations and run local deterministic tests.

**Destructive or external actions:** None.

**Steps:**

1. Inspect `tests/test_scene_relative_pacing.py` and
   `tests/test_canon_journey.py` for existing timing and journey coverage.
2. Run the focused pacing and canonical-journey tests.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q tests/test_scene_relative_pacing.py tests/test_canon_journey.py
```

Expected: the existing structural pacing checks and the two scripted journeys
pass. This does not by itself prove all permutations of optional storylets are
timing-safe; record any separate permutation-audit result here.

**Observed 2026-09-07:** all 15 focused tests passed, but the command exited
nonzero because the focused subset produced only 48% coverage and the
repository enforces a 90% minimum. The full suite then passed with 294 tests
and 90.72% coverage:

```bash
TMPDIR=/tmp uv run pytest -q
```

The checked-in package has 30 optional storylets. Their target/latest turns
fit within the declared scene handoff windows, and the four declared pressure
events occur at turns 2, 2, 3, and 4 in their respective scenes. Existing
tests cover those static bounds, one fixed clocked journey, one fixed
unclocked journey, activation after an earlier same-scene storylet, and
single-reveal reachability. They do not enumerate different optional-storylet
orders, simulate slow exploration against handoff, or assert a comfortable
buffer between optional content and scheduled pressure.

**Cleanup:** None.

**Notes:** Added 2026-09-07 while evaluating the missed-obligation escalation
plan. The audit specifically checks whether existing tests cover optional
storylet order, pacing-event timing, and scene handoff thresholds. The global
1,800-second budget was subsequently removed from the design; the checked-in
package and tests still need that implementation update.

## Remaining-scene physical continuity audit

**Purpose:** Evaluate Scenes 1B through 3C against the Scene 1A continuity
benchmarks: a slower player receives a visible pressure warning and response
window; tools and physical evidence are introduced before use; and every
supported optional-storylet order leaves the next scene's bridge facts and
dependencies coherent.

**Setup / seed:** The checked-in `continuity_initiative` package under
`data/stories/continuity-initiative`; no model, credentials, or hosted session
are required for the static audit.

**Safe actions:** Read package declarations and run local deterministic tests.

**Destructive or external actions:** None.

**Steps:**

1. Inspect each scene's Markdown frontmatter, entry/bridge text, beats,
   storylet routes, pacing event, transition triggers, and required
   dependencies.
2. Compare each transition's bridge prose with the facts its activation rule
   actually guarantees.
3. Run the focused pacing and canonical-journey tests.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q tests/test_scene_relative_pacing.py tests/test_canon_journey.py
```

Expected: all 15 focused tests pass; the command may still exit nonzero because
the focused subset produces less than the repository's 90% coverage threshold.

**Observed 2026-09-08:** all 15 tests passed, with the expected 48% focused
coverage failure. Existing tests do not enumerate optional-storylet orders,
assert a two-turn response buffer after every timed pressure event, verify
pre-use item/device cues, or prove that bridge prose matches the subset of
facts delivered on a slow handoff. The remaining-scene findings and proposed
fixes are recorded in `.plans/physical-continuity-fix.md`.

**Cleanup:** None.

**Notes:** The global 1,800-second budget was removed as a design decision on
2026-09-08. Scene windows will be sized independently so Scenes 1B and 3B can
provide at least two response turns after their pressure events. The package
and its pacing tests still need the corresponding implementation update.

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
- Before the staged probe, set `RAILWAY_TOKEN`, `RAILWAY_PROJECT_ID`,
  `RAILWAY_SERVICE_ID`, `RAILWAY_STAGING_ENVIRONMENT_ID`, and
  `RAILWAY_PUBLIC_API_URL` in the shell, for example with `source .env`.

**Safe actions:** Local transport tests intercept the Worker request; no
network request is made.

**Destructive or external actions:** The optional browser probe creates a
disposable staging session and may make billed model calls. The probe script
temporarily switches the ENTIRE staging deployment to a fixed scripted
narration response for its duration, so no one else should run manual staging
checks such as `@llm-canon` or `@storylets` while it is running. It automatically
reverts staging to live narration afterward, even if the probe fails, and polls
for the live opening text to differ from the scripted one.

**Steps:**

1. Run the full suite after changing the provider contract or proposal schema.
2. After the implementation revision deploys to staging, run the persistent
   knowledge-timeline probe and retain its redacted payload-ID artifact.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q
bash scripts/knowledge_timeline_probe.sh
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

**Staging attempt 2026-09-10:** The probe initially failed because the local
Railway CLI 2.1.0 did not recognize the legacy `variable` command. The script
now detects that CLI and falls back to `npx @railway/cli@latest`, preserving
explicit project, service, and environment targeting. The retry reached the
current CLI but was rejected before changing staging variables with
`Unauthorized. Please check that your RAILWAY_TOKEN is valid and has access to
the resource you're trying to use.` The cleanup trap ran, but its three
variable-reset calls were rejected by the same authentication failure. Confirm
or replace the project token in the local environment before rerunning; no
successful Railway variable update was observed from this attempt.

**Staging verification 2026-09-10 (successful).** After correcting the probe
to compare the provider's final opening segment rather than the API's complete
opening text, `bash scripts/knowledge_timeline_probe.sh` completed successfully
against staging. The browser test passed in 2.3 minutes. The fresh artifact
`artifacts/e2e-knowledge-timeline.{json,md}` records SHA
`65184a9fc12902b6b73a7da362a764a6f7277952`, five committed timeline turns, and
the invalid future-lead turn rejected with `ineligible_selection` and HTTP 409.
The drawer turn selected `k_sl_1a_b_r2`, resolved
`SL-1A-B/SL-1A-B-R2`, and returned grounded narration. The probe's exit cleanup
restored live narration successfully. Railway's agent-tooling and Config as
Code messages remained warnings only and did not affect the result.

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

**Observed 2026-09-10.** The committed deterministic evidence implementation
passed the focused Phase 3/API checks (`3 passed, 22 deselected`) and generated
the ignored redacted artifact `artifacts/phase3-knowledge-evidence.json`. The
artifact records the four required boundaries: the damaged-warning selection
resolved to `SL-1A-B/SL-1A-B-R2` and committed `michelle_warning_known`, while
future, duplicate, and unselected IDs were rejected with unchanged SQLite
snapshots. The full Python suite passed with 310 tests and 90.92% coverage.
The frontend unit/evidence suite passed with 33 tests. No staging browser run
was performed, so this verifies the local deterministic evidence only; the
staging command above remains outstanding for the deployed SHA.

**Staging attempt 2026-09-10.** `/api/v1/version` reported staging SHA
`b3a8823ce88c7899e47d8632e91d1d3ea1db55e5`. The browser probe reached the third
drawer turn, but failed because the live provider returned only local
phone/drawer/KMS observations and did not yet mention a recording, warning,
research, evidence, continuity, or lead. The test therefore stopped before its
selected-ID and resolved-source assertions, and did not produce a new
`e2e-knowledge-timeline` report. This is a staging/live-provider acceptance
failure, not evidence that the deterministic local fixture failed.


A later staging attempt reported a browser CORS failure. Direct checks of the
current staging revision's `OPTIONS /api/v1/turn` and cross-origin invalid
`POST /api/v1/turn` both returned `Access-Control-Allow-Origin: *`; rerun the
probe before changing CORS configuration, and record the deployed SHA if it
recurs.

## Phase 5 knowledge leakage matrix and staging rollout

**Purpose:** Verify the deterministic package-wide knowledge leakage matrix in
`tests/test_knowledge_leakage_matrix.py`: every scene and audience is projected
before and after each reveal, all not-yet-reachable knowledge terms stay absent,
and the explicit payload-size regression threshold holds. Separately verify that
the browser canon judge in `frontend/e2e/roleplay-judge.js` scores each scene
against its committed reveal timeline, not the full world, route, or storylet
files.

**Setup / seed:**

- Python 3.12 dependencies are installed with `uv sync --group dev`.
- Run from the repository root; pytest temporary files belong under `/tmp`.
- Before staged gates, set the `RAILWAY_*` variables documented in the Phase 3
  entry from `.env` and source the root `.env` for the frontend staging target.

**Safe actions:** The deterministic pytest module and frontend unit tests run
locally with no network calls.

**Destructive or external actions:** The staged `@smoke`, focused safety/NPC-
knowledge cases, full spine, and `@llm-canon` gates run only against the hosted
staging deployment, never a local API, after a merge to `main` and CI redeploy.
Delete stale artifacts before every attempt, confirm `/api/v1/version` reports
the new staging SHA, and confirm each run completed before recording evidence.
`@llm-canon` makes billed OpenAI judge calls; a nonzero exit is normal when the
judge records a failing verdict.

**Steps:**

1. Run the deterministic leakage-matrix test locally.
2. Run the frontend unit suite locally.
3. After merging to `main`, confirming `/api/v1/version` reports the new
   staging SHA, and deleting stale artifacts, run the staged gates in order:
   `@smoke`, the focused `@safety|@npc` cases, the full spine, then
   `@llm-canon`. The `@llm-canon` playthrough already covers the full spine and
   satisfies that step; do not run a separate spine command.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest tests/test_knowledge_leakage_matrix.py -q
cd frontend && npm test
source .env && cd frontend && npm run test:e2e -- --grep @smoke
source .env && cd frontend && npm run test:e2e -- --grep "@safety|@npc"
source .env && cd frontend && E2E_PACKAGE_CLOCK=1 E2E_TURN_TIMEOUT_MS=90000 npm run test:e2e -- --grep @llm-canon
```

Expected: a passing run shows no future-scene term in any scene/audience
projection, and each scene's canon payload contains only its actually committed
knowledge statements and scene frame, never full world, route, or storylet
text. The staged gates must run against the new SHA; interpret a nonzero
`@llm-canon` exit from its completed artifact and verdict rather than treating
it as an incomplete run.

**Cleanup:** `artifacts/phase5-knowledge-leakage-matrix.json` is gitignored and
may be deleted once staged evidence supersedes it.

**Notes:** Staging verification 2026-09-11 (blocked): PR #446 (branch
`phase5knowledge`) merged to `main` as commit
`0c7d4f228d758d24096c7d35786f251259686463`. Staging's `/api/v1/version` was
polled until it reported that exact SHA before any gate ran.

With stale artifacts deleted, `@smoke` was run twice against staging and failed
identically both times on the first scripted turn, player input "Look carefully
at Michelle's phone.": `Turn API returned HTTP 409: narration does not ground
the knowledge term 'michelle's phone'`. The focused `@safety|@npc` gate was then
run once and both of its two tests failed with the identical error message and
grounding term on their own first scripted turns.

A local deterministic check (`KnowledgeProjector.project` against the same
scripted input) confirmed a valid grounding id, `k_scene_1a_entry`, is available
in the projection and its own statement already mentions Michelle's phone --
so this is not a missing-grounding structural gap; the live model had a valid
id to cite and did not cite it. `@llm-canon` was NOT run after this pattern, to
avoid spending further billed OpenAI calls on a scene-1A opening flow that had
just failed identically three times in a row for the same reason.

This is not a knowledge leak: the deterministic `NarrationSafetyValidator`
correctly rejected the non-compliant narration before commit or render,
exactly as designed (fail closed, no state change). The finding is a live-model
narration-grounding citation compliance gap, not a Phase 5 code defect --
nothing in the Phase 5 diff touched `storygame/runtime/narration_safety.py`,
`storygame/runtime/cloudflare.py`, or the package's `knowledge.yaml`.

The 2026-08-31 staging entry recorded in the Phase 3 section of this file above
shows `@spine` and `@llm-canon` completing structurally (all turns returning
successfully) with only narrative-quality judge complaints at that time. The
deterministic NarrationSafetyValidator's hard grounding-citation rejection was
added afterward, in the Phase 4 merge, and its Phase 3/4 staged evidence used
a test-only deterministic provider rather than the live model (see the Phase 3
section's own Phase evidence note). This staged Phase 5 run therefore appears
to be the first time that specific check ran against live model traffic, and it
reveals the live model does not reliably comply with it even for a
straightforward, already-available grounding id.

Status: the Phase 5 code changes (leakage matrix tests, roleplay-judge.js
committed-timeline rewrite, narrative_history removal) are merged and
independently verified locally (327 Python tests, 35 frontend tests, both
suites' ruff/build checks clean). The staged rollout gate is blocked by this
live-model grounding-citation compliance gap, which is outside Phase 5's scope
to fix. Production promotion was out of scope for this pass by explicit
decision.

Staging verification 2026-09-11 (follow-up): after landing the deterministic
auto-attribution fix (commit `b7d5d1d`) and a separately-discovered
opening-narration-safety fix (commit `a46f6b9`, plus ripple-effect test fixes),
staging redeployed to commit `bdc966d`. Staging's `/api/v1/version` was polled
until it reported that exact SHA. With stale artifacts deleted, `@smoke` was
re-run against staging and passed (1 passed). This is the exact test that
previously failed 4/4 times with `uncited_knowledge: narration does not ground
the knowledge term 'michelle's phone'` -- that failure is confirmed resolved.
The focused `@safety|@npc` gate was then run and both of its two tests failed,
but with DIFFERENT errors than before: `@npc` failed with `Turn API returned
HTTP 409: narration mentions unavailable knowledge 'message from michelle'`,
and `@safety` failed with `Turn API returned HTTP 409: narration mentions
unavailable knowledge 'hidden memory card'`. Both are the deterministic
`narration_known_term_leak` rejection code -- a genuine leak (the term's
owning knowledge is not yet available/committed), not the `uncited_knowledge`
citation-omission issue that was fixed. No artifact files were produced for
these failures since Playwright failed before the test's own
`writeCategoryReport` call ran. `@llm-canon` was NOT run after this, to avoid
spending further billed OpenAI calls chasing a newly-surfaced, apparently
unrelated leak in different scene content that `@npc`/`@safety` reach only once
they get past the now-fixed Scene 1A opening blocker. Status: the
grounding-citation and opening-narration-safety fixes are both confirmed
working as intended (proven by `@smoke` passing and by the earlier deterministic
unit tests). `@safety`/`@npc` are now blocked by a separate, newly-exposed
`narration_known_term_leak` issue involving 'message from michelle' and 'hidden
memory card', which is outside the scope of the grounding-citation-reliability
plan and has not yet been investigated. Production promotion remains out of
scope for this pass by earlier explicit decision.

After renaming the colliding 'Michelle's message'/'her message'/'message from Michelle'/'Michelle's note' phrasings to distinctive 'encrypted'-based variants in data/stories/continuity-initiative/knowledge.yaml (commit `cbc427b`), staging redeployed to that exact SHA (confirmed via `/api/v1/version`). With stale artifacts deleted, the focused `@safety|@npc` gate was re-run against staging and both tests now pass (2 passed). Combined with the earlier confirmed `@smoke` pass, all three of `@smoke`, `@safety`, and `@npc` now pass against staging at commit `cbc427b`. `@llm-canon` (the full nine-scene spine judge run) has still not been run. The Phase 5 exit gate in `.plans/fact-backed-knowledge-projection.md` requires it to pass before the gate can be marked fully met. Production promotion remains out of scope for this pass by earlier explicit decision.

`@llm-canon` was attempted twice against staging at commit `cbc427b`/`fcfc6ae` (delete-then-retry, per the hosted canon judge's own procedure). Both attempts aborted identically at the same point: `turn 5: scene 1A at turn 4`, with `Turn API returned HTTP 409: narration mentions unavailable knowledge 'the card'`. Both were discarded per the documented procedure (the progress artifact showed only 1 scene and 4 turns, far short of the required nine scenes/30+ turns). A direct, local reproduction (no staging, no Playwright) of the exact same 4 authored Scene 1A prompts plus a repeated 5th, run through `CloudflareTurnProvider`/`RuntimeEngine` directly, reproduced the identical failure at the identical point. That direct reproduction also showed the real root cause: candidates were genuinely offered starting turn 1 (`k_sl_1a_a_r1`/`r2`), and by turn 3 the player's input ("Recover the interrupted message she was recording, and listen to whatever survives of it") was a near-verbatim match for the then-offered `k_sl_1a_b_r1`/`k_sl_1a_b_r2` candidates -- yet the model selected nothing (`selected_knowledge_ids` empty, no events) across all 4 turns, instead writing vague atmospheric narration each time. The scene never progressed. The eventual 'the card' mention on the repeated 5th turn is consistent with the model's own narrative drifting from the engine's actual committed-fact state after four turns of non-progression, not a leak or alias problem. This is a distinct, separate, and substantially larger issue than the grounding-citation, opening-safety, and alias-collision fixes already landed. It has been scoped as its own follow-up in `.plans/narration-candidate-selection-reliability.md`. `@llm-canon` and therefore the Phase 5 exit gate remain blocked pending that investigation.

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
# Local narration prompt bench — verified 2026-09-03

**Purpose:** Verify the development-only `bench` prompt assembly and archived
judge scoring without spending Cloudflare or OpenAI budget, plus record the
safe boundary for live runs.

**Setup / seed:** Repository checkout on `prompt-bench`; use
`/home/bcorfman/dev/freytag-forge/.venv/bin/python`. Archived fixtures are
read-only under `/home/bcorfman/bakeoff-data/arm-c/run1` and the Arm C system
prompt fixture. Live commands load `.env` and require the worker and judge
environment variables; do not record their values.

**Safe actions:** `bench --help`, `bench prompt`, `bench score`, unit tests, and
ruff checks. These make no model calls and do not modify the archived fixtures.

**Destructive or external actions:** `bench run` spends Workers AI neurons and
OpenAI judge calls. Its default is four replicates; an explicitly requested
single replicate is allowed for focused iteration but cannot estimate noise.
Confirmation is required over the configured neuron threshold. The focused
live check below spent one Scene 1A traversal and one judge call.

**Steps:**

1. Assemble the archived Arm C Scene 1A turn-1 prompt with `bench prompt`.
2. Score the archived Arm C judgment with `bench score`.
3. For the authorized low-cost live smoke, run one explicit replicate of one
   scene and one input script:

   ```bash
   /home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench run --variation bench/variations/arm-c.json --scene 1A --replicates 1 --script e2e --out /tmp/bench-live-single-scene --confirm
   ```

4. Run the focused bench tests and the requested static check.

**Verify:**

```bash
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench prompt --variation bench/variations/arm-c.json --scene 1A --turn 1 --player-input "I search the kitchen and the back door for concrete signs of what happened here - the overturned chair, the forced lock, her phone left on the floor."
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench score --run-dir /home/bcorfman/bakeoff-data/arm-c/run1
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m pytest -q tests/test_bench.py --no-cov
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m ruff check bench storygame
```

Expected: the prompt system is 2,018 bytes and byte-identical to the archived
fixture; the user has five `<beat_detail>` tags and no `<beat>` block; score is
`{"total":12,...,"protected_safe":5}`; the live smoke completes with one
judge call and `n=1`; focused tests pass; ruff passes.

**Cleanup:** Temporary prompt output may be removed from `/tmp`; no repository
or fixture cleanup is needed.

**Notes:** The first live smoke attempt reached the judge bridge but failed
with `ReferenceError: sceneCanon is not defined`; the bridge used the existing
default-package `sceneCanon` export without importing it. Importing both
existing judge exports fixed the failure, and the retry completed with one
judge call, five narration turns, eight narration requests, and an estimated
88 neurons. `AI_QUOTA_EXCEEDED` from the worker is a stop condition; the app
body `{"detail":"rate limit exceeded"}` is retryable. Exact worker neuron
billing is not exposed, so live summaries report exact request counts and a
labeled estimate.

## Prompt bench ledger and story-data overlays — 2026-09-03

**Purpose:** Verify resolved prompt/package hashes, temporary story-package
overlays, append-only ledger rows, and pooled comparison reporting while
preserving the archived Arm C prompt.

**Setup / seed:** Checkout `/home/bcorfman/dev/freytag-forge` on `prompt-bench`;
use `/home/bcorfman/dev/freytag-forge/.venv/bin/python`. The live smoke requires
the variables in `.env`; never print their values. The two requested runs use
Scene 1A, one `e2e` script, and one replicate each.

**Safe actions:** `bench describe`, `bench log`, `bench prompt`, archived
`bench score`, unit tests, the deterministic acceptance checker, and ruff.

**Destructive or external actions:** `bench run` spends one narrator traversal
and one judge call per focused replicate and appends one real row to the tracked
ledger. It never modifies the source story package. Stop immediately if the
worker returns HTTP 429 with `X-Narration-Error-Code: AI_QUOTA_EXCEEDED`.

**Steps:**

1. Check the overlay without a model call:

   ```bash
   /home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench prompt --variation bench/variations/arm-c-overlay.json --scene 1A --turn 1 --player-input "I search the kitchen and the back door for concrete signs of what happened here - the overturned chair, the forced lock, her phone left on the floor."
   ```

2. Source the environment and run the focused real arms:

   ```bash
   set -a && . /home/bcorfman/dev/freytag-forge/.env && set +a
   /home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench run --variation bench/variations/arm-c.json --scene 1A --replicates 1 --script e2e --out /tmp/bench-arm-c --confirm
   /home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench run --variation bench/variations/arm-c-no-example.json --scene 1A --replicates 1 --script e2e --out /tmp/bench-arm-c-no-example --confirm
   ```

3. Inspect and compare only the rows produced by those runs:

   ```bash
   /home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench log --json --variation arm-c --limit 1
   /home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench compare arm-c arm-c-no-example
   ```

**Verify:** The overlay prompt contains the replacement detail and not the old
detail. On 2026-09-03 the final deterministic acceptance commands all passed:
`pytest -q -n 2 --no-cov` reported 243 passed, `check_bench.py --skip-live`
reported PASS, and `ruff check bench storygame` reported All checks passed.
The Arm C live run appended one valid row: score 1/63, 5 narration turns, 8
narration requests, 1 judge call, and an estimated 88 neurons. Three retries of
the no-example `e2e` script and one alternate-script attempt all failed before
scoring with the same non-quota invalid-proposal response, so no row was
written for those failed invocations. This predates the coverage-aware failed
row behavior recorded below.

**Cleanup:** Keep the real ledger rows. Temporary effective package copies and
run artifacts under `/tmp` may be removed after reporting.

**Notes:** `package_hash` is the effective package hash, so package-mismatched
comparisons require `--allow-package-mismatch` and emit a warning.
`spend.neurons` is a request-based estimate because the Worker does not return
billing telemetry.

## Coverage-aware bench ledger and failed replicates — 2026-09-03

**Purpose:** Verify that focused scene scores cannot be pooled with full-story
scores, that alternate ledgers can exercise the guard, and that failed narrator
replicates remain attributable experimental results.

**Setup / seed:** Checkout `/home/bcorfman/dev/freytag-forge` on
`prompt-bench`; use `/home/bcorfman/dev/freytag-forge/.venv/bin/python`.
The tracked ledger is `bench/results/ledger.jsonl`; tests use temporary ledgers
through `--ledger PATH`.

**Safe actions:** Focused tests, `bench log`, `bench compare` against temporary
JSONL, the archived baseline coverage check, acceptance scripts, and Ruff.

**Destructive or external actions:** The two live runs append to the tracked
ledger and spend narrator/judge budgets. Stop if the worker returns HTTP 429
with `X-Narration-Error-Code: AI_QUOTA_EXCEEDED`.

**Steps:**

1. Run the focused bench tests.
2. Use `bench compare --ledger PATH` with matching and mismatched
   `scenes_scored` rows; verify the mismatch names both coverage values and the
   `--allow-coverage-mismatch` override permits the report.
3. Run the authorized Arm C and no-example smoke commands from the preceding
   entry and inspect the newest JSONL rows.

**Verify:**

```bash
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m pytest -q tests/test_bench.py --no-cov
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m pytest -q -n 2 --no-cov
python3 /home/bcorfman/bakeoff-data/check_bench.py --skip-live
python3 /home/bcorfman/bakeoff-data/check_ledger.py
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m ruff check bench storygame
```

Observed 2026-09-03: the full suite reported `248 passed in 15.47s`,
`check_bench.py --skip-live` and `check_ledger.py` both reported `PASS`, and
Ruff reported `All checks passed!`. Successful rows carry `status: "ok"`, `scenes_scored`, `max_score`,
and an actual denominator; failed rows carry `status: "failed"` and
`failure_reason`, remain visible in `log`, and are absent from comparison
statistics. `run --baseline` applies the same coverage guard to an archived
nine-scene `e2e-llm-canon.json`.

**Cleanup:** Keep the real append-only ledger rows and live artifacts; temporary
test ledgers may be discarded. Do not rewrite existing ledger lines.

**Notes:** The Arm C run on 2026-09-03 produced three Scene 1A script scores
`[2, 1, 1]` (aggregate 4/7), 15 narration turns, 24 narration requests, and
three judge calls. The no-example run produced three failed rows after repeated
`INVALID_PROPOSAL` responses (`segments.0:model_type` through
`segments.4:model_type` and `segments:too_short`), with zero judge calls. Neither
run returned the quota-specific 429 header.

## Unknown-scale narration bench ledger rows — 2026-09-03

**Purpose:** Verify that ledger rows without an explicit `scenes_scored`
denominator remain visible but are excluded from comparison statistics, while
known coverage mismatches remain guarded.

**Setup / seed:** Run from `/home/bcorfman/dev/freytag-forge` with
`/home/bcorfman/dev/freytag-forge/.venv/bin/python`. Deterministic fixtures use
temporary JSONL ledgers; the real-ledger comparison reads
`bench/results/ledger.jsonl` and makes no model calls.

**Safe actions:** Read-only tests, lint, deterministic checker scripts, and
`bench compare` against the tracked ledger. No live narration or judge calls.

**Destructive or external actions:** None. The repository and tracked ledger
must remain unmodified; do not run a live `bench run` for this verification.

**Steps:**

1. Run the whole suite with `-n 2 --no-cov` using the project interpreter.
2. Run the four deterministic bakeoff-data check scripts, then Ruff for
   `bench storygame`.
3. Compare `arm-c` with itself against the tracked ledger and inspect the
   skip message and reported n.

**Verify:**

```bash
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m pytest -q -n 2 --no-cov
python3 /home/bcorfman/bakeoff-data/check_bench.py --skip-live
python3 /home/bcorfman/bakeoff-data/check_ledger.py
python3 /home/bcorfman/bakeoff-data/check_coverage.py
python3 /home/bcorfman/bakeoff-data/check_neutral.py
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m ruff check bench storygame
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench compare arm-c arm-c
```

Expected: rows missing or null `scenes_scored` are identified as unknown or
legacy and reported as skipped; they contribute to neither arm's n or any
statistic. Known rows with differing scene counts still fail unless the
coverage override is supplied. The tracked ledger remains byte-for-byte
unchanged.

**Cleanup:** None.

**Observed 2026-09-03:** The focused bench tests reported `20 passed in 1.11s`;
the full suite reported `252 passed in 15.06s`. `check_legacy.py`,
`check_bench.py --skip-live`, `check_ledger.py`, and `check_coverage.py` all
reported `PASS`. `check_neutral.py` remains a pre-existing failure because
`bench/variations/arm-c-neutral-example.json` and its ledger evidence are not
present; this fix does not create a new variation, criterion, or live result.
`ruff check bench storygame` reported `All checks passed!`. Against the real
ledger, `bench compare arm-c arm-c` reported one skipped legacy row and
`n=3 mean=1.33 sd=0.58` for each side, with Welch `p=1.0000` and minimum
detectable effect `4.47`.

**Cleanup:** None. The tracked ledger remained 5 lines and was not rewritten or
appended to during verification.

**Notes:** Do not rewrite or backfill the legacy ledger row.

## Neutral output example and leakage metric — 2026-09-03

**Purpose:** Verify that a custom output example preserves the narrator's JSON
shape without carrying the drawer prose, and measure reuse of any configured
example in successful narration turns.

**Setup / seed:** Checkout `prompt-bench`; use
`/home/bcorfman/dev/freytag-forge/.venv/bin/python`. The live runs require the
environment variables in `.env` and spend Workers AI plus judge budget.

**Safe actions:** Prompt assembly, variation description, unit tests, the full
suite, acceptance scripts, and Ruff. Do not run the browser E2E suite locally.

**Destructive or external actions:** The authorized neutral run uses three
replicates and the declared Scene 1A scripts; the no-example run uses one
replicate and the same scripts. Both append real rows to the tracked ledger.
Stop if the narration endpoint returns HTTP 429 with
`X-Narration-Error-Code: AI_QUOTA_EXCEEDED`; retain whatever real rows exist.

**Steps:**

1. Verify `arm-c` prompt byte identity and inspect all three resolved examples
   with `bench prompt` and `bench describe --json`.
2. Source `.env`, then run the exact neutral and no-example commands from the
   task specification, without hand-writing ledger rows.
3. Run the full suite, three bakeoff-data acceptance checks, and Ruff.

**Verify:** Successful rows contain integer `example_leakage`; failed rows
contain `status: "failed"` and `failure_reason`. The neutral system prompt
contains `<output_example>` with `segments`, `kind`, and
`selected_knowledge_ids`, but none of the drawer example's distinctive prose.

**Cleanup:** Keep real ledger rows and requested run artifacts. Temporary
test-ledger files may be removed; never rewrite existing ledger lines.

**Notes:** The metric counts a turn when narration and the resolved example
share at least eight consecutive words after case folding and whitespace
normalisation. A no-example configuration scores zero by definition. Observed
on 2026-09-03: the neutral run had 5 judgeable script-replicates and 4 failed
replicates, scores `[0, 1, 1, 1, 1]`, total 4/7, leakage 0, and 5 judge calls;
the no-example run had 3 failed replicates, zero judge calls, and no score. The
full suite reported `257 passed`; `check_bench.py --skip-live`,
`check_ledger.py`, `check_coverage.py`, and `check_neutral.py` all reported
`PASS`; Ruff reported `All checks passed!`.

## Portable archived bench fixtures — 2026-09-03

**Purpose:** Verify the archived Arm C scorer and prompt contracts without
depending on the author's machine-specific bakeoff directory.

**Setup / seed:** The repository fixtures live under
`tests/fixtures/bench/`. The archived run includes `summary.json` with
`scenes_scored: 9`, `max_score: 63`, and `replicate_scores: [12]` so baseline
comparison preserves its real nine-scene refusal path.

**Safe actions:** Run the deterministic suite, Ruff, and the repository checks
below. No live model calls or external writes are needed.

**Destructive or external actions:** None.

**Steps:**

1. Run the full pytest suite with the repository virtualenv interpreter.
2. Run Ruff and all five bakeoff-data checks.

**Verify:** The suite remains at or above the 90% coverage gate; the scorer
returns the archived 12/63 result; the prompt fixture remains byte-identical;
and the archived nine-scene baseline is rejected before live work.

```bash
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m pytest -q -n 2
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m ruff check bench storygame tests
python3 /home/bcorfman/bakeoff-data/check_bench.py --skip-live
python3 /home/bcorfman/bakeoff-data/check_ledger.py
python3 /home/bcorfman/bakeoff-data/check_coverage.py
python3 /home/bcorfman/bakeoff-data/check_neutral.py
python3 /home/bcorfman/bakeoff-data/check_legacy.py
```

**Cleanup:** None. Do not rewrite the tracked ledger.

**Notes:** Tests resolve every archived path from `Path(__file__)`; the
acceptance scripts under `/home/bcorfman/bakeoff-data` remain orchestrator
tooling and are intentionally outside this portability boundary.
Observed 2026-09-03: the full suite reported `262 passed in 39.86s` and
`90.43%` coverage. Ruff and each of `check_bench.py --skip-live`,
`check_ledger.py`, `check_coverage.py`, `check_neutral.py`, and
`check_legacy.py` reported `PASS`.

## Authored reveal handoff Phase 0 contract

**Purpose:** Verify the Phase 0 migration boundary: authored handoff is
opt-in, legacy candidates keep the LLM-proposal path, and existing runtime
state remains compatible with save/load.

**Setup / seed:** The checked-in `continuity-initiative` package and Python
dependencies installed with `uv sync --group dev`.

**Safe actions:** Run the deterministic save/load regression. It uses a
temporary SQLite snapshot under pytest's temporary directory.

**Destructive or external actions:** None.

**Steps:**

1. Run the projection/save-load regression for the existing fact-backed state.
2. Review the Phase 0 contract in `.plans/authored-reveal-handoff.md` and
   `docs/PRD.md`.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q --no-cov tests/test_knowledge_projection.py::test_projection_is_stable_across_turn_recording_and_save_load
```

Expected: the test passes, proving that save/load preserves the runtime state
needed to reproduce the same knowledge projection. The Phase 0 docs state that
adding authored delivery changes delivery only, not fact IDs or package
effects.

**Cleanup:** Pytest removes its temporary SQLite snapshot.

**Notes:** Added 2026-09-11. This phase changes documentation only; the
authored-handoff runtime remains disabled until later phases add and validate
the package data and decision path.

## Authored reveal handoff Phase 1 loader contract

**Purpose:** Verify optional package-owned delivery text, its load-time
conveyance and bookkeeping checks, and legacy evidence-only candidates.

**Setup / seed:** The checked-in `continuity-initiative` package, temporary
copied-package fixtures, and Python dependencies installed with
`uv sync --group dev`.

**Safe actions:** Run the focused loader and projection tests, Ruff, and the
full local suite. Tests write only temporary copied packages.

**Destructive or external actions:** None.

**Steps:**

1. Run the Phase 1 loader and projection tests.
2. Run Ruff autofix and formatting.
3. Run the full Python suite.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q --no-cov tests/test_markdown_story_package.py tests/test_knowledge_projection.py
uv run ruff check --fix . && uv run ruff format .
TMPDIR=/tmp uv run pytest -q
```

Expected: complete authored handoff data loads, its delivery text is absent
from runtime model serialization, incomplete handoffs are rejected before
play, and the legacy package still loads. Ruff and the full suite pass.

**Cleanup:** Pytest removes temporary package copies. None required.

**Notes:** Added 2026-09-11 for Phase 1 of
`.plans/authored-reveal-handoff.md`. The handoff remains disabled because no
shipped candidate has `delivery_text`; Phase 2 owns runtime matching and Phase
3 owns composition.

Observed 2026-09-11: the focused loader/projection command passed 76 tests;
Ruff passed after formatting one test file; the full suite passed 367 tests
with 91.54% coverage. After narrowing the internal-token guard to allow
player-facing entity names, the focused command and full suite were rerun and
passed with the same results.

## Authored reveal handoff Phase 3 composition contract

**Purpose:** Verify that one exact authored match becomes an ordinary narration
segment before the existing resolver, safety checks, effects, and atomic commit.
Model selection and candidate grounding are ignored for that matched handoff;
legacy candidates retain their existing path.

**Setup / seed:** The checked-in `continuity-initiative` package, an in-memory
test copy with one candidate given `delivery_text`, and Python dependencies
installed with `uv sync --group dev`. If `.venv` is stale or incomplete, repair
it with `uv sync --reinstall`.

**Safe actions:** Run the focused transport/safety tests, Ruff, and the full
local suite. Tests use an in-memory package and do not alter the checked-in
story data.

**Destructive or external actions:** None.

**Steps:**

1. Run the authored-handoff composition and safety tests.
2. Run Ruff autofix and formatting.
3. Run the full Python suite.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q -o addopts='' tests/test_cloudflare_transport.py tests/test_candidate_matcher.py tests/test_narration_safety.py
uv run ruff check --fix . && uv run ruff format .
TMPDIR=/tmp uv run pytest -q
```

Expected: a matched handoff returns the exact authored sentence with the
candidate grounding and selected ID, then commits through the normal effects
path. Invalid surrounding prose rejects the composed proposal and leaves the
full pre-turn state unchanged. No new public segment kind or bookkeeping field
appears.

**Cleanup:** None.

**Notes:** Added 2026-09-12 for Phase 3 of
`.plans/authored-reveal-handoff.md`. The handoff remains opt-in and disabled in
ordinary play because no checked-in candidate has `delivery_text`.

Observed 2026-09-12: the focused command passed 103 tests; Ruff passed; the
full suite passed 376 tests with 91.60% coverage.

## CI test-suite overlap and timing investigation

**Purpose:** Verify the tests that run on push and pull request in the
`tests` workflow, and identify duplicate or misclassified coverage that makes
those jobs slower.

**Setup / seed:** A clean checkout with the locked Python dependencies. The
workflow's required gate uses `TMPDIR=/tmp uv run pytest -q --cov -n 2`.

**Safe actions:** Collection, timing, and local deterministic test runs only.
No provider, deployment, or hosted request is made.

**Destructive or external actions:** None.

**Steps:**

1. Inspect `.github/workflows/test.yml` and `tests/conftest.py` for the three
   required CI jobs and their test markers.
2. Run the fast-feedback selection with `--durations=20`.
3. Run the required coverage command with its health report under `/tmp`.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q --no-cov -m "(unit or component) and not authoring_quality" --durations=20
TMPDIR=/tmp uv run pytest -q --cov -n 2 --tier-report=/tmp/test-suite-health.json
```

Expected: the full gate remains green at or above 90% total branch coverage;
fast feedback contains only unit/component runtime-safety tests after the CI
selection is tightened. On 2026-09-12 before the change, collection reported
378 total tests, 323 unit/component tests, and 61 authoring-quality tests;
the serial fast-feedback diagnostic passed 323 tests in 39.40 seconds. The
serial full baseline passed 378 tests in 109.62 seconds at 91.63% coverage.

**Cleanup:** Remove only temporary reports under `/tmp` if no longer needed.

**Notes:** The cutover job and fast-feedback job both repeated the same
61-file authoring suite that the required gate already runs. The leakage
matrix and Phase 3/4 evidence tests are deterministic package/runtime
boundary checks, not fast unit feedback; their required-gate coverage remains
the source of truth after reclassification.

Observed after the change on 2026-09-12: the changed fast-feedback command
collected and passed 257 tests in 16.16 seconds, with zero authoring-quality
tests selected. The unchanged required-gate command passed all 378 tests in
60.02 seconds at 91.63% coverage. The cutover job's remaining Ruff command
also passed.

The loader follow-up caches YAML parsing by file content and deep-copies the
cached value for each load. The 61-test Markdown package module then passed in
8.49 seconds wall time. The required-gate command passed all 378 tests in
25.86 seconds at 91.64% coverage, down from the 60.02-second pre-cache run;
no tests were skipped from the required gate.
