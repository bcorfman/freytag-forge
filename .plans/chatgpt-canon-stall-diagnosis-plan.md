# Hosted canon stall diagnosis

Status: diagnosis complete; F1–F5 implemented 2026-10-31 on branch `canon-stall-harness-fixes` (uncommitted; Ringer run `canon-stall-harness-fixes`, both tasks PASS first try; 169 Node tests pass). Billed verification not performed; it needs Brandon's explicit authorization and a revised cost estimate.
Reviewed 2026-10-31 against HEAD `b0d5d6f5` and the three recorded staging attempts.

## Resume here

Do not buy another unchanged canon run. Remove the false storylet-count stall gate, correct the departed-scene event assertion, and let resolution reach the actual ending. Verify those changes together offline before considering one SHA-bound staging attempt. Keep #737 and #738. No plot, pacing, knowledge, world, narrator, or runtime change is needed to remedy the three aborts.

Only this diagnosis was written. Proposed edits below are reviewable text, not applied changes. No credentials were loaded, hosted service contacted, or billed test run. Free checks: 33 Node tests passed; 41 focused Python tests passed. The free scripted runtime probe reached 1B on turn 9, with a limitation described below.

## Evidence and scope

Read the PRD, contributor boundaries/safety/design guides, player-input, narrator-writing, world-model grounding, scene-fixing, agent-workflow, promotion and testing guides; the world-model checklist and historical W1–W7 decision text at `5ea0119955c62b84699a8dc7878a4af770b55a7e`; current scene declarations, pacing, routes, knowledge and incident data; the saved prompts; and both merged harness diffs. No new world-model or narrator technique is proposed. Existing package deadlines, scripted providers, injected walker responses, fact-based eligibility and the spine ending test supply the remedies.

Paths below are relative to the repository root. `C0`, `C1`, `C2` mean respectively:

- `bench/results/staged-de04ad8e/canon/`
- `bench/results/staged-fa60c481/canon/`
- `bench/results/staged-b0d5d6f5/canon/`

`S` means `bench/results/staged-de04ad8e/spine/`. Artifact line numbers refer to JSON files, not their Markdown wrappers. Each canon `identity.json:1` records the corresponding full SHA, `scene-v1`, and `staging`. These identify the saved runs; they do not establish today's live deployment or model configuration.

The running plan's last top-level Update (`.plans/grounded-llm-environment-narration.md:23`) describes an earlier `21377382` run, not these attempts. Its 6.9-second maximum must not be attributed to S: S's operator note records 9029 ms. The later artifacts are the evidence for this diagnosis.

`scripts/ringer/staged-de04ad8e/staged-regression.json` explicitly allows at most one paid attempt per task, clears stale artifacts, checks SHA and preserves failures. The two build manifests in `scripts/ringer/canon-conditional/` restrict edits to three frontend files and prohibit billed tests. Derived hosted manifests for the later SHAs were not found under `scripts/ringer`, including ignored files; their exact invocation policy cannot be independently reconstructed beyond the saved logs/reports. No delegation was run from those historical manifests.

## What each abort actually establishes

| Run | Actual failure | Cause and classification |
|---|---|---|
| C0 | `canon-run.log:15–26`: turn **5**, missing `officer_presses_1a`; received arrival and entry events. Progress JSON `:2` ends at turn **4**. | Harness flaw: it required a conditional event without checking eligibility. Recovery at turn 2 selected the unwatched card branch; `card_challenged` was not earned. This is not evidence of a broken officer event. |
| C1 | `canon-run.log:15–25`: turn **6**, observed relative turn 6 after **0** turns needed for `officer_presses_1a`. Progress JSON `:2` ends at **5**. | Harness flaw: #737 stopped requiring the event but left the clock selecting its already-reached turn-5 target. A legitimate next accepted turn advances to 6 and trips the overshoot assertion. No server clock jump is demonstrated. |
| C2 | `canon-run.log:15–26`: turn **8**, `committed nothing for 5 turns running`; expected `< 5`, received 5. Progress JSON `:2` ends at **7**. | Harness flaw: it equates unchanged `fired_storylet_ids.length` with no progress. Storylets A/E/B were spent by turn 3; turns 4–8 make five further turns. Arrival, entry and departure facts demonstrably change during that interval. The guard prevents reaching the normal turn-9 exit. |

