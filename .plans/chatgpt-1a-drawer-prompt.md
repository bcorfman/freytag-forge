Fix how Scene 1A of the Continuity Initiative package
(`data/stories/continuity-initiative/`) lets a player find Michelle's memory
card. Read first: `AGENTS.md` ("Writing Player Input", "Writing Narrator Rules",
"Fixing a Scene"), `docs/world-model-grounding.md`,
`storygame/runtime/candidate_matcher.py` (the exact matcher, including
`_SYNONYM_CLASSES`, the negation words and the one-match rule), `plot.md`
(Scenes 1A.1 to 1A.4), `knowledge.yaml` (`k_sl_1a_*`; read the CURRENT
`action_evidence`) and `handoffs.yaml` (the 1A entries and their cues). Do not
edit files; return text to paste. Run the real matcher for every claim.

## What happened

The step that matters: the card is taped beneath the drawer
(`k_sl_1a_b_r0`, "Kristin finds Michelle's memory card taped beneath the
drawer and takes it with her"). Scene 1A cannot end until the player earns it.
Its evidence is three groups; a command must hit one phrase from each:

```text
verbs:   look, search, inspect, check            (examine is covered by the matcher's look/check class)
where:   under, beneath, underside, gap
thing:   drawer, KMS, workstation
```

The 1A cue (shown on turn 1) reads: "Kristin's initials, KMS, are carved into a
drawer of Michelle's workstation. The drawer rides high in its frame, leaving a
thin gap along its lower edge. Kristin's laptop is in her truck outside."

Three live blind-player runs on staging (all nine scenes). The card was found
on turn 3 in one run and only by the 13-turn timer in the other two:

| Run | Turn | Command | Fired |
|---|---|---|---|
| r1 | 1 | Inspect the workstation. | nothing needed (cue shows) |
| r1 | 2 | Open the KMS drawer. | nothing; narrator: "stapler, spare batteries, pens ... nothing else out of the ordinary" then invented a note ("Meet me at the old warehouse at midnight") on turn 3 |
| r1 | 3 | Take the note. | nothing (the note is invented) |
| r3 | 1 | Inspect Michelle's workstation. | nothing needed |
| r3 | 2 | Open the high-riding drawer. | nothing; narrator: "she does notice that the drawer is now open" |
| r3 | 3 | Examine the drawer's lower edge. | nothing; narrator invented "a small piece of paper stuck between the drawer and the workstation" |
| r3 | 4 | Pull the small piece of paper free. | nothing; invented note again |
| r2 | 1 | Inspect the workstation. | nothing needed |
| r2 | 2 | Open the KMS drawer. | nothing; "nothing else out of the ordinary" |
| r2 | 3 | Inspect the gap beneath the KMS drawer. | **k_sl_1a_b_r0 fired** (turn 3) |

So the working command names the gap AND says "beneath". The players who typed
"Open the ... drawer" and "Examine the drawer's lower edge" (words straight from
the cue) fired nothing. Both players then followed an INVENTED paper note to a
made-up warehouse or oak tree, because the narrator had no card to give and
filled the gap with a note. After the timer the card was handed over by the
fallback text (`first_shown` turn 13).

The next steps (1A.2 reading the files, 1A.3 the recording) are fine: they fire
once the card is earned.

## The task

1. **Evidence.** Add words so the natural commands above fire `k_sl_1a_b_r0`,
   for example for the "where" group: "lower edge", "edge", "underneath",
   "bottom"; and decide for the verbs whether "open", "pull", "lift", "feel"
   belong ("Open the KMS drawer." has no "where" word at all today). Say what
   each addition does to the one-match rule against the other 1A reveals
   (`k_sl_1a_a_r1` kitchen/back door; `k_sl_1a_b_r1`/`r2`/`d_r1` card files and
   recording, which need the card first; `k_sl_1a_c_r1`/`r2`). Be strict: a bare
   "Open the KMS drawer." that finds the card removes the small puzzle (the plot
   says the drawer is not opened and the card is beneath it). Decide whether
   "open the drawer" should fire, should not, or should lead the player to the
   gap through the narration, and justify it. Give a recommendation.
2. **The invented note.** The narrator had nothing to give for "open the drawer"
   and wrote a note. That is the real harm: it sends the player off-story. Use
   only proven techniques from `AGENTS.md` and `docs/world-model-grounding.md`,
   in this order, and say which you chose and why: (a) a better cue or reveal
   handoff for the drawer (story text; Brandon wants it written in the 3A/3B
   cue style: a scene description naming a thing and a move, never a command);
   (b) a world fact for the drawer. `michelle_drawer` in `world.yaml` already
   declares `contents: [pens, binder clips, stapler, spare batteries]` and is
   `openable`; the narrator listed exactly those on the "Open the ... drawer"
   turn, and invented the note only one or two turns later when the player
   asked about the edge or the paper. Say whether the grounding guide offers a
   way to declare what is NOT in the drawer, or to name the gap as a thing, and
   whether the gap or the card (`memory_card`, hidden?) needs a declared place;
   (c) a narrator rule only if (a) and (b) cannot work. Say plainly what you
   checked. Do not propose a new mechanism if one of these covers it.
3. **Neighbours.** Check these still behave: "Search the kitchen for signs of a
   struggle." (`k_sl_1a_a_r1`), "Read Michelle's memory card." and "Insert
   Michelle's memory card into my laptop." (after the card), "Evacuate the
   house.", "Open the back door." (nothing).

## Rules to keep

- ONE reveal may match a command. Report every double match.
- Add words only; do not remove or reorder existing words.
- Use only things the story has: `world.yaml` names and nouns in `plot.md` 1A.
  No invented person, place, record or paper.
- Cue text: do not say what the move reveals. 8th-grade reading level, one idea
  per sentence, Kristin by name (never "you").
- Commands follow `AGENTS.md` "Writing Player Input": imperative, verb plus
  object, `my` for the player's own things, no "do not", no waiting.
- Do not put a later-scene name or "Phase One/Two" into 1A text.

## Output

1. YAML or text to paste per file and key, changed lines only.
2. A table of at least 40 commands (the ones above, the neighbours, and your own
   adversarial ones, close wording that must NOT fire and wording that should)
   with the matcher result before and after.
3. Every double match after your change and what you did.
4. For item 2: the technique, what you checked in the plan, the grounding guide
   and earlier scene fixes, and why the others do not apply.
5. Anything you could not satisfy, and why.
