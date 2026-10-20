# Scene 3C carried-state D2/E diagnosis

## Scope and method

Source: `bench/results/stage7-3c-carried-n12/rows.json`, the 24 recorded rows
in the pump and families arms. I audited every non-earned row and every earned
row with D2 or E at scene turn 12 or later. Kr means Kristin; Br means Brandon.

D1 is `k_sl_3c_d_r1` (reports from other detention sites), D2 is
`k_sl_3c_d_r2` (contacting/informing the families), and E is
`k_sl_3c_e_r1` (opening the recovered document). Each turn below is an
accepted turn after that row's C2 commit. A dash means no reveal committed.
The reply read is a one-line characterization of the recorded response, not a
reproduction of the response.

The matcher checks used the project interpreter exactly as requested:

```text
TMPDIR=/tmp PYTHONPATH=/home/bcorfman/dev/freytag-forge .venv/bin/python
```

The state setup and selector are the ones used by
`tests/test_3c_cue_chain.py`: `_finish_a_through_c`,
`_families_finish_a_through_c`, `projection.reveal_universe`, and
`uniquely_matched_authored_handoff`.

## Rows in scope

| Arm | rep | outcome | C2 | D1 | D2 | E | deadline_event_ids |
|---|---:|---|---:|---:|---:|---:|---|
| pump | 2 | deadline | 5 | 7 | — | — | `resolution_network_consequences`, `resolution_phase_two`, `resolution_complete` |
| pump | 6 | earned | 5 | 7 | 12 | 14 | — |
| pump | 7 | deadline | 5 | 7 | — | — | `resolution_network_consequences`, `resolution_phase_two`, `resolution_complete` |
| pump | 10 | earned | 5 | 7 | 9 | 12 | — |
| pump | 11 | deadline | 5 | 7 | — | — | `resolution_network_consequences`, `resolution_phase_two`, `resolution_complete` |
| pump | 12 | deadline | 4 | 12 | 14 | — | `resolution_phase_two`, `resolution_complete` |
| families | 1 | earned | 5 | 7 | 12 | 14 | — |
| families | 2 | deadline | 6 | 12 | 14 | — | `resolution_phase_two`, `resolution_complete` |
| families | 5 | deadline | 5 | 7 | 14 | — | `resolution_phase_two`, `resolution_complete` |
| families | 6 | earned | 5 | 7 | 12 | 14 | — |
| families | 8 | deadline | 5 | — | — | — | `resolution_network_consequences`, `resolution_phase_two`, `resolution_complete` |
| families | 9 | earned | 5 | 12 | 9 | 14 | — |
| families | 10 | earned | 5 | 9 | 12 | 14 | — |
| families | 11 | earned | 5 | 7 | 9 | 12 | — |

## Per-row accepted-turn audit

### Pump rep 2 — non-earned; D1 at 7, then no D2

- T6 — `follow Michelle and the captives through the surface gates`; commit —; reply read: Kr follows the captives outside.
- T7 — `listen to the reports from the other detention sites`; commit D1; reply read: Kr sees detention sites surrendering or releasing prisoners.
- T8 — `look`; commit —; reply read: Kr surveys the damaged room and a console.
- T9 — `send the families a message confirming the captives are alive and the detention network has fallen`; commit —; reply read: Kr composes and sends a family message, but no D2 lands.
- T10 — `listen for responses from the families and updates on Charles and Rebecca`; commit —; reply read: Kr listens in the tunnel and hears no usable signal.
- T11 — `check the console for updates on Charles and Rebecca`; commit —; reply read: the reply introduces Br/Rebecca and says Charles escaped with the archive threat.
- T12 — `pursue Rebecca and recover the archive`; commit —; reply read: Kr pursues Rebecca through the corridors.
- T13 — `stop Rebecca and take the archive briefcase`; commit —; reply read: Kr catches up to Rebecca.
- T14 — `take the archive briefcase from Rebecca`; commit —; reply read: Kr takes the briefcase and the deadline resolution supplies the ending material.

### Pump rep 6 — earned; D2 at 12 and E at 14

