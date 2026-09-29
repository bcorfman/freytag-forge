# World model: plan

Status (2026-09-28): decisions W1-W13 settled. S1 merged (PR 480),
S2 merged (PRs 481 and 485), and the 1B, 1C and 2A grounding merged (PR
486), and the narration leak fixes merged (PR 487), measured live: no
leak rejection in 1B, 1C or 2A, and every 1B-2A handoff fires. On
`claude/ground-2b`: scene-entry recall scoped (ef80a28) and 2B grounded
(3f765ba) with reveal handoffs (a1e7885), measured live, and merged
(PR 488). 2C grounded with handoffs on `claude/ground-2c`, plus two
recall fixes (EARLIER IN THE STORY; people alone do not recall),
measured live: no drift in 3 of 3, every handoff fires. Turn 5 no longer
contradicts 2C.3 and Brandon voices his stance 2 of 3 (00052d3); the
bare "console" drift is fixed by scoping the shortcut (b7dcec5) and the
match call's THINGS (decba7f), measured live 10 of 10, and match
answers limited to THINGS (d7e0c68); showing the match call the
narration sentence is probed, not built; bare "corridor" is a measured
known gap. Next: decide on building the sentence, push
`claude/ground-2c`, then 3A-3C, S3 and S4. See "Resume here".
The task split is in section 11. Written at Brandon's request
after decision 1e (containment) in
[narrated-world-continuity.md](narrated-world-continuity.md) kept turning into
separate small decisions. This plan replaces decision 1e. It also gives
decision 1a's state axes, the `fixed` refusal and the protagonist's place a
home in one model. The capture loop, cause routing and rollout stay in the
continuity plan; this plan defines the world they write into.

## Resume here (2026-09-28)

Everything through the 1B-2A handoffs is on `main` (PR 486, merge
5ecc30a). Branch `claude/magical-wozniak-tvkj5x` holds the three leak fixes
below. It was made in a cloud session with no Ringer, no `.env` and no
saved `bench/results`, so it was diagnosed and checked offline only.

