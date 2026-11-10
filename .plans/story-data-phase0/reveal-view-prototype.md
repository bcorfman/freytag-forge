### Scene 1A / The KMS Mark [SL-1A-E]

- Purpose: Let the KMS mark reward a careful search of Michelle's workstation before the patrol closes in.
- Available: memory_card_recovered is false
- Window: earliest 1, target 3, latest 12
- Completes when: memory_card_recovered is true; abandoned if the scene is left

#### Variant SL-1A-E-R1: Kristin searches beneath the KMS drawer, finds Michelle's hidden memory card, and keeps it with her.
- Commits: memory_card_recovered=true
- Claim k_sl_1a_b_r0: when patrol_in_house is false; establishes all of the route's commits; voiceable=False
  - Statement: Kristin finds Michelle's memory card taped beneath the drawer and pockets it.
  - Earned by: searches the drawer, the gap in the drawer, or the space beneath it (reach: michelle_drawer)
  - Delivery: Kristin's fingers find something taped beneath the drawer. She peels it loose. It is Michelle's memory card, and she pockets it. Her laptop is still out in her truck.

#### Variant SL-1A-E-R2: Kristin finds the hidden card while a patrol officer is in the house, and the officer challenges her.
- Commits: memory_card_recovered=true, card_challenged=true, kristin_marked_by_patrol=true
- Claim k_sl_1a_b_r0w: when patrol_in_house is true; establishes all of the route's commits; voiceable=True
  - Statement: An officer saw Kristin take Michelle's memory card and asked what it is.
  - Earned by: searches the drawer, the gap in the drawer, or the space beneath it (reach: michelle_drawer)
  - Delivery: Kristin's fingers find something taped beneath the drawer. She peels it loose. It is Michelle's memory card, and she pockets it. The officer turns at the sound. "What have you got there?" His hand is already out.

#### Facts and who uses them
- card_challenged: A patrol officer saw Kristin take Michelle's memory card and challenged her.
  - pacing event officer_presses_1a (scene 1A) waits on it
  - tests naming it: 4 files (test_1a_officer_press.py, test_1a_witnessed_recovery.py, test_markdown_story_package.py, test_voiceable_knowledge.py)
- kristin_marked_by_patrol: The patrol has Kristin marked as someone to watch.
  - pacing event pursuit_1b (scene 1B) picks a passage by it
  - tests naming it: 3 files (test_1a_witnessed_recovery.py, test_markdown_story_package.py, test_voiceable_knowledge.py)
- memory_card_recovered: Kristin has recovered Michelle’s memory card.
  - pacing event reyes_rams_drawer_1a (scene 1A) waits on it
  - transition t_1a_1b requires it
  - storylet SL-1A-E activation depends on it
  - storylet SL-1A-F activation depends on it
  - storylet SL-1A-B activation depends on it
  - storylet SL-1A-D activation depends on it
  - claim k_sl_1a_f_r1 requires it
  - claim k_sl_1a_f_r2 requires it
  - claim k_sl_1a_f_r3 requires it
  - claim k_sl_1a_b_r1 requires it
  - claim k_sl_1a_b_r2 requires it
  - claim k_sl_1a_d_r1 requires it
  - tests naming it: 41 files (test_1a_drawer_close_gap.py, test_1a_gap_pointer.py, test_1a_officer_press.py, test_1a_phone_thread.py, test_1a_research_files_eligibility.py, test_1a_spine_prompts.py...)

### Scene 2C / Michelle Changes the Choice [SL-2C-D]

- Purpose: Let Rebecca’s offer, the purge, the physical commitment, and Michelle’s route unfold as one live crisis.
- Available: rebecca_offer_heard is true
- Window: earliest 0, target 13, latest 14
- Completes when: combined_broadcast_rescue_plan_known is true; abandoned if the scene is left

#### Variant SL-2C-D-R1: Rebecca offers Brandon Michelle’s release. Her tablet shows the purge. Brandon says yes and Michelle sends her route.
- Commits: rebecca_offer_active=true, antagonist_split_known=true, purge_clock_started=true, evidence_ready_to_transmit=true, rebecca_office_required_for_broadcast=true, combined_broadcast_rescue_plan_known=true

#### Variant SL-2C-D-R2: The negotiation exposes the split between Rebecca and Charles. Michelle’s route makes the combined mission clear.
- Commits: rebecca_offer_active=true, antagonist_split_known=true, purge_clock_started=true, evidence_ready_to_transmit=true, rebecca_office_required_for_broadcast=true, combined_broadcast_rescue_plan_known=true