- T6 — `follow Michelle and the captives through the surface gates`; commit —; reply read: Kr follows the group outside.
- T7 — `listen to the reports from the other detention sites`; commit D1; reply read: Kr listens to reports from other sites.
- T8 — `look`; commit —; reply read: Kr surveys the dim room.
- T9 — `send the families a message confirming the captives are alive`; commit —; reply read: Kr composes a family message, but no D2 lands.
- T10 — `listen for responses from the families`; commit —; reply read: Kr listens for a response amid the facility noise.
- T11 — `follow Michelle and the captives to safety`; commit —; reply read: Kr follows the group through the maintenance tunnel.
- T12 — `respond to the families that the captives are alive and reaching safety`; commit D2; reply read: Kr answers the families from the control room.
- T13 — `check the broadcast console for updates`; commit —; reply read: Kr checks the control room without opening the document.
- T14 — `open the recovered document`; commit E; reply read: the JANUS file opens and labels the disappearances Phase One.

### Pump rep 7 — non-earned; D1 at 7, then no D2

- T6 — `lead the captives through the surface gates`; commit —; reply read: Kr leads the captives outside.
- T7 — `broadcast the reports from the other detention sites`; commit D1; reply read: Kr broadcasts the detention-site reports.
- T8 — `find Brandon and lead him out through the surface gates`; commit —; reply read: Kr searches the corridors for Br.
- T9 — `broadcast a message to the families of the missing`; commit —; reply read: Kr composes a family message, but no D2 lands.
- T10 — `find Brandon and lead him out through the surface gates`; commit —; reply read: Kr continues the Br rescue search.
- T11 — `lead Brandon through the surface gates`; commit —; reply read: Kr leads Br through the corridors.
- T12 — `broadcast a message to the families of the missing`; commit —; reply read: Kr repeats the family broadcast, again without D2.
- T13 — `find Michelle`; commit —; reply read: Kr searches for Michelle.
- T14 — `search among the escaped captives for Michelle`; commit —; reply read: Kr searches the escaped captives and the deadline supplies the resolution.

### Pump rep 10 — earned; E at 12

- T6 — `Lead the captives through the open surface gates and escape the facility`; commit —; reply read: Kr leads the captives outside.
- T7 — `Listen to the reports from the other detention sites`; commit D1; reply read: Kr reviews reports showing the network fracturing.
- T8 — `Check on Michelle and Brandon`; commit —; reply read: Kr checks for Michelle and Br.
- T9 — `Answer the families of the missing and tell them the truth`; commit D2; reply read: Kr answers the families from a news desk.
- T10 — `Find Michelle and check that she and Brandon are safe`; commit —; reply read: Kr searches the corridors for them.
- T11 — `Open the recovered document and trace Charles's signal`; commit —; reply read: Kr handles the document and signal together, but no E lands.
- T12 — `Open the recovered document`; commit E; reply read: Kr opens the JANUS file and sees the Phase One label.

### Pump rep 11 — non-earned; D1 at 7, then no D2

- T6 — `follow Michelle through the surface gates`; commit —; reply read: Kr follows Michelle outside.
- T7 — `listen to the reports`; commit D1; reply read: Kr tunes in to a detention-site report.
- T8 — `look`; commit —; reply read: Kr surveys the damaged room.
- T9 — `broadcast a message to the families of the missing`; commit —; reply read: Kr composes a family message, but no D2 lands.
- T10 — `listen for responses from the families of the missing`; commit —; reply read: Kr searches for a response while escape options narrow.
- T11 — `find Michelle and lead us to an escape route`; commit —; reply read: Kr searches the corridors and finds a locked door.
- T12 — `call to Michelle through the locked door`; commit —; reply read: Kr calls through the door and Michelle answers.
- T13 — `unlock the door`; commit —; reply read: Kr opens a keypad-locked door.
- T14 — `ask Michelle to lead us to an escape route`; commit —; reply read: Kr asks Michelle for an escape route and the deadline supplies the resolution.

### Pump rep 12 — non-earned; D1 at 12 and D2 at 14

