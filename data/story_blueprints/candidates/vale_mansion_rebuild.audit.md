# Story Blueprint Audit: vale_mansion_rebuild.candidate.json

**Overall:** PASS
**SHA-256:** `7a9f7330207b99ae06df75efca704f21dec2c0081b2bd3a7c0ac8bdbdf01826d`

## Story summary

**Title:** Death in the West Gallery
**Genre/profile:** `mystery` / `mystery`

During a snowbound winter gathering at Vale Mansion, host Emma Vale is found dead in the west gallery. The household must determine which guest had the motive, means, opportunity, and nerve to kill her before the estate can be safely opened again.

### Opening boundary

- **emma_dead** — Emma Vale has been killed in the west gallery.
- **household_snowbound** — A severe winter storm has isolated Vale Mansion and its estate.
- **public_rooms_accessible** — The foyer, study, library, and grounds are accessible to the gathered household.

### Cast

- **emma_vale** — victim and host
- **beatrice_harrow** — estate solicitor and perpetrator
- **thomas_reed** — groundskeeper and alternative suspect
- **clara_vale** — niece and alternative suspect
- **martha_quill** — housekeeper and witness

### Locations and access

- **foyer** (initially accessible) — central public entrance
- **study** (initially accessible) — private office and weapon source
- **library** (initially accessible) — public reading room and records area
- **west_gallery** (initially locked) — crime scene
- **grounds** (initially accessible) — snowbound estate grounds and gate approach
- **east_gate** (initially locked) — estate gate and clock
- **service_corridor** (initially locked) — household passage linking private rooms to the gallery

### Causal timeline

| Event | Window | Location | Outputs |
| --- | --- | --- | --- |
| `winter_gathering` | 21:00–22:49 | `foyer` | household_snowbound, public_rooms_accessible |
| `emma_discovers_diversion` | 22:50–23:10 | `study` | diverted_restoration_payments |
| `beatrice_takes_letter_opener` | 23:20–23:35 | `study` | brass_letter_opener_used |
| `household_suspicions_form` | 23:25–23:34 | `foyer` | groundskeeper_near_gallery, groundskeeper_bootprints, groundskeeper_master_key, clara_debt, clara_argument, clara_missing_minutes |
| `groundskeeper_repairs_clock` | 23:35–23:45 | `east_gate` | groundskeeper_clock_testimony, groundskeeper_prints_old |
| `clara_enters_library` | 23:38–23:39 | `library` | clara_receipt_alibi, clara_witnessed_elsewhere |
| `clara_receipt_written` | 23:40–23:58 | `library` | clara_receipt_alibi |
| `emma_killed` | 23:42–23:50 | `west_gallery` | emma_dead, beatrice_culprit, gallery_access_window, letter_opener_stabbing, death_between_2342_and_2350 |
| `beatrice_hides_body` | 23:50–24:00 | `west_gallery` | gallery_screen_concealment |

### Evidence routes

#### `terminal_proof_route_a` → `terminal_solution`

- **blood_on_letter_opener** (physical_evidence) — `study`, held by `martha_quill`, supports `brass_letter_opener_used`
- **wound_matches_opener** (physical_evidence) — `west_gallery`, held by `martha_quill`, supports `letter_opener_stabbing`
- **gallery_snow_gap** (physical_evidence) — `west_gallery`, held by `thomas_reed`, supports `gallery_access_window`
- **payment_ledger** (document) — `study`, held by `martha_quill`, supports `diverted_restoration_payments`
- **screen_fibers** (physical_evidence) — `west_gallery`, held by `martha_quill`, supports `gallery_screen_concealment`
- **death_window_medical_note** (document) — `library`, held by `martha_quill`, supports `death_between_2342_and_2350`
- Failure-forward alternatives: `terminal_proof_route_b`

#### `terminal_proof_route_b` → `terminal_solution`

