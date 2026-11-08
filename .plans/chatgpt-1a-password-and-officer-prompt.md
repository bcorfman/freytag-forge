# ChatGPT prompt: two misses in scene 1A (wrong device for "the password"; the wrong person answers the officer)

Paste everything below the line into ChatGPT Desktop. It has the project files open, so it reads them itself. Bring the plan back to Claude Code,
which applies approved changes through Ringer tasks (tests first) and probes them.

---

## Task

Brandon played scene 1A live and hit two misses, recorded below. **Establish the causes and the evidence yourself** from the recorded prompts, the story
package and the code, then write one plan that proposes fixes at the source, in the order `docs/scene-fixing-guide.md` ranks them. Do not assume one cause
covers both misses. For each proposed change, say whether it is a story-text proposal for ChatGPT Desktop to author (Brandon approves), a story-data
edit, or an engine change for Claude Code to build through Ringer. Name the earlier fixes and decisions you checked. Say what you could not establish.

Write the plan to `.plans/1a-password-and-officer-plan.md`. Edit it in place on later rounds; do not regenerate it.

## What to read first

- `AGENTS.md`, `docs/scene-fixing-guide.md`, `docs/world-model-grounding.md` (and the detail files it indexes), `docs/narrator-writing-guide.md`,
  `docs/contributor-guide.md`, `docs/player-input-guide.md`, the relevant parts of `docs/PRD.md`
- `.plans/lead-up-contradictions-plan.md` and `.plans/lead-up-contradictions-prereg.md` (commit `f7cbf7b3` fixed a character-list omission for scene 3A)
- The story package: `data/stories/continuity-initiative/` (`plot.md` scene 1A and Principal Characters, `world.yaml`, `storylets.md`, `knowledge.yaml`)
- Code: `storygame/runtime/reference_resolution.py`, `storygame/runtime/cloudflare.py` (`_character_lines`, `_is_present`, `_placement_rules`,
  `_owner_rules`, `assemble_turn_prompt`), `storygame/runtime/engine.py` (`turn`), `storygame/story_package/loader.py` (`_parse_characters`),
  `storygame/runtime/recent_cue.py`, `storygame/runtime/knowledge.py` (`_entity_surface_forms`)

## The recorded evidence

| Path | What it is |
| --- | --- |
| `.plans/1a-password-and-officer/transcript.md` | Brandon's 1A session, verbatim |
| `.plans/1a-password-and-officer/replay_1a.py` and `replay_1a-output.txt` | Network-free replay of that session. Each narrator reply is stubbed with the text Brandon saw; the output has the full user prompt the narrator received each turn, world state before and after each turn, and the composed result. No model was called, so the narrator replies in the output are the stubs, not new samples |
| `.plans/1a-password-and-officer/check_scope_and_characters.py` and `...-output.txt` | `package.characters`, the reference resolver's in-scope things for 1A, and resolver results for three commands |

The replay reproduces where the appended authored lines landed in Brandon's session (patrol arrival after "type the password into michelle's phone",
the officer entering after "turn off the phone and put it in my pocket", the patrol leaving after the last command).

## What was observed

**Miss 1.** After the phone showed a password prompt, "type in the password" was narrated as "the laptop screen flickers to life", and the narration then
went on to scroll through files. Brandon's expected behavior: with no named object, the default is the thing the narration just mentioned; when that is
potentially ambiguous the game asks a clarifying question ("Do you mean X or Y?"). The clarifying question already exists in the game. The next command,
which named Michelle's phone, was narrated correctly.

**Miss 2.** After the officer entered and was addressed ("officer, hello", answered correctly), "officer, do you know where Dr. McGehee is?" was answered
by "Michelle's neighbor, Mrs. Jenkins", from across the street. Brandon's position: even if the officer had left, Mrs. Jenkins should not answer instead
of the officer. He asked whether the game had recorded the patrol leaving before the turn narrated it, or whether this is a character-reference problem.

## Claude Code's observations from the replay (unverified; check each against the files, do not take them as established)

- In the replay, before the last command is sent, the world model has the officer in the kitchen together with Kristin. `patrol_departed` is asserted
  only after that turn.
- In every replayed prompt, the CHARACTERS section lists only Kristin and Michelle. No prompt contains "Officer Reyes", "Walt Pruitt" or "Jenkins".
- `package.characters` has no entry for the officer or for Walt Pruitt.
- For "type in the password", the resolver found no matching thing and passed the command through. The phone and the laptop were both in the 1A item
  placements and in the prompt's placement lines.
- The user prompt carries no earlier narration or earlier turn.

## What I need back

1. For each miss, the cause, established from the recorded prompts, the story package and the code, with quoted evidence. Say which of Brandon's two
   questions about the officer turn the evidence answers, and what you could not establish.
2. Whether either miss belongs to a class already fixed elsewhere (name the scene, commit and result), or is new.
3. A plan of fixes ranked as `docs/scene-fixing-guide.md` ranks them: for each, the exact story-text or data diff or the engine change, what it would be
   probed against (arms, sample count, the narration-scoring rule), and the win rule to preregister. Keep any new mechanism story-agnostic and
   world-model logic in `packages/worldkeeper`, as `AGENTS.md` requires. Nothing in the plan is applied until Brandon approves it.
