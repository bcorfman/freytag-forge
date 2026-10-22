My earlier statement that `handoffs.yaml` needed no changes was wrong. Both new bridge facts need deadline deliveries. Also, **both new deliveries are unreachable under the stated ordering algorithm**: N-2 reaches its two-fact threshold before it ever needs the fourth entry.

**N-1: keep Option A and the existing order.**

The recording remains a valid earned alternative without adding national-network knowledge to it. At the deadline, if neither alternative is known, the player receives the existing logistics discovery. If either is already known, no additional alternative is delivered.

Option B would expand what R2 reveals. Putting the strategy first would change the default deadline revelation merely to make its delivery reachable. Accepting forced exits would retain the original contradiction. A required but unused deadline delivery is the smallest repair here.

**N-2: keep Option A and the existing order.**

The bait discovery remains distinct from Brandon’s admission. At the deadline, the existing priority favors Brandon’s role and claimed reform motive. If the player already knows they were bait but lacks Michelle’s resistance evidence, the backstop supplies **Brandon’s role**, completing the threshold.

Option B would make an admission part of every earned R3. Putting bait first would change the default deadline path without resolving any additional earned-exit problem. Accepting forced exits would leave R3 unable to earn the exit even after Michelle’s evidence.

Insert these entries into the existing FactDelivery list in `handoffs.yaml`:

```yaml
- fact_id: architects_strategy_known
  scene_id: 1C
  source_kind: observation
  source_entity_id: kristin
  must_convey:
  - [Charles and Rebecca]
  - [made the crisis]
  - [rule as its promised solution]
  fallback_text: >-
    A recording shows that Charles and Rebecca made the crisis.
    They plan to rule as its promised solution.
  cue_text: The recorded conference is available to play.
  costs: []

- fact_id: kristin_was_bait
  scene_id: 2B
  source_kind: observation
  source_entity_id: kristin
  must_convey:
  - [Charles expected Kristin to seek Brandon]
  - [Michelle's evidence]
  - [expose Brandon's hidden network]
  fallback_text: >-
    Charles expected Kristin to seek Brandon.
    He left Michelle's evidence where she could find it and expose Brandon's hidden network.
    Corrupted files flicker on the medical terminal.
  cue_text: Corrupted files flicker on the medical terminal.
  costs: []
```

The fallbacks reproduce the existing earned delivery text. No new evidence-gap or trust penalty is justified by the supplied material.

Keep these bridge activation blocks in `storylet-routes.yaml`:

```yaml
# bridge_1c_infiltration_needed
activation:
  all_facts_true: [facility_proof, captives_confirmed_alive]
  any_of: [national_detention_network_known, architects_strategy_known]
  at_least: 1
```

```yaml
# bridge_2b_archive_crisis
activation:
  all_facts_true: [janus_evidence]
  any_of:
  - brandon_janus_role_known
  - brandon_claimed_reform_motive
  - michelle_resistance_known
  - kristin_was_bait
  at_least: 2
```

The ordering tables below cover the alternative facts. Independently, the backstop also supplies any missing `all_facts_true` prerequisites through their existing deliveries.

For N-1, **N** means `national_detention_network_known`; **S** means `architects_strategy_known`.

| Already known | Alternative facts delivered |
|---|---|
| Neither | N |
| N | None |
| S | None |
| N, S | None |

The strategy fallback is never selected. No unintended alternative is added after an earned R2.

For N-2, **R** means `brandon_janus_role_known`, **M** means `brandon_claimed_reform_motive`, **H** means `michelle_resistance_known`, and **B** means `kristin_was_bait`.

| Already known | Alternative facts delivered |
|---|---|
| None | R, M |
| R | M |
| M | R |
| H | R |
| B | R |
| R,M / R,H / R,B / M,H / M,B / H,B | None |
| R,M,H / R,M,B / R,H,B / M,H,B | None |
| R,M,H,B | None |

**The B-only case crosses alternatives:** the player receives Brandon’s role despite having played R3. This is an intentional deadline backstop under the retained priority, not an additional earned realization. The bait fallback itself never fires; the earlier three entries always suffice.

No `plot.md` change is needed. No replacement is needed for Scene 1C’s supplied `bridge_text` or either earned delivery text. Scene 2B’s bridge prose and existing deadline fallbacks were not supplied, so I would check them before claiming they need no changes.

Before applying, check:

- Kristin is declared a participant in both scenes, and the recording and medical terminal are visible when their cues can appear.
- Existing Brandon deadline text does not imply his reform motive was delivered when only his role was supplied.
- Delivery costs do not retract bridge prerequisites or otherwise invalidate the ordering table.
- Package loading and deadline verification pass for both earned alternatives and every table row. The tables are a logical check, not a reported test run.