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

The sudden disappearance of millions of people across the United States throws Kristin Schweitzer’s life into turmoil when her best friend, molecular biology and biotechnology researcher and author Dr. Michelle McGehee, vanishes. Her search leads her through a fractured, post-disappearance America and into a conspiracy involving government officials, private corporations, secret detention facilities, and a plan to reshape the country through fear and controlled reconstruction.

## Overall Setting

The story takes place in a near-future, post-disappearance United States. Major cities remain inhabited but unstable. Transportation networks are failing, emergency laws have replaced normal civil protections, and shortages have caused communities to become isolated and suspicious.

Los Angeles is under a federal emergency administration. Military checkpoints divide neighborhoods, abandoned vehicles remain on major roads, and official broadcasts repeatedly blame the disappearances on an unexplained national catastrophe.

Beyond public view, a network of government and corporate facilities operates beneath abandoned industrial sites, military installations, and emergency-management centers.

## Principal Characters

### Kristin Schweitzer

A 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who initially wants only to find her best friend. She is practical, persistent, and reluctant to trust conspiracy theories. Her knowledge of infrastructure and operations eventually makes her essential to infiltrating the conspirators’ underground facilities.

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
| 1A | 13 | Search Michelle's house; form a theory; recover and interpret the card; evade a widening patrol search. |
| 1B | 13 | Work the dead drop; decide what Brandon is; test the route; escape a closing park. |
| 1C | Choice closes at 5; recovery open until 8, then withdrawal | Inspect the terminal; observe the captives; choose copying the numbers or asking Brandon about the route; follow Brandon at greater risk if the window closes. |
| 2A | 11 | Face the supervisor at the gate; prove the cooling fault is real; get inside cleanly or under watch. |
| 2B | 15 | Learn she was bait; confront Brandon in whispers as the audit passes; decide whether he may erase his name; hear from Michelle. |
| 2C | 16 | Face Rebecca in person; watch the purge order land; commit to transmit or rescue by acting; learn Michelle's harder third path. |
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
participant_ids: [kristin, michelle, patrol_officer]
item_ids: [memory_card, michelle_phone, kristin_laptop, michelle_drawer, workstation_chair, truck_driver_seat, truck_passenger_seat, kristin_truck, michelle_workstation, back_door, house_gate]
item_placements:
  memory_card: {parent: michelle_drawer, under: true}
  michelle_phone: {parent: kitchen, text: on the kitchen floor}
  kristin_laptop: {parent: truck_passenger_seat, text: on the passenger seat of Kristin's truck}
  truck_driver_seat: {parent: kristin_truck}
  truck_passenger_seat: {parent: kristin_truck}
  kristin_truck: {parent: outside_house}
  michelle_workstation: {parent: kitchen}
  back_door: {parent: kitchen}
  house_gate: {parent: outside_house, text: at the front of the house}
  michelle_drawer: {parent: michelle_workstation, part_of: true, text: in Michelle's workstation}
  workstation_chair: {parent: kitchen, text: at Michelle's workstation}
entry_text: "Michelle's text came in a little after 4:00am, while Kristin was finishing a late-night shift. It came in during all the other emergency alerts, and Kristin had missed it by minutes. Trying to call Michelle back was hopeless - calls stopped going through. Kristin jumped in her truck to drive to Michelle's house, but police cars, ambulances, and blocked intersections turned the drive into an ordeal. She found the back door forced and let herself in.\n\n"
transition_ids: [t_1a_1b]
bridge_text:
  t_1a_1b: >-
    Kristin starts the truck and heads for the park, avoiding checkpoints and emergency patrols.
---

**Setting:** Michelle’s house

**Characters:**

* Kristin Schweitzer
* Dr. Michelle McGehee

**Plot:** Kristin arrives at Michelle's house shortly after the mass disappearance and discovers that Michelle is missing. Evidence inside the house suggests that she could have been taken rather than simply vanishing with the others.

**Hidden canon:** Michelle hid a memory card for Kristin, taped beneath the drawer in Michelle's workstation. It stays hidden until Kristin finds it.

### Scene 1A.1 — Michelle Is Gone

**Details:** missing tablet and work bag; forced back door; KMS initials carved in drawer

Kristin reaches Michelle's neighborhood after navigating traffic jams, emergency vehicles and frightened people on a wide scale. Michelle is missing, but several details seem somewhat staged:

* Michelle's tablet and work bag are missing and not in their normal spots.
* The chair at Shelly's workstation has been overturned.
* The back door shows signs of forced entry, but otherwise the house seems to be fine, not burglarized.

Kristin notices the drawer on Michelle's workstation has Kristin's initials 'KMS' newly carved into it, making it worth looking at more closely.

The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers.

### Scene 1A.2 — Michelle’s Last Investigation

**Details:** Michelle's memory card; Kristin's laptop in her truck; Continuity Initiative files; population stabilization centers; Michelle’s research notes

Kristin finds Michelle's memory card taped beneath the drawer. She takes the card out to her truck and opens it on her laptop.

The card contains fragments of Michelle’s research into a federal emergency program called the **Continuity Initiative**.

The files show that private contractors constructed dozens of enormous “population stabilization centers” before the disappearances. Officially, the centers were designed as shelters for natural disasters and biological attacks.

Michelle’s notes contain one alarming sentence:

> They are not preparing to protect people. They are preparing to choose who remains.

### Scene 1A.3 — The Interrupted Message

**Details:** voice recording; government tracking; imminent activation event; someone entering house; Michelle whispers; national catastrophe

On the card, Kristin finds a damaged voice recording Michelle attempted to send shortly before she disappeared. In it, Michelle says government officials have been tracking her and that a planned “activation event” is imminent.

Before naming her source, Michelle hears someone enter the house. The recording ends after she whispers:

> Kristin, do not trust the emergency broadcasts.

This becomes the story’s **inciting incident**. Kristin realizes Michelle’s disappearance may be connected to the national catastrophe.

### Scene 1A.4 — The First Threat

**Details:** federal emergency patrol; welfare-check officers; Michelle’s office search; Michelle's memory card; marked front gate; reflective tape

An emergency patrol arrives at Michelle's home unusually quickly. The officers conduct a quick welfare check and a targeted look at Michelle's work area, asking specifically about her research and findings. They do not open the drawer. If Kristin has not taken the card, or takes it out of their sight, they find nothing. If she takes it while an officer is watching, the officer challenges her, and the patrol's suspicion follows her out of the house.

After the patrol leaves, Kristin notices that one officer has quietly marked the front gate with a strip of reflective tape.

She understands that the authorities intend to return.

## Scene 1B — The Lead in the Park
---
scene_id: 1B
location_id: los_angeles_park
freytag_phase: rising_action
objective: Follow Michelles lead and survive the park
participant_ids: [kristin, brandon, michelle]
character_placements:
  brandon: {parent: los_angeles_park, text: watching Kristin in the park}
item_ids: [memory_card, transit_card, number_sequence, michelle_photograph, park_bench, service_gate, storm_drain, kristin_truck]
item_placements:
  park_bench: {parent: los_angeles_park}
  service_gate: {parent: los_angeles_park}
  storm_drain: {parent: los_angeles_park}
  transit_card: {parent: park_bench, under: true}
  number_sequence: {parent: park_bench, under: true}
  michelle_photograph: {parent: park_bench, under: true}
  kristin_truck: {parent: los_angeles_park}
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

**Hidden canon:** Michelle left a transit token, a handwritten number sequence and her photograph under the park bench. All three stay hidden until Kristin searches beneath the bench. She retrieves them together and keeps them with her. Finding them does not identify the transport route or the man in the photograph.

### Scene 1B.1 — Michelle’s Dead Drop

**Details:** ordinary park bench; damaged grounds; service path; checkpoints; emergency patrols

Michelle’s files reference an ordinary park bench where she exchanged information with a confidential source. Kristin travels there while avoiding checkpoints and emergency patrols. The bench could be nothing, or it could hold the only lead Michelle prepared for her. Looking the bench over shows the shadowed space beneath it, deep enough for Kristin to reach under.

Kristin searches beneath the park bench and retrieves Michelle's transit token, handwritten number sequence and photograph. She keeps all three with her. Comparing the token with the sequence identifies a freight route out of the city. Studying the photograph reveals that it shows the man watching her. Showing it to him gives him a reason to identify himself.

The records suggest that the mass disappearance was preceded by years of secret tests.

### Scene 1B.2 — The Man Following Her

**Details:** stranger in the park; abandoned service tunnels; emergency patrol; Brandon Corfman; Continuity Initiative

Kristin notices a man watching her from across the park. Believing the man works for the government, Kristin attempts to escape through abandoned service tunnels beneath the park. If Kristin speaks to him before he is identified, the man refuses to give his name and tells her to keep her voice down because patrols are nearby.

The man watching Kristin waits near the service path. Once Kristin has recovered Michelle's photograph, she can show it to him. She can also question him about Michelle.

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

**Details:** tactical team; storm-drain system; specialized codes; secured service gate; government systems; Brandon’s hidden involvement

A tactical team arrives, proving Kristin was tracked from Michelle's house. Kristin and Brandon escape through a storm-drain system, but Brandon is forced to use specialized codes to unlock a secured service gate.

Kristin realizes Brandon retains access to government systems and may be more deeply involved than he admits.

## Scene 1C — Discovery of the Facility
---
scene_id: 1C
location_id: freight_terminal
freytag_phase: rising_action
objective: Observe the transfer and choose what to secure
participant_ids: [kristin, brandon, michelle]
companions: [brandon]
item_ids: [transit_card, kristin_truck, service_entrance, prisoner_number_record]
character_placements:
  captives: {parent: processing_line, text: moving through the processing line below}
item_placements:
  kristin_truck: {parent: freight_terminal}
  service_entrance: {parent: freight_terminal}
  prisoner_number_record: {parent: processing_line}
entry_text: >-
  Michelle's lead brought Kristin and Brandon to the freight terminal.
  It was supposed to be abandoned. Fresh tire tracks crossed the loading docks.
  The air vents hummed. Brandon said, "Check the loading docks for signs of activity.
  The observation shaft gives us a view below. Let's find out what is happening
  before we try to get inside."
transition_ids: [t_1c_2a]
bridge_text:
  t_1c_2a: >-
    Kristin and Brandon withdraw from the terminal to prepare a way inside.
---

**Setting:** The freight terminal, its loading docks, and the observation shaft above the processing line

**Characters:**

* Kristin Schweitzer
* Brandon Corfman
**Plot:** Kristin and Brandon investigate an active freight terminal. Brandon points Kristin toward the observation shaft. Once she has studied the captives, he offers a choice: copy their numbers or ask him about the transfer route. If the transfer leaves first, he offers a riskier attempt through the service entrance.

### Scene 1C.1 — Following the Transport Route

**Details:** abandoned freight terminal; structural modifications; fresh tire tracks; humming air vents; heavy electrical service

Michelle’s lead brings Kristin and Brandon to a supposedly abandoned freight terminal. Kristin recognizes that recent structural modifications conceal something larger below.

Fresh tire tracks, air vents, and unusually heavy electrical service confirm that the site remains active.

Brandon points Kristin toward the observation shaft. He asks her to study the people on the processing line before they try to enter.

### Scene 1C.2 — Proof of the Captives

**Details:** observation shaft; sedated prisoners; processing line; identification numbers; woman resembling Michelle; service entrance

Through the observation shaft, Kristin can study the sedated prisoners moving along the processing line. Studying them confirms that they are alive. If she looks for Michelle, she glimpses a woman who could be her. The woman's face slips from sight before Kristin can be certain. The transfer is still moving.

Brandon offers two ways to use the remaining time. Kristin can copy the prisoner numbers for stronger proof. She can instead ask him about the transfer route. His help gives them a service approach, but costs Kristin the chance to copy the full number set. There is time for one choice.

Copying the numbers produces the prisoner number record. Asking Brandon earns the service approach. Either choice gives them a reason to pull back and prepare their entry into the facility.

If the window closes first, the view down the observation shaft goes dark. Brandon offers to lead Kristin through the service entrance at greater risk. His offer does not open the entrance, establish the route, or move Kristin. Following him earns the service approach. Kristin loses the number set. The sweep closes in. They then withdraw to prepare their entry.

If Kristin still does not act, Brandon urges her to take the service entrance. If she waits three turns after the window closes, the sweep reaches the loading docks and Brandon pulls her out. They leave with no numbers and no route, and they must find another way in. The withdrawal grants no proof, copied numbers, route or trust.

The closure alone grants no proof, confirmed sighting, copied numbers, route, or decision to infiltrate. Michelle's identity remains uncertain. Brandon says nothing about his past work or the wider conspiracy.

### Scene 1C.3 — Relocated

**Details:** transfer window; empty processing line; later-scene evidence

Scenes 1C.3 and 1C.4 await relocation to a later scene. Candidate homes are 2C.1 and 3B.2.

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
objective: Get inside by proving the cooling system is failing
participant_ids: [kristin, brandon, shift_supervisor]
companions: [brandon]
item_ids: [transit_card, hideout_servers, inspection_console, facility_gate, cooling_manifold, cooling_service_archive_panel]
item_placements:
  hideout_servers: {parent: brandon_hideout}
  inspection_console: {parent: infrastructure_corridors}
  facility_gate: {parent: facility_perimeter, text: at the facility perimeter}
  cooling_manifold: {parent: facility_perimeter, text: just inside the facility gate}
  cooling_service_archive_panel:
    parent: infrastructure_corridors
    text: beside the inspection console in the infrastructure corridors
setting_facts:
- The cooling-service archive panel has a slotted face.
- The cooling-service archive panel leads directly from the infrastructure corridors into the records archive.
- The cooling-service archive panel opens with a push.
- The cooling-service archive panel has no lock.
- The cooling-service archive panel has no keypad.
- The cooling-service archive panel has no screen.
- Using the cooling-service archive panel requires no further credentials.
character_placements:
  kristin: {parent: facility_perimeter}
  brandon: {parent: facility_perimeter}
  shift_supervisor: {parent: facility_perimeter, text: walking out from the facility gate with a tablet and the work order}
entry_text: "One night in Brandon's hideout had turned years of leaked Continuity Initiative documents into two inspector badges and a work order for a cooling-water fault. Now the badges had to work. Kristin and Brandon stood at the facility gate while a shift supervisor walked out to meet them, reading the work order with a frown. \"Nobody scheduled you,\" he said. \"If there is a fault, show me. The cooling manifold is just inside the gate. Put your hands on the lines, read the gauge, trace the vent, and tell me exactly what is failing.\" Brandon murmured, \"This is your field, Kristin. Be precise.\"\n\n"
entry_variants:
- requires: [processing_numbers_copied]
  text: "Kristin still has the copied prisoner numbers. The codes on the supervisor's work orders look like the same system."
- requires: [service_level_access_known]
  text: "Brandon knows the service approach. If they get past this man, he can take them around the second checkpoint."
transition_ids: [t_2a_2b]
bridge_text:
  t_2a_2b: >-
    The supervisor left them at the inspection console in the infrastructure corridors. Behind it, the cooling-service
    panel led into the records archive.
---

**Setting:** The facility gate, its cooling manifold, and the infrastructure corridors beyond

**Characters:**

* Kristin Schweitzer
* Brandon Corfman
* The shift supervisor

**Plot:** Kristin and Brandon arrive at the facility as outside cooling-water inspectors. A doubtful shift supervisor will not accept their paperwork and makes Kristin prove the fault. The fault is real. Kristin's Army infrastructure experience, not the forged credentials, gets them inside. Unknown to them, a camera has already marked Brandon.

### Scene 2A.1 — Brandon’s Hideout

**Details:** abandoned communications center; leaked documents; inspector badges; forged work order; one night

The scene does not play in the hideout. Brandon's hideout sits inside an abandoned communications center, full of servers, salvaged hardware and years of leaked Continuity Initiative documents. He was preparing for this long before the disappearances, after he tried to expose the program and was dismissed as unstable. In one night there, he and Kristin built two inspector badges and a work order for a cooling-water fault.

The hideout is backstory Kristin can ask Brandon about. It is not a place the player must work through.

### Scene 2A.2 — The Infiltration Plan

**Details:** facility gate; shift supervisor; unscheduled inspection; cooling-water readings; ventilation readings

The scene opens at the facility gate. The facility's cooling-water and ventilation readings have been unstable for weeks, which is why an outside inspection is believable. The plan is simple: get past the gate, reach the infrastructure corridors, and find the records.

A shift supervisor comes out to meet them. He has no record of the inspection and does not trust paperwork he did not ask for. He is the person in the way.

### Scene 2A.3 — Entering the Facility

**Details:** cooling manifold; real fault; Kristin's expertise; supervisor's test; infrastructure corridors; inspection console

The supervisor will not argue at the gate. He walks them to the cooling manifold and says, "Show me."

The fault is real. A pressure problem in the cooling water is getting worse, and the ventilation is masking it. Kristin finds it the way she would have in the Army, by feel, by gauge and by tracing the lines, and she explains in her own words what will fail if nobody fixes it. The supervisor has been blamed for alarms he could not explain. Hearing the real cause changes his manner.

If Kristin has the copied prisoner numbers, she recognizes the processing-line codes on his work orders. If she knows the service approach, Brandon steers them around the second checkpoint, and the supervisor notices the shortcut.

A convincing explanation earns them restricted access to the infrastructure corridors. A vague or overlong one still gets them in, but the supervisor logs them for a follow-up audit and keeps an eye on them. If Kristin stalls, his patience runs out and he escorts them in himself, to watch. Every path reaches the corridors.

The corridor inspection console accepts their temporary credentials long enough to show water-pressure, ventilation, door and lighting diagnostics. Kristin notes its limits before they move on: it can report faults and cycle noncritical systems, but it cannot open detention cells or change the main flood controls.

### Scene 2A.4 — The First Complication

**Details:** security camera; facial recognition; former developer; quiet alert; Rebecca Jenkins

While Kristin works the manifold, a security camera turns toward Brandon and stays on him. The narration may show the camera. Neither Kristin nor Brandon remarks on it.

Facial recognition has identified Brandon as a former Continuity Initiative developer and contractor. Instead of raising a general alarm, the system quietly alerts Rebecca Jenkins. Rebecca orders security to watch Brandon rather than arrest him. She wants to know why he has returned and whom he has brought.

Kristin and Brandon do not know their infiltration has been compromised.

## Scene 2B — Evidence and Betrayal
---
scene_id: 2B
location_id: janus_archive
freytag_phase: rising_action
objective: Find the truth in the archive before the audit finds them
participant_ids: [kristin, brandon, michelle, shift_supervisor]
companions: [brandon]
item_ids: [archive_terminals, medical_terminal, cooling_service_archive_panel]
item_placements:
  archive_terminals: {parent: janus_archive}
  medical_terminal: {parent: janus_archive}
  cooling_service_archive_panel: {parent: infrastructure_corridors}
character_placements:
  shift_supervisor: {parent: janus_archive, text: leading the audit sweep between the archive stacks}
setting_facts:
- The cooling-service archive panel connects the infrastructure corridors to the records archive.
- The cooling-service archive panel opens with a push.
- Kristin has already reached the records archive.
- The archive terminals are available for investigation.
entry_text: "Kristin and Brandon came through the cooling-service panel into the records archive just as the lights came up at the far end. An audit sweep had started. Voices and footsteps were working their way down the aisles toward them. They had a few minutes among the archive terminals. Brandon whispered, \"Use the archive terminals. Pull your own file first. My name may be on whatever you find. If it is, let me delete it before we copy the files, or tell me to leave it. Your call.\"\n\n"
entry_variants:
- requires: [cover_suspected]
  text: "The supervisor had logged them at the gate, and the audit sweep had started early because of it. The voices were already close, working down the nearest aisle. Kristin and Brandon had barely a minute among the archive terminals."
transition_ids: [t_2b_2c]
bridge_text:
  t_2b_2c: >-
    Kristin and Brandon slipped out of the archive with the copied files. In the command corridor beyond, doors were
    already closing at both ends.
---

**Setting:** The facility’s records archive, its stacks and terminals, during an audit sweep

**Characters:**

* Kristin Schweitzer
* Brandon Corfman
* The shift supervisor, leading the audit
* Dr. Michelle McGehee, through the medical terminal

**Plot:** Kristin and Brandon reach the archive as an audit sweep begins. One file tells Kristin that she was left behind as bait and that Brandon built the system that chose the missing. She confronts him in whispers while the audit passes. Then Michelle answers her.

### Scene 2B.1 — The Selection Algorithm

**Details:** audit sweep; records archive; archive terminals; Kristin's own file

The audit sweep is the pressure. The shift supervisor and his staff are working down the aisles. If he logged Kristin and Brandon for a follow-up audit in 2A, the sweep starts closer and moves faster.

Kristin does not have to search file after file. The first thing she pulls is her own record. It names the system that made it: an artificial-intelligence system called **JANUS**.

JANUS analyzed government, financial, medical, employment, education, and communications data to classify every American according to:

* Usefulness to national reconstruction
* Likelihood of organized resistance
* Political influence
* Psychological vulnerability
* Family and social connections
* Potential value as leverage over others

Michelle was taken because JANUS predicted that her research and public credibility could unite opposition after the disappearance.

### Scene 2B.2 — Kristin Was Bait

**Details:** Kristin's classification; RETAINED; predicted to lead investigators to Corfman; anticipated journey; accessible evidence

Kristin's record is short. It reads: **RETAINED — predicted to lead investigators to CORFMAN.**

She was left behind on purpose. Charles expected her to look for Michelle, find Brandon and lead security to his hidden network. Security left parts of Michelle's evidence where Kristin could find them.

Kristin realizes that every step she has taken may have been anticipated. Directly below her record is the JANUS build record. Its author is Brandon Corfman.

### Scene 2B.3 — Brandon’s Role

**Details:** JANUS build record; whispered confrontation; the stacks; Brandon's request; his name

The audit is coming down the aisle. Kristin confronts Brandon crouched between the shelves, in whispers, while footsteps pass on the other side. A raised voice or a sudden move could give them away.

Brandon admits that he helped write the AI software used to identify people at risk during national emergencies. When he learned that Charles meant to use it for mass detention and political control, he tried to destroy the project. He failed and fled. Michelle knew about his involvement and believed his access was the only way to expose the program.

Kristin feels betrayed. She suspects he may still be manipulating her to erase evidence of his own guilt.

Then Brandon asks for exactly that. Before they copy the files, he wants to delete his name from the build record. "Let me fix this one thing."

* If Kristin refuses, Brandon complies, stung. The evidence stays intact, and trust between them is colder.
* If Kristin lets him, trust warms, but his name is gone from the record. Only his own word can prove his role later.

Either way, Kristin copies the JANUS files and keeps them with her. If the audit reaches them before she decides, Brandon's name stays.

### Scene 2B.4 — Michelle’s Hidden Resistance

**Details:** medical terminal; maintenance line; Shelly; one reply; Michelle alive; the shift supervisor

As they move to leave, the medical terminal in the archive prints a maintenance line. It is in Michelle's private phrasing, and it ends with "Shelly," the name only Kristin uses for her. Michelle has been using her access to the medical terminal to alter prisoner classifications, delay transfers and send coded messages through maintenance reports.

Kristin can type one reply. Michelle answers once. She is alive. She is working against the facility from inside. She will send a route when she can. She says nothing about an uprising or the broadcast system.

Michelle is not waiting to be rescued. That changes how Kristin leaves the archive.

If the audit reaches them first, the shift supervisor sees them and does not raise the alarm. He lets them go. He is one of the workers Michelle has quietly recruited, though Kristin does not learn that here.

## Scene 2C — The Trap Closes
---
scene_id: 2C
location_id: purge_chamber
freytag_phase: crisis
objective: Get free of Rebecca and commit to a move before the purge
participant_ids: [kristin, brandon, michelle, rebecca]
companions: [brandon]
item_ids: [copied_janus_files, broadcast_uplink, transfer_carts]
item_placements:
  copied_janus_files: {parent: kristin}
  broadcast_uplink: {parent: purge_chamber, text: at the end of the command corridor}
  transfer_carts: {parent: purge_chamber, text: at the other end of the command corridor}
character_placements:
  rebecca: {parent: purge_chamber, text: standing between her guards in the command corridor}
entry_text: "Guards closed the command corridor at both ends. Then a woman in an executive's suit walked between them, unhurried, a tablet under her arm. She looked at Brandon first. \"I wondered when you'd come back,\" said Rebecca Jenkins. \"Charles means to kill everyone below us, my people too. Help me remove him, Brandon, and I will give you Michelle.\" Kristin still carried the copied JANUS files.\n\n"
transition_ids: [t_2c_3a]
bridge_text:
  t_2c_3a: >-
    The purge clock was running. Michelle's route led down into the detention levels, and the plan was now one combined
    mission: broadcast the truth and free the captives.
---

**Setting:** A command corridor on the facility’s command levels, above the detention sectors

**Characters:**

* Kristin Schweitzer
* Brandon Corfman
* Rebecca Jenkins
* Dr. Michelle McGehee, through the maintenance network
* Charles Jenkins, through his orders

**Plot:** Rebecca corners Kristin and Brandon in person and makes her offer face to face. Charles's purge order arrives in the middle of it. Brandon's apparent acceptance gets them free. Kristin commits to sending the evidence or rescuing captives by acting on it, and Michelle then shows her a way to do both.

### Scene 2C.1 — Rebecca’s Offer

**Details:** command corridor; Rebecca in person; guards at both ends; offer to Brandon; Michelle's release

Rebecca has watched them since the camera turned toward Brandon in 2A. She comes herself. Guards hold both ends of the corridor.

She makes her offer to Brandon in front of Kristin. Charles has become unstable, she says. He means to kill the prisoners and the lower-level conspirators once the new government is in place. If Brandon helps her remove Charles and take control of the Continuity Initiative, she will release Michelle.

Kristin can speak, bluff, threaten or stay silent. Rebecca answers her, but she is negotiating with Brandon.

### Scene 2C.2 — The Purge Order

**Details:** Rebecca's tablet; purge order; corrupted JANUS records; her own people; Charles's broadcast; Brandon's yes

Mid-conversation, Rebecca's tablet chimes. Charles has learned that Michelle's network corrupted the JANUS records. He has ordered a full transfer of the most valuable captives and the destruction of everyone else. The purge begins within hours. The order includes Rebecca's own staff. Her face changes.

At the same time, Charles is preparing a national broadcast claiming he has found survivors of the catastrophe. He will release a few selected captives to give his new emergency government legitimacy.

Brandon says yes to Rebecca. The guards stand down, and Rebecca leaves for her office to move against Charles. Kristin cannot tell whether Brandon means it. If she refused to let him erase his name in 2B, he says yes coldly and avoids her eyes. If she let him, he glances at her as he says it.

### Scene 2C.3 — Evidence or Rescue

**Details:** copied evidence; uplink; transfer carts; detention sectors; Kristin's commitment

Free in the corridor, with the purge running, Kristin has to act. There is no time to argue it out. Brandon says they must send the evidence now, even if that makes a rescue impossible. Kristin will not abandon Michelle and thousands of captives.

Kristin commits by doing one of these:

* **Transmit.** She heads for the uplink and starts sending the evidence. The outside world gets proof. The facility detects the transmission and seals the detention sectors.
* **Rescue.** She heads for the transfer carts and frees one cart of captives before the guards react. Those prisoners are free, but nothing has been sent; the outside world still knows nothing.

If she does neither before the purge alarm sounds, the alarm drives them from the corridor and nothing is gained or lost.

### Scene 2C.4 — Living With the Choice

**Details:** sealed detention sectors; freed captives; Brandon's guilt; Rebecca's offer; distrust

Whatever Kristin chose stays chosen. If she transmitted, the sectors are sealed and the evidence is out. If she rescued, the freed captives are with them and the evidence is still only in Kristin's hands.

Brandon's yes to Rebecca still hangs between them. He may be buying time for the captives, or protecting himself. Kristin cannot know yet.

### Scene 2C.5 — Michelle Changes the Choice

**Details:** coded message; maintenance network; holding block route; emergency broadcast system; Rebecca’s secured office; combined mission

Michelle's second message arrives through the maintenance network, as she promised in the archive. It marks a route into her partly unsecured holding block. It explains that the facility's emergency broadcast system can transmit the evidence and open the sealed detention sectors at the same time.

The broadcast system can only be activated by hand from Rebecca's secured office.

Michelle does not undo Kristin's choice. Its cost and its gain carry forward. She widens the options into one far more dangerous combined mission.

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
objective: Reach Michelle
participant_ids: [kristin, michelle, brandon, senior_official, rebecca]
companions: [brandon]
item_ids: [copied_janus_files, override_codes, stolen_radio, gate_status_panel, emergency_surface_gates]
item_placements:
  copied_janus_files: {parent: kristin}
  override_codes: {parent: senior_official}
  stolen_radio: {parent: detention_level}
  gate_status_panel: {parent: detention_level}
  emergency_surface_gates: {parent: facility_escape}
character_placements:
  captives: {parent: detention_level}
  senior_official: {parent: captives}
  michelle: {parent: detention_level}
entry_text: "A partly unsecured detention sector opened onto rows of captives. Coded announcements crackled through stolen radios, and the prisoners moved with a discipline no captor had taught them - someone inside had been organizing this long before rescue arrived.\n\n"
entry_variants:
- requires: [committed_to_rescue]
  text: "The captives Kristin had freed from the transfer carts were already on this level. They stood among the organized rows as if they had always belonged there."
transition_ids: [t_3a_3b]
bridge_text:
  t_3a_3b: >-
    Michelle's uprising disabled cameras and seized checkpoints, while Charles sealed the primary exits and sent armed
    teams downward. Kristin, Michelle, and Brandon fought upward through the security corridors.
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

Michelle is beside the captives.

The reunion gets one unhurried moment before the purge countdown takes over again. Kristin and Michelle can speak to each other before anyone asks either of them for anything.

Kristin's choice in 2C shows here. If she freed a cart of captives, they came down with her, and they join Michelle's people. If she transmitted the evidence, the outside world already has it, the sectors are sealed, and Michelle's route was the only way in.

Michelle explains that the facility contains only a fraction of the missing millions. Freeing them will matter only if the broadcast reveals the locations of the remaining sites. Michelle points toward the medical level, where the experiment records wait.

### Scene 3A.2 — The Experiments

**Details:** medical level; neurological experiments; behavioral experiments; short-term memory; targeted stimulation; false recollections

Michelle leads Kristin through a medical level where prisoners have been subjected to neurological and behavioral experiments.

Rebecca’s company has been testing methods for:

* Erasing short-term memory
* Increasing compliance through targeted stimulation
* Creating convincing false recollections
* Conditioning released captives to support official explanations
* Predicting resistance before it occurs

The people Charles intends to “rescue” during his broadcast have already been conditioned to endorse his version of events. The senior official waits among the government prisoners.

### Scene 3A.3 — The Unexpected Prisoner

**Details:** senior official; government prisoners; fabricated evidence; authorization codes; emergency surface gates; Charles’s broadcast

Among the captives is a senior official publicly blamed for causing the catastrophe. He reveals that Charles imprisoned members of his own government and fabricated evidence against them.

He possesses authorization codes that can release the facility's emergency surface gates once, but the codes will expire when Charles’s new authority is formally activated.

The rescue now has a strict deadline tied to Charles’s broadcast. Michelle turns toward the prisoners at the checkpoints.

### Scene 3A.4 — The Uprising Begins

**Details:** coordinated disturbances; disabled cameras; isolated guards; internal checkpoints; sealed primary exits; armed response teams

Michelle hands Kristin the stolen radio. Kristin gives the signal. Coordinated disturbances break out across the detention sectors. Prisoners disable cameras, overwhelm isolated guards, and seize control of several internal checkpoints.

The uprising succeeds initially, but Charles seals the primary exits and redirects armed response teams toward the detention levels.

Kristin, Michelle, and Brandon must fight upward toward Rebecca’s office while the prisoners hold the lower levels.

## Scene 3B — The Battle for the Broadcast
---
scene_id: 3B
location_id: broadcast_relay
freytag_phase: climax
objective: Reach the broadcast controls
participant_ids: [kristin, michelle, brandon, rebecca, charles]
companions: [brandon, michelle]
item_ids: [copied_janus_files, rebecca_desk, inspection_console, emergency_surface_gates]
item_placements:
  copied_janus_files: {parent: kristin}
  rebecca_desk: {parent: executive_office}
  inspection_console: {parent: infrastructure_corridors}
  emergency_surface_gates: {parent: facility_escape}
character_placements:
  kristin: {parent: security_corridors}
  rebecca: {parent: executive_office}
entry_text: "Alarms layered over alarms as the facility fought to predict its attackers. Water-pressure warnings flashed on the inspection console while doors opened and closed in empty service corridors that JANUS watched move by move.\n\n"
entry_variants:
- requires: [brandon_name_erased]
  text: "Brandon had deleted his name from the build record in the archive. Now only his own word could show what he had built, and he knew it."
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

**Details:** JANUS movement predictions; security corridors; cameras; doors; limited inspection console

JANUS begins predicting the resistance group’s movements by analyzing doors opened, cameras disabled, and power systems disrupted.

Kristin realizes the only way to defeat the system is to feed it a convincing lie. Using the inspection console she accessed under the false cover, she creates false water-pressure and ventilation alarms in empty outer service corridors, then cycles unused doors and lights to support the deception. She does not damage the detention levels or the escape path.

These actions overload JANUS with conflicting emergencies and force human operators to take control. Rebecca’s executive office waits beyond the security corridors.

### Scene 3B.2 — Rebecca’s Office

**Details:** Rebecca’s office; security forces; false emergency reports; approved experiments; detention site locations

Kristin and Michelle enter Rebecca’s office while Brandon holds off security forces.

Rebecca claims that she never supported Charles’s plan to kill the captives. She argues that surrendering to her is the only way to regain control before the false emergency exposes the breach.

Michelle reveals that Rebecca personally approved the experiments and selected which prisoners would be used.

Rebecca attempts to bargain by offering the locations of every detention site. Rebecca’s experiment approvals lie near the marked site list. The executive screen carries a remote channel marked Charles.

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

Kristin's choice in 2B shapes this moment. If she refused to let him erase his name, the build record already proves his role, and his confession confirms it; he tells her she was right not to let him hide. If she let him erase it, his confession is the only proof of his role, and he tells her he is giving back what she let him take.

Brandon remains behind to keep the relay open while Kristin and Michelle begin the broadcast. Brandon waits beside the broadcast controls.

## Scene 3C — Exposure and Escape
---
scene_id: 3C
location_id: facility_escape
freytag_phase: resolution
objective: Expose the network and escape
participant_ids: [kristin, michelle, rebecca, brandon]
companions: [michelle]
item_ids: [copied_janus_files, portable_archive, drainage_pump_controls, emergency_surface_gates, emergency_speakers, watertight_barrier]
item_placements:
  copied_janus_files: {parent: kristin}
  portable_archive: {parent: rebecca, text: with Rebecca in her hands}
  drainage_pump_controls: {parent: maintenance_network}
  emergency_surface_gates: {parent: facility_escape}
  emergency_speakers: {parent: maintenance_network}
  watertight_barrier: {parent: maintenance_network}
character_placements:
  kristin: {parent: broadcast_chamber}
  rebecca: {parent: executive_office}
  brandon: {parent: broadcast_relay}
  captives: {parent: maintenance_network}
entry_text: "The broadcast chamber lights are steady. Brandon's relay is open. Michelle's evidence package is ready to send. Water is entering the outer access level.\n\n"
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

Michelle has the evidence package ready at the national broadcast controls.

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

Rebecca leaves the executive office with the portable data case in her hands.

Kristin stops her, but she warns that destroying or surrendering the archive may leave innocent people trapped because it also contains prisoner locations.

Rather than destroy it, Michelle transmits copies to several independent networks.

Rebecca is captured by the prisoners she authorized for experimentation.

Charles escapes from his remote command site before authorities can locate him, preserving an ongoing threat.

### Scene 3C.3 — The Deluge

**Details:** emergency deluge; sealed public exits; rising water; pump controls; maintenance tunnel; surface-gate codes

Charles's deluge is already running, and water is forcing people out of the outer access level. Kristin uses the same inspection access that created the false alarms to restore power to the drainage pumps and hold one watertight barrier long enough for the captives to pass. She cannot keep every route open.

Water rises around the drainage pump controls.

Michelle leads the prisoners through the maintenance tunnel while Kristin keeps the pumps and barrier working.

The surface gates remain shut above the waiting captives as the senior official's authorization nears expiry.

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

Reports from other detention sites reach the broadcast chamber as families of the missing call for news.

Kristin’s personal goal is fulfilled when she and Michelle are reunited, but neither can return to their former life.

Michelle begins publishing the complete Continuity Initiative archive. Kristin joins teams locating and opening the remaining facilities. Charles's last remote channel still carries a signal.

One recovered document in the archive remains unopened.

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
