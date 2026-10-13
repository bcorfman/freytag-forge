# Brief for ChatGPT Desktop: audit our refusal evidence and pick the path forward

You are an independent reviewer for freytag-forge, an interactive-fiction engine with one shipped story, "The Continuity Initiative". A player types free text. A small, non-reasoning Llama-class model narrates each turn. The engine, not the model, owns the world facts. You cannot run the game. If you can read the repository files named below, read them. If you cannot, use the excerpts in this brief. Do not edit files. Do not write code, regexes, or new narrator rules. Describe mechanisms in plain steps, and say what you could not verify.

We want two things from you, in this order:

1. **Audit the evidence.** Tell us which of our conclusions the data supports and which it does not. We would rather hear that a result is weaker than we think.
2. **Pick the path forward.** Choose among the options below, or propose a better one, with a measurement plan and pass bars stated before any run.

You previously reviewed an earlier version of this work (the candidate "refuse fixed move" step). Your answer is in `.plans/astra-refusal-alternatives-answer.md`. We built and measured that candidate on the commands you proposed. Results are below. Say where your earlier answer was right, where it was wrong, and what you would now change.

## The problem

The narrator writes the turn's prose and, in the same reply, an `item_facts` object saying what changed. The engine commits the turn and only then applies `item_facts` ("capture"). Capture refuses a move of a thing declared `fixed: true` in `world.yaml` (the workstation, the back door, the drawer, the truck's seats). The refusal is only an issue string. The player already has prose that says the move happened. The next turn then contradicts what the player was told.

Example, scene 1A, command `Carry the workstation to the truck.`:

> Kristin carefully lifts the workstation and carries it out to her truck. She sets the workstation down on the passenger seat, next to her laptop. The workstation is now in the truck.

The engine's record says the workstation never moved.

## Approaches already measured (before this round)

Baseline: the narrator claims the move on nearly every command that names a fixed thing (32 of 40 on four commands; 32 of 32 on eight held-out commands).

| Approach | Result |
| --- | --- |
| Append engine clause "X has not moved." after the prose | Reply still says it moved, then says it did not. 0 of 29 coherent. Free. |
| Ask the narrator to rewrite only the false sentences ("repair") | About 4 of 29 coherent. One extra call. |
| Re-narrate the turn with a correction note, then restore authored cue text ("renarrate") | About 23 to 31 of 33 to 36 coherent on the original four commands. One extra narrator call per refused turn. |
| Always tell the narrator in its THINGS list that a fixed thing is fixed (three wordings) | Fixes lift, take out, bring, pick up, take outside. Does nothing for commands with a destination or a push. Over-refuses ordinary use of fixed things ("Sit in the driver's seat.", "Open the drawer."). |

## The new experiment: refuse-fixed-move prerequisite step

You recommended building this next. It works like the existing prerequisite steps (`stand_before_leave`, `board_vehicle`, `take_before_put`, `seat_before_use`). When a command names a fixed thing that is in the scene, the engine asks the small yes/no model: does this command carry, push, drag, lift, remove, or otherwise relocate that thing? If yes, the engine records no world change and hands the narrator one line for that turn: "{Protagonist} tried to move {the thing}. It is fixed in place and did not move." That line appears under "Just before this:". The narrator then writes the rest of the turn. If the answer is no, nothing is added. The step runs first in `before_turn` and, when it fires, the other four steps are skipped. It adds no narrator call.

### Pre-registered bars (written before the run)

- At least 15 of 16 coherent honest refusals on the refusal commands, with zero claims of a successful prohibited move.
- Destination and push commands: 6 of 6.
- Controls: 16 of 16 intended successes, zero invented fixedness obstacles.
- No added narrator call.
- Drop rule: if destination or push commands still claim the move, or controls fail, drop the step and measure an engine-owned refusal next.

### Design

Sixteen fresh commands (8 refusal, 8 controls) in scene 1A, 2 replicates each, 3 arms, 96 turns. Replies were scored blind: shuffled sheet, arm labels removed, key unblinded only after scoring. A deterministic substring screen was used only to sort; every reply was read by one reader. Before reading outcomes we confirmed the changed text actually appears in the recorded narrator prompt.

Refusal commands (as typed): `Raise the workstation off the floor.`, `Detach the driver's seat from the truck.`, `Extract the drawer from the workstation.`, `Transport the workstation into the truck.`, `Bring the drawer to the passenger seat.`, `Shove the workstation toward the back door.`, `Lift the drawer and the back door together.`, `Lift the workstation, then lower it back into place.`

Controls: `Place my laptop on the workstation.`, `Set my laptop on the passenger seat.`, `Retrieve my laptop from the passenger seat.`, `Pull the drawer open.`, `Push the drawer shut.`, `Push the back door open.`, `Seat myself in the driver's seat.`, `Move the workstation chair beside the workstation.`

### Results (16 refusal-command replies and 16 control replies per arm)

| Arm | Coherent refusals / 16 | Claims the move | Controls that succeed / 16 | Narrator calls added |
| --- | --- | --- | --- | --- |
| Baseline | 0 | 16 | 16 | 0 |
| Candidate (the new step) | 7 | 9 | 16 | 0 |
| `renarrate` with cue-restore | 8 | 6 (+2 off-topic) | 14 | 13 across 32 turns |

