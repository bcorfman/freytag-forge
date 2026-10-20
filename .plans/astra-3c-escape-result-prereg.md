# Preregistration: Stage 7 Scene 3C escape-result statement screen (Step 5 of `.plans/chatgpt-3c-stuck-turns-plan.md`)

Written 2026-10-18 before any billed run. Brandon ordered this run before the Step 2 smoke (2026-10-18) after the Step 1 result
(surface binding unadopted: 9/12 consistent replies, surface earned 3/12 against control 7/12, tunnel loops in rows 10-12 that
follow the C-R1 statement). Engine for typing: codex `gpt-5.6-luna`. Same harness and stop rules as
`.plans/astra-3c-stuck-turns-prereg.md`. The Step 2 screen is NOT cancelled; it resumes after this one.

## Change under test (one source change, WITHOUT the surface binding)
`knowledge.yaml` k_sl_3c_c_r1 `statement`: "Kristin restores power to drainage pumps and holds one watertight barrier while
Michelle leads captives through the maintenance tunnel." becomes "The drainage pumps have power. The evacuation route is open."
Reveal-time delivery text, evidence, effects and eligibility are unchanged. Variation `bench/variations/stage7-3c-escape-result.json`
(old string matches exactly once). Technique: scope or remove stale completed-action recall (2C stale recall, 1A #668).
It asserts no location for any person. The world.yaml binding is NOT part of either arm.

## Free checks (before any billed call)
1. Variation loads; replacement matches once; only the C-R1 statement differs in the shipped payload.
2. C1-only control (offline, real engine): after C-R1 alone, `captives_reaching_surface` is false and no captive or person
   parent changed in either arm. Both C orders still reach the same facts and eligibility in both arms. Matcher results for
   the 15 recorded commands are identical in both arms.
3. Hermetic harness tests and `--dry-run` pass; rows record `first_d_commit_scene_turn` (first scene turn that committed
   k_sl_3c_d_r1 or k_sl_3c_d_r2, null if none).

## Live screen (arms `control`, `escape`; labelled synthetic post-C start; semantic fallback ON; raw blind player)
Same start as the Step 1 screen: scripted A-R1, B-R1, C-R1, C-R2, turn index 7, scripted first command
`Follow Michelle and the captives through the surface gates.`, then the raw player, cap 10 attempts. Smoke 1 row per arm
(80 Cloudflare / 40 player), then n=12 (480 / 240).

## Measures and bar (plan Step 5)
Win: >= 10/12 `escape` rows commit a D reveal within two accepted commands after the scripted first command (first D commit on
scene turn <= 10), then improvement in earned completion shown separately in a fresh-entry screen (not this one). Also reported,
read by hand: the first reply's account of where Kristin and the group are, and rows with >= 3 consecutive tunnel or travel
commands. Report both arms' counts, earned/deadline/none, rejections, clarifications. Difference under 3 rows reads "not
distinguishable at n=12". Reference points from Step 1 (same start, same first command): control first D commit by turn 10 in
n of 12 is recomputed from `bench/results/stage7-3c-surface-n12/rows.json` for context, not pooled with this run.
No claim about the whole scene from this start (the synthetic start is kinder than a fresh game).

## Not covered
Fresh-entry effect (needs the 20-attempt fresh screen), Kristin's own position (not asserted here), the Step 2 entry text,
deadline changes.

## RESULT (2026-10-18)
See the "Step 5 RESULT" entry in `.plans/implementation_plan.md`. Bar missed (3/12 against control 7/12). Not adopted.
