# ChatGPT prompt: the invented keycard door that stalls scene 2B

Paste everything below the line into ChatGPT Desktop. It has the project files
open, so it reads them itself. Bring the answer back to Claude Code, which
applies it through a Ringer task and probes it.

---

You are helping fix a defect in an interactive-fiction engine, `freytag-forge`,
and its story package `data/stories/continuity-initiative/`. You can read the
repository. Read these first, in order, and follow them: `AGENTS.md`,
`docs/scene-fixing-guide.md`, `docs/world-model-grounding.md`,
`docs/narrator-writing-guide.md`, `docs/player-input-guide.md`, then
`data/stories/continuity-initiative/plot.md` (Scenes 2A and 2B),
`handoffs.yaml`, `pacing.yaml` and `knowledge.yaml`.

## The defect

A hosted run of the whole story with a "raw" blind player (an LLM that sees
only the screen and types free text) got stuck for 14 of 15 turns in scene 2B
and left only on the forced handoff. The player never earned a 2B reveal.

What happened, from the recorded run:

1. In scene 2A the player's last command was "Look for a concealed route or
   access panel leading from the service corridors to the detention area."
   The narrator answered with an invented object: "she notices a small,
   unmarked door with a keycard reader and a ventilation grille." Nothing in
   the story package declares an unmarked door, a keycard reader or a
   ventilation grille as a place or thing. The words `keycard` and `unmarked`
   appear nowhere in `plot.md` or the YAML files. That reply is the 2A exit
   turn, so the authored 2B entry text ("The records archive hummed behind the
   restricted corridor...") is appended after it.
2. The 2A turn-7 narrator prompt (recorded in
   `bench/results/stage7-blind-raw/attempt-1/e2e-blind-player-prompts.json`,
   scene `2A`, turn 7) carries strong credential material: SCENE lines about
   "inspector credentials", "technical credentials", "false identities", and a
   pacing event shown this turn, "A second credential check threatens their
   inspector cover." (`pacing.yaml`, the 2A event). The player's command asked
   for a hidden panel, and the narrator supplied a credential-style door.
3. In 2B the player took up the invention. Its first command was "Examine the
   unmarked door, keycard reader, and ventilation grille." Its next 13
   commands asked for "inspector credentials", an "inspector ID and password",
   and searched "financial data" and "government and financial records".
   None of the 15 commands matches any 2B reveal under the real matcher
   (`storygame/runtime/candidate_matcher.py`, `_matches_all`).
4. The 2B reveals need the player to name Michelle's file or selection files
   (`k_sl_2b_a_r1`), "my record" (`k_sl_2b_a_r2`), or, after `janus_evidence`,
   development records, security logs, corrupted files or maintenance reports
   (`knowledge.yaml`, ids `k_sl_2b_*`). The `janus_evidence` cue in
   `handoffs.yaml` reads "Selection files fill the archive terminals.
   Government and financial records sit open beside them." and shows on turn 1
   and again at the turn-10 nudge.

Full transcript: `bench/results/stage7-blind-raw/attempt-1/e2e-blind-player.json`
(scenes `2A` and `2B`, field `turns`). Plan record:
`.plans/implementation_plan.md`, Stage 7 step 1 result, 2B DIAGNOSIS and 2B CUE
PROBE.

## What was already tried (do not recommend it again)

A live probe changed only the 2B `janus_evidence` cue. Each arm had 12 trials of
the same setup: recorded 2A exit text, the recorded first command, live 2B
narration, then a raw player picks command 2, scored by the real matcher.

- Current cue: 0/12 earn a 2B reveal.
- "Selection files fill the archive terminals. Michelle's file is one of them.":
  0/12.
- "Selection files fill the archive terminals. One file carries Michelle's name,
  and another carries Kristin's.": 2/12.

Commands that name the invented door, keycard, grille or credentials: 12/12,
11/12 and 10/12. So the cue wording is a weak lever; the invented door in the
2A exit turn is the strong pull. Do not propose another cue rewrite as the main
fix.

## Rules you must follow

- Use only techniques the project already proved. `docs/scene-fixing-guide.md`
  and `docs/world-model-grounding.md` list them. In order: missing story
  material goes in as a reveal handoff or a statement; a line that pulls the
  narration the wrong way is scoped or removed; a narrator rule comes last,
  and only if it is story-neutral. Most tried rules lost their probes. Say
  which proven technique each fix uses and where an earlier scene used it
  (for example 3A's captives talk line, 2C's stale 1A recall, 3B's missing
  3B.2 office-entry line).
- Remove before adding. Prefer a subtractive fix.
- Never use keyword or regex scanning of narration as a gate. Never repair
  places by scanning prose.
- Facts are the only mutable truth; the shared runtime stays story-agnostic.
  Do not propose engine changes. Your fix is story material, scoping or
  removal in the package files, or a story-neutral narrator rule.
- If you propose declaring a thing (for example a door or reader that the 2A to
  2B corridor really contains), follow the Things and Names sections of the
  grounding guide: kind, `fixed`, placement, scoped aliases, and the leak-term
  caution. Do not give a bare common word to a later-scene thing.
- Do not weaken a correct guard, and do not widen `action_evidence` just to
  make a recorded command match. An evidence change is allowed only for a
  proven authoring miss, and only with the matcher's rules in mind: whole
  words, possessives, negation words, exactly one match per command.
- New text is plain: 12th-grade reading level, one idea per sentence, no
  figurative filler.

## What I need from you

1. Confirm or correct the diagnosis. Name the lines in `plot.md`, `pacing.yaml`,
   `handoffs.yaml` and `knowledge.yaml` that pull the 2A exit turn toward an
   invented credential door, and say whether the player's own "concealed route
   or access panel" wording, the pacing event, or the SCENE credential lines is
   the strongest cause. Quote the lines. If you think something else is
   responsible, say so and show the evidence.
2. Give two or three ranked fixes. For each: the exact file, the exact old
   text, the exact new text (or the deletion), why it should stop the
   invention or redirect the player, the earlier fix it follows, and what it
   could break. Rank subtractive and scoping fixes first.
3. For the best fix, say what the 2B player should do next and what the 2A exit
   turn should mention instead, using only things the story declares. If the
   corridor really needs a door to the archive, say how to declare it so a
   reply naming it resolves to a real thing.
4. Propose probe arms for Claude Code to run: one per candidate cause, the
   exact variation overrides (same format as
   `bench/variations/stage7-2b-cue-b.json`), and which command and scene state
   each arm replays. Say how to score it and what 12 trials per arm must show
   to count as a win. Claude Code will run the probe and apply the winner.
5. List anything you could not verify from the files.

Do not write code. Give story and package text, plus the reasoning above.
