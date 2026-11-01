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

**Source beats:** [1A.1 — Michelle Is Gone](plot.md#scene-1a1--michelle-is-gone), [1A.2 — Michelle’s Last Investigation](plot.md#scene-1a2--michelles-last-investigation)

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
- Michelle’s missing tablet/work bag as absence evidence

**Dramatic purpose**
- Turn the house from a generic post-disappearance loss into a physical crime scene.
- Let player curiosity accumulate toward the authored conclusion that Michelle was probably taken.

**Possible realizations**
- Kristin notices that the disorder is too localized to fit ordinary looting.
- Handling Michelle’s phone makes the missing tablet and work bag stand out.
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
- earliest: `turn 0`
- target: `turn 2`
- latest: `turn 3`

---

### SL-1A-E — The KMS Mark

**Source beats:** [1A.1 — Michelle Is Gone](plot.md#scene-1a1--michelle-is-gone)

**Allowed scene:** `1A`

**Available when**
- Kristin does not yet have Michelle's memory card.

**Participants / items**
- Kristin Schweitzer
- Michelle's workstation drawer carved KMS
- Hidden memory card

**Dramatic purpose**
- Let the KMS mark reward a careful search of Michelle's workstation before the patrol closes in.

**Possible realizations**
- Kristin searches beneath the KMS drawer, finds Michelle's hidden memory card, and keeps it with her.
- While a patrol officer is in the house, Kristin finds the card in plain sight of the officer, who challenges her.

**Effects**
- May set `memory_card_recovered` when Kristin finds the card.
- May set `card_challenged` and `kristin_marked_by_patrol` when an officer sees Kristin take the card.
- The officer then demands the card (`officer_demanded_card`), and the departure line acknowledges the demand; custody remains the player's choice.

**Completion**
- Kristin has Michelle's memory card.

**Abort**
- Kristin leaves scene 1A.

**Protected boundary**
- Does not reveal who took Michelle, JANUS, Brandon’s role, the detention network, or the true mechanics of the disappearances.

**Pacing window**
- earliest: `turn 1`
- target: `turn 3`
- latest: `turn 12`

---

### SL-1A-F — The Drawer Points to the Gap

**Source beats:** [1A.1 — Michelle Is Gone](plot.md#scene-1a1--michelle-is-gone)

**Allowed scene:** `1A`

**Available when**
- Kristin does not yet have Michelle's memory card.

**Participants / items**
- Kristin Schweitzer
- Michelle's workstation drawer carved KMS
- Hidden memory card

**Dramatic purpose**
- Give opening the drawer or examining the initials a short authored reply.
- Point Kristin back toward the thin gap without recovering the memory card.

**Possible realizations**
- Kristin pulls or opens the drawer and notices the thin gap beneath its lower edge.
- Kristin examines the carved initials and notices the thin gap beneath the drawer.

**Effects**
- Sets `drawer_gap_pointed_out`.
- Does not recover the memory card.

**Completion**
- Kristin has been pointed toward the thin gap beneath the drawer.

**Abort**
- Kristin leaves scene 1A.

**Protected boundary**
- Does not reveal who took Michelle, JANUS, Brandon’s role, the detention network, or the true mechanics of the disappearances.

**Pacing window**
- earliest: `turn 0`
- target: `turn 3`
- latest: `turn 12`

**Non-coercion note:** Offer as a consequence of free-text investigation. Do not present it as a choice or required command; equivalent drawer searches may validate the same operation.

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
- Provide a compact investigative situation in which Michelle’s own preparation gives her best friend Kristin direction.
- Reinforce Michelle as an active researcher rather than merely a missing objective.

**Possible realizations**
- Kristin discovers and secures the memory card through careful searching before reading its files.
- Kristin then reads the damaged recording and card files in either authored order, but the recording is never heard before the card is secured.
- Kristin may initially mistrust the material and only later connect it to the forced entry.
- The recording can emotionally sharpen the danger without adding facts beyond Michelle’s authored warning.

**Effects**
- May set `memory_card_recovered` when Kristin secures the card.
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
- earliest: `turn 2`
- target: `turn 5`
- latest: `turn 6`

---

### SL-1A-D — The Rest of Michelle's Files

**Source beats:** [1A.2 — Michelle’s Last Investigation](plot.md#scene-1a2--michelles-last-investigation)

**Allowed scene:** `1A`

**Available when**
- Kristin has recovered Michelle’s damaged warning but not yet read all of her research files.
- Kristin is already carrying the recovered memory card.
- Kristin remains able to search Michelle’s work area.
- The memory card has not been destroyed or permanently lost.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee through her research notes
- Recovered memory card in Kristin's custody

**Dramatic purpose**
- Guarantee that the concrete lead away from the house stays earnable when Kristin reads the damaged recording before the remaining research files.
- Keep the already-recovered memory card's remaining files, not the damaged recording alone, as the thing that names where Michelle was working.

**Possible realizations**
- Kristin reads enough of the remaining files on the card she is carrying to know where Michelle was pointing.
- Kristin reads only fragments of the research on the card she is carrying, but they still name the exchange point Michelle used.

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
- earliest: `turn 0`
- target: `turn 8`
- latest: `turn 9`

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
- earliest: `turn 4`
- target: `turn 6`
- latest: `turn 7`

---

## Storylets for [Scene 1B — The Lead in the Park](plot.md#scene-1b--the-lead-in-the-park)

### SL-1B-D — Beneath the Park Bench

**Source beats:** [1B.1 — Michelle’s Dead Drop](plot.md#scene-1b1--michelles-dead-drop)

**Allowed scene:** `1B`

**Available when**
- Kristin has not recovered the clues under the park bench.

**Participants / items**
- Kristin Schweitzer
- Park bench
- Transit token
- Handwritten number sequence
- Michelle's photograph

**Dramatic purpose**
- Reward an underside search with the clues Michelle left for Kristin.

**Possible realizations**
- Kristin searches beneath the bench, retrieves all three clues, and keeps them with her.

**Effects**
- Sets `bench_clues_recovered`.

**Completion**
- Kristin has recovered the three clues.

**Abort**
- Kristin leaves scene 1B.

**Protected boundary**
- Finding the clues does not identify the route or the photographed man.
- It does not identify Brandon, establish trust, or reveal the fate of the missing.

**Pacing window**
- earliest: `turn 0`
- target: `turn 2`
- latest: `turn 12`

---

### SL-1B-A — The Dead Drop Has More Than One Meaning

**Source beats:** [1B.1 — Michelle’s Dead Drop](plot.md#scene-1b1--michelles-dead-drop)

**Allowed scene:** `1B`

**Available when**
- Kristin has recovered the three clues beneath the park bench.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee through the dead drop
- Transit token
- Handwritten number sequence
- Photograph of Michelle with Brandon

**Dramatic purpose**
- Let the player decide which clue feels most important while all clues still point toward the authored transport/test history.
- Build a quality-based investigative texture rather than a single “correct” inspection.

**Possible realizations**
- The dates lead Kristin to suspect earlier tests.
- The photograph makes the unknown man personally important.
- The transit token and handwritten sequence can be correlated into routing information that points toward a freight/industrial destination, rather than merely suggesting physical infrastructure.
- The number sequence remains unresolved context for later interpretation.

**Effects**
- May reveal evidence of earlier secret tests.
- May set `brandon_face_known`.
- May make the transport route more compelling to investigate.

**Completion**
- Kristin has identified the transport route or recognized the man in the photograph.

**Abort**
- The park situation is overtaken by the pursuit/ambush.

**Protected boundary**
- Brandon is not yet established as trustworthy or as a JANUS developer.

**Pacing window**
- earliest: `turn 0`
- target: `turn 2`
- latest: `turn 3`

---

### SL-1B-E — The Bench Points Beneath

**Source beats:** [1B.1 — Michelle’s Dead Drop](plot.md#scene-1b1--michelles-dead-drop)

**Allowed scene:** `1B`

**Available when**
- Kristin has not recovered the clues under the park bench.

**Participants / items**
- Kristin Schweitzer
- Park bench

**Dramatic purpose**
- Give a plain look at the bench a short authored reply.
- Point Kristin toward the space beneath the bench without recovering the clues.

**Possible realizations**
- Kristin looks the bench over and notices the shadowed space beneath it.

**Effects**
- Sets `bench_underside_pointed_out`.
- Does not recover the clues.

**Completion**
- Kristin has been pointed toward the space beneath the park bench.

**Abort**
- Kristin leaves scene 1B.

**Protected boundary**
- Does not name or reveal what is beneath the bench, and does not identify Brandon, trust, or the fate of the missing.

**Pacing window**
- earliest: `turn 0`
- target: `turn 3`
- latest: `turn 12`

**Non-coercion note:** Offer as a consequence of free-text investigation. Do not present it as a choice or required command; equivalent careful looks at the bench may validate the same operation.

---

### SL-1B-B — Is Brandon Hunter or Rescuer?

**Source beats:** [1B.2 — The Man Following Her](plot.md#scene-1b2--the-man-following-her), [1B.3 — Brandon’s Warning](plot.md#scene-1b3--brandons-warning)

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
- earliest: `turn 0`
- target: `turn 6`
- latest: `turn 7`

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
- Secured service gate

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
- earliest: `turn 0`
- target: `turn 10`
- latest: `turn 11`

---

## Storylets for [Scene 1C — Discovery of the Facility](plot.md#scene-1c--discovery-of-the-facility)

### SL-1C-A — The “Abandoned” Terminal Is Working Too Hard

**Source beats:** [1C.1 — Following the Transport Route](plot.md#scene-1c1--following-the-transport-route)

**Allowed scene:** `1C`

**Available when**
- Kristin and Brandon are at the freight terminal/industrial site.
- The underground complex has not yet been fully confirmed.
- The transfer window remains open.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- Transit token
- Freight-terminal infrastructure

**Dramatic purpose**
- Give Kristin’s Army infrastructure and operations background real investigative weight.
- Make discovery of the facility emerge from physical contradictions in the site.

**Possible realizations**
- Kristin compares declared abandonment with electrical load, ventilation, and recent infrastructure work.
- Brandon supplies operational context while Kristin supplies infrastructure and operations analysis.

**Effects**
- May set `facility_proof`.
- May reveal evidence of continuing facility activity.

**Completion**
- Kristin and Brandon have proof that the terminal is active.

**Abort**
- The facility becomes openly alerted and the subtle-entry situation ends.

**Protected boundary**
- Does not reveal the full national network before the logistics evidence is reached.

**Pacing window**
- earliest: `turn 0`
- target: `turn 2`
- latest: `turn 3`

---

### SL-1C-B — One Face in the Processing Line

**Source beats:** [1C.2 — Proof of the Captives](plot.md#scene-1c2--proof-of-the-captives)

**Allowed scene:** `1C`

**Available when**
- The active underground facility has been credibly confirmed.
- Kristin can observe the captive-processing area.
- Michelle’s status remains unconfirmed.
- The transfer window remains open.

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
- Kristin studies the prisoners through the observation shaft.
- She watches a woman who might be Michelle but cannot obtain certainty.
- Brandon offers copying the prisoner numbers for stronger proof.
- Brandon offers help with the transfer route at the cost of the full number set.

**Effects**
- May set `captives_confirmed_alive`.
- May make rescue more urgent.
- May set `michelle_possible_sighting` without confirming Michelle's location.

**Completion**
- Kristin accepts that living captives are being held here.

**Abort**
- Observation becomes impossible because of security movement or scene progression.

**Protected boundary**
- Michelle’s exact position and resistance network remain protected.

**Pacing window**
- earliest: `turn 0`
- target: `turn 2`
- latest: `turn 3`

---

### SL-1C-C — The Transfer Window

**Source beats:** [1C.2 — Proof of the Captives](plot.md#scene-1c2--proof-of-the-captives)

**Allowed scene:** `1C`

**Available when**
- The active facility and living captives have been credibly confirmed.
- Kristin knows captives are present.
- The transfer window remains open.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- Prisoner number record
- Service entrance

**Dramatic purpose**
- Force a meaningful choice while the transfer window remains open.

**Possible realizations**
- Kristin copies the visible prisoner numbers and matches them to missing-person records.
- Kristin asks Brandon about the transfer route or has him open the service entrance with the transit token.

**Effects**
- The copy outcome establishes `processing_numbers_copied` and `facility_infiltration_needed`.
- The route outcome establishes `service_level_access_known`, `evidence_gap_processing_numbers`, `facility_infiltration_needed`, and `trust_brandon`.

**Completion**
- Kristin has chosen proof or a route into the facility.

**Abort**
- The transfer window closes.

**Protected boundary**
- The national network and the architects’ strategy remain for a later scene.

**Pacing window**
- earliest: `turn 0`
- target: `turn 3`
- latest: `turn 4`

---

### SL-1C-D — The Sweep Closes In

**Source beats:** [1C.2 — Proof of the Captives](plot.md#scene-1c2--proof-of-the-captives)

**Allowed scene:** `1C`

**Available when**
- The transfer window has been missed.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- Service entrance

**Dramatic purpose**
- Turn the missed window into a costly final chance to enter.

**Possible realizations**
- Brandon invites Kristin to follow him through the service entrance. The offer alone grants nothing.
- Brandon leads Kristin through the service entrance while the sweep closes in.

**Effects**
- Reuses the secure-route outcome.
- Establishes `terminal_sweep_closing` as the recovery cost.

**Completion**
- Kristin reaches the next scene.

**Abort**
- Kristin leaves the scene.

**Protected boundary**
- The national network and the architects’ strategy remain undisclosed.

**Pacing window**
- earliest: `turn 0`
- target: `turn 6`
- latest: `turn 10`

---

# Scene 2 — The Infiltration

## Storylets for [Scene 2A — False Identities](plot.md#scene-2a--false-identities)

### SL-2A-C — The Supervisor Needs a Reason

**Source beats:** [2A.3 — Entering the Facility](plot.md#scene-2a3--entering-the-facility), [2A.4 — The First Complication](plot.md#scene-2a4--the-first-complication)

**Allowed scene:** `2A`

**Available when**
- Kristin and Brandon are at the facility gate.
- The shift supervisor is questioning their unscheduled inspection.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- The shift supervisor
- Inspection console
- False credentials

**Dramatic purpose**
- Make Kristin’s infrastructure experience the reason the cover works.
- Let entry succeed while Rebecca quietly watches Brandon.

**Possible realizations**
- The supervisor takes them to the cooling manifold and says, “Show me.”
- Kristin feels the pipe, reads the gauge, and traces the vent.
- She explains the real pressure fault in her own words.
- A camera turns toward Brandon and stays on him.
- The inspection console reports faults and cycles noncritical systems.
- The console cannot open detention cells or change the main flood controls.

**Effects**
- May set `restricted_corridor_access`.
- May set `rebecca_observing_infiltrators`.
- May set `inspection_console_used`.
- A doubtful explanation may set `cover_suspected`.

**Completion**
- Kristin and Brandon have reached the infrastructure corridors.

**Abort**
- The scene is no longer `2A`.

**Protected boundary**
- Kristin and Brandon do not learn that Rebecca is watching them.

**Pacing window**
- earliest: `turn 0`
- target: `turn 3`
- latest: `turn 5`

---

### SL-2A-D — The Supervisor Takes Them In

**Source beats:** [2A.3 — Entering the Facility](plot.md#scene-2a3--entering-the-facility), [2A.4 — The First Complication](plot.md#scene-2a4--the-first-complication)

**Allowed scene:** `2A`

**Available when**
- `inspection_window_missed` is true.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- The shift supervisor
- Inspection console

**Dramatic purpose**
- Turn a missed inspection window into entry under watch.

**Possible realizations**
- The supervisor’s patience ends.
- He escorts Kristin and Brandon to the manifold and watches the test.
- Kristin proves the fault well enough to reach the infrastructure corridors.
- The supervisor logs the inspection for follow-up.

**Effects**
- Sets `restricted_corridor_access`.
- Sets `rebecca_observing_infiltrators`.
- Sets `inspection_console_used`.
- Sets `cover_suspected`.
- Sets `supervisor_escorting`.

**Completion**
- Kristin and Brandon have reached the infrastructure corridors under watch.

**Abort**
- The scene is no longer `2A`.

**Protected boundary**
- Kristin and Brandon do not learn that Rebecca is watching them.

**Pacing window**
- earliest: `turn 5`
- target: `turn 6`
- latest: `turn 10`

---

## Storylets for [Scene 2B — Evidence and Betrayal](plot.md#scene-2b--evidence-and-betrayal)

### SL-2B-B — Brandon’s Name Is in the Build Records

**Source beats:** [2B.1 — The Selection Algorithm](plot.md#scene-2b1--the-selection-algorithm), [2B.2 — Kristin Was Bait](plot.md#scene-2b2--kristin-was-bait), [2B.3 — Brandon’s Role](plot.md#scene-2b3--brandons-role)

**Allowed scene:** `2B`

**Available when**
- Kristin and Brandon are in the records archive.
- The audit sweep is moving through the stacks.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- The shift supervisor
- Archive terminals
- Copied JANUS files

**Dramatic purpose**
- Make one file pull reveal Kristin’s bait status, JANUS, and Brandon’s role.
- Turn the audit into a whispered confrontation.

**Possible realizations**
- Kristin pulls her own file first.
- The record reads, “RETAINED — predicted to lead investigators to CORFMAN.”
- The build record below it names Brandon as JANUS’s author.
- Kristin confronts Brandon between the shelves while the audit passes.
- Brandon admits that he wrote the software and claims he broke with Charles.
- Brandon asks Kristin to remove his name before they copy the files.
- Kristin keeps his name or lets him erase it.

**Effects**
- May set `janus_known`.
- May set `janus_evidence`.
- May set `kristin_was_bait`.
- May set `michelle_selected_for_resistance_influence`.
- May set `brandon_janus_role_known`.
- May set `brandon_claimed_reform_motive`.
- May set `archive_crisis_understood`.

**Completion**
- Kristin has confronted Brandon and resolved whether his name stays in the build record.

**Abort**
- The scene is no longer `2B`.

**Protected boundary**
- Michelle’s uprising and the broadcast solution remain undisclosed.

**Pacing window**
- earliest: `turn 0`
- target: `turn 5`
- latest: `turn 7`

---

### SL-2B-C — Michelle Answers Once

**Source beats:** [2B.4 — Michelle’s Hidden Resistance](plot.md#scene-2b4--michelles-hidden-resistance)

**Allowed scene:** `2B`

**Available when**
- Kristin and Brandon have completed the archive discovery.
- The medical terminal is available.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- Dr. Michelle McGehee through the medical terminal
- Medical terminal

**Dramatic purpose**
- Let Michelle answer after the betrayal.
- Show that she is alive and active without revealing the uprising plan.

**Possible realizations**
- The medical terminal prints a maintenance line in Michelle’s private phrasing.
- The line ends with “Shelly.”
- Kristin types one reply.
- Michelle answers once.
- She says she is alive, active, and will send a route.

**Effects**
- Sets `michelle_resistance_known`.
- Sets `michelle_reply_received`.
- Sets `archive_crisis_understood`.

**Completion**
- Kristin receives Michelle’s single reply.

**Abort**
- The scene is no longer `2B`.

**Protected boundary**
- The uprising and broadcast solution remain undisclosed.

**Pacing window**
- earliest: `turn 4`
- target: `turn 6`
- latest: `turn 7`

---

### SL-2B-D — The Audit Reaches the Stacks

**Source beats:** [2B.1 — The Selection Algorithm](plot.md#scene-2b1--the-selection-algorithm), [2B.2 — Kristin Was Bait](plot.md#scene-2b2--kristin-was-bait), [2B.3 — Brandon’s Role](plot.md#scene-2b3--brandons-role), [2B.4 — Michelle’s Hidden Resistance](plot.md#scene-2b4--michelles-hidden-resistance)

**Allowed scene:** `2B`

**Available when**
- `audit_window_missed` is true.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- The shift supervisor
- Archive terminals
- Medical terminal
- Copied JANUS files

**Dramatic purpose**
- Complete the archive crisis when the audit closes the normal choice.

**Possible realizations**
- The audit reaches the stacks.
- The shift supervisor sees Kristin and Brandon but does not raise the alarm.
- Kristin keeps Brandon’s name in the build record.
- They leave with the copied JANUS files.
- Michelle’s maintenance line prints as they leave.
- Kristin receives Michelle’s one reply.

**Effects**
- Sets `brandon_name_kept`.
- Sets `janus_known`.
- Sets `janus_evidence`.
- Sets `kristin_was_bait`.
- Sets `michelle_selected_for_resistance_influence`.
- Sets `brandon_janus_role_known`.
- Sets `brandon_claimed_reform_motive`.
- Sets `michelle_resistance_known`.
- Sets `michelle_reply_received`.
- Sets `archive_crisis_understood`.

**Completion**
- Kristin and Brandon leave the archive with the files and the audit has passed.

**Abort**
- The scene is no longer `2B`.

**Protected boundary**
- The uprising and broadcast solution remain undisclosed.

**Pacing window**
- earliest: `turn 5`
- target: `turn 6`
- latest: `turn 10`

---

## Storylets for [Scene 2C — The Trap Closes](plot.md#scene-2c--the-trap-closes)

### SL-2C-D — Michelle Changes the Choice

**Source beats:** [2C.1 — Rebecca’s Offer](plot.md#scene-2c1--rebeccas-offer), [2C.2 — The Purge Order](plot.md#scene-2c2--the-purge-order), [2C.3 — Evidence or Rescue](plot.md#scene-2c3--evidence-or-rescue), [2C.4 — Living With the Choice](plot.md#scene-2c4--living-with-the-choice), [2C.5 — Michelle Changes the Choice](plot.md#scene-2c5--michelle-changes-the-choice)

**Allowed scene:** `2C`

**Available when**
- Kristin and Brandon are in the command corridor.
- Rebecca has come to meet them.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- Rebecca Jenkins
- Dr. Michelle McGehee through the maintenance network
- Copied JANUS files
- Rebecca’s tablet
- Rebecca’s secured office

**Dramatic purpose**
- Make Rebecca’s offer, the purge, and the physical commitment one live confrontation.
- Let Michelle widen the choice without erasing its cost.

**Possible realizations**
- Rebecca offers Brandon Michelle’s release if he helps remove Charles.
- Her tablet shows the purge order during the negotiation.
- The order includes Rebecca’s people.
- Brandon says yes and the guards stand down.
- Kristin commits by heading for the uplink or the transfer carts.
- Michelle sends a route through the maintenance network.
- The route reaches Michelle’s holding block and Rebecca’s secured office.
- The office can broadcast the evidence and open the sealed detention sectors.

**Effects**
- May set `rebecca_offer_active`.
- May set `antagonist_split_known`.
- May set `purge_clock_started`.
- May set `evidence_ready_to_transmit`.
- May set `rebecca_office_required_for_broadcast`.
- May set `combined_broadcast_rescue_plan_known`.

**Completion**
- Michelle’s route makes the combined broadcast and rescue plan known.

**Abort**
- The scene is no longer `2C`.

**Protected boundary**
- The uprising, Brandon’s sacrifice, and Charles’s deluge remain undisclosed.

**Pacing window**
- earliest: `turn 0`
- target: `turn 13`
- latest: `turn 14`

---

### SL-2C-E — Michelle’s Route Arrives

**Source beats:** [2C.1 — Rebecca’s Offer](plot.md#scene-2c1--rebeccas-offer), [2C.2 — The Purge Order](plot.md#scene-2c2--the-purge-order), [2C.5 — Michelle Changes the Choice](plot.md#scene-2c5--michelle-changes-the-choice)

**Allowed scene:** `2C`

**Available when**
- `purge_window_missed` is true.

**Participants / items**
- Kristin Schweitzer
- Brandon Corfman
- Rebecca Jenkins
- Dr. Michelle McGehee through the maintenance network
- Copied JANUS files
- Rebecca’s tablet

**Dramatic purpose**
- Let the purge force the group onto Michelle’s route without deciding Kristin’s commitment.

**Possible realizations**
- The purge alarm forces Kristin and Brandon out of the command corridor before Kristin has chosen between sending and rescuing.
- Rebecca’s offer and the purge order remain unresolved behind them.
- Michelle’s route arrives through the maintenance network.
- It leads toward her holding block and Rebecca’s secured office.
- The group learns that the office can broadcast the evidence and open the detention sectors.

**Effects**
- Sets `rebecca_offer_active`.
- Sets `antagonist_split_known`.
- Sets `purge_clock_started`.
- Sets `evidence_ready_to_transmit`.
- Sets `rebecca_office_required_for_broadcast`.
- Sets `combined_broadcast_rescue_plan_known`.
- Sets `purge_alarm_active`.
- Does not set `committed_to_transmit`.
- Does not set `committed_to_rescue`.

**Completion**
- Michelle’s route is known and neither commitment has been asserted.

**Abort**
- The scene is no longer `2C`.

**Protected boundary**
- The uprising, Brandon’s sacrifice, and Charles’s deluge remain undisclosed.

**Pacing window**
- earliest: `turn 5`
- target: `turn 6`
- latest: `turn 10`

---

# Scene 3 — The Captives

## Storylets for [Scene 3A — Reaching Michelle](plot.md#scene-3a--reaching-michelle)

### SL-3A-A — Michelle Has Turned Sabotage Into an Uprising

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
- Pay off the earlier evidence of a small hidden resistance by showing what it has become in person.
- Reframe the immediate goal from “get Michelle out” to “help the organized captives expose the whole network.”

**Possible realizations**
- The reunion is interrupted by Michelle directing others.
- Kristin tries to prioritize Michelle; she redirects her to the national stakes.
- Prisoners treat Michelle as an organizer rather than a victim.
- Before this storylet, Michelle is reachable only through the coded route and must not be a direct dialogue speaker.
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
- earliest: `turn 0`
- target: `turn 2`
- latest: `turn 3`

---

### SL-3A-B — The “Rescued” Captives Were Being Prepared

**Source beats:** [3A.2 — The Experiments](plot.md#scene-3a2--the-experiments)

**Allowed scene:** `3A`

**Available when**
- Kristin has reached Michelle and can move with her resistance network.
- Kristin and Michelle can pass through or access evidence from the medical level.
- The experiment program is not yet fully understood.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee
- Medical/behavioral experiment records or equipment already present in the authored setting

**Dramatic purpose**
- Raise the moral and political stakes of Charles’s planned broadcast.
- Show that simply releasing selected prisoners could strengthen the conspiracy.

**Possible realizations**
- Michelle explains what she has observed while Kristin sees corroborating evidence.
- A conditioned “rescue” plan becomes visible through records or treatment setup.
- Kristin recognizes that public testimony itself has been engineered.

**Effects**
- May set `behavioral_experiments_known`.
- May set `conditioned_release_plan_known`.
- May make the broadcast evidence more compelling.
- May increase danger or moral urgency.

**Completion**
- Kristin understands why exposing the experiments must be part of the broadcast evidence.

**Abort**
- Immediate security pressure makes the medical level inaccessible.

**Protected boundary**
- Do not invent successful mind control beyond the specific authored methods and goals.

**Pacing window**
- earliest: `turn 0`
- target: `turn 6`
- latest: `turn 7`

---

### SL-3A-E — The Conditioning Records Confirm the Broadcast Plan

**Source beats:** [3A.2 — The Experiments](plot.md#scene-3a2--the-experiments)

**Allowed scene:** `3A`

**Available when**
- Kristin has reached Michelle.
- Kristin knows the facility ran behavioral experiments.
- Kristin does not yet know the conditioning plan for released captives.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee
- Detention medical records in the medical level

**Dramatic purpose**
- Keep the records as an optional second look after the medical level is entered.
- Show that the planned survivors were prepared to support Charles’s story.

**Possible realizations**
- Kristin reads the detention medical records with Michelle.
- The records confirm the conditioning plan without replaying the medical-level discovery.

**Effects**
- Sets `conditioned_release_plan_known`.
- Does not move the group or repeat the medical-level discovery.

**Completion**
- Kristin understands that the planned survivors were conditioned to support Charles’s story.

**Abort**
- The conditioning plan is already known.

**Protected boundary**
- Do not invent successful mind control beyond the specific authored methods and goals.

**Pacing window**
- earliest: `turn 0`
- target: `turn 6`
- latest: `turn 7`

---

### SL-3A-D — The Framed Official’s Window

**Source beats:** [3A.3 — The Unexpected Prisoner](plot.md#scene-3a3--the-unexpected-prisoner)

**Allowed scene:** `3A`

**Available when**
- Kristin has reached Michelle.
- The experiment stakes are understood.
- The imprisoned senior official can be reached.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee
- The imprisoned senior official
- One-use emergency surface-gate authorization

**Dramatic purpose**
- Turn the political evidence into a human encounter with someone Charles framed and buried.
- Give the group a narrow escape resource early enough to react to its cost and deadline.

**Possible realizations**
- The official explains why Charles framed and detained him.
- He gives Kristin authorization that can release the emergency surface gates once.
- A limited system response makes the expiry tied to Charles’s authority activation visible.

**Effects**
- May set `military_override_codes_available`.
- May set `charles_framed_officials_known`.
- May set `override_codes_deadline_known`.

**Completion**
- The group has a one-use escape authorization and understands that it is a shrinking window, not a general solution.

**Abort**
- The authority activation voids the code before it can be secured, requiring a declared alternate escape path.

**Protected boundary**
- The authorization cannot open the sealed detention sectors or replace the later broadcast controls.

**Pacing window**
- earliest: `turn 0`
- target: `turn 8`
- latest: `turn 9`

---

### SL-3A-C — The Uprising Begins

**Source beats:** [3A.4 — The Uprising Begins](plot.md#scene-3a4--the-uprising-begins)

**Allowed scene:** `3A`

**Available when**
- Kristin has reached Michelle.
- Michelle’s uprising preparation is in place.
- The one-use emergency surface-gate authorization is secured.
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
- earliest: `turn 0`
- target: `turn 10`
- latest: `turn 11`

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
- Facility doors, cameras, diagnostic readings, and empty service corridors

**Dramatic purpose**
- Make Kristin’s Army operations mindset the counter to predictive security.
- Encourage creative free-form disruption rather than one prescribed puzzle solution.

**Possible realizations**
- Kristin creates false water-pressure and ventilation alarms from the inspection console.
- Harmless door and light cycles make the group’s true route less legible.
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
- earliest: `turn 0`
- target: `turn 3`
- latest: `turn 4`

---

### SL-3B-E — Reach Rebecca’s Office

**Source beats:** [3B.2 — Rebecca’s Office](plot.md#scene-3b2--rebeccas-office)

**Allowed scene:** `3B`

**Available when**
- JANUS has been overloaded enough that human security has taken direct control.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee
- Brandon Corfman

**Dramatic purpose**
- Bring Kristin and Michelle into Rebecca’s office while Brandon holds off security forces.

**Possible realizations**
- Kristin and Michelle enter Rebecca’s office while Brandon holds off security forces.

**Effects**
- May set `rebecca_office_reached`.

**Completion**
- Kristin and Michelle have reached Rebecca’s office.

**Abort**
- The group leaves the scene before reaching Rebecca’s office.

**Protected boundary**
- Reaching the office does not confront Rebecca; that remains `SL-3B-B`.

**Pacing window**
- earliest: `turn 0`
- target: `turn 5`
- latest: `turn 6`

---

### SL-3B-B — Rebecca Bargains With the Only Thing She Still Has

**Source beats:** [3B.2 — Rebecca’s Office](plot.md#scene-3b2--rebeccas-office)

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
- Let the player evaluate Rebecca’s bargain before Charles collapses her position.

**Possible realizations**
- Rebecca claims surrender is the only way to save the failing facility.
- Michelle confronts her with approvals for experiments.
- Rebecca offers all detention-site locations.

**Effects**
- May set `rebecca_experiment_approval_confronted`.
- May set `detention_locations_offer_known`.

**Completion**
- The group has secured Rebecca’s detention-site information while deciding how much of her word to trust.

**Abort**
- Rebecca escapes before the confrontation or a non-canonical branch supersedes it.

**Protected boundary**
- Rebecca’s offer is not automatically trusted; later archive evidence remains independently valuable.

**Pacing window**
- earliest: `turn 0`
- target: `turn 7`
- latest: `turn 8`

---

### SL-3B-D — Charles Makes the Deluge Real

**Source beats:** [3B.3 — Charles’s Betrayal](plot.md#scene-3b3--charless-betrayal)

**Allowed scene:** `3B`

**Available when**
- Human security control has replaced JANUS’s predictions.
- The group has secured the detention-site locations.
- Rebecca remains in the office under pressure.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee
- Rebecca Jenkins
- Charles Jenkins through remote communication
- The office security system and outer access-level water controls

**Dramatic purpose**
- Give Rebecca’s exposure room to land before Charles demonstrates that she is expendable.
- Turn Charles’s strategic retreat into a real, contained physical danger rather than an arbitrary disaster.

**Possible realizations**
- Charles locks down the office and abandons Rebecca while transferring national control.
- He turns the harmless diagnostic false alarm into a real deluge in the outer access level.
- Rising water cuts off routes and makes the already-earned drainage and surface-gate resources urgent.

**Effects**
- May set `charles_abandoned_rebecca`.
- May set `facility_destruction_threat`.
- May change Rebecca from an antagonist in control to a trapped, self-preserving antagonist.

**Completion**
- Charles has committed to flooding the outer access level, and the group has time to react before the relay climax.

**Abort**
- The deluge has already begun through a validated alternate event, and the relay crisis takes priority.

**Protected boundary**
- The deluge does not destroy the facility, cause explosions, or decide Brandon’s fate.

**Pacing window**
- earliest: `turn 0`
- target: `turn 9`
- latest: `turn 10`

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
- Security lockdown and rising water make continued relay control costly.
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
- Brandon’s final survival/fate remains unresolved until the authored flood-and-escape outcome permits it.

**Pacing window**
- earliest: `turn 0`
- target: `turn 11`
- latest: `turn 12`

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
- earliest: `turn 0`
- target: `turn 3`
- latest: `turn 4`

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
- earliest: `turn 0`
- target: `turn 7`
- latest: `turn 8`

---

### SL-3C-C — Escape Through the Deluge

**Source beats:** [3C.3 — The Deluge](plot.md#scene-3c3--the-deluge), [3C.4 — Resolution and New Direction](plot.md#scene-3c4--resolution-and-new-direction)

**Allowed scene:** `3C`

**Available when**
- Charles’s emergency deluge is running, and rising water is closing the outer access level.
- The prisoners are moving toward escape routes.
- Kristin can still use the inspection console to control drainage pumps and one watertight barrier.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee
- Brandon Corfman only as allowed by his current status/fate
- Escaping prisoners
- Drainage pumps, a watertight barrier, and the maintenance tunnel
- Emergency surface gates

**Dramatic purpose**
- Give Kristin one final infrastructure-and-operations problem while Michelle leads the human evacuation.
- Move the climax into falling action without removing danger too early.

**Possible realizations**
- Kristin restores power to drainage pumps and holds one barrier long enough for captives to pass.
- Michelle organizes movement through maintenance tunnels.
- The group must accept that not every section can be saved.
- Michelle uses the senior official’s authorization to release the surface gates once.

**Effects**
- May intensify the deluge as Charles seals more access routes.
- May set `evacuation_route_open`.
- May transition into resolution once escape and broadcast consequences are established.

**Completion**
- The evacuation route is open and the captives are moving through the maintenance tunnel.

**Abort**
- Ends on transition to the resolution state.

**Protected boundary**
- The final Phase Two revelation is delivered only by the authored recovered-JANUS resolution event, not by this escape storylet.

**Pacing window**
- earliest: `turn 0`
- target: `turn 11`
- latest: `turn 12`

---

### SL-3C-F — Open the Surface Gates

**Source beats:** [3C.3 — The Deluge](plot.md#scene-3c3--the-deluge), [3C.4 — Resolution and New Direction](plot.md#scene-3c4--resolution-and-new-direction)

**Allowed scene:** `3C`

**Available when**
- Charles’s emergency deluge is running, and rising water is closing the outer access level.
- The prisoners are moving toward escape routes.
- Kristin can still use the inspection console to control drainage pumps and one watertight barrier.

**Participants / items**
- Kristin Schweitzer
- Dr. Michelle McGehee
- Brandon Corfman only as allowed by his current status/fate
- Escaping prisoners
- Drainage pumps, a watertight barrier, and the maintenance tunnel
- Emergency surface gates

**Dramatic purpose**
- Give Kristin one final infrastructure-and-operations problem while Michelle leads the human evacuation.
- Move the climax into falling action without removing danger too early.

**Possible realizations**
- Michelle uses the senior official’s authorization to release the surface gates once.

**Effects**
- May set `los_angeles_facility_lost`.

**Completion**
- The surface gates are released and the Los Angeles operation can no longer be concealed.

**Abort**
- Ends on transition to the resolution state.

**Protected boundary**
- The final Phase Two revelation is delivered only by the authored recovered-JANUS resolution event, not by this escape storylet.

**Pacing window**
- earliest: `turn 0`
- target: `turn 11`
- latest: `turn 12`

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
- May establish Kristin/Michelle’s next-direction facts.

**Completion**
- Reports from other detention sites show the national network breaking apart.

**Abort**
- None in canonical resolution.

**Protected boundary**
- Off-scene facilities are described only through public/currently-known reports.

**Pacing window**
- earliest: `turn 0`
- target: `turn 13`
- latest: `turn 13`

---

### SL-3C-G — Families Begin the Rescue

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
- Families and communities begin independent rescue efforts.

**Effects**
- May set `community_rescue_efforts_begun`.

**Completion**
- Families and communities begin independent rescue efforts.

**Abort**
- None in canonical resolution.

**Protected boundary**
- Off-scene facilities are described only through public/currently-known reports.

**Pacing window**
- earliest: `turn 0`
- target: `turn 13`
- latest: `turn 13`

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
- earliest: `turn 0`
- target: `turn 14`
- latest: `turn 14`

---

# Coverage index

| Playable scene | Storylets | Primary function |
|---|---|---|
| [1A](plot.md#scene-1a--michelles-disappearance) | `SL-1A-A` … `SL-1A-D` | Crime-scene inference, Michelle’s evidence, first authority pressure |
| [1B](plot.md#scene-1b--the-lead-in-the-park) | `SL-1B-A` … `SL-1B-E` | Hidden clue recovery, bench lead, clue interpretation, Brandon trust, pursuit |
| [1C](plot.md#scene-1c--discovery-of-the-facility) | `SL-1C-A` … `SL-1C-D` | Facility discovery, living captives, one advantage, costly recovery after a missed window |
| [2A](plot.md#scene-2a--false-identities) | `SL-2A-C`, `SL-2A-D` | Real fault diagnosis, watched entry, recovery under supervision |
| [2B](plot.md#scene-2b--evidence-and-betrayal) | `SL-2B-B`, `SL-2B-C`, `SL-2B-D` | One-file JANUS discovery, whispered confrontation, Michelle’s reply |
| [2C](plot.md#scene-2c--the-trap-closes) | `SL-2C-D`, `SL-2C-E` | Rebecca’s offer, physical commitment, Michelle’s route |
| [3A](plot.md#scene-3a--reaching-michelle) | `SL-3A-A` … `SL-3A-C` | Reunion reversal, experiments, deadline/override |
| [3B](plot.md#scene-3b--the-battle-for-the-broadcast) | `SL-3B-A` … `SL-3B-C` | Defeat JANUS, confront Rebecca, open relay |
| [3C](plot.md#scene-3c--exposure-and-escape) | `SL-3C-A` … `SL-3C-E` | Broadcast credibility, archive custody, deluge escape, epilogue |

## Canonical scene beats vs. optional storylets

The compiled story package may declare a **canonical bridge event** for a scene transition. A canonical bridge event is story progression that must eventually become true for the single authored scene chain to continue, but **no storylet is itself mandatory**. Storylets are optional realization guidance: free-text player action, NPC reaction, or pacing pressure may realize the same validated fact operation without selecting a storylet.

Bridge facts should describe why the current scene is complete and the next scene is now necessary; they should not pre-assert a revelation whose dramatic payoff belongs to the next scene. Pacing events should create observable pressure or consequences rather than unearned player knowledge.

Current bridge facts are: `michelle_lead_actionable`, `transport_route_departure_ready`, `facility_infiltration_needed`, `restricted_corridor_access`, `archive_crisis_understood`, `combined_broadcast_rescue_plan_known`, `command_levels_assault_underway`, and `broadcast_started`.

## Authoring notes

1. **Optional means optional.** A scene must remain satisfiable even if none of its ordinary storylets are selected. Canonical bridge events may be required, but storylets only provide optional realization guidance for them.
2. **No fixed action vocabulary.** “Possible realizations” are prompt guidance only. The LLM interprets arbitrary player roleplay and proposes semantic effects.
3. **Scene-local context first.** Only participating/present/relevant entities should enter the default turn context. Off-scene references should add only public/currently-known facts.
   A later scene participant is not automatically present: Brandon cannot speak in 1B until `SL-1B-B` establishes his encounter, Michelle cannot speak directly in 3A until `SL-3A-A`, the imprisoned official cannot speak directly in 3A until `SL-3A-D`, and Rebecca cannot speak directly in 3B until `SL-3B-E` brings the group to her office.
4. **Pressure carries pacing.** `SL-2C-D`, `SL-3A-C`, and the deluge/broadcast situations are natural places for deterministic pressure. Pressure may force circumstances to worsen or a canonical event to become urgent, but it must not grant Kristin unexplained knowledge.
5. **Required dependencies stay explicit elsewhere.** The memory card, Brandon, broadcast access, relay access, archive, or any substitutes/fallbacks should be declared in the package dependency model; this file does not silently make them mandatory.
6. **Protected revelations are monotonic.** Optional content can foreshadow later facts, but it must not make a protected revelation true/known before the original scene permits it.
7. **Effects are bounded proposals.** The exact fact paths, numeric pressure ranges, trigger predicates, and transition priorities belong in validated package data rather than being inferred from prose here.

## Design-reference rationale

This pool follows the architecture summarized in `storylet.md`:

- Façade-style organization keeps higher-level dramatic progression separate from lower-level reactive realization.
- Failbetter-style quality-based narrative makes small storylets available from mutable state and lets their effects feed later availability.
- The “Grandfather Clock” pattern is especially close to the intended pacing model: fast local activity can build progress while the major narrative chain advances at a deliberately controlled rate.
- Full causal planning is not treated as the runtime authoring model; deterministic dependency/future-satisfiability checks protect the authored scene spine instead.
