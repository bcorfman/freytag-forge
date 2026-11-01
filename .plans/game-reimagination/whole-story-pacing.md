# Whole-story pacing and excitement redesign

Part of the [game reimagination plan](../game-reimagination-plan.md), section 4.
Read this when you are rewriting any scene's beats, or when deciding what a scene's
entry, set piece or exit should be. Act 2 (2A, 2B, 2C) has its own detail file:
[act2-redesign.md](act2-redesign.md).

Status: proposed design, 2026-10-31. Not canon until Brandon approves it and it is
written into `plot.md` (through a ChatGPT Desktop prompt), then propagated.

**Constraint: ship fast.** Every change here reuses a mechanism that already exists
and is tested: the 1C incident contract (`incidents.yaml`), `entry_variants`,
`bridge_text`, storylets, and already-declared items. No new engine features. The
redesign mostly *cuts* and *reorders*; it adds one NPC.

## 1. What is wrong with the story as it plays

The canon is strong: a missing friend, a compromised ally, a captive who is secretly
fighting back, a villain couple who turn on each other, a flood and a broadcast. The
problem is the order in which the player meets it.

- **Information arrives as reading.** 1A reads a card, 1B reads clues, 1C reads
  numbers, 2A reads readings, 2B reads files, 2C reads orders and a coded message.
  The player is a clerk for most of the game.
- **Every scene starts at rest.** 2A opens in a hideout with exposition, 2B at ready
  terminals, 2C with "She could check them now."
- **The antagonists are offstage until 3B.** Rebecca phones in an offer; Charles is a
  name on orders. Nobody the player can talk to stands in the way.
- **Michelle is a rumour until 3A.** The emotional engine (Kristin wants Shelly back)
  has no live contact for two thirds of the game.
- **Choices do not carry.** The 1C choice changes one 2A entry line. The 2C "crisis
  choice" is erased one beat later by Michelle's message.
- **Middle flat, climax crowded.** 3B to 3C hold nine beats; Act 2 holds a cover
  story, a supervisor and a file search.

## 2. Five rules for every scene

1. **Open in motion.** Something is already going wrong when the scene starts.
   Preparation and travel go in the bridge text. (Cost: rewrite `entry_text`.)
2. **One set piece done with the hands.** Hide, bluff, run, hold a door, talk someone
   down. Reading is the reward, never the set piece.
3. **A person in the way**, present and talkable.
4. **One choice per act that leaves a mark**, recorded as an incident advantage or
   cost and paid off with an existing `entry_variants` line or outcome segment.
5. **Release before the next blow.** After a reversal, a quiet beat; then a
   *different* kind of pressure.

## 3. The tension curve

| Scene | Opens in motion | Set piece | Person in the way | Release | Change size |
| --- | --- | --- | --- | --- | --- |
| 1A | unchanged | unchanged | patrol officer | Michelle's voice | none |
| 1B | unchanged | unchanged | Brandon, tactical team | Brandon names himself | none |
| 1C | shipped | numbers or route | Brandon, sweep | a face like Shelly's | close staller gap only |
| 2A | At the gate in the inspection van | **The real leak** | shift supervisor | waved through | rewrite (Act 2 file) |
| 2B | Supervisor's audit sweep starts | **Hide in the stacks, confront Brandon in whispers** | supervisor, Brandon | **Shelly answers** | rewrite |
| 2C | Rebecca's guards close the corridor | **Rebecca in person** | Rebecca | Brandon's "yes" frees them | rewrite |
| 3A | Prisoners already moving | Reunion, then Kristin gives the go on the radio | a guard post | the reunion | entry + one storylet line |
| 3B | JANUS predicting their doors | decoy, office, flood | Rebecca, Charles | Brandon's goodbye | one entry variant |
| 3C | Charles cuts into the live broadcast | already Phase 2 scope | Charles, water | surface at dawn | Phase 2 as planned |

Target stays 45 to 75 minutes. The 120-turn ceiling stays a ceiling. Rewriting
2A to 2C shorter (one incident each, see Act 2 file) is the biggest single time
saving in the game: it removes most of SL-2A-A/B/E and SL-2B-A/B/C as mandatory
steps.

## 4. The consequence ledger (three facts, all cheap)

| Set in | Fact | Paid off by (existing mechanism) |
| --- | --- | --- |
| 1C | `processing_numbers_copied` / `service_level_access_known` (exist) | 2A entry variants (exist); 2A supervisor reacts to numbers or route |
| 2B | `brandon_name_kept` / `brandon_name_erased` (new incident outcomes) | 3B entry variant: Brandon's goodbye line and how his confession lands |
| 2C | `committed_to_transmit` / `committed_to_rescue` (new incident outcomes) | 3A entry variant: a freed cart joins the uprising, or the evidence is already out and the sectors are sealed |

2A's clean-or-suspected cover is *not* a ledger fact; it only picks a 2B entry
variant. Every combination reaches the same ending structure. Do not add more
ledger facts until humans have played this set.

## 5. Explicitly not doing (to save time)

- No 1A/1B rewrites. They work; touching them reopens tested journeys.
- No scene merges or new scene IDs.
- No new mechanisms: no "service key" item (use the declared `inspection_console`),
  no new auditor NPC (the 2A supervisor runs the 2B audit), no new printer (Michelle
  replies through the declared `medical_terminal` channel she already uses in canon).
- No branching endings beyond 3C's Phase 2 variants.
- 3C's three-episode split stays Phase 2 scope; this file adds nothing to it.

## 6. Authoring cost

One new NPC (the shift supervisor) needs declaring and placing per the
[grounding guide](../../docs/world-model-grounding.md). Everything else uses
declared entities. Story text goes to ChatGPT Desktop as one short pointer prompt
covering 2A to 2C plus the three entry variants; Claude does not write canon prose.
