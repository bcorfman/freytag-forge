# Story 1373

**Genre:** Adventure / Conspiracy Thriller

> **Story specification note:** This story package is one specification made of seven co-equal files: `plot.md`, `world.yaml`, `knowledge.yaml`, `pacing.yaml`, `storylets.md`, `storylet-routes.yaml`, and `handoffs.yaml`. Each carries a distinct part of the story. This file holds narrative canon, scene order, dramatic beats, protected revelations, and intended meaning. The others hold world truth, player knowledge, pressure, optional situations, durable consequences, and fallback delivery. Read them together.
>
> Story changes start here. Any change to what happens, in what order, or what it means is made in `plot.md` first, then propagated out to every other file it affects. A change made in another file must never leave this plot saying something different.
>
> When files conflict, the developer settles it. Decide the intended story, record it in `plot.md` first, then bring the other files into line with it. Do not resolve a conflict by quietly editing whichever file is closest. A purely mechanical change that does not alter the story, such as a turn number, a fact ID, or wiring between facts, can be made in the other files alone, as long as `plot.md` still describes the story correctly afterwards.
>
> `participant_ids` and `item_ids` identify entities and items that are narratively relevant to a scene; they do **not** imply mandatory runtime dependencies. Hard dependencies, when any are required, are declared only in the runtime YAML files.

## Premise

The sudden disappearance of millions of people across the United States throws Kristin Schweitzer’s life into turmoil when her best friend and longtime roommate, molecular biology and biotechnology researcher and author Dr. Michelle McGehee, vanishes. Her search leads her through a fractured, post-disappearance America and into a conspiracy involving government officials, private corporations, secret detention facilities, and a plan to reshape the country through fear and controlled reconstruction.

## Overall Setting

The story takes place in a near-future, post-disappearance United States. Major cities remain inhabited but unstable. Transportation networks are failing, emergency laws have replaced normal civil protections, and shortages have caused communities to become isolated and suspicious.

Los Angeles is under a federal emergency administration. Military checkpoints divide neighborhoods, abandoned vehicles remain on major roads, and official broadcasts repeatedly blame the disappearances on an unexplained national catastrophe.

Beyond public view, a network of government and corporate facilities operates beneath abandoned industrial sites, military installations, and emergency-management centers.

## Principal Characters

### Kristin Schweitzer

A 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who initially wants only to find her best friend and longtime roommate. She is practical, persistent, and reluctant to trust conspiracy theories. Her knowledge of infrastructure and operations eventually makes her essential to infiltrating the conspirators’ underground facilities.

### Dr. Michelle McGehee

A 48-year-old molecular biology and biotechnology researcher and author whose research into genetics led her into secret contracts that place her at the center of the conspiracy. Although initially treated as someone Kristin must rescue, she possesses crucial information and has continued investigating from inside captivity. Kristin, her closest friend, is the only person who calls her "Shelly"; everyone else addresses her as Dr. McGehee.

### Brandon Corfman

A 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin but conceals his own past involvement in the program: writing AI software to identify threats to the conspiracy.

### Charles Jenkins

A 58-year-old former senior government official and the principal architect of the conspiracy. Charles believes democracy has become incapable of responding to national crises, and he and his wife are the only ones with the fortitude to reshape the country properly. He intends to replace our democracy with a centralized system controlled by selected government and corporate leaders.

### Rebecca Jenkins

Charles’s 56-year-old wife and the chief executive of a biotechnology and defense contractor. She oversees the technical operation that made the disappearances possible. Unlike Charles, she is motivated less by ideology than by survival, influence, and the opportunity to control the rebuilding of the country.

# Expanded Scene Outline

## Interactive pacing contract

The story is built for a maximum of 120 accepted player turns. A scene should not advance merely because its next reveal exists. Each scene gives Kristin time to investigate, test a relationship, make a plan, and react when pressure changes the situation. The player may move more quickly by pursuing the central objective, but fast play still has to earn the scene's major change.

| Scene | Turn ceiling | Player-facing dramatic rhythm |
|---|---:|---|
| 1A | 13 | Search the shared home; form a theory; recover and interpret the card; evade a widening patrol search. |
| 1B | 13 | Work the dead drop; decide what Brandon is; test the route; escape a closing park. |
| 1C | 11 | Read the terminal as infrastructure; watch the captives; investigate the network; withdraw before the sweep. |
| 2A | 11 | Build a cover; rehearse it under scrutiny; exploit facility weaknesses; survive a second credential review. |
| 2B | 15 | Gather JANUS evidence; confront Brandon; trace Michelle's sabotage; leave as an archive audit closes in. |
| 2C | 16 | Receive Rebecca's offer; face the purge; live with the evidence-or-rescue conflict; learn Michelle's harder third path. |
| 3A | 13 | Reach Michelle; document the experiments; prepare prisoners and codes; launch before the lockdown wins. |
| 3B | 14 | Confuse JANUS; force Rebecca's reckoning; survive Charles's betrayal; hold the relay through failing power. |
| 3C | 14 | Win the broadcast contest; secure the archive; guide the evacuation; absorb the national consequences and Phase Two. |

