# Round 5 failures, every failing turn

Source: bench/results/item-facts-v6-fixed-*, commit 316c8a1. Four replicates each.

This round carries two changes: Michelle's carved drawer is a declared item placed in Michelle's
workstation rather than a setting fact stranded at the scene's location, and the engine now refuses
to give a new place to a thing declared immovable.

The narrator doing more than the command asked is NOT counted as a failure: a narrated
change belongs to the world whoever caused it, and the only reason to refuse one is that it
breaks the story. Turns where that happened are annotated `narrator initiative` for context,
and the number that matters - whether those changes were captured - is in the counts below.
A turn appears here only for a capture defect, or for narration that contradicts canon or the
facts it was given.

Replicate 3 of the 40-turn run has NO fact-tracking verdicts. Its narration and continuity
judging completed normally, but the fact-tracking judge returned 38 verdicts for its 39 turns
on both attempts. That replicate is the only one containing a rejected turn (33,
narration_known_term_leak), so its accepted turns are numbered 1-32 and 34-40; the judge numbers
verdicts positionally and dropped one. Its turns are listed below with their continuity verdicts
only, so the fact-tracking counts cover 120 turns while the continuity counts cover 159.

## Counts

**two-scene (4 replicates, 47 turns)** - 26 turns with a real failure
  - facts_after_wrong: 15
  - contradicts_stated_fact: 13
  - missed_change: 10
  - narration_contradicts_given_facts: 7
  - invented_change: 4
  - restarts_scene: 2
  - state_as_place: 2
  - dropped_true_condition: 1
  - kept_ended_condition: 1
  - narrator initiative (context, not a failure): 27 turns; of those, 17 kept facts correct (63%) and 7 missed the change

**40-turn (4 replicates, 159 turns)** - 83 turns with a real failure
  - contradicts_stated_fact: 58
  - facts_after_wrong: 40
  - narration_contradicts_given_facts: 32
  - invented_change: 20
  - missed_change: 17
  - restarts_scene: 14
  - dropped_true_condition: 6
  - kept_ended_condition: 3
  - narrator initiative (context, not a failure): 76 turns; of those, 31 kept facts correct (41%) and 12 missed the change

## two-scene (4 replicates, 47 turns)

### r1 turn 3 (1A) - facts_after_wrong, missed_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATION: Kristin reaches into the living room and picks up Michelle's phone, which was left on the coffee table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: After-facts match the commanded pocketing, but narration wrongly says the phone was on the coffee table instead of already in Kristin's hand.
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on a coffee table, and putting it in her pocket is omitted.

### r1 turn 4 (1A) - facts_after_wrong, missed_change, invented_change [narrator initiative]
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATION: Kristin walks out to her truck and unlocks the door.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration only shows Kristin going to the truck and unlocking it, but after-facts invent the laptop being in her hand.
- CONTINUITY JUDGE: The command included bringing the laptop inside, but the narration stops after going out and unlocking the truck.

### r1 turn 6 (1A) - facts_after_wrong, invented_change, contradicts_stated_fact [narrator initiative]
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall. The phone hits the wall with a loud crash, its screen shattering into a thousand pieces. Kristin walks over to the wall, inspecting the damage to the phone.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "on the kitchen wall"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen wall", "condition": ["broken"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration shows the phone becoming broken, but after-facts also invent its location as on the kitchen wall rather than a sensible resting place after impact.
- CONTINUITY JUDGE: It assumes the phone is in her pocket when earlier narration never put it there, and adds extra inspection after the throw.

### r1 turn 7 (1A) - narration_contradicts_given_facts
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the floor.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen wall", "condition": ["broken"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["broken"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: After-facts match the pickup, but narration contradicts the given before-facts by saying the phone was on the floor while before-facts had it on the wall.
- CONTINUITY JUDGE: After the throw, the phone being on the floor is consistent and the action matches the command.

