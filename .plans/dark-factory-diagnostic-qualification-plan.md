# Dark factory diagnostic and story repair qualification

2026-11-22. Status: planned; no qualification model calls or live runs authorized by writing this plan.

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

### Resume here

- [x] Phase 1 inventory and measurement foundation verified (2026-11-22). Inventory and audit in `/home/bcorfman/dev/ringer-work/qual-20261122/qualification/` (`inventory.json`, `foundation.md`). Defects D1, D2, D2b repaired through Ringer and merged in PR #817 (`83dac802`); the gate is met.
- [~] Phase 2 development and isolated held-out cases prepared (2026-11-23 update: private answer records written by six Opus evaluator sessions; held-out candidates 1B healthy, 2A healthy, 2B narration_provenance defect, 3A wording_or_matching defect; scoring spec frozen, sha256 c4917eb7cc4f99bd37e31384c75536a886b5f9276f02fb7d47820a00f650bba1; still missing 2 more defects incl. one story_structure, and the separate derivability sign-off). Done: case builder `tools/make_case.py` (pinned commit, clean export, leak scan, hash manifest), design `phase2.md`, five unplanned billed blind-player runs. Not done: the evaluator's private answer records, the derivability sign-off, the frozen scoring spec, and the run specification below. Deviation recorded: fresh billed runs came earlier than this plan places them, with no call ceilings or dry run, and cost $0.733 Cloudflare against about $0.35 approved (calibration table in the main plan). Saved diagnosis-shaped evidence exists only for scene 1A (15d, 17c, 18c; pre18c duplicates 17c).
- [x] Phase 3 current-factory baseline recorded (2026-11-23): `qual-20261122/qualification/baseline-results.json`, `gap-report.md`. Planner saw no failing turns because `fix_plan._bound_evidence` dropped all of them; rerun owed after the fix.
- [ ] Phase 4 bounded investigation implemented only where needed.
- [ ] Phase 5 structural repair completes through the factory.
- [ ] Phase 6 twelve held-out solver trials evaluated.
- [ ] Phase 7 real player-experience transfer assessed.

Next action: finish Phase 2 under the plan's rules: write the run specification (exact prompts, call and token ceilings, estimates, output paths, dry run) for the evaluator and the Phase 3 baseline, and request authorization before any model call. Owner decision 2026-11-22: strict adherence to this plan; the proposed pivot to real tickets is not adopted.

**2026-11-23 resume.** Re-read the state: `main` at `83dac802`, run specification R1 to R4 written in `qual-20261122/qualification/run-spec.md`, no model call made since. Free finding: the 3B failure cannot be diagnosed from saved artifacts because the live playtest station drops the runner's output on a non-zero exit (see the run spec). Waiting on the owner's yes or no per item R1 to R4 before any model call.

