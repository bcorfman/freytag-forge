# T9c (redirected): inspect is a look verb and the drawer-gap nudge repeats: preregistration (rewritten 2026-10-27, before any build and before any billed call)

Status: written for Brandon's approval of the numbers and gates, then his go on each billed stage (P, S, F below). Nothing below is built. No billed call has been made. This file replaces the first T9c preregistration (the engine opens a closed container; see git history, commit `99334ee7`, and the plan section "T9c preregistered"), which Brandon's redirect made obsolete. It follows the T9b result (`t9b-scope-prereg.md`, plan section "T9b stage F RESULT"): the stage F run failed clause 1 on route A because of one command. It does not change `t9b-scope-prereg.md`, `t9-enforce-stage1-prereg.md` or their data; their numbers are never pooled with these.

**Decisions (Brandon, 2026-10-27):**
1. "I want 'inspect' in the same group as 'examine', 'search', 'check', etc. What it should do is restate the same thing about the gap in the drawer frame."
2. "I want it to repeat the nudge about the drawer gap if the player is interested in the drawer, so it pushes them to try something else."
3. "I want to gate on 'look under' not just 'look'. Obviously the 'under' goes for the other verbs as well: examine, search, etc."
4. "You can rewrite the story data for the drawer nudge." and "I told you that you can write the story in this case, not ChatGPT (for the nudge text)."

## Why

In the T9b full run all 7 unsuccessful turns (6 of 80 on route A, 1 of 20 on route B) were `inspect the drawer`, request kind `open` (Jev answered `opens_container` true on 14 of 15 such turns). Kind `open` adds the conditional line "If the drawer opens, show what is inside it". In each failure the narrator set the drawer `"state":"open"` in `item_facts` while its prose only said Kristin "decides to open it", so the world became open and the four supplies were never shown. Under Brandon's rule `inspect the drawer` is not an opening command, so it must be kind `look` on a closed drawer: nothing inside is required and the conditional line never appears. The story already has the nudge Brandon wants (`k_sl_1a_f_r2`: "The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers."), but its evidence needs the words "initials" or "carving" and it can fire only once.

## The change (fixed now)

**1. Jev wording (code, Ringer).** `opens_container` in `storygame/runtime/jev_questions.py` is reworded so that only opening counts:
- instructions: `Decide whether the command has the player open the container. Only opening it or pulling it open or out counts.`
- true: `The command opens the container, pulls it open, or pulls it out.`
- false: `The command only looks at, inspects, examines, searches, checks, closes, locks, touches, moves, carries, or talks about the container, or goes under, behind, or on top of it.`
Function name, signature, return type and the `noul` type are unchanged. `searches_underneath` is unchanged (T9b probe 2 passed it). The wording follows `docs/jev-guard-rules.md` and was written from Brandon's rule and the T9b failure class only. The lists below were written after it. None of them has been run, and none of their commands appears in an earlier probe's list except the labelled regression set.

**2. A repeatable knowledge entry (code, Ringer; story-agnostic).** `KnowledgeDefinition` gains `repeatable: bool = False`. A repeatable entry, after its effects already hold, is still an eligible reveal: `explain_reveal` (`reveal_eligibility.py`) and `_eligible_reveal_candidates` (`cloudflare.py`) skip the already-established and storylet-spent checks for it. Every other rule still applies (`requires`, audience, `reach_entity_ids`, scene, evidence). The authored `delivery_text` is appended after the narration each time it matches. No names, verbs or story strings enter engine code.

**3. A specific match wins (code, Ringer; story-agnostic).** `uniquely_matched_authored_handoff` returns nothing today when two entries match one command. The new nudge (verb x drawer) and the card find (verb x under-word x drawer) both match `look under the drawer`. When more than one entry matches in full, the entry with the most evidence groups wins; a tie still returns nothing. This ranks only complete matches, never partial ones, and uses no vocabulary.

