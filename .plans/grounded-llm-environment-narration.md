# Reliable environment narration without per-item engine prose

Status: implementation proposal, 2026-10-25. Reviewed local baseline `14f11314`.
No runtime changes, new live experiments, model switch, or deployment were made
while writing this plan. Historical measurements below are not fresh results.

## Resume here

T1, T2, T3a, T3b and T3c are done (records below). Start at **T5** (billed screen; needs Brandon's approval of `.plans/grounded-llm-environment-narration/t5-screen-prereg.md` and a bench Worker first), then complete tasks in order. T1–T4 prepare a concrete, free
experiment; T5 is the first billed gate. Do not restart the old prompt-tweaking
queue. This plan supersedes the proposed engine-written empty-search response
in the 1A continuity plan and supplies the replacement path for its boarding
workaround. Preserve its other fixes and unfinished verification.

Speed requirement (Brandon, 2026-10-25): narration must have a fast response
time. It is a gate, not a note: see the T5 preregistration (narration call p95
<= 5 s and p50 <= 2x the baseline model, numbers pending his confirmation).
DeepSeek runs at `reasoning_effort: low` in the Worker profile; whether to also
test `none` is an open choice there.

The user's requirement is LLM-written environmental prose across interchangeable
stories. Do not meet a test by adding `notice_text`, fixed sentences, a truck
branch, a command whitelist, or a package-specific narrator rule. Facts and
typed validation remain deterministic. They do not have to become prose.

For each task, record: status, commit, changed paths, exact checks/results,
artifact paths, unresolved defects, and next task. Keep only one task in progress.
After a context reset, read this section, the task table, and the last completed
record before editing. Failed experiments are results, not permission to lower
the bar or add a fallback sentence.

Existing workflow: code changes use the continuity plan's Ringer/Luna-high
tasks, tests first, focused checks between tasks, one final full suite. This
document is detailed enough for Sonnet to coordinate that work; the recommended
routine coordinator is now Opus (section below). No new delegation ran for this
planning task. Preserve the existing requirement for user-approved billed
preregistrations; prepare the fixtures, harness, counts, and cost estimate before
requesting that approval. Planning does not authorize deployment or paid runs.

## Diagnosis and evidence

Read: PRD, contributor, world-model-grounding, narrator-writing, player-input,
scene-fixing, agent-workflow, testing-runbook, railway-production-promotion,
and jev-guard-rules. Also read the active reimagination and continuity plans,
the boarding/open-defect preregistrations, and historical W1–W14 plus amendments
at `5ea0119955c62b84699a8dc7878a4af770b55a7e:.plans/world-model.md`.

| Evidence | Conclusion and limit |
| --- | --- |
| [Boarding probe](1a-transcript-continuity/boarding-probe-prereg.md): control 0/30; steps-as-action 1/30; added rule 3/30; laptop in THINGS 5/30 | Those interventions failed with that prompt/model. This does not test a stronger model or a complete perceptual view. Three nominal command cases collapsed to one identical prompt. |
| Same probe: steps-as-action caused exits in 11/30; original boarding command was consumed; THINGS originally held only Kristin | Replacing the action with background prose makes the task ambiguous. Restore the action as information, not as permission to execute it twice. |
| Historical W9 amendment: opening a drawer invented contents in 15/15 recorded samples, 0/15 when actual contents were supplied | Material availability can be decisive. Closed-container context is useful for resolving an opening action, but is not permission to describe concealed contents before opening. |
| [Open-defect probe](1a-transcript-continuity/postfix2-open-probe-prereg.md): past/drop arms still invented replacement objects; no arm won | Removing old card text is insufficient. Absence, search scope, and whether new objects may be created need explicit semantics. |
| Continuity step 13 / `14f11314`: spurious reference matches admitted outside objects into house prompts; expansion also needed filtering | Keep that fix. Do not solve omission by dumping every scene entity into the narrator. |
| Continuity step 10 / `fa3c837d`: laptop custody echo could hide a later notice | Prose quality and state consistency must be scored independently. A model switch cannot fix a bad projection. |
| Scene-fixing guide: go-into-place, plain-corridor, copy-refers rules lost; concrete material and one dialogue rule succeeded | Do not grow a permanent list of prohibitions. Test distinct causes. |
| Historical W1/W4/W7/W9 | Preserve name resolution, fact authority, one-way effects and hidden-item protection. Do not resurrect regex place parsing, English composed from the tree, or a global ban on model-created objects. |

Source findings, distinct from hypotheses:

- `worker/src/index.js` defaults to `@cf/meta/llama-3.1-8b-instruct-fast`.
  `CF_AI_MODEL` may override it: the deployed model was **not** verified here.
  `worker/src/budget.js` prices that exact default and Jev only. A model change
  also needs an explicit price entry and transport compatibility checks.
- `ItemFactsProvider._thing_names` begins with selected/dependency names and
  expands contents/seats, then filters reach. It is not a complete observer
  view. The recent filter remains important, but relevance, reach and sight
  are different questions.
- `WorldCapture.before_turn` performs implicit moves before narration.
  `ItemFactsProvider._player_lines` replaces a consumed command with prior-step
  text. `ItemFactsProvider.__call__` directly emits those steps for boarding.
- `seating.board_vehicle` adds authored item `notice_text` to those steps;
  its already-seated branch also generates a generic English sentence.
  Most existing story wording lives in package data, not literal Kristin
  branches in shared code. That preserves some interchangeability, but still
  imposes per-item prose authoring and bypasses the requested narrator.
- `RuntimeEngine._turn_active` has a pre-turn snapshot and bounded guard retry,
  but item-fact application is in `capture.after_commit`. A new semantic gate
  cannot simply run after that method and leave mutated state behind.

The proposed solution is a bounded **observation contract**: project facts,
identify what this action needs described, have the LLM write it, and reject or
repair an inadequate description before publishing the turn. This is a new,
measured technique, justified because the existing prompt remedies failed.
It is not a guarantee that unconstrained natural language becomes infallible.

## Required architecture

### 1. Separate the player's view from movement permission

Add an immutable typed `ObservationContext` projection, built from the working
fact snapshot and validated package declarations. Suggested internal fields:
observer, requested action, completed implicit actions, visible things,
action-contingent contents, known-but-not-visible references, required mentions,
and search-scope completeness. Internal entity IDs are fine inside the engine;
the narrator receives unique public names and short fields, never IDs, the full
tree, protected reveals, or future routes.

Reuse worldkeeper's current hidden/closed/container/custody machinery. Audit
`is_visible` before treating it as observer-relative line of sight. Do not infer
sight from `together()` alone. First implement same-view contents and carried
items. If an exterior-to-interior view is needed, represent it as a generic,
validated package view connection with opening/opacity conditions; do not infer
that every vehicle is transparent or every room sees its siblings. Add that
schema only when a test demonstrates the current declarations cannot express
the view. Engine code must never name a truck, laptop, Kristin, or a scene ID.

Being on the driver's seat is not an epistemic prerequisite. An explicit look
through an unobstructed window can reveal public contents while the player stays
outside. An opaque, shut container cannot. A known item named by the command
can be identified without asserting that it is visible or reachable. Hidden
story items remain excluded until the existing reveal contract earns them.

The latest broad approach-to-boarding behavior was a workaround, not the target.
Restore the distinction between approaching and boarding using the existing
bounded intent proposal mechanism. No exact-verb dispatch table. An ambiguous
reference is clarified; it does not silently select the only helpful seat.

### 2. Give the narrator a small, complete task

Keep the original player action. Supply completed implicit actions separately
as typed facts projected into short fields. State that those actions have
already occurred and ask for their result; never feed imperative engine steps
as though they were a fresh command. For observation, include the visible
contents of the requested scope even when the player has not named them.

Required mentions derive from the task and facts: the directly inspected item,
the visible contents of a small inspected container, and relevant items newly
exposed by opening or entering. Do not require every object in a region on every
turn. Use stable selection and a token budget; retain required items and drop
optional detail first. If required content cannot fit, report/clarify the scope
instead of silently dropping an item. Record omitted optional items in telemetry.

Use public place/holder/state labels as the grounding guide specifies. Do not
generate English placement sentences from the containment chain. Package
descriptive attributes may be optional material, but correct naming and location
must work with names, kinds, placements and facts alone. `notice_text` must not
be required or used as an emergency player-facing appendage on the new path.

Maintain existing reveal handoffs in this slice. They concern earned plot
information, not ordinary environment description. Do not migrate all authored
story prose, bridges, refusals and dialogue in one change. Report this boundary
honestly; eliminating the boarding workaround is not eliminating all authored
text in the game.

### 3. Represent absence without inventing a discovery

An unlisted object is not automatically nonexistent: this engine permits new
objects. Do not turn W9 into a global closed-world policy.

For a bounded search, derive the known contents after current custody/moves and
eligible reveal effects. Distinguish `known_contents` from `contents_complete`.
If completeness is not expressible today, introduce a generic optional
container/search-scope declaration, with an open-world default and loader tests.
It is data about the world, never an authored empty-search sentence. Only a
complete, empty scope licenses an unqualified empty result. An incomplete scope
does not license a replacement clue, a new dependency, or re-finding a held item;
any genuinely new object still needs the normal validated proposal path.

If a complete scope forbids additions, enforce that at structured creation
validation, not by scanning prose for nouns. Independently judge unsupported
objects in prose during evaluation. Do not pretend the structured guard detects
every unreported narrative invention. On the new path, a searched place's prose
is written by the model, including when nothing relevant remains there.

### 4. Check prose, not the model's self-report

Initially keep the current response contract. A `mentioned_items` list or a
coverage boolean alone proves nothing and must never be accepted as evidence.
An optional evidence span must actually occur in the displayed narration, and
still needs semantic assessment: “the laptop is missing” contains its name.

Build a narrow injectable observation verifier. For each required relation,
ask whether the final displayed narration actually describes that named thing
at its permitted place/holder, without contradicting the accepted action result.
Use the existing typed Jev client for a **shadow** experiment first; the
[Jev guide](../docs/jev-guard-rules.md) supports short fact questions, not an
universal “did it invent anything?” question. Calibrate against hand-labelled
positive, negated, hypothetical, wrong-holder and wrong-seat examples across
stories. Never treat Jev confidence as a probability of correctness without
calibration. If it cannot meet the false-accept gate, do not enable it as a guard.

Production budget proposal: at most one batched observation-verifier request
per narration attempt (at most two per turn), separately metered and documented;
no extra narration request beyond the existing initial plus shared recovery.
This is an explicit contract addition, not a free or existing call. Unknown,
timeout or low-confidence verification fails closed. Repair uses the same
safe context and generic failure code; follow the existing rule against naming
an untyped rejected term in feedback. Never forward hidden facts or raw unsafe
output as repair instructions. Revalidate everything after the repair.

Before enabling, preview captured item-fact changes on the candidate snapshot
and validate the prose against that candidate. Reject unrelated custody drift
on an observation action and all already-forbidden moves. Do not apply a
different set of effects after the verifier approves. Use the same validated
candidate for publication/commit; preserve game-break resume and exact rollback.
This is a scoped transaction change, not authorization to restart the parked
whole-engine outcome-first redesign.

On exhaustion, return the existing typed unsuccessful turn/service response
with no environmental assertions and restore the pre-turn snapshot. Count that
as an unsuccessful player turn. A guard that rejects every turn is not success.
Do not fall back to engine item descriptions or stream unvalidated prose.

## Cloudflare narrator recommendation

Check availability again at implementation time and record the actual model
and revision from every run. Start the comparison with the current configured
model, **Llama 3.3 70B FP8 Fast** as the simpler non-reasoning upgrade, and
**DeepSeek V4.1 Flash 1017** as the primary higher-capability candidate. This
ranking is an engineering hypothesis, not a measured game-quality ranking.

| Candidate | Documented cost per million input/output tokens | Proposed role |
| --- | --- | --- |
| `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | $0.293 / $2.253 | Lower integration risk comparison; 24k context is ample for bounded scene context. |
| `@cf/deepseek-ai/deepseek-v4.1-flash-1017` | $0.30 / $1.20 | First stronger candidate; start at `low` reasoning, measure time and quality. Paid Workers or prepaid Gateway credits required. |
| `@cf/zai-org/glm-5.3` | $1.40 / $4.40 | Conditional escalation if the first screen fails; use `low`, not its default `max`. Reasoning cannot be disabled. Paid access required. |

Official sources checked 2026-10-25:
[Llama](https://developers.cloudflare.com/workers-ai/models/llama-3.3-70b-instruct-fp8-fast/),
[DeepSeek](https://developers.cloudflare.com/workers-ai/models/deepseek-v4.1-flash-1017/),
[GLM](https://developers.cloudflare.com/workers-ai/models/glm-5.3/),
[pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/).
These documents establish availability and interfaces, not narration reliability.

At 2,000 input and 500 output tokens, a DeepSeek call is approximately $0.0012
before extra reasoning, recovery, matching and verification. Use measured billed
usage for estimates. Do not count free allocation as an unlimited budget.

The Worker currently clamps `max_tokens` to 64–2048. Add typed, model-specific
parameter/envelope handling before testing a reasoning model. Confirm supported
`reasoning_effort`, `max_completion_tokens` versus `max_tokens`, JSON output,
reasoning/final separation, truncation and usage accounting. Do not display
reasoning as narration. Explicitly price every candidate; preserve authentication,
quota errors, reservation/settlement and revision headers. Keep model selection
server-controlled. A benchmark model override is not a new public API knob.

A larger model cannot recover an item omitted from its context or correct an
engine-imposed viewpoint. Conversely, if a stronger model with the minimal safe
projection passes, do not build a multi-agent narrator, a prose compiler, or a
large new response language merely to complete this proposal.

## Fine-grained implementation queue

Each row is one reviewable task. New paths below are proposals; existing symbols
were inspected at the baseline. Rediscover symbols with codebase-memory first;
use Serena for edits when available. Do not assume line numbers remain stable.

| Task | Work and expected artifact | Exit condition |
| --- | --- | --- |
| T1 | Freeze baseline evidence under a new `scripts/ringer/environment_narration/` harness. Reuse `transcript_1a/boarding_probe.py` plumbing, not its collapsed command assumptions. Save exact system/user payloads, state hashes, model identity and expected observations. | Offline fixtures reproduce the consumed-command/laptop omission and identify engine-text turns; no network. Record missing historical artifacts instead of fabricating them. |
| T2 | Add a matrix of observation/viewpoint tests (below), including a second synthetic package with no notice/seat prose. Audit worldkeeper visibility and document the minimum schema change. | Failing tests describe player outcomes and safe context, not prompt substrings; existing hidden/reach tests stay unchanged. |
| T3 | Implement the pure `ObservationContext` projection in a small new runtime module; wire prompt capture behind an internal experimental option. Preserve action and separate completed steps. Add generic visibility/search completeness declarations only where T2 proves the need. | Projection is repeatable, safe and state-derived; stale labels disappear after moves; package swap needs no engine edit. All new paths are exercised offline. |
| T4 | Add candidate model profiles to typed transport, Worker price accounting, test-only harness configuration and response normalization. Build checker/dry-run mode and preregistration with exact counts and USD ceiling. | Worker/Python transport tests cover success, malformed JSON, reasoning-only, truncation, timeout, quota and exhausted recovery; no deployed/default model change. |
| T5 | Run the approved model/context screen described below. Read every output. Record first-attempt prose, required-item recall, relation errors, inventions, latency and cost separately. | A candidate advances on the preregistered rule. A losing screen stops; do not add story prose or retune against confirmation fixtures. |
| T6 | Integrate the winning minimal projection/model path. Keep explicit boarding facts but return narration through the model, including already-seated results. Restore approach versus board. Retire use of item notices on this path. | Existing boarding/custody/reach regression suites plus synthetic vehicle and nonvehicle tests pass. No player must board merely to obtain a view. |
| T7 | Build the narrow observation verifier and labelled calibration corpus; run in shadow only. Add explicit verifier budget and failure telemetry. | Calibration report includes false accepts and false rejects per case type, model/version and uncertain answers. No enforcement until the gate passes. |
| T8 | Add candidate item-fact preview and one shared recovery path; place observation validation before publication and canonical commit. Update snapshot/context serialization only as needed. | Fault-injection tests prove exact rollback on every failure and game-break resume; no double seating, repeated pacing, hidden feedback, stale item facts or third narration call. |
| T9 | Confirm the integrated behavior on withheld fixtures and closed-loop sequences; compare prose against committed state, not raw `item_facts`. | Quality, acceptance, safety, latency and authoring-burden gates all pass. Preserve failures; no replacement samples. |
| T10 | Remove the superseded boarding engine-text shortcut from the chosen production path, adjust tests which pinned it, and make notice/seat prose optional where the replacement supports it. Update guides in place. | A second package runs with no per-item environmental sentences. Existing authored reveal handoffs still work. Record any retained legacy compatibility paths explicitly. |
| T11 | Ruff autofix/format, focused checks, one full coverage suite, CI and SHA-bound staging verification under existing workflow; then update this plan. | ≥90% coverage, required checks green, staged player-visible run passes on exact SHA. Production promotion remains separate. |

T3 may need a test-only bypass of `command_consumed` engine text to capture the
experimental narrator payload. Keep that bypass out of the production default
until T6. T8 is the riskiest code task: split preview, retry integration and
save/resume into separate Ringer tasks if one diff would span too many concerns.

### Regression matrix for T2/T6/T8

| Case / representative player input | Required behavior |
| --- | --- |
| `Enter the truck.` | Seat once; model describes the visible laptop at its actual current place; no driving or exit. |
| `Approach the truck.` | Approach stays outside; no forced boarding merely to improve narration. |
| `Look through the truck window.` | With an explicitly unobstructed view, laptop can be described from outside; player position unchanged. With opaque/blocked view, interior remains withheld. |
| `Inspect the passenger seat.` | Describe actual visible contents; do not put a held or moved laptop back there. |
| `Examine my laptop.` after carrying it elsewhere | Correct current holder/place, no stale seat label and no duplicate laptop. |
| `Open the drawer.` | Public contents are available to resolve opening; hidden story item stays protected until earned. |
| `Inspect the closed drawer.` | Public exterior only; contingent contents must not be described as already seen. |
| `Search beneath the drawer.` after recovery | Never re-find the held card. A complete empty scope yields LLM-written absence, not a replacement clue. |
| `Enter the truck and inspect my laptop.` | Preserve both actions; complete implicit moves once; no residual-action loss. |
| `Examine the kitchen.` | Outside objects do not enter through noisy refers or seat/content expansion. |
| Synthetic observatory: `Inspect the telescope tray.` | Same coverage and custody semantics for a lens, with no Kristin vocabulary or notice text. |
| Synthetic boat: `Board the skiff.` | Same observation behavior with differently named cargo and seats; no runtime changes. |
| Large view, ambiguous names, missing placements | Required items are not silently truncated; clarify ambiguity; never resolve an unknown place to a plausible remote seat. |
| Repair/error/save/load/game-break | Facts, aliases, pending facts, turn counters, cue delivery and capture context remain consistent; no successful text on a rejected turn. |

Write all authored test inputs in the player-input guide's imperative voice.
Historical raw inputs in archived transcripts remain verbatim evidence, not new
probe examples. Synthetic declarations must obey the grounding guide too.

### Experiment and adoption gates

T5 draft design, to finalize and price in its preregistration:

1. Six frozen starts: boarding, outside view, moved/held item, drawer opening,
   searched scope after recovery, and unrelated nearby-area observation. Use
   three matched models (actual baseline, Llama 70B, DeepSeek) and two contexts
   (reconstructed existing narrator path, proposed observation context).
   Ten samples per cell: **360 narration requests**, plus a separately capped
   six-call transport smoke. Interleave order. No runtime verifier in this
   causal screen, no retries or replacement samples. Scoring is manual.
2. Record both prompts in every paired comparison. Existing context may be
   missing required material: label this as a projection failure, not purely a
   model failure. Do not reintroduce hidden information to make an arm pass.
3. Advance only a proposed-context model with at least 9/10 fully correct
   outputs in **each** family, no protected disclosure, no unrequested movement
   and no unsupported actionable discovery. This is a screen, not reliability
   proof. If none advances, report the failed layer. GLM escalation requires its
   own fixed preregistration, not an endless parameter search.
4. T7 calibration: at least 200 labelled short cases, balanced correct/incorrect,
   including unseen names and genre, with deliberate negation/wrong-place and
   unreported-invention cases. Freeze labels before scoring. Gate: zero observed
   false accepts on required relations and at most 5% false rejects, reported
   by category. Limited sample confidence must be stated. Do not claim this
   proves detection of all invented objects; it does not.
5. T9 confirmation: 12 withheld start states × 25 attempts = **300 player
   turns**, at most 600 narration and 600 batched verifier requests. Item-name
   matching has its separate existing cap and must be costed too. Add six
   independent six-turn sequences in each of two packages: **72 turns**, with
   separately counted calls. No tuning on these fixtures. Stop and preregister
   a new confirmation set after any material change.
6. Proposed acceptance target: at least 95% first-attempt complete/correct
   narration and at least 99% successful turns after the one recovery overall;
   at least 24/25 successful turns in each fixture; zero observed hidden leaks,
   wrong custody/place, unrequested moves or unsupported actionable objects in
   accepted prose; zero new engine-written environmental sentences. Report
   Wilson/binomial intervals and each family separately. These are acceptance
   targets, not claims of a statistically proven 99% population success rate.
7. Measure end-to-end p50/p95, including matching, verifier and recovery. Target
   p95 <10 seconds on the normal path. Reject a nominal quality win that causes
   excessive rejected turns or unusable latency; report recovery-path latency
   separately. Record billable usage and cost per **successful** turn.

All caps are maxima, not targets. Preregister total narration, matching,
verification and any judge calls and USD ceiling; stop on quota/budget errors,
retain partial rows, never silently rerun an arm. Preserve the source SHA,
package hash, model ID/revision, settings, prompts, raw response, final visible
text, before/candidate/after facts and verdicts. A judge may assist annotation;
the generator must not certify its own outputs. Human review remains the
reference. Small samples and repeated identical prompts limit generalization.

### Verification map

Use [testing-runbook](../docs/testing-runbook.md), updating existing entries
when the actual procedures change. Do not put future unbuilt commands there.
Current relevant files include:

- `tests/test_boarding.py`, `test_boarding_engine_text.py`,
  `test_boarding_already_seated.py`, `test_seating.py`;
- `tests/test_referred_reach.py`, `test_held_by_echo.py`,
  `test_staged_cue_reach.py`, `test_narration_safety.py`;
- `tests/test_cloudflare_transport.py`, `test_web_demo.py`,
  `test_markdown_story_package.py`, and Worker tests under `worker/test/`.

Commands already documented: `TMPDIR=/tmp uv run pytest -q --no-cov <files>`,
`uv run python scripts/quick_suite.py`, `node --check worker/src/index.js`,
Ruff autofix/format and final `TMPDIR=/tmp uv run pytest -q --cov`. Verify the
Worker package's test command before using it. New proposed modules need their
own focused suites. Offline prompt checks prove context, not model compliance.
Hosted checks follow main CI deployment and exact-SHA verification; a local
replay is not staged E2E evidence.

## Claude choice for routine project work

**Recommendation: keep Luna for implementation; use Claude Opus 5.5 at Medium
as the routine coordinator/reviewer, escalating to High for cross-module
debugging, transaction boundaries and interpreting conflicting experiment
results.** This is for daily engineering, not a recommendation to do every task
as a planning exercise. Keep Luna Medium for well-bounded edits and High for
harder implementation, subject to existing task-specific Ringer instructions.
There is no project evidence here that replacing the worker would help.

If cost makes Opus undesirable, try Sonnet 5.5 **High** for orchestration before
rejecting Sonnet entirely. Keep Sonnet Medium for self-contained tasks with
explicit acceptance criteria. Do not use Max by default. Anthropic documents
Opus 5.5 as intended for long-running agentic coding with Medium default, and
Sonnet 5.5's API default as High; application defaults can differ.
[Opus documentation](https://platform.claude.com/docs/en/models/opus-5-5/overview),
[Sonnet documentation](https://platform.claude.com/docs/en/models/sonnet-5-5/overview),
[effort/model selection](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model).

That recommendation is a project-specific inference, not a measured comparison
on this repository. Orchestration here requires retaining design constraints
across many successful local patches; it is not merely dispatching workers.
The old probe explicitly prescribed engine prose if every arm lost, and the
record says that fallback was approved. Following that branch does not itself
prove Sonnet lacks capability. The new user instruction changes the objective;
update the working contract as well as the model.

Give the coordinator this short implementation brief on every task:

> Preserve freely interchangeable story packages and LLM-written environment
> prose. Complete the next task in this plan. A passing local test is not proof
> of live narration quality. Do not introduce per-item fallback text, weaken a
> gate, or call a failed model experiment an engine limitation. Report remaining
> failure modes and update the resume record before starting another task.

Evaluate the coordinator switch over 10–15 comparable routine tasks. Track
first-review acceptance, missed design constraints, rework, wall time and total
cost including workers. Keep changes bounded so a stronger coordinator does
not start rewriting unrelated systems. No Claude configuration was changed by
this planning task.

## Completion record

- Planning complete: source/docs/history reviewed; current official Cloudflare
  and Claude documentation checked; no runtime or provider tests run because
  this change contains only plans. No paid requests or deployments performed.
- T1: **done 2026-10-25**, uncommitted (branch `fix-1a-transcript-continuity`,
  baseline `14f11314`). Ringer run `grounded-environment-narration-20261025T125147Z-p843072`
  (Luna high, 2 attempts). Ringer marked it FAIL only because the manifest's
  relative `expect_files` resolved against the task dir (`worktrees: false`); the
  executed check exited 0 and the manifest now uses absolute paths. Paths:
  `scripts/ringer/environment_narration/baseline.py`, `tests/test_environment_baseline.py`,
  manifest `scripts/ringer/environment_narration/build-t1-baseline.json`.
  Checks: 6 hermetic tests pass (socket/urllib patched to fail); two CLI runs
  byte-identical; ruff check/format clean; no edits to storygame/data/docs/worker.
  Artifact: `bench/results/environment-narration/t1-baseline.json` (8 cases,
  0 network calls, deployed model unverified; `bench/results/` is gitignored so it is local only, regenerate with `baseline.py --out`; worker default is
  `@cf/meta/llama-3.1-8b-instruct-fast`; all 5 historical artifacts present).
  Findings: the four boarding cases are engine-text turns, command consumed,
  THINGS = `['Kristin']`, laptop only in the `Just before this:` line, so the
  narrator payload omits it (captured by `bypass_for_capture`, not sent in
  product). `already_seated` is engine text ("Kristin is already in the driver's
  seat.") and also omits the laptop from THINGS. New: `compound_enter_and_inspect`
  is NOT consumed (real narrator call) yet still lists only Kristin in THINGS and
  carries the laptop only in the background line, so the omission is not limited
  to consumed commands. `approach_truck` and `look_around_outside` record no
  steps in this fixture because the simulated classifier answered `boards=false`.
  Classifier answers are inputs, not measurements. Unresolved: no live check of
  these prompts; deployed model not verified. Next: T2.
- T2: **done 2026-10-25**, uncommitted. Ringer run
  `grounded-environment-narration-20261025T130028Z-p857295` (Luna high, 2 attempts).
  Ringer marked it FAIL only because my check demanded >=8 passing tests; the
  file has 4 passing and 16 strict xfails, which matches the spec (threshold
  corrected to >=4 in the manifest). Paths: `tests/test_observation_context.py`
  (624 lines), `.plans/grounded-llm-environment-narration/t2-visibility-audit.md`
  (written by the coordinator), manifest `scripts/ringer/environment_narration/build-t2-tests.json`.
  Checks (rerun by hand): `4 passed, 16 xfailed`, no failures; `storygame/runtime/observation.py`
  does not exist. Passing: real-package fact sanity and the three audit-gap
  demonstrations (is_visible is not observer-relative; contents() cannot tell
  emptied from never-described; given_with mixes shut-away and visible).
  xfail(strict, raises=ImportError) for 14 projection rows incl. synthetic
  observatory and skiff; 2 schema-need rows (`view`, `contents_complete`)
  accept ImportError or worldkeeper SchemaError. Verified the schema-need fixtures
  build cleanly minus the new keys, and that worldkeeper currently IGNORES unknown
  entity keys silently, so T3 must decide whether to validate them. T3 must remove
  the xfail marks when it passes (strict xfail forces this). Unresolved: no
  test of the real-prompt wiring yet. Next: T3.
- T3a: **done 2026-10-25**, uncommitted. Two Ringer runs:
  `grounded-environment-narration-20261025T130750Z-p867555` (projection; Ringer FAIL
  because my check omitted `CLOUDFLARE_WORKER_URL`, which 4 environment-dependent
  boarding tests need; those 4 also fail on a clean baseline without it) and
  `...T131958Z-p879362` (derived-kind fix, PASS, 1 attempt). Paths:
  `storygame/runtime/observation.py` (new, pure, no story vocabulary),
  `packages/worldkeeper/src/worldkeeper/model.py` (+87 lines: optional `view`
  and `contents_complete` entity declarations, `World.sees`, `World.contents_complete`,
  schema validation with SchemaError; other unknown keys still tolerated),
  `packages/worldkeeper/tests/test_view_and_scope.py`, `tests/test_observation_context.py`
  (xfail marks removed, assertions unchanged, one derived-kind test added),
  manifests `build-t3a-projection.json`, `build-t3a-fix.json`.
  Checks (rerun by hand): 149 passed, 0 xfailed, over observation, worldkeeper,
  seating, boarding (3 files), referred_reach and baseline suites; ruff clean;
  data/docs/worker untouched.
  Review found and fixed one bug: items were matched by exact kind
  (`== "thing"`), silently dropping items of story-defined kinds inheriting
  `thing`; now `_is_item` (is_a thing, not container/supporter/furniture/vehicle).
  Known limits: defaults `max_required`/`max_optional` are 32 (spec said 8; T3b
  sets real budgets); a portable container (bag) is not an item; `blocked_by.axis`
  accepts an entity id or an axis name; story-package loader plumbing
  (`storygame/story_package/`) for `view`/`contents_complete` is NOT done, so the
  real 1A package cannot declare a window view yet (needed before T6's
  "Look through the truck window" row). Not yet wired into any prompt. Next: T3b.
- T3b: **done 2026-10-25**, uncommitted. Ringer run
  `grounded-environment-narration-20261025T132302Z-p883198` (PASS, 1 attempt,
  Luna high). Paths: `storygame/runtime/item_facts.py` (+54/-9),
  `tests/test_observation_prompt.py`, `scripts/ringer/environment_narration/compare_baseline.py`
  (coordinator-written: fails unless a fresh baseline run matches the frozen T1
  cases, ignoring dirty/package_hash), manifest `build-t3b-wiring.json`.
  Opt-in `ItemFactsProvider.observation_request` (None by default, nothing in the
  product sets it). When set: engine-text shortcut skipped; PLAYER keeps the
  original action and adds one `Already done:` line; projected visible things are
  appended to THINGS in the existing line format; one CONSTRAINTS line
  `Show these in your reply: <names>.`; contingent things never listed. The
  check proves default prompts are unchanged (all 8 baseline cases identical)
  plus 12+ focused suites green. I reviewed the diff and printed the real prompt
  for "Enter the truck.": THINGS lists Kristin and Kristin's laptop (Place:
  passenger seat), required line names the laptop, Already done holds both steps.
  OPEN: the `Already done:` line still contains the engine-written notice
  sentence ("Kristin's laptop sat on the passenger seat."), i.e. per-item
  `notice_text` prose still reaches the narrator on this path. A package with no
  notice_text would not have it, so a T5 "proposed context" arm built from this
  would be unfair to the generic claim. T3c removes notice steps from the
  observation prompt.
- T3c: **done 2026-10-25**, uncommitted. Ringer run
  `grounded-environment-narration-20261025T132739Z-p888607` (PASS, 2 attempts).
  `SeatingResult.notice_steps` (steps unchanged), `provider.prior_notice_steps`,
  observation-mode `Already done:` and `completed_actions` drop notice sentences.
  Edits: `storygame/runtime/{seating,capture,item_facts}.py`, tests appended to
  `tests/test_observation_prompt.py`. I printed the real prompt: PLAYER ends
  `Already done: Kristin sat down in the driver's seat.`; THINGS still lists the
  laptop at the passenger seat. Default path and all 8 baseline cases identical.
  Remaining limit: the seat step (`enter_text`) is still authored per-seat
  package text; it is a completed action, not an environment description.
- T4a: **done 2026-10-25**, uncommitted. Ringer run
  `grounded-environment-narration-20261025T133511Z-p896777` (Ringer FAIL: my check
  required no diff under `storygame/`, which the uncommitted T3b/T3c edits break;
  every other gate passed when run by hand). New `worker/src/models.js`
  (profiles: Llama 3.1 8B default unchanged, Llama 3.3 70B FP8 fast, DeepSeek V4.1
  Flash 1017 with `max_completion_tokens` + `reasoning_effort: low`, final text only
  from `choices[0].message.content`, reasoning never shown, reasoning-only reply =
  AI_EMPTY_RESPONSE, `finish_reason: length` => `truncated: true`, ceiling 4096),
  prices added to `worker/src/budget.js`, `worker/src/index.js` uses the profile,
  and a server-gated `X-Bench-Model` header: honored only if the id is in env
  `CF_BENCH_MODELS` (unset = off, the production default), has a profile and a
  price; otherwise 400 `BENCH_MODEL_REJECTED` with zero Workers AI calls and zero
  budget reservations; no silent fallback. `node --test test/`: 30 pass (15 old
  unchanged + 15 new), syntax checks ok, no story vocabulary. Unconfirmed until the
  T5 transport smoke: DeepSeek's real final-text/usage field names (docs do not
  list them) and whether it accepts `response_format`; the Worker fails closed on
  unknown shapes. Deploying this Worker change is separate and not done.