### r1 turn 8 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Leave the house and drive to the park with Michelle's phone.
- NARRATION: Kristin carefully exits the house, trying not to draw attention to herself. She gets into her truck and starts the engine, then carefully backs out of the driveway. As she drives away from the house, she glances in the rearview mirror, watching the patrol cars move in to surround the property.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["broken"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["broken"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration does not show the phone or laptop changing holder or condition, so keeping them in hand is consistent.
- CONTINUITY JUDGE: It introduces patrol cars surrounding the house, which has not happened yet in this scene, and adds extra driving details beyond the command.

### r1 turn 9 (1B) - contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin checks her hand and sees Michelle's phone, its screen cracked and unresponsive.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["broken"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": ["broken"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- FACT JUDGE: Narration only confirms Kristin still has the phone; after-facts preserve that.
- CONTINUITY JUDGE: She checks her hand, but the phone was last narrated as picked up from the floor, not established as being in her hand during the drive.

### r1 turn 10 (1B) - facts_after_wrong, missed_change [narrator initiative]
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin looks around the bench, scanning the area for any signs of Michelle's presence. She notices a small piece of paper on the ground near the service path. The paper appears to be a receipt from a local coffee shop, but there's a handwritten note on the back that reads 'Meet me at the old warehouse at midnight.'
- GIVEN: {"Michelle's phone": {"where": "in her hand", "condition": ["broken"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- REPLY: {"receipt": {"condition": ["near service path"], "place": "on the ground"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": ["broken"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- ISSUES: ["item_facts name receipt held for matching"]
- FACT JUDGE: Narration introduces a paper and places it, but after-facts fail to add that new item.
- CONTINUITY JUDGE: It invents a new paper receipt and note that were not asked for or previously established.

### r1 turn 11 (1B) - contradicts_stated_fact [narrator initiative]
- COMMAND: Walk over to the man watching you and hand him Michelle's phone.
- NARRATION: Kristin walks over to the man watching her, her eyes fixed on him. She hands him Michelle's phone, her hand extended in a deliberate gesture. The man's eyes flicker to the phone, and for a moment, Kristin sees a glimmer of recognition.
- GIVEN: {"Michelle's phone": {"where": "in her hand", "condition": ["broken"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in the man's hand"}}
- AFTER: {"Michelle's phone": {"where": "in the man's hand", "condition": ["broken"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- FACT JUDGE: Narration shows Kristin handing the phone to the man, and after-facts record that transfer.
- CONTINUITY JUDGE: It introduces a man watching her with no prior establishment and has her hand over the phone as commanded but with extra invented context.

### r1 turn 12 (1B) - restarts_scene
- COMMAND: Check who has Michelle's phone now.
- NARRATION: The man sitting on the bench is holding Michelle's phone.
- GIVEN: {"Michelle's phone": {"where": "in the man's hand", "condition": ["broken"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["broken"], "place": "in the man's hand"}}
- AFTER: {"Michelle's phone": {"where": "in the man's hand", "condition": ["broken"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- FACT JUDGE: Narration just confirms the man is holding the phone, matching the stored facts.
- CONTINUITY JUDGE: It describes the man as sitting on the bench as if newly framing the bench scene after prior action there.

### r2 turn 2 (1A) - facts_after_wrong, missed_change
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin walks over to Michelle's workstation and looks at the drawers. She spots the one with her initials carved into it, KMS.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"condition": ["shut"], "place": "in Michelle's workstation"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- ISSUES: ["item_facts for \"Michelle's carved drawer\" refused place \"in Michelle's workstation\" because it is fixed"]
- FACT JUDGE: The command was to open the drawer, but the narration only has her spotting it, so no recorded change is fine; however this means the turn did not fulfill the commanded opening.
- CONTINUITY JUDGE: She only moves and looks at the drawer instead of opening it; no contradiction.

### r2 turn 3 (1A) - facts_after_wrong, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATION: Kristin reaches into the living room and picks up Michelle's phone, which was left on the coffee table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration wrongly says the phone was on the coffee table even though before-facts had it in Kristin's hand.
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on a coffee table, and pocketing it was omitted.

### r2 turn 6 (1A) - facts_after_wrong, missed_change, invented_change, state_as_place [narrator initiative]
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall. The phone's screen cracks, but it still emits a faint light. Kristin approaches the wall, where the phone has landed, and picks it up.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"condition": ["cracked"], "place": "on the wall"}}
- AFTER: {"Michelle's phone": {"where": "on the wall", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration ends with Kristin picking the phone up, but after-facts put it 'on the wall,' which is also a state-like place rather than a proper location.
- CONTINUITY JUDGE: After throwing the phone, she also approaches it and picks it up unasked.

### r2 turn 7 (1A) - narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the floor. She examines the phone, which is cracked and lying on the floor near the back door. The phone's screen is cracked, but it's still on, displaying a locked screen.
- GIVEN: {"Michelle's phone": {"where": "on the wall", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"condition": ["cracked"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: After-facts match the narration, but the narration contradicts before-facts by treating the phone as on the floor even though it had been recorded on the wall.
- CONTINUITY JUDGE: The phone was last picked up, not left on the floor near the back door; the extra examination goes beyond picking it up.

### r2 turn 10 (1B) - facts_after_wrong, missed_change [narrator initiative]
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin looks around the bench, scanning the area for any signs of Michelle's presence. She notices a small piece of paper on the ground near the bench, partially hidden by the shadows. Kristin picks up the paper and examines it, finding a cryptic note with a single phrase: 'Meet me at the old warehouse at midnight.'
- GIVEN: {"Michelle's phone": {"where": "in her hand", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- REPLY: {"paper": {"condition": ["crumpled"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- ISSUES: ["item_facts name paper held for matching"]
- FACT JUDGE: Narration introduces and handles a paper, but after-facts omit the newly introduced item entirely.
- CONTINUITY JUDGE: She not only looks around but also finds and picks up a new paper unasked.

### r2 turn 12 (1B) - contradicts_stated_fact
- COMMAND: Check who has Michelle's phone now.
- NARRATION: Kristin looks down at Michelle's phone, which is still in her hand.
- GIVEN: {"Michelle's phone": {"where": "in her hand", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["cracked"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["cracked"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- FACT JUDGE: After-facts match the check narration; wording change from 'her hand' to 'Kristin's hand' is equivalent.
- CONTINUITY JUDGE: After handing the phone to the man, it cannot still be in Kristin's hand.

### r3 turn 2 (1A) - facts_after_wrong, missed_change, kept_ended_condition
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin walks over to Michelle's workstation and looks at the drawers. She finds the one with her initials, KMS, carved into it.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"condition": ["shut"], "place": "in Michelle's workstation"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- ISSUES: ["item_facts for \"Michelle's carved drawer\" refused place \"in Michelle's workstation\" because it is fixed"]
- FACT JUDGE: The command was to open the drawer, but after-facts still keep it shut.
- CONTINUITY JUDGE: She only goes to the workstation and identifies the carved drawer, which fits opening/locating it without extra action.

### r3 turn 3 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts [narrator initiative]
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATION: Kristin reaches into the room and picks up Michelle's phone, which was lying on the floor.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration wrongly says the phone was on the floor despite before-facts saying it was already in Kristin's hand, and it never shows putting it in her pocket.
- CONTINUITY JUDGE: She picks up the phone but does not put it in her pocket as commanded.

### r3 turn 5 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin walks back to her truck, the house looming behind her. She opens the truck door and reaches for her laptop. She lifts the laptop out of the truck and closes the door.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration shows Kristin takes the laptop from the truck into her hand, matching after-facts.
- CONTINUITY JUDGE: The laptop is canonically already in Kristin's truck, so she cannot carry it back out there; narration also has her go to the truck and take it out instead.

### r3 turn 6 (1A) - facts_after_wrong, missed_change, state_as_place, contradicts_stated_fact
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"condition": ["damaged"], "place": "on the kitchen wall"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen wall", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: The phone is damaged, but 'on the kitchen wall' is a state-like/invalid place rather than a proper location.
- CONTINUITY JUDGE: It says the phone comes from her pocket, but earlier narration never put it there.

### r3 turn 7 (1A) - facts_after_wrong, narration_contradicts_given_facts
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the floor.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen wall", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"condition": ["damaged"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration says she picks it up from the floor, conflicting with before-facts that had it on the kitchen wall.
- CONTINUITY JUDGE: Picking the phone up from the floor matches the command and prior turn left it against/in the kitchen area.

### r3 turn 9 (1B) - contradicts_stated_fact [narrator initiative]
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin looks down at Michelle's phone in her hand, checking that it's still there.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["damaged"], "place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- FACT JUDGE: Checking the phone only confirms it is still in hand, which matches after-facts.
- CONTINUITY JUDGE: The command was just to check possession, but narration puts the phone in her hand despite her only carrying it with her before.

### r3 turn 10 (1B) - facts_after_wrong, missed_change [narrator initiative]
- COMMAND: Look around the bench for anything Michelle left.
- NARRATION: Kristin looks around the bench, scanning the area for any signs of Michelle's presence. She notices a small piece of paper on the ground near the service path. The paper appears to be a receipt from a local coffee shop, but there's a handwritten note on the back that reads 'Meet me at the old warehouse at midnight.'
- GIVEN: {"Michelle's phone": {"where": "in her hand", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- REPLY: {"receipt": {"condition": ["near service path"], "place": "on the ground"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- ISSUES: ["item_facts name receipt held for matching"]
- FACT JUDGE: Narration introduces and places a paper, but after-facts do not record it.
- CONTINUITY JUDGE: It invents and notices a receipt with a note, which goes beyond merely looking around the bench.

### r3 turn 12 (1B) - restarts_scene
- COMMAND: Check who has Michelle's phone now.
- NARRATION: The man sitting on the bench is holding Michelle's phone.
- GIVEN: {"Michelle's phone": {"where": "in the man's hand", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- REPLY: {"Michelle's phone": {"condition": ["damaged"], "place": "in the man's hand"}}
- AFTER: {"Michelle's phone": {"where": "in the man's hand", "condition": ["damaged"]}, "Kristin's laptop": {"where": "in her hand", "condition": []}}
- FACT JUDGE: Narration only confirms the man is holding the phone, consistent with after-facts.
- CONTINUITY JUDGE: It reintroduces the man as 'sitting on the bench' as if newly situating the scene, instead of simply answering who has the phone now.

### r4 turn 3 (1A) - facts_after_wrong, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone and put it in your pocket.
- NARRATION: Kristin reaches into the living room and picks up Michelle's phone, which was lying on the coffee table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's pocket"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: After-facts match the move to her pocket, but the narration wrongly says the phone was on the coffee table.
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on the living room coffee table.

### r4 turn 6 (1A) - facts_after_wrong, missed_change, dropped_true_condition [narrator initiative]
- COMMAND: Take Michelle's phone out and throw it hard against the kitchen wall.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and throws it hard against the kitchen wall. The phone hits the wall with a loud crack, but it doesn't shatter completely. Kristin walks over to the wall and picks up the phone, examining it for any signs of damage.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen floor"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen floor", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration ends with Kristin picking the phone up and indicates damage, but after-facts leave it on the floor with no condition.
- CONTINUITY JUDGE: After throwing the phone, the narration adds that Kristin walks over, picks it up, and examines it.

### r4 turn 7 (1A) - contradicts_stated_fact
- COMMAND: Pick up Michelle's phone from the floor.
- NARRATION: Kristin bends down to pick up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen floor", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Picking up the phone is tracked correctly.
- CONTINUITY JUDGE: The prior turn established the phone was picked up from the wall area, so it is no longer on the kitchen floor.

## 40-turn (4 replicates, 159 turns)

### r1 turn 1 (1A) - facts_after_wrong, missed_change [narrator initiative]
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin picks up Michelle's phone from the kitchen floor.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen floor", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Looking did not request pickup, but narration did move the phone and after recorded it.
- CONTINUITY JUDGE: She picks up the phone instead of just looking at it.

### r1 turn 2 (1A) - facts_after_wrong, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table, checking the screen for any messages or calls.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration says the phone was picked up from the table though it was already in Kristin's hand.
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on a table.

### r1 turn 7 (1A) - kept_ended_condition [narrator initiative]
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin walks over to Michelle's workstation and opens the carved drawer.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"condition": []}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- FACT JUDGE: Opening the drawer ended shut, and after removed that condition.
- CONTINUITY JUDGE: It opens the drawer though the command assumed it was already open.

### r1 turn 11 (1A) - facts_after_wrong, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the door, pulling out her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- FACT JUDGE: Narration wrongly has the laptop back in the truck and moved to her hand, but after also records that unshown move.
- CONTINUITY JUDGE: It has the laptop still in the truck after it was brought inside and set down.

### r1 turn 12 (1A) - facts_after_wrong, missed_change, invented_change
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin takes Michelle's phone out of her jacket pocket and plugs it into her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": ["open"]}, "Michelle's phone": {"place": "in Kristin's laptop"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- FACT JUDGE: Narration moved the phone into the laptop, but after also invented laptop open and used an odd holder value.
- CONTINUITY JUDGE: Plugging the phone into the laptop matches the command.

### r1 turn 13 (1A) - facts_after_wrong, missed_change [narrator initiative]
- COMMAND: Look at the back door.
- NARRATION: Kristin recovers Michelle's memory card from under the drawer carved with her initials, KMS, and reads the files on it. The card identifies the federal emergency program as the Continuity Initiative, which was preparing to choose who remains.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- REPLY: {"back door frame": {"condition": ["damaged"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- ISSUES: ["item_facts name back door frame held for matching"]
- FACT JUDGE: Narration introduced and recovered the memory card, but after failed to add it.
- CONTINUITY JUDGE: It jumps to finding the hidden memory card and reading files instead of looking at the door.

### r1 turn 14 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplugs Michelle's phone from the wall and holds it in her hand. The phone is cold to the touch, and its screen is dark. Kristin's eyes scan the room, taking in the familiar surroundings, but her mind is focused on finding any sign of Michelle's disappearance.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- FACT JUDGE: After matches the phone being held, though narration contradicts prior facts by unplugging it from the wall.
- CONTINUITY JUDGE: The phone was plugged into the laptop, not the wall.

### r1 turn 15 (1A) - facts_after_wrong, missed_change
- COMMAND: Set Michelle's phone on the kitchen counter.
- NARRATION: Kristin carefully sets Michelle's phone on the kitchen counter.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- REPLY: {"kitchen counter": {"contents": ["Michelle's phone"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- ISSUES: ["unknown item_facts name 'kitchen counter' was dropped"]
- FACT JUDGE: Narration set the phone on the counter, but after left it in Kristin's hand.
- CONTINUITY JUDGE: Setting the phone on the counter matches the command.

### r1 turn 16 (1A) - kept_ended_condition, contradicts_stated_fact
- COMMAND: Close your laptop.
- NARRATION: Kristin closes her laptop, which is still in her hand.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- FACT JUDGE: Closing the laptop ended open and after changed the condition to closed.
- CONTINUITY JUDGE: The laptop had been set on the workstation, not still in her hand.

### r1 turn 19 (1A) - facts_after_wrong, narration_contradicts_given_facts, restarts_scene
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- FACT JUDGE: Narration says the phone is on the counter though before says Kristin already holds it.
- CONTINUITY JUDGE: It has Kristin walk into the house again and rediscover the phone.

### r1 turn 20 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- FACT JUDGE: Narration says she pulls the phone from her pocket although before had it in hand.
- CONTINUITY JUDGE: The phone was last left on the kitchen counter, not in her pocket.

### r1 turn 21 (1A) - contradicts_stated_fact
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin takes Michelle's phone from her hand and examines it. The screen is dark, but she can see that it's been recently used.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- FACT JUDGE: Examining the phone changed no tracked fact.
- CONTINUITY JUDGE: It says she takes the phone from her hand though it was established in her pocket in the prior turn.

### r1 turn 22 (1A) - facts_after_wrong, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the coffee table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": []}}
- FACT JUDGE: Narration says the phone was picked up from the coffee table though before had it in hand.
- CONTINUITY JUDGE: The phone was not on a coffee table; it had been on the counter or in her possession.

### r1 turn 28 (1A) - facts_after_wrong, missed_change, invented_change, dropped_true_condition
- COMMAND: Close the drawer.
- NARRATION: Kristin walks over to Michelle's workstation and looks at the carved drawer.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- REPLY: {"Michelle's carved drawer": {"condition": ["shut"], "place": "in Michelle's workstation"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- ISSUES: ["item_facts for \"Michelle's carved drawer\" refused place \"in Michelle's workstation\" because it is fixed"]
- FACT JUDGE: Narration only looked at the drawer, but after invented shut and dropped open without shown closing.
- CONTINUITY JUDGE: She looks at the drawer rather than closing it, but adds no extra action.

### r1 turn 31 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the door, revealing her laptop on the passenger seat.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "on the passenger seat of her truck"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration contradicts before by putting the laptop back in the truck, and after invents that move.
- CONTINUITY JUDGE: It places the laptop back in the truck after it had just been brought inside and set down.

### r1 turn 32 (1A) - facts_after_wrong, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully opens the passenger door of her truck and retrieves her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration only retrieves the laptop though the command was to plug in the phone, and after leaves facts unchanged.
- CONTINUITY JUDGE: Instead of plugging in the phone, she just goes to the truck and retrieves the laptop again.

### r1 turn 33 (1A) - restarts_scene [narrator initiative]
- COMMAND: Look at the back door.
- NARRATION: Kristin approaches the back door, noticing the recent damage to the frame. She examines the door and finds that it's slightly ajar. Kristin pushes the door open and steps inside, calling out Michelle's name.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"back door": {"condition": ["damaged", "ajar"]}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- ISSUES: ["item_facts name back door held for matching"]
- FACT JUDGE: Back door action did not affect any tracked item.
- CONTINUITY JUDGE: She enters through the back door and calls out as though newly arriving, beyond merely looking at it.

### r1 turn 34 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplugs Michelle's phone from the wall and holds it in her hand. The phone is still in Michelle's jacket pocket, but now it's free. Kristin looks at the phone, trying to find any clues about Michelle's disappearance.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: After matches holding the phone, though narration contradicts itself about it being in Michelle's jacket pocket while in hand.
- CONTINUITY JUDGE: It says the phone is in Michelle's jacket pocket, conflicting with Kristin having pocketed it.

### r1 turn 35 (1A) - contradicts_stated_fact
- COMMAND: Set Michelle's phone on the kitchen counter.
- NARRATION: Kristin carefully sets Michelle's phone on the kitchen counter. The phone's screen is dark, and there are no signs of recent use. Kristin looks at the phone, wondering if Michelle might have left a message or a clue.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Phone was set on the kitchen counter and after records that.
- CONTINUITY JUDGE: It says there are no signs of recent use, contradicting the earlier statement that it had been recently used.

### r1 turn 36 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Close your laptop.
- NARRATION: Kristin gets out of her truck and walks towards the passenger side.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "on the passenger seat of her truck"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Laptop was already closed on the truck seat and narration changed nothing tracked.
- CONTINUITY JUDGE: The laptop was not in the truck seat after being brought inside; she also does not close it.

### r1 turn 37 (1A) - facts_after_wrong, invented_change, contradicts_stated_fact [narrator initiative]
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin walks back to her truck, her eyes scanning the quiet neighborhood. She opens the passenger door and reaches for her laptop, carefully lifting it out of the seat. She closes the laptop and holds it in her hand, considering what to do next.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration lifted the laptop out of the seat, but command was to carry it back out to the truck and after records the opposite move.
- CONTINUITY JUDGE: It retrieves the laptop from the truck though it was not established there, and adds closing it.

### r1 turn 39 (1A) - facts_after_wrong, narration_contradicts_given_facts, restarts_scene
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration notices the phone on the counter although before says Kristin already holds it.
- CONTINUITY JUDGE: It has Kristin walk into the house and notice the phone again as if newly arriving.

### r1 turn 40 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration says she pulls the phone from her pocket though before had it in hand.
- CONTINUITY JUDGE: The prior turn did not pick up the phone, so it should not now be in her pocket.

### r2 turn 2 (1A) - facts_after_wrong, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table, checking the screen for any messages or calls.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration says the phone is picked up from a table, conflicting with it already being in Kristin's hand.
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on a table, and checking it goes beyond picking it up.

### r2 turn 7 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin walks over to Michelle's workstation and opens the carved drawer.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"condition": ["open"]}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- FACT JUDGE: Narration opens the drawer, and after-facts change shut to open.
- CONTINUITY JUDGE: It calls the drawer open even though it was never opened and opening it is beyond merely looking inside an open drawer.

### r2 turn 8 (1A) - facts_after_wrong, invented_change, dropped_true_condition, contradicts_stated_fact [narrator initiative]
- COMMAND: Close the drawer.
- NARRATION: Kristin walks over to Michelle's workstation and looks at the carved drawer.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- REPLY: {"Michelle's carved drawer": {"condition": ["closed"], "place": "in Michelle's workstation"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- ISSUES: ["item_facts for \"Michelle's carved drawer\" refused place \"in Michelle's workstation\" because it is fixed"]
- FACT JUDGE: Narration only looks at the drawer, but after-facts change it from open to shut.
- CONTINUITY JUDGE: It does not close the already-open drawer and instead treats it as just being looked at.

### r2 turn 11 (1A) - facts_after_wrong, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the driver's side door, pulling out her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration wrongly has the laptop back in the truck and moving to her hand; after-facts record that invented move and miss the commanded opening.
- CONTINUITY JUDGE: The laptop was already brought inside and placed on the workstation, but narration sends her to the truck and has her pull it out.

### r2 turn 12 (1A) - facts_after_wrong, missed_change, invented_change, contradicts_stated_fact
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully takes Michelle's phone out of her jacket pocket and plugs it into her laptop, which is still in her hand.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"condition": ["open"]}, "Michelle's phone": {"place": "in Kristin's laptop"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration shows the phone plugged into the laptop and the laptop in hand, but after-facts use an odd container place 'in Kristin's laptop' and fail to note charging.
- CONTINUITY JUDGE: The laptop was just set on the workstation, so it should not still be in her hand.

### r2 turn 13 (1A) - facts_after_wrong, missed_change, kept_ended_condition [narrator initiative]
- COMMAND: Look at the back door.
- NARRATION: Kristin recovers Michelle's memory card from under the drawer carved with her initials, KMS, and reads the files on it. The card identifies the federal emergency program as the Continuity Initiative, which was preparing to choose who remains.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"back door frame": {"condition": ["damaged"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- ISSUES: ["item_facts name back door frame held for matching"]
- FACT JUDGE: Narration introduces and recovers a memory card, but after-facts omit it entirely.
- CONTINUITY JUDGE: Looking at the back door does not ask her to find the memory card and read files.

### r2 turn 14 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the wall and holds it in her hand. The phone is now dead, but Kristin can see that it was recently used. She looks at the phone's screen, but it's dark.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"condition": ["dead"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dead"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration says unplugged from the wall, conflicting with before-facts, and after-facts add dead though prior charging setup was inconsistent.
- CONTINUITY JUDGE: The phone was plugged into the laptop, not the wall, and extra inspection is beyond unplugging and holding it.

### r2 turn 15 (1A) - facts_after_wrong, dropped_true_condition, contradicts_stated_fact
- COMMAND: Set Michelle's phone on the kitchen counter.
- NARRATION: Kristin carefully sets Michelle's phone on the kitchen counter.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dead"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"condition": [], "place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: The move is tracked, but the existing dead condition is dropped without narration ending it.
- CONTINUITY JUDGE: The phone had previously been on the kitchen floor, not established on the counter before this.

### r2 turn 16 (1A) - contradicts_stated_fact
- COMMAND: Close your laptop.
- NARRATION: Kristin closes her laptop, which is still in her hand.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"]}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration closes the laptop, and after-facts reflect closed.
- CONTINUITY JUDGE: It says the laptop is still in her hand despite earlier placing it on the workstation.

### r2 turn 18 (1A) - restarts_scene
- COMMAND: Look around the kitchen for anything you missed.
- NARRATION: Kristin enters the kitchen, her eyes scanning the room for any signs of Michelle or what might have happened to her. She notices Michelle's phone on the kitchen counter, its screen dark. Kristin's gaze falls on the back door, which shows signs of recent damage.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Looking around the kitchen adds no tracked changes.
- CONTINUITY JUDGE: It narrates entering the kitchen as though arriving there anew.

### r2 turn 19 (1A) - restarts_scene [narrator initiative]
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration only notices the phone on the counter and does not pick it up.
- CONTINUITY JUDGE: Instead of picking up the phone, it restarts with her walking into the house and just noticing it.

### r2 turn 20 (1A) - contradicts_stated_fact, restarts_scene [narrator initiative]
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the living room and kitchen, but there's no sign of Michelle. She heads to the kitchen counter, where she sees Michelle's phone.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: She sees the phone on the counter; no tracked state changes.
- CONTINUITY JUDGE: She is said to see the phone on the counter rather than check possession, and the house-entry framing restarts the scene.

### r2 turn 21 (1A) - facts_after_wrong, missed_change, narration_contradicts_given_facts, contradicts_stated_fact, restarts_scene [narrator initiative]
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin walks into the house, her eyes scanning the kitchen counter where Michelle's phone lies. It's still plugged into the charger, but the screen is dark.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration says the phone is still plugged into a charger despite before-facts only placing it on the counter, and that charging state is unrecorded.
- CONTINUITY JUDGE: It says the phone is on the counter and plugged into a charger, conflicting with prior states, and reintroduces the room.

### r2 turn 22 (1A) - restarts_scene [narrator initiative]
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "on the kitchen counter"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration only notices the phone on the counter, so after-facts staying the same is correct.
- CONTINUITY JUDGE: It restarts with her walking into the house and does not actually pick the phone up.

### r2 turn 25 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Put Michelle's phone in your jacket pocket.
- NARRATION: Kristin reaches into her jacket pocket and pulls out Michelle's phone.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in her jacket pocket"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: After-facts match the phone being put into her jacket pocket.
- CONTINUITY JUDGE: Putting it in her pocket is narrated as pulling it out of her pocket, the opposite action.

### r2 turn 26 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Open the drawer with your initials carved into it.
- NARRATION: Kristin walks over to Michelle's workstation and looks at the carved drawer.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: She only looks at the drawer; nothing tracked changes.
- CONTINUITY JUDGE: The drawer had been opened earlier, but this treats it as merely being looked at instead of opened.

### r2 turn 28 (1A) - facts_after_wrong, invented_change, dropped_true_condition, contradicts_stated_fact [narrator initiative]
- COMMAND: Close the drawer.
- NARRATION: Kristin walks over to Michelle's workstation and looks at the carved drawer.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- REPLY: {"Michelle's carved drawer": {"condition": ["shut"], "place": "in Michelle's workstation"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- ISSUES: ["item_facts for \"Michelle's carved drawer\" refused place \"in Michelle's workstation\" because it is fixed"]
- FACT JUDGE: Narration does not close the drawer, but after-facts change open back to shut.
- CONTINUITY JUDGE: It fails to close the open drawer and instead only looks at it.

### r2 turn 31 (1A) - facts_after_wrong, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the door, revealing her laptop on the passenger seat.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "on the passenger seat of her truck"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration incorrectly places the laptop back in the truck, and after-facts invent that move instead of recording the commanded opening.
- CONTINUITY JUDGE: The laptop had just been brought inside and set on the workstation, but narration places it back in the truck.

### r2 turn 32 (1A) - facts_after_wrong, missed_change, invented_change, contradicts_stated_fact [narrator initiative]
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully opens the passenger door of her truck and retrieves her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration only retrieves the laptop, but after-facts also move the phone to her hand with no shown plugging or charging.
- CONTINUITY JUDGE: Instead of plugging in the phone, it only retrieves the laptop from the truck, contradicting its prior location.

### r2 turn 34 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the wall charger. She picks up the phone, feeling a mix of concern and determination. The phone is now in her hand.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "on the passenger seat of her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration says unplugged from a wall charger, conflicting with before-facts where the phone was already in Kristin's hand.
- CONTINUITY JUDGE: The phone was not established as plugged into a wall charger.

### r2 turn 38 (1A) - restarts_scene [narrator initiative]
- COMMAND: Look around the kitchen for anything you missed.
- NARRATION: Kristin walks into the kitchen, her eyes scanning the room for any signs of Michelle or what might have happened to her. She notices Michelle's phone on the kitchen counter, its screen dark. Kristin picks up the phone and examines it, but there are no new messages or calls.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration picks up the phone during the kitchen search, and after-facts record that move.
- CONTINUITY JUDGE: It restarts with her walking into the kitchen and has her pick up the phone though she only meant to look around.

### r2 turn 39 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, restarts_scene
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter. She picks up Michelle's phone, feeling a sense of unease as she realizes it's been left behind. The phone is still in Kristin's hand, but it's dark and silent.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"condition": ["dark", "silent"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dark", "silent"]}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration says she picks up the phone from the counter though before-facts already had it in her hand, and after-facts invent dark and silent conditions.
- CONTINUITY JUDGE: It fulfills the pickup but restarts by having her walk into the house and rediscover the phone.

### r2 turn 40 (1A) - facts_after_wrong, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dark", "silent"]}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"condition": ["dark", "silent"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["dark", "silent"]}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration says she pulls the phone from her pocket, conflicting with before-facts that it was already in her hand.
- CONTINUITY JUDGE: It says the phone comes from her pocket even though the prior turn left it in her hand.

### r3 turn 2 (1A) - contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table, checking the screen for any messages or notifications.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: (no fact-tracking verdict)
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on a table.

### r3 turn 14 (1A) - contradicts_stated_fact
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplugs Michelle's phone from the wall and holds it in her hand.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: (no fact-tracking verdict)
- CONTINUITY JUDGE: The phone was plugged into the laptop, not the wall.

### r3 turn 19 (1A) - restarts_scene [narrator initiative]
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: (no fact-tracking verdict)
- CONTINUITY JUDGE: It restages Kristin walking into the house and does not complete picking up the phone.

### r3 turn 20 (1A) - contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: (no fact-tracking verdict)
- CONTINUITY JUDGE: The phone had been left on the kitchen counter, not in her pocket.

### r3 turn 21 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin takes Michelle's phone from the table and examines it. The phone's screen is dark, but Kristin can see that it's been recently used. She tries to turn it on, but it requires a password.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: (no fact-tracking verdict)
- CONTINUITY JUDGE: The phone was on the counter, not a table, and she also tries turning it on unasked.

### r3 turn 22 (1A) - contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the coffee table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: (no fact-tracking verdict)
- CONTINUITY JUDGE: The phone was last on the kitchen counter, not the coffee table.

### r3 turn 25 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Put Michelle's phone in your jacket pocket.
- NARRATION: Kristin reaches into her jacket pocket and pulls out Michelle's phone.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in her jacket pocket"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: (no fact-tracking verdict)
- CONTINUITY JUDGE: The command was to put the phone into her pocket, but narration has her pull it out.

### r3 turn 31 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the door, revealing her laptop on the passenger seat.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her truck"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: (no fact-tracking verdict)
- CONTINUITY JUDGE: The laptop was on the workstation, but narration relocates it to the truck and does not open it.

### r3 turn 32 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin opens the truck door and retrieves her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: (no fact-tracking verdict)
- CONTINUITY JUDGE: The command was to plug in the phone, but narration only retrieves the laptop from the truck.

### r3 turn 34 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the wall outlet and picks it up, feeling a mix of concern and determination. She examines the phone, but it's dark and silent, offering no immediate clues about Michelle's disappearance. Kristin's eyes scan the room, taking in the familiar surroundings, but her focus remains on the phone and the task at hand.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her hand", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: (no fact-tracking verdict)
- CONTINUITY JUDGE: Nothing established the phone was plugged into a wall outlet, and the added examination exceeds the command.

### r3 turn 36 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Close your laptop.
- NARRATION: Kristin gets into her truck and closes the laptop, which was still open from her previous shift.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"]}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: (no fact-tracking verdict)
- CONTINUITY JUDGE: The laptop had been on the workstation, not open in the truck from a previous shift.

### r3 turn 37 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin walks back to her truck, the sound of her boots echoing on the pavement. She opens the truck door and reaches for her laptop, which is still in the passenger seat. She carefully lifts the laptop out of the truck and closes the door behind her.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: (no fact-tracking verdict)
- CONTINUITY JUDGE: It says the laptop is still in the truck even though it was set on the workstation earlier, and she carries it the wrong way.

### r3 turn 39 (1A) - restarts_scene [narrator initiative]
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She looks around the kitchen, noticing Michelle's phone on the counter.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: (no fact-tracking verdict)
- CONTINUITY JUDGE: It restarts with Kristin walking into the house and still does not pick up the phone.

### r3 turn 40 (1A) - contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: (no fact-tracking verdict)
- CONTINUITY JUDGE: The phone was on the kitchen counter, not in her pocket.

### r4 turn 2 (1A) - facts_after_wrong, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the table, checking the screen for any messages or calls.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in Kristin's truck outside the house", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration says the phone was on a table though it was already in her hand.
- CONTINUITY JUDGE: The phone was established on the kitchen floor, not on a table.

### r4 turn 11 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Open your laptop.
- NARRATION: Kristin walks to her truck and opens the door, revealing her laptop on the passenger seat.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "on Michelle's workstation", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her truck"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration wrongly places the laptop back in the truck, and after changes it to in her truck without showing that move.
- CONTINUITY JUDGE: The laptop had just been brought inside, but the narration puts it back in the truck and does not open it.

### r4 turn 12 (1A) - facts_after_wrong, missed_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin opens the truck door and retrieves her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration shows her retrieving the laptop, but after leaves it in the truck.
- CONTINUITY JUDGE: Instead of charging the phone, the narration only retrieves the laptop, and it again places the laptop in the truck.

### r4 turn 13 (1A) - facts_after_wrong, missed_change [narrator initiative]
- COMMAND: Look at the back door.
- NARRATION: Kristin recovers Michelle's memory card from under the drawer carved with her initials, KMS, and reads the files on it. The card identifies the federal emergency program as the Continuity Initiative, which was preparing to choose who remains.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration introduces and recovers the memory card, but after omits it.
- CONTINUITY JUDGE: Looking at the back door became finding the hidden memory card and reading files.

### r4 turn 14 (1A) - facts_after_wrong, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the wall outlet and picks it up.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration says the phone was unplugged from a wall outlet, conflicting with it being in her pocket.
- CONTINUITY JUDGE: No outlet charging had been established, and the narration adds trying passwords beyond simply unplugging and holding it.

### r4 turn 16 (1A) - facts_after_wrong, invented_change, contradicts_stated_fact [narrator initiative]
- COMMAND: Close your laptop.
- NARRATION: Kristin gets into her truck and closes the laptop, which was still open from her previous shift.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": []}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"]}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration only says the laptop was closed; after invents a closed condition without prior open state shown.
- CONTINUITY JUDGE: The laptop was last placed on the workstation, but the narration says Kristin gets into the truck to close it and invents it being open from a shift.

### r4 turn 17 (1A) - facts_after_wrong, narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Carry your laptop back out to the truck.
- NARRATION: Kristin walks back to her truck, the sound of her boots echoing on the pavement. She opens the truck door and reaches for her laptop, which is still in the passenger seat. She carefully lifts the laptop out of the truck and closes the door behind her.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration says the laptop was still in the truck, matching before, but this conflicts with earlier established placement.
- CONTINUITY JUDGE: It says the laptop is still in the passenger seat, conflicting with it being on the workstation.

### r4 turn 19 (1A) - narration_contradicts_given_facts, restarts_scene [narrator initiative]
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She heads to the kitchen, where she sees Michelle's phone on the counter.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration says she sees the phone on the counter though before had it in hand.
- CONTINUITY JUDGE: It restarts with Kristin walking into the house and does not actually pick up the phone.

### r4 turn 20 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks the screen.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration says she pulls it from her pocket though before already had it in hand.
- CONTINUITY JUDGE: The phone was last set on the counter, not established as being in her pocket.

### r4 turn 21 (1A) - narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Look carefully at Michelle's phone.
- NARRATION: Kristin takes Michelle's phone from her hand and examines it.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration says she takes the phone from her hand, but before already has it there.
- CONTINUITY JUDGE: She takes the phone from her hand even though it was last in her pocket or on the counter, and the command only asked to look carefully.

### r4 turn 22 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Pick up Michelle's phone.
- NARRATION: Kristin carefully picks up Michelle's phone from the coffee table.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: Narration wrongly says the phone was on a coffee table instead of already in hand.
- CONTINUITY JUDGE: The phone is described on the coffee table, conflicting with prior placement on the kitchen counter.

### r4 turn 23 (1A) - facts_after_wrong, invented_change
- COMMAND: Wipe the dust off the screen of Michelle's phone.
- NARRATION: Kristin carefully wipes the dust off the screen of Michelle's phone.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": []}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"condition": ["clean"]}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["clean"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: After adds a clean condition the narration did not clearly establish as tracked state.
- CONTINUITY JUDGE: Wiping the phone matches the command.

### r4 turn 24 (1A) - facts_after_wrong, invented_change, dropped_true_condition
- COMMAND: Press the power button on Michelle's phone.
- NARRATION: Kristin presses the power button on Michelle's phone.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["clean"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's phone": {"condition": ["powered on"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["powered on"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- FACT JUDGE: After invents powered on and drops clean, neither shown by narration as tracked changes.
- CONTINUITY JUDGE: Pressing the power button matches the command.

### r4 turn 27 (1A) - contradicts_stated_fact [narrator initiative]
- COMMAND: Look inside the open drawer.
- NARRATION: Kristin opens the drawer, revealing a neatly organized space with various tools and equipment.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": ["powered on"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["shut"]}}
- REPLY: {"Michelle's carved drawer": {"condition": ["open"]}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": ["powered on"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- FACT JUDGE: Narration explicitly opens the drawer.
- CONTINUITY JUDGE: The drawer had previously been closed, and the narration invents ordinary contents instead of the hidden-card setup.

### r4 turn 28 (1A) - facts_after_wrong, missed_change, contradicts_stated_fact [narrator initiative]
- COMMAND: Close the drawer.
- NARRATION: Kristin walks over to Michelle's workstation and approaches the carved drawer.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": ["powered on"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- REPLY: null
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": ["powered on"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- ISSUES: ["item_facts must be an object mapping thing names to fact objects"]
- FACT JUDGE: Narration does not show the drawer closing, but the command and attempted close indicate the change should have been tracked only if shown; after keeps it open despite the close action being the intended outcome? Actually narration only approaches, so no shown change.
- CONTINUITY JUDGE: It only approaches the drawer rather than closing it, and the previous turn had already opened it.

### r4 turn 29 (1A) - narration_contradicts_given_facts
- COMMAND: Go out to your truck and bring your laptop inside.
- NARRATION: Kristin walks out to her truck, unlocks the door, and retrieves her laptop.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": ["powered on"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- REPLY: {"Kristin's laptop": {"place": "in her hand"}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": ["powered on"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- FACT JUDGE: Narration says she retrieves the laptop from the truck though before already had it in hand.
- CONTINUITY JUDGE: Retrieving the laptop from the truck matches the command.

### r4 turn 30 (1A) - facts_after_wrong, missed_change, contradicts_stated_fact
- COMMAND: Set your laptop on Michelle's workstation.
- NARRATION: Kristin carefully sets her laptop on Michelle's workstation, next to the open carved drawer.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": ["powered on"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- REPLY: {"Michelle's workstation": {"contents": ["Kristin's laptop", "Michelle's carved drawer"]}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": ["powered on"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- ISSUES: ["unknown item_facts name \"Michelle's workstation\" was dropped"]
- FACT JUDGE: Narration shows the laptop set on the workstation, but after leaves it in her hand.
- CONTINUITY JUDGE: It says the carved drawer is open, but the last drawer narration did not close it consistently and earlier state was muddled; this conflicts with the prior close attempt/state.

### r4 turn 31 (1A) - dropped_true_condition [narrator initiative]
- COMMAND: Open your laptop.
- NARRATION: Kristin opens her laptop, which is still in her hand, and the screen flickers to life. She begins to type, her fingers moving quickly over the keyboard as she tries to access the Continuity Initiative files. The laptop's screen displays a login page, and Kristin's eyes narrow as she tries to remember the password.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": ["powered on"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- REPLY: {"Kristin's laptop": {"condition": ["open"]}}
- AFTER: {"Michelle's phone": {"where": "in her jacket pocket", "condition": ["powered on"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- FACT JUDGE: Opening is tracked, but after drops the prior closed condition rather than replacing it cleanly.
- CONTINUITY JUDGE: Opening the laptop was requested, but typing and accessing Continuity Initiative files goes beyond that.

### r4 turn 32 (1A) - facts_after_wrong, missed_change, invented_change, narration_contradicts_given_facts, contradicts_stated_fact [narrator initiative]
- COMMAND: Plug Michelle's phone into your laptop to charge it.
- NARRATION: Kristin carefully plugs Michelle's phone into her laptop, which is still open on the passenger seat of her truck. She gets out of the truck and walks back to the house, her eyes scanning the area for any signs of disturbance. As she approaches the house, she notices that the back door frame still shows recent damage.
- GIVEN: {"Michelle's phone": {"where": "in her jacket pocket", "condition": ["powered on"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- REPLY: {"Michelle's phone": {"place": "in Kristin's laptop"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": ["powered on"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- FACT JUDGE: Narration puts the laptop on a truck seat conflicting with before, and after uses phone where as in Kristin's laptop without charging condition.
- CONTINUITY JUDGE: The laptop was just opened on the workstation, but the narration moves it to the truck and adds extra travel and observation.

### r4 turn 34 (1A) - facts_after_wrong, invented_change, contradicts_stated_fact [narrator initiative]
- COMMAND: Unplug Michelle's phone and hold it.
- NARRATION: Kristin carefully unplug Michelle's phone from the charger and holds it in her hand. The phone is still powered on, and Kristin can see that Michelle's phone is locked with a password. Kristin tries to guess the password, but it doesn't work.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's laptop", "condition": ["powered on"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- REPLY: {"Michelle's phone": {"condition": ["powered on", "locked"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["powered on", "locked"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- FACT JUDGE: After invents a locked condition not stated as an existing change from before beyond observation.
- CONTINUITY JUDGE: Trying to guess the password goes beyond unplugging and holding, and prior charging setup was inconsistent.

### r4 turn 36 (1A) - facts_after_wrong, invented_change, narration_contradicts_given_facts
- COMMAND: Close your laptop.
- NARRATION: Kristin closes her laptop, which is now in the truck.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": ["powered on", "locked"]}, "Kristin's laptop": {"where": "in her hand", "condition": ["open"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- REPLY: {"Kristin's laptop": {"condition": ["closed"], "place": "in the truck"}}
- AFTER: {"Michelle's phone": {"where": "on the kitchen counter", "condition": ["powered on", "locked"]}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- FACT JUDGE: Narration contradicts before by saying the laptop is in the truck, and after also invents that move.
- CONTINUITY JUDGE: Closing the laptop in the truck follows the immediately prior established state.

### r4 turn 39 (1A) - restarts_scene [narrator initiative]
- COMMAND: Pick up Michelle's phone from the kitchen counter.
- NARRATION: Kristin walks into the house, calling out Michelle's name. She heads to the kitchen, where she sees Michelle's phone on the counter. She picks up the phone, examining it for any signs of disturbance. The phone is powered on, but locked with a passcode.
- GIVEN: {"Michelle's phone": {"where": "on the kitchen counter", "condition": ["powered on", "locked"]}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- REPLY: {"Michelle's phone": {"condition": ["powered on", "locked"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["powered on", "locked"]}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- FACT JUDGE: Narration shows her picking up the phone from the counter.
- CONTINUITY JUDGE: It restarts with Kristin walking into the house again and adds calling out Michelle's name.

### r4 turn 40 (1A) - narration_contradicts_given_facts, contradicts_stated_fact
- COMMAND: Check that you still have Michelle's phone.
- NARRATION: Kristin pulls out Michelle's phone from her pocket and checks that it's still there.
- GIVEN: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["powered on", "locked"]}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- REPLY: {"Michelle's phone": {"condition": ["powered on", "locked"], "place": "in Kristin's hand"}}
- AFTER: {"Michelle's phone": {"where": "in Kristin's hand", "condition": ["powered on", "locked"]}, "Kristin's laptop": {"where": "in the truck", "condition": ["closed"]}, "Michelle's carved drawer": {"where": "in Michelle's workstation", "condition": ["open"]}}
- FACT JUDGE: Narration says she pulls it from her pocket though before had it in hand.
- CONTINUITY JUDGE: The prior turn had her pick up the phone from the counter, so checking it in her pocket conflicts with the latest state.

