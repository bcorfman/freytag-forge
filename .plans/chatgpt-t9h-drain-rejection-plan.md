# T9h drain rejection: artifact diagnosis and next checks

2026-10-30. Read-only investigation; no billed calls, tests, implementation, story edits, preregistration edits, or historical-artifact edits. This file is the sole deliverable. Working HEAD was `74b0e58d3eaf2a52a6f38785c04fa1a39ed6443d`, with substantial pre-existing uncommitted implementation and story changes. Current source is not proof of the source used by every historical run.

**Recommendation: wait, then change the full enforced stage before running it.** The new Route E runs reproduce the location-evidence problem under **V0**, not a failure of J1c. But they also expose unauthorized drain-opening prose, which the location verifier does not test. The prior J1c smoke already accepted an invented “slightly ajar” condition. Correct the measurement and labels first; retain J1c's already-screened material-only change, unchanged questions and thresholds. Do not promote the flag or spend the $0.20 full-stage budget on the claim that location acceptance proves drain safety.

## What the rows actually show

Paths below are relative to `bench/results/environment-narration/`. `rNt5` means `rows[N].turns[5]`, the sixth command, **not** the stored runtime `turn_index` (often 14 after a rollback). Every row here has `input = "inspect the storm drain"` and observation request `{"kind":"look","focus":"storm drain"}`.

All five new runs have `scene_state: false` in both replicate records and summaries, enforcement on, shadow off. Every actual verifier attempt has one drain relation at `Los Angeles park`, holder null. The ordinary narrator user prompts are identical across all 23 drain turns, including retries (system prompts differ only by the retry instruction). The prompt supplies:

```
THINGS:
- Kristin. Place: Los Angeles park.
- storm drain. Place: Los Angeles park.
- Transit token. Held by: Kristin. State: intact. It can be: destroyed.

CONSTRAINTS:
- Show these in your reply: storm drain.
```

It gives no drain state, contents, lid, opening operation, or drain-specific descriptive material. The SCENE still talks about the bench, damaged grounds, service path, checkpoints and patrols. The photograph ownership/storage constraints are present too, but neither a new prompt difference nor an established cause of drain rejection. Do not delete those or the pressure lines on speculation.

In the table, `U` is an uncertain relation verdict, which fails closed; `A` is accept. All rejections are the typed `ProposalValidationError: The narration did not show the observed things as the world has them.` Every rejected turn records equal state digests and `state_unchanged: true`. All previews have `moved_unrelated: []`; no drain rejection here is the earlier bench pickup guard, quota stop, missing observation focus, or unavailable verifier. Scores are valid, with outcome `ok`.

| Run / replicate | Verdict scores, in attempt order | Outcome | Wall seconds | Artifact row begins at line |
| --- | --- | --- | ---: | ---: |
| hidden/smoke r0 | U .57, U .56 | rejected | 9.957 | 7971 |
| hidden/smoke r1 | U .64, U .60 | rejected | 11.414 | 17494 |
| hidden/smoke r2 | U .61, U .55 | rejected | 19.860 | 27001 |
| latency/hedge-short r0 | A .71 | committed | 6.647 | 8023 |
| latency/hedge-short r1 | U .40, U .45 | rejected | 14.710 | 17496 |
| latency/hedge-short r2 | U .52, U .57 | rejected | 12.956 | 26881 |
| latency/hedge-short r3 | U .56, U .45 | rejected | 14.918 | 36426 |
| latency/hedge-short r4 | U .52, U .39 | rejected | 14.915 | 45933 |
| latency/all-on r0 | U .42, U .46 | rejected | 16.263 | 7945 |
| latency/all-on r1 | U .51, U .54 | rejected | 15.780 | 17339 |
| latency/all-on r2 | U .46, U .59 | rejected | 27.555 | 26742 |
| latency/all-on r3 | U .44, U .47 | rejected | 10.567 | 36182 |
| latency/all-on r4 | A .70 | committed | 10.156 | 45593 |
| latency/on-2 r0 | U .63, U .43 | rejected | 16.108 | 7977 |
| latency/on-2 r1 | U .39, U .55 | rejected | 13.991 | 17424 |
| latency/on-2 r2 | U .50, U .41 | rejected | 18.943 | 26883 |
| latency/on-2 r3 | U .49, A .72 | committed after retry | 15.889 | 36350 |
| latency/on-2 r4 | U .42, U .59 | rejected | 14.319 | 45845 |
| latency/off-2 r0 | U .43, U .44 | rejected | 10.813 | 8023 |
| latency/off-2 r1 | A .71 | committed | 14.941 | 17533 |
| latency/off-2 r2 | U .43, U .51 | rejected | 24.645 | 26982 |
| latency/off-2 r3 | A .71 | committed | 8.203 | 36486 |
| latency/off-2 r4 | U .55, U .41 | rejected | 31.904 | 45935 |

