# ChatGPT Desktop prompt: open the 2C evidence step before the purge clock (2026-10-09)

Paste everything below the line into ChatGPT Desktop with the repo files
attached or readable (`data/stories/continuity-initiative/plot.md`,
`storylets.md`, `storylet-routes.yaml`, `knowledge.yaml`, `pacing.yaml`,
`docs/world-model-grounding.md`). Do not edit files. Answer in the format at
the end.

---

## The problem

In live play of scene 2C, players type "Copy the JANUS evidence to my laptop."
on turn 1. Nothing in the story answers it. The turn prompt then says "This
turn has no candidates", the SCENE lines say nothing about the evidence, and
the narrator makes something up. Last run it made up "Project Elysium" and
saved it as a condition on Kristin's laptop. Later turns recalled it, and the
player spent turns chasing it.

Why nothing answers: the copied-files reveals `k_sl_2c_c_r1` and
`k_sl_2c_c_r2` (knowledge.yaml) come from storylet `SL-2C-C`. The story only
opens `SL-2C-C` after the fact `purge_clock_started` is true. That fact is set
by the pacing event `purge_2c` at turn 3 (pacing.yaml). We already removed
`purge_clock_started` from the `requires` of both reveals (PR 551). It did not
help, because `SL-2C-C` itself still has it:

- `storylet-routes.yaml`, `SL-2C-C`, `activation.conditions`:
  `- fact_id: purge_clock_started` / `equals: true`
- `storylets.md`, `SL-2C-C`, **Available when**:
  "The purge/transfer clock is active and understood." (then "Enough evidence
  exists to expose the conspiracy." and "Rescue remains possible but
  dangerous.")

`SL-2C-D` (Michelle's coded message) also lists the purge clock, but it
comes after the evidence step, so leave it alone.

The 2C chain, in order, is: read the transfer orders (`SL-2C-B`, starts the
purge clock), copy the files (`SL-2C-C`), read Michelle's coded message
(`SL-2C-D`).

## Two things to fix

**A. The gate.** Let the copy command count on turn 1, without breaking the
order of the story. The evidence step must still read as the cost of the
choice, not as the thing that starts the purge.

**B. The opening.** In one run, the narrator's 2C opening (the first
narration, before any command) made up "Detention Level 3: Cell 17, Dr.
Michelle McGehee" and the player followed that for all 16 turns. Its opening
began: "Kristin looks around the archive ... as she tries to locate Michelle's
detention cell." The scene `entry_text` in plot.md is:
"The command levels tightened around them. Somewhere above, orders were
already moving - transfers, schedules, contingency plans measured in hours
instead of days. Whatever Kristin and Brandon did next had to count."
The recorded opening prompt is in
`artifacts/e2e-blind-player-prompts-r3.json` (scene 2C, first prompt) if you
can read it. If you cannot, say what you would need to see.

## Rules that already cost us playtime

- Take a pulling line out. Do not add a new one. Naming a place players can
  walk to makes them go there on turn 1 and skip the chain.
- Do not add a new fact, place, name or document. Do not change the plot.
- The `purge_clock_started` fact stays. `SL-2C-B` and the turn-3 pacing event
  still set it. Only the gate on `SL-2C-C` is in question.
- Story text reaches a small narrator model. Write at an 8th-grade reading
  level: short common words, short sentences, one idea per sentence. No
  project words (`entity`, `grounding`, `candidate`).
- Do not use "Rebecca", "relay" or "broadcast" in new text. Do not name
  anything from a later scene.
- Do not suggest a code change.

## Questions

1. **Gate.** Give the exact new `Available when` list for `SL-2C-C` in
   `storylets.md`, and the exact new `activation.conditions` for `SL-2C-C` in
   `storylet-routes.yaml` (old line and new line, with line numbers). Say
   whether the yaml is written from the markdown, so we know which one is
   the source. Keep "Enough evidence exists" and "Rescue remains possible but
   dangerous" unless you can show they also block turn 1; say what they are
   checked against.
2. **Order.** With the gate open, a player can copy the files before the
   purge starts. Read `SL-2C-C`'s `realization_options`, the knowledge
   `statement` and `delivery_text` of `k_sl_2c_c_r1` and `k_sl_2c_c_r2`, and
   the bridge text `t_2c_3a`. Does any of that say or imply the purge is
   already running? Quote any line that does. If one does, give the smallest
   wording change that is true in both orders.
3. **Other gates.** Does anything else keep `k_sl_2c_c_r1` or `k_sl_2c_c_r2`
   from being offered on turn 1 (for example `available_in_scenes`, a pacing
   window, a `bridge_2c_*` activation, or a loader check that ties a reveal's
   `requires` to its storylet)? List each place you checked.
4. **Opening.** Give up to three alternatives for a small change to 2C story
   text (the `entry_text`, the frame situation, or a `Details:` line) that
   makes the opening less likely to invent a cell, a level number or a
   named detention room. Prefer taking a line out. For each, show the exact
   old and new line, and say how likely it is to pull players off the chain.
   Do not claim certainty; we will test.
5. Say which you would pick for A and for B. If you think B should wait,
   say so.
6. Anything in my reading above that is wrong? Check the quotes against the
   files.

## Format

Four short sections: **Gate** (old and new lines, both files), **Order**,
**Other gates**, **Opening** (a table: file and line, old, new, pull risk),
then **Pick**. No preamble.
