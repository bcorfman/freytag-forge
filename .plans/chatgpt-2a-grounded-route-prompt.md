# ChatGPT prompt: ground the 2A concealed-route search (candidate 2)

Paste everything below the line into the ChatGPT Desktop thread used for the
2A door work. It has the repository, so the prompt points at files instead of
quoting them. Bring the answer back to Claude Code, which applies it through a
Ringer task, runs the loader, `_matches_all` positive/near-miss checks and the
payload diff, then probes it. Source plan: `.plans/astra-fixes-plan.md`
section 2, candidate 2.

---

Ground the route that the 2A narrator keeps inventing, so it becomes a
declared world entity with a bounded outcome. Give me story and package text,
not code.

## Read first

- `.plans/astra-fixes-plan.md` (sections 1 and 2), and the "Stage 7 door"
  results in `.plans/implementation_plan.md`.
- `bench/results/stage7-door-n12/prompts/control.json` (the recorded 2A
  prompt), and the narrations in `bench/results/stage7-door-source-n12/` and
  `bench/results/stage7-door-completion-smoke/`.
- `docs/world-model-grounding.md`, `docs/narrator-writing-guide.md`,
  `docs/markdown-story-authoring.md`.
- `data/stories/continuity-initiative/`: `plot.md` (2A and 2B), `world.yaml`,
  `knowledge.yaml` (`k_sl_2b_a_r1`), `handoffs.yaml`.

## The defect

The player's search command ("Look for a concealed route or access panel
leading from the service corridors to the detention area.") is player input,
not plot. The narrator finishes it by inventing an object that no file
declares: a panel behind a maintenance console (sometimes with a keypad and
screen), a ventilation grille, or a seam. The player then chases it and
sometimes never reaches the 2B archive.

Already lost, do not propose again: command rewrite, credential-review
rewrite, stale-scene removal, bridge deletion, perimeter deletion,
console-limits addition, and deleting "Finish each action the player gives."

## What I need

Design ONE fixed, uniquely named route object the narrator can use instead of
inventing one:

1. **`world.yaml`:** the entity (id, name, kind, parent, `fixed: true`, and any
   actionable hardware). Pick a scene-specific name. A bare common word such
   as "door" or "panel" is leak-scanned in earlier scenes and rejected. Put the
   plain words in `scoped_aliases`. Every physical noun in your text must
   resolve to a declared entity.
2. **`plot.md` 2A:** scene scope, `item_ids`, `item_placements` in the
   `{parent: ...}` form, and the `t_2a_2b` transition wording.
3. **Outcome:** using the object gives access to the existing records-archive
   investigation. It adds no credential prerequisite, no second lock, and no
   detention access. The console limits stay. The player reaches the archive
   within two commands of finding it.
4. **`knowledge.yaml` / `handoffs.yaml`:** only if the outcome needs it, and
   only for the approved outcome or evidence delivery. JANUS disclosure stays
   earned in 2B. Do not touch the matcher.

Keep the usual rules: plain 12th-grade text, one idea per sentence, no facts
created by prose, no keyword or regex gates, no engine changes, no restriction
on player wording, and no archive contents disclosed in 2A.

## Answer format

For each file: exact old and new text (or the insertion point), the proven
technique it copies (scene 1B bench grounding; authored reveal handoffs), what
it could break, and what you could not establish. Also say how the object is
named so "access panel", "hidden panel", "grille" and "seam" resolve to it,
and confirm the normal 2A exit still works when the player never looks for it.
