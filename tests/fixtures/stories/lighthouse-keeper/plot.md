# A Light on the Shore

**Genre:** Mystery

## Scene 1A — The Cottage
---
scene_id: 1A
location_id: cottage
freytag_phase: exposition
objective: Find the brass key
participant_ids: [ada, tom]
item_ids: [ada_lantern, sea_chest, keeper_bench, brass_key, rowboat, logbook]
item_placements:
  ada_lantern: {parent: parlour, text: on the parlour windowsill}
  sea_chest: {parent: parlour, text: against the parlour wall}
  keeper_bench: {parent: parlour}
  brass_key: {parent: keeper_bench, under: true}
  rowboat: {parent: shore, text: pulled up on the shore}
  logbook: {parent: keeper_bench, text: on the bench}
entry_text: Ada returns to the cottage before the lamp is due.
transition_ids: [t_1a_1b]
bridge_text:
  t_1a_1b: Ada carries the lantern into the lamp room.
---

### Scene 1A.1 — The Search

**Details:** a quiet cottage; a dusty bench; a locked chest

Ada searches the cottage for the key.

## Scene 1B — The Lamp Room
---
scene_id: 1B
location_id: lamp_room
freytag_phase: rising_action
objective: Tend the lamp
participant_ids: [ada]
item_ids: [ada_lantern, logbook]
item_placements:
  ada_lantern: {parent: lamp_room}
  logbook: {parent: lamp_room, text: on the lamp room floor}
entry_text: Ada reaches the lamp room.
---

### Scene 1B.1 — The Lamp

**Details:** a dark room; a cold lamp; a fallen logbook

Ada tends the lamp.