**Live result (2026-09-28, Ringer, one replicate each, check passed).**
Both replicates completed. The three fixes held. 1C turn 16 ("Search the
logistics terminal for transfer records.") earned `k_sl_1c_c_r1` in 1C,
and the scene moved to 2A after it. 2A turn 5 ("Warn the supervisor
about the cooling-water fault.") earned `k_sl_2a_c_r1`, and the scene
moved to 2B after turn 7. No turn was rejected for "the supervisor",
"logistics terminal" or "workstation". Every other handoff fired as
before: 1B turn 5, 1C turns 9 and 13, and 2A turns 1 and 2. The 2A
variation stops when the scene is left, so no 2B turn ran, and the
side-effect case in 2B is still unmeasured live.

**A fourth leak, found by the run:** 1B turns 6, 7 and 8 ("Walk across
the park to the man watching me.", "Show the man Michelle's
photograph.", "Hand the man the number sequence.") were rejected for
"park bench". That phrase is a `must_convey` of the 1A memory-card
reveal `k_sl_1a_b_r1`. The 1B-1C variation started 1B bare, so the 1A
reveal was never earned. This is the same setup gap 6be66c7 fixed for
2A, and it likely explains the earlier "Brandon's name 2 of 3" in 1B.
Offline, a thorough 1B start passes "park bench", "dead drop" and
"memory card", and a bare one rejects all three. The 1B-1C variation
now has `"entry_state": "thorough"`. Offline, the whole 20-turn script
still plays with the same handoffs and moves to 2A after 1C turn 9.
`leak_fix_check.py` now fails on any leak rejection, not only the three
terms. It missed this one.

**Rerun (2026-09-28, Ringer, 1B-1C only, thorough entry; check
passed).** The replicate completed, with all 20 turns narrated and no
rejected turn. Every handoff fired: 1B turn 5 (`k_sl_1b_a_r1`), 1B turn 7
(`k_sl_1b_b_r1`, Brandon's name, rejected before by "park bench"), 1C
turns 12, 16 and 19 (the tire tracks, the captives, the logistics
terminal). The story moved to 2A after 1C turn 9 (run turn 19), as the
offline run predicted. Judges: continuity contradicts a stated fact
1/20, acts beyond the command 5/20, restarts the scene 0/20. Fact
tracking: facts after the turn correct 17/20. Read
`bench/results/world-leakfix2-1b-1c` for the three wrong facts and
the five over-acting turns before 2B, if they matter. Not measured
live: 2B turns after the supervisor path, because the 2A variation
stops when the scene is left.

**Merged** as PR 487 (459d0ae).

**Stale 1A entry line in later scenes (fixed, ef80a28).** Any command
naming Michelle recalled `k_scene_1a_entry` ("Michelle's phone remains
on the kitchen floor") as true SCENE material in every later scene. It
showed live in 1B turns 4 and 7. Brandon chose to scope it:
`KnowledgeProjector._committed_for` no longer recalls `scene_entry`
items outside their own scene. Ringer, Luna, one attempt; suite 897
passed. Offline capture confirms the line now reaches only 1A. Not
measured live.

**2B grounding (Brandon's decisions, 2026-09-28).** `janus_archive` is
renamed "records archive" (alias "restricted records archive"), because
the old name put the reveal phrase "JANUS archive" (a `janus_evidence`
must_convey) into 2B's opening. Fixed `archive_terminals` ("archive
terminals") and `medical_terminal` things are placed in the archive;
the medical terminal is not in a medical level. 2B declares
`companions: [brandon]`. Payloads must stay byte-identical except 2B's
opening location line. **Done as 3f765ba** (Ringer, Luna, one attempt;
suite 898 passed; `ringer-work/freytag-2b-grounding/verify_2b.py`
passed: 1A-3A payloads byte-identical except that line). The leakage
matrix needed no knowledge edits. Not measured live: no 2B bench script
exists.

**2B live replicate (2026-09-28, Ringer, one replicate, check
passed; 18c4f30).** `bench/variations/item-facts-world-2b.json`,
script `archive-evidence` (10 turns, thorough entry), results in
`bench/results/world-2b`, read by
`.plans/world-model-scenes/scene_2b_check.py`. Completed, no rejected
turn, no leak rejection. Every name the reply used resolved directly
("records archive", "archive terminals", "medical terminal",
"infrastructure corridors", "inspection console"), so no match call
was needed and nothing was unplaced. The engine refused the reply's
bad changes: the medical terminal (turns 5, 9) and the archive
terminals (turn 10) "moved to Kristin" were refused as fixed, and "records
archive" placed in Kristin (turn 4) was refused as an area. Kristin's
walk to the corridors and back (turns 7-8) landed, with Brandon
following. Fact tracking: facts after the turn correct 10/10.
Continuity: command not finished 3/10 (turns 2, 5, 10), restarts the
scene 1/10 (turn 8, "Lead Brandon back into the records archive.", a
judge false positive, because the command asks for the return).
**The gap:** `k_sl_2b_a_r1` and `k_sl_2b_a_r2` were offered on every
turn, and the narrator selected neither, even for turn 1 "Search the
archive terminals for Michelle's record." (R1) and turn 2 "Pull up my
own record on the archive terminals." (R2). So no 2B knowledge was
earned, `janus_evidence` arrived only as the turn-10 cue, and the scene
never left. The 2B candidates have no `earn_when`, `action_evidence` or
`delivery_text`. This is the same gap 2a806db closed for 1B-2A.

**2B reveal handoffs (a1e7885).** Written in ChatGPT Desktop over three
prompt rounds and approved by Brandon. The first answer gave alternatives
the same nouns, which my prompt allowed, and a handoff fires only when
exactly one offered candidate matches. The final prompt stated the
matcher's rules (whole-word phrases, no plurals, possessives are one
word, exactly one match), the commands each entry must and must not
catch, and that `earn_when` finishes "Earn it when the player ___.".
Landed by Ringer (Luna, one attempt; suite 898 passed; payloads
unchanged); `ringer-work/freytag-2b-handoffs/verify_handoffs_2b.py`
checks the exact values and 16 matcher cases.

**2B rerun (2026-09-28, Ringer, one replicate, check passed;
`bench/results/world-2b-handoffs`).** Handoffs fired on turns 1
(`k_sl_2b_a_r1`), 3 (`k_sl_2b_b_r1`) and 5 (`k_sl_2b_c_r1`), each
delivery sentence reached the narration word for word, and the scene
moved to 2C after turn 8 (min_turns), so turns 9-10 did not run. No
rejected turn, no leak rejection. Facts after the turn correct 8/8.
Continuity: command not finished 2/8 (turns 5, 6), acts beyond the
command 2/8 (turns 4, 8), restarts the scene 1/8 (turn 8, the same judge
false positive as before). Turn 5's lead-up said the files were "heavily
encrypted" right before the delivered find, although the reveal-turn
rule ("Write only what leads up to it.") was in its prompt: 1 of 3
reveal turns. Watch it over more replicates before any change. Minor:
turn 8's reply carried an empty `lantern` entry copied from the
variation's output example; the engine flagged and ignored it.

**Merged** as PR 488 (2df25bb).

**2C grounding (Brandon's decisions, 2026-09-29).** 2C happens in the
command levels: the detention sectors are sealed until 3A. `purge_chamber`
keeps its id and is renamed "command levels" (aliases "command level",
"upper command corridors"), as `janus_archive` was. 2C declares
`companions: [brandon]`. Rebecca, Charles and Michelle stay unplaced
(private contact, orders, a coded message), and Rebecca's secured office
is not declared in 2C, because it is a must_convey of
`rebecca_office_required_for_broadcast`. No things are declared up
front. The `evidence_ready_to_transmit` cue named "broadcast controls"
beside "Kristin's terminal", which contradicts 2C.5 (the broadcast works
only from Rebecca's office). ChatGPT Desktop reworded it, and Brandon
chose: "In the command levels, Kristin notices the copied files close at
hand, yet using them could expose her and Brandon." Payloads must stay
byte-identical except 2C's opening location line. Check:
`ringer-work/freytag-2c-grounding/verify_2c.py`. **Done as 6f10f91**
(Ringer, Luna, one attempt; suite 899 passed; payloads byte-identical
except that line).

**2C live replicate (2026-09-29, Ringer, one replicate, check passed).**
`bench/variations/item-facts-world-2c.json`, script `purge-clock`,
results in `bench/results/world-2c`. Completed, no rejected turn, no
leak rejection, facts after the turn correct 9/10. No handoff (2C has
none yet); the purge clock came by pacing (turn 3) and the two later
facts by cues (turns 9, 10). Two grounding problems:
- **Place drift from "corridor".** Turn 2's reply put Kristin in
  "corridor", and the match call mapped it to 2A's infrastructure
  corridors, which are in play because every facility area now shares a
  parent. Turn 3 then ran in the corridors, turn 4 ("Check the copied
  files for proof of the purge order.") walked her into 2B's records
  archive, and turns 4-7 played there. The engine tracked it all
  correctly; the scene drifted. **Brandon chose a match-call rule:**
  after the spot rule, 'A plain word like "corridor", "hall" or "room"
  is a spot in the place where PLAYER CHARACTER is now.'
- **Dropped move on turn 10.** "Follow Michelle's route through the
  maintenance network." put Kristin in "maintenance network", which
  matched no area, so the move was dropped. **Brandon chose to declare
  an area:** `maintenance_network` ("maintenance network", aliases
  "maintenance route", "maintenance routes"). Its parent is
  `purge_chamber`, not `regional_facility`, because narration safety
  lets a scene name only its own area and the areas above and below it.
  "maintenance access route" is not an alias: it is a must_convey of
  `rebecca_office_required_for_broadcast`.
Both fixes are in one Ringer run (`ringer-work/freytag-2c-fixes`), with
verifiers `verify_match_rule.py` and `verify_maintenance_area.py`.

**Landed:** the match rule as c1962aa and the area as e414060 (Ringer,
Luna, one attempt each; full suite passed in each worktree; the two
affected test files pass together).

**2C rerun (2026-09-29, one replicate, check passed;
`bench/results/world-2c-fixes`).** Kristin stayed in the command levels
for all ten turns, and turn 10 landed her in the maintenance network,
with nothing unplaced. No rejected turn, no leak rejection, no
continuity flag. Facts after the turn correct 9/10: turn 3's reply
moved Kristin to "upper command corridors", an alias of the command
levels, so the tracked place did not change and the judge counted a
missed move (a judge false positive about an alias). **Not measured:**
the match rule. The narrator never said a bare "corridor" this run, and
the match call ran on only 2 turns. Watch for it in later replicates.

**2C reveal handoffs (bc595b8).** Written in ChatGPT Desktop over four
prompt rounds and approved by Brandon. Round 2 copied the prompt's test
commands into the noun lists (15/15 prompt commands, 0/17 variants); the
fix was telling it that other wordings would be tested and capping noun
phrases at three words. Final: 43/46 across 2C's three offered sets, no
false positive. Landed by Ringer (Luna, one attempt; suite 900 passed;
payloads unchanged; `ringer-work/freytag-2c-handoffs/verify_handoffs_2c.py`).

**2C rerun with handoffs (2026-09-29, one replicate, check passed;
`bench/results/world-2c-handoffs`).** Handoffs fired on turns 1
(`k_sl_2c_b_r1`), 4 (`k_sl_2c_c_r1`) and 6 (`k_sl_2c_d_r2`), and the
scene moved to 3A after turn 8. Facts after the turn correct 8/8, no
rejected turn, no leak rejection. Continuity: turn 3 acts beyond the
command and does not finish it; turn 7 does not finish decoding.
**Place drift again, with a different cause.** Turn 2 ("Ask Brandon
what he is hiding.") narrated Brandon "in the corner of the restricted
infrastructure corridor", and the match call correctly followed the
prose. The cause: naming Brandon recalls out-of-scene knowledge about
him (2A's "Kristin and Brandon have opened a restricted infrastructure
corridor...", plus 1B, 1C and 2B statements), and it is listed in SCENE
as present fact. It was in all three 2C runs' turn-2 prompts; the
narrator moved there in two. So the first 2C run's drift was this too,
not the match call. **Brandon chose to mark it as the past:** keep the
recall, but render other scenes' committed knowledge under its own
EARLIER IN THE STORY heading after SCENE. Ringer run
`ringer-work/freytag-earlier-recall` (check: `verify_earlier.py` on
thorough-state prompts for 1B, 2B and 2C; fresh-state payloads
byte-identical).

**EARLIER IN THE STORY landed (522c00c;** Ringer, Luna, one attempt;
suite 901 passed; fresh-state payloads byte-identical). **Measured over
four 2C replicates** (`bench/results/world-2c-earlier` and
`world-2c-earlier-x3`): every handoff fired on turns 1, 4 and 6 and the
scene moved to 3A after turn 8 in all four; no rejected turn, no leak
rejection; facts after the turn correct 8/8, 8/8, 7/8, 7/8 (the misses
are turn 8 recording 3A's entry placement after the transition, a bench
artifact). **Drift: 1 of 4** (x3 replicate 1: turn 2 again put Brandon
"in the corner of the restricted infrastructure corridor", and turns 4-7
ran in the records archive), against 2 of 3 before. The corridor line
was correctly under EARLIER IN THE STORY; the narrator borrowed it
anyway. Also seen: the narrator's generic "console" was mapped by the
match call to 2A's fixed inspection console (refused as fixed, no harm).

**Brandon chose: naming only a person does not recall (ae6406f).**
Out-of-scene recall now ignores character ids (the world's npcs and the
protagonist): "Ask Brandon about the infrastructure corridors." still
recalls the 2A corridor, "Ask Brandon what he is hiding." recalls
nothing. EARLIER IN THE STORY stays for what is recalled. Ringer, Luna;
the first run failed only because my spec forbade updating the EARLIER
test, which used the person-only command; the second passed in one
attempt (suite 903). **Measured over three 2C replicates**
(`bench/results/world-2c-people-x3`): **drift 0 of 3**, every 2C turn
in the command levels, no earlier place named in any narration; every
handoff fired (turns 1, 4, 6) and each replicate moved to 3A after turn
8; facts after the turn correct 23/24; no rejected turn, no leak
rejection. Continuity still flags turn 5 ("Argue with Brandon about
sending the copied files now.") as contradicting a stated fact in 2 of
3 (Brandon agrees to hold the files, while 2C.3 has him argue to send
them at once), and 3 of 7 runs since the handoffs. Not addressed yet.

**Plain-place-word match rule, measured live (2026-09-29).** It did run
live: in all three people-x3 replicates turn 2's reply put Kristin in a
bare "room", mapped to the command levels. A bare "corridor" had not
come up, so a Ringer probe (`~/dev/ringer-work/freytag-corridor-probe`:
stubbed narrator reply, live match call and Jev check, real 2C state
with "infrastructure corridors" in THINGS) measured it: **"corridor" went
to 2A's infrastructure corridors 9 of 10**, "room" to the command levels
5 of 5. Fix ranking, as measured:
- Rule: moving the plain-word sentence first and adding 'Give that place
  even when another place in THINGS has the same word in its name, like
  "east corridors" or "guest room".' (1da3bbf) made it worse: corridor
  10 of 10 wrong, room 0 of 5 (all to "kitchen"). Reverted (a8d4761).
- LLM check: the existing Jev place check had said yes to 'Is the place
  called "corridor" the same place as "infrastructure corridors", or
  inside it?'. c0ddddc asks a contrastive question when the target area
  is unrelated to the player's area ('Kristin Schweitzer is in "command
  levels". Is the place called "corridor" really "infrastructure
  corridors", rather than a spot in "command levels"?'), and a no now
  lands the move in the player's area (before, a no left the thing with
  no place). Jev answered yes 8 of 8; corridor still 8 of 10 wrong.
  Kept for the no-place fix; suite 906 passed.
- Scoping the match call to the current scene's areas was declined: a
  real narrated move into an earlier scene's area (which narration
  safety allows once that scene was entered) would be dropped.
**Brandon chose: a known gap.** The drift that happened came from recall,
which is fixed. Revisit if a bare "corridor" appears in 3A-3C.

**Turn 5 cause (2026-09-29).** No 2C statement says where Brandon stands.
The turn-5 SCENE has only `k_sl_2c_c_r2` ("...Kristin and Brandon must
choose whether to risk the captives by sending it now."), so the
narrator picks a side; in two replicates Brandon wants to wait. Plot 2C.3
has him argue to send at once. **Brandon chose:** ChatGPT Desktop rewords
`k_sl_2c_c_r2`'s statement and delivery_text to state Brandon's stance in
third person, without deciding Kristin's side, keeping one phrase from
each must_convey group. First round returned unattributed dialogue as
the statement (my prompt asked for "something he could say aloud"); a
corrected prompt is out. Brandon chose the pair: statement "Brandon wants
to send the evidence now. He will risk the captives. He accepts that this
makes rescue impossible." and the matching delivery_text. **Landed**
(Ringer, Luna, one attempt; suite passed; only those two fields changed).

**2C turn-5 rerun (2026-09-29, three replicates, check passed;
`bench/results/world-2c-stance-x3`).** The stance line was in every
turn-5 SCENE. Continuity contradicts a stated fact **0 of 24 turns**
(turn 5 was 2 of 3 before). But in all three, turn 5 is one paragraph
of Kristin arguing to wait, and Brandon never answers, so the judge
flags command_not_finished 3 of 3. By Brandon's standing rule an NPC
who stays silent does not make a command unfinished, so that is a judge
false positive; the open question is only whether Brandon should voice
his stance. Otherwise unchanged: every handoff fired (turns 1, 4, 6),
Kristin in the command levels every turn, facts after the turn correct
21/24, no rejected turn, restarts_scene 2 of 24 (turn 2 "enters the
room").

**Brandon chose to have Brandon voice his stance.** A live A/B replay of
the three recorded turn-5 prompts (Ringer,
`~/dev/ringer-work/freytag-answer-rule-probe`, 15 samples per arm, read
by hand): Brandon says aloud that they must send now 5 of 15 as
recorded, 10 of 15 with "When the player talks to someone, that person
answers." after the gives-a-thing turn rule (one rule sample ran into a
long exchange ending with Brandon giving in). **Landed as 00052d3**
(Ringer, Luna; suite passed; one line in `_turn_rules_before_grounding`,
which the recovery path reuses; not in the opening, which narrates no
player action).

**2C rerun with the answer rule (2026-09-29, three replicates, check
passed; `bench/results/world-2c-answer-x3`).** Turn 5: Brandon argues to
send now in 2 of 3 and is silent in 1; command_not_finished on turn 5
0 of 3. Contradicts a stated fact 0 of 24, restarts 0 of 24, acts
beyond the command 4 of 24 (walking into "the room" on turns 2 and 5, a
pistol grip on turn 8). Every handoff fired (1, 4, 6); facts after the
turn correct 21/24; no rejected turn.
**New drift, 1 of 3, from a different cause:** replicate 1 turn 4 ("Check
the copied files for proof of the purge order.") replied `"Kristin":
{"place": "console"}`. "console" resolves directly (no match call) to
2A's fixed inspection console, so Kristin moved into the infrastructure
corridors. Turn 5's "room" then matched the corridors, and turns 6-7
were narrated there, until turn 8 walked her back.
The cause was the bare-name shortcut in `_resolve_name`: `_resolve_refer`
takes a bare word when exactly one tracked name in the whole story ends
in it. Brandon asked whether renaming the console to "terminal" would
help; no, several tracked names already end in "terminal", and the match
call had already sent a bare "terminal" to 2B's archive terminals.
**Brandon chose to scope the shortcut (b7dcec5):** it now considers only
tracked names in scene scope (the scene's and the player's areas and
below, scene items and people, held things, unplaced things). Full
names and aliases resolve as before. Ringer, Luna; suite 910 passed.
The first run failed on my verifier, which demanded that Kristin stay
in the command levels after a "new" match, while the existing design
leaves her unplaced; the worker changed placement logic to satisfy it.
The corrected run passed on its second attempt.
**Measured by a live probe** (`~/dev/ringer-work/freytag-console-probe`:
stubbed reply putting Kristin at a bare "console" on "Check the copied
files for proof of the purge order.", thorough 2C entry, live match call
and Jev): the shortcut no longer fires, but the match call picked
"inspection console" 10 of 10, Jev confirmed 10 of 10, and Kristin still
landed in the infrastructure corridors 10 of 10 ("room" 5 of 5 to the
command levels). The match call sees the console because its THINGS
filter compares top-level areas, and every facility area shares one.
**Brandon chose to scope the match call's THINGS too (decba7f):** it now
uses the same `_name_in_scene_scope` test as the shortcut, so in 2C it
lists only Kristin and the memory card. The place and character lines
that follow are unchanged. Ringer, Luna, first attempt; the check
compared THINGS with scene scope in 1A, 1B and 2C, compared the place
lines with a baseline from the old code, and ran the full suite.
**Measured by the same live probe:** Kristin no longer reaches the
infrastructure corridors (0 of 10, was 10 of 10). Her place is the new
"console" 10 of 10. "room" still goes to the command levels 5 of 5. The
match call still never answers "new" for "console": it now picks
"Michelle's memory card" 10 of 10, and Jev rejects that pairing 10 of 10.
So the right outcome depends on Jev catching a wrong match. Not tested:
where the new console itself is placed, and a full live 2C replay.
Brandon: Jev is meant to be the fallback, not the thing that makes this
work. Cause: the match call never sees the narration, only the command,
THINGS and the bare new name, so it guesses the thing that fits the
command.
**Closed set (d7e0c68):** a same_as answer must be "new" or a name
offered in THINGS (any case); anything else is kept as new with an
issue. Before this, an answer naming the unoffered inspection console
still moved Kristin. Ringer, Luna, second attempt (first was a worker
network error); full suite passed. Eight existing tests stubbed targets
their THINGS never offered; they now inject the target into the offer.
Risk not measured: a new name the model maps to a person named only in
the command, not in THINGS, is now new.
**Probe `~/dev/ringer-work/freytag-match-sentence-probe`** (stubbed 2C
turn, live match call and Jev; not yet in the engine): showing each new
name's narration sentence in NEW NAMES (`- console (from: "Kristin sits
down at the console.")`) took "console" to "new" 9, 8 of 10, but "room"
to the command levels only 3 of 5 and 6 of 10 (the rest echoed "room").
Adding "Each same_as answer must be a name copied from THINGS or "new"
..." fixed "room" 10 of 10 but sent "console" to the memory card 5 of
10. Finishing the existing rule instead ("... where PLAYER CHARACTER is
now, so give that place.") gave "room" 10 of 10 and "console" 8 "new",
1 echo, 1 memory card (Jev rejected it); Kristin's place right 20 of 20.

**Next:** Brandon to decide whether to build the sentence and the
finished "room" rule into `_match_payload` and `_MATCH_SYSTEM` (then
rerun both probes), then push `claude/ground-2c` for review, then 3A.

### Narration leak diagnosis (2026-09-28, offline)

Reproduced by running the real `RuntimeEngine` and
`CloudflareTurnProvider` with `urlopen` stubbed to return a fixed
narration line, from the bench's bare and thorough 2A states. A
second stub run played each variation's script with neutral narration,
to see which scene each turn runs in. Three separate causes:

- **"the supervisor" (2A "Warn the supervisor about the cooling-water
  fault."). Fixed, not yet measured live.** `k_sl_2a_c_r1` was
  `world_only`, because it also set `rebecca_observing_infiltrators`.
  The projector never offers a `world_only` item as a player candidate,
  so its 2a806db handoff could never fire. Its `must_convey` phrases
  ("the supervisor", "security officer", "corridor access", "cooling
  failure" and the rest) still counted as known terms, and a
  `world_only` item is never earned by the player. So narration could
  never say them in 2A. The fix splits it the way SL-2A-C-R2 is already
  split: `k_sl_2a_c_r1` is now public and sets only
  `restricted_corridor_access`, and a new `world_only`
  `k_sl_2a_c_r1_rebecca_observes` (a copy of the R2 one, same source)
  sets the Rebecca fact. No other hidden item has this problem.
  Verified offline: the handoff fires on the script's turn 5, and
  narration naming "the supervisor" passes on that turn
  (`test_warning_the_supervisor_earns_corridor_access_by_handoff`, which
  fails on the old package). The full suite (893) passes. The capture of
  1A, 1B, 1C, 2A and 3A payloads is byte-identical. Side effect: R1 now
  fires at turn 5, so R2 (the corridors, turn 6) can no longer fire,
  because the storylet has fired. R2 put `infrastructure_corridors` and
  `inspection_console` in the earned entities. R1's `entity_ids` are
  empty, so after R1 those names are unavailable once the scene moves to
  2B. The script's turns 8-10 already run in 2B (min_turns 7), and they
  name the console. Expect leak rejections there until 2B is grounded
  or the script is cut. Not decided: whether R1 should list
  `infrastructure_corridors` in its `entity_ids`.
- **"logistics terminal" (1C "Go up to the logistics terminal.").
  Fixed (Brandon chose a).** The turn ran in 2A, where the terminal
  was not available. The captives handoff (1C script turn 6) sets
  `captives_confirmed_alive`. `bridge_1c_infiltration_needed` needed
  only that and `facility_proof`, so it fired on the same turn, and at
  min_turns (7) the scene moved to 2A. SL-1C-C (the terminal) needs
  both facts too, so a player who found the captives first never got a
  turn to reach it. The bridge's own `fallback_realization` says it
  follows "national scope". The bridge now also requires
  `national_detention_network_known`. The loader requires a
  FactDelivery for every fact a bridge needs, so `handoffs.yaml` has one
  for it. Its `fallback_text` is `k_sl_1c_c_r1`'s authored
  `delivery_text`, word for word, and its `must_convey` phrases come
  from that text. It has no `cue_text`. No new prose was written. If
  better phrasing is wanted, get it from ChatGPT Desktop. SL-1C-C is now
  a required storylet (28, was 27), and the canon journey selects
  `k_sl_1c_c_r1` in a 1C slot that was empty. Offline, the 1B-1C script
  now earns the terminal on 1C turn 8 and moves to 2A on turn 9. A
  player who never reads the terminal still reaches 2A at
  handoff_after_turns (11), through the new delivery.
- **"workstation" (a 2A opening). Fixed (Brandon chose a).**
  `michelle_workstation`'s name is the bare word "workstation", so any
  narration outside 1A that called a desk a workstation was rejected.
  The leak check now also allows the things of every scene the player
  has entered (`NarrationSafetyValidator._entered_scene_entity_ids`,
  read from the `scene_<id>_entry_known` facts). A thing the player
  has already met is not a spoiler. This also allows "logistics
  terminal" after 1C. Future places are still rejected: the detention
  level stays unavailable in 2A and 2B. The leakage matrix is
  unchanged, because it checks future terms only.
- **The supervisor fix's side effect is covered by the workstation
  fix.** On the supervisor path, R2 never fires, so the corridors and
  the console never enter the earned entities. They are 2A scene
  things, though, so once 2A is entered they stay available in 2B.
  Offline probes from the thorough 2B state pass "inspection console",
  "infrastructure corridors" and "the supervisor". Proposed, not
  applied: give `k_sl_2a_c_r1` `entity_ids: [kristin, brandon,
  regional_facility, infrastructure_corridors]` and `relevance.entity_ids:
  [infrastructure_corridors]`. Its statement already says "gaining
  corridor access", so the knowledge would name what it grants, like R2
  does. That is a structured edit with no prose, and it changes no
  payload a capture covers.

Verified for all three: the full suite passes (896), ruff is clean, and
the 1A, 1B, 1C, 2A and 3A payload capture is byte-identical. New tests
fail on the old code: the supervisor handoff, the 1C bridge waiting for
the terminal, and 2A narration allowing things from entered scenes.
Not yet measured live.

### Where things stand

- **The model.** The `worldkeeper` library and its storygame adapter, the
  package schema (kinds, area parents, new-form placements, character
  placements, companions, `on_assert` effects), seats and the engine's
  prerequisite steps (W11-W13). Sections 4-9 describe the model, and
  section 11 records how each part was built.
- **The bench uses it (S2).** Replies name the parent. THINGS shows the
  authored text or the parent's name. Things are captured into the world. The
  match call lists only things in play: the scene's `item_ids`, things in the
  protagonist's top-level area, and things she carries.
- **The shipped narrator still reads authored placement text only.** The
  runtime turn does not capture into the world until S4. Every package change
  must leave the shipped payloads of converted scenes byte-identical, unless
  a change is intended and approved.
- **Measured.** On the v36 comparison with the fixed judge, the branch beat
  v36 in every category: place changes 38/40 against 18/24, conditions 15/16
  against 6/10, and turns with every fact right 61/68 against 26/36.
- **Converted scenes.** 1A in full. 1B in full as a package: the dead drop,
  the truck and Brandon's companion effect (44a99eb). 1C in full as a
  package (f1b8d5b): the facility area tree, the freight terminal and its
  sub-areas, and Brandon as companion. 2A in full as a package (6aad57e):
  Brandon's hideout, the servers and the move to the facility. All three
  have bench scripts, live-measured, and reveal handoffs (2a806db).
  Scenes 2B-3C have no placements and no handoffs at all.
  **Next: merge the leak fixes, then 2B.**
- **Bench scripts for 1B, 1C and 2A, and what their runs found.**
  `bench/variations/item-facts-world-1b-1c.json` plays 1B's `dead-drop`
  (10 turns) and continues into 1C's `terminal-descent` (10 turns). The
  two scenes are chained because a bare 1C start has no transit token;
  1B's last turn puts it in the truck, and an offline check confirmed the
  1B-to-1C advance keeps it there at the freight terminal.
  `bench/variations/item-facts-world-2a.json` plays 2A's
  `hideout-to-corridors` (10 turns): the servers, the cover (the
  `false_identities_ready` move), the corridors and the console. Both use
  the two-scene variation's item_facts and system prompt, with no 1A
  overrides. Run each with `--replicates 1` (`--scene 1B` and
  `--scene 2A`) through Ringer, then read `item_facts_unplaced` and the
  match-call resolutions.
  **First replicate (2026-09-27, at 3a907ba):** both completed, with no
  rejected turns and no failed replicate. Every new name resolved:
  the transit token, the number sequence, the photograph, the bench, the
  truck, the loading docks, the freight terminal, the logistics terminal,
  the hideout, the servers, the corridors and the console. The token rode
  in the truck from 1B to 1C. The run shows four problems:
  - `item_facts_unplaced` read 0 of 77, and that is true: no reply change
    was dropped. Every place that did not resolve by name went to the
    match call, which mapped it to a known name. The turn record keeps
    those place mappings only inside `match_raw`; `item_facts_resolutions`
    lists thing names only. Some mappings are right ("parking lot" to the
    park, "stairway" to the corridors). Three are wrong: "below" to the
    loading docks (1C), "checkpoint" to Brandon's hideout (2A turn 4, so
    Kristin stayed in the hideout) and "security desk" to the inspection
    console (2A turn 5, so Kristin moved to the console's corridors).
  - The match call also maps strangers to Brandon: "stranger" and
    "stranger in the park" in 1B (right, since he is the man), and also
    "prisoners" in 1C and "guard" in 2A. It mapped "ID" to the inspection
    console. The call seems to prefer any listed name over "new".
  **Match fix (Ringer, Luna, one attempt; suite 876 passed).** Two rules
  follow the spot rule in `_MATCH_SYSTEM`: a place not in THINGS and not a
  spot in one is "new", and a person maps to someone in THINGS only when
  it is that same person ("A guard or a prisoner who is not in THINGS is
  \"new\"."). Each turn record now has `item_facts_place_resolutions`
  (place name to world name, or "new"). One rerun replicate of each
  variation, with no rejected turns: "checkpoint" was "new" and recorded
  as unplaced, "prisoners" and "guard" no longer became Brandon, and
  "below" went to the observation shaft. New misses in the same run:
  "stranger in the park" became Kristin (1B turn 6) and "door" became the
  inspection console (2A turn 10). One replicate cannot tell the rules'
  effect from sampling noise; more replicates are needed before judging.
  **Three more replicates each (2026-09-27, at 1d342c1; Ringer, all six
  completed, no rejected turns).** The two rules do not hold most of the
  time. Across the four post-fix replicates: "checkpoint" became Brandon's
  hideout in 2 of 3 (it was "new" once, in the first rerun); "stranger in
  the park" became Kristin in 2 of 4; "prisoners" became Brandon in 1 of 3.
  Other wrong mappings seen once each: "service path" to Kristin, "heavy
  electrical service" to the service level, "below" to the prisoners and to
  the loading docks, "in front of metal door" to the inspection console,
  and "stairway" in 2A's corridors to 1C's service level. Right mappings
  held: "stranger" to Brandon in 1B turn 6 (3 of 3), "server console" to
  the servers (3 of 3), "park entrance" to the park, "corridors" to the
  infrastructure corridors. Per the fix ranking, a rule that fails this
  often calls for step 2, an LLM check. Brandon chose both an engine kind
  guard (B) and a per-mapping Jev question (A), B first.
  **B done (Ringer, Luna, two attempts; suite 880 passed).** Two guards in
  `apply_item_facts`, using only the world's kinds: a new name that the
  match maps to the player character stays new (issue "...mapped ... to
  the player character; kept as new"), and a character whose place the
  match mapped to a character is left unplaced (issue "...mapped place
  ... to a character; ... left unplaced"). A thing placed at a place
  mapped to a character is still allowed ("Kristin's pocket"). Unit tests
  replay the recorded live replies. Not measured live on its own; it is
  measured together with A. **Next: A.**
  Correction (Brandon): "B first" meant measure B live before building A.
  A's first task was stopped before any live run, and B was measured
  alone. **B alone, three replicates each at d98cbd5** (all six completed;
  2A replicate 2 had one rejected turn): the guard fired 4 times, all
  "new name to the player character": "stranger" or "stranger in the park"
  at 1B turn 6 in 3 of 3, and "prisoners" in 1C once. The later turns then
  mapped "stranger in the park" and "man in the park" to that new
  stranger, consistently. The place guard never fired. At 1B turn 6 the
  match now gave Kristin in 3 of 3, where the pre-B replicates gave
  Brandon in 3 of 3; B does not touch the match call, so this is the
  model's sampling, not B. Wrong mappings B leaves, out of 46: "prisoners"
  and "guard" to Brandon (once each), "checkpoint" to "checkpoint guard"
  and to the infrastructure corridors, "security checkpoint" to the
  corridors, "credentials" to the inspection console, "identification
  numbers" to the handwritten number sequence. "checkpoint" to the hideout
  did not recur. Right: the parking lot, the truck, the servers, the
  corridors, the stairway, the loading dock, "below" to the observation
  shaft. So A is still needed, for people, things and places alike.
  **A, first live run (not applied).** Brandon asked for concrete
  questions: five templates by kind ("Are the guard and Brandon Corfman
  the same person?", "Is the place called the checkpoint the same place
  as Brandon's hideout, or inside it?"), fact lines from the world, and
  "Answer yes only if the story shows it." Luna passed on the second
  round (suite 892). Three replicates each: Jev answered all 24 checks,
  but about 11 were wrong "no"s, mostly places in 1B and 1C ("park",
  "parking lot", "park entrance", "loading dock", "service levels",
  "service entrance", "server" twice, and "stranger in the park" to
  Brandon). Right: "checkpoint" to the hideout rejected twice, the
  corridors, the server console, the door. Unplaced entries rose from 8
  to 23. Causes: the fact lines lack "in" ("Kristin Schweitzer is Los
  Angeles park."), the evidence-only wording is too strict for place
  names, and the "the" rule garbles phrases ("the below"). 2A turn 5 was
  rejected in 3 of 3 by the narration leak check (1 of 3 without A);
  that check runs before capture, so A does not cause it.
  **A, grammar round (not applied).** Brandon judged the questions sound
  and the glued-together grammar the problem. Names are now quoted with no
  article ('Are "guard" and "Brandon Corfman" the same person?') and the
  facts are structured `player` and `known` fields (name, place, held_by,
  can_move, place_text). Wording otherwise unchanged. Three replicates
  each (2A replicate 3 failed at its opening on a narration leak,
  "workstation", unrelated to A): 25 checks, all answered, about 12 wrong
  "no"s, so no better. Fixed: "park" to Los Angeles park (yes 2 of 2).
  Still wrong: "parking lot" and "park entrance" to the park, "loading
  dock" to the loading docks, "stranger" to Brandon (2 of 3). Newly wrong:
  "server console" to the servers (no in 4 of 4, was yes). Right: every
  person and thing that truly differs ("prisoners" to Brandon, "keycard"
  to the credentials, "ladder" to the service entrance). Jev says no
  whenever the story does not literally show two names are one, which
  points at the evidence-only wording.
  **A, most-likely round (applied).** Only the Jev wording changed:
  "{question} Use story, player and known to decide what is most likely.",
  yes "Most likely, {statement}.", no "Most likely, this is not so:
  {statement}.". Luna, one attempt; suite 892 passed. Three replicates
  each, no failed replicate: 26 checks, all answered, about 22 right.
  Right yes: "park" and "parking lot" to the park, "stranger" to Brandon
  (2 of 2), "loading dock" to the loading docks, "server console" to the
  servers (3 of 3), the corridors, the facility. Right no: "prisoners" to
  Brandon, "below" on Kristin. Wrong: "checkpoint" to Brandon's hideout
  accepted in 2 of 2 (the tracked Kristin was still in the hideout, since
  the cover move had not fired), "below" to the loading docks, and
  "stranger in the park" at the stranger rejected once. Unplaced entries
  fell to 4 (8 with B alone). Next: decide whether the checkpoint case is
  a script problem (turn 4 runs before the cover is ready) or a check
  problem; then 2B.
  **Settled: a bench setup problem (6be66c7).** A bare 2A start lacks
  `facility_infiltration_needed` (set by 1C), so SL-2A-B, the cover, was
  never offered. The 2A variation now uses `"entry_state": "thorough"`.
  Three replicates confirm the cover candidates are offered from turn 1,
  and "checkpoint" no longer maps to the hideout (Kristin is unplaced at
  "checkpoint" at turn 4). But `false_identities_ready` still arrives
  only by the pacing cue at turn 9, because **the narrator selected no
  knowledge candidate in any 1B, 1C or 2A turn: 0 of 147 turns with
  candidates offered**, across the B-only, A and thorough runs. Even 1B
  turn 5, "Compare the number sequence with the transit token.", which
  is exactly k_sl_1b_a_r1, narrated a match and selected nothing. The
  saved 1A run's two "selections" were authored reveals, not candidate
  picks. **Diagnosis:** the narrator has never picked an offered candidate
  in any saved item-facts run (40 runs, 0 picks). Knowledge is earned by
  the authored reveal handoff (PRD: opt-in per candidate, needs
  `action_evidence` and `delivery_text`; the runtime's exact matcher
  decides). Only the seven 1A candidates have them; every candidate from
  1B to 3C has neither, so it falls back to narrator selection, which
  never happens. In 1B-2A, facts arrive only by pacing cues. The fix is
  authoring: `earn_when`, `action_evidence` and `delivery_text` for each
  1B, 1C and 2A candidate, with the prose from ChatGPT Desktop.
  **Done.** ChatGPT Desktop wrote `earn_when`, `action_evidence` and
  `delivery_text` for the 18 candidates (`k_sl_2a_c_r2_rebecca_observes`
  left out: Kristin does not know Rebecca is watching). Brandon approved
  eight evidence edits found by running the real matcher: added verbs
  (study, open, read, pull, build), plurals (infrastructure corridors),
  identification numbers, tire tracks, one merged cooling/ventilation
  group, and `open` removed from 1c_c_r1 to avoid a tie with the
  recording. Ringer, Luna, one attempt; suite 892 passed; the 1A, 1B, 1C,
  2A and 3A payloads are byte-identical. Three replicates each: 1B turn 5
  earned the freight route 3 of 3, turn 7 Brandon's name 2 of 3 (the third
  was rejected by the leak check); 1C turn 12 facility proof and turn 16
  captives alive 3 of 3; 2A turn 1 the hideout files, turn 2 the cover and
  turn 6 corridor access 3 of 3. By 1C's last turns the story has already
  moved to 2A, so the logistics-terminal turn runs in 2A.
  **Open (diagnosed 2026-09-28, see "Narration leak diagnosis"):** the
  narration leak check (`narration_known_term_leak`) rejects
  turns often: 1C "Go up to the logistics terminal." 3 of 3, 2A "Warn the
  supervisor..." in every earlier run, and a 2A opening once ("workstation").
  Two findings from the first replicate are also still open:
  - In 1C the narrator never took Kristin below ground. The reply put her
    at the loading docks for "Climb down into the service level.", and put
    the observation shaft in the loading-dock wall. "service entrance"
    resolved to the service level area, which moved Kristin there on turn
    13 while the narration kept her at the door.
  - The narrator gave fixed things (the servers, the logistics terminal,
    the console) to a person. The world refused each one, as it should.
- **How to ground a scene:** `docs/world-model-grounding.md`, which
  `AGENTS.md` points to. Read it before any package or prompt work.

### Next steps, in order

**1. Ground scenes 1B-3C, one Ringer task per scene.** Use structured YAML
edits in `world.yaml`, `plot.md` and, where needed, `knowledge.yaml`.
New prose goes to ChatGPT Desktop, never to a worker. What each scene needs
is in "Story survey" below, and Brandon's six decisions on it are settled
(listed there). Order:

1. **1B.** The dead drop is the transit token, the handwritten number
   sequence and Michelle's photograph. Decided by Brandon, 2026-09-27:
   all three are entities (`transit_card`, `number_sequence`,
   `michelle_photograph`), and they are **visible**, placed `under` the
   park bench with no text. They are not hidden. The survey's hidden-plus-reveal
   proposal was rejected because the `transport_route_identified` cue tells
   the narrator the drop "lie[s] beside Michelle's photograph" as something
   Kristin notices. worldkeeper refuses a narrated move of a hidden thing,
   so a narrated pickup would have been dropped. No single fact records the
   find either: SL-1B-A sets either `transport_route_identified` or
   `brandon_face_known`. The truck is placed in the park, and the laptop
   and driver's seat ride in it. `brandon_identified` declares W8's
   `{accompany: brandon, with: kristin}`. **Done as 44a99eb.** The 1A and
   1B payloads are byte-identical, and the leakage matrix raised no flag.
   Not yet measured live: add a 1B script to a bench variation and run one
   replicate to confirm the new names resolve.
2. **1C. Done as f1b8d5b** (Ringer, Luna, one attempt).
   `regional_facility` parents the six facility areas and a new
   `freight_terminal` ("freight terminal", alias "abandoned freight
   terminal"), which is 1C's location. `loading_docks` and
   `observation_shaft` are areas inside the terminal, because the entry
   text and 1C.2 put Kristin there, and a character can only be in an area
   or an enterable thing. `logistics_terminal` is a fixed item in the
   terminal, with no bare "terminal" alias. 1C declares
   `companions: [brandon]`. Brandon decided (2026-09-27) that the truck
   drove them there, so `kristin_truck` is placed at the terminal and the
   laptop rides in it. The transit token is not placed, so it stays where
   Kristin left it in 1B.
   One engine change was needed. Narration safety allowed only the scene's
   `location_id`, participants, item_ids and placement parents, so 1C
   narration naming "loading docks" would have been rejected as a leak. It
   now also allows every area above or below the scene's location
   (`_related_area_ids`). The detention level is still rejected in 1C.
   Verified: the full suite (862) passes, ruff is clean, and the 1A, 1B,
   2A and 3A payloads are byte-identical. 1C's opening changes in one line:
   "The scene takes place at freight terminal." Not yet measured live: no
   1C bench script exists.
   **Follow-up, 969d2d7.** 1C's `scene_frames` situation line said Kristin
   and Brandon start "in its lower service level", which spoiled SL-1C-A.
   Brandon chose to start them above ground. ChatGPT Desktop's sentence
   ("...at its loading docks above ground, looking for a way down into its
   service level.") was applied verbatim. `service_level` is a new area in
   the terminal, and `observation_shaft` is inside it. The leakage
   matrix's `_scene_entity_ids` now calls the runtime's
   `_related_area_ids`. Its copy of the allowed set had predated
   f1b8d5b, and flagged "loading docks" in 1C. Verified: the full suite
   (865) passes, and payloads change only by the situation sentence.
   A leftover worktree from the first, correctly stopped attempt is at
   the session scratchpad's `scene-1c-service/run/scene-1c-service-level`;
   remove it with `git worktree remove --force` when convenient.
3. **2A. Done as 6aad57e** (Ringer, Luna, one attempt).
   `brandon_hideout` is a new top-level area ("Brandon's hideout", aliases
   "hideout" and "communications center"). Kristin and Brandon start there
   through `character_placements`; `location_id` stays
   `facility_perimeter`. `hideout_servers` ("servers") is a fixed thing in
   the hideout. 2A declares `companions: [brandon]`.
   Two decisions by Brandon (2026-09-27), made after checking what reads
   `location_id`:
   - **The move fact is `false_identities_ready`, not
     `restricted_corridor_access`.** The latter is the `t_2a_2b` trigger,
     so a move on it would be replaced at once by 2B's placement. The cover
     being ready is the last fact before the facility half. Its `on_assert`
     moves Kristin to `facility_perimeter`, and Brandon follows as her
     companion.
   - **The opening names the protagonist's placement.** `_scene_entry` in
     `cloudflare.py` read `location_id`, so 2A's opening said "The scene
     takes place at Facility perimeter." before the hideout entry text. When
     a scene gives the protagonist a `character_placements` entry, the
     opening now names that parent: "...at Brandon's hideout."
   Narration safety now builds a scene's allowed entities in one helper,
   `NarrationSafetyValidator._scene_entity_ids`. It adds character
   placement parents and their related areas, and the leakage matrix calls
   the same helper, so the two cannot drift. `k_sl_2a_a_r1` lists the
   hideout and the servers in its `entity_ids`.
   Verified: the full suite (870) passes, ruff is clean, and payloads for
   1A, 1B, 1C and 3A are byte-identical. 2A changes only by its opening
   location line. Not yet measured live: no 2A bench script exists.
   **Follow-up, 88ed193** (Ringer, Luna, one attempt; Brandon asked for
   both). `infrastructure_corridors` is an area in `regional_facility`, and
   `inspection_console` is a fixed thing in it. The console is placed in
   2A, 3B and 3C with no text, because 3B.1's Details line names it, and a
   declared item that is not placed would be dropped from the narrator's
   input. `scrutiny_2a` and `cover_review_2a` now also require
   `false_identities_ready`, so they no longer fire in the hideout. A
   runtime test shows scrutiny stays unset for three turns without the
   cover, and is set with it. Verified: the full suite (875) passes, and
   payloads for 1A-3C, 3B and 3C included, are byte-identical.
4. **2B-2C.** Brandon is a companion in 2B and 2C. Fix the areas whose
   text happens elsewhere (2C).
5. **3A-3C.** Michelle is a captive in `detention_level`, and
   `michelle_reached` sets her free. 3B declares `companions: [brandon,
   michelle]`. Rebecca is placed in her office, and `rebecca_captured` sets
   her captive. The senior official is in `detention_level`. Brandon moves
   to the relay by a fact's `on_assert`, and joins 3C's participants there.
   The portable archive gets a new-form placement.

For each scene:

- Before the task, capture the shipped payloads:
  `uv run python .plans/world-model-scenes/capture_scenes.py BEFORE.json
  1A:"Search the kitchen for signs of a struggle." 1B:"Look around the bench
  for anything Michelle left." <scene>:"<a command>"`
- The check re-captures after the change and diffs. A difference fails
  unless it was intended and approved.
- The check runs the whole suite without `-x`, so every failure shows in one
  round. The brief names the tests the change is expected to break. The
  1B-bench task broke the leakage matrix (a new item's name counts as a
  future term until knowledge available earlier lists the item) and two
  fixtures that edited the old front matter.
- Add a script for the scene to a bench variation only when the scene is
  ready to be measured. One live replicate per converted scene confirms that
  its names resolve (read `item_facts_unplaced` and the match-call
  resolutions).

**2. S3: remove what the model makes redundant.** The bigger-place rule
already went in task B. What is left is the start-place rule: one run
without it, and keep the removal only if the numbers hold.

**3. Revisit the bookmark before S4.** Capture is scored only on places and
declared axes. Brandon was not sure undeclared conditions stay unimportant,
such as the truck unlocked or its engine running (see "Bookmarked" in the
S2 record).

**4. S4: runtime.** Capture during play, the tree in saves (a schema bump),
and cause routing, handed to the continuity plan's Phases 4-6. Known gap: the
bench applies seating before the turn, so the runtime must seat inside the
turn's snapshot, so that a rejected turn undoes it.

### Working rules that bit this project

- Every code change is a Ringer task on GPT-5.6 Luna (`"engine": "codex",
  "model": "gpt-5.6-luna"`). Claude writes the brief and the check, and
  reviews the patch.
- `worktrees: true` detaches each task at the repository's HEAD. Commit
  earlier rounds to a work branch before the next round. The check exports a
  cumulative patch (`git diff --cached <base>`), because a passing
  worktree is deleted.
- A check that runs the full suite needs `"check_timeout_s": 900`.
- Write manifests from a quoted heredoc (`<<'EOF'`). An unquoted one runs
  the backticks in a brief as shell commands.
- A worker may call failures "pre-existing". Verify that against the base
  commit before accepting it.
- Live bench and judge runs go through Ringer too. The check sources
  `.env`, because a worker has no network. Re-score with
  `bench/calibration/rejudge.py`. The saved S2 runs and comparison scripts
  are in the main checkout's gitignored `bench/results/` (listed in the S2
  record).

## S2 record (2026-09-26 to 2026-09-27)

Branch `world-model-s2b` (merged as PR 485) held everything after PR 481,
oldest first:

- 17437be: task B, the reply names the parent.
- 77c0240: task D, seats (W11). c06ee38, 7989583, c7705b8: fixes from
  the first seat smokes.
- ea59876: task E, seating before use (W12). 795580d: Jev answers a
  probability; a yes is `noul > 0.5`.
- d08defa: bench `item_facts.drop_rules`. 09e1d98: the two upright
  narrator rules and the 1A setting fact "The workstation chair is
  overturned." removed.
- b2a827f: task F. The new "use" question, standing up before leaving a
  seat (W13), a kind may declare `fixed`, and `seat` is movable
  furniture.
- 9210622: task G. The engine's steps reach the narrator as "Just before
  this: ..."; the stay-seated rule; a seat placed at its own furniture
  does not move; "overturned workstation chair" out of the 1A Details
  line.
- c29c2f7: task H. Kristin and Michelle are friends; the house is
  "Michelle's house"; a fixed back door in the kitchen. 35d490f: the
  entry text says "late-night shift", and Kristin "arrives at" the house.
- 7ea8c2b: Brandon is placed in the 1B park; script turn 10 fixed.
  79eeaa9: learned names (`add_alias`). 82b9c22 and d22a221: task I, the
  driver's seat and the pick-up step.

The full suite passes and ruff is clean at d22a221. The shipped
narrator's 1A baseline (`.plans/world-model-s1/narrator-1a-baseline.json`)
matches the code. The results of every smoke are recorded under tasks E,
F and G in section 11.

The Ringer manifests, checks and smoke variations lived in a session
scratchpad and are gone. To rebuild the W13 stand smoke: take
`item-facts-world-two-scene`'s item_facts and overrides, place the laptop
`{parent: michelle_workstation, text: on Michelle's workstation}`, set
`fixed_turns: 6`, turn both judges off, and use two 1A scripts:

- `stand-overturned`: "Read the files on my laptop.", "Open the
  drawer.", "Go out to the truck.", "Go back into the kitchen.", "Read
  the files on my laptop.", "Pick up Michelle's phone from the kitchen
  floor."
- `stand-upright`: "Set the workstation chair upright.", "Type a note on
  my laptop.", "Close my laptop.", "Walk to the back door.", "Search my
  laptop for Michelle's notes.", "Pick up the workstation chair and carry
  it out to the truck."

### Task H done: friends, not roommates (c29c2f7)

Brandon decided on 2026-09-26 to simplify the fiction so that place names
resolve. Kristin and Michelle are longtime friends, and Kristin does not
live in the house. The stand smoke's replies had named the house
"Michelle's home" or "inside the house". None of those names resolved, so
Kristin ended up outside every area.

- The story lines came from ChatGPT Desktop and were applied verbatim.
  Brandon then kept ChatGPT's "late-night shift" in the entry text and had
  the 1A plot line say that Kristin "arrives at" Michelle's house.
- The saved prompt missed four lines, which were found by a sweep and
  included: `storylet-routes.yaml` 73, 147 and 495, and `plot.md` 223
  ("tracked from her house").
- `mcgehee_home` is now named `Michelle's house`, with the aliases
  `Michelle's home` and `the house`.
- The back door is a fixed item in the kitchen, placed in 1A with no text.
  A reply that puts Kristin at the back door leaves her in the kitchen.
- The shipped 1A baseline changed only in the scene line, the two bios and
  the entry text's drive clause.
- Ringer passed on the first attempt on Luna. The full suite passes, and
  ruff is clean.

### S2: the two-scene smoke replicate

One replicate of `bench/variations/item-facts-world-two-scene.json` with
the fact and continuity judges, for a few cents. It answers W5's two
questions at the 92% bar (Brandon, 2026-09-26):

- at least 92% of turns where a thing's place is Kristin are judged
  consistent;
- at least 92% of reported places resolve (`item_facts_unplaced`).

One replicate near the bar means another replicate, not a decision.
Seating stays on: opening the laptop is not use, so turn 6 ("Open my
laptop.") adds nothing, and turn 13 happens at the truck, where there is
no seat.

Also watch the empty condition. After "Set the workstation chair
upright.", the reply gave the chair an empty condition in 2 of 3 runs of
the task G stand smoke (0 of 3 before it), so the chair stayed
overturned. Turn 7 ("Stand the overturned chair back up.") and the
drawer turns test it. If it recurs, the fix is a rule that replaces the
existing condition sentence rather than adding one: `For "condition",
give the new state in one or two words, like "open" or "upright".`

Accepted, not fixed (Brandon, 2026-09-26): the narrator may stand
Kristin up for "Open the drawer." despite the stay-seated rule (3 of 3).
The reply now records it, so the world and the story agree.

Result, first replicate (2026-09-26, at 35d490f): the run completed with
19 accepted turns and no failed replicate.

- **Places resolve: 41 of 43 (95%), which meets the bar.** Both misses
  are from turn 16 of 1B, "Walk over to the man watching me and hand him
  Michelle's phone.". The reply put Kristin and the phone at "stranger",
  and the match call mapped "stranger" to "man". Brandon has no name
  Kristin could know him by yet, so neither name resolved.
- **Held things: 11 or 12 of 15 turns (73-80%), below the bar.** Every
  place probe the fact judge ran on a held thing agreed with the tracked
  place, 14 of 14. The failures come from two causes that are not the
  label:
  - Turn 10 of the script, "Take Michelle's phone out and throw it hard
    against the kitchen wall.", runs after turn 9 has sent Kristin out to
    the truck. The narration threw the phone from outside. The reply kept
    the phone with Kristin, and turns 10 and 11 conflict.
  - Turn 18 follows on from the turn 16 miss. The handed-over phone was
    left unplaced, and turn 17's reply put it back with Kristin.
  A per-turn "all facts right" measure scored 6 of 15. It counts faults
  in other things, so it does not measure this question.
- **Empty condition: no repeat.** Turn 7's chair reply was `["upright"]`.
- Seen, but not measured: at turn 13 the narrator drove Kristin "back to
  her house, where her laptop is", which is the old shared-home idea.

Fixes after replicate 1 (7ea8c2b), both approved by Brandon: script turn
10 now reads "Go back into the kitchen and throw Michelle's phone hard
against the wall.". Scene 1B places Brandon "across the park from
Kristin", and the bench match call shows a placed character's place. No
alias was added, because narration safety scans aliases, so a "stranger"
alias would reject narration in scenes where Brandon is not allowed. A
"known as" label was considered and dropped, because the 1B narrator
prompt already names Brandon.

Result, second replicate (2026-09-26, at 7ea8c2b): the run completed with
19 accepted turns.

- **Places resolve: 50 of 52 (96%).** The two misses: at turn 7 Kristin
  was placed "at Michelle's workstation", which copies the chair's
  authored text and is a phrase, not a name. At turn 13 the truck was
  placed at "driveway", which is not in the world.
- **Held things: 15 of 15 place probes agree.** Every per-thing place
  probe on a held thing agreed with the tracked place (lowest 0.53). The
  handoff now lands: at turn 16 the match call mapped "stranger in the
  park" to Brandon, the phone was tracked with Brandon through turn 17,
  and it came back to Kristin at turn 18. The one held-thing conflict, at
  turn 18, is the judge reading the place "Brandon" against narration
  that calls him "the stranger". The judge does not know they are the
  same person.
- **The per-turn "all facts right" measure: 11 of 19.** This is the
  capture accuracy that the v36 comparison measures, not W5.
- **Empty condition: no repeat** (the turn 7 chair reply was `["upright"]`).
- Seen in both replicates: at turn 13 ("Read the files on Michelle's
  memory card with my laptop.") the narrator drives Kristin "back to her
  house". At turn 17 the reply listed 1B Details nouns as things, which
  created "stranger in the park" as a second entity alongside Brandon.

Verdict on W5: both questions pass. The bare parent name reads as held,
and replies use names, not phrases. No `Held by:` fallback is needed.

Follow-ups on the two issues above (Brandon, 2026-09-26):

- **Duplicate entity: fixed (79eeaa9).** The engine did not remember a
  name the match call had resolved. worldkeeper's `add_alias` now stores a
  learned name as a `wk_alias` fact, and the bench learns every name the
  match call maps to a thing or character. It never learns a name mapped
  to an area, so "floor" does not become a name for the kitchen. Replaying
  live turns 16 and 17 now resolves "stranger in the park" to Brandon.
- **Turn 13's drive: probed live, 10 calls per version, on the
  replicate 2 prompt.**

  | Version | Drives off | "Her house" | Reads at once |
  |---|---|---|---|
  | A: as recorded | 10 | 10 | 0 |
  | B: without "Write only what leads up to it." | 10 | 10 | 0 |
  | C: B, also without the reveal line | 10 | 3 | 0 |
  | D: engine step, seated in the driver's seat | 1 | 1 | about 3 |
  | E: D without the reveal line | 2 | 0 | about 1 |
  | F: D, and the engine hands her the laptop | 0 | 0 | 10 |

  The two prompt lines are not the cause. The narrator ignores where
  Kristin already is and invents a trip home. In D, 6 of 10 narrations had
  Kristin walk round to fetch the laptop before reading. Engine steps fix
  the turn, in line with the rule that the engine performs a command's
  prerequisite steps. The build is task I.
- **Task I (Brandon approved, 2026-09-26):**
  - The truck gets a fixed `driver's seat`.
  - Items may declare an authored `take_text`, and the laptop's is
    "Kristin picked up her laptop."
  - The seating step treats "already seated" as having a seat as parent,
    not merely an enterable parent, so being inside the truck no longer
    counts.
  - It prefers the seat next to the thing being used.
  - It hands the protagonist the thing, saying its `take_text`, unless she
    already holds it or it rests on a supporter.
  - The task also fixes `add_alias`, which called the host's resolver
    callback when checking for a conflicting name.

Task I was built as 82b9c22. The third replicate found a hole: the
narrator had left the laptop on the driver's seat, and a seat is a
supporter, so the engine skipped the pick-up. d22a221 fixes it. A thing
is now used in place only when it rests on the furniture its seat serves
(`seat_for`).

Results of replicates 3 and 4 (2026-09-26), each with 19 accepted turns:

- **Places resolve: 40 of 40, then 41 of 41.**
- **Turn 13, in replicate 4:** the engine seated Kristin and handed her
  the laptop. The narration reads the card at once, with no drive and no
  "her house".
- **The phone handoff:** "stranger" resolves to Brandon, and the phone
  stays tracked with him through turn 18.
- **Fact judge, per turn, all facts right:** 10, 11, 13 and then 14 of 19
  over replicates 1 to 4.
- **Continuity judge, replicate 4:** 0 contradictions and 0 scene
  restarts.
- **Judge noise left over:**
  - At turn 13 the judge counts the engine's seating move as a start
    conflict, because the narration does not show her sitting down.
  - At turn 18 it scores "Brandon" against narration that says "the
    stranger".

The v36 comparison, first pass (2026-09-26):

- **Before comparing, the bench's measurement was fixed (f0f58a4).**
  - The before-state is now read after the engine's seating steps and
    before the turn. It used to be read after the turn, so a
    scene-leaving turn was scored with Kristin already in 1B.
  - Both judges now receive `also_called`, each thing's other names.
  - `rejudge.py` re-scores any saved results folder.
- **v36's 2 saved replicates, re-scored with the current judges:** almost
  unchanged, 28 of 38 turns with every fact right.
- **Current branch at f0f58a4:** 4 single-replicate Ringer tasks.
- **Script turn 10 is left out of both arms,** because the script changed
  there.

| Measure (per-thing judge answers) | v36 (n=2) | Branch (n=4) |
|---|---|---|
| Place changes captured | 18/25 (72%) | 42/48 (88%) |
| Condition changes captured | 6/10 (60%) | 16/31 (52%) |
| Turns with every fact right | 26/36 (72%) | 43/69 (62%) |

- **Turns 4, 6, 12 and 13 fail in all 4 replicates.**
  - **Turns 4 and 12 are real capture misses.** The narrator unlocks the
    truck or starts its engine on its own, and the reply does not
    report it.
  - **Turn 6 is a measurement artifact.** The card's place label changes
    from the authored "with Kristin" to the bare "Kristin" when Kristin
    moves, and the judge scores that as an invented change. v36's store
    never changed labels, so this hurts only the branch arm. It cost 3
    turns.
  - **Turn 13:** the narrator reopens a laptop that is already open.

Why condition changes are missed (2026-09-27, the 4 comparison
replicates): 16 of 31 condition changes the judge saw were captured. The
engine lost no condition that a reply reported; every miss is a reply
that never reported the change.

- **8 misses: the truck.** The narrator itself unlocked the truck (turn
  4) or started its engine (turn 12). The truck has no declared state, so
  nothing in THINGS asks for it.
- **4 misses: turn 13.** The narrator re-opens a laptop that is already
  open. The hypothesis is that `open (or closed)` reads as "either" to the
  8b model; a probe is running.
- **3 misses: other small cases.**
- **An engine gap, found in replicate 3.** When the narrator had already
  seated Kristin, the seating step returned early and skipped the laptop
  pick-up. The fix is running as a Ringer task.

**Bookmarked (Brandon, 2026-09-27, "for now").** Capture is scored only
on places and declared state axes. Changes to undeclared conditions that
the narrator makes on its own, such as the truck unlocked or its engine
running, do not count as misses. Brandon is not convinced this will stay
unimportant, so revisit it before S4 (runtime capture). The alternative
is declaring more axes so that THINGS gives the narrator something to
report against.

Built after that analysis (2026-09-27):

- **7815dd3: judge records use structural parents.** The narrator keeps
  its authored labels, so "with Kristin" becoming "Kristin" is no longer
  scored as a change.
- **b82761f: the pick-up also runs when Kristin is already seated.**
- **The turn 13 condition-hint probe:** the narrator writes "opens her
  laptop" 10 of 10 times with both `open (or closed)` and `open`. The
  rendering is not the cause, so it was not changed.
- **e7873af: condition capture is scored only on declared axes** (the
  bookmark above). Records carry `item_facts_axes`, and old records get
  theirs from the package through `rejudge --variation`. The fact judge
  asks no condition question for a thing without axes. It names `states`
  for a thing with axes, and it says that a state the thing already has
  did not change.

**Next:**
- Re-score v36 with `rejudge` (judge calls only).
- Run fresh replicates of the branch. The four comparison replicates
  predate these fixes, so they cannot be re-scored.

The v36 comparison, second pass (2026-09-27): v36 re-scored with the
fixed judges; 4 fresh replicates of the branch at dd01cdf. Turn 10 is left
out of both arms.

| Measure | v36 (n=2) | Branch (n=4) |
|---|---|---|
| Place changes captured | 17/26 (65%) | 40/46 (87%) |
| Condition changes captured (declared axes) | 6/8 (75%) | 15/16 (94%) |
| Turns with every fact right | 26/36 (72%) | 47/68 (69%) |

Both capture categories beat v36, which meets the S2 exit criterion. The
turn-level measure is held down by judge logic faults that the
per-change-type counts are not exposed to:

- **Turn 4, a round trip.** Kristin goes out to the truck and comes
  back, so her end place equals her start place. The judge's "moved"
  answer then scores it as a missed change.
- **Turn 6, a refinement.** "Michelle's house" becomes "kitchen" when she
  walks to the workstation. The judge scores the kitchen as the wrong
  after-place, although it is a more specific place inside the given one.
- **Turn 13, engine steps in the command.** The judge receives the
  command with the engine's steps glued on ("Kristin sat down in the
  driver's seat. …"), so it thinks she moved.
- **Turn 12, pocket to hand.** Taking the phone out of her pocket counts
  as a move, although its holder does not change.
- **Turn 8, a walk inside the room.** Crossing the kitchen to the
  workstation is scored as a start conflict.

One real narrator fault: in replicate 1 at turn 12 the narrator never
walked Kristin to the truck, and turn 13 derailed after it.

**Decided (Brandon, 2026-09-27): fix the five judge faults first, then
open the PR.** The faults were poorly phrased questions: they asked about
events during the turn, while scoring needs where a thing started and
where it ended. Built as 2302ef6 (three Ringer rounds on Luna):

- Round trip: the protagonist's move question asks whether she ends the
  turn in a different room or area from where she started.
- Refinement: `judge_input` builds `place_contents` from the package and
  the tracked places, at any depth, and the judge gets
  `after_place_contains`. The plan's first idea, skipping "moved" when
  the tracked end place equals the start, was dropped: it grades the
  tracked places with themselves.
- Command text: the judge gets the typed command, the engine's steps as
  `just_before`, and `narrator_narration`. Move questions are answered
  from the narrator's own text. A probe on turn 13 (replicates 2-4) found
  the cause was the story's ending sentence ("heads for the park"), not
  the steps: "moved" was 0.69 as recorded, 0.07 without the story text,
  and 0.90 without the steps.
- Holder unchanged: anywhere on the holder, such as a hand, a pocket or
  a bag, is the same place. No pocket part was added to the world model;
  the judge reads prose, so the question had to change.
- In-room walk: the protagonist's start question asks whether she
  started outside `before_place`.

Re-scored with the fixed fact judge only (the continuity judge did not
change), turn 10 excluded:

| Measure | v36 (n=2) | Branch (n=4) |
|---|---|---|
| Place changes captured | 18/24 (75%) | 38/40 (95%) |
| Condition changes captured (declared axes) | 6/10 (60%) | 15/16 (94%) |
| Turns with every fact right | 26/36 (72%) | 61/68 (90%) |

Turns 4, 8, 12 and 13 now pass in every replicate. Of the 7 remaining
failed turns, 2 are one real engine fault: at turn 15 in replicates 3
and 4 the reply put Kristin at "bench" in the 1B park, the park has no
bench entity, and the name resolved to the 1A workstation chair (by the
match call in replicate 3, by a learned name in replicate 4). The match
call should not resolve to a thing in another scene's area, and 1B may
need the bench declared. Fixed as b1a1a35 (Brandon chose both, 2026-09-27): the bench is declared
as a fixed seat placed in the 1B park, and the match call lists only things
in play (the scene's `item_ids`, things in the protagonist's top-level area,
and things she carries). The 1A card knowledge that names "a bench in the
park" lists the bench, or the leakage matrix counts "bench" as a future term
in 1A. One live replicate (`bench/results/item-facts-s2-t15-verify`, 19
turns) kept Kristin in the Los Angeles park through all of 1B. That reply
tracked the park bench as a thing in the park rather than placing Kristin at
it, so the "bench as her place" path is covered only by the deterministic
test that "bench" resolves to the park bench.

### Story survey: places, things and NPCs (2026-09-27)

Brandon asked for a survey of the whole story for concerns like turn 15's,
with NPCs placed the way 1B places Brandon (`character_placements`, which
works live: "stranger in the park" resolved to Brandon and the phone handoff
landed). The general rule and checklist are now in
`docs/world-model-grounding.md`. Only 1A and 1B are converted today. Every
later scene has no placements at all, so every item below is a gap, not a
regression. Story changes start in `plot.md` and follow Brandon's decisions;
prose goes to ChatGPT Desktop.

**Places: the scene's area is not where its text happens.**

- 2A: `location_id` is `facility_perimeter`, but the entry text, Setting and
  beats are in Brandon's hideout, a dead communications center. There is no
  hideout area.
- 2C: `purge_chamber`, but the Setting is "command levels and detention
  sectors", and no text mentions a purge chamber.
- 3C: `facility_escape`, but the entry text is in the broadcast chamber, and
  the Setting starts in Rebecca's office.
- 1C: `regional_facility`, but the text is a freight terminal with loading
  docks and an observation shaft.
- Named sub-places with no area: Rebecca's executive office (3B, 3C), the
  relay chamber (3B), the medical level (2B, 3A), the records archive's
  terminals (2B), the service entrance and maintenance routes (1C, 3C).
- No shared parent: the seven facility areas are all top-level. The match
  call's scope and `together()` treat them as unrelated worlds. Proposed: one
  facility area as their parent, which is a plot.md decision.

**Things: named by the story, never declared or placed.**

- 1B dead drop: the handoff cue has "a transit token and a handwritten number
  sequence ... beside Michelle's photograph". `transit_card` is in 1B-2A
  `item_ids` but is never placed. The number sequence and the photograph are
  not entities. The drop should get the card's treatment: hidden at the bench,
  then moved to Kristin and revealed by the fact that records finding it. In
  replicate 3 the narrator already invented "tape under the bench".
- The truck and laptop are left at Michelle's house forever. The 1A bridge
  drives Kristin to the park, but the truck is never placed in 1B. "Get in my
  truck" in 1B would resolve to the truck at the house. The laptop has the
  same problem wherever the story expects Kristin to have it.
- `override_codes` (3A) and `portable_archive` (3C) have no new-form
  placement. The archive still uses the old string placement "with Rebecca in
  her hands", so it has no world parent.
- 1A: the tablet and work bag are "missing" (section 4.3) but are not tracked.
  The drawer's contents are still a setting-fact sentence (W9 asks for
  `contents:`).

**NPCs: presence, companions and captivity.**

- Brandon is the only placed NPC (1B). From 1C on he travels with Kristin (1B
  bridge: "Kristin and Brandon headed for the freight terminal"). W8's
  `companions: [brandon]` and the `brandon_identified` `accompany` effect were
  never declared, so from 1C Brandon stays tracked in the park.
- 2B: the Setting says "Brandon's hideout through a remote connection".
  Decide whether Brandon is in the archive with Kristin or remote. If remote,
  he is not placed, and he is not a companion in 2B.
- 3C: Brandon holds the relay open ("Brandon's relay held open") and is not a
  participant. He should be placed at the relay, not travel with Kristin.
- Michelle is a participant in 1A-2C while missing or captive, which is
  correct because presence is not participation. She needs a placement from
  3A in the detention level, as a captive. `michelle_reached` should declare
  her `free` and, if the plot says so, `accompany` Kristin.
- Senior official (3A): a participant with no placement. He is a prisoner in
  the detention level.
- Rebecca: a participant in 3B and 3C with no placement (her office).
  `rebecca_captured` should `set_axis` her captive (W7 already names this
  effect). She is also the parent the portable archive needs.
- Charles is never a participant. He is only heard (1C "recorded conference",
  3A "Charles's broadcast"), except 3B's Details "Charles appears". Decide
  whether 3B has him in person. If so, he needs participation and a
  placement.
- Characters listed in a scene's **Characters** section but not in
  `participant_ids`: Charles and Rebecca in 1C, 2B, 2C and 3B, and Brandon in
  3C. Most are heard, not present. Each one is a plot.md decision.

**Decided (Brandon, 2026-09-27), after checking each question against the
text:**

1. **The facility is one area tree.** `regional_facility` becomes the parent
   of `facility_perimeter`, `janus_archive`, `purge_chamber`,
   `detention_level`, `broadcast_relay` and `facility_escape`. A new
   `freight_terminal` area inside it is 1C's location. The knowledge entries
   that already reference `regional_facility` then mean the whole
   installation. No "the facility" alias is added until a leakage check shows
   it is safe, because 1A and 1B narration may use the word first.
2. **2A starts in Brandon's hideout.** Add a `brandon_hideout` area, "Brandon's
   hideout". Kristin and Brandon get 2A `character_placements` there. The
   story fact set on entering the facility (2A.3) declares an `on_assert`
   move of Kristin to `facility_perimeter`, and Brandon follows as her
   companion. `location_id` stays `facility_perimeter`. The 2A task must first
   check what else reads `location_id`.
3. **Brandon is present in 2B** and travels as Kristin's companion. The
   Setting line's "remote connection" is his network, not his location.
4. **Charles is never placed.** Every appearance is remote: surveillance
   footage in 1C, orders in 2C, "appears remotely" in 3B, and a remote command
   site in 3C.
5. **Michelle** is placed in `detention_level` in 3A as a captive.
   `michelle_reached` sets her free. She travels with Kristin **from 3B on**,
   not from the moment she is reached: 3B declares
   `companions: [brandon, michelle]`, and no `accompany` effect is added in 3A.
6. **Characters listed but not participants:** Charles and Rebecca stay
   unplaced in 1C, 2B and 2C (footage, private contact, orders). In 3C,
   Brandon joins `participant_ids` and is placed at the relay, not as a
   companion. In 3B his move to the relay is a fact's `on_assert` move.

**Proposed order.** Scene by scene, as each one enters a bench script:

1. 1B: the dead drop and the truck's 1B place.
2. 1C: Brandon as a companion, and the terminal areas.
3. 2A-2C: the hideout, the areas' shared parent, and Brandon in 2B.
4. 3A-3C: the NPC placements, captivity effects, the offices and the relay,
   and the archive's new-form placement.

Each scene is one Ringer task of structured YAML edits. The shipped
narrator's payloads for converted scenes are guarded by a stubbed capture, as
1A and 1B are.

The saved second-pass runs are in the main checkout's `bench/results/`,
which is gitignored and so exists only on this machine:

- `item-facts-s2-world-two-scene-rep1` to `-rep4`: the branch replicates.
- `item-facts-v36-rescore-s2`: v36 re-scored with the fixed judges.
- `item-facts-s2-rescore-judgefix-rep1` to `-rep4` and
  `item-facts-v36-rescore-judgefix`: fact judge re-scored at 2302ef6.
- `item-facts-s2-comparison-tools`: the scripts. `compare.py` computes
  capture per change type, with turn 10 excluded:
  `compare.py V36_RAW -- REP_RAW... --exclude-turns 10`. The raw inputs
  are each folder's `jev-raw.json` or `fact-tracking-jev-raw.json`.
  `analyze.py` computes the W5 metrics for one results folder, and
  `score.py` aggregates re-scored judgments.

To re-score a folder: `uv run python bench/calibration/rejudge.py
--results bench/results/<folder> --out <new folder>`.

### S1 record

Branch `world-model-s1` held all of S1 on top of main after PR 479:

- task 2: bd8c46b and 529b6a0;
- task 3: 515201e and cf31bd2;
- task 4: 89b1eea and 54541e9;
- the exit gaps: 2c546cb and the round 2 commit after it;
- d498b9d: ruff formatting of the `.plans/` scripts.

The full suite is green (747 tests, 92.84% coverage), and ruff is clean across
the whole repository. The shipped narrator's 1A payloads are still
byte-identical to the pre-S1 baseline. S1 merged as PR 480.

The S1 exit is met:

- `tests/test_world_second_package.py` runs the section 10 storygame checks
  over continuity-initiative and a synthetic second package,
  `tests/fixtures/stories/lighthouse-keeper/`. The second package loaded
  zero-shot apart from one general loader fix: a delivery's own fact now
  counts as set in its scene, as the engine sets it.
- The whole tree survives SQLite save and load, snapshot and restore, and a
  `FactStore` clone. A created thing keeps its minted ID and is still found by
  name.
- `MemoryBackend` and `FactStore` give the same world.
- The protagonist starts each scene in the scene's `location_id`, and a scene
  change carries what she holds. A refusal is logged like any other
  placement.

Left for S2: W8's `companions` and `character_placements` front-matter
fields. S1's task list never scheduled them. Also left for S2 is the
`together()` question below.

What S1 left in place, for S2 to build on:

- **Package fields.** `world.yaml` declares `kinds` (typed `KindDeclaration`), a
  location `parent`, and item `kind`, `openable`, `open`, `hidden`,
  `contents` and `owner`. `Item.fixed` is `None` unless declared, and
  `WorldSchema.is_fixed` and `WorldSchema.kind_is` decide it.
- **Placements.** Scene 1A uses only the `{parent, text?, under?,
  part_of?}` form. The other scenes still use strings. `apply_scene_placements`
  runs at bootstrap and on a scene change. The loader simulates every scene's
  new-form placements and rejects bad ones.
- **The found card.** `memory_card_in_kristins_custody` is now
  `memory_card_recovered` everywhere outside `.plans/`. Its `on_assert` is
  `{move: memory_card, parent: kristin, text: with Kristin}` plus
  `{reveal: memory_card}`. The card starts hidden `under` the drawer.
- **Text on a move effect.** A move effect may carry `text`, which becomes the
  thing's authored place text until it or its holder moves
  (`World.place_text`). This was added in task 4 so the narrator still says
  "Michelle's memory card is with Kristin." once the card is found.
- **The shipped narrator reads a world view.**
  `CloudflareTurnProvider._placement_world()` clones `_placement_facts()`,
  applies world effects and wraps the result in a world. It is built once
  per rule call. The narrator leaves out things the world says are hidden.
  A new-form placement's line comes from `place_text`. Owner and placement
  rules cover only things with narrator text, so the truck and the
  workstation get no line.
- **The workstation's name.** The item is named `workstation` with `owner:
  michelle`, in the same way as the `drawer`. As `Michelle's workstation` it
  made the audit flag the beat detail "overturned workstation chair"
  (`test_real_package_has_no_ambiguous_owned_item`).
- **Bench and judge.** The bench seed skips hidden things and seeds the card
  (`with Kristin`) once the world reveals it. The judge treats a thing that a
  handoff's fact reveals through `on_assert` as revealed.

Materials in [world-model-s1/](world-model-s1/):

- `prompt_capture.py` records the shipped narrator's 1A payloads with the
  network stubbed: the opening plus the turn "Search the kitchen for signs of
  a struggle.", each with and without the found fact. It applies world effects
  after setting the fact, as every commit point does. Its default fact is
  `memory_card_recovered`. Run it from the repository root: `uv run python
  .plans/world-model-s1/prompt_capture.py OUT.json`.
- `narrator-1a-baseline.json` is its output from before S1, and the capture
  still matches it after task 4. S2 changes the narrator on the bench only,
  so the shipped narrator must keep matching it until S4.
- `s1t3_acceptance_draft.py` is task 3's acceptance test, which built the 1A
  conversion in a temp copy.
- `s1t2_check_example.sh` is the task 2 check. Reuse its structure:
  ownership, library boundary, acceptance, full suite, mutation checks,
  ruff, patch export. Grep only `*.py` files (`--include="*.py"`), because a
  bare `grep -r` matches `__pycache__`. Run acceptance tests with
  `PYTHONPATH=packages/worldkeeper/src:.` plus the acceptance directory, or
  `bench` does not import.

Lessons from task 2, for writing the next checks:

- Enforce the required tests in the check. Round 1 skipped them because only
  the spec asked for them. Mutation checks work.
- Scope a layering rule to the new code. A blanket rule ("story_package
  never imports runtime") pushed the worker to rewrite
  `_validate_narration_term_traps`, and that rewrite was dropped at
  integration.
- `uv sync` makes `packages/worldkeeper/src/worldkeeper.egg-info/`, which is
  now ignored. Run `uv lock` and `uv sync` yourself after a pyproject change;
  workers have no network.

`together()` (decided by Brandon, 2026-09-25): `World.area()` returns the
nearest area, so a phone in the kitchen and Kristin in the house were not
`together()`. Two entities are now together when one's area is the other's
area or contains it: Kristin in the house is together with the phone in the
kitchen, but two sibling rooms of the house are not together. Rejected:
comparing the top-level area, which would make every room of the house one
place. This library change rides with S2 task C.

This plan is self-contained so it can be picked up in a new chat with no
other context. The continuity plan's principles (its section 2) and working
rules (its section 3) apply here unchanged: every code change is a Ringer task
on GPT-5.6 Luna, and narrator strings are written at an 8th-grade reading level.

## Contents

1. Why a separate plan
2. What we take from world-model practice
3. Scope: the questions the model answers
4. The model
5. Operations and rules
6. What the narrator reads
7. Capture: from the narrator's reply to operations
8. Authoring
9. How the existing mechanisms map onto the model
10. Checks
11. Phases
12. Decisions for Brandon

---

## 1. Why a separate plan

The engine has a representation of the world but almost no model of how it
changes. On the bench (`bench/item_facts.py`) a tracked thing is a `place`
phrase of up to 80 characters plus up to two `condition` phrases. The narrator
effectively decides what every action does, and the engine works backwards
from the reply's phrases.

Each defect since round 3 has added one mechanism to that representation:

- binary state axes with aliases (decision 1a, round 4);
- the `fixed` flag on furniture, which refuses a place change;
- seeding the protagonist as a tracked thing in the scene's location
  (`_seed_protagonist`), and giving her line every turn (v30);
- the start-place rule and the "bigger place" rule for the protagonist's
  moves (v31, v33);
- the name-match call, which today runs only for names not already tracked;
- lifting reply entries the narrator put outside `item_facts`.

Each one is sound on its own terms. Together they are a world model built one
defect at a time, with no statement of what the world is. The symptom that
triggered this plan: the laptop was recorded "in her hand" with no record of
whether Kristin was at the truck or in the house. Container-shaped replies
such as `{"kitchen counter": {"contents": ["Michelle's phone"]}}` are still
dropped, because nothing in the representation can hold them.

There is also a structural conflict with the PRD. The PRD says facts are the
only durable truth, and the runtime's `FactStore` holds
`(predicate, subject, object, value)` facts. The bench's `item_facts` dict is
a second, separate store of truth. The runtime build must not copy it.

## 2. What we take from world-model practice

Source: Nate B. Jones, "Inside NVIDIA: What a world model actually is"
(an interview with Ming-Yu Liu of NVIDIA's Cosmos Lab, September 2026).
The article is about learned neural world models for robots and video. We
take its architecture, not its technique. Nothing here is learned or neural.

1. **Keep the world model separate from what acts on it.** The article traces
   this to Ha and Schmidhuber (2018): one part represents the environment and
   predicts how actions change it; a separate part chooses what to do.
   Producing a convincing outcome is not the same as modelling one. For us the
   narrator is the generator. The engine's model owns what an action does to
   the world. The narrator proposes; the model's rules decide what is legal and
   what follows from it. This is the PRD's "LLM-proposal-first" rule, applied to
   things and places.
2. **Scope the model to the job.** A model needs a useful representation of
   the part of the world the task depends on, not all of it. Section 3 writes
   our scope down, and anything outside it is out of the model.
3. **An observation can show a change without the action that caused it.**
   The narrator's reply reports end states ("the phone is on the counter"), not
   actions. Capture therefore turns an observed end state into an operation,
   and the model must derive the effects the reply did not state, such as
   everything Kristin carries moving with her.
4. **A symbolic simulator and a learned generator do different jobs.** The
   article describes a physics engine used alongside a learned model. Ours is
   a deterministic symbolic world with the LLM on top.
5. **A check proves only what it covers.** The article's example is a garment
   folded into the right shape but put in the wrong drawer. A place phrase can
   read correctly while the tree behind it is wrong, so checks in section 10
   test the tree, not the phrase.

The shape of the model borrows from interactive fiction's standard world model
(Inform 7): an object tree with typed relations, kinds that carry properties,
and rules that check and carry out actions. That model has been proven over
decades of parser games. Our difference is only where changes come from:
narrated prose rather than a parser.

## 3. Scope: the questions the model answers

The model must answer these, for any story package, every turn:

1. **Where is X?** Its immediate parent, and the chain up to a top-level area.
2. **Who has X?** Whether a character carries it, directly or inside
   something she carries.
3. **Are X and Y together?** Whether they share an area.
4. **What state is X in?** Its value on each declared axis, plus free
   condition phrases.
5. **Can X change like that?** Whether it can move, open or be carried.
6. **Can the player see X?** Whether X is hidden, for example inside a closed
   container or not yet revealed.
7. **Does the story still work?** Whether a thing a future transition needs is
   still available. The existing dependency analysis answers this; the model
   only has to feed it.
8. **Whose is X?** Its owner, which is not where it is. Kristin can hold
   Michelle's phone. The owner is how the narrator names a thing at first
   mention, and how "my laptop" or "her phone" resolves.
9. **Who goes where Kristin goes?** Which characters travel with the player
   character, so that moving her moves them.

Out of scope: force, weight, size, exact position within a parent ("near the
door"), time, and routes between areas. Detail like "face down" or "near the
door" may be kept as a condition phrase, but nothing reasons over it.

Also out of scope, because other parts of the package already model them:

- **Who knows what.** `knowledge.yaml` entries carry an `audience` (public,
  world-only, or named characters) and `entity_ids`. The world model does not
  duplicate this.
- **What a thing tells you.** The memory card's files, the photograph showing
  Michelle with Brandon, and the transit token's number sequence are
  knowledge attached to things through `entity_ids` and deliveries, not
  physical relations.
- **Access between areas.** Sealed exits, sealed detention sectors, a locked
  office and a maintenance route are story facts moved by storylets and
  pacing (`relay_open`, `evacuation_route_open`, `restricted_corridor_access`).
  A map with blocked connections would duplicate them.

These scope choices come from reading every file in
`data/stories/continuity-initiative/`. Section 4.6 lists what that reading
found.

## 4. The model

### 4.1 Entities and kinds

Every tracked entity has a stable ID, a display name, aliases and one kind.
Kinds form a hierarchy, as in Inform 7: a kind inherits every property, part
and rule of the kinds above it (decided by Brandon, 2026-09-25).

```text
entity
├── area                  part: floor; can hold characters and things
├── character             part: hands; carries things; captive|free
└── thing                 portable unless fixed
    ├── container         takes things "in"; may be openable (open|closed)
    │   └── vehicle       a container characters can be in; portable
    ├── supporter         takes things "on"
    └── furniture         fixed
```

- **The engine defines only these base kinds**, so it stays story-agnostic.
  A story declares each of its entities as an instance of a kind, and may add
  its own sub-kinds (a `desk` that is both furniture and a supporter) in the
  package. Runtime code never names a story's kinds or things.
- **A kind decides the relation.** A thing whose parent is a container is
  `in` it; a supporter, `on` it; a character, `carried_by`; an area, `in`. The
  narrator's preposition is never read (section 7).
- **A kind limits parents.** A phone cannot be carried by a truck, because a
  truck is not a character. These checks are invariants (section 4.4).
- **Inherited parts** absorb common phrases. Every area has a floor, so a thing
  on the kitchen floor is `on` the kitchen. Every character has hands, so a
  thing in Kristin's hand is `carried_by` Kristin.
- **Properties inherit and can be set per instance**: `fixed`, `openable`,
  `hidden`, declared axes. The drawer is an openable container that is fixed;
  the truck is a vehicle, not fixed, because it can drive away.

### 4.2 The tree

Every entity except a top-level area has exactly one parent and one relation
to it:

| Relation | Parent | Example |
|---|---|---|
| `in` | area, or a container | the phone in the kitchen; the card in the laptop |
| `on` | a supporter, or an area's floor | the phone on the kitchen counter |
| `under` | a thing | the memory card taped beneath the drawer |
| `carried_by` | a character | the phone carried by Kristin |
| `part_of` | a thing | the drawer part of Michelle's workstation |

`under` must be its own relation. The story's first key item depends on it:
the card is taped beneath the drawer, not in it. The narrator finding the card
in the drawer was a round 7 canon leak, so "under" and "in" must not collapse
into one relation.

A carried thing can be inside another carried thing: the card in a bag, the
bag carried by Kristin. "With Rebecca in her hands" and "with Kristin" in the
authored placements are both `carried_by`.

Two relations sit outside the tree, because they do not decide where
something is:

| Relation | Example | Effect |
|---|---|---|
| `owned_by` | Michelle's phone owned by Michelle | naming only; never moves anything |
| `accompanies` | Brandon accompanies Kristin from 1B | when Kristin moves, Brandon moves to the same parent |

A thing's owner is part of its display name today ("Michelle's phone"). The
model keeps it as a relation too, so "her phone" and "my laptop" resolve, and
so a thing narrated as new with an owner can be matched to the owned thing.

A worked example, scene 1A after Kristin takes the phone to the truck:

```text
outside the house            (area)
└── Kristin's truck          in
    ├── Kristin              in
    │   └── Michelle's phone carried_by
    └── Kristin's laptop     in   (narrated "on the seat"; detail not kept)
Kristin and Michelle's house (area)
└── kitchen                  in
    └── Michelle's workstation  in, fixed
        └── drawer           part_of, fixed
```

Everything else is derived by walking the tree: the phone is in the truck, the
truck is outside the house, so the phone is outside the house.

### 4.3 State

- **Axes.** Exactly two opposite poles with aliases, as decided in 1a. Setting
  one pole removes the other.
- **Conditions.** Up to two free phrases not on any axis, as today.
- **Availability.** The existing `destroyed` and `incapacitated` predicates.
- **Hidden or found.** An axis on a concealed thing. The memory card starts
  `hidden` and becomes `found` only by the story's own route. A hidden thing is
  never in THINGS and cannot be moved by a reply, which makes the round 7 leak
  structurally impossible rather than something a rule asks the narrator to
  avoid. Hidden is separate from "inside a closed container": the card is under
  the drawer, and opening the drawer does not reveal it.
- **Missing.** A thing the story says is gone has no parent, and it has a
  `missing` status. Michelle's tablet and work bag are "missing and not in
  their normal spots". They are tracked so that the narrator cannot find them
  in the house. "Where is X?" answers "unknown", never a guessed place.
- **Captive or free.** An axis on characters. Captives, Michelle in her
  holding block and Rebecca once captured all need it. A captive character's
  parent is an area like any other character's.

### 4.6 What the story package already says

A reading of all seven files in `data/stories/continuity-initiative/` found
these relationships. Each is either in the model above or deliberately left
out in section 3.

| Found in the story | Where | In the model |
|---|---|---|
| card taped beneath the drawer, hidden until found | `plot.md` 1A hidden canon | `under`, `hidden` axis |
| drawer in Michelle's workstation; KMS carved in it | 1A placements, cue text | `part_of`, fixed |
| drawer "holds pens, binder clips, a stapler, and spare batteries" | 1A setting facts | declared `contents`, expanded to entities (W9) |
| tablet and work bag missing | 1A beats, storylets | `missing` status |
| laptop in Kristin's truck outside the house | 1A placements | `in` truck, truck `in` outside the house |
| card "with Kristin"; archive "with Rebecca in her hands" | 1A and 3C placements | `carried_by` |
| Kristin opens the card on her laptop | 1A beat | card `in` laptop |
| phone owned by Michelle, laptop owned by Kristin | item names | `owned_by` |
| Brandon travels with Kristin from 1B | 1B beats onward | `accompanies` |
| captives, holding block, Rebecca captured | 2C-3C | `captive|free` axis |
| locked office, sealed exits, relay connected to JANUS | 3A-3C | story facts (out of scope) |
| photograph of Michelle with Brandon; files on the card | 1B, 1A | knowledge (out of scope) |
| who knows a fact; Brandon-only knowledge | `knowledge.yaml` `audience` | knowledge (out of scope) |
| `memory_card` falls back to `michelle_phone` | `world.yaml` `fallback_ids` | existing dependency analysis |

### 4.7 Story facts that restate a physical relation

The package already has story facts that say where a thing is.
`memory_card_in_kristins_custody` is asserted by the 1A delivery's `costs`
and by storylets, and the placement `memory_card: with Kristin` is shown only
`while_fact_true` of it. `portable_archive_secured` hides the placement "with
Rebecca in her hands". `rebecca_captured` and `michelle_reached` are similar.

If the tree also records the card as carried by Kristin, there are two truths
that can disagree. Decision W7 (decided) makes the binding one-way: setting
such a fact applies a declared world effect, and narrated moves never change
story facts. In this package the facts record events, not current places.

### 4.4 Invariants

The engine refuses any operation that breaks one of these, and records why:

1. One parent per entity; no cycles.
2. A top-level entity is an area.
3. `carried_by` points only at a character.
4. `in` points only at an area or a container; `on` only at a supporter or an
   area.
5. A `fixed` thing never changes parent.
6. A character's parent is an area or a container (a truck, a closet), never
   a character or a supporter.

### 4.5 Storage

At runtime the tree and state are facts in `FactStore`, keyed by entity ID:
`Fact(predicate="in", subject="michelle_phone", object="kristin_truck")`,
`Fact(predicate="state", subject="michelle_drawer", value="open")`. They are
saved, cloned for candidate turns and restored exactly like every other fact.
No second store of truth.

The model lives in the `worldkeeper` library (section 4.8), which never owns
state. It reads and writes facts through a small backend interface that
`FactStore` already satisfies, so `FactStore` stays the only truth.

The bench keeps its own harness, but it uses the same library with the same
operations, so the bench measures the thing the runtime will run.

### 4.8 The `worldkeeper` library

Decided by Brandon, 2026-09-25 (W10): the model is its own self-contained,
reusable library named `worldkeeper`, designed so it could be published to
PyPI later even if it never is. Existing libraries were considered first and
rejected: Microsoft's TextWorld (`textworld.logic`) is closest, with a type
hierarchy, typed facts and rules, but its rules model player commands rather
than narrated end states, its `State` would be a second store of truth, it has
no parent chain, hidden things, owners or companions, and it pulls in a native
Z-machine emulator (`jericho`) and a pinned `tatsu`. Evennia is a whole MUD
server; Tale, IntFicPy, textadv and adventurelib are unmaintained or too
small. TextWorld's kind declarations remain a useful reference for the
`world.yaml` schema.

**Storage through a backend interface.** The library never imports
`FactStore` and never keeps its own state:

```python
class FactBackend(Protocol):
    def matching(self, predicate: str, subject: str | None = None) -> tuple[FactLike, ...]: ...
    def assert_fact(self, fact: FactLike) -> None: ...
    def retract_fact(self, fact: FactLike) -> None: ...
```

`FactStore` already has these three methods, so freytag-forge passes its store
in directly; another user could pass a dict-backed store. Cloning, rollback and
saves are unchanged.

**What goes where:**

| In `worldkeeper` (story-agnostic, no LLM) | Stays in freytag-forge |
|---|---|
| Base kinds, inheritance, story sub-kinds | Reading YAML and `plot.md`; the library takes plain data |
| Entities, the tree, the invariants | The narrator's reply format and prompt text |
| Operations and derived effects (W3, W8 rules) | The match call; the library accepts an optional resolver callback for names it cannot find |
| Minting IDs; name and alias lookup | Deciding when a story fact's world effects apply (W7); the library applies an effect list |
| Visibility (hidden, closed containers); what is given with an open container (W9) | Formatting THINGS lines |
| The place label: authored text while still true, else the parent's name (W4) | The bench, judges and saves |

**Structure and rules:**

- A uv workspace member in this repository (`packages/worldkeeper/`) with its
  own `pyproject.toml`; storygame depends on it as it would on a published
  package. Publishing later is only a release step.
- Standard library only: no pydantic or other runtime dependency.
- It never imports `storygame`. A test enforces this, and another enforces
  the standard-library-only rule.
- Its own tests use synthetic worlds only; continuity-initiative tests stay in
  storygame. Principle 8 (any story package) is then part of how the library
  is built, not a check afterwards.
- `worldkeeper` was free on PyPI on 2026-09-25 (the JSON API returned 404).
  PyPI can still refuse a name too close to an existing one; only registering
  proves it. Reserving it early is a public action and needs Brandon's go.

## 5. Operations and rules

Capture produces operations; only operations change the model.

| Operation | Does | Refused when |
|---|---|---|
| `move(x, relation, parent)` | sets x's parent | an invariant would break; x is fixed |
| `set_axis(x, pole)` | sets one pole, clears its opposite | x has no such axis |
| `set_conditions(x, phrases)` | replaces free phrases (max two) | more than two, or too long |
| `create(x, kind, relation, parent)` | adds a narrated new thing (decision 1c) with a minted ID | the name resolves to an existing entity |
| `make_unavailable(x, predicate)` | `destroyed` or `incapacitated` | never refused; the story check decides what follows |

**A created thing is a full entity (decided by Brandon, 2026-09-25).** If the
narration creates a thing, it must exist in the world facts and be
referenceable, not only in narration. So `create`:

- mints a stable, deterministic ID in the engine, never from the model:
  `n_` plus a slug of the name plus a counter (`n_usb_drive_1`), unique and
  stable across save and load;
- records the thing as facts exactly like an authored entity: name, kind
  (default `thing`), parent, and owner when the reply gives one (owner capture
  already exists in `_resolve_new_items`);
- after that the thing is ordinary: the name resolver finds it from player
  input and later replies, THINGS gives it under the 1c reference rule, and it
  is saved and restored.

The narrator is already asked for new things ("Every time your story moves
or changes a thing, or puts a new thing in a place, add that thing to
item_facts."), so only the ID and facts were missing. Today the bench stores a
narrated thing under its name string only.

Derived effects the model applies with no reply saying so:

- Moving anything moves everything under it. Kristin walking to the truck
  moves the phone she carries. Nothing else is written.
- A thing inside a closed container is hidden from the player's view until
  the container is opened. (Protected knowledge still follows the existing
  reveal rules; this only covers what can be seen.)

The closed-container rule is decided (W3). A reply may move a thing to an
area its holder is not in (the phone tossed out of the truck window): the
engine has no map to tell a real move from a mistaken one (routes are out of
scope, section 3), and refusing would drop a narrated change. If the bench
shows the narrator teleporting things by mistake, find its cause then.

Every refused operation refuses only itself, never the turn, and is recorded
in the turn's issues. A refusal is still a story failure under the rule that
every reply change must land, so the continuity plan's regeneration path
(cause routing) is where a refused change goes next.

## 6. What the narrator reads

The narrator never sees relations, IDs or the tree. The engine never composes
English from the tree either (W4, decided): generating sentences from kinds
and relations needs templates for articles, plurals and chain depth, and loses
authored detail. The THINGS line's `Place` is one of two things:

1. **The authored `text`**, verbatim, while it is still true: neither the
   thing nor anything above it has moved since the scene began. The check is
   structural and never reads the words.
2. **Otherwise, the parent's name only**, as a label. It is the same form the
   narrator's reply uses (section 7), so what it reads is what it writes.

```text
THINGS:
- Kristin. Place: Kristin's truck.
- Michelle's phone. Place: Kristin. Condition: not damaged.
- Kristin's laptop. Place: in Kristin's truck outside the house.
```

(The laptop still shows its authored text because neither it nor the truck
has moved. If the truck drives away, the laptop's line becomes
`Place: Kristin's truck.`)

- Because the line comes from the tree every turn, it cannot go stale.
- Which things are given stays as decided: the ones the command refers to and
  those a current beat or progression involves (1c), plus the protagonist
  every turn.
- When an open container is given, its visible direct contents are given
  with it (W9). Otherwise "Open the drawer." hands the narrator the drawer
  but not what is in it, and it invents contents. Hidden things are never
  given.
- How a bare parent name reads to the narrator is decision W5.

Because the line is built from the model, the "bigger place" and start-place
rules may no longer be needed. Remove them only after a bench run shows the
narrator still reports Kristin's moves without them (principle 5: remove a
mechanism before adding a rule, but verify the removal).

## 7. Capture: from the narrator's reply to operations

Capture stays in the one narration call. Its single job is to translate each
reply entry into operations the model then validates. No place phrase is ever
parsed (decision W1, Brandon, 2026-09-25).

**The reply names the parent.** `place` changes from a phrase to the name of
a thing, character or area:

```json
{"item_facts": {
  "Michelle's phone": {"place": "Kristin", "condition": ["not damaged"]},
  "Kristin": {"place": "Kristin's truck"},
  "memory card": {"place": "drawer", "under": true}
}}
```

1. **Key to entity.** Resolve the reply's key to a tracked entity by exact
   name or alias. If that fails, use the existing match call (as today, only
   for unresolved names). If that fails, the key is a new thing: `create`.
2. **`place` to parent.** Resolve the `place` name with the same resolver:
   exact name or alias, then the match call. This is name resolution, which
   the engine already does, not phrase parsing.
3. **Relation from the parent's kind** (section 4.1). `"under": true` is the
   one relation a kind cannot imply, so it is an optional flag.
4. **An unresolved name still lands.** If no parent is found, record the name
   as the thing's place with an unknown parent. Never drop it and never guess
   the scene's location (place-is-the-most-local-container). The next THINGS
   line shows it, and the offline report counts these.
5. **Container-shaped replies.** `{"kitchen counter": {"contents": [...]}}`
   becomes one `move` into the kitchen counter per listed thing, with the
   relation from its kind.
6. **Condition phrases** go through the existing axis matching, then
   `set_axis` or `set_conditions`.

The cost is a changed reply format, so capture is re-measured against the 92%
bar. The risk is whether the 8b model writes `"Kristin"` where it now writes
`"in her hand"`. One smoke replicate answers that before any full run. The
narrator rule and example that ask for this must be rewritten at the
8th-grade level, replacing the current place example rather than adding one.

## 8. Authoring

Following principle 9, `plot.md` settles the world first; the other package
files follow it.

- **Areas** are declared with a parent, for example `kitchen` in `the house`.
  Scene `location_id`s become top-level or nested areas.
- **Kinds and properties** (`container`, `supporter`, `openable`, `fixed`) are
  declared per item in `world.yaml`, alongside the existing `fixed` field.
- **Placements** (W4, decided) name the parent by ID, with an optional
  authored `text` for the narrator. Loading checks the ID like any other
  reference and never reads `text`:

  ```yaml
  item_placements:
    michelle_phone: {parent: kitchen, text: on the kitchen floor}
    kristin_laptop: {parent: kristin_truck, text: in Kristin's truck outside the house}
    memory_card: {parent: michelle_drawer, under: true}
  ```

  Whether `text` agrees with `parent` is the author's job; no check reads it.
- **Hidden things get declared places.** The authoring rule that keeps a
  hidden item out of `item_placements` exists because placements were sent to
  the narrator as sentences. A `hidden` thing is never in THINGS, so its place
  can be declared. Delivery text and the `**Hidden canon:**` line stay.
  `docs/markdown-story-authoring.md` changes with this.
- **Declared contents** (W9, decided) are one line on the container; the
  loader expands each into an entity with an ID, parented to the container:

  ```yaml
  - {id: michelle_drawer, name: drawer, kind: container, openable: true, fixed: true,
     contents: [pens, binder clips, stapler, spare batteries]}
  ```

  The setting fact "The drawer holds pens, binder clips, a stapler, and spare
  batteries." is removed: the tree says it, and the sentence would go stale
  once a thing leaves the drawer.
- **Hidden things and bindings** (W7) are declared with the item: the memory
  card starts `hidden`, and `memory_card_recovered` (renamed, W7) moves and reveals it.
- **Add them scene by scene as problems surface**, not exhaustively (standing
  preference). Scene 1A needs: the house, the kitchen, outside the house,
  Kristin's truck, Michelle's workstation.
- Story text changes go to ChatGPT Desktop with a self-contained prompt.

## 9. How the existing mechanisms map onto the model

| Today (bench) | In the model |
|---|---|
| `place` phrase | `place` names the parent; relation from its kind; unresolved names kept |
| state axes (1a) | axes, unchanged |
| `fixed` refusal | invariant 5 |
| protagonist seeded "in {location}" | the protagonist's parent is the scene's area |
| protagonist line every turn | unchanged |
| start-place and bigger-place rules | candidates for removal once the THINGS line carries the area (section 6) |
| name-match call | step 1 of capture, unchanged |
| dropped `contents` replies | `move` per listed thing |
| `destroyed` / `incapacitated` | `make_unavailable`, feeding the existing dependency analysis |

## 10. Checks

Two gates, as elsewhere in this project.

**Deterministic (authoritative).** Unit tests of the model module with no
live worker and no story names in the module:

- each invariant refuses its violation and records why;
- moving a container moves its contents, to any depth;
- the THINGS line for each entity matches the tree after every operation;
- a saved and loaded game gives the same tree;
- package loading rejects a placement with an undeclared parent;
- declared `contents` expand to entities with IDs, parented to the container;
- a created thing gets a minted ID, is found by the name resolver afterwards,
  and survives save and load;
- an open container's visible contents are given with it; hidden things never
  are;
- every case runs against a second, synthetic package as well as
  continuity-initiative (principle 8);
- `worldkeeper` never imports `storygame` and has no runtime dependency
  outside the standard library;
- `FactStore` satisfies the `FactBackend` interface, and a dict-backed
  backend passes the same library tests.

**Live (integration and quality).** The bench scores capture per operation
type (`move`, `set_axis`, `set_conditions`, `create`) against the 92% bar,
grading the whole world state every turn. The fact judge reads the rendered
tree so that it grades location, not wording. The hosted E2E `@world-state`
test asserts the phone's parent is Kristin, not merely that a scene exists.

## 11. Phases

Each phase is Ringer tasks on Luna; Claude writes the spec and check, and
reviews the patch. Phases are numbered S0-S4 so they are not confused with
decisions W1-W10. Scope decided by Brandon, 2026-09-25 (W6).

**S0 - Decisions.** Brandon settles section 12. Nothing is built before.

**S1 - The model and the package schema.** No billed runs.

- Task 1: the `worldkeeper` library (section 4.8) in
  `packages/worldkeeper/`: kinds and inheritance, the tree, axes, invariants,
  operations, ID minting, the W3 closed-container rule, the W8 companion rule,
  W9 contents, and the W4 place label, all through the `FactBackend`
  interface. Synthetic-world tests only, plus the no-`storygame`-import and
  standard-library-only tests.
- Task 2: wire it into storygame: `FactStore` passed as the backend, the
  package data handed to it as plain data, W7 effects applied when a story
  fact is set. This task and the ones below depend on task 1.
  Task 1 is done (PR 479). Task 2 is done (branch `world-model-s1`,
  commits bd8c46b and 529b6a0). worldkeeper is a uv workspace dependency.
  `storygame/runtime/world_model.py` is the adapter. `world.yaml` facts may
  declare `on_assert` effects, which apply once per fact through a sweep
  after every commit point, leaving a `world_effects_applied` marker.
  Bootstrap seeds the world, and the provider cannot write `wk_` facts. The
  two library fixes from task 1's review landed with it: story-effect moves
  carry companions, and `create()` lost `parent_id`. So did a third: a
  companion with no place never follows. The schema data is built in
  `storygame/story_package/world_schema.py`, and the next task extends it.
- Package schema and loader: `kind` on items, `parent` on locations, an
  optional `kinds` list, placements as `{parent, text, under}`. Loading
  rejects unknown IDs and parents a kind does not allow. String placements
  still load, so nothing breaks before it is converted.
  Done as task 3 (commits 515201e and cf31bd2), together with the narrator,
  bench and docs bullets below.
- The shipped narrator: `_placement_rules`
  (`storygame/runtime/cloudflare.py`) reads `text` and says exactly what it
  says today. This is the only change to shipped behaviour, and it must change
  nothing the player sees. The loader (`storygame/story_package/loader.py`)
  and the bench readers (`bench/item_facts.py`, `bench/judge_input.py`) are the
  other placement readers.
- Convert continuity-initiative scene 1A only: the kitchen and
  outside-the-house areas, the truck, the workstation, the card's hidden place.
  Structured YAML edits in a Ringer task; no story prose. Keep the setting
  fact "The drawer holds pens, binder clips, a stapler, and spare
  batteries." through S1, because the shipped narrator does not read the
  tree yet. Removing it now would change what the player sees. It goes when
  THINGS gives an open container's contents (S2 on the bench, S4 at runtime).
  The shipped narrator's 1A payloads must stay byte-identical to the
  baseline captured before S1 (opening and one turn, with and without the
  card custody fact).
- Update `docs/markdown-story-authoring.md` for hidden places and the new
  placement form.
- The 1A conversion and the W7 rename are done as task 4 (commits 89b1eea
  and 54541e9). See "Resume here" for the move-effect `text`, the narrator's
  world view and the workstation's name.
- Exit: the section 10 unit tests pass on continuity-initiative and a
  synthetic second package; full suite green.

**S2 - The bench uses the model.** Billed.

S2 is split into Ringer tasks on branch `world-model-s2` (S1 merged as PR
480):

- **Task A: the bench store is the world.** `ItemFactsProvider` keeps no dict
  of places. Every tracked place, axis pole and condition is a `wk_*` fact in
  `state.facts`, and `item_facts` becomes a read-only view rendered from the
  world. The reply format and prompt wording do not change. A phrase that
  names no entity lands as an unplaced name, and each turn records these as
  `item_facts_unplaced`. Characters are shown by their short name
  (`Kristin`). Variation state axes become world axes; the drawer's axis must
  use the world's `open`/`closed` poles. Done as 7e32ab1 (five Ringer
  rounds squashed). Review found what the checks missed: a move out of a
  closed container was refused, match calls ran once per name, and view
  reads re-seeded the store. The last was a worldkeeper bug: `seed()`
  re-hid revealed things. Lesson for B's check: guard the patterns a
  review found, and read the whole diff, since one round added a
  `seed_defaults()` alias only to pass a grep.
- **Task B: the reply names the parent.** THINGS and PLAYER lines follow
  W4 and W5. The place rule and the output example are replaced: the lantern
  becomes `{"place": "Kristin"}`, with an optional `"under": true`. The
  bigger-place rule ("name both, like the passenger seat of the truck") goes
  in this task, not S3, because it asks for a phrase and W1 asks for a name.
  Container-shaped replies land. Unresolved place names join the existing
  match call's NEW NAMES. A given open container brings its visible contents
  (W9). A new variation drops the drawer-contents setting fact. Two
  corrections to task C's section of `docs/markdown-story-authoring.md` ride
  along: the protagonist's own placement replaces where she starts, not the
  scene's `location_id`; and the companion and protagonist roles are
  written without gendered pronouns, like the rest of the guide.
  Done as 17437be on branch `world-model-s2b` (two Ringer rounds
  squashed). Choices the plan left open: a character named at furniture
  (Kristin "at the workstation") lands in the furniture's area, since a
  character cannot be on a supporter; the match call lists nearby areas
  and placed characters only when it carries a place name, and
  `_MATCH_SYSTEM` gained one sentence mapping a spot in a room to the
  room. Review found what the check missed: the echo test guessed the
  relation from the parent's kind, which refused an echo of the fixed
  drawer (`part_of`); three owner tests had been weakened to expect match
  calls; and required repository tests were missing because the check
  grepped for words, not test names. Lesson for later checks: require
  named tests and run them.
- **Task C: W8's front matter.** `companions` and `character_placements`,
  in the loader and in `apply_scene_placements`, plus the decided
  `together()` rule in `worldkeeper`. It is independent of A and B. Done as
  1ab6d22.
- **Task D: seats (W11).** `enterable` and `enter_pole` in `worldkeeper`,
  item axes and `seat_for` in `world.yaml` and the loader, the workstation
  chair declared as a seat, and THINGS giving a furniture's seat with it.
  The shipped narrator's 1A payloads must stay byte-identical. Then a
  small smoke with "Sit in the workstation chair." on an overturned chair,
  separate from the v36 script.
  Done as 77c0240 (two Ringer rounds). Round 2 removed two library
  changes nobody asked for and added the seat tests round 1 skipped. The
  smoke runs led to three follow-ups: c06ee38, 7989583 and c7705b8 (see
  "Resume here"). W12 replaces seat smoke 3 as the next step.
- **Task E: seating before use (W12).** `use_seated` on items and
  `right_text`/`enter_text` on seats in `world.yaml` and the loader, with the
  loader rejecting a seat that lacks either line. A Python Jev client and
  the yes/no question. The two checks and the added sentences on the bench
  turn path. The shipped narrator's 1A payloads must stay byte-identical.
  Unit tests stub Jev and cover: overturned and unseated (both lines),
  upright and unseated (enter line only), already seated (nothing), in the
  truck (nothing), no seat nearby (nothing), and a "no" answer (nothing).
  The seating logic is `storygame/runtime/seating.py`, story-agnostic and
  handed the question as a callable, so S4 can reuse it with the Worker
  route. The bench turn record's `player_input` is the command the narrator
  received, including the added steps, so the judges do not count the
  sitting as beyond the command. The typed input is kept as
  `typed_input`, and the added steps as `seating_steps`.
  Done as the commit after ac07f03 (two Ringer rounds; round 1 skipped the
  named tests). Known gap for S4: the bench applies the seating before the
  turn, so a rejected turn keeps Kristin seated with no narration. The
  runtime version should run inside the turn's snapshot so a rejection
  undoes it.
  Jev answers a probability (`{"type": "noul", "noul": 0.78}`), not a
  boolean, so the first smoke asked but never seated anyone; 795580d reads
  `noul > 0.5`, as `bench/jev-judge.mjs` does.
  W12 seat smoke (2026-09-26, 3 replicates each of `laptop-overturned` and
  `laptop-upright`, variation in the session scratchpad): Jev answered all
  questions correctly (yes for reading files; no for setting upright,
  knocking over, standing up and carrying the laptop). The engine added the
  right steps every time it was asked, and the narration never seated
  Kristin before righting the chair. Both steps narrated in order 4 of 5
  times (one reply dropped the sit sentence); the sit step alone narrated 2
  of 3 times (one reply righted the already upright chair instead). The
  remaining faults are capture, not W12: a narrated stand-up not captured,
  so Kristin stayed "in" the chair and no question was asked; "Set the
  workstation chair upright." captured as Kristin sitting in it (2 of 3);
  and one reply putting the chair's place as Kristin, after which seating
  was refused as a cycle.
  Without the two-line upright rule (d08defa added `item_facts.drop_rules`;
  same scripts and replicates, every prompt confirmed without the lines):
  the added steps were narrated in order 12 of 12 times (both steps 7 of 7,
  sit alone 5 of 5), against 6 of 8 with the rule; no turn seated Kristin
  before righting the chair; Jev answered every question correctly. The
  "set upright" command was no longer captured as Kristin sitting. Both arms
  still have the narrator call the chair "overturned" after it was righted,
  which looks like the authored setting fact "The workstation chair is
  overturned." still reaching the prompt (W9's stale-sentence problem), and
  one reply captured that description as the chair's state. Brandon
  (2026-09-26): remove both. The two lines are gone from
  `_SINGLE_CALL_RULES`, and "The workstation chair is overturned." is gone
  from the 1A setting facts; the chair's axis already starts it overturned.
  The shipped narrator's 1A baseline was regenerated, and it differs only
  by that sentence.
  Then a seat smoke with "Read the files on my laptop." in the kitchen, on
  an overturned chair and again on an upright one, and a run without the
  two-line upright rule to decide whether it goes.
- **Task F: the "use" question, standing up, movable seats (W12, W13).**
  The Jev "use" question is rewritten so opening, closing and turning the
  laptop on or off are not use. A second Jev question and `leave_text`
  stand a seated Kristin up before a command that needs it. `worldkeeper`
  kinds may declare `fixed`, and `seat` becomes `[furniture, supporter]`
  with `fixed: false`. The check calls Jev live on eight "use" cases and six
  "stand" cases; the old question is asked the same "use" cases for the
  record. The shipped narrator's 1A payloads stay byte-identical.
  Done as b2a827f (two Ringer rounds; round 1 skipped the named tests, as
  in task E). Live Jev: the old "use" question answered "Open my laptop."
  as use; the new one answered all 8 "use" cases and all 6 "stand" cases
  right. Next: a seat smoke with a stand-up case.
  W13 stand smoke (2026-09-26, `stand-overturned` and `stand-upright`, 3
  replicates each, variation in the session scratchpad, laptop on the
  workstation): Jev answered every seating and standing question right,
  and every added step was narrated, in order (8 stand steps, 9 sit
  steps). The movable chair was carried to the truck 2 of 3 times, and
  held by Kristin once. Faults found, none in the engine's steps:
  1. With two added steps (right the chair, sit), the narration stopped
     after them and never read the files, and the reply omitted
     item_facts (3 of 3). With one step it finished the command.
  2. "Open the drawer." while seated: Jev said stay seated, but the
     narration stood her up 3 of 3, and the reply kept her in the chair.
  3. A reply giving the chair's place as the workstation put the chair on
     the desk (3 of 3 in `stand-upright`), since the chair is no longer
     fixed.
  4. The narration called the righted chair "overturned" twice. The 1A
     Details line "overturned workstation chair" still reaches the prompt.
  Brandon (2026-09-26): fix 1, 3 and 4, and add a rule for 2. Task G:
  1. The engine's steps reach the narrator as a separate PLAYER line,
     "Just before this: ...", not as commands in front of the player's
     command. The seat's authored lines become past-tense statements
     ("Kristin set the workstation chair upright."). The turn record and
     the judges still get the steps with the command.
  2. While Kristin is seated when the prompt is built, the bench narrator
     gets one rule: "Kristin stays sitting in the workstation chair."
     She is only seated then when Jev said she need not stand.
  3. A reply giving a seat's place as the furniture it is `seat_for` is a
     quiet no-op, like a thing named as its own place.
  4. "overturned workstation chair" leaves the 1A Details line. The
     bullet "The chair at Shelly's workstation has been overturned." stays:
     it never reaches the narrator, and knowledge and storylets cite the
     overturned chair as evidence.
  Done as 9210622 (one Ringer round). Stand smoke rerun on it (same
  scripts, `item-facts-w13g-stand-smoke-*`): Jev and the engine's steps
  were right on every turn.
  1. Fixed: with two added steps, the command was carried out 5 of 5
     times (was 0 of 3). The narration now shows the command, not the
     steps.
  2. Not fixed by the rule: the rule was in every prompt, and "Open the
     drawer." still stood her up 3 of 3. "Close my laptop." kept her
     seated 3 of 3. The replies now record her standing, so world and
     story agree.
  3. Fixed: the chair stayed off the desk 3 of 3.
  4. Fixed: no narration called the chair overturned.
  Capture faults left, for the two-scene run to measure: "Set the
  workstation chair upright." captured with an empty condition, so the
  chair stayed overturned (2 of 3); and places the engine did not resolve
  ("Michelle's home", "inside the house") left Kristin outside every area,
  so no seating question was asked on the next laptop command.
- Then the smoke replicate and the v36 comparison below.

- Capture produces operations; THINGS follows W4 and W5; the reply names the
  parent; the system prompt's place example is replaced.
- One smoke replicate first, answering W5's two questions. Then compare
  against v36 on the same script.
- Exit: no capture category worse than v36, and container-shaped replies
  land.
- The continuity plan's Phase 0 bar (92% per change type) restarts on the new
  reply format from here, with v36 as the baseline.

S2 is done: merged as PRs 481 and 485, with the exit met (see the S2
record).

**Scene grounding (after S2).** Declare and place the things, areas and
NPCs of scenes 1B-3C, one Ringer task per scene. The order and the settled
decisions are in "Resume here".

**S3 - Remove what the model makes redundant.** One run per removal. The
bigger-place rule already went in task B, so only the start-place rule is
left. Keep a removal only if the numbers hold.

**S4 - Runtime.** Capture during play, the tree in saves (schema bump), cause
routing: hand over to the continuity plan's Phases 4-6, which build on this
model instead of a `place`/`condition` dict.

## 12. Decisions for Brandon

W1. **How a reply's place becomes a relation and parent. Decided (Brandon,
2026-09-25).** Brandon rejected parsing the place phrase (finding names in it
and reading the relation from its first word) as brittle, and asked for an
inheritance-like model instead. Decision: kinds form a hierarchy (section
4.1); the reply's `place` names the parent; the engine resolves that name
with its existing resolver; the relation comes from the parent's kind, with an
optional `under` flag (section 7). Rejected: phrase parsing; a match call for
every changed place.

W2. **Relation set. Decided with W1.** `in`, `on`, `under`, `carried_by`,
`part_of` in the tree, and `owned_by` and `accompanies` outside it. Every
relation but `under` follows from the parent's kind. "Behind" and "beside" are
not relations; the narrator names the nearest parent, and detail can be kept
as a condition phrase.

W3. **Closed containers. Decided (Brandon, 2026-09-25).** When a reply puts
a thing into, or takes it from, a closed container, the move is accepted and
the container is set `open` as a derived effect, because the narration showed
it happen and narrator initiative is not a failure. The engine applies a
reply's moves first and its states second, so a reply that also says the
container is closed wins. Opening makes contents visible but never reveals a
`hidden` thing. The rule belongs to the container kind, so every openable
container inherits it. `locked` is left out until a story needs it. Rejected:
refusing the move (drops a narrated change); accepting it with the container
still closed (an impossible state).

W4. **Where kinds, areas and starting places are declared. Decided (Brandon,
2026-09-25).** Base kinds live in the engine. What an entity is (its kind,
properties, and an area's parent) goes in `world.yaml`, next to the existing
`fixed` field, with optional story sub-kinds in a `kinds` list. Where an
entity starts goes in each scene's `plot.md` `item_placements`, as a parent
ID plus optional authored `text` (section 8). Hidden things get declared
places. Brandon rejected rendering the narrator's placement sentences from the
tree as brittle; the authored text is shown while it is still true, and a bare
parent name after that (section 6).

W5. **How a bare parent name reads. Decided (Brandon, 2026-09-25).** After a
thing moves, THINGS shows only its parent's name (`Place: Kristin.`), the same
form the reply writes. The system prompt's place example is replaced, not
added to: a picked-up lantern becomes `{"place": "Kristin"}`. The S2 smoke
replicate must answer two questions before a full run: does narration show a
thing whose place is a character as held by that character (fact judge), and
do replies use bare parent names rather than slipping back to phrases (the
harness counts unresolved names)? If either fails, the fallback is a separate
`Held by:` label for things whose parent is a character. Rejected: a relation
word before the name ("with Kristin"), because it composes English and the
narrator would echo it back, forcing phrase parsing.

W6. **Scope of the first build. Decided (Brandon, 2026-09-25).** Three steps
before the runtime turn (section 11, S1-S3). "Bench first" cannot mean bench
only: the shipped loader and narrator both read item placements, so S1 changes
the shared schema and loader, with the shipped narrator's output kept
identical.

W7. **Story facts that restate a relation. Decided (Brandon, 2026-09-25):
one-way.** A story fact may declare world effects in `world.yaml`; setting the
fact from any source (storylet operation, route event, delivery `costs`)
applies them. Narrated moves never change story facts.

```yaml
facts:
- id: memory_card_recovered
  on_assert:
  - {move: memory_card, parent: kristin}
  - {reveal: memory_card}
```

The story fact records that an event happened and stays true; the tree
records where things are now. This is the only way a hidden thing becomes
found. Only facts with a clear world effect declare one: `rebecca_captured`
sets Rebecca `captive`; `portable_archive_secured` declares none, because the
archive has no single new holder.

Rejected: a two-way binding. Tracing the package showed it causes a replay
bug: `SL-1A-E` ("The KMS Mark", finding the card beneath the drawer) activates
while the custody fact is false, so a narrated drop that retracted the fact
would offer the find again with the card on the truck seat. Also rejected: no
binding, which leaves the card hidden under the drawer after the story says
Kristin found it.

Consequences, all in S1 as a Ringer task (structured data, not prose; Brandon
confirmed a label rename is not a prose rewrite):

- Rename `memory_card_in_kristins_custody` to `memory_card_recovered` everywhere
  it is referenced (`world.yaml`, `knowledge.yaml`,
  `storylet-routes.yaml`, `pacing.yaml`, `handoffs.yaml`, plus the two
  mentions in `storylets.md` and the placement guard in `plot.md`).
- Drop "and is carrying it" from its purpose, which now states the event.
- Remove the card's `while_fact_true` placement guard; the tree records the
  move.
- The pacing line "searching the house for something Kristin now carries" is
  left as is: it can be slightly wrong if she has put the card down, which
  does not break the story.

W8. **Companions. Decided (Brandon, 2026-09-25).** Who travels with Kristin
is plot, so only the story sets it, never a reply: a scene's front matter may
list `companions: [brandon]` from the scene's start, and a fact's `on_assert`
(W7) may add `{accompany: brandon, with: kristin}` partway through (in 1B,
`brandon_identified`). The move rule carries one condition: a companion moves
with Kristin only if he is in the same place as her when she moves. So a
narrated split ("Brandon stays in the truck") lands and he stays behind, and a
narrated rejoin makes him travel with her again, with no flag to set or clear.
Each new scene resets companions and positions from its own declarations.
Rejected: companions reported by the narrator; clearing the companion flag on
a split, which cannot resume after a narrated rejoin.

Scene `participant_ids` cannot stand in for presence: Michelle is listed in
1A-2C while she is missing or captive. So characters get starting places in a
new `character_placements` front-matter field with the same `{parent, text}`
shape as `item_placements`, added scene by scene. The protagonist defaults to
the scene's area.

W9. **Contents of a container. Decided (Brandon, 2026-09-25): each
declared content is an entity.** Brandon's criterion: anything the narration
creates must exist in the world facts and be referenceable. Authored contents
known only from a setting-fact sentence fail it (the player can type "Take the
stapler." and the world has no stapler), and the sentence goes stale. So a
container declares `contents` in one line, the loader expands them into
entities with IDs, the setting fact is removed, and an open container's
visible contents are given with it (sections 6 and 8). New things narrated
inside a container are created under 1c with minted IDs (section 5).

Rejected: a closed list that refuses unlisted things. Its motivating case,
the round 7 USB drive in the drawer, was already removed in round 8 by fix A
(the owner rule no longer names hidden items: 4/4 to 0/4), and the remaining
hidden-card leak is closed by the `hidden` axis. The list would also need
text matching of narrated names against authored ones, which W1 rejected,
and it overrides 1c. Also rejected: contents left as setting text only.

W11. **Seats. Decided (Brandon, 2026-09-25).** When the narration has
Kristin sit down, the reply names the chair, and the world must hold her
there. Following Inform 7, a container or supporter may be `enterable`, and
a character's parent is an area or an enterable container or supporter
(invariant 6). `vehicle` is enterable by kind; a story kind or an item may
declare `enterable: true`. An enterable thing may declare an `enter_pole`:
a character entering it sets that pole, as taking a thing from a closed
container opens it (W3). So the workstation chair is an enterable
supporter with an `overturned|upright` axis declared in `world.yaml` and
`enter_pole: upright`: Kristin can never sit in an overturned chair. A
seat may declare `seat_for` a piece of furniture; when that furniture is
given in THINGS, its seat is given with it, so the narrator has the chair's
name and state when it seats her by its own initiative. A reply that puts
Kristin "at" furniture that is not enterable still lands her in its area:
that reply does not say she sat, and seating her anyway would narrate a
change the prose never showed. Whether the narration shows her righting
the chair before sitting is measured in its own smoke run first; a short
prompt rule follows only if it fails most of the time (the narration fix
ranking).

W12. **Seating before using a thing. Decided (Brandon, 2026-09-26).** Seat
smokes 1 and 2 showed the narrator seating Kristin before it righted the
overturned chair (0 of 6, then 2 of 5 turns in the right order). A prompt
rule asks the narrator to get the order right. Instead, the engine does the
steps itself, before narration, as Inform 7 does with implicit actions
("(first taking the lamp)"). Brandon limited it to the one case that
matters: sitting is needed only to use a computer. No other command seats
her.

- **Data, not branches.** An item may declare `use_seated: true` in
  `world.yaml`; in continuity-initiative, only `kristin_laptop` does. A seat
  declares its two authored lines, `right_text` ("Set the workstation chair
  upright.") and `enter_text` ("Sit in the workstation chair."). The engine
  never builds these sentences itself (W4). Runtime code names no story
  thing.
- **The trigger.** One short yes/no question goes to Jev (`typesafe/jev` on
  Cloudflare, chosen by Brandon as cheap and fast): does this command use
  that thing? "Read the files on my laptop." is yes; "Take my laptop to the
  truck." is no. Jev reads only the player's input and the thing's name,
  never narration.
- **What "use" means (Brandon, 2026-09-26).** Using the laptop means
  working on it: reading, typing, or searching its files. Opening or
  closing it, turning it on or off, moving it, carrying it, picking it up
  and putting it down are not using it. The first question named only the
  moving verbs as "no", so "Open my laptop." (turn 6 of the two-scene
  script) would probably have seated Kristin. Task F rewrites the question
  and checks it live.
- **When the question is asked (task E, 2026-09-26).** Only on a turn where
  the steps could apply: a `use_seated` thing is `together()` with Kristin
  (held by her, or in her area), a seat is `together()` with her, and her
  parent is not already enterable. The world decides this, with no reading
  of the input. The earlier wording, "a turn whose input names the thing",
  would have needed name matching over the player's words, and the bench's
  only reference detection is an 8b match call. "Near" is `together()`,
  not the same area: Kristin starts 1A in the house, and the chair is in
  the kitchen.
- **Bench first, Worker later.** On the bench (task E), a Python client
  calls Jev on the Cloudflare API directly with the local
  `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_AI_TOKEN`, as
  `bench/jev-judge.mjs` already does. The bench runs only on a developer's
  machine and exposes no endpoint. The Worker route below is for the
  runtime turn, in S4.
- **Auth guard (Brandon, 2026-09-26).** No one outside the game may call
  Jev, for their own use or to run up the Cloudflare bill. The question
  goes through the existing narration Worker as a new route, never straight
  from Railway to the Cloudflare API, so the Cloudflare credentials stay in
  the Worker only. The Worker sends a fixed yes/no question and takes only
  the player's input and the thing's name; it never forwards a
  caller-supplied prompt or model. The Worker's shared bearer token
  becomes required: today `.plans/cloudflare.js` checks it only when
  `DEMO_SHARED_TOKEN` is set, so the Worker fails open. With no token set,
  both routes must refuse every request. This covers the narration route
  too. Rate limits and the $5 daily model budget, which the Jev route
  shares, are in [rate-limits.md](rate-limits.md).
- **The two checks, on a yes.** The seat to use is the first seat, by ID,
  that is `together()` with Kristin. On a no, or with no answer, nothing is
  added, and no answer is recorded as an issue. Otherwise:
  1. if the seat is not at its `enter_pole` (the chair is overturned), set
     that pole and add the seat's `right_text`;
  2. if Kristin's parent is not the seat, move her into it and add the
     seat's `enter_text`.
  An upright chair gets only step 2; a seated Kristin gets neither.
- **The narrator is told.** The added lines go before the player's command
  as separate sentences, in the same way the command splitter
  (`storygame/runtime/command_split.py`) hands the narrator a compound
  command. The world changes are committed before narration, so no fact
  changes after rendering. The narrator narrates the steps as material,
  not as a rule to obey.
- **What it does not cover.** The narrator seating her on its own
  initiative, when the command never asked, is left to `enter_pole` for
  state. The two-line upright rule (c7705b8) is a candidate for removal once
  W12 lands; remove it only if a seat smoke shows the order still holds
  without it (principle 5).

Rejected: seating her before any command that names the workstation
("Search under the workstation." does not need a seat); a list of "use"
verbs (a fixed action table, forbidden by AGENTS.md); asking before any
command that names the laptop with no judgement ("Take my laptop to the
truck." would seat her first).

W13. **Standing up before leaving a seat. Decided (Brandon, 2026-09-26).**
The counterpart of W12. The engine tracks whether a character is seated or
standing, and a seated character can move only once she stands. The seat
smokes found the gap: the narration showed Kristin standing up, the reply
left the change out, and the world kept her in the chair.

- **Posture is the tree.** Kristin is seated when her parent is a seat, a
  thing with `seat_for`. Otherwise she is standing. A vehicle is not a seat:
  sitting in the truck is not covered.
- **Data, not branches.** A seat declares a third authored line,
  `leave_text` ("Stand up from the workstation chair."), next to
  `right_text` and `enter_text`. A seat without it fails to load.
- **The trigger.** Only while Kristin is seated, one Jev question: does
  she need to get up to carry out this command? The state holds the
  command, the seat's name, and the names of the things within reach of the
  seat. Within reach means the seat, the furniture it is `seat_for`,
  everything inside or on that furniture, and everything Kristin holds. It
  is yes when the command sends her somewhere else, or acts on a thing that
  is not within reach. While she is standing, the question is not asked.
- **The step, on a yes.** The engine moves her from the seat to the seat's
  area and adds the seat's `leave_text` before the command, as W12 does. On
  a no, or with no answer, nothing is added, and no answer is recorded as
  an issue. A turn that stands her up does not also ask the W12 question.
- **A reply that moves a seated Kristin elsewhere** without the step is
  accepted as standing up and then moving. Refusing it would drop a
  narrated change, which is a severe failure. The step before the turn
  should make this rare.

**Seats are furniture, but the chair can move (Brandon, 2026-09-26).** The
`seat` kind becomes `[furniture, supporter]`. Furniture is fixed by default,
so a kind may now declare `fixed`, and `seat` declares `fixed: false`. A
chair is light enough to carry to another room, and `fixed` would refuse
every move of it. The desk kind stays fixed. A reply that records the
chair's place as Kristin is a capture error, and W5's held-by question
measures it.

W10. **A self-contained library. Decided (Brandon, 2026-09-25).** The model is
a separate, reusable library named `worldkeeper`, designed to be publishable
to PyPI later: a uv workspace member, standard library only, no `storygame`
imports, state kept in the host's store through a backend interface (section
4.8). Names considered: `kindtree`, `worldkeeper`, `fictree`, `worldstate`;
Brandon chose `worldkeeper`.
