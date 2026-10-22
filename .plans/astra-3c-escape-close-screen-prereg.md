# Preregistration: Stage 7 Scene 3C escape-close screen (approved 2026-10-22 by Brandon: code task, smoke, 3-row rule kept)

Written 2026-10-22 before any billed run. Brandon approved the arm, the smoke and the decision rule on 2026-10-22; he said the Cloudflare and player budgets are well within limits and need no recorded figures. The 24-row screen needs his go-ahead after the smoke is read.
Follows the deadline-row reading in `.plans/astra-3c-relay-access-prereg.md` (two `deadline_complete` rows) and plan step 5/6 of `.plans/game-path-completion-plan.md`.

## Question
Does the shipped scene 3C escape close (`resolution_escape` `delivery_text`: evacuation done, Brandon over the emergency speakers, barrier holds the route) change how often a blind free-text player leaves 3C by an earned transition, compared with the same package without it?

## Why the earlier rows cannot answer it
Both earlier rows used a scripted first command ("Follow Michelle and the captives through the surface gates.") that re-requests a passage the synthetic prefix had already completed. In both rows the narrator re-narrated the gates opening. In the item-facts row Michelle then said "We have to get them to safety" and the player spent five turns on the tunnel (the original loop shape). A real player is not given that command after being told the captives emerged. This screen drops it: `--first-command` is omitted, so the raw blind player chooses its own first command from the full prefix transcript, escape text included.

## Arms (one variable)
- `item-facts`: shipped package, product place capture (`WorldCapture` with the item-facts provider, as in the 2026-10-22 product-capture row).
- `no-close`: identical except the `resolution_escape` `delivery_text` line is removed by a variation override. Built by Ringer run `3c-no-close-arm` (manifest `scripts/ringer/stage7/3c-no-close-arm.json`, lint clean, not yet run). Known residual difference: `emergency_speakers` and `watertight_barrier` stay declared in world.yaml for both arms; with no delivery text nothing in the no-close prompt introduces them.

## Free checks (before any billed call)
1. `3c-no-close-arm` passes: the variation differs from shipped in exactly the one `delivery_text` line; existing arms' dry artifacts byte-identical; 24-row dry plan, no first command, caps unchanged.
2. Full suite and ruff green after applying its patch.

## Billed design (two separate Ringer tasks, no retries, no replacement rows, no top-ups)
Start: labelled synthetic post-C start, Kristin at `facility_escape` (surface), so the escape text lands where the original loop happened. Raw blind player, semantic fallback ON, product capture ON, at most 10 attempts per row.
1. **Smoke:** `--n 1 --arms item-facts,no-close` (2 rows, caps 80 Cloudflare / 40 player). Proceed only if the harness is clean (no rejected-for-harness reasons, both arms run, artifacts pass the checker, no first command recorded). Stop and ask Brandon on any harness problem.
2. **Screen:** `--n 12 --arms item-facts,no-close`, 12 rows per arm alternating, existing `POSTC_CAPS[12]` = 480 Cloudflare / 240 player for all 24 rows. Expected use from the 2026-10-22 rows is about 15 Cloudflare (7 narration, 8 Jev capture) and 7 player requests per row, so about 360 / 170, inside the caps. Jev calls count against the Cloudflare cap.

Command shape (smoke shown; screen differs only in `--n 12` and `--out`):
`.venv/bin/python scripts/ringer/stage7/three_c_probe.py --n 1 --mode play --start postc --kristin-place facility_escape --arms item-facts,no-close --capture-item-facts --semantic on --confirm --out bench/results/stage7-3c-escape-close-smoke`

Before the billed run record here: Cloudflare dashboard daily cap, dollar usage and UTC timestamp, and the player-model budget (the default $5 daily cap is shared with staging traffic and is not headroom). Stop on `AI_DAILY_BUDGET_EXCEEDED`; keep partial evidence; do not raise the cap or retry around it.
Cap / usage record: not recorded; Brandon (2026-10-22) said usage is well within limits.

## Measures
Per row, from `rows.json`: `outcome` (`earned_complete`, `deadline_complete`, other), `accepted_turns`, `attempts`, committed reveal ids and their scene turns, `deadline_event_ids`, `kristin_parent` per turn, rejections, clarifications. A row counts as earned only if D and E commit before the deadline event fires. A D commit on the same turn the deadline fires is `deadline_complete`, as in the item-facts row.
Loop marker: three or more consecutive accepted turns whose commands re-request the evacuation, tunnel or gates after the escape text.

## Read by hand, every turn of every row, in full
- Does the player's first command respond to the escape text, or re-request the finished passage?
- Does the narrator treat the evacuation as done after the escape text (item-facts) and what does it do without it (no-close)?
- Where is Kristin when the D1/D2 cues are appended, and does the player act on them?
- Does any reply invent a device or place (the earlier row invented a phone) or place anything at the speakers or barrier?
- Does "return to the chamber" succeed, and does `kristin_parent` follow it?
- Does a reply deliver "families of the missing" content when the player listens to calls (D2 meaning), or only a generic call?
- Any false reveal, unplaced item fact or wrong match-call resolution.
Preserve malformed, rejected and partial rows. No pooling with the earlier single rows.

## Decision rule (triage only, not a population rate)
Twelve rows per arm can choose a candidate; they cannot establish a success rate, and the historical 10/12 screen is not an 80% claim. Seven free turns after a synthetic prefix is a short window, so a deadline row is read for cause, not counted as a failure of the whole scene.
- If `item-facts` earns at least 3 more exits than `no-close` with no new grounding failure: the close helps; keep it and move to plan step 5's next hypothesis.
- If the arms differ by 2 or fewer: the close is not shown to matter. The cause is elsewhere (cue placement or a passage that never reads finished); choose the next change only from a reproduced mismatch in these rows.
- If `no-close` earns more: read why before touching anything; the close may be inviting the player back into the evacuation.
Report counts per arm and quote every deadline row's looping turns.

## Not covered
Whole-game quality, a fresh-entry 3C, hosted deadline telemetry, the D2 "families" meaning if it never appears, and any claim about rates.