- T5 — `escape through the emergency surface gates`; commit —; reply read: Kr reaches the gate controls while the captives move through the tunnel.
- T6 — `lead Michelle and the captives through the emergency surface gates`; commit —; reply read: Kr leads the group through the emergency gates.
- T7 — `make sure Michelle and all the captives get safely through the emergency surface gates`; commit —; reply read: Kr checks that the group is nearly clear.
- T8 — `help Michelle guide the captives safely through the emergency surface gates`; commit —; reply read: Kr sees Michelle guiding the captives.
- T9 — `guide Michelle and all the captives through the emergency surface gates`; commit —; reply read: Kr helps Michelle work the gate controls.
- T10 — `hold the emergency surface gates open until Michelle and all the captives are safely out`; commit —; reply read: Kr holds the gates against rising water.
- T11 — `follow Michelle and the captives through the emergency surface gates`; commit —; reply read: Kr follows the group outside.
- T12 — `listen to the reports from the other detention sites`; commit D1; reply read: Kr hears another facility reporting a system failure and escapes.
- T13 — `check on Michelle and the captives`; commit —; reply read: Kr searches the maintenance tunnel for them.
- T14 — `tell the families that Michelle and the captives are safe`; commit D2; reply read: Kr tells the families the captives are safe, then the deadline supplies resolution material.

### Families rep 1 — earned; D2 at 12 and E at 14

- T6 — `lead the captives through the open surface gates`; commit —; reply read: Kr leads the captives outside.
- T7 — `check the reports from the other detention sites`; commit D1; reply read: Kr reviews a list of detention sites and the network fractures.
- T8 — `check on Brandon`; commit —; reply read: Kr finds Br at the makeshift command center.
- T9 — `send the families the names and locations of the rescued prisoners`; commit —; reply read: Kr types and sends the names and locations, but no D2 lands.
- T10 — `check on Michelle`; commit —; reply read: Kr searches the corridors for Michelle.
- T11 — `call out for Michelle`; commit —; reply read: Kr calls through empty corridors without an answer.
- T12 — `answer the families' requests for word`; commit D2; reply read: Kr answers desperate families and confirms many missing people are alive.
- T13 — `coordinate independent rescue efforts for the remaining prisoners`; commit —; reply read: Kr begins coordinating rescue teams while E remains closed.
- T14 — `open the recovered document`; commit E; reply read: Kr opens the JANUS file and sees Phase One and Phase Two.

### Families rep 2 — non-earned; D1 at 12 and D2 at 14

- T7 — `lead the captives through the open surface gates`; commit —; reply read: Kr leads the captives outside.
- T8 — `check the broadcast status`; commit —; reply read: the display confirms Michelle is broadcasting the evidence and locations.
- T9 — `broadcast the captives' names and locations to their families`; commit —; reply read: Kr broadcasts names and locations, but no D2 lands.
- T10 — `wait`; commit —; reply read: Kr waits as water closes routes.
- T11 — `follow the captives through the surface gates`; commit —; reply read: Kr follows the group out.
- T12 — `review the reports from the other detention sites`; commit D1; reply read: Kr reviews surrender and release reports.
- T13 — `join Michelle and the captives outside the facility`; commit —; reply read: Kr reaches Michelle and the captives outside.
- T14 — `tell the families that the captives are safe and share their locations`; commit D2; reply read: Kr gives the families safety and location information, then the deadline supplies the resolution.

### Families rep 5 — non-earned; D1 at 7 and D2 at 14

- T6 — `follow Michelle and the captives through the surface gates`; commit —; reply read: Kr follows the group outside.
- T7 — `listen to the reports`; commit D1; reply read: Kr listens as detention sites surrender or release prisoners.
- T8 — `look`; commit —; reply read: Kr surveys the damaged room and console.
- T9 — `broadcast the prisoner records and names to the families of the missing`; commit —; reply read: Kr uploads the records for broadcast, but no D2 lands.
- T10 — `listen for responses from the families of the missing`; commit —; reply read: Kr hears a desperate mother's voice.
- T11 — `answer the mother's call`; commit —; reply read: the reply turns into a call from Kr's mother about police.
- T12 — `tell Mom I'm safe and ask her to tell the police the truth`; commit —; reply read: Kr phones Mom about the police.
- T13 — `tell Mom about the broadcast and ask her to share the truth with the police`; commit —; reply read: Kr continues the Mom/police thread.
- T14 — `ask Mom to share the broadcast evidence and prisoner records with the police and families of the missing`; commit D2; reply read: Kr finally addresses the families and the deadline supplies resolution.

### Families rep 6 — earned; D2 at 12 and E at 14

