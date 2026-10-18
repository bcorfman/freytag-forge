# ChatGPT prompt: what is Scene 1A still getting stuck on?

Paste everything below the line into ChatGPT Desktop. It has the project files
open, so it reads them itself. Bring the answer back to Claude Code, which
applies it through a Ringer task and probes it.

---

You are helping investigate a defect in an interactive-fiction engine,
`freytag-forge`, and its story package `data/stories/continuity-initiative/`.
You can read the repository. Read these first, in order, and follow them:
`AGENTS.md`, `docs/scene-fixing-guide.md`, `docs/world-model-grounding.md`,
`docs/narrator-writing-guide.md`, `docs/player-input-guide.md`, then
`data/stories/continuity-initiative/plot.md` (Scene 1A),
`knowledge.yaml` (every `k_sl_1a_*` entry), `handoffs.yaml`, `pacing.yaml`
(the 1A event) and `storylets.md` (SL-1A-A to SL-1A-F).

## The question

Scene 1A is the opening scene. In two hosted runs of the whole story with a
"raw" blind player (an LLM that sees only the screen and types free text), 1A
was left by earned play, never by a forced handoff or timer. But it still shows
stuck turns. The harness counts a turn as stuck when it commits no reveal. I
want you to investigate what 1A is still getting stuck on, decide which of
those turns are real defects, and propose fixes only for the real ones.

I have a lead, not a conclusion. Treat everything under "Leads" as unverified.
Check each against the files and say whether it holds.

## Evidence

Two runs, same raw profile, one replicate each. Report fields are in
`e2e-blind-player.json`, scene `1A`, `turns`; per-turn engine decisions are in
`e2e-blind-player-bundles.json`, scene `1A`, `bundles[].attempt_bundle`
(`reveal_selection`, `selected_reveal`, `pre_state`, `committed_delta`,
`command`); the exact prompts sent to the narrator are in
`e2e-blind-player-prompts.json`.

- Run A, staging `8aba3ba3`: `bench/results/stage7-blind-raw/attempt-1/`.
  1A took 8 turns, exit by play, stuck turns reported as [4, 7].
- Run B, staging `62cae8ae`: `bench/results/stage7-2b-entry/attempt-1/`.
  1A took 8 turns, exit by play, stuck turns [2, 5, 7, 8].

Run B commands and what the engine did (reveal ids are `k_sl_1a_*`):

| Turn | Command | Reveal committed |
| ---: | --- | --- |
| 1 | Examine the damaged back door. | a_r1 |
| 2 | Examine Michelle's phone. | none (stuck) |
| 3 | Pull open the drawer with the carved initials. | f_r1 |
| 4 | Feel underneath the drawer. | b_r0 (memory card found) |
| 5 | Go outside to my truck and get my laptop. | none (stuck) |
| 6 | Insert Michelle's memory card into my laptop. | b_r1 |
| 7 | Open Michelle's saved files and examine the information about the Continuity Initiative. | none (stuck) |
| 8 | Open the documents in the Continuity Initiative folder and read them. | none (stuck); scene moves to 1B on this turn |

Run A commands, turns 4 to 8: "go to the truck" (stuck), "insert the memory
card into the laptop" (b_r1), "Drive to the park and look for the bench
mentioned in Michelle's files." (no reveal, not counted stuck), "search the
park for the bench mentioned in Michelle's files" (stuck), "go to the bench and
examine it" (exit).

## Leads (unverified)

1. **d_r1 can no longer fire after b_r1.** The plan already records that
   `k_sl_1a_d_r1` lost the real raw tie on a scripted 1A prompt to
   `k_sl_1a_b_r1` and that the semantic reason was not recoverable offline
   (`.plans/implementation_plan.md`, "SIX MISSED REVEALS DIAGNOSED"). The
   open part is why, and what to do about it; do not just restate it. With the real matcher
   (`storygame/runtime/candidate_matcher.py`, `_matches_all`), the run B turn 7
   command matches `k_sl_1a_d_r1` ("open" plus "files"). But the engine's
   decision for that turn was `reveal_selection.outcome = "semantic_refusal"`,
   `universe_size = 2`. By then `b_r1` had committed `continuity_initiative_known`,
   `michelle_lead_actionable` and, earlier, `michelle_abduction_suspicion`, which
   is every fact `d_r1` establishes. The semantic-fallback candidate filter
   (`_eligible_reveal_candidates` in `storygame/runtime/cloudflare.py`) drops
   reveals whose facts are all established. So `d_r1` may be dead content once
   `b_r1` has fired. `b_r1`'s delivery already names the Continuity Initiative
   and "a dead drop at a bench in the park". Verify the filter, say what the
   other universe candidate was, and say whether `d_r1` and `b_r1` overlap by
   design.
2. **Turns 2 and 5 may not be defects.** "Examine Michelle's phone" and "Go
   outside to my truck" have no authored reveal. Michelle's phone is declared
   (`michelle_phone`, on the kitchen floor), and the laptop is in the truck
   (`kristin_laptop`). Decide whether these need an authored response or are
   fair dead ends, and whether the harness's stuck count should treat them as
   defects at all.
