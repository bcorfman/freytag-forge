# Original phase specification (2026-11-22)

**These are records, not commands.** Moved here verbatim from [the qualification plan](../dark-factory-diagnostic-qualification-plan.md) on 2026-11-23 when it was split into subplans. Where they conflict with the hub or a step file, the hub and step files win. "This plan", "below" and "above" refer to the old single-file plan.

**Read this when:** a step file points you to the original wording of Phase 1 to 7, or you need the objective, the 19q starting inputs or the verification protocol as first written.

## Earlier specification and execution record

## Objective and completion criteria

Establish whether the dark factory can independently find and repair intrinsic story problems, using evidence it retrieves itself. Passing more wiring checks or refusing an unsafe repair is insufficient. The factory must demonstrate correct causal diagnosis, an appropriate repair, a measurement that can observe the intended change, and successful execution without the operator supplying the answer.

This is the next factory-development milestone. Defer unrelated station expansion until it passes. Preserve the owner's zero-stuck final-game bar, continuity rules, fun review and release requirements. Qualification is evidence of a bounded capability, not proof that every story can be repaired autonomously.

Completion requires all of the following:

- The known 19q defects have meaningful passing regression checks against current code.
- A frozen evaluation includes both defective and healthy cases; the factory finds the required causes, cites evidence and avoids unjustified edits.
- Fresh runs pass held-out cases whose answers and corrective patches were not available to the solver.
- At least one structural story repair is diagnosed, specified, implemented and verified through the factory's persisted workflow. An owner-wait reroute does not satisfy this requirement.
- A cue hypothesis, if selected, is tested with a responding player. Fixed replay is used only for hypotheses about the same actions.
- A written result names what passed, what failed, cost and remaining limitations. No failed run is silently replaced.

## Current baseline and first action

At plan creation the checkout is on `main`, HEAD `3c2ab7d3`, merging PR #815. Commit `2a526bdf` contains the 19q provider, exit reporting, provenance and planner repairs. The planner already supports `unsupported` with `station_code`, `story_edit` and `adaptive_probe` routes. Do not rebuild these blindly.

There are pre-existing edits in `factory/stations/live_playtest.py` and `tests/test_factory_live_playtest.py`, plus untracked manifests including a calendar-split task. They are not owned by this plan. Capture `git status --short`, HEAD and the diff inventory before work; preserve them. Use an isolated checkout for implementation if needed. Do not reset, clean, stash or commit someone else's work. Reconcile any newer completed work into the inventory before starting.

Read these inputs before implementation:

- `AGENTS.md`, `docs/PRD.md`, contributor guide and applicable detail files, agent workflow guide and testing runbook.
- `docs/scene-fixing-guide.md`, `docs/story-gap-guide.md`, world-model grounding, player-input and narrator-writing guides.
- `.plans/Continuity Initiative dark factory plan.md`, especially 19q repairs and standing decisions. Its older resume command is historical and must not be executed.
- `/home/bcorfman/dev/ringer-work/out/chatgpt-19q-diagnosis.md` as an implementation reference, not solver input.
- Original evidence: `/home/bcorfman/dev/ringer-work/e2e-blind-player-17c.json` and `/home/bcorfman/dev/ringer-work/rehearse-19f/work/factory-19-1A-story_data/`.

**First executable task:** create `qualification/inventory.json` in a new, uniquely named workspace under `/home/bcorfman/dev/ringer-work/`. Record current code/package hashes, existing changes, which 19q repairs are present, their tests and remaining gaps. Do not resume `rehearse-19f`.

## Execution rules for Sonnet or Opus

Either model can execute the engineering phases. Use current repository-approved model IDs and guarded call adapters; do not copy an old model ID into a new provider configuration. Work sequentially by phase. Each phase ends with its artifacts, verification result and an updated resume point before beginning the next.

A model may question an earlier diagnosis, including the ChatGPT report, but must cite contrary source or runtime evidence. Do not implement diagnoses as keyword rules for Reyes, calendars, notebooks or this ticket. Shared runtime and diagnosis logic remain story-agnostic. World-state-only behavior remains in `packages/worldkeeper`.