# Scene 1 — The Search Begins

**Freytag Function:** Exposition, inciting incident, and the beginning of the rising action

**Central Plot:** Kristin searches for Michelle in the chaotic aftermath of the disappearances. What begins as a personal search becomes evidence that the missing people were deliberately selected and removed.

**Primary Characters:**

* Kristin Schweitzer
* Dr. Michelle McGehee
* Brandon Corfman

## Scene 1A — Michelle’s Disappearance
---
scene_id: 1A
location_id: mcgehee_home
freytag_phase: exposition
objective: Find evidence of Michelle's disappearance
participant_ids: [kristin, michelle]
item_ids: [memory_card, michelle_phone, kristin_laptop, michelle_drawer]
item_placements:
  michelle_phone: on the kitchen floor
  kristin_laptop: in Kristin's truck outside the house
  michelle_drawer: in Michelle's workstation
setting_facts: ["The drawer is shut.", "Michelle's phone is not damaged."]
entry_text: "Michelle's text came in a little after 4:00am, while Kristin was finishing an overnight assessment shift. It came in during all the other emergency alerts, and Kristin had missed it by minutes. Trying to call Michelle back was hopeless - calls stopped going through. Kristin jumped in her truck to get back to the house she shared with her best friend, but police cars, ambulances, and blocked intersections turned the drive into an ordeal.\n\n"
transition_ids: [t_1a_1b]
bridge_text:
  t_1a_1b: >-
    Michelle's files reference an ordinary park bench where she exchanged information with a confidential source.
    Kristin travels there while avoiding checkpoints and emergency patrols.
---

**Setting:** Kristin and Michelle’s shared home

**Characters:**

* Kristin Schweitzer
* Dr. Michelle McGehee

**Plot:** Kristin returns to the home she shares with Michelle shortly after the mass disappearance and discovers that Michelle is missing. Evidence inside the house suggests that she could have been taken rather than simply vanishing with the others.

**Hidden canon:** Michelle hid a memory card for Kristin, taped beneath the workstation drawer carved with Kristin's initials, KMS. It stays hidden until Kristin finds it.

### Scene 1A.1 — Michelle Is Gone

**Details:** Michelle's phone on the kitchen floor; missing tablet and work bag; overturned workstation chair; forced back door; KMS initials carved in drawer

Kristin reaches Michelle's neighborhood after navigating traffic jams, emergency vehicles and frightened people on a wide scale. Michelle is missing, but several details seem somewhat staged:

* Michelle's phone remains on the kitchen floor undamaged.
* Michelle's tablet and work bag are missing and not in their normal spots.
* The chair at Shelly's workstation has been overturned.
* The back door shows signs of forced entry, but otherwise the house seems to be fine, not burglarized.

Kristin notices the drawer on Michelle's workstation has Kristin's initials 'KMS' newly carved into it, making it worth looking at more closely.

### Scene 1A.2 — Michelle’s Last Investigation

**Details:** Michelle's memory card; Kristin's laptop in her truck; Continuity Initiative files; population stabilization centers; Michelle’s research notes

Kristin finds Michelle's memory card. Kristin plugs the memory card into her laptop out in her truck.

The memory card contains fragments of Michelle’s research into a federal emergency program called the **Continuity Initiative**.

The files show that private contractors constructed dozens of enormous “population stabilization centers” before the disappearances. Officially, the centers were designed as shelters for natural disasters and biological attacks.

Michelle’s notes contain one alarming sentence:

> They are not preparing to protect people. They are preparing to choose who remains.

### Scene 1A.3 — The Interrupted Message

**Details:** voice recording; government tracking; imminent activation event; someone entering house; Michelle whispers; national catastrophe

On the memory card, Kristin also finds a voice recording Michelle attempted to send shortly before she disappeared. In it, she says that government officials have been tracking her and that a planned “activation event” is imminent.

Before naming her source, Michelle hears someone enter the house. The recording ends after she whispers:

> Kristin, do not trust the emergency broadcasts.

This becomes the story’s **inciting incident**. Kristin realizes Michelle’s disappearance may be connected to the national catastrophe.

### Scene 1A.4 — The First Threat

**Details:** federal emergency patrol; welfare-check officers; Michelle’s office search; Michelle's memory card; marked front gate; reflective tape

An emergency patrol arrives at Kristin and Michelle's shared house unusually quickly. The officers conduct a quick welfare check and a targeted look at Michelle's work area, asking specifically about her research and findings. They do not open the drawer, so the card remains undiscovered; they discover and confiscate nothing.

Kristin conceals the memory card and pretends to know nothing. After the patrol leaves, she notices that one officer has quietly marked the front gate with a strip of reflective tape.

She understands that the authorities intend to return.

