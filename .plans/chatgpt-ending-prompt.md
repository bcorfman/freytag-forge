# Brief for ChatGPT Desktop: write the closing beat of "The Continuity Initiative"

You are helping with freytag-forge, an interactive-fiction engine with one story, "The Continuity Initiative" (nine scenes, 1A to 3C). A player types free text; a small model narrates each turn. The engine owns the world facts. You cannot run the game. This brief is self-contained. Write story text only; do not propose engine changes.

## The problem

The story has no ending. Scene 3C is the last scene. The player reaches the last reveal (the "Phase Two" file), the game says that sentence, and then the game just waits for more input. A human player cannot tell the story is over. We are adding an authored closing beat that the engine shows once, right after the final reveal, and then ends the game.

## Where the closing beat appears

The engine shows it as its own paragraph, straight after the final reveal's text, in the same turn. The final reveal is one of two alternatives. The player earns one of them, and the engine fills in the other as a forced delivery if the player never does. Either way, both facts below are true when the closing beat appears:

- `phase_one_label_known` and `phase_two_conflict_plan_known`.

The two alternatives deliver these lines (your closing must read well after either, and after both):

- File route: "A recovered JANUS file calls the disappearances Phase One. It names a second plan to provoke conflict among survivors."
- Charles route: "From an unknown location, Charles watches the unrest. He believes frightened people may still ask him to restore order."

## Facts that are true by the end (use only these)

- Kristin Schweitzer, 47, ex-Army assessment lead, found her best friend Dr. Michelle McGehee ("Shelly" to Kristin only). They are together and safe.
- Michelle broadcast the evidence nationally. Charles Jenkins tried to call her a terrorist. Live images of revolts at other facilities made the truth impossible to contain.
- Rebecca Jenkins, Charles's wife, was captured by the prisoners she had authorized for experiments.
- Charles escaped from his remote command site before authorities found him. His last remote channel still carries a signal.
- Brandon Corfman held the relay open so the broadcast stayed live. His fate is uncertain at this point. Do not say he lived or died.
- Kristin restored power to the drainage pumps and held a barrier. Michelle led the captives through the maintenance tunnel. The surface gates were released once. Thousands of captives reached Los Angeles.
- The detention network is breaking up: some facilities surrender, some release prisoners, some stay under Charles's control. Agencies blame rogue officials. Communities organize rescues. Families learn many of the missing may be alive.
- Kristin and Michelle are reunited. Neither can go back to their old life. Michelle begins publishing the full archive. Kristin joins teams that find and open the remaining facilities.
- The story's last note: Phase One removed people; Phase Two was meant to provoke conflict among those who remained. Charles believes frightened people may still ask him to restore order. The victory is real but incomplete.

Do not invent new people, places, objects, or events. Do not name anything outside this list and the lines above.

## What to write

1. **Closing text.** One paragraph, 90 to 130 words, third person past tense, in the voice of the delivery lines above (short sentences, concrete, plain words, no melodrama). It must:
   - land the reunion and the cost (no return to the old life),
   - show the exposure working but unfinished (some facilities open, some do not),
   - end on the open threat from Phase Two and Charles, not on triumph,
   - leave Brandon's fate unstated.
   Reading level: 12th grade or lower. One idea per sentence. Do not use the words "authored", "grounding", "segment", "scene", "player", "game" or "turn".
2. **End marker.** One short line (under 8 words) the engine shows after the paragraph, for example "The story ends here." Offer two alternatives.
3. **Self-check.** Confirm in one line each: no new people or places; Brandon's fate unstated; reads correctly after the file route alone, after the Charles route alone, and after both; every sentence is plain English a 12th grader reads easily.

## Format

Return paste-ready YAML:

```yaml
ending:
  scene_id: 3C
  when:
    - {fact_id: phase_two_conflict_plan_known, equals: true}
  text: >-
    <closing paragraph>
  marker: <end marker line>
```

Then the alternatives and the self-check. Keep your explanation short.
