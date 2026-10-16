# Stage 4 reference resolver measurement

## commands measured

- Total non-rejected commands: **250**.
- `1A`: 24 commands; 0 asked, 6 unique, 18 untouched.
- `1B`: 24 commands; 0 asked, 2 unique, 22 untouched.
- `1C`: 21 commands; 0 asked, 1 unique, 20 untouched.
- `2A`: 26 commands; 0 asked, 0 unique, 26 untouched.
- `2B`: 24 commands; 3 asked, 0 unique, 21 untouched.
- `2C`: 24 commands; 0 asked, 6 unique, 18 untouched.
- `3A`: 30 commands; 0 asked, 14 unique, 16 untouched.
- `3B`: 29 commands; 0 asked, 2 unique, 27 untouched.
- `3C`: 48 commands; 0 asked, 5 unique, 43 untouched.

## asked

- Count: **3** (1.20 per 100 commands).
- [2B, turn 5] `Review the maintenance reports on the next terminal.` — noun `terminal`; options: `archive terminals`, `medical terminal`.
- [2B, turn 5] `Read the maintenance reports on the next terminal.` — noun `terminal`; options: `archive terminals`, `medical terminal`.
- [2B, turn 6] `Access the maintenance reports terminal.` — noun `terminal`; options: `archive terminals`, `medical terminal`.

## unique

- Count: **36** commands (45 resolutions).
### 1A
- [turn 3] `Retrieve my laptop from my truck.` — `laptop` -> `Kristin's laptop` (`kristin_laptop`).
- [turn 3] `Retrieve my laptop from my truck.` — `truck` -> `Kristin's truck` (`kristin_truck`).
- [turn 4] `Insert Michelle's memory card into my laptop.` — `laptop` -> `Kristin's laptop` (`kristin_laptop`).
- [turn 4] `Retrieve my laptop from my truck.` — `laptop` -> `Kristin's laptop` (`kristin_laptop`).
- [turn 4] `Retrieve my laptop from my truck.` — `truck` -> `Kristin's truck` (`kristin_truck`).
- [turn 5] `Insert Michelle's memory card into my laptop.` — `laptop` -> `Kristin's laptop` (`kristin_laptop`).
- [turn 4] `Retrieve my laptop from my truck.` — `laptop` -> `Kristin's laptop` (`kristin_laptop`).
- [turn 4] `Retrieve my laptop from my truck.` — `truck` -> `Kristin's truck` (`kristin_truck`).
- [turn 5] `Insert Michelle's memory card into my laptop.` — `laptop` -> `Kristin's laptop` (`kristin_laptop`).
### 1B
- [turn 1] `Search the bench.` — `bench` -> `park bench` (`park_bench`).
- [turn 8] `Follow Brandon through the narrow tunnel.` — `tunnel` -> `storm drain` (`storm_drain`).
### 1C
- [turn 1] `Search the loading docks for an entrance.` — `entrance` -> `service entrance` (`service_entrance`).
### 2C
- [turn 1] `Copy the encrypted Project Echelon file to my laptop.` — `file` -> `copied JANUS files` (`copied_janus_files`).
- [turn 1] `Copy the JANUS evidence to my laptop.` — `evidence` -> `copied JANUS files` (`copied_janus_files`).
- [turn 7] `Broadcast the JANUS evidence.` — `evidence` -> `copied JANUS files` (`copied_janus_files`).
- [turn 8] `Broadcast the JANUS evidence.` — `evidence` -> `copied JANUS files` (`copied_janus_files`).
- [turn 1] `Download the JANUS evidence.` — `evidence` -> `copied JANUS files` (`copied_janus_files`).
- [turn 8] `Broadcast my JANUS evidence.` — `evidence` -> `copied JANUS files` (`copied_janus_files`).
### 3A
- [turn 6] `Find Michelle among the captives.` — `captives` -> `detention captives` (`captives`).
- [turn 1] `Free the captives.` — `captives` -> `detention captives` (`captives`).
- [turn 3] `Find the senior official among the government prisoners.` — `prisoners` -> `detention captives` (`captives`).
- [turn 4] `Use the official access seal on the gate-status panel.` — `official` -> `Imprisoned senior official` (`senior_official`).
- [turn 4] `Use the official access seal on the gate-status panel.` — `gate` -> `emergency surface gates` (`emergency_surface_gates`).
- [turn 4] `Use the official access seal on the gate-status panel.` — `panel` -> `gate-status panel` (`gate_status_panel`).
- [turn 5] `Enter the expiring one-use code into the gate-status panel.` — `code` -> `emergency override codes` (`override_codes`).
- [turn 5] `Enter the expiring one-use code into the gate-status panel.` — `gate` -> `emergency surface gates` (`emergency_surface_gates`).
- [turn 5] `Enter the expiring one-use code into the gate-status panel.` — `panel` -> `gate-status panel` (`gate_status_panel`).
- [turn 6] `Open the emergency gate.` — `gate` -> `emergency surface gates` (`emergency_surface_gates`).
- [turn 7] `Open the maintenance access panel.` — `panel` -> `gate-status panel` (`gate_status_panel`).
- [turn 9] `Access the emergency gate controls.` — `gate` -> `emergency surface gates` (`emergency_surface_gates`).
- [turn 10] `Open the emergency gate.` — `gate` -> `emergency surface gates` (`emergency_surface_gates`).
- [turn 11] `Lead the captives through the emergency gate.` — `captives` -> `detention captives` (`captives`).
- [turn 11] `Lead the captives through the emergency gate.` — `gate` -> `emergency surface gates` (`emergency_surface_gates`).
- [turn 12] `Guide the captives through the open emergency gate.` — `captives` -> `detention captives` (`captives`).
- [turn 12] `Guide the captives through the open emergency gate.` — `gate` -> `emergency surface gates` (`emergency_surface_gates`).
- [turn 5] `Search the government prisoners.` — `prisoners` -> `detention captives` (`captives`).
- [turn 7] `Use my emergency surface-gate authority.` — `gate` -> `emergency surface gates` (`emergency_surface_gates`).
- [turn 9] `Lead Michelle and the prisoners through the emergency surface gates.` — `prisoners` -> `detention captives` (`captives`).
### 3B
- [turn 7] `Broadcast the evidence through Rebecca's national network controls.` — `evidence` -> `copied JANUS files` (`copied_janus_files`).
- [turn 8] `Broadcast the JANUS evidence.` — `evidence` -> `copied JANUS files` (`copied_janus_files`).
### 3C
- [turn 1] `Complete the evidence broadcast.` — `evidence` -> `copied JANUS files` (`copied_janus_files`).
- [turn 12] `Investigate the second plan in my recovered JANUS file.` — `file` -> `copied JANUS files` (`copied_janus_files`).
- [turn 1] `Transmit the JANUS evidence to outside networks.` — `evidence` -> `copied JANUS files` (`copied_janus_files`).
- [turn 1] `Complete my JANUS evidence broadcast.` — `evidence` -> `copied JANUS files` (`copied_janus_files`).
- [turn 15] `Review the recovered JANUS file.` — `file` -> `copied JANUS files` (`copied_janus_files`).

