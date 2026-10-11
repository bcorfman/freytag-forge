# Brief for ChatGPT Desktop: judge the evidence-penalty lines as a player would read them

You are helping with freytag-forge, an interactive-fiction engine with one shipped story ("The Continuity Initiative", nine scenes 1A to 3C). A player types free text and a small model narrates. You wrote the timer-penalty proposal last round (four "evidence gaps", paid on the 3C broadcast scene). It is now built and has been played live. I need you to **judge how it reads**, because the author has not read it yet and a script cannot judge tone.

## What was built (so you do not have to guess)

- Four gap facts. A gap is set only when the scene's timer forces a delivery the player did not earn: `evidence_gap_processing_numbers` (1C), `evidence_gap_development_record` (2B), `evidence_gap_copy_check` (2C), `evidence_gap_marked_site_list` (3B).
- In scene 3C two pacing events fire at fixed turns. Turn 4 picks the first matching line: processing numbers, then development record, else the default. Turn 10 picks: marked site list, then copy check, else the default. At most two gap lines can ever show.
- The line is now **appended verbatim after whatever the narrator wrote that turn**. Before, the narrator was asked to show it and dropped it every time (0 of 18). Now it shows 18 of 18, never twice, no rejected turns.
- The ending stays reachable with all four gaps true. No progress rule reads a gap. This is checked offline.

The four lines, exactly as shipped:

1. Turn 4, processing numbers: `Water seeps under the outer doors. On the broadcast, Michelle says, "Kristin could not copy the full set of prisoner numbers from the processing line."`
2. Turn 4, development record: `Water seeps under the outer doors. On the broadcast, Michelle says, "Kristin left without a copy of the development record bearing Brandon's name."`
3. Turn 10, marked site list: `Rising water closes a maintenance passage behind the fleeing captives. On the broadcast, Michelle says, "Rebecca gave us the locations, but Kristin left without a copy of her marked site list."`
4. Turn 10, copy check: `Rising water closes a maintenance passage behind the fleeing captives. On the broadcast, Michelle says, "Kristin had no time to check her copied evidence against the original files."`

Defaults (no gap), unchanged: turn 4 `Water seeps under the outer doors. Charles's emergency deluge is becoming real.` Turn 10 `Rising water closes a maintenance passage behind the fleeing captives. The remaining routes are narrowing fast.`

## Four real turns, exactly as a player saw them

The player command is the heading. The narrator's prose is first; the shipped line is the end of the paragraph.

**All gaps, turn 4. Command: "Copy the archive to the independent networks."**
> Kristin quickly types on the computer, copying the archive to the independent networks. She watches as the files transfer and the network activity spikes. Rebecca Jenkins storms into the room, furious at Kristin for compromising their operation. Water rises around the drainage pump controls. Water seeps under the outer doors. On the broadcast, Michelle says, "Kristin could not copy the full set of prisoner numbers from the processing line."

**Development record only, turn 4. Same command.**
> Kristin quickly types on the computer, copying the archive to the independent networks. She watches as the files transfer, her eyes scanning the screen for any signs of error. The transfer completes, and Kristin breathes a sigh of relief, knowing that the information is now beyond Rebecca's reach. Water rises around the drainage pump controls. Water seeps under the outer doors. On the broadcast, Michelle says, "Kristin left without a copy of the development record bearing Brandon's name."

**All gaps, turn 10. Command: "Read the reports of facilities surrendering."**
> Kristin stands on the Los Angeles surface, the warm sun shining down on her as she scans the reports on her phone. She sees the list of facilities that have surrendered, and her eyes widen as she realizes the scope of the situation. Michelle stands beside her, her eyes fixed on the reports as well, a determined look on her face. Across the country, detention sites begin to surrender or release prisoners. The national network fractures. Rising water closes a maintenance passage behind the fleeing captives. On the broadcast, Michelle says, "Rebecca gave us the locations, but Kristin left without a copy of her marked site list."

**Copy check only, turn 10. Same command.**
> Kristin stands on the Los Angeles surface, the warm sun on her face as she scans the reports on her phone. She sees the list of facilities surrendering, their names and locations flashing on the screen. Michelle stands beside her, her eyes fixed on the phone as well, a look of determination on her face. Across the country, detention sites begin to surrender or release prisoners. The national network fractures. Rising water closes a maintenance passage behind the fleeing captives. On the broadcast, Michelle says, "Kristin had no time to check her copied evidence against the original files."

Notes on the samples: in these tests the scripted player jumps ahead, so by turn 10 the narrator has Kristin on the surface. A real player at turn 10 could be anywhere in 3C (the plot runs: the broadcast and answering Charles, the archive, the pumps and tunnel, the surface). The turn-10 default line was written before this work and already says rising water closes a passage behind the fleeing captives, which does not fit a Kristin who is already outside. Read `data/stories/continuity-initiative/plot.md` Scenes 3C.1 to 3C.4 for what the player can be doing.

## What I need from you (judgment, with reasons)

1. **Does it read as a cost?** For each of the four lines, say whether a player would feel the evidence slipped away because they were slow, or would read it as flavor. Name the exact words that carry or lose that feeling. Say whether any line sounds like an accusation or a game-over, which the author does not want: the penalty must feel like weaker evidence, never like failure. Rank the four lines from strongest to weakest effect.
2. **Voice and fit.** Michelle is speaking on a live broadcast about Kristin in the third person, while Kristin is in the scene. Does that work, or does it break the fiction when Kristin is next to her, far away, or the speaker? If it breaks, give the smallest wording change that holds wherever Kristin is. Quote the old and new line.
3. **The turn-10 place problem.** The turn-10 lines (both the gap variants and the default) start with rising water closing a passage "behind the fleeing captives", which clashes with a Kristin already on the surface. Propose replacement wording for the **turn-10 pressure sentence** that is true wherever the player is in 3C and still carries the pressure of closing routes. Give one version for the default and the matching first sentence for each of the two gap variants. These are authored story lines, so write them in the voice of the existing story text, and keep every other sentence exactly as it is. Say which 3C moments you checked the wording against (cite scene numbers).
4. **Does the gap sentence repeat information the player just read?** In the turn-4 samples the narrator's own text and the gap sentence are separate. Say whether the order (narrator text, then pressure, then Michelle) is right, or whether a gap line would land better in a different place. Do not propose an engine change; if you think one is needed, say exactly why and propose the smallest.
5. **Honesty check.** In `plot.md`, which earlier scene beats show the thing each line says Kristin missed (1C.2, 2B.3, 2C.3 and 2C.4, 3B)? Confirm each line only refers to something the player has seen by 3C, and flag any line that could confuse a player who played those scenes thoroughly and never hit a timer (they have no gap; the line should never appear for them).
6. **A rubric I can use.** Give me a short human-read rubric (five to seven yes/no questions) for scoring these turns across many playthroughs, including a check for a no-gap run that invented a penalty on its own. Make every question answerable from the turn text alone.

## Rules you must keep

- Existing `fallback_text`, `delivery_text`, `cue_text`, plot lines and the two default pacing lines stay byte-identical **except** the turn-10 sentence if you propose a change in item 3, which I will apply as a deliberate edit. Say plainly if a proposed change touches an existing default.
- Facts are the only truth. A pacing line may show what is happening or what is visible. It may not reveal knowledge the player has not earned or name a hidden place.
- No progress rule reads a gap. A line may not make a later reveal depend on a gap.
- These lines are emitted verbatim, not written by the small narrator, so they need not use the narrator's eighth-grade register. Keep them plain and in the voice of the existing story text.
- Say what you could not check.

Keep it concrete and quote exact text. No new mechanism.
