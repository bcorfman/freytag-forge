# Preregistration: Stage 7 Scene 3C families-offer cue, continuation screen (DRAFT, not approved)

Written 2026-10-22 before any billed run. Brandon has not approved this document, the arm build or the caps. Nothing billed runs until he does.
Follows `.plans/astra-3c-families-offer-prereg.md` (player-choice screen: offer 11/12 answer the families, control 0/12) and `.plans/chatgpt-3c-after-escape-plan.md` order-of-work step 6. Proposal 1 was stopped (`.plans/astra-3c-entry-subtraction-prereg.md`).

## Question
With the D2 cue offering the answer action, does a blind free-text player in a live post-C 3C continuation leave 3C by an earned transition more often than with the shipped cue?

## Arms (one variable)
- `item-facts`: shipped package, product place capture (as in `bench/results/stage7-3c-escape-close-smoke`).
- `families-offer`: identical except `handoffs.yaml` `community_rescue_efforts_begun` `cue_text` gains `Kristin can answer the families with news of the captives.` (variation `bench/variations/stage7-3c-families-offer.json` plus the `item_facts` block and `WorldCapture` wiring that `stage7-3c-item-facts.json` has). The escape close stays in both arms.

## Free checks (required before any billed call)
1. A Ringer code task adds arm `families-offer` to `three_c_probe.py` (as `3c-no-close-arm` did for `no-close`): variation proof in plan.json/source.json, accepted as a baseline pair with `item-facts`, existing arms' dry artifacts byte-identical, `check_three_c_probe.py` accepts it and rejects tampering. Variation equals `item-facts` in every file except the one cue line.
2. Tests: arm loads, differs from `item-facts` only by that sentence, same provider and WorldCapture wiring, 24-row dry plan with no first command and `POSTC_CAPS[12]`. Full suite and ruff green.

## Billed design (two separate Ringer tasks, no retries, no replacement rows, no top-ups)
Start: labelled synthetic post-C, Kristin at `facility_escape`, no scripted first command, raw blind player, semantic fallback ON, product capture ON, at most 10 attempts per row, as in the escape-close smoke.
1. Smoke: `--n 1 --arms item-facts,families-offer` (2 rows, caps 80 Cloudflare / 40 player). Proceed only if the harness is clean (both arms ran, 0 rejections for harness reasons, artifacts pass the checker, no first command). Stop and ask on any harness problem.
2. Screen: `--n 12 --arms item-facts,families-offer`, 24 rows alternating, `POSTC_CAPS[12]` = 480 Cloudflare / 240 player. Expected use about 15 Cloudflare and 7 player requests per row, so about 360 / 170. Stop on `AI_DAILY_BUDGET_EXCEEDED`; keep partial evidence.
Command shape (smoke): `.venv/bin/python scripts/ringer/stage7/three_c_probe.py --n 1 --mode play --start postc --kristin-place facility_escape --arms item-facts,families-offer --capture-item-facts --semantic on --confirm --out bench/results/stage7-3c-families-offer-smoke`
Cap / usage record: Brandon (2026-10-22) said usage is well within limits; no figures recorded.

## Measures (per row, from rows.json)
`outcome` (`earned_complete`, `deadline_complete`, other), `accepted_turns`, `attempts`, committed reveal ids and their scene turns, D1/D2/E commit turns and order, `deadline_event_ids`, `kristin_parent` per turn, rejections, clarifications. Earned only if D and E commit before the deadline event fires; a D commit on the deadline turn is `deadline_complete`. Also: the raw command at each turn after the D2 cue is staged (does it answer the families?), repeated evacuation/tunnel commands (loop marker: three or more consecutive turns), refused or unplaced item facts, invented devices or callers.

## Read by hand, every turn of every row, in full
- Does the player act on the D2 cue, and in which turn after it appears? Does the D2 delivery follow?
- Does the tunnel loop still occur, and does it block the D2 or E turns?
- Does any reply invent a phone, caller or device for the families, or restart pumps, gates or the rescue?
- Any false reveal, unplaced item fact or wrong match-call resolution.
Preserve malformed, rejected and partial rows. No pooling with earlier rows (the A/B smoke rows are different arms and n=1).

