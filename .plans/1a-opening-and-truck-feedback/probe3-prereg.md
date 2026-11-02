# Preregistration: 1A opening and truck feedback, probe 3 (surroundings, unboarded fallback, concrete opening)

Written 2026-11-02 after probe 2 (`probe2-prereg.md`, Result) and before any probe 3 billed run. Brandon asked for it ("yes", 2026-11-02). All candidates are general: an action line derived from the new seat, a place line for a thing the command names, and authored story lines. Controls are probe 2's same-day rows where the arm already exists; only new arms and the unboarded control are billed.

## Questions
- **Q1 Surroundings on a committed boarding turn.** Probe 2 arm 2 (no raw command, plus the reach line) kept her seated, parked, with the laptop shown in 20 of 20 but described no surroundings. Does giving the turn a neutral action to narrate fix that without losing the laptop?
- **Q2 Boarding that does not fire.** When the boarding question answers no ("go out to the truck" on the shipped question, 0.47), the narrator gets the bare command and no truck location. Does the named thing's place line stop the engine-start and driving?
- **Q3 Concrete opening.** Do concrete, observable lines (positions, the phone, clean cuts) do what the abstract lines in probe 2 arm O1 did not: layout, a specific reaction, KMS as fresh and strange, without re-entering the house?

## Candidates (exact text; system text identical in every arm)
**Q1.** Both arms start from probe 2 arm 2 (raw command line removed, reach line inserted after the driver's-seat SCENE bullet) and insert one PLAYER line in the position the raw command had (between the `Kristin. Place: driver's seat.` line and the `Already done:` line):
- Arm 3: `- Kristin looks around from the driver's seat.`
- Arm 4: `- Kristin takes in what she can see and reach from the driver's seat.`
Commands: `head out to the truck` and `go to the truck`, 10 samples each per arm (40 calls). Compared with probe 2 arm 2 (12 and 8 samples).

**Q2.** Product-wired replay with the boarding question scripted to answer no, route `open the drawer`, `feel in the gap`, then `go out to the truck`; keep the narrator request for the last turn. Arm 0 is that request as built. Arm T1 inserts one THINGS bullet, `- Kristin's truck. Place: outside the house.` (creating a `THINGS:` section directly before `CONSTRAINTS:` when the prompt has none). 10 samples each (20 calls).

**Q3 (arm O2).** The shipped opening user text with these SCENE bullets inserted after the objective line:
- `Kristin has already stepped inside and stands in Michelle's kitchen, beside the forced back door.`
- `The workstation is across the kitchen from the back door. Its chair lies on its side in front of it.`
- `Michelle's phone lies on the kitchen floor.`
- `The KMS cuts in the drawer front are pale and clean. They are Kristin's own initials, carved into Michelle's workstation.`
Control: probe 1 Part 3 and probe 2 O1 rows. 10 samples (10 calls).

Total 70 calls, hard cap 80. Smoke first, 5 calls: Q1 arm 3 on `head out to the truck`, Q1 arm 4 on `go to the truck`, Q2 arm 0, Q2 arm T1, Q3 once. No retries, no replacement samples, partial rows kept, stop on quota. The world already declares the phone's place (the kitchen floor), the workstation and the chair; no new thing is introduced. The layout sentence ("across the kitchen from the back door") is new authored layout and stays a story decision for Brandon before any adoption.

## Scoring (every reply read by hand)
**Q1** passes when all hold: (a) seated and parked (no engine start, driving, gate crossing, return to the house, or getting out); (b) the laptop shown on the passenger seat; (c) at least one outside surrounding from the SCENE text named (house, gate, curb, street, sirens); (d) nothing invented (object, person, place) and no thought written for her. **Q2** passes when: (a) no engine start, driving, gate crossing or pulling away; (b) nothing invented; and report separately whether the reply ends with her at the truck (informational). **Q3** items: kitchen named; layout understood (back door, workstation and chair with the relation given); a specific reaction tied to a concrete thing (the phone, the cuts, the silence); KMS shown as fresh or strange; card not revealed; invented object count; no re-entry wording ("steps in", "pushes the door open"); acts for her.

## Decision rules (triage only; nothing adopted from this probe)
- **Q1:** an arm advances at 8 of 10 or more on (a) to (d) together on each command. If both advance, prefer arm 3 (fewer words).
- **Q2:** T1 advances if driving or engine start is 1 of 10 or fewer, control is 3 of 10 or more, and invention is 2 of 10 or fewer.
- **Q3:** O2 advances at 8 of 10 or more on kitchen, 7 of 10 or more on layout, specific reaction, KMS fresh/strange and no re-entry, with no revealed card and at most 1 reply inventing an object.
A winner becomes a tested change (a generic projection in `storygame` using the `World` reach method, the reach line and neutral action for a committed boarding turn, the place line for named things, the story lines in `plot.md` and its sibling files), a product-wired live check and three live replicates, per the plan.

## Not covered
Later turns, the interpretation turn, other models, hosted staging, and the classifier wording (probe 2 showed it only moves the failure).