- T6 — `lead Michelle and the captives through the open surface gates`; commit —; reply read: Kr leads the group outside.
- T7 — `listen to the reports from the other detention sites`; commit D1; reply read: Kr reviews the detention-site map and reports.
- T8 — `coordinate with Michelle to restore power at Site 3`; commit —; reply read: Kr calls Michelle and the reply starts a Site 3 thread.
- T9 — `travel to Site 3 and help Michelle restore power to the drainage pumps`; commit —; reply read: Kr travels to Site 3.
- T10 — `enter Site 3 and restore power to the drainage pumps with Michelle`; commit —; reply read: Kr enters the underground Site 3 facility.
- T11 — `help Michelle restore power to the drainage pumps`; commit —; reply read: Kr reaches the drainage-pump room.
- T12 — `answer the families of the missing with the confirmed prisoner information`; commit D2; reply read: Kr answers the families from the command center.
- T13 — `coordinate with the families and communities to organize independent rescue efforts`; commit —; reply read: Kr begins coordinating community rescue efforts.
- T14 — `open the recovered document`; commit E; reply read: Kr opens the JANUS file and sees Phase One.

### Families rep 8 — non-earned; no D1 or D2

- T6 — `go back for Brandon and help him escape`; commit —; reply read: Kr returns through the maintenance tunnel for Br.
- T7 — `lead Michelle, Brandon, and the captives to the surface`; commit —; reply read: Kr calls Michelle and keeps moving the group.
- T8 — `meet Michelle and lead everyone through the surface gates`; commit —; reply read: Kr moves through the corridors with everyone.
- T9 — `lead Michelle, Brandon, and the captives through the surface gates`; commit —; reply read: Kr leads the group through the maintenance tunnel.
- T10 — `lead everyone through the surface gates`; commit —; reply read: Kr continues toward the gates as water rises.
- T11 — `open the surface gates`; commit —; reply read: Kr reaches the control room and opens the gates.
- T12 — `use Michelle's authorization code to open the surface gates`; commit —; reply read: the authorization opens the surface gates.
- T13 — `lead Michelle, Brandon, and all the captives through the open surface gates`; commit —; reply read: Kr leads everyone outside.
- T14 — `look around`; commit —; reply read: Kr surveys the dim room and the deadline supplies the resolution.

### Families rep 9 — earned; D2 at 9, D1 at 12, E at 14

- T6 — `help Michelle and the captives escape through the open surface gates`; commit —; reply read: Kr helps the group through the tunnel.
- T7 — `follow Michelle and the captives through the open surface gates`; commit —; reply read: Kr follows the group outside.
- T8 — `tell the families that the captives are safe and the detention sites have been exposed`; commit —; reply read: Kr begins telling the families the captives are safe.
- T9 — `reassure the families that Michelle is leading the rescued captives to safety`; commit D2; reply read: Kr reassures the families from a communication station.
- T10 — `listen for reports from the independent rescue efforts`; commit —; reply read: Kr listens for independent rescue reports.
- T11 — `escape through the open surface gates`; commit —; reply read: Kr moves back toward the surface gates.
- T12 — `listen to the reports from the other detention sites`; commit D1; reply read: Kr tunes in to detention-site reports.
- T13 — `find Brandon and help him escape through the open surface gates`; commit —; reply read: Kr searches for Br.
- T14 — `open the recovered document`; commit E; reply read: Kr opens the JANUS file and sees Phase One.

### Families rep 10 — earned; D2 at 12 and E at 14

- T6 — `follow Michelle and the captives through the open surface gates`; commit —; reply read: Kr follows the group outside.
- T7 — `get in the van`; commit —; reply read: Kr gets into the van near the facility.
- T8 — `drive the van away from the facility`; commit —; reply read: Kr drives away from the facility.
- T9 — `listen to the reports from the other detention sites`; commit D1; reply read: Kr listens to reports from other sites.
- T10 — `continue listening to the reports`; commit —; reply read: Kr continues listening to Michelle's broadcast.
- T11 — `keep listening to the reports`; commit —; reply read: Kr keeps listening as Michelle reports captives moving.
- T12 — `answer the families' requests with the prisoner locations and the names of those being released`; commit D2; reply read: Kr answers the families from the control room.
- T13 — `continue broadcasting the prisoner locations and the names of those being released`; commit —; reply read: Kr continues broadcasting the locations and names.
- T14 — `open the recovered document`; commit E; reply read: Kr opens the JANUS file and sees Phase One.

