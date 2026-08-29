# Continuity Initiative Storylets

> Companion storylet pool for [`plot.md`](plot.md).
>
> **Design contract:** Storylets are optional, bounded situations attached to a playable scene. They may reveal already-permitted context, change pressure, move a scene-local NPC/item, or help satisfy a scene trigger. They are **not** hidden mandatory actions and do not replace free-form LLM roleplay. The player is always Kristin Schweitzer.
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

## Storylets for [Scene 1A — Michelle’s Disappearance](plot.md#scene-1a--michelles-disappearance)

### SL-1A-A — The House Does Not Look Abandoned

**Source beats:** [1A.1 — The Empty House](plot.md#scene-1a1--the-empty-house), [1A.2 — Michelle’s Last Investigation](plot.md#scene-1a2--michelles-last-investigation)

**Allowed scene:** `1A`

**Available when**
- Kristin is at the house.
- The forced entry, missing work materials, or overturned chair have not yet been meaningfully reconciled.
- The federal patrol has not made the house unsafe.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee, only through her possessions and prior presence
- Michelle’s phone
- Hidden memory card
- Michelle’s missing laptop/work bag as absence evidence

**Dramatic purpose**
- Turn the house from a generic post-disappearance loss into a physical crime scene.
- Let player curiosity accumulate toward the authored conclusion that Michelle was probably taken.

**Possible realizations**
- Kristin notices that the disorder is too localized to fit ordinary looting.
- Handling Michelle’s phone makes the missing laptop and work bag stand out.
- Inspecting the back door changes Kristin’s working theory.
- A failed or hurried search can leave uncertainty while still increasing suspicion.

**Effects**
- May increase `michelle_abduction_suspicion`.
- May establish one or more already-authored evidence facts as noticed.
- May make the memory card easier to discover without making this storylet the only route to it.

**Completion**
- Kristin has enough physical evidence to treat forced removal as a serious possibility.

**Abort**
- Kristin leaves the house after the scene transition becomes valid.
- The federal patrol forces the immediate threat situation to dominate.

**Protected boundary**
- Does not reveal who took Michelle, JANUS, Brandon’s role, the detention network, or the true mechanics of the disappearances.

**Pacing window**
- earliest: `00:00:00`
- target: `00:01:00`
- latest: `00:01:00`

**Pacing impact**
`brief_delay`

---

### SL-1A-B — Michelle Hid Something for Kristin

**Source beats:** [1A.2 — Michelle’s Last Investigation](plot.md#scene-1a2--michelles-last-investigation), [1A.3 — The Interrupted Message](plot.md#scene-1a3--the-interrupted-message)

**Allowed scene:** `1A`

**Available when**
- Kristin remains able to search Michelle’s work area.
- The memory card has not been destroyed or permanently lost.
- Michelle’s investigation is not yet understood.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee through research notes, author drafts, and recordings
- Hidden memory card
- Damaged voice recording

**Dramatic purpose**
- Provide a compact investigative situation in which Michelle’s own preparation gives her best friend and longtime roommate Kristin direction.
- Reinforce Michelle as an active researcher rather than merely a missing objective.

**Possible realizations**
- Kristin discovers the memory card through careful searching.
- The damaged recording and card are encountered in either order.
- Kristin may initially mistrust the material and only later connect it to the forced entry.
- The recording can emotionally sharpen the danger without adding facts beyond Michelle’s authored warning.

**Effects**
- May set `continuity_initiative_known`.
- May establish Kristin's distrust of the emergency broadcasts as part of the warning's emotional force.
- May deepen the context for Michelle's investigation.
- May set `michelle_lead_actionable` once Kristin has a concrete lead she can follow away from the house.

**Completion**
- Kristin possesses or has securely copied the relevant evidence and understands that Michelle expected danger.

**Abort**
- The evidence becomes inaccessible through a player-caused destructive proposal; if it is a required future dependency with no fallback, normal game-break handling applies.

**Protected boundary**
- “Continuity Initiative” may be known as Michelle’s suspicious emergency program, but its actual national purpose remains protected.

**Pacing window**
- earliest: `00:02:00`
- target: `00:02:00`
- latest: `00:02:00`

**Pacing impact**
`brief_delay`

---

### SL-1A-D — The Memory Card Under the Drawer

**Source beats:** [1A.2 — Michelle’s Last Investigation](plot.md#scene-1a2--michelles-last-investigation)

**Allowed scene:** `1A`

**Available when**
- Kristin has recovered Michelle’s damaged warning but not yet her research files.
- Kristin remains able to search Michelle’s work area.
- The memory card has not been destroyed or permanently lost.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee through her research notes
- Hidden memory card

**Dramatic purpose**
- Guarantee that the concrete lead away from the house stays earnable when Kristin reached the damaged recording before the research files.
- Keep the memory card, not the damaged recording, as the thing that names where Michelle was working.

**Possible realizations**
- Kristin finds the card taped beneath the drawer and reads enough of the files to know where Michelle was pointing.
- Kristin recovers only fragments of the research, but they still name the exchange point Michelle used.

**Effects**
- Sets `continuity_initiative_known`.
- Sets `michelle_lead_actionable` once Kristin has a concrete lead she can follow away from the house.
- May set `michelle_abduction_suspicion`.

**Completion**
- Kristin holds or has copied Michelle’s research and knows where to go next.

**Abort**
- The card becomes inaccessible through a player-caused destructive proposal; if it is a required future dependency with no fallback, normal game-break handling applies.

**Protected boundary**
- “Continuity Initiative” may be known as Michelle’s suspicious emergency program, but its actual national purpose remains protected.

**Pacing window**
- earliest: `00:00:00`
- target: `00:02:00`
- latest: `00:05:00`

**Pacing impact**
`brief_delay`

---

### SL-1A-C — The Welfare Check Feels Like a Search

**Source beats:** [1A.4 — The First Threat](plot.md#scene-1a4--the-first-threat)

**Allowed scene:** `1A`

**Available when**
- Kristin is still at or immediately around the house.
- The federal emergency patrol has arrived.
- Michelle's recovered warning has established the immediate danger.
- Kristin has not openly surrendered Michelle’s investigation materials.

**Participants / items**
- Kristin Schweitzer
- Federal emergency patrol officers
- Michelle’s office/work materials
- Hidden memory card, if currently carried or concealed
- Reflective gate tape

**Dramatic purpose**
- Add pressure and force Kristin to interpret official behavior without requiring a scripted confrontation.
- Establish that the search is dangerous before the park sequence.

**Possible realizations**
- Kristin deflects questions while observing what the officers care about.
- An officer’s attention to Michelle’s research becomes more revealing than the stated welfare-check purpose.
- Kristin notices the reflective marker only after the patrol leaves.
- Open defiance may raise pressure without automatically forcing combat.

**Effects**
- May establish `house_marked_for_return` through the marked gate.
- May set `house_marked_for_return`.
- May make the official story less credible.
- May create immediate pressure to leave the house.

**Completion**
- The patrol departs or the interaction otherwise resolves without ending the authored story.

**Abort**
- Kristin is no longer at the house.
- A larger validated game-break consequence supersedes the storylet.

**Protected boundary**
- Patrol officers do not know or disclose the later JANUS bait revelation.

**Pacing window**
- earliest: `00:00:00`
- target: `00:03:00`
- latest: `00:05:00`

**Pacing impact**
`brief_delay`

---

## Storylets for [Scene 1B — The Lead in the Park](plot.md#scene-1b--the-lead-in-the-park)

### SL-1B-A — The Dead Drop Has More Than One Meaning

**Source beats:** [1B.1 — Michelle’s Dead Drop](plot.md#scene-1b1--michelles-dead-drop)

**Allowed scene:** `1B`

**Available when**
- Kristin reaches the park/dead-drop area.
- The dead-drop materials remain recoverable.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee through the dead drop
- Transit access card
- Handwritten number sequence
- Photograph of Michelle with Brandon
- List of earlier disappearance dates

**Dramatic purpose**
- Let the player decide which clue feels most important while all clues still point toward the authored transport/test history.
- Build a quality-based investigative texture rather than a single “correct” inspection.

**Possible realizations**
- The dates lead Kristin to suspect earlier tests.
- The photograph makes the unknown man personally important.
- The transit card and handwritten sequence can be correlated into routing information that points toward a freight/industrial destination, rather than merely suggesting physical infrastructure.
- The number sequence remains unresolved context for later interpretation.

**Effects**
- May reveal evidence of earlier secret tests.
- May set `brandon_face_known`.
- May establish possession of the `transit_card`.
- May make the transport route more compelling to investigate.

**Completion**
- Kristin has recovered the dead-drop materials or enough of them to continue.

**Abort**
- The park situation is overtaken by the pursuit/ambush.

**Protected boundary**
- Brandon is not yet established as trustworthy or as a JANUS developer.

**Pacing window**
- earliest: `00:02:00`
- target: `00:03:15`
- latest: `00:04:30`

**Pacing impact**
`brief_delay`

---

### SL-1B-B — Is Brandon Hunter or Rescuer?

**Source beats:** [1B.2 — The Man Following Him](plot.md#scene-1b2--the-man-following-him), [1B.3 — Brandon’s Warning](plot.md#scene-1b3--brandons-warning)

**Allowed scene:** `1B`

**Available when**
- Brandon is following or has just contacted Kristin.
- Kristin has not yet reached a stable judgment about Brandon.

**Participants / items**
- Kristin Schweitzer, former assessment lead for the U.S. Army with Army intelligence, infrastructure, and operations experience
- Brandon Corfman
- Photograph from the dead drop

**Dramatic purpose**
- Create an early trust problem without forcing the player to accept Brandon immediately.
- Give Brandon a reason to earn provisional credibility through behavior and limited disclosure.

**Possible realizations**
- Kristin confronts Brandon with the photograph.
- Kristin tries to evade him and sees Brandon intervene against the patrol.
- Kristin questions how Brandon knows the missing are alive.
- Brandon refuses full disclosure, preserving suspicion.

**Effects**
- May change `trust_brandon` within an early bounded range.
- May set `brandon_identified`.
- May set `missing_may_be_alive`.
- May set `transport_route_identified` when Brandon can credibly connect Michelle’s transit clue to the removal operation.
- May leave Brandon suspicious even as trust increases.

**Completion**
- Kristin has enough reason to continue with Brandon, even if he remains distrustful.

**Abort**
- Brandon becomes unavailable through a validated destructive branch.
- The park escape forces immediate movement into the next situation.

**Protected boundary**
- Brandon may admit prior Continuity Initiative work, but not yet the full JANUS-development history.

**Pacing window**
- earliest: `00:02:00`
- target: `00:03:15`
- latest: `00:04:30`

**Pacing impact**
`brief_delay`

---

### SL-1B-C — The Gate Code Gives Brandon Away

**Source beats:** [1B.4 — The Park Ambush](plot.md#scene-1b4--the-park-ambush)

**Allowed scene:** `1B`

**Available when**
- A tactical/emergency team has closed on Kristin and Brandon.
- The secured maintenance route is relevant.
- Brandon remains capable of helping.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- Tactical/emergency patrol
- Secured maintenance gate

**Dramatic purpose**
- Turn escape pressure into character evidence.
- Let Brandon solve an immediate problem in a way that creates a larger trust problem.

**Possible realizations**
- Brandon uses specialized codes only after ordinary access fails.
- Kristin notices how practiced Brandon is with the system.
- Brandon minimizes the significance of his access.
- The escape succeeds but the player can press him afterward.

**Effects**
- May increase immediate danger.
- May leave Brandon more suspicious.
- May set `brandon_retains_system_access`.
- May establish `transport_route_identified` when Brandon’s retained access and the escape route make the physical removal route followable.

**Completion**
- Kristin and Brandon escape the immediate park pursuit.

**Abort**
- The maintenance route is no longer relevant or the scene has advanced.

**Protected boundary**
- The access proves deeper involvement, not the exact nature of Brandon’s guilt.

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
- Kristin and Brandon are at the freight terminal/industrial site.
- The underground complex has not yet been fully confirmed.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- Transit access card
- Freight-terminal infrastructure

**Dramatic purpose**
- Give Kristin’s Army infrastructure and operations background real investigative weight.
- Make discovery of the facility emerge from physical contradictions in the site.

**Possible realizations**
- Kristin compares declared abandonment with electrical load, ventilation, and recent infrastructure work.
- The transit card opens access that should not exist at a dead facility.
- Brandon supplies operational context while Kristin supplies infrastructure and operations analysis.

**Effects**
- May set `facility_proof`.
- May reveal evidence of continuing facility activity.
- May establish safe service-level access.
- May set `facility_infiltration_needed` when the main installation cannot be reached safely from the service level.

**Completion**
- Kristin and Brandon have a credible route into the service level.

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
- Kristin can observe the captive-processing area.
- Michelle’s status remains unconfirmed.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- Sedated prisoners
- Dr. Michelle McGehee only as a possible, obscured sighting
- Michelle’s missing-person evidence/identification records, if available

**Dramatic purpose**
- Convert abstract conspiracy evidence into immediate human stakes.
- Intensify Kristin’s rescue impulse while preserving uncertainty about Michelle.

**Possible realizations**
- Kristin matches prisoner identifiers to missing-person records.
- She sees a woman who might be Michelle but cannot obtain certainty.
- Brandon physically or verbally stops an impulsive move into the processing area.
- Kristin can resent Brandon’s restraint even if it is strategically sound.

**Effects**
- May set `captives_confirmed_alive`.
- May make rescue more urgent.
- May change `trust_brandon`.
- May set `michelle_possible_sighting` without confirming Michelle's location.
- May set `facility_infiltration_needed` when an impulsive rescue would endanger or relocate the captives.

**Completion**
- Kristin accepts that living captives are being held here.

**Abort**
- Observation becomes impossible because of security movement or scene progression.

**Protected boundary**
- Michelle’s exact position and resistance network remain protected.

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
- Brandon can access the logistics terminal or equivalent authored records.
- Kristin knows captives are present but does not yet know the operation’s scale.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- Charles Jenkins through recorded conference material
- Rebecca Jenkins through recorded conference material
- Logistics records / recorded conference

**Dramatic purpose**
- Deliver the scene’s scale reversal in stages: regional facility → national network → deliberate political strategy.
- Allow the player to absorb operational and ideological evidence separately.

**Possible realizations**
- Logistics categories reveal why different people were selected.
- Kristin focuses on Michelle’s category before recognizing the national pattern.
- The Charles/Rebecca recording clarifies the reconstruction strategy.
- Brandon’s reactions can create additional suspicion without disclosing his later confession.

**Effects**
- May set `national_detention_network_known`.
- May reveal the selection categories.
- May set `architects_strategy_known`.
- May convey the conspiracy's national scope.
- May establish `facility_infiltration_needed` once Kristin understands that observation or a direct local rescue is insufficient.

**Completion**
- Kristin understands that the disappearances were engineered to remove, classify, and later leverage people at national scale.

**Abort**
- Required records become inaccessible and no declared fallback remains; use dependency/game-break handling rather than silently rewriting the plot.

**Protected boundary**
- JANUS itself, Kristin-as-bait, Brandon’s development role, and Michelle’s resistance network remain protected for Scene 2B.

**Pacing window**
- earliest: `00:04:30`
- target: `00:05:30`
- latest: `00:06:30`

**Pacing impact**
`brief_delay`

---

# Scene 2 — The Infiltration

## Storylets for [Scene 2A — False Identities](plot.md#scene-2a--false-identities)

### SL-2A-A — Brandon Prepared for This Years Ago

**Source beats:** [2A.1 — Brandon’s Hideout](plot.md#scene-2a1--brandons-hideout)

**Allowed scene:** `2A`

**Available when**
- Kristin is inside Brandon’s communications-center hideout.
- Brandon’s history remains only partially trusted.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman, a former software developer now living as an isolated conspiracy researcher estranged from his family
- Servers and salvaged hardware
- Emergency supplies
- Continuity Initiative files

**Dramatic purpose**
- Deepen the contradiction around Brandon: preparedness can read as foresight, obsession, guilt, or all three.
- Support free-form questioning without prematurely resolving his history.

**Possible realizations**
- Kristin examines how long Brandon has tracked the Initiative.
- Brandon describes being discredited after trying to expose it.
- Kristin notices leaked code, internal documents, and old software/security contacts that imply retained technical capability.
- The player may accept the explanation provisionally or become more suspicious.

**Effects**
- May change `trust_brandon`.
- May leave Brandon more suspicious.
- May set `brandon_prepared_before_event`.
- May provide historical context for the Continuity Initiative.

**Completion**
- The hideout has yielded enough context to support planning the infiltration.

**Abort**
- The group leaves for the facility.

**Protected boundary**
- Brandon’s direct work on JANUS remains protected.

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
- Kristin and Brandon have concluded that deliberate deeper infiltration is necessary.
- Kristin and Brandon are preparing entry.
- The cooling/structural-monitoring weakness is known or discoverable from authored facility information.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- False credentials
- Facility structural/cooling information

**Dramatic purpose**
- Make the infiltration cover depend on Kristin’s authentic Army infrastructure and operations background rather than pure deception.
- Give the LLM room to improvise a technically plausible cover story while preserving the authored objective set.

**Possible realizations**
- Kristin identifies which infrastructure concern would justify an unscheduled inspection.
- Brandon shapes that into credential/cover material.
- They discuss how much truth to include in the lie.
- Preparation can improve confidence without guaranteeing entry.

**Effects**
- May set `false_identities_ready`.
- May establish a structural-inspection cover.
- May improve infiltration preparedness.
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
- Kristin and Brandon are passing facility security.
- Their credentials have survived initial checks.
- The unscheduled nature of the inspection is being questioned.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- Facility supervisor
- False credentials

**Dramatic purpose**
- Give Kristin a social/technical obstacle that can be realized through free-form roleplay.
- Preserve dramatic irony: entry can succeed even as Rebecca quietly becomes aware of Brandon.

**Possible realizations**
- Kristin explains progressive-collapse risk in her own words.
- Brandon stays quiet to avoid drawing recognition.
- Overexplaining may raise suspicion while still succeeding.
- The supervisor grants restricted-infrastructure access reluctantly.

**Effects**
- May set `restricted_corridor_access`.
- May change how suspicious the facility is of the pair.
- May set `rebecca_observing_infiltrators` through a pacing/event effect once facial recognition occurs.
- `restricted_corridor_access` is the outgoing scene bridge once the protagonists have moved beyond the outer security layer.

**Completion**
- Kristin and Brandon have moved beyond the main public/security entry layer.

**Abort**
- The cover is fully blown and an alternate declared transition supersedes it.

**Protected boundary**
- Kristin and Brandon do not learn that Rebecca is observing them merely because the state flag exists.

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
- Kristin can access the records archive.
- JANUS has not yet been understood.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- JANUS records

**Dramatic purpose**
- Reveal the selection system through concrete classifications rather than an exposition dump.
- Connect national-scale data collection directly to Michelle and Kristin.

**Possible realizations**
- Kristin searches Michelle’s record first.
- She notices the categories used to predict resistance, influence, vulnerability, and leverage.
- Her own record reveals that being left behind was itself a decision.
- Brandon’s reaction can become part of the evidence.

**Effects**
- May set `janus_known`.
- May set `michelle_selected_for_resistance_influence`.
- May set `kristin_deliberately_left_behind`.
- May sharply intensify the betrayal.

**Completion**
- Kristin understands JANUS as the selection mechanism and recognizes that her own path was modeled.

**Abort**
- Archive access ends before enough material is recovered; another declared source may serve as fallback if the package defines one.

**Protected boundary**
- The exact reason Charles expected Kristin to expose Brandon may emerge only as supported by the authored records; no new hidden motives are invented.

**Pacing window**
- earliest: `00:08:30`
- target: `00:09:30`
- latest: `00:10:30`

**Pacing impact**
`brief_delay`

---

### SL-2B-B — Brandon’s Name Is in the Build Records

**Source beats:** [2B.2 — Kristin Was Bait](plot.md#scene-2b2--kristin-was-bait), [2B.3 — Brandon’s Role](plot.md#scene-2b3--brandons-role)

**Allowed scene:** `2B`

**Available when**
- JANUS has been credibly identified in the archive evidence.
- JANUS records are accessible.
- Brandon’s development role has not yet been confronted.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- JANUS development records

**Dramatic purpose**
- Turn accumulated distrust into a direct character confrontation.
- Preserve ambiguity between culpability for creating the system and opposition to its later use.

**Possible realizations**
- Kristin confronts Brandon immediately.
- She withholds the discovery briefly and observes Brandon first.
- Brandon admits writing AI software for JANUS to identify threats.
- Kristin challenges whether Brandon is still manipulating her.

**Effects**
- May set `brandon_janus_role_known`.
- May set `brandon_claimed_reform_motive`.
- May set `janus_evidence` when the development records are preserved/authenticated as evidence.
- May substantially change `trust_brandon`.
- May leave Brandon more or less suspicious depending on accepted interaction facts.

**Completion**
- Brandon’s original role and claimed break with Charles are explicit between him and Kristin.

**Abort**
- Brandon is absent/unavailable and the confrontation must be deferred by declared package logic.

**Protected boundary**
- Brandon’s later sacrifice/confession is not foreshadowed as guaranteed.

**Pacing window**
- earliest: `00:08:30`
- target: `00:09:30`
- latest: `00:10:30`

**Pacing impact**
`brief_delay`

---

### SL-2B-C — Michelle Is Already Sabotaging the System

**Source beats:** [2B.4 — Michelle’s Hidden Resistance](plot.md#scene-2b4--michelles-hidden-resistance)

**Allowed scene:** `2B`

**Available when**
- JANUS has been credibly identified in the archive evidence.
- Kristin can inspect corrupted prisoner/maintenance records.
- Michelle’s active resistance is not yet known.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- Dr. Michelle McGehee through coded records
- Corrupted prisoner files / maintenance reports

**Dramatic purpose**
- Reverse the rescue framing: Michelle is an active agent affecting the facility from inside.
- Give Kristin renewed direction after the JANUS/Brandon betrayal.

**Possible realizations**
- Kristin recognizes phrases Michelle used in private notes.
- A pattern of delayed transfers and altered classifications becomes visible.
- Brandon sees operational sabotage; Kristin sees Michelle’s signature.
- The player may infer organization before knowing its full scale.

**Effects**
- May set `michelle_resistance_known`.
- May renew hope.
- May set `prisoner_records_corrupted`.
- May preserve enough corrupted JANUS/prisoner material to establish `janus_evidence` while also pointing toward Michelle’s resistance.

**Completion**
- Kristin knows Michelle is alive enough to act or has left recent operational evidence strongly supporting that conclusion.

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

### SL-2C-A — Rebecca Offers Brandon a Different Conspiracy

**Source beats:** [2C.1 — Rebecca’s Offer](plot.md#scene-2c1--rebeccas-offer)

**Allowed scene:** `2C`

**Available when**
- Rebecca has identified Brandon.
- Brandon remains capable of private contact.
- Kristin may know of the contact only if the interaction makes that knowledge available.

**Participants / items**
- Brandon Corfman
- Rebecca Jenkins
- Kristin Schweitzer, only when physically/informationally justified

**Dramatic purpose**
- Show fracture inside the antagonist coalition without turning Rebecca into an ally.
- Pressure Brandon’s credibility after his JANUS admission.

**Possible realizations**
- Rebecca frames Charles as the immediate danger.
- She offers Michelle’s release in exchange for helping her seize control.
- Brandon appears to consider the offer to gain executive access.
- Kristin can misread Brandon’s performance if he lacks context.

**Effects**
- May set `rebecca_offer_active`.
- May set `antagonist_split_known`.
- May change `trust_brandon` only if Kristin has legitimate knowledge of the exchange.
- May open a route toward executive-level access.

**Completion**
- Brandon has accepted, rejected, or strategically exploited the offer enough for the scene to move on.

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
- Kristin Schweitzer
- Brandon Corfman
- Charles Jenkins through orders/broadcast preparation
- Facility records/alerts where locally available

**Dramatic purpose**
- Add deterministic time/pressure to a scene that could otherwise become leisurely.
- Make delay materially dangerous without scripting Kristin’s response.

**Possible realizations**
- An internal order reveals accelerated transfers.
- Facility movement patterns suddenly change.
- Broadcast-preparation traffic exposes the deadline indirectly.
- Kristin and Brandon disagree about what the remaining time permits.

**Effects**
- Starts or advances `purge_clock_started`.
- May establish that Charles's broadcast is imminent.
- May reduce safe infiltration options as pressure rises.
- May fire scene pacing complications at declared thresholds.

**Completion**
- The pressure event remains in force until the scene transition; this storylet completes once the deadline is understood.

**Abort**
- None while the authored purge order is active, though the storylet itself does not have to be selected as a discrete encounter.

**Protected boundary**
- Does not reveal the later exact broadcast-system solution before Michelle provides it.

**Pacing window**
- earliest: `00:10:30`
- target: `00:11:45`
- latest: `00:13:00`

**Pacing impact**
`brief_delay`

---

### SL-2C-C — The False Choice Breaks Open

**Source beats:** [2C.3 — Evidence or Rescue](plot.md#scene-2c3--evidence-or-rescue), [2C.4 — Michelle Changes the Choice](plot.md#scene-2c4--michelle-changes-the-choice)

**Allowed scene:** `2C`

**Available when**
- The purge/transfer clock is active and understood.
- Enough evidence exists to expose the conspiracy.
- Rescue remains possible but dangerous.
- Michelle’s coded maintenance channel can reach Kristin/Brandon.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- Dr. Michelle McGehee through coded communication
- Copied conspiracy evidence
- Maintenance network

**Dramatic purpose**
- Realize the central crisis as a character disagreement, then convert it into the authored combined mission.
- Keep the player free to argue, hesitate, or explore while pacing prevents indefinite stalling.

**Possible realizations**
- Brandon argues for immediate transmission.
- Kristin refuses to abandon the captives.
- Their conflict can become personal because of Brandon’s earlier guilt.
- Michelle’s coded message introduces the manual broadcast/door-opening solution.

**Effects**
- May set `evidence_ready_to_transmit`.
- May set `archive_crisis_understood`.
- May set `combined_broadcast_rescue_plan_known`.
- May set `rebecca_office_required_for_broadcast`.
- Establishes `combined_broadcast_rescue_plan_known`, the scene bridge toward reaching Michelle and executing the combined mission.

**Completion**
- Kristin and Brandon understand that the next objective combines rescue and exposure.

**Abort**
- The player causes a validated non-canonical branch that makes the combined plan impossible and chooses to proceed.

**Protected boundary**
- Exact events of the uprising, Brandon’s sacrifice, facility destruction, and final broadcast outcome remain protected.

**Pacing window**
- earliest: `00:10:30`
- target: `00:11:45`
- latest: `00:13:00`

**Pacing impact**
`brief_delay`

---

# Scene 3 — The Captives

## Storylets for [Scene 3A — Reaching Michelle](plot.md#scene-3a--reaching-michelle)

### SL-3A-A — The Rescue Target Is Running an Uprising

**Source beats:** [3A.1 — The Detention Block](plot.md#scene-3a1--the-detention-block)

**Allowed scene:** `3A`

**Available when**
- Kristin reaches Michelle’s detention sector.
- Michelle is active and the purge countdown is running.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee
- Brandon Corfman
- Prisoners
- Sympathetic facility workers
- Stolen radios

**Dramatic purpose**
- Pay off Michelle’s agency with an in-person reversal of Kristin’s rescue expectations.
- Reframe the immediate goal from “get Michelle out” to “help the organized captives expose the whole network.”

**Possible realizations**
- The reunion is interrupted by Michelle directing others.
- Kristin tries to prioritize Michelle; she redirects her to the national stakes.
- Prisoners treat Michelle as an organizer rather than a victim.
- The reunion can establish that Michelle is ready to launch coordinated disturbances, but the canonical launch waits until the experiment stakes and expiring-code deadline have been established (or equivalent validated free-text realizations occur).
- Brandon’s arrival may be met with distrust because of his history.

**Effects**
- May set `michelle_reached`.
- May set `uprising_prepared`.
- May establish that the uprising is prepared; the canonical launch is gated later in the scene.
- May establish that national facility locations are required for the broadcast.
- May change relationship/trust facts consistent with the reunion.

**Completion**
- Kristin accepts Michelle as an operational partner and understands the larger rescue requirement.

**Abort**
- Scene pressure escalates directly into the uprising before the interaction fully resolves.

**Protected boundary**
- The final outcome of the broadcast and Brandon’s fate remain unknown.

**Pacing window**
- earliest: `00:13:00`
- target: `00:14:00`
- latest: `00:15:00`

**Pacing impact**
`brief_delay`

---

### SL-3A-B — The “Rescued” Captives Were Being Prepared

**Source beats:** [3A.2 — The Experiments](plot.md#scene-3a2--the-experiments), [3A.3 — The Unexpected Prisoner](plot.md#scene-3a3--the-unexpected-prisoner)

**Allowed scene:** `3A`

**Available when**
- Kristin has reached Michelle and can move with her resistance network.
- Kristin and Michelle can pass through or access evidence from the medical level.
- The experiment program is not yet fully understood.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee
- Prisoners, including the imprisoned senior official
- Medical/behavioral experiment records or equipment already present in the authored setting
- Emergency military override authorization codes

**Dramatic purpose**
- Raise the moral and political stakes of Charles’s planned broadcast.
- Show that simply releasing selected prisoners could strengthen the conspiracy.
- Turn one prisoner into a time-sensitive strategic resource without making the NPC a permanent companion.

**Possible realizations**
- Michelle explains what she has observed while Kristin sees corroborating evidence, and the framed official hands over his expiring authorization.
- A conditioned “rescue” plan becomes visible through records or treatment setup while the codes are secured or copied.
- Kristin recognizes that public testimony itself has been engineered.

**Effects**
- May set `behavioral_experiments_known`.
- May set `conditioned_release_plan_known`.
- May set `military_override_codes_available` and `charles_framed_officials_known`.
- May make the broadcast evidence more compelling.
- May increase danger or moral urgency.

**Completion**
- Kristin understands why exposing the experiments must be part of the broadcast evidence.

**Abort**
- Immediate security pressure makes the medical level inaccessible.

**Protected boundary**
- Do not invent successful mind control beyond the specific authored methods and goals.
- The codes do not automatically solve the facility fight or national conspiracy.

**Pacing window**
- earliest: `00:13:00`
- target: `00:14:00`
- latest: `00:15:00`

**Pacing impact**
`brief_delay`

---

### SL-3A-C — The Uprising Begins

**Source beats:** [3A.4 — The Uprising Begins](plot.md#scene-3a4--the-uprising-begins)

**Allowed scene:** `3A`

**Available when**
- Kristin has reached Michelle.
- Michelle’s uprising preparation is in place.
- Charles’s planned authority activation remains pending.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee
- Brandon Corfman
- Organized prisoners across the detention sectors

**Dramatic purpose**
- Convert the expiring authorization deadline into forward motion toward the command levels.
- Commit the resistance to the coordinated assault that carries the story into Scene 3B.

**Possible realizations**
- Michelle triggers coordinated disturbances and the freed checkpoints become a route upward.
- The expiring authorization window itself forces the resistance to launch while the codes retain value.

**Effects**
- Sets `detention_uprising_started`.
- May advance `override_codes_deadline_known` when the deadline forces the launch.
- Helps the Scene 3A → 3B transition under declared package rules.

**Completion**
- The uprising is underway and the group is committed to fighting toward the command and broadcast levels.

**Abort**
- Immediate security lockdown pins the resistance before the disturbances can begin.

**Protected boundary**
- The uprising does not by itself defeat JANUS, seize the broadcast, or resolve the national conspiracy.

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
- Kristin can affect facility infrastructure.
- The group is trying to reach Rebecca’s office/broadcast controls.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee
- Brandon Corfman
- JANUS as system
- Facility doors, cameras, power, structural alarms, and unused corridors

**Dramatic purpose**
- Make Kristin’s Army operations mindset the counter to predictive security.
- Encourage creative free-form disruption rather than one prescribed puzzle solution.

**Possible realizations**
- Kristin creates unrelated infrastructure alarms.
- Power cuts or flooding make the group’s true route less legible.
- The group intentionally chooses tactically irrational movement.
- A failed disruption can still raise pressure while teaching what JANUS is using.

**Effects**
- May force `human_security_control` when enough conflicting emergencies overload JANUS.
- May increase local infrastructure pressure as a cost.

**Completion**
- JANUS can no longer reliably predict the group’s route and human operators take over.

**Abort**
- JANUS is already disconnected or the group has reached Rebecca’s office.

**Protected boundary**
- The disruption does not itself disconnect the external relay; that remains Brandon’s later task.

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
- Kristin and Michelle have reached Rebecca’s office.
- Rebecca is present and has not yet escaped.
- Charles has not fully destroyed the local situation.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee
- Rebecca Jenkins
- Charles Jenkins through remote communication
- Detention-site location information available to Rebecca

**Dramatic purpose**
- Put Rebecca’s self-preservation against Michelle’s evidence of her direct responsibility.
- Allow Charles’s betrayal to collapse Rebecca’s bargaining position in real time.

**Possible realizations**
- Rebecca claims surrender is the only way to save the failing facility.
- Michelle confronts her with approvals for experiments.
- Rebecca offers all detention-site locations.
- Charles remotely strips Rebecca of control and locks down the office.

**Effects**
- May set `rebecca_experiment_approval_confronted`.
- May set `detention_locations_offer_known`.
- May set `charles_abandoned_rebecca`.
- May set `facility_destruction_threat`.
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

### SL-3B-C — Brandon Holds the Relay Open

**Source beats:** [3B.4 — Brandon’s Sacrifice](plot.md#scene-3b4--brandons-sacrifice)

**Allowed scene:** `3B`

**Available when**
- JANUS predictive control has been defeated.
- Charles has stripped Rebecca of control and the protagonists have secured exact detention-site locations.
- The broadcast is ready except for Charles’s control of the external communications relay.
- Brandon is still capable of reaching/operating the relay chamber.

**Participants / items**
- Brandon Corfman
- Kristin Schweitzer and Dr. Michelle McGehee through communication where justified
- External communications relay
- Brandon’s confession recording/transmission

**Dramatic purpose**
- Resolve Brandon’s guilt arc through an action that is both operationally necessary and personally accountable.
- Create the final condition for the national transmission without scripting Kristin’s emotional response.

**Possible realizations**
- Brandon chooses the relay because his old access makes him the viable operator.
- He transmits a confession that authenticates Michelle’s evidence.
- Security pressure and electrical danger make continued relay control costly.
- Kristin or Michelle may argue against him, but the authored situation keeps the relay problem concrete.

**Effects**
- May set `relay_open`.
- May set `brandon_confession_available`.
- May set `relay_open`.
- May set `broadcast_started` once Michelle/Kristin activate the transmission through the opened relay.
- May critically worsen `brandon_health/status` only through validated effects consistent with the authored sacrifice.
- `broadcast_started` is the Scene 3B → 3C bridge.

**Completion**
- The relay remains open long enough for Michelle and Kristin to begin the broadcast.

**Abort**
- A declared fallback solves the relay dependency instead; otherwise incapacitating Brandon beforehand may be game-breaking and must be handled explicitly.

**Protected boundary**
- Brandon’s final survival/fate remains unresolved until the authored escape/collapse outcome permits it.

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
- Michelle has sufficient evidence to transmit.
- Charles still has remote communications capability.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee
- Charles Jenkins remotely
- Broadcast evidence
- Brandon’s confession, if available
- Live facility feeds where available

**Dramatic purpose**
- Make exposure a contest over credibility rather than a simple upload-success event.
- Let accumulated evidence qualities determine how convincingly Michelle can answer Charles.

**Possible realizations**
- Michelle presents captives, JANUS records, facility locations, experiment evidence, and planning records.
- Charles calls the group terrorists.
- Michelle counters with independently verifiable facility information or live images.
- Brandon’s confession can authenticate evidence without being the only possible credibility support if fallbacks are declared.

**Effects**
- May make the public aware of the conspiracy.
- May set `national_facility_locations_broadcast`.
- May show Charles publicly denying the evidence.
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
- Kristin Schweitzer
- Dr. Michelle McGehee
- Rebecca Jenkins
- Portable archive of conspirator identities and prisoner locations

**Dramatic purpose**
- Turn a chase/capture into an information-custody problem.
- Prevent “destroy the bad thing” from being an uncomplicated solution because the same archive can save captives.

**Possible realizations**
- Kristin stops Rebecca and learns what the archive contains.
- Rebecca exploits the mixed contents to bargain.
- Michelle argues for duplication/distribution rather than destruction or sole custody.
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
- Kristin can still affect structural/power systems.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee
- Brandon Corfman only as allowed by his current status/fate
- Escaping prisoners
- Facility emergency supports / power systems
- Surface gates and maintenance tunnels

**Dramatic purpose**
- Give Kristin one final infrastructure-and-operations problem while Michelle leads the human evacuation.
- Move the climax into falling action without removing danger too early.

**Possible realizations**
- Kristin redirects power to keep some sections supported.
- Michelle organizes movement through maintenance tunnels.
- The group must accept that not every section can be saved.
- Brandon’s relay action contributes to the surface gates opening if his authored state permits it.

**Effects**
- May intensify the facility's collapse.
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
- Kristin Schweitzer
- Dr. Michelle McGehee
- Public reports from other detention sites

**Dramatic purpose**
- Show distributed consequences without pulling unrelated off-scene NPC private state into the prompt.

**Possible realizations**
- Reports indicate some facilities surrender while others resist.
- Families and communities begin independent rescue efforts.
- Official agencies issue conflicting denials.
- Kristin and Michelle understand that Los Angeles was a victory, not an ending.

**Effects**
- May set `national_network_fragmenting`.
- May set `community_rescue_efforts_begun`.
- May establish Kristin/Michelle’s next-direction facts.

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
- Kristin Schweitzer
- Dr. Michelle McGehee
- Partially recovered JANUS file

**Dramatic purpose**
- Deliver the final sequel-scale reversal only after the main personal and national victory has landed.

**Possible realizations**
- Michelle or Kristin notices the operation label “Phase One.”
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
| [1A](plot.md#scene-1a--michelles-disappearance) | `SL-1A-A` … `SL-1A-D` | Crime-scene inference, Michelle’s evidence, first authority pressure |
| [1B](plot.md#scene-1b--the-lead-in-the-park) | `SL-1B-A` … `SL-1B-C` | Dead-drop clues, Brandon trust, pursuit |
| [1C](plot.md#scene-1c--discovery-of-the-facility) | `SL-1C-A` … `SL-1C-C` | Facility discovery, living captives, national scale |
| [2A](plot.md#scene-2a--false-identities) | `SL-2A-A` … `SL-2A-C` | Brandon context, infiltration preparation, entry complication |
| [2B](plot.md#scene-2b--evidence-and-betrayal) | `SL-2B-A` … `SL-2B-C` | JANUS, Kristin-as-bait, Brandon’s role, Michelle’s resistance |
| [2C](plot.md#scene-2c--the-trap-closes) | `SL-2C-A` … `SL-2C-C` | Rebecca’s offer, purge pressure, crisis reframing |
| [3A](plot.md#scene-3a--reaching-michelle) | `SL-3A-A` … `SL-3A-C` | Reunion reversal, experiments, deadline/override |
| [3B](plot.md#scene-3b--the-battle-for-the-broadcast) | `SL-3B-A` … `SL-3B-C` | Defeat JANUS, confront Rebecca, open relay |
| [3C](plot.md#scene-3c--exposure-and-escape) | `SL-3C-A` … `SL-3C-E` | Broadcast credibility, archive custody, collapse, epilogue |

## Canonical scene beats vs. optional storylets

The compiled story package may declare a **canonical bridge event** for a scene transition. A canonical bridge event is story progression that must eventually become true for the single authored scene chain to continue, but **no storylet is itself mandatory**. Storylets are optional realization guidance: free-text player action, NPC reaction, or pacing pressure may realize the same validated fact operation without selecting a storylet.

Bridge facts should describe why the current scene is complete and the next scene is now necessary; they should not pre-assert a revelation whose dramatic payoff belongs to the next scene. Pacing events should create observable pressure or consequences rather than unearned player knowledge.

Current bridge facts are: `michelle_lead_actionable`, `transport_route_departure_ready`, `facility_infiltration_needed`, `restricted_corridor_access`, `archive_crisis_understood`, `combined_broadcast_rescue_plan_known`, `command_levels_assault_underway`, and `broadcast_started`.

## Authoring notes

1. **Optional means optional.** A scene must remain satisfiable even if none of its ordinary storylets are selected. Canonical bridge events may be required, but storylets only provide optional realization guidance for them.
2. **No fixed action vocabulary.** “Possible realizations” are prompt guidance only. The LLM interprets arbitrary player roleplay and proposes semantic effects.
3. **Scene-local context first.** Only participating/present/relevant entities should enter the default turn context. Off-scene references should add only public/currently-known facts.
4. **Pressure carries pacing.** `SL-2C-B`, `SL-3A-C`, and the collapse/broadcast situations are natural places for deterministic pressure. Pressure may force circumstances to worsen or a canonical event to become urgent, but it must not grant Kristin unexplained knowledge.
5. **Required dependencies stay explicit elsewhere.** The memory card, Brandon, broadcast access, relay access, archive, or any substitutes/fallbacks should be declared in the package dependency model; this file does not silently make them mandatory.
6. **Protected revelations are monotonic.** Optional content can foreshadow later facts, but it must not make a protected revelation true/known before the original scene permits it.
7. **Effects are bounded proposals.** The exact fact paths, numeric pressure ranges, trigger predicates, and transition priorities belong in validated package data rather than being inferred from prose here.

## Design-reference rationale

This pool follows the architecture summarized in `storylet.md`:

- Façade-style organization keeps higher-level dramatic progression separate from lower-level reactive realization.
- Failbetter-style quality-based narrative makes small storylets available from mutable state and lets their effects feed later availability.
- The “Grandfather Clock” pattern is especially close to the intended pacing model: fast local activity can build progress while the major narrative chain advances at a deliberately controlled rate.
- Full causal planning is not treated as the runtime authoring model; deterministic dependency/future-satisfiability checks protect the authored scene spine instead.
