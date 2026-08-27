# Continuity Initiative Storylets

> Companion storylet pool for [`plot.md`](plot.md).
>
> **Design contract:** Storylets are optional, bounded situations attached to a playable scene. They may reveal already-permitted context, change pressure, move a scene-local NPC/item, or help satisfy a scene trigger. They are **not** hidden mandatory actions and do not replace free-form LLM roleplay. The player is always Jeremiah Thomas.
>
> **ID scheme:** `SL-<scene>-<letter>`. For example, `SL-1A-B` is the second optional storylet associated with **Scene 1A**.

## Runtime interpretation

Each entry below is authoring data, not a player action menu.

- **Allowed scene** identifies the only playable scene in which the storylet may become active.
- **Source beats** link the storylet to the more detailed outline beats in `plot.md`.
- **Available when** is a semantic state condition; exact runtime predicates should be declared in the compiled story package rather than inferred from this prose.
- **Participants / items** are intentionally limited to entities already established or locally implied by the source scene.
- **Dramatic purpose** explains why the situation exists.
- **Possible realizations** are examples for the narration model, not fixed commands or required branches.
- **Effects** are bounded state changes the storylet may propose if realized and validated.
- **Canonical fact operations live in `storylet-routes.yaml`.** Backticked effect/quality names in this prose source are semantic authoring shorthand unless they also appear as declared fact operations in the compiled route document; do not compile them implicitly.
- **Completion / abort** keep the situation finite.
- **Protected boundary** prevents optional content from leaking later revelations.

---

# Scene 1 — The Search Begins

## Storylets for [Scene 1A — Sarah’s Disappearance](plot.md#scene-1a--sarahs-disappearance)

### SL-1A-A — The House Does Not Look Abandoned

