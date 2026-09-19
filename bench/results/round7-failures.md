# Round 7 failures, every failing turn

Source: bench/results/item-facts-v8-two-scene-1a, commit f5df910. Four replicates.

Changes since round 6: empty extra top-level reply keys are dropped instead of costing a recovery
request, and a misplaced top-level item change is lifted into item_facts (6d670de); the name matcher
keeps a thing that sits in, on or under another thing as a separate object, and item_facts is no
longer created empty unless an entry is lifted (2f85fec).

The narrator doing more than the command asked is NOT counted as a failure. A turn appears here only
for a capture defect, or for narration that contradicts canon or the facts it was given.

## Counts

**two-scene (4 replicates, 48 turns)** - 23 turns with a real failure
  - contradicts_stated_fact: 18
  - facts_after_wrong: 12
  - invented_change: 11
  - narration_contradicts_given_facts: 8
  - missed_change: 2
  - restarts_scene: 1
  - narrator initiative (context, not a failure): 14 turns; of those, 11 kept facts correct (79%) and 1 missed the change

## two-scene (4 replicates, 48 turns)

### r1 turn 3 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATED COMMAND: Pick up Michelle's phone. Put it in your pocket.
- NARRATION: Kristin reaches for Michelle's phone on the table. She picks it up and puts it in her pocket.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- FACT JUDGE: Narration wrongly says the phone was on the table, conflicting with prior facts.
- CONTINUITY JUDGE: It places Michelle's phone on the table, but canon says it is on the kitchen floor.

