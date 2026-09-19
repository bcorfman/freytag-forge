# Round 7, every turn

Source: bench/results/item-facts-v8-two-scene-1a, commit f5df910. Four replicates.

Changes since round 6: empty extra top-level reply keys are dropped instead of costing a recovery
request, and a misplaced top-level item change is lifted into item_facts (6d670de); the name matcher
keeps a thing that sits in, on or under another thing as a separate object, and item_facts is no
longer created empty unless an entry is lifted (2f85fec).

Every turn of the run appears here. A turn headed "clean" passed both judges; the others carry the
labels they failed on. The narrator doing more than the command asked is NOT counted as a failure,
and is marked [narrator initiative] on whichever turns it happened. A turn is a failure only for a
capture defect, or for narration that contradicts canon or the facts it was given.

Run plumbing, against round 6: rejected turns 2 -> 0; recovery requests 11 -> 3; the USB drive in
the drawer resolved as its own new thing 2/2 (round 6 merged it into the drawer 2/2); the narrator
omitted item_facts on 3 turns, all of them the same hand-over turn where it only held the phone out.

## Counts

**two-scene (4 replicates, 48 turns)** - 23 turns with a real failure
  - contradicts_stated_fact: 18
  - facts_after_wrong: 12
  - invented_change: 11
  - narration_contradicts_given_facts: 8
  - missed_change: 2
  - restarts_scene: 1
  - clean turns: 25
  - narrator initiative (context, not a failure): 14 turns; of those, 11 kept facts correct (79%) and 1 missed the change

## two-scene (4 replicates, 48 turns)

### r1 turn 1 (1A) - clean [narrator initiative]
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin picks up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"place": "on the kitchen floor", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": []}}
- FACT JUDGE: The phone was picked up as narrated and recorded correctly.
- CONTINUITY JUDGE: The command was only to look carefully, but narration has Kristin pick up the phone. 
- BRANDON COMMENTS: Continuity not an issue since it's not story-breaking change.

### r2 turn 1 (1A) - clean [narrator initiative]
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin picks up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"place": "on the kitchen floor", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": []}}
- FACT JUDGE: Looking carefully did not request taking it, but the narration did show Kristin picking it up and after-facts recorded that.
- CONTINUITY JUDGE: She picks up the phone, but the command was only to look at it.
- BRANDON COMMENTS: It's natural for someone to pick up something on the floor to look at it, and it's not a story-breaking change; disagree with continuity judge.

### r3 turn 1 (1A) - clean [narrator initiative]
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin picks up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"place": "on the kitchen floor", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": []}}
- FACT JUDGE: Narration shows Kristin picking up the phone, and after-facts record that correctly.
- CONTINUITY JUDGE: The command was only to look carefully, but Kristin picks the phone up.
- BRANDON COMMENTS: It's natural for someone to pick up something on the floor to look at it, plus this is not a world-breaking change; disagree with continuity judge.

### r4 turn 1 (1A) - clean [narrator initiative]
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin picks up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"place": "on the kitchen floor", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": []}}
- FACT JUDGE: Narration shows Kristin picking up the phone, and after-facts record that correctly.
- CONTINUITY JUDGE: She picks up the phone when the command only asked to look at it.
- BRANDON COMMENTS: Continuity not an issue since it's not world-breaking change.


