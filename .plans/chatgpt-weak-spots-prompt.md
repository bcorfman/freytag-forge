# Brief for ChatGPT Desktop: analyse three weak spots in a playtest and propose fixes

You are advising on freytag-forge, an interactive-fiction engine with one shipped story, "The Continuity Initiative" (nine scenes: 1A 1B 1C 2A 2B 2C 3A 3B 3C). A player types free text. A small, non-reasoning Llama-class model narrates each turn. The engine, not the model, owns the world facts and decides which authored "reveal" a command earns. You cannot run the game. Read the files named below yourself, then answer the task at the end. Cite a file and line for every claim. Do not edit any file and do not run billed calls.

## How the engine decides what a command earns

- A reveal (a `k_sl_*` item in `data/stories/continuity-initiative/knowledge.yaml`) has `action_evidence`: a list of word groups. The exact matcher (`storygame/runtime/candidate_matcher.py`) fires a reveal only when the command contains at least one word or phrase from EVERY group, as whole words, with possessives and plurals handled. If a command matches two eligible reveals, the result is a tie and nothing fires. Commands containing negation words ("do", "not", "don't", "without", "instead of" and similar) never match. The reveal's `requires` facts must already be true.
- If the exact matcher finds nothing, a bounded semantic fallback asks a small model one yes/no question per shortlisted reveal, using the reveal's `earn_when` text. It accepts exactly one "yes". It is literal: idioms and state claims often fail.
- Each scene has pacing in `pacing.yaml`: `nudge_after_turns` (the engine appends one stronger authored pointer, the cue text from `handoffs.yaml`, for an unresolved reveal) and `handoff_after_turns` (the engine force-delivers the remaining reveals and the scene moves on). A forced handoff is a safety backstop, not the goal: the goal is that an ordinary player earns the reveals by playing.
- A safety scan rejects any narration that names a later-scene thing or protected term before the player has earned it. A rejected turn is discarded and the player sees an error. Names declared anywhere in `world.yaml` or `knowledge.yaml` (including `aliases`) are scanned in scenes where they are not yet known.
- Player input is imperative ("Search the drawer.") or, for the raw-language profile, longer natural wording.

## What the latest playtest found

Six full playthroughs of the hosted game on staging (3 with a "canonical" model player who types short imperative commands, 3 with a "raw" player who types longer natural commands). All six reached the new ending. Three weak spots remain.

### Weak spot 1: scene 1C, players do not follow the reveal chain (4 forced exits in 6 runs)

Scene 1C (freight terminal, `plot.md` "Scene 1C", lines 244 onward; `pacing.yaml` 1C: min 7, nudge 8, handoff 11). The intended chain, from `knowledge.yaml` (ids `k_sl_1c_*`):

- `a_r1` inspect signs of activity at the loading docks (verbs: inspect, examine, check, search, study, look at; objects: loading docks, power, electrical load, ventilation, vents, tire tracks). Establishes `facility_proof`.
- `a_r2` use the transit token at the service entrance (an alternative first step).
- `b_r1` (requires `facility_proof`) compare prisoners with missing-person records, or read, examine, copy, photograph or log the ID numbers on the prisoners' uniforms. Groups: [compare, match, cross-check, check, read, examine, record, copy, ...] x [prisoners, captives, people in the processing area, uniforms, ...] x [missing-person records, records, identification numbers, ID numbers].
- `b_r2` (requires `facility_proof`) search the processing line for Michelle. Groups: [look for, search for, find, search, look] x [Michelle, woman who looks like Michelle] x [processing line, processing area, observation shaft].
- `c_r1` (requires `facility_proof` and `captives_confirmed_alive`) use the logistics computer; `c_r2` play the Charles and Rebecca recording.
- The scene exits when `facility_infiltration_needed` is true (transition `t_1c_2a`).

The authored cue for `captives_confirmed_alive` (in `handoffs.yaml`, scene 1C) is: "The observation shaft overlooks a processing line. Identification numbers are visible on the uniforms below."

Evidence. In all three raw runs the player earned `a_r1` on turn 1 (checked offline with the real matcher), then never earned `b_r1` or `b_r2`. Their next commands, verbatim (raw run, each from a separate replicate):

- "Inspect the observation shaft and look for a way down into the processing area."
- "Examine the locked stairs and the surrounding service level for a way to unlock or bypass them."
- "Climb down the ladder from the observation shaft to the service level."
- "Inspect the service level for a safe route toward the processing line and any signs of the missing people."
- "Stay hidden and follow the processing line to see where the restrained people are being taken."
- "Open the ajar ventilation grille and slip through it with Brandon before the guards reach the service level."

Each run then built a route of its own (ladders, a catwalk, a keypad, vents) until the forced handoff at turn 11. In the canonical runs one of three also got forced at turn 11 ("Inspect the observation shaft.", "Examine the processing line.", "Find an entrance to the processing line.", "Enter the biohazard containment zone.", "Use the transit token on the access panel."). Earlier rounds (see `.plans/scene-affordance-e2e.md`, search "1C shaft frame", "PR 578", "1c-wording") fixed 1C by adding a frame sentence about the observation shaft and widening verbs; that measured 9 of 9 by play on one run, 6 of 9 on another, and now 2 of 6 canonical-or-raw runs earn the chain by play. The players treat the shaft as a way down, not as a place to look from.

