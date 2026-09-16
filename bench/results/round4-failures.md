# Round 4 failures, every failing turn

Source: bench/results/item-facts-v3-place-*, commit d969ed8. Four replicates each.
A turn appears here if the fact-tracking judge marked it not kept or flagged any criterion,
or if the continuity judge flagged it. Passing turns are omitted.

## Counts

**two-scene (4 replicates, 47 turns)** - 39 turns with at least one failure
  - protagonist_acts_beyond_command: 25
  - facts_after_correct: 19
  - missed_change: 13
  - contradicts_stated_fact: 12
  - narration_contradicts_given_facts: 7
  - invented_change: 6
  - restarts_scene: 2

**40-turn (4 replicates, 159 turns)** - 113 turns with at least one failure
  - protagonist_acts_beyond_command: 68
  - facts_after_correct: 54
  - contradicts_stated_fact: 54
  - missed_change: 34
  - narration_contradicts_given_facts: 32
  - invented_change: 20
  - dropped_true_condition: 11
  - restarts_scene: 10
  - kept_ended_condition: 3



## two-scene (4 replicates, 47 turns)

### r1 turn 1 (1A) - protagonist_acts_beyond_command
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin picks up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen floor", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows Kristin picked up the phone, and after-facts record that.
- CONTINUITY JUDGE: Command was only to look carefully, but narration has Kristin pick up the phone.

