# Round 4 failures, every failing turn

Source: bench/results/item-facts-v3-place-*, commit d969ed8. Four replicates each.

The narrator doing more than the command asked is NOT counted as a failure: a narrated
change belongs to the world whoever caused it, and the only reason to refuse one is that it
breaks the story. Turns where that happened are annotated `narrator initiative` for context,
and the number that matters - whether those changes were captured - is in the counts below.
A turn appears here only for a capture defect, or for narration that contradicts canon or the

## Counts

**two-scene (4 replicates, 47 turns)** - 27 turns with a real failure
  - facts_after_correct: 19
  - missed_change: 13
  - contradicts_stated_fact: 12
  - narration_contradicts_given_facts: 7
  - invented_change: 6
  - restarts_scene: 2
  - narrator initiative (context, not a failure): 25 turns; of those, 15 kept facts correct (60%) and 7 missed the change

**40-turn (4 replicates, 159 turns)** - 93 turns with a real failure
  - facts_after_correct: 54
  - contradicts_stated_fact: 54
  - missed_change: 34
  - narration_contradicts_given_facts: 32
  - invented_change: 20
  - dropped_true_condition: 11
  - restarts_scene: 10
  - kept_ended_condition: 3
  - narrator initiative (context, not a failure): 68 turns; of those, 39 kept facts correct (57%) and 25 missed the change

facts it was given.

## two-scene (4 replicates, 47 turns)

