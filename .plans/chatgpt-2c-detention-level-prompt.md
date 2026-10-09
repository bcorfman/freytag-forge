# ChatGPT Desktop prompt: let scene 2C name the detention level (2026-10-09)

Paste everything below the line into ChatGPT Desktop with the repo files
attached or readable (`data/stories/continuity-initiative/plot.md`,
`knowledge.yaml`, `world.yaml`, `docs/world-model-grounding.md`,
`storygame/runtime/narration_safety.py`). Do not edit files. Answer in the
format at the end.

---

## The problem

In live play of scene 2C, the narrator sometimes writes "detention level".
The game rejects that turn as a leak: "narration mentions an unavailable entity
'detention level'". It happened four times in one run. Each rejected turn
costs the player a turn, and one run never left 2C because the timer turn was
itself rejected.

The place `detention_level` is in `world.yaml` (parent `regional_facility`).
The leak scan in `narration_safety.py` lets narration name a place when either
(a) the player has earned a reveal that lists it (2C: only after
`k_sl_2c_d_r1` or `d_r2` is earned, which lists `holding_block`, whose parent
is `detention_level`), or (b) the **scene frame `situation` text or the current
beat's text already names it** (see `authored_scene_text` and
`_contains_optional_plural`; "level" and "levels" both count).

The 2C frame `situation` today is:

> The command levels during an accelerating crisis: private executive channels,
> transfer orders, and a maintenance network. Security activity is increasing
> faster than Kristin can explain, and Michelle's phrasing may be hidden
> somewhere in the traffic.

The 2C plot text says "sealed detention sectors" (2C.4, 2C.5) and "partly
unsecured holding block", but never "detention level" or "detention levels".

The narrator says "detention level" because players type things like "Override
the termination order on the detention console." and "Search the corridor for
Michelle." Michelle is held on the detention level (see 3A).

## What I want

The smallest change to **story text** so that scene 2C names "detention
level" or "detention levels" (route (b)), without pulling players off the 2C
chain. The 2C chain is: read the transfer orders, check the copied files,
then read Michelle's coded message.

## Rules that already cost us playtime

- Take a pulling line out. Do not add a new one. In 3B, naming the office and
  the relay in the opening made players go there on turn 1 and skip the first
  step.
- Players already type "Enter the next level." and "Follow Michelle's
  maintenance route." in 2C. A new sentence must not make the detention level
  look like somewhere to go now. It should read as a fact about the facility,
  not a destination.
- The text reaches a small narrator model. Write at an 8th-grade reading
  level: short common words, short sentences, one idea per sentence. No
  project words (`entity`, `grounding`, `candidate`).
- Do not use "Rebecca", "relay" or "broadcast" in the new text. Do not name
  anything from a later scene.
- Do not state anything the story has not said by 2C. Do not change the plot.

## Questions

1. Give three alternatives. Each is a small edit to **one** of: the 2C frame
   `situation`, the 2C `Details:` line of one beat, or one sentence of a 2C
   beat. Show the exact old line and the exact new line, and say which file
   and line it is in. Each new line must contain "detention level" or
   "detention levels".
2. For each alternative, say which one the scan reads (frame `situation` or
   the beat text), and check that against `narration_safety.py`. If a beat
   only counts while that beat is the current one, say so and say which
   alternative is safest for that reason.
3. For each alternative, say how likely it is to send players to the
   detention level instead of the 2C chain, and why. Do not claim certainty;
   we will test.
4. Say which one you would pick. If you think none is safe, say so and name
   the smallest change you would make instead. Do not suggest a code change.
5. Anything in my reading above that is wrong? Check the quotes against the
   files.

## Format

Four short sections: **Alternatives** (a table: file and line, old, new),
**Scan check**, **Pull risk**, **Pick**. No preamble.