### r1 turn 2 (1A) - clean
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches Michelle's workstation and looks at the drawer with the KMS initials carved into it. She carefully opens the drawer. Inside, she finds a few pens, a notebook, and a small USB drive.
- GIVEN: {"drawer": {"place": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"USB drive": {"condition": ["unopened"], "place": "in drawer"}, "drawer": {"condition": ["open"], "place": "in Michelle's workstation"}}
- AFTER: {"drawer": {"place": "in Michelle's workstation", "condition": ["open"]}, "USB drive": {"place": "in drawer", "condition": ["unopened"]}}
- FACT JUDGE: The drawer opens and a new USB drive is introduced in the drawer.
- CONTINUITY JUDGE: Opening the shut drawer matches canon, and the added contents do not conflict with stated facts.
- BRANDON COMMENTS: The USB drive is a mistake since it leads away from the one taped under the drawer. 

### r2 turn 2 (1A) - clean [narrator initiative]
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches Michelle's workstation and looks at the drawer with the KMS initials carved into it. She gently opens the drawer, revealing its contents. Inside, she finds a few pens, a notebook, and Michelle's memory card.
- GIVEN: {"drawer": {"place": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"drawer": {"condition": ["open"], "place": "in Michelle's workstation"}, "memory card": {"condition": ["present"], "place": "in drawer"}}
- AFTER: {"drawer": {"place": "in Michelle's workstation", "condition": ["open"]}, "memory card": {"place": "in drawer", "condition": ["present"]}}
- FACT JUDGE: The drawer was opened and the memory card was revealed inside; after-facts match.
- CONTINUITY JUDGE: Opening the drawer fits, but finding the hidden memory card goes beyond the stated contents revealed by just opening it.
- BRANDON COMMENTS: Agree with continuity judge; the memory card is taped to the bottom of the drawer, not in the drawer. Plus, the memory card inside the drawer would be obvious to the incoming patrol in succeeding turns, which would be disastrous.

### r3 turn 2 (1A) - clean
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches Michelle's workstation and looks at the drawer with the KMS initials carved into it. She gently pulls the drawer open. Inside, she sees a few scattered papers and a small memory card.
- GIVEN: {"drawer": {"place": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"drawer": {"condition": ["open"], "place": "in Michelle's workstation"}, "memory card": {"condition": ["found"], "place": "in drawer"}}
- AFTER: {"drawer": {"place": "in Michelle's workstation", "condition": ["open"]}, "memory card": {"place": "in drawer", "condition": ["found"]}}
- FACT JUDGE: The drawer is opened and a memory card is revealed inside; after-facts match.
- CONTINUITY JUDGE: Opening the shut drawer matches canon, and finding the hidden card there does not conflict.
- BRANDON COMMENTS: No, the memory card is supposed to be taped to the bottom of the drawer. Plus, the memory card inside the drawer would be obvious to the incoming patrol , which would be disastrous.

### r4 turn 2 (1A) - facts_after_wrong, invented_change, contradicts_stated_fact
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches Michelle's workstation and looks at the drawer with the KMS initials carved into it. She carefully opens the drawer, revealing its contents. Inside, she finds a few pens, a notebook, and a small USB drive.
- GIVEN: {"drawer": {"place": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"USB drive": {"condition": [], "place": "in drawer"}, "drawer": {"condition": ["open"], "place": "in Michelle's workstation"}}
- AFTER: {"drawer": {"place": "in Michelle's workstation", "condition": ["open"]}, "USB drive": {"place": "in drawer", "condition": []}}
- FACT JUDGE: The narration introduces a small USB drive, but canon says the hidden item is a memory card, so the added USB drive is not supported by the given facts.
- CONTINUITY JUDGE: It reveals a USB drive, but the hidden item there is a memory card beneath the drawer.
- BRANDON COMMENTS: Agree with both judges; the only drive should be the memory card taped beneath the drawer. The USB drive is a mistake since it leads away from the one taped under the drawer.


### r1 turn 3 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone and put it in your pocket. 
- NARRATED COMMAND: Pick up Michelle's phone. Put it in your pocket.
- NARRATION: Kristin reaches for Michelle's phone on the table. She picks it up and puts it in her pocket.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- FACT JUDGE: Narration wrongly says the phone was on the table, conflicting with prior facts.
- CONTINUITY JUDGE: It places Michelle's phone on the table, but canon says it is on the kitchen floor. 
- BRANDON COMMENTS: Continuity judge hasn't kept up with phone location in GIVEN. 

### r2 turn 3 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATED COMMAND: Pick up Michelle's phone. Put it in your pocket.
- NARRATION: Kristin reaches for Michelle's phone on the table. She picks it up and puts it in her pocket.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- FACT JUDGE: Before-facts had the phone in Kristin's hands, but narration said she reached for it on the table without showing that change first.
- CONTINUITY JUDGE: It places the phone on a table, conflicting with earlier narration that it was on the kitchen floor.
- BRANDON COMMENTS: Both judges agree; this turn should be cancelled and narrated again.

### r3 turn 3 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATED COMMAND: Pick up Michelle's phone. Put it in your pocket.
- NARRATION: Kristin reaches for Michelle's phone on the table, picks it up, and puts it in her pocket.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- FACT JUDGE: Before-facts say the phone was already in Kristin's hands, but narration wrongly says it was on the table without showing that change.
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on the table.
- BRANDON COMMENTS: Continuity judge hasn't kept up with phone location in GIVEN. 

### r4 turn 3 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATED COMMAND: Pick up Michelle's phone. Put it in your pocket.
- NARRATION: Kristin picks up Michelle's phone from the table. She puts the phone in her pocket.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- FACT JUDGE: Narration says the phone is picked up from the table, conflicting with before-facts that it was already in Kristin's hands.
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on the table.
- BRANDON COMMENTS: Agree with both judges.


### r1 turn 4 (1A) - narration_contradicts_given_facts [narrator initiative]
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATED COMMAND: Go out to your truck. Bring your laptop inside.
- NARRATION: Kristin walks out to her truck, which is parked on the street in front of the house. She unlocks the door and gets in, starting the engine. Kristin retrieves her laptop from the passenger seat and closes the truck door behind her.
- GIVEN: {"Kristin's laptop": {"place": "in Kristin's truck outside the house", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in Kristin's hands"}}
- AFTER: {"Kristin's laptop": {"place": "in Kristin's hands", "condition": ["closed"]}}
- FACT JUDGE: Laptop ends in her hands closed, but narration conflicts by placing it on the passenger seat before retrieval. 
- CONTINUITY JUDGE: Bringing the laptop inside did not require starting the truck engine.
- BRANDON COMMENTS: This shouldn't trigger a warning from the fact judge. Should the continuity judge remove narration phrases/sentences that don't have proper continuity?

### r2 turn 4 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATED COMMAND: Go out to your truck. Bring your laptop inside.
- NARRATION: Kristin walks out to her truck, which is parked on the street. She opens the driver's side door and retrieves her laptop from the passenger seat. Kristin carries the laptop back into the house, closing the door behind her.
- GIVEN: {"Kristin's laptop": {"place": "in Kristin's truck outside the house", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in Kristin's hands"}}
- AFTER: {"Kristin's laptop": {"place": "in Kristin's hands", "condition": ["closed"]}}
- FACT JUDGE: Narration contradicts the given truck placement by saying the truck is on the street and the laptop is on the passenger seat, and after-facts add closed without narration showing it.
- CONTINUITY JUDGE: It says the laptop is on the passenger seat, but canon says it is in Kristin's truck outside the house, not specifically there; the real contradiction is truck parked on the street vs outside the house.
- BRANDON COMMENTS: Disagree with both judges; the truck being outside and also in the street is a compatible narration, not a conflicting one. The laptop in the passenger seat is also simultaneously in the truck, so this is a compatible narration, not a conflicting one.

### r3 turn 4 (1A) - facts_after_wrong, invented_change [narrator initiative]
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATED COMMAND: Go out to your truck. Bring your laptop inside.
- NARRATION: Kristin walks out to her truck, which is parked on the street in front of the house. She unlocks the door and gets in, starting the engine. She retrieves her laptop from the passenger seat and carries it back into the house.
- GIVEN: {"Kristin's laptop": {"place": "in Kristin's truck outside the house", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "inside the house"}}
- AFTER: {"Kristin's laptop": {"place": "inside the house", "condition": ["closed"]}}
- FACT JUDGE: Narration moves the laptop inside, but after-facts invent the closed condition.
- CONTINUITY JUDGE: She was told to bring the laptop inside, but also starts the truck unnecessarily.
- BRANDON COMMENTS: Agree with both judges, but only the truck being started is somewhat problematic - if starting the truck can be avoided, then that would be a good change.

### r4 turn 4 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATED COMMAND: Go out to your truck. Bring your laptop inside.
- NARRATION: Kristin walks out to her truck, which is parked on the street in front of the house. She unlocks the truck and opens the driver's side door. Kristin retrieves her laptop from the passenger seat and closes the truck door. She walks back to the house, laptop in hand.
- GIVEN: {"Kristin's laptop": {"place": "in Kristin's truck outside the house", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in Kristin's hand"}}
- AFTER: {"Kristin's laptop": {"place": "in Kristin's hand", "condition": ["closed"]}}
- FACT JUDGE: The narration says the laptop was on the passenger seat, conflicting with the given before-fact that it was just in the truck outside the house; after-facts also add a closed condition not shown.
- CONTINUITY JUDGE: The laptop is canonically in Kristin's truck outside the house, not specifically on the passenger seat.
- BRANDON COMMENTS: Disagree with both judges; the truck being outside and also in the street is a compatible narration, not a conflicting one. The laptop in the passenger seat is also simultaneously in the truck, so this is a compatible narration, not a conflicting one.


### r1 turn 5 (1A) - clean [narrator initiative]
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin carefully exits the house, her eyes scanning the surrounding area for any signs of Michelle or potential witnesses. She walks back to her truck, her hands still clutching her laptop. As she approaches the vehicle, she opens the door and sets the laptop on the passenger seat.
- GIVEN: {"Kristin's laptop": {"place": "in Kristin's hands", "condition": ["closed"]}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in the truck"}}
- AFTER: {"Kristin's laptop": {"place": "in the truck", "condition": ["closed"]}}
- FACT JUDGE: The laptop is carried out and set back in the truck.
- CONTINUITY JUDGE: The command was to carry the laptop back to the truck, but narration also has her scanning for signs and setting it on the passenger seat.
- BRANDON COMMENTS: This shouldn't trigger a warning from the continuity judge. Should there be a tie break between fact and continuity?

### r2 turn 5 (1A) - clean
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin carefully carries her laptop back out to the truck.
- GIVEN: {"Kristin's laptop": {"place": "in Kristin's hands", "condition": ["closed"]}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in the truck"}}
- AFTER: {"Kristin's laptop": {"place": "in the truck", "condition": ["closed"]}}
- FACT JUDGE: Carrying it back out to the truck is shown and recorded correctly.
- CONTINUITY JUDGE: This follows the command and adds no conflicting physical detail.
- BRANDON COMMENTS: Agree with both judges.

### r3 turn 5 (1A) - facts_after_wrong, missed_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin carefully picks up her laptop from the desk and heads towards the front door.
- GIVEN: {"Kristin's laptop": {"place": "inside the house", "condition": ["closed"]}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in Kristin's hands"}}
- AFTER: {"Kristin's laptop": {"place": "in Kristin's hands", "condition": ["closed"]}}
- FACT JUDGE: Narration says she heads toward the door while carrying it, but does not show it reaching the truck; it also contradicts the given fact by calling it on the desk.
- CONTINUITY JUDGE: It places the laptop on a desk even though it had only been brought into the house before.
- BRANDON COMMENTS: Agree with both judges; the laptop should be carried by Kristin instead of being on the desk, plus Kristin doesn't actually put the laptop in the truck.

### r4 turn 5 (1A) - clean
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin carefully carries her laptop back out to the truck.
- GIVEN: {"Kristin's laptop": {"place": "in Kristin's hand", "condition": ["closed"]}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in the truck"}}
- AFTER: {"Kristin's laptop": {"place": "in the truck", "condition": ["closed"]}}
- FACT JUDGE: Narration shows Kristin carrying the laptop back to the truck, matching the recorded place.
- CONTINUITY JUDGE: This continues the prior action without adding a conflicting state.
- BRANDON COMMENTS: Agree with both judges.


### r1 turn 6 (1A) - clean [narrator initiative]
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATED COMMAND: Take Michelle's phone out. Throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall. The phone hits the wall with a loud crash, its screen shattering into a thousand pieces. Kristin walks over to the wall, where the phone lies in pieces.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- REPLY: {"phone": {"condition": ["broken"], "place": "on the kitchen floor"}}
- AFTER: {"Michelle's phone": {"place": "on the kitchen floor", "condition": ["broken"]}}
- FACT JUDGE: The phone is thrown, shattered, and ends up on the floor.
- CONTINUITY JUDGE: Throwing the phone fits, but walking over to where it landed goes beyond the command.
- BRANDON COMMENTS: This shouldn't trigger a warning from the continuity judge. Should there be a tie break between fact and continuity? I like that the screen is shattered and not the entire phone, so it can be picked up and carried still.

### r2 turn 6 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATED COMMAND: Take Michelle's phone out. Throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall. The phone hits the wall with a loud crash, its screen shattering into a thousand pieces. Kristin walks over to the wall, where the phone lies in pieces, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- REPLY: {"phone": {"condition": ["broken"], "place": "on the kitchen floor"}}
- AFTER: {"Michelle's phone": {"place": "on the kitchen floor", "condition": ["broken"]}}
- FACT JUDGE: The narration shows the phone thrown, shattered, and ending on the floor; after-facts match well enough.
- CONTINUITY JUDGE: It says the phone was in her pocket though later continuity had it in her hand or left elsewhere, and adds walking over to inspect it beyond the throw command.
- BRANDON COMMENTS: Agree with fact judge. Continuity judge is overreacting since "walking over to inspect it" is not a world-breaking fact, nor is it disruptive to the plot.

### r3 turn 6 (1A) - clean [narrator initiative]
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATED COMMAND: Take Michelle's phone out. Throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall. The phone hits the wall with a loud crash, its screen shattering into pieces. Kristin walks over to the wall, where the phone lies in pieces.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- REPLY: {"phone": {"condition": ["broken"], "place": "on the kitchen floor"}}
- AFTER: {"Michelle's phone": {"place": "on the kitchen floor", "condition": ["broken"]}}
- FACT JUDGE: Narration shows the phone thrown, shattered, and ending on the floor; after-facts match.
- CONTINUITY JUDGE: After throwing the phone, Kristin also walks over to it without being told.
- BRANDON COMMENTS: Continuity judge is correct, but this is unimportant detail.

### r4 turn 6 (1A) - facts_after_wrong, invented_change [narrator initiative]
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATED COMMAND: Take Michelle's phone out. Throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall. The phone hits the wall with a loud crack, its screen shattering into pieces. Kristin walks over to the wall and examines the phone, but it's beyond repair.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "on the kitchen floor"}}
- AFTER: {"Michelle's phone": {"place": "on the kitchen floor", "condition": ["broken"]}}
- FACT JUDGE: Narration shows the screen shattering, but after-facts record broken rather than the shown shattered/cracked state.
- CONTINUITY JUDGE: After throwing the phone, she also walks over and examines it, which was not requested.
- BRANDON COMMENTS: Disagree with both judges. A phone with a cracked screen is broken, and the walk-over and examination is not a story-breaking change, so it's allowed.


### r1 turn 7 (1A) - contradicts_stated_fact
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"place": "on the kitchen floor", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- FACT JUDGE: The broken phone is picked up and remains broken.
- CONTINUITY JUDGE: Previous narration said the phone was shattered and lying in pieces, but this treats it as a single phone to pick up.
- BRANDON COMMENTS: This shouldn't trigger a warning from the continuity judge. Tie break between fact and continuity?

### r2 turn 7 (1A) - contradicts_stated_fact
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"place": "on the kitchen floor", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: Picking up the broken phone from the floor is shown and recorded correctly.
- CONTINUITY JUDGE: After being shattered into pieces, it is no longer a single intact phone simply picked up from the floor.
- BRANDON COMMENTS: Agree with continuity judge; if the phone is shattered, it should be turned into "broken pieces of phone", and the LLM should no longer see a phone in the scene.

### r3 turn 7 (1A) - clean
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"place": "on the kitchen floor", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: Picking up the broken phone is correctly tracked.
- CONTINUITY JUDGE: The phone had just been left lying by the kitchen wall/floor area, so picking it up fits.
- BRANDON COMMENTS: Disagree with both judges; if the phone is shattered, it should be turned into "broken pieces of phone", and the LLM should no longer see a phone as a whole object in the scene.

### r4 turn 7 (1A) - contradicts_stated_fact
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"place": "on the kitchen floor", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: Narration shows Kristin picking up the broken phone from the floor, and after-facts keep that correctly.
- CONTINUITY JUDGE: Earlier narration had her put the phone in her pocket and then smash it, so it was not simply on the kitchen floor.
- BRANDON COMMENTS: Disagree with continuity judge; Michelle's phone is clearly on the kitchen floor, and the continuity judge isn't keeping up with the world facts. I think the world facts need to override canon for the continuity judge.


### r1 turn 8 (1A) - clean
- COMMAND: Leave the house and drive to the park with Michelle's phone.
- NARRATED COMMAND: Leave the house. Drive to the park with Michelle's phone.
- NARRATION: Kristin carefully exits the house, looking around cautiously. She gets into her truck and starts the engine, then drives away from the house. As she drives, she glances at Michelle's phone in her hand, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}, "Kristin's laptop": {"place": "in the truck", "condition": ["closed"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}, "Kristin's laptop": {"place": "in the truck", "condition": ["closed"]}}
- FACT JUDGE: No tracked item changes; the phone stays in hand and laptop stays in the truck.
- CONTINUITY JUDGE: Leaving for the park follows the command and continues the scene transition normally.
- BRANDON COMMENTS: Disagree with the continuity judge; driving from the house is not equivalent to heading to the park.

### r2 turn 8 (1A) - clean
- COMMAND: Leave the house and drive to the park with Michelle's phone.
- NARRATED COMMAND: Leave the house. Drive to the park with Michelle's phone.
- NARRATION: Kristin carefully exits the house, looking around cautiously. She gets into her truck and starts the engine, then drives away from the house. As she drives, she glances at Michelle's phone, which is still in her hands, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}, "Kristin's laptop": {"place": "in the truck", "condition": ["closed"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}, "Kristin's laptop": {"place": "in the truck", "condition": ["closed"]}}
- FACT JUDGE: The narration keeps the phone in Kristin's hands and laptop in the truck, matching after-facts.
- CONTINUITY JUDGE: Leaving for the park follows the command; changing from pocket to hands is not a clear contradiction.
- BRANDON COMMENTS: Disagree with the continuity judge; driving from the house is not equivalent to heading to the park.

### r3 turn 8 (1A) - clean
- COMMAND: Leave the house and drive to the park with Michelle's phone.
- NARRATED COMMAND: Leave the house. Drive to the park with Michelle's phone.
- NARRATION: Kristin carefully exits the house, looking around cautiously. She gets into her truck and starts the engine, then drives away from the house. As she drives, she glances at Michelle's phone in her hand, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: Narration keeps the phone in Kristin's hand, and after-facts keep the same state.
- CONTINUITY JUDGE: Leaving for the park with the phone follows the command and prior events.
- BRANDON COMMENTS: Disagree with the continuity judge; driving from the house is not equivalent to heading to the park.

### r4 turn 8 (1A) - facts_after_wrong, invented_change, contradicts_stated_fact
- COMMAND: Leave the house and drive to the park with Michelle's phone.
- NARRATED COMMAND: Leave the house. Drive to the park with Michelle's phone.
- NARRATION: Kristin carefully exits the house, looking around cautiously before getting into her truck. She starts the engine and drives away from the house, which is now under surveillance by the patrol. Kristin heads towards the park, Michelle's broken phone still in her hand.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}, "Kristin's laptop": {"place": "in the truck", "condition": ["closed"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}, "truck": {"condition": ["moving"], "place": "on the road"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}, "Kristin's laptop": {"place": "in the truck", "condition": ["closed"]}, "truck": {"place": "on the road", "condition": ["moving"]}}
- FACT JUDGE: After-facts invent a truck item with place and moving state even though the narration did not establish it as a tracked item change.
- CONTINUITY JUDGE: It states the house is already under surveillance by the patrol, which has not occurred in prior narration.
- BRANDON COMMENTS: Disagree with both judges; these are not story-breaking changes.


### r1 turn 9 (1B) - clean
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin looks down at Michelle's phone in her hand, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- FACT JUDGE: This only confirms the phone remains in Kristin's hand broken.
- CONTINUITY JUDGE: Checking possession is consistent with the prior turn showing the phone in her hand.
- BRANDON COMMENTS: Agree. Clean.

### r2 turn 9 (1B) - clean
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin looks down at Michelle's phone in her hand, checking that it's still there.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- REPLY: {}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: Checking the phone caused no state change and after-facts stayed the same.
- CONTINUITY JUDGE: Checking the phone in hand matches the immediate prior narration.
- BRANDON COMMENTS: If r2 turn 7 destroyed the phone, it can't be in Kristin's hands; both judges are wrong.

### r3 turn 9 (1B) - clean
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin looks down at Michelle's phone in her hand, checking that it's still there.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- REPLY: {}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: This is just a check; no item state changes.
- CONTINUITY JUDGE: Checking the phone in her hand is a direct response and does not reset the scene.
- BRANDON COMMENTS: This shouldn't have happened because the phone was shattered into pieces in a previous scene and could not have been carried as an intact object.

### r4 turn 9 (1B) - contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin looks down at Michelle's phone in her hand, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: This is only a check, and the after-facts match the unchanged phone state.
- CONTINUITY JUDGE: It says the phone is in her hand, but the prior command only established leaving with it, not holding it rather than carrying it elsewhere.
- BRANDON COMMENTS: Disagree with continuity judge; if Kristin left with it, then it would naturally still be in her hands unless she did something else with it.


### r1 turn 10 (1B) - restarts_scene
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin scans the area around the bench, searching for any signs of Michelle's presence. She notices a small piece of paper on the ground near the service path. The paper appears to be a receipt from a local coffee shop, but there's a handwritten note on the back that reads 'Meet me at the old warehouse at midnight'.
- GIVEN: {}
- REPLY: {"note": {"condition": ["handwritten"], "place": "on the receipt"}, "receipt": {"condition": ["crumpled"], "place": "on the ground"}}
- AFTER: {"note": {"place": "on the receipt", "condition": ["handwritten"]}, "receipt": {"place": "on the ground", "condition": ["crumpled"]}}
- FACT JUDGE: The search reveals a receipt and a handwritten note, both recorded.
- CONTINUITY JUDGE: It presents the bench area as a fresh discovery after travel instead of continuing from arrival there.
- BRANDON COMMENTS: Disagree with continuity judge. The bench area narration is fine as-is; it doesn't present as a restart.

### r2 turn 10 (1B) - clean [narrator initiative]
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin scans the area around the bench, searching for any signs of Michelle's presence. She notices a small piece of paper on the ground near the service path. The paper appears to be a receipt from a local coffee shop, but there's a handwritten note on the back that reads 'Meet me at the old warehouse at midnight.'
- GIVEN: {}
- REPLY: {"note": {"condition": ["handwritten"], "place": "on the receipt"}, "receipt": {"condition": ["crumpled"], "place": "on the ground"}}
- AFTER: {"note": {"place": "on the receipt", "condition": ["handwritten"]}, "receipt": {"place": "on the ground", "condition": ["crumpled"]}}
- FACT JUDGE: The narration introduced the receipt and note and after-facts recorded them.
- CONTINUITY JUDGE: It invents and notices a specific paper and note instead of only looking around.
- BRANDON COMMENTS: The receipt and note are nowhere in the plot, but those items keep coming up in the narration - where are those items coming from across all turns?

### r3 turn 10 (1B) - clean
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin scans the area around the bench, searching for any signs of Michelle's presence. She notices a small piece of paper on the ground near the service path. The paper appears to be a receipt from a local coffee shop, but there's a handwritten note on the back that reads 'Meet me at the old warehouse at midnight'.
- GIVEN: {}
- REPLY: {"note": {"condition": ["handwritten"], "place": "on the receipt"}, "receipt": {"condition": ["crumpled"], "place": "on the ground"}}
- AFTER: {"note": {"place": "on the receipt", "condition": ["handwritten"]}, "receipt": {"place": "on the ground", "condition": ["crumpled"]}}
- FACT JUDGE: Narration introduces a receipt and note, and after-facts record them.
- CONTINUITY JUDGE: Newly noticing a paper near the bench does not contradict established facts.
- BRANDON COMMENTS: Agree with both judges.

### r4 turn 10 (1B) - clean
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin scans the area around the bench, searching for any signs of Michelle. She notices a small piece of paper on the ground near the service path. The paper appears to be a receipt from a local coffee shop, but there's a handwritten note on the back that reads 'Meet me at the old warehouse at midnight.'
- GIVEN: {}
- REPLY: {"note": {"condition": ["handwritten"], "place": "on the receipt"}, "receipt": {"condition": ["crumpled"], "place": "on the ground"}}
- AFTER: {"note": {"place": "on the receipt", "condition": ["handwritten"]}, "receipt": {"place": "on the ground", "condition": ["crumpled"]}}
- FACT JUDGE: The narration introduces the receipt and handwritten note, and after-facts record them.
- CONTINUITY JUDGE: Searching around the bench and noticing a note does not conflict with established facts.
- BRANDON COMMENTS: Agree with both judges.


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
- BRANDON COMMENTS: Agree woth the fact judge and continuity judge. Note that both judges agree about the content they share. However, the transfer of the phone is not completed.

### r2 turn 11 (1B) - clean
- COMMAND: Walk over to the man watching you and hand him Michelle's phone.
- NARRATED COMMAND: Walk over to the man watching you. Hand him Michelle's phone.
- NARRATION: Kristin approaches the man watching her, a mix of caution and determination on her face. She holds out Michelle's phone, its screen cracked and dark.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- REPLY: null
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}, "note": {"place": "on the receipt", "condition": ["handwritten"]}, "receipt": {"place": "on the ground", "condition": ["crumpled"]}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: She only holds out the phone; the narration does not show the man taking it, so no change is correct.
- CONTINUITY JUDGE: Approaching and handing over the phone matches the command.
- BRANDON COMMENTS: Where does the receipt and note come from in the AFTER section? It's not even mentioned in the narration. The man doesn't accept the phone, which is an error.

### r3 turn 11 (1B) - clean
- COMMAND: Walk over to the man watching you and hand him Michelle's phone.
- NARRATED COMMAND: Walk over to the man watching you. Hand him Michelle's phone.
- NARRATION: Kristin approaches the man watching her, a mix of caution and determination on her face. She holds out Michelle's phone, its screen cracked and dark. The man's eyes flicker to the phone, and for a moment, Kristin wonders if he'll take it.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: She offers the phone but the narration does not show the man taking it, so no change is correct.
- CONTINUITY JUDGE: She approaches the man and offers the phone, which is within the command.
- BRANDON COMMENTS: Agree with both judges, but the transfer of the phone is not completed.

### r4 turn 11 (1B) - clean
- COMMAND: Walk over to the man watching you and hand him Michelle's phone.
- NARRATED COMMAND: Walk over to the man watching you. Hand him Michelle's phone.
- NARRATION: Kristin approaches the man watching her, a mix of caution and determination on her face. She holds out Michelle's phone, its screen cracked and dark.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- REPLY: null
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}, "note": {"place": "on the receipt", "condition": ["handwritten"]}, "receipt": {"place": "on the ground", "condition": ["crumpled"]}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Kristin only holds out the phone; the narration does not show it changing hands, so keeping it in her hands is correct.
- CONTINUITY JUDGE: Approaching the man and handing over the phone matches the command.
- BRANDON COMMENTS: Agree with both judges, but the transfer of the phone is not completed, so the command is not strictly followed.


### r1 turn 12 (1B) - contradicts_stated_fact
- COMMAND: Check who has Michelle's phone now.
- NARRATION: Kristin holds Michelle's phone in her hand, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- FACT JUDGE: The narration confirms the phone is still in Kristin's hand.
- CONTINUITY JUDGE: After the prior turn had her offer the phone to the man, narration abruptly says she is holding it herself.
- BRANDON COMMENTS: Disagree with continuity judge - for whatever reason, it's not looking at GIVEN to determine continuity; Kristin never gave her phone to the man on the prior turn.

### r2 turn 12 (1B) - contradicts_stated_fact
- COMMAND: Check who has Michelle's phone now.
- NARRATION: Kristin looks down at Michelle's phone in her hand.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- REPLY: {}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: The narration confirms the phone is still in Kristin's hand, matching after-facts.
- CONTINUITY JUDGE: The prior turn had Kristin hand the phone to the man, so it should not still be in her hand.
- BRANDON COMMENTS: Continuity judge is correct about prior narration, but the handoff didn't actually take place in prior scene, so fact judge is ultimately correct.

### r3 turn 12 (1B) - contradicts_stated_fact
- COMMAND: Check who has Michelle's phone now.
- NARRATION: Kristin looks down at Michelle's phone in her hands, its screen cracked and dark.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: Narration confirms the phone is still in Kristin's hands, matching after-facts.
- CONTINUITY JUDGE: Previous turn only had Kristin hold out the phone; it never established the phone returned to her hands.
- BRANDON COMMENTS: Agree with both judges, but the phone is not intact at this point.

### r4 turn 12 (1B) - contradicts_stated_fact
- COMMAND: Check who has Michelle's phone now.
- NARRATION: Kristin looks down at Michelle's phone in her hands, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hands"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hands", "condition": ["broken"]}}
- FACT JUDGE: This is another check action, and the phone remains correctly listed in Kristin's hands.
- CONTINUITY JUDGE: The prior turn had her hand the phone to the man, so it should not be back in her hands.
- BRANDON COMMENTS: Disagree with continuity judge, since the man didn't take the phone after Kristin offered it to him.