Do not report these as failures on turns 4, 5 and 7. Those are the last persisted progress checkpoints. In `scene-runtime.spec.js:268–395`, submission and assertions precede writing the checkpoint. The failure-turn response/narration is not in the progress JSON. C0's log does expose turn 5's event list; C1's log exposes turn 6's counter; C2's log exposes the turn-8 counter assertion, not its full payload.

No attempt reached the judge loop (`scene-runtime.spec.js:402` onward). There is no canon verdict, no zero-out-of-63 score, and no protected-safe verdict. All three are unusable as completed canon scores but useful diagnostic records. None of the three exceptions is evidence of an HTTP, quota, provider availability or infrastructure failure.

## Turn-by-turn comparison

The actions are identical across the comparable turns: `@spine` and canon both call `promptFor`, not different scripts. Different model outputs/world captures still make these separate samples, not byte-identical runs.

| 1A turn/action | C0 | C1 | C2 | Passing spine S |
|---|---|---|---|---|
| 1 Search kitchen/back door | A reveal | A reveal | A reveal | A reveal |
| 2 Search beneath drawer | E/unwatched recovery | Same | Same | Same |
| 3 Read remaining fragments | B files/warning/lead | Same | Same | Same |
| 4 Read files | No new reveal; arrival | Same | Same | Same |
| 5 Play recording | Response has arrival+entry; assertion abort | No new reveal; entry | Same | Same |
| 6 Hide findings/watch departing officers at gate | Not run | Response advances to 6; assertion abort | No reveal; empty summarized fact delta | No reveal; `wk_unplaced` for Michelle's phone |
| 7 Cycle kitchen search | Not run | Not run | No reveal; `patrol_departed` | Same pacing fact; no reveal |
| 8 Cycle drawer search | Not run | Not run | Response received, stall assertion abort; unsaved | No reveal; `home_search_window_narrowing` |
| 9 Cycle fragments | Not run | Not run | Not run | No new reveal; `patrol_return_pressure`, entry knowledge; **earned** 1A→1B |

Turn row evidence starts:

- C0 `e2e-llm-canon-progress.json`: 11, 80, 146, 227 (inputs/narration and following bundles); progress rows 302, 384, 471, 559.
- C1 same filename: 11, 80, 146, 222, 278; progress rows 350, 432, 519, 607, 699.
- C2 same filename: 11, 80, 146, 222, 278, 336, 389; progress rows 463, 545, 632, 720, 812, 906, 1000.
- S `e2e-spine.json`: turn objects start at 396, 448, 498, 552, 595, 638, 686, 729, 772. The turn-9 object records `transition_cause: earned` and the two changed predicates.

C2's storylet lists at lines 662, 752, 845, 939 and 1034 remain A/B/E. Its bundles nevertheless record `patrol_on_scene`, `patrol_in_house`, and `patrol_departed`. The assertion text “committed nothing” is demonstrably false. S continued through exactly this reveal-free interval and completed all nine scenes in 75 turns with eight earned exits. Its pass establishes reachability/expected chains, not literary quality: the spine artifact does not preserve narration or full per-turn state.

## Does canon match authored 1A?

**Branch:** yes for early recovery, no for demanding the watched-card consequences. `plot.md:159` explicitly distinguishes taking the card out of sight from taking it while watched. `knowledge.yaml:336–382` establishes only recovery for the early branch; `:383–435` establishes `card_challenged` for the watched branch. `storylet-routes.yaml:652–696` agrees. `pacing.yaml:24–34` requires both `card_challenged` and `patrol_in_house` for the officer demand. By turn 2 the canon player already recovered the card before arrival at 4/entry at 5. Hiding later cannot retroactively earn a witnessed recovery.

**Time:** the fixed five-turn stall rule conflicts with authored play. `pacing.yaml:255–259` sets 1A min/nudge/handoff at 9/10/13. Arrival/entry/departure/search pressure/return are at 4/5/7/8/9 (`:3–72`, `:183–190`). The transition requires the actionable lead, return pressure, recovered card, and memory-card dependency (`:292–305`). The lead/warning/file reveal has already landed by turn 3; the normal route then waits for pressure. `_apply_authored_transition` (`storygame/runtime/engine.py:1218–1244`) enforces the ordinary minimum. Removing the false guard does not require shortening the story or inventing more reveals.

