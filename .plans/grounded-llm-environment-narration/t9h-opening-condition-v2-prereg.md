# T9h opening condition check v2: preregistration (2026-10-30)

Approved by the user on 2026-10-30 ("Go ahead with all", after the step (a) report). That covers the kind edit, this preregistration, the gate below, the generation cost and the judge cost. It does not cover Step 3 integration, the hosted flag, staging, the full enforced stage or the `plot.md:204` Details edit.

Design and history: `t9h-drain-condition-experiment-design.md`, sections 9 to 11. This replaces the class in section 10 with the declared kind from section 11.

## Question

Does the Step 2 judge (Variant B, wording unchanged) separate forbidden from clean narrations about things of kind `opening` that it has never seen? The drain result from Step 2 (52 of 54 forbidden rejected, 46 of 46 clean accepted) is the in-class evidence already collected. This run tests the other four members of the class.

## Class

A thing is in scope when the story package declares it with kind `opening` (`world.yaml` `kinds:`: `is: [thing]`, `fixed: true`, no axis, no contents). The harness reads the class from the loaded package and never from a list of names. In `continuity-initiative` that gives `back_door`, `house_gate`, `service_gate`, `facility_gate` and `storm_drain`. The drain is excluded from the new set because its narrations were already used.

## Policy encoded (the author's decision, unchanged from section 10)

For a thing of kind `opening`, a narration that states it open, ajar, lifted, covered or entered, or states what is inside it, is unauthorized, because the world declares nothing that would support it.

## New held-out set

- Four things, ten narrations each, 40 narrations, nobody has seen them.
- Each prompt is the real narrator request the engine builds offline (stubbed model, no network) for one turn, with the protagonist placed where the thing is, then sent verbatim to the narration model through the local Worker:
  - `Inspect the back door.` in scene 1A, protagonist in `kitchen`.
  - `Inspect the house gate.` in scene 1A, protagonist in `outside_house`.
  - `Inspect the service gate.` in scene 1B, protagonist in `los_angeles_park`.
  - `Inspect the facility gate.` in scene 2A, protagonist in `facility_perimeter`.
- If a prompt cannot be built offline for one of the four, that thing is reported as not reproducible and dropped; the run then needs at least three things and 30 narrations, else it stops before any billed call.
- Cap: 40 calls and $0.06 (local Worker spend guard). Stop reasons are recorded; a partial set is reported as partial and gates nothing.

## Labels (frozen before any narration is read)

Claude labels blind (per the standing rule that Claude, not ChatGPT, adjudicates drain-style labels). The sheet shows only the narration, shuffled with a fixed seed. Labels are frozen by SHA-256 before the cases are built or the judge runs.

The D3 contract from `t9h-drain-full-stage-addendum.md`, applied to an opening:

- `opens_or_enters`: the player character opens, lifts, pushes open, climbs through or enters the opening in a way the command did not ask for (the command only inspects).
- `invents_open_state`: the narration states an initial condition the world does not declare: open, ajar, lifted, cover missing, unlatched or swinging free.
- `asserts_definite_contents`: the narration states as fact what is inside the opening, or what is past a door or gate as seen through it standing open or after it is opened. Looking at the outside, over a gate or through its bars is exterior, not contents.
- Informational, not forbidden: `speculative_only` (wonders what might be past it), `asserts_closed_or_locked` (states it closed, locked, chained or padlocked; the policy and the judge wording do not cover this, so it is recorded and not scored), `wrong_place`.
- `forbidden` is true when any of the first three is true.

## Judge

- Variant B question and payload from `drain_condition_judge_probe.py`, imported, not copied, so the wording is byte-identical.
- Declared sentence for each case, built from the declaration of kind `opening`: `the <thing name> has no open or closed value, no declared contents, and is fixed in place.`
- Five samples per case, 200 calls, paced at 0.5 s, cap 200 calls and $0.02.
- Per-case median score; accepted above .65, rejected below .35, otherwise uncertain. Uncertain counts against both conditions.

## Gate (approved)

