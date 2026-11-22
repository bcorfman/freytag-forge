**Reasoning**
- Delight can't mean "more stuff". Without limits, the judge will reward embellishment and invented facts. The check therefore allows only material that is already in the scene context.
- The check asks the judge to name the specific detail that earns a yes. That makes yes/no answers consistent and lets the owner audit them.
- The four allowed jobs (plant a clue, pay off a plant, reveal a character, sharpen the stakes) all fit within 20 to 600 characters, so the bar can be cleared.
- A matcher phrase adds no visible text, so asking it to "be more fun than a plain fix" would be impossible. For that case, delight means the player's own natural words now reach the intended moment. The phrase must not be so broad that it lets players skip a puzzle or reward, because that kills fun quietly.
- So one key covers both cases, but the question has two clauses: one for visible text and one for no visible text.
- The advice field gives the lever to use (which existing detail, which job), not finished wording. The planner stays the author, and the reviewer can't write fixes that slip past the lint.
- The planner's "smallest change" rule is the part that pushes toward "not broken", so it gets replaced. Smallest now only breaks ties between equally fun fixes.
- On a block, the planner gets the failed check names, the reasons and the advice. It doesn't get the reviewer's brief, so it can't write to the test.
- Each fun round costs one Opus call, so cap it at two. After that, the owner's taste decides.

**FINAL**

**(a) New check key and bullet line** (insert after the `continuity_between_scenes` bullet; change "seven" to "eight" in "Answer these seven yes/no questions:")

Key: delights_the_player

- delights_the_player: would a player enjoy this moment, using only the facts, people, places and objects already in the scene context shown? If the fix adds or changes player-visible text, answer yes only if you can name one specific detail in it that plants a clue, pays off an earlier detail, reveals a character, or sharpens the stakes. Generic mood words, extra props, and invented facts never count. If the fix adds no player-visible text, answer yes when the added words are a natural way a player would try the action. They must let the player reach the scene's intended moment without skipping a puzzle, a clue or a reward.

**(b) Updated JSON reply template lines** (replace the reply template and the two lines after it)

Reply with ONE JSON object and nothing else:
{"verdict": "pass" or "block", "checks": {"fits_scene": true, "gives_a_reason_to_act": true, "keeps_pace": true, "fits_freytag_phase": true, "characters_in_character": true, "continuity_within_scene": true, "continuity_between_scenes": true, "delights_the_player": true}, "reasons": "one to three plain sentences", "fun_advice": "empty on pass; one or two plain sentences on block"}
In reasons, when delights_the_player is true, name the detail that earns it.
In fun_advice, on a block, say how a fix could be more fun and still free the stuck turns.
Name the existing detail to use and the job it should do: plant, payoff, character, or stakes.
Do not write the finished wording.
Use only facts in the scene context shown, and keep to the three fix kinds.
Keep fun_advice to 300 characters or fewer.
Block when any answer is no or missing. A fix that only moves words around without a reason is a block.

**(c) Planner sentences**

Replace "Prefer the smallest change that would have let the failing turns succeed." with:

Among the fixes that would have let the failing turns succeed, choose the one the player would enjoy most.
Fun means Freytag pacing, quality characters, and continuity in and between scenes.
A fix is more fun when it uses a detail already in the scene to plant a clue, pay off an earlier detail, show a character, or sharpen the stakes.
Never invent a new fact, object, person, or place to make a fix more fun.
Choose the smaller fix only when two fixes would be equally fun.
For edit_claim_evidence, the fun is letting the player's own words reach the intended moment.
Never choose a phrase so broad that it lets a player skip a puzzle, a clue, or a reward.

Replace "Keep reason at 400 characters or fewer." with:

After the cause, name in a few words the detail that makes the fix fun.
Keep reason at 400 characters or fewer.

Add these after "When check output is shown, the plan was applied and the check failed, so reply with a revised plan that fixes the reason shown.":

When a story editor's block is shown, treat its fun_advice as the owner's taste and follow it.
The advice never overrides the evidence, the precedents, or the lint.
Never resubmit the blocked fix with only its words moved around.

**(d) Other changes**
- **What the planner gets back on a block:** its own blocked plan, the check keys that were false, the reasons, and the fun_advice. It doesn't get the reviewer's brief or the check questions.
- **Re-checking revisions:** every revised plan goes through the lint and the probe (station 12) again before the fun review. A more fun rewrite can break the stuck-turn fix again.
- **Round limit:** cap fun-review blocks at two rounds per ticket. This counts separately from the probe's three rounds. After the second block, don't merge. Send the ticket to the owner with both plans, both reasons, and the last fun_advice.
- **Reviewer packet:** the review packet must include the failing turns' typed commands and the claim's existing action_evidence phrases. Without them, the no-visible-text clause can't be answered.
- **Precedents:** when a fix passes after a fun block, record the advice and the passing fix as a proven fun technique. Record the blocked fix as lost.
- **Owner spot-checks:** log the reasons for every pass so the owner can spot-check what the judge called delightful and correct it.

Commit ac400ee8 already uses the key delights_the_player, so check this text against what that commit built before pasting.