- T3d: **done 2026-10-25**, uncommitted. Ringer run
  `grounded-environment-narration-20261025T134..` `t3d-package-view-and-scope`
  (Ringer FAIL, 2 attempts: my `git diff -- worker` guard tripped on T4a's
  uncommitted edits AND a real regression, below). `storygame/story_package/models.py`:
  `ItemView`/`ItemViewBlockedBy` models and `Item.view`, `Item.contents_complete`
  (StrictBool); `world_schema.py` passes them through only when set (shipped
  packages produce identical schema data); `tests/test_package_view_scope.py`
  9 tests incl. loader errors as StoryPackageError. `data/` untouched.
- T1 regression found and fixed 2026-10-25: T4a renamed `const model` to
  `const configuredModel` in `worker/src/index.js`, so T1's default-model regex
  failed and 5 baseline tests broke; nothing ran them between T4a and T3d. Fixed
  by Ringer run `...t1-fix-model-parse` (PASS, 1 attempt): pattern accepts any
  identifier, tests for both forms. Lesson: every task's check must include the
  baseline comparator and `tests/test_environment_baseline.py`. After the fix: 287
  passed over the 13 focused suites, baseline cases identical (8), Worker 30 pass.
- Known gap before T5: `scope_complete` is computed but not rendered in the prompt,
  so a "complete, empty scope" start would equal the existing path. T3e adds
  one generic constraint line for it.
