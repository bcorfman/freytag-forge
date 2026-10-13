# Brief for ChatGPT Desktop: evaluate other ways to stop the narrator claiming a move the game refuses

You are advising on freytag-forge, an interactive-fiction engine with one shipped story, "The Continuity Initiative". A player types free text. A small, non-reasoning Llama-class model narrates each turn. The engine, not the model, owns the world facts. You cannot run the game. If you can read the repository files named below, read them. If you cannot, use the excerpts in this brief. Do not edit files. Do not write code, regexes, or new narrator rules. Describe mechanisms in plain steps, and be explicit about what you could not verify.

Your job: judge one untried candidate solution (below), look for a better one if you can, and say which to measure next and how. We have already measured four approaches. Do not re-propose them without saying what would be different.

## The problem

The narrator writes the turn's prose and, in the same reply, an `item_facts` object saying what changed. The engine commits the turn and only then applies `item_facts` ("capture"). Capture refuses a move of a thing declared `fixed: true` in `world.yaml` (the workstation, the back door, the drawer, the truck's seats). The refusal is only an issue string. The player already has prose that says the move happened.

Example, scene 1A, command `Carry the workstation to the truck.` Reply the player sees:

> Kristin carefully lifts the workstation and carries it out to her truck. She sets the workstation down on the passenger seat, next to her laptop. The workstation is now in the truck.

The engine's record says the workstation never moved. The next turn contradicts the story the player was told.

## What has been measured (scene 1A, live narrator, n per command is small because replies are near-identical across replicates)

Baseline: the narrator claims the move on nearly every command that names a fixed thing (32 of 40 on four commands; 32 of 32 on eight different held-out commands).

| Approach | Result |
| --- | --- |
| Append an engine clause "X has not moved." after the prose | The reply still says it moved, then says it did not. 0 of 29 coherent. Free. |
| Ask the narrator to rewrite only the false sentences ("repair") | Mostly leaves the false sentences or contradicts itself. About 4 of 29 coherent. One extra call. |
| Re-narrate the turn with a correction note, then restore the authored cue text ("renarrate") | About 23 to 31 of 33 to 36 coherent honest refusals; some off-topic replies. One extra narrator call per refused turn. Works. |
| Always tell the narrator in its THINGS list that a fixed thing is fixed (a sentence per rendered fixed thing, three wordings tried) | Fully fixes "lift", "take out", "bring", "pick up", "take outside". Does nothing for commands with a destination or a push: "Drag the workstation to my truck." / "Push the workstation against the wall." / "Carry the drawer to my truck." still claim the move 4 of 4 times, with every wording. It also causes over-refusal of ordinary play on fixed things the player should use: "Sit in the driver's seat." (the seats are `fixed`) and "Open the drawer." failed in 1 to 3 of 3 replies. Wording was not the lever. |

So an always-on statement about the thing does not beat a command that names a destination, and it taxes normal use of fixed things. The only approach that handled destination commands also costs a second narrator call.

## How the engine already prepares a turn (read these)

- `storygame/runtime/capture.py`, `WorldCapture.before_turn`: before the narrator is called, the engine runs "prerequisite step" modules (`stand_before_leave`, `board_vehicle`, `take_before_put`, `seat_before_use`). Each looks at the command and the world. Where the command names a thing and a step is needed, it asks a small yes/no model one question (`storygame/runtime/jev_questions.py`: `moves_thing`, `needs_to_stand`, `goes_to_vehicle`, `uses_thing`), performs the step in the world, and hands the narrator a short past-tense line (a "Just before this: ..." line, such as "Just before this: Kristin sat down in the driver's seat."). `storygame/runtime/taking.py` `take_before_put` explicitly skips fixed things (`world.schema.is_fixed`).
- `docs/world-model-grounding.md`, section "What a model is shown": "Engine steps are told, not asked. ... Don't ask the narrator to perform a step the world model can perform."
- `storygame/runtime/item_facts.py`: `prepare_turn` runs a match call (small model) that lists which tracked things the command talks about; `world.schema.is_fixed(entity_id)` says whether a thing is fixed; `_things_block` builds the THINGS list the narrator sees.
- Project rules that bind any proposal: facts are the only mutable truth; the shared runtime is story-agnostic and LLM-proposal-first; prefer deterministic authored text over model-generated text; prefer subtractive or material fixes over new prompt rules (new rules often lose their probes); the narrator is small and its context must stay bounded by relevance; every path that calls a billed model must be guarded; clarification questions cost no story turn; narrator-facing text is written in plain 12th-grade language.

