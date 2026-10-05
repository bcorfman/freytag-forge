# ChatGPT Desktop prompt: Scene 1B reveal wording (2026-10-04)

Paste everything below the line into a FRESH ChatGPT Desktop chat with the
project open. Score the answer with the real matcher on held-back commands
before applying it. If it misses, fix this prompt and start a fresh chat; do
not hand-edit the answer.

---

You have the whole freytag-forge project. Edit story data for Scene 1B of the
Continuity Initiative package (`data/stories/continuity-initiative/`). Read
first: `AGENTS.md` ("Writing Narrator Rules", "Fixing a Scene"),
`docs/markdown-story-authoring.md` (cue_text, action_evidence, delivery_text),
`docs/world-model-grounding.md`, `storygame/runtime/candidate_matcher.py` (the
exact matcher, including `_SYNONYM_CLASSES`), and the 1B entries in
`handoffs.yaml`, `knowledge.yaml` (`k_sl_1b_*`), `plot.md` (Scene 1B) and
`world.yaml`. Do not edit files; return text to paste.

## The problem

Three live playtests showed players cannot finish 1B from the screen. The
cues name a thing but not the move, and one cue points at a step the player
cannot do yet. 1B needs only TWO player moves:

1. Step 1: show the man watching Kristin Michelle's photograph (or ask him
   about it). `k_sl_1b_b_r1` or `_r2`. He names himself, the missing are alive.
2. Step 2 (needs step 1): follow Brandon through the maintenance gate, or ask
   him to use the gate code. `k_sl_1b_c_r1` or `_r2`.

Players typed "Approach the watcher.", "Question the watcher.", "Enter the
storm drain.", "Follow the tunnel." Nothing matched, so the narrator invented
filler. The storm-drain cue also appeared around turn 5, before step 1 could
be done.

## Rules to keep

- Before step 1 the man is not named. No cue or pre-step-1 text may say
  "Brandon". Call him "the man watching Kristin" (the project's label for an
  unnamed man). "man" and "watcher" stay usable in commands; "stranger" may be
  added.
- A cue points at a thing and a move. It never states the fact the move
  reveals: not that he is Brandon, not that the missing are alive, not that he
  can open the gate. Cues are one or two short sentences at an 8th-grade level.
- The photograph is hidden under the bench; `k_sl_1b_a_r2` (looking at it) is a
  different reveal and must keep firing on "Examine the photograph."
- Only one reveal may match a command. Check every group against
  `_SYNONYM_CLASSES`: "go through", "look into", "check" and similar pull in
  "search" and "examine". Looking at a gate must not leave the scene.
- `earn_when` is one short fragment listing objects and moves the way a player
  names them, using on-screen nouns. The 1A card reveal is the working model:
  "searches the drawer, the gap in the drawer, or the space beneath it".
  Probes showed vague or short fragments matched worse.
- Test commands follow AGENTS.md "Writing Player Input": imperative, verb plus
  object, no first person, no "do not", no waiting.
- "maintenance gate" (aliases gate, secured gate) and "storm drain" (aliases
  storm-drain, drain, tunnel) will be added to `world.yaml` as things; you may
  name them in cues and commands. Do not edit `world.yaml`.

## Tasks

A. New `brandon_identified.cue_text`: the man watching Kristin, Michelle's
   photograph, a hint at showing it to him.
B. New `park_pursuit_resolved.cue_text`: the tactical team only. No storm
   drain, no gate. One sentence.
C. Confirm `missing_may_be_alive.cue_text` should be deleted (the list it names
   does not exist). No new text.
D. Final `earn_when` and `action_evidence` for `k_sl_1b_b_r1` and `_r2`.
   - Fire r1 only: "Show the man Michelle's photograph.", "Show the photograph
     to the man.", "Hold up the photograph to the watcher.", "Ask the man about
     the photograph.", "Question the man about Michelle's photograph.",
     "Approach the man with the photograph.", "Confront the stranger with the
     photo."
   - Fire r2 only: "Question the man about Michelle.", "Ask the watcher about
     Michelle.", "Press the man about Michelle."
   - r1 must not fire: "Examine the photograph.", "Question the man.",
     "Approach the watcher.", "Search the bench.", "Compare the token to the
     number sequence."
   - No LOOK or READ class phrases in r1 (clash with `k_sl_1b_a_r2`).
E. Final `earn_when` and `action_evidence` for `k_sl_1b_c_r1` and `_r2`.
   - Fire r1 only: "Follow Brandon through the maintenance gate.", "Follow
     Brandon into the storm drain.", "Go through the gate.", "Enter the storm
     drain.", "Run through the gate with Brandon.", "Head into the tunnel.",
     "Take the tunnel."
   - Fire r2 only: "Ask Brandon to use the gate code.", "Tell Brandon to open
     the gate with the code.", "Ask Brandon for the gate code."
   - Neither fires: "Search the storm drain.", "Examine the gate.", "Look into
     the tunnel.", or any Task D command. If a command above cannot work
     without pulling in "search"/"examine", say so and offer the nearest
     alternative.
F. Add one closing sentence to the `delivery_text` of `k_sl_1b_b_r1` and
   `_r2` pointing at the next move. Draft: "A tactical team is closing across
   the park. Brandon points to a secured maintenance gate beside the storm
   drain." Reword freely; keep the existing sentences and key facts; do not
   state step 2's result.
G. One sentence for plot.md Scene 1B.2 that carries the same fact as the Task A
   cue, so plot and cue agree. Also check `handoffs.yaml` `must_convey` for
   `brandon_identified` and `park_pursuit_resolved` still holds with your
   delivery text.

## Output

1. YAML or text to paste, per file and key, changed lines only.
2. A table: every command above, which reveal fires, checked word by word
   against the matcher (apostrophe rule, synonym classes, negations, the
   one-match rule). Mark any you could not satisfy.
3. Five held-back commands you invent per step, with results. At least two per
   step must be ones that should NOT fire.
4. Two sentences on why you chose the phrases.

Other wordings will be tested after you answer. A group that is too wide is as
bad as one that is too narrow.