**Source beats:** [1A.1 — The Empty House](plot.md#scene-1a1--the-empty-house), [1A.2 — Sarah’s Last Investigation](plot.md#scene-1a2--sarahs-last-investigation)

**Allowed scene:** `1A`

**Available when**
- Jeremiah is at the house.
- The forced entry, blood, missing work materials, or overturned chair have not yet been meaningfully reconciled.
- The federal patrol has not made the house unsafe.

**Participants / items**
- Jeremiah Thomas
- Sarah Thomas, only through her possessions and prior presence
- Sarah’s phone
- Hidden memory card
- Sarah’s missing laptop/work bag as absence evidence

**Dramatic purpose**
- Turn the house from a generic post-disappearance loss into a physical crime scene.
- Let player curiosity accumulate toward the authored conclusion that Sarah was probably taken.

**Possible realizations**
- Jeremiah notices that the disorder is too localized to fit ordinary looting.
- Handling Sarah’s phone makes the missing laptop and work bag stand out.
- Inspecting the back door or blood changes Jeremiah’s working theory.
- A failed or hurried search can leave uncertainty while still increasing suspicion.

**Effects**
- May increase `sarah_abduction_suspicion`.
- May establish one or more already-authored evidence facts as noticed.
- May make the memory card easier to discover without making this storylet the only route to it.

**Completion**
- Jeremiah has enough physical evidence to treat forced removal as a serious possibility.

**Abort**
- Jeremiah leaves the house after the scene transition becomes valid.
- The federal patrol forces the immediate threat situation to dominate.

**Protected boundary**
- Does not reveal who took Sarah, JANUS, Gabriel’s role, the detention network, or the true mechanics of the disappearances.

**Pacing window**
- earliest: `00:00:00`
- target: `00:01:00`
- latest: `00:02:00`

**Pacing impact**
`brief_delay`

---

### SL-1A-B — Sarah Hid Something for Jeremiah

**Source beats:** [1A.2 — Sarah’s Last Investigation](plot.md#scene-1a2--sarahs-last-investigation), [1A.3 — The Interrupted Message](plot.md#scene-1a3--the-interrupted-message)

**Allowed scene:** `1A`

**Available when**
- Jeremiah remains able to search Sarah’s work area.
- The memory card has not been destroyed or permanently lost.
- Sarah’s investigation is not yet understood.

**Participants / items**
- Jeremiah Thomas
- Sarah Thomas through notes/recordings
- Hidden memory card
- Damaged voice recording

**Dramatic purpose**
- Provide a compact investigative situation in which Sarah’s own preparation gives Jeremiah direction.
- Reinforce Sarah as an active investigator rather than merely a missing objective.

**Possible realizations**
- Jeremiah discovers the memory card through careful searching.
- The damaged recording and card are encountered in either order.
- Jeremiah may initially mistrust the material and only later connect it to the forced entry.
- The recording can emotionally sharpen the danger without adding facts beyond Sarah’s authored warning.

**Effects**
- May set `continuity_initiative_known`.
- May set `emergency_broadcasts_distrusted`.
- May increase `sarah_investigation_context`.
- May set `sarah_lead_actionable` once Jeremiah has a concrete lead he can follow away from the house.

**Completion**
- Jeremiah possesses or has securely copied the relevant evidence and understands that Sarah expected danger.

**Abort**
- The evidence becomes inaccessible through a player-caused destructive proposal; if it is a required future dependency with no fallback, normal game-break handling applies.

**Protected boundary**
- “Continuity Initiative” may be known as Sarah’s suspicious emergency program, but its actual national purpose remains protected.

**Pacing window**
- earliest: `00:00:00`
- target: `00:01:00`
- latest: `00:02:00`

**Pacing impact**
`brief_delay`

---

### SL-1A-C — The Welfare Check Feels Like a Search

**Source beats:** [1A.4 — The First Threat](plot.md#scene-1a4--the-first-threat)

**Allowed scene:** `1A`

**Available when**
- Jeremiah is still at or immediately around the house.
- The federal emergency patrol has arrived.
- Jeremiah has not openly surrendered Sarah’s investigation materials.

**Participants / items**
- Jeremiah Thomas
- Federal emergency patrol officers
- Sarah’s office/work materials
- Hidden memory card, if currently carried or concealed
- Reflective gate tape

**Dramatic purpose**
- Add pressure and force Jeremiah to interpret official behavior without requiring a scripted confrontation.
- Establish that the search is dangerous before the park sequence.

**Possible realizations**
- Jeremiah deflects questions while observing what the officers care about.
- An officer’s attention to Sarah’s reporting becomes more revealing than the stated welfare-check purpose.
- Jeremiah notices the reflective marker only after the patrol leaves.
- Open defiance may raise pressure without automatically forcing combat.

**Effects**
- May increase `authority_attention`.
- May set `house_marked_for_return`.
- May increase `official_story_distrust`.
- May create immediate pressure to leave the house.

**Completion**
- The patrol departs or the interaction otherwise resolves without ending the authored story.

**Abort**
- Jeremiah is no longer at the house.
- A larger validated game-break consequence supersedes the storylet.

**Protected boundary**
- Patrol officers do not know or disclose the later JANUS bait revelation.

**Pacing window**
- earliest: `00:00:00`
- target: `00:01:00`
- latest: `00:02:00`

**Pacing impact**
`brief_delay`

---

## Storylets for [Scene 1B — The Lead in the Park](plot.md#scene-1b--the-lead-in-the-park)

### SL-1B-A — The Dead Drop Has More Than One Meaning

**Source beats:** [1B.1 — Sarah’s Dead Drop](plot.md#scene-1b1--sarahs-dead-drop)

**Allowed scene:** `1B`

**Available when**
- Jeremiah reaches the park/dead-drop area.
- The dead-drop materials remain recoverable.

**Participants / items**
- Jeremiah Thomas
- Sarah Thomas through the dead drop
- Transit access card
- Handwritten number sequence
- Photograph of Sarah with Gabriel
- List of earlier disappearance dates

**Dramatic purpose**
- Let the player decide which clue feels most important while all clues still point toward the authored transport/test history.
- Build a quality-based investigative texture rather than a single “correct” inspection.

**Possible realizations**
- The dates lead Jeremiah to suspect earlier tests.
- The photograph makes the unknown man personally important.
- The transit card and handwritten sequence can be correlated into routing information that points toward a freight/industrial destination, rather than merely suggesting physical infrastructure.
- The number sequence remains unresolved context for later interpretation.

**Effects**
- May increase `evidence_secret_tests`.
- May set `gabriel_face_known`.
- May set `transit_card_acquired`.
- May increase `transport_route_interest`.

**Completion**
- Jeremiah has recovered the dead-drop materials or enough of them to continue.

**Abort**
- The park situation is overtaken by the pursuit/ambush.

**Protected boundary**
- Gabriel is not yet established as trustworthy or as a JANUS developer.

**Pacing window**
- earliest: `00:02:00`
- target: `00:03:15`
- latest: `00:04:30`

**Pacing impact**
`brief_delay`

---

### SL-1B-B — Is Gabriel Hunter or Rescuer?

**Source beats:** [1B.2 — The Man Following Him](plot.md#scene-1b2--the-man-following-him), [1B.3 — Gabriel’s Warning](plot.md#scene-1b3--gabriels-warning)

**Allowed scene:** `1B`

**Available when**
- Gabriel is following or has just contacted Jeremiah.
- Jeremiah has not yet reached a stable judgment about Gabriel.

**Participants / items**
- Jeremiah Thomas
- Gabriel Dexter
- Photograph from the dead drop

**Dramatic purpose**
- Create an early trust problem without forcing the player to accept Gabriel immediately.
- Give Gabriel a reason to earn provisional credibility through behavior and limited disclosure.

**Possible realizations**
- Jeremiah confronts Gabriel with the photograph.
- Jeremiah tries to evade him and sees Gabriel intervene against the patrol.
- Jeremiah questions how Gabriel knows the missing are alive.
- Gabriel refuses full disclosure, preserving suspicion.

**Effects**
- May change `trust_gabriel` within an early bounded range.
- May set `gabriel_identified`.
- May set `missing_may_be_alive`.
- May set `transport_route_identified` when Gabriel can credibly connect Sarah’s transit clue to the removal operation.
- May increase `gabriel_suspicion` at the same time that trust increases.

**Completion**
- Jeremiah has enough reason to continue with Gabriel, even if he remains distrustful.

**Abort**
- Gabriel becomes unavailable through a validated destructive branch.
- The park escape forces immediate movement into the next situation.

**Protected boundary**
- Gabriel may admit prior Continuity Initiative work, but not yet the full JANUS-development history.

**Pacing window**
- earliest: `00:02:00`
- target: `00:03:15`
- latest: `00:04:30`

**Pacing impact**
`brief_delay`

---

### SL-1B-C — The Gate Code Gives Gabriel Away

**Source beats:** [1B.4 — The Park Ambush](plot.md#scene-1b4--the-park-ambush)

**Allowed scene:** `1B`

**Available when**
- A tactical/emergency team has closed on Jeremiah and Gabriel.
- The secured maintenance route is relevant.
- Gabriel remains capable of helping.

**Participants / items**
- Jeremiah Thomas
- Gabriel Dexter
- Tactical/emergency patrol
- Secured maintenance gate

**Dramatic purpose**
- Turn escape pressure into character evidence.
- Let Gabriel solve an immediate problem in a way that creates a larger trust problem.

**Possible realizations**
- Gabriel uses specialized codes only after ordinary access fails.
- Jeremiah notices how practiced Gabriel is with the system.
- Gabriel minimizes the significance of his access.
- The escape succeeds but the player can press him afterward.

**Effects**
- May increase `danger`.
- May increase `gabriel_suspicion`.
- May set `gabriel_retains_system_access`.
- May establish `transport_route_identified` when Gabriel’s retained access and the escape route make the physical removal route followable.

**Completion**
- Jeremiah and Gabriel escape the immediate park pursuit.

**Abort**
- The maintenance route is no longer relevant or the scene has advanced.

**Protected boundary**
- The access proves deeper involvement, not the exact nature of Gabriel’s guilt.

**Pacing window**
- earliest: `00:02:00`
- target: `00:03:15`
- latest: `00:04:30`

**Pacing impact**
`brief_delay`

---

## Storylets for [Scene 1C — Discovery of the Facility](plot.md#scene-1c--discovery-of-the-facility)

### SL-1C-A — The “Abandoned” Terminal Is Working Too Hard

**Source beats:** [1C.1 — Following the Transport Route](plot.md#scene-1c1--following-the-transport-route)

**Allowed scene:** `1C`

**Available when**
- Jeremiah and Gabriel are at the freight terminal/industrial site.
- The underground complex has not yet been fully confirmed.

**Participants / items**
- Jeremiah Thomas
- Gabriel Dexter
- Transit access card
- Freight-terminal infrastructure

**Dramatic purpose**
- Give Jeremiah’s engineering expertise real investigative weight.
- Make discovery of the facility emerge from physical contradictions in the site.

**Possible realizations**
- Jeremiah compares declared abandonment with electrical load, ventilation, or recent structural work.
- The transit card opens access that should not exist at a dead facility.
- Gabriel supplies operational context while Jeremiah supplies structural inference.

**Effects**
- May set `facility_location_confirmed`.
- May increase `facility_activity_evidence`.
- May establish safe service-level access.
- May set `facility_infiltration_needed` when the main installation cannot be reached safely from the service level.

**Completion**
- Jeremiah and Gabriel have a credible route into the service level.

**Abort**
- The facility becomes openly alerted and the subtle-entry situation ends.

**Protected boundary**
- Does not reveal the full national network before the logistics evidence is reached.

**Pacing window**
- earliest: `00:04:30`
- target: `00:05:30`
- latest: `00:06:30`

**Pacing impact**
`brief_delay`

---

### SL-1C-B — One Face in the Processing Line

**Source beats:** [1C.2 — Proof of the Captives](plot.md#scene-1c2--proof-of-the-captives)

**Allowed scene:** `1C`

**Available when**
- The active underground facility has been credibly confirmed.
- Jeremiah can observe the captive-processing area.
- Sarah’s status remains unconfirmed.

**Participants / items**
- Jeremiah Thomas
- Gabriel Dexter
- Sedated prisoners
- Sarah Thomas only as a possible, obscured sighting
- Sarah’s missing-person evidence/identification records, if available

**Dramatic purpose**
- Convert abstract conspiracy evidence into immediate human stakes.
- Intensify Jeremiah’s rescue impulse while preserving uncertainty about Sarah.

**Possible realizations**
- Jeremiah matches prisoner identifiers to missing-person records.
- He sees a woman who might be Sarah but cannot obtain certainty.
- Gabriel physically or verbally stops an impulsive move into the processing area.
- Jeremiah can resent Gabriel’s restraint even if it is strategically sound.

**Effects**
- May set `captives_confirmed_alive`.
- May increase `rescue_urgency`.
- May change `trust_gabriel`.
- May set `sarah_possible_sighting` without setting `sarah_location_confirmed`.
- May set `facility_infiltration_needed` when an impulsive rescue would endanger or relocate the captives.

**Completion**
- Jeremiah accepts that living captives are being held here.

**Abort**
- Observation becomes impossible because of security movement or scene progression.

**Protected boundary**
- Sarah’s exact position and resistance network remain protected.

**Pacing window**
- earliest: `00:04:30`
- target: `00:05:30`
- latest: `00:06:30`

**Pacing impact**
`brief_delay`

---

### SL-1C-C — A Regional Hub, Not the Prison

**Source beats:** [1C.3 — The Nationwide Network](plot.md#scene-1c3--the-nationwide-network), [1C.4 — The Architects Revealed](plot.md#scene-1c4--the-architects-revealed)

**Allowed scene:** `1C`

**Available when**
- The active facility and living captives have been credibly confirmed.
- Gabriel can access the logistics terminal or equivalent authored records.
- Jeremiah knows captives are present but does not yet know the operation’s scale.

**Participants / items**
- Jeremiah Thomas
- Gabriel Dexter
- Charles Jenkins through recorded conference material
- Rebecca Jenkins through recorded conference material
- Logistics records / recorded conference

**Dramatic purpose**
- Deliver the scene’s scale reversal in stages: regional facility → national network → deliberate political strategy.
- Allow the player to absorb operational and ideological evidence separately.

**Possible realizations**
- Logistics categories reveal why different people were selected.
- Jeremiah focuses on Sarah’s category before recognizing the national pattern.
- The Charles/Rebecca recording clarifies the reconstruction strategy.
- Gabriel’s reactions can create additional suspicion without disclosing his later confession.

**Effects**
- May set `national_detention_network_known`.
- May set `selection_categories_known`.
- May set `charles_rebecca_architects_known`.
- May increase `conspiracy_scope`.
- May establish `facility_infiltration_needed` once Jeremiah understands that observation or a direct local rescue is insufficient.

**Completion**
- Jeremiah understands that the disappearances were engineered to remove, classify, and later leverage people at national scale.

**Abort**
- Required records become inaccessible and no declared fallback remains; use dependency/game-break handling rather than silently rewriting the plot.

**Protected boundary**
- JANUS itself, Jeremiah-as-bait, Gabriel’s development role, and Sarah’s resistance network remain protected for Scene 2B.

**Pacing window**
- earliest: `00:04:30`
- target: `00:05:30`
- latest: `00:06:30`

**Pacing impact**
`brief_delay`

---

# Scene 2 — The Infiltration

## Storylets for [Scene 2A — False Identities](plot.md#scene-2a--false-identities)

### SL-2A-A — Gabriel Prepared for This Years Ago

**Source beats:** [2A.1 — Gabriel’s Hideout](plot.md#scene-2a1--gabriels-hideout)

**Allowed scene:** `2A`

**Available when**
- Jeremiah is inside Gabriel’s communications-center hideout.
- Gabriel’s history remains only partially trusted.

**Participants / items**
- Jeremiah Thomas
- Gabriel Dexter
- Surveillance equipment
- Emergency supplies
- Continuity Initiative files

**Dramatic purpose**
- Deepen the contradiction around Gabriel: preparedness can read as foresight, obsession, guilt, or all three.
- Support free-form questioning without prematurely resolving his history.

**Possible realizations**
- Jeremiah examines how long Gabriel has tracked the Initiative.
- Gabriel describes being discredited after trying to expose it.
- Jeremiah notices resources that imply retained professional capability.
- The player may accept the explanation provisionally or become more suspicious.

**Effects**
- May change `trust_gabriel`.
- May increase `gabriel_suspicion`.
- May set `gabriel_prepared_before_event`.
- May increase `continuity_history_context`.

**Completion**
- The hideout has yielded enough context to support planning the infiltration.

**Abort**
- The group leaves for the facility.

**Protected boundary**
- Gabriel’s direct work on JANUS remains protected.

**Pacing window**
- earliest: `00:06:30`
- target: `00:07:30`
- latest: `00:08:30`

**Pacing impact**
`brief_delay`

---

### SL-2A-B — Build the Cover Around a Real Structural Risk

**Source beats:** [2A.2 — The Infiltration Plan](plot.md#scene-2a2--the-infiltration-plan)

**Allowed scene:** `2A`

**Available when**
- Jeremiah and Gabriel have concluded that deliberate deeper infiltration is necessary.
- Jeremiah and Gabriel are preparing entry.
- The cooling/structural-monitoring weakness is known or discoverable from authored facility information.

**Participants / items**
- Jeremiah Thomas
- Gabriel Dexter
- False credentials
- Facility structural/cooling information

**Dramatic purpose**
- Make the infiltration cover depend on Jeremiah’s authentic expertise rather than pure spycraft.
- Give the LLM room to improvise a technically plausible cover story while preserving the authored objective set.

**Possible realizations**
- Jeremiah identifies which infrastructure concern would justify an unscheduled inspection.
- Gabriel shapes that into credential/cover material.
- They discuss how much truth to include in the lie.
- Preparation can improve confidence without guaranteeing entry.

**Effects**
- May set `false_credentials_ready`.
- May set `structural_inspection_cover_ready`.
- May increase `infiltration_preparedness`.
- May reduce initial entry pressure.

**Completion**
- A plausible inspection identity and objective are ready.

**Abort**
- The infiltration has already begun.

**Protected boundary**
- Does not grant knowledge of later archive discoveries or Rebecca’s surveillance decision.

**Pacing window**
- earliest: `00:06:30`
- target: `00:07:30`
- latest: `00:08:30`

**Pacing impact**
`brief_delay`

---

### SL-2A-C — The Supervisor Needs a Reason

**Source beats:** [2A.3 — Entering the Facility](plot.md#scene-2a3--entering-the-facility), [2A.4 — The First Complication](plot.md#scene-2a4--the-first-complication)

**Allowed scene:** `2A`

**Available when**
- The false inspection identities/cover are ready.
- Jeremiah and Gabriel are passing facility security.
- Their credentials have survived initial checks.
- The unscheduled nature of the inspection is being questioned.

**Participants / items**
- Jeremiah Thomas
- Gabriel Dexter
- Facility supervisor
- False credentials

**Dramatic purpose**
- Give Jeremiah a social/technical obstacle that can be realized through free-form roleplay.
- Preserve dramatic irony: entry can succeed even as Rebecca quietly becomes aware of Gabriel.

**Possible realizations**
- Jeremiah explains progressive-collapse risk in his own words.
- Gabriel stays quiet to avoid drawing recognition.
- Overexplaining may raise suspicion while still succeeding.
- The supervisor grants restricted-infrastructure access reluctantly.

**Effects**
- May set `restricted_corridor_access`.
- May change `facility_suspicion`.
- May set `rebecca_observing_infiltrators` through a pacing/event effect once facial recognition occurs.
- `restricted_corridor_access` is the outgoing scene bridge once the protagonists have moved beyond the outer security layer.

**Completion**
- Jeremiah and Gabriel have moved beyond the main public/security entry layer.

**Abort**
- The cover is fully blown and an alternate declared transition supersedes it.

**Protected boundary**
- Jeremiah and Gabriel do not learn that Rebecca is observing them merely because the state flag exists.

**Pacing window**
- earliest: `00:06:30`
- target: `00:07:30`
- latest: `00:08:30`

**Pacing impact**
`brief_delay`

---

## Storylets for [Scene 2B — Evidence and Betrayal](plot.md#scene-2b--evidence-and-betrayal)

### SL-2B-A — JANUS Classified Everyone

**Source beats:** [2B.1 — The Selection Algorithm](plot.md#scene-2b1--the-selection-algorithm)

**Allowed scene:** `2B`

**Available when**
- Jeremiah can access the records archive.
- JANUS has not yet been understood.

**Participants / items**
- Jeremiah Thomas
- Gabriel Dexter
- JANUS records

**Dramatic purpose**
- Reveal the selection system through concrete classifications rather than an exposition dump.
- Connect national-scale data collection directly to Sarah and Jeremiah.

**Possible realizations**
- Jeremiah searches Sarah’s record first.
- He notices the categories used to predict resistance, influence, vulnerability, and leverage.
- His own record reveals that being left behind was itself a decision.
- Gabriel’s reaction can become part of the evidence.

**Effects**
- May set `janus_known`.
- May set `sarah_selected_for_resistance_influence`.
- May set `jeremiah_deliberately_left_behind`.
- May sharply increase `betrayal_pressure`.

**Completion**
- Jeremiah understands JANUS as the selection mechanism and recognizes that his own path was modeled.

**Abort**
- Archive access ends before enough material is recovered; another declared source may serve as fallback if the package defines one.

**Protected boundary**
- The exact reason Charles expected Jeremiah to expose Gabriel may emerge only as supported by the authored records; no new hidden motives are invented.

**Pacing window**
- earliest: `00:08:30`
- target: `00:09:30`
- latest: `00:10:30`

**Pacing impact**
`brief_delay`

---

### SL-2B-B — Gabriel’s Name Is in the Build Records

**Source beats:** [2B.2 — Jeremiah Was Bait](plot.md#scene-2b2--jeremiah-was-bait), [2B.3 — Gabriel’s Role](plot.md#scene-2b3--gabriels-role)

**Allowed scene:** `2B`

**Available when**
- JANUS has been credibly identified in the archive evidence.
- JANUS records are accessible.
- Gabriel’s development role has not yet been confronted.

**Participants / items**
- Jeremiah Thomas
- Gabriel Dexter
- JANUS development records

**Dramatic purpose**
- Turn accumulated distrust into a direct character confrontation.
- Preserve ambiguity between culpability for creating the system and opposition to its later use.

**Possible realizations**
- Jeremiah confronts Gabriel immediately.
- He withholds the discovery briefly and observes Gabriel first.
- Gabriel admits helping design JANUS for emergency-risk identification.
- Jeremiah challenges whether Gabriel is still manipulating him.

**Effects**
- May set `gabriel_janus_role_known`.
- May set `gabriel_claimed_reform_motive`.
- May set `janus_evidence` when the development records are preserved/authenticated as evidence.
- May substantially change `trust_gabriel`.
- May increase or decrease `gabriel_suspicion` depending on accepted interaction facts.

**Completion**
- Gabriel’s original role and claimed break with Charles are explicit between him and Jeremiah.

**Abort**
- Gabriel is absent/unavailable and the confrontation must be deferred by declared package logic.

**Protected boundary**
- Gabriel’s later sacrifice/confession is not foreshadowed as guaranteed.

**Pacing window**
- earliest: `00:08:30`
- target: `00:09:30`
- latest: `00:10:30`

**Pacing impact**
`brief_delay`

---

### SL-2B-C — Sarah Is Already Sabotaging the System

**Source beats:** [2B.4 — Sarah’s Hidden Resistance](plot.md#scene-2b4--sarahs-hidden-resistance)

**Allowed scene:** `2B`

**Available when**
- JANUS has been credibly identified in the archive evidence.
- Jeremiah can inspect corrupted prisoner/maintenance records.
- Sarah’s active resistance is not yet known.

**Participants / items**
- Jeremiah Thomas
- Gabriel Dexter
- Sarah Thomas through coded records
- Corrupted prisoner files / maintenance reports

**Dramatic purpose**
- Reverse the rescue framing: Sarah is an active agent affecting the facility from inside.
- Give Jeremiah renewed direction after the JANUS/Gabriel betrayal.

**Possible realizations**
- Jeremiah recognizes phrases Sarah used in private notes.
- A pattern of delayed transfers and altered classifications becomes visible.
- Gabriel sees operational sabotage; Jeremiah sees Sarah’s signature.
- The player may infer organization before knowing its full scale.

**Effects**
- May set `sarah_resistance_known`.
- May increase `hope`.
- May set `prisoner_records_corrupted`.
- May preserve enough corrupted JANUS/prisoner material to establish `janus_evidence` while also pointing toward Sarah’s resistance.

**Completion**
- Jeremiah knows Sarah is alive enough to act or has left recent operational evidence strongly supporting that conclusion.

**Abort**
- The records are lost and a declared alternate path must carry the same necessary transition information.

**Protected boundary**
- The exact uprising plan and broadcast solution remain protected until later scenes.

**Pacing window**
- earliest: `00:08:30`
- target: `00:09:30`
- latest: `00:10:30`

**Pacing impact**
`brief_delay`

---

## Storylets for [Scene 2C — The Trap Closes](plot.md#scene-2c--the-trap-closes)

### SL-2C-A — Rebecca Offers Gabriel a Different Conspiracy

**Source beats:** [2C.1 — Rebecca’s Offer](plot.md#scene-2c1--rebeccas-offer)

**Allowed scene:** `2C`

**Available when**
- Rebecca has identified Gabriel.
- Gabriel remains capable of private contact.
- Jeremiah may know of the contact only if the interaction makes that knowledge available.

**Participants / items**
- Gabriel Dexter
- Rebecca Jenkins
- Jeremiah Thomas, only when physically/informationally justified

**Dramatic purpose**
- Show fracture inside the antagonist coalition without turning Rebecca into an ally.
- Pressure Gabriel’s credibility after his JANUS admission.

**Possible realizations**
- Rebecca frames Charles as the immediate danger.
- She offers Sarah’s release in exchange for helping her seize control.
- Gabriel appears to consider the offer to gain executive access.
- Jeremiah can misread Gabriel’s performance if he lacks context.

**Effects**
- May set `rebecca_offer_active`.
- May increase `antagonist_internal_conflict`.
- May change `trust_gabriel` only if Jeremiah has legitimate knowledge of the exchange.
- May open a route toward executive-level access.

**Completion**
- Gabriel has accepted, rejected, or strategically exploited the offer enough for the scene to move on.

**Abort**
- Rebecca withdraws the offer or direct conflict supersedes it.

**Protected boundary**
- Rebecca’s later claim that she opposed killing captives is not treated as verified truth.

**Pacing window**
- earliest: `00:10:30`
- target: `00:11:45`
- latest: `00:13:00`

**Pacing impact**
`brief_delay`

---

### SL-2C-B — The Purge Clock Starts Moving

**Source beats:** [2C.2 — The Purge Order](plot.md#scene-2c2--the-purge-order)

**Allowed scene:** `2C`

**Available when**
- Charles has learned that prisoner records were corrupted.
- The purge/transfer order has become active.

**Participants / items**
- Jeremiah Thomas
- Gabriel Dexter
- Charles Jenkins through orders/broadcast preparation
- Facility records/alerts where locally available

**Dramatic purpose**
- Add deterministic time/pressure to a scene that could otherwise become leisurely.
- Make delay materially dangerous without scripting Jeremiah’s response.

**Possible realizations**
- An internal order reveals accelerated transfers.
- Facility movement patterns suddenly change.
- Broadcast-preparation traffic exposes the deadline indirectly.
- Jeremiah and Gabriel disagree about what the remaining time permits.

**Effects**
- Starts or advances `purge_pressure`.
- May set `charles_broadcast_imminent`.
- May reduce safe infiltration options as pressure rises.
- May fire scene pacing complications at declared thresholds.

**Completion**
- The pressure event remains in force until the scene transition; this storylet completes once the deadline is understood.

**Abort**
- None while the authored purge order is active, though the storylet itself does not have to be selected as a discrete encounter.

**Protected boundary**
- Does not reveal the later exact broadcast-system solution before Sarah provides it.

**Pacing window**
- earliest: `00:10:30`
- target: `00:11:45`
- latest: `00:13:00`

**Pacing impact**
`brief_delay`

---

### SL-2C-C — The False Choice Breaks Open

**Source beats:** [2C.3 — Evidence or Rescue](plot.md#scene-2c3--evidence-or-rescue), [2C.4 — Sarah Changes the Choice](plot.md#scene-2c4--sarah-changes-the-choice)

**Allowed scene:** `2C`

**Available when**
- The purge/transfer clock is active and understood.
- Enough evidence exists to expose the conspiracy.
- Rescue remains possible but dangerous.
- Sarah’s coded maintenance channel can reach Jeremiah/Gabriel.

**Participants / items**
- Jeremiah Thomas
- Gabriel Dexter
- Sarah Thomas through coded communication
- Copied conspiracy evidence
- Maintenance network

**Dramatic purpose**
- Realize the central crisis as a character disagreement, then convert it into the authored combined mission.
- Keep the player free to argue, hesitate, or explore while pacing prevents indefinite stalling.

**Possible realizations**
- Gabriel argues for immediate transmission.
- Jeremiah refuses to abandon the captives.
- Their conflict can become personal because of Gabriel’s earlier guilt.
- Sarah’s coded message introduces the manual broadcast/door-opening solution.

**Effects**
- May set `evidence_ready_to_transmit`.
- May set `rescue_exposure_crisis_explicit`.
- May set `combined_broadcast_rescue_plan_known`.
- May set `rebecca_office_required_for_broadcast`.
- Establishes `combined_broadcast_rescue_plan_known`, the scene bridge toward reaching Sarah and executing the combined mission.

**Completion**
- Jeremiah and Gabriel understand that the next objective combines rescue and exposure.

**Abort**
- The player causes a validated non-canonical branch that makes the combined plan impossible and chooses `proceed`.

**Protected boundary**
- Exact events of the uprising, Gabriel’s sacrifice, facility destruction, and final broadcast outcome remain protected.

**Pacing window**
- earliest: `00:10:30`
- target: `00:11:45`
- latest: `00:13:00`

**Pacing impact**
`brief_delay`

---

# Scene 3 — The Captives

## Storylets for [Scene 3A — Reaching Sarah](plot.md#scene-3a--reaching-sarah)

### SL-3A-A — The Rescue Target Is Running an Uprising

**Source beats:** [3A.1 — The Detention Block](plot.md#scene-3a1--the-detention-block)

**Allowed scene:** `3A`

**Available when**
- Jeremiah reaches Sarah’s detention sector.
- Sarah is active and the purge countdown is running.

**Participants / items**
- Jeremiah Thomas
- Sarah Thomas
- Gabriel Dexter
- Prisoners
- Sympathetic facility workers
- Stolen radios

**Dramatic purpose**
- Pay off Sarah’s agency with an in-person reversal of Jeremiah’s rescue expectations.
- Reframe the immediate goal from “get Sarah out” to “help the organized captives expose the whole network.”

**Possible realizations**
- The reunion is interrupted by Sarah directing others.
- Jeremiah tries to prioritize Sarah; she redirects him to the national stakes.
- Prisoners treat Sarah as an organizer rather than a victim.
- The reunion can establish that Sarah is ready to launch coordinated disturbances, but the canonical launch waits until the experiment stakes and expiring-code deadline have been established (or equivalent validated free-text realizations occur).
- Gabriel’s arrival may be met with distrust because of his history.

**Effects**
- May set `jeremiah_sarah_reunited`.
- May set `uprising_prepared`.
- May establish that the uprising is prepared; the canonical launch is gated later in the scene.
- May increase `network_locations_required_for_broadcast`.
- May change relationship/trust facts consistent with the reunion.

**Completion**
- Jeremiah accepts Sarah as an operational partner and understands the larger rescue requirement.

**Abort**
- Scene pressure escalates directly into the uprising before the interaction fully resolves.

**Protected boundary**
- The final outcome of the broadcast and Gabriel’s fate remain unknown.

**Pacing window**
- earliest: `00:13:00`
- target: `00:14:00`
- latest: `00:15:00`

**Pacing impact**
`brief_delay`

---

### SL-3A-B — The “Rescued” Captives Were Being Prepared

**Source beats:** [3A.2 — The Experiments](plot.md#scene-3a2--the-experiments)

**Allowed scene:** `3A`

**Available when**
- Jeremiah has reached Sarah and can move with her resistance network.
- Jeremiah and Sarah can pass through or access evidence from the medical level.
- The experiment program is not yet fully understood.

**Participants / items**
- Jeremiah Thomas
- Sarah Thomas
- Prisoners
- Medical/behavioral experiment records or equipment already present in the authored setting

**Dramatic purpose**
- Raise the moral and political stakes of Charles’s planned broadcast.
- Show that simply releasing selected prisoners could strengthen the conspiracy.

**Possible realizations**
- Sarah explains what she has observed while Jeremiah sees corroborating evidence.
- A conditioned “rescue” plan becomes visible through records or treatment setup.
- Jeremiah recognizes that public testimony itself has been engineered.

**Effects**
- May set `behavioral_experiments_known`.
- May set `conditioned_release_plan_known`.
- May increase `broadcast_evidence_value`.
- May increase `danger` or `moral_urgency`.

**Completion**
- Jeremiah understands why exposing the experiments must be part of the broadcast evidence.

**Abort**
- Immediate security pressure makes the medical level inaccessible.

**Protected boundary**
- Do not invent successful mind control beyond the specific authored methods and goals.

**Pacing window**
- earliest: `00:13:00`
- target: `00:14:00`
- latest: `00:15:00`

**Pacing impact**
`brief_delay`

---

### SL-3A-C — The Override Codes Are Expiring

**Source beats:** [3A.3 — The Unexpected Prisoner](plot.md#scene-3a3--the-unexpected-prisoner), [3A.4 — The Uprising Begins](plot.md#scene-3a4--the-uprising-begins)

**Allowed scene:** `3A`

**Available when**
- Jeremiah has reached Sarah.
- The behavioral-experiment stakes have been established.
- The senior official prisoner is reachable.
- Charles’s planned authority activation remains pending.

**Participants / items**
- Jeremiah Thomas
- Sarah Thomas
- Gabriel Dexter
- Senior official prisoner
- Emergency military override authorization codes

**Dramatic purpose**
- Add a second deadline tied directly to the national political takeover.
- Turn one prisoner into a time-sensitive strategic resource without making the NPC a permanent companion.

**Possible realizations**
- The official explains that Charles framed and imprisoned members of his own government.
- Sarah evaluates the codes as one more way to disrupt the takeover.
- The uprising may begin before every implication can be discussed.
- The expiring authorization window can itself force the resistance to launch coordinated disturbances.
- The codes can be secured or relayed according to validated free-form action.

**Effects**
- May set `charles_framed_officials_known`.
- May set `military_override_codes_available`.
- Starts/advances `authority_activation_pressure`.
- May set `detention_uprising_started` when the deadline forces Sarah to launch the resistance.
- May help resistance efforts under declared package rules; securing the codes is not required for the Scene 3A → 3B transition.

**Completion**
- The codes and their expiration condition are understood/secured, or a declared alternate path makes them unnecessary.

**Abort**
- The codes expire after the relevant pacing deadline.
- The NPC becomes unavailable; future satisfiability determines whether a warning is required.

**Protected boundary**
- The codes do not automatically solve the facility fight or national conspiracy.

**Pacing window**
- earliest: `00:13:00`
- target: `00:14:00`
- latest: `00:15:00`

**Pacing impact**
`brief_delay`

---

## Storylets for [Scene 3B — The Battle for the Broadcast](plot.md#scene-3b--the-battle-for-the-broadcast)

### SL-3B-A — Give JANUS Too Many Emergencies

**Source beats:** [3B.1 — The Facility Fights Back](plot.md#scene-3b1--the-facility-fights-back)

**Allowed scene:** `3B`

**Available when**
- JANUS is predicting resistance movement.
- Jeremiah can affect facility infrastructure.
- The group is trying to reach Rebecca’s office/broadcast controls.

**Participants / items**
- Jeremiah Thomas
- Sarah Thomas
- Gabriel Dexter
- JANUS as system
- Facility doors, cameras, power, structural alarms, and unused corridors

**Dramatic purpose**
- Make Jeremiah’s engineering mindset the counter to predictive security.
- Encourage creative free-form disruption rather than one prescribed puzzle solution.

**Possible realizations**
- Jeremiah creates unrelated structural alarms.
- Power cuts or flooding make the group’s true route less legible.
- The group intentionally chooses tactically irrational movement.
- A failed disruption can still raise pressure while teaching what JANUS is using.

**Effects**
- May increase `janus_prediction_noise`.
- May reduce `janus_route_confidence`.
- May force `human_security_control` when a declared threshold is reached.
- May increase local infrastructure pressure as a cost.

**Completion**
- JANUS can no longer reliably predict the group’s route and human operators take over.

**Abort**
- JANUS is already disconnected or the group has reached Rebecca’s office.

**Protected boundary**
- The disruption does not itself disconnect the external relay; that remains Gabriel’s later task.

**Pacing window**
- earliest: `00:15:00`
- target: `00:16:15`
- latest: `00:17:30`

**Pacing impact**
`brief_delay`

---

### SL-3B-B — Rebecca Bargains With the Only Thing She Still Has

**Source beats:** [3B.2 — Rebecca’s Office](plot.md#scene-3b2--rebeccas-office), [3B.3 — Charles’s Betrayal](plot.md#scene-3b3--charless-betrayal)

**Allowed scene:** `3B`

**Available when**
- JANUS has been overloaded enough that human security has taken direct control.
- Jeremiah and Sarah have reached Rebecca’s office.
- Rebecca is present and has not yet escaped.
- Charles has not fully destroyed the local situation.

**Participants / items**
- Jeremiah Thomas
- Sarah Thomas
- Rebecca Jenkins
- Charles Jenkins through remote communication
- Detention-site location information available to Rebecca

**Dramatic purpose**
- Put Rebecca’s self-preservation against Sarah’s evidence of her direct responsibility.
- Allow Charles’s betrayal to collapse Rebecca’s bargaining position in real time.

**Possible realizations**
- Rebecca claims surrender is the only way to save the failing facility.
- Sarah confronts her with approvals for experiments.
- Rebecca offers all detention-site locations.
- Charles remotely strips Rebecca of control and locks down the office.

**Effects**
- May set `rebecca_experiment_approval_confronted`.
- May set `detention_locations_offer_known`.
- May set `charles_abandoned_rebecca`.
- May increase `facility_destruction_threat`.
- May change Rebecca’s status from antagonist-in-control to trapped/self-preserving antagonist.

**Completion**
- Charles’s remote betrayal has occurred and Rebecca can no longer credibly claim operational control.

**Abort**
- Rebecca escapes before the confrontation or a non-canonical branch supersedes it.

**Protected boundary**
- Rebecca’s offer is not automatically trusted; later archive evidence remains independently valuable.

**Pacing window**
- earliest: `00:15:00`
- target: `00:16:15`
- latest: `00:17:30`

**Pacing impact**
`brief_delay`

---

### SL-3B-C — Gabriel Holds the Relay Open

**Source beats:** [3B.4 — Gabriel’s Sacrifice](plot.md#scene-3b4--gabriels-sacrifice)

**Allowed scene:** `3B`

**Available when**
- JANUS predictive control has been defeated.
- Charles has stripped Rebecca of control and the protagonists have secured exact detention-site locations.
- The broadcast is ready except for Charles’s control of the external communications relay.
- Gabriel is still capable of reaching/operating the relay chamber.

**Participants / items**
- Gabriel Dexter
- Jeremiah Thomas and Sarah Thomas through communication where justified
- External communications relay
- Gabriel’s confession recording/transmission

**Dramatic purpose**
- Resolve Gabriel’s guilt arc through an action that is both operationally necessary and personally accountable.
- Create the final condition for the national transmission without scripting Jeremiah’s emotional response.

**Possible realizations**
- Gabriel chooses the relay because his old access makes him the viable operator.
- He transmits a confession that authenticates Sarah’s evidence.
- Security pressure and electrical danger make continued relay control costly.
- Jeremiah or Sarah may argue against him, but the authored situation keeps the relay problem concrete.

**Effects**
- May set `external_relay_disconnected_from_janus`.
- May set `gabriel_confession_available`.
- May set `broadcast_path_open`.
- May set `broadcast_started` once Sarah/Jeremiah activate the transmission through the opened relay.
- May critically worsen `gabriel_health/status` only through validated effects consistent with the authored sacrifice.
- `broadcast_started` is the Scene 3B → 3C bridge.

**Completion**
- The relay remains open long enough for Sarah and Jeremiah to begin the broadcast.

**Abort**
- A declared fallback solves the relay dependency instead; otherwise incapacitating Gabriel beforehand may be game-breaking and must be handled explicitly.

**Protected boundary**
- Gabriel’s final survival/fate remains unresolved until the authored escape/collapse outcome permits it.

**Pacing window**
- earliest: `00:15:00`
- target: `00:16:15`
- latest: `00:17:30`

**Pacing impact**
`brief_delay`

---

## Storylets for [Scene 3C — Exposure and Escape](plot.md#scene-3c--exposure-and-escape)

### SL-3C-A — Charles Tries to Reframe the Broadcast

**Source beats:** [3C.1 — The National Transmission](plot.md#scene-3c1--the-national-transmission)

**Allowed scene:** `3C`

**Available when**
- `broadcast_started` is true.
- The broadcast path is open.
- Sarah has sufficient evidence to transmit.
- Charles still has remote communications capability.

**Participants / items**
- Jeremiah Thomas
- Sarah Thomas
- Charles Jenkins remotely
- Broadcast evidence
- Gabriel’s confession, if available
- Live facility feeds where available

**Dramatic purpose**
- Make exposure a contest over credibility rather than a simple upload-success event.
- Let accumulated evidence qualities determine how convincingly Sarah can answer Charles.

**Possible realizations**
- Sarah presents captives, JANUS records, facility locations, experiment evidence, and planning records.
- Charles calls the group terrorists.
- Sarah counters with independently verifiable facility information or live images.
- Gabriel’s confession can authenticate evidence without being the only possible credibility support if fallbacks are declared.

**Effects**
- May increase `public_conspiracy_awareness`.
- May set `national_facility_locations_broadcast`.
- May set `charles_public_denial`.
- May set `truth_no_longer_containable` once declared credibility/evidence conditions are met.

**Completion**
- Enough independently checkable evidence is public that Charles cannot contain the story by controlling one broadcast channel.

**Abort**
- Broadcast capability is permanently lost through a validated non-canonical branch.

**Protected boundary**
- Phase Two remains protected until the resolution discovery.

**Pacing window**
- earliest: `00:17:30`
- target: `00:19:00`
- latest: `00:20:00`

**Pacing impact**
`brief_delay`

---

### SL-3C-B — Rebecca’s Archive Cannot Simply Be Destroyed

**Source beats:** [3C.2 — The Final Confrontation](plot.md#scene-3c2--the-final-confrontation)

**Allowed scene:** `3C`

**Available when**
- Rebecca is attempting to escape.
- The portable archive is present and recoverable.

**Participants / items**
- Jeremiah Thomas
- Sarah Thomas
- Rebecca Jenkins
- Portable archive of conspirator identities and prisoner locations

**Dramatic purpose**
- Turn a chase/capture into an information-custody problem.
- Prevent “destroy the bad thing” from being an uncomplicated solution because the same archive can save captives.

**Possible realizations**
- Jeremiah stops Rebecca and learns what the archive contains.
- Rebecca exploits the mixed contents to bargain.
- Sarah argues for duplication/distribution rather than destruction or sole custody.
- The archive can be copied to independent networks once capability exists.

**Effects**
- May set `portable_archive_secured`.
- May set `archive_contains_prisoner_locations`.
- May set `archive_copies_distributed`.
- May set `rebecca_captured` when the authored confrontation resolves.

**Completion**
- The archive is preserved/distributed in a way that does not strand the prisoners whose locations it contains.

**Abort**
- The archive is destroyed or lost; future-satisfiability rules determine whether this is merely costly or game-breaking based on declared fallbacks.

**Protected boundary**
- The archive does not automatically contain or reveal Phase Two unless that is explicitly declared elsewhere in the package.

**Pacing window**
- earliest: `00:17:30`
- target: `00:19:00`
- latest: `00:20:00`

**Pacing impact**
`brief_delay`

---

### SL-3C-C — Escape While the Facility Comes Apart

**Source beats:** [3C.3 — The Collapse](plot.md#scene-3c3--the-collapse), [3C.4 — Resolution and New Direction](plot.md#scene-3c4--resolution-and-new-direction)

**Allowed scene:** `3C`

**Available when**
- Charles has activated facility destruction.
- The prisoners are moving toward escape routes.
- Jeremiah can still affect structural/power systems.

**Participants / items**
- Jeremiah Thomas
- Sarah Thomas
- Gabriel Dexter only as allowed by his current status/fate
- Escaping prisoners
- Facility emergency supports / power systems
- Surface gates and maintenance tunnels

**Dramatic purpose**
- Give Jeremiah one final engineering problem while Sarah leads the human evacuation.
- Move the climax into falling action without removing danger too early.

**Possible realizations**
- Jeremiah redirects power to keep some sections supported.
- Sarah organizes movement through maintenance tunnels.
- The group must accept that not every section can be saved.
- Gabriel’s relay action contributes to the surface gates opening if his authored state permits it.

**Effects**
- May increase `facility_collapse`.
- May set `evacuation_route_open`.
- May set `captives_reaching_surface`.
- May set `los_angeles_facility_lost`.
- May transition into resolution once escape and broadcast consequences are established.

**Completion**
- The surviving captives reach the surface and the Los Angeles operation can no longer be concealed.

**Abort**
- Ends on transition to the resolution state.

**Protected boundary**
- The final Phase Two revelation is delivered only by the authored recovered-JANUS resolution event, not by this escape storylet.

**Pacing window**
- earliest: `00:17:30`
- target: `00:19:00`
- latest: `00:20:00`

**Pacing impact**
`brief_delay`

---

# Resolution-phase storylet realizations

These do **not** create a new playable scene after `3C`. The storylets themselves remain optional realization guidance, but the underlying authored resolution beats that belong to the sole ending—network fragmentation, Charles remaining at large, and the Phase Two revelation—are canonical and must also have non-storylet fallback realizations in the compiled package.

### SL-3C-D — The Network Fractures

**Source beats:** [3C.4 — Resolution and New Direction](plot.md#scene-3c4--resolution-and-new-direction)

**Allowed scene:** `3C` (resolution phase only)

**Available when**
- `truth_no_longer_containable` is true.
- Captives have reached the surface.
- The broadcast consequences are being summarized.

**Participants / items**
- Jeremiah Thomas
- Sarah Thomas
- Public reports from other detention sites

**Dramatic purpose**
- Show distributed consequences without pulling unrelated off-scene NPC private state into the prompt.

**Possible realizations**
- Reports indicate some facilities surrender while others resist.
- Families and communities begin independent rescue efforts.
- Official agencies issue conflicting denials.
- Jeremiah and Sarah understand that Los Angeles was a victory, not an ending.

**Effects**
- May set `national_network_fragmenting`.
- May set `community_rescue_efforts_begun`.
- May establish Jeremiah/Sarah’s next-direction facts.

**Completion**
- The immediate national consequences are established.

**Abort**
- None in canonical resolution.

**Protected boundary**
- Off-scene facilities are described only through public/currently-known reports.

**Pacing window**
- earliest: `00:17:30`
- target: `00:19:00`
- latest: `00:20:00`

**Pacing impact**
`brief_delay`

---

### SL-3C-E — Phase One

**Source beats:** [3C.4 — Resolution and New Direction](plot.md#scene-3c4--resolution-and-new-direction)

**Allowed scene:** `3C` (final resolution only)

**Available when**
- The canonical resolution has been reached.
- A partially recovered JANUS file is available through the authored resolution event.

**Participants / items**
- Jeremiah Thomas
- Sarah Thomas
- Partially recovered JANUS file

**Dramatic purpose**
- Deliver the final sequel-scale reversal only after the main personal and national victory has landed.

**Possible realizations**
- Sarah or Jeremiah notices the operation label “Phase One.”
- The recovered material identifies Phase Two as an effort to provoke conflict among those who remained.
- The revelation changes the meaning of the unrest already visible outside the facility.

**Effects**
- Sets `phase_one_label_known`.
- Sets `phase_two_conflict_plan_known`.
- Preserves `charles_at_large`.

**Completion**
- The final unresolved threat is established.

**Abort**
- None in canonical resolution.

**Protected boundary**
- Do not invent Phase Two mechanisms beyond the source statement that it was designed to provoke conflict among those who remained.

**Pacing window**
- earliest: `00:17:30`
- target: `00:19:00`
- latest: `00:20:00`

**Pacing impact**
`brief_delay`

---

# Coverage index

| Playable scene | Storylets | Primary function |
|---|---|---|
| [1A](plot.md#scene-1a--sarahs-disappearance) | `SL-1A-A` … `SL-1A-C` | Crime-scene inference, Sarah’s evidence, first authority pressure |
| [1B](plot.md#scene-1b--the-lead-in-the-park) | `SL-1B-A` … `SL-1B-C` | Dead-drop clues, Gabriel trust, pursuit |
| [1C](plot.md#scene-1c--discovery-of-the-facility) | `SL-1C-A` … `SL-1C-C` | Facility discovery, living captives, national scale |
| [2A](plot.md#scene-2a--false-identities) | `SL-2A-A` … `SL-2A-C` | Gabriel context, infiltration preparation, entry complication |
| [2B](plot.md#scene-2b--evidence-and-betrayal) | `SL-2B-A` … `SL-2B-C` | JANUS, Jeremiah-as-bait, Gabriel’s role, Sarah’s resistance |
| [2C](plot.md#scene-2c--the-trap-closes) | `SL-2C-A` … `SL-2C-C` | Rebecca’s offer, purge pressure, crisis reframing |
| [3A](plot.md#scene-3a--reaching-sarah) | `SL-3A-A` … `SL-3A-C` | Reunion reversal, experiments, deadline/override |
| [3B](plot.md#scene-3b--the-battle-for-the-broadcast) | `SL-3B-A` … `SL-3B-C` | Defeat JANUS, confront Rebecca, open relay |
| [3C](plot.md#scene-3c--exposure-and-escape) | `SL-3C-A` … `SL-3C-E` | Broadcast credibility, archive custody, collapse, epilogue |

## Canonical scene beats vs. optional storylets

The compiled story package may declare a **canonical bridge event** for a scene transition. A canonical bridge event is story progression that must eventually become true for the single authored scene chain to continue, but **no storylet is itself mandatory**. Storylets are optional realization guidance: free-text player action, NPC reaction, or pacing pressure may realize the same validated fact operation without selecting a storylet.

Bridge facts should describe why the current scene is complete and the next scene is now necessary; they should not pre-assert a revelation whose dramatic payoff belongs to the next scene. Pacing events should create observable pressure or consequences rather than unearned player knowledge.

Current bridge facts are: `sarah_lead_actionable`, `transport_route_departure_ready`, `facility_infiltration_needed`, `restricted_corridor_access`, `archive_crisis_understood`, `combined_broadcast_rescue_plan_known`, `command_levels_assault_underway`, and `broadcast_started`.

## Authoring notes

1. **Optional means optional.** A scene must remain satisfiable even if none of its ordinary storylets are selected. Canonical bridge events may be required, but storylets only provide optional realization guidance for them.
2. **No fixed action vocabulary.** “Possible realizations” are prompt guidance only. The LLM interprets arbitrary player roleplay and proposes semantic effects.
3. **Scene-local context first.** Only participating/present/relevant entities should enter the default turn context. Off-scene references should add only public/currently-known facts.
4. **Pressure carries pacing.** `SL-2C-B`, `SL-3A-C`, and the collapse/broadcast situations are natural places for deterministic pressure. Pressure may force circumstances to worsen or a canonical event to become urgent, but it must not grant Jeremiah unexplained knowledge.
5. **Required dependencies stay explicit elsewhere.** The memory card, Gabriel, broadcast access, relay access, archive, or any substitutes/fallbacks should be declared in the package dependency model; this file does not silently make them mandatory.
6. **Protected revelations are monotonic.** Optional content can foreshadow later facts, but it must not make a protected revelation true/known before the original scene permits it.
7. **Effects are bounded proposals.** The exact fact paths, numeric pressure ranges, trigger predicates, and transition priorities belong in validated package data rather than being inferred from prose here.

## Design-reference rationale

This pool follows the architecture summarized in `storylet.md`:

- Façade-style organization keeps higher-level dramatic progression separate from lower-level reactive realization.
- Failbetter-style quality-based narrative makes small storylets available from mutable state and lets their effects feed later availability.
- The “Grandfather Clock” pattern is especially close to the intended pacing model: fast local activity can build progress while the major narrative chain advances at a deliberately controlled rate.
- Full causal planning is not treated as the runtime authoring model; deterministic dependency/future-satisfiability checks protect the authored scene spine instead.
