# Scenes 2C and 3A in the proposed authoring format (hand-written draft, no compiler)

Status (2026-11-15): **revision 2, not yet tried by Brandon** (revision 1 was written 2026-11-14; revision 2 brings it up to the live story, see the box below). This is the second
hand-written slice from [Phase 1 item 10](story-data-redesign-plan.md) (option B,
decided 2026-11-13). Nothing here is read by any code. It extends
[the 1A draft](story-data-1a-draft.md), which defines the format; this file only
describes what the 2C-to-3A slice **added or changed** and then shows the slice.

Source: the nine story files at the snapshot `20892032`. Where I changed nothing
about behavior I say so. Where the format forced a choice it is marked
**CHOICE**; where the data raised a question I did not answer it is marked
**QUESTION**.

**Revision 2 (2026-11-15): the 2C gap is repaired in the live story, and this
draft now shows the repaired state.** Revision 1 deliberately did not repair it
(migration preserves behavior, so the repair was a separate story change). That
change has been made and is in PR #767: 3A has a second entry variant, keyed on
`detention_sectors_sealed`, and 3B has an entry variant keyed on
`evidence_not_transmitted`, so both declared costs of the incident now have a
reader. This draft was updated to match: the second 3A variant, a short 3B
excerpt, the generated view, the task sheet's answers and the notes. Nothing else
in the draft changed since revision 1. The gap itself is no longer in the data, so
it is no longer the thing to find; the edits below test whether the format makes a
consequence easy to follow and a passage easy to change.

What the slice covers, and what it leaves out:

| Covered | Left out (still legacy) |
| --- | --- |
| 2C reveal `michelle_changes_the_choice` (SL-2C-D), the two outcome variants (R3, R4) | 2C reveals C, F, G, H (SL-2C-C, -F, -G, -H) |
| 2C recovery reveal (SL-2C-E) and the missed-window bridge | 3A reveals and beats other than the entry |
| 2C beats (3 pacing events), exit `t_2c_3a` | |
| The incident `i_2c_rebecca_corridor` | |
| 3A header, entry, the two entry variants, placements, entry claim | |
| 3B entry and its two entry variants (excerpt only, added in revision 2) | The rest of 3B |
| Fact declarations and fact deliveries for the facts 2C sets | |
| Root catalog, as short sketches only (last file below) | Full conversion of the catalog (about 110 entities) |

## Correction to the plan's wording

Plan item 10 says "commit-only variants for the two outcomes with no claim". That
is not what the data says. Both incident outcomes (`SL-2C-D-R3`, `-R4`) **have**
claims (`k_sl_2c_d_r3`, `k_sl_2c_d_r4`). The two variants with **no claim** are
`SL-2C-D-R1` and `-R2`; they are not incident outcomes. I read the plan sentence
as a slip and drafted from the data.

**Decision, 2026-11-14 (Brandon): delete `SL-2C-D-R1` and `-R2`.** Git history:
their claims were removed on purpose in commit `16d6094c` (2026-11-01), and the
propagation contract only said they "may be rewritten to the merged route"; no
later commit did that. They do nothing that R3, R4 and the recovery storylet do
not. This draft therefore leaves them out, and it no longer matches the live
package on that point (see "Live package" below). The commit-only variant they
needed (row 1) is withdrawn.

## What this slice needed that the 1A draft did not have

Each row is a proposal for the Phase 1 schema, not something D1 adopted. A row
marked "checked" was verified by the script described in the last section.

| # | Addition | Why the slice needed it | Status |
| --- | --- | --- | --- |
| 1 | ~~**Commit-only variant.**~~ **Withdrawn 2026-11-14.** Only `SL-2C-D-R1` and `-R2` needed it, and they are deleted | | Not needed |
| 2 | **`commits_common`** on a reveal: effects added to every variant's `commits` | The same six commits are repeated in all four legacy D variants (24 operations; with R1 and R2 deleted, 12 operations over R3 and R4; 6 would be written) | Checked: expansion equals legacy sets. **CHOICE**: operation order in the compiled output differs from legacy; I did not check whether order matters |
| 3 | **`outcome`** on a variant: `{id, advantages, costs}`. The `incidents` block then lists variants by key and does not restate facts | Plan item 2: incident costs and advantages derived from the named variant. Legacy `incidents.yaml` restates the fact IDs | Checked: matches legacy. Layer 2 rule needed: every listed fact must be in the variant's commits. I did not check whether the legacy loader already enforces that |
| 4 | **`incidents` block** in the scene file | Five incidents live in `incidents.yaml` today | Checked for this one incident |
| 5 | **`internal_claims`** on a variant: claims with their own audience that no player command earns | `SL-2C-E-R1` carries two claims, one `world_only`, one visible to `charles` only. "One variant = one claim with the reveal's audience" does not fit | **QUESTION** for Brandon: is this the right shape, or should such records not be claims at all? |
| 6 | **Passage list in `text`**, same shape as a beat's `say` | Legacy `delivery_variants` (`requires` plus text) | Checked: both expansions equal legacy `delivery_text` after whitespace is collapsed. First-match semantics not verified in the runtime |
| 7 | **`helps_exit` at reveal level** as a default for variants | Every variant of D lists `t_2c_3a` | Checked |
| 8 | **`delivery`** on a fact declaration | The 48 `handoffs.yaml` records belong to facts. Fields: `source_kind`, `source_entity_id`, `must_convey`, `fallback_text`, `cue_text`, `costs`. `scene_id` is the declaring scene, so it is not written | Checked for the six shown |
| 9 | **`entry_claim`** on a scene; the fact `scene_<id>_entry_known` is generated | Ten entry claims exist | Checked: all nine scene-entry facts have the same purpose text with the scene id substituted. The tenth record (`k_1b_stranger_evasion`) is a different kind and does not fit; not drafted |
| 10 | **`claim` on a `bridge` entry** | Bridge event `bridge_2c_missed_window_recovery` produces claim `k_purge_window_missed` | Checked |
| 11 | **`turns: {min, nudge, handoff}`** in the scene header | Legacy `pacing.yaml` `scenes:` list: `min_turns`, `nudge_after_turns`, `handoff_after_turns` | Checked |
| 12 | **`note`** on a beat, readers only | Legacy `pacing_event_review` holds a `reason` per pacing event, in a third file | Not a behavior field |
| 13 | **`ending`, `connections`, `disclosure_guards`, `protected_knowledge`, entities** in a root `catalog` file | No scene owns them | Sketch only, last file below |

