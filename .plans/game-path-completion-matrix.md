# Game-path coverage ledger (step 1)

Generated from baseline `f918c663d67d368645f9a24a47a28ffb29fb77d8`, package files hash `be926170fdc9a87a` (first 16 hex of sha256 over the seven source files).
Generator: `.plans/game-path-completion-matrix-gen.py`. The 'Test files' columns count test files that mention the ID text.
They show where to look, not that a journey covers the row. Journey IDs and live evidence are filled in by later steps.

Classes: **required** = in `required_storylet_ids` (resolution/bridge closure); **alternative** = storylet with more than one realization;
**observer-only** = knowledge audience is not player-visible public. Scene-entry items and fallback text are listed in sections C and D.

## A. Scene timing (accepted scene-local turns)

| Scene | Min | Nudge | Handoff | Pressure events (turn, id, conditions) |
|---|---|---|---|---|
| 1A | 8 | 10 | 13 | 4 pressure_1a; 8 home_search_narrows_1a |
| 1B | 8 | 10 | 13 | 4 pursuit_1b; 8 park_lockdown_1b |
| 1C | 7 | 8 | 11 | 3 security_1c; 7 terminal_sweep_1c |
| 2A | 7 | 8 | 11 | 3 scrutiny_2a if facility_perimeter_reached=true; 7 cover_review_2a if facility_perimeter_reached=true |
| 2B | 8 | 10 | 15 | 8 archive_sweep_2b |
| 2C | 8 | 9 | 16 | 3 purge_2c; 8 transfers_2c |
| 3A | 9 | 10 | 13 | 9 override_deadline_3a; 8 detention_lockdown_3a |
| 3B | 9 | 10 | 14 | 9 destruction_3b if charles_abandoned_rebecca=true; 9 relay_power_3b |
| 3C | 10 | 11 | 14 | 4 collapse_3c; 10 routes_collapse_3c |

## B. Storylets and realizations

