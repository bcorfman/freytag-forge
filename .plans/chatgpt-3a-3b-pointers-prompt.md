Write new story text for the Continuity Initiative package
(`data/stories/continuity-initiative/`). Read first: `AGENTS.md` ("Writing
Narrator Rules", "Fixing a Scene"), `docs/markdown-story-authoring.md`
(cue_text, delivery_text), `docs/world-model-grounding.md`,
`storygame/runtime/candidate_matcher.py` (the exact matcher, including
`_SYNONYM_CLASSES`), and these files: `handoffs.yaml` (the Scene 3A and Scene
3B entries), `knowledge.yaml` (`k_sl_3a_*` and `k_sl_3b_*`, read the CURRENT
`action_evidence` groups, they were just widened), `plot.md` (Scenes 3A and 3B)
and `world.yaml`. Do not edit files; return text to paste.

## The problem

In live play, players of 3A and 3B act on the LAST step of the chain first and
the scene then runs to its timer. The game now shows a cue only after the step
behind it can be earned, so a scene's first screen can carry a cue for the first
step only. What is missing is a short closing sentence on each delivery that
names the next thing to act on, and one missing cue.

Fix it with story text only. A pointer is ONE short closing sentence at the end
of a `delivery_text` that names the next thing to act on. A cue is the short
hint shown before a step can fire. Both are SCENE DESCRIPTIONS, never commands
("A warning message blinks on the medical terminal.", not "Read the warning
message."). Every pointer already in the package is written this way.

### 3A chain (gate: `michelle_reached`, `detention_uprising_started`, `military_override_codes_available`)
- `k_sl_3a_a_r1` / `a_r2` -> `michelle_reached`. No requirement.
- `k_sl_3a_b_r1` / `b_r2` -> `behavioral_experiments_known`. Needs `michelle_reached`.
- `k_sl_3a_d_r1` / `d_r2` -> `military_override_codes_available`. Needs `michelle_reached` and `behavioral_experiments_known`.
- `k_sl_3a_c_r1` / `c_r2` -> `detention_uprising_started`. Needs `michelle_reached` and `military_override_codes_available` (c_r2 also `override_codes_deadline_known`).
Players typed: "Free the captives.", "Use the stolen radio.", "Use the official
access seal on the gate-status panel.", "Help Michelle organize the prisoner
escape.", and spent turns on the gate-status panel before Michelle and the
experiment records.

### 3B chain (bridge: `relay_open`, `brandon_confession_available`, `detention_locations_secured`, plus `human_security_control` or `charles_abandoned_rebecca`)
- `k_sl_3b_a_r1` / `a_r2` -> `human_security_control`. No requirement.
- `k_sl_3b_e_r1` -> `rebecca_office_reached`. Needs `human_security_control`.
- `k_sl_3b_b_r1` / `b_r2` -> `detention_locations_secured`. Needs `human_security_control` and `rebecca_office_reached`.
- `k_sl_3b_d_r1` / `d_r2` -> `charles_abandoned_rebecca`. Needs `human_security_control` and `detention_locations_secured`.
- `k_sl_3b_c_r1` / `c_r2` -> `relay_open`. Needs `human_security_control`, `charles_abandoned_rebecca`, `detention_locations_secured`.
Players went straight to the relay chamber and the broadcast relay, and never
did the false alarms, Rebecca's office, the site list or Charles's channel.

## Rules to keep

- A cue or pointer names a thing and a move. It never states the fact the move
  reveals.
- Use only things the story already has: names in `world.yaml` and nouns the
  `plot.md` text for 3A and 3B uses. Do NOT invent a person, place, record
  type, code or fact. If a sentence needs a thing that is not declared, say so
  and give your nearest alternative.
- The words in a pointer must be words the NEXT step's `action_evidence`
  matches, so the player's natural command fires it. Copy the current groups
  from `knowledge.yaml` into your answer and check each word against the matcher.
- The narration leak scan rejects a pointer that uses a multi-word alias or
  `action_evidence` phrase of a LATER reveal (`coded message`, `the supervisor`
  were rejected before). Use single words, declared `world.yaml` names, or
  story wording no reveal lists. After you choose a pointer, say which
  later-reveal phrases you avoided. A cue is exempt.
- 8th-grade reading level. Short, common words, one idea per sentence. A cue is
  one or two sentences. A pointer is ONE sentence.
- Kristin is "Kristin", Michelle is "Michelle", Brandon is "Brandon". Never "you".
- Keep every existing sentence and key fact in a `delivery_text`. Add the
  pointer as a new last sentence only. `must_convey` lists in `handoffs.yaml`
  must still hold.
- Only one reveal may match a command, unless two reveals set the same fact.
- Test commands follow AGENTS.md "Writing Player Input": imperative, verb plus
  object, no first person, no "do not", no waiting.

## Tasks

### A. Pointers (append to delivery_text in knowledge.yaml)

One closing sentence per reveal, naming the next thing to act on, so a player
who follows them reaches the bridge. Spread the next steps; do not send every
delivery to the same thing.

3A: `a_r1`, `a_r2` -> the experiment records or the medical level. `b_r1`,
`b_r2` -> the senior official (or the person holding the official access seal).
`d_r1`, `d_r2` -> Michelle and the uprising; do not give away that the codes are
about to expire if that is the fact `c_r2` reveals.
3B: `a_r1`, `a_r2` -> Rebecca's executive office. `e_r1` -> the approvals, or the
marked site list. `b_r1`, `b_r2` -> the executive screen with the channel marked
Charles. `d_r1`, `d_r2` -> the voice channel marked Brandon beside the broadcast
controls.

### B. Cue check (handoffs.yaml)

For each 3A and 3B cue, say whether its nouns match the evidence of the step it
cues. Where a cue names a thing the evidence does not match, give a replacement
(a description, one or two sentences). Keep a cue that works. Current cues:
- 3A `michelle_reached`: "The detention block opens onto rows of captives. A stolen radio crackles nearby."
- 3A `military_override_codes_available`: "A prisoner with an official access seal watches the gate-status panel cycle toward expiry."
- 3A `detention_uprising_started`: "Stolen radios crackle across the detention sector. Several cameras show no picture."
- 3A has no cue for `behavioral_experiments_known`; write one (it needs the experiment records or the medical level).
- 3B `human_security_control`: "Water-pressure warnings flash while doors open and close in empty service corridors."
- 3B `charles_abandoned_rebecca`: "The executive screen still carries a remote channel marked Charles. Security doors are sealing around the room."
- 3B `detention_locations_secured`: "A marked site list lies beside Rebecca's national network controls."
- 3B `relay_open`: "The relay chamber lies beyond the broadcast controls. Its access panel shows fresh tool marks."
- 3B `brandon_confession_available`: "A voice channel marked Brandon is queued beside the broadcast controls."
- 3B has no cue for `rebecca_office_reached`; write one.

### C. plot.md

If any pointer or cue adds wording that the 3A or 3B text in `plot.md` does not
carry, give one sentence for the matching sub-scene and say which paragraph it
follows. If none is needed, say so.

## Output

1. Text to paste, per file and key, changed lines only. For deliveries, only the
   new last sentence and the reveal id.
2. A table: every cue and pointer, the exact nouns it uses, and which next-step
   evidence group each noun matches, checked word by word against the matcher
   (apostrophe rule, synonym classes, negations, the one-match rule).
3. For each pointer, five commands a player might type after reading it; at
   least two per pointer must be ones that should NOT fire. Give the result for
   each.
4. Anything in this brief you could not satisfy, and why.

A sentence that is vague about the move is as bad as one that gives away the
answer.