- T3e: **done 2026-10-25**, uncommitted. Ringer run `t3e-render-complete-empty-scope`
  (PASS, 1 attempt). In observation mode only, a declared-complete scope with
  nothing known inside adds `- The <focus name> holds nothing else the player can find.`
  to CONSTRAINTS; undeclared or non-empty scopes add nothing; default path unchanged.
  Edits: `storygame/runtime/item_facts.py`, tests appended to `tests/test_observation_prompt.py`.
  Rerun by hand: 212 passed over 13 suites.
- T4b: **done 2026-10-25**, uncommitted. Ringer run `t4b-screen-harness` (PASS, 1
  attempt, 490 s). `scripts/ringer/environment_narration/screen.py` +
  `tests/test_environment_screen.py` (7 tests). Dry run: 6 starts x 2 contexts x 3
  models = 36 cells, 360 calls at 10 samples, estimated ceiling **$0.964**; 6-call
  smoke ceiling **$0.016** (input estimate = ceil(bytes/3), max_tokens 1024/1024/3072).
  Live path needs `--confirm`, `--max-calls`, `--max-usd` (refuses without), is
  interleaved, no retries/replacements, writes rows after every call, stops on quota
  or `BENCH_MODEL_REJECTED`, and marks the run invalid if the Worker echoes a
  different model. `--report` renders every call. I read each start's real E-vs-P
  diff: S1, S2, S3, S6 differ as designed; S4 prompts are IDENTICAL (control: models
  only); S5 keeps the authored "Dr. McGehee may say this aloud: Kristin finds
  Michelle's memory card ... pockets it" cue line in both arms (faithful to the
  open-defect scenario; the screen isolates the scope line, not the cue).
  Shipped story data untouched; S2/S5 proposed arms run on tmp package copies with
  `view` / `contents_complete` declared (hashes recorded).
