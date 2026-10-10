Review and finish the action words for the last two Scene 3C steps of the
Continuity Initiative package (`data/stories/continuity-initiative/`). Read
first: `AGENTS.md` ("Writing Player Input", "Fixing a Scene"),
`storygame/runtime/candidate_matcher.py` (the exact matcher, including
`_SYNONYM_CLASSES`, the negation words and the one-match rule), `knowledge.yaml`
(`k_sl_3c_*`; read the CURRENT `action_evidence` groups of all ten 3C reveals,
they now include last round's additions) and `handoffs.yaml` (the seven 3C cues).
Do not edit files; return text to paste.

Run the real matcher for every claim. Do not infer a result from reading a group.
Your answer overrides mine wherever they differ; say where and why.

## Where we are

Three live blind-player runs on staging (all nine scenes, 3C is last). The seven
cues work. In 3C the three players fired 4, 5 and 7 of the 7 steps by their own
commands (before the cues and last round's verb additions: 2, 5, 4; before any
3C cue: 1). One run reached the ending with no timer dump. No 3C turn was
rejected. Two stalls remain, both in words:

### Stall 1: the families (step D, part two, reveal `k_sl_3c_d_r2`)

After `cue_d_families` ("Families of the missing ask the broadcast chamber for
word.") the players typed these. `d_r2` fired only on the last one.

| Run | Turn | Command | Fired |
|---|---|---|---|
| r1 | 9, 10 | Answer the families. | nothing |
| r1 | 11 | Reassure the families. | nothing |
| r2 | 10 | Answer the families' requests for information. | nothing |
| r3 | 10 | Answer the families with the detention-site reports. | d_r2 (worked) |

`d_r2` has the verb phrase `answer the families with`, so only the last works.
The 14-turn timer then printed the rest in r1 and r2. These are the natural
commands for that cue; Michelle even says "Answer the families" in r1's text.

### Stall 2: the E cue and the second E reveal (`k_sl_3c_e_r2`)

`cue_e` reads: "A recovered document remains closed. Charles's signal still runs
through his last remote channel." In r3, E fired from "Open the recovered
document." (`e_r1`), which ends the chain. The player then typed the following
about the channel, none fired (`e_r2` has no `remote channel` object):
"Trace Charles's last remote channel.", "Examine Charles's last remote channel.",
"Read Charles's last remote channel.", "Decode Charles's last remote message."

E is the ending, so these did not cost the run. But a player who follows the
other half of the cue would stall.

### Other commands that did not fire (read these too)

- `c_r2`, after `cue_c_gates` ("The surface gates are shut above the waiting
  captives. The gate authorization is close to expiry."): r2 turn 5 typed "Enter
  my one-use authority code into the gate-status panel." Nothing fired; the
  narrator invented a panel readout. `c_r2` has the verb `enter` and the objects
  `one-time authorization`, `gate code`, `override code`, but not `authority code`
  or `gate-status panel`. Decide whether this is a word to add, a thing the story
  does not have (check `world.yaml` for `gate_status_panel`, which belongs to
  scene 3A), or something to leave unmatched. Give a reason.
- The gates cue text itself changed in the build: your round-2 text said "The
  senior official's authorization is close to expiry." The first-turn safety test
  rejected "senior official" in a cue, so the worker wrote "The gate
  authorization is close to expiry." and `gate authorization` is in the `c_r2`
  object group. Review that sentence. Say if it is the best wording or give a
  better one that passes the same test (no multi-word alias of a later reveal).

## My proposal (to compare with, not to copy)

- `k_sl_3c_d_r2`, first group: add `answer`, `reassure`, `respond to`.
- `k_sl_3c_e_r2`, second group: add `Charles's last remote channel`, `his last
  remote channel`.

I ran 26 commands over all ten reveals. Results with these additions: "Answer the
families.", "Reassure the families.", "Answer the families' requests for
information.", "Respond to the families of the missing.", "Reassure the families
of the missing." all `d_r2`; "Trace/Follow/Examine Charles's last remote channel."
`e_r2`; "Read Charles's last remote channel." none (`read` is not an `e_r2` verb).
One regression: "Answer the families about Charles's terrorist claim." matched
`a_r2` before and matches `a_r2` AND `d_r2` after, so it returns none. Not
changed: "Answer Charles's terrorist claim.", "Respond to Charles's terrorist
claim." (`a_r2`), "Answer Michelle.", "Reassure the captives.", "Answer the
reports from other detention sites." (none).

## What I want from you

1. The best set of additions for `d_r2` and `e_r2`, as YAML to paste (old words
   plus new words, new words marked). Say whether `answer` as a bare verb is
   acceptable given the `a_r2` clash above, or whether to use phrases such as
   `answer the families`, `reassure the families`, `respond to the families` and
   keep `a_r2` clean. Weigh the cost: a bare verb catches more natural commands;
   a phrase leaves "Answer the families." working but not "Answer them." or
   "Answer the people waiting."; say what you recommend.
2. Whether `read`, `decode` or `examine` belong in `e_r2`'s verbs (`e_r1` already
   has `read`, `examine`, `open`), given that `e_r1` and `e_r2` must not both
   match one command. Check "Read the recovered document." and "Read Charles's
   signal." specifically.
3. The `c_r2` question above (authority code / gate-status panel), and your view
   of the gates cue sentence.
4. A review of last round's additions with fresh eyes: `follow` and `follow
   Rebecca` in `b_r1`; `extend`, `guide`, `lead` in `c_r2`; `broadcast the
   reports` in `d_r1`; `broadcast updates` and `answer the families with` in
   `d_r2`. Say if any of them now causes a surprising match, with commands.

## Rules to keep

- ONE reveal may match a command; two matches return none, and that breaks the
  command. Report every new double match.
- Add words only. Do not remove or reorder existing words. Do not change a
  statement, a `delivery_text` or a cue unless your answer to the gates sentence
  requires it, and say so plainly if it does.
- Use only things the story already has. No invented person, place or record.
- Do not add "Phase One", "Phase Two" or "JANUS" to any group outside `e_r1` and
  `e_r2`.
- Commands follow AGENTS.md "Writing Player Input": imperative, verb plus object,
  `my` for the player's own things, no "do not", no waiting.
- "Evacuate the facility.", "Carry Michelle to safety.", "Lead the captives to
  safety." and "Open the access panel." must still match nothing.

## Output

1. YAML to paste per reveal, new words marked.
2. A table of at least 40 commands with the matcher result before and after:
   every command quoted in this brief, plus the negatives above, plus your own
   adversarial ones (close wording that must NOT fire, and wording that should).
3. Every command that matches two reveals after your change, and what you did.
4. Your answers to items 2, 3 and 4 above, each with the evidence behind it.
5. Anything you could not satisfy, and why.

A word that fixes one command and breaks a neighbour is a net loss. Prefer the
smaller list, but say which commands that choice leaves unfixed.
