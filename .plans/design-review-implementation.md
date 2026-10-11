# Design review: implementation plan

Status (2026-10-11): Step 1 merged (PR #592). Step 2 merged (PR #593) with a partial live smoke; a rejection and a forced or earned exit are still unobserved live; Steps 3-10 not started. Source: [chatgpt-design-review-answer.md](chatgpt-design-review-answer.md) (reviewed at `45a35cc3`, 10-step sequence). This plan turns that sequence into Ringer-sized tasks with gates. Update this file after each step is completed and tested (commit, what the check showed, what is untested), and refresh "Resume here".

## Resume here

Step 2 leftovers: observe a rejected turn and a forced or earned exit live (a blind-player 1A run gave only timer exits). Then start Step 3 (one success, one rejection, one short forced continuation), needs Brandon's go since it is billed. Then open the Step 2 PR. Branch per step, one PR per step, merge commit only on Brandon's per-PR instruction, delete the branch after green CI.

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

### Step 2 live smoke (2026-10-11, staging at 806c5174)
- Ringer run `design-review-step2-smoke`: blind-player scene 1A, 3 replicates, PASS (134 s). `scripts/ringer/design-review-step2/check_smoke.py` passed: 24 of 24 turns carried a bundle with a narration stage.
- Outcomes: 21 committed with cause `none`, 3 committed with cause `timer`; all three replicates exited by `timer`. No rejection, no `forced`, no `earned` exit occurred, so those paths are verified only by the replay tests, not live.
- Not shown: the main report's `exit_cause` also read `timer` for all three, as expected from the bundle. The earlier mislabel (late earned exit as timer) cannot be seen live until an earned exit happens after the handoff turn.
