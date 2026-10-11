# Design review: implementation plan

Status (2026-10-11): Steps 1-3 done (Step 2 gate met on staging at f324cc17; Step 3 matrix and Brandon's decisions recorded). The two source conflicts Step 3 found (2A and 2C entry knowledge) are fixed and live-checked (PRs #599, #600). Step 4 done and live-checked (PRs #601 merged, #602 shard rebalance merged; live gate recorded in the status log); Step 5 merged (#607) and deployed to staging (Railway deployment `0accc21a`, `/version` sha `b259a037`); Step 6 smoke run with approved pointers only (branch `design-review-step6`, not merged); Steps 7-10 not started. Source: [chatgpt-design-review-answer.md](chatgpt-design-review-answer.md) (reviewed at `45a35cc3`, 10-step sequence). This plan turns that sequence into Ringer-sized tasks with gates. Update this file after each step is completed and tested (commit, what the check showed, what is untested), and refresh "Resume here".

## Resume here

Step 4 is finished: code and the 2C pilot are merged (#601) and the live gate ran on staging at a4ad67ed. Step 5 is merged and live on staging. Step 6 ran the three recovery paths with the approved cue text re-shown as the stage-two pointer (no `escalation_text` authored); results below. The 2A verb gap is fixed (see the last Step 6 entry). Open: the abrupt pointer placement; merge `design-review-step6` on his instruction; then Step 7. The `medical records` rejection found by the Step 4 live gate is fixed (see its log entry); the L2 script now waits on Railway's deployment list (#603). Branch per step, one PR per step, merge commit only on Brandon's per-PR instruction, delete the branch after green CI. Open question carried from the entry-knowledge fix: `k_scene_1b_entry` was left unchanged on purpose.

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

### Step 4, disclosure guards and 2C pilot (2026-10-11, branch `design-review-step4`)
- Ringer runs `design-review-step4` (T1 guards, PASS attempt 1; T2 recall, PASS attempt 2) and `design-review-step4-pilot` (T3, FAILED its own check on one wrong test; patch exported by hand from the kept worktree). Commit 4b21d9c5 plus the pilot commit.
- Built: `Entity.disclosure` (`legacy` default | `public`), world `disclosure_guards` (terms, audience `player`, exactly one of `unlock_fact` / `unlock_knowledge_id`), compiled into `KnowledgeIndexes.disclosure_guards`; a public entity is left out of `entity_alias_to_entities`. New global scan code `disclosure_guard_leak` (not scene-scoped; handoff text exempt; a term shared by several guards is released only when all are unlocked). Loader refuses unknown unlocks, duplicate ids, a guard term equal to a public form, and a hidden or `named_by` entity marked public. Recall now honours placed, in-scope scoped aliases through the same function as the resolver (`scoped_alias_entity_ids` in `knowledge.py`).
- Pilot: item `copied_janus_files` (name `copied JANUS files`, `disclosure: public`, scoped aliases `copied files`, `JANUS files`, `JANUS evidence`), placed under Kristin in 2C, 3A, 3B and 3C (placements are scene-local). No prose changed.
- Offline gate: 36-cell verdict table (4 sentences x 9 scenes) identical to base; matrix gains 12 rows, all for the new item, no other row changed; secret fixtures still rejected; five copied-files commands still match only `k_sl_2c_c_r1`. Full suite 1444 passed at 92.67% coverage, ruff clean.
- Fixes by hand after the failed check: the recall test asserted on the projection's `referenced_entity_ids`, which only lists entities a knowledge record establishes (no 2C reveal lists this item in `entity_ids`), so it now tests `_input_referenced_entity_ids` directly. Old tests updated for legitimate changes: the group-member test's 2C text anchor. `bench/affordance_known_gaps.json` gains four 1A entries (checks 2 and 3 on the two `t_1a_1b` gates): the affordance map matches the 1A reveals' terms `files` and `JANUS files` by substring against the new item's name. They are false positives of that matcher, not 1A gaps.
- Not done: no schema `disclosure_guards` entry is used by the shipped story yet (only tests exercise it); a custody check beyond placement; `named_by` secrets not migrated. Resolver now strips leading articles in scoped aliases (slightly looser than before); `item_facts._name_in_scene_scope` still has its own copy of the scope test.
- Untested: live behaviour. Gate still to run: smoke, then three linked 2B-to-2C hosted runs including a Michelle-first start (rejections, how the files are named, custody, turn at which c_r1/c_r2 fires, play vs timer).

### Step 4 live gate (2026-10-11, staging at a4ad67ed, Ringer runs `copied-files-michelle-first-smoke|full`, `freytag-affordance-live` smoke and x3)
- Hosted linked runs, 3 continuous replicates 1A through 2C: every scene exited by play in every replicate (6 scenes x 3), 2C at turn 8 each, transition cause `earned`. Rejected turns: 0 in 1A, 1B, 1C, 2A, 2C; 3 in 2B (1, 2, 0), all `narration mentions an unavailable entity 'medical records'` on a medical-terminal command, never about the copied files. In 2C the item `copied_janus_files` is shown from turn 0 in all three, so it is in the narrator's THINGS at entry in the hosted game. All three players copied the files as their first command (the opening sentence works for the model player); the copy path was not exercised by a player who skips it.
- Michelle-first arm (local bench, real narrator, 2C start; `bench/variations/copied-files-michelle-first.json`; 4 scripted commands, 3 replicates): 'Check my copied JANUS files.' fired `k_sl_2c_c_r1` on turn 3 in every replicate that reached it (3 of 3); the files were never rejected; final state in all three: files held by Kristin, condition `scanned`. Two of three replicates failed on the same `medical records` rejection when the scripted medical-terminal command repeated. In the bench the files were absent from THINGS until a command named them (the hosted runs show them from turn 0, so this is a bench entry-state effect, not confirmed as a game defect).
- Not covered: a Michelle-first player in the hosted game; the full journey past 2C; the 3A-3C placements (not exercised live); human play. Three replicates is smoke evidence only.
- Open defect, not from this step: `detention medical records` (world.yaml item, alias `medical records`) is guarded in 2B and 2C where the player has a medical terminal. It caused 3 rejected turns across 2 of 3 hosted replicates and ended 2 of 3 bench replicates. It is a natural next use of `disclosure: public` or scoped aliases, but it is a 3A thing, so decide whether the name is ordinary before changing it.
- Staging deploy timing: GitHub's staging job reports success before Railway has swapped containers, and each cap change by `scene-affordance-l2-all-live.sh` creates its own Railway deployment. Fix in progress: Ringer `l2-railway-wait` replaces the sleep-and-health polling with a wait on Railway's own deployment list (newest deployment id changes and reaches SUCCESS, then one version check).

### Medical records rejection fixed (2026-10-11, branch `medical-records-scoped-aliases`, Ringer `medical-records-alias`)
- Cause: the 3A item `detention_medical_records` had ordinary words as aliases (`medical records`, `survivor records`), so the entity-alias scan rejected them in every scene where the item was not nameable (3 rejected turns in 2 of 3 hosted replicates, 2 of 3 bench replicates). Fix: the proven scoped-alias technique (PR #590, grounding guide Things bullet): the two words moved from `aliases` to `scoped_aliases`; the name `detention medical records` and its guard are unchanged. No other data touched.
- Offline: 54-cell table (6 sentences x 9 scenes) differs from base in exactly 20 cells, all intended (`medical records` and `survivor records` accepted everywhere; the combined warning sentence accepted in 2B). The full-name sentence, `medical level` and `experiment records` cells are unchanged. Matrix: two rows `entity_name` to `scoped_alias`, nothing else. Existing 3A records tests unchanged and passing; full suite 1452 passed.
- Live (local bench, Michelle-first arm, 3 replicates): 3 of 3 completed (was 1 of 3), 0 rejected turns, 'medical records' appears in turn-10 narration and is accepted; the copied-files reveal fired on turn 3 in all three; files held by Kristin. Smoke evidence only; the hosted 2B and 2C scenes have not been rerun.
- Noted, not changed: `medical level` and `medical terminal` are still rejected outside their scenes (the base table shows `medical level` rejected in 2B and 2C, and `medical terminal` outside 2B). Same fix class if they bite in play.

### Hosted 2B and 2C rerun after the medical records fix (2026-10-11, staging at f1b3e95d, Ringer `l2-1a-2c-x3`)
- 3 continuous hosted replicates, 1A through 2C, after PR #604. Rejected turns: 0 in all 18 scene-runs (the earlier hosted run had 3 in 2B, all `medical records`). 1A, 1B, 1C, 2A and 2B exited by play in every replicate (earned). 2C exited by play in 2 of 3 (turn 8, earned) and by forced handoff in replicate 3 (turn 16). `copied_janus_files` was shown from turn 0 in 2C in all three.
- 2C replicate 3, read: the player copied the files on turn 1 (`k_sl_2c_c_r1` fired), then typed "Open Michelle's message." on turn 2. `k_sl_2c_d_r1` needs `purge_clock_started`, which the pacing event sets at turn 3, so the command was not yet eligible, and the player never retried it after turn 3 (it led the captives out instead). This is the known gap that a command typed before its `requires` is lost; it predates and is unrelated to the copied-files, medical-records and wait-script changes. It is the case Step 5 (unresolved-cue escalation) targets.
- The 2C result meets the usual 2-of-3 bar; it does not meet the stricter every-scene-by-play check that was set for this run. Three replicates is smoke evidence only.
- The L2 script's Railway wait (#603, #605) ran against real staging in the smoke and this run and both completed. Its per-poll lines are not in the Ringer output, so its behaviour poll by poll is not recorded. Railway deployments here carry no `commitHash` and report `SLEEPING` when idle (#605 accepts `SLEEPING`).

### Step 5, unresolved-cue escalation engine (2026-10-11, branch `design-review-step5`)
- Ringer `design-review-step5` (codex, 1 attempt, PASS, 363 s; manifest `scripts/ringer/design-review-step5/manifest.json`). Local re-run after applying the patch: 1457 passed at 92.60% coverage, ruff clean.
- Built: optional `FactDelivery.escalation_text` (fallback is `cue_text`); `CueStage` records (`cue_stages`) and `staged_cue_stage` on state and snapshot (defaults keep old saves loading; stage one stays in `delivered_cue_ids`; scene entry clears them, so re-entry is a new visit). Escalation stages once per visit when `turns_since_entry >= nudge_after_turns`, the cue was delivered, its fact is not asserted, `_cue_reveal_available` still holds and no other cue is staged. Delivered through `_compose_staged_cue` (authored path), consumed only on a committed, non-handoff turn that stays in the scene; a rejected turn restores the snapshot. Handoff precedence unchanged. Attempt bundle `cue_stage.delivered` now also true for stage two.
- Tests: `tests/test_cue_escalation.py` (new); `test_missed_pointer` now asserts the escalation; `test_persona_escalation.py` uniqueness assertion relaxed (stage one and two share a fact id).
- Not done / untested: no shipped delivery sets `escalation_text`, so no live behaviour changes yet (Step 6). `CueStage.last_turn` is stored but no rule reads it; the review (Finding 2) asked for "stage and last delivery turn per scene visit" so a later stage can be spaced from the last pointer and so Step 6 can report turns from pointer to earned reveal. Keep it, read it in Step 6.
- Cue safety gate (follow-up, same branch): the worker's claim that safety is enforced on the composed path was only half true. The engine does validate the composed text, but the loader does not check it, and an unsafe pointer would be rejected on every turn from the nudge on, because a rejected turn leaves it staged. The gate is `tests/test_cue_text_safety.py`, now parametrised over every shipped `cue_text` (stage 1) and `escalation_text` (stage 2), plus a test that a stage-two pointer naming `Phase Two` is rejected with `protected_narration_leak`. 31 passed. Step 6 text must pass this test before use.
- Gap filled (Ringer `design-review-step5b`, codex, 1 attempt, PASS, 366 s; manifest `scripts/ringer/design-review-step5/manifest-tests.json`): `tests/test_cue_escalation.py` now has 12 tests using the real `CloudflareTurnProvider` with its network call stubbed. Added: reveal earned before the nudge, spent alternative (asserts `_cue_reveal_available` is false first), rejected nudge turn restores state then an accepted turn records stage two, scene re-entry clears cue state and allows a new escalation, forced handoff still changes the scene, pointer delivered once as the last segment, old-save conversion. Full suite 1465 passed, ruff clean (worker run; I did not rerun the full suite locally). Step 5 offline gate is now met.

### Step 6, recovery runs with approved pointers (2026-10-11, branch `design-review-step6`, Railway staging at `b259a037`)
- Staging check first: Railway's deployment list shows `0accc21a` SUCCESS (19:55Z) with the three older deployments REMOVED, and the staging URL's `/api/v1/version` reports `b259a037`. GitHub's job status alone was not trusted. A first 1A smoke started before this was confirmed and was discarded.
- Arm: the local bench (real narrator, `entry_state: thorough`), `bench/variations/recovery-detours.json`, Ringer runs `design-review-step6-recovery-{1a,2a,2c}-smoke` then `-x3`. No `escalation_text` exists, so stage two re-shows the existing `cue_text`. Scripts are fixed commands: ten detour turns that match nothing, then the command the pointer invites. The bench caps a scene at 12 turns.
- 1A (laptop detour, nudge 10): 3 of 3 replicates. Pointer at turn 10, `k_sl_1a_b_r0` earned at turn 11, no handoff, 0 rejected turns.
- 2A (ignore the forms, nudge 8): 3 of 3. Pointer at turn 8, `k_sl_2a_b_r2` earned at turn 9 by 'Fill out the blank inspector forms with Brandon.'; the forced handoff still moved the scene at turn 11 (other facts unmet). 0 rejected turns.
- 2C (Michelle-first, long, nudge 9): 3 of 3. Pointer at turn 9, `k_sl_2c_c_r1` earned at turn 10 by 'Check my copied JANUS files.'; a different cue (`rebecca_office_required_for_broadcast`) followed at turns 11 and 12. 0 rejected turns.
- Turns pointer to reveal: 1 on every path. Assisted deliveries: 0 forced handoffs on 1A and 2C; 2A's exit was a forced handoff after the reveal. False disclosure: none; no rejected turn, and no pointer or narration named an unrevealed secret. Prose read at all nine pointer turns: the pointer is appended verbatim after the narrator's text and states only what the scene already shows; nothing orders the player. It sometimes lands abruptly (1A, after 'Check the front door.', the narration jumps to the drawer).
- Finding, 2A: the first recovery command I wrote, 'Ask Brandon about the inspection forms.', matched nothing and the scene ran to the forced handoff. `k_sl_2a_b_r2` accepts verbs like fill out, show and complete, not ask. The pointer says Brandon 'has laid out blank inspector forms', so a player who asks about them is not rewarded. Not fixed; a matcher or pointer wording decision for Brandon.
- Limits: the recovery commands are scripted from the pointers, so the engine side is deterministic and the three replicates agree turn for turn; only the prose varies. This shows the pointer arrives on the nudge turn and that a pointer-following command lands. It does not show a real player follows the pointer. No baseline arm (pre-Step-5 behaviour) was run: the old engine shows the cue once, so the comparison is known from the Step 5 tests. Hosted blind-player recovery runs and a Michelle-first player who skips the opening sentence are untested. Smoke evidence only.

### Step 6, 2A verb gap fixed (2026-10-11, branch `design-review-step6`; Brandon said to fix it)
- Technique: widen the reveal's match words, as the 1A drawer fix did (no new prose; the approved pointer is unchanged). Ringer `design-review-step6-2a-forms-verb` (codex, 1 attempt, PASS, 162 s): `ask` appended to the verb group of `k_sl_2a_b_r2` in `knowledge.yaml` (one line); new `tests/test_2a_forms_words.py` with the real matcher in a 2A state. 'Ask Brandon about the inspection forms.', '...the blank inspector forms.' and '...the credentials.' select `k_sl_2a_b_r2` uniquely; 'Ask Brandon how to reach the gate.', '...the facility layout.', '...the cooling system.' and two search commands do not. Full suite and ruff passed in the worker's check; I reran the new, matcher and package tests locally (154 passed).
- Live (local bench, Railway staging at `b259a037` for the engine's Step 5; the data fix is local until merged): `recovery-2a-ask-x3`, 3 of 3 replicates, pointer at turn 8, 'Ask Brandon about the inspection forms.' at turn 9 earns `k_sl_2a_b_r2`, 0 rejected turns. The previous run of the same command earned nothing.
- Not checked: other realizations that share the forms vocabulary in other scenes; hosted staging with the fix (needs merge and deploy). The abrupt placement of the appended pointer is still open and unchanged.
