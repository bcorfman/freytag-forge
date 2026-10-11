# Design review: implementation plan

Status (2026-10-11): Steps 1-3 done (Step 2 gate met on staging at f324cc17; Step 3 matrix and Brandon's decisions recorded). The two source conflicts Step 3 found (2A and 2C entry knowledge) are fixed and live-checked (PRs #599, #600). Step 4 in progress; Steps 5-10 not started. Source: [chatgpt-design-review-answer.md](chatgpt-design-review-answer.md) (reviewed at `45a35cc3`, 10-step sequence). This plan turns that sequence into Ringer-sized tasks with gates. Update this file after each step is completed and tested (commit, what the check showed, what is untested), and refresh "Resume here".

## Resume here

Step 4 (opt-in disclosure guards, 2C copied-files pilot) on branch `design-review-step4`. Before writing the spec, re-read `.plans/world-model.md` section 12, `docs/world-model-grounding.md` and `.plans/disclosure-decisions.md`. Branch per step, one PR per step, merge commit only on Brandon's per-PR instruction, delete the branch after green CI. Open question carried from the entry-knowledge fix: `k_scene_1b_entry` ("immediate place of pursuit") was left unchanged on purpose.

## Ground rules (from AGENTS.md and memory)

- Every code change runs through Ringer, one task per independent unit. Any check that runs the full suite needs `"check_timeout_s": 900`. Workers cannot run `uv`: use the main `.venv` with `PYTHONPATH`; remove failed worktrees before a rerun.
- Specs must let workers update old-behaviour tests.
- Plot or story text goes to ChatGPT Desktop (Steps 3, 6 author rounds); fix the prompt, not its output.
- New narrator-facing strings (rules, cues, pointers, escalation text) are written at a 12th-grade reading level; existing 8th-grade strings are left as they are. Apply any change to every narrating path. Brandon's change, 2026-10-11; AGENTS.md "Writing Narrator Rules" still says 8th grade until it is amended.
- Player input in probes: imperative, first-person possessives. Step 9 deliberately adds a separate robustness corpus; the canonical probe style stays.
- Measure each fix before the next. Live runs: smoke-test first, one Ringer task per run unit, hosted demo only for E2E.
- Run `uv run ruff check --fix . && uv run ruff format .` at the end of each step. Do not append results to `docs/testing-runbook.md`; record them here.
- Prior-art check (AGENTS "Fixing a Scene"): the review's Finding 5 is a new proposal after checking W1-W14. Findings 1-4 and 6 extend existing mechanisms (scoped aliases, `leak_terms`, handoffs, corpus test). Before Step 4 and Step 8, re-read `.plans/world-model.md` section 12 and `docs/world-model-grounding.md`.

## Pre-work: verify the review's claims against code

Per memory "verify plan questions against code first", before Step 1 a read-only Ringer `ask` (or direct reads) confirms each cited fact still holds at `e8722548`:

1. `nudge_after_turns` validated in `models.py` but unused in `engine.py` scheduling.
2. `delivered_cue_ids` excludes a cue after delivery.
3. Candidate projection keeps four (`knowledge.py`), fallback cap six (`cloudflare.py`).
4. 40-call semantic counter is per provider instance; web route builds a provider per request.
5. Blind-player validator rejects every `listen*` command and first-person/restraint input.
6. PRD line 29 bans model intent; authoring guide ~152 says cues wait for the nudge.

Record any claim that fails and drop or adjust the dependent step.

## Steps

### Step 1: six state-exact regression fixtures
- Cases: ordinary-name acceptance, premature secret, skipped reveal, missed pointer, matcher tie, more than four eligible reveals. Current defects asserted explicitly (xfail-style with reason, or asserting present behaviour with a comment naming the review finding).
- Place beside `tests/test_narration_corpus.py`; build real engine state at each point, no fully-earned substitute state; no network.
- Includes must-reject entries (the corpus gate currently checks only formerly accepted).
- Gate: new tests pass in the suite; coverage gate stays at 90%.
- Untested after: live behaviour.

### Step 2: typed attempt bundle (hosted path)
- Immutable record per attempt: code/package/config identity, pre-state, command, typed request/reply per model stage, selected reveal, committed delta, cue stage, transition cause (`earned` | `forced` | `timer`). Keep rejected attempts. Operational failure recorded apart from gameplay miss. Versioned schema.
- Do not overwrite the single prompt slot in `blind-player.js`; add the bundle beside it, keep old capture readable.
- Gate: replay one accepted, one rejected, one forced-handoff continuation through the real engine with model calls stubbed; classification matches. Smoke live: one success, one rejection, one short forced continuation keep all stages and causes (smoke-test first).
- Fixes `play` vs `timer` mislabel of late earned exits.

### Step 3: disclosure vocabulary review (author round, no code)
- Inventory shipped guards: entity-name guards, identifier-derived fragments (`phase_two` guards `phase`), `leak_terms`, scoped aliases.
- Classify each: public / secret-with-unlock-fact. ChatGPT Desktop round for genuine secrets' unlock conditions.
- Produce the nine-scene ordinary/secret matrix (early, earned, skipped-reveal states).
- Gate: matrix reviewed by Brandon. Output is a data file under `.plans/`, not engine change.

### Step 4: opt-in explicit disclosure guards (pilot)
- Schema: guard with `terms`, audience, unlock fact or knowledge ID. Legacy compiler path kept for unreviewed records (`loader._compile_knowledge_indexes`, three loops in `narration_safety.py`). New declarations must pick a policy; never silently publicize existing names.
- Make resolver and recall (`item_facts.py`, `knowledge.py`) consistent on scoped aliases.
- Pilot: only the reviewed copied-files declaration in 2C (resolves the custody trade in the 2C declaration decision).
- Gate: before/after matrix from Step 3 shows only intended changes; adding a public object changes no unrelated verdict; secret fixtures still rejected; custody tracked. Live smoke: three linked 2B-to-2C runs including a Michelle-first start.
- Risk: omitted secret becomes public. Mitigation: legacy default plus matrix.

### Step 5: unresolved-cue escalation
- Implement `nudge_after_turns` in `engine.py` scheduling: one stronger pointer for an eligible unresolved reveal, stage + last delivery turn stored per scene visit, snapshot-safe, not consumed on rejection, stops when earned or source spent. Tie cue to reveal via optional link field; fallback text is the existing cue.
- Save compatibility: convert delivered flags to stage-one history, or version the save.
- Append through the existing authored path, never via narrator.
- Gate: timeline tests (ignored cue, earned reveal, spent alternative, rejection, save/load, scene re-entry); no pointer names an unrevealed secret.
- Forced delivery stays; recorded as assisted progress.

### Step 6: recovery story round (1A, 2A, Michelle-first 2C)
- Reuse approved pointers first. New escalation text goes to ChatGPT Desktop, scored with the real matcher.
- Run documented detours via Ringer, three per path, each must actually exercise recovery (check the bundle's cue stage).
- Report turns pointer-to-reveal, assisted deliveries, false disclosure vs baseline. Read the prose for coercion. Smoke evidence only.

### Step 7: reveal universe separated from narrator truncation
- Selection service evaluates exact matching over all eligible reveals; the four-item narrator projection no longer bounds it. Semantic fallback gets its own bounded shortlist.
- Telemetry, separate records for: no eligible action, shortlist exclusion, exact tie, semantic refusal, provider error, budget exhaustion. No semantic policy change.
- Gate: candidate five remains exact-matchable; distinct records for each outcome; saved-command set with positive, wrong-target, partial-action, ambiguous cases, more than four eligible, request reconstruction.

### Step 8: typed action contract, 2C copy step, shadow mode
- Re-read W decisions and grounding guide first (prior-art note above).
- Contract: target references, short required act, prerequisites, positive and near-miss examples. Semantic question derived from it. Runs in shadow beside the existing path; effects still validated deterministically; tie stays ambiguous.
- Import current evidence groups unchanged as the fast path.
- Gate: ten samples each for six hard commands against both contracts, then three 2C continuations. Score false grants before recall; keep current path if false grants rise. Activation is a separate decision.
- Follow-up (not in this step): persisted semantic-call budget (per session, not per provider instance); update PRD line 29 to describe bounded model proposal honestly.

### Step 9: raw-language robustness profile
- Add a second corpus (polite requests, pronouns, corrections, scene-valid listening, unrelated restraint clauses) and a distinct blind-player profile; remove the blanket `listen` rejection; keep raw input beside normalization.
- Amend AGENTS "Writing Player Input" to separate canonical probe style from supported player language (Brandon approves wording). Fix PRD line 29 and authoring guide ~152 contradictions here.
- Label clarification-needed cases separately; do not widen runtime matching.
- Gate: paired command variants in the same state keep intended outcomes; three matched scene starts per profile.

### Step 10: read-only scene contract view
- Report assembling plot metadata, knowledge, routes, handoffs, pacing per scene with provenance and duplicate-value warnings.
- Gate: a reviewer can trace cue, action, delivery, effect, exit for 2C from one report.
- Output decides whether the compiler pilot is worth starting.

## Explicitly deferred

- Authoring compiler (Finding 5 consolidation): only after Step 10 shows it removes real authoring work.
- Persisted semantic-call budget and PRD rewrite beyond Step 9's wording fixes.

## Measurement cadence (from Finding 4)

Deterministic replay on every affected change; targeted live arms when a model behaviour changes (10-15 replies per arm for a fixed prompt); three scene continuations as smoke gate; full journey after a batch or shared-progression change. Scene success-rate decisions use 12 paired entry scenarios per arm with uncertainty. Do not pool scenes as replicates. Three clean runs are smoke, not reliability.

## Status log

(Append per step: commit, what verification showed, what is untested.)

### Step 1 (2026-10-11, branch `design-review-step1`)
- Ringer run `design-review-step1` (manifest `scripts/ringer/design-review-step1/manifest.json`), codex, 1 attempt, PASS, 199 s. Added `tests/test_design_review_fixtures.py` (six tests). Re-run locally after applying the patch: 6 passed, ruff clean. Worker's full suite: 1404 passed (coverage gate not run).
- Pre-work claims 1-5 all HOLD at e8722548 (`nudge_after_turns` unused in engine.py:410-435; delivered cue excluded at engine.py:417-433; projection default 4 at knowledge.py:87 and fallback cap 6 at cloudflare.py:400-416; 40-call counter per provider at cloudflare.py:249 with a provider per turn at web_demo.py:334-337; matcher ties return None at candidate_matcher.py:100-101). Claim 5 (blind-player `listen` filter) and claim 6 (PRD line 29, authoring guide ~152) were not in the worker's list: still unverified, do before Step 9.
- Tightened (Ringer run `design-review-step1b`, 2 attempts, PASS, 331 s; manifest `scripts/ringer/design-review-step1b/manifest.json`): ordinary-name test is now paired (public `drawer` in 1A and `park` in 1B accepted and committed; `Rebecca` rejected in the same 1A state). Secret test is parametrised over three guard kinds: protected knowledge term (`Phase Two`, code `protected_narration_leak`), declared leak term (`cooling-water imbalance`) and not-yet-nameable NPC (`Rebecca`), both `narration_known_term_leak`, each after asserting the reveal is unearned. Skipped-reveal builds a late 3C state with the Phase Two reveal's facts retracted, asserts rejection, then accepts it in a copy where the facts are re-asserted.
- Remaining limit: the package has no scene after 3C, so the skipped reveal is an earlier reveal within the final scene, not one skipped across a scene boundary. Five-eligible fixture uses real 1A data (`k_sl_1a_c_r2` dropped by the 4-cap).
- Untested: live behaviour; coverage gate.


### Step 2, Python side (2026-10-11, branch `design-review-step2`)
- Ringer runs `design-review-step2` (codex, 1 attempt, PASS, 405 s; full suite 1412 passed, ruff clean) and `design-review-step2b` (tests only, PASS, 212 s). Manifests in `scripts/ringer/design-review-step2/`.
- Added `storygame/runtime/attempt_bundle.py` (frozen, `schema_version` 1, unknown versions refused), `RuntimeEngine.attempts` / `last_attempt` (last 24; recorded on committed, rejected, game-break and provider-failure paths, snapshot restored before recording), and `attempt_bundle` in `/api/v1/turn` responses behind `FREYTAG_EXPOSE_PROMPT=1` (409 body carries it; `detail` and rejection header unchanged; absent when gate is off).
- `transition_cause` is observed from the branch that moved the scene: staged handoff = `forced`, resolution-deadline backstop = `timer`, otherwise `earned`. Not a turn-count comparison, so late earned exits are no longer `timer`.
- Tests (`tests/test_attempt_bundle.py`, 8): round-trip and version refusal, accepted and rejected, operational failure apart from rejection, forced handoff, late earned 1A to 1B (`k_sl_1a_b_r0`), same late state forced, deadline timer, gated web rejection. No engine logic change was needed in the second run.
- Limit: `timer` currently means only the resolution-deadline backstop; a timed route event that moves the scene without a selected reveal is classed `earned`. Unverified whether any route does that.
- Untested: blind-player.js integration, live behaviour, coverage gate.

### Step 2, blind-player.js (2026-10-11)
- Ringer run `design-review-step2c` (PASS, 197 s, 1 attempt). `turnRecord` carries `attempt_bundle`; `collectBundles` and `bundlesCategory` write a `blind-player-bundles` report beside the untouched prompts report; `analyseRun` takes `exit_cause` from the bundle (earned=play, forced, timer) with the old turn-count rule as fallback, and adds `exit_transition_cause`, `bundle_rejected_turns`, `forced_exit_rate`. `helpers.js` submitTurn attaches `error.payload` and `error.status` to a non-ok error; the spec reads the bundle from it on a 409.
- Frontend node tests 85 pass locally. `error.payload` has no unit test (needs Playwright).
- Untested: live smoke (one success, one rejection, one short forced continuation). Hosted staging serves main, so this waits for the merge and SHA-bound staging deploy.

### Step 2 targeted live probes (2026-10-11, staging at 806c5174)
- Smoke defect found: all three 1A exits were labelled `timer` but were earned (reveals on turns 2, 3, 5, authored transition fired on turn 8 of 13 on a turn that selected nothing). Cause: the first `transition_cause` rule treated "this turn selected no reveal" as timer. Fix (Ringer `design-review-step2d`): scene unchanged = none; staged handoff = forced; deadline backstop produced segments = timer; any other scene change = earned. New test `test_authored_transition_on_a_no_reveal_turn_is_earned`; the old deadline fixture's facts satisfy the authored transition, so it is now earned too.
- Probe run (`scripts/ringer/design-review-step2/probe_live.py`, run by the Ringer check): 13 idle turns in 1A, the 13th (the handoff turn) committed with cause `forced` and moved the scene to 1B. Two protected-term inputs ("Say JANUS out loud.", "Ask for Rebecca.") were rejected with bundles whose `rejection.code` equals the `X-Freytag-Rejection-Code` header (`protected_narration_leak`, `narration_known_term_leak`); the rejected turns left the session playable. Staging allows about 10 turns a minute per session, so the script backs off on 429.
- Open: `timer` is now rarely reachable. `_apply_resolution_deadline_backstop` runs after `_apply_authored_transition` in the same turn, so a scene change on the turn the backstop commits facts cannot happen; a later exit would be classed `earned`. No test or live run shows `timer`. Decide whether `timer` should mean "a deadline-backstop event fired in this scene visit before the exit" (needs a state flag) or be dropped from the enum.
- Still unobserved live: an earned exit after the handoff turn (needs the cause fix deployed).

### Step 2, timer made reachable without a flag (2026-10-11, PR #595 branch)
- Ringer `design-review-step2e` (2 attempts; its only failing check was ruff on my own `probe_live.py`, fixed by hand). `TurnRecord.deadline_event_ids` (default empty, old saves load) records the resolution events the deadline backstop committed that turn; the engine copies it onto the turn record right after the backstop. At a non-forced scene exit, `_deadline_transition_cause` reads the records of the visit just left (bounded to 24, any shortfall degrades to `earned`) and re-tests the taken transition's triggers with the backstop's asserted facts removed: not satisfied = `timer`, else `earned`. No mutable flag; `_apply_authored_transition` now also stores the taken `transition_id` on the turn record.
- Hand edit after review: the re-test uses the post-exit facts (the worker used the pre-turn facts, which would miss a trigger fact earned on the exit turn itself and call that exit `timer`). No test pins that case yet.
- Tests: 13 in `tests/test_attempt_bundle.py`; full suite 1419 passed. The real package has resolution events only in 3C (terminal, no transition), so the timer test patches a package copy; no real scene can show `timer` live.
- Untested: a real-package `timer` exit; the exit-turn-earned-fact case above; live earned exit (needs this deployed).

### Step 2 closeout (2026-10-11, staging at f324cc17)
- Re-ran the 1A blind-player smoke (3 replicates, Ringer `design-review-step2-smoke`, PASS): 25 of 25 turns carried a bundle; 3 exits `earned` (reported `exit_cause` play, at turns 8, 9, 8 of a 13-turn handoff), 21 committed with cause `none`, 1 rejected attempt with its bundle. The earlier `timer` mislabel is gone.
- Live evidence for Step 2's three required cases: success (smoke), rejection (probe: JANUS and Rebecca, plus one in this smoke), forced continuation (probe: idle 1A, turn 13 `forced`). Earned exits confirmed live. Not observed live: `timer` (the real package gives no scene that can produce it; replay test with a patched package only).
- Step 2 gate met. PR #594 (earlier smoke note) is superseded by this entry.

### Step 3, inventory and matrix generated (2026-10-11, branch `design-review-step3`)
- Ringer `design-review-step3` (2 attempts, PASS, 415 s). `scripts/disclosure_matrix.py` reads the package and runs the real narration validator; outputs `.plans/disclosure-matrix.json` (480 inventory rows, 647 matrix rows) and `.plans/disclosure-matrix.md`. `tests/test_disclosure_matrix.py` checks determinism, completeness and freshness of the generated files. Full suite 1421+ passed.
- Guard kinds present: entity_name 102, identifier_fragment 7, knowledge_alias 107, leak_term 59, must_convey_phrase 201, scoped_alias 4. Suggested class: secret_with_unlock_fact 349, public_candidate 125, needs_review 6 (a heuristic suggestion, not a decision).
- Tables: earned-rejected 80; early-rejected public candidates 18; early-accepted secret candidates 26.
- Things to check before trusting the tables: (1) `memory card` and `michelle's memory card` are rejected in the 'earned' state of 1A and 1B, and `infrastructure corridor` in 2A and 3B; the earned state asserts only the owning reveal's establishes facts, so this may be how the state was built rather than an engine fault; (2) `janus`, `phase`, `phase two` are rejected in every scene's earned state, probably correct since the reveal sits in 3C; (3) `phase` is guarded only through the identifier fragment of `phase_two` (the review's Finding 1 example), which the data confirms.
- Brandon's decisions for the contested terms are recorded in `.plans/disclosure-decisions.md`. Correction: the earlier note here that `janus` family releases in 3C was wrong; JANUS is revealed in 2B (`janus_evidence`). Two entry-knowledge items assert reveals too early (2C purge clock, 2A false identities), confirmed in knowledge.yaml. The 'earned rejected' table may reflect how the states were built, not engine behaviour. No engine change. Step 3 gate met.

### Entry-knowledge fix (2026-10-11, PRs #599 and #600)
- Fixed the two source conflicts from Step 3 (2C purge clock, 2A false identities) plus spoiling objectives and pressure lines in 2B, 2C, 3B. Details, matrix effect and the live check (4 replicates each of 2A and 2C, 0 premature assertions) are in `.plans/disclosure-decisions.md`. Untested: reveals still landing after the fix, rejected-turn counts, 1B.
