# Preregistration: Stage 7 Scene 3C surface-binding consistency screen (Step 1 of `.plans/chatgpt-3c-stuck-turns-plan.md`)

Written 2026-10-18 before any billed run. Brandon authorized free work, one smoke, and the n=12 screen in one pass
(2026-10-18). Engine for typing: codex `gpt-5.6-luna`. Extends `.plans/astra-3c-stuck-turns-prereg.md` (same stop rules,
same harness `scripts/ringer/stage7/three_c_probe.py`).

## Change under test (one source change)
`data/stories/continuity-initiative/world.yaml`: bare `captives_reaching_surface` becomes
`{id: captives_reaching_surface, on_assert: [{move: captives, parent: facility_escape}]}`.
Variation file `bench/variations/stage7-3c-surface-binding.json`; control is `bench/variations/stage7-3c-control.json`.
No `data/` file is edited by this work; the screen applies the change as an override.

## Free checks (must pass before any billed call)
1. Populated-member fixture: with members actually placed in `captives`, the move relocates the group and its members
   and no person (Kristin, Michelle, Brandon). Both C orders, C2-only (no early move), deadline fallback, save/load.
2. New harness start `postc`: scripted A-R1, B-R1, C-R1, C-R2 committed, turn index 7, Kristin in `maintenance_network`.
   Preflight: reveal universe is exactly `[k_sl_3c_d_r1, k_sl_3c_d_r2]`.
3. Hermetic harness tests and `--dry-run` pass.

## Live screen (arms: `control`, `surface`; interleaved; semantic fallback ON; labelled synthetic start)
Per row: from `postc`, first command `Follow Michelle and the captives through the surface gates.` (identical in both arms),
then the raw blind player with the running transcript, cap 10 attempts total, stop at `story_complete`.
Smoke: 1 row per arm, read in full before n=12. Caps: smoke 80 Cloudflare / 40 player; n=12: 480 / 240.

## Measures (engine data; narration is read by the orchestrator, never lexically scanned)
Mechanical: captives' parent after the first command (target `facility_escape` in `surface`, unchanged in `control`),
no person moved, captives never moved by C2-only controls. Per row: committed reveal ids in order, accepted turns,
accepted travel-type turns before the next D commit (read by hand), outcome (`earned_complete`, `deadline_complete`,
`no_complete`), rejections, clarifications, deadline ids. Record complete state (captives parent, Kristin parent) after each accepted turn.

## Bars
Consistency (adopt as grounding correction): in at least 10/12 `surface` rows, the reply after the first command respects the
completed captive escape and answers Kristin's own movement (read by hand, quoted in the report), no new guard failures.
Continuation (claim only if shown): D-R1 and E reached more often than control. Scene claim needs fresh-entry >= 10/12 earned (not this screen).
Differences under 3 rows read "not distinguishable at n=12". Report all rows.

## Stop rules
As in `.plans/astra-3c-stuck-turns-prereg.md`: one Ringer task per smoke or screen, one attempt each, stop on cap, quota,
malformed output or a harness problem and report; never replace rows. A smoke showing a harness problem stops the run.

## RESULT (2026-10-18)
See the "Stage 7 3C surface-binding screen, Step 1 RESULT" entry in `.plans/implementation_plan.md`. Consistency bar missed (9/12); surface earned 3/12 against control 7/12. Binding not adopted.