| Scene | Storylet | Windows e/t/l | Class | Activation | Realization | Operations | Helps transitions | Knowledge item(s) | Test files |
|---|---|---|---|---|---|---|---|---|---|
| 1A | SL-1A-A The House Does Not Look Abandoned | 0/2/3 | optional | michelle_abduction_suspicion=false | SL-1A-A-R1 | assert michelle_abduction_suspicion | - | k_sl_1a_a_r1 | 14 |
| 1A | SL-1A-E The KMS Mark | 1/3/12 | required | memory_card_recovered=false | SL-1A-E-R1 | assert memory_card_recovered | t_1a_1b | k_sl_1a_b_r0 | 25 |
| 1A | SL-1A-F The Drawer Points to the Gap | 0/3/12 | optional, alternative | memory_card_recovered=false | SL-1A-F-R1 | assert drawer_gap_pointed_out | - | k_sl_1a_f_r1 | 9 |
| 1A | SL-1A-F The Drawer Points to the Gap | 0/3/12 | optional, alternative | memory_card_recovered=false | SL-1A-F-R2 | assert drawer_gap_pointed_out | - | k_sl_1a_f_r2 | 4 |
| 1A | SL-1A-B Michelle Hid Something for Kristin | 2/5/6 | required, alternative | memory_card_recovered=true; continuity_initiative_known=false | SL-1A-B-R1 | assert continuity_initiative_known; assert michelle_abduction_suspicion; assert michelle_warning_known; assert michelle_lead_actionable | t_1a_1b | k_sl_1a_b_r1 | 18 |
| 1A | SL-1A-B Michelle Hid Something for Kristin | 2/5/6 | required, alternative | memory_card_recovered=true; continuity_initiative_known=false | SL-1A-B-R2 | assert michelle_warning_known; assert michelle_abduction_suspicion | - | k_sl_1a_b_r2 | 21 |
| 1A | SL-1A-C The Welfare Check Feels Like a Search | 4/6/7 | optional, alternative | michelle_warning_known=true | SL-1A-C-R1 | assert official_interest_in_michelle_known; assert michelle_abduction_suspicion | - | k_sl_1a_c_r1 | 5 |
| 1A | SL-1A-C The Welfare Check Feels Like a Search | 4/6/7 | optional, alternative | michelle_warning_known=true | SL-1A-C-R2 | assert house_marked_for_return; assert patrol_return_pressure | - | k_sl_1a_c_r2 | 7 |
| 1A | SL-1A-D The Rest of Michelle's Files | 0/8/9 | required | continuity_initiative_known=false; michelle_warning_known=true; memory_card_recovered=true | SL-1A-D-R1 | assert continuity_initiative_known; assert michelle_abduction_suspicion; assert michelle_lead_actionable | t_1a_1b | k_sl_1a_d_r1 | 11 |
| 1B | SL-1B-A The Dead Drop Has More Than One Meaning | 0/2/3 | required, alternative | - | SL-1B-A-R1 | assert transport_route_identified | t_1b_1c | k_sl_1b_a_r1 | 5 |
| 1B | SL-1B-A The Dead Drop Has More Than One Meaning | 0/2/3 | required, alternative | - | SL-1B-A-R2 | assert brandon_face_known | - | k_sl_1b_a_r2 | 4 |
| 1B | SL-1B-B Is Brandon Hunter or Rescuer? | 0/6/7 | required, alternative | - | SL-1B-B-R1 | assert trust_brandon; assert brandon_identified; assert missing_may_be_alive; assert transport_route_identified | t_1b_1c | k_sl_1b_b_r1 | 4 |
| 1B | SL-1B-B Is Brandon Hunter or Rescuer? | 0/6/7 | required, alternative | - | SL-1B-B-R2 | assert brandon_identified; assert missing_may_be_alive | - | k_sl_1b_b_r2 | 1 |
| 1B | SL-1B-C The Gate Code Gives Brandon Away | 0/10/11 | required, alternative | brandon_identified=true; missing_may_be_alive=true | SL-1B-C-R1 | assert brandon_retains_system_access; assert transport_route_identified; assert park_pursuit_resolved | t_1b_1c | k_sl_1b_c_r1 | 3 |
| 1B | SL-1B-C The Gate Code Gives Brandon Away | 0/10/11 | required, alternative | brandon_identified=true; missing_may_be_alive=true | SL-1B-C-R2 | assert brandon_retains_system_access; assert transport_route_identified; assert park_pursuit_resolved | - | k_sl_1b_c_r2 | 1 |
| 1C | SL-1C-A The “Abandoned” Terminal Is Working Too Hard | 0/2/3 | required, alternative | - | SL-1C-A-R1 | assert facility_proof | t_1c_2a | k_sl_1c_a_r1 | 4 |
| 1C | SL-1C-A The “Abandoned” Terminal Is Working Too Hard | 0/2/3 | required, alternative | - | SL-1C-A-R2 | assert facility_proof; assert service_level_access_known | t_1c_2a | k_sl_1c_a_r2 | 2 |
| 1C | SL-1C-B One Face in the Processing Line | 0/5/6 | required, alternative | facility_proof=true | SL-1C-B-R1 | assert captives_confirmed_alive | t_1c_2a | k_sl_1c_b_r1 | 6 |
| 1C | SL-1C-B One Face in the Processing Line | 0/5/6 | required, alternative | facility_proof=true | SL-1C-B-R2 | assert captives_confirmed_alive; assert michelle_possible_sighting | t_1c_2a | k_sl_1c_b_r2 | 2 |
| 1C | SL-1C-C A Regional Hub, Not the Prison | 0/9/10 | required, alternative | facility_proof=true; captives_confirmed_alive=true | SL-1C-C-R1 | assert national_detention_network_known | t_1c_2a | k_sl_1c_c_r1 | 6 |
| 1C | SL-1C-C A Regional Hub, Not the Prison | 0/9/10 | required, alternative | facility_proof=true; captives_confirmed_alive=true | SL-1C-C-R2 | assert architects_strategy_known | t_1c_2a | k_sl_1c_c_r2 | 7 |
| 2A | SL-2A-A Brandon Prepared for This Years Ago | 0/2/3 | optional, alternative | - | SL-2A-A-R1 | assert brandon_prepared_before_event | - | k_sl_2a_a_r1 | 2 |
| 2A | SL-2A-A Brandon Prepared for This Years Ago | 0/2/3 | optional, alternative | - | SL-2A-A-R2 | assert brandon_prepared_before_event | - | k_sl_2a_a_r2 | 1 |
| 2A | SL-2A-B Build the Cover Around a Real Infrastructure Risk | 0/5/6 | required, alternative | facility_infiltration_needed=true | SL-2A-B-R1 | assert false_identities_ready | - | k_sl_2a_b_r1 | 3 |
| 2A | SL-2A-B Build the Cover Around a Real Infrastructure Risk | 0/5/6 | required, alternative | facility_infiltration_needed=true | SL-2A-B-R2 | assert false_identities_ready | - | k_sl_2a_b_r2 | 3 |
| 2A | SL-2A-E Reach the Facility | 0/7/8 | required | false_identities_ready=true | SL-2A-E-R1 | assert facility_perimeter_reached | - | k_sl_2a_e_r1 | 5 |
| 2A | SL-2A-C The Supervisor Needs a Reason | 0/9/10 | required, alternative, observer-only | false_identities_ready=true; facility_perimeter_reached=true | SL-2A-C-R1 | assert restricted_corridor_access; assert rebecca_observing_infiltrators | t_2a_2b | k_sl_2a_c_r1, k_sl_2a_c_r1_rebecca_observes | 6 |
| 2A | SL-2A-C The Supervisor Needs a Reason | 0/9/10 | required, alternative, observer-only | false_identities_ready=true; facility_perimeter_reached=true | SL-2A-C-R2 | assert restricted_corridor_access; assert rebecca_observing_infiltrators | t_2a_2b | k_sl_2a_c_r2, k_sl_2a_c_r2_rebecca_observes | 8 |
| 2B | SL-2B-A JANUS Classified Everyone | 0/2/3 | required, alternative | - | SL-2B-A-R1 | assert janus_known; assert michelle_selected_for_resistance_influence; assert janus_evidence | t_2b_2c | k_sl_2b_a_r1 | 3 |
| 2B | SL-2B-A JANUS Classified Everyone | 0/2/3 | required, alternative | - | SL-2B-A-R2 | assert janus_evidence; assert kristin_deliberately_left_behind | t_2b_2c | k_sl_2b_a_r2 | 3 |
| 2B | SL-2B-B Brandon’s Name Is in the Build Records | 0/6/7 | required, alternative | janus_evidence=true | SL-2B-B-R1 | assert brandon_janus_role_known; assert brandon_claimed_reform_motive | t_2b_2c | k_sl_2b_b_r1 | 5 |
| 2B | SL-2B-B Brandon’s Name Is in the Build Records | 0/6/7 | required, alternative | janus_evidence=true | SL-2B-B-R2 | assert brandon_janus_role_known; assert brandon_claimed_reform_motive | t_2b_2c | k_sl_2b_b_r2 | 2 |
| 2B | SL-2B-B Brandon’s Name Is in the Build Records | 0/6/7 | required, alternative | janus_evidence=true | SL-2B-B-R3 | assert kristin_was_bait | t_2b_2c | k_sl_2b_b_r3 | 4 |
| 2B | SL-2B-C Michelle Is Already Sabotaging the System | 4/7/7 | required, alternative | janus_evidence=true | SL-2B-C-R1 | assert prisoner_records_corrupted; assert michelle_resistance_known | t_2b_2c | k_sl_2b_c_r1 | 3 |
| 2B | SL-2B-C Michelle Is Already Sabotaging the System | 4/7/7 | required, alternative | janus_evidence=true | SL-2B-C-R2 | assert michelle_resistance_known | t_2b_2c | k_sl_2b_c_r2 | 1 |
| 2C | SL-2C-A Rebecca Offers Brandon a Different Conspiracy | 0/2/3 | optional, alternative, observer-only | - | SL-2C-A-R1 | assert rebecca_offer_active | - | k_sl_2c_a_r1 | 5 |
| 2C | SL-2C-A Rebecca Offers Brandon a Different Conspiracy | 0/2/3 | optional, alternative | - | SL-2C-A-R2 | assert rebecca_offer_active; assert antagonist_split_known | - | k_sl_2c_a_r2 | 2 |
| 2C | SL-2C-B The Purge Clock Starts Moving | 0/5/6 | required, alternative | - | SL-2C-B-R1 | assert purge_clock_started | - | k_sl_2c_b_r1 | 3 |
| 2C | SL-2C-B The Purge Clock Starts Moving | 0/5/6 | required, alternative | - | SL-2C-B-R2 | assert purge_clock_started | - | k_sl_2c_b_r2 | 2 |
| 2C | SL-2C-C Evidence or Rescue | 0/10/11 | required, alternative | - | SL-2C-C-R1 | assert evidence_ready_to_transmit | - | k_sl_2c_c_r1 | 12 |
| 2C | SL-2C-C Evidence or Rescue | 0/10/11 | required, alternative | - | SL-2C-C-R2 | assert evidence_ready_to_transmit | - | k_sl_2c_c_r2 | 11 |
| 2C | SL-2C-D Michelle Changes the Choice | 0/13/14 | required, alternative | purge_clock_started=true; evidence_ready_to_transmit=true | SL-2C-D-R1 | assert rebecca_office_required_for_broadcast; assert combined_broadcast_rescue_plan_known | t_2c_3a | k_sl_2c_d_r1 | 7 |
| 2C | SL-2C-D Michelle Changes the Choice | 0/13/14 | required, alternative | purge_clock_started=true; evidence_ready_to_transmit=true | SL-2C-D-R2 | assert rebecca_office_required_for_broadcast; assert combined_broadcast_rescue_plan_known | t_2c_3a | k_sl_2c_d_r2 | 3 |
| 3A | SL-3A-A Michelle Has Turned Sabotage Into an Uprising | 0/2/3 | required, alternative | - | SL-3A-A-R1 | assert michelle_reached; assert uprising_prepared | - | k_sl_3a_a_r1 | 4 |
| 3A | SL-3A-A Michelle Has Turned Sabotage Into an Uprising | 0/2/3 | required, alternative | - | SL-3A-A-R2 | assert michelle_reached; assert uprising_prepared | - | k_sl_3a_a_r2 | 2 |
| 3A | SL-3A-B The “Rescued” Captives Were Being Prepared | 0/6/7 | required, alternative | michelle_reached=true | SL-3A-B-R1 | assert behavioral_experiments_known; assert conditioned_release_plan_known | - | k_sl_3a_b_r1 | 5 |
| 3A | SL-3A-B The “Rescued” Captives Were Being Prepared | 0/6/7 | required, alternative | michelle_reached=true | SL-3A-B-R2 | assert behavioral_experiments_known | - | k_sl_3a_b_r2 | 6 |
| 3A | SL-3A-E The Conditioning Records Confirm the Broadcast Plan | 0/6/7 | optional | michelle_reached=true; behavioral_experiments_known=true; conditioned_release_plan_known=false | SL-3A-E-R1 | assert conditioned_release_plan_known | - | k_sl_3a_e_r1 | 3 |
| 3A | SL-3A-D The Framed Official's Window | 0/8/9 | required, alternative | michelle_reached=true; behavioral_experiments_known=true | SL-3A-D-R1 | assert military_override_codes_available; assert charles_framed_officials_known; assert override_codes_deadline_known | - | k_sl_3a_d_r1 | 5 |
| 3A | SL-3A-D The Framed Official's Window | 0/8/9 | required, alternative | michelle_reached=true; behavioral_experiments_known=true | SL-3A-D-R2 | assert military_override_codes_available; assert charles_framed_officials_known; assert override_codes_deadline_known | - | k_sl_3a_d_r2 | 2 |
| 3A | SL-3A-C The Uprising Begins | 0/10/11 | required, alternative | michelle_reached=true; uprising_prepared=true; military_override_codes_available=true | SL-3A-C-R1 | assert detention_uprising_started | t_3a_3b | k_sl_3a_c_r1 | 5 |
| 3A | SL-3A-C The Uprising Begins | 0/10/11 | required, alternative | michelle_reached=true; uprising_prepared=true; military_override_codes_available=true | SL-3A-C-R2 | assert detention_uprising_started | t_3a_3b | k_sl_3a_c_r2 | 2 |
| 3B | SL-3B-A Give JANUS Too Many Emergencies | 0/3/4 | required, alternative | - | SL-3B-A-R1 | assert human_security_control | - | k_sl_3b_a_r1 | 4 |
| 3B | SL-3B-A Give JANUS Too Many Emergencies | 0/3/4 | required, alternative | - | SL-3B-A-R2 | assert human_security_control | - | k_sl_3b_a_r2 | 1 |
| 3B | SL-3B-E Reach Rebecca’s Office | 0/5/6 | required | human_security_control=true | SL-3B-E-R1 | assert rebecca_office_reached | - | k_sl_3b_e_r1 | 7 |
| 3B | SL-3B-B Rebecca Bargains With the Only Thing She Still Has | 0/7/8 | required, alternative | human_security_control=true; rebecca_office_reached=true | SL-3B-B-R1 | assert rebecca_experiment_approval_confronted; assert detention_locations_offer_known; assert detention_locations_secured | - | k_sl_3b_b_r1 | 4 |
| 3B | SL-3B-B Rebecca Bargains With the Only Thing She Still Has | 0/7/8 | required, alternative | human_security_control=true; rebecca_office_reached=true | SL-3B-B-R2 | assert detention_locations_offer_known; assert detention_locations_secured | - | k_sl_3b_b_r2 | 2 |
| 3B | SL-3B-D Charles Makes the Deluge Real | 0/9/10 | required, alternative | human_security_control=true; detention_locations_secured=true | SL-3B-D-R1 | assert charles_abandoned_rebecca; assert facility_destruction_threat | - | k_sl_3b_d_r1 | 4 |
| 3B | SL-3B-D Charles Makes the Deluge Real | 0/9/10 | required, alternative | human_security_control=true; detention_locations_secured=true | SL-3B-D-R2 | assert charles_abandoned_rebecca; assert facility_destruction_threat | - | k_sl_3b_d_r2 | 1 |
| 3B | SL-3B-C Brandon Holds the Relay Open | 0/11/12 | required, alternative | human_security_control=true; charles_abandoned_rebecca=true; detention_locations_secured=true | SL-3B-C-R1 | assert relay_open; assert brandon_confession_available | t_3b_3c | k_sl_3b_c_r1 | 5 |
| 3B | SL-3B-C Brandon Holds the Relay Open | 0/11/12 | required, alternative | human_security_control=true; charles_abandoned_rebecca=true; detention_locations_secured=true | SL-3B-C-R2 | assert relay_open; assert brandon_confession_available | t_3b_3c | k_sl_3b_c_r2 | 1 |
| 3C | SL-3C-A Charles Tries to Reframe the Broadcast | 0/3/4 | required, alternative | broadcast_started=true | SL-3C-A-R1 | assert national_facility_locations_broadcast; assert truth_no_longer_containable | - | k_sl_3c_a_r1 | 12 |
| 3C | SL-3C-A Charles Tries to Reframe the Broadcast | 0/3/4 | required, alternative | broadcast_started=true | SL-3C-A-R2 | assert truth_no_longer_containable | - | k_sl_3c_a_r2 | 2 |
| 3C | SL-3C-B Rebecca’s Archive Cannot Simply Be Destroyed | 0/7/8 | required, alternative | truth_no_longer_containable=true | SL-3C-B-R1 | assert portable_archive_secured; assert archive_contains_prisoner_locations; assert archive_copies_distributed; assert rebecca_captured | - | k_sl_3c_b_r1 | 11 |
| 3C | SL-3C-B Rebecca’s Archive Cannot Simply Be Destroyed | 0/7/8 | required, alternative | truth_no_longer_containable=true | SL-3C-B-R2 | assert portable_archive_secured; assert archive_copies_distributed; assert archive_contains_prisoner_locations; assert rebecca_captured | - | k_sl_3c_b_r2 | 3 |
| 3C | SL-3C-C Escape While the Facility Comes Apart | 0/11/12 | required | truth_no_longer_containable=true; rebecca_captured=true | SL-3C-C-R1 | assert evacuation_route_open | - | k_sl_3c_c_r1 | 8 |
| 3C | SL-3C-F Open the Surface Gates | 0/11/12 | required | truth_no_longer_containable=true; rebecca_captured=true | SL-3C-F-R1 | assert los_angeles_facility_lost | - | k_sl_3c_c_r2 | 9 |
| 3C | SL-3C-D The Network Fractures | 0/13/13 | required | truth_no_longer_containable=true; captives_reaching_surface=true | SL-3C-D-R1 | assert national_network_fragmenting | - | k_sl_3c_d_r1 | 4 |
| 3C | SL-3C-G Families Begin the Rescue | 0/13/13 | required | truth_no_longer_containable=true; captives_reaching_surface=true | SL-3C-G-R1 | assert community_rescue_efforts_begun | - | k_sl_3c_d_r2 | 5 |
| 3C | SL-3C-E Phase One | 0/14/14 | required, alternative | truth_no_longer_containable=true; captives_reaching_surface=true | SL-3C-E-R1 | assert phase_one_label_known; assert phase_two_conflict_plan_known | - | k_sl_3c_e_r1 | 7 |
| 3C | SL-3C-E Phase One | 0/14/14 | required, alternative | truth_no_longer_containable=true; captives_reaching_surface=true | SL-3C-E-R2 | assert phase_one_label_known; assert phase_two_conflict_plan_known | - | k_sl_3c_e_r2 | 2 |