Engineering the harness and reading saved artifacts are free. Separate authorized model evaluations from local tests: subscription calls also consume a limited resource. Before each external run, prepare exact prompts, arm configuration, call/token ceilings, USD/window estimates, output paths and a dry-run result. Execute only within explicit authorization already present in the session. If none covers the run, finish the reviewable run specification and request the missing authorization, citing the main plan's standing run rule. Never treat this document as spend authorization.

Do not create a self-modifying judge. Freeze acceptance criteria before results. Any new fun-judging wording or logic must be designed and checked by Opus under the standing rule; Sonnet can prepare the input and implement the approved specification. Do not start parallel agents merely because multiple phases are listed.

## Phase 1 Verify the repaired measurement foundation

Audit current source and existing tests before adding anything. Relevant owners are `factory/stations/probe.py`, `bench/core.py`, `storygame/runtime/item_facts.py`, `factory/stations/diagnose.py`, `fix_plan.py`, `planner.py`, `live_playtest.py`, `factory/line.py` and `guard.py`.

Demonstrate these invariants with free tests using fake providers and saved artifacts:

| Boundary | Required evidence |
| --- | --- |
| Provider parity | Item-facts construction retains semantic selection. An exact miss reaches a fake semantic asker, and refusal/ambiguity remain safe. Record actual features, not just requested config. |
| Exit cause | Earned, forced and unknown causes remain distinct through runtime, bench record, summary and verdict. Missing cause cannot improve the candidate's earned-exit rate. |
| Failure visibility | Failed/partial replicates, rejections and unknown exits cannot disappear from denominators or turn into success. |
| Spend | An unauthorized second probe, crash/restart or rejection/replan cannot reuse a consumed allowance or exceed the cumulative ceiling. No network needed to prove this. |
| Diagnosis | Previously delivered content, distinct sibling rewards, unmet prerequisites, wrong addressees, scoped aliases and prior invented narration remain distinguishable. Missing historical state is reported as missing. |
| Planner safety | The rejected `reyes_orders_1a` plan cannot enter wiring. Unsupported repairs and adaptive hypotheses cannot be disguised as a fixed replay beat. |

Use `tests/test_factory_diagnose.py`, `test_factory_probe.py`, `test_factory_probe_routing.py`, `test_factory_fix_plan.py`, `test_factory_planner.py`, `test_factory_line.py` and relevant bench/provider files as starting points. Test behavior and negative cases, not exact explanatory strings. Do not assert historic collection counts.

Artifact: `qualification/foundation.md`, linking each invariant to source, test and result. Gate: every measurement/safety invariant passes, or record the defect and repair it before a billed evaluation. Tests passing is not yet model qualification.

## Phase 2 Build an evaluation that cannot pass by repeating this report

The executor who read this plan is not a blind solver. Separate solver input from evaluator material through an enforced file/tool allowlist and fresh model sessions without inherited conversation. A prompt saying “ignore the answer” is not isolation. Solver runs must have no access to this plan, the ChatGPT diagnosis, labelled answer files, corrective commits, revealing filenames, or the current fixed version of a historical test case. Pin each case's source snapshot and permitted artifacts. Use a clean export without git history where historical patches reveal the answer.

Maintain three sets:

1. **Known regressions:** the 19q cases. They prove repaired behavior only; the code and this conversation already contain their answers.
2. **Development cases:** small independent examples used while building retrieval and routing. Include healthy controls and distinct defects. These may inform prompt revisions.
3. **Held-out qualification:** six cases selected and sealed before solver runs: four defects covering at least two scenes and three causal mechanisms, plus two healthy/insufficient-evidence controls. Include at least one intrinsic story-structure problem and one narration/provenance problem. Prefer previously unexamined saved runs; if only synthetic cases exist, label the result synthetic qualification and retain the live transfer requirement. Do not reuse 19q under renamed nouns as the entire holdout.

Before solving, the evaluator creates a private answer record for each case: immutable input hashes, observed symptoms, causal mechanism, source/turn evidence, acceptable alternative repairs, forbidden shortcuts, minimum necessary evidence and an executable acceptance check where possible. Ground expected outcomes in authored intent and runtime behavior. Ambiguous cases must permit uncertainty or be excluded before unsealing outputs; disagreement is not resolved by assuming the ChatGPT answer is authoritative.