## Scene 1B — The Lead in the Park
---
scene_id: 1B
location_id: los_angeles_park
freytag_phase: rising_action
objective: Follow Michelles lead and survive the park
participant_ids: [kristin, brandon, michelle]
item_ids: [memory_card, transit_card]
entry_text: "The park was quieter than the streets around it. The clues led Kristin to an ordinary bench near the service path. She crossed the damaged grounds, kept clear of the checkpoints, and knelt beside the bench.\n\n"
transition_ids: [t_1b_1c]
bridge_text:
  t_1b_1c: >-
    The park pursuit was behind them. Kristin and Brandon headed for the freight terminal along the transport route.
---

**Setting:** Kristin’s neighborhood and a damaged public park in Los Angeles

**Characters:**

* Kristin Schweitzer
* Brandon Corfman
* Dr. Michelle McGehee, through recordings and evidence

**Plot:** Kristin follows clues left by Michelle and discovers that the disappearances were coordinated through disguised emergency operations.

### Scene 1B.1 — Michelle’s Dead Drop

**Details:** ordinary park bench; damaged grounds; service path; checkpoints; emergency patrols

Michelle’s files reference an ordinary park bench where she exchanged information with a confidential source. Kristin travels there while avoiding checkpoints and emergency patrols. The bench could be nothing, or it could hold the only lead Michelle prepared for her.

The records suggest that the mass disappearance was preceded by years of secret tests.

### Scene 1B.2 — The Man Following Her

**Details:** watching man; abandoned service tunnels; emergency patrol; Brandon Corfman; Michelle photograph; Continuity Initiative

Kristin notices a man watching her from across the park. Believing the man works for the government, Kristin attempts to escape through abandoned service tunnels beneath the park.

The man follows but saves Kristin when an emergency patrol corners her. He identifies himself as Brandon Corfman, the person in Michelle’s photograph.

Brandon says Michelle contacted him because he had once worked on the Continuity Initiative.

### Scene 1B.3 — Brandon’s Warning

**Details:** contaminated emergency water; disguised response teams; evacuation tunnels; missing registrations; communications outages; falsified casualty data

Brandon explains that the disappearances were not instantaneous. During the hours before the public became aware of the event, selected people were:

* Drugged through contaminated emergency water supplies
* Removed by disguised response teams
* Transported through evacuation tunnels
* Registered as missing before local authorities understood what had occurred

The scale was hidden by communications outages, manufactured panic, and falsified casualty data.

Brandon claims the missing are still alive, but he refuses to explain how he knows.

### Scene 1B.4 — The Park Ambush

**Details:** tactical team; storm-drain system; specialized codes; secured maintenance gate; government systems; Brandon’s hidden involvement

A tactical team arrives, proving Kristin was tracked from her house. Kristin and Brandon escape through a storm-drain system, but Brandon is forced to use specialized codes to unlock a secured maintenance gate.

Kristin realizes Brandon retains access to government systems and may be more deeply involved than he admits.

## Scene 1C — Discovery of the Facility
---
scene_id: 1C
location_id: regional_facility
freytag_phase: rising_action
objective: Confirm the facility and its purpose
participant_ids: [kristin, brandon, michelle]
item_ids: [transit_card]
entry_text: "Michelle's lead brought Kristin and Brandon to a freight terminal that was supposed to be abandoned. Fresh tire tracks, humming air vents, and unusually heavy electrical service said otherwise. They kept to the shadow of the loading docks, looking for a way into whatever lay below.\n\n"
transition_ids: [t_1c_2a]
bridge_text:
  t_1c_2a: >-
    The observation shaft showed them living captives in an active regional command center, but the main facility could
    not be reached from the service level without triggering security. Kristin and Brandon withdrew to prepare a way
    inside.
---

**Setting:** Industrial outskirts of Los Angeles and an underground Continuity Initiative installation

**Characters:**

* Kristin Schweitzer
* Brandon Corfman
* Charles Jenkins, through surveillance footage
* Rebecca Jenkins, through surveillance footage

**Plot:** Kristin and Brandon locate one of the secret facilities and discover that it is only one part of a nationwide network.

### Scene 1C.1 — Following the Transport Route

**Details:** abandoned freight terminal; structural modifications; fresh tire tracks; humming air vents; heavy electrical service

Michelle’s lead brings Kristin and Brandon to a supposedly abandoned freight terminal. Kristin recognizes that recent structural modifications conceal something larger below.

Fresh tire tracks, air vents, and unusually heavy electrical service confirm that the site remains active.

Kristin and Brandon search for a route into the service level without triggering security.

An old service schematic marks one dry maintenance ascent joining the drainage spine. It is too exposed to use now, but Kristin memorizes it as the sort of route that might matter if the facility's systems fail later.

### Scene 1C.2 — Proof of the Captives

**Details:** observation shaft; sedated prisoners; processing area; identification numbers; missing-person reports; woman resembling Michelle

From an observation shaft, Kristin sees rows of sedated prisoners being moved through a processing area. Their identification numbers correspond to missing-person reports stored in Michelle’s files.

She briefly sees a woman resembling Michelle among a group being transferred, but the view is obscured before she can confirm her identity.

Kristin wants to enter immediately. Brandon stops her, arguing that a reckless rescue attempt would cause the prisoners to be relocated or killed.

### Scene 1C.3 — The Nationwide Network