For the first three rows use `t9h-hidden/smoke/rows/rows.json`; for the others use `t9h-latency/<arm>/rows/rows.json`. These line references identify the containing turn, not just a summary. More precise evidence anchors: hidden r0 provider bodies 8179, verifier attempts 8215, timings 8265, digest result 9272 and previews 9393; hedge-short r4 bodies 46157 and attempts 46193; all-on r1 bodies 17563 and attempts 17597; on-2 r2 bodies 27115, attempts 27155 and timings 27205; off-2 r4 attempts 46195 and timings 46245.

Totals: **18/23 rejected**, 5 committed; 42 logical narration attempts reached verification, 37 uncertain and 5 accepted. Of the paired runs, **ON rejected 4/5, OFF rejected 3/5: 7/10**, not “all 8 drain turns in both arms.” Four accepts were first attempts; one was a retry. All five accepted narrations explicitly use “park” in their descriptive context, unlike many uncertain replies. That is consistent with the location-evidence explanation, not proof of a keyword rule. Never encode such a rule.

Configuration differences matter: hidden/smoke was the unhedged baseline; hedge-short enabled short-call hedges; all-on added batching/prefetch but its narration hedge was inert and proxy serialization prevented useful overlap; on-2/off-2 are the repaired same-day latency comparison. Those ON/OFF names concern latency features. **Neither arm enables J1c.** The latency preregistration says this explicitly. Summaries record 3/3 or 5/5 replicates, no stop reason, and 113, 189, 141, 157, 184 total calls respectively. Worker logs identify the 70B narrator and `jev-1.13.0`; they do not record the full verifier input state. The runner records relation requests and scores, not full `/jev` payloads. State shape is supported by recorded flags plus the source wiring, rather than a nonexistent raw-state capture.

## Causes and their boundaries

### 1. Real verifier-context defect: implicit scene continuity is absent from V0

`observation_verifier.py:140–145` sends only `{"narration": narration}` when the flag is off. The unchanged question at 148–168 asks whether the named thing is present **at its permitted relation**; `_location_text` makes that `storm drain (at place Los Angeles park)`. The model gets the required place in the question, but no evidence establishing scene continuity. The narrator got that evidence in THINGS and PLAYER and naturally does not repeat the proper place name.

Example: hidden r0 first attempt shows Kristin approaching and inspecting the drain, with no move out of the park, but scores .57. Its reply also contains `"storm drain":{"place":"Los Angeles park"}` in item_facts. That structured proposal is not narration evidence and must not be fed back as authoritative proof of its own correctness. The appropriate evidence is validated world context.

Trace: `item_facts.py:647–662` passes the scene `location_id`; `observation.py:213–226` compares parent IDs and excludes held things from scene-level status; `capture.py:482–487` builds candidate relations and passes `context.scene`; `web_demo.py:268–272` wires the environment flag. The bench creates its own verifier at `live_baseline.py:700`, so changing only the hosted environment cannot change a bench run. `plot.md:168,178` places the drain directly in the current scene location. This is not a name-resolution or placement defect.

Earlier evidence accounts for this:

- Drain probe: all 180 planned rows exist, including d-real-1 at lines 188/203/218 onward. J0 accepted 10/30 positives and left the two real cases uncertain; J1 and J2 each accepted 30/30, with 0/30 negative accepts. J2's extra wording gained nothing. The JSON ends with `stop_reason: "max_calls"` at the exact 180-call budget; do not describe that flag as a missing-sample failure or silently call it null.
- J1 screen: 1,296 rows. Generalized J1m is **not safe to substitute**: a-022, `j1-screen-rows.json:1252`, accepted a copper-locket look-alike at .66; sample 1 was uncertain .63. d-009 reached .65, still uncertain because acceptance is strictly above .65. Held-out gains do not erase C1's failure.
- J1c scope: 620 rows; the scene-level branch uses J1m, other relations retain V0. F1 0/180 negative accepts, F2 55/60 positive accepts, F3 60/60. The five misses were one tin-kettle case (rows near 2698/2730); it is not evidence of universal reliability. Corpus V0 results were carried, not rerun as J1c.
- Wiring: 420 rows test product labels and mixed batches. A2 60/60, B2 90/90, negative gates zero; kettle rows near 1528/1558 now pass. This qualifies the tested payload shapes, not arbitrary narration behavior.
- Earlier enforced smoke: `t9h-drain/smoke/off/rows/rows.json` turns begin 977, 3266, 5559; OFF rejected all three with .44/.49, .35/.53, .49/.44. ON turns begin 977, 3264, 5550; all first-attempt accepts .94/.93/.94, with `scene_state:true`. OFF reports false. This is direct plumbing evidence, with only three samples and a different, pre-hidden-clue package/prefix.

Thus the new V0 rows are not unexplained regression evidence against J1c. What remains unexplained by the old positive/negative location calibration is **drain condition/action safety**.

### 2. Real narration defect and an untested safety boundary

Hedge-short r4 retry says “She pushes the storm drain open slowly”; all-on r1 retry says “She then proceeds to push the storm drain open.” These go beyond `inspect the storm drain`. Several other attempts invent “slightly ajar, as if someone or something had recently passed through it.” On-2 r4 retry asserts an interior containing stagnant water and debris. Distinguish actual opening, invented initial condition, asserted contents, and tentative speculation; do not label all four as missing-location failures or all inspection prose as safe.

These rejected attempts were blocked by **location uncertainty**, not by a demonstrated opening/content guard. `engine_opened:false` and `focus_open_state_after:null` only show that the engine did not open a tracked container. They cannot certify the prose. World declaration `world.yaml:215–219` is a fixed thing with aliases including drain/tunnel, no open/closed axis, no declared contents and no completeness promise. Fixed prevents relocation; it does not mean sealed, closed, empty, or impossible to enter. The observation relation contains name, place, holder and scene-level status, not conditions or player intent. `capture.py:408–561` combines relation acceptance with the unrelated-parent-move check, not a proof that the focused thing's condition was authorized.

Most decisive: old J1c ON smoke r0, `on/rows/rows.json:1035`, already narrates “slightly ajar”; raw capture at 1147 and 1175 carries that condition, yet the verifier accepts .94 and the turn commits. Its structural world view has the same parent/relation/hidden/empty axes before and after. That view does not include every free-form condition. “D4 holds” is true; “D3 safety is established” is not. This is not a false location accept: the drain is present at the right location. It is a separate story/action fidelity concern.

The prompt gives only the drain's name and place, while the model supplies a familiar thriller escape-opening story. Sparse source material is a plausible contributing cause, **not an isolated experimental result**. The repetition across samples does not identify a specific prompt sentence as causal. The world-model checklist explicitly leaves undeclared conditions unscored. Adding an open/closed axis would introduce an affordance and could conflict with the desired control; do not do it merely to obtain a boolean for this bench.

The plot later requires a storm-drain escape (`plot.md:241–243`, `knowledge.yaml:923–927`). Therefore do not seal it permanently, convert it to a closed container, remove its tunnel alias, or invent a gate/grate entity as a quick fix. Future plot changes require **Brandon's approval**.

### 3. Measurement flaws: counts, scope, stale records and asynchronous attribution