## C. Knowledge items

| Item | Source | Scenes | Audience | Requires | Establishes | Test files |
|---|---|---|---|---|---|---|
| k_sl_1a_a_r1 | SL-1A-A-R1 | 1A | public | - | assert michelle_abduction_suspicion | 14 |
| k_sl_1a_b_r0 | SL-1A-E-R1 | 1A | public | - | assert memory_card_recovered | 25 |
| k_sl_1a_f_r1 | SL-1A-F-R1 | 1A | public | - | assert drawer_gap_pointed_out | 9 |
| k_sl_1a_f_r2 | SL-1A-F-R2 | 1A | public | - | assert drawer_gap_pointed_out | 4 |
| k_sl_1a_b_r1 | SL-1A-B-R1 | 1A | public | memory_card_recovered=true | assert michelle_warning_known; assert continuity_initiative_known; assert michelle_abduction_suspicion; assert michelle_lead_actionable | 18 |
| k_sl_1a_b_r2 | SL-1A-B-R2 | 1A | public | memory_card_recovered=true | assert michelle_warning_known; assert michelle_abduction_suspicion | 21 |
| k_sl_1a_d_r1 | SL-1A-D-R1 | 1A | public | memory_card_recovered=true | assert continuity_initiative_known; assert michelle_abduction_suspicion; assert michelle_lead_actionable | 11 |
| k_sl_1a_c_r1 | SL-1A-C-R1 | 1A | public | michelle_warning_known=true | assert official_interest_in_michelle_known; assert michelle_abduction_suspicion | 5 |
| k_sl_1a_c_r2 | SL-1A-C-R2 | 1A | public | michelle_warning_known=true | assert house_marked_for_return; assert patrol_return_pressure | 7 |
| k_sl_1b_a_r1 | SL-1B-A-R1 | 1B | public | - | assert transport_route_identified | 5 |
| k_sl_1b_a_r2 | SL-1B-A-R2 | 1B | public | - | assert brandon_face_known | 4 |
| k_sl_1b_b_r1 | SL-1B-B-R1 | 1B | public | - | assert trust_brandon; assert brandon_identified; assert missing_may_be_alive; assert transport_route_identified | 4 |
| k_sl_1b_b_r2 | SL-1B-B-R2 | 1B | public | - | assert brandon_identified; assert missing_may_be_alive | 1 |
| k_sl_1b_c_r1 | SL-1B-C-R1 | 1B | public | brandon_identified=true; missing_may_be_alive=true | assert brandon_retains_system_access; assert transport_route_identified; assert park_pursuit_resolved | 3 |
| k_sl_1b_c_r2 | SL-1B-C-R2 | 1B | public | brandon_identified=true; missing_may_be_alive=true | assert brandon_retains_system_access; assert transport_route_identified; assert park_pursuit_resolved | 1 |
| k_sl_1c_a_r1 | SL-1C-A-R1 | 1C | public | - | assert facility_proof | 4 |
| k_sl_1c_a_r2 | SL-1C-A-R2 | 1C | public | - | assert facility_proof; assert service_level_access_known | 2 |
| k_sl_1c_b_r1 | SL-1C-B-R1 | 1C | public | facility_proof=true | assert captives_confirmed_alive | 6 |
| k_sl_1c_b_r2 | SL-1C-B-R2 | 1C | public | facility_proof=true | assert captives_confirmed_alive; assert michelle_possible_sighting | 2 |
| k_sl_1c_c_r1 | SL-1C-C-R1 | 1C | public | facility_proof=true; captives_confirmed_alive=true | assert national_detention_network_known | 6 |
| k_sl_1c_c_r2 | SL-1C-C-R2 | 1C | public | facility_proof=true; captives_confirmed_alive=true | assert architects_strategy_known | 7 |
| k_sl_2a_a_r1 | SL-2A-A-R1 | 2A | public | - | assert brandon_prepared_before_event | 2 |
| k_sl_2a_a_r2 | SL-2A-A-R2 | 2A | public | - | assert brandon_prepared_before_event | 1 |
| k_sl_2a_b_r1 | SL-2A-B-R1 | 2A | public | facility_infiltration_needed=true | assert false_identities_ready | 3 |
| k_sl_2a_b_r2 | SL-2A-B-R2 | 2A | public | facility_infiltration_needed=true | assert false_identities_ready | 3 |
| k_sl_2a_e_r1 | SL-2A-E-R1 | 2A | public | false_identities_ready=true | assert facility_perimeter_reached | 5 |
| k_sl_2a_c_r1 | SL-2A-C-R1 | 2A | public | false_identities_ready=true; facility_perimeter_reached=true | assert restricted_corridor_access | 6 |
| k_sl_2a_c_r1_rebecca_observes | SL-2A-C-R1 | 2A | world_only (not player-visible) | false_identities_ready=true; facility_perimeter_reached=true | assert rebecca_observing_infiltrators | 0 |
| k_sl_2a_c_r2 | SL-2A-C-R2 | 2A | public | false_identities_ready=true; facility_perimeter_reached=true | assert restricted_corridor_access | 7 |
| k_sl_2a_c_r2_rebecca_observes | SL-2A-C-R2 | 2A | world_only (not player-visible) | false_identities_ready=true; facility_perimeter_reached=true | assert rebecca_observing_infiltrators | 1 |
| k_sl_2b_a_r1 | SL-2B-A-R1 | 2B | public | - | assert janus_known; assert michelle_selected_for_resistance_influence; assert janus_evidence | 3 |
| k_sl_2b_a_r2 | SL-2B-A-R2 | 2B | public | - | assert janus_evidence; assert kristin_deliberately_left_behind | 3 |
| k_sl_2b_b_r1 | SL-2B-B-R1 | 2B | public | janus_evidence=true | assert brandon_janus_role_known; assert brandon_claimed_reform_motive | 5 |
| k_sl_2b_b_r2 | SL-2B-B-R2 | 2B | public | janus_evidence=true | assert brandon_janus_role_known; assert brandon_claimed_reform_motive | 2 |
| k_sl_2b_b_r3 | SL-2B-B-R3 | 2B | public | janus_evidence=true | assert kristin_was_bait | 4 |
| k_sl_2b_c_r1 | SL-2B-C-R1 | 2B | public | janus_evidence=true | assert prisoner_records_corrupted; assert michelle_resistance_known | 3 |
| k_sl_2b_c_r2 | SL-2B-C-R2 | 2B | public | janus_evidence=true | assert michelle_resistance_known | 1 |
| k_sl_2c_a_r1 | SL-2C-A-R1 | 2C | world_only (not player-visible) | - | assert rebecca_offer_active | 5 |
| k_sl_2c_a_r2 | SL-2C-A-R2 | 2C | public | - | assert rebecca_offer_active; assert antagonist_split_known | 2 |
| k_sl_2c_b_r1 | SL-2C-B-R1 | 2C | public | - | assert purge_clock_started | 3 |
| k_sl_2c_b_r2 | SL-2C-B-R2 | 2C | public | - | assert purge_clock_started | 2 |
| k_sl_2c_c_r1 | SL-2C-C-R1 | 2C | public | janus_evidence=true | assert evidence_ready_to_transmit | 12 |
| k_sl_2c_c_r2 | SL-2C-C-R2 | 2C | public | janus_evidence=true | assert evidence_ready_to_transmit | 11 |
| k_sl_2c_d_r1 | SL-2C-D-R1 | 2C | public | purge_clock_started=true; evidence_ready_to_transmit=true | assert rebecca_office_required_for_broadcast; assert combined_broadcast_rescue_plan_known | 7 |
| k_sl_2c_d_r2 | SL-2C-D-R2 | 2C | public | purge_clock_started=true; evidence_ready_to_transmit=true | assert rebecca_office_required_for_broadcast; assert combined_broadcast_rescue_plan_known | 3 |
| k_sl_3a_a_r1 | SL-3A-A-R1 | 3A | public | - | assert michelle_reached; assert uprising_prepared | 4 |
| k_sl_3a_a_r2 | SL-3A-A-R2 | 3A | public | - | assert michelle_reached; assert uprising_prepared | 2 |
| k_sl_3a_b_r1 | SL-3A-B-R1 | 3A | public | michelle_reached=true | assert behavioral_experiments_known; assert conditioned_release_plan_known | 5 |
| k_sl_3a_b_r2 | SL-3A-B-R2 | 3A | public | michelle_reached=true | assert behavioral_experiments_known | 6 |
| k_sl_3a_e_r1 | SL-3A-E-R1 | 3A | public | michelle_reached=true; behavioral_experiments_known=true | assert conditioned_release_plan_known | 3 |
| k_sl_3a_d_r1 | SL-3A-D-R1 | 3A | public | michelle_reached=true; behavioral_experiments_known=true | assert military_override_codes_available; assert charles_framed_officials_known; assert override_codes_deadline_known | 5 |
| k_sl_3a_d_r2 | SL-3A-D-R2 | 3A | public | michelle_reached=true; behavioral_experiments_known=true | assert military_override_codes_available; assert charles_framed_officials_known; assert override_codes_deadline_known | 2 |
| k_sl_3a_c_r1 | SL-3A-C-R1 | 3A | public | michelle_reached=true; uprising_prepared=true; military_override_codes_available=true | assert detention_uprising_started | 5 |
| k_sl_3a_c_r2 | SL-3A-C-R2 | 3A | public | michelle_reached=true; uprising_prepared=true; military_override_codes_available=true; override_codes_deadline_known=true | assert detention_uprising_started | 2 |
| k_sl_3b_a_r1 | SL-3B-A-R1 | 3B | public | - | assert human_security_control | 4 |
| k_sl_3b_a_r2 | SL-3B-A-R2 | 3B | public | - | assert human_security_control | 1 |
| k_sl_3b_e_r1 | SL-3B-E-R1 | 3B | public | human_security_control=true | assert rebecca_office_reached | 7 |
| k_sl_3b_b_r1 | SL-3B-B-R1 | 3B | public | human_security_control=true; rebecca_office_reached=true | assert rebecca_experiment_approval_confronted; assert detention_locations_offer_known; assert detention_locations_secured | 4 |
| k_sl_3b_b_r2 | SL-3B-B-R2 | 3B | public | human_security_control=true; rebecca_office_reached=true | assert detention_locations_offer_known; assert detention_locations_secured | 2 |
| k_sl_3b_d_r1 | SL-3B-D-R1 | 3B | public | human_security_control=true; detention_locations_secured=true | assert charles_abandoned_rebecca; assert facility_destruction_threat | 4 |
| k_sl_3b_d_r2 | SL-3B-D-R2 | 3B | public | human_security_control=true; detention_locations_secured=true | assert charles_abandoned_rebecca; assert facility_destruction_threat | 1 |
| k_sl_3b_c_r1 | SL-3B-C-R1 | 3B | public | human_security_control=true; charles_abandoned_rebecca=true; detention_locations_secured=true | assert relay_open; assert brandon_confession_available | 5 |
| k_sl_3b_c_r2 | SL-3B-C-R2 | 3B | public | human_security_control=true; charles_abandoned_rebecca=true; detention_locations_secured=true | assert relay_open; assert brandon_confession_available | 1 |
| k_sl_3c_a_r1 | SL-3C-A-R1 | 3C | public | broadcast_started=true | assert national_facility_locations_broadcast; assert truth_no_longer_containable | 12 |
| k_sl_3c_a_r2 | SL-3C-A-R2 | 3C | public | broadcast_started=true | assert truth_no_longer_containable | 2 |
| k_sl_3c_b_r1 | SL-3C-B-R1 | 3C | public | truth_no_longer_containable=true | assert portable_archive_secured; assert archive_contains_prisoner_locations; assert archive_copies_distributed; assert rebecca_captured | 11 |
| k_sl_3c_b_r2 | SL-3C-B-R2 | 3C | public | truth_no_longer_containable=true | assert portable_archive_secured; assert archive_copies_distributed; assert archive_contains_prisoner_locations; assert rebecca_captured | 3 |
| k_sl_3c_c_r1 | SL-3C-C-R1 | 3C | public | truth_no_longer_containable=true; rebecca_captured=true | assert evacuation_route_open | 8 |
| k_sl_3c_c_r2 | SL-3C-F-R1 | 3C | public | truth_no_longer_containable=true; rebecca_captured=true | assert los_angeles_facility_lost | 9 |
| k_sl_3c_d_r1 | SL-3C-D-R1 | 3C | public | truth_no_longer_containable=true; captives_reaching_surface=true | assert national_network_fragmenting | 4 |
| k_sl_3c_d_r2 | SL-3C-G-R1 | 3C | public | truth_no_longer_containable=true; captives_reaching_surface=true | assert community_rescue_efforts_begun | 5 |
| k_sl_3c_e_r1 | SL-3C-E-R1 | 3C | public | truth_no_longer_containable=true; captives_reaching_surface=true; national_network_fragmenting=true; charles_at_large=true | assert phase_one_label_known; assert phase_two_conflict_plan_known | 7 |
| k_sl_3c_e_r2 | SL-3C-E-R2 | 3C | public | truth_no_longer_containable=true; captives_reaching_surface=true; national_network_fragmenting=true; charles_at_large=true | assert phase_one_label_known; assert phase_two_conflict_plan_known | 2 |
| k_bridge_1b_departure | bridge_1b_departure | 1B | public | - | assert transport_route_departure_ready | 2 |
| k_bridge_1c_infiltration | bridge_1c_infiltration_needed | 1C | public | - | assert facility_infiltration_needed | 0 |
| k_bridge_2b_archive_crisis | bridge_2b_archive_crisis | 2B | public | - | assert archive_crisis_understood | 0 |
| k_bridge_3a_command_assault | bridge_3a_command_assault | 3A | public | - | assert command_levels_assault_underway | 0 |
| k_bridge_3b_broadcast | bridge_3b_broadcast | 3B | public | - | assert broadcast_started | 0 |
| k_resolution_complete | resolution_complete | 3C | public | - | assert resolution_complete | 0 |
| k_resolution_escape | resolution_escape | 3C | world_only (not player-visible) | - | assert captives_reaching_surface | 0 |
| k_resolution_michelle_publishing | resolution_network_consequences | 3C | public | - | assert michelle_publishing_archive | 0 |
| k_resolution_charles_at_large | resolution_network_consequences | 3C | world_only (not player-visible) | - | assert charles_at_large | 0 |
| k_resolution_kristin_rescue | resolution_network_consequences | 3C | public | - | assert kristin_joined_rescue_efforts | 1 |
| k_scene_1a_entry | scene_entry | 1A | public | - | assert scene_1a_entry_known | 4 |
| k_scene_1b_entry | scene_entry | 1B | public | - | assert scene_1b_entry_known | 1 |
| k_1b_stranger_evasion | scene_entry | 1B | characters (not player-visible) | - | assert scene_1b_entry_known | 0 |
| k_scene_1c_entry | scene_entry | 1C | public | - | assert scene_1c_entry_known | 0 |
| k_scene_2a_entry | scene_entry | 2A | public | - | assert scene_2a_entry_known | 0 |
| k_scene_2b_entry | scene_entry | 2B | public | - | assert scene_2b_entry_known | 1 |
| k_scene_2c_entry | scene_entry | 2C | public | - | assert scene_2c_entry_known | 0 |
| k_scene_3a_entry | scene_entry | 3A | public | - | assert scene_3a_entry_known | 0 |
| k_scene_3b_entry | scene_entry | 3B | public | - | assert scene_3b_entry_known | 0 |
| k_scene_3c_entry | scene_entry | 3C | public | - | assert scene_3c_entry_known | 0 |