### Weak spot 2: scene 1A, the phone rejection

Command "Examine Michelle's phone." was rejected once with `narration mentions an unavailable entity 'photo'`. The narrator described a photo on the phone. `world.yaml` line 213 declares the 1B item `michelle_photograph` with `aliases: [photograph, photo]`, so the word "photo" is scanned in 1A where that item is not yet known. The project already has a proven technique for common words that belong to a later-scene item: `scoped_aliases` (see `.plans/world-model.md` section 12, `docs/world-model-grounding.md` "Things", PR 590 and the 3A medical-records fix recorded in `.plans/design-review-implementation.md`, "Medical records rejection fixed"). Check whether it applies here, and whether "photograph" and "picture" have the same problem.

### Weak spot 3: scene 1A, drift to an invented place

In one canonical run the player missed the 1A cue and kept going: "Visit the old warehouse.", "Search the old warehouse.", "Examine the old boxes.", "Examine the discarded equipment.", "Examine the leather-bound book.", "Open the leather-bound book.", "Read the leather-bound book.". None of these things exist. The narrator accepted and described them, so the player spent turns 7 to 13 on invented content and the scene ended by forced handoff on turn 14. 1A pacing is nudge 10, handoff 13. A stage-two pointer exists (`escalation_text` support was added; no shipped 1A delivery sets one, so the pointer repeats the stage-one cue). Decide whether this is a real defect or normal for a model player.

## Constraints you must respect

1. **Prior art first.** Read `docs/scene-fixing-guide.md`, `docs/world-model-grounding.md`, `.plans/world-model.md` section 12 (W decisions), `.plans/scene-affordance-e2e.md` for 1A and 1C, and `.plans/design-review-implementation.md` (Steps 5 and 6: the escalation pointer and the 2A verb fix). Recommend only proven techniques: widening a reveal's verbs or objects, scoped aliases, a reveal handoff or cue text, removing a line that pulls the wrong way, a frame sentence in the plot. If you propose something new, say so, say what you checked, and rank it last.
2. **Prefer subtractive fixes** (remove or scope a conflicting line) over adding constraints to the narrator. The narrator is a small model; added rules mostly lost in earlier probes (the go-into-a-place rule 1/15 vs 4/15).
3. **No regex, no scene-specific runtime code, no new engine mechanism.** Story data and wording only.
4. **Matcher rules.** Any wording you propose for `action_evidence` must be scored mentally against the matcher: every group needs a hit, whole words, exactly one reveal may match. Give must-fire and must-not-fire commands, including the raw commands quoted above, and check each against the sibling reveals (`b_r1` versus `b_r2`, and `a_r1` versus `b_*`) so you do not create ties.
5. **Do not break secrecy.** New words in `action_evidence`, cues or delivery text must not contain a protected or later-scene term. Check `leak_terms` in `knowledge.yaml` and the aliases in `world.yaml`.
6. **Writing level.** Any new narrator-facing or player-facing text: 12th grade reading level or lower, short sentences, one idea each, plain words.
7. **Player input** in examples is imperative and uses first-person possessives for the player's own things ("Check my laptop."), never "I search...".
8. **Keep the story intact.** Do not change reveal ids, effects (`establishes`), `requires`, pacing numbers, or the plot's events. Do not change `entry_text` or `bridge_text` unless you show a sentence cannot work otherwise, and say plainly that it changes player-visible text.

## Task

1. **Root cause for each weak spot,** with evidence from the files and the commands above. For 1C, say specifically why "Inspect the observation shaft ..." earns nothing: which group fails for each of the quoted commands, whether the semantic fallback should have helped, and whether the cue text, the `a_r1` delivery text, the entry text or the plot's 1C.1/1C.2 wording points the player at "a way down" instead of "look at the prisoners". Say how likely a human player is to behave like the raw model player here, and say honestly if you cannot tell.
2. **For each weak spot, at most three candidate fixes,** ranked, each with: the exact file and the paste-ready change (YAML or text); the proven technique it follows (cite the earlier fix); the risk (ties, leaks, a regression in another scene); and the cheapest offline check (the repo has `scripts/disclosure_matrix.py`, `tests/test_leak_terms.py`, `tests/test_design_review_fixtures.py`, the matcher, and a narration corpus test). Include a scoring table of at least 12 commands for any `action_evidence` change: command, expected reveal or none, and your matcher verdict.
3. **A recommendation:** which single fix to try first for each weak spot, and which to leave alone. If a weak spot is not worth fixing (for example the 1A drift), say so and why.
4. **The smallest live test** that would show the fix works: which bench script or hosted run, how many replicates, what to count (for example, reveals earned by turn 8 in 1C, forced exits, rejected turns), and what result would make you drop the proposal. The project's rule: 10 to 15 samples per arm for a fixed-prompt probe, 12 paired starts for a success-rate decision; three clean runs is only a smoke check.
5. **An honest limit statement:** what offline scoring cannot show.

Keep sentences short. Put the recommendation first, then the evidence.