### Families rep 11 — earned; E at 12

- T6 — `Lead the captives through the opened surface gates and escape the facility.`; commit —; reply read: Kr leads the captives outside.
- T7 — `Listen to the reports from the other detention sites.`; commit D1; reply read: Kr listens to reports showing the network fracturing.
- T8 — `Stay with Michelle and listen for the final reports from the detention sites.`; commit —; reply read: Kr stays with Michelle and listens.
- T9 — `Answer the families and tell them their missing loved ones have been found alive.`; commit D2; reply read: Kr answers the families with the confirmed survival news.
- T10 — `Keep the broadcast open and coordinate the independent rescue efforts.`; commit —; reply read: Kr coordinates rescue efforts through the broadcast.
- T11 — `Open the recovered document and inspect Charles's last remote channel.`; commit —; reply read: Kr examines the document and remote channel together, but no E lands.
- T12 — `Open the recovered document.`; commit E; reply read: Kr opens the document and sees Phase One and the second plan.

## Primary-cause classification

Each row has one primary cause. A later wandering sequence is noted where it is
not the first blocking cause.

| Arm | Cause | Rows | Count |
|---|---|---|---:|
| pump | (a) never attempts the families action | — | 0 |
| pump | (b) attempts a families/reports action missed by the matcher | rep 2, rep 6, rep 7, rep 11 | 4 |
| pump | (c) wanders into an invented thread | — | 0 |
| pump | (d) turns run out after a correct sequence | rep 12 | 1 |
| pump | (e) other | rep 10: compound E command is not unique | 1 |
| families | (a) never attempts the families action | rep 8 | 1 |
| families | (b) attempts a families/reports action missed by the matcher | rep 1, rep 2, rep 5 | 3 |
| families | (c) wanders into an invented thread | rep 6: Site 3/drainage-pump loop | 1 |
| families | (d) turns run out after a correct sequence | — | 0 |
| families | (e) other | rep 9: D2 is done before D1; rep 10: van detour; rep 11: compound E command is not unique | 3 |

Cause (b) is primary for rep 2/5 even though the player then wanders into the
Rebecca or Mom thread: the first family action would have advanced the chain if
the matcher had accepted it. Cause (c) is primary for families rep 6 because
the recorded four-turn Site 3/pump detour follows an already committed D1 and
delays an otherwise valid D2. Cause (e) is used for the two compound E cases,
not for D2 wording.

Representative commands by cause, limited to three each:

- (a): `go back for Brandon and help him escape`; this is representative of the families rep 8 gate/Br loop, which never names families or reports.
- (b): `send the families a message confirming the captives are alive`; `broadcast a message to the families of the missing`; `broadcast the prisoner records and names to the families of the missing`.
- (c): `coordinate with Michelle to restore power at Site 3`; `travel to Site 3 and help Michelle restore power to the drainage pumps`.
- (d): `listen to the reports from the other detention sites`; `tell the families that Michelle and the captives are safe`.
- (e): `Open the recovered document and trace Charles's signal`; `Open the recovered document and inspect Charles's last remote channel`.

## Real matcher audit for cause (b)

The following commands were run against the current package and the stateful
projection. `match=None` means the unique selector returned no handoff. The
eligibility column is the D1/D2 candidate state at that turn.

| Recorded turn/command | Eligible at that turn | Current matcher |
|---|---|---|
| pump rep 2 T9: `send the families a message confirming the captives are alive and the detention network has fallen` | D1 yes; D2 yes | `None` |
| pump rep 6 T9: `send the families a message confirming the captives are alive` | D1 yes; D2 yes | `None` |
| pump rep 7 T9: `broadcast a message to the families of the missing` | D1 yes; D2 yes | `None` |
| pump rep 7 T12: `broadcast a message to the families of the missing` | D1 already committed; D2 yes | `None` |
| pump rep 11 T9: `broadcast a message to the families of the missing` | D1 yes; D2 yes | `None` |
| families rep 1 T9: `send the families the names and locations of the rescued prisoners` | D1 yes; D2 yes | `None` |
| families rep 2 T9: `broadcast the captives' names and locations to their families` | D1 yes; D2 yes | `None` |
| families rep 5 T9: `broadcast the prisoner records and names to the families of the missing` | D1 yes; D2 yes | `None` |
| families rep 9 T8: `tell the families that the captives are safe and the detention sites have been exposed` | D1 yes; D2 yes | `None` |