## D. Bridge and resolution events

| Kind | Event | Scene | Activation | Operations | Realization storylets | Fallback text | Test files |
|---|---|---|---|---|---|---|---|
| bridge | bridge_1a_actionable_lead | 1A | continuity_initiative_known | assert michelle_lead_actionable | SL-1A-B, SL-1A-D | no | 0 |
| bridge | bridge_1b_departure | 1B | park_pursuit_resolved, transport_route_identified, brandon_identified, missing_may_be_alive | assert transport_route_departure_ready | SL-1B-A, SL-1B-B, SL-1B-C | no | 4 |
| bridge | bridge_1c_infiltration_needed | 1C | facility_proof, captives_confirmed_alive, national_detention_network_known | assert facility_infiltration_needed | SL-1C-A, SL-1C-B, SL-1C-C | no | 3 |
| bridge | bridge_2a_restricted_access | 2A | false_identities_ready, rebecca_observing_infiltrators | assert restricted_corridor_access | SL-2A-C | no | 1 |
| bridge | bridge_2b_archive_crisis | 2B | janus_evidence any_of(brandon_janus_role_known, brandon_claimed_reform_motive, michelle_resistance_known) at_least 2 | assert archive_crisis_understood | SL-2B-A, SL-2B-B, SL-2B-C | no | 2 |
| bridge | bridge_2c_combined_plan | 2C | purge_clock_started, evidence_ready_to_transmit, rebecca_office_required_for_broadcast | assert combined_broadcast_rescue_plan_known | SL-2C-D | no | 1 |
| bridge | bridge_3a_command_assault | 3A | michelle_reached, detention_uprising_started, military_override_codes_available | assert command_levels_assault_underway | SL-3A-A, SL-3A-B, SL-3A-D, SL-3A-C | no | 1 |
| bridge | bridge_3b_broadcast | 3B | relay_open, brandon_confession_available, detention_locations_secured any_of(human_security_control, charles_abandoned_rebecca) at_least 1 | assert broadcast_started | SL-3B-A, SL-3B-B, SL-3B-D, SL-3B-C | no | 0 |
| resolution | resolution_exposure_holds | 3C | broadcast_started, brandon_confession_available, detention_locations_secured | assert truth_no_longer_containable | SL-3C-A | yes | 1 |
| resolution | resolution_archive_and_rebecca | 3C | truth_no_longer_containable | assert portable_archive_secured; assert archive_copies_distributed; assert rebecca_captured | SL-3C-B | yes | 0 |
| resolution | resolution_escape | 3C | truth_no_longer_containable | assert captives_reaching_surface; assert los_angeles_facility_lost | SL-3C-C, SL-3C-F | yes | 0 |
| resolution | resolution_network_consequences | 3C | truth_no_longer_containable, captives_reaching_surface | assert national_network_fragmenting; assert community_rescue_efforts_begun; assert michelle_publishing_archive; assert kristin_joined_rescue_efforts; assert charles_at_large | SL-3C-D, SL-3C-G | yes | 1 |
| resolution | resolution_phase_two | 3C | national_network_fragmenting, charles_at_large | assert phase_one_label_known; assert phase_two_conflict_plan_known | SL-3C-E | yes | 0 |
| resolution | resolution_complete | 3C | truth_no_longer_containable, captives_reaching_surface, archive_copies_distributed, rebecca_captured, national_network_fragmenting, charles_at_large, phase_two_conflict_plan_known | assert resolution_complete | SL-3C-A, SL-3C-B, SL-3C-C, SL-3C-F, SL-3C-D, SL-3C-G, SL-3C-E | yes | 6 |

