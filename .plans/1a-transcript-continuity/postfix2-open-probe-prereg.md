# Preregistration: Scene 1A narrator probe for the open postfix2 model-behavior defects (DRAFT, not approved)

Written 2026-10-25 before any billed run. Brandon has not approved this document. Nothing billed runs until he does.
Source: the postfix2 live result in `1a-transcript-continuity-plan.md` (Step 8) and the rows in `bench/results/transcript-1a-postfix2-{reported,witnessed,movement}/rows.json`. Method: scene-fixing guide step 2 (replay recorded prompts, one arm per likely cause, 10 samples per arm, read every narration). Control for every problem is the prompt exactly as recorded.

## Questions
Three narrator defects remain after the deterministic fixes (`fa3c837d`, `ea6b6a5a`). Each has its own recorded prompt, so each is a separate problem with its own arms. They are never pooled.

- **P1 Card re-find.** After the card is already taken, "feel under the drawer" narrates finding a memory card again (5 of 5 on route A, turn 5).
- **P2 Wait in the house.** "wait" in the house describes "the living room" or "in front of the house", and in 2 of 3 witnessed replicates it moved her outside (route C, turn 2, the first "wait").
- **P3 Invented paper.** "look around" outside invents "a piece of paper on the ground near the gate" (3 of the 9 outside or seated looks on route D: replicate 1 turn 6, replicate 2 turns 5 and 6).

## What the recorded prompts show (read, not inferred)
- **P1.** THINGS already says "Michelle's memory card. Held by: Kristin." The same prompt still carries the committed statement under CONSTRAINTS: "Michelle may say this aloud: Kristin finds Michelle's memory card taped beneath the drawer and pockets it." So the narrator is told both that she holds the card and, as speakable fact, that she is finding it.
- **P2.** The house prompt has no line saying where she is. The outside prompt opens SCENE with "Kristin is outside the house." The house prompt does not have a matching line, THINGS holds only "Kristin. Place: Michelle's house." and no house objects, and the situation text names no room. "Michelle's house" can mean the building seen from the street.
- **P3.** The outside prompt describes only a low gate, the curb, the truck and distant sirens. A "look around" with nothing more to see leaves the narrator to fill the view.

## Prompts (built offline, free, from the head of the branch)
A Ringer task builds them with the product-wired provider, a stubbed network and Jev stubbed to the recorded answers, by replaying the recorded inputs of each route:
1. P1: route A through "feel under the drawer" (card already taken).
2. P2: route C replicate 0 through "wait" at turn 2 (in the house, before the patrol).
3. P3: route D replicate 1 through the outside "look around" at turn 6 (after a truck visit).
`scripts/ringer/transcript_1a/open_probe.py --dry` writes the three prompts and the diff of each arm against control. The only differences between arms are the edits below. System text is identical in every arm.

## Arms
- **P1:** `0 control`; `1 drop`: the card statement line is removed from CONSTRAINTS once `memory_card_recovered` is true (subtractive, per the memory on subtractive fixes); `2 past`: the line is kept and reads "Kristin already took Michelle's memory card from beneath the drawer."
- **P2:** `0 control`; `1 where`: SCENE gains "Kristin is inside the house." as its first bullet, matching the outside prompt's "Kristin is outside the house."; `2 place`: THINGS reads "Kristin. Place: inside Michelle's house." and nothing else changes.
- **P3:** `0 control`; `1 view`: the authored area text gains a concrete view: "From the curb she can see the gate, the front of the house, the truck, the street, and the lights on the next street." (written as the interactive-fiction author; one idea per sentence, 12th-grade level); `2 rule`: control plus one CONSTRAINTS line, "Describe only the things in THINGS and SCENE." (the rule arm is here because rules often lose per the scene-fixing guide, so it is the arm to beat or fail).

## Design
10 samples per arm, interleaved, one narrator call each: 3 problems x 3 arms x 10 = 90 calls, cap 100. No Jev or capture calls beyond what the single-call narrator reply already returns. One Ringer task builds the harness (Luna, high effort, hermetic test, `--dry`), then a 2-sample smoke per problem, then the run as a `probe` runner task. No retries, no replacement samples, partial rows kept. Stop on 429 `AI_QUOTA_EXCEEDED` or `AI_DAILY_BUDGET_EXCEEDED`. Engine: the same Cloudflare narrator model the live runs used.

## Scoring (every reply read by hand: narration, then the returned `item_facts`)
A reply passes when all hold:
- **P1:** (a) it does not narrate finding, peeling or taking a memory card or any hidden object; (b) it invents no other object under the drawer; (c) item_facts do not move the card.
- **P2:** (a) it names no room that THINGS or SCENE does not give (no "living room"); (b) it puts her neither outside nor in front of the house; (c) item_facts leave her place unchanged.
- **P3:** (a) it names no object that THINGS or SCENE does not give (no paper, note, bag); (b) it keeps her outside; (c) item_facts leave her place unchanged.
Unusable replies (not valid narration) count as failures.

## Decision rule (triage only, n=10)
An arm is a candidate fix when it passes at least 9 of 10 and the control passes at most 5 of 10. Candidates are then written into the material or code, run through the failing route live (see below), and not accepted on this probe alone. If two arms qualify, the subtractive or data arm wins over the rule arm. If no arm qualifies, nothing ships for that problem and the defect stays open. A 0/10 failure count is "not reproduced at n", not a rate.

## After the probe
A winning arm is built through Ringer (tests first), then the failing route is rerun live at its postfix2 sample size (A n=5, C n=3, D n=3, about 250 calls) in a second preregistration for Brandon's approval. No fix is reported corrected from this probe alone.

## Not covered
The route C 502 `INVALID_PROPOSAL` (one malformed reply in 145 turns; no cause under test); the laptop `held_by` echo and the stale drawer cue (fixed deterministically, to be seen in the rerun); hosted staging; other scenes.

## Budget
About 90 narrator calls (cap 100), plus 6 smoke calls.
