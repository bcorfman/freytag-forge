# Preregistration: 3C Step 2, completed-broadcast recall (DRAFT, not approved)

Written 2026-10-18. Follows `.plans/chatgpt-3c-stuck-turns-plan.md` Step 2. Step 1 missed the bar (earned 1/12 control,
1/12 pre667 of the 10/12 bar; `.plans/implementation_plan.md`), so Step 2 is available. Nothing billed runs until Brandon approves.

## Arm

`bench/variations/stage7-3c-broadcast-result.json` (free check done: replacement matches once, package loads, hash `96999bed44d2`).
It changes only the `knowledge.yaml:2413` statement to "Independent networks have the captives' video, JANUS records,
planning sessions, and detention locations." Control = current package. Both arms keep #667.

## Harness gap (must be fixed before any run)

`scripts/ringer/stage7/three_c_probe.py` hardcodes `ARMS = ("control", "pre667")` and a pre667-specific phrase check
(lines 29, 86-92). It needs a `--arms control,broadcast-result` option. Code change: route through Ringer, test-first.

## Design (plan Step 2)

1. Free: diff the SCENE/sayable prompt payload between arms for the recorded turns 9-11 states; only the one statement may change.
2. Live A-style diagnostic, post-turn-8 synthetic start, recorded raw commands of turns 9, 10, 11, 12 replicas per arm.
   Single-turn win: less repeated broadcasting, no invented outcomes, no new rejections. Diagnostic only.
3. Live C fresh screen, 12 rows per arm, 20-attempt cap, semantic fallback ON. Bar: >=10/12 earned (no deadline-supplied link).
   Compare with control rerun in the same run; report earned / deadline / none, rejections, clarifications separately.

## Known weakness (decide before spending)

Step 1 Live B/C showed the stall is mostly the post-gates flee loop (115 of 144 commands were movement; none mentioned
reports or broadcast) and the lost turn 1, not broadcast recall. Step 2 may not move the earned count. The surface binding
(`3c-surface-group-binding`) targets the observed loop and is the plan's separate, independent probe.

## Spend

Same ceilings as the Step 1 Live C row: 960 Cloudflare / 480 player for 24 rows, plus a n=1 smoke read in full first.
Stop rules and one-Ringer-task-per-run as in `astra-3c-stuck-turns-prereg.md`.