## E. Transitions and ending

| Transition | From -> to | Priority | Triggers | Required dependencies |
|---|---|---|---|---|
| t_1a_1b | 1A -> 1B | 10 | michelle_lead_actionable=true; patrol_return_pressure=true; memory_card_recovered=true | memory_card |
| t_1b_1c | 1B -> 1C | 10 | transport_route_departure_ready=true | transit_card, brandon |
| t_1c_2a | 1C -> 2A | 10 | facility_infiltration_needed=true | - |
| t_2a_2b | 2A -> 2B | 10 | restricted_corridor_access=true | - |
| t_2b_2c | 2B -> 2C | 10 | archive_crisis_understood=true | brandon |
| t_2c_3a | 2C -> 3A | 10 | combined_broadcast_rescue_plan_known=true | brandon |
| t_3a_3b | 3A -> 3B | 10 | command_levels_assault_underway=true | - |
| t_3b_3c | 3B -> 3C | 10 | broadcast_started=true | - |

Ending: scene 3C, requires phase_two_conflict_plan_known=true. Budget 7200s (authored 120 accepted turns; see plan).

## F. Custody and deliveries (step-2 extension targets)

Rows here are where an acquisition or custody obligation exists: a transition `required_dependencies` item (an availability check, see `ProgressionValidator.transition_dependencies_available`), a delivery cost, or a world `fact_effects` move/reveal.