## The candidate to evaluate: a "refuse fixed move" prerequisite step

When the command names a fixed thing, ask the small yes/no model one question: does this command carry, push, drag, lift, remove, or otherwise relocate that thing? (The existing `moves_thing` question is about put, place, store, or hand over, with the player holding the thing, so it would need a different question.) If yes, the engine records nothing in the world (the thing stays put) and hands the narrator a "Just before this:" line for that turn only, for example: "Just before this: Kristin tried to move the workstation. It is fixed and did not move." The narrator then writes the rest of the turn. If no (the command opens, examines, sits in, or looks at the thing), nothing is added.

Points we already see, and want you to check or contradict:
- It adds no always-on text, so it should not cause the seat and drawer over-refusals.
- The line arrives as a past event the narrator continues from, which is how the existing steps already steer the narrator.
- It costs one extra small-model yes/no call, only on turns that name a fixed thing. It should not add a narrator call.
- Risks we can think of: the yes/no model misclassifies; the narrator may ignore a "Just before this" line the way it ignored the THINGS sentence for destination commands; the engine may not know the command's intent when a fixed thing is only the destination ("Put my laptop on the workstation." names a fixed thing but moves the laptop); a command that names two things.

## What we want back

Use these headings.

1. **Verdict on the candidate.** Will it work for destination and push commands, where the THINGS sentence failed? Why or why not, using the narrator's behaviour described above. Say which parts of your answer are guesses.
2. **Ways it fails.** Concrete command examples, written as a player types (imperative, direct object, first person for the player's own things: `Put my laptop on the workstation.`, not "I put..."). Include cases where the fixed thing is a destination, cases with two named things, and cases where the player means to use the fixed thing.
3. **Other candidates.** Up to two alternatives not in the measured table and not the candidate above, each with: mechanism in plain steps, cost per turn, what it could break (over-refusal, authored cue text and must-convey delivery, progression, save/load), and why it might beat the candidate. If you think the candidate is the best option, say so and do not invent others.
4. **A measurement plan.** For your top pick: the commands to use (give at least eight fresh ones that are not in the lists above, covering lift, remove, destination, push, two-thing, and use-in-place controls), arms to compare (baseline, candidate, and `renarrate`), how many samples, and the pass bar for "coherent honest refusal rate" and "controls that must still succeed". State the bar before any run. Note that replies are near-identical across replicates, so prefer more commands over more replicates.
5. **Recommendation.** One paragraph: what to build and measure first, and what result would make you drop it.

Be direct about uncertainty. If a claim depends on code you could not read, name the file you would check.

## Files worth reading if you can

- `.plans/astra-implementation-plan.md`, sections "Phase 4 item 2 result", "Phase 4 item 2, prevention arm", and "marker wording variants: result" for the data above.
- `storygame/runtime/capture.py`, `storygame/runtime/taking.py`, `storygame/runtime/jev_questions.py`, `storygame/runtime/item_facts.py` (`_things_block`, `apply_item_facts`), `storygame/runtime/engine.py` (`_handle_refusal`).
- `docs/world-model-grounding.md` and `docs/narrator-writing-guide.md`.
- `data/stories/continuity-initiative/world.yaml` for the fixed things in scene 1A: `michelle_drawer`, `back_door`, `michelle_workstation` (a desk), `truck_driver_seat`, `truck_passenger_seat`.