## evidence would change

- Hypothetical changed-command count: **3**.
- This appends the resolved display name only for measurement; the engine does not do this today.
- [2C, turn 1] `Copy the encrypted Project Echelon file to my laptop.` + `copied JANUS files` (`file`): [] -> ['k_sl_2c_c_r1'].
- [3A, turn 11] `Lead the captives through the emergency gate.` + `emergency surface gates` (`gate`): [] -> ['k_sl_3a_c_r1'].
- [3A, turn 12] `Guide the captives through the open emergency gate.` + `emergency surface gates` (`gate`): [] -> ['k_sl_3a_c_r1'].

## scenes with a collision

- `1A`:
  - `seat`: `driver's seat` (`truck_driver_seat`), `passenger seat` (`truck_passenger_seat`).
  - `seats`: `driver's seat` (`truck_driver_seat`), `passenger seat` (`truck_passenger_seat`).
- `1B`:
  - `seat`: `driver's seat` (`truck_driver_seat`), `passenger seat` (`truck_passenger_seat`).
  - `seats`: `driver's seat` (`truck_driver_seat`), `passenger seat` (`truck_passenger_seat`).
- `1C`:
  - `seat`: `driver's seat` (`truck_driver_seat`), `passenger seat` (`truck_passenger_seat`).
  - `seats`: `driver's seat` (`truck_driver_seat`), `passenger seat` (`truck_passenger_seat`).
- `2A`: none.
- `2B`:
  - `terminal`: `archive terminals` (`archive_terminals`), `medical terminal` (`medical_terminal`).
  - `terminals`: `archive terminals` (`archive_terminals`), `medical terminal` (`medical_terminal`).
- `2C`: none.
- `3A`: none.
- `3B`: none.
- `3C`: none.

## summary

3 of 250 commands asked for clarification (1.20 per 100). The unique-resolution false-resolution risk is limited to the following observable flags: Potential false-resolution flags: 1A turn 4 `Insert Michelle's memory card into my laptop.` resolves `Kristin's laptop` from `laptop` while also naming `Dr. Michelle McGehee`, `Michelle's memory card`; 1C turn 1 `Search the loading docks for an entrance.` resolves `service entrance` from `entrance` while also naming `loading docks`; 3A turn 6 `Find Michelle among the captives.` resolves `detention captives` from `captives` while also naming `Dr. Michelle McGehee`; 3B turn 7 `Broadcast the evidence through Rebecca's national network controls.` resolves `copied JANUS files` from `evidence` while also naming `Rebecca Jenkins`; 1A turn 5 `Insert Michelle's memory card into my laptop.` resolves `Kristin's laptop` from `laptop` while also naming `Dr. Michelle McGehee`, `Michelle's memory card`; 3A turn 3 `Find the senior official among the government prisoners.` resolves `detention captives` from `prisoners` while also naming `Imprisoned senior official`; 1A turn 5 `Insert Michelle's memory card into my laptop.` resolves `Kristin's laptop` from `laptop` while also naming `Dr. Michelle McGehee`, `Michelle's memory card`; 1B turn 8 `Follow Brandon through the narrow tunnel.` resolves `storm drain` from `tunnel` while also naming `the man watching Kristin`; 3A turn 9 `Lead Michelle and the prisoners through the emergency surface gates.` resolves `detention captives` from `prisoners` while also naming `Dr. Michelle McGehee`, `emergency surface gates`. The evidence hypothetical changed 3 commands; The nonzero hypothetical effect makes this worth building and testing as a real feature. It remains hypothetical: the engine does not do this today.