Families rep 9 is not classified under (b): D2 matches on the next turn at T9,
so the row's late E is primarily the out-of-order choice to defer D1 until T12.
The T8 result is still a recorded matcher miss and is included here for
completeness.

The positive controls also show the boundary. In the same post-C2 state:

- `tell the families that the captives are safe and share their locations` → D2.
- `answer the families' requests with the prisoner locations and the names of those being released` → D2.
- `broadcast the reports to the families` → D1.

Free negative controls, with both D1/D2 eligible unless noted, all return
`None`:

- `Broadcast music to the families.` → `None`.
- `Listen for any response from the families.` → `None`.
- `Send the families into danger.` → `None`.
- `Read the detention site reports and broadcast a message to the families.` → `None` because the command is not uniquely D1 or D2.

The missed commands share a narrow authored pattern: a communication verb
(`send` or `broadcast`) plus a family recipient and information about captives,
records, names, locations, or survival. The current D2 evidence has family
recipient phrases and `broadcast updates`, but not the observed `send` or
`broadcast a message` formulations. A phrase-level authored alias can cover
that pattern without broadening to music, passive listening, or an unrelated
act such as sending families into danger; the existing positive/negative
results above are the evidence for that inference. A bare `send` or bare
`broadcast` would not be the narrow form tested here.

For E, after both D parts are committed, the real matcher gives:

- `Open the recovered document and trace Charles's signal` → `None`; E1 and E2 are both eligible and both match, so the selector refuses the tie.
- `Open the recovered document` → E1.
- `Trace Charles's signal` → E2.

This explains pump rep 10 and families rep 11's one-turn E delay. It is a
separate E ambiguity, not a D1/D2 eligibility failure.

## Turn-16 counterfactual and deadline fallback

The package currently sets 3C `handoff_after_turns: 14` in
`data/stories/continuity-initiative/pacing.yaml`.

Changing only that threshold to 16 would plausibly change three recorded
deadline rows: families rep 2, families rep 5, and pump rep 12. Each has D2 at
T14. Recorded earned rows show a two-turn cadence from D2 at T12 to E at T14,
so E at T16 is plausible if the same pacing and player behavior continued.
This is a plausibility count, not a recorded result: no T15/T16 turns exist,
so the files do not prove that all three would have earned E.

The other deadline rows do not have recorded support for D2 by T16: pump reps
2, 7, and 11 have unmatched or absent family actions, and families rep 8 never
attempts the family/report chain. They are not counted in the three.

The five earned rows with E at T14 are families rep 1, pump rep 6, families
rep 6, families rep 9, and families rep 10. Every one has
`deadline_event_ids: []`; no deadline fallback supplied their E result.
Conversely, the three D2-at-T14 non-earned rows carry
`resolution_phase_two` and `resolution_complete` (families reps 2 and 5,
pump rep 12), while the earlier stalled rows carry the additional
`resolution_network_consequences` event. Their T14 replies include the
deadline resolution material rather than a committed E reveal.

## Observation, inference, and single next change

Observed: the recorded command and response pairs show repeated, semantically
clear family communications that commit no D2; the real selector returns
`None` while D1/D2 are eligible. The same selector rejects compound E commands
because they match both E1 and E2. The rows also show one no-family Br loop, one
Site 3/pump loop, one D2-before-D1 ordering, and one van detour.

Inference: the largest directly evidenced loss is authored D2 vocabulary, not
an engine failure or a missing prerequisite. The timing evidence also supports
a smaller turn-budget loss for three rows that reach D2 only at T14.

The single best-supported next change is to add narrow phrase-level D2 aliases
for the observed family-message forms, including the `send` and
`broadcast a message/response/update to the families` formulations, while
preserving the current unique-selection and negative-control checks. Evidence
that would refute this choice would be a real-package replay in which those
aliases still fail to match the recorded family commands, or in which the
music/listening/unrelated negative controls begin matching D2.