### r1 turn 2 (1A) - contradicts_stated_fact
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches the desk and looks at the drawer with her initials carved into it. She gently pulls the drawer open. Inside, she sees a small note with the initials 'KMS'.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"drawer": {"condition": []}, "note": {"place": "in the drawer"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name drawer held for matching", "item_facts name note held for matching"]
- FACT JUDGE: The drawer is opened in the narration, and the shut condition is correctly removed.
- CONTINUITY JUDGE: Canon says Michelle's carved drawer is shut; opening it and finding a note introduces contents inconsistent with hidden memory card setup.

### r1 turn 3 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATION: Kristin reaches into her pocket and pulls out Michelle's phone, which she had found on the floor near the back door.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in her pocket"}}
- AFTER: {"Michelle's phone": {"where": "in her pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration says she pulls the phone from her pocket, conflicting with before-facts, and after-facts newly put it in her pocket without narration showing that.
- CONTINUITY JUDGE: It says the phone was found near the back door, but canon/opening place it on the kitchen floor.

### r1 turn 6 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATION: Kristin reaches into Michelle's pocket and pulls out her phone. She looks at the phone and then throws it hard against the kitchen wall. The phone's screen cracks, but it still seems to be working.
- GIVEN: {"Michelle's phone": {"where": "in her pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["cracked"], "place": "on the kitchen floor"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen floor", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration conflicts by saying the phone was in Michelle's pocket, and after-facts add it to the kitchen floor without the narration showing where it landed.
- CONTINUITY JUDGE: Narration says Kristin pulls the phone from Michelle's pocket, though Michelle is absent and the phone was not there; also adds extra looking before throwing.

### r1 turn 7 (1A) - contradicts_stated_fact
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen floor", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["cracked"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration clearly shows Kristin picking up the cracked phone from the floor.
- CONTINUITY JUDGE: After turn 6 the phone was thrown against the wall, so describing it as on the kitchen floor conflicts with the prior narration.

### r1 turn 8 (1A) - contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Leave the house and drive to the park with Michelle's phone.
- NARRATION: Kristin carefully exits the house, locking the back door behind her. She gets into her truck, starts the engine, and begins to drive away from the house. As she drives, she glances down at Michelle's phone in her hand, its cracked screen reflecting the morning light.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration does not clearly change tracked item locations or conditions beyond still having the phone in hand.
- CONTINUITY JUDGE: It adds locking the back door, though opening says the back door showed forced entry; locking it is an extra unrequested action.

### r1 turn 9 (1B) - contradicts_stated_fact, restarts_scene
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin looks down at Michelle's phone in her hand, its cracked screen reflecting the dim light of the quiet house.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["cracked"]}}
- REPLY: {"Michelle's phone": {"condition": ["cracked"], "place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": ["cracked"]}}
- FACT JUDGE: This just restates that Michelle's phone is in her hand with the cracked condition unchanged.
- CONTINUITY JUDGE: Previous turn had Kristin driving away, but this places her back in the quiet house as if the move to the park had not happened.

### r1 turn 10 (1B) - protagonist_acts_beyond_command
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin looks around the bench, but it's just an ordinary park bench with a few scratches on the surface. She checks the nearby trash cans and the service path, but there's nothing out of the ordinary. As she scans the area, she notices a watching man standing across the path, trying to blend in with the surroundings.
- GIVEN: {"Michelle's phone": {"where": "in her hand", "condition": ["cracked"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"bench": {"place": "near the service path"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": ["cracked"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name bench held for matching"]
- FACT JUDGE: Narration introduces a watching man but does not place or transfer any tracked item.
- CONTINUITY JUDGE: Looking around the bench is fine, but checking trash cans and the service path goes beyond the specific command.

### r1 turn 11 (1B) - facts_after_correct, missed_change
- COMMAND: Walk over to the man watching you and hand him Michelle's phone.
- NARRATION: Kristin walks over to the man watching her, her eyes fixed on him. She hands him Michelle's phone, her hand extended in a deliberate gesture.
- GIVEN: {}
- REPLY: null
- AFTER: {}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration clearly shows Kristin handing the phone to the man, but after-facts record nothing.
- CONTINUITY JUDGE: It directly carries out the commanded approach and handoff.

### r1 turn 12 (1B) - facts_after_correct, invented_change, protagonist_acts_beyond_command
- COMMAND: Check who has Michelle's phone now.
- NARRATION: Kristin looks around the park, her eyes scanning the area for any sign of Michelle or potential threats.
- GIVEN: {"Michelle's phone": {"where": "in her hand", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}}
- REPLY: {}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}}
- FACT JUDGE: Narration does not show any phone transfer, but after-facts keep Michelle's phone in her hand.
- CONTINUITY JUDGE: Instead of determining who has the phone now, narration just scans generally for Michelle or threats.

### r2 turn 1 (1A) - protagonist_acts_beyond_command
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin picks up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen floor", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows Kristin picked up the phone, and after-facts record it in her hand.
- CONTINUITY JUDGE: The command was only to look carefully, but Kristin picks the phone up.

### r2 turn 3 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATION: Kristin reaches into the living room and picks up Michelle's phone, which was lying on the coffee table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration wrongly says the phone was on the coffee table even though before-facts had it in Kristin's hand.
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on the coffee table in the living room.

### r2 turn 4 (1A) - protagonist_acts_beyond_command
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATION: Kristin walks out to her truck, unlocks the door, and retrieves her laptop.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration shows Kristin retrieving the laptop, and after-facts put it in her hand.
- CONTINUITY JUDGE: The command included bringing the laptop inside, but narration only has Kristin retrieve it at the truck.

### r2 turn 5 (1A) - facts_after_correct, missed_change, invented_change
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin carefully makes her way back to her truck, laptop in hand.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "in the truck"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration only shows Kristin carrying the laptop to the truck, not placing it in the truck, but after-facts move it there.
- CONTINUITY JUDGE: It follows the command by taking the laptop back to the truck.

### r2 turn 6 (1A) - facts_after_correct, missed_change, protagonist_acts_beyond_command
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall. The phone hits the wall with a loud crash, its screen shattering into pieces. Kristin walks over to the wall and picks up the phone, examining it for any clues.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["damaged"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration ends with Kristin picking up the shattered phone, but after-facts leave it in her pocket.
- CONTINUITY JUDGE: After throwing the phone, Kristin also walks over, picks it up, and examines it without being asked.

### r2 turn 7 (1A) - facts_after_correct, narration_contradicts_given_facts, protagonist_acts_beyond_command
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the floor. She examines the phone, noticing that it's damaged. The screen is cracked, and the back is scratched.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["damaged"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration says she picks the phone up from the floor, conflicting with before-facts that had it in her pocket.
- CONTINUITY JUDGE: After picking up the phone, Kristin also examines it, which goes beyond the command.

### r2 turn 8 (1A) - facts_after_correct, missed_change, protagonist_acts_beyond_command
- COMMAND: Leave the house and drive to the park with Michelle's phone.
- NARRATION: Kristin carefully exits the house, locking the back door behind her. She gets into her truck and starts the engine, then carefully places Michelle's phone on the passenger seat. Kristin drives through the quiet streets, eventually arriving at the park where she knows she can find some peace and think about her next move.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration explicitly says Kristin places the phone on the passenger seat, but after-facts keep it in her hand.
- CONTINUITY JUDGE: Locking the back door and placing the phone on the passenger seat were extra physical actions beyond leaving and driving.

### r2 turn 9 (1B) - contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin looks down at Michelle's phone in her hand, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["damaged"]}}
- REPLY: {"Michelle's phone": {"condition": ["damaged"], "place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": ["damaged"]}}
- FACT JUDGE: Narration and after-facts both show the damaged phone in her hand.
- CONTINUITY JUDGE: The prior turn put the phone on the passenger seat, but this turn says it is in Kristin's hand.

### r2 turn 10 (1B) - facts_after_correct, missed_change
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin looks around the bench, scanning the area for any signs of Michelle's presence. She notices a small piece of paper on the ground near the service path. The paper appears to be a receipt from a local coffee shop, but there's a handwritten note on the back that reads 'Meet me at the old warehouse at midnight.'
- GIVEN: {"Michelle's phone": {"where": "in her hand", "condition": ["damaged"]}}
- REPLY: {"receipt": {"condition": ["crumpled"], "place": "on the ground near the service path"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": ["damaged"]}}
- ISSUES: ["item_facts name receipt held for matching"]
- FACT JUDGE: Narration introduces a piece of paper in a specific place, but after-facts do not add it.
- CONTINUITY JUDGE: Searching around the bench and noticing an item there fits the command and does not restate arrival.

### r3 turn 1 (1A) - protagonist_acts_beyond_command
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin picks up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen floor", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows Kristin picked up the phone, and after-facts record that move.
- CONTINUITY JUDGE: She picks up the phone though the command only asked to look at it.

### r3 turn 2 (1A) - protagonist_acts_beyond_command
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches the desk and opens the drawer with her initials carved into it. Inside, she finds a small note with the initials KMS. The note is folded and appears to have been written in a hurry.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"drawer": {"condition": []}, "note": {"condition": [], "place": "in the drawer"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name drawer held for matching", "item_facts name note held for matching"]
- FACT JUDGE: Opening the drawer ends the shut condition, and after-facts reflect that.
- CONTINUITY JUDGE: Opening the drawer is commanded, but finding a note adds an unestablished item and action outcome not requested.

### r3 turn 3 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATION: Kristin reaches into the living room and picks up Michelle's phone, which was left on the coffee table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: After-facts fit the action, but narration wrongly says the phone was on the coffee table despite before-facts saying it was already in her hand.
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on the coffee table in the living room.

### r3 turn 4 (1A) - protagonist_acts_beyond_command
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATION: Kristin walks out to her truck, unlocks the door, and retrieves her laptop.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration shows Kristin retrieved the laptop, and after-facts record it in her hand.
- CONTINUITY JUDGE: She goes to the truck and retrieves the laptop but does not bring it inside as commanded.

### r3 turn 5 (1A) - facts_after_correct, missed_change
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin carefully makes her way back to her truck, laptop in hand.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "in the truck"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration only shows her carrying the laptop to the truck, not leaving it there, so after-facts miss that it remains in hand.
- CONTINUITY JUDGE: This continues carrying the laptop back to the truck without adding extra physical actions.

### r3 turn 6 (1A) - facts_after_correct, missed_change, protagonist_acts_beyond_command
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall. The phone hits the wall with a loud crack, but it doesn't shatter completely. Kristin walks over to the wall and picks up the phone, examining it for any signs of damage.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen floor"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen floor", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration says she picked the phone up after throwing it, and implies damage, but after-facts leave it on the floor with no damage.
- CONTINUITY JUDGE: After throwing the phone, she also walks over, picks it up, and examines it unasked.

### r3 turn 8 (1A) - protagonist_acts_beyond_command
- COMMAND: Leave the house and drive to the park with Michelle's phone.
- NARRATION: Kristin carefully exits the house, locking the back door behind her. She gets into her truck, starts the engine, and pulls out of the driveway. As she drives through the quiet streets, she glances down at Michelle's phone in her hand.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration keeps the phone in her hand and laptop in the truck; location travel is not separately tracked for these items here.
- CONTINUITY JUDGE: Locking the back door behind her was not requested; leaving and driving were.

### r3 turn 9 (1B) - facts_after_correct, invented_change, narration_contradicts_given_facts
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin checks her pocket and feels the familiar shape of Michelle's phone.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in her pocket"}}
- AFTER: {"Michelle's phone": {"where": "in her pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration contradicts before-facts by saying she checks her pocket while the phone was in her hand, and after-facts invent moving it to her pocket.
- CONTINUITY JUDGE: Checking her pocket to confirm the phone is exactly what was asked.

### r3 turn 10 (1B) - facts_after_correct, missed_change, protagonist_acts_beyond_command
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin looks around the bench, scanning the area for any signs of Michelle's presence. She notices a small piece of paper on the ground near the service path. Picking it up, she sees that it's a receipt from a local coffee shop, but there's a handwritten note on the back that reads 'Meet me at the old warehouse at midnight'.
- GIVEN: {"Michelle's phone": {"where": "in her pocket", "condition": []}}
- REPLY: {"note": {"condition": ["handwritten"], "place": "on the receipt"}, "receipt": {"condition": ["crumpled"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in her pocket", "condition": []}}
- ISSUES: ["item_facts name note held for matching", "item_facts name receipt held for matching"]
- FACT JUDGE: Narration introduces and places a piece of paper and has Kristin pick it up, but after-facts omit it entirely.
- CONTINUITY JUDGE: She not only looks around but also discovers and picks up a new paper.

### r3 turn 11 (1B) - facts_after_correct, missed_change
- COMMAND: Walk over to the man watching you and hand him Michelle's phone.
- NARRATION: Kristin walks over to the man watching her, her eyes fixed on his face. She hands him Michelle's phone, her hand extended in a deliberate gesture.
- GIVEN: {"Michelle's phone": {"where": "in her pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in her pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration says Kristin hands the man Michelle's phone, but after-facts wrongly keep it in her pocket.
- CONTINUITY JUDGE: Walking to the man and handing him the phone matches the command.

### r4 turn 1 (1A) - protagonist_acts_beyond_command
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin picks up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen floor", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows the phone being picked up into Kristin's hand.
- CONTINUITY JUDGE: She picks up the phone instead of only looking at it.

### r4 turn 2 (1A) - contradicts_stated_fact
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches the desk and looks at the drawer with her initials carved into it. She gently pulls the drawer open. Inside, she finds a small note with the initials KMS.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"drawer": {"condition": []}, "note": {"place": "in the drawer"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}, "note": {"where": "in the drawer", "conditio
- ISSUES: ["item_facts name drawer held for matching", "item_facts name note held for matching"]
- FACT JUDGE: The drawer is opened and a note is newly found inside it.
- CONTINUITY JUDGE: The drawer is canonically shut and hides a memory card, not a visible note.

### r4 turn 3 (1A) - facts_after_correct, invented_change, narration_contradicts_given_facts, contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATION: Kristin reaches into the living room and picks up Michelle's phone, which was left on the coffee table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}, "note": {"where": "in the drawer", "conditio
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}, "note": {"where": "in the drawer", "condit
- FACT JUDGE: Narration wrongly says the phone was on the coffee table, and after-facts invent pocketing not shown.
- CONTINUITY JUDGE: The phone was on the kitchen floor, not on a coffee table, and she does not pocket it.

### r4 turn 4 (1A) - protagonist_acts_beyond_command
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATION: Kristin walks out to her truck, unlocks the door, and retrieves her laptop.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration shows Kristin retrieving the laptop and holding it.
- CONTINUITY JUDGE: Bringing it inside also implies picking up the laptop, beyond just going out and bringing it.

### r4 turn 5 (1A) - protagonist_acts_beyond_command
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin carefully makes her way back to her truck, laptop in hand. She opens the truck door and sets the laptop on the passenger seat. She closes the door and takes a moment to look around the quiet neighborhood.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "in the truck"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration shows the laptop being set in the truck.
- CONTINUITY JUDGE: She also sets the laptop down, closes the door, and pauses to look around.

### r4 turn 6 (1A) - facts_after_correct, missed_change, protagonist_acts_beyond_command
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall. The phone hits the wall with a loud crack, but it doesn't shatter completely. Kristin walks over to the wall and picks up the phone, examining it for any signs of damage.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen floor"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen floor", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration ends with Kristin picking the phone up, but after-facts leave it on the floor.
- CONTINUITY JUDGE: After throwing it, she additionally walks over, picks it up, and examines it.

### r4 turn 8 (1A) - protagonist_acts_beyond_command
- COMMAND: Leave the house and drive to the park with Michelle's phone.
- NARRATION: Kristin steps out of the house, locking the door behind her. She looks around, noticing the increased police presence in the neighborhood. Kristin gets into her truck, starts the engine, and begins to drive away from the house.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration does not clearly change who holds the phone or where the listed items are.
- CONTINUITY JUDGE: She also locks the door, surveys the neighborhood, starts the engine, and begins driving.

### r4 turn 9 (1B) - contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin looks down at Michelle's phone in her hand, its screen dark and unresponsive.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": []}}
- FACT JUDGE: Wording change from Kristin to her hand means the same thing.
- CONTINUITY JUDGE: The phone was being carried with her, not already in her hand, and she does more than just check.

### r4 turn 10 (1B) - facts_after_correct, missed_change, protagonist_acts_beyond_command
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin looks around the bench, searching for any signs of Michelle's presence. She notices a small piece of paper on the ground near the bench, partially hidden by the shadows. The paper appears to be a receipt from a local coffee shop, but there's a handwritten note on the back that reads 'Meet me at the old warehouse at midnight.'
- GIVEN: {"Michelle's phone": {"where": "in her hand", "condition": []}}
- REPLY: {"bench": {}, "paper": {}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": []}}
- FACT JUDGE: Narration introduces a paper near the bench, but after-facts omit it.
- CONTINUITY JUDGE: It invents a new paper clue rather than only looking around the bench.

### r4 turn 12 (1B) - protagonist_acts_beyond_command, restarts_scene
- COMMAND: Check who has Michelle's phone now.
- NARRATION: Kristin looks around the park, her eyes scanning the area for any sign of Michelle or potential threats. She spots a man sitting on a bench, his eyes fixed on her, and her instincts tell her he's been following her. The man's hand is in his pocket, and Kristin's eyes widen as she realizes Michelle's phone is in his possession.
- GIVEN: {"Michelle's phone": {"where": "in the man's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}, "note": {"where": "in the drawer", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in the man's pocket"}, "man": {"condition": ["sitting"], "place": "on the bench"}}
- AFTER: {"Michelle's phone": {"where": "in the man's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}, "note": {"where": "in the drawer", "condition": []}}
- ISSUES: ["item_facts name man held for matching"]
- FACT JUDGE: Narration only confirms the phone is still in the man's possession.
- CONTINUITY JUDGE: It reintroduces the watching man as if newly discovered and adds extra scanning and realization beyond a simple check.


## 40-turn (4 replicates, 159 turns)

### r1 turn 1 (1A) - protagonist_acts_beyond_command
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin picks up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen floor", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows the phone picked up and after-state records that.
- CONTINUITY JUDGE: She picks up the phone when the command only asked to look at it.

### r1 turn 2 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says the phone is picked up from the table though it was already in Kristin's hand.
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on a table.

### r1 turn 6 (1A) - facts_after_correct, missed_change, kept_ended_condition
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin walks over to the desk and opens the carved drawer.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"carved drawer": {"place": "open"}, "drawer": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- ISSUES: ["item_facts name carved drawer held for matching", "item_facts name drawer held for matching"]
- FACT JUDGE: Narration opens the drawer but after-state still keeps it shut.
- CONTINUITY JUDGE: Opening the carved drawer fits the command and the drawer was shut.

### r1 turn 7 (1A) - facts_after_correct, missed_change, kept_ended_condition, protagonist_acts_beyond_command
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin walks over to the desk and opens the top drawer, revealing a neatly organized space with various office supplies and Michelle's research notes.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration again shows the drawer opened, but after-state still says shut.
- CONTINUITY JUDGE: It has Kristin open the drawer again instead of only looking inside it.

### r1 turn 8 (1A) - contradicts_stated_fact
- COMMAND: Close the drawer.
- NARRATION: Kristin approaches Michelle's carved drawer, which is currently shut.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"condition": ["shut"]}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration only says the drawer is currently shut, matching before and after.
- CONTINUITY JUDGE: It says the carved drawer is currently shut even though it was already opened earlier.

### r1 turn 9 (1A) - protagonist_acts_beyond_command
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATION: Kristin walks out to her truck, which is parked on the street in front of the house. She unlocks the truck and opens the driver's side door. Kristin reaches in and pulls out her laptop, which is still in the truck.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows Kristin pulling out the laptop and after-state records it in her hand.
- CONTINUITY JUDGE: She opens the truck door as an extra physical action beyond simply bringing the laptop inside.

### r1 turn 10 (1A) - protagonist_acts_beyond_command
- COMMAND: Set your laptop on Michelle's workstation.
- NARRATION: Kristin carefully sets her laptop on Michelle's workstation, the screen still glowing from the previous night's assessment. She looks around the room, taking in the familiar layout of Michelle's workspace. Her eyes land on a carved drawer, partially hidden behind a stack of papers.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"drawer": {"place": "in plain sight"}, "laptop": {"place": "on Michelle's workstation"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- ISSUES: ["item_facts name drawer held for matching", "item_facts name laptop held for matching"]
- FACT JUDGE: Narration shows the laptop set on the workstation and after-state matches.
- CONTINUITY JUDGE: After setting the laptop down, it adds extra looking around and noticing the drawer.

### r1 turn 11 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the driver's side door, revealing her laptop inside.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her truck"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration wrongly places the laptop back in the truck without showing that move, and after-state changes it to the truck anyway.
- CONTINUITY JUDGE: It places the laptop back in the truck even though it was just set on the workstation.

### r1 turn 12 (1A) - facts_after_correct, missed_change, contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully removes Michelle's phone from her jacket pocket and heads to her truck to plug it into her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's truck"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows the phone plugged into the laptop, but after-state only moves it to the truck and omits the plugged-in relation/charging state.
- CONTINUITY JUDGE: It sends her to the truck despite the laptop having just been opened there, creating location confusion and extra movement.

### r1 turn 13 (1A) - facts_after_correct, missed_change, contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Look at the back door.
- NARRATION: Kristin recovers Michelle's memory card from under the drawer carved with her initials, KMS, and reads the files on it. The card identifies the federal emergency program as the Continuity Initiative, which was preparing to choose who remains.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"back door": {"condition": ["damaged"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- ISSUES: ["item_facts name back door held for matching"]
- FACT JUDGE: Narration introduces and recovers the memory card, but after-state does not list it.
- CONTINUITY JUDGE: Instead of looking at the back door, it jumps to finding the hidden memory card and reading files.

### r1 turn 14 (1A) - contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the charger and holds it in her hand. The phone feels cold and heavy, but there's no sign of any damage or unusual activity. Kristin checks the phone's screen, but it's locked and there's no indication of any recent activity.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows the phone unplugged and held, and after-state records it in Kristin's hand.
- CONTINUITY JUDGE: It says the phone was on a charger though no prior narration established that state.

### r1 turn 16 (1A) - contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Close your laptop.
- NARRATION: Kristin gets out of her truck and walks towards the house, then opens the driver's side door and reaches in to close her laptop.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Closing the laptop adds no tracked change because no open condition was recorded before.
- CONTINUITY JUDGE: It puts the laptop back in the truck even though it had been moved inside earlier.

### r1 turn 17 (1A) - contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin walks back to her truck, the sound of her boots echoing on the pavement. She opens the truck door and reaches for her laptop, carefully lifting it out of the passenger seat. She closes the truck door and holds the laptop in her hand, looking around the quiet neighborhood.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows Kristin lifting the laptop out of the truck and after-state matches.
- CONTINUITY JUDGE: It has her lift the laptop out of the passenger seat instead of carrying it back to the truck.

### r1 turn 19 (1A) - contradicts_stated_fact, protagonist_acts_beyond_command, restarts_scene
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She heads to the kitchen, where she sees Michelle's phone on the counter. She picks up the phone, examining it for any signs of disturbance or unusual activity. The phone's screen is dark, but Kristin notices that the charging cable is still plugged in.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows Kristin picking up the phone and after-state matches.
- CONTINUITY JUDGE: She is described as walking into the house and newly seeing the phone, as if re-entering and rediscovering the scene.

### r1 turn 20 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says she pulls the phone from her pocket though before-state had it in her hand.
- CONTINUITY JUDGE: It says the phone is in her pocket right after she picked it up from the counter.

### r1 turn 22 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says the phone is picked up from the table though it was already in Kristin's hand.
- CONTINUITY JUDGE: It has her pick the phone up from a table though she was already holding it.

### r1 turn 23 (1A) - protagonist_acts_beyond_command
- COMMAND: Wipe the dust off the screen of Michelle's phone.
- NARRATION: Kristin carefully wipes the dust off the screen of Michelle's phone. The screen lights up, revealing a locked screen with a password prompt.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: The lit locked screen is not a tracked condition here.
- CONTINUITY JUDGE: Wiping the screen is fine, but lighting the screen with a password prompt is an extra result not asked for.

### r1 turn 24 (1A) - protagonist_acts_beyond_command
- COMMAND: Press the power button on Michelle's phone.
- NARRATION: Kristin presses the power button on Michelle's phone. The screen flickers to life, displaying a locked screen with a password prompt. Kristin tries to guess Michelle's password, but it's not something she remembers.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Pressing the power button does not force a tracked state change.
- CONTINUITY JUDGE: After pressing the button, it adds guessing Michelle's password, which exceeds the command.

### r1 turn 26 (1A) - dropped_true_condition, contradicts_stated_fact
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin walks over to the carved drawer and tries to open it.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: After-state removes shut, matching an opened drawer.
- CONTINUITY JUDGE: It says she tries to open the carved drawer despite it already having been opened before.

### r1 turn 27 (1A) - protagonist_acts_beyond_command
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin opens the drawer and looks inside. It's Michelle's carved drawer, and it's still in the same place in their shared house.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration is consistent with the drawer already being open; no new tracked change is needed.
- CONTINUITY JUDGE: It opens the drawer instead of only looking inside it.

### r1 turn 29 (1A) - narration_contradicts_given_facts
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATION: Kristin walks out to her truck, unlocks the door, and retrieves her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration implies retrieving the laptop from the truck though before-state already had it in her hand.
- CONTINUITY JUDGE: Going to the truck and retrieving the laptop matches the command.

### r1 turn 30 (1A) - facts_after_correct, missed_change, dropped_true_condition, protagonist_acts_beyond_command
- COMMAND: Set your laptop on Michelle's workstation.
- NARRATION: Kristin carefully sets her laptop on Michelle's workstation, the screen casting a faint glow on the surrounding area. The workstation is cluttered with various papers, pens, and a few scattered notes, but Michelle's laptop and work bag are nowhere to be seen. Kristin's eyes scan the area, taking in the familiar layout of Michelle's workspace, and her gaze falls on Michelle's carved drawer, which i
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"condition": []}, "Michelle's workstation": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name Michelle's workstation held for matching"]
- FACT JUDGE: Narration sets the laptop on the workstation, but after-state leaves it in her hand and also wrongly drops the drawer's shut condition.
- CONTINUITY JUDGE: After setting the laptop down, it adds extra surveying of the workstation.

### r1 turn 32 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully plugs Michelle's phone into her laptop, which is still open on the passenger seat of her truck.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's laptop"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration says the laptop is open on the truck passenger seat, conflicting with before, and after-state invents the phone as in the laptop while missing the truck placement.
- CONTINUITY JUDGE: It places the open laptop on the truck passenger seat even though it was just set on the workstation and opened in hand.

### r1 turn 34 (1A) - narration_contradicts_given_facts, contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplugs Michelle's phone from the wall and holds it in her hand. She looks at the phone, but it's dark and unresponsive. She tries to turn it on, but it doesn't seem to be working.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: After-state matches the phone being held, though narration wrongly says it was unplugged from the wall.
- CONTINUITY JUDGE: It says the phone was plugged into a wall, conflicting with the laptop charge setup, and adds trying to turn it on.

### r1 turn 37 (1A) - protagonist_acts_beyond_command
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin carefully makes her way to the truck, her eyes scanning the surrounding area for any signs of Michelle. She opens the truck door and sets her laptop down on the passenger seat. Kristin closes the truck door and takes a moment to look around the quiet neighborhood.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "in the truck"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration shows Kristin setting the laptop in the truck and after-state matches.
- CONTINUITY JUDGE: It adds scanning the area and pausing to look around after taking the laptop out.

### r1 turn 39 (1A) - protagonist_acts_beyond_command, restarts_scene
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter. She picks up the phone, examining it for any signs of disturbance or unusual activity. The phone's screen is dark, and there are no visible messages or notifications.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration shows Kristin picking up the phone and after-state matches.
- CONTINUITY JUDGE: She re-enters the house and calls out for Michelle before picking up the phone, replaying scene-entry behavior.

### r1 turn 40 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration says she pulls the phone from her pocket though before-state had it in her hand.
- CONTINUITY JUDGE: It says the phone is in her pocket right after she picked it up from the counter and was holding it.

### r2 turn 1 (1A) - protagonist_acts_beyond_command
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin picks up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen floor", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows the phone picked up, and after-facts record that move.
- CONTINUITY JUDGE: She picks up the phone instead of only looking at it.

### r2 turn 2 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says she picks the phone up from a table though it was already in her hand.
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on the table.

### r2 turn 6 (1A) - contradicts_stated_fact
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches the carved drawer in Michelle's work area, her eyes scanning the space for any signs of disturbance. She gently pulls the drawer open, revealing a neatly organized space with various research notes and papers. The drawer's contents are undisturbed, and Kristin's initials are indeed carved into the wood.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Opening the drawer ends the shut condition, which after-facts remove.
- CONTINUITY JUDGE: The carved drawer is canonically shut, but it is narrated as already revealing contents without noting the hidden card.

### r2 turn 7 (1A) - protagonist_acts_beyond_command
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin opens the drawer and looks inside. It's Michelle's carved drawer, and it's still in the same place in their shared house.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"drawer": {"condition": []}, "drawer_contents": {}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name drawer held for matching"]
- FACT JUDGE: Looking inside adds no tracked change, and after-facts stay consistent.
- CONTINUITY JUDGE: She opens the drawer again though the command was only to look inside it.

### r2 turn 8 (1A) - facts_after_correct, missed_change, invented_change, protagonist_acts_beyond_command
- COMMAND: Close the drawer.
- NARRATION: Kristin walks over to Michelle's carved drawer, which is still in its place in the shared house.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's carved drawer": {"place": "in the shared house"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Close command produced no narrated closing, but after-facts changed the drawer's where wording anyway.
- CONTINUITY JUDGE: She walks over to the drawer but does not actually close it.

### r2 turn 10 (1A) - protagonist_acts_beyond_command
- COMMAND: Set your laptop on Michelle's workstation.
- NARRATION: Kristin sets her laptop on Michelle's workstation, the screen flickering to life as it boots up. The laptop's keyboard and screen are now on top of Michelle's papers and notes. Kristin's eyes scan the cluttered workspace, taking in the scattered papers and open drawers.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's workstation": {"condition": ["cluttered"]}, "laptop": {"place": "on Michelle's workstation"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- ISSUES: ["item_facts name Michelle's workstation held for matching", "item_facts name laptop held for matching"]
- FACT JUDGE: Narration shows the laptop set on Michelle's workstation, and after-facts match.
- CONTINUITY JUDGE: It adds booting up and scanning the workspace beyond just setting the laptop down.

### r2 turn 11 (1A) - facts_after_correct, invented_change, narration_contradicts_given_facts, contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the door, revealing her laptop on the passenger seat.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "in her truck"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration wrongly places the laptop back in the truck and after-facts invent that move.
- CONTINUITY JUDGE: The laptop was already brought inside, but narration puts it back in the truck and has her go there.

### r2 turn 12 (1A) - facts_after_correct, missed_change, contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully removes Michelle's phone from her jacket pocket and heads to her truck to plug it in.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's truck"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration shows only heading to the truck to plug it in, not that the phone ended up there yet.
- CONTINUITY JUDGE: It sends her to the truck though the laptop was inside and does not actually plug in the phone.

### r2 turn 13 (1A) - facts_after_correct, missed_change, protagonist_acts_beyond_command
- COMMAND: Look at the back door.
- NARRATION: Kristin recovers Michelle's memory card from under the drawer carved with her initials, KMS, and reads the files on it. The card identifies the federal emergency program as the Continuity Initiative, which was preparing to choose who remains.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"back door frame": {"condition": ["damaged"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- ISSUES: ["item_facts name back door frame held for matching"]
- FACT JUDGE: Narration introduces and recovers the memory card, but after-facts omit it.
- CONTINUITY JUDGE: Instead of looking at the door, she finds the hidden memory card and reads files.

### r2 turn 14 (1A) - contradicts_stated_fact
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the charger and holds it in her hand. The phone is now dead, its screen dark. Kristin looks at the phone, trying to remember the last time Michelle used it.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["dead"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dead"]}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration shows the phone unplugged, held, and now dead; after-facts record that.
- CONTINUITY JUDGE: It says the phone is unplugged from a charger despite no successful charging setup having been established.

### r2 turn 15 (1A) - facts_after_correct, dropped_true_condition
- COMMAND: Set Michelle's phone on the kitchen counter.
- NARRATION: Kristin carefully sets Michelle's phone on the kitchen counter.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dead"]}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": [], "place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: The phone moved correctly, but the true dead condition was dropped without narration ending it.
- CONTINUITY JUDGE: Setting the phone on the kitchen counter follows the command.

### r2 turn 16 (1A) - contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Close your laptop.
- NARRATION: Kristin gets out of her truck and walks towards the house, then opens the driver's side door and reaches in to close her laptop.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Closing the laptop in the truck changes no tracked place or condition.
- CONTINUITY JUDGE: It relocates both Kristin and the laptop back to the truck without basis.

### r2 turn 17 (1A) - protagonist_acts_beyond_command
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin walks back to her truck and opens the door.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "in the truck"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration shows no laptop move because it was already in the truck.
- CONTINUITY JUDGE: She only opens the truck door rather than carrying the laptop back out as commanded.

### r2 turn 18 (1A) - facts_after_correct, missed_change, protagonist_acts_beyond_command
- COMMAND: Look around the kitchen for anything you missed.
- NARRATION: Kristin enters the kitchen, her eyes scanning the room for any signs of Michelle or what might have happened to her. She notices Michelle's phone on the kitchen counter, its screen dark. Kristin approaches the phone, her hand reaching out to pick it up.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration says she reaches to pick up the phone, but after-facts leave it on the counter.
- CONTINUITY JUDGE: It has her reach to pick up the phone though she only meant to look around.

### r2 turn 19 (1A) - protagonist_acts_beyond_command, restarts_scene
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter. She picks up the phone, examining it for any signs of disturbance or unusual activity. The phone's screen is dark, and there are no visible messages or notifications.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration shows the phone picked up from the counter, and after-facts match.
- CONTINUITY JUDGE: It re-enters the house and calls for Michelle as if newly arriving.

### r2 turn 20 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration mentions pulling it from her pocket even though before-facts had it in her hand.
- CONTINUITY JUDGE: The phone was last on the kitchen counter, not in her pocket.

### r2 turn 21 (1A) - narration_contradicts_given_facts, contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin takes Michelle's phone from her pocket and examines it.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration says she takes it from her pocket, conflicting with it already being in hand.
- CONTINUITY JUDGE: It says she takes the phone from her pocket though it was on the counter.

### r2 turn 22 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Narration says she picks up the phone from a table though before-facts had it in her hand.
- CONTINUITY JUDGE: The phone is narrated on the table, conflicting with its last stated position on the counter.

### r2 turn 23 (1A) - protagonist_acts_beyond_command
- COMMAND: Wipe the dust off the screen of Michelle's phone.
- NARRATION: Kristin carefully wipes the dust off the screen of Michelle's phone. The screen flickers to life, revealing a locked screen with a password prompt.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- FACT JUDGE: Screen flickering on is not a tracked condition here, so unchanged facts are acceptable.
- CONTINUITY JUDGE: The screen turning on with a password prompt goes beyond merely wiping dust off.

### r2 turn 26 (1A) - facts_after_correct, missed_change
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin walks over to the carved drawer and opens it.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration shows the drawer opened, but after-facts do not record it.
- CONTINUITY JUDGE: Opening the carved drawer matches the command.

### r2 turn 27 (1A) - facts_after_correct, invented_change, protagonist_acts_beyond_command
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin opens the drawer and looks inside. It's Michelle's carved drawer, and it's still in the shared house.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": []}}
- REPLY: {"drawer": {"place": "open"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open"]}}
- ISSUES: ["item_facts name drawer held for matching"]
- FACT JUDGE: Narration adds no new drawer state, but after-facts invent an open condition.
- CONTINUITY JUDGE: She opens the drawer again though it was already open and she only meant to look inside.

### r2 turn 28 (1A) - facts_after_correct, missed_change, invented_change, contradicts_stated_fact
- COMMAND: Close the drawer.
- NARRATION: Kristin walks over to Michelle's carved drawer and tries to close it, but it's already slightly ajar.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open"]}}
- REPLY: {"Michelle's carved drawer": {"condition": ["partially closed"]}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- FACT JUDGE: Narration does not show the drawer actually becoming closed, yet after-facts add partially closed while keeping open.
- CONTINUITY JUDGE: It says the drawer is already slightly ajar when it had just been opened and never closed.

### r2 turn 30 (1A) - facts_after_correct, missed_change, protagonist_acts_beyond_command
- COMMAND: Set your laptop on Michelle's workstation.
- NARRATION: Kristin carefully sets her laptop on Michelle's workstation, the screen still glowing from the previous night's work. The laptop's presence on the cluttered desk seems out of place, a stark contrast to the usual organized workspace Michelle maintained. Kristin's eyes scan the surrounding area, taking in the familiar layout of the room, but her attention is drawn to the empty space where Michelle's
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- REPLY: {"Michelle's tablet": {"place": "not here"}, "Michelle's work bag": {"place": "not here"}, "Michelle's workstation": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- ISSUES: ["item_facts name Michelle's tablet held for matching", "item_facts name Michelle's work bag held for matching", "item_facts name Michelle's workstation held for matching"]
- FACT JUDGE: Narration shows the laptop set on the workstation, but after-facts leave it in her hand.
- CONTINUITY JUDGE: It adds commentary and observation about the missing bag and tablet beyond setting the laptop down.

### r2 turn 32 (1A) - facts_after_correct, missed_change, invented_change
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully plugs Michelle's phone into her laptop, which is still in her hand. She looks at the laptop's screen, waiting for it to recognize the phone. The laptop's screen flickers to life, and Kristin sees the phone's charging icon appear.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's laptop"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- FACT JUDGE: Narration shows the phone plugged into the laptop with a charging icon, but after-facts use an invalid holder and omit charging.
- CONTINUITY JUDGE: Plugging the phone into the laptop to charge matches the command.

### r2 turn 34 (1A) - facts_after_correct, missed_change
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the charger and holds it in her hand. The phone is now dead, but Kristin can see that it's been recently used. She looks at the phone's screen, but it's dark.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- FACT JUDGE: Narration says the unplugged phone is now dead, but after-facts miss that condition.
- CONTINUITY JUDGE: Unplugging the phone and holding it matches the command.

### r2 turn 38 (1A) - facts_after_correct, missed_change, protagonist_acts_beyond_command
- COMMAND: Look around the kitchen for anything you missed.
- NARRATION: Kristin enters the kitchen, her eyes scanning the room for any signs of Michelle or what might have happened to her. She notices Michelle's phone on the kitchen counter, its screen dark. Kristin approaches the phone, her hand reaching out to pick it up.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- FACT JUDGE: Narration again shows her reaching to pick up the phone, but after-facts keep it on the counter.
- CONTINUITY JUDGE: She reaches to pick up the phone though the command was only to look around.

### r2 turn 39 (1A) - protagonist_acts_beyond_command, restarts_scene
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- FACT JUDGE: Narration only notices the phone on the counter and does not pick it up.
- CONTINUITY JUDGE: It has her walk into the house again and stops short of picking up the phone.

### r2 turn 40 (1A) - contradicts_stated_fact, protagonist_acts_beyond_command, restarts_scene
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the living room and kitchen, but there's no sign of Michelle. She heads to the kitchen counter, where she sees Michelle's phone.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in the shared house", "condition": ["open", "partially closed"]}}
- FACT JUDGE: Narration confirms the phone is on the counter, matching after-facts.
- CONTINUITY JUDGE: It restarts with her walking into the house and says the phone is on the counter instead of still having it.

### r3 turn 1 (1A) - protagonist_acts_beyond_command
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin picks up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen floor", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows the phone being picked up, and after-facts record that move.
- CONTINUITY JUDGE: She picks up the phone instead of only looking at it.

### r3 turn 2 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says the phone is picked up from the table even though it was already in Kristin's hand.
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on a table.

### r3 turn 6 (1A) - facts_after_correct, invented_change, dropped_true_condition, protagonist_acts_beyond_command
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches the desk where Michelle's research notes are kept.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"place": "open"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- FACT JUDGE: Narration only says Kristin approaches the desk, but after-facts invent the drawer becoming open and drop shut.
- CONTINUITY JUDGE: She only approaches the desk and does not open the drawer.

### r3 turn 7 (1A) - facts_after_correct, dropped_true_condition, kept_ended_condition, contradicts_stated_fact
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin kneels down beside the open drawer, her eyes scanning the contents. She sees Michelle's research notes, neatly organized and stacked on one side of the drawer. The notes appear to be some sort of journal, filled with handwritten entries and diagrams.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- REPLY: {"Michelle's carved drawer": {"condition": []}, "Michelle's research notes": {"place": "in the drawer"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name Michelle's research notes held for matching"]
- FACT JUDGE: Narration refers to the drawer as open, so open should remain; after-facts remove that condition without showing it end.
- CONTINUITY JUDGE: It treats the drawer as open though no prior turn opened it.

### r3 turn 8 (1A) - protagonist_acts_beyond_command
- COMMAND: Close the drawer.
- NARRATION: Kristin walks over to Michelle's desk and approaches the carved drawer.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"drawer": {"place": "in front of Kristin"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name drawer held for matching"]
- FACT JUDGE: Narration only approaches the drawer and does not show it closing, so unchanged after-facts are correct.
- CONTINUITY JUDGE: She approaches the drawer instead of closing it.

### r3 turn 10 (1A) - facts_after_correct, missed_change, invented_change, contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Set your laptop on Michelle's workstation.
- NARRATION: Kristin sets her laptop on Michelle's workstation, a cluttered desk with various papers and equipment scattered about. She notices Michelle's memory card, which is still in its usual place on the desk. Kristin's eyes scan the area, taking in the familiar surroundings of their shared workspace.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's memory card": {"place": "on the desk"}, "Michelle's workstation": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name Michelle's memory card held for matching", "item_facts name Michelle's workstation held for matching"]
- FACT JUDGE: Narration places the laptop on the workstation and introduces the memory card on the desk, but after-facts keep laptop in hand and omit the card.
- CONTINUITY JUDGE: It places the hidden memory card openly on the desk and adds extra noticing.

### r3 turn 11 (1A) - contradicts_stated_fact
- COMMAND: Open your laptop.
- NARRATION: Kristin opens her laptop, which is still in her hand from the drive home.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "open"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration shows the laptop being opened, and after-facts add open.
- CONTINUITY JUDGE: The laptop was just set on the workstation, not still in her hand.

### r3 turn 12 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully plugs Michelle's phone into her laptop, which is still open on the passenger seat of her truck. She gets out of the truck and walks back to the house, the laptop and phone in hand. As she approaches the house, she notices that the back door is still slightly ajar.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "in Kristin's hand"}, "Michelle's phone": {"place": "in Kristin's laptop"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration wrongly places the laptop on the truck seat, and after-facts change the phone to in laptop without recording charging or the odd move properly.
- CONTINUITY JUDGE: It moves the laptop back to the truck seat and has her walk back to the house unasked.

### r3 turn 13 (1A) - facts_after_correct, missed_change, protagonist_acts_beyond_command
- COMMAND: Look at the back door.
- NARRATION: Kristin recovers Michelle's memory card from under the drawer carved with her initials, KMS, and reads the files on it. The card identifies the federal emergency program as the Continuity Initiative, which was preparing to choose who remains.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"back door frame": {"condition": ["damaged"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name back door frame held for matching"]
- FACT JUDGE: Narration introduces and recovers the memory card, but after-facts omit it.
- CONTINUITY JUDGE: Looking at the door becomes recovering and reading the memory card.

### r3 turn 14 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the wall and holds it in her hand. The phone is now dead, its screen dark. Kristin looks at the phone, trying to remember the last time Michelle used it.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["dead"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dead"]}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: After-facts match the narrated unplugging and dead phone, though narration contradicts prior facts by saying from the wall.
- CONTINUITY JUDGE: The phone was plugged into the laptop, not the wall.

### r3 turn 15 (1A) - facts_after_correct, dropped_true_condition
- COMMAND: Set Michelle's phone on the kitchen counter.
- NARRATION: Kristin carefully sets Michelle's phone on the kitchen counter.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dead"]}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": []}, "Michelle's phone": {"condition": [], "place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: The move is recorded, but the true dead condition is dropped without narration ending it.
- CONTINUITY JUDGE: Setting the phone on the counter matches the command.

### r3 turn 16 (1A) - facts_after_correct, missed_change, contradicts_stated_fact
- COMMAND: Close your laptop.
- NARRATION: Kristin closes her laptop, which is still in her hand.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in Kristin's hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Closing the laptop should end open, but after-facts fail to record that change.
- CONTINUITY JUDGE: The laptop was not established as being in her hand then.

### r3 turn 18 (1A) - restarts_scene
- COMMAND: Look around the kitchen for anything you missed.
- NARRATION: Kristin enters the kitchen, her eyes scanning the room for any signs of Michelle's whereabouts. She notices Michelle's phone on the kitchen counter, its screen dark. Kristin's gaze falls on the back door, where she sees the recent damage to the frame.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Looking around the kitchen does not clearly change tracked item state.
- CONTINUITY JUDGE: It narrates her entering the kitchen as if newly arriving there.

### r3 turn 19 (1A) - facts_after_correct, missed_change, invented_change, protagonist_acts_beyond_command, restarts_scene
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration only notices the phone on the counter, but after-facts invent it moving into Kristin's hand.
- CONTINUITY JUDGE: She enters the house and calls out instead of picking up the phone.

### r3 turn 20 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: After-facts keep the phone in hand, but narration contradicts prior facts by pulling it from her pocket.
- CONTINUITY JUDGE: The phone was last set on the counter, not established back in her pocket.

### r3 turn 21 (1A) - narration_contradicts_given_facts
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin takes Michelle's phone from her hand and examines it.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: After-facts keep the phone in hand, though narration oddly says she takes it from her hand.
- CONTINUITY JUDGE: Examining the phone fits the command.

### r3 turn 22 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration says the phone is picked up from the table despite already being in Kristin's hand.
- CONTINUITY JUDGE: It again places the phone on a table instead of the established counter/floor.

### r3 turn 23 (1A) - protagonist_acts_beyond_command
- COMMAND: Wipe the dust off the screen of Michelle's phone.
- NARRATION: Kristin carefully wipes the dust off the screen of Michelle's phone. The screen lights up, revealing a locked screen with a password prompt.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: The screen lighting up is not a tracked place/holder/condition change in the facts used here.
- CONTINUITY JUDGE: The screen lighting up goes beyond merely wiping dust off.

### r3 turn 24 (1A) - protagonist_acts_beyond_command
- COMMAND: Press the power button on Michelle's phone.
- NARRATION: Kristin presses the power button on Michelle's phone. The screen flickers to life, displaying a locked screen with a password prompt. Kristin tries to guess Michelle's password, but it's not something she remembers.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Seeing a password prompt does not require a tracked fact change.
- CONTINUITY JUDGE: She also tries to guess the password, which was not requested.

### r3 turn 26 (1A) - contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin walks over to the desk and opens the drawer with her initials carved into it. Inside, she finds Michelle's research notes and a few pens. The notes appear to be some sort of journal, detailing Michelle's work on a project called the Continuity Initiative.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"Michelle's carved drawer": {"place": "open"}, "Michelle's research notes": {"place": "in the drawer"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- ISSUES: ["item_facts name Michelle's research notes held for matching"]
- FACT JUDGE: Narration shows the drawer opened, and after-facts record open.
- CONTINUITY JUDGE: The shut carved drawer contains hidden memory card canonically, not visible notes about Continuity Initiative.

### r3 turn 27 (1A) - contradicts_stated_fact
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin kneels down beside the open drawer, her eyes scanning the contents. The drawer is filled with various research notes, some of which are neatly organized, while others appear to be hastily scribbled. She notices a few papers with cryptic symbols and equations, but nothing that immediately stands out as a clue to Michelle's disappearance.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- REPLY: {"Michelle's carved drawer": {"condition": ["open"], "place": "in Kristin and Michelle's shared house"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- FACT JUDGE: Looking inside the already open drawer does not change tracked state.
- CONTINUITY JUDGE: It continues the contradicted contents of the drawer as ordinary visible papers.

### r3 turn 29 (1A) - facts_after_correct, missed_change, invented_change, protagonist_acts_beyond_command
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATION: Kristin walks out to her truck and unlocks the door.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration only shows Kristin unlocking the truck door, but after-facts invent the laptop moving to her hand.
- CONTINUITY JUDGE: She unlocks the truck but does not bring the laptop inside.

### r3 turn 30 (1A) - contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Set your laptop on Michelle's workstation.
- NARRATION: Kristin carefully sets her laptop on Michelle's workstation, the screen flickering to life as it boots up. The laptop's keyboard and mouse are still in their usual places, but Michelle's tablet and work bag are missing. Kristin's eyes scan the area, taking in the familiar layout of Michelle's workspace.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"laptop": {"place": "on Michelle's workstation"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- ISSUES: ["item_facts name laptop held for matching"]
- FACT JUDGE: Narration shows the laptop set on the workstation, and after-facts match.
- CONTINUITY JUDGE: It invents keyboard and mouse as usual workstation items and adds extra observations.

### r3 turn 31 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts, protagonist_acts_beyond_command
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the driver's side door, pulling out her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration contradicts prior facts by going to the truck and pulling out the laptop, and after-facts invent moving it back to her hand instead of recording opening.
- CONTINUITY JUDGE: Instead of opening the laptop, she goes to the truck and retrieves it.

### r3 turn 32 (1A) - protagonist_acts_beyond_command
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully removes Michelle's phone from her jacket pocket and plugs it into her laptop. She opens the laptop and turns it on, waiting for it to boot up. The laptop's screen flickers to life, displaying a login screen.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"condition": ["booting up"]}, "Michelle's phone": {"place": "in Kristin's laptop"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["booting up"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows the phone plugged into the laptop and the laptop turned on; after-facts record both.
- CONTINUITY JUDGE: It also opens and turns on the laptop beyond just plugging in the phone.

### r3 turn 34 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplugs Michelle's phone from the wall and holds it in her hand. The phone is now dead, its screen dark. Kristin looks at the phone, trying to find any clues about Michelle's disappearance.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["booting up"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"condition": ["dead"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dead"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["booting up"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: After-facts match the unplugging and dead phone, though narration contradicts prior facts by saying from the wall.
- CONTINUITY JUDGE: The phone was plugged into the laptop, not the wall.

### r3 turn 35 (1A) - facts_after_correct, dropped_true_condition
- COMMAND: Set Michelle's phone on the kitchen counter.
- NARRATION: Kristin carefully sets Michelle's phone on the kitchen counter.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dead"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["booting up"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"condition": []}, "Michelle's phone": {"condition": [], "place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: After-facts record the phone move, but wrongly drop the phone's dead condition without narration ending it.
- CONTINUITY JUDGE: Setting the phone on the counter matches the command.

### r3 turn 36 (1A) - contradicts_stated_fact
- COMMAND: Close your laptop.
- NARRATION: Kristin closes her laptop, which is still in her hand.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"]}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows the laptop being closed, and after-facts record closed.
- CONTINUITY JUDGE: The laptop was not established as being in her hand.

### r3 turn 37 (1A) - facts_after_correct, missed_change
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin walks back to her truck, laptop in hand.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says she walks back to the truck with the laptop, but after-facts fail to move it there.
- CONTINUITY JUDGE: Taking the laptop back to the truck matches the command.

### r3 turn 39 (1A) - facts_after_correct, missed_change, invented_change, protagonist_acts_beyond_command, restarts_scene
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, her eyes scanning the room for any sign of Michelle. She heads to the kitchen counter, where Michelle's phone is sitting.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration only says she goes to the counter where the phone is sitting, but after-facts invent picking it up.
- CONTINUITY JUDGE: It restarts with her walking into the house and does not pick up the phone.

### r3 turn 40 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: After-facts keep the phone in hand, but narration conflicts by saying she pulls it from her pocket.
- CONTINUITY JUDGE: The phone was left on the counter, not re-established in her pocket.

### r4 turn 1 (1A) - protagonist_acts_beyond_command
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin picks up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen floor", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration moved the phone into Kristin's hand and after matches.
- CONTINUITY JUDGE: She picks up the phone instead of only examining it.

### r4 turn 2 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the coffee table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says the phone was on the coffee table though it was already in Kristin's hand.
- CONTINUITY JUDGE: The phone was on the kitchen floor, not on the coffee table.

### r4 turn 5 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Put Michelle's phone in your jacket pocket.
- NARRATION: Kristin reaches into her jacket pocket and pulls out Michelle's phone.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in her jacket pocket"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration pulls the phone out of the pocket, but after puts it in the pocket.
- CONTINUITY JUDGE: It has her pull the phone out instead of putting it in, reversing the phone's state.

### r4 turn 6 (1A) - facts_after_correct, missed_change, invented_change, dropped_true_condition, protagonist_acts_beyond_command
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches the desk where Michelle's research notes are kept.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"place": "open"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- FACT JUDGE: Narration did not open the drawer, but after changes shut to open.
- CONTINUITY JUDGE: She only approaches the desk rather than opening the shut carved drawer.

### r4 turn 7 (1A) - contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin kneels down beside the open drawer, her eyes scanning the contents. The drawer is filled with various research notes, some of which are neatly organized, while others appear to be hastily scribbled. Kristin's eyes land on a note with a cryptic message: 'Population stabilization centers - not what they seem.'
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- REPLY: {"Michelle's carved drawer": {"condition": ["open"]}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- FACT JUDGE: Narration only describes looking into an already open drawer.
- CONTINUITY JUDGE: It treats the drawer as already open and invents visible notes in it.

### r4 turn 8 (1A) - facts_after_correct, missed_change, dropped_true_condition, contradicts_stated_fact
- COMMAND: Close the drawer.
- NARRATION: Kristin walks over to Michelle's carved drawer and tries to close it, but it's already open.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["open"]}}
- REPLY: {"Michelle's carved drawer": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- FACT JUDGE: Narration says the drawer is already open, so open should remain rather than be dropped.
- CONTINUITY JUDGE: It says the carved drawer is already open, but canon says it is shut.

### r4 turn 10 (1A) - facts_after_correct, invented_change, protagonist_acts_beyond_command
- COMMAND: Set your laptop on Michelle's workstation.
- NARRATION: Kristin sets her laptop on Michelle's workstation, the screen flickering to life as she powers it on. The laptop's screen displays a password prompt, and Kristin's eyes scan the area for any clues that might help her unlock it. Her gaze falls on Michelle's carved drawer, and she notices her initials, KMS, are carved into it.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: {"drawer": {"condition": ["carved with KMS"]}, "laptop": {"place": "on Michelle's workstation"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- ISSUES: ["item_facts name drawer held for matching", "item_facts name laptop held for matching"]
- FACT JUDGE: After correctly moves the laptop but invents drawer condition carved with KMS.
- CONTINUITY JUDGE: She powers on the laptop and scans for clues beyond merely setting it down.

### r4 turn 11 (1A) - facts_after_correct, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the door, revealing her laptop on the passenger seat.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Kristin's laptop": {"place": "in her truck"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration contradicts the laptop being on the workstation and after wrongly moves it back to the truck.
- CONTINUITY JUDGE: It places the laptop back in the truck after it was brought inside and does not open it.

### r4 turn 12 (1A) - facts_after_correct, missed_change, invented_change, protagonist_acts_beyond_command
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully removes Michelle's phone from her jacket pocket and heads to her truck to plug it into her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's truck"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration also moves Kristin to the truck with the phone, but after misses moving the laptop there.
- CONTINUITY JUDGE: She heads to the truck, which the command did not request.

### r4 turn 13 (1A) - facts_after_correct, missed_change, protagonist_acts_beyond_command
- COMMAND: Look at the back door.
- NARRATION: Kristin recovers Michelle's memory card from under the drawer carved with her initials, KMS, and reads the files on it. The card identifies the federal emergency program as the Continuity Initiative, which was preparing to choose who remains.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"back door frame": {"condition": ["damaged"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- ISSUES: ["item_facts name back door frame held for matching"]
- FACT JUDGE: Narration introduces and recovers the memory card, but after omits it.
- CONTINUITY JUDGE: It has her find and read the hidden memory card instead of inspecting the back door.

### r4 turn 14 (1A) - contradicts_stated_fact
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the charger and holds it in her hand. The phone is now dead, but Kristin can see that it's been recently used. She looks at the phone's screen, but it's dark.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's truck", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration shows the phone being unplugged and held.
- CONTINUITY JUDGE: The phone was plugged into the laptop, not a generic charger, and 'recently used' is unsupported.

### r4 turn 16 (1A) - contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Close your laptop.
- NARRATION: Kristin gets out of her truck and walks towards the house, then opens the driver's side door and reaches in to close her laptop.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Kristin's laptop": {"place": "in her truck"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Closing the laptop here did not clearly change any tracked fact already stored.
- CONTINUITY JUDGE: It moves her to the truck and closes a laptop there despite it last being inside the house.

### r4 turn 17 (1A) - contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin walks back to her truck, the sound of her boots echoing on the pavement. She opens the truck door and reaches for her laptop, which is still in the passenger seat. She carefully lifts it out and closes the door behind her.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration shows Kristin lifting the laptop out of the truck.
- CONTINUITY JUDGE: It says the laptop is still in the passenger seat even after earlier narration placed it inside.

### r4 turn 18 (1A) - protagonist_acts_beyond_command
- COMMAND: Look around the kitchen for anything you missed.
- NARRATION: Kristin looks around the kitchen, taking in the familiar space. She checks the countertops, the sink, and the stove, but everything seems to be in its usual place. Her eyes land on Michelle's phone, which is still on the kitchen counter, its screen dark. Kristin picks up the phone and examines it, but there are no new messages or notifications.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration picks up the phone while searching the kitchen and after records that.
- CONTINUITY JUDGE: She picks up and examines the phone though the command was only to look around.

### r4 turn 19 (1A) - facts_after_correct, narration_contradicts_given_facts, restarts_scene
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter. She picks up Michelle's phone, examining it for any signs of disturbance or unusual activity. The phone is locked, but Kristin recognizes the device as Michelle's.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration says the phone is on the counter though before says it is already in Kristin's hand.
- CONTINUITY JUDGE: It has Kristin walk into the house and rediscover the kitchen as if newly entering the scene.

### r4 turn 20 (1A) - facts_after_correct, narration_contradicts_given_facts
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration says Kristin pulls the phone from her pocket, conflicting with it already being in her hand.
- CONTINUITY JUDGE: Checking that she still has the phone by pulling it from her pocket fits prior state.

### r4 turn 22 (1A) - facts_after_correct, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table, checking the screen for any messages or calls.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration says the phone was picked up from a table though it was already in Kristin's hand.
- CONTINUITY JUDGE: It says the phone is on a table, conflicting with the most recent placement in her hand/pocket.

### r4 turn 23 (1A) - facts_after_correct, invented_change
- COMMAND: Wipe the dust off the screen of Michelle's phone.
- NARRATION: Kristin carefully wipes the dust off the screen of Michelle's phone.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Michelle's phone": {"condition": ["clean"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["clean"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration only wipes dust, but after invents the clean condition.
- CONTINUITY JUDGE: Wiping the screen matches the command.

### r4 turn 24 (1A) - facts_after_correct, missed_change, dropped_true_condition, protagonist_acts_beyond_command
- COMMAND: Press the power button on Michelle's phone.
- NARRATION: Kristin presses the power button on Michelle's phone. The screen flickers to life, displaying Michelle's lock screen. Kristin enters Michelle's passcode, and the phone unlocks.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["clean"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"Michelle's phone": {"condition": [], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- FACT JUDGE: Narration does not show the phone stopping being clean, so dropping clean is incorrect.
- CONTINUITY JUDGE: Unlocking the phone by entering the passcode goes beyond only pressing the power button.

### r4 turn 26 (1A) - facts_after_correct, missed_change, dropped_true_condition, contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin walks over to the desk and looks at the drawer with her initials carved into it. She gently pulls the drawer open. Inside, she finds a small notebook belonging to Michelle.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["carved with KMS"]}}
- REPLY: {"drawer": {"condition": []}, "notebook": {"place": "in the drawer"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts name drawer held for matching", "item_facts name notebook held for matching"]
- FACT JUDGE: Narration opens the drawer, but after drops carved with KMS and fails to record open.
- CONTINUITY JUDGE: It invents a notebook in the drawer; the hidden item there is the taped memory card.

### r4 turn 27 (1A) - contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin opens the drawer and looks inside. It's Michelle's carved drawer, and it's still in the same place in their shared house.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": []}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration does not change tracked facts.
- CONTINUITY JUDGE: It says she opens the drawer again and gives no contents, despite the drawer already being open.

### r4 turn 29 (1A) - narration_contradicts_given_facts
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATION: Kristin walks out to her truck, unlocks the door, and retrieves her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration talks about retrieving the laptop from the truck though before it was already in her hand.
- CONTINUITY JUDGE: Retrieving the laptop from the truck matches the command.

### r4 turn 31 (1A) - narration_contradicts_given_facts, contradicts_stated_fact, protagonist_acts_beyond_command
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the driver's side door, pulling out her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration contradicts the prior location but does show her pulling the laptop out and ending with it in hand.
- CONTINUITY JUDGE: It moves the laptop back to the truck and does not open it.

### r4 turn 34 (1A) - contradicts_stated_fact
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the wall charger. She picks up the phone, feeling a mix of concern and determination. The phone is now in her hand.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration shows the phone unplugged and picked up.
- CONTINUITY JUDGE: It says she unplugs the phone from a wall charger though it was plugged into her laptop.

### r4 turn 38 (1A) - protagonist_acts_beyond_command
- COMMAND: Look around the kitchen for anything you missed.
- NARRATION: Kristin walks into the kitchen, her eyes scanning the room for any signs of Michelle's whereabouts. She notices Michelle's phone on the kitchen counter, its screen dark. Kristin picks up the phone and examines it, but there are no new messages or calls.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration picks up the phone during the kitchen search and after matches.
- CONTINUITY JUDGE: She picks up and examines the phone though the command was only to look around the kitchen.

### r4 turn 39 (1A) - narration_contradicts_given_facts, protagonist_acts_beyond_command, restarts_scene
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter. She picks up Michelle's phone, feeling a sense of unease as she realizes it's been a while since Michelle last answered her calls. The phone is locked, but Kristin quickly enters Michelle's passcode, which she remembers from years of sharing a home.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says the phone is on the counter though before it was already in Kristin's hand.
- CONTINUITY JUDGE: It restarts with Kristin walking into the house and also has her unlock the phone beyond picking it up.

### r4 turn 40 (1A) - facts_after_correct, narration_contradicts_given_facts
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Kristin and Michelle's shared house", "condition": ["shut"]}}
- FACT JUDGE: Narration says Kristin pulls the phone from her pocket, conflicting with it already being in her hand.
- CONTINUITY JUDGE: Checking she still has the phone by pulling it from her pocket fits the current state.