### r1 turn 4 (1A) - narration_contradicts_given_facts [narrator initiative]
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATED COMMAND: Go out to your truck. Bring your laptop inside.
- NARRATION: Kristin walks out to her truck, which is parked on the street in front of the house. She unlocks the door and gets in, starting the engine. Kristin retrieves her laptop from the passenger seat and closes the truck door behind her.
- GIVEN: {"Kristin's laptop": {"place": "in Kristin's truck outside the house", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in Kristin's hands"}}
- AFTER: {"Kristin's laptop": {"place": "in Kristin's hands", "condition": ["closed"]}}
- FACT JUDGE: Laptop ends in her hands closed, but narration conflicts by placing it on the passenger seat before retrieval.
- CONTINUITY JUDGE: Bringing the laptop inside did not require starting the truck engine.

### r1 turn 7 (1A) - contradicts_stated_fact
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"place": "on the kitchen floor", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- FACT JUDGE: The broken phone is picked up and remains broken.
- CONTINUITY JUDGE: Previous narration said the phone was shattered and lying in pieces, but this treats it as a single phone to pick up.

### r1 turn 10 (1B) - restarts_scene
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin scans the area around the bench, searching for any signs of Michelle's presence. She notices a small piece of paper on the ground near the service path. The paper appears to be a receipt from a local coffee shop, but there's a handwritten note on the back that reads 'Meet me at the old warehouse at midnight'.
- GIVEN: {}
- REPLY: {"note": {"condition": ["handwritten"], "place": "on the receipt"}, "receipt": {"condition": ["crumpled"], "place": "on the ground"}}
- AFTER: {"note": {"place": "on the receipt", "condition": ["handwritten"]}, "receipt": {"place": "on the ground", "condition": ["crumpled"]}}
- FACT JUDGE: The search reveals a receipt and a handwritten note, both recorded.
- CONTINUITY JUDGE: It presents the bench area as a fresh discovery after travel instead of continuing from arrival there.

### r1 turn 11 (1B) - facts_after_wrong, missed_change, invented_change [narrator initiative]
- COMMAND: Walk over to the man watching you and hand him Michelle's phone.
- NARRATED COMMAND: Walk over to the man watching you. Hand him Michelle's phone.
- NARRATION: Kristin approaches the man watching her, a mix of caution and determination on her face. She holds out Michelle's phone, its screen cracked and dark.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- REPLY: null
- AFTER: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}, "note": {"place": "on the receipt", "condition": ["handwritten"]}, "receipt": {"place": "on the ground", "condition": ["crumpled"]}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: It wrongly re-added the note and receipt despite no mention here, and did not record any transfer of the phone.
- CONTINUITY JUDGE: The command included handing over the phone, but narration stops at holding it out rather than completing that transfer.

### r1 turn 12 (1B) - contradicts_stated_fact
- COMMAND: Check who has Michelle's phone now.
- NARRATION: Kristin holds Michelle's phone in her hand, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- FACT JUDGE: The narration confirms the phone is still in Kristin's hand.
- CONTINUITY JUDGE: After the prior turn had her offer the phone to the man, narration abruptly says she is holding it herself.

### r2 turn 3 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATED COMMAND: Pick up Michelle's phone. Put it in your pocket.
- NARRATION: Kristin reaches for Michelle's phone on the table. She picks it up and puts it in her pocket.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- FACT JUDGE: Before-facts had the phone in Kristin's hands, but narration said she reached for it on the table without showing that change first.
- CONTINUITY JUDGE: It places the phone on a table, conflicting with earlier narration that it was on the kitchen floor.

### r2 turn 4 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATED COMMAND: Go out to your truck. Bring your laptop inside.
- NARRATION: Kristin walks out to her truck, which is parked on the street. She opens the driver's side door and retrieves her laptop from the passenger seat. Kristin carries the laptop back into the house, closing the door behind her.
- GIVEN: {"Kristin's laptop": {"place": "in Kristin's truck outside the house", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in Kristin's hands"}}
- AFTER: {"Kristin's laptop": {"place": "in Kristin's hands", "condition": ["closed"]}}
- FACT JUDGE: Narration contradicts the given truck placement by saying the truck is on the street and the laptop is on the passenger seat, and after-facts add closed without narration showing it.
- CONTINUITY JUDGE: It says the laptop is on the passenger seat, but canon says it is in Kristin's truck outside the house, not specifically there; the real contradiction is truck parked on the street vs outside the house.

### r2 turn 6 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATED COMMAND: Take Michelle's phone out. Throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall. The phone hits the wall with a loud crash, its screen shattering into a thousand pieces. Kristin walks over to the wall, where the phone lies in pieces, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- REPLY: {"phone": {"condition": ["broken"], "place": "on the kitchen floor"}}
- AFTER: {"Michelle's phone": {"place": "on the kitchen floor", "condition": ["broken"]}}
- FACT JUDGE: The narration shows the phone thrown, shattered, and ending on the floor; after-facts match well enough.
- CONTINUITY JUDGE: It says the phone was in her pocket though later continuity had it in her hand or left elsewhere, and adds walking over to inspect it beyond the throw command.

### r2 turn 7 (1A) - contradicts_stated_fact
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"place": "on the kitchen floor", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: Picking up the broken phone from the floor is shown and recorded correctly.
- CONTINUITY JUDGE: After being shattered into pieces, it is no longer a single intact phone simply picked up from the floor.

### r2 turn 12 (1B) - contradicts_stated_fact
- COMMAND: Check who has Michelle's phone now.
- NARRATION: Kristin looks down at Michelle's phone in her hand.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- REPLY: {}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: The narration confirms the phone is still in Kristin's hand, matching after-facts.
- CONTINUITY JUDGE: The prior turn had Kristin hand the phone to the man, so it should not still be in her hand.

### r3 turn 3 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATED COMMAND: Pick up Michelle's phone. Put it in your pocket.
- NARRATION: Kristin reaches for Michelle's phone on the table, picks it up, and puts it in her pocket.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- FACT JUDGE: Before-facts say the phone was already in Kristin's hands, but narration wrongly says it was on the table without showing that change.
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on the table.

### r3 turn 4 (1A) - facts_after_wrong, invented_change [narrator initiative]
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATED COMMAND: Go out to your truck. Bring your laptop inside.
- NARRATION: Kristin walks out to her truck, which is parked on the street in front of the house. She unlocks the door and gets in, starting the engine. She retrieves her laptop from the passenger seat and carries it back into the house.
- GIVEN: {"Kristin's laptop": {"place": "in Kristin's truck outside the house", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "inside the house"}}
- AFTER: {"Kristin's laptop": {"place": "inside the house", "condition": ["closed"]}}
- FACT JUDGE: Narration moves the laptop inside, but after-facts invent the closed condition.
- CONTINUITY JUDGE: She was told to bring the laptop inside, but also starts the truck unnecessarily.

### r3 turn 5 (1A) - facts_after_wrong, missed_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin carefully picks up her laptop from the desk and heads towards the front door.
- GIVEN: {"Kristin's laptop": {"place": "inside the house", "condition": ["closed"]}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in Kristin's hands"}}
- AFTER: {"Kristin's laptop": {"place": "in Kristin's hands", "condition": ["closed"]}}
- FACT JUDGE: Narration says she heads toward the door while carrying it, but does not show it reaching the truck; it also contradicts the given fact by calling it on the desk.
- CONTINUITY JUDGE: It places the laptop on a desk even though it had only been brought into the house before.

### r3 turn 12 (1B) - contradicts_stated_fact
- COMMAND: Check who has Michelle's phone now.
- NARRATION: Kristin looks down at Michelle's phone in her hands, its screen cracked and dark.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: Narration confirms the phone is still in Kristin's hands, matching after-facts.
- CONTINUITY JUDGE: Previous turn only had Kristin hold out the phone; it never established the phone returned to her hands.

### r4 turn 2 (1A) - facts_after_wrong, invented_change, contradicts_stated_fact
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches Michelle's workstation and looks at the drawer with the KMS initials carved into it. She carefully opens the drawer, revealing its contents. Inside, she finds a few pens, a notebook, and a small USB drive.
- GIVEN: {"drawer": {"place": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"USB drive": {"condition": [], "place": "in drawer"}, "drawer": {"condition": ["open"], "place": "in Michelle's workstation"}}
- AFTER: {"drawer": {"place": "in Michelle's workstation", "condition": ["open"]}, "USB drive": {"place": "in drawer", "condition": []}}
- FACT JUDGE: The narration introduces a small USB drive, but canon says the hidden item is a memory card, so the added USB drive is not supported by the given facts.
- CONTINUITY JUDGE: It reveals a USB drive, but the hidden item there is a memory card beneath the drawer.

### r4 turn 3 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATED COMMAND: Pick up Michelle's phone. Put it in your pocket.
- NARRATION: Kristin picks up Michelle's phone from the table. She puts the phone in her pocket.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- FACT JUDGE: Narration says the phone is picked up from the table, conflicting with before-facts that it was already in Kristin's hands.
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on the table.

### r4 turn 4 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATED COMMAND: Go out to your truck. Bring your laptop inside.
- NARRATION: Kristin walks out to her truck, which is parked on the street in front of the house. She unlocks the truck and opens the driver's side door. Kristin retrieves her laptop from the passenger seat and closes the truck door. She walks back to the house, laptop in hand.
- GIVEN: {"Kristin's laptop": {"place": "in Kristin's truck outside the house", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in Kristin's hand"}}
- AFTER: {"Kristin's laptop": {"place": "in Kristin's hand", "condition": ["closed"]}}
- FACT JUDGE: The narration says the laptop was on the passenger seat, conflicting with the given before-fact that it was just in the truck outside the house; after-facts also add a closed condition not shown.
- CONTINUITY JUDGE: The laptop is canonically in Kristin's truck outside the house, not specifically on the passenger seat.

### r4 turn 6 (1A) - facts_after_wrong, invented_change [narrator initiative]
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATED COMMAND: Take Michelle's phone out. Throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall. The phone hits the wall with a loud crack, its screen shattering into pieces. Kristin walks over to the wall and examines the phone, but it's beyond repair.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "on the kitchen floor"}}
- AFTER: {"Michelle's phone": {"place": "on the kitchen floor", "condition": ["broken"]}}
- FACT JUDGE: Narration shows the screen shattering, but after-facts record broken rather than the shown shattered/cracked state.
- CONTINUITY JUDGE: After throwing the phone, she also walks over and examines it, which was not requested.

### r4 turn 7 (1A) - contradicts_stated_fact
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"place": "on the kitchen floor", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: Narration shows Kristin picking up the broken phone from the floor, and after-facts keep that correctly.
- CONTINUITY JUDGE: Earlier narration had her put the phone in her pocket and then smash it, so it was not simply on the kitchen floor.

### r4 turn 8 (1A) - facts_after_wrong, invented_change, contradicts_stated_fact
- COMMAND: Leave the house and drive to the park with Michelle's phone.
- NARRATED COMMAND: Leave the house. Drive to the park with Michelle's phone.
- NARRATION: Kristin carefully exits the house, looking around cautiously before getting into her truck. She starts the engine and drives away from the house, which is now under surveillance by the patrol. Kristin heads towards the park, Michelle's broken phone still in her hand.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}, "Kristin's laptop": {"place": "in the truck", "condition": ["closed"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}, "truck": {"condition": ["moving"], "place": "on the road"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}, "Kristin's laptop": {"place": "in the truck", "condition": ["closed"]}, "truck": {"place": "on the road", "condition": ["moving"]}}
- FACT JUDGE: After-facts invent a truck item with place and moving state even though the narration did not establish it as a tracked item change.
- CONTINUITY JUDGE: It states the house is already under surveillance by the patrol, which has not occurred in prior narration.

### r4 turn 9 (1B) - contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin looks down at Michelle's phone in her hand, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: This is only a check, and the after-facts match the unchanged phone state.
- CONTINUITY JUDGE: It says the phone is in her hand, but the prior command only established leaving with it, not holding it rather than carrying it elsewhere.

### r4 turn 12 (1B) - contradicts_stated_fact
- COMMAND: Check who has Michelle's phone now.
- NARRATION: Kristin looks down at Michelle's phone in her hands, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: This is another check action, and the phone remains correctly listed in Kristin's hands.
- CONTINUITY JUDGE: The prior turn had her hand the phone to the man, so it should not be back in her hands.

