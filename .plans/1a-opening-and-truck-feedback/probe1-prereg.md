# Preregistration: 1A opening and truck feedback, probe 1 (baseline of three causes)

Written 2026-11-02 before any billed run. Brandon approved the probe in principle on 2026-11-02 ("yes to both"); this document fixes its design. Plan: `.plans/1a-opening-and-truck-feedback-plan.md` step 1. Method: scene-fixing guide step 2 (replay the shipped prompts, one arm per supported cause, read every reply). Fixes must be general (Brandon, 2026-11-02): the commands below are samples of a class, not the thing being fixed.

## Questions
- **Q1 Boarding classifier.** Does the live boarding question answer "boards" for movement-toward-a-vehicle phrasings the player means as getting in ("head out to", "go out to", "go to", "get in"), for more than one vehicle name? Free capture showed that a "no" leaves the narrator with the bare command and no truck location (cause A), and that the question text contradicts itself.
- **Q2 Boarding turn prose.** When boarding is committed (seated, truck parked), does the narrator keep her seated and parked, show the laptop, and ground the surroundings? Free capture showed the PLAYER block still carries the raw movement phrase beside "Already done: Kristin sat down in the driver's seat." (cause B). Arm 1 removes the raw phrase.
- **Q3 Opening baseline.** What does the shipped opening write when Kristin starts at house level with no layout lines? (Baseline for plan step 2, not a test of a fix.)

## Design (all calls through the shipped transports; no retries, no replacement samples, partial rows kept)
**Part 1 (Q1), live Jev, 40 calls.** `boards_vehicle` for 8 phrasings x 2 vehicle names (`Kristin's truck`, `the van`), 2 samples each = 32 calls. Phrasings use a `{v}` slot: `head out to {v}`, `go out to {v}`, `go to {v}`, `get in {v}`, `climb into {v}`, `walk up to {v}` (contract: not boarding), `look at {v}` (not boarding), `get out of {v}` (not boarding). Plus `only_boards_vehicle` for the first four phrasings on the truck only, 2 samples each = 8 calls. Vehicle names are slotted in; nothing is specific to the 1A commands.

**Part 2 (Q2), live narrator, 24 calls.** Build the control prompt offline with the product-wired provider (WorldCapture attached, Jev scripted to boards yes / only-boards yes, network stubbed) for `head out to the truck` from the 1A kitchen state after the card is held. Arm 0 control: the prompt as built. Arm 1: the same prompt with the raw command line removed from the PLAYER block (the "Already done:" line and the protagonist place line stay). System text is identical. 12 samples per arm, interleaved.

**Part 3 (Q3), live narrator, 10 calls.** The shipped 1A opening prompt as built offline (system and user), 10 samples.

Total 74 calls, hard cap 85. Smoke first: 3 Jev calls, 1 Part 2 call, 1 Part 3 call (5 calls), read, then the full run. Stop on 429 `AI_QUOTA_EXCEEDED` or `AI_DAILY_BUDGET_EXCEEDED`.

## Scoring (every row read by hand; Part 1 is mechanical)
**Part 1:** per phrasing and vehicle, the share of yes answers; unanswered counts as no. Contract expectation: yes for the first five phrasings, no for the last three. A mismatch is a finding, reported per phrasing, never pooled.

**Part 2 reply passes when all hold:** (a) she stays seated in a parked truck: no engine start, driving, gate crossing, return to the house or getting out; (b) the laptop is shown on the passenger seat; (c) at least one surrounding from the SCENE is grounded (house, gate, curb, sirens, cab); (d) no new object, person or place is invented. Report (a) to (d) separately and together. Unusable replies fail.

**Part 3 reply is scored on separate yes/no items:** names the kitchen; makes the immediate layout understandable using only declared things; a specific reaction to Michelle's absence or the damage; KMS treated as new and strange; hidden card not revealed and no search done for the player; no invented object, clue or person.

