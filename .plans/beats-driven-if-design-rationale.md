Use a **beats-driven plot with soft convergence**, not a scene-by-scene outline that constantly forces the player back onto a prescribed route.

That fits FreytagForge’s architecture better. The engine already treats the LLM as the author of immediate framing while deterministic state controls goals, clues, reveals, incidents, scene pressure, beat phase, and world-state commits. It also explicitly allows lighter disruptions to adapt around the current goal, reserving full replanning for player-confirmed actions that would fundamentally break the story.

## The core distinction

A conventional outline says:

> Jeremiah goes to the park, finds a transit card, meets Gabriel, gets ambushed, and escapes through a storm drain.

An IF-oriented beat says:

> Jeremiah obtains credible evidence that Sarah’s disappearance was deliberate, makes contact with Gabriel, and attracts the attention of the conspiracy.

The second version defines the **dramatic result**, but not the exact action sequence.

The player might:

* Search the park as expected.
* Interrogate a federal patrol officer.
* Track Sarah’s phone.
* Break into her newsroom.
* Follow a suspicious vehicle.
* Refuse to trust Gabriel and investigate him independently.

Any of those paths can fulfill the same beat.

## Recommended structure

I would structure a FreytagForge story at four levels:

### 1. Dramatic phases

These are the broad Freytag regions:

1. Exposition
2. Disruption
3. Rising action
4. Midpoint reversal
5. Crisis
6. Climax
7. Falling action
8. Resolution

These should control overall pressure, revelation scale, opposition strength, and what kinds of events become available.

### 2. Mandatory story beats

These are facts that must eventually become true for the central story to remain coherent.

For this story:

* Jeremiah learns Sarah was abducted.
* Jeremiah learns the missing are alive.
* Jeremiah discovers the Continuity Initiative.
* Jeremiah learns Gabriel helped create JANUS.
* Jeremiah establishes contact with Sarah.
* The purge threat becomes imminent.
* Evidence of the conspiracy is broadcast.
* At least some captives escape.

These are **destination states**, not scenes.

### 3. Optional or substitutable beats

These deepen the story but can be skipped, replaced, or generated dynamically.

Examples:

* Jeremiah finds Sarah’s hidden memory card.
* Jeremiah meets a sympathetic facility worker.
* Jeremiah finds evidence of earlier test disappearances.
* Gabriel saves Jeremiah from an ambush.
* Rebecca offers an alliance.
* Jeremiah discovers conditioned prisoners.
* A released captive unknowingly spreads false information.

Several optional beats can satisfy the same narrative function.

### 4. Moment-to-moment incidents

These are concrete realizations selected according to location, player behavior, inventory, known facts, relationships, and pressure.

FreytagForge already distinguishes abstract beats from concrete incidents, with incidents selected through deterministic conditions such as turn timing, location, inventory, action patterns, cooldowns, and one-shot flags.

That is where the park ambush, facility checkpoint, damaged recording, storm-drain escape, or confrontation with Rebecca should live.

## Do not steer back to the planned scene

Steer toward the **dramatic obligation**.

Suppose the active beat is:

> Establish that Sarah’s disappearance was deliberate.

The player decides to leave Los Angeles instead of visiting the park. Do not contrive a roadblock that says, effectively, “You must go to the park.”

Instead, relocate or reinterpret the evidence:

* A patrol searching Jeremiah’s car possesses Sarah’s press credentials.
* Sarah scheduled an email that arrives while Jeremiah is leaving.
* A survivor at a gas station recognizes the van used in her abduction.
* Gabriel contacts Jeremiah after detecting use of Sarah’s access key.
* Jeremiah encounters a convoy carrying sedated prisoners.

The story advances because the **revelation follows causal opportunities**, not because the player is teleported back onto a scene list.

## Use soft convergence

The ideal model is a funnel:

```text
Many player approaches
        ↓
Several acceptable discoveries
        ↓
One important dramatic realization
        ↓
New range of player approaches
```

For example:

```text
Search Sarah’s office ──────────┐
Question her editor ────────────┤
Follow federal patrols ─────────┼─> Sarah was abducted
Trace her phone ────────────────┤
Contact one of her sources ─────┘
```

The paths converge on a necessary truth, but the player retains authorship over how it is discovered.

After that convergence, the story opens again:

```text
Sarah was abducted
        ↓
Trust Gabriel
Investigate Gabriel
Approach the authorities
Locate a transport route
Try to contact Sarah
Expose the evidence immediately
```

This gives you a coherent dramatic curve without producing the feeling of a disguised choose-your-own-adventure tree.

## A useful beat contract

Each major beat should contain something like this:

```yaml
- id: sarah_abduction_revealed
  phase: disruption
  role: revelation

  dramatic_question:
    Was Sarah one of the unexplained missing, or was she deliberately taken?

  required_outcome:
    Jeremiah gains credible evidence that Sarah was abducted because of her investigation.

  entry_conditions:
    all:
      - flag: sarah_missing
      - not:
          flag: sarah_abduction_confirmed

  possible_evidence:
    - forced_entry
    - interrupted_recording
    - eyewitness_account
    - patrol_documents
    - transit_surveillance
    - gabriel_testimony

  completion_conditions:
    any:
      - discovered_clue: forced_entry_and_blood
      - discovered_clue: sarah_abduction_recording
      - discovered_clue: eyewitness_saw_removal
      - confirmed_fact: sarah_taken_by_continuity_team

  pressure_change: 1
  unlocks:
    - investigate_continuity_initiative
    - locate_gabriel
    - trace_prisoner_transport

  failure_forward:
    The conspiracy realizes Jeremiah is investigating and takes action against him,
    inadvertently leaving new evidence behind.

  protected_facts:
    - Sarah is alive at this stage.
    - Jeremiah does not yet know the full purpose of JANUS.
    - Charles Jenkins has not yet been publicly identified.
```

