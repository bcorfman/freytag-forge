# Preregistration: 1A opening and truck feedback, probe 2 (generic candidate changes)

Written 2026-11-02 after probe 1 (`probe1-prereg.md`, Result section) and before any probe 2 billed run. Brandon asked for this probe ("yes", 2026-11-02). Every candidate below is a general change to what the engine or the story gives the model, not a command list: the boarding question is about any vehicle, the reach line is derived from the seat's vehicle, and the opening lines are authored story material. Controls are probe 1's same-day rows (same code, same day); no control is re-billed except where noted.

## Questions
- **Q1** Can the boarding question be reworded so that "out to / over to" movement toward a vehicle answers consistently, for any vehicle name, without making "walk up to" or "look at" board?
- **Q2** With the raw command line removed (probe 1 arm 1), does one more general fact, that everything inside the occupied seat's vehicle is within reach from that seat, stop the narrator from sending her out of the truck to reach the laptop? (Probe 1 lead: all 5 remaining exits walked to the passenger side.)
- **Q3** Does authored kitchen start, layout and personal-significance material fix the opening's missing kitchen, layout, reaction and "KMS is new and strange"?

## Candidates (exact text; system text identical in every arm)
**Q1 revised boarding question (arm R)**, same payload shape as `boards_vehicle_payload`:
- instructions: `Decide whether the command has the player go to the vehicle in order to get in it. Going to, going out to, or heading out to a vehicle means the player gets in. Getting in, climbing in, sitting in, or driving it also counts.`
- true: `The command has the player go to, go out to, head out to, get into, sit in, or drive the vehicle.`
- false: `The command only looks at, touches, or talks about the vehicle, or only walks up to it or stands beside it. It is not boarding if it leaves the vehicle.`
Arm S is the shipped question. Phrasings, 12, each with `{v}`: `head out to`, `go out to`, `go to`, `get in`, `climb into`, `walk out to` (expected yes); `walk up to`, `approach`, `look at`, `get out of` (expected no); `head over to`, `make for` (reported, not scored). Vehicles: `Kristin's truck` (command text `the truck`) and `the van`. One sample per cell (probe 1 showed repeat scores differ by at most 0.03).

**Q2 reach line (arm 2).** Probe 1 arm 1 prompt plus one SCENE bullet inserted directly after the line that places her in the driver's seat: `- Kristin can reach anything inside Kristin's truck from where she sits.` Commands: `head out to the truck` (arms 1 and 2 against probe 1's control and arm 1 rows) and `go to the truck` (arms 0, 1, 2 all billed, 8 samples each).

**Q3 opening material (arm O1).** The shipped opening user text plus these SCENE bullets inserted after the objective line:
- `Kristin is in Michelle's kitchen, just inside the forced back door.`
- `The workstation stands in the kitchen. Its chair lies overturned beside it.`
- `Michelle is Kristin's best friend, and Kristin knows this house. It is far too quiet.`
- `The KMS initials on the drawer are fresh cuts: Kristin's own initials on Michelle's furniture. Kristin cannot explain them.`
Control: probe 1 Part 3 rows.

## Design and cost
Part 1: 12 phrasings x 2 vehicles x 2 arms (S, R) x 1 sample = 48 Jev calls. Part 2: 12 (`head out`, arm 2) + 24 (`go to`, arms 0, 1, 2 x 8) = 36 narrator calls, interleaved. Part 3: 10 narrator calls (arm O1). Total 94, hard cap 105. Smoke first: 3 Jev (one per `head out to`, `go out to`, `walk up to`, arm R, truck), 1 Part 2, 1 Part 3 = 5 calls. No retries, no replacement samples, partial rows kept, stop on quota. Offline prompt arms are built from the product-wired replay like probe 1.

## Scoring (every narrator row read by hand)
Part 1: a cell is correct when its yes/no matches the expected answer (threshold 0.5); report the score, and any correct cell with margin under 0.1 as knife-edge. Part 2: same (a) to (d) as probe 1. Part 3: the same six yes/no items as probe 1, plus: names two or more of back door, workstation, chair relative to her.

## Decision rules (triage only; nothing adopted from this probe)
- **Q1:** arm R advances if it is correct in at least 19 of the 20 scored cells (12 expected-yes, 8 expected-no), has no knife-edge expected-yes cell, and beats arm S by at least 3 cells. Otherwise the question stays and the failure goes back to the plan.
- **Q2:** arm 2 advances if (a) and (b) both pass in at least 10 of 12 on `head out to the truck` and at least 6 of 8 on `go to the truck`, and arm 2 beats arm 1 on (a) by at least 3 on the combined samples.
- **Q3:** arm O1 advances if it names the kitchen, shows the layout, treats KMS as new and strange, and shows a specific reaction in at least 7 of 10 each, with no revealed card and no new invented object or person in any reply.
A winning candidate then becomes a tested change (a generic `World` projection for the reach line, the reworded question in `jev_questions.py`, the authored story lines), a product-wired live check, and three live replicates, per the plan.

