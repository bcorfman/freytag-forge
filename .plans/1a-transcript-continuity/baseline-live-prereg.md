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