- Active plan's paired-run sentence at `.plans/grounded-llm-environment-narration.md:1295` says “all 8”; the table above shows seven rejected of ten. The rejected paired turns span **10.813–31.904 seconds**, not uniformly 14–32. Historical text is left unchanged here.
- `hidden_clues_smoke_report.py:394–403` hardcodes three replicates; complete five-replicate latency runs are printed incomplete. Use their summaries and actual rows. The original three-replicate gate remains historical.
- S5 and S6 explicitly skip the drain. “ordinary rejected turns: none” means none in the assessed non-drain subset. `_drain_lines:377–390` prints all drain outcomes under “drain rejections,” even commits, and its label mentions S1–S5 while `_request_lines` excludes the drain from S6 too. S1–S6 PASS is not full-route acceptance or drain-budget certification. The stage-3 preregistration deliberately separates drain rejections; that exclusion is a scope limit, not proof of success.
- `live_baseline.py:527–528` counts narrator **HTTP prompts** as `narration_attempts`. In on-2 the drain counters are 3,3,4,4,3, while every drain has exactly two verifier/preview attempts. A delayed duplicate is part of one logical inference under the contributor contract. Do not claim a product two-attempt violation from this field.
- More seriously, `CallCounter.finish_timing` appends at completion to mutable current lists; `inspect` does the same for response bodies. `_replicate:794–796` clears those lists at the next command. `hedged_request.py` returns the first success while the losing daemon request continues. On-2 r2t5's first recorded narrator body is **“Kristin bends down to look under the park bench”**, not a drain reply (`rows.json:27115` onward). R3t5 has another bench body at 36588 onward. These belong to preceding commands, not extra drain recovery attempts. R2t5 records five narrator completions but four dispatched narrator prompts. Its 31.222 summed narrator seconds exceed the 18.943 wall seconds. That is overlap plus cross-turn attribution, not 31 seconds of serial drain generation.
- Rejected `engine_steps.capture.reply` can also be stale: hidden r0t5 contains the prior `look under the park bench` narration prompt/raw capture beside the current drain request. Use per-attempt previews, enforce attempts, current outbound prompts and provider bodies, not that previous successful `last_after`, to diagnose a rejected attempt. `observation_enforce:null` on a rejection does not mean no verifier ran.

The async recorder flaw does not show that a losing reply was committed. Actual verification narrations are drain replies, the final result is typed, and rollback digests agree. It limits call attribution, per-kind time shares, winner reconstruction and budget reporting. Headers and bodies are interleaved strings without request identity; do not zip them to prompt order. Worker logs are completion logs with duration/model but no matching logical turn IDs. They support run totals and observed service durations, not a complete per-turn causal reconstruction.

## Cost of rejecting an inspection

Every terminal rejection here consumes **two logical narration attempts and two observation-verifier requests**, plus setup/selection calls. With batching off and no relevant hedge, a rejected drain costs **9 model HTTP calls**: 1 referent match, 2 action classifiers (`relocates_thing`, `boards_vehicle`), 2 candidate-selection Jev calls, 2 narrations, 2 relation verifications. First-attempt acceptance costs 6: the unnecessary retry adds **3 calls** (selection, narration, verification). Batched classifiers reduce the corresponding baseline to 8 versus 5; speculative calls/hedges may add more.

| Run | Rejected drains | Mean wall seconds | Recorded call entries per rejected drain |
| --- | ---: | ---: | --- |
| hidden/smoke | 3 | 13.744 | 9 each |
| hedge-short | 4 | 14.375 | 9 each |
| all-on | 4 | 17.541 | 9, 8, 10, 8 |
| on-2 | 4 | 15.840 | 8, 8, 11, 8; completion buckets, not attributable dispatch totals |
| off-2 | 3 | 22.454 | 9 each |

Across these 18 rejections: mean **16.646 s**, range **9.957–31.904 s**. Descriptive only: different runs, load, batching and hedge implementations are not exchangeable replicates. In the clean hidden baseline, the two narration calls consume 7.648, 8.417 and 11.251 seconds per rejected turn; both verifications together only .357, .403 and .372 seconds. Off-2 r4 spends **29.465 s generating two narrations**, versus .420 s verifying them. A cheap uncertain judgment triggers an expensive regeneration that often repeats the same omission and can add an invented opening. Hedging that regeneration does not fix its cause.

Whole-run spend from spent files/log finals: hidden $0.022153; hedge-short $0.036512; all-on $0.036776; on-2 $0.049837; off-2 $0.035096. Earlier drain-only smoke spent $0.011934 across both arms, including openings. **Exact dollars per rejected turn are not recorded**; do not divide total run spend and present it as measured drain pricing. No new pricing lookup or paid request is needed for this diagnosis.

## Proposed work, ordered by evidence and dependency

All checks below are proposals, not spending authorization. Preserve frozen artifacts; write future outputs to fresh directories. Use the existing Ringer probe procedure when later authorized. No threshold change, per-drain exception, reply-text parser, new narration rule, increased request budget, or blanket held/scene mention-only policy is proposed.

