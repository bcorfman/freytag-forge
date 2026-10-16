# World-model remaining checklist

Reviewed 2026-10-15 against [implementation_plan.md](implementation_plan.md).
S1–S4 and the later 1B/1C fixes are complete. There is no additional active
implementation work to schedule from this plan.

## Conditional follow-up not already explicit in the implementation plan

- [ ] **Only if a story depends on an undeclared condition:** declare the
  necessary state axis, then include it in capture evaluation. Until then,
  score places and declared axes only; undeclared conditions remain unscored.
  This is the bookmark Brandon retained on 2026-10-03, not a request to add
  axes exhaustively or reopen the completed runtime integration. Report this
  scoring boundary alongside the implementation plan's 92% accuracy target.

## Already covered — do not duplicate

- Judge calibration, real state/cost reporting and game-break handling:
  implementation plan **2**.
- Reference resolution and unresolved existing entities: **4** and **5**.
- Concealment, custody, narration/capture inconsistencies and parked defects:
  **5**. Reopen parked knock-out, state-echo, false-pole, bare-corridor and
  hand-back cases only when current play reproduces them.
- Package audits, save/load, runtime-path continuity, dependency breaks,
  accuracy and staging qualification: **6** and **7**.
- Any outcome-first redesign: **8**, subject to its existing gates.

## Decisions and evidence

Use the [grounding guide](../docs/world-model-grounding.md) for current
world-model rules and the [scene-fixing guide](../docs/scene-fixing-guide.md)
for diagnosis. The start-place rule and command-scoped state wording were
kept; old removal experiments are not outstanding tasks.

The full decision and measurement record is preserved in git at
`5ea0119955c62b84699a8dc7878a4af770b55a7e`. Retrieve it with:

```sh
git show 5ea0119955c62b84699a8dc7878a4af770b55a7e:.plans/world-model.md
```

For historical rationale, read section 12 (W1–W14) and the later dated
“Brandon chose” entries together; amendments supersede earlier proposals.
Do not treat historical “Next” lists or unfinished checkboxes as active work.