PASS when at least 90% of forbidden cases are rejected and at least 90% of clean cases are accepted, with at least 10 forbidden and at least 10 clean cases. Fewer than 10 of either: INCONCLUSIVE. A partial judge run: INCONCLUSIVE. No relabeling after the judge rows are read; no top-up in this run.

## What a pass does and does not establish

A pass says the judge, given the declared sentence, generalizes from the drain to the other declared openings of one story. It does not show it generalizes to another story, to containers or other kinds, to live engine turns, or that wiring it in is safe; Step 3 would need its own approval and preregistration.

## Artifacts

`bench/results/environment-narration/t9h-opening-v2/` (gitignored): `capture.json`, `generate/rows.json`, `sheet/`, `labels.json` and its freeze, `cases.jsonl` and lock, `judge/rows.json`, `report.md`.

## Amendment 1 (2026-10-30, before any billed call or any narration was read)

- **Capture fidelity.** The first harness build left the inspected thing out of the narrator's THINGS block (its stub never let the referent match name it) and force-activated every storylet of the scene. A live turn lists the inspected thing (`- storm drain. Place: Los Angeles park.` in `t9h-hidden/smoke`) and activates no storylet by force. The capture is fixed before generation, and the check requires `- <name>. Place: ...` in THINGS for all four things.
- **Back door and the 1A reveal.** In scene 1A the inspect turn carries the authored reveal "the back door was forced" (the game appends it after the narration). That is a declared story fact, not an invented condition. Label rule, frozen now: forced, broken, damaged or a broken lock on the back door is not `invents_open_state`; stating it open, ajar, standing or swinging open, or stepping through it, still is, and so is any view past it presented as seen through it open. The judge's declared sentence is unchanged (it does not mention the reveal), so a judge rejection of a clean "forced" narration counts against clean acceptance; the back door is also reported on its own line.
- **How billed stages run.** Each billed stage (generate, judge) runs as its own one-task Ringer manifest, with the local Worker spend guard at the caps above.

## Amendment 2 (2026-10-30, after a partial generation; no narration read)

The first generation (`generate/`) stopped at 3 of 40 rows, `stop_reason request_error`, $0.0022 spent: `rows.json` was written exactly 20.0 s after the third reply, i.e. the 4th narration request (and its 4.5 s hedge duplicate) stalled upstream until the request timeout, the same "hedged request timed out" failure seen in the drain OFF smoke. It is kept as a partial run and gates nothing; its 3 narrations are not labeled or used. The harness now records each failed call's error type and message and retries a timed-out sample once after the planned calls (at most 44 HTTP calls, stop after 3 consecutive failures; any other error still stops the run). One fresh generation runs into `generate-2/` with the Worker guard at $0.057, so the two runs together stay inside the approved $0.06. Labels, gate and judge are unchanged.

## Result (2026-10-30)

Generation `generate-2` 40/40, no failed calls, $0.0423 (plus $0.0022 for the partial `generate`); blind labels by Claude frozen (sha256 `248f923e...4258`): 19 forbidden, 21 clean; cases locked (`ccec34d0...e2b3`, 40 cases); judge 200/200 rows, no stop reason, $0.0059. **Verdict PASS: forbidden rejected 19/19, clean accepted 21/21, no uncertain case.** Per thing: back door 9 clean accepted (including every "forced open" reveal narration) and 1 forbidden rejected; facility gate 9 and 1; house gate 3 and 7; service gate 0 clean, 10 forbidden rejected. Total billed for v2 $0.0504. Report: `bench/results/environment-narration/t9h-opening-v2/report.md`. Ringer runs under `t9h-opening-condition-v2` (kind edit, harness build, capture fix, timeout retry, generate, generate-2, judge).

Limits, read before any further step: the forbidden set is dominated by one pattern, the gate described "slightly ajar" and then pushed open (17 of 19); the service gate gave no clean narration, so clean acceptance there is untested; the labels are mine (one labeler, blind to source but not independent); one story; offline-built prompts replayed through the narration model, not live engine turns. The pass licenses proposing Step 3 for things of kind `opening`; it does not approve it.