### P1. Repair reporting before interpreting another stage (free first)

Use the existing typed counters, per-attempt records and `HedgedResult` rather than guessing from prose. The telemetry implementation below is new and unmeasured, but uses established request instrumentation and typed primary/hedge outcomes; it changes no acceptance logic.

Exact contract replacements:

- Old `narration_attempts`: `sum(prompt["system"].startswith("You are the narrator") for prompt in counter.prompts)`.
  New definition: **“Count logical narration requests owned by this turn; record primary and hedge HTTP dispatches separately under the same logical request ID.”** Retain legacy raw counts under an explicitly named HTTP field for compatibility.
- Old completion behavior: append response/timing to whatever `counter.responses`/`counter.timings` list is current.
  New definition: **“Bind each dispatched request to an immutable run, replicate, turn and logical-request identity. Record completion, status, winner and primary/hedge role against that identity, including completions after the turn ends.”** Snapshot turn rows without reassigning late work to another turn. Capture `/jev` input state and questions at dispatch, using the same bounded evidence handling as existing prompt capture. Do not wait for losing requests in the gameplay path merely to simplify measurement.
- Old rejected capture display: previous successful capture reply alongside current request.
  New definition: **“A capture reply belongs only to its recorded attempt. If the current attempt has no capture result, record null and retain the prior result only as explicitly identified prior-turn evidence.”**
- Old report label: `drain rejections (turn 5; excluded from S1-S5):`.
  New: `drain outcomes (turn 5; excluded from S1-S6):` for the historical hidden-clue report scope. A future drain-inclusive stage gets its own scope, not a retroactive gate rewrite.
- Old completeness check: requested == completed == len(rows) == 3.
  New contract: **“Compare requested, completed and actual replicate counts against the run's declared expected count; verify every expected command. Missing expected-count evidence is insufficient evidence.”** Preserve expected=3 for the original stage.
- Old active-plan claim: `all 8 drain turns in both arms were rejected, 14 to 32 s each`.
  Proposed correction in a future plan update: **“Seven of ten paired drain turns rejected: ON 4/5 and OFF 3/5. Rejections took 10.813–31.904 s. J1c was off in both arms.”** No historical file is edited by this task.

Cheapest free check: old/current versus corrected recorder/report, six deterministic scenarios per arm (12 fixtures, $0): first-attempt success; two-attempt reject; hedge wins then loser completes in next turn; primary wins with late hedge; late completion crosses replicate boundary; incomplete/capped run. Include 3- and 5-replicate reports and a stale `last_after`. Assert matching run spend/dispatch totals, correct logical counts, owner IDs and equal rollback digests. Re-read all 23 recorded drain outcomes for the arithmetic independently of the reporter.

Cheapest billed check: **none needed to prove this repair**. If transport integration needs confirmation, one corrected-recorder arm, 3 one-command drain replicates, at most 40 HTTP calls, estimated $0.006–$0.012, cap $0.02; count openings and late completions. This can be folded into P2's smoke rather than bought twice. A synthetic delayed fake is the reliable proof of ownership; three live calls need not fire a hedge.

Tests: `test_live_baseline_evidence.py`, `test_live_baseline_scene_state.py`, `test_hidden_clues_smoke_report.py`, `test_hedged_request.py`, `test_narration_hedge.py`, and `test_enforce_drain_report.py`. For telemetry, assert event identity and winners, not prose keyword guesses. Update the existing testing-runbook entry only in that later implementation change.

### P2. Use the already-proved scene material, not another judge rule

Old bench argument: no `--scene-state`; new candidate arm: `--scene-state` alongside `--enforce`. OFF remains the same invocation without that argument. This exercises existing code, not a proposed new verifier algorithm. Hosted flag remains unchanged pending qualification.

Exact state change for the unchanged drain relation:

```json
{"narration":"<the attempt's composed narration>"}
```

becomes:

```json
{"narration":"<the attempt's composed narration>","scene":"Los Angeles park","starting_places":{"storm drain":"Los Angeles park"}}
```

The `_question_for` instructions and criteria remain byte-identical. Specific-place and held relations retain their current behavior. Keep accept strictly above .65 and reject strictly below .35. This ranks **validated material above rules**, and avoids reintroducing failed unrestricted J1m or needless J2 wording.