The case package supplied to the solver starts with symptoms, player-visible records and access to the relevant repository snapshot. It contains no diagnosis category or proposed remedy. It must be possible to request predecessor turns and source definitions.

Artifacts: case manifest, solver allowlist, private answer records, hashes and frozen scoring specification. Gate: someone in the evaluator role verifies that each expected conclusion is derivable from accessible evidence. This role may be a separate fresh, authorized model invocation; no additional human story editing is required.

## Phase 3 Measure the current factory before expanding it

Prepare a model-evaluation runner that invokes the real current diagnosis/planner path through existing guards, logs complete inputs and outputs, and never wires a patch or calls live narration. Preserve configuration and source identities.

Run the current path on development cases first. After authorization, freeze that baseline output before changing prompts. For a controlled workflow comparison, use the same solver model and effort for baseline and revised workflow. Do not change model, evidence access and repair schema simultaneously and attribute improvement to one of them. A Sonnet/Opus comparison is optional and needs its own authorized budget; the executor's model need not equal the solver model.

For each result, evaluate:

- Does the diagnosis explain the observed failure and separate it from legitimate behavior?
- Are its citations real and sufficient, and does it identify missing evidence honestly?
- Does the repair preserve story meaning and give the player a meaningful outcome?
- Can the selected experiment observe the causal prediction?
- Does the system implement a supported repair or create an actionable bounded engineering task?

Artifact: `qualification/baseline-results.json` and a short gap report. Gate: select only the missing capabilities evidenced by this comparison. If the current implementation already satisfies a phase's requirements, retain it and prove that instead of adding another abstraction.

## Phase 4 Allow bounded investigation before committing to a cause

Extend the existing stations only where needed. Keep deterministic orchestration, but let a solver request evidence and revise an initial hypothesis. A deterministic lexical signal must not become an irrevocable causal label.

Implement a read-only evidence interface, using existing story CLI/runtime explanation APIs where possible, with these operations:

- Fetch a bounded turn range, including preceding narration and rejected attempts.
- Fetch a story record and its source, conditions, effects and text.
- Fetch producers/readers and sibling relationships for a fact or claim.
- Explain reveal eligibility from a recorded or faithfully reconstructed pre-turn state.
- Fetch the full relevant prompt, provider features and guard rejection evidence.
- Inspect bounded runtime/harness source needed to distinguish implementation from story defects.

Every response carries file/JSON locator, snapshot hash, truncation status and provenance. Never silently substitute current story data for historical data. Reconstruction uses a frozen prefix and network-free stubs, records its assumptions and cannot be represented as an observed historical state.

Use a small proposed default limit of three retrieval rounds, six requests per round and two hypothesis revisions per ticket, additionally bounded by token/spend caps. Make limits configuration, persist usage and do not reset them on restart. If essential evidence is unavailable or limits are exhausted, emit a precise blocked-evidence result; do not fabricate certainty or repeatedly replan.

Persist a structured causal report with: observed problem, prior hypotheses, current cause, evidence references, counterevidence, confidence/unknowns, affected commands, intended player outcome, repair boundary and predicted before/after behavior. Validate references and schema mechanically; semantic correctness is evaluated against evidence, not a rigid category name.

Gate: development tests prove retrieval, provenance, revision, truncation handling, restart behavior and no secret/out-of-scope access. The solver can correct a wrong initial lexical classification from evidence without an operator telling it the answer.

## Phase 5 Make structural repair a real factory capability

The current `unsupported` route safely avoids a bad fix but parks work for the owner. Preserve that fallback. Add one bounded route for the demonstrated class of story restructuring; do not build an unrestricted general editing agent.

A repair specification must include: affected source record IDs/files; the player-facing defect; authored intent evidence; before/after availability or progression; fact meanings and downstream readers; permitted changes; preserved canon; checks and measurement; and why smaller existing fix kinds cannot solve it. Permit supported package structure changes such as independent rewards or explicit follow-ups when justified. Do not require arbitrary new state merely to satisfy the schema.