- Direct smoke (pre-T5), **run 2026-10-25**, billed, uncommitted code. Ringer run
  `grounded-environment-narration-20261025T151408Z-p946240` (runner, 1 attempt).
  Tool: `scripts/ringer/environment_narration/smoke_direct.py` (calls Workers AI REST
  directly with the account's existing credentials; no Worker, so no Worker hop in
  the latency). 4 models x 6 calls = 24 calls, ceiling $0.0218, measured about
  $0.007 for the three models that returned usage (Gemma 4 returned none).
  Artifacts (local, `bench/results/` is gitignored):
  `bench/results/environment-narration/smoke-direct-{rows.json,report.md}`.
  Client read timeout was 15 s, so any latency of ~15.07 s is CENSORED.
  Results: llama-3.1-8b 0.73-1.08 s, 6/6 usable, ~0.1k completion tokens/call;
  qwen3-30b-a3b 2.3-10.6 s (median 6.15 s), 6/6 usable, ~970 completion tokens per
  call because of hidden reasoning; gpt-oss-20b 9.5-15.1 s (median 11.8 s), 5/6
  usable, 1 timeout; gemma-4-26b-a4b timed out all 6 calls at 15 s (no data past 15 s).
  Response shape found: final text at `result.choices[0].message.content` for all
  three that answered; Qwen3 and GPT-OSS expose `reasoning` / `reasoning_content`
  fields (never used as narration); `response_format` json_object accepted by all
  three that answered (Gemma 4 unknown).
  Speed gate (p95 <= 5 s, p50 <= 2x baseline): only the 8B baseline passes; Qwen3
  median 6.2 s fails, GPT-OSS ~11.8 s fails, Gemma 4 > 15 s fails.
  Hand-read correctness (tiny n, rubric from the T5 prereg): 8B 0/3 on S1-proposed
  (steps in by the passenger door, or drops the laptop), 1/1 usable on S2; Qwen3
  puts the laptop on the passenger seat 3/3 but INVENTS story-breaking clues in S1
  and S2 (a "Project Aegis" file, red-pin map, coordinates of an abandoned
  facility) and in S2 unlocks and opens the door (unrequested movement); GPT-OSS
  places the laptop correctly in 2/2 usable S1-proposed and the S1-existing call,
  but misses it in S2. S5: ALL models re-found the memory card; the authored
  "Dr. McGehee may say this aloud: Kristin finds ... pockets it" cue line in the
  prompt overrode the scope line, so S5 is confounded and says nothing about the
  scope line. S1-existing passed for Qwen3 and GPT-OSS (1 call each): their
  context included the engine notice sentence, so P vs E is not separated by 1 call.
  Finding: no model in this set is both fast and correct; only speed-qualified
  model (8B) fails the prompt even with the projected facts.