**Prompt order and prose:** the comment claiming one beat per prompt is stale. The turn-3 handoff already delivers both files and the recording warning; turns 4/5 revisit them. The prompt at turn 6 presupposes questions and departure while authored departure is turn 7. It also combines two potential observations. The visible saved prompt says “This turn has no candidates” (C2 turn-6 `prompt.user`, beside input at line 336), so the absence of a reveal is not evidence that a model refused an offered reveal. The same prompt contains officer speech permissions quoting Kristin's private investigative summaries. That matters to the narration defects below.

`plot.md:133` calls for taking the card to the truck and using the laptop. The shared journey never explicitly performs that move. C0/C1 instead invent a computer/USB port in the house; C2 delivers the files without showing playback. A spine pass with the same actions does not validate that physical story sequence. Rewriting the journey would change the measurement and needs its own offline review, rather than being mixed into a stall repair.

## Game defects present in the samples, distinct from abort causes

1. **Unsupported information and equipment:** C0 narration `:147` invents a nearby USB port; `:228` adds a café on the outskirts of town, beyond the bench lead. C1 `:147` invents a computer; `:279` uses the laptop despite the recorded placement remaining the truck passenger seat. Compare `plot.md:88–91,133` and each artifact's `state.things`. These are observed prose/continuity defects, not proof of a particular resolver defect.
2. **Premature departure and misplaced speech:** C2 `:337` narrates officers leaving at turn 6, invents a detective, and has the officer repeat “Kristin traces the forced entry…” as dialogue. The saved turn-6 prompt explicitly permits the officer to say that summary; the source of this text is visible. The action itself also presupposes departure. Distinguishing the contribution of those two inputs needs the scene-fixing workflow, not another broad run or an untested narrator prohibition.
3. **Re-taking an already held phone:** C2 `:390` picks Michelle's phone up from the floor. Its turn-7 prompt says it is held by Kristin. The repeated player action also asserts it was left on the floor. This is a visible contradiction with competing inputs; it does not justify changing canonical custody facts to agree with prose.
4. **Capture gap in the passing control:** S turn 6 (`:638` onward) reports `capture_unplaced: ["Michelle's phone"]`. With no narration/raw capture prompt in S, the resolver cause cannot be established. “Spine passed” must not be rewritten as “world continuity passed.”

These defects deserve a separate recorded-prompt investigation, using existing subtraction/availability techniques from the scene-fixing guide and the active narration plan. **No exact product fix is proposed here:** the evidence does not isolate a winning intervention. Do not add a story-specific runtime branch, accept prose as truth, change placements, or add narrator rules on this evidence alone. Any eventual plot/order/pacing/story-data change requires Brandon's approval before application, starting in `plot.md` when it changes what happens. This report proposes none.

## Review of #737 and #738

**#737 / `14c69af2`: keep.** Correctly preserves `when` validation, adds `isConditional`, retains unconditional-event assertions, and records fired conditional events. But its tests cover projection classification, not the actual sequence of arm → submit → evaluate → record. `check_conditional.sh` checks source strings and the conditional set; it cannot catch the stale target in C1, the stall guard, or the departed-scene bug. Treating conditional absence as unjudgeable at the browser boundary also reduces coverage: a condition that really was true could now be missed. Existing engine tests must retain that responsibility. Do not expose hidden facts to the player to repair a browser assertion.

**#738 / `d062246f`: keep.** `nextPendingEvent` uses strict `>` for conditional targets and `>=` for unconditional targets. Skipping an expired conditional target is only harness steering; `_activate_pacing` still checks `turns_since_entry >= at_turn` and current predicates every turn. Late eligibility is not disabled. Existing `test_guarded_pacing_event_waits_for_its_predicates_even_after_at_turn` covers that engine contract. The new tests and `check_steering.sh` prove helper selection; they do not execute canon's stall/recording/judging logic. The subsequent run verifies progress beyond the overshoot, not full correctness.

