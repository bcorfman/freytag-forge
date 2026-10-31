# T9h stage 2 diagnostic arm screen (preregistration)

Status: FROZEN before any billed call of this screen (2026-10-30). Source plan:
`.plans/chatgpt-t9h-stage2-diagnosis-plan.md` (proposals B and C). Brandon's authorisation: "go ahead with all when
they are correct" (2026-10-30), given after the free repairs passed their checks.

This is a **separate diagnostic registration**. It does not reopen the frozen stage 2 chain, does not relabel its
results, and does not authorise stage 3. The recorded stage 2 result stays FAIL (`bench/results/environment-narration/
t9h-hidden/prose/report.md`, labels sha256 `76559b6f...152bc1a3`). Its artifacts are byte-pinned by
`scripts/ringer/environment_narration/check_t9h_stage2_measure_repair.sh`.

## What is measured

Ten `find`-state replies per arm, through the same hermetically captured, world-aware request path
(`hidden_bench_arm_probe.py`, built on the repaired prose probe). No injected prompt text in any arm.

| arm | what differs from `base` |
| --- | --- |
| `base` | nothing: the working-tree package as it stands |
| `B` | one line of `plot.md` in a temporary copy: the bench Details line gains `The park bench is fixed in place.` (exact old and new lines are in the probe; it fails if the old line is not found exactly once) |
| `C` | the captured request loses exactly one line: `- Brandon Corfman may say this aloud: I won't tell you that. Keep your voice down; patrols are nearby.` (a recorded-prompt diagnostic, not a package edit; the CHARACTERS biography stays) |

B and C are never combined in one arm. The wording of B is new and unmeasured. Nothing is edited in the real story
package by this screen.

## Budget and rules

30 calls (3 arms x 10), ceiling $0.03 behind `local_worker.mjs --max-usd 0.03`; the probe's own estimate is about
$0.002. Billed once. Never rerun after a partial result; no replacement samples; stop on 429, 401/403, 5xx or the cap.
The output directory is fresh (`bench/results/environment-narration/t9h-stage2-diagnostic/`).

## Reading the results

Replies are labelled by Claude from blind sheets (arm and payload hidden; narrator text and the engine-appended
delivery shown separately), with the labels file hash frozen before the join to arms. The sheets hide arm labels but
the prose can make an arm recognisable (C has no Brandon dialogue line, B mentions the fixed bench); this is a known
limit. Labels are the nine defined in the probe: attempted lift, completed lift, final bench place changed,
route/face/identity revealed, premature Brandon naming, extra object invented, meta-narration, unsolicited Brandon
dialogue, and whether narrator plus appended text convey all three objects and keeping.

**No gate, no rate.** The report gives per-arm counts only. Ten samples per arm cannot prove a rate. A candidate
"wins" only if it shows clearly fewer of the targeted defects than `base` and no new defect; B targets lifting
language, C targets unsolicited and premature Brandon. A win is a reason to propose an integration and a larger
registration, never a pass of any stage.

## After the screen

Any production edit to `plot.md`, knowledge or handoffs for a winning arm is a separate change that needs its own
free checks first. Stage 3 (the route E smoke) stays blocked until the runner records `facts_after` for every turn
(the repaired reporter reports S1 and S3 as insufficient evidence without it) and Brandon registers it separately.