## Decision rule (triage only, nothing adopted from this probe)
- Cause A is supported if the "boards" phrasings answer no or unanswered in at least 30% of samples for any vehicle, in any of the first four phrasings.
- Cause B is supported if arm 0 fails (a) in at least 3 of 12 and arm 1 fails (a) in at most 1 of 12.
- If neither holds, the cause is not in these two places; the plan goes back to the saved live transcript and the recorded prompts before any edit.
- Part 3 only sets the baseline for step 2.
Any winning idea becomes a tested change, a product-wired live check and three live replicates in the plan's later steps.

## Not covered
Later turns after boarding, the card and laptop interpretation turn, the patrol, hosted staging, other models, and writing the fix.

## Result (2026-11-02, base `8da80120` on branch `1a-opening-and-truck-feedback`; 74 calls, 74 usable, no quota stop; plus a 5-call smoke)

Rows: `bench/results/1a-opening-and-truck/probe1.json` (smoke: `probe1-smoke.json`). Every Part 2 and Part 3 reply was read by hand. Harness: `scripts/ringer/opening_truck/probe.py`.

**Part 1 (boarding question; yes means a score above 0.5). Scores repeated almost exactly across the two samples.**

| Phrasing | Kristin's truck | the van |
| --- | --- | --- |
| get in / climb into | 0.96 yes | 0.96 yes |
| go to | 0.63 yes | 0.69 yes |
| head out to | 0.55, 0.57 yes (margin 0.05) | 0.67 yes |
| **go out to** | **0.44, 0.47 NO (2 of 2)** | 0.60 yes |
| walk up to / look at / get out of | 0.18 / 0.05 / 0.03 no (contract) | same |

`only_boards_vehicle` was yes for all four phrasings (0.78 to 0.96). Cause A rule met: "go out to the truck" answers no in 2 of 2 samples. "Head out to the truck" boards, but by 0.05. The same words flip with the vehicle name, so the question is knife-edge on "out to" phrasings.

**Part 2 (boarding turn, 12 per arm).**

| Criterion | Control | Arm 1 (raw command line removed) |
| --- | --- | --- |
| (a) stays seated and parked | **0 / 12** (12 of 12 "opens the door and steps out of the truck"; 4 also walk toward the gate) | 7 / 12 (5 get out and "walk around to the passenger side"; one also opens and turns on the laptop) |
| (b) laptop shown on the passenger seat | 0 / 12 | 12 / 12 |
| (c) surroundings from the scene grounded | 7 / 12, but all from outside the truck | 0 / 12 beyond the laptop and seat |
| (d) nothing invented | 12 / 12 on objects; 4 invent a walk toward the gate | 7 / 12; 7 invent thoughts ("wonders if she should check her email") and 5 invent walking around |
| all four | 0 / 12 | 0 / 12 (best case 7 pass a and b) |

Cause B rule (control fails (a) in at least 3 and arm 1 in at most 1): control 12 of 12 is met, arm 1 at 5 of 12 is not met. Removing the raw phrase cuts exits from 12 to 5 but does not fix the turn. All 5 remaining exits walk to the passenger side, pairing the exit with the laptop on that seat; that link is a lead, not tested.

**Part 3 (opening baseline, 10 replies).** Kitchen named 0/10; layout understandable 0/10 (all say "the room" or "inside"); specific reaction to Michelle's absence 0/10 (all call out her name, 3 add a generic tone); KMS drawn as new or strange 0/10 (8 mention carved initials as a flat fact); hidden card revealed 0/10; reword the entry text's arrival ("steps into the house") 10/10; acts for the player ("moves towards the workstation") 10/10; one invents "dim light".

**Conclusions (decision rules applied, nothing adopted).**
1. The control turn contradicts the committed state in 12 of 12. This is the user's "she drives" report in its smaller form: the narrator reads "head out" as leaving.
2. Cause B is a major contributor but not the whole cause. Cause A makes it fragile. A later round tests only generic, story-name-free changes and replays the same check.
3. The opening lacks layout and personal significance by construction (confirmed in the free capture) and acts for the player.