**Details:** logistics terminal; regional command center; nationwide facilities; political personnel; resistance organizers; experimental programs

Brandon accesses a logistics terminal and discovers that the Los Angeles site is not where all the missing people are held. It is a regional command center connected to facilities throughout the country.

The missing have been divided into categories:

* Political and military personnel
* Scientists, engineers, and medical specialists
* Journalists and public figures
* People labeled as potential resistance organizers
* Civilians selected for experimental programs
* Families of strategically valuable individuals

The conspiracy did not simply remove random citizens. It removed people who might either help control the country or resist that control.

### Scene 1C.4 — The Architects Revealed

**Details:** recorded conference; Charles Jenkins; Rebecca Jenkins; overcrowded facilities; resisting prisoners; emergency authority

A recorded conference shows Charles and Rebecca Jenkins discussing the next phase of the Continuity Initiative.

Charles intends to announce that the federal government has collapsed and establish a new emergency authority. Rebecca warns him that several facilities are overcrowded and that prisoners are beginning to resist.

Charles responds that the public will accept any government that promises to restore the missing.

Kristin now understands the central strategy: the conspirators created the catastrophe so they could later present themselves as the only people capable of ending it.

# Scene 2 — The Infiltration

**Freytag Function:** Rising action, progressive complications, midpoint revelation, and crisis

**Central Plot:** Kristin and Brandon prepare to enter the facility, gather evidence, and locate Michelle. Their alliance is strained when Kristin discovers Brandon’s connection to the conspiracy.

**Primary Characters:**

* Kristin Schweitzer
* Brandon Corfman
* Charles Jenkins
* Rebecca Jenkins
* Dr. Michelle McGehee

## Scene 2A — False Identities
---
scene_id: 2A
location_id: facility_perimeter
freytag_phase: rising_action
objective: Enter the facility under false identities
participant_ids: [kristin, brandon]
item_ids: [transit_card]
entry_text: "Brandon's hideout was buried inside a dead communications center: servers, salvaged hardware, and years of leaked Continuity Initiative documents. Somewhere beneath the city the facility waited, and its unstable cooling-water and ventilation readings were exactly the kind of flaw a pair of outside inspectors might be sent to examine.\n\n"
transition_ids: [t_2a_2b]
bridge_text:
  t_2a_2b: >-
    Their false credentials survived the initial checks, and Kristin's warning about unstable cooling-water pressure
    won them access to restricted infrastructure corridors. Beyond those corridors, the records archive waited behind
    another layer of security.
---

**Setting:** Brandon’s hidden operations base and the secret facility

**Characters:**

* Kristin Schweitzer
* Brandon Corfman

**Plot:** Brandon uses old contacts from his software and security circles to create identities that will allow him and Kristin to enter the facility as technical inspectors.

### Scene 2A.1 — Brandon’s Hideout

**Details:** fortified hideout; abandoned communications center; servers; salvaged hardware; emergency supplies; leaked code

Brandon takes Kristin to a fortified hideout inside an abandoned communications center. It contains servers, salvaged hardware, emergency supplies, and years of leaked code and internal documents on the Continuity Initiative.

Kristin discovers that Brandon has been preparing for the disappearance event for a long time.

Brandon explains that he tried to expose the program but was discredited, dismissed, and labeled unstable.

### Scene 2A.2 — The Infiltration Plan

**Details:** cooling-water imbalance; ventilation monitors; underground installation; false credentials; inspection console; command center records

Kristin identifies unstable cooling-water and ventilation readings in the facility's overextended service systems. The installation needs outside inspectors to distinguish a genuine leak from a sensor fault.

Brandon creates false credentials presenting them as specialists sent to investigate a dangerous cooling-water fault.

Their objectives are:

1. Enter without raising an alarm.
2. Copy the command center’s records.
3. Locate Michelle and the other captives.
4. Discover how prisoners are being transported.
5. Transmit the evidence to independent news and emergency networks.
6. Escape before Charles orders the facility purged.

### Scene 2A.3 — Entering the Facility

**Details:** security layers; initial identity checks; unscheduled inspection; cooling-water warning; technical explanation; infrastructure corridors

Kristin and Brandon pass through several layers of security. Their identities survive the initial checks, but a supervisor questions why their inspection was not scheduled.

Kristin improvises, warning that a cooling-water fault could disable the underground service level. Her technical explanation is convincing enough that the supervisor reluctantly permits them to continue.

This gives Kristin access to restricted infrastructure corridors that bypass the main security checkpoints.

The corridor inspection console accepts the temporary credentials long enough to display water-pressure, ventilation, door, and lighting diagnostics. Kristin notes its limits before they move on: it can report faults and cycle noncritical systems, but it cannot open detention cells or alter the main flood controls.

### Scene 2A.4 — The First Complication

**Details:** facial-recognition system; former developer; Continuity Initiative contractor; quiet security alert; Rebecca Jenkins; compromised infiltration

A facial-recognition system identifies Brandon as a former Continuity Initiative developer and contractor. Instead of triggering a general alarm, the system quietly alerts Rebecca Jenkins.

