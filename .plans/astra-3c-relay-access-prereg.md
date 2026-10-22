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

## KRISTIN-PLACE RESULT (2026-10-22, one row per place, arm `control`, `bench/results/stage7-3c-relay-access-{maintenance_network,facility_escape}/`)
Probe change: `--kristin-place` (Ringer run `3c-kristin-place`); both rows 0 rejections, 0 clarifications, harness clean.
- Escape text landed with Kristin at the maintenance network (before C-R1) and at the surface (before C-R2); the C-R2 response
  carries the shipped text exactly.
- Every row: "Return to the broadcast chamber." was accepted, narrated as Kristin rushing back and reaching the chamber, with no
  refusal and no claim that the route was closed or that she could not hear Brandon. No reply placed anything at the speakers or
  barrier. Outcomes: `facility_escape` earned_complete (13 turns); `maintenance_network` deadline_complete (14 turns; the player
  looped on a phone call and the deadline closed the scene, not tied to this change).
- Observation outside this change: in both rows the tracked `kristin_parent` never changed (stayed `maintenance_network` /
  `facility_escape`) although the narration moved her to the chamber; the same field was constant in the earlier smoke too. Rows do
  not record unplaced item facts, so the cause is undiagnosed. It is the "narrated move does not land" class, not the speakers or
  barrier; the engine does not check connectivity, so the open route cannot cause it.
Bar: met (no false reveals, no new grounding failures seen, chamber return not refused). n=6 not run: two clean rows and an
outside-scope tracking observation; a larger run would not test the changed text further.

## Tracking diagnosis (Brandon, 2026-10-22: "yes" to diagnosing the Kristin-position observation)
Free: `--capture-item-facts` flag (Ringer run `3c-capture-diagnosis`). Live: one row, `--start postc --kristin-place facility_escape
--arms control --capture-item-facts`, same first command and caps as the smoke (80 Cloudflare / 40 player), manifest
`scripts/ringer/stage7/3c-capture-diagnosis-row.json`. Read: for the turn after "Return to the broadcast chamber.", whether the
narrator listed Kristin in item_facts, what place it named, and whether the move was matched, unplaced or refused. No fix is chosen
before that is read; the technique comes from the plan's decisions and earlier narration fixes.

## TRACKING DIAGNOSIS RESULT (2026-10-22, `bench/results/stage7-3c-capture-diagnosis/`, 1 row, facility_escape, flag on)
Every capture field is null (`match`, `unplaced`, `refused`, `raw`) and `issues`/`steps` are empty on every turn, and no THINGS or
PLAYER line is recorded. Cause: the 3C probe builds its provider from `bench/variations/stage7-3c-control.json`, which has no
`item_facts` key, so `provider_for` returns a plain `CloudflareTurnProvider`. The product's place capture (`WorldCapture` with an
`ItemFactsProvider`, enabled by `FREYTAG_WORLD_CAPTURE=1` in `web_demo.py`) never runs in these rows. A constant `kristin_parent`
in 3C probe rows is therefore a harness property, not evidence that narrated moves fail in the product, and the earlier note
that it was a tracking defect is withdrawn. Not covered: whether the product captures Kristin's chamber return; that needs a probe
variation with `item_facts` (e.g. `item-facts-world-3c-runtime.json` style) or the hosted check.

## Item-facts arm row (Brandon, 2026-10-22: "yes" to checking the product's own capture)
Arm `item-facts` (variation `stage7-3c-item-facts.json`: control package, product capture provider settings from
`build_capture_provider`), built by Ringer run `3c-item-facts-arm`. One row, `--start postc --kristin-place facility_escape
--capture-item-facts`, same first command and caps (80 Cloudflare / 40 player), manifest `scripts/ringer/stage7/3c-item-facts-row.json`.
Read: after "Return to the broadcast chamber.", does `kristin_parent` become `broadcast_chamber`, and what do match, unplaced and
refused say; also whether any reply moves a person or thing to the speakers or barrier.

## PRODUCT-CAPTURE RESULT (2026-10-22, `bench/results/stage7-3c-world-capture-row/`, 1 row, arm `item-facts` with WorldCapture, facility_escape start)
First `item-facts` row (`stage7-3c-item-facts-row`) had the product provider but no `WorldCapture` in the engine, so a narrated
`{"Kristin": {"place": "broadcast chamber"}}` was discarded. Ringer runs `3c-item-facts-arm` and `3c-world-capture` wired the
product's engine construction into the arm; every Jev call is counted against the 80-request Cloudflare cap (8 Jev events of 21 in this row).
Read by hand: 0 rejections, 0 clarifications. The tracked `kristin_parent` followed the narration: surface -> maintenance_network
(when the player helped Michelle through the tunnel) -> broadcast_chamber on "Return to the broadcast chamber." The reply for that
turn reads "heads back through the maintenance tunnel. She emerges into the broadcast chamber", the route the barrier sentence opened,
with no refusal and no unplaced or refused capture entry. Scene ended by deadline (player lingered in the tunnel), unrelated to this change.
Conclusion: the product's capture applies Kristin's return to the chamber after the escape text; the constant position in the
`control` rows was the harness. n=1, so no rate claim.