## Not covered
Later turns after boarding, the card and laptop interpretation turn, other models, hosted staging, and whether a sentence-level instruction beats these (rules lose first, per the scene-fixing guide).

## Result (2026-11-02; 94 calls, 94 usable, no quota stop; plus a 5-call smoke)

Rows: `bench/results/1a-opening-and-truck/probe2.json` (smoke: `probe2-smoke.json`). Harness `scripts/ringer/opening_truck/probe2.py`. Every narrator row was read by hand.

**Q1, boarding question (S shipped, R revised; scores).** R fixes the "out to" phrasings and breaks "approach".

| Phrasing (truck / van) | S | R |
| --- | --- | --- |
| head out to | 0.59 / 0.65 yes | 0.89 / 0.89 yes |
| go out to | **0.47 NO** / 0.62 yes | 0.82 / 0.84 yes |
| go to | 0.62 / 0.69 yes | 0.77 / 0.85 yes |
| walk out to | **0.26 / 0.28 NO** | 0.74 / 0.70 yes |
| get in, climb into | 0.96 yes | 0.97 yes |
| walk up to | 0.16 / 0.19 no | 0.41 / 0.36 no (near edge) |
| **approach** | 0.23 / 0.21 no | **0.68 / 0.66 YES (wrong)** |
| look at, get out of | no | no |

Scored cells correct: S 17 of 20, R 18 of 20; R has no knife-edge expected-yes cell (S has 1). Rule needs R at 19 or more and 3 above S: **not met.** The reworded question trades two gaps for one new one. It cannot tell "head out to" from "approach" (both are movement toward the vehicle).

**Q2, reach line (arm 2 = no raw command + "Kristin can reach anything inside Kristin's truck from where she sits.").**

| Command / arm | n | (a) seated, parked | (b) laptop shown | (c) surroundings beyond the laptop | (d) nothing new |
| --- | --- | --- | --- | --- | --- |
| head out to the truck / arm 1 (probe 1) | 12 | 7 | 12 | 0 | 7 |
| head out to the truck / **arm 2** | 12 | **12** | **12** | 0 | 10 (2 add "fading light") |
| go to the truck / control | 8 | 2 | 1 | 5 (only when she is out of the truck) | 8 |
| go to the truck / arm 1 | 8 | 1 | 8 | 0 | 8 (1 adds a thought) |
| go to the truck / **arm 2** | 8 | **8** | **8** | 0 | 6 (2 add "fading light") |

The control for "go to the truck" reproduces the report: **3 of 8 start the engine and drive up to the gate**, 3 of 8 turn off the engine and step out, 1 looks at the laptop, 1 is the "already in the driver's seat" line. Rule met: arm 2 passes (a) and (b) 12 of 12 and 8 of 8 (bars 10 and 6), and beats arm 1 on (a) by 12 of 20. All 20 arm 2 replies reach for the laptop, pull it out and open the screen: the narrator does the one action left in the prompt and describes no surroundings. Requirement (c) is not met by arm 2.

**Q3, opening arm O1 (10 replies).** Kitchen named 8 of 10 (was 0). Layout (two or more of back door, workstation, chair): 4 of 10 (rest name only the back door). KMS drawn as strange: 2 of 10 ("What's going on, Shelly?" at the initials; neither says fresh). Specific reaction: 2 of 10. Card revealed: 0 of 10. Invented objects: 3 of 10 (a ticking clock twice; papers and an open laptop once, which contradicts the laptop being in the truck). Two replies right the overturned chair for the player. All 10 move Kristin. Rule (7 of 10 each) is **not met** on layout, KMS and reaction. The kitchen line works; the abstract significance lines ("knows this house", "cannot explain them") were mostly ignored.

**Conclusions.** (1) Removing the raw command plus the reach line fixes the seated/parked and laptop requirements generally (20 of 20), but leaves the surroundings unmet; a probe 3 arm gives the boarding turn an action to narrate. (2) The classifier reword is not adopted; it moves the failure. Boarding must be made harmless either way (committed or not): when the question says no, the narrator still needs the truck's location. (3) Opening needs concrete, observable material for layout, reaction and the initials; abstract lines lose.