Rebecca orders security to observe Brandon rather than arrest him. She wants to know why he has returned and whom he has brought with him.

Kristin and Brandon remain unaware that their infiltration has already been compromised.

## Scene 2B — Evidence and Betrayal
---
scene_id: 2B
location_id: janus_archive
freytag_phase: rising_action
objective: Secure evidence while judging Brandons betrayal
participant_ids: [kristin, brandon, michelle]
item_ids: []
entry_text: "The records archive hummed behind the restricted corridor. Rows of terminals held the Initiative's selection files - and, somewhere in them, the answers to why Michelle was taken and who helped build the system that chose her.\n\n"
transition_ids: [t_2b_2c]
bridge_text:
  t_2b_2c: >-
    The JANUS evidence in the archive showed what the system was built to do. Kristin and Brandon understood how much
    danger that evidence put them in.
---

**Setting:** The facility’s records archive, medical levels, and Brandon’s hideout through a remote connection

**Characters:**

* Kristin Schweitzer
* Brandon Corfman
* Charles Jenkins
* Rebecca Jenkins
* Dr. Michelle McGehee

**Plot:** Kristin and Brandon uncover the true purpose of the experiments. Kristin also learns that Brandon helped design the system used to select the missing.

### Scene 2B.1 — The Selection Algorithm

**Details:** restricted records archive; unfamiliar system files; government data; financial data; Michelle’s research

Inside the records archive, Kristin discovers files describing an artificial-intelligence system called **JANUS**.

JANUS analyzed government, financial, medical, employment, education, and communications data to classify every American according to:

* Usefulness to national reconstruction
* Likelihood of organized resistance
* Political influence
* Psychological vulnerability
* Family and social connections
* Potential value as leverage over others

Michelle was not taken merely because she discovered the conspiracy. JANUS predicted that her research and public credibility could unite opposition groups after the disappearance.

Kristin was deliberately left behind because the system predicted she would lead investigators to Brandon.

### Scene 2B.2 — Kristin Was Bait

**Details:** facility discovery; Michelle’s evidence; Brandon’s hidden network; anticipated journey; accessible evidence; security access

The revelation transforms Kristin’s understanding of her journey. Her discovery of the facility was not entirely accidental.

Charles expected Kristin to seek Brandon. Security allowed portions of Michelle’s evidence to remain accessible so Kristin would expose Brandon’s hidden network.

Kristin realizes that every step she has taken may have been anticipated.

### Scene 2B.3 — Brandon’s Role

**Details:** JANUS development records; AI software; national emergencies; mass detention; political control; Michelle’s access

Kristin finds Brandon’s name in the original JANUS development records. Brandon admits that he helped write the AI software used to identify people at risk during national emergencies.

When he discovered that Charles intended to use it for mass detention and political control, he attempted to destroy the project. He failed and fled.

Michelle knew about Brandon’s involvement but believed his access was the only way to expose the program.

Kristin feels betrayed. She suspects Brandon may still be manipulating her to erase evidence of his own guilt.

### Scene 2B.4 — Michelle’s Hidden Resistance

**Details:** equipment failures; corrupted prisoner files; medical terminal; altered classifications; delayed transfers; maintenance reports

The records reveal unusual equipment failures and corrupted prisoner files throughout the facility. Kristin recognizes phrases in the corrupted data that Michelle used in her private notes.

Michelle has built a small covert network among prisoners and sympathetic workers. Using her access to a medical terminal, she has been:

* Altering prisoner classifications
* Delaying transfers
* Hiding vulnerable captives from experimental programs
* Sending coded messages through maintenance reports
* Preparing prisoners for an organized uprising

The records prove that Michelle is active inside, but they cannot yet show how far her hidden network reaches.

Michelle is not passively waiting to be rescued. She has already begun dismantling the facility from within.

## Scene 2C — The Trap Closes
---
scene_id: 2C
location_id: purge_chamber
freytag_phase: crisis
objective: Survive the purge clock and choose a combined mission
participant_ids: [kristin, brandon, michelle]
item_ids: []
entry_text: "The command levels tightened around them. Somewhere above, orders were already moving - transfers, schedules, contingency plans measured in hours instead of days. Whatever Kristin and Brandon did next had to count.\n\n"
transition_ids: [t_2c_3a]
bridge_text:
  t_2c_3a: >-
    The purge clock was running, and the evidence was ready to transmit. Kristin and Brandon committed to one combined
    mission: broadcast the truth and rescue the captives.
---

**Setting:** The facility’s command levels and detention sectors

**Characters:**

* Kristin Schweitzer
* Brandon Corfman
* Dr. Michelle McGehee
* Charles Jenkins
* Rebecca Jenkins

**Plot:** Rebecca exposes the infiltrators, Charles accelerates his plans, and Kristin must choose between escaping with evidence or remaining to rescue the captives.

### Scene 2C.1 — Rebecca’s Offer

**Details:** private executive channels; upper command corridors; live transfer traffic; an invitation addressed to Brandon