| Fact / dependency | Where declared | Effect | Staged cue text | Cue guard now applies |
|---|---|---|---|---|
| memory_card | t_1a_1b required_dependencies | entity must not be unavailable (for example destroyed) when the exit fires; not a possession check | - | - |
| transit_card | t_1b_1c required_dependencies | entity must not be unavailable (for example destroyed) when the exit fires; not a possession check | - | - |
| brandon | t_1b_1c required_dependencies | entity must not be unavailable (for example destroyed) when the exit fires; not a possession check | - | - |
| brandon | t_2b_2c required_dependencies | entity must not be unavailable (for example destroyed) when the exit fires; not a possession check | - | - |
| brandon | t_2c_3a required_dependencies | entity must not be unavailable (for example destroyed) when the exit fires; not a possession check | - | - |
| facility_perimeter_reached | world.yaml fact_effects | move kristin -> facility_perimeter | no | - |
| relay_open | world.yaml fact_effects | move brandon -> broadcast_relay | yes | - |
| memory_card_recovered | world.yaml fact_effects | move memory_card -> kristin; reveal memory_card | no | - |
| brandon_identified | world.yaml fact_effects | move=None parent=None text=None under=False reveal=None accompany='brandon' with_='kristin' set_axis=None value=None | yes | - |
| behavioral_experiments_known | world.yaml fact_effects | move detention_medical_records -> medical_level | no | - |
| military_override_codes_available | world.yaml fact_effects | move override_codes -> kristin; reveal override_codes | yes | - |
| rebecca_office_reached | world.yaml fact_effects | move kristin -> executive_office; move brandon -> security_corridors | no | - |
| portable_archive_secured | world.yaml fact_effects | move portable_archive -> kristin | no | - |
| continuity_initiative_known (delivery, 1A) | handoffs.yaml costs | asserts memory_card_recovered | yes | applies to cue |
| captives_confirmed_alive (delivery, 1C) | handoffs.yaml costs | asserts evidence_gap_processing_numbers | yes | applies to cue |
| brandon_janus_role_known (delivery, 2B) | handoffs.yaml costs | asserts evidence_gap_development_record | yes | applies to cue |
| detention_locations_secured (delivery, 3B) | handoffs.yaml costs | asserts evidence_gap_marked_site_list | yes | applies to cue |