Route such a specification into the existing Ringer implementation and factory gates using persisted parent/child dependencies. Reuse ticket infrastructure before adding new station numbers. Define completion, failure, retry budget and parent resumption explicitly. A child that merely exists or returns a patch is not complete. Preserve evidence and validation results across restart; prevent duplicate child creation and unbounded child chains.

Use the calendar case only as a development/regression exercise. If the existing calendar-split work has already landed, reuse its checks and do not duplicate its patch. Require both discovery orders, valid repeat responses, patrol-state conditions and unchanged exit dependencies. Avoid a hardcoded calendar-only route.

Free gate: the factory processes a development structural ticket from diagnosis to verified patch without an operator supplying a file edit or revised cause. No merge is needed for this qualification. State-only engine work still belongs in Worldkeeper; changes outside this route become separate bounded engineering tickets, not stealth story edits.

## Phase 6 Qualify independent diagnosis and repair

Freeze the revised workflow, solver model, prompts, evaluator rubric and limits. Run each of the six held-out cases twice in fresh sessions: twelve solver trials, no live narrator calls. Both trials of a case receive the same evidence access. Prepare and authorize the exact maximum calls/tokens before starting. The repeated trials test consistency, not statistical generalization.

Acceptance is per case, not an average that lets safe cases hide harmful failures:

- Both trials identify the required mechanism or an independently substantiated equivalent cause, with valid evidence.
- Both choose a compatible repair/test or the correct no-change/insufficient-evidence response for controls.
- No trial invents canon, broadens a claim across different characters, falsifies a fact, relaxes a guard to pass, counts an unknown exit as earned or silently changes the test.
- At least one held-out structural repair completes through the Phase 5 route and passes its frozen behavioral checks. Refusing all cases cannot pass.

A failed case remains in the report. After a workflow revision, that case becomes development evidence; a new held-out case is required for a fresh independence claim. Do not repeatedly tune against the same holdout and label the final result blind. Report diagnosis, planning, implementation and measurement failures separately.

Artifact: `qualification/heldout-results.json`, evaluator evidence, complete solver transcripts and a decision of pass/fail/inconclusive. If this phase fails, fix the evidenced capability gap before attempting 1A end to end. Do not resume broad factory expansion.

## Phase 7 Demonstrate transfer to the actual player experience

A held-out pass permits preparing one real scene-repair experiment. It does not authorize spending or deployment. Select a still-unresolved problem from current evidence, avoiding a duplicate of a human-supplied patch. Have the qualified factory diagnose it, choose the repair and preregister the experiment itself.

For identical-command behavior, use matched fixed replay with hosted-equivalent provider settings. For guidance/pacing, use a responding blind player with the same model/profile/start-state distribution across arms. Do not feed that player the intended solution. Verify actual state, custody, grounding, authored outcome and transition cause; inspect complete player-facing prose. Report knowledge progress, world action success, forced exits, rejection and fun separately.

Choose replicate counts from the applicable runbook and freeze them before running. The live bench currently specifies at least four replicates; hosted qualification follows its own runbook. Separate a targeted repair pass from whole-scene zero-stuck qualification. A targeted fix may succeed while the scene remains unqualified.

Apply existing free gates, Opus fun review, CI and SHA-bound staging procedures. Hand-built station-code PRs and factory-produced story PRs retain their distinct standing merge rules. Do not promote production as part of this milestone. If the run is interrupted or underpowered, retain partial evidence and mark it inconclusive; do not replace unsuccessful samples.

Completion artifact: `qualification/final-assessment.md` states what the factory independently solved, whether it generalized beyond 19q, player-experience evidence, remaining failures and the precise scope in which autonomy is justified.

## Verification and resume protocol

For implementation, follow `docs/testing-runbook/local-checks.md`. Run relevant focused tests during edits, then the quick tier with relevant heavy files and Ruff; the full suite follows repository pre-merge/CI rules. Update the existing runbook entry when a procedure changes. Keep dated outcomes here or in the workspace, not in the runbook.

At every phase boundary record: code/package hashes, owned files, artifact paths, commands and results, actual model usage, unresolved failures and the exact next task. Stop dependent work on a failed gate, but continue independent free preparation. Ask the owner only for unavailable policy/spend authority, not to choose wording or solve a scene.