- T5–T11: not started (the 36-cell design is superseded by what the smoke showed). Reliability, model suitability, verifier calibration,
  latency and hosted behavior remain unverified.

### Smoke 2 and 3 record (2026-10-25, direct Workers AI, local artifacts under bench/results/environment-narration/)
- Tool changes (Ringer, tests first): `--variants` selector; `llama-3.3-70b`, `llama-3.3-70b-nojson`, `qwen3-think-off-kwargs`, `qwen3-think-off-soft` profiles (`json_mode`, `user_suffix`); an HTTP 200 with an unparseable body is one unusable row, not a dead variant; report prints raw reply text.
- `smoke70b-*` (6 calls, JSON mode forced, 70B fp8-fast): 1.39-1.96 s, median 1.64 s; 0/6 valid JSON (every reply opens with the same broken `{"segments':[{"`, response model name `llama-3.3-70b-json`); content: laptop on passenger seat 3/3 on S1, S2 ok, S5 no re-find. Cost $0.0023.
- `smoke-nj-*` (18 calls, 6 each): 70B without JSON mode 2.33-3.48 s plus one 9.11 s, median 2.66 s, 3/6 valid JSON (unescaped quotes in dialogue), full production contract incl. item_facts, laptop right 4/4 on S1/S2, no story-breaking clue, S5 re-found the card. Qwen3 + `/no_think` suffix: 0.98-2.22 s, median 1.59 s, 6/6 valid, laptop placed right but invents clues (message thread, files) and in S2 enters the truck and takes the laptop. Qwen3 + `chat_template_kwargs.enable_thinking=false`: 0.94-1.32 s, ~130 tokens, but the answer arrives in `reasoning`/`reasoning_content` with `content` null (0/6 readable by a content-only reader); S1-existing exits the truck. Cost about $0.0045.
- "Shelly" in replies is the authored nickname Kr uses for Michelle (in the prompt), not an error.
- S5 stays confounded by the authored "Dr. McGehee may say this aloud ... pockets it" cue; every model re-found the card.