Both scopes left the duplicated selector and identical false stall gate in `scene-walk.js:4,16–20,50–51,80–83`. Its controller itself records timing rather than enforcing the spec's overshoot assertion, so do not claim it necessarily raises the same exception; it does arm the obsolete target and still aborts on storylet-count stagnation. Its three tests use an empty event list and short synthetic paths or explicitly demand the bad stall behavior.

`nextPendingEvent` chooses declaration order, not earliest target: at 1A turn 7 it selects return at 9 before search pressure at 8. Current submissions still advance one accepted turn at a time, so this is not a demonstrated skipped runtime event and does not warrant sorting/refactoring as part of this fix.

## Further failures predictable before paying

- **1C early incident completion:** S global turns 18–20 (`e2e-spine.json:1160–1316`) enter/resolve 1C in three turns. `incidents.yaml:1–19` declares `completes_scene: true`; engine lines 1233–1242 permit that completion before the normal minimum. Canon's lines 300–311 require every unconditional event from every scene already left, including `transfer_window_1c` at 5. That is a false failure on a successful copy-numbers route. An unfired event does not follow the player out of a scene; `test_unfired_pacing_event_does_not_cross_a_scene_exit` is existing proof. This is a source/control-derived prediction, not an observed fourth canon attempt.
- **Same count problem elsewhere:** S's last new 3A reveal is relative turn 4 and its exit is turn 9. The five-turn count is not a safe generic rule. In 3C the last new reveal in S is turn 3 but completion is turn 14. 1B/2A/2B also include repeated actions while pacing advances. No inference about the number of reveals alone establishes a stall.
- **Resolution stops too early:** canon's loop breaks once the five 3C prompts have been used (`scene-runtime.spec.js:263`), whereas the spine deliberately cycles to actual `story_complete` (`:21–23,169`). S needs 14 3C turns. Canon merely records `story_complete_seen` and checks that 3C was reached. A nine-scene/30-turn file can therefore be an incomplete story; it is not proof that judging finished either.
- **Other conditionals:** transfer nudge/withdrawal in 1C, scrutiny/cover review in 2A, destruction in 3B carry predicates. Preserve #737/#738 and test both eligible and ineligible branches offline rather than arranging the story so every optional event always fires.

## Exact proposed edits (not applied)

All edits in this section are **test harness or verification documentation changes**. None changes plot, package pacing, story data, narrator prompts or runtime behavior. Removal comes first; no new progress metric, fact interpreter or retry mechanism is introduced. New regression cases are proposed, but their techniques already exist in the repository.

### F1 — Delete the false early-stall heuristic

In `frontend/e2e/scene-runtime.spec.js`, delete these three pieces:

Old:

```js
// A scene has at most three authored reveals, so more consecutive empty turns than
// that means the scene is not progressing rather than merely taking its time.
const MAX_STALLED_TURNS = 5;
```

New:

Delete this text; no replacement.

Old:

```js
  let stalledTurns = 0;
  let lastCommittedCount = 0;
```

New:

Delete this text; no replacement.

Old:

```js
      // A scene that commits nothing several turns running is stalled: the reveals
      // its outgoing bridge needs are never landing. Say so where it happens rather
      // than letting it quietly consume the whole turn budget.
      const committed = (payload.state?.fired_storylet_ids || []).length;
      stalledTurns = committed === lastCommittedCount && reachedSceneId === sourceSceneId ? stalledTurns + 1 : 0;
      lastCommittedCount = committed;
      expect(
        stalledTurns,
        `Scene ${sourceSceneId} committed nothing for ${stalledTurns} turns running; its outgoing reveals are not landing.`,
      ).toBeLessThan(MAX_STALLED_TURNS);
```

New:

Delete this text; no replacement.

In `frontend/e2e/scene-walk.js`, delete each of:

Old:

```js
const MAX_STALLED_TURNS = 5;
```

New:

Delete this text; no replacement.

Old:

```js
  let stalled = 0;
  let committed = 0;
```

New:

Delete this text; no replacement.

Old:

```js
    const committedNow = (payload.state?.fired_storylet_ids || []).length;
    stalled = committedNow === committed && next === source ? stalled + 1 : 0;
    committed = committedNow;
    if (stalled >= MAX_STALLED_TURNS) throw new Error(`Scene ${source} stalled for ${stalled} turns.`);
```