Cheapest free check: OFF/ON product payloads for six fixtures each (12, $0): the real drain; another story's scene-level object; specific place; held object; mixed batch; explicit moved-away negative. Confirm candidate relations and state shapes, unchanged questions, and exact flags; include current package plus the recorded pre-hidden-clue distinction. A stub proves wiring only, not judgment quality.

Cheapest billed causal check: replay six frozen cases, V0/J1c, 5 samples each = **60 Jev calls**, estimated $0.001–$0.002, cap $0.005. Freeze cases and labels before scores: two new location-valid drain attempts, missing, remembered, elsewhere, and the recorded ajar ON-smoke reply. Score the last separately as location-valid but condition-policy problematic; do not require a relation-only judge to reject it. This confirms transfer of location context; it cannot qualify action safety. The earlier 420-row wiring run need not be repeated simply because time passed.

Next smallest engine check, only after P1 and the policy decision below: OFF/ON 3 one-command replicates each, same frozen candidate package/settings, estimated around the previous $0.011934, cap $0.04 and 40 calls per arm if dry-run headroom confirms it. Disable hedges/batching identically in both arms to isolate J1c; record settings. Separately freeze at least one post-Route-E state to establish whether the one-command entry smoke transfers. Do not silently substitute one start for the other.

Tests: extend existing `test_observation_scene_state.py`, `test_live_baseline_scene_state.py`, `test_web_demo_observation_enforce.py`; preserve specific-place/held and mixed-batch negative fixtures, strict boundary scores, actual candidate-location handling, and unrelated-move rejection. Assert both logical request counts and sent-state telemetry.

### P3. Diagnose invented drain affordances with source material before adding rules

No runtime guard or narrator instruction is ready to add. The proven technique is the scene-fixing guide's isolated frozen-prompt material probe, not a claim that this particular wording already works. First remove the unsupported inference that “fixed” establishes closed/empty. The smallest reviewable **plot candidate requiring Brandon's approval** is to describe the existing drain as an opening, rather than create an openable cover. This is a proposed authoring choice, not recovered canon.

At `plot.md:204`, exact old text:

```
**Details:** ordinary park bench; damaged grounds; service path; checkpoints; emergency patrols
```

Exact candidate new text:

```
**Details:** ordinary park bench; damaged grounds; service path; checkpoints; emergency patrols; storm drain opening in the damaged grounds
```

This adds public material about the existing declared `storm_drain`, not an entity named “opening,” a new place, contents, or a new reveal. It leaves the future escape possible. **Brandon must approve that physical interpretation before any package edit.** If he intends a covered or gated opening instead, withdraw this candidate; that needs a separately grounded declaration and approved starting state, not an inferred closed-container patch. Do not conflate the service gate and the drain.

Cheapest free check: old/candidate package in memory, eight payload captures per arm (16, $0): opening, initial inspect, retry, malformed recovery, post-find drain inspect, unrelated bench command, 1B.2 and earned escape. Verify the new phrase resolves to the existing drain, introduces no new thing/place, and reaches the intended narrator requests. Inspect all affected paths described in the narrator-writing guide; unrelated scenes must remain byte-identical. Check the public phrase does not leak a future revelation. This is a capture/check plan, not evidence that the material will work.

Cheapest billed check: old prompt versus same prompt with this **one generated Details-line addition**, 10 samples per arm = **20 narration calls**, approximately $0.014, cap $0.03 (historical per-prompt estimate, not a quote). Use the exact recorded drain prompt, ordinary `inspect the storm drain` input, no negative command restraints. Read every narration; separately label opening/entering, invented prior ajar condition, definite contents, speculation, wrong place, and prose/capture disagreement. Require the control to reproduce the defect and the candidate to have zero opening/entering or invented cover/contents failures in this screen before a separate 15-per-arm confirmation (30 calls, approximately $0.021, cap $0.04). Do not use one passing screen as an enforcement guarantee. Free capture replay first; any reply needing a live matcher is unverified rather than silently passed.

Tests if approved and supported by the probe: `test_scene_1b_grounding.py`, `test_1b_spine_prompts.py`, package loading and leakage tests, prompt captures for every affected path, and the existing escape journey. Preserve correct name resolution and later service-gate/escape earning. Add cross-genre material/capture fixtures where applicable; do not hardcode a drain exception in shared runtime. No prompt-string assertion is offered as evidence of model obedience.

