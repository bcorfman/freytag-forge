# ChatGPT Desktop answer, 3C structure and cues (round 2, 2026-10-10)

Source material for the build. Fact ids replace the `FILL` slugs as noted in the
Ringer spec. Matcher claims below were made by ChatGPT; the build's tests
re-check them with the real matcher.

## handoffs.yaml (append under `deliveries:`)

```yaml
- fact_id: FILL # cue_a
  scene_id: 3C
  source_kind: broadcast
  must_convey:
  - [national broadcast, evidence package]
  - [Charles speaks over Michelle, Charles's voice over Michelle]
  fallback_text: The national broadcast stays live while Charles speaks over Michelle.
  cue_text: The national broadcast is live. Charles speaks over Michelle while her evidence package waits to be sent.

- fact_id: FILL # cue_b
  scene_id: 3C
  source_kind: observation
  source_entity_id: kristin
  must_convey:
  - [Rebecca leaves the executive office, Rebecca is leaving the executive office]
  - [Portable data case, data case]
  fallback_text: Rebecca leaves the executive office with the Portable data case.
  cue_text: Rebecca is leaving the executive office with the Portable data case in her hands.

- fact_id: FILL # cue_c_pumps
  scene_id: 3C
  source_kind: observation
  source_entity_id: kristin
  must_convey:
  - [water rises, rising water]
  - [drainage pump controls, pump controls]
  fallback_text: Water rises around the drainage pump controls.
  cue_text: Water rises around the drainage pump controls.

- fact_id: FILL # cue_c_gates
  scene_id: 3C
  source_kind: observation
  source_entity_id: kristin
  must_convey:
  - [surface gates, emergency surface gates]
  - [senior official's authorization, gate authorization]
  fallback_text: The surface gates remain shut as the senior official's authorization nears expiry.
  cue_text: The surface gates are shut above the waiting captives. The senior official's authorization is close to expiry.

- fact_id: FILL # cue_d_reports
  scene_id: 3C
  source_kind: observation
  source_entity_id: kristin
  must_convey:
  - [reports from other detention sites, detention site reports]
  - [broadcast chamber, Michelle's broadcast]
  fallback_text: Reports from other detention sites reach the broadcast chamber.
  cue_text: Reports from other detention sites reach the broadcast chamber.

- fact_id: FILL # cue_d_families
  scene_id: 3C
  source_kind: observation
  source_entity_id: kristin
  must_convey:
  - [families of the missing, missing families]
  - [ask for word, ask for news]
  fallback_text: Families of the missing ask the broadcast chamber for word.
  cue_text: Families of the missing ask the broadcast chamber for word.

- fact_id: FILL # cue_e
  scene_id: 3C
  source_kind: observation
  source_entity_id: kristin
  must_convey:
  - [recovered document, recovered file]
  - [Charles's signal, Charles's last remote channel]
  fallback_text: A recovered document remains closed while Charles's signal runs through his last remote channel.
  cue_text: A recovered document remains closed. Charles's signal still runs through his last remote channel.
```

## knowledge.yaml

Keep the final pointer sentence in each of `a_r1`, `a_r2`, `b_r1`, `b_r2`.
Remove ONLY the final pointer sentence from each of these four `delivery_text`
values (they are false when the other half is already done; the cue supplies the
lead):

```text
c_r1: The gates at the surface remain shut.
c_r2: Water keeps rising around the drainage pump controls.
d_r1: Families of the missing are calling for word.
d_r2: Reports from detention sites still reach the broadcast chamber.
```

## plot.md (one sentence at each place)

| Location | Sentence |
|---|---|
| 3C.1, after "A portable data case..." | Michelle has the evidence package ready at the national broadcast controls. |
| 3C.2, after the first paragraph | Rebecca leaves the executive office with the portable data case in her hands. |
| 3C.3, after the first paragraph | Water rises around the drainage pump controls. |
| 3C.3, after the paragraph where Michelle leads the prisoners through the tunnel | The surface gates remain shut above the waiting captives as the senior official's authorization nears expiry. |
| 3C.4, after the paragraph beginning "Michelle begins publishing..." | One recovered document in the archive remains unopened. |

## world.yaml and 3C metadata (for review; the gates have no entity today)

```yaml
# world.yaml items:
- id: emergency_surface_gates
  name: emergency surface gates
  aliases: [surface gates]
  fixed: true
```

```yaml
# plot.md Scene 3C frontmatter:
item_ids: [portable_archive, drainage_pump_controls, emergency_surface_gates]
item_placements:
  emergency_surface_gates: {parent: facility_escape}
```

## Player commands and the matcher result ChatGPT reported
(None = no unique reveal matches.)

| Command | Result |
|---|---|
| Send the evidence package. | a_r1 |
| Answer Charles's terrorist claim. | a_r2 |
| Inspect the broadcast controls. | None |
| Evacuate the facility. | None |
| Call Rebecca. | None |
| Take the Portable data case from Rebecca. | b_r1 |
| Copy Rebecca's archive. | b_r2 |
| Follow Rebecca out of the executive office. | None |
| Inspect the executive office. | None |
| Open the drainage pump controls. | None |
| Restore the drainage pumps. | c_r1 |
| Lead Michelle through the maintenance routes. | c_r1 |
| Inspect the drainage pump controls. | None |
| Open the surface gates. | c_r2 |
| Release the surface gates. | c_r2 |
| Use the senior official's authorization. | c_r2 |
| Inspect the surface gates. | None |
| Check reports from other detention sites. | d_r1 |
| Read the detention site reports. | d_r1 |
| Call the families of the missing. | d_r2 |
| Contact missing families. | d_r2 |
| Open the reports. | None |
| Watch the families of the missing. | None |
| Open the recovered document. | e_r1 |
| Trace Charles's signal. | e_r2 |
| Read Charles's last signal. | None |
| Inspect the broadcast chamber. | None |
| Send the evidence package to independent networks. | None (matches a_r1 and b_r2) |
