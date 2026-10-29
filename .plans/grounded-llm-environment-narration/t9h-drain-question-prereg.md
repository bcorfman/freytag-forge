# T9h route E drain question: J0/J1/J2 calibration (preregistration, RUN 2026-10-29)

Status: run 2026-10-29 with Brandon's go; result in `.plans/grounded-llm-environment-narration.md` ("drain question calibration result"). Drafted 2026-10-29 from the route E plan, proposal 5 (`.plans/chatgpt-t9h-route-e-plan.md`) and the free hand-labels in `.plans/grounded-llm-environment-narration.md` ("T9h route E: drain hand-labels"). The cases and the harness are built free; the billed run needs Brandon's go.

**Question.** Both recorded `inspect the storm drain` attempts show the drain present in the scene (question A true), but neither names the park (question B not explicit), and the verifier answered `uncertain` (0.58, 0.57), which the product rejects. Is the rejection an over-demanded location on a scene-level place? Does telling the judge the scene and the thing's starting place, or also replacing the question sentence, accept those replies without accepting a missing, remembered or relocated drain?

**Arms (all against the same frozen cases, same thresholds: accept above 0.65, reject below 0.35, same Worker `/jev` route).**
- `J0 current`: the product's own `_question_for(relation)` and the state `{"narration": ...}` only.
- `J1 context only`: the J0 question unchanged; the state gains `"scene": "The Lead in the Park"` and `"starting_place": "Los Angeles park"` (the thing's public pre-turn place). The scene name is the scene 1B title in `plot.md`; a product change would take it from the validated current scene.
- `J2 context plus sentence`: the J1 state, and in the question instructions the second sentence ("Check whether the narration shows the thing named {target} as a present fact at its permitted relation.") is replaced by "Check whether the narration shows the named thing in the scene. Use its starting place when the narration leaves it there. Reject a different final place stated by the narration." The first and third sentences and the true/false criteria stay as they are.

**Cases (frozen; six, one relation each: `storm drain`, place `Los Angeles park`, no holder).**
| id | kind | label | narration |
| --- | --- | --- | --- |
| d-real-1 | positive | accept | recorded attempt 1 (`e/rows` r0, turn 5), verbatim |
| d-real-2 | positive | accept | recorded attempt 2 (`e/rows` r0, turn 5), verbatim |
| d-explicit | positive | accept | authored: the reply says outright that the drain is at the park |
| d-missing | negative | reject | a recorded route E reply that never mentions the drain (checked by script), verbatim |
| d-remembered | negative | reject | authored: Kristin only remembers a drain, none is here |
| d-elsewhere | negative | reject | authored: the reply puts the drain somewhere else (a different place) |
The two real positives carry my hand-labels (not blind). The three authored cases are written to the player-input and world-model guides' standards: no new story things or places beyond the elsewhere place, which must be a place the story already declares. The corpus is locked by SHA-256 in `cases.lock.json`; `--run` refuses on a mismatch.

**Counts and cost.** 6 cases x 3 arms x 10 samples = **180 Jev requests**, fixed-seed order, arms interleaved, no retries, no replacement samples. Expected under $0.005; `--max-calls 180 --max-usd 0.01`. Stops after 3 consecutive unusable replies or on HTTP 429/5xx.

**Gate (each of J1 and J2 against J0).**
- G1: zero accepts among the 30 negative samples.
- G2: at least 27 of the 30 positive samples are `accept` (at most 10% not accepted; `uncertain` counts as a failure because the product fails closed on it). This is my reading of "positive strict failures at most 10%" in the plan; say so if you meant only `reject`.
- G3: positive accepts at least equal J0's.
Choose the simpler winning arm (J1 is simpler than J2). If neither passes, no new product wording. J0's numbers are the before and are reported next to each arm.

**Limits.** Three positives, three negatives, one drain; a pass shows the context fixes the known miss, not that it generalizes. This small screen cannot qualify a changed verifier: rerun the frozen T7 corpus and fresh held-out locations under a new preregistration before any enforcement change. Single-relation requests, whereas the product batches several. Two of the three positives are the replies that exposed the defect.

**Command (after approval, one Ringer probe task).** `(set -a; . ./.env; set +a; .venv/bin/python scripts/ringer/environment_narration/drain_question_probe.py --run --confirm --samples 10 --max-calls 180 --max-usd 0.01 --out bench/results/environment-narration/drain-probe-rows.json)` then `--report --rows ... --out bench/results/environment-narration/drain-probe-report.md`.