### r1 turn 2 (1A) - contradicts_stated_fact
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches the desk and looks at the drawer with her initials carved into it. She gently pulls the drawer open. Inside, she sees a small note with the initials 'KMS'.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"drawer": {"condition": []}, "note": {"place": "in the drawer"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name drawer held for matching", "item_facts name note held for matching"]
- FACT JUDGE: The drawer is opened in the narration, and the shut condition is correctly removed.

### r1 turn 3 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATION: Kristin reaches into her pocket and pulls out Michelle's phone, which she had found on the floor near the back door.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in her pocket"}}
- AFTER: {"Michelle's phone": {"where": "in her pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration says she pulls the phone from her pocket, conflicting with before-facts, and after-facts newly put it in her pocket without narration showing that.

### r1 turn 6 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATION: Kristin reaches into Michelle's pocket and pulls out her phone. She looks at the phone and then throws it hard against the kitchen wall. The phone's screen cracks, but it still seems to be working.
- GIVEN: {"Michelle's phone": {"where": "in her pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["cracked"], "place": "on the kitchen floor"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen floor", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration conflicts by saying the phone was in Michelle's pocket, and after-facts add it to the kitchen floor without the narration showing where it landed.

### r1 turn 7 (1A) - contradicts_stated_fact
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen floor", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["cracked"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration clearly shows Kristin picking up the cracked phone from the floor.

### r1 turn 8 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Leave the house and drive to the park with Michelle's phone.
- NARRATION: Kristin carefully exits the house, locking the back door behind her. She gets into her truck, starts the engine, and begins to drive away from the house. As she drives, she glances down at Michelle's phone in her hand, its cracked screen reflecting the morning light.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration does not clearly change tracked item locations or conditions beyond still having the phone in hand.

### r1 turn 9 (1B) - contradicts_stated_fact, restarts_scene
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin looks down at Michelle's phone in her hand, its cracked screen reflecting the dim light of the quiet house.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["cracked"]}}
- REPLY: {"Michelle's phone": {"condition": ["cracked"], "place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": ["cracked"]}}
- FACT JUDGE: This just restates that Michelle's phone is in her hand with the cracked condition unchanged.

### r1 turn 11 (1B) - facts_after_correct, missed_change
- COMMAND: Walk over to the man watching you and hand him Michelle's phone.
- NARRATION: Kristin walks over to the man watching her, her eyes fixed on him. She hands him Michelle's phone, her hand extended in a deliberate gesture.
- GIVEN: {}
- REPLY: null
- AFTER: {}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration clearly shows Kristin handing the phone to the man, but after-facts record nothing.

### r1 turn 12 (1B) - facts_after_correct, invented_change [narrator initiative]
- COMMAND: Check who has Michelle's phone now.
- NARRATION: Kristin looks around the park, her eyes scanning the area for any sign of Michelle or potential threats.
- GIVEN: {"Michelle's phone": {"where": "in her hand", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}}
- REPLY: {}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}}
- FACT JUDGE: Narration does not show any phone transfer, but after-facts keep Michelle's phone in her hand.

### r2 turn 3 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATION: Kristin reaches into the living room and picks up Michelle's phone, which was lying on the coffee table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration wrongly says the phone was on the coffee table even though before-facts had it in Kristin's hand.

### r2 turn 5 (1A) - facts_after_correct, missed_change, invented_change
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin carefully makes her way back to her truck, laptop in hand.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "in the truck"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration only shows Kristin carrying the laptop to the truck, not placing it in the truck, but after-facts move it there.

### r2 turn 6 (1A) - facts_after_correct, missed_change [narrator initiative]
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall. The phone hits the wall with a loud crash, its screen shattering into pieces. Kristin walks over to the wall and picks up the phone, examining it for any clues.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["damaged"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration ends with Kristin picking up the shattered phone, but after-facts leave it in her pocket.

### r2 turn 7 (1A) - facts_after_correct, narration_contradicts_given_facts [narrator initiative]
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the floor. She examines the phone, noticing that it's damaged. The screen is cracked, and the back is scratched.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["damaged"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration says she picks the phone up from the floor, conflicting with before-facts that had it in her pocket.

### r2 turn 8 (1A) - facts_after_correct, missed_change [narrator initiative]
- COMMAND: Leave the house and drive to the park with Michelle's phone.
- NARRATION: Kristin carefully exits the house, locking the back door behind her. She gets into her truck and starts the engine, then carefully places Michelle's phone on the passenger seat. Kristin drives through the quiet streets, eventually arriving at the park where she knows she can find some peace and think about her next move.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration explicitly says Kristin places the phone on the passenger seat, but after-facts keep it in her hand.

### r2 turn 9 (1B) - contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin looks down at Michelle's phone in her hand, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["damaged"]}}
- REPLY: {"Michelle's phone": {"condition": ["damaged"], "place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": ["damaged"]}}
- FACT JUDGE: Narration and after-facts both show the damaged phone in her hand.

### r2 turn 10 (1B) - facts_after_correct, missed_change
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin looks around the bench, scanning the area for any signs of Michelle's presence. She notices a small piece of paper on the ground near the service path. The paper appears to be a receipt from a local coffee shop, but there's a handwritten note on the back that reads 'Meet me at the old warehouse at midnight.'
- GIVEN: {"Michelle's phone": {"where": "in her hand", "condition": ["damaged"]}}
- REPLY: {"receipt": {"condition": ["crumpled"], "place": "on the ground near the service path"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": ["damaged"]}}
- ISSUES: ["item_facts name receipt held for matching"]
- FACT JUDGE: Narration introduces a piece of paper in a specific place, but after-facts do not add it.

### r3 turn 3 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATION: Kristin reaches into the living room and picks up Michelle's phone, which was left on the coffee table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: After-facts fit the action, but narration wrongly says the phone was on the coffee table despite before-facts saying it was already in her hand.

### r3 turn 5 (1A) - facts_after_correct, missed_change
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin carefully makes her way back to her truck, laptop in hand.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "in the truck"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration only shows her carrying the laptop to the truck, not leaving it there, so after-facts miss that it remains in hand.

### r3 turn 6 (1A) - facts_after_correct, missed_change [narrator initiative]
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall. The phone hits the wall with a loud crack, but it doesn't shatter completely. Kristin walks over to the wall and picks up the phone, examining it for any signs of damage.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen floor"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen floor", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration says she picked the phone up after throwing it, and implies damage, but after-facts leave it on the floor with no damage.

### r3 turn 9 (1B) - facts_after_correct, invented_change, narration_contradicts_given_facts
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin checks her pocket and feels the familiar shape of Michelle's phone.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in her pocket"}}
- AFTER: {"Michelle's phone": {"where": "in her pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration contradicts before-facts by saying she checks her pocket while the phone was in her hand, and after-facts invent moving it to her pocket.

### r3 turn 10 (1B) - facts_after_correct, missed_change [narrator initiative]
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin looks around the bench, scanning the area for any signs of Michelle's presence. She notices a small piece of paper on the ground near the service path. Picking it up, she sees that it's a receipt from a local coffee shop, but there's a handwritten note on the back that reads 'Meet me at the old warehouse at midnight'.
- GIVEN: {"Michelle's phone": {"where": "in her pocket", "condition": []}}
- REPLY: {"note": {"condition": ["handwritten"], "place": "on the receipt"}, "receipt": {"condition": ["crumpled"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in her pocket", "condition": []}}
- ISSUES: ["item_facts name note held for matching", "item_facts name receipt held for matching"]
- FACT JUDGE: Narration introduces and places a piece of paper and has Kristin pick it up, but after-facts omit it entirely.

### r3 turn 11 (1B) - facts_after_correct, missed_change
- COMMAND: Walk over to the man watching you and hand him Michelle's phone.
- NARRATION: Kristin walks over to the man watching her, her eyes fixed on his face. She hands him Michelle's phone, her hand extended in a deliberate gesture.
- GIVEN: {"Michelle's phone": {"where": "in her pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in her pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration says Kristin hands the man Michelle's phone, but after-facts wrongly keep it in her pocket.

### r4 turn 2 (1A) - contradicts_stated_fact
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches the desk and looks at the drawer with her initials carved into it. She gently pulls the drawer open. Inside, she finds a small note with the initials KMS.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"drawer": {"condition": []}, "note": {"place": "in the drawer"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}, "note": {"where": "in the drawer", "conditio
- ISSUES: ["item_facts name drawer held for matching", "item_facts name note held for matching"]
- FACT JUDGE: The drawer is opened and a note is newly found inside it.

### r4 turn 3 (1A) - facts_after_correct, invented_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATION: Kristin reaches into the living room and picks up Michelle's phone, which was left on the coffee table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}, "note": {"where": "in the drawer", "conditio
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}, "note": {"where": "in the drawer", "condit
- FACT JUDGE: Narration wrongly says the phone was on the coffee table, and after-facts invent pocketing not shown.

### r4 turn 6 (1A) - facts_after_correct, missed_change [narrator initiative]
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall. The phone hits the wall with a loud crack, but it doesn't shatter completely. Kristin walks over to the wall and picks up the phone, examining it for any signs of damage.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen floor"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen floor", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration ends with Kristin picking the phone up, but after-facts leave it on the floor.

### r4 turn 9 (1B) - contradicts_stated_fact [narrator initiative]
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin looks down at Michelle's phone in her hand, its screen dark and unresponsive.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": []}}
- FACT JUDGE: Wording change from Kristin to her hand means the same thing.

### r4 turn 10 (1B) - facts_after_correct, missed_change [narrator initiative]
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin looks around the bench, searching for any signs of Michelle's presence. She notices a small piece of paper on the ground near the bench, partially hidden by the shadows. The paper appears to be a receipt from a local coffee shop, but there's a handwritten note on the back that reads 'Meet me at the old warehouse at midnight.'
- GIVEN: {"Michelle's phone": {"where": "in her hand", "condition": []}}
- REPLY: {"bench": {}, "paper": {}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": []}}
- FACT JUDGE: Narration introduces a paper near the bench, but after-facts omit it.

### r4 turn 12 (1B) - restarts_scene [narrator initiative]
- COMMAND: Check who has Michelle's phone now.
- NARRATION: Kristin looks around the park, her eyes scanning the area for any sign of Michelle or potential threats. She spots a man sitting on a bench, his eyes fixed on her, and her instincts tell her he's been following her. The man's hand is in his pocket, and Kristin's eyes widen as she realizes Michelle's phone is in his possession.
- GIVEN: {"Michelle's phone": {"where": "in the man's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}, "note": {"where": "in the drawer", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in the man's pocket"}, "man": {"condition": ["sitting"], "place": "on the bench"}}
- AFTER: {"Michelle's phone": {"where": "in the man's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}, "note": {"where": "in the drawer", "condition": []}}
- ISSUES: ["item_facts name man held for matching"]
- FACT JUDGE: Narration only confirms the phone is still in the man's possession.

## 40-turn (4 replicates, 159 turns)

### r1 turn 2 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says the phone is picked up from the table though it was already in Kristin's hand.

### r1 turn 6 (1A) - facts_after_correct, missed_change, kept_ended_condition
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin walks over to the desk and opens the carved drawer.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"carved drawer": {"place": "open"}, "drawer": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- ISSUES: ["item_facts name carved drawer held for matching", "item_facts name drawer held for matching"]
- FACT JUDGE: Narration opens the drawer but after-state still keeps it shut.

### r1 turn 7 (1A) - facts_after_correct, missed_change, kept_ended_condition [narrator initiative]
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin walks over to the desk and opens the top drawer, revealing a neatly organized space with various office supplies and Michelle's research notes.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration again shows the drawer opened, but after-state still says shut.

### r1 turn 8 (1A) - contradicts_stated_fact
- COMMAND: Close the drawer.
- NARRATION: Kristin approaches Michelle's carved drawer, which is currently shut.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"condition": ["shut"]}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration only says the drawer is currently shut, matching before and after.

### r1 turn 11 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the driver's side door, revealing her laptop inside.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her truck"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration wrongly places the laptop back in the truck without showing that move, and after-state changes it to the truck anyway.

### r1 turn 12 (1A) - facts_after_correct, missed_change, contradicts_stated_fact [narrator initiative]
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully removes Michelle's phone from her jacket pocket and heads to her truck to plug it into her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's truck"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows the phone plugged into the laptop, but after-state only moves it to the truck and omits the plugged-in relation/charging state.

### r1 turn 13 (1A) - facts_after_correct, missed_change, contradicts_stated_fact [narrator initiative]
- COMMAND: Look at the back door.
- NARRATION: Kristin recovers Michelle's memory card from under the drawer carved with her initials, KMS, and reads the files on it. The card identifies the federal emergency program as the Continuity Initiative, which was preparing to choose who remains.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"back door": {"condition": ["damaged"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- ISSUES: ["item_facts name back door held for matching"]
- FACT JUDGE: Narration introduces and recovers the memory card, but after-state does not list it.

### r1 turn 14 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the charger and holds it in her hand. The phone feels cold and heavy, but there's no sign of any damage or unusual activity. Kristin checks the phone's screen, but it's locked and there's no indication of any recent activity.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows the phone unplugged and held, and after-state records it in Kristin's hand.

### r1 turn 16 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Close your laptop.
- NARRATION: Kristin gets out of her truck and walks towards the house, then opens the driver's side door and reaches in to close her laptop.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Closing the laptop adds no tracked change because no open condition was recorded before.

### r1 turn 17 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin walks back to her truck, the sound of her boots echoing on the pavement. She opens the truck door and reaches for her laptop, carefully lifting it out of the passenger seat. She closes the truck door and holds the laptop in her hand, looking around the quiet neighborhood.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows Kristin lifting the laptop out of the truck and after-state matches.

### r1 turn 19 (1A) - contradicts_stated_fact, restarts_scene [narrator initiative]
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She heads to the kitchen, where she sees Michelle's phone on the counter. She picks up the phone, examining it for any signs of disturbance or unusual activity. The phone's screen is dark, but Kristin notices that the charging cable is still plugged in.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows Kristin picking up the phone and after-state matches.

### r1 turn 20 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says she pulls the phone from her pocket though before-state had it in her hand.

### r1 turn 22 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says the phone is picked up from the table though it was already in Kristin's hand.

### r1 turn 26 (1A) - dropped_true_condition, contradicts_stated_fact
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin walks over to the carved drawer and tries to open it.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: After-state removes shut, matching an opened drawer.

### r1 turn 29 (1A) - narration_contradicts_given_facts
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATION: Kristin walks out to her truck, unlocks the door, and retrieves her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration implies retrieving the laptop from the truck though before-state already had it in her hand.

### r1 turn 30 (1A) - facts_after_correct, missed_change, dropped_true_condition [narrator initiative]
- COMMAND: Set your laptop on Michelle's workstation.
- NARRATION: Kristin carefully sets her laptop on Michelle's workstation, the screen casting a faint glow on the surrounding area. The workstation is cluttered with various papers, pens, and a few scattered notes, but Michelle's laptop and work bag are nowhere to be seen. Kristin's eyes scan the area, taking in the familiar layout of Michelle's workspace, and her gaze falls on Michelle's carved drawer, which i
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"condition": []}, "Michelle's workstation": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name Michelle's workstation held for matching"]
- FACT JUDGE: Narration sets the laptop on the workstation, but after-state leaves it in her hand and also wrongly drops the drawer's shut condition.

### r1 turn 32 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully plugs Michelle's phone into her laptop, which is still open on the passenger seat of her truck.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's laptop"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration says the laptop is open on the truck passenger seat, conflicting with before, and after-state invents the phone as in the laptop while missing the truck placement.

### r1 turn 34 (1A) - narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplugs Michelle's phone from the wall and holds it in her hand. She looks at the phone, but it's dark and unresponsive. She tries to turn it on, but it doesn't seem to be working.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: After-state matches the phone being held, though narration wrongly says it was unplugged from the wall.

### r1 turn 39 (1A) - restarts_scene [narrator initiative]
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter. She picks up the phone, examining it for any signs of disturbance or unusual activity. The phone's screen is dark, and there are no visible messages or notifications.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration shows Kristin picking up the phone and after-state matches.

### r1 turn 40 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration says she pulls the phone from her pocket though before-state had it in her hand.

### r2 turn 2 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says she picks the phone up from a table though it was already in her hand.

### r2 turn 6 (1A) - contradicts_stated_fact
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches the carved drawer in Michelle's work area, her eyes scanning the space for any signs of disturbance. She gently pulls the drawer open, revealing a neatly organized space with various research notes and papers. The drawer's contents are undisturbed, and Kristin's initials are indeed carved into the wood.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Opening the drawer ends the shut condition, which after-facts remove.

### r2 turn 8 (1A) - facts_after_correct, missed_change, invented_change [narrator initiative]
- COMMAND: Close the drawer.
- NARRATION: Kristin walks over to Michelle's carved drawer, which is still in its place in the shared house.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's carved drawer": {"place": "in the shared house"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Close command produced no narrated closing, but after-facts changed the drawer's where wording anyway.

### r2 turn 11 (1A) - facts_after_correct, invented_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the door, revealing her laptop on the passenger seat.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "in her truck"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration wrongly places the laptop back in the truck and after-facts invent that move.

### r2 turn 12 (1A) - facts_after_correct, missed_change, contradicts_stated_fact [narrator initiative]
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully removes Michelle's phone from her jacket pocket and heads to her truck to plug it in.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's truck"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration shows only heading to the truck to plug it in, not that the phone ended up there yet.

### r2 turn 13 (1A) - facts_after_correct, missed_change [narrator initiative]
- COMMAND: Look at the back door.
- NARRATION: Kristin recovers Michelle's memory card from under the drawer carved with her initials, KMS, and reads the files on it. The card identifies the federal emergency program as the Continuity Initiative, which was preparing to choose who remains.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"back door frame": {"condition": ["damaged"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- ISSUES: ["item_facts name back door frame held for matching"]
- FACT JUDGE: Narration introduces and recovers the memory card, but after-facts omit it.

### r2 turn 14 (1A) - contradicts_stated_fact
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the charger and holds it in her hand. The phone is now dead, its screen dark. Kristin looks at the phone, trying to remember the last time Michelle used it.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["dead"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dead"]}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration shows the phone unplugged, held, and now dead; after-facts record that.

### r2 turn 15 (1A) - facts_after_correct, dropped_true_condition
- COMMAND: Set Michelle's phone on the kitchen counter.
- NARRATION: Kristin carefully sets Michelle's phone on the kitchen counter.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dead"]}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": [], "place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: The phone moved correctly, but the true dead condition was dropped without narration ending it.

### r2 turn 16 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Close your laptop.
- NARRATION: Kristin gets out of her truck and walks towards the house, then opens the driver's side door and reaches in to close her laptop.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Closing the laptop in the truck changes no tracked place or condition.

### r2 turn 18 (1A) - facts_after_correct, missed_change [narrator initiative]
- COMMAND: Look around the kitchen for anything you missed.
- NARRATION: Kristin enters the kitchen, her eyes scanning the room for any signs of Michelle or what might have happened to her. She notices Michelle's phone on the kitchen counter, its screen dark. Kristin approaches the phone, her hand reaching out to pick it up.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration says she reaches to pick up the phone, but after-facts leave it on the counter.

### r2 turn 19 (1A) - restarts_scene [narrator initiative]
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter. She picks up the phone, examining it for any signs of disturbance or unusual activity. The phone's screen is dark, and there are no visible messages or notifications.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration shows the phone picked up from the counter, and after-facts match.

### r2 turn 20 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration mentions pulling it from her pocket even though before-facts had it in her hand.

### r2 turn 21 (1A) - narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin takes Michelle's phone from her pocket and examines it.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration says she takes it from her pocket, conflicting with it already being in hand.

### r2 turn 22 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration says she picks up the phone from a table though before-facts had it in her hand.

### r2 turn 26 (1A) - facts_after_correct, missed_change
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin walks over to the carved drawer and opens it.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration shows the drawer opened, but after-facts do not record it.

### r2 turn 27 (1A) - facts_after_correct, invented_change [narrator initiative]
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin opens the drawer and looks inside. It's Michelle's carved drawer, and it's still in the shared house.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"drawer": {"place": "open"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open"]}}
- ISSUES: ["item_facts name drawer held for matching"]
- FACT JUDGE: Narration adds no new drawer state, but after-facts invent an open condition.

### r2 turn 28 (1A) - facts_after_correct, missed_change, invented_change, contradicts_stated_fact
- COMMAND: Close the drawer.
- NARRATION: Kristin walks over to Michelle's carved drawer and tries to close it, but it's already slightly ajar.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open"]}}
- REPLY: {"Michelle's carved drawer": {"condition": ["partially closed"]}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- FACT JUDGE: Narration does not show the drawer actually becoming closed, yet after-facts add partially closed while keeping open.

### r2 turn 30 (1A) - facts_after_correct, missed_change [narrator initiative]
- COMMAND: Set your laptop on Michelle's workstation.
- NARRATION: Kristin carefully sets her laptop on Michelle's workstation, the screen still glowing from the previous night's work. The laptop's presence on the cluttered desk seems out of place, a stark contrast to the usual organized workspace Michelle maintained. Kristin's eyes scan the surrounding area, taking in the familiar layout of the room, but her attention is drawn to the empty space where Michelle's
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- REPLY: {"Michelle's tablet": {"place": "not here"}, "Michelle's work bag": {"place": "not here"}, "Michelle's workstation": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- ISSUES: ["item_facts name Michelle's tablet held for matching", "item_facts name Michelle's work bag held for matching", "item_facts name Michelle's workstation held for matching"]
- FACT JUDGE: Narration shows the laptop set on the workstation, but after-facts leave it in her hand.

### r2 turn 32 (1A) - facts_after_correct, missed_change, invented_change
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully plugs Michelle's phone into her laptop, which is still in her hand. She looks at the laptop's screen, waiting for it to recognize the phone. The laptop's screen flickers to life, and Kristin sees the phone's charging icon appear.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's laptop"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- FACT JUDGE: Narration shows the phone plugged into the laptop with a charging icon, but after-facts use an invalid holder and omit charging.

### r2 turn 34 (1A) - facts_after_correct, missed_change
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the charger and holds it in her hand. The phone is now dead, but Kristin can see that it's been recently used. She looks at the phone's screen, but it's dark.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- FACT JUDGE: Narration says the unplugged phone is now dead, but after-facts miss that condition.

### r2 turn 38 (1A) - facts_after_correct, missed_change [narrator initiative]
- COMMAND: Look around the kitchen for anything you missed.
- NARRATION: Kristin enters the kitchen, her eyes scanning the room for any signs of Michelle or what might have happened to her. She notices Michelle's phone on the kitchen counter, its screen dark. Kristin approaches the phone, her hand reaching out to pick it up.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- FACT JUDGE: Narration again shows her reaching to pick up the phone, but after-facts keep it on the counter.

### r2 turn 39 (1A) - restarts_scene [narrator initiative]
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- FACT JUDGE: Narration only notices the phone on the counter and does not pick it up.

### r2 turn 40 (1A) - contradicts_stated_fact, restarts_scene [narrator initiative]
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the living room and kitchen, but there's no sign of Michelle. She heads to the kitchen counter, where she sees Michelle's phone.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- FACT JUDGE: Narration confirms the phone is on the counter, matching after-facts.

### r3 turn 2 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says the phone is picked up from the table even though it was already in Kristin's hand.

### r3 turn 6 (1A) - facts_after_correct, invented_change, dropped_true_condition [narrator initiative]
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches the desk where Michelle's research notes are kept.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"place": "open"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- FACT JUDGE: Narration only says Kristin approaches the desk, but after-facts invent the drawer becoming open and drop shut.

### r3 turn 7 (1A) - facts_after_correct, dropped_true_condition, kept_ended_condition, contradicts_stated_fact
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin kneels down beside the open drawer, her eyes scanning the contents. She sees Michelle's research notes, neatly organized and stacked on one side of the drawer. The notes appear to be some sort of journal, filled with handwritten entries and diagrams.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- REPLY: {"Michelle's carved drawer": {"condition": []}, "Michelle's research notes": {"place": "in the drawer"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name Michelle's research notes held for matching"]
- FACT JUDGE: Narration refers to the drawer as open, so open should remain; after-facts remove that condition without showing it end.

### r3 turn 10 (1A) - facts_after_correct, missed_change, invented_change, contradicts_stated_fact [narrator initiative]
- COMMAND: Set your laptop on Michelle's workstation.
- NARRATION: Kristin sets her laptop on Michelle's workstation, a cluttered desk with various papers and equipment scattered about. She notices Michelle's memory card, which is still in its usual place on the desk. Kristin's eyes scan the area, taking in the familiar surroundings of their shared workspace.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's memory card": {"place": "on the desk"}, "Michelle's workstation": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name Michelle's memory card held for matching", "item_facts name Michelle's workstation held for matching"]
- FACT JUDGE: Narration places the laptop on the workstation and introduces the memory card on the desk, but after-facts keep laptop in hand and omit the card.

### r3 turn 11 (1A) - contradicts_stated_fact
- COMMAND: Open your laptop.
- NARRATION: Kristin opens her laptop, which is still in her hand from the drive home.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "open"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration shows the laptop being opened, and after-facts add open.

### r3 turn 12 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully plugs Michelle's phone into her laptop, which is still open on the passenger seat of her truck. She gets out of the truck and walks back to the house, the laptop and phone in hand. As she approaches the house, she notices that the back door is still slightly ajar.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "in Kristin's hand"}, "Michelle's phone": {"place": "in Kristin's laptop"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration wrongly places the laptop on the truck seat, and after-facts change the phone to in laptop without recording charging or the odd move properly.

### r3 turn 13 (1A) - facts_after_correct, missed_change [narrator initiative]
- COMMAND: Look at the back door.
- NARRATION: Kristin recovers Michelle's memory card from under the drawer carved with her initials, KMS, and reads the files on it. The card identifies the federal emergency program as the Continuity Initiative, which was preparing to choose who remains.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"back door frame": {"condition": ["damaged"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name back door frame held for matching"]
- FACT JUDGE: Narration introduces and recovers the memory card, but after-facts omit it.

### r3 turn 14 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the wall and holds it in her hand. The phone is now dead, its screen dark. Kristin looks at the phone, trying to remember the last time Michelle used it.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["dead"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dead"]}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: After-facts match the narrated unplugging and dead phone, though narration contradicts prior facts by saying from the wall.

### r3 turn 15 (1A) - facts_after_correct, dropped_true_condition
- COMMAND: Set Michelle's phone on the kitchen counter.
- NARRATION: Kristin carefully sets Michelle's phone on the kitchen counter.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dead"]}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": []}, "Michelle's phone": {"condition": [], "place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: The move is recorded, but the true dead condition is dropped without narration ending it.

### r3 turn 16 (1A) - facts_after_correct, missed_change, contradicts_stated_fact
- COMMAND: Close your laptop.
- NARRATION: Kristin closes her laptop, which is still in her hand.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Closing the laptop should end open, but after-facts fail to record that change.

### r3 turn 18 (1A) - restarts_scene
- COMMAND: Look around the kitchen for anything you missed.
- NARRATION: Kristin enters the kitchen, her eyes scanning the room for any signs of Michelle's whereabouts. She notices Michelle's phone on the kitchen counter, its screen dark. Kristin's gaze falls on the back door, where she sees the recent damage to the frame.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Looking around the kitchen does not clearly change tracked item state.

### r3 turn 19 (1A) - facts_after_correct, missed_change, invented_change, restarts_scene [narrator initiative]
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration only notices the phone on the counter, but after-facts invent it moving into Kristin's hand.

### r3 turn 20 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: After-facts keep the phone in hand, but narration contradicts prior facts by pulling it from her pocket.

### r3 turn 21 (1A) - narration_contradicts_given_facts
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin takes Michelle's phone from her hand and examines it.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: After-facts keep the phone in hand, though narration oddly says she takes it from her hand.

### r3 turn 22 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration says the phone is picked up from the table despite already being in Kristin's hand.

### r3 turn 26 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin walks over to the desk and opens the drawer with her initials carved into it. Inside, she finds Michelle's research notes and a few pens. The notes appear to be some sort of journal, detailing Michelle's work on a project called the Continuity Initiative.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's carved drawer": {"place": "open"}, "Michelle's research notes": {"place": "in the drawer"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- ISSUES: ["item_facts name Michelle's research notes held for matching"]
- FACT JUDGE: Narration shows the drawer opened, and after-facts record open.

### r3 turn 27 (1A) - contradicts_stated_fact
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin kneels down beside the open drawer, her eyes scanning the contents. The drawer is filled with various research notes, some of which are neatly organized, while others appear to be hastily scribbled. She notices a few papers with cryptic symbols and equations, but nothing that immediately stands out as a clue to Michelle's disappearance.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- REPLY: {"Michelle's carved drawer": {"condition": ["open"], "place": "in Kristin and Michelle's shared house"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- FACT JUDGE: Looking inside the already open drawer does not change tracked state.

### r3 turn 29 (1A) - facts_after_correct, missed_change, invented_change [narrator initiative]
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATION: Kristin walks out to her truck and unlocks the door.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration only shows Kristin unlocking the truck door, but after-facts invent the laptop moving to her hand.

### r3 turn 30 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Set your laptop on Michelle's workstation.
- NARRATION: Kristin carefully sets her laptop on Michelle's workstation, the screen flickering to life as it boots up. The laptop's keyboard and mouse are still in their usual places, but Michelle's tablet and work bag are missing. Kristin's eyes scan the area, taking in the familiar layout of Michelle's workspace.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"laptop": {"place": "on Michelle's workstation"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- ISSUES: ["item_facts name laptop held for matching"]
- FACT JUDGE: Narration shows the laptop set on the workstation, and after-facts match.

### r3 turn 31 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts [narrator initiative]
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the driver's side door, pulling out her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration contradicts prior facts by going to the truck and pulling out the laptop, and after-facts invent moving it back to her hand instead of recording opening.

### r3 turn 34 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplugs Michelle's phone from the wall and holds it in her hand. The phone is now dead, its screen dark. Kristin looks at the phone, trying to find any clues about Michelle's disappearance.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["booting up"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"condition": ["dead"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dead"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["booting up"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: After-facts match the unplugging and dead phone, though narration contradicts prior facts by saying from the wall.

### r3 turn 35 (1A) - facts_after_correct, dropped_true_condition
- COMMAND: Set Michelle's phone on the kitchen counter.
- NARRATION: Kristin carefully sets Michelle's phone on the kitchen counter.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dead"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["booting up"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"condition": []}, "Michelle's phone": {"condition": [], "place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: After-facts record the phone move, but wrongly drop the phone's dead condition without narration ending it.

### r3 turn 36 (1A) - contradicts_stated_fact
- COMMAND: Close your laptop.
- NARRATION: Kristin closes her laptop, which is still in her hand.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"]}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows the laptop being closed, and after-facts record closed.

### r3 turn 37 (1A) - facts_after_correct, missed_change
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin walks back to her truck, laptop in hand.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says she walks back to the truck with the laptop, but after-facts fail to move it there.

### r3 turn 39 (1A) - facts_after_correct, missed_change, invented_change, restarts_scene [narrator initiative]
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, her eyes scanning the room for any sign of Michelle. She heads to the kitchen counter, where Michelle's phone is sitting.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration only says she goes to the counter where the phone is sitting, but after-facts invent picking it up.

### r3 turn 40 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: After-facts keep the phone in hand, but narration conflicts by saying she pulls it from her pocket.

### r4 turn 2 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the coffee table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says the phone was on the coffee table though it was already in Kristin's hand.

### r4 turn 5 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Put Michelle's phone in your jacket pocket.
- NARRATION: Kristin reaches into her jacket pocket and pulls out Michelle's phone.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in her jacket pocket"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration pulls the phone out of the pocket, but after puts it in the pocket.

### r4 turn 6 (1A) - facts_after_correct, missed_change, invented_change, dropped_true_condition [narrator initiative]
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches the desk where Michelle's research notes are kept.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"place": "open"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- FACT JUDGE: Narration did not open the drawer, but after changes shut to open.

### r4 turn 7 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin kneels down beside the open drawer, her eyes scanning the contents. The drawer is filled with various research notes, some of which are neatly organized, while others appear to be hastily scribbled. Kristin's eyes land on a note with a cryptic message: 'Population stabilization centers - not what they seem.'
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- REPLY: {"Michelle's carved drawer": {"condition": ["open"]}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- FACT JUDGE: Narration only describes looking into an already open drawer.

### r4 turn 8 (1A) - facts_after_correct, missed_change, dropped_true_condition, contradicts_stated_fact
- COMMAND: Close the drawer.
- NARRATION: Kristin walks over to Michelle's carved drawer and tries to close it, but it's already open.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- REPLY: {"Michelle's carved drawer": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration says the drawer is already open, so open should remain rather than be dropped.

### r4 turn 10 (1A) - facts_after_correct, invented_change [narrator initiative]
- COMMAND: Set your laptop on Michelle's workstation.
- NARRATION: Kristin sets her laptop on Michelle's workstation, the screen flickering to life as she powers it on. The laptop's screen displays a password prompt, and Kristin's eyes scan the area for any clues that might help her unlock it. Her gaze falls on Michelle's carved drawer, and she notices her initials, KMS, are carved into it.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"drawer": {"condition": ["carved with KMS"]}, "laptop": {"place": "on Michelle's workstation"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- ISSUES: ["item_facts name drawer held for matching", "item_facts name laptop held for matching"]
- FACT JUDGE: After correctly moves the laptop but invents drawer condition carved with KMS.

### r4 turn 11 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the door, revealing her laptop on the passenger seat.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Kristin's laptop": {"place": "in her truck"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration contradicts the laptop being on the workstation and after wrongly moves it back to the truck.

### r4 turn 12 (1A) - facts_after_correct, missed_change, invented_change [narrator initiative]
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully removes Michelle's phone from her jacket pocket and heads to her truck to plug it into her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's truck"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration also moves Kristin to the truck with the phone, but after misses moving the laptop there.

### r4 turn 13 (1A) - facts_after_correct, missed_change [narrator initiative]
- COMMAND: Look at the back door.
- NARRATION: Kristin recovers Michelle's memory card from under the drawer carved with her initials, KMS, and reads the files on it. The card identifies the federal emergency program as the Continuity Initiative, which was preparing to choose who remains.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"back door frame": {"condition": ["damaged"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- ISSUES: ["item_facts name back door frame held for matching"]
- FACT JUDGE: Narration introduces and recovers the memory card, but after omits it.

### r4 turn 14 (1A) - contradicts_stated_fact
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the charger and holds it in her hand. The phone is now dead, but Kristin can see that it's been recently used. She looks at the phone's screen, but it's dark.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration shows the phone being unplugged and held.

### r4 turn 16 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Close your laptop.
- NARRATION: Kristin gets out of her truck and walks towards the house, then opens the driver's side door and reaches in to close her laptop.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Kristin's laptop": {"place": "in her truck"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Closing the laptop here did not clearly change any tracked fact already stored.

### r4 turn 17 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin walks back to her truck, the sound of her boots echoing on the pavement. She opens the truck door and reaches for her laptop, which is still in the passenger seat. She carefully lifts it out and closes the door behind her.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration shows Kristin lifting the laptop out of the truck.

### r4 turn 19 (1A) - facts_after_correct, narration_contradicts_given_facts, restarts_scene
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter. She picks up Michelle's phone, examining it for any signs of disturbance or unusual activity. The phone is locked, but Kristin recognizes the device as Michelle's.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration says the phone is on the counter though before says it is already in Kristin's hand.

### r4 turn 20 (1A) - facts_after_correct, narration_contradicts_given_facts
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration says Kristin pulls the phone from her pocket, conflicting with it already being in her hand.

### r4 turn 22 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table, checking the screen for any messages or calls.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration says the phone was picked up from a table though it was already in Kristin's hand.

### r4 turn 23 (1A) - facts_after_correct, invented_change
- COMMAND: Wipe the dust off the screen of Michelle's phone.
- NARRATION: Kristin carefully wipes the dust off the screen of Michelle's phone.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Michelle's phone": {"condition": ["clean"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["clean"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration only wipes dust, but after invents the clean condition.

### r4 turn 24 (1A) - facts_after_correct, missed_change, dropped_true_condition [narrator initiative]
- COMMAND: Press the power button on Michelle's phone.
- NARRATION: Kristin presses the power button on Michelle's phone. The screen flickers to life, displaying Michelle's lock screen. Kristin enters Michelle's passcode, and the phone unlocks.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["clean"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Michelle's phone": {"condition": [], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration does not show the phone stopping being clean, so dropping clean is incorrect.

### r4 turn 26 (1A) - facts_after_correct, missed_change, dropped_true_condition, contradicts_stated_fact [narrator initiative]
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin walks over to the desk and looks at the drawer with her initials carved into it. She gently pulls the drawer open. Inside, she finds a small notebook belonging to Michelle.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"drawer": {"condition": []}, "notebook": {"place": "in the drawer"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name drawer held for matching", "item_facts name notebook held for matching"]
- FACT JUDGE: Narration opens the drawer, but after drops carved with KMS and fails to record open.

### r4 turn 27 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin opens the drawer and looks inside. It's Michelle's carved drawer, and it's still in the same place in their shared house.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration does not change tracked facts.

### r4 turn 29 (1A) - narration_contradicts_given_facts
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATION: Kristin walks out to her truck, unlocks the door, and retrieves her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration talks about retrieving the laptop from the truck though before it was already in her hand.

### r4 turn 31 (1A) - narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the driver's side door, pulling out her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration contradicts the prior location but does show her pulling the laptop out and ending with it in hand.

### r4 turn 34 (1A) - contradicts_stated_fact
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the wall charger. She picks up the phone, feeling a mix of concern and determination. The phone is now in her hand.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows the phone unplugged and picked up.

### r4 turn 39 (1A) - narration_contradicts_given_facts, restarts_scene [narrator initiative]
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter. She picks up Michelle's phone, feeling a sense of unease as she realizes it's been a while since Michelle last answered her calls. The phone is locked, but Kristin quickly enters Michelle's passcode, which she remembers from years of sharing a home.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says the phone is on the counter though before it was already in Kristin's hand.

### r4 turn 40 (1A) - facts_after_correct, narration_contradicts_given_facts
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says Kristin pulls the phone from her pocket, conflicting with it already being in her hand.
