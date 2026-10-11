# Brief for ChatGPT Desktop: three scenes where the player does not reach the reveal that ends the scene

You are advising on freytag-forge, an interactive-fiction engine with one shipped story ("The Continuity Initiative", nine scenes). A player types free text. A small non-reasoning Llama-class model narrates each turn. The engine, not the model, owns the world facts. Read the evidence files named below yourself, then answer the task at the end. I have not told you what I think the cause is on purpose. Find it in the evidence. Every claim you make must cite a file and a turn.

## How the game works (what you need)

- The player types an imperative command ("Fill out the blank inspector forms.").
- Each scene has **reveals** (knowledge items in `data/stories/continuity-initiative/knowledge.yaml`). A reveal fires when the command contains one phrase from **each** `action_evidence` group (case-insensitive, whole phrase, fixed synonym classes only; two matching reveals tie and neither fires) and its `requires` facts hold. Then its `delivery_text` is appended to the narration and its `establishes` facts are asserted. Matcher: `storygame/runtime/candidate_matcher.py`.
- A scene ends in one of two ways. **By play:** a reveal asserts the fact that a transition trigger reads (`storylet-routes.yaml`, `trigger_fact_id`). **By timer:** after a fixed number of turns (`pacing.yaml`, `handoff_after_turns`) the engine forces the missing deliveries and moves on. A timer ending means the player never found the step.
- **Cues** (`handoffs.yaml`, `cue_text`) are one short line the engine shows to point the player at a reveal. Read `storygame/runtime/engine.py` (search `staged_cue_fact_id`, `delivered_cue_ids`, `_cue_reveal_available`, `_ranked_cue_fact_ids`) to see when a cue is shown and whether it can be shown again.
- When no reveal matches, the narrator improvises from the SCENE and THINGS sections of its prompt. It can invent doors, people and objects.
- Hard rules: story-agnostic engine, no story nouns in code, no regex or fixed action tables, no unvalidated model output. Story text and word lists are yours to write. Code is built by workers from your spec.
- Read `docs/world-model-grounding.md` and the decisions in `.plans/world-model.md` (W decisions, "Brandon chose") before proposing anything. Recommend only techniques already proven there or in `.plans/scene-affordance-e2e.md` (earlier scene fixes). If you propose something new, say so and say what you checked.

## The measurement

An LLM blind player plays each scene from the opening on the hosted staging copy, three replicates, all nine scenes. Latest run, main 1c10272f (2026-10-11): 0 rejected turns, 23 of 24 runs in scenes 1A to 3B left by play. The unresolved cases are below. Three replicates cannot separate a real defect from player variance, so reason from the recorded turns, not from the rates.

## Evidence files (read them)

- `~/dev/ringer-work/l2-1c10272f/e2e-blind-player-r{1,2,3}.json`: per turn: `turn`, `input`, `text` (the narration the player saw), `scene_id`, `rejected`. `by_scene` gives exit type per scene.
- `~/dev/ringer-work/l2-1c10272f/e2e-blind-player-prompts-r{1,2,3}.json`: the exact prompt (`system`, `user`) sent to the narrator each turn, per scene. Read these next to the narration to see what material the narrator had.
- Older runs with the same layout: `~/dev/ringer-work/l2-41240bb/` (prompts and `.md` reports), `~/dev/ringer-work/l2-a773378/`.
- `.plans/scene-affordance-e2e.md`: the running record. Search for "2A", "2C", "1A" and "cue" to see what was tried and measured. The latest entries are at the end.
- Story data: `data/stories/continuity-initiative/{plot.md, knowledge.yaml, handoffs.yaml, storylet-routes.yaml, pacing.yaml}`.

## The three cases

### Case 1: scene 2A, replicate 2 of the latest run ended by timer at turn 11
Read replicate 2's 2A turns (commands, narration, and the recorded prompts) and the 2A items in `knowledge.yaml` (`k_sl_2a_*`) and the 2A scene in `plot.md`. Compare with how replicates 1 and 3 of the same run left 2A by play, and with the 2A timer cases written up in `.plans/scene-affordance-e2e.md`. Work out which step the player never took, what in the data should have led them to it, and why it did not. Check each command the player typed against the actual `action_evidence` groups, including the tie rule.

### Case 2: scene 2C, the evidence step
Last measured on 80f5c64c, two of three 2C replicates ended by timer: they typed "Retrieve my copied JANUS files.", "Take the copied files." (twice) and "Use my copied files on the purge-control console." and nothing fired. PR 584 (merged) added those verbs to `k_sl_2c_c_r1` and rewrote the `evidence_ready_to_transmit` cue. On the latest run all three 2C replicates passed, but every one fired the step on turn 1 with an already-working verb, so the new verbs are untested by play. Answer: (a) can a player who misses the step on their first tries ever be reminded? Read the cue code and say exactly when a cue is shown, whether it repeats, and what the timer nudge does. (b) If the step stays unfound, what in the data or the cue is the remaining gap? Read the 2C turns of all three latest replicates and the older 2C timer record in the plan.

### Case 3: scene 1A, the memory-card reveal
`k_sl_1a_b_r0` (the card behind the KMS drawer) fires only for a narrow set of commands. In several earlier runs a replicate never typed a drawer search and left by timer (see the 1A entries in `.plans/scene-affordance-e2e.md`; the earlier brief is `.plans/chatgpt-1a-drawer-prompt.md`; PRs 569 and 570 changed the drawer words, the cue and a plot sentence). Read the 1A turns in the latest run and in `~/dev/ringer-work/l2-41240bb/`. Answer whether the remaining miss is a wording gap, a cue gap, or the narrator steering away from the drawer, and what story data would fix it without telling the player the secret before the reveal.

## Task

For each case give: the cause, tied to a file and a turn; a fix as paste-ready story data (YAML for `action_evidence`, `cue_text` or `delivery_text`, or plot/frame lines) or a precise code request for a worker if the engine really is the cause (story-neutral rule in plain words plus the hermetic test that proves it); a cheap offline check before any billed run (for 2A and 2C, replay the recorded commands against the real matcher; say which commands must match and which must not); and what the change does to protected knowledge. If one cause is shared by two cases, say so and give one fix. Rank the fixes by (play exits gained) / (cost and risk).

Be explicit about uncertainty. If the evidence cannot separate two causes, say which probe would (a billed probe has to be run by us; describe the arms). If a case has only one recorded instance, say that.

Format: a short diagnosis per case (at most 8 lines each), then the ranked fix list, then the paste-ready data. Keep sentences short. Narrator-facing lines must be at an 8th-grade level. Do not propose rewriting the engine, switching the narrator model, a regex or synonym guesser, or story-specific code.
