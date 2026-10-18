I recommend changing only three passages in `plot.md`: make the bridge route-neutral, put the panel’s identity in `setting_facts`, and remove its ineffective beat paragraph. This is the requested proposal for later Ringer application; no files were modified.

**1. Replace the bridge**

At [plot.md:371](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:371), replace lines 371–374.

Old:

```yaml
  t_2a_2b: >-
    Kristin and Brandon gained access to the infrastructure corridors under their inspection cover.
    The cooling-service archive panel gave them direct access to the records archive.
    They entered the records archive.
```

New:

```yaml
  t_2a_2b: >-
    Kristin and Brandon gained access to the infrastructure corridors under their inspection cover.
    They continued into the records archive.
```

This names no route, credential, lock, or additional check. The existing 2B entry text—“The records archive hummed behind the restricted corridor”—still follows naturally.

**Technique copied:** runtime-controlled transition prose describes the earned arrival without inventing an optional action.

**Risk / unestablished:** this removes the bridge’s false panel-use claim, but cannot prevent generated narration immediately before it from inventing an obstacle.

**2. Put the panel’s identity in the persistent narrator material**

At [plot.md:361](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:361), replace lines 361–364.

Old:

```yaml
setting_facts:
- The cooling-service archive panel leads directly from the infrastructure corridors into the records archive.
- The cooling-service archive panel opens with a push.
- Using the cooling-service archive panel requires no further credentials.
```

New:

```yaml
setting_facts:
- The cooling-service archive panel stands beside the inspection console in the infrastructure corridors.
- The cooling-service archive panel looks like a ventilation grille.
- The visible seam outlines the cooling-service archive panel.
- The access panel beside the inspection console is the cooling-service archive panel.
- The cooling-service archive panel leads directly from the infrastructure corridors into the records archive.
- The cooling-service archive panel opens with a push.
- The cooling-service archive panel has no lock.
- The cooling-service archive panel has no keypad.
- The cooling-service archive panel has no screen.
- Using the cooling-service archive panel requires no further credentials.
```

These sentences describe the declared object and its affordance. They do not say Kristin discovered it, opened it, passed through it, or earned any knowledge. They also avoid permanently declaring it closed or open.

The current source contains **three** setting facts; the placement sentence supplies the fourth panel-related constraint mentioned in the prompt. Repeating its location here makes the identity block self-contained.

**Technique copied:** the authoring guide’s verbatim `setting_facts` channel, plus the grounding guide’s concrete identity and placement method used for the bench repair. Positive description comes before the short hardware exclusions.

**Risk / unestablished:** scene-wide facts can surface the route while Kristin is still at the hideout. Explicitly locating it in the corridors reduces location ambiguity but does not provide beat gating. Negative hardware sentences might still prime unwanted vocabulary. Neither narrator compliance nor reliable match selection is established by this proposal.

**3. Remove the unused paragraph**

At [plot.md:425](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:425), delete:

```text
The cooling-service archive panel stands beside the inspection console. It is easy to mistake for a ventilation grille. Its seam belongs to the same panel. A push opens it directly into the records archive. This route ends at the records archive.
```

New: no replacement paragraph. Keep the preceding console-limits paragraph unchanged.

**Technique copied:** move actionable description into a documented narrator-facing channel instead of relying on beat prose.

**Risk / unestablished:** readers lose that paragraph in the beat narrative, although its useful description remains in the scene metadata. This deletion alone has no demonstrated behavioral benefit.

I considered `SL-2A-C`, whose existing realization describes access to the diagnostic console. It is the natural storylet carrier, copying that concrete affordance technique. However, its availability concerns the supervisor confrontation; it is not a reliable persistent source for every panel-search turn. Adding the panel there could also encourage premature discovery during that confrontation. I recommend leaving `storylets.md` unchanged.

**Aliases and normal exit**

Keep [world.yaml:256](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/world.yaml:256) unchanged. The unique name remains `cooling-service archive panel`; its scoped aliases already include all six requested terms, plus `ventilation grille`. Keeping common words scoped follows the grounding guide and avoids introducing new global leak vocabulary. Broad aliases can still absorb unrelated seams or grilles; they cannot force the match call to include the panel in `refers`.

The normal exit remains independent of panel discovery or use:

- [pacing.yaml:243](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/pacing.yaml:243) requires `restricted_corridor_access == true`, with no panel dependency.
- [storylet-routes.yaml:2717](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/storylet-routes.yaml:2717) retains the canonical producer activated by `false_identities_ready` and `rebecca_observing_infiltrators`.

Only the three identified `plot.md` passages are proposed for modification. No eligibility, facts, matcher rules, player-wording restrictions, knowledge, or handoffs change. JANUS remains earned in 2B. Loader checks, shipped-payload comparison, and live behavior remain unverified.