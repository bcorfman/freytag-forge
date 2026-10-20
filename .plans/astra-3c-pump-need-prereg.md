# Preregistration: Stage 7 Scene 3C pump-need screen (Step 4 of `.plans/chatgpt-3c-stuck-turns-plan.md`)

Written 2026-10-19 before any billed run; no harness change or arm run yet. Not authorized to spend until Brandon says go.

## Why this step
Step 3 (custody) result, 2026-10-19: custody wording stops the case re-take loop (4 re-take commands in 1 row of 12, against 15 in 10 rows)
but earned completion stays 1/12 in both arms. Gates (C-R2) are committed in 10-11 of 12 rows and pumps (C-R1) in only 5-6, and the
D/E chain needs both. Step 2's entry text had also dropped the old "forcing water toward the maintenance routes" pump pressure.

## Change under test (baseline = the `custody` arm: entry text + custody delivery)
`knowledge.yaml` k_sl_3c_b_r1 `delivery_text`: "... independent networks. Water rises around the drainage pump controls." becomes
"... independent networks. The drainage pumps need power. Water rises around the drainage pump controls." Arm `pump`
(`bench/variations/stage7-3c-pump-need.json`, entry text + custody wording + this sentence; the new sentence occurs once). Cue text and matcher unchanged.
Baseline choice: Step 3 "won" on its custody measure (11/12 never retry) though not on earned completion; the plan says to build on a winning Step 3 line.

## Free checks (before any billed call)
1. Only the pump sentence differs between `custody` and `pump`. 2. B commit asserts neither C fact; replay C2-first (`Open the surface gates.`)
then `Restore the drainage pumps.`: surface stays false until both. 3. Harness gains arm `pump` (Ringer build task), tests and `--dry-run` pass.

## Live screen
Same start as Step 3 (`posta`, `Follow Rebecca.`, raw player, cap 20 attempts, deadline 14, semantic ON). Smoke 1 row per arm (80 / 40), read in full, then
n=12 (960 Cloudflare / 480 player), arms `custody,pump`.

## Bar (plan)
>= 10/12 `pump` rows commit BOTH C parts by accepted scene turn 10, with no gate-only escape fact. Also reported: C-R1 rows, earned/deadline/none, D/E commits,
rejections, clarifications. Differences under 3 rows read "not distinguishable at n=12". Final target stays the scene bar (earned transitions in >= 80% of runs).

## Limits
Synthetic start; one story; one raw player prompt. Only addresses pumps: rows lost earlier to invention (arrest/vehicle drift, file searches) are out of scope.
