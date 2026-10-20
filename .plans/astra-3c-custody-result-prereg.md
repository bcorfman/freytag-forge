# Preregistration: Stage 7 Scene 3C custody-handoff screen (Step 3 of `.plans/chatgpt-3c-stuck-turns-plan.md`)

Written 2026-10-19 before any billed run. Brandon: "Keep the entry text where it needs to be for the 12 rows. Do Step 3."
I read that as: the Step 2 entry text is in BOTH arms of this screen (as an override, no `data/` edit); the only difference is the
custody delivery. Engine for typing: codex `gpt-5.6-luna`. Same harness and stop rules as `.plans/astra-3c-stuck-turns-prereg.md`.
Step 2 is not adopted into `data/`; it is the baseline, not a verdict.

## Change under test (one source change on top of the entry-text baseline)
`knowledge.yaml` k_sl_3c_b_r1 `delivery_text`: "Kristin stops Rebecca from fleeing with the data case. Michelle sends its prisoner
locations to independent networks. Water rises around the drainage pump controls." becomes "Kristin takes the Portable data case
from Rebecca. Michelle sends its prisoner locations to independent networks. Water rises around the drainage pump controls."
The pump sentence is kept (Step 4 changes it separately). It states the custody change that `world.yaml` `portable_archive_secured`
already commits; it adds no fact. Arms: `entry` (baseline = entry text only, existing variation) and `custody`
(`bench/variations/stage7-3c-custody-result.json` = entry text + this delivery; each old string matches exactly once).

## Free checks (before any billed call)
1. Both overrides apply once; only the entry text and the B-R1 delivery differ between arms.
2. After B, the existing on_assert puts the Portable data case under Kristin in both arms; B does not grant either C part;
   a no-move provider replaying `Take the Portable data case from Rebecca.` leaves it under Kristin.
3. Hermetic harness tests and `--dry-run` pass.

## Live screen (plan: start after A at turn 2, earn B with `Follow Rebecca.`)
New labelled start `posta`: scripted A-R1 (`Send the evidence package.`), turn index 1, entry facts asserted, entry text shown to the
player (new text in both arms). Scripted first command `Follow Rebecca.` (earns B-R1 in both arms; verify by preflight and report
any row where it does not). Then the raw blind player, cap 20 attempts, real deadline 14, semantic fallback ON.
Smoke 1 row per arm (80 Cloudflare / 40 player), read in full, then n=12 (960 / 480).

## Measures and bar (plan)
Win: >= 10/12 `custody` rows treat custody as completed (hand read of the reply after the first command and the next accepted
reply: the case is with Kristin, not back in Rebecca's hand), no regression in the case's recorded parent, and fewer repeated
acquisition commands than baseline. Per attempt the harness records the case's parent; per row it counts player commands after the
B commit that try to take, grab, retrieve or wrest the case again (a count over PLAYER commands for reporting; narration is never
scanned). Also reported: C-R1/C-R2 and D/E commits, outcome (earned / deadline / none), rejections, clarifications. Differences
under 3 rows read "not distinguishable at n=12". If the case's parent regresses despite correct material, that is reported as a
separate shared proposal/commit finding with a reproducer; no story-specific engine branch.

## Limits (say up front)
This changes the text AFTER B. The 4 of 12 Step 2 rows that never reached B (never left the chamber) are not touched by it; they
need a different hand-off and are outside this screen. Synthetic start; one story; one raw player prompt.
