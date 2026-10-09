# ChatGPT Desktop prompt: does Scene 3B still make sense? (2026-10-08)

Paste everything below the line into a FRESH ChatGPT Desktop chat with the
project open. This is an evaluation, not a rewrite. Do not apply anything from
the answer until Brandon has read it.

---

You have the whole freytag-forge project. Read, do not edit:
`data/stories/continuity-initiative/plot.md` (Scenes 3A, 3B, 3C and the
Scene 2C to 3A bridge), `knowledge.yaml` (`scene_frames` for 3A, 3B, 3C;
`k_scene_3b_entry`; every `k_sl_3b_*`), `handoffs.yaml` (3B entries),
`pacing.yaml` (`t_3a_3b`, `t_3b_3c`), `world.yaml` (`broadcast_relay`,
`broadcast_chamber`, `executive_office`, `security_corridors`), and
`AGENTS.md` ("Fixing a Scene").

## Why I am asking

Scene 3B has one stated purpose in two different wordings, and I worry the
story no longer hangs together.

- Old wording (still in `scene_frames` and `k_scene_3b_entry`): the objective
  is to "Overload JANUS and seize the broadcast", and "the broadcast relay is
  the immediate contested objective". `location_id` for 3B is `broadcast_relay`.
- New wording (the plot objective since PR 533): "Overload JANUS with false
  alarms". Plot 3B.1 says Kristin feeds JANUS false water-pressure and
  ventilation alarms and cycles unused doors, which forces human operators to
  take control.

In live play, players read the old wording and go straight for the relay (the
last step), never doing the false alarms (the first step). The game cannot fire
the relay step until four earlier steps are done: `human_security_control`,
`rebecca_office_reached`, `detention_locations_secured`,
`charles_abandoned_rebecca`. I need to know whether I should keep the relay as
the scene's goal, make the false alarms the goal, or state both in a way that
stays true.

## History of the wording (read this before judging)

Origin: the original plot (commit a9b49e8) already had the 3B objective
"Overload JANUS and seize the broadcast". The bridge text "fought upward toward
Rebecca's office and the broadcast levels" and the `entry_text` "Above the
fighting, Rebecca's executive office and the external broadcast relay waited
at the end of corridors that JANUS watched move by move." were added later,
when the canon journey was made playable (2e238cd and f0a292d; check
`git show` on them). The plot steps themselves (3B.1 false alarms, 3B.2
Rebecca's office, 3B.3 Charles's betrayal, 3B.4 Brandon at the relay) never
changed.

Why we changed wording: we run a blind player (a model that sees only the game
screen and types commands) through every scene, and measure whether it leaves
each scene by playing the plot (not by the timer). In 3B it never did. The
whole chain starts at the false alarms (`k_sl_3b_a_r1/a_r2`); every later step
requires them. Players instead typed "Reach/Seize the external broadcast
relay" or "Reach Rebecca's executive office" from turn 1, which cannot fire.

Changes so far, all subtractive (remove the line that pulls the wrong way):

1. PR 532 (c392947): `entry_text` rewritten to the cue's own words: "Alarms
   layered over alarms as the facility fought to predict its attackers.
   Water-pressure warnings flashed on the inspection console while doors
   opened and closed in empty service corridors that JANUS watched move by
   move." Also widened the verbs the false-alarm step accepts. Result: 3B
   still timer x3; players now saw the warnings but still typed "Reach the
   secured broadcast office".
2. PR 533 (a6f3fbd): bridge text changed to "...fought upward through the
   security corridors." (office and broadcast levels removed) and the plot
   objective changed to "Overload JANUS with false alarms". Result: 3B went
   from 0 of 3 to 1 of 3 by play. Players now touched the inspection console;
   two reached Rebecca's office and read the approvals and site list.
3. PR 535 (2ee09ec): widened the Charles-channel step so natural phrasing
   fires it. Result: 3B was played to completion in 2 of 2 replicates that
   reached it.
4. Latest run (a628561): 3B timer x3 again. Every player spent all 14 turns on
   the relay (the last step) and none tried the false alarms.

What we did NOT change, and why it matters: `knowledge.yaml` `scene_frames`
for 3B still says situation "the group needs an opening to reach the
broadcast relay" and pressure "Overload JANUS and seize the broadcast", and
`k_scene_3b_entry` still says "The broadcast relay is the immediate contested
objective." The narrator reads these, so its text keeps saying "they need to
overload JANUS and seize the broadcast relay". Also 3B `location_id` is
`broadcast_relay`. So the plot objective and the frame now disagree.

The worry: by trimming relay and office mentions to fix player behaviour, we
may have made the story read as if the relay no longer matters until the very
end, or left the scene with two goals that do not connect. Judge that
directly. Be fair to both sides: the edits were made to fix a test result, so
tell me where they helped the story, where they hurt it, and where they were
neutral.

## What to do

Judge the scene twice, then compare.

### Perspective 1: "Seize the broadcast relay" is the goal

1. Walk 3B.1 to 3B.4 as a story. Which beats serve this goal and which feel
   like detours? Does Rebecca's office (3B.2) and Charles's betrayal (3B.3)
   still earn their place?
2. Does a player who goes straight to the relay contradict the plot? What
   would a faithful story do if they tried it at turn 1 (blocked by what, and
   how does the narration say so without giving the plot away)?
3. Does the 3A bridge text and the 3C entry text still agree with this goal?

### Perspective 2: "Overload JANUS with false alarms" is the goal

1. Same walk. Which beats serve this goal and which feel like detours? Does
   the relay (3B.4) read as a payoff or as a new, unrelated goal?
2. Is the false-alarm step a satisfying first beat for a player who has only
   the scene text and the cue "Water-pressure warnings flash while doors open
   and close in empty service corridors."?
3. Does the bridge text and the 3C entry text still agree with this goal?

### History check

- Compare the original wording (a9b49e8) with today's. Did the PR 532 and 533
  edits change what the scene is about, or only what the narrator tells the
  player at the start? Name any plot fact, motive or setup that the trimmed
  lines used to carry and that the story now lacks.
- Does the 3A to 3B bridge still set up Rebecca's office and the relay for
  3B.2 and 3B.4, or does the player arrive at them with no setup?

### Compare

- Which single sentence of purpose is true for the whole scene? Write it in
  one plain sentence, plot-neutral, usable as a scene frame `pressure`.
- Is there a version where both are true (alarms are how you get an opening;
  the relay is where the opening leads)? If so, say it in two short sentences,
  one for `situation` and one for `pressure`, written at an 8th-grade reading
  level (these reach a small narrator model).
- List every line in the files above that contradicts your chosen purpose.
  Give file, key or line, the line as it stands, and say whether it is a
  contradiction, a pull toward the wrong step, or fine. Do not propose edits
  to plot facts, only to wording.

## Rules

- Use only places, people and things the story already has. Invent nothing.
- Do not change which facts a step establishes or the order of the chain.
- Do not suggest a runtime or engine change. Story wording only.
- Be blunt. If the story is incoherent as it stands, say so first and say why
  in three sentences or fewer, before the detail.
- End with a table: line, file, verdict (contradiction / pull / fine), and a
  one-line fix idea.
