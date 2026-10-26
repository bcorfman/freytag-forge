# Reliable environment narration without per-item engine prose

Status: in progress, 2026-10-25 (see "Resume here"). Reviewed local baseline `14f11314`.
No runtime changes, new live experiments, model switch, or deployment were made
while writing this plan. Historical measurements below are not fresh results.

## Resume here

**State as of 2026-10-25 (end of session).** Done, with records under "Completion record": T1, T2, T3a-e, T3f (outcome-wording scope line), T4a, T4b, T6a (stray-quote repair), T6b (narrator cannot board the protagonist), T6c (boarding question wording). The billed T5 screen was replaced by seven small direct smokes (about $0.05 in total, plus a 100-call Jev probe); the T5 preregistration is superseded and unapproved. Commits: `e7913d3a` (runtime, tests, Worker profiles) and `ece5dcdd` (bench tooling, records, plan). T6b, T6c, T6d, `jev_boarding_probe.py` and its test, and the later plan records are committed together on this branch. Nothing is deployed.

Decision from the measurements: narrate with `@cf/meta/llama-3.3-70b-instruct-fp8-fast`, JSON mode OFF (no `response_format`), the product's default sampling, and the stray-quote repair. Median about 3 s (Brandon accepted this speed); tail up to 10.4 s was seen once. Scope line: S5b invented finds 8/15 before, 0/15 after the outcome wording. Boarding: Jev wording fixes the walk-over/approach cases; "Go out to the truck." is borderline and left as is by Brandon.

**Next, in order:** (0) T7 is done (calibration gate PASS on the frozen corpus; verifier stays shadow-only; see the T7 section). (1) T6 is functionally done (T6d-T6g below): the Worker supports only the 70B, and the product builds an observation request every turn. The live check of the whole path is done (T6i and the Live check record below, 2026-10-25); no deploy or production config change was made, and any such change needs Brandon's explicit instruction. (2) T7 verifier in shadow (done), T8 candidate preview and transaction (done 2026-10-25, uncommitted on branch `t8-candidate-preview`; enforcement is built but OFF), T9 confirmation (needs a live shadow sample of the verifier first), T10 retire the boarding engine-text path and `notice_text` (the legacy path now runs only with `observe_automatically = False`), T11 ruff, one full pytest+cov run, CI and SHA-bound staging.

**Open items:** the laptop place phrase "passenger seat of Kristin's truck" (copied from the prompt) left the laptop unplaced in a hermetic test with the matcher and Jev stubbed out; production adds both, so it needs a live check before it is called a bug. S4 (drawer opening) invented drawer contents in 2/2 samples (only the memory card matters, so likely harmless, but n=2). Portable containers are excluded from items; the markdown story-package format lacks `view` and `contents_complete`; the `blocked_by.axis` field accepts an entity id or an axis name. Ask Brandon whether to commit.

Older text follows. Where it conflicts with this paragraph, this paragraph wins.

Do not restart the old prompt-tweaking queue. This plan supersedes the proposed
engine-written empty-search response in the 1A continuity plan and supplies the
replacement path for its boarding workaround. Preserve its other fixes and
unfinished verification.

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