New:

Delete this text; no replacement.

Retain canon's package handoff limit/global budget and walker's handoff/maxTurns failures. These are existing bounds. Do not merely change five to six, count cosmetic world changes, or reset on every accepted response: those would substitute another weak proxy for progress.

Cheapest free check: feed the recorded C2 checkpoints plus the recorded S turns 8/9 through the harness behavior, then assert that turn 9 can be reached and an over-budget path still fails. Do not invent C2's missing eighth response: label any fixture continuation as S-derived. Existing walker injection is the test pattern. Change its test `reports a stall rather than spending the turn budget` to exercise the bounded terminal failure and add a paced reveal-free interval that reaches the next scene. Assert output/transition behavior, not a new magic count.

What could break: genuinely stuck runs may consume more turns before reporting the failure. The existing package/global ceilings bound the extra spend. This is intentional and must be included in any later cost estimate.

### F2 — Use the already-fixed selector in the other walker

In `frontend/e2e/scene-walk.js`, add after the existing import (old text is the single existing import; replacement contains both):

Old:

```js
import { promptFor, scenePrompts } from "./canon-journey.js";
```

New:

```js
import { promptFor, scenePrompts } from "./canon-journey.js";
import { nextPendingEvent } from "./package-clock.js";
```

Old:

```js
  const event = (pacing.eventOrder || [])
    .map((id) => pacing.eventPoint(id))
    .find((candidate) => candidate.scene_id === sceneId && !fired.has(candidate.event_id) && candidate.target_turn >= turns);
```

New:

```js
  const event = nextPendingEvent(pacing, sceneId, turns, fired);
```

Cheapest free check: existing Node clock/walker tests, plus a walker fixture with a conditional event that remains unfired at and after its due turn, another that fires late, and an unconditional event due now. Observe the actual armed target, not just a source-text grep. Fixtures with events must implement the projection's existing `isConditional`; the current empty-event fixture never exercises it.

What could break: incomplete fake pacing objects in tests/callers may lack `isConditional`. Use the real projection or complete the fake contract; do not add production duck-typing fallbacks. This is reuse of #738, not a new clock algorithm.

### F3 — Require only events whose source scene actually reached their due turn

In canon's event loop, replace the following comment and due-test. Keep the conditional skip, assertion, and fired-set addition immediately after it.

Old:

```js
      // A pacing event is bound to its own scene, so it is due only once the
      // story is in that scene at or past its instant - or has left the scene
      // behind, in which case a beat that never landed is a real defect.
      for (const eventId of pacing.eventOrder) {
        const event = pacing.eventPoint(eventId);
        const eventScene = sceneOrder.indexOf(event.scene_id);
        const inScenePastDue = eventScene === to && observedTurns >= event.target_turn;
        if (!inScenePastDue && eventScene >= to) continue;
```

New:

```js
      // Require an event only when play reached its due turn in its own scene.
      // A successful early exit does not make later events overdue.
      for (const eventId of pacing.eventOrder) {
        const event = pacing.eventPoint(eventId);
        const inScenePastDue = event.scene_id === reachedSceneId && observedTurns >= event.target_turn;
        const departedPastDue = event.scene_id === sourceSceneId && reachedSceneId !== sourceSceneId
          && turnsSinceSceneEntry + 1 >= event.target_turn;
        if (!inScenePastDue && !departedPastDue) continue;
```

The `+ 1` uses the existing one-accepted-turn contract already asserted by `turn_index`; it is not a time skip. Validate this at the transition boundary rather than relying on the comment. Earlier due events were checked on the responses that made them due; a future event in a departed scene is never required retroactively.

Cheapest free check: a synthetic successful scene exit at relative turn 3 with an unconditional event at 5 must pass; staying until 5 without the event must fail; departing exactly at 5 without it must fail; a fired event at departure must pass; absent conditional events remain permitted. Replay the S 1C three-turn incident route through the same production assertion logic. Do not merely duplicate the expression in a test: use the repository's pure-helper/injected-response pattern to make the actual assertion policy callable, if necessary. That small testability extraction is new code to review, not a new runtime technique.