3. **Run B turn 8 narration moved Kristin.** The reply read "Kristin walks up
   to the house, still trying to process the scene before her. She opens the
   front door...", after she had been at the truck on turn 5. Check whether
   the narrator prompt for that turn carried the right place for Kristin and
   whether a line pulled it toward the house.
4. **What ends 1A?** The scene left on turn 8 in run B (command about the
   Continuity Initiative folder) and turn 8 in run A. Find the transition
   `t_1a_1b`, the `handoff_after_turns` value for 1A and the pacing event
   `pressure_1a` (turn 4), and say what actually triggered the exit each time.
   The reveal-selection outcome on run B turn 8 was `no_eligible_action` with
   `universe_size = 0`.
5. **The patrol reveals (`c_r1`, `c_r2`) were not reached in either run.** Say
   whether that matters: they need `michelle_warning_known`, which `b_r1`
   commits, and a player action about the officers or the gate.

## Already tried or settled for 1A (do not recommend these again)

All of these are in `.plans/implementation_plan.md`; search it for "1A".

- **Drawer path.** Widened `k_sl_1a_b_r0` evidence ("lower edge", "bottom edge",
  "drawer's"); added the gap pointer reveals `k_sl_1a_f_r1` and `k_sl_1a_f_r2`;
  changed the 1.1 plot line to "A thin gap beneath its lower edge is wide
  enough for Kristin's fingers." These are why turns 3 and 4 now work in both
  runs.
- **Laptop pointer.** Dropped the "Kristin's laptop is in her truck outside"
  sentence from the pre-card cue for `continuity_initiative_known`
  (`95451d7d`). The card's own delivery still says the laptop is in the truck.
- **Guards.** Bare `card` stays guarded until the card is recovered
  (`5170479b`, `22f818ad`). `house_gate` and the 1A `park bench` are declared
  and scoped; do not reopen leak terms for them.
- **Photograph words.** The early-1A photograph sentence and the linked
  1A-to-1B photo-word smoke passed 3 of 3. Not a 1A defect.
- **Playing without the drawer.** Not reproduced: scripted non-drawer play
  ("Look around.", "Examine Michelle's phone.", "Search the truck.", "Walk
  around the building.") leaves 1A on turn 13 by forced handoff and the card
  state is consistent (`tests/test_drawer_avoidance_repro.py`). So a player who
  never opens the drawer is not stuck forever.
- **Sibling reveals.** `k_sl_1a_b_r2` is an alternative realization of the
  storylet `SL-1A-B`, and a fired storylet is spent, so it is not a missed
  reveal when `b_r1` fires. The plan's missed-reveal list is over-strict for
  it. The fix choice (derive expected reveals from storylet eligibility, or
  script a distinct `d_r1` prompt) is open and needs Brandon.
- **Not a lever for 1A:** more cue wording. The 2B probes found cue wording
  weak against an invented object, and the 1A cues are already tuned.

## Rules you must follow

- Use only techniques the project already proved. `docs/scene-fixing-guide.md`
  and `docs/world-model-grounding.md` list them. In order: missing story
  material goes in as a reveal handoff or a statement; a line that pulls the
  narration the wrong way is scoped or removed; a narrator rule comes last,
  and only if it is story-neutral. Say which proven technique each fix uses
  and where an earlier scene used it.
- Remove before adding. Prefer a subtractive fix.
- Never use keyword or regex scanning of narration as a gate.
- Facts are the only mutable truth; the shared runtime stays story-agnostic.
  If your investigation shows the cause is in the engine (for example the
  eligibility filter in lead 1), report it as a finding with file and line, and
  separately give the best story-side fix. Do not make the engine change part
  of the story fix.
- Do not weaken a correct guard, and do not widen `action_evidence` just to
  make a recorded command match. An evidence change is allowed only for a
  proven authoring miss, with the matcher's rules in mind: whole words,
  possessives, negation words, exactly one match per command.
- If you propose declaring or placing a thing, follow the Things and Names
  sections of the grounding guide.
- New text is plain: 12th-grade reading level, one idea per sentence, no
  figurative filler.

## What I need from you

1. For each stuck turn in both runs, say what the engine did and why, with the
   file and line that decides it. Mark each turn real defect, fair dead end, or
   not counted by design.
2. Confirm or correct each lead. Quote the lines you rely on.
3. For each real defect, give one to three ranked fixes: the exact file, the
   exact old text, the exact new text (or the deletion), the earlier fix it
   follows, and what it could break. Rank subtractive and scoping fixes first.
   If the honest answer is that no fix is worth making, say so and why.
4. Propose the cheapest probe for Claude Code to run for the best fix: arms,
   exact variation overrides (same format as
   `bench/variations/stage7-2b-cue-b.json`), the command and scene state each
   arm replays, how to score it with the real matcher, and what a win looks
   like. Prefer a free offline matcher check over a billed run where one can
   decide it.
5. Say which of the "already tried" items your answer would repeat, if any,
   and why it is different this time.
6. List anything you could not verify from the files.

Do not write code. Give story and package text, plus the reasoning above.