### Capture check on the S2 (look through the truck window) replies (2026-10-25; hermetic, no model call; probe script kept in the session scratchpad, not in the repo)
Method: start S2 on the proposed package copy, feed recorded 70B `item_facts` through `ItemFactsProvider.apply_item_facts` with the Jev and matcher stubs used by the screen.
- Kr `{"place": "truck"}` (70B JSON-off wide run: 3/3; schema run 0/3 said "outside the house"; nj run 0/1) puts Kr in the truck's driver's seat (`_apply_move` seats a protagonist who is placed in a vehicle) while the prose has her outside looking through the window. Cause is deterministic once the narrator names the truck; "truck" resolves by exact name, so no model call can correct it.
- Laptop `{"place": "passenger seat of Kristin's truck"}` (copied from the prompt's own "on the passenger seat of Kristin's truck"; all 70B S2 proposed rows) left the laptop UNPLACED (no parent) with no issue text when the matcher/Jev stubs return nothing. Production adds a matcher `same_as` and a Jev mapping check, so this is unproven either way and needs a live check before it is called a bug.
- Recommendation (not built): in observation mode, a look request must not move the protagonist into the focus entity. Deterministic, story-agnostic, testable offline; the alternative is a prompt arm (costs billed samples).

### T6b/T6c and Jev boarding probe (2026-10-25)
- Decision (Brandon): "go out to my truck", a bare "go to the truck" and "get in" board; "walk over to", "walk up to" and "approach" stay outside; the bare "go to" is open to interpretation and need not be tuned further.
- T6b: `ItemFactsProvider._apply_move` no longer lets a narrator reply board the protagonist. A reported vehicle or vehicle seat when she is not already aboard keeps her at the vehicle's area and records an issue. Boarding is decided only by the engine (`board_vehicle` + Jev `boards_vehicle`). Tests: `tests/test_narrator_cannot_board.py`; two old assertions in `tests/test_vehicle_landing.py` and one in `tests/test_bench_item_facts.py` that encoded narrator boarding were changed.
- T6c: `boards_vehicle` question reworded (go to it to use it counts; only walking over/up to, approaching, looking at, touching, talking about or leaving it does not).
- Jev probe (`jev_boarding_probe.py`, 100 calls, 25 commands x old/current x 2, via the Worker /jev route, median 0.35 s per call, usage not recorded): old 43/50 (should-board 24/24, should-not 19/26), current 48/50 (22/24, 26/26). All walk-over/approach/step-up cases are fixed. The two misses are both samples of "Go out to the truck." (0.43, 0.49 against the 0.5 cutoff); "Go out to my truck." passes at 0.52/0.56, bare "go to" at 0.58-0.66. Left as is by decision.
- T6d (2026-10-25): Ringer run `grounded-environment-narration-20261025T204710Z-p1047262` (Luna high, 2 attempts; Ringer FAIL only because my check grepped `# fail 0` and this Node prints `ℹ fail 0`, and had `git diff --quiet -- storygame` which the uncommitted T6b/T6c edits break; every gate rerun by hand). `worker/src/models.js`: the 70B profile uses `buildLlamaPlainBody` (messages and max_tokens only, ignores `response_format`, no `temperature`); 8B and DeepSeek unchanged. Three new tests in `worker/test/models.test.js`. `node --test test/`: 33 pass; T1 baseline identical (8); 481 passed over 12 focused Python suites; ruff clean (also fixed `compare_baseline.py` SIM115). Not deployed. Risk: matcher and second-call prompts on the 70B without JSON mode are unmeasured.
- T6e (2026-10-25): Ringer run `grounded-environment-narration-20261025T205341Z-p1053015` (PASS, 1 attempt). The 8B and DeepSeek Worker profiles and prices are gone; `worker/src/index.js` defaults to `@cf/meta/llama-3.3-70b-instruct-fp8-fast`; an unknown id falls back to the 70B profile (still refused if unpriced). Worker tests rewritten around the 70B. Bench tooling that names the old models (`screen.py` model list, `smoke_direct.py` variants) is historical and was left alone; the screen's old-model arms would now be refused by the Worker. Cost effect: the 70B is about 3x the 8B per token, so the daily budget buys fewer calls once deployed.
- T6f (same run, 2 tasks in parallel): observation mode is the product default. `ItemFactsProvider.observe_automatically` (True); `WorldCapture.before_turn` rebuilds `observation_request` every turn: boarding sets kind `enter` with the vehicle as focus; otherwise the first resolved referred name that is a thing, container, supporter, area or vehicle becomes the focus (kind `look`, or `open` when the new Jev question `opens_container` says so); a command with no such referent sets none and keeps the old prompt. Already aboard no longer produces the engine sentence: the command goes to the narrator unconsumed. Consumed boarding now calls the narrator (steps = her seat only, no notice sentence). `SeatingResult` gained `vehicle_id`, `already_aboard`. `baseline.py` and `screen.py` set `observe_automatically = False`, so the T1 comparator still passes (8 identical). Tests: `tests/test_observation_mode.py` (7); legacy engine-text tests pin the old path with the flag off; `test_boarding.py` and `test_observation_prompt.py` assertions changed to the new behavior. 622 passed over the focused suites; ruff clean. Not live-checked.
- T6g and Smoke 8 (2026-10-25): `classifier_smoke.py` (10 tests) plus Ringer run `grounded-environment-narration-20261025T210725Z-p1067610`; 35 calls, 70B, JSON off, about 16.3k input and 0.8k output tokens (under one cent), local artifacts `bench/results/environment-narration/smoke-classifier-{rows.json,report.md}`. Latency median 0.79 s, max 3.5 s. `second_call_update` is NOT in the product path (only the bench's second_call mode uses it; the product uses single_call), so only the matcher matters. Matcher by the product's own validity rule (`refers` a list, `same_as` an object): "Enter the truck." 5/5 refers the truck, "Examine my laptop." 5/5, "Open the drawer." 5/5; "Look around." 2/5 clean JSON and 3/5 correct JSON wrapped in a sentence ("Since there are no new names in the command, the response would be: {...}"), which fails `json.loads`, so `prepare_turn` records "item_facts match failed" and falls back to dependency-only selection (the right outcome for that command, but a logged failure; seen only when `refers` is empty, 0/15 otherwise). The harness's own `shape_valid`/`correct` columns were stricter than the product (they also rejected the extra `same_as`/`kind` entries the model invents when NEW NAMES is empty; the product ignores them), so use the raw replies, not those columns. Second-call replies were valid JSON 15/15 (not in the product path). n is tiny. Open choice: leave it, or add a JSON-object extractor for prose-wrapped replies.
- T6h (2026-10-25): Ringer run `grounded-environment-narration-20261025T211715Z-p1070305` (Luna high, 2 attempts; Ringer FAIL only because my check had `git diff --quiet -- worker`, which the uncommitted T6e edits break; every gate rerun by hand: 482 passed over 7 focused suites, ruff clean, no regex, no story vocabulary). `storygame/runtime/narration_json.py::extract_json_object` (character scanner, string and escape aware): returns the dict when exactly one balanced top-level `{...}` in the text parses (strictly or after the stray-quote repair); None for none, two or more, or an unterminated object (so a cut-off reply is never answered by an inner object). `CloudflareTurnProvider._decode_narration` calls it on the original text after the stray-quote repair and before truncation completion; it logs a warning and does not count as recovery. Fixtures are the real prose-wrapped matcher replies from Smoke 8. Not re-measured live: whether this changes the "Look around." rate (3/5 wrapped) needs a fresh small matcher smoke if Brandon wants the number.
- T6i (2026-10-25): Ringer run `grounded-environment-narration-20261025T212642Z-p1081207` (PASS). `scripts/ringer/environment_narration/local_worker.mjs` (+ `local_worker.test.mjs`, 7 tests) runs the real `worker/src/index.js` on 127.0.0.1 only, requires `--max-usd` and the three credential env vars, enforces the cap with the real `DailyBudget` ledger over an in-memory namespace, exposes `GET /__spent`, and logs only time, path, status, latency and model. This lets a branch be tested against the product before any deploy.
- Live check of the whole product path (2026-10-25, billed, local Worker, 70B JSON off, observation mode on): Ringer run `grounded-environment-narration-20261025T224042Z-p1092550` via `scripts/ringer/environment_narration/live_check.sh` (a first launch the runner refused because of a mistaken port check made no call; the port check now lives in the script). 145 real calls (74 narrator/match/capture on the 70B, 71 Jev), **$0.0354** against the $0.25 ceiling. All 200s; 70B median 2.2 s, max 9.1 s; Jev median 0.17 s. Both routes stopped at my `--max-calls` caps (60, 85) because the dry-run count (27/38 per replicate) undercounts real calls (about 4.6 per turn against 3.4): one full replicate each plus a partial second (reported 8+5 turns, corrected 12+8). Artifacts (gitignored): `bench/results/environment-narration/live-check/{reported,corrected}/{rows,summary}.json`, `worker.log`, `spent.json`. Every turn read:
  - Boarding: "go out to the truck" moved Kr outside, then "get in" boarded her through the engine (driver's seat, laptop on the passenger seat) 3/3, with the narrator told "Already done: Kr sat down in the driver's seat." and writing her seated with the laptop closed on the passenger seat. "Get out of the truck" moved her out 1/1 and the next "look around" and "wait" were consistent. No reply moved Kr by itself.
  - Drawer: "pull out the drawer" gave the stapler, spare batteries, pens and binder clips 4/4, matching the facts (no invented contents). "Feel in the gap" and "feel under the drawer" gave the memory card to Kr 6/6 and set `memory_card` held by Kr.
  - "Look around": grounded in the gate, the truck, the sirens and the patrol 4/4 outside; indoors it repeats the facts. Warnings seen: stray-quote repair 2, "text around its JSON; kept the object" at least 8, "match failed" 0 (the extractor works live; the earlier 3/5 wrapped rate is not re-measured as a rate).
  - Faults: "look at the fabric" invented a clue 2/2 (a fabric caught on the splintered door frame, in one reply Michelle's jacket); one "look around" from the truck invented trees, bushes and "the patrol is coming back" (the patrol had pulled away); "feel under the drawer" with the card already held quoted a scene sentence ("Kr finds Michelle's memory card taped beneath the drawer and pockets it") as speech 2/2 and once added "Dr. Michelle McGehee might have said". None changed a tracked fact. The laptop-phrase item (open earlier) is resolved: the engine step placed the laptop, so the unplaced case did not occur.

### T7 (observation verifier in shadow) - in progress, 2026-10-25
- Design: one batched Jev request per narration attempt, one noul question per required relation (thing at place/holder), state = the final narration. Verdict `accept` above 0.65, `reject` below 0.35, else `uncertain` (thresholds are starting guesses; the calibration records raw scores). Unknown, timeout, malformed and over-budget answers fail closed. Per-turn request budget 2. Failure telemetry carries generic codes only, never narration or model text. Shadow only: nothing is enforced and no turn changes.
- Steps: (1) round 1, Ringer `build-verifier-round1.json`: `storygame/runtime/observation_verifier.py` plus tests, and four corpus files `scripts/ringer/environment_narration/verifier_corpus/cases-{a,b,c,d}.jsonl` (56 cases each, 224 total, about 50% reject relations, ten categories, one file shaped like the product scene with fresh names). (2) round 2: the shadow hook in the provider (off by default) and the calibration harness (`--validate-corpus`, dry-run count, `--confirm --max-calls --max-usd`, per-category false accepts and false rejects, uncertain, model/version). (3) I spot-check labels, freeze the corpus hash, write the preregistration and cost estimate, and ask Brandon before any billed run.
- Limit stated up front: the corpus cannot show that unreported inventions are detected; `invention_unreported` cases are labelled accept and reported apart.
- T7 build done (2026-10-25), calibration NOT run. Ringer runs `grounded-environment-narration-20261025T234858Z-p1102219` (5 tasks, all PASS, corpus c needed 2 attempts) and `...T235729Z-p1115237` (3 tasks, all PASS, 1 attempt each). Delivered: `storygame/runtime/observation_verifier.py` (Relation, relations_from_context, ObservationVerifier with fail-closed verdicts, per-turn budget 2, generic failure codes, QUESTION_VERSION `observation-relation-v1`); `WorldCapture.shadow_verifier` (default None; adds an `observation_shadow` key to the after_commit record only when set; any error is swallowed and recorded as `shadow_error`; nothing reads it, nothing enables it); `JevClient.last_model` and `last_status`; `scripts/ringer/environment_narration/verifier_calibration.py` (`--validate-corpus [--lock]`, dry run, `--run --confirm --max-calls --max-usd`, `--report` with gate); the corpus (224 cases, 274 relations) locked in `verifier_corpus/corpus.lock.json`. Checks: 110 focused tests pass, ruff check and format clean over the repo. The verifier is wired nowhere in the product.
- T7 next: Brandon's go on `.plans/grounded-llm-environment-narration/t7-verifier-calibration-prereg.md` (448 Jev requests, ceiling about $0.008); then the Ringer probe run, read every row, record the report and the gate result here. Until the gate passes the verifier is never a guard.
- T7 calibration RESULT (2026-10-25, billed with Brandon's go, Ringer run `grounded-environment-narration-20261026T000211Z-p1125479`, PASS, 1 attempt; 448 requests, none unavailable, about $0.008 or less; artifacts gitignored: `bench/results/environment-narration/verifier-{rows.json,report.md}`; model `jev-1.13.0`; latency p50 0.38 s, p95 1.49 s). Gate at the preregistered thresholds (accept > 0.65, reject < 0.35): **PASS**. Zero false accepts over 294 reject-labelled relation samples (147 relations x 2); false rejects 0 of 254 accept-labelled samples; strict (fail-closed) accept-label failures 2 (1.0%, both `c-034`, scores 0.63 and 0.65, a paraphrase "glass dose container" for "sealed vial"). Uncertain 6 in all: `c-042` (hand-over, 0.61 and 0.65), `a-046` (look-alike badge, 0.50 and 0.42), `c-034`. Every uncertain reject fails closed, so none is a leak. Invention-unreported rows: 25/25 relation confirmed (not an inventions test).
- T7 reading (limits, my analysis): (a) the two samples of each case agreed every time (0 of 274 disagree), so the effective n is 147 reject relations, not 294; the report's Wilson bound (1.3%) uses 294, so the honest upper bound is about 2.5%. (b) The margin is thin: the highest reject score is 0.65, exactly the accept threshold, and the lowest accept score is 0.63; the post-hoc sweep shows 2 false accepts at accept_above 0.5 or 0.6 and 7 strict failures at 0.8. The scores of right and wrong cases touch; the pass depends on the threshold and the 0.65 equality rule. (c) The cases were written by an LLM with explicit cues ("never passes to", "is not on"), so they are easier than live narration; the corpus cannot show performance on subtle live prose. (d) One corpus, one authoring pass, one model version; re-run the frozen corpus whenever Jev's version changes.
- T7 decision: shadow verifier stays shadow-only. The gate passed on this corpus, which permits T8 to design enforcement, but enforcement itself needs a live shadow sample (turn the hook on in the T9 closed-loop runs and compare verdicts with a hand reading) before it is trusted as a guard. The threshold stays as preregistered; do not tune on this corpus. T7 is complete; next is T8 (candidate item-fact preview and one shared recovery path).
- CI fix on PR #700 (2026-10-25): the branch had never run CI and about 47 tests failed in six shards (all pass on main). Causes: tests that build the real narration provider needed a worker URL (my local runs had a fake `CLOUDFLARE_WORKER_URL` set, which hid it; always run focused suites with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN`); the boarding probe's frozen legacy prompts now pin `observe_automatically = False`; stale expectations (story place aliases, a fenced matcher reply the product now decodes, consumed boarding now narrated); and one real regression: a refused fixed-object move set an observation request and dropped the "Just before this" refusal line from the narrator prompt (`WorldCapture.before_turn` now sets no observation request on a refused fixed move, with a test). Ringer run `grounded-environment-narration-20261026T001415Z-p1129836` (3 tasks PASS). Full suite without the worker URL: 2929 passed, 16 skipped, 1 xfailed, coverage 92.75%.

### T8 (candidate preview, one shared recovery path) - done 2026-10-25, uncommitted, branch `t8-candidate-preview` (from main `b52c8cd0`)
- Facts about the code (read, not assumed): item facts live in `state.facts`, which `RuntimeSnapshot` clones and restores whole; they are applied only in `WorldCapture.after_commit`, after `state.apply_proposal`, by `ItemFactsProvider.apply_item_facts`, which also makes the billed item-facts match call and the Jev mapping checks. `RuntimeEngine._turn_active` already runs two narration attempts (`TURN_NARRATION_ATTEMPTS = 2`, narration budget 2, item-facts budget 2) and a `candidate_state` deepcopy, so the preview slots into that loop and a rejection reuses the guard-retry branch (`note_rejection(code)`, generic feedback, no raw term). A forced handoff (`_prepare_handoff`) changes the proposal after the loop, so installing preview facts at commit would be wrong; the commit therefore re-applies the real effects with the preview's billed answers replayed, and compares the result with the preview.
- Design: (T8a) `WorldCapture.preview_commit` runs the item-fact application on the candidate state with every provider field restored in a `finally` (billing counters excepted), runs the verifier against the candidate world, rejects any unrelated move of a pre-existing item, and records a `CallMemo` of the billed answers; `after_commit` replays that memo (one match call and one set of mapping checks per accepted attempt in total) and sets `observation_diverged` when the real application differs. (T8b) the engine loop calls the preview after narration validation; a rejection raises `ProposalValidationError(code="observation_unverified")` into the existing retry branch; the last attempt fails the turn with the existing typed rejection and snapshot restore; divergence at commit rolls the turn back. (T8c) the memo and preview outcome ride in `capture.context()` / `resume()` so a game break resumes with the same answers; fault-injection tests for each failure point.
- Enforcement stays OFF in the product: `WorldCapture.enforcing_verifier` defaults to None and nothing in `web_demo` sets it. Enabling it needs a live shadow sample first (T7 decision), so T8 builds and proves the mechanism only.
- T8a manifest: `scripts/ringer/environment_narration/build-t8a-preview.json` (generated by `make_t8_manifests.py`).

- T8 RESULT (2026-10-25, four Ringer runs, Luna high, all PASS on attempt 1; `...T005024Z-p1141303` t8a, `...T010538Z-p1157575` t8a2, `...T011250Z-p1166974` t8b, `...T012301Z-p1180928` t8c; manifests `build-t8{a,a2,b,c}-preview.json`). Delivered: `storygame/runtime/observation_preview.py` (`CallMemo`, `CandidatePreview`); `WorldCapture.enforcing_verifier` (default None), `preview_commit`, `take_preview`, preview-aware `after_commit` (`observation_preview`, `observation_diverged` in the record), `context()` / `resume()` carry a pending preview; `ItemFactsProvider.item_facts_call_memo` (the match call goes through it only when set); `RuntimeEngine._preview_observation` inside the existing attempt loop (rejection = `ProposalValidationError` code `observation_unverified`, generic feedback, no term; a non-provider exception = `observation_preview_failed`), exact rollback with `capture.resume(pre_turn_context)`, divergence at commit or on `proceed` = `observation_diverged` with snapshot restore. Tests: 41 new (`test_observation_preview.py` 18, `test_observation_enforcement.py` 13, `test_observation_resume.py` 10) plus a synthetic second story in each; quick suite 2505 passed, 15 skipped, 1 xfailed; ruff check and format clean over the repo. Full suite + coverage NOT run (planned once, at T11).
- T8 review fixes made after the first runs: the unrelated-move baseline is now the candidate world just before item facts apply (T8a compared with the pre-proposal state and would have flagged authored reveal moves); no-relations turns still reject an unrelated move; T8b's per-turn context capture and provider-error discard are gated on enforcement so the product default path is unchanged.
- T8 limits: (1) nothing sets `enforcing_verifier` in the product, and no live call has exercised the preview, so the verifier's behavior as a guard on real narration is unmeasured (T7 decision: a live shadow sample comes first). (2) The preview adds the verifier request per attempt (at most 2 per turn) and keeps item-facts match/Jev calls within the existing budget by replay; replay is checked with counting fakes, not against the live Worker. (3) After a divergence on `proceed`, provider turn-output fields are reset by the next `before_turn`, not at once (the pre-turn context is not stored in the game break). (4) A forced-handoff turn commits with the previewed narration as the item-fact `story`, not the hand-off-extended text. (5) `moved_unrelated` only considers parent changes of existing things; unreported inventions are still not detected (same limit as T7).
- Next: Brandon decides whether to commit this branch. Then a live shadow sample (turn `shadow_verifier` on in a closed-loop run, hand-read, preregistered) before T9; T10 and T11 follow.

### T8 live shadow sample of the verifier (2026-10-25, Brandon approved the run) - gate FAIL, enforcement stays off
- Preregistration, addendum A and full result: `.plans/grounded-llm-environment-narration/t8-shadow-sample-prereg.md`. Harness: `live_baseline.py --shadow --route observe`, `shadow_report.py` (blind sheet, labels, join), `shadow_sample.sh`, runner manifests `run-shadow-{smoke,full}.json`. Smoke 24 calls $0.0048; full 336 calls **$0.0633**, 5 replicates, 65 turns, 55 observation turns, 76 relations, no errors. Labels were written blind to verdicts and frozen by hash before the join.
- Result: 0 false accepts in 76 (upper bound 3.9%); good-turn strict reject 9.5%; p95 0.27 s; clause 2b (acceptable turns that enforcement would reject) **9/42 = 21.4%, limit 10%: FAIL**. Causes: all 5 scene-transition turns carry a stale requirement (the old drawer's contents), and 4 of 10 true holder relations were rejected or uncertain (place and holder both rendered as the character's full name). Drawer-content and passenger-seat relations agreed with hand labels 66 of 66.
- Not the verifier's job but found: all 10 `feel under the drawer` turns re-find the card Kristin already holds; 3 of 5 `inspect the passenger seat` turns invent an object. Enforcement as designed would neither catch nor repair them.
- Next (none billed, none started): (1) drop observation requirements when the scene or area changed during the turn; (2) test holder-relation wording on the frozen T7 corpus plus the 10 holder cases found here; (3) fix the harness defect (engine-authored move turns carry the previous turn's shadow record); (4) decide how the re-find and invented-object defects are fixed (the T3f scope line did not cover a held item); (5) a second shadow sample needs a new preregistration; T9 waits for it.
- Review mistakes to avoid: two of my Ringer checks used `git diff --quiet` over paths with uncommitted edits and failed a correct task; a builder registration edit missed a reformatted dict and the task silently never ran (it was caught from the output).
