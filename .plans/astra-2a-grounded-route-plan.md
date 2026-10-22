Propose **the cooling-service archive panel**: one fixed, push-open object beside the inspection console. It leads directly into the records archive. It has no separate actionable hardware.

This is proposed package text for the later Ringer task. No story files were changed or live probes run.

**`world.yaml`**

Insert immediately after the `inspection_console` declaration:

```yaml
- id: cooling_service_archive_panel
  name: cooling-service archive panel
  kind: thing
  fixed: true
  openable: true
  open: false
  hidden: false
  scoped_aliases:
  - access panel
  - hidden panel
  - concealed panel
  - panel
  - grille
  - ventilation grille
  - seam
```

Its parent is `infrastructure_corridors`, declared through the scene placements below. The current `Item` schema has no `parent` field; putting one here would not be a valid way to establish its location.

“Hidden panel” is a player reference, not a hidden-state declaration. The object is inconspicuous but visible. Making it mechanically hidden would require a separate fact-backed reveal and risk another prerequisite.

The aliases identify the whole panel. “Grille” and “seam” do not introduce removable components. No keypad, reader, screen, latch, or release button is proposed.

**Technique:** copies the 1B bench repair: a unique world identity, common scene-scoped names, fixed status, and explicit placement.

**Risk / unestablished:** broad aliases could absorb references to unrelated ventilation hardware while this object is in scope. Actual name resolution and earlier-scene leak behavior still need verification.

**`plot.md`: 2A scope and placement**

Replace:

```yaml
item_ids: [transit_card, hideout_servers, inspection_console, facility_gate]
```

with:

```yaml
item_ids: [transit_card, hideout_servers, inspection_console, facility_gate, cooling_service_archive_panel]
```

Insert under 2A’s `item_placements`:

```yaml
  cooling_service_archive_panel:
    parent: infrastructure_corridors
    text: beside the inspection console in the infrastructure corridors
```

Insert after the complete `item_placements` mapping, before `character_placements`:

```yaml
setting_facts:
- The cooling-service archive panel leads directly from the infrastructure corridors into the records archive.
- The cooling-service archive panel opens with a push.
- Using the cooling-service archive panel requires no further credentials.
```

These describe a declared object’s affordance. They do not assert discovery, passage, earned access, or knowledge.

In **Scene 2A.3**, insert immediately after the existing console-limits paragraph:

> The cooling-service archive panel stands beside the inspection console. It is easy to mistake for a ventilation grille. Its seam belongs to the same panel. A push opens it directly into the records archive. This route ends at the records archive.

Keep the console-limits paragraph unchanged. The new text names only the declared panel, `inspection_console`, and `janus_archive`. The grille and seam are references to the panel itself.

**`plot.md`: `t_2a_2b` wording**

Replace:

```yaml
  t_2a_2b: >-
    Their false credentials survived the initial checks, and Kristin's warning about unstable cooling-water pressure
    won them access to restricted infrastructure corridors. Beyond those corridors, the records archive waited behind
    another layer of security.
```

with:

```yaml
  t_2a_2b: >-
    Kristin and Brandon gained access to the infrastructure corridors under their inspection cover.
    The cooling-service archive panel gave them direct access to the records archive.
    They entered the records archive.
```

This replacement accompanies the declared route; it is not another standalone bridge-deletion experiment. It removes the implied additional obstacle from this route’s committed transition.

**`plot.md`: retain identity in 2B**

Replace:

```yaml
item_ids: [archive_terminals, medical_terminal]
```

with:

```yaml
item_ids: [archive_terminals, medical_terminal, cooling_service_archive_panel]
```

Insert under 2B’s `item_placements`:

```yaml
  cooling_service_archive_panel: {parent: infrastructure_corridors}
```

The fixed panel retains its original parent. It does not move into the archive.

Insert after that mapping, before `entry_text`:

```yaml
setting_facts:
- The cooling-service archive panel connects the infrastructure corridors to the records archive.
- Kristin has already reached the records archive.
- The archive terminals are available for investigation.
```

Keep the existing 2B entry text.

**Technique:** the placements repeat the bench-grounding method. The bridge uses the existing runtime-controlled transition to deliver arrival, rather than asking generated prose to create access.

**Risk / unestablished:** the route changes canon and may appear earlier than intended in 2A’s payload. Follow-up narration might still invent hardware or describe passage inconsistently. The shipped payload diff and live smoke must establish whether the material reaches the relevant turn and prevents the chase.

**`knowledge.yaml` and `handoffs.yaml`**

No changes.

Panel discovery, opening, or passage earns no archive evidence. Preserve `k_sl_2b_a_r1`, its prerequisites, action evidence, effects, and delivery text exactly. Preserve the existing handoffs.

**Technique:** retain the existing authored reveal handoff: an eligible investigation earns the disclosure, then the runtime delivers it. The route supplies access only.

**Risk / unestablished:** existing narration can contradict an appended delivery, as the recorded rows demonstrate. Keeping the handoff unchanged preserves its boundary but does not establish that the new route fixes that behavior.

**Outcome and limits**

The normal 2A exit remains available without searching for the panel: `t_2a_2b` still depends on `restricted_corridor_access`. No panel-discovery or panel-opening fact is added to its eligibility.

Once access is earned, the transition delivers arrival in the archive. Finding the panel does not create another credential check, lock puzzle, or detention route. The intended continuation reaches the archive within two commands; **that behavioral bound remains unproven**, especially if discovery happens before existing 2A requirements are satisfied. Package prose cannot enforce a two-command guarantee while preserving those requirements and unrestricted player actions.

Still required before adoption: loader validation, real `_matches_all` positive/near-miss checks, shipped payload diff, alias-resolution inspection, and the preregistered smoke and screen. JANUS remains earned in 2B; the proposed 2A text discloses no archive contents.