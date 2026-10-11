# Brief for ChatGPT Desktop: a pointer sentence in the 2C opening text

You are advising on freytag-forge, an interactive-fiction engine with one shipped story ("The Continuity Initiative", nine scenes). A player types free text. A small non-reasoning Llama-class model narrates each turn. The engine, not the model, owns the world facts. Read the files named below yourself, then answer the task at the end. Cite a file for every claim. Story lines are yours to write; code is not.

## The problem

Scene 2C cannot end by play until the player takes the "copy step": `k_sl_2c_c_r1` (or `k_sl_2c_c_r2`) in `data/stories/continuity-initiative/knowledge.yaml` sets `evidence_ready_to_transmit`, and the Michelle reveals d_r1/d_r2 need it. A player who never takes it leaves 2C by timer.

Evidence (read `.plans/scene-affordance-e2e.md`, entries "2C copy-step wording", "L2 all nine scenes x3 on 1c10272f" and "2C file-sentence probe", all near the end):
- On main 80f5c64c two of three 2C runs ended by timer. Both players went to Michelle first ("Search the command levels for Michelle.", "Retrieve Michelle's current location from the medical terminal.") and later typed "Retrieve my copied JANUS files." and "Take the copied files." PR 584 widened the verbs of c_r1, so those commands now match offline.
- On main 1c10272f all three 2C runs passed, but each player copied the evidence on turn 1 ("Copy the JANUS evidence to my laptop."). So the recovery path for a Michelle-first player is still unmeasured.
- Billed probe, 72 replies, read by hand: adding a file sentence to the 2C SCENE (either "Kristin can check the copied files." or "The copied files lie close at hand.") did NOT make the narrator bring up the copied files. The narrator narrates the command it was given. So a frame sentence is not the fix.
- What points at the files today: (1) a one-time cue after a delivery (`handoffs.yaml`, fact `evidence_ready_to_transmit`, never repeated; see `storygame/runtime/engine.py`, `delivered_cue_ids`); (2) the closing sentence of the 2C purge-order and broadcast-schedule deliveries, "The copied files lie close at hand." (`k_sl_2c_b_r1`, `k_sl_2c_b_r2` in knowledge.yaml). A Michelle-first player reaches neither.

## What I want you to design

The 2C opening text is player-visible, appears once when the scene starts, and is the one place every player reads. The current text (`data/stories/continuity-initiative/plot.md`, scene 2C front matter, `entry_text`):

> The command levels tightened around them. Somewhere above, orders were already moving - transfers, schedules, contingency plans measured in hours instead of days. Whatever Kristin and Brandon did next had to count.

The player also sees the 2B to 2C bridge before it (`bridge_text` `t_2b_2c`): "The JANUS evidence in the archive showed what the system was built to do. Kristin and Brandon understood how much danger that evidence put them in."

`entry_text` is also sent to the narrator once, in the first prompt of the scene (`storygame/runtime/cloudflare.py`, search `entry_text`). Check how it is used in `engine.py` (search `entry_text`) and in `docs/world-model-grounding.md` ("give the starting position in `entry_text`").

Task: write the smallest addition to the 2C `entry_text` (one or two sentences, appended, existing text byte-identical) so a player who reads it knows Kristin holds the copied evidence and can act on it, without telling them the answer.

## Constraints (check every one yourself)

1. **Prior art.** Read how the other scenes' `entry_text` set up their first step (2A names the cooling-water readings; 2B the selection files) and the earlier fixes in `.plans/scene-affordance-e2e.md` and `.plans/world-model.md` (W decisions, "Brandon chose"). Recommend only proven techniques. If an entry-text pointer is new, say so and say what you checked.
2. **Words the matcher accepts.** The player will type a command containing one phrase from each `action_evidence` group of `k_sl_2c_c_r1`. Pick wording that leads a player to words in those groups (for example "copied files", "JANUS files", "evidence" with "check", "copy", "take", "use"). Do not put a command in the text ("Check the files.") and do not use a word list the matcher lacks. `storygame/runtime/candidate_matcher.py` shows the matching rules.
3. **No early secrets.** The c_r1 statement ("sending it now would reveal their position and seal the detention sectors"), c_r2 and the Michelle message content (maintenance route, Rebecca's office, opening the cells) must not appear. The loader rejects authored prose that contains a guarded leak term (`storygame/story_package/loader.py`, `_validate_narration_term_traps`; see the `leak_terms` section of `docs/markdown-story-authoring.md`). Your sentence must pass it.
4. **Grounding.** `docs/world-model-grounding.md`: every physical thing the text names must be declared and placed, and a scene text never says where a character is except in `entry_text`. `world.yaml` has no entity named "copied files"; check what exists (for example `portable_archive`, "Portable data case") and where the story says the evidence was copied (search `plot.md`, `storylets.md`, `knowledge.yaml` for "copied", "JANUS", "USB drive", "archive file"). If your sentence names a thing that is not declared, say what declaration is needed and give it.
5. **Continuity with the bridge.** It must not repeat or contradict `t_2b_2c`, and it must read right when the player arrives from 2B and when the engine shows the opening on its own.
6. **Do not give away the timer penalty.** The pacing lines and the evidence-gap lines are separate (see the "penalty" entries in the plan); do not touch them.

## Deliverables

- Three candidate additions, ranked, each with: the exact text; which `c_r1` verbs and objects a player is likely to type after reading it (give five plausible commands); and the one risk that would make it lose (for example the narrator copying the sentence, or players treating it as a non-event).
- For the top candidate: the paste-ready `entry_text` line for `plot.md` (full line, keeping the trailing `\n\n` exactly as it is now), plus any `world.yaml` or `knowledge.yaml` lines it needs.
- A cheap offline check before any billed run: load the package with the new text (does the term-trap check pass?), run the five commands through the real matcher, and run the sentence as narration through the narration safety scan in an early 2C state (c_r1 unearned). Say what result would make you drop the candidate.
- An honest limit statement: what offline checks cannot show (that players read the text and act on it), and the smallest live test that would (a blind-player run of 2C only, how many replicates, what to count).
- If you conclude the opening text is the wrong place (for example the bridge, or a repeated cue is required), say so and name the evidence. Do not propose a matcher change, a narrator rule or a runtime change.

Keep sentences short. Player-facing prose should match the voice of the existing 2C text.