### Smoke 4 record: 70B in json_schema mode (2026-10-25, 20 calls, $0.0124; `smoke-schema-*`, local)
- 20/20 valid JSON (answer arrives as an object at `result.response`). Latency 2.38-7.64 s, median 4.46 s, 8 of 20 over 5 s (slower than JSON-off, 2.3-3.5 s): fails the p95 <= 5 s gate and 2x-baseline-median.
- Defect: 8 of 20 replies end in a dangling stub ("She says to herself, "): the schema blocks the unescaped quote the model wants to write, so the speech is lost instead of malformed. Valid JSON but truncated text.
- Projection evidence (first clean one): S2 proposed shows the laptop 3/3 and stays outside; S2 existing (no view) omits the laptop and invents bottles/map/gloves. S5b (reveal cue line deleted) proposed: 0/3 invented clue; existing: 2/2 invented a receipt with a handwritten "Meet me at the old warehouse at midnight" note. S6 proposed 3/3 invent missing work bag/tablet. S4 1/2 invents drawer contents.
- Search: Cloudflare supports json_schema for this model but cannot guarantee it; bare inner quotes are the known cause; standard fixes are constrained decoding, strict-parse-then-repair, json_repair (fragile). Product asks json_object with a retry only on HTTP error and re-asks on bad bodies.
- Offline: a ten-line "escape an inner quote unless a structural character follows" repair parsed 3/3 of the real invalid JSON-off replies and kept the dialogue. n=3; not in product code.