- **beatrice_statement** (testimony) — `foyer`, held by `martha_quill`, supports `beatrice_culprit`
- **ledger_signature** (document) — `library`, held by `beatrice_harrow`, supports `diverted_restoration_payments`
- **clock_and_guest_testimony** (testimony) — `foyer`, held by `martha_quill`, supports `death_between_2342_and_2350`
- **beatrice_gallery_testimony** (testimony) — `library`, held by `clara_vale`, supports `gallery_access_window`
- **concealment_account** (testimony) — `west_gallery`, held by `martha_quill`, supports `gallery_screen_concealment`
- Failure-forward alternatives: `terminal_proof_route_a`

#### `tom_false_solution_route` → `tom_hypothesis`

- **tom_muddy_boots** (physical_evidence) — `grounds`, held by `thomas_reed`, supports `groundskeeper_bootprints`
- **tom_gallery_sighting** (testimony) — `foyer`, held by `martha_quill`, supports `groundskeeper_near_gallery`
- **tom_master_key** (physical_evidence) — `grounds`, held by `thomas_reed`, supports `groundskeeper_master_key`
- Failure-forward alternatives: `tom_exoneration_route`

#### `tom_exoneration_route` → `tom_exonerated`

- **tom_clock_log** (document) — `east_gate`, held by `thomas_reed`, supports `groundskeeper_clock_testimony`
- **old_bootprint_layer** (physical_evidence) — `west_gallery`, held by `thomas_reed`, supports `groundskeeper_prints_old`
- Failure-forward alternatives: `terminal_proof_route_a`

#### `clara_false_solution_route` → `clara_hypothesis`

- **clara_debt_letter** (document) — `library`, held by `clara_vale`, supports `clara_debt`
- **clara_argument_testimony** (testimony) — `foyer`, held by `martha_quill`, supports `clara_argument`
- **clara_gallery_gap** (testimony) — `west_gallery`, held by `clara_vale`, supports `clara_missing_minutes`
- Failure-forward alternatives: `clara_exoneration_route`

#### `clara_exoneration_route` → `clara_exonerated`

- **clara_library_receipt** (document) — `library`, held by `clara_vale`, supports `clara_receipt_alibi`
- **clara_library_witness** (testimony) — `library`, held by `martha_quill`, supports `clara_witnessed_elsewhere`
- Failure-forward alternatives: `terminal_proof_route_b`

### Protected knowledge

- `diverted_restoration_payments` releases after `terminal_solution`
- `beatrice_culprit` releases after `terminal_solution`
- `gallery_screen_concealment` releases after `terminal_solution`

### End states

- **truth_revealed_and_estate_cleared**
  - Outcomes: `identify_beatrice`, `establish_motive`, `establish_means`, `establish_opportunity`, `establish_method`, `establish_time`, `establish_concealment`
  - Truths: `beatrice_culprit`, `diverted_restoration_payments`, `brass_letter_opener_used`, `gallery_access_window`, `letter_opener_stabbing`, `death_between_2342_and_2350`, `gallery_screen_concealment`

## Automated checks

| Check | Status | Findings |
| --- | --- | --- |
| `compiler_validation` | **PASS** | — |
| `terminal_roles` | **PASS** | — |
| `knowledge_boundaries` | **PASS** | — |
| `route_diversity` | **PASS** | — |
| `failure_forward` | **PASS** | — |
| `map_and_custody` | **PASS** | — |

## Human review

Use the passing automated checks as evidence, then record the five required editorial decisions:

- `terminal_roles`: Does the ending prove the intended solution or goal?
- `knowledge_boundaries`: Is the opening spoiler-safe?
- `route_diversity`: Are the alternative evidence routes meaningfully different?
- `failure_forward`: Do failed attempts create pressure or another lead?
- `map_and_custody`: Are clues reachable, plausible, and held sensibly?

This report is diagnostic evidence. It is not a reviewed or runtime artifact.