Two things I looked at and **did not** add:

- A claim's `relevance` is passed through unchanged. I checked whether
  `relevance.entity_ids` could default to the claim's `entity_ids`: it equals
  them in 61 of 122 claims and differs in 61, so a default would change data.
- The six facts that D and E both commit are written twice (once as D's
  `commits_common`, once in E's variant). A scene-level named set would remove
  that; not drafted, since the 1A draft has no such construct and one case is
  not enough to design it.

---

## File: `scenes/2C.yaml` (proposed)

```yaml
scene: 2C
title: The Trap Closes
location: purge_chamber
objective: Get free of Rebecca and commit to a move before the purge
freytag_phase: crisis
situation: "A command corridor on the command levels, closed at both ends by guards. Transfer orders for the captives are moving, and a maintenance network runs through the walls. Security activity is rising faster than Kristin can explain."
pressure: Decide what to do before the purge begins
turns: {min: 8, nudge: 9, handoff: 16}
companions: [brandon]

entry: >-
  Guards closed the command corridor at both ends. Then a woman in an
  executive's suit walked between them, unhurried, a tablet under her arm. She
  looked at Brandon first. "I wondered when you'd come back," said Rebecca
  Jenkins. "Charles means to kill everyone below us, my people too. Help me
  remove him, Brandon, and I will give you Michelle." Kristin still carried the
  copied JANUS files.

entry_claim:
  id: k_scene_2c_entry
  says: Kristin fears a possible purge. She must choose her next move.
  entities: [kristin, purge_chamber]
  aliases: [purge]
  # the fact scene_2c_entry_known is generated, not declared

# ---------------------------------------------------------------- facts
# Declared here because every producer of these facts is in 2C (checked against
# the loaded package). Facts 2C only reads (ticket_header_matched, held_transfers_seen,
# brandon_name_kept, brandon_name_erased) belong to the scene that first sets them.
facts:
  rebecca_offer_heard:
    purpose: Kristin has answered Rebecca's offer and learned the purge order and Brandon's answer.
  rebecca_offer_active:
    purpose: Rebecca has offered Brandon safety/Michelle’s release in exchange for helping her displace Charles.
  antagonist_split_known:
    purpose: Kristin has legitimate evidence that Rebecca and Charles are in conflict.
  purge_clock_started:
    purpose: Charles has ordered valuable captives transferred and the rest destroyed within hours after Michelle corrupts the records.
    delivery:
      source_kind: message
      source_entity_id: rebecca
      must_convey:
        - [Charles's purge order, purge order, command order]
        - [purge begins within hours, purge deadline, hours remain before the purge]
      fallback_text: >-
        Rebecca's tablet shows Charles's purge order. The purge begins within hours.
  evidence_ready_to_transmit:
    purpose: The protagonists have enough authenticated evidence to attempt the combined exposure-and-rescue mission.
  rebecca_office_required_for_broadcast:
    purpose: Rebecca's secured office is the required manual activation point to broadcast the evidence and release the sealed detention sectors.
  combined_broadcast_rescue_plan_known:
    purpose: Kristin and Brandon know Michelle’s plan to enter her detention sector through local maintenance access, then combine evidence transmission with opening sealed detention sectors via Rebecca’s office.
    delivery:
      source_kind: message
      source_entity_id: michelle
      must_convey:
        - [broadcast the evidence, transmit the evidence]
        - [open the detention cells, rescue the captives]
        - [Rebecca's office, Rebecca's secured office]
      fallback_text: >-
        Michelle says that Rebecca's office can broadcast the evidence. It can
        also open the detention cells.
  committed_to_transmit:
    purpose: Kristin physically committed to sending the JANUS evidence through the uplink.
    delivery:
      source_kind: observation
      source_entity_id: kristin
      must_convey:
        - [heads to the uplink, goes to the uplink, starts sending]
        - [copied files, evidence]
      fallback_text: Kristin heads to the uplink and starts sending the copied files.
  detention_sectors_sealed:
    purpose: The detention sectors sealed when Kristin began transmitting the evidence.
    delivery:
      source_kind: observation
      source_entity_id: kristin
      must_convey:
        - [detention sectors seal, detention sectors sealed, sectors lock]
        - [transmission starts, transmission begins, sending starts]
      fallback_text: The detention sectors seal as transmission starts from the uplink.
  committed_to_rescue:
    purpose: Kristin physically committed to freeing captives from the transfer carts.
    delivery:
      source_kind: observation
      source_entity_id: kristin
      must_convey:
        - [heads to the transfer carts, goes to the transfer carts, rescue]
        - [frees a cart of captives, frees captives, captives get out]
      fallback_text: Kristin heads to the transfer carts and frees a cart of captives.
  evidence_not_transmitted:
    purpose: Kristin rescued captives before sending the copied evidence.
    delivery:
      source_kind: observation
      source_entity_id: kristin
      must_convey:
        - [evidence not transmitted, nothing has been sent, no evidence sent]
        - [evidence in Kristin's hands, copied files remain with Kristin]
      fallback_text: >-
        Evidence not transmitted. The evidence in Kristin's hands remains with
        her. Kristin keeps the copied files with her.
  purge_window_missed:
    purpose: The purge alarm forced the group out before Kristin made a commitment.
  purge_alarm_active:
    purpose: The purge alarm is active while Michelle's neutral route remains open.
  purge_recovery_ready:
    purpose: The purge alarm has lasted long enough for the neutral route recovery to move the group onward.
  # Also declared in 2C, not drafted: corridor_watch_lifted, held_carts_known,
  # uplink_eye_seen (reveals F, G, H). Deliveries for the other 2C facts are
  # unchanged and omitted: 6 more (purge_window_missed, evidence_ready_to_transmit,
  # rebecca_office_required_for_broadcast, and others).

# ---------------------------------------------------------------- setup
placements:
  copied_janus_files: {parent: kristin}
  broadcast_uplink: {parent: purge_chamber, text: at the end of the command corridor}
  transfer_carts: {parent: purge_chamber, text: at the other end of the command corridor}
  corridor_camera: {parent: purge_chamber, text: "over the guards at the near end of the command corridor, its lens held on Brandon"}
  monitor_light: {parent: purge_chamber, text: burning steady amber beside the one outbound channel on the broadcast uplink}
  cart_tags: {parent: purge_chamber, text: on the rails of the transfer carts}
  rebecca: {parent: purge_chamber, text: standing between her guards in the command corridor}
  corridor_guards: {parent: purge_chamber, text: holding both ends of the command corridor}

# ---------------------------------------------------------------- beats
beats:
  - id: purge_window_2c
    at_turn: 5
    sets: {purge_window_missed: true}
    note: Lets the purge alarm force the group out while Michelle's neutral route arrives.
    say: The purge alarm forces Kristin and Brandon out. A maintenance ticket scrolls across the nearest wall panel and opens a way forward.

  - id: purge_nudge_2c
    at_turn: 6
    when: {purge_window_missed: true, committed_to_transmit: false, committed_to_rescue: false}
    sets: {purge_alarm_active: true}
    note: Keeps a missed purge moving toward Michelle's route without asserting a commitment.
    say: The purge alarm is active. A maintenance channel is open. Kristin must follow it without making a commitment here.

  - id: purge_recovery_2c
    at_turn: 6
    when: {purge_window_missed: true, purge_alarm_active: true}
    sets: {purge_recovery_ready: true}
    # no say: this event is silent in the legacy file too

# ---------------------------------------------------------------- reveals
# Reveal C (rebecca_hears_her_answer, SL-2C-C) is not drafted. It sets
# rebecca_offer_heard, which D's available_while reads.

reveals:

  - id: michelle_changes_the_choice          # [SL-2C-D]
    title: Michelle Changes the Choice
    guidance:
      pressure_role: Let Rebecca’s offer, the purge, the physical commitment, and Michelle’s route unfold as one live crisis.
      window: {earliest_turn: 0, target_turn: 13, latest_turn: 14}
      available_while: {rebecca_offer_heard: true}
      done_when: {combined_broadcast_rescue_plan_known: true}
      boundaries: [janus_phase_two]
    audience: public
    helps_exit: [t_2c_3a]                    # default for every variant
    commits_common:                          # added to every variant's commits
      rebecca_offer_active: true
      antagonist_split_known: true
      purge_clock_started: true
      evidence_ready_to_transmit: true
      rebecca_office_required_for_broadcast: true
      combined_broadcast_rescue_plan_known: true
    parts:
      route_close: >-
        Michelle's route leads to Rebecca's secured office. The office can
        broadcast the evidence and open the detention cells.
      sending: >-
        Kristin heads to the uplink and starts sending the copied files. The
        detention sectors seal.
      freeing: >-
        Kristin heads to the transfer carts and frees a cart of captives. The
        evidence is not transmitted.

    variants:
      transmit:                              # [SL-2C-D-R3, claim k_sl_2c_d_r3]
        claim_id: k_sl_2c_d_r3
        when: {rebecca_offer_heard: true}
        intent: Kristin commits to the uplink after Rebecca’s offer and Michelle’s route reveal. The detention sectors seal.
        commits: {committed_to_transmit: true, detention_sectors_sealed: true}
        outcome:
          id: committed_to_transmit
          advantages: [committed_to_transmit]
          costs: [detention_sectors_sealed]
        aliases: [committed to transmit, detention sectors sealed, combined broadcast rescue plan known]
        says: Kristin starts the uplink as the detention sectors seal and receives Michelle’s route to the combined plan.
        earn_when: heads to the uplink and starts sending the copied JANUS files
        action_evidence:
          - [head, go, move, start, begin, send, transmit, upload]
          - [uplink, broadcast uplink, copied files, JANUS files, JANUS evidence, evidence]
        entities: [kristin, brandon, michelle, rebecca, purge_chamber, copied_janus_files]
        relevance: {entity_ids: [kristin, brandon, michelle, rebecca, purge_chamber, copied_janus_files], priority: 10}
        must_convey:
          - [starts sending the evidence, transmit the evidence, uplink]
          - [detention sectors seal, detention sectors sealed]
          - [Michelle's route, maintenance route, route to Michelle]
          - [Rebecca's secured office, Rebecca's office]
          - [broadcast the evidence, open the detention cells, combined plan]
        text:
          - when: {ticket_header_matched: true}
            text: >-
              {sending} A maintenance ticket scrolls up the uplink's status panel
              with the archive header and the code sensor fault. {route_close}
          - text: >-
              {sending} A maintenance ticket scrolls up the uplink's status panel.
              {route_close}

      rescue:                                # [SL-2C-D-R4, claim k_sl_2c_d_r4]
        claim_id: k_sl_2c_d_r4
        when: {rebecca_offer_heard: true}
        intent: Kristin commits to the transfer carts after Rebecca’s offer and Michelle’s route reveal. The evidence stays unsent.
        commits: {committed_to_rescue: true, evidence_not_transmitted: true}
        outcome:
          id: committed_to_rescue
          advantages: [committed_to_rescue]
          costs: [evidence_not_transmitted]
        aliases: [committed to rescue, evidence not transmitted, combined broadcast rescue plan known]
        says: Kristin commits to rescue, accepts that the evidence is not transmitted, and receives Michelle’s route to the combined plan.
        earn_when: heads to the transfer carts and frees a cart of captives
        action_evidence:
          - [head, go, move, reach, free, release, open]
          - [transfer carts, rescue cart, cart of captives, frees a cart of captives, free a cart of captives, prisoners, rescue]
        entities: [kristin, brandon, michelle, rebecca, purge_chamber, copied_janus_files]
        relevance: {entity_ids: [kristin, brandon, michelle, rebecca, purge_chamber, copied_janus_files], priority: 10}
        must_convey:
          - [rescue cart, frees a cart of captives, rescue]
          - [evidence is not transmitted, evidence remains in Kristin's hands]
          - [Michelle's route, maintenance route, route to Michelle]
          - [Rebecca's secured office, Rebecca's office]
          - [broadcast the evidence, open the detention cells, combined plan]
        text:
          - when: {ticket_header_matched: true}
            text: >-
              {freeing} A maintenance ticket scrolls across the cart's latch
              display with the archive header and the code sensor fault.
              {route_close}
          - text: >-
              {freeing} A maintenance ticket scrolls across the cart's latch
              display. {route_close}

  - id: michelles_route_arrives              # [SL-2C-E] the missed-window recovery
    title: Michelle’s Route Arrives
    guidance:
      pressure_role: Let the missed purge window force the group onto Michelle’s route without deciding Kristin’s commitment.
      window: {earliest_turn: 5, target_turn: 6, latest_turn: 10}
      available_while: {purge_window_missed: true}
      done_when: {combined_broadcast_rescue_plan_known: true}
      boundaries: [janus_phase_two]
    helps_exit: [t_2c_3a]
    # no reveal-level audience: this reveal makes no player-visible claim
    variants:
      forced_route:                          # [SL-2C-E-R1]
        intent: The purge alarm forces the group out of the corridor before Kristin commits. Michelle’s route identifies Rebecca’s office and widens the options without crediting a commitment.
        commits:
          rebecca_offer_active: true
          antagonist_split_known: true
          purge_clock_started: true
          evidence_ready_to_transmit: true
          rebecca_office_required_for_broadcast: true
          combined_broadcast_rescue_plan_known: true
          purge_alarm_active: true
          purge_recovery_ready: true
        internal_claims:
          - id: k_purge_recovery_ready
            says: The purge alarm is ready for the neutral route recovery.
            aliases: [purge recovery ready]
            audience: {kind: world_only, player_visible: false}
            leak_terms: []
            commits_subset: {purge_recovery_ready: true}
          - id: k_sl_2c_e_route_effects
            says: The missed-window purge recovery carries its route effects.
            aliases: [purge recovery route effects]
            audience: {kind: characters, character_ids: [charles], player_visible: false}
            must_convey: [[purge recovery, route effects]]
            commits_subset:
              rebecca_offer_active: true
              antagonist_split_known: true
              purge_clock_started: true
              evidence_ready_to_transmit: true
              rebecca_office_required_for_broadcast: true
              combined_broadcast_rescue_plan_known: true
              purge_alarm_active: true

# ---------------------------------------------------------------- incident
incidents:
  - id: i_2c_rebecca_corridor
    reveal: michelle_changes_the_choice
    outcomes: [transmit, rescue]             # variant keys. What each gains and costs is written on the variant (outcome:)
    recovery: michelles_route_arrives
    missed_window: purge_window_2c
    successor: t_2c_3a
    observed_by: [rebecca_hears_her_answer]  # reveal C; the outcome variants' own claims are added by the compiler
    completes_scene: true

# ---------------------------------------------------------------- bridge
bridge:
  - id: bridge_2c_combined_plan
    when: {purge_clock_started: true, evidence_ready_to_transmit: true, rebecca_office_required_for_broadcast: true}
    commits: {combined_broadcast_rescue_plan_known: true}
    realized_by: [michelle_changes_the_choice, michelles_route_arrives]
    note: After the purge crisis is active, Michelle’s canonical coded message must eventually make the combined rescue/broadcast mission known; the player may react freely.   # legacy key fallback_realization, which no code reads

  - id: bridge_2c_missed_window_recovery
    when: {purge_window_missed: true, purge_recovery_ready: true}
    commits:
      purge_window_missed: true
      rebecca_offer_active: true
      antagonist_split_known: true
      purge_clock_started: true
      evidence_ready_to_transmit: true
      rebecca_office_required_for_broadcast: true
      combined_broadcast_rescue_plan_known: true
      purge_alarm_active: true
    realized_by: [michelles_route_arrives]
    note: The purge forces the group onto a neutral maintenance route toward Rebecca’s office.   # legacy key fallback_realization, which no code reads
    claim:
      id: k_purge_window_missed
      says: The purge window closed before Kristin resolved the command-corridor incident.
      aliases: [purge window missed, purge alarm]
      audience: public
      leak_terms: []
      commits_subset: {purge_window_missed: true}

# ---------------------------------------------------------------- exit
exit:
  - id: t_2c_3a
    to: 3A
    priority: 10
    when_all: [combined_broadcast_rescue_plan_known]
    needs:
      - {item: brandon, relation: exists}    # legacy required_dependencies: [brandon]. Not "held": migration keeps behavior
    bridge: >-
      The purge clock was running. Michelle's route led down into the detention
      levels, and the plan was now one combined mission: broadcast the truth and
      free the captives.
```

## File: `scenes/3A.yaml` (proposed, entry only)

```yaml
scene: 3A
title: Reaching Michelle
location: detention_level
objective: Join the uprising
freytag_phase: crisis
situation: "The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives."
pressure: Join the uprising
turns: {min: 9, nudge: 10, handoff: 13}
companions: [brandon]

entry: >-
  A partly unsecured detention sector opened onto rows of captives. Secret
  messages crackled through stolen radios, and the prisoners moved with a
  discipline no captor had taught them - someone inside had been organizing this
  long before rescue arrived.
entry_variants:
  - when: {committed_to_rescue: true}        # fact declared in 2C, used here by ID
    text: >-
      The captives Kristin had freed from the transfer carts were already on this
      level. They stood among the organized rows as if they had always belonged
      there.
  - when: {detention_sectors_sealed: true}   # revision 2: the transmit branch's declared cost, read here
    text: >-
      The upload was still running. The other detention sectors had sealed the
      moment it started, and this was the one sector still open.

entry_claim:
  id: k_scene_3a_entry
  says: Supporting the uprising is the immediate priority.
  entities: [kristin, michelle, detention_level]
  aliases: [Michelle, uprising]

placements:
  copied_janus_files: {parent: kristin}
  override_codes: {parent: senior_official}
  stolen_radio: {parent: detention_level, text: "tuned to the facility's own message, played on repeat"}
  gate_status_panel: {parent: detention_level}
  emergency_surface_gates: {parent: facility_escape}
  wrist_tags: {parent: detention_level, text: "on the wrists of the captives, each stamped with the same transfer date, a week old"}
  checkpoint_reader: {parent: detention_level, text: beside the checkpoint door at the top of the block}
  captives: {parent: detention_level}
  senior_official: {parent: captives}
  michelle: {parent: detention_level, text: beside the captives}

# Not drafted: 3A's facts (michelle_reached, uprising_prepared, detention_uprising_started, ...),
# beats (override_deadline_3a, detention_lockdown_3a), reveals SL-3A-A to -I, and the exit t_3a_3b.
```

Entry variants are **appended** to the base `entry` text, in order, when their
`when` holds; they do not replace it (`scene_entry_texts`, `models.py:647`). So
after the transmit branch the player reads the base paragraph and then the
sealed-sectors paragraph. The base line says "a partly unsecured detention
sector", which stays true in both branches: it is one sector, reached by
Michelle's route, while the others are sealed. The loader also rejects entry text
that names a term the player has not earned, so neither variant can say "Michelle's
route" or "maintenance route"; the format has to keep that check.

## File: `scenes/3B.yaml` (excerpt, entry only; added in revision 2)

```yaml
scene: 3B
title: The Battle for the Broadcast
location: broadcast_relay

entry: >-
  Alarms layered over alarms as the facility fought to predict its attackers.
  Water-pressure warnings flashed on the inspection console while doors opened and
  closed in empty service corridors that JANUS watched move by move.
entry_variants:
  - when: {brandon_name_erased: true}        # fact declared in 2B
    text: >-
      Brandon had deleted his name from the build record in the archive. Now only
      his own word could show what he had built, and he knew it.
  - when: {evidence_not_transmitted: true}   # revision 2: the rescue branch's declared cost, declared in 2C, read here
    text: >-
      The evidence had never been sent. It was still with Kristin, and the
      broadcast was the first chance to get it out.

# Not drafted: everything else in 3B.
```

## File: `catalog.yaml` (root; sketches only)

Not a conversion. It shows where the things no scene owns would sit and what an
entry looks like. Counts are from the loaded package: 25 places, 9 characters,
2 groups, 72 items, 2 connections, 3 protected-knowledge names, 1 disclosure
guard. None of these has a "setter" fact, so they do not follow the shared-facts
rule (option A); they have one home each, here.

```yaml
story: continuity_initiative
protagonist: kristin

places:
  purge_chamber: {name: command levels, aliases: [command level, upper command corridors], parent: regional_facility}
  maintenance_network: {name: maintenance network, aliases: [maintenance route, maintenance routes, maintenance tunnel, maintenance tunnels], parent: purge_chamber}
  detention_level: {name: detention level, parent: regional_facility}
  # ... 22 more

characters:
  rebecca:
    name: Rebecca Jenkins
    aliases: [Rebecca]
    narrator_bio: Charles's 56-year-old wife and the chief executive of a biotechnology and defense contractor. She is exacting and technically capable.
  # ... 8 more

groups:
  captives: {name: detention captives, scoped_aliases: [prisoners, prisoner, captives, captive]}
  corridor_guards: {name: corridor guards, scoped_aliases: [guards, guard]}

items:
  copied_janus_files: {name: copied JANUS files, disclosure: public, owner: kristin, scoped_aliases: [copied files, JANUS files, JANUS evidence]}
  corridor_camera: {name: corridor camera, scoped_aliases: [camera], fixed: true, kind: thing}
  cart_tags: {name: cart tags, scoped_aliases: [tags, tag, cart tag], fixed: true, kind: thing}
  # ... 69 more

connections:
  house_to_outside: {from: mcgehee_home, to: outside_house, arrival: "Kristin steps outside. Her truck is parked at the curb."}
  outside_to_house: {from: outside_house, to: mcgehee_home, arrival: "Kristin goes back inside through the forced back door."}

protected_knowledge: [janus_selection_system, brandon_history, janus_phase_two]

disclosure_guards:
  memory_card_word_guard: {terms: [card], unlock_fact: memory_card_recovered}

ending:                                      # legacy pacing.yaml; its scene is 3C. CHOICE: root or 3C's file? Left open
  scene: 3C
  when: {evacuation_complete: true}
  text: >-
    Dawn finds Michelle alive and Kristin reunited with her. The captives are
    out. Brandon was last seen holding the relay, and no one knows what happened
    to him. Charles is still out there. Their old lives are gone.
  variants:
    - {when: {barrier_held: true}, text: "The lower levels stand, and every cart came through."}
    - {when: {lower_levels_lost: true}, text: The lower levels went under. Everyone who reached the surface lived.}
    # ... 5 more
  marker: The story ends here.
```

---

## What the compiler would generate (never edited)

**How this block was made:** by running `scripts/branch_report.py
i_2c_rebecca_corridor` and the producer/consumer lookups
(`storygame/story_package/dependencies.py`) on the loaded package (first at the
snapshot, regenerated for revision 2 on the live package), then reformatting. It is the legacy graph shown in the new
vocabulary, not the output of a compiler for this format. The Phase 2 parity
gate would compare a real one with it.

```text
detention_sectors_sealed
  declared in: 2C
  set by:   reveals.michelle_changes_the_choice.transmit
  read by:  3A entry_variants[1] (adds the sealed-sectors paragraph)
  declared cost of: incident i_2c_rebecca_corridor, outcome committed_to_transmit
  RESULT:   none; the declared cost has a reader

evidence_not_transmitted
  declared in: 2C
  set by:   reveals.michelle_changes_the_choice.rescue
  read by:  3B entry_variants[1] (adds the evidence-not-sent paragraph)
  declared cost of: incident i_2c_rebecca_corridor, outcome committed_to_rescue
  RESULT:   none; the declared cost has a reader

committed_to_transmit
  declared in: 2C
  set by:   reveals.michelle_changes_the_choice.transmit
  read by:  beats.purge_nudge_2c (when, must be false)
  read in 3A: nothing (3A reads the cost fact, not this one)

committed_to_rescue
  declared in: 2C
  set by:   reveals.michelle_changes_the_choice.rescue
  read by:  beats.purge_nudge_2c (when, must be false)
  read in 3A: entry_variants[0] (adds the freed-captives paragraph)

combined_broadcast_rescue_plan_known
  declared in: 2C
  set by:   reveals.michelle_changes_the_choice (both variants),
            reveals.michelles_route_arrives.forced_route,
            bridge.bridge_2c_combined_plan, bridge.bridge_2c_missed_window_recovery
  read by:  exit.t_2c_3a (trigger), reveals.*.done_when
```

The branch report for the same incident (run on the live package, 2026-11-15)
now says that the transmit branch leaves a trace in 3A through the sealed-sectors
paragraph, that the rescue branch leaves one in 3A (the freed captives) and one in
3B (the evidence not sent), and that the recovery and missed-window ways out
leave 3A at its base text. The report quotes the branch text beside the next
scene's text for a reader to judge; the tool does not decide.

---

## Two edits to try (task sheet)

Same rules as the 1A task sheet: use only this file; write down where you looked
first, what you typed, and where you were unsure; if the schema does not tell you
what to do, that is the finding. Do not repair the 2C gap in either edit.

### Edit 1. Reword a passage shared by both outcomes

**Change:** Rebecca's office should be "the secured office on the command
level", not "Rebecca's secured office", in what the player is told after the
commitment.

**Done when:** every passage in the 2C file that describes the office to the
player says so, and you can say which `must_convey` lists still hold.

**Watch for:** which passages the shared sentence reaches; the `must_convey`
words (`Rebecca's secured office`, `Rebecca's office`); `says` and `aliases`;
whether the edit also needs to touch E, the bridge fallback text or the delivery
`must_convey`.

**Legacy:** the sentence is a separate string in the `delivery_text` and in the
one `delivery_variant` of each of `k_sl_2c_d_r3` and `k_sl_2c_d_r4` (four
copies). The fact delivery for `rebecca_office_required_for_broadcast` has a
similar but different sentence ("The office contains the manual command
controls"). I did not count which tests contain the sentence.

**Check yourself:** the shared sentence is one part, `route_close`; the four
passages pick it up from there. The `must_convey` lists in both outcome variants
still name "Rebecca's secured office", which a reworded passage no longer
contains, so they must change too, and nothing in the format tells you that. That
is the honest result to record. The bridge fallback text and the fact's delivery
are separate sentences and do not change unless you change them.

### Edit 2. Follow one consequence out of 2C and into 3A and 3B (read-only)

**Change:** none. Start at `detention_sectors_sealed` and answer, using only this
file: where is it set; what reads it in 2C; what reads it in 3A; what does the
player see in 3A because of it; and what is the declared cost of the transmit
outcome. Then do the same for `evidence_not_transmitted` (3B), and say which of the
two scenes a player who rescued would see a difference in.

**Done when:** you have written the answers for both facts.

**Where to look:** the `outcome` fields of the two outcome variants, the 3A
`entry_variants`, the 3B excerpt, and the generated block at the end.

**Legacy:** the two facts appear in `world.yaml`, `knowledge.yaml` (purpose and
claim), `handoffs.yaml` (delivery), `storylet-routes.yaml` (definition and
operations) and `incidents.yaml`. As of revision 2 they are also read in
`plot.md`: `detention_sectors_sealed` in a 3A `entry_variants` entry and
`evidence_not_transmitted` in a 3B one; `committed_to_rescue` is read by the other
3A entry variant and in `pacing.yaml` (the nudge event).

**Check yourself:** `detention_sectors_sealed` is set by the transmit variant, read
by 3A `entry_variants[1]`, and the player sees the sealed-sectors paragraph; its
declared cost has an effect. `evidence_not_transmitted` is set by the rescue
variant and read by 3B `entry_variants[1]`, so a player who rescued sees a
difference in 3A (the freed captives) and again in 3B (the evidence not sent).
The generated block states this without you grepping. If you wanted to know what
else reads `detention_sectors_sealed` and the file does not say, that is the
finding.

---

## Things I noticed while writing this (for you, not decisions)

- **Revision 2: variants append.** An entry variant adds its text after the base
  `entry`; it cannot replace it. That is how the legacy `plot.md` works, and an
  author who reads `entry_variants:` can easily assume a variant substitutes. The
  format may want to say so in the field name or the generated view.
- **Revision 2: the loader checks entry text for unearned terms.** Both new lines
  were first rejected for naming terms the player had not yet earned ("maintenance
  route", "Michelle's route", "copied files"). The format has to keep that check
  at the same layer (a build error), and the author needs the error to say which
  term and which claim owns it, as the loader does today.
- **The plan's sentence about "two outcomes with no claim" is wrong.** See the
  correction above. Plan item 10 should be amended.
- **D's two claimless variants were deleted.** `SL-2C-D-R1` and `-R2` had no
  `when`, no claim and the same operations as `commits_common`. Git history
  (commit `16d6094c`, 2026-11-01; `act2-propagation-contract.md` lines 134-144)
  shows their claims were removed on purpose and the promised rewrite never
  happened. Brandon decided on 2026-11-14 to delete them. The live package
  still has them.
- **Two places say "the purge begins within hours"**: the fact delivery for
  `purge_clock_started` and the Reveal C passage (not drafted). That is a
  wording duplication for the author to judge, not a derivation.
- **The 2C bridge events carry a text no code reads.** Their legacy key is
  `fallback_realization`; the loader reads only `fallback_text` and
  `delivery_text` (`loader.py:1626-1632`) and the loaded records have both as
  `None`. All 11 bridge events in `storylet-routes.yaml` use that key (the 5 resolution events carry it too, beside a real `fallback_text`). The draft keeps the text as
  a reader-only `note`. The 1A draft writes the same kind of text as
  `fallback_text` for `bridge_1a_actionable_lead` and says it lands in
  `fallback_text`; that is wrong for the same reason and is not corrected in the
  1A file, which Brandon has already marked up. **QUESTION:** should these 11
  texts be kept as notes, deleted, or made real fallbacks? That is a story
  decision.
- **`item` for a character.** Legacy `required_dependencies: [brandon]` names a
  character. The shape `{item, relation}` chosen on 2026-11-13 would put a
  character under `item`. A neutral key (`entity`) would be clearer. Brandon
  decided the shape, so I kept `item` and am noting the oddity.
- **Operation order.** The compiled operations for each D variant would list the
  common six first and then the variant's own; legacy lists them in a different
  order. I did not check whether anything depends on order within a storylet
  realization.
- **`says` and the passage are still two copies** of what the player now knows
  (same cost as the 1A draft). The `says` of `transmit` repeats what `sending`
  and `route_close` say.
- **Size, measured:** the draft's `reveals:` block (D and E, 146 lines, comments
  included) replaces 189 lines of `storylet-routes.yaml` (SL-2C-D and -E) and
  164 lines of claims in `knowledge.yaml` (`k_sl_2c_d_r3` 60, `k_sl_2c_d_r4` 60,
  `k_purge_recovery_ready` 8, `k_sl_2c_e_route_effects` 29, `k_purge_window_missed`
  8, which the draft puts in `bridge:`; 354 legacy lines in all). The fact
  declarations, deliveries and the incident are extra on both sides and not
  counted. It is a line count, not a measure of ease of editing; that is what the
  two edits test.

## What I checked by running code, and what I did not

**Revision 2 (2026-11-15).** The revision 1 script was not kept, so I did not
re-run all 180 comparisons. I wrote a small new script that pulls the `scene: 3A`
and `scene: 3B` blocks out of this file and compares both scenes' base entry text
and every entry variant (`when` and text, whitespace collapsed) with the loaded
live package; the result is reported in the plan's record. Everything in the
revision 1 list below was true of the file as of 2026-11-14 and is unchanged in
revision 2, except the 3A entry variants, which that script re-checks.

I wrote a scratch script (not committed; it lives in the session scratchpad, and
the repo's code goes through Ringer) that pulls the three YAML blocks out of this
file, parses them and compares them with the loaded legacy `StoryPackage` at the
snapshot. **180 comparisons, all matching (188 before R1 and R2 were dropped from the draft)** on the final run. A first run found
two mistakes, both fixed in this file: the bridge text was labeled
`fallback_text` although the loader ignores that legacy key (see "Things I
noticed"), and one catalog line had an unquoted comma that cut an ending text
short.

What it compared:

- D: for R3 and R4 (R1 and R2 are deleted from the draft, so they are not compared), `commits_common` plus the variant's commits equal the
  legacy operations; intent, `helps_exit`, boundaries, window, title, pressure
  role and `available_while` equal the legacy fields.
- E: commits, intent, window, boundaries and `available_while`; the two internal
  claims' statements, aliases, audiences, effects and source; their effects
  together cover the variant's commits.
- The two outcome claims: statement, aliases, `earn_when`, `action_evidence`,
  `must_convey`, entities, relevance, `requires`, effects, audience, and the
  expanded passages (parts substituted, whitespace collapsed) equal the legacy
  `delivery_text` and `delivery_variants`.
- The incident: outcome ids, advantages, costs, realization ids, recovery,
  missed window, successor, `completes_scene`; and that the legacy
  `observation_knowledge_ids` can be derived as reveal C's claim plus the two
  outcome claims.
- The three beats, the exit and its bridge text, both scene headers (location,
  objective, phase, entry text, companions, turns, situation, pressure), the
  entry claims, the 3A entry variant, all placements for both scenes, the 2C fact
  purposes and the six deliveries, the two 2C bridge events (the commits, the
  trigger facts, the realizing reveals, and that the text equals the legacy
  `fallback_realization`), the bridge claim, the catalog entries copied here, the
  catalog counts, and that all nine scene-entry facts have the same purpose text
  apart from the scene id.

What it did **not** check, and nobody has:

- First-match semantics of passage lists in the runtime (the check only expanded
  the text).
- Whether anything depends on the order of operations within a realization.
- Whether `internal_claims` is the right shape.
- Whether the legacy loader already rejects an incident cost its variant does not
  commit.
- That the generated block is what a compiler would print; it is the legacy graph
  in new words.
- That the 3A entry text really "follows" the transmit branch in a way a player
  would notice; that is a reading judgment.

## Where you hesitated (fill in)

| Edit | Looked first | Edited | Hesitated at |
| --- | --- | --- | --- |
| 1 | | | |
| 2 | | | |


## Live package

**2026-11-15 (PR #767):** the live package gained a 3A entry variant on `detention_sectors_sealed`, a 3B entry variant on `evidence_not_transmitted`, and the 3A.1 plot sentence now says the upload is still running. This draft matches both.

`SL-2C-D-R1` and `-R2` were deleted from the live package on 2026-11-14 (Ringer run
`delete-2c-d-r1-r2`): 50 lines out of `storylet-routes.yaml` and the two entries out of
`unmapped_realizations` in `tests/test_markdown_story_package.py`. The draft now matches
the live package on this point. Frozen copies (`bench/frozen`, `tests/fixtures`), old
plan documents, the generated `disclosure-matrix.json` and old Ringer manifests under
`scripts/ringer/` still mention them and were left as history.