Rebecca contacts Brandon privately and offers him safe passage. She claims Charles has become unstable and intends to eliminate both prisoners and lower-level conspirators once the new government is established.

She asks Brandon to help her remove Charles and take control of the Continuity Initiative.

In exchange, she promises to release Michelle.

Brandon pretends to consider the offer so he can gain access to the executive level.

### Scene 2C.2 — The Purge Order

**Details:** corrupted JANUS records; valuable captives; full transfer; destruction order; national broadcast; selected survivors

Charles discovers that Michelle’s resistance network has corrupted JANUS records. Fearing that evidence will escape, he orders a full transfer of the most valuable captives and the destruction of everyone else.

The purge will begin within hours.

At the same time, Charles prepares a national broadcast in which he will claim to have located survivors of the catastrophe. He plans to release a small number of carefully selected captives and use their return to legitimize his new emergency government.

### Scene 2C.3 — Evidence or Rescue

**Details:** conspiracy evidence; exposed position; sealed detention sectors; transmitting evidence; thousands of captives; crisis choice

Kristin and Brandon obtain enough evidence to expose the conspiracy, but transmitting it will reveal their position and seal the detention sectors.

Brandon argues that they must send the evidence immediately, even if doing so makes a rescue impossible. Without proof, freeing one group of prisoners will not stop the national operation.

Kristin refuses to abandon Michelle and thousands of other captives.

Their disagreement creates the story’s central **crisis choice**:

* Escape with the evidence and expose the conspiracy
* Attempt a rescue and risk losing both the evidence and their lives

### Scene 2C.4 — Living With the Choice

**Details:** copied evidence; sealed detention sectors; transfer carts; Brandon's guilt; Rebecca's offer; maintenance network

The apparent choice cannot be solved by a quick argument. Kristin and Brandon have time to test what each path would cost, but not enough time to pretend the costs are theoretical.

Sending the evidence would make the national case harder for Charles to bury, yet it would expose their position while transfer carts begin moving below. A direct rescue might save Michelle and the nearby captives, yet it could leave Charles free to repeat the operation elsewhere.

Rebecca's offer makes the distrust worse. Brandon can use the contact to seek a route upward, but Kristin cannot know whether he is buying time for the captives or protecting himself.

### Scene 2C.5 — Michelle Changes the Choice

**Details:** coded message; maintenance network; emergency broadcast system; detention sectors; Rebecca’s secured office; combined mission

Michelle sends a coded message through the maintenance network. It marks a route into her partly unsecured holding block and explains that the facility’s emergency broadcast system can transmit the evidence while opening the sealed detention sectors.

However, the broadcast system can only be activated manually from Rebecca’s secured office.

The apparent choice between exposure and rescue becomes a far more dangerous combined mission.

# Scene 3 — The Captives

**Freytag Function:** Final rise, climax, falling action, and resolution

**Central Plot:** Kristin, Brandon, and Michelle coordinate an uprising, expose the Continuity Initiative, and confront Charles and Rebecca as Charles turns a false emergency into a real flood.

**Primary Characters:**

* Kristin Schweitzer
* Dr. Michelle McGehee
* Brandon Corfman
* Charles Jenkins
* Rebecca Jenkins

## Scene 3A — Reaching Michelle
---
scene_id: 3A
location_id: detention_level
freytag_phase: crisis
objective: Reach Michelle and join the uprising
participant_ids: [kristin, michelle, brandon, senior_official]
item_ids: [override_codes]
entry_text: "A partly unsecured detention sector opened onto rows of captives. Coded announcements crackled through stolen radios, and the prisoners moved with a discipline no captor had taught them - someone inside had been organizing this long before rescue arrived.\n\n"
transition_ids: [t_3a_3b]
bridge_text:
  t_3a_3b: >-
    Michelle's uprising disabled cameras and seized checkpoints, while Charles sealed the primary exits and sent armed
    teams downward. Kristin, Michelle, and Brandon fought upward toward Rebecca's office and the broadcast levels.
---

**Setting:** Detention sectors and experimental laboratories within the facility

**Characters:**

* Kristin Schweitzer
* Dr. Michelle McGehee
* Brandon Corfman
* Imprisoned senior official

**Plot:** Kristin and Brandon descend into the detention levels while Michelle organizes the prisoners for an uprising.

### Scene 3A.1 — The Detention Block

**Details:** detention sector; rows of captives; scattered radios; coded announcements; tightening security

Kristin follows Michelle's maintenance route into one partly unsecured detention sector, not a mass release. She expects rows of helpless captives. Instead, Michelle speaks into a stolen radio, coordinating prisoners through coded announcements and sympathetic facility workers.

The reunion between Kristin and Michelle is brief because the purge countdown has begun.

Michelle explains that the facility contains only a fraction of the missing millions. Freeing them will matter only if the broadcast reveals the locations of the remaining sites.

### Scene 3A.2 — The Experiments

**Details:** medical level; neurological experiments; behavioral experiments; short-term memory; targeted stimulation; false recollections

Michelle leads Kristin through a medical level where prisoners have been subjected to neurological and behavioral experiments.