**4. Story data (I write it; no ChatGPT round).** In `data/stories/continuity-initiative/knowledge.yaml`, `k_sl_1a_f_r2` is rewritten in place (same id and source):
- `statement`: `Kristin looks over the drawer and is pointed toward the thin gap beneath its lower edge.`
- `earn_when`: `examines, inspects, searches or checks the drawer without going underneath it`
- `action_evidence`: `[[examine, inspect, search, check, look, study], [drawer, "drawer's", KMS]]` (the matcher's synonym class already adds feel, investigate, look at and the rest).
- `repeatable: true`; `requires` stays `memory_card_recovered` false, so the nudge ends when the card is found.
- `delivery_text`: `The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers.` It is the scene cue's own sentences without the card, and it is the same text every time, as Brandon asked.
- The card find (`k_sl_1a_b_r0`, `k_sl_1a_b_r0w`) keeps its evidence `[[look, search, inspect, check], [under, beneath, underside, gap, lower edge, bottom edge], [drawer, KMS, workstation, "drawer's"]]`. The synonym classes make examine, feel, study and the rest count as the verb too, and below, underneath and underside count as the under word; a test pins this for each verb.
- Whether `k_sl_1a_f_r2` can stay sourced to SL-1A-F once that storylet completes is not yet verified; the build's first test decides it. If the source rule blocks the repeat, the entry moves to a realization of SL-1A-E (active until the card is found) and the change is recorded here before any billed call.

No engine open step is built. Opening verbs passed in T9b (15 of 15 `pull out the drawer` turns committed first try); the engine-performs-prerequisite-steps idea (decision W12) can return if a later run shows opening verbs failing. Nothing here is deployed; production changes need Brandon's explicit instruction and `FREYTAG_OBSERVATION_ENFORCE` stays unset.

## Stage P: Jev classification probe (billed, tiny)

Asks the product's Jev client, 2 samples per question, on frozen lists, no narration, no engine. Labels fixed here, before any call. Player-input voice: imperative with a direct object (`docs/player-input-guide.md`). Container names in brackets.

**Grid (the "under goes with every verb" gate).** Verbs: Inspect, Examine, Search, Check, Look at. Containers: cabinet, chest, locker, toolbox. Two forms per verb and container: bare (`Inspect the cabinet.`, `Look at the chest.`) and under (`Inspect under the cabinet.`, `Examine beneath the locker.`, `Search underneath the toolbox.`, `Check below the cabinet.`; the verb `Look at` becomes `Look under` in its under form). The generator rotates under, beneath, underneath and below across the cells in a fixed order and records the result in the corpus lock. 5 verbs x 4 containers x 2 forms = 40 commands. Each is asked both `opens_container` and `searches_underneath`.
- Required: `opens_container` false on all 40 commands. `searches_underneath` false on the 20 bare commands and true on the 20 under commands.

**Opening positives (12, `opens_container` must be true, `searches_underneath` not asked):** Open the chest. [chest] / Pull open the locker. [locker] / Slide open the cabinet. [cabinet] / Pull out the bottom drawer. [bottom drawer] / Yank open the crate. [crate] / Lift open the cooler. [cooler] / Open the glove box. [glove box] / Tug open the toolbox. [toolbox] / Pull open the cabinet. [cabinet] / Open up the chest. [chest] / Open the top drawer. [top drawer] / Pull out the file drawer. [file drawer].

**Non-opening negatives (18, `opens_container` must be false):** Close the cabinet. [cabinet] / Shut the chest. [chest] / Push the bottom drawer shut. [bottom drawer] / Slam the locker shut. [locker] / Close the glove box. [glove box] / Lock the locker. [locker] / Touch the crate. [crate] / Knock on the locker. [locker] / Push the cabinet against the wall. [cabinet] / Carry the toolbox. [toolbox] / Lift the suitcase. [suitcase] / Drag the chest to the door. [chest] / Kick the cooler. [cooler] / Tap the cabinet. [cabinet] / Wipe the cabinet. [cabinet] / Paint the chest. [chest] / Read the label on the crate. [crate] / Polish the toolbox. [toolbox].

**Reported, not gated (8 phrases, `opens_container` only):** Look inside the locker. / Feel inside the chest. / Peek into the cooler. / Reach into the toolbox. / Study the chest. / Glance at the crate. / Admire the locker. / Rummage through the cabinet. (Containers as written: locker, chest, cooler, toolbox, chest, crate, locker, cabinet.) Whether "look inside" opens the container is a content call Brandon has not made; it is measured here, not decided.

**Regression set (6, labelled, seen while writing, NOT part of the fresh gates):** `opens_container` must be true: Open the drawer. [drawer] / Pull out the drawer. [drawer]. `opens_container` must be false: Inspect the drawer. [drawer] / Examine the drawer. [drawer] / Search the drawer. [drawer] / Close the drawer. [drawer].

**Counts and cost.** Grid: 40 commands x 2 questions x 2 samples = 160 requests. Opening and non-opening lists: (12 + 18) x 2 = 60. Reported: 8 x 2 = 16. Regression: 6 x 2 = 12. Total **248 requests**, estimate under $0.002, ceiling `--max-calls 248 --max-usd 0.01`. Stop on 429, auth failure or the cap; no rerun, no replacement samples. Output `bench/results/environment-narration/t9c-open/probe/`. Code SHA: the merge commit on main containing this work, staging deployed and recorded for it, no merge during the run.

**Gate P (set now).**
- **J1 (grid, opens_container): zero true answers among the 80 samples** (one-sided 95% bound about 3.7%).
- **J2 (grid, searches_underneath): at least 36 of 40 samples false on the bare commands and at least 36 of 40 true on the under commands;** every miss named by verb.
- **J3 (opening positives): at least 22 of 24 samples true.** **J4 (non-opening negatives): zero true answers among the 36 samples.**
- **R (regression): all 4 true-labelled answers true (the two opening commands, 4 samples) and all 8 false-labelled samples false.**
- A `None` counts as not true; report their number and every score. The reported group is printed and shares the gate with nothing.
`probe gate: PASS` only if J1 to J4 and R all pass. If any fails, no enforced run starts; a further rewording needs another fresh list and preregistration.

## Free build tests (not billed; must pass before any billed stage)

Written first, run by Ringer checks, no model calls:
- The engine delivers the repeatable nudge on three consecutive `inspect`/`examine`/`search` turns on the drawer in a real continuity package, the text is identical each time, and `drawer_gap_pointed_out` stays true. After them `feel under the drawer` still earns the card find (`k_sl_1a_b_r0`), with the card in Kristin's hands.
- A command with the under word, for each of look, examine, inspect, search, check, feel, with each of under, beneath, underneath, below, matches the card find and not the nudge. A command without it matches the nudge and not the card find.
- The specific-match rule: two full matches pick the one with more evidence groups; equal groups pick none; all existing candidate-matcher tests pass unchanged; partial matches never win.
- `repeatable` false (the default) keeps every existing entry's behaviour: one delivery, then never again (existing tests plus one for a spent storylet).
- A second synthetic story with a repeatable entry behaves the same, with no story strings in engine code.
- The nudge never fires after the card is recovered (`requires`), and never when the container is out of reach.

## Stages S and F: enforced runs

**What runs.** As T9b: real engine, product wiring, observation mode on, enforcing verifier on (`live_baseline.py --enforce`), shadow off, local Worker with a hard dollar cap, 70B JSON off, 20 s timeout and no retry on a timeout. New: the reworded question, the repeatable nudge, the specific-match rule.

**Routes.**
- **A `observe_topup`** (9 commands, unchanged): carries the stage-1 clauses and the first `inspect the drawer` of each replicate.
- **B `observe_under_first`** (4 commands, unchanged): guards the card-find path (`feel under the drawer` must stay kind `under` and find the card) and has an `inspect the drawer` as its third command.
- **C `observe_look_then_under`** (new, 5 commands): `inspect the drawer`, `examine the drawer`, `search the drawer`, `check the drawer`, then `look under the drawer`. Four look-group turns in a row on the same closed drawer test the repeat; the fifth tests that "look under" finds the card after the nudge has been delivered four times.

**Counts and cost.** Pooled look-group turns (inspect, examine, search, check on the drawer): route A 10, route B 5, route C 15 x 4 = 60, total **75**; the 15 `look under` turns on route C and the 5 `feel under` turns on route B test the find.
- Stage S (billed once, not counted in any rate): A 1 replicate (`--max-calls 90`), B 1 (`--max-calls 40`), C 2 (`--max-calls 70`); local Worker `--max-usd 0.06`; expected about $0.03. Checks plumbing: rows record the delivered handoff id and the container's open state after each turn; the report builds sheets for the three routes.
- Stage F (billed once): A 10 replicates (`--max-calls 800`), B 5 (`--max-calls 250`), C 15 (`--max-calls 600`); `--max-usd 0.40`; expected about $0.20. No retries, no replacement samples. Stop on any quota code, 429, 5xx or cap and keep the partial result. A turn that fails because enforcement exhausted its recovery is a result, not a stop.
- Output `bench/results/environment-narration/t9c-open/{smoke,full}/{a,b,c}`, harness port 8797, `enforce_stage3.sh`.

**Procedure.** As T9b: free dry run, billed stage, each a Ringer probe task whose check asserts a stop reason or the exact row count; blind sheets; I read every turn and freeze the labels hash before any verdict is opened; then `join`. Added labels, from narration and command text only: `gap_restated` (the committed narration plus delivered text tells the player the drawer rides high with a thin gap beneath its lower edge) and `opened_by_narrator` (the narration or `item_facts` has the drawer open).

**Gate (set now).**
- Route A: all stage-1 clauses 1 to 7 unchanged, in particular **clause 1: at most 1 unsuccessful of about 80 observation turns** (the T9b run had 6), clause 2 zero committed narrations missing a required thing, clause 3 tags (zero leak, wrong custody, unrequested move; at most 1 each of refind and invented object), clause 4 rollback, clause 5 at most 2 attempts and 2 verifier requests, clause 6 p95 of no-recovery turns at most 10 s, clause 7 false rejects at most 1 (inconclusive under 5 rejections). S1 and S2 as in T9b.
- **N1, the aim: of the 75 pooled look-group turns, at least 72 end with a committed narration** (96%; the T9b run was 7 of 15 failed on inspect). Every other turn is listed by id with its reason.
- **N2, the nudge repeats: of the 75 look-group turns, at least 72 end with the gap restated** (the delivered text appears in the committed turn), and on route C the nudge appears on at least 58 of the 60 look-group turns, including the second to fourth turns of each replicate. Every miss is listed with the handoff outcome.
- **N3, the find is not blocked: the card is held after `look under the drawer` in at least 14 of 15 route C replicates, and after the first `feel under the drawer` in at least 4 of 5 route B replicates,** with the find shown in prose and zero turns mention the card before it is found (S3 as in T9b). The nudge must not be delivered on a turn that finds the card.
- **N4, no accidental opening command: the engine never opens a container** (there is no engine step), and Jev `opens_container` true on a look-group command is listed by id; it is expected to be zero and is printed, not gated, because the verifier's behaviour is what the gate N1 measures.
Printed, not gated: share of look-group turns classified kind `look`, `open` and `under`; share where the narrator opened the drawer (`opened_by_narrator`); first-attempt rejection rate and recovery success rate; per-route kind distribution; Jev request count per replicate; handoff outcome counts.

A pass does not deploy anything and does not turn the hosted switch on; it permits writing the T9 confirmation preregistration. A fail on N1, N2 or N3 or on clause 1 is a stop with the rows and labels recorded.

**Expected, not measured.** N1 close to 75 of 75 if inspect stops being kind `open`: the 20 `feel under the drawer` turns in the T9b run (kind `under`) and the 15 `pull out the drawer` turns all committed first try. N2 follows from a deterministic match once the specific-match rule works, and the free tests must show that before any billed call. Risks I can see: Jev may still answer `opens_container` true for some inspect phrasings (the wording was written from the failure class); the narrator may open the drawer itself in `item_facts` on a look turn and then omit the supplies, which would repeat the T9b failure under kind `look` (the supplies would then be required by the verifier, because the container became open); `look` is in the same synonym class as feel, so `feel the drawer` with no under word will now earn the nudge, which I think is intended; the first delivery of the nudge in a turn that the card find also matches depends on the new specific-match rule working in the live path, not only in unit tests.

**Stated limits.** One story, 70B only, one reader who knows the aim, ten route A replicates share one start (routes B and C share it too). The phrase lists are small and hand-made; a pass shows the wording works on them, not on all player language, and says nothing about pronoun commands ("inspect it"). Unlocking, keys and locked containers are out of scope. The nudge text is repeated verbatim by design; players who keep inspecting will see the same two sentences each time, and whether that reads as a hint or as nagging is a story judgement this run does not measure.

## Build (free, Ringer, tests first, after approval)

1. `KnowledgeDefinition.repeatable`, `explain_reveal` and `_eligible_reveal_candidates` honour it; the specific-match rule in `candidate_matcher.py`; tests as listed under "Free build tests".
2. `jev_questions.opens_container` carries the three strings above exactly; update the tests that pin the old text (`tests/test_jev_questions.py`, `tests/test_observation_mode.py`, `tests/test_observation_under_scope.py` if affected).
3. Story data for `k_sl_1a_f_r2` as written above (I edit it after the code lands, in the same branch, so the package never carries an unknown field), and the real-package tests.
4. `opens_container_probe.py` modelled on `under_question_probe.py`: grid generator and lock, frozen cases and SHA-256 lock (`--check-corpus`), `--dry-run`, `--run --confirm`, `--report` with J1 to J4, R and the reported group; a runner manifest from a generator that asserts every number; a test that every command string occurs in this document and none of the fresh-list commands occurs in the T9b probe lists (the regression set is exempt).
5. Route C in `live_baseline.py` and `ROUTES`, handoff id and container open state in the rows; `enforce_stage3.sh smoke|full` (A then B then C under one Worker cap) and runner manifests from a generator that asserts every number.
6. `enforce_report.py`: labels `gap_restated` and `opened_by_narrator`, clauses N1 to N4 chosen by the rows' route, the new information lines; tested with synthetic rows that violate each clause. The earlier script, manifests and report tests keep passing.
