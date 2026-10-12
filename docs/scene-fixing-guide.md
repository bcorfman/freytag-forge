# Scene-fixing guide

Recommend only techniques already supported by the project. Before proposing
a fix, check the decisions in section 12 of `.plans/world-model.md` (including
the “Brandon chose” entries), [the world-model grounding guide](world-model-grounding.md),
and fixes that landed in earlier scenes. Name what you checked; propose a new
technique only when none covers the case.

For each scene, ground places, things, and placements; keep payloads
byte-identical except for approved lines; add reveal handoffs; write a bench
script; run three live replicates; then fix what the evidence shows.

When a turn narrates the wrong thing or misses what the plot says happens,
follow these steps in order:

1. Read the full recorded prompt beside the scene in `plot.md`. Check whether
   it includes the story material needed and whether any SCENE line, talk line,
   or stale recall pulls the narration the other way. Past examples include
   3B's missing 3B.2 office-entry line, 3A's captives talk line, 2C's silent
   stance, and 2C's stale 1A recall.
2. Probe recorded prompts before building. Replay live with one arm per likely
   cause; add the missing plot sentence unchanged or remove the conflicting
   line. Use 10–15 samples per arm through Ringer and read every narration.
   Score the narration, not `item_facts`, which can report moves the prose did
   not make. On reveal turns, score the narration plus appended delivery text:
   the narrator writes only the lead-up, so stopping there can mean the handoff
   worked.
3. Fix the source identified by the probe. Missing story material belongs in
   a reveal handoff or in a statement written in ChatGPT Desktop and scored
   with the real matcher. Scope or remove a line that pulls the wrong way. Add
   a narrator rule only for a story-neutral behavior and only when its probe
   arm wins. Most tried rules lost: the go-into-a-place rule (1/15 vs 4/15),
   the plain-corridor rule, and the copy-refers rule. One won: “When the player
   talks to someone, that person answers.”
4. Rerun the same bench script with the same replicate count and read it with
   the scene check. Record what changed and what remains open in the plan.