What could break: incorrect assumptions about relative counters on transition or game-break resolution. Include a transition response whose destination counter resets to zero and a resumed warning path. No old-scene event should be tested against the destination counter. This does not authorize relaxing checks for due unconditional events.

### F4 — Finish 3C before paying to judge it

In canon's loop, replace:

Old:

```js
    if (sceneId === sceneOrder.at(-1) && (promptsUsed.get(sceneId) || 0) >= scenePrompts[sceneId].length) break;
```

New:

```js
    if (storyCompleteSeen) break;
```

Old:

```js
  expect(sceneId, "the playthrough must end in the authored resolution scene").toBe(sceneOrder.at(-1));
```

New:

```js
  expect(sceneId, "the playthrough must end in the authored resolution scene").toBe(sceneOrder.at(-1));
  expect(storyCompleteSeen, "the story must actually complete; reaching 3C is not the ending").toBe(true);
```

Retain `canonTurnBudget(pacing)` and prompt cycling. This reuses spine's actual-completion contract. Do not call the nine judges if the journey exhausted its budget without completion.

Cheapest free check: replay S's 3C timeline as injected responses; no stop at prompt 5; stop at the completion signal on turn 14. A synthetic no-completion path must reach the existing cap and fail without judge calls. Also cover an earlier valid ending. Current canon budget is package-derived, so avoid pinning a magic total.

What could break: longer, more expensive but complete canon samples; comparisons against old five-turn resolution samples are not like-for-like. A true late-ending defect now fails explicitly instead of receiving a misleading full-story score.

### F5 — Replace the runbook's unsupported automatic-retry advice

In `docs/testing-runbook/hosted-probes.md`, replace items 3 and 4 under “Deciding whether a run counts”:

Old:

```markdown
3. A run counts only if `e2e-llm-canon-progress.json` holds nine scenes and 30
   or more turns. The loop bound is derived from the package pacing. Anything
   less is aborted: discard it and retry, never record it.
4. About one run in three dies on infrastructure, most often
   `Scene 2A exceeded its handoff turn 4`. Retry; it is not a configuration
   difference.
```

New:

```markdown
3. Nine scenes and at least 30 turns are necessary for a comparable canon
   sample, but also require `story_complete_seen: true` and a fresh final
   `e2e-llm-canon.json` containing all nine scene judgments. Keep incomplete
   runs as diagnostic evidence; do not include them in canon scores.
4. Preserve the exact failure and the last saved turn before any retry.
   A harness assertion is not automatically an infrastructure failure.
   Diagnose it against the deployed package and free replay checks. Run
   another billed attempt only within an explicitly authorized attempt limit.
```

Cheapest free check: review the three aborted records and a synthetic nine-scene progress record with no final judgments; neither qualifies as a complete score. Cross-check the runbook against the actual loop/ending assertion and the Ringer at-most-once instruction. No live call is needed. Retain failed logs before clearing shared scratch artifacts for a newly authorized run.

What could break: historical reports may have called partial resolution playthroughs complete. Preserve those historical records and label comparison limits; do not rewrite them into new successes/failures. The one-in-three infrastructure rate and old “handoff turn 4” example are not supported by these artifacts (current 2A handoff is 11).

## Free verification performed and remaining tests

Commands actually run from repository root, using the existing local-checks recipes at focused scope:

```bash
node --test frontend/e2e/package-clock.test.js frontend/e2e/package-clock-controller.test.js frontend/e2e/canon-journey.test.js frontend/e2e/scene-walk.test.js
TMPDIR=/tmp uv run pytest -q --no-cov tests/test_1a_officer_press.py tests/test_1a_patrol.py tests/test_pacing_handoff.py tests/test_scene_relative_pacing.py
```

Results: 33 Node tests passed; 41 Python tests passed in 7.83 s. Counts describe this run, not a permanent gate. These passes confirm the existing tests' coverage gap, not that the proposed changes work. No files implementing those changes or tests were written. No full suite/build/browser test was warranted for this diagnosis-only change.