#### Variant SL-2C-D-R3: Kristin commits to the uplink after Rebecca’s offer and Michelle’s route reveal. The detention sectors seal.
- Commits: rebecca_offer_active=true, antagonist_split_known=true, committed_to_transmit=true, detention_sectors_sealed=true, purge_clock_started=true, evidence_ready_to_transmit=true, combined_broadcast_rescue_plan_known=true, rebecca_office_required_for_broadcast=true
- Claim k_sl_2c_d_r3: when rebecca_offer_heard is true; establishes all of the route's commits; voiceable=True
  - Statement: Kristin starts the uplink as the detention sectors seal and receives Michelle’s route to the combined plan.
  - Earned by: heads to the uplink and starts sending the copied JANUS files (reach: )
  - Delivery: Kristin heads to the uplink and starts sending the copied files. The detention sectors seal. A maintenance ticket scrolls up the uplink's status panel. Michelle's route leads to Rebecca's secured office. The office can broadcast the evidence and open the detention cells.

#### Variant SL-2C-D-R4: Kristin commits to the transfer carts after Rebecca’s offer and Michelle’s route reveal. The evidence stays unsent.
- Commits: rebecca_offer_active=true, antagonist_split_known=true, committed_to_rescue=true, evidence_not_transmitted=true, purge_clock_started=true, evidence_ready_to_transmit=true, combined_broadcast_rescue_plan_known=true, rebecca_office_required_for_broadcast=true
- Claim k_sl_2c_d_r4: when rebecca_offer_heard is true; establishes all of the route's commits; voiceable=True
  - Statement: Kristin commits to rescue, accepts that the evidence is not transmitted, and receives Michelle’s route to the combined plan.
  - Earned by: heads to the transfer carts and frees a cart of captives (reach: )
  - Delivery: Kristin heads to the transfer carts and frees a cart of captives. The evidence is not transmitted. A maintenance ticket scrolls across the cart's latch display. Michelle's route leads to Rebecca's secured office. The office can broadcast the evidence and open the detention cells.

#### Facts and who uses them
- antagonist_split_known: Kristin has legitimate evidence that Rebecca and Charles are in conflict.
  - tests naming it: 1 files (test_2c_paths_repro.py)
- combined_broadcast_rescue_plan_known: Kristin and Brandon know Michelle’s plan to enter her detention sector through local maintenance access, then combine evidence transmission with opening sealed detention sectors via Rebecca’s office.
  - transition t_2c_3a requires it
  - tests naming it: 3 files (test_2c_paths_repro.py, test_leak_terms.py, test_recovery_after_choice.py)
- committed_to_rescue: Kristin physically committed to freeing captives from the transfer carts.
  - pacing event purge_nudge_2c (scene 2C) waits on it
  - tests naming it: 4 files (test_2c_paths_repro.py, test_act2_probe.py, test_act3a_probe.py, test_recovery_after_choice.py)
- committed_to_transmit: Kristin physically committed to sending the JANUS evidence through the uplink.
  - pacing event purge_nudge_2c (scene 2C) waits on it
  - tests naming it: 3 files (test_2c_paths_repro.py, test_act2_probe.py, test_recovery_after_choice.py)
- detention_sectors_sealed: The detention sectors sealed when Kristin began transmitting the evidence.
  - tests naming it: 2 files (test_2c_paths_repro.py, test_act2_probe.py)
- evidence_not_transmitted: Kristin rescued captives before sending the copied evidence.
  - tests naming it: 2 files (test_2c_paths_repro.py, test_act2_probe.py)
- evidence_ready_to_transmit: The protagonists have enough authenticated evidence to attempt the combined exposure-and-rescue mission.
  - tests naming it: 6 files (test_2c_paths_repro.py, test_established_reveal_match.py, test_evidence_penalty.py, test_leak_terms.py, test_narration_safety.py, test_revealed_knowledge_ids.py)
- purge_clock_started: Charles has ordered valuable captives transferred and the rest destroyed within hours after Michelle corrupts the records.
  - tests naming it: 3 files (test_2c_paths_repro.py, test_2c_turn_one_copy.py, test_narration_safety.py)
- rebecca_offer_active: Rebecca has offered Brandon safety/Michelle’s release in exchange for helping her displace Charles.
  - tests naming it: 1 files (test_2c_paths_repro.py)
- rebecca_office_required_for_broadcast: Rebecca's secured office is the required manual activation point to broadcast the evidence and release the sealed detention sectors.
  - tests naming it: 2 files (test_2c_paths_repro.py, test_leak_terms.py)

#### Incident
- i_2c_rebecca_corridor: outcomes committed_to_transmit (+committed_to_transmit / cost detention_sectors_sealed); committed_to_rescue (+committed_to_rescue / cost evidence_not_transmitted)
- Recovery storylet: SL-2C-E; missed-window event: purge_window_2c; next scene transition: t_2c_3a