## Decision rule (triage only, not a population rate)
- If `families-offer` earns at least 3 more exits than `item-facts` with no new grounding failure, and at least 10/12 earned in total (plan step 6): the cue helps; go to step 7 (carried entry through the real 3B→3C crossing, then the scene-fixing guide's three live replicates).
- If it earns at least 3 more but fewer than 10/12 total: it helps but is not enough; read the deadline rows for cause before choosing the next change (the tunnel loop is the likely remaining one and has no supported fix).
- If the arms differ by 2 or fewer, or both pass with a difference under 3: the cue is not shown necessary; prefer the shipped wording.
- If `item-facts` earns more: read why before touching anything.
Report counts per arm and quote every deadline row's looping turns.

## Not covered
Whole-game quality, a fresh-entry 3C, hosted deadline telemetry, rates.

## Arm built and smoke approved (Brandon, 2026-10-22)
Arm `families-offer` built by Ringer run `3c-families-offer-arm` (committed; variation `bench/variations/stage7-3c-families-offer-arm.json`, 23 tests green). Smoke approved with "if it passes, run the smoke"; caps 80 Cloudflare / 40 player; Ringer run `3c-families-offer-smoke`, manifest `scripts/ringer/stage7/3c-families-offer-smoke.json`.

## SMOKE RESULT (2026-10-22, `bench/results/stage7-3c-families-offer-smoke/`, 1 row per arm)
Harness clean: both arms ran, 0 rejections, 0 clarifications, no first command, artifacts pass the checker, spend inside caps.
- `item-facts`: `deadline_complete`, no D1/D2/E. Turn 8 return to the chamber (cue D1 staged, no reveal), turn 9 "Leave the broadcast chamber and exit through the surface gates", turns 10-12 asked Michelle about the plan on the surface (the D1 and D2 cues were staged on turns 11 and 12 and never acted on), turns 13-14 followed Michelle through the maintenance tunnel; the deadline ended the scene on turn 14.
- `families-offer`: `earned_complete`, 13 turns. Turn 8 chamber, turn 9 "Listen to the reports." (D1), turn 10 "Ask Michelle to connect the families' calls to the broadcast." (D2), turns 11-12 listened to the families and Charles's signal, turn 13 "Open the recovered document." (E). No deadline event.
Observations: the player did not use the offered sentence's words; it chose its own families command. n=1 per arm, no inference. The surface-versus-chamber difference in the first moves is the player's own choice and reflects the screen's spread, not a result.
The 24-row screen needs Brandon's go-ahead and his approval of the caps (480 Cloudflare / 240 player).

## Screen approved (Brandon, 2026-10-22: "run the 24-row screen")
Ringer run `3c-families-offer-screen-n12`, manifest `scripts/ringer/stage7/3c-families-offer-n12.json`, caps 480 Cloudflare / 240 player, no retries or replacement rows.

## SCREEN STOPPED BY A HARNESS FAILURE (2026-10-22, `bench/results/stage7-3c-families-offer-screen/`, partial, 7 of 24 rows)
The harness stopped at row `stage7-3c-04-families-offer`, attempt 0, with `Blind player model call cap reached (1)` (run-failure.txt kept in place). Cause: `scripts/ringer/stage7/door_ask_player.mjs` calls `askPlayer` with `cap: 1`; `frontend/e2e/blind-player.js` retries once when the player's command fails its format check (imperative, ends with a period, 2 to 25 words, no waiting or restraint words), and the cap of 1 turns that retry into a thrown error that stops the whole run. The invalid command was not recorded. This is a player-format failure, not a game failure; the earlier smoke (13 player calls) did not hit it.
Completed rows, kept as recorded and not scored as a result: item-facts 01 earned (13 turns), 02 earned (13), 03 deadline, 04 deadline; families-offer 01 earned (14), 02 deadline, 03 deadline. 4 item-facts rows and 3 families-offer rows is not a decision basis.
Per this prereg a harness problem stops the screen and goes to Brandon; no retry, no top-up, no pooling of these 7 rows into any later run.

## Rerun approved (Brandon, 2026-10-22: "yes, raise the cap to 2 and rerun")
`door_ask_player.mjs` now passes `cap: 2` so the blind player's own format retry can run (Ringer run `door-ask-player-cap`, 3 hermetic tests: valid first reply, invalid then valid, two invalid still stop). This is a harness change that applies to both arms equally. A fresh 24-row screen runs into `bench/results/stage7-3c-families-offer-screen2/` with the same design and caps (480 Cloudflare / 240 player; a retried format check can make up to 2 model calls for one counted player request). The 7 rows of the stopped run stay in `bench/results/stage7-3c-families-offer-screen/` and are not pooled. Ringer run `3c-families-offer-n12-rerun`, manifest `scripts/ringer/stage7/3c-families-offer-n12-rerun.json`. Decision rule unchanged.

## SCREEN RESULT (2026-10-22, `bench/results/stage7-3c-families-offer-screen2/`, 24 rows, Ringer run `3c-families-offer-n12-rerun`)
Harness clean: 24 rows, 0 rejections, 0 clarifications, no first command, checker OK, 320 Cloudflare + 167 player requests (caps 480 / 240), no failed calls. (Ringer marked the task FAIL; its check script, not the run, was at fault, as in the earlier screens.) Read by hand: the command, K place, cue and commits of every turn of all 24 rows, plus the replies with a device or caller word.
Earned exits: `item-facts` 1/12 (row 07), `families-offer` 5/12 (rows 02, 04, 05, 07, 12). Four of the five offer exits commit E on turn 14 with no deadline event, as the harness classes it.
D2 commits (the cue's target): `item-facts` 3/12 (rows 04 t10, 07 t11, 11 t13), `families-offer` 9/12 (rows 01, 02, 04, 05, 07, 09, 10, 11, 12), 8 of them by turn 12 and 5 on turn 10 or 11 by the offered sentence's words ("Answer the families with news of the captives"). D1 commits are similar: 9/12 vs 8/12 (including late ones).
Rule: `families-offer` earned +4 over `item-facts` (needs +3) but 5/12 total is below the 10/12 total the rule asks for. Branch: it helps but is not enough; read the deadline rows for cause.
Deadline rows, what stopped them (offer arm): 01 D2 only (t10), no D1, then tunnel and "Look ahead"; 03 never D, corridor then tunnel and a metal door; 06 D1 only, tunnel loop turns 10-14 ("Continue through the tunnel to the surface/toward the light"); 08 no D, executive office and surface; 09 D2 t10, D1 t13, E cue staged only on t14; 10 D2 only, tunnel then "Open the large metal door"; 11 D1 and D2 by t12, E cue staged t13, player did not open the document on t13 or t14. Control deadline rows: tunnel loops of 4-6 turns in 01, 08, 10 (15 turns), 12; executive-office detours (asking Rebecca about escape) in 02, 06, 09, 11; 03 and 05 on the surface with Michelle questions.
Tunnel loop (3 or more consecutive tunnel-style turns): `item-facts` 4 rows (01, 08, 10, 12), `families-offer` 3 to 4 rows (03, 06, 10, partly 01). The loop persists in both arms; it did not block D2 in the offer arm, which committed D2 mostly before the loop began.
Device invention: a Kristin "phone" appears in replies in 7 offer rows (02, 05, 07, 09, 10, 11, 12) and 2 control rows (04, 07): "answers the phone", "takes out her phone and starts dialing a number", and the E delivery turn reads "opens it on her phone". Microphone mentions are the Michelle broadcast. Not scored as story-breaking, but it recurs and is more frequent in the offer arm.
Item-fact refusals: none unplaced; refused `item-facts` 8:1, 10:3, 12:1; offer 10:1. No false reveal seen.
Not covered: rates; the screen is triage. The exit counts are 1 vs 5 of 12 and differ by a few rows.

## ADOPTED (Brandon, 2026-10-22: "keep the cue change")
Shipped `handoffs.yaml` `community_rescue_efforts_begun` cue_text now carries the sentence (Ringer run `adopt-families-cue`, full suite 2956 passed / 15 skipped, ruff clean). The two experiment variations were reversed so they still load as the pre-adoption package. Not yet verified: the `--cov` gate, frontend/build gates, hosted behaviour. Still open: the tunnel loop, the late E turn, and the invented phone (below).

## PHONE INVENTION CHECK (2026-10-22, same 24 rows)
Standalone "phone" (microphone excluded) in replies: `families-offer` 7 rows (02, 05, 07, 09, 10, 11, 12), `item-facts` 2 rows (04, 07). Two situations: (a) after "Open the recovered document." (E): offer rows 02, 05, 07, 12, control row 07, "pulls out her phone and opens the recovered document" or "opens it on her phone"; (b) after answering the families: offer rows 07, 09, 10, 11, control 04, 07, "answers the phone", "takes out her phone and starts dialing a number", "who's busy on her phone".
Origin: none of the ~160 saved narrator prompts contains the word "phone". The only phone in the package is Michelle's phone in scene 1A (`world.yaml:149`, 1A aliases). No recovered-document thing and no communications device is declared in 3C, so the narrator supplies a device from its own habit when a command needs one (open a file; talk to a caller). No unplaced or refused item fact came from it and no false reveal. Frequency is higher in the offer arm because more rows reach D2 and E, the two moments that call for a device, not because the sentence names one (the sentence does not).
No fix is chosen. Any fix that declares a device or document is a package/plot addition for ChatGPT, not for me.