The important fields are:

* **Required outcome:** What must become true.
* **Possible evidence:** Multiple ways to reach that truth.
* **Completion conditions:** Fact-based advancement.
* **Failure forward:** How an unsuccessful player action still changes the situation.
* **Protected facts:** Revelations the narrator must not expose prematurely.
* **Unlocks:** New goals and possibilities rather than a single next scene.

## Scenes should become temporary containers

Keep scenes, but redefine them.

A scene should not mean:

> The player must complete Scene 1B exactly as written.

It should mean:

> The current dramatic situation involves these participants, this location or location class, this immediate objective, this dramatic question, and this pressure.

That aligns closely with FreytagForge’s existing fact-backed scene state: `current_scene`, `scene_location`, `scene_objective`, `dramatic_question`, `scene_pressure`, `beat_phase`, `beat_role`, `player_approach`, and `scene_participant`.

A scene might therefore be generated at runtime:

```yaml
scene:
  objective: Obtain evidence about Sarah's disappearance
  dramatic_question: Can Jeremiah learn what happened before the authorities stop him?
  participants:
    required:
      - Jeremiah
    optional:
      - Gabriel
      - patrol_officer
      - Sarah's editor
  location_constraints:
    any:
      - Sarah's home
      - newspaper office
      - public records facility
      - transport checkpoint
      - park dead drop
  pressure: 2
  beat_role: investigation
```

The player’s actions determine which concrete version becomes canonical.

## Separate revelation order from event order

For an adventure mystery, the crucial authored material is usually not the exact order of actions. It is the **order in which the player can understand the truth**.

For example:

1. Sarah did not vanish naturally.
2. The mass disappearance was engineered.
3. The missing people are alive.
4. The victims were deliberately selected.
5. Gabriel helped create the selection system.
6. Jeremiah himself was used as bait.
7. Sarah has built a resistance network.
8. The “rescue” announcement is part of the coup.
9. The conspiracy has a second phase.

That reveal ladder should be comparatively firm.

The precise locations, conversations, chases, infiltrations, and evidence objects used to deliver it should be flexible.

## Treat Freytag as pressure, not geography

Freytag phases should control how the world responds:

| Phase          | Runtime behavior                                                            |
| -------------- | --------------------------------------------------------------------------- |
| Exposition     | Broad exploration, low immediate danger, relationship establishment         |
| Disruption     | First irreversible evidence or threat                                       |
| Rising action  | Opposition reacts, clues interconnect, options narrow                       |
| Midpoint       | A revelation changes the meaning of earlier events                          |
| Crisis         | Goals conflict; the player cannot preserve everything                       |
| Climax         | Actions create irreversible public or world-level consequences              |
| Falling action | Consequences propagate through factions and locations                       |
| Resolution     | Final state reflects choices, losses, relationships, and unresolved threats |

The player should be able to wander geographically without escaping the dramatic phase forever. Pressure can advance through timed events, NPC actions, resource loss, changing relationships, or antagonist progress.

## Use deadlines carefully

A dynamic IF story needs some protection against indefinite avoidance, but hard timers everywhere will feel punitive.

Use three kinds of pressure:

* **Reactive pressure:** The antagonist responds to what the player does.
* **Background clocks:** Transfers, broadcasts, searches, or purges move forward.
* **Opportunity decay:** Some leads become harder, riskier, or altered rather than disappearing completely.

For example, ignoring the park lead should not end the story. It might mean:

* The dead drop is discovered by security.
* Gabriel is forced to contact Jeremiah differently.
* The player loses an easy infiltration credential.
* A later route into the facility becomes more dangerous.
* Gabriel initially trusts Jeremiah less.

This preserves consequence without enforcing a correct route.

## Failure should change the route

Avoid repeating the same obstacle until the player performs the expected action.

A failed attempt should produce one or more of:

* New information
* Increased pressure
* Lost trust
* A changed location
* An injured or displaced NPC
* A compromised disguise
* A new enemy awareness flag
* A more costly alternative route

Thus:

> Jeremiah fails to hack the archive.

becomes:

> The failed intrusion alerts Rebecca, but Jeremiah sees that the security response is routed through a hidden sublevel.

The player failed tactically but advanced narratively.

## My recommendation for FreytagForge

Use approximately:

* **7–9 major Freytag beats**
* **2–4 required outcomes per phase**
* **3–6 possible realizations for each required outcome**
* **A larger pool of optional incidents**
* **Firm revelation dependencies**
* **Flexible location and action dependencies**
* **Soft convergence before major turning points**
* **Explicit replanning only when the player truly rejects the premise**

The detailed outline we created should therefore become the **author’s hidden possibility library**, not the runtime itinerary.

For example, “The Park Ambush” should be one possible incident representing:

> The conspiracy detects Jeremiah’s investigation and forces him into an uneasy alliance with Gabriel.

If the player never visits the park, the engine can realize that function at the newsroom, on a freeway checkpoint, inside Sarah’s home, or after Jeremiah contacts a government office.

The best rule is:

> **Protect causality, revelation order, dramatic escalation, and consequential choices. Do not protect the exact sequence of scenes.**

That gives FreytagForge enough structure to deliver a compelling authored story while still letting the player feel that their actions—not the outline—determine how events unfold.
