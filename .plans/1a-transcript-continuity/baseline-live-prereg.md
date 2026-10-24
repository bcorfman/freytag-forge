# Preregistration: Scene 1A transcript live baseline (DRAFT, not approved)

Written 2026-10-24 before any billed run. Brandon has not approved this document. Nothing billed runs until he does.
Source: `.plans/1a-transcript-continuity-plan.md`, step 1 (live part). Free part: `baseline-stubbed.json`, committed `3a741ac6`.

## Question
When the shipped package at SHA `3a741ac6` (code `206de861`) answers the eight reported raw inputs through the real Cloudflare narrator, how often does each of the four requirements fail, and where?

## Design (one Ringer task, no retries, no replacement samples, no pooling)
- Script: `.plans/1a-transcript-continuity/baseline_replay.py` adapted to the live provider (stub removed, world capture on as in product: `FREYTAG_WORLD_CAPTURE=1`, semantic reveal and boarding ask on). Inputs, in order: go in the house / feel in the gap / look at the fabric / pull out the drawer / feel under the drawer / go out to the truck / get in / look around.
- 5 independent replicates from a fresh bootstrap state, 8 turns each = 40 turns. The fabric command is a historical regression input only.
- Free first: `--dry-run` of the harness must reproduce `baseline-stubbed.json` prompts byte for byte, and one smoke replicate of the first two turns before the full run (smoke-test rule).
- Per turn record: pre/post parents of Kristin, laptop and card; custody; fired events; reference matches; engine steps; every prompt; provider response; composed narration including appended delivery text; `item_facts_unplaced`; model and package identity; code SHA.

## Cap and cost
- Cap 200 Cloudflare calls (5 x 8 x up to 5 calls: narration, one recovery, up to two item-facts, one boarding ask). Expected about 100 to 120.
- Neurons at the 30-turn canon rate come to roughly 450 for 40 turns, plus Jev calls on AI Gateway credit. No OpenAI judge calls; no LLM judge at all, because every narration is read by hand.
- Stop on 429 `AI_QUOTA_EXCEEDED` or `AI_DAILY_BUDGET_EXCEEDED` and keep the partial artifacts.

## Engine (Ringer worker that types and runs the script)
Recommended: GPT-5.6 Luna, effort unspecified. Local scoreboard: 537 tasks, 89% first-try, median 4.8k tokens. Terra is 79% over 19 tasks at about 8 times the tokens. Brandon picks; no exploration lane in a single-task run.

## Read by hand, every narration in full
Per requirement, per replicate, per turn:
1. Gap: any gap, seam or fabric between a door and its frame; whether "the gap" after the pointer reaches the drawer.
2. Patrol: any officer appearing or returning with no arrival shown earlier.
3. Truck: laptop's stated location on entering; any suggestion that Kristin has gone to the truck or read its files at card recovery.
4. Observation: whether "look around" outside describes the exterior, seated describes the cab, and whether either places Kristin in the house or moves her.
Narration only, not `item_facts`, which can report moves the prose did not make.

## Decision rule
No pass or fail threshold: this run measures. Report counts per requirement per turn out of 5 and the list of committed-state mismatches. A requirement with 0/5 failures is recorded as "not reproduced at n=5", not as fixed. These counts set the control arm for the step 2 to 5 probes.

## Not covered
Fix effectiveness, other scenes, hosted behavior, rates beyond n=5.

## APPROVED (Brandon, 2026-10-24: "1. yes; 2. yes; 3. ok")
Luna worker. Smoke: Ringer run `transcript-1a-baseline-smoke` (1 replicate, 2 turns, 8 calls). Full: Ringer run `transcript-1a-baseline-live`, manifest `scripts/ringer/transcript_1a/baseline-live.json`. Calls were estimated at 100 to 120 and came to 145 (cap 200), because each turn makes about 3 to 4 calls.

## RESULT (2026-10-24, git `ae0d7a34`, 5 replicates, 40 turns, 145 calls, 0 errors, no quota stop)
Raw rows: `bench/results/transcript-1a-baseline/` (ignored by git). Compact fixture of every narration: `baseline-live-narrations.json`. Read by hand, narration only. Counts are out of 5; a count is a failure of the requirement at that turn, not a rate.

**1 Gap/fabric (fails 5/5).**
- “Feel in the gap” was read as a door-frame gap in 5/5 (“between the back door and the frame”, “between the door frame and the wall”). 5/5 invented an object there: torn fabric 2 (replicates 1, 4), key fragment 1 (2), screw 2 (3, 5).
- “Look at the fabric” was accepted as real in 5/5 (fabric examined, or entry scratches described).
- No reveal on “feel in the gap” in 5/5; the gap never reached the drawer (0/5).
- Later “look around” repeated the door gap in 2/5 (torn fabric in replicate 1, key in the gap in replicate 2).
- `item_facts_unplaced` held the invented object in 4/5 (fabric in 1, key in 2, screw in 3 and 5; replicate 4's fabric was not recorded as unplaced), plus a door handle in replicate 3.

**2 Patrol (fails 5/5).**
- Turn 4 (“pull out the drawer”) narrated an officer who “lingers at the drawer” (replicates 1 to 3) or “lingers nearby” (4, 5) with no arrival shown; replicate 3 adds the officer saying “I'll be right back”.
- At card recovery the officer is in the narrated room in 5/5 and has no consequence: nobody reacts to the card (0/5 visible, 0/5 committed).

**3 Truck and laptop (fails 5/5 on the sequence).**
- The delivery text ends “Her laptop is in her truck outside” in 5/5. Kristin's committed place stays the house in 5/5, so no replicate moved her at card recovery.
- “Go out to the truck”: the engine seated her (“Kristin sat down in the driver's seat. Kristin's laptop sat on the passenger seat.”) in 5/5, and the narration contradicted it in 5/5 (“gets out of the driver's seat”, “gets out of the truck”; replicate 2 also had her open the laptop). Committed place after that turn: outside_house 4, kristin_truck 1.
- “Get in” (no vehicle named): no step, no laptop notice in 5/5. Prose and place: correct in 1/5 (replicate 1, `truck_driver_seat`). Wrong in 4/5: into the kitchen (2), to the house (3), toward the front door (4, 5).
- The laptop moved to Kristin (“opens the laptop”) in replicate 2 before she was in the truck.

**4 Observation (fails 3/5 outright).**
- Seated, “look around” described the house and the door gap (replicate 1). Standing in the kitchen after “get in” (replicate 2) and at the house (3) both described the house.
- Outside (4, 5) the narration was the exterior, but mostly the `home_search_narrows_1a` patrol line, not the view from where she stood.
- No “look around” moved her (0/5). The wrong places came from “get in”.

**Other.** The opening already narrates Kristin inside the house in 4/5, while she is committed to `mcgehee_home` in 5/5, so “go in the house” repeats the entry. Replicate 3 opened outside and walked in.

**Causes this supports, not proves.** Gap: scene situation “back door frame shows recent damage” plus no “gap” referent and no “feel” verb. Patrol: the unconditional turn-4 realization. Truck: the card delivery, “get in” naming no vehicle, and the narrator contradicting the engine's boarding step. Observation: no seat or area in the narration. All of this is the control arm for steps 2 to 5 probes.