### Smoke 5 record: 70B JSON-off, wide, with the product's quote repair (2026-10-25, 20 calls, $0.0127; `smoke-nojsonwide-*`, local)
- Product change (Ringer, tests first): `storygame/runtime/narration_json.py::escape_stray_quotes` (char scanner, no regex) called from `CloudflareTurnProvider._decode_narration`; repaired replies cost no second call and do not set recovery_used. Smoke rows/report carry strict vs repaired validity.
- Validity: strict 17/20, after repair 20/20. Latency 2.05-5.95 s, median 3.01 s, 19 of 20 under 5 s (max 5.95, next 4.82); about 4x the 8B median (0.76 s).
- Content (16 proposed calls): S1 3/3 laptop on passenger seat; S2 3/3 laptop seen from outside (existing context omits it and invents a paper); S3 2/2 ok; S6 3/3 clean; S4 2/2 invent drawer contents (papers, a pen), card stays hidden; **S5b 3/3 invent a clue (receipt "Meet me at the old warehouse at midnight", torn paper) with the scope line present**, and 2/2 existing also invent. The scope line does not stop the 70B from inventing on a search.
- Correction to the schema-mode record: its S5b "0/3 invented" was weak evidence; two of those replies are dangling stubs cut at the point an invention could have started.
- Risk to check: S2 item_facts said Kristin's place is "truck" while she is narrated outside (3/3); verify capture handling before relying on it.
- Hypothesis to probe next: the prompt still carries "What presses on Kristin now: Find evidence of Michelle's disappearance", which pushes the model to find something.

