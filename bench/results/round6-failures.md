# Round 6 failures, every failing turn

Source: bench/results/item-facts-v7-two-scene-1a, commit cc1e422. Four replicates.

Changes since round 5: a thing's location is called place everywhere; the drawer is just "drawer";
compound commands are split into separate sentences by the engine before narration; the narrator's
example rule shows a thrown thing falling to the floor broken; new things the narrator introduces are
recorded on the same turn; THINGS carries a tracked thing only when the command refers to it or a
reachable transition needs it; judge verdicts carry real turn numbers.

The narrator doing more than the command asked is NOT counted as a failure. A turn appears here only
for a capture defect, or for narration that contradicts canon or the facts it was given.

## Counts

**two-scene (4 replicates, 46 turns)** - 19 turns with a real failure
  - contradicts_stated_fact: 11
  - invented_change: 8
  - facts_after_wrong: 7
  - narration_contradicts_given_facts: 6
  - kept_ended_condition: 3
  - missed_change: 3
  - restarts_scene: 3
  - dropped_true_condition: 1
  - narrator initiative (context, not a failure): 14 turns; of those, 12 kept facts correct (86%) and 1 missed the change

## two-scene (4 replicates, 46 turns)

### r1 turn 2 (1A) - facts_after_wrong, missed_change, invented_change, kept_ended_condition, contradicts_stated_fact
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches Michelle's workstation and looks at the drawer with the KMS initials carved into it. She carefully opens the drawer, revealing a space that was previously shut. Inside, she finds a few pens, a notebook, and a small USB drive.
- GIVEN: {"drawer": {"place": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"USB drive": {"condition": ["unexamined"], "place": "in drawer"}, "drawer": {"condition": ["open"], "place": "open"}}
- AFTER: {"drawer": {"place": "in Michelle's workstation", "condition": ["open", "unexamined"]}}
- ISSUES: ["item_facts for 'drawer' refused place 'in drawer' because it is fixed"]
- FACT JUDGE: The drawer was opened but after-facts kept shut implicitly by omission of its ending and added unshown unexamined while missing the introduced USB drive.
- CONTINUITY JUDGE: It says the opened drawer contains a small USB drive, but the hidden canon says the memory card is taped beneath the drawer and stays hidden until found there.

### r1 turn 4 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATED COMMAND: Go out to your truck. Bring your laptop inside.
- NARRATION: Kristin walks out to her truck, which is parked on the street in front of the house. She unlocks the truck and opens the driver's side door. Kristin retrieves her laptop from the passenger seat and closes the truck door. She walks back to the house, laptop in hand.
- GIVEN: {"Kristin's laptop": {"place": "in Kristin's truck outside the house", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in Kristin's hand"}}
- AFTER: {"Kristin's laptop": {"place": "in Kristin's hand", "condition": ["closed"]}}
- FACT JUDGE: The narration says the laptop was on the passenger seat, conflicting with the given truck location, and after-facts also add unshown closed.
- CONTINUITY JUDGE: The laptop is canonically in Kristin's truck outside the house, not specifically on the passenger seat.

### r1 turn 8 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Leave the house and drive to the park with Michelle's phone.
- NARRATED COMMAND: Leave the house. Drive to the park with Michelle's phone.
- NARRATION: Kristin carefully exits the house, looking around cautiously. She gets into her truck and starts the engine. She drives through the emergency-clogged streets, Michelle's broken phone lying on the passenger seat.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}, "Kristin's laptop": {"place": "in the truck", "condition": ["closed"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "on the passenger seat"}}
- AFTER: {"Michelle's phone": {"place": "on the passenger seat", "condition": ["broken"]}, "Kristin's laptop": {"place": "in the truck", "condition": ["closed"]}}
- FACT JUDGE: The narration places the broken phone on the passenger seat, and after-facts record that.
- CONTINUITY JUDGE: The phone was just picked up, but now it is on the passenger seat, and the command did not ask Kristin to set it there.

### r1 turn 9 (1B) - contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin looks down at the passenger seat and sees Michelle's phone, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "on the passenger seat", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "on the passenger seat"}}
- AFTER: {"Michelle's phone": {"place": "on the passenger seat", "condition": ["broken"]}}
- FACT JUDGE: This is only a check; the facts stay the same and match the narration.
- CONTINUITY JUDGE: It says the phone is on the passenger seat and has a cracked screen, both details unsupported by the prior narrated state.

### r1 turn 10 (1B) - restarts_scene [narrator initiative]
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin scans the area around the bench, searching for any signs of Michelle's presence. She notices a small piece of paper on the ground near the service path. The paper appears to be a receipt from a local coffee shop, but there's a handwritten note on the back that reads 'Meet me at the old warehouse at midnight.'
- GIVEN: {}
- REPLY: {"note": {"condition": ["handwritten"], "place": "on the receipt"}, "receipt": {"condition": ["crumpled"], "place": "on the ground"}}
- AFTER: {"note": {"place": "on the receipt", "condition": ["handwritten"]}, "receipt": {"place": "on the ground", "condition": ["crumpled"]}}
- FACT JUDGE: The narration introduces a receipt and a handwritten note, and after-facts record both.
- CONTINUITY JUDGE: It introduces a newly discovered bench area and an unprompted note as though beginning a new scene rather than continuing established action.

### r1 turn 12 (1B) - contradicts_stated_fact
- COMMAND: Check who has Michelle's phone now.
- NARRATION: Kristin looks down at Michelle's phone in her hand, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- FACT JUDGE: The check confirms the phone remains in Kristin's hand with the same broken condition.
- CONTINUITY JUDGE: The prior turn had Kristin holding the phone out to the man, but this turn states it is in her hand without any intervening resolution.

### r2 turn 11 (1B) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Walk over to the man watching you and hand him Michelle's phone.
- NARRATED COMMAND: Walk over to the man watching you. Hand him Michelle's phone.
- NARRATION: Kristin walks over to the man watching her, a mixture of caution and determination on her face. She hands him Michelle's phone, which is still on the passenger seat, its screen cracked and unresponsive. The man takes the phone, his eyes flicking to the broken screen before returning to Kristin.
- GIVEN: {"Michelle's phone": {"place": "on the passenger seat", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in the man's hand"}}
- AFTER: {"Michelle's phone": {"place": "in the man's hand", "condition": ["broken"]}}
- FACT JUDGE: Narration wrongly says Kristin hands over a phone that was on the passenger seat while she walked to the man, without showing her taking it first.
- CONTINUITY JUDGE: It says she hands him the phone while it is still on the passenger seat, conflicting with itself and prior possession.

### r3 turn 2 (1A) - facts_after_wrong, missed_change, invented_change, dropped_true_condition, kept_ended_condition
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches Michelle's workstation and looks at the drawer with the KMS initials carved into it. She carefully opens the drawer, revealing its contents. Inside, she finds a few pens, a notebook, and a USB drive.
- GIVEN: {"drawer": {"place": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"USB drive": {"condition": ["unexamined"], "place": "in drawer"}, "drawer": {"condition": ["open"], "place": "in Michelle's workstation"}}
- AFTER: {"drawer": {"place": "in Michelle's workstation", "condition": ["open", "unexamined"]}}
- ISSUES: ["item_facts for 'drawer' refused place 'in drawer' because it is fixed"]
- FACT JUDGE: Drawer became open, but after-state wrongly kept no end to shut/open properly, added unexamined, and omitted introduced contents.
- CONTINUITY JUDGE: Opening the shut drawer matches canon; the added contents do not conflict with stated facts.

### r3 turn 3 (1A) - narration_contradicts_given_facts
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATED COMMAND: Pick up Michelle's phone. Put it in your pocket.
- NARRATION: Kristin reaches into the room and picks up Michelle's phone. She puts the phone in her pocket.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- FACT JUDGE: After-state matches the narrated pocketing, though narration redundantly says she picked it up despite already holding it.
- CONTINUITY JUDGE: Picking up the phone and pocketing it matches the command and prior placement.

### r3 turn 4 (1A) - invented_change, narration_contradicts_given_facts
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATED COMMAND: Go out to your truck. Bring your laptop inside.
- NARRATION: Kristin walks out to her truck, which is parked on the street in front of the house. She unlocks the truck and opens the driver's side door. Kristin retrieves her laptop from the passenger seat and closes the truck door. She walks back to the house, laptop in hand.
- GIVEN: {"Kristin's laptop": {"place": "in Kristin's truck outside the house", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in Kristin's hand"}}
- AFTER: {"Kristin's laptop": {"place": "in Kristin's hand", "condition": ["closed"]}}
- FACT JUDGE: Place change is correct, but after-state adds closed, and narration says passenger seat though before said only in truck.
- CONTINUITY JUDGE: The laptop is canonically in Kristin's truck, and bringing it inside matches the command.

### r3 turn 9 (1B) - contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin looks down at the passenger seat and sees Michelle's phone, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "on the passenger seat", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "on the passenger seat"}}
- AFTER: {"Michelle's phone": {"place": "on the passenger seat", "condition": ["broken"]}}
- FACT JUDGE: This is only a check; after-state correctly stays the same.
- CONTINUITY JUDGE: Earlier narration had Kristin pick the phone up, so it should not now be on the passenger seat unless she set it down.

### r3 turn 11 (1B) - narration_contradicts_given_facts
- COMMAND: Walk over to the man watching you and hand him Michelle's phone.
- NARRATED COMMAND: Walk over to the man watching you. Hand him Michelle's phone.
- NARRATION: Kristin walks over to the man watching her, her eyes fixed on his face. She hands him Michelle's phone, her hand extended in a deliberate gesture. The man takes the phone, his expression unreadable, and Kristin waits for a reaction.
- GIVEN: {"Michelle's phone": {"place": "on the passenger seat", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"place": "in the man's hand"}}
- AFTER: {"Michelle's phone": {"place": "in the man's hand", "condition": ["broken"]}}
- FACT JUDGE: After-state matches the handoff, but narration conflicts with before-state because the phone was on the passenger seat, not already with Kristin.
- CONTINUITY JUDGE: Walking to the man and handing over the phone follows the command.

### r4 turn 2 (1A) - facts_after_wrong, invented_change, kept_ended_condition
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin approaches Michelle's workstation and looks at the drawer with her initials carved into it.
- GIVEN: {"drawer": {"place": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"drawer": {"condition": ["open"], "place": "in Michelle's workstation"}}
- AFTER: {"drawer": {"place": "in Michelle's workstation", "condition": ["open"]}}
- FACT JUDGE: Narration only says she looks at the shut drawer; after-facts invent it being open and wrongly remove shut.
- CONTINUITY JUDGE: Approaching and looking at the drawer is within the command, and nothing conflicts with prior facts.

### r4 turn 3 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts [narrator initiative]
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATED COMMAND: Pick up Michelle's phone. Put it in your pocket.
- NARRATION: Kristin reaches into the room and picks up Michelle's phone.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hands", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's pocket", "condition": []}}
- FACT JUDGE: Before-facts already had the phone in Kristin's hands, so narration conflicts, and pocketing it was not narrated.
- CONTINUITY JUDGE: The command also said to put the phone in her pocket, but the narration only has her pick it up.

### r4 turn 5 (1A) - facts_after_wrong, missed_change, invented_change, contradicts_stated_fact, restarts_scene [narrator initiative]
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin walks back to her truck, opens the door, and retrieves her laptop.
- GIVEN: {"Kristin's laptop": {"place": "in Kristin's truck outside the house", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in Kristin's truck"}}
- AFTER: {"Kristin's laptop": {"place": "in Kristin's truck", "condition": ["closed"]}}
- FACT JUDGE: Narration shows taking the laptop from the truck, but after-facts leave it in the truck and add closed without support.
- CONTINUITY JUDGE: The laptop is already canonically in Kristin's truck, so carrying it back out there is impossible; the narration also re-enters the truck scene and retrieves instead of carries.

### r4 turn 7 (1A) - contradicts_stated_fact
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"place": "on the kitchen floor", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- FACT JUDGE: Narration shows Kristin picking up the broken phone, and after-facts match.
- CONTINUITY JUDGE: Earlier narration had the phone put in Kristin's pocket and then taken out and thrown against the wall, so it should not simply be on the kitchen floor intact as stated here.

### r4 turn 9 (1B) - contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin checks her hand and sees Michelle's phone, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- FACT JUDGE: Checking the phone does not change anything, and after-facts stay the same.
- CONTINUITY JUDGE: The prior turn placed the phone on the floor, but this turn says Kristin sees it in her hand.

### r4 turn 10 (1B) - restarts_scene [narrator initiative]
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin scans the area around the bench, searching for any signs of Michelle's presence. She notices a small piece of paper on the ground near the service path. The paper appears to be a receipt from a local coffee shop, but there's a handwritten note on the back that reads 'Meet me at the old warehouse at midnight.'
- GIVEN: {}
- REPLY: {"note": {"condition": ["handwritten"], "place": "on the receipt"}, "receipt": {"condition": ["crumpled"], "place": "on the ground"}}
- AFTER: {"note": {"place": "on the receipt", "condition": ["handwritten"]}, "receipt": {"place": "on the ground", "condition": ["crumpled"]}}
- FACT JUDGE: Narration introduces the receipt and note, and after-facts record them.
- CONTINUITY JUDGE: This abruptly shifts to a bench from a different scene and introduces discovering new evidence there as if newly arrived.

### r4 turn 12 (1B) - contradicts_stated_fact
- COMMAND: Check who has Michelle's phone now.
- NARRATION: Kristin looks down at Michelle's phone in her hand, its screen cracked and dark.
- GIVEN: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"place": "in Kristin's hand", "condition": ["broken"]}}
- FACT JUDGE: Narration confirms the phone is still in Kristin's hand, matching after-facts.
- CONTINUITY JUDGE: The previous turn had Kristin hand the phone to the man, but this turn says it is in her hand.