**2026-11-23 progress (owner's go: R1, R2, R3 per the run spec; R4 held).**
- R1 done through Ringer (round 21a, both tasks passed first attempt, 203k and 68k Codex tokens): `factory/qualification/run_case.py` (ceilings mandatory, `private/` never read, dry run makes zero calls) and the live-playtest station now keeps the exit code and a redacted 2,000-character tail of a failed runner. Local branch `qualification-runner`, commit `144e82a1`, not pushed, no PR; needs the owner's word like any station-code change.
- R2 done: six fresh read-only Opus sessions (`qual-20261122/tools/run_evaluator.py`; deviation from the spec: `--bare` needs an API key, so isolation is tools Read/Grep/Glob, `--strict-mcp-config`, `--setting-sources project,local`, auto-memory off, with the session killed if init shows other tools or non-builtin plugins). Estimate before: about 330k tokens, ceiling 480k. Actual: 255k counted (cache reads excluded), five-hour window peak 35%, seven-day 2%. A first attempt was killed by my own over-counting (I counted one message's usage once per content block; fixed) and one by the isolation guard before any model work. Answers: 15d defect (story_structure), 18c defect (wording_or_matching), held-out candidates 1B healthy, 2A healthy, 2B defect (narration_provenance), 3A defect (wording_or_matching). Evaluators called every case derivable; two quote mismatches in the 3A answer, and the separate derivability sign-off is still open. Held-out set status: 2 defects and 2 controls sealed-candidate; at least 2 more defects (one story_structure) are still missing, which is R4.
- Frozen scoring spec: `qual-20261122/qualification/scoring-spec.md`, sha256 `c4917eb7cc4f99bd37e31384c75536a886b5f9276f02fb7d47820a00f650bba1`.
- R3 estimate before the run: about 70k Claude tokens per development case (planner prompt about 8.7k tokens by dry run, up to 3 attempts plus an optional classifier call), 140k in all; ceiling 75k per case, 4 calls per case.
- R3 done (2026-11-23): baseline on 15d and 18c, 4 calls, about 4k tokens actual vs 140k estimated (0.03x: the planner prompts carried no turns). Both cases: planner answered `unsupported` (station_code) because `failing_turns` was empty; cause found and reproduced: `fix_plan._bound_evidence` silently drops all failing turns when the rest of the packet exceeds 12,000 characters (1A: 23 turns, 18.7k of 40.0k). Results in `qual-20261122/qualification/baseline-results.json` and `gap-report.md`. Gate result: Phase 3 recorded; first gap is silent evidence truncation (then no investigation step, then no structural route). Next: bounded repair of the evidence cap through Ringer (free), then one rerun of the same baseline (needs the owner's go, about 70k tokens). R4 still held.

### Resume here (2026-11-23, session interrupted by the owner to record progress)
Owner said **yes to all three**: (1) fix the evidence cap, (2) rerun the same baseline once, (3) R4 billed scene runs. Nothing from these three has started; no model call has been made since the R3 baseline. State: branch `qualification-runner` (local, commit `144e82a1`, not pushed, no PR) holds R1; `main` is untouched; the Ringer manifest `scripts/ringer/1a-stuck/round21a-qualification-runner-manifest.json` and its builder are committed on that branch.
Next actions, in order:
1. **Ringer task A (free engineering, Codex):** repair `factory/stations/fix_plan.py::_bound_evidence` so the packet keeps the failing turns the diagnosis rows reference, cuts lower-value parts first (candidates, fact readers, precedents) and adds a truncation marker (`truncated` with what was cut) to the evidence; hermetic tests; a regression test with 20+ turns proves some turns survive. Own only `factory/stations/fix_plan.py` and `tests/test_factory_fix_plan.py`. Branch from `qualification-runner`.
2. **Ringer task B (same batch, disjoint files):** per-run spend cap for the live playtest station: refuse a billed run unless the payload carries `max_usd`; estimate = replicates x turn cap x 0.0074 USD per counted turn (measured 2026-11-22), refuse when the estimate exceeds `max_usd`, record `estimate_usd` on the ledger row, and flag `cap_exceeded` if the measured Cloudflare spend passes `max_usd`. Own `factory/stations/live_playtest.py` and `tests/test_factory_live_playtest.py`. This is the "ticket-enforced cap" R4 waits on.
3. **Rerun of the baseline** on 15d and 18c with `qual-20261122/tools/run_baseline.sh` (change the out dir to `baseline2`, same ceilings: 4 calls and 75k tokens per case). Write the estimate (about 70k tokens, 140k ceiling in all) in the calibration table before, actual after. Score with the frozen spec; keep run 1 as is.
4. **R4:** after task B lands, find why 3B failed (the new output tail will say), then runs on 3B, 1C, 2C at 3 replicates through `qual-20261122/tools/run_scenes.sh` style, each with `max_usd` (estimate about $0.45 total, ceiling $0.70, plus about $0.05 OpenAI; staging must be at the commit under test). Write estimate before and actual after. Then one evaluator session per new case (`tools/run_evaluator.py`, 80k ceiling, about 40k expected).
5. Then: derivability sign-off by a fresh evaluator invocation, seal six held-out cases, continue with Phase 4.
Standing: station-code branches wait for the owner's word to push or merge; `factory/config/**` is frozen (do not edit the allowlist); evaluator sessions run via `run_evaluator.py` (Ringer has only a Codex engine here); do not run `rm` with globs (the harness blocks it).

### Resume here (2026-11-23, later: owner's three yeses carried out)
Branch `qualification-runner` (local, not pushed, no PR; station-code branches wait for the owner's word) now holds, on top of `144e82a1`: `c82dcbb9` (round 21b: `_bound_evidence` keeps failing turns and reports every cut in a `truncated` marker; live playtest needs `max_usd`, refuses an estimate above it, records `estimate_usd` on the ledger row, flags `cap_exceeded`), `4009cc64` (round 21c), the round 21d commit (evidence limit 24,000 characters, measured on the two 1A cases so every failing turn at 150 characters, beats and exits survive) and `88f20e21` (R4 driver passes `max_usd` and `turn_cap`). Ringer: three rounds, all first-attempt passes, 98k + 140k + 84k + 40k Codex tokens; no model call in any of them.
1. **Evidence cap: done.** Run 1's `unsupported (station_code)` on both development cases is gone.
2. **Baseline rerun: done** (`qual-20261122/qualification/baseline2-results.md`, outputs `baseline2/`). 4,575 counted tokens against a 140k estimate. 15d: planner routes `unsupported` / `story_edit` for sibling spending (a real, different defect from the record's surrender branch; wrong mechanism against the record, right route class). 18c: right class (wording), wrong target (planner fixed a one-turn Walt wording row; the diagnosis rows had classed the dominant cause, `lead_outside_scene`, 6 turns, correctly and the planner passed it over). Gaps in order: the planner follows a row, not the cause with most player harm; the surrender-style defect has no rule row and needs bounded investigation (Phase 4); the structural route is only a label (Phase 5).
3. **R4 billed runs: done, 3 scenes.** 1C: 11 turns, 3 stuck (all replicate 2). 2C: 6 turns, 0 stuck. 3B: failed again, cause found from the new output tail: the Playwright `blind-player` test has a fixed 20-minute `test.setTimeout` and each replicate first replays the earlier scenes (8 for 3B, up to 160 turns); 2C's three replicates already took 18 minutes. It is a harness limit, not a story fault. Cloudflare $0.434 against $0.50 estimated and a $0.70 ceiling; OpenAI about $0.015 plus unknown for 3B. 3B was not rerun.
4. **Evaluator sessions: done for 1C and 2C** (35.5k and 34.5k tokens against 40k each; five-hour window 15%, seven-day 5%). 1C `healthy` (replicate 2 ignored the authored order; the source authors that recovery), 2C `defect` / `narration_provenance` (a `voiceable: true` claim whose bookkeeping `says` text the narrator speaks as dialogue). Both marked derivable, 2C with uncertainty allowed.

**Held-out set status (not sealed).** Controls: 1B, 2A, 1C (three candidates, two needed). Defects: 2B narration_provenance, 2C narration_provenance, 3A wording_or_matching (two quote mismatches in the 3A record are still to fix). Missing: **one defect whose mechanism is story_structure**, in a scene other than the 1A development scenes, so the Phase 5 requirement can be exercised on held-out data. Still owed: the separate fresh-evaluator derivability sign-off, then sealing.

**Next, in this order (owner decisions in bold).**
- **Decision: the story_structure defect.** Options: (a) fix the harness timeout so 3B can be run (scale `test.setTimeout` by replicates and prefix length, one bounded frontend ticket through Ringer, then rerun 3B at 3 replicates, about $0.2 to $0.25 and the same timeout risk is removed), or run 3B at 1 replicate first (about $0.07) to see whether it yields a structural case; (b) run 3C or 1A-variant scenes the same way. I recommend (a) with a 1-replicate probe before the full rerun. Needs the owner's go (billed).
- Fix the two 3A record quote mismatches and run the derivability sign-off (one fresh Opus session per case, about 35k tokens each, free of dollars).
- Phase 4 (bounded investigation) has its first evidence now: the baseline shows the two gaps it must close (cause with most player harm over first row; surrender-style defects with no rule row).
Standing items unchanged: `factory/config/**` frozen; evaluator sessions through `run_evaluator.py`; no `rm` with globs; no merge to main during staged runs.

### Seeded scene entry (2026-11-23, owner decision: start a scene anywhere; `thorough` default, `bare` selectable)
Why: the hosted blind player replayed every earlier scene live (3B: 8 scenes, up to 160 billed narration turns), which hit the 20-minute Playwright timeout and cost $0.027 per counted turn on 2C. The engine already seeds offline (`bench` `entry_state`); the hosted session endpoint could not. Ringer round 22a (`build_round22a_start_scene.py`): backend task passed first try (133k tokens); the frontend task's work was sound but my check ran the whole `node --test` set, and 7 of those files fail on `main` itself (they read `data/stories/continuity-initiative/knowledge.yaml`, removed in round 6i): the attribution-audit, authored-spans, judge-journeys, knowledge-available, package-clock, roleplay-judge and scene-partition tests. I took the worker's tree, ran the 17 baseline-passing files plus the new one (142 pass), and exported its patch. Those 7 stale tests are a separate cleanup ticket, not done.
Where it lives: local branch `seeded-scene-entry` (worktree `/home/bcorfman/dev/ringer-work/pr-seeded-entry`, cut from `main` `83dac802`, one commit, not pushed, no PR). Product change (hosted API + e2e spec), so it needs the owner's word to push and merge, then CI and the staging deploy of the merged SHA before any seeded run. Architecture check: `entry_seed.py` is a verbatim move that composes the existing adapters in `storygame/runtime/world_model.py`; `web_demo.py` adds only HTTP gating (403 without the test token or in production, 422 for a bad scene or state). No world-only logic was added, so nothing goes to `worldkeeper`.
Labelling: seeded runs carry `entry.mode: "seeded"` and state; they are not whole-path evidence. Next once merged and staged: 3B at 3 replicates seeded (estimate to be written first, about 6 counted turns per run x 3 x $0.0074 plus the opening, under $0.15).

### Canonical entry states (2026-11-23, owner decision: derived canonical path, committed golden snapshots, worldkeeper owns the world part)
Trigger: the owner pointed out that entering a scene cold means the World state must be right and managed. Measured offline for scenes 1B to 3C: `bare` entry has 87 to 115 facts and none of the earned story facts (113 missing at 3B, earned items still hidden); `thorough` has 203 to 431 and earns every optional storylet. Neither is a real player's state.
Built through Ringer on branch `seeded-scene-entry` (PR #818, open, not merged; CI pending at the time of writing), rounds 22a, 23a to 23d, all first-attempt passes except two checks of mine that were wrong (the whole-`node --test` check on seven stale files; a grep for `_package_root` that matched `default_package_root`): `World.export_state/import_state/entry_problems` and `diff_states` in worldkeeper (with a drift test over every `wk_` predicate); a `canonical` persona (only `required_storylet_ids` storylets; all 8 hops earned; whole path about 2 s); nine golden `entry/<SCENE>.json` files with source fingerprint; `python -m storygame.runtime.entry_snapshots check|write`; a carry-in report (three optional storylet chains are not reachable from canonical entry: SL-1C-E, SL-2C-G, SL-3A-H, gated on optional earlier discoveries; informational only); `start_state` `canonical` default for the hosted session; Playwright defaults to `canonical`. Full suite without coverage passed on the final tree (4,999 in `tests/`, plus worldkeeper).
Consequences for qualification: seeded runs are labelled `entry.mode: seeded` with state `canonical`; canonical entry is the route minimum, so optional-chain content in 1C, 2C and 3A is not reachable in a seeded run (use `thorough` for those, labelled). Seeded results are not whole-path evidence; 1A remains the only real-start scene. Next once PR #818 is merged (owner's word), CI is green and staging shows the merged SHA: write the estimate, then run 3B at 3 replicates seeded canonical (about 6 counted turns per run, under $0.15 expected), have the evaluator judge it, and look for the missing story_structure defect. Open: the seven stale frontend test files (read the removed `knowledge.yaml`) are a separate cleanup.
**PR #818 merged 2026-11-23** (merge commit `38d1af20`, CI green: static checks and six shards; local and remote branch deleted). The post-merge `tests` run on main (which deploys staging) was queued when this was written. Do not start the 3B seeded run until `/api/v1/version` reports `38d1af20` (the step-7 driver waits for the SHA itself). Note: `coverage nightly` failed on the previous main commit (`83dac802`); it is the nightly job, not part of this PR, and not yet looked at. `qualification-runner` (factory station commits through `88f20e21`) is still local and now behind main; it needs a rebase and the owner's word before a PR.

### Owner: "Open PRs and make the rest of the fixes in the order that makes sense" (2026-11-23, evening)
Order chosen: (1) rebase and PR the factory branch, because the planner and spend-cap code the next billed run needs lives there; (2) the red `coverage nightly`; (3) the stale frontend tools; (4) the seeded 3B run once staging serves `38d1af20`.
- **Rebase done.** `qualification-runner` rebased onto `38d1af20` without conflicts. Running the whole factory suite on it (earlier rounds ran focused files only) found one real regression of mine: `tests/test_factory_claim_edit.py::test_evidence_menu_and_candidate_matcher_context_are_bounded` failed because the evidence cut dropped the claim a failing turn offered when the ticket had no diagnosis. Round 24a (first attempt, 166 s, 46.6k tokens) now protects every offered or matched candidate like a diagnosis claim; commit `be3d8010`.
- **`coverage nightly` has been red since 2026-11-02** (last green 11-01 `1abb54b0`, 12 straight reds; not caused by this work). Ten nightly-only tests fail (the normal `tests` run skips them; reproduce with `pytest --run-nightly`). Cause: `06b2ccb3` "Rebuild 3C as a finite evacuation that ends the game". Six are dry-run tests of the archived Stage 7 3C probe, whose scripted prefix predates the rebuild; they fail inside the probe, not the engine. Four are `test_game_path_journeys` cases for `k_sl_3c_d_r1`, `k_sl_3c_d_r2`, `k_sl_3c_e_r1`, `k_sl_3c_e_r2`.
- **Real story gap found (candidate for the held-out `story_structure` slot).** SL-3C-D (network fractures) and SL-3C-E (Phase One / Phase Two reveal, the sequel hook) need `captives_reaching_surface`, which only the old `resolution_escape` event sets. After the rebuild the game ends through `resolution_archive_and_rebecca` / `evacuation_complete` first, and no route the journey harness tried (c_r1, c_r2, with and without f) ever plays D or E. The rebuild commit says Phase Two "becomes an optional epilogue", so the design intent is not met. Repair is a story decision (the weigh-fun rule applies: unreachable content is a question of worth, not a reason to delete); it is not part of the nightly fix.
- Round 24b (in progress when written): delete the six stale probe tests; pin the four journeys as a named strict `xfail` (story gap N-3) so the nightly is honest and turns red the day the story is fixed.
- **Stale frontend tools (seven node test files).** The canon judge, authored-spans, knowledge-available and roleplay-judge tools read `knowledge.yaml`, `handoffs.yaml`, `pacing.yaml`, `storylet-routes.yaml` and `plot.md` from `data/stories/continuity-initiative/`. Those files moved to `tests/fixtures/parity/continuity-initiative/legacy/` (frozen) in `1ef50250` (2026-11-17), when the default story became the compiled `source/` tree. Pointing the tools at the frozen copies would silently judge stale story text; the repair is an exporter from the live package. Separate ticket, after the PRs.
- **Seeded 3B rerun blocked on staging configuration (2026-11-23).** Staging serves `38d1af20` (`scene-v1`, `staging`), but `POST /api/v1/session` with `start_scene` returns `403 start_scene requires an opted-in staging test` for the `.env` token. A probe turn with a deliberately wrong test-clock token ran normally (HTTP 200, one billed narration turn, about $0.008), which is only possible when `FREYTAG_ALLOW_TEST_CLOCK` is not `1` on the staging service. `docs/testing-runbook/hosted-probes.md` section 8 says staging sets both variables; either they were lost or never set after the staging rebuild. I cannot read or set Railway variables (CLI not logged in). Owner action: `railway login`, set `FREYTAG_ALLOW_TEST_CLOCK=1` and `FREYTAG_TEST_CLOCK_TOKEN` (same value as `.env`) on the staging service, let it redeploy, then rerun `sh ~/dev/ringer-work/qual-20261122/tools/run_3b_seeded.sh` (estimate and cap already in calibration row 24). The run itself cost $0.
- **Round 24b result and PR.** The worker's diff was right on the second attempt (six stale tests deleted, four journeys pinned strict xfail, 112 passed / 4 xfailed in the kept worktree); my check failed it because `git diff --cached --name-only` lists a deleted file and ruff then reported E902 on it. Same class as the round 23d grep mistake: checks must list files with `--diff-filter=d` before linting. I verified by hand and shipped the diff as PR #820 (`nightly-3c-honest`, from `main`, tests and one plan table only). It records the story gap as N-3 in `.plans/game-path-completion-matrix.md`. The factory branch PR is #819.