Rebecca’s company has been testing methods for:

* Erasing short-term memory
* Increasing compliance through targeted stimulation
* Creating convincing false recollections
* Conditioning released captives to support official explanations
* Predicting resistance before it occurs

The people Charles intends to “rescue” during his broadcast have already been conditioned to endorse his version of events.

### Scene 3A.3 — The Unexpected Prisoner

**Details:** senior official; government prisoners; fabricated evidence; authorization codes; emergency surface gates; Charles’s broadcast

Among the captives is a senior official publicly blamed for causing the catastrophe. He reveals that Charles imprisoned members of his own government and fabricated evidence against them.

He possesses authorization codes that can release the facility's emergency surface gates once, but the codes will expire when Charles’s new authority is formally activated.

The rescue now has a strict deadline tied to Charles’s broadcast.

### Scene 3A.4 — The Uprising Begins

**Details:** coordinated disturbances; disabled cameras; isolated guards; internal checkpoints; sealed primary exits; armed response teams

Michelle triggers coordinated disturbances across the detention sectors. Prisoners disable cameras, overwhelm isolated guards, and seize control of several internal checkpoints.

The uprising succeeds initially, but Charles seals the primary exits and redirects armed response teams toward the detention levels.

Kristin, Michelle, and Brandon must fight upward toward Rebecca’s office while the prisoners hold the lower levels.

## Scene 3B — The Battle for the Broadcast
---
scene_id: 3B
location_id: broadcast_relay
freytag_phase: climax
objective: Overload JANUS and seize the broadcast
participant_ids: [kristin, michelle, brandon, rebecca]
item_ids: []
entry_text: "Alarms layered over alarms as the facility fought to predict its attackers. Above the fighting, Rebecca's executive office and the external broadcast relay waited at the end of corridors that JANUS watched move by move.\n\n"
transition_ids: [t_3b_3c]
bridge_text:
  t_3b_3c: >-
    Brandon disconnected the relay from JANUS and held it open while Kristin and Michelle began the broadcast. The
    evidence was moving beyond Charles's control as water rose through the outer access level.
---

**Setting:** Security corridors, command center, and Rebecca Jenkins’s executive office

**Characters:**

* Kristin Schweitzer
* Dr. Michelle McGehee
* Brandon Corfman
* Rebecca Jenkins
* Charles Jenkins

**Plot:** The protagonists attempt to transmit the evidence while Charles and Rebecca turn against one another.

### Scene 3B.1 — The Facility Fights Back

**Details:** JANUS movement predictions; security corridors; cameras; doors; limited inspection console; broadcast relay

JANUS begins predicting the resistance group’s movements by analyzing doors opened, cameras disabled, and power systems disrupted.

Kristin realizes the only way to defeat the system is to feed it a convincing lie. Using the inspection console she accessed under the false cover, she creates false water-pressure and ventilation alarms in empty outer service corridors, then cycles unused doors and lights to support the deception. She does not damage the detention levels or the escape path.

These actions overload JANUS with conflicting emergencies and force human operators to take control.

### Scene 3B.2 — Rebecca’s Office

**Details:** Rebecca’s office; security forces; false emergency reports; approved experiments; detention site locations

Kristin and Michelle enter Rebecca’s office while Brandon holds off security forces.

Rebecca claims that she never supported Charles’s plan to kill the captives. She argues that surrendering to her is the only way to regain control before the false emergency exposes the breach.

Michelle reveals that Rebecca personally approved the experiments and selected which prisoners would be used.

Rebecca attempts to bargain by offering the locations of every detention site.

### Scene 3B.3 — Charles’s Betrayal

**Details:** Charles appears; locked office; national network; emergency deluge; anti-government terrorists; remote command site

Charles appears remotely and locks down Rebecca’s office. He reveals that he has already transferred control of the national network away from her.

He has already transferred national control away from Los Angeles. He intends to drown the local witnesses, captives, Rebecca, and infiltrators, then blame the catastrophe on anti-government terrorists who sabotaged the water system.

He turns Kristin's false emergency into a real one, opening the emergency deluge into the outer access level and sealing the public exits. Water begins to force its way toward the command and detention routes.

Rebecca finally understands that Charles always considered her expendable.

### Scene 3B.4 — Brandon’s Sacrifice

**Details:** broadcast system; communications relay; relay chamber; security lockdown; JANUS confession; manual bypass

The broadcast system cannot operate while Charles controls the external communications relay. Brandon reaches the relay chamber and manually disconnects it from JANUS.

Doing so leaves him isolated in a relay chamber that security can lock down and flood once Charles understands what he has done.

Before completing the override, Brandon transmits a confession describing his role in creating JANUS. His statement authenticates Michelle’s evidence and prevents Charles from dismissing it as fabricated.

Brandon remains behind to keep the relay open while Kristin and Michelle begin the broadcast.

## Scene 3C — Exposure and Escape
---
scene_id: 3C
location_id: facility_escape
freytag_phase: resolution
objective: Expose the network and escape
participant_ids: [kristin, michelle, rebecca]
item_ids: [portable_archive]
item_placements:
  portable_archive:
    placement: with Rebecca in her hands
    while_fact_false: portable_archive_secured
