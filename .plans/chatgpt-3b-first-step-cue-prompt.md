Write new story text for the Continuity Initiative package
(`data/stories/continuity-initiative/`). Read first: `AGENTS.md` ("Writing
Narrator Rules", "Fixing a Scene"), `docs/markdown-story-authoring.md`
(cue_text, delivery_text), `docs/world-model-grounding.md`,
`storygame/runtime/candidate_matcher.py` (the exact matcher, including
`_SYNONYM_CLASSES`), and these files: `handoffs.yaml` (the Scene 3B entries),
`knowledge.yaml` (`k_sl_3b_*`, read the CURRENT `action_evidence` groups),
`plot.md` (Scene 3B) and `world.yaml`. Do not edit files; return text to paste.
This brief is the 3B twin of the 3A first-step cue brief that already landed.

## The problem

Scene 3B ("The Battle for the Broadcast") often runs to its timer. The player
is never led to the first step of the chain, the false alarms
(`k_sl_3b_a_r1` / `a_r2`, fact `human_security_control`). Three live replicates
of the full game (1A to 3B) all went straight for the broadcast, the relay or
Rebecca's office, and never fed JANUS false alarms.

What the recorded 3B turn-1 prompts carry:
- The SCENE block has only JANUS lines, the inspection console, "What presses
  on Kristin now: Feed JANUS false water and air alarms." and a few setting
  nouns. It has NO line about the broadcast, the relay or Rebecca's office.
  The earlier entry-text, bridge and objective edits did what they were meant to.
- The current cue for `human_security_control` is appended to every 3B
  narration: "An inspection console flashes water-pressure warnings while doors
  open and close in empty service corridors." The player sees it every turn and
  still ignores it. It reads as scenery. It names no person and gives no move.
- The player is a blind model that reads the whole transcript from 1A. By 3B it
  has been told "broadcast the truth and rescue the captives" (2C), and
  Michelle's message and the 3A text repeat the broadcast. Against that goal a
  console line is scenery.
- One replicate typed "command console" five times. The screen says
  "inspection console". The first narration reply had invented "command
  console". The matcher does not know that name, and it must not (it is an
  invented thing).

Fix it with story text only. Do not touch matching, rules or code. (A separate
Ringer task is widening a_r1's verbs with access, open and enter. Assume that
has landed.)

### 3B chain
- `k_sl_3b_a_r1` / `a_r2` -> `human_security_control`. No requirement.
  `action_evidence` a_r1: the verb group (trigger, set off, sound, raise,
  create, plant, feed, send, report, fake, stage, simulate, cause, start, trip,
  activate, use, reset, flood, overwhelm, trace, follow, exploit, overload,
  manipulate, spoof, falsify, inspect, examine, read, check, study, watch,
  monitor, look at, plus access, open, enter) and a noun group that includes
  inspection console, false/fake alarm(s), water-pressure alarm(s)/warning(s),
  ventilation alarm(s)/warning(s), empty service corridor(s), JANUS alert(s).
  a_r2: cycle, reroute, switch, bypass, open, close, flip... with unused
  door(s), door cycle(s), light cycle(s), corridor light(s), JANUS guidance.
- `e_r1` -> `rebecca_office_reached`. Needs `human_security_control`.
- `b_r1` / `b_r2` -> `detention_locations_secured`. Needs `human_security_control`
  and `rebecca_office_reached`.
- `d_r1` / `d_r2` -> `charles_abandoned_rebecca`. Needs `human_security_control`
  and `detention_locations_secured`.
- `c_r1` / `c_r2` -> `relay_open`. Needs `human_security_control`,
  `charles_abandoned_rebecca`, `detention_locations_secured`.

