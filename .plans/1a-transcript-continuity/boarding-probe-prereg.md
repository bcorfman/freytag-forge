# Preregistration: Scene 1A boarding narration probe (DRAFT, not approved)

Written 2026-10-24 before any billed run. Brandon has not approved this document. Nothing billed runs until he does.
Source: Brandon's question on 2026-10-24 ("aren't there other successful cases of items in the scene being narrated consistently instead of having to do pure engine text?"). Method: scene-fixing guide step 2 (replay prompts, one arm per likely cause, 10 samples per arm, read every narration).

## Question
When the engine seats the player in the truck, can the narrator be made to narrate what the engine knows (she sits in the driver's seat and her laptop is on the passenger seat) consistently, without replacing the turn with engine-only text?

## Evidence that motivates it (all from this branch's recorded live runs)
- Placed items listed with a place are narrated: 9 of 9 in-house "look around" turns named a placed house item (phone, chair, workstation, drawer).
- The boarding notice is not: of 10 boarding turns where the engine produced "Kristin's laptop sat on the passenger seat.", the player-visible narration mentioned the laptop in 0. The step reaches the narrator only as a background line ("Just before this: ...").
- Before the post-fix changes the baseline narrator contradicted the engine's seating in 5 of 5 runs ("she gets out of the driver's seat"). Since then the raw boarding command is dropped from the prompt (7a), and the one post-7a live sample ("go out to the truck") no longer contradicts, but still did not mention the laptop.
So the cause under test is the notice's role in the prompt: a background line the narrator is not asked to show.

## Checked first (supported techniques only)
Narrator-writing guide (plain words, 12th-grade, one idea per sentence; apply a winning rule to every narration path), scene-fixing guide (fix the material first, rules last; most tried rules lost), memory "prefer subtractive fixes over prompt constraints" and "deterministic authored text over LLM generation" (the fallback), grounding guide (notice_text is the supported way to surface what is in a vehicle).

## Prompts (built offline, free, from the head of the branch after step 7b)
Three narrator prompts built with the product-wired provider and a stubbed network and stubbed Jev (boards: true, only_boards: true), so the control is exactly what the current code sends:
1. "Go out to the truck." from `outside_house`, nothing else changed.
2. "Get in." from `outside_house` (contextual boarding).
3. "Go out to the truck." from the kitchen (a house-to-truck boarding).
Each contains the real SCENE, THINGS, PLAYER and CONSTRAINTS of that state. A Ringer task builds them (`scripts/ringer/transcript_1a/boarding_probe.py --dry` writes the three prompts and the diff of each arm against control).

## Arms (a minimal edit to the user text; system text identical in every arm)
- **0 control:** as built.
- **1 steps as the action:** the `Just before this: <steps>` line is removed and the same steps become the final PLAYER line, the thing to narrate (no label). Nothing else changes.
- **2 steps plus a rule:** control, plus one CONSTRAINTS line: `Show every thing named in the Just before this line.` (12th-grade reading level, one idea.)

## Design
10 samples per arm per prompt, interleaved, one narrator call each: 3 arms x 3 prompts x 10 = 90 calls, cap 100. No Jev or item-facts calls. One Ringer task (Luna, high effort for the build; the billed run is a runner task), `--dry` first, a 2-sample smoke, no retries, no replacement samples, partial rows kept. Stop on 429 `AI_QUOTA_EXCEEDED` or `AI_DAILY_BUDGET_EXCEEDED`.

## Scoring (every reply read by hand, narration only)
A reply passes when all three hold:
- (a) it shows the laptop on the passenger seat (any wording that puts it there and in the cab);
- (b) it keeps her seated (it does not say she gets out, leaves, walks away, or starts driving);
- (c) it invents no new object or place (a car, a bag, a passenger).
Unusable replies (not valid narration) count as failures.

## Decision rule (triage only)
An arm advances when it passes at least 8 of 10 on at least 2 of the 3 prompts, and beats control by at least 3 passes on average across prompts. If both arms advance, prefer arm 1 (it adds no rule). A winning arm proceeds to one product-wired live check inside the main verification run, never straight to adoption; a winning rule is applied to every narration path per the writing guide. If neither arm advances, the fallback is engine-authored text for a boarding-only turn (the steps shown verbatim, no narrator call), which needs Brandon's separate approval because it changes how boarding reads.

## Not covered
Other vehicles, other in-cab items, hosted staging, narration after the first boarding turn, and whether the laptop is mentioned on later turns (a separate question: the place-scoped feed lists it).
