Write new story text for the Continuity Initiative package
(`data/stories/continuity-initiative/`). Read first: `AGENTS.md` ("Writing
Narrator Rules", "Fixing a Scene"), `docs/markdown-story-authoring.md`
(cue_text, delivery_text), `docs/world-model-grounding.md`,
`storygame/runtime/candidate_matcher.py` (the exact matcher, including
`_SYNONYM_CLASSES`), and these files: `handoffs.yaml` (the Scene 3A entries),
`knowledge.yaml` (`k_sl_3a_*`, read the CURRENT `action_evidence` groups),
`plot.md` (Scene 3A) and `world.yaml`. Do not edit files; return text to paste.

## The problem

Scene 3A ("Reaching Michelle") often runs to its timer. The player is never led
to Michelle, the first step of the chain. A live narrator probe replayed the
3A opening turn 12 times per case and read every reply. On the neutral command
"Search the detention sector." Michelle was named in 2 of 12 replies as the game
is today, 0 of 12 with the two earned 2C lines removed (the change now applied),
and 1 of 12 with a route-only replacement line. So on a plain first turn the
narration does not lead the player to Michelle in any case. The 3A cue for
`michelle_reached` is "The detention block opens onto rows of captives. A stolen
radio crackles nearby." It names no person, so a player cannot tell who is on
the radio or where to go.

Fix it with story text only. Do not touch matching, rules or code.

### 3A chain
- `k_sl_3a_a_r1` / `a_r2` -> `michelle_reached`. No requirement. Current
  `action_evidence` for a_r1: verbs look, search, check, examine, inspect, read,
  study, find, trace, follow, enter, listen, free, help, use, organize,
  coordinate, rescue; nouns Michelle, stolen radio(s), coded announcement(s),
  holding block(s), captives, prisoners, prisoner escape, detention block. a_r2:
  verbs ask, question, talk, speak, tell, press, discuss, inquire, probe,
  consult, listen, hear; nouns Michelle, other site(s), the sites.
- `b_r1` / `b_r2` -> `behavioral_experiments_known`. Needs `michelle_reached`.
- `d_r1` / `d_r2` -> `military_override_codes_available`. Needs `michelle_reached`
  and `behavioral_experiments_known`.
- `c_r1` / `c_r2` -> `detention_uprising_started`. Needs `michelle_reached` and
  `military_override_codes_available`.

The 3A opening the player reads comes from the scene's `entry_text` and
`objective` ("Reach Michelle and join the uprising."), `plot.md` Scene 3A.1, and
the cue above. Plot 3A.1 already says Michelle speaks into a stolen radio and
coordinates prisoners through coded announcements.

## Rules to keep

- A cue is a SCENE DESCRIPTION, never a command ("A warning message blinks on
  the medical terminal.", not "Read the warning message."). It names a thing and
  a place to act on. It never states the fact the move reveals.
- Use only things the story already has: names in `world.yaml` and nouns the
  `plot.md` text for 3A uses. Do NOT invent a person, place, record type, code
  or fact. If a sentence needs a thing that is not declared, say so and give
  your nearest alternative.
- The nouns in the cue must be nouns the `michelle_reached` evidence matches
  (a_r1 or a_r2), so the player's natural command fires it. Check each word
  against the matcher (apostrophe rule, synonym classes, negations, the
  one-match rule).
- The narration leak scan rejects a cue-derived sentence that uses a multi-word
  alias or `action_evidence` phrase of a LATER reveal. A cue is exempt, but
  list any later-reveal phrases you avoided anyway.
- Do not point at Rebecca's office, the broadcast controls or the relay. The
  2C lines that pulled that way were removed on purpose.
- 8th-grade reading level. Short, common words, one idea per sentence. A cue is
  one or two sentences. Kristin is "Kristin", Michelle is "Michelle". Never
  "you".
- A `handoffs.yaml` cue lives on a delivery that also has `must_convey` and
  `fallback_text` (the timer fallback). If you change a cue, keep those two
  intact. Do not add a new delivery unless you say what it adds and why.
- Test commands follow AGENTS.md "Writing Player Input": imperative, verb plus
  object, no first person, no "do not", no waiting.

## Tasks

### A. Replace the `michelle_reached` cue (handoffs.yaml, Scene 3A)

Write 2 candidate cues (one or two sentences each) that make a player who reads
only the screen walk toward Michelle. Each must name Michelle or the radio
voice as a person and give one place or thing to act on.

### B. Check the 3A entry text and objective

Say whether `entry_text` or `objective` pulls the player toward anything but
Michelle. If so, give a subtractive edit (remove or reword), not an addition.

### C. plot.md

If a cue adds wording that plot 3A.1 does not carry, give one sentence and say
which paragraph it follows. If none is needed, say so.

## Output

1. Text to paste, per file and key, changed lines only.
2. A table: each candidate cue, the exact nouns it uses, and which `a_r1` / `a_r2`
   group each noun matches, checked word by word against the matcher.
3. For each candidate, five commands a player might type after reading it; at
   least two must be ones that should NOT fire a 3A reveal. Give the result for
   each, including which other 3A reveal a command could also fire.
4. Your pick of the two candidates, and anything in this brief you could not
   satisfy, and why.

A sentence that is vague about where to go is as bad as one that gives away the
answer.