The 3B opening comes from `entry_text`, `objective` ("Overload JANUS with false
alarms"), plot 3B.1 and the cue above. Plot 3B.1 already says Kristin uses the
inspection console she accessed under the false cover to create false
water-pressure and ventilation alarms in empty outer service corridors.

## Hard requirement from the first attempt

A first attempt (cue A: "JANUS tracks Kristin. The inspection console in the
infrastructure corridors can send false water-pressure alarms into empty
service corridors.") matched the evidence nouns but FAILED
`tests/test_cue_text_safety.py`: `narration mentions protected knowledge
'janus'`. On the first turn of 3B the name JANUS is protected knowledge the
player has not earned, and a cue is checked on that turn. So the cue must NOT
contain the word JANUS, or any other name or alias of a later reveal. The
second sentence of that attempt (inspection console, infrastructure corridors,
false water-pressure alarms, empty service corridors) passed on its own and is
the part to keep. Keep the person hook, but say it without the name JANUS.
Words checked against the real first-turn scan and accepted: Kristin,
Michelle, Brandon, cameras, security, security cameras, guards, doors, the
facility, the security system. Refer to the tracker as the cameras, security,
or the guards (the 3B.1 plot Details line already names cameras and doors), not
as JANUS and not as the AI. Do not use any word you cannot show is safe; if you
are unsure, list it under "unverified" in your answer.

## Rules to keep

- A cue is a SCENE DESCRIPTION, never a command ("A warning message blinks on
  the medical terminal.", not "Read the warning message."). It names a thing and
  a place to act on. It never states the fact the move reveals.
- Use only things the story already has: names in `world.yaml` and nouns the
  `plot.md` text for 3B uses. Do NOT invent a person, place, record type, code
  or fact. In particular there is no "command console". The console is the
  "inspection console". If a sentence needs a thing that is not declared, say so
  and give your nearest alternative.
- The nouns in the cue must be nouns the `human_security_control` evidence
  matches (a_r1 or a_r2), so the player's natural command fires it. Check each
  word against the matcher (apostrophe rule, synonym classes, negations, the
  one-match rule).
- The cue should be a person-and-thing hook with a move: the cameras or
  security are watching a named person move by move (never "JANUS"), and the
  inspection console is the thing that can answer it. Use only people already in 3B (Kristin, Michelle, Brandon)
  and do not hand any of them a new action the plot does not give them.
- The narration leak scan rejects a cue-derived sentence that uses a multi-word
  alias or `action_evidence` phrase of a LATER reveal. A cue is exempt, but list
  any later-reveal phrases you avoided anyway.
- Do not point at Rebecca's office, the broadcast controls, the relay or the
  relay chamber. Those are later steps. The cue for `relay_open` and the site
  list cue must stay as they are.
- 8th-grade reading level. Short, common words, one idea per sentence. A cue is
  one or two sentences. Kristin is "Kristin". Never "you".
- A `handoffs.yaml` cue lives on a delivery that also has `must_convey` and
  `fallback_text` (the timer fallback). If you change a cue, keep those two
  intact. Do not add a new delivery unless you say what it adds and why.
- Test commands follow AGENTS.md "Writing Player Input": imperative, verb plus
  object, no first person, no "do not", no waiting.

## Tasks

### A. Replace the `human_security_control` cue (handoffs.yaml, Scene 3B)

Write 2 candidate cues (one or two sentences each) that make a player who reads
only the screen walk up to the inspection console and send false alarms.
Each must give one person the cameras or security are tracking and one thing to
act on, using nouns the evidence matches ("inspection console" is the safest).
Neither may contain the word JANUS. Candidate wording that worked on its other
half: "The inspection console in the infrastructure corridors can send false
water-pressure alarms into empty service corridors." (It is a capability, not
a command, and it names the console's place, as plot 3B.1 now does.)

### B. Check the 3B entry text and objective

Say whether `entry_text` or `objective` pulls the player toward anything but
the false alarms (for example "the broadcast"). If so, give a subtractive edit
(remove or reword), not an addition. Say where, if anywhere, the opening got
"trying to reach the broadcast controls": we cannot see the opening prompt, so
check `entry_text`, the `t_3a_3b` bridge text and the 3A text, and name any line
that could pull that way.

### C. plot.md

If a cue adds wording that plot 3B.1 does not carry, give one sentence and say
which paragraph it follows. If none is needed, say so.

## Output

1. Text to paste, per file and key, changed lines only.
2. A table: each candidate cue, the exact nouns it uses, and which `a_r1` / `a_r2`
   group each noun matches, checked word by word against the matcher.
3. For each candidate, a line saying every word is on the safe list above or
   is under "unverified". We will run the real first-turn test on it.
4. For each candidate, five commands a player might type after reading it; at
   least two must be ones that should NOT fire a 3B reveal. Give the result for
   each, including which other 3B reveal a command could also fire.
5. Your pick of the two candidates, and anything in this brief you could not
   satisfy, and why.

A sentence that is vague about where to go is as bad as one that gives away the
answer.
