I recommend replacing **four setting-fact lines with one physical description**. This is a proposal for the requested Ringer handoff; no files were changed.

In [plot.md:362](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:362), replace lines 362–365.

Old:

```yaml
- The cooling-service archive panel stands beside the inspection console in the infrastructure corridors.
- The cooling-service archive panel looks like a ventilation grille.
- The visible seam outlines the cooling-service archive panel.
- The access panel beside the inspection console is the cooling-service archive panel.
```

New:

```yaml
- The cooling-service archive panel has a slotted face.
```

Keep lines 366–371 unchanged:

```yaml
- The cooling-service archive panel leads directly from the infrastructure corridors into the records archive.
- The cooling-service archive panel opens with a push.
- The cooling-service archive panel has no lock.
- The cooling-service archive panel has no keypad.
- The cooling-service archive panel has no screen.
- Using the cooling-service archive panel requires no further credentials.
```

This follows the grounding guide, narrator-writing guide, and linked memory principles: subtract redundant material, describe the concrete object, and leave narrator rules until last. It uses the established source-material repair technique; this particular wording remains untested.

The changes have distinct purposes and risks:

| Original line | Reason for change | Possible loss |
|---|---|---|
| 362: location | Duplicates the unchanged placement text at line 360. | Less location reinforcement in scene-wide facts. |
| 363: grille comparison | Replaces a comparison between two nouns with a physical property of one object. | “Slotted face” may evoke a grille less reliably. |
| 364: seam | Removes another descriptive reference. | The narrator may stop mentioning a visible seam. |
| 365: identity equation | Removes the second panel noun that the model might separate from the first. | Less explicit reinforcement of the “access panel” wording. |

Of the three hypotheses, **two names for one thing is the most directly targeted explanation**, but N=1 does not establish it. Echo remains plausible: this reduces the long name from 12 mentions to nine in the recorded user-prompt structure. It does not guarantee that the narrator stops saying that name. Negative hardware priming is also plausible, but I would retain those exclusions in this first change because the smoke avoided the earlier hardware invention.

Leave [world.yaml:256](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/world.yaml:256) unchanged. The tracked name and scoped aliases—including `access panel`, `hidden panel`, `grille`, `ventilation grille`, and `seam`—remain attached to the same entity. Removing those words from descriptive sentences does not remove their alias declarations.

**Match selection is still unestablished.** The recorded prompt explicitly assumes the panel appears in THINGS; its `things_assumption` says the real selection rate was not measured. Existing aliases preserve the intended resolution target, but this smoke cannot prove the match call picks it.

The proposal preserves the working boundaries:

- The route-neutral bridge at lines 378–380 stays unchanged.
- The normal exit still depends on `restricted_corridor_access`, independently of panel use.
- The destination and push affordance remain explicit.
- No archive contents or JANUS information enter the 2A material.
- The 2B reveal machinery stays unchanged; the recorded continuation earned JANUS there.

I would add no narrator rule or regex gate. A payload diff and live rerun remain necessary to establish whether this removes the contrast without reintroducing invented hardware or a second panel.