entry_text: "The broadcast chamber lights steadied as Brandon's relay held open. Outside, Charles's emergency deluge was filling the outer access level and forcing water toward the maintenance routes; inside, the evidence was ready to leave for good.\n\n"
transition_ids: []
---

**Setting:** Rebecca’s office, the collapsing facility, and the surface of post-disappearance Los Angeles

**Characters:**

* Kristin Schweitzer
* Dr. Michelle McGehee
* Brandon Corfman
* Rebecca Jenkins
* Charles Jenkins

**Plot:** The conspiracy is exposed, the captives escape, and the protagonists achieve a meaningful but incomplete victory.

### Scene 3C.1 — The National Transmission

**Details:** national broadcast controls; JANUS selection records; detention network locations; behavioral-experiment records; Brandon’s confession

A portable data case holding the archive is with Rebecca in the executive office.

Michelle broadcasts:

* Video of the captives
* JANUS selection records
* Locations of the national detention network
* Charles and Rebecca’s planning sessions
* Evidence of the behavioral experiments
* Brandon’s confession
* Instructions for local authorities to verify nearby facilities

Charles interrupts the transmission and claims Michelle is part of a terrorist organization.

Michelle counters by displaying live images from multiple facilities where prisoners and sympathetic workers have begun revolting.

The truth can no longer be contained by controlling a single broadcast.

### Scene 3C.2 — The Final Confrontation

**Details:** portable archive; corporate conspirators; prisoner locations; independent networks; captured Rebecca; remote command site

Rebecca attempts to escape with a portable archive containing the identities of corporate and political conspirators.

Kristin stops her, but she warns that destroying or surrendering the archive may leave innocent people trapped because it also contains prisoner locations.

Rather than destroy it, Michelle transmits copies to several independent networks.

Rebecca is captured by the prisoners she authorized for experimentation.

Charles escapes from his remote command site before authorities can locate him, preserving an ongoing threat.

### Scene 3C.3 — The Deluge

**Details:** emergency deluge; sealed public exits; rising water; pump controls; maintenance tunnel; surface-gate codes

Charles's deluge is already running, and water is forcing people out of the outer access level. Kristin uses the same inspection access that created the false alarms to restore power to the drainage pumps and hold one watertight barrier long enough for the captives to pass. She cannot keep every route open.

Michelle leads the prisoners through the maintenance tunnel while Kristin keeps the pumps and barrier working.

From Rebecca's office, Michelle uses the senior official's expiring authorization to release the emergency surface gates once. Brandon remains at the relay so the broadcast stays live. His fate is initially uncertain.

Thousands of captives emerge into Los Angeles as news drones, civilians, and local responders begin arriving.

### Scene 3C.4 — Resolution and New Direction

**Details:** surrendered facilities; released prisoners; Charles’s control; rogue officials; rescue efforts; partially recovered JANUS file

The national detention network begins to fracture:

* Some facilities surrender.
* Others release their prisoners.
* Several remain under Charles’s control.
* Government agencies deny involvement and blame rogue officials.
* Communities begin organizing independent rescue efforts.
* Families learn that many of the missing may still be alive.

Kristin’s personal goal is fulfilled when she and Michelle are reunited, but neither can return to their former life.

Michelle begins publishing the complete Continuity Initiative archive. Kristin joins teams locating and opening the remaining facilities.

The final revelation comes from a partially recovered JANUS file. The disappearance operation was labeled **Phase One**.

Phase Two was designed not to remove people, but to provoke conflict among those who remained.

The story closes with Charles observing the growing unrest from an unknown location. Although his conspiracy has been exposed, he believes the country is still moving toward the collapse he intended—and that frightened people may yet ask him to restore order.

# Freytag Structure Summary

## Exposition

Kristin and Michelle’s relationship, the post-disappearance crisis, Michelle’s investigation, and the unstable condition of Los Angeles are established.

## Inciting Incident

Kristin discovers evidence that Michelle was abducted and that her disappearance is connected to the Continuity Initiative.

## Rising Action

Kristin meets Brandon, discovers the secret facility, learns the missing are alive, infiltrates the installation, uncovers JANUS, and discovers both Brandon’s guilt and Michelle’s resistance network.

## Crisis

Kristin must seemingly choose between transmitting evidence and rescuing the captives. Michelle reveals a dangerous plan capable of accomplishing both.

## Climax

Kristin, Michelle, and Brandon seize the emergency broadcast system while the prisoners revolt. Kristin defeats the facility’s predictive security system, Brandon holds open the communications relay, and Michelle begins the national exposure of the conspiracy; the transmission’s public contest and consequences continue into Scene 3C.

## Falling Action

The captives escape, Rebecca is captured, the flooded Los Angeles facility is exposed, and detention centers across the country begin responding to the broadcast.

## Resolution

Kristin and Michelle reunite and commit themselves to freeing the remaining captives. Charles escapes, while the discovery of “Phase Two” creates a larger unresolved threat.