## How the full enforced stage should change

Keep the frozen preregistration intact. Write a new addendum only after the free repairs and authoring decision, then obtain the separately required billed-run go. This task grants neither that go nor deployment permission.

1. **Retain** the narrow one-command entry experiment, 20 replicates per arm, D1 18/20, D2 16/20 and the $0.20 ceiling as the proposed confirmation design. Hold it now. The old smoke's package differs from the current hidden-clue package, so pin code plus package hashes, model, flags and entry checkpoint. The uncommitted working tree makes HEAD alone insufficient provenance. Confirm caps by dry run with openings, retries and any chosen hedges; no automatic budget expansion.
2. **Clarify D3 before seeing new scores.** Old label: `opens_drain (the drain is opened, lifted or entered)`. New label contract: **“Record player-caused opening/lifting/entry separately from an invented initial ajar/open condition. D3 permits neither unauthorized opening/entry nor an unsupported cover/open-state claim in committed inspection prose. Score definite interior assertions separately from attempts to peer inside.”** Preserve zero committed forbidden behavior. Freeze whether ambient water/debris counts under the existing contents criterion; its current vegetation/debris carve-out must not be used inconsistently after results arrive. All plot decisions require Brandon's approval. Do not claim the historical smoke formally failed a gate it never ran.
3. **Separate D6 location fidelity from other safety labels.** Old `really_deficient` lists missing/remembered/elsewhere/denied. Keep that definition for location analysis; add a separate condition/action label rather than changing its meaning to rescue counts. A location-valid but action-invalid rejection is not evidence that the location judge correctly enforced action safety. Freeze blind labels for every unique attempt that reached verification, including rejected second attempts, then join. Do not count losing hedge bodies as logical attempts.
4. **Strengthen evidence, not thresholds.** Old D5 checks `places_after == places_before` (six tracked parents, excluding the drain). New requirement: **“Every unsuccessful turn has a typed error, no committed narration, equal full-state digests, and matching structural evidence; logical narration and verifier requests remain at most two. Report physical dispatches and late completions separately.”** Retain D4 for all actual ON/OFF requests, now with recorded state. Test missing telemetry as insufficient evidence, not PASS.
5. **Limit the conclusion.** Even a clean 20-per-arm entry result does not prove the sixth Route E turn under post-find state. Cheapest subsequent integration check is unchanged Route E, J1c ON, 3 replicates = 18 turns, estimate $0.02–$0.04, cap $0.07/240 HTTP calls as the existing smoke precedent. Include drain outcomes and safety explicitly; don't reuse its drain-excluding S gates as coverage. Regression C/D and hosted SHA-bound staging remain later requirements, not authorized work here. No promotion claim follows from a local Worker run.

## Verification performed and remaining uncertainty

Read the named preregistrations, prior Route E proposal 5, reports and probe rows; inspected each new drain's prompts, returned narration/item_facts, observation request, verifier attempts, previews, timings, summaries and run-log spend totals, plus the earlier drain-only OFF/ON smoke. Recomputed counts and timings with read-only `uv run python` JSON inspection. Inspected the observation/capture/adapter/runner/report source and scene declarations. Used codebase-memory discovery for source symbols; Serena was not available. Consulted PRD, contributor, player-input, narrator-writing, grounding, scene-fixing, workflow, promotion and testing guides; historical W1–W5 and the command-scoped state-wording result at `5ea0119955c62b84699a8dc7878a4af770b55a7e` establish the no-parsing, material-first and scoped-state precedents. The testing-runbook skill was consulted; the explicit only-plan-file scope takes precedence over its usual runbook-edit requirement.

Not performed: new billed calls, model calibration, formal blind labels/join, implementation tests, hosted checks, or a full replay of runtime capture for all recorded replies. The source-material hypothesis is unmeasured. J1c on the current post-find Route E state is unmeasured. Exact per-turn billing and every hedge winner cannot be recovered from these records; run-level spend remains valid within logged completion limits. Full-state digest equality supports rollback, not the semantic correctness of accepted prose. The recorded relation verifier cannot by itself certify conditions, contents or action authorization. If approved source material fails to suppress those defects, stop and design a separate story-agnostic safety experiment; no proven general condition verifier is established by these artifacts, so none is smuggled into this plan as an implementation fix.
