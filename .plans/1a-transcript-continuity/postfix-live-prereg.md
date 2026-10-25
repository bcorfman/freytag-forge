# Preregistration: Scene 1A post-fix live replicates (DRAFT, not approved)

Written 2026-10-24 before any billed run. Brandon has not approved this document. Nothing billed runs until he does.
Source: `.plans/1a-transcript-continuity-plan.md`, acceptance section. Control: `baseline-live-prereg.md` result (5 replicates, 40 turns, code `ae0d7a34`).

## Question
With steps 2 to 5a applied (head of branch `fix-1a-transcript-continuity`), does the real Cloudflare narrator, driven by the product wiring, satisfy the four user-facing requirements on the corrected route, and how does the reported raw-language route now behave?

## What changed since the baseline (the arms differ by these, nothing else)
Back door text; card delivery and statement; drawer pointers retire after recovery; reveals gated by reach to the drawer; fact-driven patrol timeline with a placed officer; witnessed card recovery (officer challenge, two facts, 1B consequence); boarding means getting in, not approaching, plus contextual "get in"; a cue shown last turn makes "the gap" refer to the drawer; opening sentence "She found the back door forced and let herself in."

## Design (two Ringer tasks, no retries, no replacement samples, no pooling)
Harness: `scripts/ringer/transcript_1a/live_baseline.py` (product wiring, call cap, quota stop), extended only by a `--inputs` option that selects an input script (a Ringer task adds it, with a hermetic test).
- **Route A, the reported raw route (regression arm), 5 replicates x 8 turns:** the baseline's eight inputs, unchanged, so each count compares with the baseline's counts. Expected calls about 150 (baseline 145 plus contextual boarding questions).
- **Route B, the corrected route (acceptance arm), 3 replicates x 12 turns, three complete live replicates as the plan requires:** go in the house / pull out the drawer / feel in the gap / look around / wait / wait / go out to the truck / get in / look around / get out of the truck / look around / wait. The order puts the card search before the turn-4 patrol arrival so recovery is unobserved. Expected calls about 130.
- **Route C, the observed-recovery branch, 3 replicates x 11 turns:** go in the house / examine the carved initials / wait / wait / wait / feel under the drawer / say what the card is to the officer / wait / go out to the truck / get in / look around. The patrol officer enters the house after scene turn 5 completes, so the card is taken at input 6 with the officer inside. Expected calls about 120.
  *Amended 2026-10-24 before any billed run, after a free dry run: the first draft took the card at input 5 with a bare "feel in the gap", which would have been unwitnessed (the officer is not yet inside) and whose one-turn gap referent would have expired. Brandon approved the design; this corrects the input script only.*
- Free first: `--dry-run` of each route; one 2-turn smoke per route.
- Cap per task 200 Cloudflare calls (route B and C together about 250 expected, so each is its own task with its own 200 cap). Total expected 390 to 420 calls, cap 600.
- No LLM judge. Every narration is read by hand, narration plus appended delivery text, never `item_facts`.

## Engine
GPT-5.6 Luna, high effort, as for the build tasks (Brandon asked for high on 2026-10-24). One task per route; no exploration lane.

## Read by hand, per requirement, per replicate
1. Gap: any door or frame gap, seam or fabric; any invented object at the drawer; "feel in the gap" after the staged cue reaches the card; "look at the fabric" (route A only) is not accepted as a real object.
2. Patrol: no officer appears or "returns" before the arrival text; the arrival, entry and leaving texts appear once each at scene turns 4, 5, 7; on route C the challenge text appears on the recovery turn and the next turn answers it (the officer is not forgotten, the card stays with Kristin, the player's reply is not auto-resolved).
3. Truck: "go out to the truck" leaves Kristin beside it (committed place outside, no driver's-seat step); "get in" seats her and the laptop notice appears exactly once; the laptop is on the passenger seat; card recovery text does not imply she has travelled or read files.
4. Observation: "look around" outside describes the exterior; seated describes the cab; neither places Kristin in the house or moves her; committed place unchanged across the look.

## Decision rule
Acceptance (plan): all three route-B replicates and all three route-C replicates satisfy every requirement that route exercises, in final prose and committed state; any failure keeps that requirement open and is reported per case, not pooled. Route A is descriptive (counts out of 5 beside the baseline). A requirement passing 3/3 is "not reproduced at n=3", not proof of a rate.

## Stop conditions
HTTP 429 with `AI_QUOTA_EXCEEDED` or `AI_DAILY_BUDGET_EXCEEDED`: stop, keep partials. Anything else: no retry; partial rows stay.

## Not covered
Hosted staging behavior (a separate gate after merge), other scenes, rates beyond n=3 to 5, the three-way response to the challenge as an engine outcome (free text only), step 5's observation scoping if routes show the cab or exterior still described from the house (that would open a probe arm per the scene-fixing guide).

## APPROVED (Brandon, 2026-10-24: "I approve the post-fix prereg")
Gate before spending: full suite 2590 passed, 92.55% coverage (bar 90%), ruff clean, at the commit that precedes this note. Luna at high effort. Ringer run `transcript-1a-postfix`.
