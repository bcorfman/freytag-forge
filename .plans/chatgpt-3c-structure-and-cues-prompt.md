Write new story text for the Continuity Initiative package
(`data/stories/continuity-initiative/`). Read first: `AGENTS.md` ("Writing
Narrator Rules", "Fixing a Scene"), `docs/markdown-story-authoring.md`
(cue_text, delivery_text, deliveries), `docs/world-model-grounding.md`,
`storygame/runtime/candidate_matcher.py` (the exact matcher, including
`_SYNONYM_CLASSES`), and these files: `handoffs.yaml` (read ALL entries; the 3A
and 3B ones show the shape and wording of a good cue; there is still NO Scene 3C
entry), `knowledge.yaml` (`k_sl_3c_*`, read the CURRENT `action_evidence` groups
and `delivery_text`), `storylet-routes.yaml` (`SL-3C-A` to `SL-3C-E` and the
`resolution_*` events), `plot.md` (Scene 3C) and `world.yaml`. Do not edit files;
return text to paste.

This is the second round for 3C. Your first answer is already applied in part:
the eight closing pointer sentences are in `knowledge.yaml` and two sentences
are in `plot.md` 3C.4. The five `handoffs.yaml` entries were NOT applied. Read
"What we learned" before you write anything.

## What we learned (checked in code, this session)

1. Cue staging is switched off in resolution scenes (`engine.py`
   `_escalation_eligible`). 3C is a resolution scene. We will open that gate for
   cue staging only (not for Deadline escalation). That is an engine change; you
   do not write it.
2. A cue is chosen from facts the unfired events in `canonical_bridge_events`
   still lack. The 3C events are in `resolution_events`, which the cue code does
   not read. We will wire 3C cues so each step's fact is staged in order. You
   write the cue text; each cue is keyed to one fact.
3. A cue is rejected on the first scene turn if it contains protected
   knowledge. Your first answer used "JANUS records" and "recovered JANUS file"
   in cues, and `tests/test_cue_text_safety.py` rejected both ("narration
   mentions protected knowledge 'janus'"). Do NOT use "JANUS", "Phase One",
   "Phase Two" or "coded message" in any cue or pointer. Check the loader's
   protected terms in `storygame/runtime/narration_safety.py` and
   `knowledge.yaml` if unsure.
4. Two structural limits make some pointers false. We are fixing them in the
   data, as described next.

## The structure we are building (so write cues for THIS shape)

Steps A to E stay. Step C and step D change from "either reveal finishes the
step" to "both reveals are needed, in any order":

- A: `a_r1` / `a_r2`. Either one sets `truth_no_longer_containable`. (Unchanged.)
- B: `b_r1` / `b_r2`. Either one sets `rebecca_captured` and the archive facts. (Unchanged.)
- C is now TWO parts. C-pumps (`c_r1`: restore power to the drainage pumps, hold
  the barrier, lead the captives through the maintenance tunnel). C-gates
  (`c_r2`: release the emergency surface gates with the senior official's
  authorization). Each sets its own fact. `captives_reaching_surface` is set
  only when both are done.
- D is now TWO parts. D-reports (`d_r1`: check reports from detention sites).
  D-families (`d_r2`: call the families of the missing). Each sets its own fact.
  Step D is complete only when both are done. Step E needs step D complete.
- E: `e_r1` (open the recovered file) / `e_r2` (trace Charles's last signal).
  Ends the story. No pointer.

Cue shape: one cue per part, so SEVEN cues keyed to: A, B, C-pumps, C-gates,
D-reports, D-families, E. The game shows the cue for the first part that is
missing and can fire. When a part is done, the cue for the next missing part is
shown. We will map each cue to its fact id; give each cue a short slug
(`cue_a`, `cue_b`, `cue_c_pumps`, `cue_c_gates`, `cue_d_reports`,
`cue_d_families`, `cue_e`) and we will fill the fact ids.

Because a cue now names whichever part is still missing, a pointer on a C or D
reveal can be wrong: after the player has already done the other half, the
pointer would send them back. So:

- Keep the pointers on `a_r1`, `a_r2` (to Rebecca / the data case) and `b_r1`,
  `b_r2` (to the pumps / the gates). Re-check them against the new shape.
- Say whether the four pointers on `c_r1`, `c_r2`, `d_r1`, `d_r2` should be
  removed. We expect yes, because the cue now does that job. If you want one
  kept, give the reason and make it true whether or not the other half is done.

## Where the player starts and what they typed

Kristin is in the broadcast chamber with Michelle. Rebecca is in the executive
office with the portable data case. Charles is on a channel. The drainage pump
controls are in the maintenance network with the captives. Brandon is at the
broadcast relay. In two earlier live runs nothing past step A fired. Players
typed: "Finalize my evidence broadcast.", "Evacuate the facility.", "Lead
Michelle through the hidden exit.", "Carry Michelle to safety.", "Open the
access panel.", "Examine the recovered JANUS file.", "Discuss the Phase Two
plan with Michelle." The narrator invented hidden exits, a nightstand and a
project journal.

## Rules to keep

- A cue names a thing and a move. It never states the fact the move reveals.
  Cues are SCENE DESCRIPTIONS, never commands ("Water rises around the pump
  controls.", not "Restore the pumps.").
- Use only things the story already has: names in `world.yaml` and nouns the
  `plot.md` 3C text uses. The surface gates are in `plot.md` but have no entity
  in `world.yaml`. Say so and give your nearest alternative, or give the exact
  `world.yaml` addition you need as a separate line for review.
- The words in a cue must be words the matching reveal's `action_evidence`
  matches, so the player's natural command fires it. Copy the current groups
  into your answer and check each word against the matcher. Only ONE reveal may
  match a command.
- The cue must not contain a multi-word alias or `action_evidence` phrase of a
  LATER reveal, because the narration leak scan rejects it. Name the later-reveal
  phrases you avoided.
- Cues must pass the first-turn safety test: see point 3 above.
- 8th-grade reading level. Short, common words, one idea per sentence. A cue is
  one or two sentences.
- Kristin is "Kristin", Michelle is "Michelle", Brandon is "Brandon". Never "you".
- Test commands follow AGENTS.md "Writing Player Input": imperative, verb plus
  object, no first person, no "do not", no waiting.

## Tasks

### A. Seven cues (handoffs.yaml)

For each of the seven slugs, the full `deliveries` entry in the 3B shape:
`fact_id` (leave as `FILL`), `scene_id: 3C`, `source_kind`,
`source_entity_id`, `must_convey` (two groups of short phrases), `fallback_text`
(printed by the timer; it must contain a phrase from each group), `cue_text`.
Write each cue as if the earlier parts are done. Cue content:

- `cue_a`: the broadcast is live and Charles is talking over it. No "JANUS".
  Name something `a_r1` or `a_r2` matches (for example "independent networks",
  "national broadcast", "evidence package", "Charles's terrorist claim").
- `cue_b`: Rebecca is leaving the executive office with the portable data case.
- `cue_c_pumps`: water is rising around the drainage pump controls.
- `cue_c_gates`: the surface gates are shut and the captives are waiting. Use a
  phrase `c_r2` matches ("surface gates"). If the sentence cannot also name the
  senior official's authorization, say so.
- `cue_d_reports`: reports from other detention sites are coming in.
- `cue_d_families`: families of the missing are asking for word.
- `cue_e`: a recovered file is still closed, and Charles's last channel is
  still open. No "JANUS", no "Phase". Use a phrase `e_r1` or `e_r2` matches
  ("recovered document" is in the `e_r1` group; check it).

### B. Pointers (knowledge.yaml)

State what stays and what is removed, per the section above. Give any
replacement text as one last sentence for the reveal id.

### C. plot.md

If a cue adds wording the 3C text in `plot.md` does not carry, give one
sentence for the matching sub-scene and say which paragraph it follows. The two
3C.4 sentences from round one are already in; do not repeat them.

## Output

1. Text to paste, per file and key, changed lines only.
2. A table: every cue and kept pointer, the exact nouns it uses, and which
   reveal's evidence group each noun matches, checked word by word against the
   matcher (apostrophe rule, synonym classes, negations, the one-match rule).
3. For each cue, five commands a player might type after reading it; at least
   two per cue must be ones that should NOT fire. Give the result for each.
   Include "Lead Michelle through the maintenance routes." and "Evacuate the
   facility." and say which part, if any, each fires.
4. Anything you could not satisfy, and why.

A sentence that is vague about the move is as bad as one that gives away the
answer.
