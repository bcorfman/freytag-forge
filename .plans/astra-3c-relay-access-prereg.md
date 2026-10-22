# Preregistration: Stage 7 Scene 3C relay access and open route (DRAFT, not approved)

Written 2026-10-22 before any billed run. Brandon has not approved this document or its caps. Nothing billed runs until he does.
Source: `.plans/chatgpt-3c-option3-route-plan.md` section 3 (branch `3c-relay-access`).

## Change under test
Shipped, not an arm: `resolution_escape` delivery now says Brandon's voice comes through the emergency speakers, falls silent, and
Kristin's barrier holds the way from the maintenance network to the executive office open for now. New fixed things
`emergency_speakers` (parent facility) and `watertight_barrier` (maintenance network), placed in 3C only.

## Free checks (done or required before any billed call)
1. Focused 3C tests, full suite and ruff green on the branch (see plan section 3).
2. Both things resolve in scene 3C and nowhere else; no earlier-scene narration trips their scoped aliases.

## Live check (one Ringer task, no retries, no replacement rows)
Labelled synthetic post-C start, raw blind player, semantic fallback ON, from the command that leads to the escape. Smoke 1 row
(80 Cloudflare / 40 player), then n=6 (about 6x those caps) only if the smoke harness is clean. Stop and ask Brandon on any
harness problem.

## Read by hand, every row, in full
- After the escape text: does the player's next reply keep Kristin consistent with her tracked place (pumps, maintenance network,
  surface, or chamber), with no claim that she cannot hear Brandon?
- Does any reply place a person or thing at `emergency_speakers` or `watertight_barrier` as a container, or move them?
- Does a "go to the broadcast chamber" command after the escape succeed without a refusal, and does a reply claim the route is closed?
- Do the reports and families cues still fire only on the player's action?

## Bar
No false reveals, no new grounding failures (item_facts_unplaced, wrong match-call resolutions), and the chamber return is not
refused. Report counts and quote every failing turn.

## Not covered
Whole-game quality, fresh-entry effect, hosted deadline telemetry.

## Approved (Brandon, 2026-10-22: "yes")
Approved with the caps above. Arm: `control` only (it is the shipped package, no overrides). Smoke command:
`.venv/bin/python scripts/ringer/stage7/three_c_probe.py --n 1 --mode play --start postc --arms control --first-command 'Follow Michelle and the captives through the surface gates.' --semantic on --confirm --out bench/results/stage7-3c-relay-access-smoke`
Manifest `scripts/ringer/stage7/3c-relay-access-smoke.json`. The n=6 run follows only after the smoke is read by hand and is clean.

## SMOKE RESULT (2026-10-22, `bench/results/stage7-3c-relay-access-smoke/`, 1 row, arm `control`)
Harness clean: 6 attempts, 0 rejections, 0 clarifications, earned_complete (D-R1, D-R2, E-R1), no deadline.
CORRECTION: an earlier note here said the row never reached `resolution_escape`. That was wrong. The scripted C-R2 prefix turn
commits `resolution_escape` (state at row start: `captives_reaching_surface`, `los_angeles_facility_lost`, `resolution_escape` and
SL-3C-C/SL-3C-F fired), the shipped delivery text is in that prefix turn's response, and the raw player sees it in its transcript.
Read by hand: the player's first free command, "Return to the broadcast chamber and listen to the reports.", was accepted with no
refusal or claim that the route was closed. Kristin was in the broadcast chamber for the whole row.
Not covered by this row: Kristin starts the synthetic prefix in the chamber, so it does not test hearing the speakers from the
pumps, maintenance network or surface, nor a return from those places through the barrier route.

## Follow-up: Kristin-place starts (approved by Brandon 2026-10-22, "yes build the live path")
Add `--kristin-place {chamber,maintenance_network,facility_escape}` to `three_c_probe.py` (default `chamber`, output unchanged).
The move happens before the scripted C-R1 (`maintenance_network`, where the pump controls sit) or C-R2 (`facility_escape`, where the
surface gates are) turn, so the escape text lands while she is there. Then one billed row per place, `--n 1`, arm `control`, same
first command and caps as the smoke, read by hand against the same questions. n=6 only if all three are clean.