By command (candidate): Raise, Detach, Extract were honest 2 of 2 each. Transport, Bring, Shove were 0 of 2 each (destination and push: 0 of 6). "Lift the drawer and the back door together" was 1 of 2. "Lift ... then lower it back into place" was 0 of 2.

What went wrong, separated:

- **Narrator disobedience.** The classifier fired and the line was in the prompt, and the narrator wrote past it. Example: "tries to move the workstation, but it's fixed in place. She decides to transport the workstation into her truck instead. She carefully lifts the workstation and carries it out." This happened on Transport, Bring and Shove.
- **Classifier errors.** It fired on 14 of the 16 refusal-command turns. It missed "Lift the workstation, then lower it back into place" both times. It fired falsely on "Retrieve my laptop from the passenger seat" both times, treating the seat as the relocated thing. The narrator still retrieved the laptop, so the control passed, but the step was wrong.
- **`renarrate`.** It handles carry, bring and shove and misses lifts. It failed the control "Seat myself in the driver's seat" in 2 of 2 replies, and answered "Detach the driver's seat" off-topic. It only fires when capture notices the claim. Capture flagged 13 of the 32 baseline turns, while on reading we judged 16 of 16 refusal-command replies to be claims. So `renarrate` undercounts what it should repair.
- The candidate and `renarrate` look complementary: the step covers lift, detach and extract; `renarrate` covers carry, bring and shove.

Caveats we know about: one scene, one narrator, replies near-identical across replicates (16 distinct commands, not 96 independent samples), one reader. Prompt text was confirmed in the recorded `prompt_user`.

By the drop rule, the candidate version is dropped and stays opt-in.

## Options on the table

1. **Engine-owned refusal.** When the classifier says a command relocates a fixed thing and the command is wholly a prohibited relocation, the engine writes the refusal text itself and skips the narrator call. Needs the classifier's misses fixed. Open risks: mixed commands ("Carry the workstation to the truck, then open my laptop"), authored cue text and must-convey delivery that is due that turn, pacing (does a refused turn consume a story turn?), save/load of pending obligations, rollback of any prerequisite mutations.
2. **Combined arm.** The step plus `renarrate`, measured on fresh commands.
3. **Stop on refusals.** Leave everything opt-in and move to the next plan items.

Also open: whether `renarrate` should become the default in the web build. It works on some commands, costs a narrator call per detected claim, and failed one control.

## Project rules that bind any proposal

Facts are the only mutable truth. The shared runtime is story-agnostic and LLM-proposal-first. Prefer deterministic authored text over model-generated text. Prefer subtractive or material fixes over new prompt rules (new rules often lose their probes). The narrator is small and its context must stay bounded by relevance. Every path that calls a billed model must be guarded. Clarification questions cost no story turn. Narrator-facing text is plain 12th-grade language. Player input in examples is imperative with first-person possessives (`Put my laptop on the workstation.`).

## What we want back

Use these headings.

1. **Audit of the evidence.** For each claim below, say supported, partly supported, or not supported, and why. Name any scoring or design flaw that could change a conclusion (blind scoring by one reader, near-identical replicates, the substring screen, capture undercounting, the classifier misses and false positives being counted against the candidate). Claims:
   - The candidate fails its bars.
   - The failure on Transport, Bring and Shove is narrator disobedience, not a prompt-delivery or classifier problem.
   - The candidate causes no over-refusal on controls.
   - `renarrate` and the candidate are complementary.
   - `renarrate` is unfit as a default because of the driver's-seat control failure.
2. **Where your earlier answer stands.** What you predicted correctly, what you got wrong, and anything you would retract.
3. **Path forward.** Pick one of the three options, or a better fourth. Give your reasoning in plain steps. If you choose engine-owned refusal, say how it should treat mixed commands, authored cue and must-convey delivery, turn consumption, and classifier unavailability (a `None` answer must not silently mean "ordinary use"). If you propose something new, say which measured result it builds on and why it should beat the options above. Do not re-propose the four approaches in the first table without saying what is different.
4. **Measurement plan for your pick.** At least twelve fresh commands not listed above, covering lift, remove, destination, push, two-thing, fixed-destination and use-in-place controls. Arms. Sample counts (we prefer more commands over more replicates). Pass bars stated before any run. Include how to separate classifier errors from narrator disobedience, and what to check in the recorded prompt before reading outcomes.
5. **What result would make you stop.** One paragraph: the result that should end the refusal work for Phase 4 and send us on to the next plan items, and your view on the `renarrate` default question.

Be direct about uncertainty. If a claim depends on code you could not read, name the file you would check.

## Files worth reading if you can

- `.plans/astra-implementation-plan.md`: sections "Phase 4 item 2 result", "marker wording variants: result", and "refuse-fixed-move step: result" for the data above.
- `.plans/astra-refusal-alternatives-answer.md`: your earlier answer.
- `storygame/runtime/fixed_refusal.py`, `storygame/runtime/capture.py` (`WorldCapture.before_turn`), `storygame/runtime/jev_questions.py` (`relocates_thing`), `storygame/runtime/engine.py` (`_handle_refusal`, `_refusal_rewrite`, `_splice_refusal_segments`), `storygame/runtime/item_facts.py`.
- `docs/world-model-grounding.md` and `docs/narrator-writing-guide.md`.
- `data/stories/continuity-initiative/world.yaml` for the fixed things in scene 1A: `michelle_drawer`, `back_door`, `michelle_workstation`, `truck_driver_seat`, `truck_passenger_seat`.
