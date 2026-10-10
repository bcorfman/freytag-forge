Write new story text for the Continuity Initiative package
(`data/stories/continuity-initiative/`). Read first: `AGENTS.md` ("Writing
Narrator Rules", "Fixing a Scene"), `docs/markdown-story-authoring.md`
(cue_text, delivery_text, deliveries), `docs/world-model-grounding.md`,
`storygame/runtime/candidate_matcher.py` (the exact matcher, including
`_SYNONYM_CLASSES`), and these files: `handoffs.yaml` (read ALL entries, the 3A
and 3B ones show the shape and wording of a good cue; there is NO Scene 3C
entry yet), `knowledge.yaml` (`k_sl_3c_*`, read the CURRENT `action_evidence`
groups), `plot.md` (Scene 3C, and the 3B text before it) and `world.yaml`. Do
not edit files; return text to paste.

## The problem

Scene 3C is the last scene. It has no transition. Players should work through
its chain and read the ending, but in two live runs (six players) nothing past
the first step ever fired. The 3C prompt the narrator gets carries only the two
statements of step A, so the player is told nothing about Rebecca, the data
case, the pumps or the gates. Players typed escape commands ("Evacuate the
facility.", "Lead Michelle through the maintenance routes.") and the narrator
invented hidden exits, a nightstand and a project journal. After 14 turns the
timer printed the rest of the chain in one block.

Fix it with story text only: a cue for each step, and a pointer on each
delivery. A cue is the short hint shown before a step can fire. A pointer is ONE
short closing sentence at the end of a `delivery_text` that names the next thing
to act on. Both are SCENE DESCRIPTIONS, never commands ("A warning message
blinks on the medical terminal.", not "Read the warning message."). Every cue
and pointer already in the package is written this way.

### 3C chain (facts; each row is one or two reveals that set the same facts)
- A: `k_sl_3c_a_r1` (sends the evidence to networks) / `a_r2` (answers Charles's terrorist claim). Needs `broadcast_started` (set in 3B, always true on entry). Sets `truth_no_longer_containable`.
- B: `b_r1` (takes the data case from Rebecca) / `b_r2` (copies the archive beyond Rebecca's reach). Needs `truth_no_longer_containable`. Sets `rebecca_captured`, `charles_at_large`, `portable_archive_secured`.
- C: `c_r1` (restores power to the drainage pumps) / `c_r2` (releases the emergency surface gates). Needs `truth_no_longer_containable` and `rebecca_captured`. Sets `captives_reaching_surface`.
- D: `d_r1` (checks reports from detention sites) / `d_r2` (calls the families of the missing). Needs `truth_no_longer_containable` and `captives_reaching_surface`. Sets `national_network_fragmenting` or `community_rescue_efforts_begun`.
- E: `e_r1` (opens the recovered JANUS file) / `e_r2` (traces Charles's unknown location). Needs A, `captives_reaching_surface`, `national_network_fragmenting`, `charles_at_large`. Ends the story.
Where the player starts: Kristin is in the broadcast chamber with Michelle.
Rebecca is in the executive office holding the portable data case. Charles is
on a channel. The drainage pump controls are in the maintenance network with the
captives. Brandon is at the broadcast relay.

What players typed on turns 1 to 14: "Finalize my evidence broadcast." (fires A
in 2 of 3 runs, never in the third), "Evacuate the facility.", "Lead Michelle
through the hidden exit.", "Carry Michelle to safety.", "Open the access panel.",
"Examine the recovered JANUS file.", "Discuss the Phase Two plan with Michelle."
Nobody went for Rebecca or the data case. C and D need B first.

## Rules to keep

- A cue or pointer names a thing and a move. It never states the fact the move
  reveals.
- Use only things the story already has: names in `world.yaml` and nouns the
  `plot.md` text for 3C uses. Do NOT invent a person, place, record type, code
  or fact. If a sentence needs a thing that is not declared, say so and give
  your nearest alternative.
- The words in a cue or pointer must be words the NEXT step's `action_evidence`
  matches, so the player's natural command fires it. Copy the current groups
  from `knowledge.yaml` into your answer and check each word against the matcher.
- The narration leak scan rejects a pointer that uses a multi-word alias or
  `action_evidence` phrase of a LATER reveal (`coded message`, `the supervisor`,
  `phase two` were rejected before). Use single words, declared `world.yaml`
  names, or story wording no reveal lists. After you choose a pointer, say which
  later-reveal phrases you avoided. A cue is exempt. Do NOT use the words
  "Phase Two" or "Phase One" anywhere before step E.
- 8th-grade reading level. Short, common words, one idea per sentence. A cue is
  one or two sentences. A pointer is ONE sentence.
- Kristin is "Kristin", Michelle is "Michelle", Brandon is "Brandon". Never "you".
- Keep every existing sentence and key fact in a `delivery_text`. Add the
  pointer as a new last sentence only. Do not change any `statement`.
- Only one reveal may match a command, unless two reveals set the same fact.
- Test commands follow AGENTS.md "Writing Player Input": imperative, verb plus
  object, no first person, no "do not", no waiting.
- The ending is a story close. Step E needs no pointer.

## Tasks

### A. Deliveries and cues (handoffs.yaml)

A cue is shown only through a `deliveries` entry. 3C has none, so write one
entry per fact below, in the same shape as the 3B entries: `fact_id`,
`scene_id: 3C`, `source_kind`, `source_entity_id`, `must_convey` (two groups of
short phrases the narration will use), `fallback_text` (printed by the timer; it
must contain a phrase from each group), and `cue_text`. Use these facts and keep
each cue pointing at the step behind it:
- `truth_no_longer_containable` (step A). Cue: the broadcast is live and Charles is still talking over it.
- `rebecca_captured` (step B). Cue: Rebecca is leaving the executive office with the portable data case.
- `captives_reaching_surface` (step C). Cue: water is rising; the pump controls and the surface gates.
- `national_network_fragmenting` and `community_rescue_efforts_begun` (step D). One entry is enough if both reveals can point at it; say which.
- `phase_two_conflict_plan_known` (step E). Cue: a recovered file and Charles's last channel. Write the cue without the words "Phase One" or "Phase Two".
The game shows a cue only after the step behind it can fire, so write each cue
as if the earlier steps are done.

### B. Pointers (append to delivery_text in knowledge.yaml)

One closing sentence per reveal, naming the next thing to act on, so a player
who follows them reaches the ending. Spread the next steps; do not send every
delivery to the same thing.
A: `a_r1`, `a_r2` -> Rebecca or the data case. B: `b_r1`, `b_r2` -> the drainage
pumps or the surface gates. C: `c_r1` -> the surface gates; `c_r2` -> the
drainage pumps. D: `d_r1` -> the families; `d_r2` -> the reports from the
detention sites. For D, if the pointer would reach E, make it name the recovered
file or Charles's last channel without the words Phase One or Phase Two.

### C. plot.md

If any cue or pointer adds wording that the 3C text in `plot.md` does not carry,
give one sentence for the matching sub-scene and say which paragraph it follows.
If none is needed, say so.

## Output

1. Text to paste, per file and key, changed lines only. For deliveries, only the
   new last sentence and the reveal id. For handoffs, the full new entries.
2. A table: every cue and pointer, the exact nouns it uses, and which next-step
   evidence group each noun matches, checked word by word against the matcher
   (apostrophe rule, synonym classes, negations, the one-match rule).
3. For each pointer and cue, five commands a player might type after reading it;
   at least two per item must be ones that should NOT fire. Give the result for
   each. Include "Lead Michelle through the maintenance routes." and "Evacuate
   the facility." and say which step, if any, each fires.
4. Anything in this brief you could not satisfy, and why.

A sentence that is vague about the move is as bad as one that gives away the
answer.
