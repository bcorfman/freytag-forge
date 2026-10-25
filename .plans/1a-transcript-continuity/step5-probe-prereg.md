# Preregistration: Scene 1A observation, referent and boarding probes (DRAFT, not approved)

Written 2026-10-24 before any billed run. Brandon has not approved this document. Nothing billed runs until he does.
Source: `postfix-live-prereg.md` result and the plan's step 5. Method: scene-fixing guide step 2 (replay recorded prompts, one arm per likely cause, 10 to 15 samples per arm, read every narration).

## Checked first (supported techniques only)
`docs/world-model-grounding.md` (a scene `situation` must not state where a character is; the starting position is given in `entry_text`; tracked facts carry the place), the narrator-writing guide (12th-grade rules, plain words, apply a winning rule to every path), scene-fixing guide (most tried rules lost; fix the source material first, rules last), memory "bound LLM context by relevance" and "prefer subtractive fixes over prompt constraints". Earlier scene fixes: 2C stale 1A recall removed; 3A captives talk line scoped. So: arms 1 to 3 below are subtractive or scoping fixes; the narrator rule (arm 4) goes last.

## P1 Requirement 4: "look around" outside and seated (the open requirement)
Recorded prompts: the three seated "look around" narration prompts of route B (replicates 1 to 3, turn 9) and the three post-exit "look around" prompts (turn 11), six prompts. Same system text in every arm; only the user text differs.
Arms (each a minimal edit to the recorded user text):
- 0 control: unchanged.
- 1 things in scope: delete the THINGS and PLAYER lines for objects not in Kristin's current area or vehicle (the house contents), keeping her place, the truck, the seats, the laptop, the card.
- 2 scene scoped: replace the SCENE bullets about the house interior (back door, drawer, the two pointer lines) with the same text prefixed by nothing and wrapped as a recalled fact only when she is in the house; when she is not, the SCENE shows only "What presses on Kristin now" and "Michelle is missing."
- 3 arms 1 and 2 together.
- 4 rule: control plus the story-neutral rule "Describe only what Kristin can see from where she is now."
10 samples per arm per prompt: 5 arms x 6 prompts x 10 = 300 narrator calls (cap 320). No item-facts or Jev calls (single narration call per sample).
Read by hand, narration only. Score each reply: (a) describes only what is visible from the stated place (cab and exterior for the seat; exterior for outside); (b) does not describe the house interior as present view; (c) does not move her or change posture (no "gets out", no "walks"). A reply passes if (a), (b), (c).
Decision rule (triage): an arm advances if it passes at least 8 of 10 samples in at least 5 of 6 prompts and beats control by at least 3 per prompt on average, with no new invented object. A tie or miss stops that arm; a pass proceeds to one product-wired live check, never straight to adoption. If arm 4 is the only winner it is applied to every narration path per the writing guide.

## P2 Requirement 1, reported route: lead-up for "feel in the gap" after the staged cue
Recorded prompts: the five route-A turn-2 narration prompts. Arms: 0 control; 1 the narrator's player line rewritten to name the referent the engine already resolved for matching ("feel in the gap" -> "feel in the gap beneath the drawer"); 2 add the committed pointer statement line to SCENE ("A thin gap beneath the drawer's lower edge is wide enough for Kristin's fingers."); 3 arms 1 and 2. 10 samples per arm per prompt: 4 x 5 x 10 = 200 calls (cap 220).
Score: no door or frame gap, no invented object, no "pry bar", fabric or key. Same decision rule.

## P3 Requirement 3: narrator boards her on "go out to the truck" (deferred)
Not started until P1 reports; it needs its own diagnosis (recorded prompts for the five replicates where the narrator boarded her). Its arms will be proposed after reading those prompts.

## Budget and engine
P1 plus P2 about 500 narrator calls, cap 540. Billed work runs as one Ringer task each through Luna at high effort (the repo's probe harness pattern, `scripts/ringer/stage7/*_replay_probe.py`), with `--dry` first, a 2-sample smoke, no retries, no replacement samples, partial rows kept.

## Not covered
Hosted staging behavior; the narrator's boarding over-narration (P3); the `None`/ad hoc parent anomalies on the witnessed turn (a separate world-model question); 1B's marked pursuit text live; rates beyond n=10 per arm.
