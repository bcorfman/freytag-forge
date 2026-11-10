# Situation trace: Reyes demands the recovered memory card (scene 1A)

Generated from the current story files. Read-only; edit the sources, not this page.
Each section answers one question: **what is happening, where does it lead, what does the next scene need, what can Kristin do, and where the story does not hold together.**
Gaps (section 5) are places where the story contradicts itself or common sense; each is computed from the sources and quotes them with file and line.

## 1. The situation

- Pacing event `officer_presses_1a` fires at turn 7 when: card_challenged is true and patrol_in_house is true.
  - `card_challenged` (A patrol officer saw Kristin take Michelle's memory card and challenged her.) comes from: claim k_sl_1a_b_r0w from SL-1A-E-R2
  - `patrol_in_house` (A patrol officer is inside Michelle's house.) comes from: pacing event patrol_enters_1a (turn 7)
- It sets: officer_demanded_card is true.
- Reyes's line: “The officer plants himself between her and the front door and holds out a gloved hand. "Whatever you just took from that desk. Let's see it, ma'am. Right now."”
- Reyes in the story files: A young, polite federal patrol officer who works from a printed list and does not like what the list asks of him.

## 2. Where the demand leads

`officer_demanded_card` is read by:
- pacing event patrol_leaves_1a (scene 1A) picks a line of wording by it [wording]

Nothing reads it except a line of wording.

## 3. What Kristin needs to leave 1A

Transition `t_1a_1b` needs all of:

| Needs | Meaning | Produced by |
| --- | --- | --- |
| `michelle_lead_actionable` | Kristin has a concrete, credible lead from Michelle’s research that can be followed away from the house. | claim k_sl_1a_b_r1 from SL-1A-B-R1; claim k_sl_1a_d_r1 from SL-1A-D-R1 |
| `patrol_return_pressure` | Observable signs indicate the federal patrol is likely to return or intensify scrutiny at Michelle's house. | pacing event patrol_returns_1a (turn 13); claim k_sl_1a_c_r2 from SL-1A-C-R2 |
| `memory_card_recovered` | Kristin has recovered Michelle’s memory card. | claim k_sl_1a_b_r0 from SL-1A-E-R1; claim k_sl_1a_b_r0w from SL-1A-E-R2; fallback handoff for continuity_initiative_known (scene 1A) |

It also lists `memory_card` as a required dependency.

### What the story says, next to what the engine checks

| The story says | The engine checks |
| --- | --- |
| “She takes the card out to her truck and opens it on her laptop.” (plot 1A.2) | Reading the files needs: memory_card_recovered is true; it names no thing she must be near. It does not check who holds the card. |
| “… let her read the remaining files on the memory card she is already carrying; the warning tells her Michelle hid something deliberately, so the files can reveal what it points to without repeating the recovery.” (SL-1A-D) | Same check as above. |
| The exit lists `memory_card` as a dependency | Passes unless the card is destroyed or incapacitated. The card has no unavailable state, so this can fail only if it is destroyed; stand-in: ['michelle_phone']. It does not check who holds it. |
| “If she takes it while he is watching, he challenges her, and the patrol's suspicion follows her out of the house.” (plot 1A.4) | The mark (`kristin_marked_by_patrol`) is set when the card is recovered in front of an officer, not by the demand or by any answer to it. |

## 4. If Kristin answers the demand

Responses below are **inference, not canon**. Rows A–D are run through the real engine; the rest have no authored mechanics.

| Response | Who holds the card | Lead already read? | Can she still read the card's files? | Does she have the lead? | Can she leave 1A (once the patrol is due back)? |
| --- | --- | --- | --- | --- | --- |
| A. Keeps it (stalls, refuses, or walks out with it) | kristin | no | yes | no | no |
| B. Keeps it | kristin | yes | no: already_established | yes | yes |
| C. Hands it over | patrol_officer | no | yes | no | no |
| D. Hands it over | patrol_officer | yes | no: already_established | yes | yes |
| E. Runs | not simulated | | | | no authored mechanics |
| F. Resists or escalates (taser, gunfire) | not simulated | | | | no authored mechanics; the story files never say Reyes is armed |

Read rows C and D together. With the card in Reyes's hands she may still read its files (C), and once she has the lead the exit opens exactly as when she kept the card (D matches B). The engine cannot tell reading-then-surrendering from surrendering-then-reading.

## 5. Story gaps

Each gap below is **computed**: it appears only if its check fails against the current sources, and every quote is located by file and line. Fix the source and the gap disappears.

### G1. A surrendered card leaves with Reyes, but Kristin can still read it and leave.

- **Common sense:** She can use the card only while she holds it. Losing it should either cost her something or send her after it; as written it does neither, so surrender is a dead end, not pressure.
- **The story says:**
  - `world.yaml:648`: “- {move: patrol_officer, parent: patrol_staging}”
  - `plot.md:215`: “item_ids: [memory_card, transit_card”
  - `t_1a_1b` lists `memory_card` as a required dependency (section 3).
- **The engine shows:**
  - After she hands it over and the patrol leaves: card is held by `patrol_officer`, who is in `patrol_staging`; Kristin is in `kitchen`.
  - She can still read the files: `eligible` (kept-card case: `eligible`).
  - With the lead already read, `t_1a_1b` opens: yes. Its `memory_card` dependency can fail only if the card is destroyed, not if someone else holds it.
  - Ways the card can return to Kristin: 1 authored effect(s) (`memory_card_recovered` moves it to `kristin`); `memory_card_recovered` is already true and nothing sets it false, so none can fire again.

### G2. She reads the card in the kitchen with no laptop; the story sends her to the truck.

- **Common sense:** She can read the card only where the laptop is: in the truck, or wherever she carries the laptop. Nothing in the model ties the reading to the laptop's place.
- **The story says:**
  - `plot.md:170`: “She takes the card out to her truck and opens it on her laptop.”
  - `knowledge.yaml:715`: “Her laptop is still out in her truck.”
  - `plot.md:99`: “on the passenger seat of Kristin's truck”
- **The engine shows:**
  - Kristin is in `kitchen`; the laptop is in `truck_passenger_seat`.
  - Claim `k_sl_1a_b_r1` lists `kristin_laptop` as relevant but sets no `reach_entity_ids` (needs: memory_card_recovered is true).
  - Engine verdict on reading the card from the kitchen, with Reyes in the house and the demand outstanding: `eligible`.

### G3. If she must hold the card to read it, Reyes taking the card strands the story.

- **Common sense:** Story pressure can cost Kristin something, but it must never leave her with no way forward. Every pressure needs a plausible fallback.
- **The story says:**
  - `plot.md:200`: “If she takes it while he is watching, he challenges her”
  - `pacing.yaml:52`: “Let's see it, ma'am. Right now.”
  - `knowledge.yaml:715`: “Her laptop is still out in her truck.”
- **The engine shows:**
  - The challenge comes the moment she takes the card in front of him (claim k_sl_1a_b_r0w from SL-1A-E-R2), so it comes before she can reach the laptop and read anything.
  - Both producers of the lead are card-reading acts: claim k_sl_1a_b_r1 from SL-1A-B-R1; claim k_sl_1a_d_r1 from SL-1A-D-R1.
  - Fallbacks that produce the lead: none (the one handoff nearby only sets `memory_card_recovered`, which is already true).
  - No authored effect returns the card to her once Reyes has it (G1).
  - With the G1 and G2 rule applied, can she read, does she have the lead: Keeps the card, lead unread → read yes, lead yes; Hands it over, lead unread → read no, lead no; Hands it over, lead already read → read no, lead yes.
  - Stranded situations: 1 (Hands it over, lead unread). From there `t_1a_1b` can never open.
  - Today the engine hides this, because it lets her read a card she gave away. Fixing G1 and G2 without a fallback turns the demand into an unwinnable state.

