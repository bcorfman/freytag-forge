# Preregistration: 1A opening and truck feedback, probe 4 (live check of the committed boarding-turn change, and surroundings)

Written 2026-11-02 after commit `e41878c3` and before any probe 4 billed run. Brandon asked for it ("yes", 2026-11-02). Scoring follows the plan's policy (Brandon, 2026-11-02): invented scenery does not fail an arm; only contradictions of canon or state, pre-empted beats, or story-name collisions do.

## Questions
- **Q1 Does the committed change hold live?** The prompts are built by the shipped code (product-wired replay), not edited by hand: the raw movement phrase is gone and the pronoun-free reach bullet is in the SCENE text. Probe 2's hand-edited arm 2 passed seated, parked and laptop shown in 20 of 20; the committed wording differs ("from the driver's seat", no pronoun).
- **Q2 Surroundings.** Adding the neutral action "takes in what she can see and reach from the driver's seat" in the place the raw phrase had (probe 3 arm 4 showed the laptop most often) to the committed prompt: does it also name something outside, without story-affecting inventions?

## Design
Prompts come from the product-wired replay on the current code: route `open the drawer`, `feel in the gap`, then the command, with the boarding question scripted to yes. Commands: `head out to the truck`, `go to the truck`. Arm A is the narrator request on the boarding turn exactly as built (it must contain the reach bullet and `Already done:`, and no line equal to `- <command>`). Arm B is arm A plus the PLAYER line `- Kristin takes in what she can see and reach from the driver's seat.` between the `Kristin. Place: driver's seat.` line and the `Already done:` line. 10 samples per arm per command, interleaved: 40 calls, hard cap 48. Smoke first, 2 calls (arm A `head out to the truck`, arm B `go to the truck`). No retries, no replacement samples, partial rows kept, stop on quota.

## Scoring (every reply read by hand)
(a) seated and parked: no engine start, driving, gate crossing, return to the house, or getting out. (b) the laptop shown on the passenger seat. (c) at least one outside surrounding from the scene text named (house, gate, curb, street, sirens). (d) no story-affecting invention: a contradiction of canon or state (the laptop moved elsewhere, another person in the truck), a pre-empted or revealed beat (patrol officers arriving at the house, someone entering the house, the card), or a story-name collision (a named person; the antagonists share the surname Jenkins). Other scenery is recorded as a count for information and does not fail. Report (a) to (d) separately and together.

## Decision rules (triage only)
- **Q1:** confirmed if arm A passes (a), (b) and (d) in at least 9 of 10 on each command. If not, the committed wording is rolled back to probe 2's and re-checked before any other change. Arm A (c) is reported and expected to fail.
- **Q2:** arm B advances if it passes (a) to (d) in at least 8 of 10 on each command. Otherwise surroundings on the boarding turn stay open and the plan returns to the scene text and the opening-prompt rule list.

## Not covered
The unboarded turn, the opening, later turns, other models, hosted staging, and the full suite.

## Result (2026-11-02; 40 calls, 40 usable, no quota stop; plus a 2-call smoke)

Rows: `bench/results/1a-opening-and-truck/probe4.json` (smoke: `probe4-smoke.json`). Harness `scripts/ringer/opening_truck/probe4.py`. Every reply read by hand; scored under the plan's relaxed invention policy.

| Command / arm | n | (a) seated, parked | (b) laptop shown | (c) outside named | (d) no story-affecting invention | (a)+(b)+(d) | all four |
| --- | --- | --- | --- | --- | --- | --- | --- |
| head out / **A** (committed change) | 10 | 10 | 10 | 0 | 10 | **10** | 0 |
| go to / **A** | 10 | 10 | 10 | 0 | 10 | **10** | 0 |
| head out / B (+ "takes in what she can see and reach") | 10 | 10 | 7 | 9 | 10 | 7 | **6** |
| go to / B | 10 | 10 | 8 | 8 | 10 | 8 | **6** |

**Q1 confirmed.** The committed change passes (a), (b) and (d) in 10 of 10 on both commands (bar 9 of 10). Every reply reaches for the laptop on the passenger seat; 2 of 10 on "head out" also type on it, which is acting for the player, not a story break. (c) is 0 of 20 as expected: arm A never describes the outside.

**Q2 not met.** Arm B reaches 6 of 10 on each command (bar 8 of 10). Its misses are coverage, not inventions: it drops the laptop in 3 of 10 and 2 of 10, and the outside view in 1 of 10 and 2 of 10. The inventions it adds this time (Michelle's car in the driveway twice, police cars or flashing lights in 5 of 20, a dark and quiet house) are scenery under the policy; the car in the driveway is worth a look when the opening is written, since it implies how Michelle left.

**Conclusions.** The boarding-turn change stays as committed. Surroundings on that turn are not solved by one neutral action line (best 6 of 10); the remaining miss is the narrator choosing either the cab or the outside, not both. Next lever, if wanted: an action line that names both halves, built generically from the world (the outside of the vehicle and what is inside it), tested as two wordings.