### Smoke 6 record: S5b four-arm prompt probe, 70B, JSON off, default sampling (2026-10-25, 32 calls, $0.0188; `smoke-probe-*`, local)
Brandon accepted the current speed (70B median about 3 s) as meeting the narration speed requirement. Score = narration only: an arm sample fails when Kr finds a new object or clue.
- Control (S5b as built, scope line "The drawer holds nothing else the player can find." and the "What presses on Kristin now: Find evidence ..." line): 3/8 invent a find (a paper; a receipt with "Meet me at the old warehouse at midnight"; a paper knocked off in the struggle).
- A (scope line reworded as an outcome: "Nothing is left in or under the drawer. Searching the drawer finds nothing."): 0/8.
- B (the "What presses on" line deleted): 0/8 (three replies mention harmless scraps of paper).
- C (A and B): 0/8.
- Earlier same-prompt run at temperature 0 failed 3/3 in the control, so the control rate is 3/11 to 6/11 across runs; the three treatments together are 0/24. Which edit does the work is not separated at n=8; the 0/8 arms cannot support a 9/10 bar yet (Wilson upper bound for 0/8 is about 32%).
- Validity 31/32 strict, 32/32 after repair. Latency median 2.71 s, but 4 of 32 over 5 s (5.8, 7.0, 9.8, 10.4 s): the tail is longer than the 20-call run's (max 5.95 s).
- Correction: the missing work bag and tablet in look-around replies are in the scene text (grounded), not inventions.

### T3f record and Smoke 7: outcome-wording scope line adopted; confirmation, 70B, JSON off, default sampling (2026-10-25, 30 calls, $0.0182; `smoke-confirm-*`, local)
- T3f (Ringer, tests first): the observation prompt's complete-empty scope line is now "- Nothing is left in or under the <focus name>. Searching the <focus name> finds nothing." (`storygame/runtime/item_facts.py`); the old "holds nothing else the player can find" wording is gone from code and tests. Condition unchanged. 130 focused tests pass, T1 baseline identical (8 cases). The Ringer task showed FAIL only because my check grepped the old sentence out of a test that asserts its absence; the worker's code was verified by hand (ruff, tests, baseline).
- Tool: `smoke_direct.py --slots confirm` (30 slots: S5b control then S5bA, samples 0-14), run on the frozen probe prompts file so the control keeps the old wording and S5bA is the wording now shipped.
- Control (old wording): 8/15 invent a find (a paper picked up in 7 replies; a receipt with "Meet me at the old warehouse at midnight" / "at 5" in 2). Arm A (shipped wording): 0/15 (mentions of dust, "lost scraps of paper", "the familiar kitchen floor" are harmless; "still holding Michelle's memory card" is grounded).
- Fisher exact on 8/15 vs 0/15: p about 0.003. With the earlier 0/8 for arm A, 0/23; the Wilson upper bound is about 14%, so the 9/10 bar holds on S5b.
- Validity 30/30 strict. Latency control median 3.24 s (max 5.96), arm A median 3.02 s (max 6.35); no call over 10 s this time (the earlier 9.8 and 10.4 s calls remain the tail).
- Not yet shown: that the new wording leaves S1-S4 and S6 unchanged (it only renders on declared-complete empty scopes, so those prompts should be byte-identical; the T1 baseline and screen dry-run cover that).