Additional free investigation used `uv run python` to read JSON and compare each turn, then imported the existing `_ScriptedProvider`, `RuntimeEngine`, `RuntimeState`, package loader and `scene_prompts` from `scripts/generate_spine_expected_reveals.py`. It bootstrapped the real package and called `engine.turn` with the existing cyclic 1A prompts for nine turns. That provider overrides transport and makes no inference request. It reached 1B at turn 9 with departure/search/return pacing intact. **Important limitation:** this exact-only provider did not earn B on turn 3; it earned it on turn 4. It therefore does not reproduce C2's precise fifth-empty-turn failure. Use the recorded C2 turn-3 commit sequence for that regression, not this substitute trace. At the end of turn 5 both C knowledge entries were eligible in this free state; eligibility alone does not prove a unique match or candidate visibility in the hosted state.

Tests to add/change, before another billed run:

1. Exercise canon's actual policy across a complete sequence: early card recovery, officer condition false, pacing-only turns, transition. Verify assertions and persistence, not just `isConditional` and `nextPendingEvent` separately.
2. Add the successful early 1C incident and due-at-departure cases in F3. Keep Python late-conditional and no-cross-scene-event tests unchanged.
3. Replace the walker test that enshrines the five-turn stall and add F1/F2 regressions. Existing `canon-journey.test.js` only pins strings and cycling; it cannot establish authored timing or reveal success.
4. Add F4 full-ending/absent-ending cases with a stub judge, ensuring nine judge calls happen only after a completed journey.
5. Preserve tests for missing unconditional events, wrong scene order, skipped scenes, malformed counters, overshoots and exhausted budgets. Include a small synthetic second package so no fix silently hardcodes 1A/1C.

No setup secrets, network, deployment, cleanup or test artifact deletion is needed for these local checks. The existing runbook was read, not edited, because the request restricts changes to the diagnosis. F5 supplies its exact proposed in-place correction; this section records today's outcomes rather than appending a results log to the operating runbook.

## Limits and decision on another billed run

Unverified: raw responses for the three failing turns, archived browser traces, full fact stores, exact hosted inference flags/model, later derived hosted manifests, per-turn spine narration, and any canon verdict. The data does not prove that #735's worldkeeper refactor is faultless; it does show that the cited aborts need no runtime regression to explain them. The saved public bundle contains predicate names, not complete fact values. Prompt/capture root causes and the outcome of a revised journey remain open.

Do not infer that fixing the stall alone will produce a complete run: the 1C event assertion and premature 3C stop remain. Do not classify every later failure as infrastructure or retry until lucky. The missing eighth C2 payload is also a diagnostic limitation; a future improvement could reuse spine's failure-recording path, but this report does not prescribe an additional implementation without an exact design.

**One more billed canon attempt is justified only after** F1–F4 and their integrated free regressions pass, the chosen implementation is merged and its exact SHA passes CI/staging identity checks, and Brandon explicitly authorizes the bounded attempt with a revised cost estimate. Keep the original prompts for that harness-validation sample so results remain interpretable. Review the estimate for the longer resolution traversal plus nine judge calls; the old 30-turn cost is not a budget for the observed 75-turn spine. Use at most one attempt, preserve all fresh artifacts/logs including failures, and stop for diagnosis on any new abort. Judge failures are evidence to analyze, not permission to retry. Production promotion and changes to hosted flags remain outside this task.

## Staged attempt on c539fb5f (2026-11-01)

One authorized attempt, artifacts in `bench/results/staged-c539fb5f/canon/`. Staging identity verified (`c539fb5f`, staging, scene-v1). The F1–F4 changes cleared all three earlier aborts: 45 turns played, scenes 1A–3A reached, no stall, overshoot or departed-event failure. It then aborted at turn 46 (3A, scene turn 2) on `expect(payload.state?.turn_index).toBe(turnIndex + 1)` (`scene-runtime.spec.js:283`, received 45). Cause: the scripted 3A prompt "Meet the imprisoned official and request the emergency gate authorization." drew the engine's by-design clarification "Do you mean the emergency surface gates or the facility gate?" (`payload.clarification` is set; no turn was consumed). Harness flaw, not a game fault; no judge ran, so no score and `story_complete_seen` is false. Proposed fix (not applied): treat a `payload.clarification` response as a non-turn in the canon loop (skip the turn_index assertion and do not consume the prompt or advance the counters), and answer it with the original command carrying `clarifies`/`clarification_round` from the payload, as the ambiguous-reference rule requires. A further billed attempt needs fresh authorization.
