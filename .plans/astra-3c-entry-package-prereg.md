# Preregistration: Stage 7 Scene 3C entry-text screen (Step 2 of `.plans/chatgpt-3c-stuck-turns-plan.md`)

Written 2026-10-18 before any billed run. Brandon said "follow the plan" after the Step 1 result (surface binding not adopted),
which I read as the same free, smoke, n=12 authorization shape as Step 1; he can stop it. Engine for typing: codex `gpt-5.6-luna`.
Same harness (`scripts/ringer/stage7/three_c_probe.py`) and stop rules as `.plans/astra-3c-stuck-turns-prereg.md`.

## Change under test (one source change)
`plot.md` scene 3C `entry_text` becomes: "The broadcast chamber lights are steady. Brandon's relay is open. Michelle's evidence
package is ready to send. Water is entering the outer access level." (trailing two newlines kept). Variation
`bench/variations/stage7-3c-entry-package.json`; the old string must match exactly once. No `data/` file is edited.

## Free checks (before any billed call)
1. Loader: variation loads; first player screen shows the new text in `entry` and the old text in `control`.
2. Matcher: the 15 recorded commands and the plan's negative controls (`Transmit/Send the evidence.`, `Run away with the evidence.`,
   `Show Rebecca the evidence.`, `Send the evidence package.`) give identical `_matches_all` results in both arms (the matcher and
   knowledge are untouched).
3. Hermetic harness tests and `--dry-run` pass; rows record `a_commit_attempt` and `a_commit_scene_turn`.

## Live screen (arms `control`, `entry`; fresh synthetic 3C entry; semantic fallback ON; raw blind player; cap 20 attempts; real deadline 14)
Smoke: 1 row per arm, read in full, then n=12. Caps as Live C: smoke 80 / 40; n=12: 960 Cloudflare / 480 player.

## Measures (engine data; narration read by hand, never lexically scanned)
First-stage win (plan): >= 10/12 `entry` rows commit A-R1 (A-R2 also counts) on attempt 1, no false public-disclosure commit
(any committed reveal outside the chain), fewer invented pre-A tasks than control (hand read of the pre-A commands). Then report
the full earned bar separately: earned means `story_complete` with no deadline event supplying a link; >= 10/12. Keep rejections,
clarifications, deadline and no-completion counts apart. Differences under 3 rows read "not distinguishable at n=12".
If the first-stage win fails, stop and diagnose the recorded opening; do not add cue synonyms or widen `evidence`.

## Not covered
Whole-game quality, carried earlier-scene knowledge, a different first-command wording, deadline changes (Step 6).

## RESULT (2026-10-18)
See the "Step 2 RESULT" entry in `.plans/implementation_plan.md`. First-stage bar passed 12/12 against 1/12; full earned bar 1/12 in both arms; 3 `relay open` guard rejections.