## G. Package issues found by the generator

None.

Observation (not a package defect): three deliveries carry an assert-cost that is a penalty (`evidence_gap_*`), not an earlier step.
The cue guard added in step 2 retires a cue when any assert-cost fact is true. Those penalty facts are asserted only by their own delivery's fallback,
which also establishes the delivery fact, so the guard cannot misfire on them today. A future cost that is a penalty set by another path would retire its cue wrongly.

## H. Reachability and journeys (offline, scripted)

`tests/test_game_path_journeys.py` plays one whole-game journey per player-visible realization, withholding its sibling alternatives, and a default journey.
Result at the baseline plus the step-2 cue fix: every player-visible realization is offered on a legal route and reaches the resolution with no deadline backstop event within 120 accepted turns.
Scripted histories prove reachability and downstream state, not free-text usability.

| Id | Realization or branch | Result |
|---|---|---|
| N-1 | SL-1C-C-R2 (architects strategy) | Earned through 1C-C, but the 1C exit is forced: `bridge_1c_infiltration_needed` needs `national_detention_network_known`, which only R1 sets. |
| N-2 | SL-2B-B-R3 (Kristin was bait) | The 2B exit is forced: `bridge_2b_archive_crisis` needs two of three Brandon/Michelle facts and R3 supplies none, leaving at most `michelle_resistance_known`. |
| J-1 | SL-1A-D-R1 (remaining files) | Reachable only after SL-1A-B-R2 (recording first); chained journey passes. The default policy never plays D. |
| O-1 | SL-2C-A-R1 and both SL-2A-C rebecca_observes rows | Observer-only (not player-visible); not journeyed. Withholding the player-visible sibling of an observer row makes a required storylet unfinishable, which is a test artifact. |

Not yet covered: the eight combinations of the three evidence-gap facts, E-R1 versus E-R2 composed text and ending (step 5), the 3C live loop, and live free-text evidence.
N-1 and N-2 are authoring decisions: either the alternative should also establish the bridge fact, or the bridge should accept the alternative. Story meaning changes start in plot.md.
