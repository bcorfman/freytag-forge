Widen the action words of four Scene 3C reveals in the Continuity Initiative
package (`data/stories/continuity-initiative/`). Read first: `AGENTS.md`
("Writing Player Input", "Fixing a Scene"), `storygame/runtime/candidate_matcher.py`
(the exact matcher, including `_SYNONYM_CLASSES`, the negation words and the
one-match rule), and `knowledge.yaml` (`k_sl_3c_*`; read the CURRENT
`action_evidence` groups of all ten 3C reveals) and `handoffs.yaml` (the seven
3C cues). Do not edit files; return text to paste.

## What happened

After PR 565 (seven cues for 3C, steps C and D split into two parts each) we ran
the blind-player test on staging (three runs, all nine scenes). The cues work:
each appeared the turn after its step and two players followed them at once.
But some players typed natural commands that fired nothing, and the 14-turn
timer printed the rest of the chain. These are the exact commands (player
voice), what the cue had just shown, and what should have happened:

| Run | Turn | Command typed | After this cue | Fired | Should fire |
|---|---|---|---|---|---|
| r1 | 3, 4, 5, 9, 10, 11 | Follow Rebecca. / Follow Rebecca with Michelle. | cue_b: "Rebecca is leaving the executive office with the Portable data case in her hands." | nothing | b_r1 (stop her) |
| r1 | 12 | Follow Rebecca's escape route. | same | nothing | b_r1 |
| r1 | 13 | Take Rebecca's escape route. | same | b_r1 (worked) | b_r1 |
| r2 | 5 | Extend the emergency gate authorization. | cue_c_gates: "The surface gates are shut above the waiting captives. The gate authorization is close to expiry." | nothing | c_r2 |
| r2 | 6 | Guide the captives through the emergency gate. | same | nothing | c_r2 |
| r2 | 7, 8 | Lead the captives to safety. / Lead the captives to the safe surface. | same | nothing | nothing is fine (no gate named) |
| r2 | 10 | Open the surface exit. | same | c_r2 (worked) | c_r2 |
| r2 | 14 | Broadcast updates to the families. | cue_d_families: "Families of the missing ask the broadcast chamber for word." | nothing | d_r2 |
| r3 | 7 | Broadcast the reports from other detention sites. | cue_d_reports: "Reports from other detention sites reach the broadcast chamber." (and then cue_d_families) | nothing | d_r1 |
| r3 | 8 | Answer the families with the broadcast's truth. | cue_d_families | nothing | d_r2 |

Why they missed (check this against the matcher, do not trust it): `b_r1` has no
"follow" and its object group needs a thing like "Rebecca's escape"; `c_r2` has
no "extend", "guide" or "lead"; `d_r1` and `d_r2` have no "broadcast"; `d_r2` has
no "answer".

## The task

Add words to the action (first) groups, and to the object (second) groups only
where an object is the gap, of `b_r1`, `c_r2`, `d_r1` and `d_r2` so the commands
above fire the right reveal. Do not remove any existing word. Do not change a
statement, a `delivery_text` or a cue unless a cue needs one word to make the
move findable; if so, give the new cue text and say why a verb change is not
enough.

## Rules to keep

- ONE reveal may match a command. Where a new word makes a command match two
  reveals, the matcher returns none, so the command breaks. Known neighbours to
  check by running the matcher, not by reading:
  - `a_r1` shares "broadcast", "show", "display", "run", "send" with others and its
    object group has "detention site list", "detention site map", "detention
    locations", "evidence package", "independent networks". `d_r1` has the object
    "detention site", which sits inside "detention site list" and "detention site
    map". Adding "broadcast" to `d_r1` may make "Broadcast the detention site
    list." match both. Say what you found and give the least risky choice.
  - `a_r2` has "answer", "respond", "broadcast", "tell", "call". `d_r2` has "call",
    "tell". Check "Answer Charles's terrorist claim.", "Call the families of the
    missing.", "Tell the missing families." keep their single match.
  - `c_r1` has "lead", "guide", "keep", "hold" with objects such as "maintenance
    routes" and "watertight barrier". Check "Lead Michelle through the maintenance
    routes." stays `c_r1` only, and "Lead the captives through the emergency
    gate." fires `c_r2` only.
  - `b_r1` and `b_r2` share verbs ("ask", "talk to", "confront"). Check "Follow
    Rebecca." choices below.
- "Follow Rebecca." has no object phrase. Giving `b_r1` the bare object "Rebecca"
  would also make "Ask Rebecca about Charles." and "Talk to Rebecca." fire B.
  Decide with the matcher: (a) add "follow" and the object "Rebecca's escape
  route" only, so "Follow Rebecca's escape route." fires and bare "Follow
  Rebecca." does not; (b) add "Rebecca" as an object; or (c) leave `b_r1` and
  change `cue_b` so the player names the object. Give a recommendation and the
  cost of each. A command that stalls the player three times is worse than one
  extra firing.
- Use only words the story already has. No invented person, place or record.
- Imperative player voice (AGENTS.md "Writing Player Input"): verb plus object, no
  first person for "the player", `my` for the player's own things, no "do not",
  no waiting.
- Do not add the words "Phase One", "Phase Two" or "JANUS" to any 3C group that is
  not `e_r1`/`e_r2` (the narration leak scan rejects a later-reveal phrase).
- Do not widen anything so far that "Evacuate the facility.", "Carry Michelle to
  safety.", "Lead the captives to safety." or "Open the access panel." fires a
  reveal. They must still match nothing.

## Output

1. For each of the four reveals, the new `action_evidence` groups in full (old
   words plus new words, new words marked), as YAML to paste.
2. A table: every command in the "What happened" table, plus 20 more you choose
   (include "Evacuate the facility.", "Carry Michelle to safety.", "Open the access
   panel.", "Lead Michelle through the maintenance routes.", "Send the evidence
   package.", "Answer Charles's terrorist claim.", "Call the families of the
   missing.", "Check reports from other detention sites.", "Broadcast the detention
   site list.", "Take Rebecca's portable data case.", "Copy Rebecca's archive.",
   "Open the surface gates.", "Use the senior official's authorization.", "Restore
   the drainage pumps."), with the matcher result before and after (which reveal,
   or none). Run the real matcher over all ten 3C reveals.
3. Every command that matches two reveals after your change, and what you did
   about it.
4. Anything you could not satisfy, and why.

A word that fixes one command and breaks a neighbour is a net loss. Prefer the
smaller list.
