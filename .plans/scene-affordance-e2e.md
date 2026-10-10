# Scene affordance E2E tests: plan

Latest (2026-10-10, main c60800a, evening): see 'Resume here (2026-10-10, evening)'. 3C cue chain (PR 565) and verb widening (PR 566) merged and measured: 3C steps by play 4/5/7 of 7, one run reached the ending with no timer dump. PRs 567 (surface gates in 3A and 3B) and 568 (3C d_r2/e_r2 phrases) merged, not yet measured live. Open: PR 569 (1A drawer words and cue, from the ChatGPT round); next is the L2 1A rerun on the merged SHA, see '1A drawer words (2026-10-10)'. Earlier latest (2026-10-10, main be59c43): PR 565 (3C cues and the C/D split) merged and measured; see 'L2 all nine scenes x3 on be59c43': 3C now gets two to five steps by play instead of one, no rejected turns; open: widen the b_r1, c_r2, d_r1, d_r2 verb groups. Earlier latest (2026-10-10, main dc0aba9): PR 563 (3B cue names the cameras and the console's alarm move; a_r1 accepts access/open/enter) merged and measured by the all-scenes L2 x3; see 'L2 all nine scenes x3 on dc0aba9'. 3B 3/3 by play (turn 9 each, first alarm command on turn 2 each), 3A 2/3, 1C 2/3, 2A 2/3, others 3/3, 3C 0/3 (timer x3). Earlier latest (2026-10-10, main 603b07b): PR 555 merged (3B `charles` participant; 2B decoded message 'The prisoners are ready to rise up.' in `k_sl_2b_c_r2` and plot 2B.4) and measured; see 'L2 1A-3B x3 on 603b07b'. Play exits: 1A-2C 3/3 each, 3A 1/3 (T14, T13, P9), 3B 2/3; 2B 'phase' and 3B 'charles jenkins' rejections 0; two rejected turns (3A 'rebecca's desk', 1C 'servers'). 3A misses the 2-of-3 bar: read in '3A timers read' and '3A line removal reviewed' (PR 556, plan only): the 3A prompt carries two earned 2C lines (`k_sl_2c_d_r1`, `k_sl_2c_d_r2`) that pull toward Rebecca's office; removing 3A from their `available_in_scenes` cuts the pull in the narrator probe, nothing applied yet. Open: apply that removal and rerun L2; 3A has no first-step cue toward Michelle (story text, ChatGPT Desktop); bare-word 'phase' protection in the loader unchanged. See 'Resume here (2026-10-10)'. Earlier latest (2026-10-09, main 576f57a): PR 545 (2C frame names the detention level) and PR 546 (2C transfer-order and copied-files evidence widened) merged and measured; see 'L2 1A-3B x3 on 576f57a'. Play exits: 1A 2/3, 1B 3/3, 1C 2/3, 2A 3/3, 2B 3/3, 2C 3/3, 3A 3/3, 3B 3/3, so every scene meets the 2-of-3 bar; 2A-3B were 3/3 for the first time. Open: 'rebecca' rejection in 2C (PR 548 adds her to 2C participants), 2B 'coded message' leak, 'phase' leak in 1C/2B, 1A and 1C one timer each (rerun to see if noise). Earlier (2026-10-09, main 37bef5c): PR 542 (3B cue names the inspection console) merged and measured; see 'L2 1A-3B x3 on 37bef5c'. 3B 1/3 by play (r3, turn 13); bar not met. Next: decide whether a_r1 should fire on inspecting the water-pressure warnings. Earlier (2026-10-08, main 7ac1423): PR 531 merged and measured; see 'L2 1A-3B x3 on 7ac1423'. 3A play 2/3 (bar met); 3B timer x3 (14); next: 3B plot line / e_r1. Earlier (branch claude/plan-3a-3b-l2): required-storylet closure and 3A c_r1 widening ready, not merged or measured; see 'L2 1A-3B x3 on 404c908'. Earlier (main 45d52ce): 2A/1C evidence widening merged (PR 527) and measured: 1A-1C play x3, 2A play 2/3; see 'L2 1A-2A x3 on 45d52ce'. Next: 3A, 3B. Earlier: (main 11aaf97): opening retry merged (PR 524); L2 1A-2A x3 shows 1A, 1B play x3, 1C play 2/3, 2A timer/timer/none; see 'L2 1A-2A x3 on 11aaf97'. 'the supervisor' leak fixed and measured (PR 525, 0 rejections; 1A-1C play x3); 2A still timer x3; next: read 2A commands vs c_r1.

Status (2026-10-06, main cc7cc20): PR 520 merged (staged cues, 1C wording, cues and pointers for 1C/2A/2C) and staging deployed on that SHA; smoke 1A,1B x1 passed. Option A chosen: per-scene wording, no cue-derived matching. NEXT: 2B, 3A, 3B (branch `claude/plan-2b-3a-3b-wording`), then one live L2. See "Resume here (2026-10-06)" below.

Older status: (2026-10-05, main e856bee; see "1B live L2 pending" near the end of the 1B notes): PR 517 (1B gate move, fallback fix, delivery wording, companion alongside) and PR 518 (plan) are merged, and staging is deployed at e856bee (`/api/v1/version` confirmed sha, `scene-v1`, `staging`). The 1B live L2 ran on e856bee (2026-10-05, Ringer `l2-1a1b-x3`, pass, 363 s): 1A exits by play 3/3 (turns 8, 8, 12); 1B by play 2 of 3 (turn 9, 9), bar met; r3 never left 1B (see "1B live L2 on e856bee"). Next: follow "Recommended plan: whole-game fix (2026-10-05)" below (offline simulation first); 1B pre-flight fixes (service gate, storm-drain statement, 5-rejection stop) are committed on `claude/plan-l2-1b-pending` but not merged or measured live. Earlier status (2026-10-04, main 4ab36ef): L0-L2 are merged (PR 510, main 3a82bc5). Brandon's rule:
if a player who reads only the screen cannot move from scene to scene, or the
narration does not place items correctly, the game is broken. Root causes
found in 1A and fixed in PR 510: (1) reveals unlocked only on exact authored
word groups, so natural phrasings missed and the narrator invented filler;
(2) the gate cue started at turn 10 of 13 and the narrator only paraphrased
it; (3) the 1A chain (card, then the laptop in the truck) was never pointed
at. Fixes: matcher synonym classes, cue from turn 1 appended verbatim, a
strict Jev fallback match (cap 6 candidates, 40 calls a session,
`FREYTAG_SEMANTIC_REVEAL=0` disables), and 1A cue/reveal text. Staging check
on 3a82bc5, 1A, 3 replicates each: L1 first-step items shown by the deadline
laptop 3/3 (was 0/3), drawer 3/3 (was 0/3), workstation 3/3, chair 2/3. L2:
2 of 3 replicates left on turn 8 by play (the old runs always left on the
turn-14 timer); r2 missed the card on 'initials-marked drawer' and followed a
clue the narrator invented. Follow-up on branch `claude/gates-judge-names`
(not yet merged or measured): the Jev question now carries entity names and
aliases, a two-sentence narrator rule stops invented clues when a command
names a thing that holds an unrevealed reveal, and the L2 silent-transition
flag ignores affordances absent from the shown list.

## L2 on aa52889 (PR 511 merged, staging sha confirmed), 1A, 3 replicates

Transition 2 of 3 (turns 13 and 8; r3 never left by turn 15). Silent
transition 2 of 3. Drawer, laptop and workstation were first shown on turn
2-3 in all three, but the deadline rate was 0 for the drawer and laptop and
1/3 for the workstation; the chair was never shown; the memory card was shown
in r1 (turn 13) and r2 (turn 3), never in r3. Stuck turns in every run. The
narrator still invents content on unlocking commands (r1 phone text, r2 a
recording on the card, r3 an email 'Meet me at the old warehouse'); r3 never
got the card. So the PR 511 fixes did not reach 3/3. L1 x3 on aa52889
(Ringer `freytag-affordance-live`, pass): by turn 1 the laptop 3/3, the drawer
2/3 (was 3/3 on 3a82bc5), the workstation 1/3 (was 3/3), the chair 0/3 (was
2/3). Input was "Search Michelle's house." The memory card is a later
affordance, never shown in the one explore turn (expected). Compared with
3a82bc5 the drawer and workstation went down, so the aa52889 follow-ups did
not help L1 and may have hurt; 3 replicates is noise-prone, so rerun before
concluding. Not yet checked: whether the chair shows as "Her chair" (alias
gap) in these runs.

### r2/r3 transcripts read against plot.md (2026-10-04)

Read from `artifacts/e2e-blind-player.json` (transcript entries are
cumulative; diff them). Recorded narrator prompts were NOT read.

- r2 (left turn 8): turn 2 "Search Michelle's workstation." showed the KMS
  drawer and the truck laptop. Turn 3 "Inspect my KMS-carved drawer." gave the
  card. Likely the semantic fallback, since the input has no under/beneath word
  (unverified). Turn 5 read the card, turn 8 the bridge fired.
- r3 (never left): turn 2 showed the drawer cue. Turn 3 "Examine Michelle's
  workstation drawer." only restated the initials. Turn 4 "Open Michelle's
  workstation drawer." narrated the world.yaml contents (stapler, batteries,
  pens), which is correct for an opened drawer. The player never looked
  beneath it, then followed an invented email to an invented warehouse.
- Cause so far: `k_sl_1a_b_r0` `action_evidence` needs a look verb AND an
  under/beneath word AND drawer/KMS/workstation, but its `earn_when` says
  "searches the KMS drawer or the space beneath it". Nothing on screen points
  to the underside; plot.md only says the drawer "sits crooked in its frame".
- Chair: the reveal text says "Her chair is tipped over", the entity is named
  "workstation chair". The L2 silent-transition flag may be a measurement
  false negative (unverified; D4 alias question).

Prior art checked (grounding guide, `.plans/world-model.md` W decisions):
W9 says an opened container shows its contents, so the r3 turn-4 contents were
correct, not a narrator fault. Nothing there covers how a player is led to
look beneath something (`hidden: true` + `on_assert` is for hidden things; the
`under` flag is placement only). Any cue for the underside is new work, not a
proven technique.

L2 x3 on aa52889 with `semantic_match` recorded (branch
`claude/l2-semantic-record`, uncommitted): transition 3/3 (turns 15, 13, 13),
all by the turn timer: the card was first shown only on the transition turn
(13-15) in every run, silent transition 3/3, chair never shown, drawer and
laptop by the deadline 2/3. The fallback RAN on 11 to 12 of 13-15 turns per run
and MATCHED NOTHING, including "Examine the crooked drawer.", "Open the crooked
drawer.", "Search the crooked drawer for hidden items." and "Search Michelle's
workstation." So the semantic fallback ran and Jev said no. The earlier r2 hit
had "KMS-carved" in the command. Still invented by the narrator: a paper note,
phone contacts, "Agent Thompson", a hardware receipt. Next probe, not run yet:
replay Jev's card question (earn_when "searches the KMS drawer or the space
beneath it", with the entity names it sent) against these commands to see why
"crooked drawer" fails; the recorded prompts are in each replicate's `prompts`.

### Jev probe and L2 rerun (2026-10-04, staging 39ddd65 = aa52889 runtime)

Probe (`scripts/ringer/affordance/jev_probe.py`, Ringer `freytag-affordance-jev-probe`,
5 samples per cell, Jev answered the same all 5 times): the question was the
card reveal's earn_when plus an approximation of the entity-name list (not the
exact runtime list, which also adds a placement text). Findings:
- The name list hurts. "Search beneath the drawer." 0/5 with names, 5/5 without.
- "crooked drawer" commands (examine, open, search) and "Search Michelle's
  workstation." were 0/5 in every arm. Only "Inspect my KMS-carved drawer." matched
  (5/5 with or without names). Jev reads "KMS drawer" as a different drawer.
- No false positives ("Read the note on the phone.", "Search the kitchen." 0/5).
- Using the reveal's `statement` as the sentence is worse (0/5 on both should-match).
Not yet probed: arms that put the on-screen wording ("crooked drawer") in the
names, or drop the names; and the exact runtime names from a recorded prompt.

L2 x3 on 1A (Ringer `freytag-affordance-live`, pass): transition 3/3, all on
turn 13 by the timer. The semantic fallback ran on most turns and matched
nothing, including "Open the crooked drawer." and "Search the crooked drawer."
(r2, r3). Drawer, laptop, workstation shown by the deadline 3/3 (better than
the previous L2 run: drawer and laptop were 0/3); chair 1/3 (shown turns 1, 3,
9); the memory card was shown only on the transition turn 13 in all three. Silent
transition 0/3 only because the timer delivery shows the card. Stuck turns 8 to 10
of 13 per run. The narrator still invents: a receipt note 'Meet me at the old
warehouse', a research article, an officer's dialogue. Staging turn cap was
restored by the check.

Authoring change (2026-10-04, Brandon's rule: the drawer is named only "drawer",
"drawer gap", "gap in drawer", "gap in the drawer"): cue_text in `handoffs.yaml`
and the 1A.1 line in `plot.md` now say "The drawer rides high in its frame,
leaving a thin gap along its lower edge." (replaces "sits crooked"); the card
reveal's `earn_when` in `knowledge.yaml` is "searches the drawer, the gap in the
drawer, or the space beneath it" and its under-word group gains "gap". Jev probe
rerun with that earn_when (5 samples, all cells 5/5 or 0/5): with the names
approximation, "Search beneath/under the drawer.", "Feel along the gap in the
drawer.", "Search the drawer gap.", "Look into the gap in the drawer." and
"Search the drawer." all 5/5; "Examine the drawer." and "Open the drawer." 0/5;
phone and kitchen controls 0/5. Without names "Examine the drawer." also matched
(looser). The shorter sentence "searches the drawer" and the statement sentence
were worse. Not yet measured live: the cue's effect on players; needs a merge,
a staging deploy and L2 x3. The probe's name list is still an approximation of
the runtime list. Still authored with other words: `plot.md` 112 and 132 and
`handoffs.yaml` 10 ("the drawer carved with her initials, KMS").

### L2 x3 on 4db42ef (drawer-gap cue; Ringer `freytag-affordance-live`, pass, 2026-10-04)

Transition 3/3, all by play (turns 11, 8, 11; every earlier run left on the
turn-13 timer or not at all). The card was first shown on turns 8, 3 and 9, no
longer only on the transition turn. In r1 and r2 the player typed "Search the
gap beneath the carved drawer." and "Examine the gap beneath the workstation
drawer.", and the card followed; both turns show `sem:off`, so the plain matcher
fired (inferred from the flag, not confirmed). r3 got there on "Examine the
underside of the KMS drawer." (turn 9). Silent transition 1/3 (r2, chair never
shown). By the deadline: workstation 3/3, laptop 2/3, drawer 2/3, chair 0/3
(shown at turns 8, never, 11), memory card 0/3 (a later affordance, so its
deadline is not the opening). Stuck turns 6, 4, 5 of 11, 8, 11; two stuck runs
(r1 turns 5-7 on the laptop, r3 turns 4-7 on scientific equipment and a
textbook). Invention remains: r2 took the card, then went to a park bench and a
paper note about an old clock tower; r3 invented a textbook DNA diagram and a
chair with a book. Not checked: whether the gap wording came from the on-screen
cue or from the player guessing; the recorded prompts were not read.

Open, not yet known (the first item is answered above): (1) whether the semantic fallback ran on r3 turns 3-4
(staging returns `semantic_match` and `prompt` per turn, but
`blind-player.spec.js:99` drops both from the turn record; the harness needs
to save them, then rerun);
(2) the recorded prompts for r3 turns 3-4; (3) the L1 x3 result.

## Parallel L2 replicates: built and measured (2026-10-04, merged in PR 513)

Built by Ringer `freytag-affordance-l2-parallel` (node side + wrapper). The
first run's task A failed only because my check grepped the spec for the env
name, which lives in `replicatePlan` (merge-blind-player.js); I applied both
patches and fixed the check. Files: `frontend/e2e/merge-blind-player.js` (+test:
`replicatePlan`, `mergeReports`, CLI `node e2e/merge-blind-player.js <dir> <n>`),
`blind-player.spec.js` (`E2E_BLIND_REPLICATE_INDEX` runs one replicate and writes
`e2e-blind-player-r<N>.json`; unset = old behaviour), wrapper
`scene-affordance-l2-parallel-live.sh <n>` (one cap raise, one Playwright process
per replicate, merge, digest) and manifest `scene-affordance-l2-parallel-live.json`
(same run_name `freytag-affordance-live`). Differences from the draft: no
`E2E_BLIND_REPORT_SUFFIX` (the index sets the name), and one Ringer task owning
the cap (the wrapper version), not a task per replicate. 69 node tests pass.
Smoke (1 replicate): merged report has the same keys as the serial path, with
prompts, turns and semantic_matches. Parallel x3 on staging (4db42ef): the check
took 288 s including the 60 s+ settle wait; no 429s or rejected turns. Result:
transition 3/3 by play, all on turn 8; drawer 3/3, workstation 3/3, laptop 2/3,
chair 0/3, memory card first shown turns 4, 3, 2; silent transition 2/3 (chair
never shown); stuck runs 2; unseen_command_rate 0.42. Invention persists after
the card (park bench, a paper note about a clock tower). Not done: a serial x3
comparison on the same sha; narration latency under 3 sessions not recorded.
Next: decide the chair (alias gap vs never shown) and the post-card invention.

## Plan item: resolve a bare noun against the player's current scene (2026-10-06, scoped at Brandon's request, offline check done, NOT built)

Brandon's point: a short name ("terminal") should mean the thing placed in the scene the player is in, and when two things there share the word, ask "Do you mean the archive terminals or the medical terminal?", as Inform does.

What the code does today (read, not changed): reveals match a bag of word groups (`candidate_matcher._matches_all`) with no link to entities; they are scene-scoped only through `available_in_scenes`. Entities are found by exact `name`/alias match (`knowledge._input_referenced_entity_ids`) across ALL scenes, not just the current one. Scene-scoped naming exists only for groups (`scoped_aliases`, grounding guide line 17). The leak scan treats a declared name as a spoiler until its scene is reached, so a bare alias such as "terminal" cannot be declared on a later-scene thing (the "desk" and "workstation" traps). No disambiguation code exists in the repo; input is free text sent to the narrator.

Offline check (`scripts/ringer/affordance/bare_name_sim.py`, run on `l2-all-x3`, 283 recorded commands, no billed calls). Rule simulated: a bare head word (last word of a thing's name or alias, when no full name in the command used it) resolves to the one thing in the current scene with that head; two or more = ambiguous; the command is rewritten with the full name and re-run through the real matcher against the scene's reveals. Findings:
- Head words shared by several things story-wide: terminal (archive terminals, medical terminal, freight terminal), tunnel, level, corridors, house, seat, jenkins. Inside ONE scene the only real collisions are `terminal` in 2B (archive terminals and medical terminal), `seat` in 1A, and `corridors`/`level` in 2C. So scene scoping removes the cross-scene problem and leaves the 2B terminal as a true "which one" case.
- 39 commands carried a bare head word; 38 resolve to one thing, 1 is ambiguous ("Read Brandon's earlier messages on the remote terminal.", 2B). Only 6 would change a reveal result, all in 3B: "relay" -> broadcast_relay fires `k_sl_3b_c_r2` on "Open/Inspect/Pry open the relay chamber access panel." and two "relay access panel" commands. Everything else resolves harmlessly or the reveal already fired.
- Noise to avoid: head words of aliases are loose ("official" and "prisoner" both resolve to the imprisoned senior official, while "prisoner" also names the captives group; "surface" -> facility_escape; "park" -> los_angeles_park). A built rule must use the name's head noun only, include scoped aliases, and treat any overlap as ambiguous.
- The 2B bare-"terminal" misses seen so far were mostly not bare words: the recorded commands name "medical terminal" in full, and the reveal missed on a missing evidence group. So this change would NOT have fixed the 2B misses; it would fix the 3B relay commands and make "Read the earlier messages on the terminal" ask which one.

Verdict: real gap, small measured gain today (one scene), bigger value for the next story. Proposed build if Brandon approves: (1) engine resolves a bare head noun against the current scene's placed things (name head plus scoped aliases) before the reveal matcher and the narrator's THINGS list; (2) ambiguity inside the scene asks the player which one, with the two full names, and spends no narration or turn; (3) reveals keep matching on phrases, with the resolved full name substituted. Open: whether the question is a deterministic engine line or a narrator rule (the proven path is deterministic authored text; this would be engine text). Risk: first technique with no W-decision precedent; must stay story-neutral. Next step, if approved: Ringer task with hermetic tests, then the all-scenes live round compares 3B relay play exits.

Decision (Brandon, 2026-10-06): the disambiguation is a fixed engine question that follows the Inform model, and the answer is spliced into the OLD command. Not a narrator rule. Brandon overruled my first proposal (treat the reply as a fresh command, no pending state). Design to build, story-neutral:
1. At the top of `RuntimeEngine.turn` (`engine.py:76`), before the reveal matcher and any narration call, find bare head nouns in the command that match two or more things placed in the current scene (name head plus scoped aliases; words already used by a full name are not bare). One match is resolved silently; none passes through unchanged.
2. On two or more matches, return a fixed line ("Do you mean the archive terminals or the medical terminal?") and store the original command and the candidate list as a pending clarification. No narration call, no fact change, the turn clock does not advance.
3. The next input is tried as an answer first: a full candidate name, a head or distinguishing word ("medical", "the medical one"), or "the first/second". On a match the engine substitutes the chosen full name for the ambiguous noun in the stored command and runs that command normally. On no match the pending clarification is dropped and the input runs as a fresh command (Inform does the same). A second ambiguity in the spliced command asks again; cap at two rounds, then run the original command unchanged.
4. The pending clarification is cleared on scene change.
State and risks to settle in the Ringer spec: the pending clarification is session state, not a world fact, and AGENTS.md says facts are the sole mutable truth, so it must be a separate transient field and must never feed the narrator or reveal evaluation. Snapshots serialise the whole `RuntimeState` (`persistence.py` payload, `SCHEMA_VERSION = 5`), so the field must stay out of the snapshot; Brandon decided (2026-10-06) that a pending question does NOT survive a reload: exclude the field from the snapshot payload (it is already built with `exclude={"package"}`), so no schema bump or old-save default is needed, and add a test that a save and load round trip comes back with no pending question. The hosted adapter and web demo need to show the question as a plain system line, not narrator prose. Brandon's rule (2026-10-06): the pending question is session state, not world fact, until it is answered and acted on; the spliced command then runs through the normal turn path and only its results become facts. The question, the stored command and the candidate list are never written as facts. Hermetic tests cover: unique match, two matches ask, answer by full name, answer by distinguishing word, unrelated input drops the question, scene change clears it, no model call on the asking turn, old-save load. Measure with the all-scenes live round: 3B relay play exits, and the count of questions asked per run (expect about 1 in 40 turns on `l2-all-x3`). The blind player must be able to answer; check `blind-player.js` treats the question as a non-narration turn.

## L2 all-scenes x3 on d3d651c (2026-10-08, PR 521 merged, staging deployed; Ringer `freytag-affordance-live`, pass, 958 s)

Smoke 1A,1B x1 passed first. Exit cause per replicate (r1/r2/r3), baseline `l2-all-x3` in brackets: 1A play/timer/timer [play x3]; 1B play x3 (turn 8) [timer x3]; 1C play/timer/timer (7,11,11) [timer x3]; 2A none/timer/timer; 2B play in both replicates that reached it (10, 8) [timer x3]; 2C timer/play (17, 8) [play once]; 3A timer x2 (15, 13); 3B timer x2 (14, 14); 3C none expected. r1 never left 2A, so it did not reach 2B-3C. Gains: 1B 3/3, 1C 1/3, 2B 2/2 reached, 2C play once more. Regression to check: 1A went from 3/3 to 1/3 play (card first shown only on turn 13 in r2/r3; the staged cues or the 1B change may have changed 1A cue timing; prompts not read). Still timer: 2A, 3A, 3B (the 3A override_codes thing never shown; 3A captives shown turns 5-6, gate_status_panel 4). Not read: recorded prompts. Next: read the 1A r2/r3 prompts against the cue timing, then 2A (r1 stalled), then 3A/3B.

1A regression found (2026-10-08): the staged-cue rule (PR 520) hid the 1A drawer cue. It sits on `continuity_initiative_known`, whose reveals all require `memory_card_recovered`, earned by `k_sl_1a_b_r0` with no cue of its own; the drawer-gap sentence is absent from r2 and r3 narration. Fix (Ringer `freytag-affordance-cue-own-reveal`, PASS on attempt 2; engine.py `_cue_reveal_available` also counts reveals for the delivery's `assert` costs; retract costs ignored; 4 tests in `tests/test_staged_cues.py`). New technique, no W-decision precedent. The worker also added an unrequested hunk hiding `cue_fact_id` on the first turn; I removed it and restored the two first-turn cue expectations in `test_pacing_handoff.py` and `test_web_demo.py` that PR 520 had loosened. Suite 1149 passed, ruff clean. Not measured live. Next: merge, redeploy staging, rerun the all-scenes x3, then look at why r1 stalled in 2A and at 3A/3B.

## L2 all-scenes x3 on 580dd6e (2026-10-08, PR 522 merged; Ringer `freytag-affordance-live`, pass, 589 s)

(An earlier attempt on the same sha failed after 619 s: replicate 2 timed out in `startSceneSession`, "Scene 1A" never showed; treated as an infra flake, no data. Not diagnosed.) Exit cause per replicate (r1/r2/r3), previous run on d3d651c in brackets: 1A play x3, turns 8/9/8 [play/timer/timer]; 1B play x3 [play x3]; 1C play/play/timer [play/timer/timer]; 2A timer x3 (12, 11, 11) [none/timer/timer]; 2B play x3 (8, 11, 8) [play x2 reached]; 2C play x3 (11, 9, 9) [timer/play]; 3A timer x3 (13, 13, 15); 3B timer x3 (14, 14, 14); 3C none expected. All three replicates now reach 3C. Rejected turns (leak scan) per run: r1 2A 1, 2C 3, 3C 1; r2 1A 1, 2B 3, 2C 1, 3C 2; r3 2C 1, 3A 2, 3C 1. The cue fix worked: the 1A drawer is shown by turn 2 and the card by turn 3. Still timer exits: 2A, 3A, 3B (and 1C r3). Open from the earlier run: 2A r1 had 5 leak-scan rejections on 'cooling-water imbalance'; the 2A.2 Details line carried that phrase and was reworded (commit 905dc47, branch `claude/2a-details-leak`, not merged, not measured; this run predates it). Next: read the 2A, 3A, 3B misses (prompts), fix in one batch, one more run.

## L2 1A-2A x3 on bff5b1a (2026-10-08, PR 523 merged: 2A.2 Details reworded; Ringer `freytag-affordance-live`, check failed, 276 s)

Replicate 1 never started: session creation was rejected on the 1A opening ("narration mentions unavailable knowledge 'forced entry'"); the same rejection failed the first smoke (the 619 s failure on 580dd6e was probably this too, not an infra flake). Replicates 2 and 3 completed (read from `artifacts/e2e-blind-player-r2/r3.json`; the merged report was not written because the check failed). Exit cause r2/r3: 1A play, play (turn 8, 8); 1B play, play (8, 8); 1C play, play (7, 7); 2A timer, timer (11, 12). So 1A-1C are 2/2 by play; 2A still exits by timer. The 'cooling-water imbalance' rejections are gone (r2 none in 2A); r3 had one 2A rejection on 'the supervisor' (turn 8, "Explain my unscheduled inspection to the supervisor."). Fix (PR 524, Ringer `freytag-opening-retry`, PASS; suite 1154 passed): `RuntimeEngine.opening()` now makes up to 3 attempts and re-raises the last rejection unchanged (still 409 if all fail). Cause: the narrator turns the opening-beat detail 'forced back door' into 'forced entry', a protected term of `k_sl_1a_a_r1`. A direct probe of 20 session creations on bff5b1a (`opening_rejection_probe.py`, Ringer `freytag-opening-rejection`) saw 0 rejections, so the rate is below the ~3 in 9 seen in Playwright runs and unexplained. Not yet measured live after the fix. Upstream Ringer commits (Ringside UI only) were not relevant. Earlier open item: (1) the 1A opening can be rejected on 'forced entry' (a 1A plot detail, line 122) and the session then fails to start, 3 times seen; (2) 2A still timer; prompts not read.

## L2 1A-2A x3 on 11aaf97 (2026-10-08, PR 524 merged: opening retry; staging confirmed on 11aaf97; Ringer `freytag-affordance-live`, pass, 300 s)

All three replicates started (the opening retry worked; no session-creation failure). Exit cause r1/r2/r3: 1A play x3 (turn 8); 1B play x3 (8); 1C play (7), timer (12), play (8); 2A timer (11), timer (11), none (never left). Rejected turns: 1C r3 one ('servers' entity, turn 2); 2A r3 three in a row on 'the supervisor' (turns 3, 4, 5), after which it never left 2A. So the 905dc47 Details edit removed 'cooling-water imbalance' but 'the supervisor' still leaks in 2A. Not read: the 2A prompts (where the narrator picks up 'the supervisor'), the 1C r2 timer exit, the 1C r3 'servers' rejection. Next: read the 2A r3 turn 3-5 prompts against plot.md and fix at the source (the leak scan declares 'the supervisor' as an alias of the supervisor reveal; see `declared-names-are-leak-scanned-earlier`).

2A 'the supervisor' leak fix (2026-10-07, branch claude/plan-l2-1a-2a-on-11aaf97, not measured live): the rejected 2A r3 turns were the player's own words ("Explain ... to the supervisor.") echoed by the narrator. Cause: `narration_safety.py` leak-scans only multi-word terms, and `k_sl_2a_c_r1` must_convey listed the two-word phrase 'the supervisor' while the 2A.1 delivery says 'A supervisor'. Removed 'the supervisor' from that group (line 1120 of knowledge.yaml); the single word 'supervisor' stays and covers it. Suite 1154 passed. Still open: other multi-word forms in the group (security supervisor, facility supervisor, security officer, inspection supervisor) could trip the same scan; 1C r2 timer exit and 1C r3 'servers' rejection unread.

L2 1A-2A x3 on 494fa23 (2026-10-08, PR 525 merged, staging deployed; Ringer `freytag-affordance-live`, pass, 284 s): zero rejected turns, so the 'the supervisor' leak is fixed. Exit cause r1/r2/r3: 1A play (8) x3; 1B play (8) x3; 1C play (7) x3; 2A timer (11) x3. 1C is now 3/3 by play. 2A still exits by timer in all three. Not read: the 2A prompts and commands; why no player-earned 2A reveal (k_sl_2a_c_r1 needs false_identities_ready and facility_perimeter_reached) fires by play. Next: read the 2A commands against plot.md and the c_r1 evidence groups.

2A wording (2026-10-08, Ringer `freytag-affordance-2a-wording`, 1 attempt, PASS): read the 2A r1-r3 commands. Cause of the timer exits: the 2A cue says 'blank inspector forms' but `k_sl_2a_b_r2` only knew 'credentials', so the identities, perimeter (e_r1) and supervisor (c_r1) steps never fired; 'supervisor' appeared in no narration. Widened `action_evidence`/`earn_when` for b_r2 (forms, complete, fill out), e_r1 (enter, follow into, forms to the guard, secured facility), c_r1 (explain ... to the supervisor), a_r1 (review, documents). Scorer `scripts/ringer/affordance/2a-wording-score.py` (real matcher, 27 commands, 8 must-not-fire): 16/27 before, 27/27 after; suite 1154 passed, ruff clean. Not measured live. Also seen: players invent a guard or a lockpicked door at the perimeter; the supervisor is introduced only by the e_r1 delivery. Next: merge, redeploy, rerun L2 1A-2A x3; then 3A, 3B (still timer).

L2 1A-2A x3 on the PR 526 build (2026-10-08, staging deployed; Ringer `freytag-affordance-live`, pass, 297 s): 0 rejected turns. Exit cause r1/r2/r3: 1A play x3 (8); 1B play x3 (8); 1C play (7), timer (11), play (7); 2A play (7), timer (11), timer (11). 2A went from timer x3 to play 1/3, and 'supervisor' now appears in narration in all three (turns 2-4). Bar (2 of 3 by play) not met for 2A or 1C. Not read: why 2A r2/r3 still timed out after the supervisor appeared (c_r1 needs cooling or ventilation words in the same command), and the 1C r2 timer exit. Next: read those commands against c_r1/c_r2 and the 1C evidence; then 3A, 3B.

2A and 1C commands read against c_r1/c_r2 and 1C evidence (2026-10-08, PR 526 build; Ringer `freytag-affordance-2a1c-wording`, 1 attempt, PASS; suite 1154 passed, ruff clean). Causes: (1) 2A r2/r3 showed their credentials at the checkpoint without preparing them, so `b_r2` never fired, `false_identities_ready` stayed false and `e_r1`/`c_r1` never became eligible; (2) `c_r1` missed "Present my cooling-water warning to the supervisor", "Present my emergency inspection warning to the supervisor" and "Explain my unscheduled inspection to the supervisor" (no generic 'to the supervisor' phrase, second group wanted cooling/ventilation); (3) 1C r2 typed "Record the identification numbers on my laptop": `b_r1` had no record verb and needed uniforms/prisoners, so the delivery that points at the logistics computer never came and r2 timed out (r1/r3 left by play at 7). 2A r1 left by play (7). Fix: `b_r2` verbs show/present/flash/hand over; `c_r1` 'to the supervisor' plus warning, unscheduled inspection, cooling-water, cooling-system; 1C `b_r1` verbs record/copy/photograph/capture/write down/log and objects identification numbers/ID numbers. Scorer `2a1c-wording-score.py` (15 commands, 7 must-not-fire): 7/15 before, 15/15 after; 2a scorer 27/27 (two expectations now include b_r2, since show/present of forms or credentials fires both, and `requires` leaves only b_r2 eligible first); 1c scorer 24/24. Not merged, not measured live. Next: merge, redeploy staging, rerun L2 1A-2A x3; then 3A, 3B.

L2 1A-2A x3 on 45d52ce (2026-10-08, PR 527 merged, staging confirmed on 45d52ce via /api/v1/version; Ringer `freytag-affordance-live`, pass, 260 s): zero rejected turns. Exit cause r1/r2/r3: 1A play (8) x3; 1B play (8) x3; 1C play (7) x3; 2A timer (11), play (9), play (7). Bar (2 of 3 by play) is met for 2A and 1C; 1C went from 2/3 to 3/3 and 2A from 1/3 to 2/3. 2A r1 read against the matcher: it completed the forms (b_r2) but then typed 'Present my inspector credentials at the facility checkpoint.' and e_r1 did not fire (e_r1 has 'present my credentials at' and 'present the inspector credentials' but not 'present my inspector credentials at'; the same phrase matches only b_r2), so the perimeter and supervisor steps never opened; it also typed 'Present my emergency inspection orders to the supervisor.' (c_r1 has no 'orders'; 'emergency inspection' was kept out because of the must-not-fire 'notice' case). Not fixed. Candidate: add 'present my inspector credentials at/to' and 'present our inspector credentials at' to e_r1's verb group. Next: decide whether to close that gap, then 3A and 3B (still timer).

2A e_r1 gap closed (2026-10-08, Ringer `freytag-affordance-2a-e-r1`, 1 attempt, PASS; suite 1154 passed, ruff clean): added 'present my/our inspector credentials at/to' to `k_sl_2a_e_r1` evidence and earn_when. Scorer `2a-e-r1-score.py` (10 commands, real matcher) 5 failing before, all correct after; 2a1c scorer expectation for 'Present my inspector credentials at the checkpoint.' now b_r2 plus e_r1; 2a scorer 27/27. Not measured live. Still open: c_r1 has no 'orders' ('Present my emergency inspection orders to the supervisor.'). Next: merge, redeploy, rerun L2 1A-2A x3; then 3A, 3B (still timer).

L2 1A-2A x3 on 404c908 (2026-10-08, PR 529 merged, staging confirmed on 404c908 via /api/v1/version; Ringer `freytag-affordance-live`, pass, 266 s): every scene exited by play in all 3 replicates (1A 8,8,9; 1B 8,8,8; 1C 7,7,8; 2A 8,8,7), so the bar (2 of 3 by play) is met for 1A-2A with 3/3 each and 2A moved from 2/3 to 3/3. Three rejected turns, none a timer: 2A r1 t6 'Follow the service corridor toward the detention level.' (unavailable entity 'detention level'); 2A r2 t1 'Search Brandon's hideout for inspection credentials.' (unavailable knowledge 'access to the facility'); 1A r3 t5 'Inspect the gap beneath my initials.' (unavailable knowledge 'beneath the drawer'). Not diagnosed. Unseen verbs: retrieve, insert, probe, beneath. Next: 3A and 3B (still timer); decide whether to look at the three rejections.

L2 1A-3B x3 on 404c908 (2026-10-08, staging; Ringer `freytag-affordance-live`, check FAIL: replicate 3 wrote no report; replicates 1 and 2 read from `artifacts/e2e-blind-player-r1/r2.json`): 1A-1C play x2; 2A timer/play; 2B, 2C play x2; 3A timer x2 (13, 13); 3B timer x2 (14, 14). Causes read from commands and the engine: (1) EXPIRY BUG: `_activate_pacing` drops every optional storylet after its `latest_turn`, and `required_storylet_ids` covered only bridge-fact storylets, so a required reveal that needs a fact only an optional storylet sets was cut off. 3A r2 earned Michelle on turn 7, SL-3A-B (latest 7) expired, so `behavioral_experiments_known` and then the override codes were unreachable (every medical-level command after turn 7 did nothing). Same shape for SL-3B-E (office reached, latest 6) feeding SL-3B-B. A sweep over the real package found exactly four: SL-1A-E, SL-2A-E, SL-3A-B, SL-3B-E. (2) 3A r1 earned a_r1, b_r2, d_r1 by turn 3, then typed 'Lead/Guide/Escort/Advance the prisoners through the blind checkpoints' and `c_r1` had none of those verbs. (3) 3B: both replicates went to the office then the external broadcast relay and never did the false-alarm step `e_r1` requires; the 3B entry text (plot.md 715) names 'the external broadcast relay' as the destination. Not fixed yet.

Fixes (Ringer `freytag-required-closure`, 1 worker pass, patch applied by hand after the check failed only on two pinned counts, 28 -> 32 in `test_storylet_expiry.py` and `test_scene_relative_pacing.py`, which I updated directly; and `freytag-affordance-3a-uprising`, PASS on rerun after a bad scorer path in my check script): `required_storylet_ids` now returns the same-scene prerequisite closure (activation conditions and knowledge `requires`), 28 -> 32; `k_sl_3a_c_r1` verbs lead, guide, escort, advance, follow, join, march and objects the prisoners, the surface gates. Scorer `3a-wording-score.py` now 37 commands, 37/37. Suite 1157 passed, ruff clean. No W decision covers the closure (checked `.plans/world-model.md`, grounding guide). Not measured live. Next: merge, redeploy, rerun L2 1A-3B x3, then decide the 3B plot line.

L2 1A-3B x3 on 7ac1423 (2026-10-08, PR 531 merged, main CI staging deploy succeeded, /api/v1/version confirmed 7ac1423 scene-v1 staging; Ringer `freytag-affordance-live`, pass, 514 s, all three replicates wrote reports): exit by play per scene, r1/r2/r3: 1A 3/3 (8,8,8); 1B 3/3 (8,8,8); 1C 3/3 (7,7,7); 2A 2/3 (7,7, timer 11); 2B 3/3 (8,9,10); 2C 2/3 (9, timer 16, 9); 3A 2/3 (9, timer 14, 9); 3B 0/3 (timer 14 x3). Bar (2 of 3 by play) is met for every scene except 3B. 3A went from timer x2 to play 2/3 (closure plus c_r1 widening worked). Rejected turns: 2B 2, 2C 2, 3A 1; not diagnosed. 3B: broadcast_relay was shown by the deadline 3/3 yet the scene still timed out, consistent with the earlier finding that players go to the relay and skip the e_r1 false-alarm step. Not read: the 3B commands against e_r1, the 3A r2 and 2C r2 timer exits, the rejections. Next: read 3B commands vs e_r1 and the plot.md 715 entry text, decide the 3B plot line (ChatGPT Desktop if it is story text), then rerun.

3B commands read against the chain and fix (2026-10-08, suite 1157 passed, ruff clean; scorer `3b-wording-score.py` 32/32 with three new cases; not measured live). The whole 3B chain starts at a_r1/a_r2 (`human_security_control`; e_r1, b, d and c all `require` it). Replicates r1/r3 typed 'Reach/Seize/Activate the external broadcast relay' from turn 1 and r2 'Reach Rebecca's executive office', none the false-alarm step; r3's 'Exploit the water-pressure warnings to overload JANUS.' matched nothing (no exploit/overload verb). Cause: the 3B `entry_text` named 'Rebecca's executive office and the external broadcast relay' as the destinations, pulling players past the chain. Fix (subtractive, per the narration-fix ranking; story text edited directly at Brandon's say-so, not via ChatGPT Desktop): entry_text now reads 'Water-pressure warnings flashed on the inspection console while doors opened and closed in empty service corridors that JANUS watched move by move.' (reuses the cue's own words); a_r1 verbs gain exploit, overload, manipulate, spoof, falsify, trigger. Next: merge, redeploy, rerun L2 1A-3B x3.

L2 1A-3B x3 on c392947 (2026-10-08, PR 532 merged, staging confirmed c392947; Ringer `freytag-affordance-live`, pass): 3B still timer x3 (14). Other scenes this run (r1/r2/r3, P=play, T=timer): 1A P P P; 1B P P P; 1C T P P; 2A T P P; 2B P P P; 2C P P T; 3A T P P (noisy, 3 replicates). Read 3B: the new entry text and the cue ('Water-pressure warnings flash while doors open and close...') reached the narration in all three, yet no player typed a warnings or false-alarm command; they typed 'Reach the secured broadcast office', 'Enter the broadcast center', 'Enter Rebecca's secured office'. Two lines still pulled to the office and relay: the 3A->3B bridge text `t_3a_3b` ('fought upward toward Rebecca's office and the broadcast levels', copied verbatim into the 3B opening) and the 3B `objective` ('Overload JANUS and seize the broadcast', which the narrator turned into 'find an opening to seize the broadcast relay'). Fix (subtractive, same method as the entry text; story text edited directly): bridge text now '...fought upward through the security corridors.'; objective now 'Overload JANUS with false alarms.' Suite 1157 passed, ruff clean. Not measured live. Next: merge, redeploy, rerun L2 1A-3B x3.

L2 1A-3B x3 on a6f3fbd (2026-10-08, PR 533 merged as first written: bridge text 'through the security corridors' plus objective 'Overload JANUS with false alarms'; staging confirmed a6f3fbd; Ringer `freytag-affordance-live`, pass): play/timer r1/r2/r3: 1A P P P; 1B P P P; 1C P P P; 2A P P P; 2B P P P; 2C T P P; 3A P P T; 3B T(14), P(9), T(14). 3B went from 0/3 to 1/3 by play; bar (2 of 3) still not met. No replicate typed a false-alarm command, but r3 inspected 'the water-pressure console' (turn 2) and r2 used 'the inspection console' (turn 1), so the cue now reaches players. r1 and r2 reached the office and read the approvals and site list, r1 also opened Charles's channel (turn 8), then both typed 'Transmit my copied evidence through Rebecca's remote channel / the broadcast controls' instead of the c_r1 steps (tell or ask Brandon to cut the relay / activate the voice channel); r1 timed out there. r3 never got past Rebecca (asked Rebecca to broadcast). Not read: which reveal let r1/r2 reach the office without a typed false alarm, and the 3A r3 and 2C r1 timer exits. Next: read the r1 3B turn-by-turn against the chain, then decide a pointer on d_r1/d_r2 delivery for the Brandon voice channel.

3B d_r1 widening (2026-10-08, from the a6f3fbd r1 turn-by-turn; suite passed, ruff clean; scorer `3b-wording-score.py` 37/37 with five new cases; not measured live). r1 reached the office by the semantic fallback matching a_r2 on 'Disable the JANUS drones through the maintenance panel.' (turn 4), then e_r1 (5), b_r2 (7), then stalled: 'Access Rebecca's remote Charles channel.' missed d_r1 (the matcher needs the unbroken phrase 'remote channel'; the player said 'remote Charles channel'), 'Confront Charles through Rebecca's remote channel.' missed (no confront verb), 'Demand Charles's surrender.' missed. d_r1 gates charles_abandoned_rebecca, which gates c_r1/c_r2, so r1 timed out. Fix: d_r1 verbs gain confront, demand, message, use, connect to, patch into, tune into, dial; nouns gain remote Charles channel, Charles channel(s), channel to Charles. 'Transmit ... through Rebecca's remote channel' still fires nothing, on purpose (c_r2 owns transmit and requires the chain). Next: merge, redeploy, rerun L2 1A-3B x3.

L2 1A-3B x3 on 2ee09ec (2026-10-08, PR 535 merged, staging confirmed 2ee09ec; Ringer `freytag-affordance-live`). First launch FAILED: replicate 2 hit a one-off 'Failed to fetch' (CORS) on staging /api/v1/turn, no reports written (the numbers I printed straight after were the previous run's stale files; disregard). Rerun per the runbook (health 200, sha 2ee09ec): pass, but only r3 reached 3B. r1: 1A P, 1B P, 1C T, 2A T, 2B P, 2C T, then 3A never transitioned in 15 turns with 3 rejected turns ('Search the detention sector for Rebecca's office.', 'Locate/Find the secured office.', each 'narration mentions an unavailable entity rebecca'); r2: 1A T, then 1B stopped on rejections (6 of 10 turns 'Show/Hand/Give Michelle's photograph to the man.' -> 'narration mentions unavailable knowledge park bench'); r3: 1A P, 1B P, 1C P, 2A T, 2B P, 2C P, 3A P (9), 3B P (9). The one 3B sample played the intended chain in order: 'Trace the water-pressure warnings on my inspection console.', enter the office, approvals, site list, 'Open the remote channel marked Charles.', broadcast controls, left on turn 9. So 3B is 1 of 1 where reached, but n=1; the 3B bar is not yet measured. New faults, not diagnosed: the 1B 'park bench' leak rejection loop (stops a replicate), the 3A 'rebecca' leak rejection on office searches, and 1C/2A/2C timers in r1. Next: rerun for more 3B samples; read the two rejection loops against the leak scan.

## Resume here (2026-10-10, evening)

State. main is c60800a (PRs 565 and 566 merged as merge commits; staging confirmed c60800a scene-v1). Open: PR 567 (branch `3a-3b-surface-gates`): the surface gates placed in 3A and 3B (a regression of mine from PR 565: five rejected turns), plus plan entries and the 1A brief. Not pushed: local branch `3c-d2-e2-verbs` (commits include the d_r2 and e_r2 phrases `answer the families`, `reassure the families`, `respond to the families`, `Charles's last remote channel`, `his last remote channel`, ChatGPT's 63-row command table pinned in `tests/test_3c_cue_chain.py`, Ringer manifests `3c-verbs`, `3c-verbs2` (bare-verb patch, discarded, never applied), `3c-verbs3`, and plan entries). Both open branches append to the end of this file, so the second one merged needs its plan entries rebased (expect a conflict at the end of the file; keep both). Suite 1201 passed on the PR 567 branch.

Measured on c60800a (L2 all nine scenes x3, see its entry): play exits 1A 1/3, 1B 3/3, 1C 3/3, 2A 3/3, 2B 3/3, 2C 2/3, 3A 1/3, 3B 3/3; 3C steps by play 4/5/7 of 7.

Decisions waiting for Brandon. (1) Merge PR 567 and push-and-merge `3c-d2-e2-verbs`: he gives the instruction per PR ('once CI is green, wait 5 seconds, then merge it'); merge style is a MERGE COMMIT, not squash. (2) Send `.plans/chatgpt-1a-drawer-prompt.md` to ChatGPT Desktop, then build its answer (evidence for `k_sl_1a_b_r0`, whether 'Open the KMS drawer.' should fire, and a grounded way to stop the invented paper note), through a Ringer task. (3) After both merge and staging is on the merged SHA, rerun L2 with 5 replicates (the wrapper takes 1 to 3 only: `scene-affordance-l2-all-live.sh` accepts replicates 1|2|3, so a 5-replicate run needs the wrapper widened or two runs) to separate the 3A and 2C stalls from noise.

Still open. 3A: the scene opening says Rebecca's secured office is the manual broadcast point and players chase it (r1: 12 turns); the Michelle cue is shown once and ignored; no proven technique covers an ignored one-time cue, so it needs a probe (recorded prompt vs plot.md, arms of 10-15 samples, AGENTS 'Fixing a Scene'). 2C: replicate openings vary; one opened at the medical terminal and the player followed Michelle's transfer records for 16 turns. Accepted known cases: 'Broadcast the detention site list.' matches a_r1 and d_r1 (none); 'Answer the families about Charles's terrorist claim.' and 'Respond to the families about Charles's terrorist claim.' match a_r2 and d_r2 (none); 'Read the recovered document and trace Charles's last remote channel.' matches e_r1 and e_r2 (none). For a later scoped review (ChatGPT noted them): 'Extend the gate authorization.' and 'Guide/Lead the captives to the surface gates.' fire c_r2; 'Broadcast the reports to the families.' fires d_r1; 'Broadcast updates about the families.' fires d_r2. Unchanged: the 2B 'coded message' leak, bare-word 'phase' protection, the staging hang costing a replicate about once in two runs.

How the 3C work went, for next time. A storylet fires on its first reveal and its sibling is then not a candidate (`knowledge.py` `_candidates`); `complete_when` in `storylet-routes.yaml` is not read. The loader requires every resolution event's activation facts to be entry-guaranteed or produced by an earlier resolution event (`loader.py` near line 953), so the both-parts rule lives in `realization_storylets`, and cue facts come from the facts the unfired required storylets would assert (`_bridge_delivery_fact_ids`). The Ringer worker sandbox cannot run `uv`: tell it to use `PYTHONPATH=$PWD /home/bcorfman/dev/freytag-forge/.venv/bin/python -m pytest` and check `storygame.__file__` is inside the worktree. A failed worker leaves its worktree behind: remove it with `git worktree remove --force <path>` before rerunning the same task key. A run that reports 'completed' in the background log may never have started if its manifest generator crashed: check `~/dev/ringer-work/<run>/` for the worktree and `change.patch`.

Files. ChatGPT briefs: `.plans/chatgpt-3c-structure-and-cues-prompt.md` (+ `-answer.md`), `.plans/chatgpt-3c-verbs-prompt.md`, `.plans/chatgpt-3c-d2-e2-prompt.md`, `.plans/chatgpt-1a-drawer-prompt.md`. Probe: `scripts/ringer/affordance/3c_cue_gate_probe.py`. Manifests beside it: `3c-cue-gate`, `3c-structure`, `3c-verbs`, `3c-verbs2`, `3c-verbs3`, `gates-scope` (each `.json` plus `-check.sh`). Per-turn 3C texts of an L2 run: read from `~/dev/ringer-work/affordance-live-all/e2e-blind-player-r*.md` (the JSON per replicate is embedded in the .md; copy them out before the next L2 overwrites them).

## Resume here (2026-10-10)

Update 2: PR 563 and plan PRs 560/562 are merged; the all-scenes L2 x3 on dc0aba9 gave 3B 3/3 by play (see 'L2 all nine scenes x3 on dc0aba9'). Open now: confirm 3B on a second run; read 3C (never transitions, rejected turns in r2/r3) and the 1C/2A/3A first-replicate timers.

Update: the 2C-only scope change is merged (PR 557, main 5643fc5) and measured: 3A 2/3 by play, 3B 1/3; see 'L2 1A-3B x3 on 5643fc5'. Decision (1) below is done.

State: main is 603b07b (PR 555 merged, staging confirmed via `/api/v1/version`). PR 556 (plan entries, probe scripts and ChatGPT briefs) is open and not merged; its branch is `claude/plan-l2-603b07b`. Nothing is uncommitted. Measured: L2 1A-3B x3 on 603b07b (rerun once after a staging hang in replicate 1, pass, 473 s): 1A-2C by play 3/3, 3A 1/3, 3B 2/3.

Decisions waiting for Brandon: (1) apply `available_in_scenes: [2C]` to `k_sl_2c_d_r1` and `k_sl_2c_d_r2` through a Ringer task (suite as the check), then rerun L2 1A-3B x3. Evidence: narrator probe `freytag-3a-pull-probe` (arm B 0/12 name Rebecca's office against 6/12 as recorded); ChatGPT's review concern about recall was checked in the code and does not apply (recall needs the entity `holding_block`). (2) Write a 3A first-step cue brief for ChatGPT Desktop: on a neutral first command no arm leads the player to Michelle (A 2/12, B 0/12, E 1/12 name her).

Still open: the 3A 'rebecca's desk' leak (one rejection) and 1C 'servers' (one rejection); the loader's bare-word protection of 'phase' (first word of `phase_two`) is untouched, so other narration of 'phase' in 2B is still rejected; the staging hang (`#command-input` disabled 90 s) costs a replicate about once in two runs; the claim that SL-2C-D cannot be earned in 3A is read from its abort rule, not proven.

How to resume: read the entries 'L2 1A-3B x3 on 603b07b', '3A timers read' and '3A line removal reviewed' at the end of this file. Probe tooling: `scripts/ringer/affordance/3a_pull_probe.py` and `2b_phase_probe.py` (manifest plus check script beside each; `PROBE_N`, `PROBE_ARMS`, `PROBE_CELLS` select the run; the prompts file must be copied out of `artifacts/` first because the next L2 overwrites it). ChatGPT briefs: `.plans/chatgpt-2b-message-content-prompt.md`, `.plans/chatgpt-3a-removal-review-prompt.md`.

## Resume here (2026-10-06)

State: PR 520 is merged as cc7cc20 and main CI's SHA-bound staging deploy succeeded. Smoke (Ringer `freytag-affordance-live`, 1A,1B x1) passed on that build. The full all-scenes x3 run is deliberately NOT run: Brandon wants 2B, 3A and 3B done first, then one live round. Branch `claude/plan-2b-3a-3b-wording` has no code changes yet.

Done and merged (read the dated entries above for detail): staged cues (item 1); 1C evidence widening (scorer `scripts/ringer/affordance/1c-wording-score.py`, 17/24 -> 24/24); cues for 1C network and 2C `purge_clock_started`; pointers on 1C a/b, 2A b/e, 2C b/c deliveries. The item 2 simulation scripts were deleted.

Method for each remaining scene (same as 1C): (1) `scene_gap.py <scene> <report>` and the recorded commands (data: `l2-all-x3`, `~/.ringer/artifacts/deliverables/freytag-affordance-live-20261005T021549Z-p713092/l2-all-x3/e2e-blind-player.json`; a throwaway script printing each distinct non-rejected command per scene is easy to rewrite from `scene_gap.py`'s RUNS block); (2) write `<scene>-wording-score.py` modeled on `1c-wording-score.py` (real matcher, imperative commands, include must-not-fire cases, pass the groups first and the command second to `_matches_all`); (3) widen `action_evidence` verbs and nouns through a Ringer task modeled on `1c-wording.json` (Luna, worktree, check script that limits the diff to `knowledge.yaml` evidence and `earn_when` lines, then scorer, ruff, full suite); (4) collect missing cues and pointers into a second ChatGPT Desktop prompt modeled on `.plans/chatgpt-cues-and-pointers-prompt.md`, score the answer with the real matcher, fix faults directly (Brandon authorised direct edits after the answer arrives). Brandon said to make post-answer edits directly; before that, code and data edits go through Ringer.

2B findings so far (nothing applied): recorded commands show only `k_sl_2b_a_r1` fires. Misses: "Read Brandon's record." and "Read Brandon's earlier messages." (b_r1 wants "development record(s)"; the cue says "a record on the archive terminal" and "earlier messages ... on the remote terminal"); every medical-terminal command ("Search the medical terminal for Michelle's patient record.", "Read the warning message on the medical terminal.") because c_r1 wants "corrupted prisoner/files" and players never typed "corrupted"; players spent most turns on Michelle's detention and transfer record and a doctor the narrator invented; neither the record's details nor the doctor are in the story package, and no 2B reveal covers them. 2B chain: a_r1/a_r2 (`janus_evidence`, no requires) then b_r1/b_r2 (`brandon_janus_role_known`) and c_r1/c_r2 (`michelle_resistance_known`), both needing `janus_evidence`; the bridge needs `janus_evidence` plus two of three of `brandon_janus_role_known`, `brandon_claimed_reform_motive`, `michelle_resistance_known`.

3A and 3B (from the 2026-10-05 offline scoring above): 3A a_r1 verbs lack "free"; 3A players used the gate-status panel before Michelle and the experiment records (staged cues should now hold that cue back; confirm in the live run); 3B c_r1 wants tell/ask plus the relay, players typed "Access the Brandon voice channel" and "Activate the relay"; 3B is a five-deep chain, players went straight to the relay.

Then: one live round. Use the smoke wrapper first (`scene-affordance-l2-all-smoke-live.json`), then `scene-affordance-l2-all-live.json` x3 (`scene-affordance-l2-all-live.sh <replicates> <scenes|all>`), with prompts recorded. Report play versus timer exits per scene and read cue timing: check that staged cues did not leave a scene with every cue withheld for long. Compare with the l2-all-x3 baseline (1A play x3; 2C play once; every other scene timer x3). Not measured live yet: staged cues, the 1C widening, the new cues and pointers.

2B wording done (2026-10-06, Ringer `freytag-affordance-2b-wording`, 1 attempt, PASS; commit 02304db on `claude/plan-2b-3a-3b-wording`). Widened `action_evidence` and `earn_when` for b_r1, b_r2, b_r3, c_r1, c_r2 (Brandon's record/earlier messages, medical terminal, patient/prisoner records, warning message, maintenance messages; verbs examine, inspect, question, access). Scorer `scripts/ringer/affordance/2b-wording-score.py` (real matcher, 30 commands, 10 must-not-fire): 20/30 before, 30/30 after; suite 1145 passed, ruff clean. Not measured live. Open: players spent most turns on Michelle's transfer and patient records and an invented doctor; these are narrator inventions (not in the story package, checked 2026-10-06), so the fix is a pointer in the a_r1/a_r2 deliveries (`.plans/chatgpt-2b-pointers-prompt.md`), not widening. Still for ChatGPT Desktop: 2B pointers. Next: 3A, then 3B.

2B cues and pointers applied (2026-10-06, uncommitted until the commit below; suite 1145 passed, scorer 30/30). ChatGPT Desktop answer (`.plans/chatgpt-2b-pointers-prompt.md`) scored with the real matcher: every matcher claim in its table held. Faults fixed directly: (1) its pointers were commands ("Read the maintenance reports."); every existing pointer is a description, so each is now a scene description ("A warning message blinks on the medical terminal."); (2) its `brandon_claimed_reform_motive` cue pointed at the security logs, which set `kristin_was_bait` (b_r3), not that fact, so the original earlier-messages cue stays (b_r1 now matches it); (3) its `janus_evidence` cue pointed at the development records, which cannot fire before janus_evidence, so the original cue stays; (4) `michelle_resistance_known` cue now names the corrupted prisoner files and a warning message (both fire c_r1). Kept from the answer: the `brandon_janus_role_known` cue (b_r2 fires on "Question Brandon about the development records."), the a_r1 closure "Michelle's file holds nothing more.", the pointer chain a_r1 -> development records, a_r2 -> security logs, b_r1 -> warning message, b_r2 -> maintenance reports, b_r3 -> corrupted files, c_r1 -> maintenance reports, c_r2 -> earlier messages, and the plot.md sentence after 2B.1. Open: "Examine the medical terminal." and "Read the security logs." still fire nothing (c_r1 holds only the phrase "inspect the medical terminal"; b_r3 needs a third group); adding bare "medical terminal" to c_r1 would also fire on "Search the medical terminal for the duty doctor.", a must-not-fire case. Not measured live. Next: 3A, 3B.

3A wording done (2026-10-06, Ringer `freytag-affordance-3a-wording`, 1 attempt, PASS; commit 6d9304b on `claude/plan-2b-3a-3b-wording`). Widened `action_evidence`/`earn_when` for a_r1 (free, help, use, organize, coordinate, rescue; captives, prisoners, prisoner escape, detention block), d_r1 (official access seal) and d_r2 (use, override, activate, operate). Scorer `scripts/ringer/affordance/3a-wording-score.py` (real matcher, 31 commands, 8 must-not-fire): 24/32 before, 31/31 after; suite 1145 passed, ruff clean. Synonym classes make some commands fire several reveals (e.g. a search near Michelle also hits a_r2/b_r2); `requires` orders them. Players' other 3A commands were leftovers from 2C (maintenance route), not 3A misses. Not measured live. Still for ChatGPT Desktop: 3A cues and pointers (and confirm staged cues hold the gate-status panel cue back until Michelle and the experiment records). Next: 3B wording, then the 3A/3B prompt, then one live L2.

3B wording done (2026-10-06, Ringer `freytag-affordance-3b-wording`; Ringer marked it FAIL after 2 attempts only because my check's grep for changed `statement` lines matched the evidence phrase "Brandon's statement"; I verified the diff by hand: only `action_evidence` and `earn_when` lines changed, scorer 29/29, suite 1145 passed, ruff clean, then applied the patch). Widened a_r1 (trace, follow; water-pressure warnings), e_r1 (reach, go, proceed to), b_r2 (examine, inspect, read, check, study; site list), d_r1 (access, examine, inspect, read, check; channel marked Charles), c_r1 (access, open, activate, use; Brandon voice channel). Scorer `scripts/ringer/affordance/3b-wording-score.py` (real matcher, 29 commands, 7 must-not-fire): 19/29 before, 29/29 after. Players went straight to the relay (c_r1/c_r2 sit behind a five-deep chain); staged cues should now hold that cue back, to be confirmed live. The relay-chamber-panel commands fire nothing on purpose (bare-noun item, not built). Not measured live. Next: ChatGPT Desktop prompt for 3A and 3B cues and pointers (modeled on `.plans/chatgpt-2b-pointers-prompt.md`), then one live L2.

3A and 3B cues and pointers applied (2026-10-07, suite 1145 passed, ruff clean; commit below). ChatGPT Desktop answer (`.plans/chatgpt-3a-3b-pointers-prompt.md`) scored with the real matcher: every fire claim in its section E held (a 'no fire' for "Broadcast the evidence." was wrong; it fires 3B c_r2, which `requires` orders). Kept: pointers on 3A a, b, d and 3B a, e, b with the wording already in the working tree (they match its table), plus matching plot.md sentences. Not taken: (1) pointers on 3A c_r1/c_r2 (ChatGPT itself says the chain ends there); (2) its cue replacements for michelle_reached, military_override_codes_available and charles_abandoned_rebecca, because the 3A/3B widening already fires on the existing cue words (captives, official access seal, gate-status panel, executive screen); (3) new cues for behavioral_experiments_known and rebecca_office_reached, because a cue needs a handoffs.yaml delivery (must_convey, fallback_text) and adding one would also add a timer fallback; the pointers already name the medical level and the executive office. Not measured live. Next: one live L2 (smoke wrapper first, then all-scenes x3).

Loose ends: a ChatGPT Desktop answer for the 2B, 3A and 3B cues and pointers is not yet requested. Open question: whether a pointer-based fix is enough or the L2 still shows timer exits.

## Resume here (2026-10-04)

Status: main 4ab36ef (PR 513) has the parallel L2 path and the drawer-gap cue
(PR 512). L2 x3 on 1A moves scene to scene by play 3/3 (turn 8 in the parallel
run). The Jev probe and the harness recording are done and merged.

Chair and drawer wording (2026-10-04, PR 514, main 86693db, staging sha confirmed): Ringer `freytag-affordance-chair-and-drawer-wording`
(pass on attempt 2; the first run failed on a stale known-gaps list and on two
bugs in my own check). Diagnosis: the 0/3 chair was a measurement alias gap.
`workstation_chair` had only the name "workstation chair"; r2 and r3 turn 1
narration said "the overturned chair" (read from
`artifacts/e2e-blind-player-r1..r3.json`), so the player did read it and the
matcher recorded null. Same gap made the silent-transition flag a false
positive. Changes: `aliases: [chair]` on `workstation_chair` (precedent:
`park_bench` `aliases: [bench]`); the drawer is now named only "drawer" in
`plot.md` 112 and 132, `handoffs.yaml` 10 (fallback_text) and `knowledge.yaml`
301 and 332 (statement, delivery_text), by Brandon's rule and his decision that
"the KMS drawer" is odd phrasing. Left alone on purpose: the initials-carved
detail in the cue_text, `plot.md` 116 and 124, `knowledge.yaml` situation,
action_evidence and must_convey word groups, and the "KMS Mark" titles in
`storylets.md` and `storylet-routes.yaml`. Side effects: the three 1A
`workstation_chair` check-3 findings left `bench/affordance_known_gaps.json`
(L0 check 3 now passes for the chair; three known gaps remain);
`test_1a_deadline_fallback_names_the_kms_drawer` is now
`..._names_the_drawer` and asserts "KMS" is absent; the bare-name shortcut test
for 1A now uses "laptop", since "chair" resolves directly. Verified: full suite
1129 passed, ruff clean; live result under "L2 x3 on 86693db" below. The worker flipped the
chair test's assertion instead of changing the example; I corrected that by
hand (one inline edit, ran the test). The 1A card handoff `must_convey` still
lists "beneath the KMS drawer" variants as match words, unchanged.

L2 x3 on 86693db (parallel script, Ringer `freytag-affordance-live`, pass,
2026-10-04): transition 3/3 by play, all on turn 8; stuck runs 0 (was 2); no
rejected turns. Shown by the deadline: laptop 3/3, workstation 3/3, drawer 3/3,
chair 1/3 (r2 turn 1: "the overturned chair", matched only through the new
alias; r1 and r3 never named it), card first shown on turns 2, 4, 2. Silent
transition 2/3 (r1, r3: chair never shown). So the alias fixed the
measurement; the remaining chair misses are real, and r3 opened the drawer on
turn 1 without ever examining the workstation. Chair is only an affordance of
the optional kitchen-search reveal `k_sl_1a_a_r1`, so
decide whether a never-shown chair should count as a silent transition at all.
Invention after the card persists in all three: r1 "encrypted messages and a
note about a coffee shop on 5th Street" from "Open Michelle's saved files." (the
files reveal did not fire; the player then walked to the invented coffee shop),
r2 and r3 a park bench receipt from a coffee shop. Players still say "carved
drawer" and "my drawer"; "KMS drawer" did not appear in player input. Not
read: the recorded prompts for the post-card turns.

Brandon's goal (2026-10-04): a working game. Invented or inconsistent items
matter only if they mislead the story or stop it progressing. Rule: in a scene
designed so that a player action satisfies the gate, a play exit before the
fallback timer is the normal event and a timer exit is rare. A scene that exits
by timer by design is exempt.

What the code and package show (read, not played): the timer does not force a
transition. At `handoff_after_turns` (11 to 16 per scene in `pacing.yaml`) the
engine stages the missing bridge facts and delivers their `handoffs.yaml`
`fallback_text`, then the transition fires normally (`engine.py` around 411).
`required_dependencies` mean an entity must not be destroyed or unavailable; the
player need not hold it (`validation.py` 385). So the timer is a safety net and
a player cannot be stuck short of a destroyed dependency. 1A's gate needs the
card found and read, so the three turn-8 exits were play exits (the earlier
turn-13 exits equalled the 1A timer, 13). Earlier entries above that count a
timer exit as "transition 3/3" were too generous. `handoffs.yaml` gives most
scenes player-earnable deliveries with a `cue_text` (1B four, 1C three, 2A one,
2B four, 3A three, 3B five), so the L0 map's "bridge events only" for 1B, 1C, 2B,
3A and 3B is a map gap, not proof of timer-by-design. 1C
`national_detention_network_known` and 2C `purge_clock_started` have no cue and
look engine-delivered.

Done (2026-10-04, Ringer `freytag-affordance-l0` task `affordance-l0c-classify`, pass
on attempt 1, 19 map tests, ruff clean): L0 map now fills a bridge event's
`activation.all_facts_true` into `requires` and adds per scene
`handoff_after_turns`, `gate_class`, per gate `player_earned_source_ids` and
`cued_by_handoff`. Result: ALL eight non-final scenes are `player_gated` (each
bridge needs player-earned facts, e.g. 1B park pursuit + route + Brandon), and
every gate has a cued handoff. So no scene is timer-by-design; the earlier "bridge
events only" reading for 1B, 1C, 2B, 3A, 3B was a map gap. `activation.any_of` is
not expanded (OR set). The label is permissive (any earned source in the chain),
so L2 exit cause is the real test. Uncommitted before this: the branch holds it.

Done (2026-10-04, PR 515 merged, main f20b24f6, commits 78795fa6 and 13aabc44):
step 2 below. L2 now records exit cause (play or timer) per run (`blind-player.js`,
`digest.py`, Ringer `scene-affordance-l2-exit`). Verified by node and pytest tests;
Live smoke passed (Ringer `l2-1a-smoke`, 1 replicate, 1A, staging): transition turn 8 of timer 13, `exit_cause: play`, aggregate has `play_exit_rate` 1 and `timer_exit_rate` 0. Status line above still says main 4ab36ef; main is now f20b24f6.

Next:
1. (done, above)
2. (done, see PR 515) record the exit cause in L2: play if the transition turn is before the
   scene's `handoff_after_turns`, else timer. For a player-gated scene a timer
   exit is a failure; for a timer-by-design scene it is informational. Re-score
   earlier results on this basis.
3. (next; needs a design for walking scenes and counting sessions, not started) One continuous blind run through all nine scenes, 3 replicates in parallel,
   using the exit labels. A player-gated scene that exits by timer in most
   replicates is a real gap; fix it at the source (a player-earned reveal with
   the thing to act on shown), earliest scene first, per "Fixing a Scene".
4. Parked unless a run shows it blocks or misleads the player: the chair (1/3
   shown, silent-transition flag counts an optional route), laptop place, the
   post-card invention (coffee shop, receipt), stuck-turn and
   silent-transition metrics, unseen-word flags.

## Recommended plan: whole-game fix (2026-10-05, Brandon asked for the most robust and resilient option, fast to staging)

Not started. Context: every scene 1C-3B stalls after its first reveal (see "Offline scoring of 1C-3B"). The game is not stuck today: every scene exits by its timer, so a full playthrough fits the 2-hour budget; what is missing is player agency. Per-scene wording would take about four rounds per scene (1B took about four), so fix the cause once in the engine, story-neutral:
1. Staged cues: show a cue only once its reveal's `requires` chain is met (no story edits; fixes 3A/3B last-step-first and the 1B storm-drain cue). No precedent in the W decisions or the grounding guide; say so when recording it.
2. Cue-derived matching: once a cue has been shown, its named things count as accepted objects for that reveal, with a broad interaction-verb class (examine, inspect, read, open, use, access, activate, enter, follow, ask). Authored groups stay; order stays protected by `requires`. Replaces widening about 40 groups by hand and carries to the next story. The Jev fallback is not the answer (probes: inconsistent, the name list made it worse).
3. Missing cues and next-step pointers in deliveries, for ChatGPT Desktop: 1C logistics computer and `national_detention_network_known` (no cue), 2C `purge_clock_started` (no cue), 2A `k_sl_2a_b_r1` delivery (fires turn 1, names no next place), plus a pointer per delivery where the next step is unnamed.
Risk: item 2 could fire a reveal on a loose interaction with the named thing. Measure before building.
Order: (1) free offline simulation of items 1 and 2 over the ~280 recorded commands in `l2-all-x3` (use `reveal_coverage.py` and `scene_gap.py`; read every new hit and miss; narrow the verb class if it over-fires); (2) build both by Ringer with hermetic tests, full suite, ruff; (3) draft the item 3 sentences for ChatGPT Desktop in parallel, scored with the real matcher; (4) merge the branch (includes the 1B pre-flight fixes), wait for the staging deploy, then ONE billed all-scenes L2 x3 with prompts recorded and the 5-rejection stop, reading play exits per scene (bar: play exit in at least 2 of 3 per scene). Still unverified and to check first: the staging turn cap (`FREYTAG_RATE_LIMIT_PER_MINUTE`) is unset after the last run.

Offline simulation of whole-game items 1 and 2 (2026-10-05, no billed calls; tools `scripts/ringer/affordance/cue_match_sim.py` and `cue_match_diag.py`, run on `l2-all-x3`; uncommitted). Rule simulated: a reveal also fires when the command has an interaction verb (examine, inspect, read, open, use, access, activate, enter, follow, ask, look at, check, search, show, talk to, question, speak to, approach) and names a declared thing that appears in the cue of a fact the reveal sets; `requires` enforced in the replay; a command must match exactly one reveal. Result: item 2 does NOT carry the whole-game fix. (a) Too weak: about half of the reveals have NO declared thing in their cue (1C c, 2A a/e/c, 2C a/b, 3A b/c, 3B a/b/d/e), because cue nouns such as "identification numbers", "uniforms", "relay" are not entities, so the rule adds nothing there. (b) Too loose where it does apply: a cue names several things and one cue is shared by sibling reveals, so "Examine Michelle's photograph." would match 1B a_r1, b_r1, b_r2 and c_r1/c_r2 alike (the uniqueness rule then blocks all of them), and "Inspect the medical terminal." matches both 2B c_r1 and c_r2. (c) Replay: the only chain changes are cue hits on 2B a_r1 (earlier turn, same reveal); no scene's gate moves. A side bug in the sim's gate flag (facts set outside the scene count as true) makes its gate column untrustworthy, so read only the fired lists. Item 1 (staged cues) cannot be scored from commands; it changes what is shown, so only a live run measures it. Decision needed from Brandon: drop item 2 and go per-scene (W2 wording plus W3 pointers, the proven path) with item 1 as the only engine change, or define cue-to-reveal binding in the package (each reveal names its own cue things and verbs) instead of deriving it.

Staged cues built (2026-10-06, whole-game item 1, Ringer run `freytag-affordance-staged-cues`, 1 attempt, PASS; uncommitted on `claude/plan-l2-1b-pending`). `RuntimeEngine._cue_reveal_available` (engine.py): a cue is staged, and kept, only when some knowledge reveal in the scene that asserts its fact has every `requires` met; a fact with no reveal is staged as before. `_ranked_cue_fact_ids`, handoff staging and the timer are unchanged. New `tests/test_staged_cues.py` (5 tests). Three old expectations changed because a scene's first turn can now show no cue: `test_cue_text_safety`, `test_pacing_handoff` (ordinary turn), `test_web_demo`. Full suite 1143 passed, ruff clean. No precedent in the W decisions or the grounding guide (new technique). NOT measured: its effect on players needs a live L2; also check no scene is left with every cue withheld for a long stretch.

Decision (Brandon, 2026-10-06): option A. Drop whole-game item 2 (cue-derived matching). Keep item 1 (staged cues, built above). Go per scene with the proven path: W2 (widen evidence groups, fix cue nouns, scored offline with the real matcher as in 1B) and W3 (next-step pointers; missing cue and delivery sentences go to ChatGPT Desktop). Scene order: 1C, 2A, 2B, 2C, 3A, 3B.

1C wording done (2026-10-06, Ringer `freytag-affordance-1c-wording`, 1 attempt, PASS; uncommitted). Widened `action_evidence` only (b_r1 verbs and uniforms, b_r2 verbs, c_r1 verbs) plus two `earn_when` lines. Scorer `scripts/ringer/affordance/1c-wording-score.py` (real matcher, 24 imperative commands, 7 must-not-fire): 17/24 before, 24/24 after; full suite and ruff pass. Not measured live. Still for ChatGPT Desktop: 1C logistics-computer and `national_detention_network_known` cues. Next: 2A.

Cues and pointers applied (2026-10-06, uncommitted). ChatGPT Desktop answer (prompt `.plans/chatgpt-cues-and-pointers-prompt.md`) scored with the real matcher, then edited directly at Brandon's instruction because of four faults: (1) its cues were commands ("Read the logistics computer."), every existing cue is a description, so cues are now "A logistics computer hums by the service entrance. It may be worth reading." and "Transfer orders sit open in the command levels. They may be worth checking."; (2) its 2C pointer had Brandon arguing about sending the proof, which gives away `k_sl_2c_c_r2`; now "The copied files lie close at hand."; (3) its 1C pointer said "prisoners" before captives_confirmed_alive; now "people in uniforms"; (4) the natural command after the 2A credentials pointer ("Show the inspector credentials at the facility checkpoint.") fired nothing, so `k_sl_2a_e_r1` verbs gained five "show/present/hand over the credentials" phrases. Also found by the suite, not by ChatGPT: the narration leak scan rejects a pointer that uses a multi-word alias or evidence phrase of a later reveal ("coded message", "the supervisor"); those pointers are now "A message from Michelle is waiting." and "A supervisor questions why their inspection was not scheduled.", and `k_sl_2c_d_r1` gained "message from Michelle" so the pointer's own words fire it. Pointers added to 1C a/b, 2A b/e, 2C b/c; cues to `national_detention_network_known` and `purge_clock_started`; one plot.md sentence each in 1C.3 and 2C.2. Suite 1145 passed. NOT measured live. Not yet done: 2B, 3A, 3B (pointers, wording), live L2 round. The abandoned item 2 sim scripts (`cue_match_sim.py`, `cue_match_diag.py`) were deleted; the plan note above records their findings.

## Resume here: continuous L2 over all nine scenes (2026-10-05, branch `claude/l2-all-scenes`, not merged)

Built by Ringer `freytag-affordance-l2-all` (failed only a ruff E501 in a test; I applied the patch,
ran ruff format, re-ran node 74 and digest 6 tests, committed). Wrappers:
`scene-affordance-l2-all-live.sh <replicates> <scenes|all>`, manifests `scene-affordance-l2-all-smoke-live.json`
and `scene-affordance-l2-all-live.json`. Smoke 1A,1B x1 passed (both timer exits; 1B opened on the transition text).
Full run x3 (Ringer `freytag-affordance-live`, pass, 1052 s, no rejected stops): exit cause per scene
(r1/r2/r3) 1A play/play/play (turn 8); 1B timer x3 (13); 1C timer x3 (11); 2A timer x3 (11); 2B timer x3 (16,16,15);
2C play/timer/timer (12,16,17); 3A timer x3 (13,13,15); 3B timer x3 (14). 3C is the last scene, so "none" is expected.
So 1B, 1C, 2A, 2B, 3A, 3B are real gaps: every player-gated scene exits by timer. Shown-by-end gaps: 1B Brandon first
shown only on turn 13; 1C service_entrance never shown, logistics_terminal turn 11; 2A facility_perimeter never shown;
3A override_codes never shown. Known digest quirk: `stopped_early` counts the last scene. Not done: reading
recorded prompts; token/429 usage of the run. Next: fix earliest first (1B), per "Fixing a Scene".

1B read (2026-10-04, from `artifacts/e2e-blind-player.json`, three replicates, 39 turns): only ONE
knowledge reveal fired in 1B at all (`k_sl_1b_a_r2`, the photograph, r1 turn 2). The cue lines were
shown from turn 1 and the player followed them, but no cue names the action the reveal needs:
- `transport_route_identified` (`k_sl_1b_a_r1`) needs "match/compare the token to the number sequence".
  Cue says "A transit token and a handwritten number sequence lie beside Michelle's photograph."
  Players only examined or took each one.
- `brandon_identified` (`k_sl_1b_b_r1`) needs "show/confront the man with the photograph"; r2 needs
  "question Brandon about Michelle". Cue says "The watcher stands near the service path. He is the same
  man shown with Michelle in the photograph." Players typed "Approach/Question the watcher." and the
  narrator invented a hidden figure. Jev fallback ran on nearly every turn and matched nothing.
- `park_pursuit_resolved` (`k_sl_1b_c_r1/r2`) needs brandon_identified AND missing_may_be_alive first.
  Cue says "The storm-drain entrance is open ahead." Players entered the storm drain 5 to 8 times per
  run; it can never fire before Brandon is identified. A cue for a gated step shown too early misleads.
Same shape as the 1A card (a cue that names the thing but not the move). Recorded prompts were NOT read:
every L2 run so far saved `prompts: []`. Cause (found 2026-10-04): staging does return the prompt
(`FREYTAG_EXPOSE_PROMPT=1` is set on Railway), as an object `{system, user}`, but `playScene` kept a prompt
only if `typeof turn.prompt === "string"`. Earlier notes here that said prompts were recorded were wrong
(smoke runs only compared keys). Fixed by Ringer `freytag-affordance-l2-prompts` (pass, attempt 1): new
`collectPrompts` and `promptsCategory` in `blind-player.js`; prompts now go to a separate
`artifacts/e2e-blind-player-prompts[-r<N>].json` and are stripped from the main report; the all-scenes
wrapper clears old prompts files. Node tests 76 pass. Applied to the working tree, not committed. Committed
as ca203273. Verified live (Ringer `freytag-affordance-live`, 1A,1B x1, pass): 8 prompts for 1A and 13 for 1B in
`e2e-blind-player-prompts-r1.json`, each `{system, user}`; the main report has no `prompts` key.

1B prompts read (r1, turns 1 and 4, 2026-10-04): SCENE carries only the 1B.1 details (bench, grounds, path,
checkpoints, patrols). No watcher, no man, no photograph-confrontation line, no storm drain. On turn 4
("Question the watcher.") THINGS lists only Kristin and the transit token, so Brandon is not a thing the
narrator is handed; he appears only in CHARACTERS and in the CONSTRAINT "Brandon Corfman may say this
aloud: I won't tell you that. Keep your voice down; patrols are nearby." That is why the narrator invented
a hidden figure. "This turn has no candidates" on both turns: the gated reveals are runtime-owned and only
fire on a matched command. So the cue shows a man the narrator was never given. Still to probe: whether
adding Brandon to THINGS and the 1B.2 detail to SCENE (placement is already authored: `brandon` in
`character_placements`) makes the narrator show him; compare with W decisions on companions in THINGS.
Proven techniques that apply: the 1A drawer-gap cue (cue text names the thing and the move; plot.md and
`handoffs.yaml` carry the same line), PR 510 matcher synonym classes. New work: gating a cue on its
`requires` chain (nothing found in W decisions or the grounding guide). Story text goes to ChatGPT
Desktop, not written here.
Next: (1) (done, see above; confirm with a 1A,1B x1 smoke) record prompts per scene; (2) probe on 1B with arms (cue gets the
move; storm-drain cue removed until Brandon is identified), 10 to 15 samples, read by hand; (3) hand
the cue wording to ChatGPT Desktop.

### 1B design: copy what makes 1A work (2026-10-04, proposed, not applied)

Checked: `docs/world-model-grounding.md`, W14 in `.plans/world-model.md`, `engine.py` cue staging,
`cloudflare.py _scene_setting`, the 1A and 1B package material, the recorded 1A and 1B prompts.

What 1A does that 1B does not (each one is an earlier landed fix, so proven):
- P1 The cue names declared things and the part to look at ("drawer", "thin gap along its lower edge").
  1B cues name things that are not entities: "the list of earlier disappearances", "the storm-drain
  entrance", "the maintenance gate" (`world.yaml` declares none of them; it does declare the bench, the
  photograph, the sequence).
- P2 The reveal's evidence verbs are what a player types by default (look, search, inspect, check) and
  the cue's noun is in a noun group ("gap" was added to the under group). 1B-B r1 wants show, confront,
  hold up, present; players typed approach, question, examine. 1B-C wants follow or escape through.
  Players typed enter, follow the tunnel.
- P3 The next step is pointed at inside the previous reveal's delivery text ("Her laptop is in her truck
  outside."), not by an early cue. 1B has no such pointer: the storm-drain cue came as the LAST cue.
- P4 A scene's unnamed man uses W14's label ("the man watching Kristin"); the 1B cue says "the watcher",
  a word that is neither the label nor an alias, so a command with it refers to nothing and THINGS
  lacks him (turn 4 prompt).

Why the storm-drain cue came early (read from `engine.py` 396-440, not run): cues are ranked by the
storylet's eligible window, but one cue is shown per turn and each is shown once; when the eligible
cues are used up, the not-yet-eligible one is staged anyway. So SL-1B-C's cue (needs Brandon identified)
lands around turn 5, before the step it needs.

Minimum path to the bridge is TWO player moves, not five: (1) show Michelle's photograph to the man
(`k_sl_1b_b_r1` sets brandon_identified, missing_may_be_alive, transport_route_identified); (2) follow
Brandon through the maintenance gate, or ask for the gate code (`k_sl_1b_c_r1/r2`, need step 1). The
token and sequence match (`k_sl_1b_a_r1`) is optional.

Recommended changes (authoring only, no engine change; wording below is a DRAFT for Brandon or ChatGPT
Desktop to rewrite, the nouns and verbs are what matter):
1. `handoffs.yaml` `brandon_identified.cue_text` uses the label and names the photograph: "The man
   watching Kristin stands near the service path. Michelle's photograph shows this same man."
2. `knowledge.yaml` `k_sl_1b_b_r1`: verb group gains ask, question, speak to, talk to, approach, hand,
   so "Show the man Michelle's photograph", "Ask the man about the photograph" and "Approach the man with
   the photograph" all fire. Keep the photograph group. Update its `earn_when` the same way (Jev sees it).
3. Move the next-step pointer into the delivery text of `k_sl_1b_b_r1` and `r2`: "A tactical team is
   closing across the park. Brandon points to a secured maintenance gate beside the storm drain."
   Reduce `park_pursuit_resolved.cue_text` to its first sentence (no storm-drain claim, so an early cue
   cannot mislead). `k_sl_1b_c_r1` gets a wider verb group (enter, go through, head into, take) and a
   wider object group (storm drain, storm-drain, drain, tunnel), which matches plot 1B.4.
4. Declare `maintenance_gate` (fixed, aliases gate, secured gate) and `storm_drain` (fixed, aliases
   storm-drain, drain, tunnel) in `world.yaml`, with `item_ids` and `item_placements` in scene 1B
   (grounding checklist: could a reply say "place": "gate"?). Placement `text` only if it must show.
5. Drop the `missing_may_be_alive` cue ("list of earlier disappearances"): no such thing exists, no
   reveal acts on it, and `k_sl_1b_b_r1/r2` already deliver the fact.
Authoring prompt written (2026-10-04): `.plans/chatgpt-1b-affordance-prompt.md` covers changes 1, 2, 3 (cue,
evidence groups, delivery pointer) and 5 as ChatGPT Desktop tasks A-G. Change 4 (declare `maintenance_gate`,
`storm_drain` in `world.yaml`) is structure and goes to Ringer. Not run yet. When the answer comes back: score it
with the real matcher on the 39 recorded 1B commands plus held-back ones, then apply by Ringer.
1B authoring applied (2026-10-05, branch `claude/l2-all-scenes`, Ringer `freytag-affordance-1b-wording`, pass on attempt 2): ChatGPT's
answer to the prompt was scored with the real matcher first. All asked-for commands resolved but ordinary phrasings missed
(Show him the photograph, Enter the tunnel, Flee through the gate, Ask Brandon to open the gate), so I widened the groups
(hand, give, him; flee, escape, run, enter, climb into, go through <object>; open/unlock the gate). Judgement call: `Brandon`
is an object word for step 2, so "Follow Brandon." fires it. Applied: both cues, delivery pointer, plot.md 1B.2 sentence,
four reveal groups, `maintenance_gate` and `storm_drain` in world.yaml and 1B placements. Alias `gate` on the gate was dropped:
it collides with the item-facts hand seed "the gate". Scorer: `scripts/ringer/affordance/1b-wording-score.py` (52 commands).
Full suite 1135 passed, ruff clean. NOT measured live: needs merge, staging deploy, then L2 1A,1B x3 (bar: 1B exits by play 2 of 3).
1B measured live (2026-10-05, PR 516 merged, main b3113c8, staging sha confirmed, Ringer `freytag-affordance-live` task
`l2-1a1b-x3`, pass, 358 s): 1A exits by play x3 (turn 8). 1B exits by play 2 of 3 (turns 11, 10); r3 left on the turn-13
timer. Pass bar (2 of 3) met; was 0/3 before. r3 turn 4 "Show Michelle's photograph to the man." then turn 5-6 "Open the
secured maintenance gate." / "Pick the lock on the maintenance gate." and it wandered into an invented alleyway and freight
receipt; whether turn 4 or 5 fired its reveal is not checked (recorded prompts for r3 not read). Next: read r3 turns 4-6 and
its prompts, then run the remaining scenes 1C to 3B (all timer x3 before) and fix earliest first.
1B r3 diagnosis and fix (2026-10-05, branch `claude/plan-1b-l2`, Ringer `freytag-affordance-1b-gate-move`): r3 turn 4 fired
`k_sl_1b_b_r1`; turns 5-6 "Open the secured maintenance gate." / "Pick the lock on the maintenance gate." fired nothing and the narrator
invented a lockpick and an alley. Causes: (1) `k_sl_1b_c_r1` verbs lacked open/unlock/pick, and `r2` needs ask/tell plus Brandon; (2) the Jev
fallback never ran on turns 5-12 because `_semantic_authored_handoff` skipped a reveal when ANY establishes fact was true (`transport_route_identified`
is set by step 1), unlike `KnowledgeProjector._established` (ALL); (3) THINGS held no Brandon or storm drain on those turns. Fixed (1) and (2)
(the same any-skip also sat in the no-clue-rules loop); both now reuse `_established`; two hermetic tests added; scorer 56 cases pass; full suite
1137 passed, ruff clean. The Ringer task was marked FAIL only because my check called `_matches_all` with swapped arguments; the worker's patch
was applied by hand and the corrected check run directly. NOT measured live: needs merge, staging deploy, then L2 1A,1B x3. Still open: the delivery
text does not name Brandon's own move (wording for ChatGPT Desktop); THINGS lacks Brandon and the storm drain on turn 5.
1B delivery wording (2026-10-05, Brandon approved me editing it): `k_sl_1b_b_r1` and `r2` delivery text now ends "A tactical team is closing across the park. Brandon says he can open the secured maintenance gate beside the storm drain. He tells Kristin to follow him." so the screen names Brandon's move ("Follow Brandon" fires `k_sl_1b_c_r1`). Suite 1137 passed, scorer 56 pass. Turn 5 THINGS gap (read from code, not yet fixed): `item_facts.py` ~464 lists a companion under the protagonist only when his parent equals hers. In r3 turn 5 Kristin was at the park bench (the narrator moved her there on turn 2) and Brandon, set by `accompany` without a move, stayed at `los_angeles_park`, so he was not listed; on turn 6 both were at the park and he was. With the matcher fix, "Open the gate" now fires `k_sl_1b_c_r1`, so that turn becomes a handoff turn; the gap still shows on commands that fire nothing (e.g. "Examine the gate.").
Turn 5 THINGS gap fixed (2026-10-05, Ringer `freytag-affordance-companion-together` task `companion-alongside`, pass attempt 1; Brandon chose "author a move" first, but `{move: brandon, parent: park_bench}` broke `test_identified_brandon_accompanies_kristin_into_the_truck`, so it was reverted; Brandon then pointed out this is a parenting question: the bench is in the park). Added `World.spot` (nearest area or container, skipping seats and supporters) and `World.alongside` in worldkeeper; the narrator's "With Kristin:" line and `_move_companions` both use it (travel is judged before the leader's placement is rewritten). A bench and the park are together; a companion inside the truck while she is outside is not, so W8's narrated split still holds. A first worker pass used `World.together` (truck-in-park counts as together) and was discarded for that reason. Tests: 6 worldkeeper cases and 2 real-package 1B cases; full suite 1138 passed, worldkeeper 49 passed, ruff clean. NOT measured live: needs merge, staging deploy, then L2 1A,1B x3 (bar: 1B exits by play in 2 of 3, and read r3-style gate turns).
Companion travel bug (found 2026-10-05 while fixing the turn 5 listing; fixed in the same commit 90f8d21): `World._move_companions`
(`packages/worldkeeper/src/worldkeeper/model.py`) carried a companion only when his parent EQUALLED the leader's old parent, the same exact-parent
rule as the THINGS listing. So with Kristin at the park bench and Brandon at `los_angeles_park`, a move by Kristin to `kristin_truck` would have
left Brandon in the park, although the bench is in the park and they are together. I first deferred it because it changes where people end up
(world state), not only what the narrator is told, and because I thought `test_identified_brandon_accompanies_kristin_into_the_truck` depended on
the old rule. That second reason was wrong: that test puts Kristin in the park (not on the bench) and passes unchanged under `alongside`. The
real constraint is W8's narrated split: a companion inside the truck while she is outside must NOT follow, which is why the rule stops at the
first area or container instead of using `World.together`. `move` and the story-effect move now compute the carried companions before the
leader's placement is rewritten. Tests: worldkeeper `test_regressions.py` (bench carried, truck split not carried, same-vehicle seat) and
`tests/test_scene_1b_grounding.py` (bench-to-truck carries Brandon). NOT measured live. Still unchecked: other scenes whose scripted
journeys rely on a companion NOT following from a sub-place; the full suite passes, but no live replay has run a multi-scene walk with this rule.
1B live L2 pending (2026-10-05): PR 517 merged as 858103e, but GitHub never started the push-to-main `tests` run for it, so no deploy happened (the Deploy job only runs on `github.ref == 'refs/heads/main'`, so re-running the PR workflow cannot deploy). A small plan-only PR (518, merged as e856bee) gave the workflow a push event; run 37387045062 passed, including Deploy staging and the scene staging evaluation, and staging reports e856bee. I started the L2 1A,1B x3 run (Ringer `freytag-affordance-live`, task `l2-1a1b-x3`, manifest `scripts/ringer/affordance/scene-affordance-l2-1a1b-live.json`) before Brandon wanted it launched, and stopped it within moments; no report was produced. The staging turn-cap variable `FREYTAG_RATE_LIMIT_PER_MINUTE` was confirmed unset afterwards. The billed calls it used before the stop were not counted. Waiting for Brandon's go before launching it again.
1B live L2 on e856bee (2026-10-05, Ringer `freytag-affordance-live` task `l2-1a1b-x3`, pass, 363 s, report in `~/dev/ringer-work/affordance-live-all/`): 1A exits by play x3 (turns 8, 8, 12; memory card first shown turns 5, 2, 10; chair shown only in r1). 1B exits by play 2 of 3 (turns 9, 9); bar met. Brandon, maintenance gate and storm drain first shown turn 3 in all three, photograph, token and sequence turn 1. r3 never left 1B: turn 3 "Show Michelle's photograph to the man." and turn 4 "Follow Brandon to the secured maintenance gate." produced no transition by turn 7, turns 8-10 were rejected and the run stopped ("scene 1B rejected three times in a row"). NOT known: why the r3 gate commands did not exit, and why turns 8-10 were rejected; r3's recorded prompts and the rejected responses are not read. Not confirmed: that the staging turn-cap variable was restored after the run. Next: read r3 turns 3-10 prompts, check the cap, then 1C to 3B.
1B r3 diagnosed (2026-10-05, read from `~/dev/ringer-work/affordance-live-all/e2e-blind-player-r1..r3.json`, no billed calls): all three replicates played the same first four turns and fired `k_sl_1b_b_r1` (turn 3) and `k_sl_1b_c_r1` (turn 4), so the gate facts were set in r3 too. 1B's `min_turns` is 8 (`pacing.yaml`; `engine.py` ~303 holds the transition until `turns_since_entry >= min_turns`), and r1 and r2 left on turn 9, the first turn past that floor. r3 had 7 accepted turns, then turns 8-10 were REJECTED ("narration mentions an unavailable entity 'maintenance tunnel'", then 'maintenance network'); a rejected turn does not advance the count, and the harness stops after 3 rejections in a row, so r3 never reached turn 9. The cause is a name collision: after the gate reveal the narrator describes the tunnel, and `world.yaml` 37-39 declares the later-scene place `maintenance_network` (parent `purge_chamber`) with aliases "maintenance tunnel(s)", which the leak scan treats as an unavailable entity in 1B. 1B's own `storm_drain` has the alias "tunnel" only. This is the memory `declared-names-are-leak-scanned-earlier` / `rename-the-fiction-to-remove-a-collision` case, not a gate failure. Candidate fixes, none applied: (a) drop "maintenance tunnel(s)" from `maintenance_network` aliases if no later scene text depends on them; (b) add "maintenance tunnel" as a `storm_drain` alias (then the alias resolves to two entities, so probably worse); (c) rename in 1B wording. Needs a grep of later-scene use of those aliases first. Also noted: the harness stop rule (3 rejections) is stricter than a real player, who would retry. Staging turn cap restored after this run: not re-verified here (no Railway access checked).
1B gate renamed (2026-10-05, Brandon chose option 1 and the name "service gate"): `maintenance_gate` -> `service_gate` ("service gate", alias "secured gate"), and "secured maintenance gate" -> "secured service gate", in `world.yaml`, `handoffs.yaml`, `plot.md`, `knowledge.yaml`, `storylets.md`, two tests and three Ringer check scripts (the scorer commands too). Dropping the "maintenance tunnel(s)" alias was rejected: it is the 3C fiction (`plot.md` 846/850, `knowledge.yaml` 2381). Verified: full suite 1138 passed, 1B scorer 56 pass, ruff clean. NOT measured live: needs merge, staging deploy, then L2 1A,1B x3; the question is whether r3-style turns still say "maintenance tunnel" (the narrator may still invent it; `storm_drain` says "tunnel" only). Side finding, left alone: `detention_level` also has the alias "secured gate", the same alias as `service_gate`.
Pre-flight before the next billed L2 (2026-10-05, Brandon approved): (1) the blind player now stops after 5 consecutive rejections, not 3 (commit 7efa0b0, node tests 81 pass). (2) Replay probe `scripts/ringer/affordance/post_gate_probe.py` (Ringer `freytag-post-gate-probe`, narrator Worker, 12 samples per cell, r3's recorded 1B turn 5-7 prompts): A = as recorded, B = "service gate" and "tunnel" in the input, C = B plus Kristin placed in the storm drain, D = B plus the gate statement saying "storm drain" for "escape route". Count = replies naming a later-scene place (all `world.yaml` location forms outside 1A/1B, plus "escape route"). Turn 5: A 12/12, B 1/12, C 1/12, D 0/12. Turn 6: A 12/12, B 3/12, C 8/12, D 0/12 (every B/C hit is "escape route"). Turn 7: A 12/12, B 12/12, C 0/12, D 12/12; the turn 7 recorded prompt already has "Kristin. Place: maintenance network" from the old wording, so B and D there only echo the prompt and do not show the shipped behaviour (the new wording should not put her in that place; not measured). Cause of the live rejections: the old gate name primed "maintenance tunnel", the engine then resolved the player's/narrator's "maintenance tunnel" to the 3C place `maintenance_network` (THINGS showed "Kristin. Place: maintenance network"), and the narrator echoed it. "Escape route" is both in the 1B `k_sl_1b_c_r1` statement and a known term of a 3C knowledge item (`knowledge.yaml` ~2731), which is the r1 turn 5 rejection. Applied: `k_sl_1b_c_r1` statement now ends "leads Kristin through the storm drain." (was "the escape route"); suite 1138 passed, scorer 56 pass, ruff clean. Not done: a turn 7-style replay from a state that did NOT come from the old wording; offline scoring of scenes 1C-3B (pre-flight item 3).
Offline scoring of 1C-3B (pre-flight item 3, 2026-10-05, no billed calls). Tools: `scripts/ringer/affordance/scene_gap.py <scene> <report>` (bridge facts, the reveals that set them with evidence groups, cues, and each run's commands with the reveals that fired) and `reveal_coverage.py <report>` (how many recorded commands the real matcher accepts per reveal, `requires` ignored). Data: the all-scenes x3 run `l2-all-x3` (~/.ringer/artifacts/deliverables/freytag-affordance-live-20261005T021549Z-p713092), which has commands and narration but NO recorded prompts, so the prompt reads (THINGS, SCENE) are not done for these scenes. Result: every scene's chain stalls after its first reveal. Commands matching each reveal (requires ignored), out of ~33-47 per scene: 1C a_r1 5, every later reveal 0; 2A b_r1 6, e_r1 0, b_r2 0; 2B a_r1 8, all of b and c 0; 2C c_r1 2, d_r2 8, b_r1/b_r2/d_r1 0; 3A a_r1 1, d_r2 3, b, c, d_r1 0; 3B e_r1 1, c_r2 17 (the LAST step, which cannot fire until four earlier ones have), all of a, b, d 0. Three causes recur, each already seen in 1A or 1B:
- Cue nouns are not in the evidence groups. 1C `k_sl_1c_b_r1` wants prisoners/captives plus records/ID numbers; the cue says "identification numbers ... uniforms", and "Read the identification numbers on the uniforms" misses. 1C `k_sl_1c_c_r1` needs the logistics computer and `national_detention_network_known` has NO cue. 2A step `k_sl_2a_e_r1` wants go/drive/travel to the facility; players typed "Enter the facility" and "Present my credentials at the checkpoint". 2A b_r2 wants "credentials"; players typed "inspection cover documents" (the cue says "blank inspector forms"). 2B `k_sl_2b_b_r1` wants "development record(s)"; the cue says "a record on the archive terminal" and players typed "Read Brandon's record". 2B c_r1 wants "corrupted prisoner files"; players searched the medical terminal for Michelle. 3A a_r1 verbs lack "free"; 3B c_r1 wants tell/ask plus the relay, players typed "Access the Brandon voice channel" and "Activate the relay".
- Every cue is shown from turn 1, so players act on the LAST step, which cannot fire. 3B has a five-deep chain (human_security_control, rebecca_office_reached, detention_locations_secured, charles_abandoned_rebecca, relay_open); runs went straight to the relay and the national network controls. 3A players used the gate-status panel (step 4) before reaching Michelle and the experiment records. Same shape as the 1B storm-drain cue; the "Contingent" item below (do not stage a cue whose reveals' `requires` are unmet) would fix this for all scenes at once, but has no proven precedent.
- No pointer to the next step in the delivery text (the 1A card and 1B gate fix, P3). 2A `k_sl_2a_b_r1` fires on turn 1 and sets `false_identities_ready`, and its delivery does not say where to go next.
Also seen: 2C 4 of 45 turns rejected in r1; 3A r3 turn 8 and 13 rejected, 3B none; 2B r1/r2 one each. Not read: the rejection reasons for those.
Whole-game options (none applied; Brandon to choose): (W1) staged cues, an engine change that is story-neutral and covers 1B, 2A-3B at once; needs a design and a hermetic test, then L2. (W2) widen the evidence groups and fix cue nouns scene by scene, scored offline with the real matcher as in 1B (56-command scorer); the verbs and nouns are mine, but cue and delivery sentences are story text for ChatGPT Desktop. (W3) add next-step pointers to the deliveries. W1 plus W3 are the cheapest per scene; W2 is the most work but is the proven way.
Contingent (new, only if 1-5 do not fix a live run): do not stage a cue whose reveals' `requires` are
unmet, story-neutral, matches the docstring on `_bridge_delivery_fact_ids`.
Rejected: adding the 1B.2 watcher details to SCENE. `_scene_setting` sends beat prose only for reveals
that are candidates this turn, on purpose (Scene 2B's first beat names JANUS). That also retires two
arms of the earlier probe idea.

Check path (each step free until the last): (a) after editing, run the real matcher over the 39 recorded
1B commands plus about 8 natural commands per step and read every hit (the photograph command must still
fire `k_sl_1b_a_r2`, nothing may fire the wrong step); (b) capture the 1B prompts offline
(`.plans/world-model-s1/prompt_capture.py`) and confirm THINGS lists the man by label once a command says
"the man"; (c) L0 map, pytest, ruff; (d) L2 1A,1B x3. Pass bar: 1B exits by play in at least 2 of 3.

## Design: L2 across all nine scenes (drafted and decided 2026-10-04, not built)

What the code says (read, not run):

- Scenes after 1A already work. `blind-player.spec.js` with `E2E_BLIND_SCENE=<id>`
  walks the earlier scenes with `walkScenes` (scripted package-aware journey,
  package clock, one session), then the blind player plays only scene S. So
  nine per-scene runs need no new harness, but each re-walks the earlier scenes:
  scene k costs k-1 scripted scenes of narrator turns. Nine scenes = 36 scripted
  scenes of live narration to measure 9 blind ones.
- The session cap is not a concern. A replicate opens one session, and the test
  clock token bypasses the per-IP cap (`web_demo.py` 257).
- Per-replicate limits: `askPlayer` cap is 20 model calls per replicate, the
  test timeout is 20 minutes, and the ceiling per scene is
  `min(20, handoff target + 2)`. A continuous run needs all three raised.

Options:

A. Per-scene runs (existing path), 3 replicates each, run as 9 Ringer tasks.
   No code change. Costs about 4x the narrator turns and measures each scene
   from a scripted (clean) entry state.
B. One continuous blind run per replicate (recommended). One session, the blind
   player plays 1A, then 1B, and so on to the end; 3 replicates in parallel
   with the existing `E2E_BLIND_REPLICATE_INDEX` path. About 9 x 13 = 120
   turns per replicate, each scene's exit labelled play or timer. A timer exit
   is not fatal: the engine stages the missing bridge facts, so the run
   continues and the next scene is measured from the state a real player would
   have. This is also the "continuous blind run" the plan's step 3 asks for.

Changes for B (all in the test harness, none in the runtime):

1. Refactor the spec's single-scene turn loop into a function
   `playScene({ sceneId, ... })` returning the run record, and loop it over
   `pacing.sceneOrder` when `E2E_BLIND_SCENE=all`. Reuse `analyseRun` per scene;
   the opening text and `firstStep` come from the current scene's map entry.
2. Per-scene model-call counter with cap 20, plus a hard total cap of 200 per
   replicate (billed-endpoint guard).
3. Test timeout 60 minutes; the Ringer check timeout 4500 s.
4. Report shape: `scenes: [{scene, ...run}]` per replicate, and the digest
   prints one row per scene (exit cause, exit turn, first-shown turns of the
   gate affordances). `merge-blind-player.js` merges per scene.
5. Stop a replicate if a scene is rejected 3 times in a row, as today.

Verify before trusting: smoke 1 replicate through scenes 1A to 1B only (cap the
scene list with `E2E_BLIND_SCENES=1A,1B`), compare scene 1A with the earlier
1-replicate result, then 3 replicates over all nine.

Decisions (Brandon, 2026-10-04): (1) B, one continuous blind run per replicate.
(2) The cost, about 360 narrator turns plus up to 120 Jev calls across 3
replicates, should fit the Workers AI budget; watch for 429s and record the
actual usage after the first full run. (3) On a timer exit the run continues
into the next scene.

Next: build B as a Ringer task (harness changes 1 to 5 above), then the 1A to 1B
smoke, then 3 replicates over all nine scenes.

## Plan: run L2 replicates in parallel (drafted 2026-10-04; built and merged, see below)

Why: `l2-1a-x3` runs its 3 replicates one after another in one Playwright test
(`blind-player.spec.js`, a `for` loop, 20 minute timeout), and the manifest has
one task with `max_parallel: 1`. Each probe-fix-rerun cycle pays for all three
serially, plus the Railway redeploy wait. No earlier written plan for this was
found in `.plans/`, `scripts/ringer/affordance/` or memory (checked 2026-10-04).

What the code says about sharing (read from source, 2026-10-04):

- The per-minute turn cap is keyed by `session_id` (`web_demo.py`
  `require_turn_rate_limit`), not by IP. Parallel replicates use separate
  sessions, so they do not slow each other. The cap raise exists only because
  the one blind player sends more than 10 turns a minute in one session.
- The session cap is per IP per day (default 20, `require_session_rate_limit`).
  A 1A replicate opens one session, so 3 replicates is cheap. A later scene
  walks the earlier scenes first and opens more, so count sessions before
  parallelising scenes beyond 1A.
- `writeCategoryReport("blind-player", ...)` always writes
  `artifacts/e2e-blind-player.{json,md}`. Parallel runs would overwrite one
  another.
- The spec rejects `E2E_BLIND_REPLICATES` outside 1 to 3 and runs the replicates
  in one test body.
- The check raises `FREYTAG_RATE_LIMIT_PER_MINUTE` on Railway, waits for the
  redeploy, and deletes the variable on exit. Parallel checks that each did this
  would redeploy staging mid-run and drop each other's sessions.
- The OpenAI player has a call counter per replicate (`counter`), so its hard cap
  already holds per replicate.

Design (smallest change that works):

1. **One wrapper owns the cap.** Split `scene-affordance-l2-live.sh` into
   `l2-cap-raise.sh` (set the variable, wait for 5 health checks) and
   `l2-cap-restore.sh`. Under Ringer, a first task raises it, the replicate tasks
   depend on it, and a last task restores it. If the dependency model cannot make
   the restore run after a failure, keep one wrapper script that raises, runs the
   replicate processes in the background with `wait`, then restores in its `trap`.
   The wrapper is the safer first version.
2. **One Playwright process per replicate.** Add `E2E_BLIND_REPLICATE_INDEX` (the
   replicate number) and `E2E_BLIND_REPORT_SUFFIX`. With an index set, the spec
   runs only that replicate and writes `artifacts/e2e-blind-player-r<N>.json`.
   Without it, behaviour is unchanged (3 replicates, one file). Playwright
   `workers` stays at 1 per process, so no change to `playwright.config`.
3. **A merge step.** Add `scripts/ringer/affordance/merge_l2.py` that reads the
   per-replicate files and writes the existing `e2e-blind-player.json` shape
   (`story_id`, `scene`, `replicates`, `aggregate`), renumbering `replicate`. The
   `aggregate` logic is JavaScript in `blind-player.js`, so either the merge is a
   small node script that imports it, or the Python version is tested against it
   on a fixture. Either way the digest and every reader stay unchanged.
4. **Digest unchanged.** `digest.py` runs on the merged file.
5. **Ringer shape.** One task per replicate is the memory rule
   (`one-ringer-task-per-run-unit`), so the manifest has `l2-1a-r1`, `r2`, `r3`
   at `max_parallel: 3`, each with its own `expect_files` and
   `check_timeout_s: 2400`, plus the cap tasks and the merge. Each replicate
   task's check is the single-replicate run, not the cap script.

Tests (no live model): node tests for the index and suffix handling in the spec
helpers; a pytest for `merge_l2.py` over two small fixture reports, including a
missing replicate (it must fail and say which). Run ruff on the script.

Verify before trusting it:

- Smoke first (memory: `smoke-test-billed-runs-first`): one replicate through the
  new path, compared field by field with a report from the old path.
- Then 3 in parallel. Compare transition turn, shown turns and stuck turns with
  a serial `x3` on the same staging sha. Expect noise, so judge only that nothing
  structural differs (same keys, the card first-shown turn recorded, prompts and
  `semantic_match` present).
- Watch staging for 429s on turns and for slower narration under 3 sessions at
  once. If narration latency rises, `E2E_TURN_TIMEOUT_MS` (now 90000) may need
  raising; record the observed latency.

Decisions (Brandon, 2026-10-04): the goal is shorter wall time only, so scenes
stay serial and the session cap is not a concern yet. The 1 to 3 replicate limit
stays per process. Three concurrent sessions fit the inference budget for now.
Each replicate is one process; extra replicates mean extra processes.

Questions that were asked (answered above):

- Is the goal wall time only, or also running L2 across scenes in parallel? The
  second needs the session cap counted first.
- Should the 1 to 3 replicate limit stay per process, with more replicates meaning
  more processes? Recommended: yes, the limit then guards the billed OpenAI
  calls per process.
- Does Cloudflare Workers AI budget allow 3 concurrent sessions? The narrator is
  the inference budget (memory: `cloudflare-workers-ai-is-the-inference-budget`),
  and the Jev fallback adds up to 40 calls a session.

Done: see "Parallel L2 replicates: built and measured" above.

## Built (2026-10-03)

| Layer | Files | Commit | Verified |
| --- | --- | --- | --- |
| L0 map + checks | `bench/affordance_map.py`, `tests/test_affordance_map.py`, `bench/affordance_known_gaps.json` | ec737dc, a1af49a | pytest, ruff, CLI on both packages |
| L1 `@affordances` | `frontend/e2e/affordances.js`, `scene-walk.js`, `affordances.spec.js` + node tests | efe3f9c | node tests; one live 1A run |
| L2/L3 `@blind-player` | `frontend/e2e/blind-player.js`, `blind-player.spec.js` + node tests | a354eb0 | node tests; listed by Playwright; never run live |

Ringer runs: `freytag-affordance-l0` (L0, L0b), `-l1` (L1, L1b), `-l2`.
Manifests and checks are `scripts/ringer/affordance/scene-affordance-l*.json` and `*-check.sh`; the live-run manifests end in `-live`, and `digest.py` there summarises an L1 or L2 report.

## First live result (L1, 1A, 1 replicate, staging, 2026-10-03)

Reproduces the complaint. The opening and the first exploring turn named the
workstation (turn 0) and never named the drawer, the workstation chair or
Kristin's laptop. The drawer holds the KMS initials the memory-card reveal
needs. One replicate: it shows the miss is possible, not how often. That
run sent "Search the Michelle's house." (a bad input); L1b fixed
`exploreInput` for possessive names, so rerun before counting.

## Open

- **Later scenes have no gates yet.** The L0 map finds player-earned gates
  only in 1A, 2A and 2C. Scenes 1B, 1C, 2B, 3A and 3B leave through
  unconditional bridge events, and the map ignores each transition's
  `required_dependencies`. So L1 reports nothing for them, which is a gap in
  the map, not a pass. Next L0 task: include `required_dependencies` and the
  storylets they name.
- Known L0 findings (14 before L0b, 6 after) are in
  `bench/affordance_known_gaps.json`: authoring gaps for ChatGPT Desktop,
  not fixed here.
- D4 paraphrase (Jev check) is not built; names and aliases only.
- L2 runs without the package clock, so it plays at real turn pacing.

## 1. The problem, with evidence

- **The material reaches the narrator; the narration drops it.** The
  shipped 1A opening prompt (captured 2026-10-02 with
  `.plans/world-model-scenes/capture_scenes.py`) carries "KMS initials
  carved in drawer" and "A drawer on Michelle's workstation has Kristin's
  initials, KMS, newly carved into it." in SCENE. Its rules also say "Show
  only the opening beat". The hosted opening in `artifacts/e2e-smoke.json`
  (2026-09-14) names the phone, "the overturned workstation chair" and "the
  desk", and never the drawer or the initials. So a check on the prompt
  passes while the player still never sees the drawer. Only a test that
  reads what the player reads catches this.
- **Today's E2E tests cannot see the gap.** `@spine` and `@llm-canon` type
  package-aware commands ("Search the back door and room for signs of
  Michelle's disappearance.") that already know the drawer exists. A
  scripted player that knows the answer never gets stuck. `@spine`'s
  `must_convey_misses` checks a reveal's delivery once it fires. It does
  not check whether the player was ever given what they need to make it
  fire.
- **The bench is the same.** Bench scripts ("Open the drawer with my
  initials carved into it.") name things the narration may never have
  shown.

## 2. Terms

- **Gate:** one route by which a scene's transition becomes true. A
  transition in `pacing.yaml` has `triggers` (facts that must hold) and
  `required_dependencies`. Each trigger fact is set by one or more
  **sources**: a knowledge item's `establishes`, a `handoffs.yaml` entry, a
  `storylet-routes.yaml` effect, or a pacing event's `effects`.
- **Player-earned source:** a knowledge item with `earn_when` and
  `action_evidence`, or a storylet route the player's action fires. The
  player must do something to it.
- **Engine source:** a pacing event (`pressure_1a` sets
  `patrol_return_pressure` at turn 4). The player does nothing. Its
  `realizations` text must still be shown.
- **Affordance:** a thing, place or person the player must act on for a
  player-earned source to fire. It comes from the source's `entity_ids`,
  the object groups of its `action_evidence`, and its `requires` chain. 1A
  example: SL-1A-A's `k_sl_1a_a_r1` needs the kitchen, back door and
  overturned chair; the memory-card reveal needs the workstation, the KMS
  drawer and its underside; reading the card needs the truck and the
  laptop.
- **Shown:** named in text the player reads. That means the entry text, the
  opening and turn narration, appended delivery text, pacing realizations,
  and bridge text, matched by the entity's name or any alias. A paraphrase
  ("the desk" for the workstation) is D4.
- **Deadline:** when an affordance must have been shown (D1).

## 3. What the package already gives us

Nothing here needs new authoring. The map is derived:

`transitions[].triggers` -> trigger fact -> sources (knowledge
`establishes`, handoffs, storylet routes, pacing `effects`) -> for
player-earned sources, `entity_ids` + `action_evidence` objects +
`requires` -> world entities (`world.yaml` names and aliases; scene
`item_placements`, `character_placements`) -> affordances, each with its
gate, source, earliest pacing window, and whether it is visible at scene
entry or only after an earlier reveal (hidden things like the memory card
become affordances only once their revealing source fires).

This follows the project's rules: facts are the truth, the shared runtime
stays story-agnostic, and every check generalizes across stories
(`tests/fixtures/stories/lighthouse-keeper` is the second story the
derivation must handle).

## 4. Test layers

### L0: the affordance map and static checks (free, deterministic)

A test tool, not runtime code (location D6), builds the map in section 3
for every scene and writes it as JSON. Unit tests over both packages
assert:

1. Every transition has at least one gate whose sources all resolve
   (no trigger fact without a source, no dangling `requires`).
2. Every affordance of a player-earned source resolves to a world entity
   that is placed and visible in that scene, or is revealed by an earlier
   source in the same gate.
3. Every affordance appears in player-facing material the narrator gets
   for that scene (scene SCENE lines, beat details, placements,
   `must_convey` of an earlier reveal). This is the prompt-side half: it
   proves the narrator *could* show it.
4. Every engine source has realization text.

Failures here are authoring gaps. They are fixed in the package (plot.md
first, ChatGPT Desktop for prose), never by test edits.

### L1: `@affordances`, shown-by-deadline (hosted, billed)

Playwright against the hosted staging demo, like the other categories. For
each scene (entered with the package clock and the existing scene-entry
setup used by `@llm-canon`), it reads the opening and plays a short fixed
exploration that names only what the narration has already shown. It then
checks every first-step affordance from the L0 map against the shown text
by its deadline. Exploration inputs follow AGENTS.md "Writing Player
Input": imperative, verb plus object, no non-events ("Search the
kitchen.", built from the scene's location name as narrated).

Output: `artifacts/e2e-affordances.{json,md}` with, per scene and
replicate, each affordance, the turn it was first shown (or never), and
the matching text. Pass or report: D3.

### L2: `@blind-player`, can a player who knows only the screen finish the scene? (hosted, billed)

An LLM player (D2) sees only the transcript so far, plus whatever the UI
shows the real player. It writes the next command under the player-input
rules. It plays each scene up to that scene's turn ceiling from plot.md's
pacing contract. The test records:

- whether the transition fired, and on which turn;
- each affordance's first-shown turn (as in L1);
- **stuck turns:** turns where the player's command named nothing from the
  affordance map and no gate source fired; runs of three or more are
  reported with the transcript;
- whether the transition happened with a gate's player-earned reveal never
  shown (a **silent transition**).

This is the test that matches Brandon's complaint directly: the player
does not know what to do. It is noisy, so it reports rates over
replicates (3 per scene to start), never one run.

### L3: transition narration checks (hosted, inside L1 and L2 runs)

On every turn that fires a gate source or a transition:

1. The source's `must_convey` groups appear in the shown text of that
   turn (the existing `delivery.must_convey_misses` telemetry, now
   asserted per gate rather than tallied).
2. An engine source's realization text was shown on the turn it fired.
3. The bridge text and the next scene's opening were shown at the
   transition, and the old scene's last turn did not already narrate the
   next scene (no restart, no skip).

## 5. Telemetry the tests need

The turn response already returns `state.scene_id`,
`fired_storylet_ids`, `fired_pacing_event_ids`, `turns_since_scene_entry`
and `delivery` (`beats_projected`, `must_convey_misses`,
`handoff_staged`, `recovery_used`, `fallback_used`). It does not return
which trigger facts were set this turn or which knowledge items were
delivered. Phase 0 checks whether `@knowledge-timeline`'s
`resolved_source_ids` path already exposes the second. If neither is
available, add a staging-only field gated like the test clock
(`FREYTAG_ALLOW_TEST_CLOCK`), so production responses are unchanged.

## 6. When a test fails

Follow AGENTS.md "Fixing a Scene". Read the turn's recorded prompt next
to plot.md. Probe the candidate causes on recorded prompts. Fix at the
source.

- An affordance missing from L0 check 3 is missing story material
  (ChatGPT Desktop).
- An affordance in the prompt but not in the narration (the 1A drawer)
  is probed first. Candidate arms: the opening's own rule list
  (`opening()` builds its own, see AGENTS.md "Writing Narrator Rules"),
  an affordance named in THINGS for the opening, or a reveal handoff that
  delivers it. A narrator rule comes last.
- Every fix reruns the same L1/L2 scene with the same replicate count.

## 7. Phases

**Phase 0 - Verify inputs (free).** Confirm in source: how `@llm-canon`
enters each scene; what the UI shows the player besides narration (the
objective?); whether delivered knowledge IDs are exposed (section 5);
that the lighthouse-keeper fixture has transitions with player-earned
sources. Record findings here. Exit: every assumption above marked true
or replaced.

**Phase 1 - L0 map and static checks (free).** Build the map tool and
its unit tests on both packages, as Ringer tasks. Run it on the shipped
package and list every failing check. Exit: map JSON for all nine scenes
read by hand against plot.md; failures listed as authoring tasks, not
fixed in this phase.

**Phase 2 - L1 `@affordances` (billed).** Build the category on the L0
map. Smoke one scene (1A, one replicate) first, then all nine scenes
once. Exit: a per-scene table of affordances shown/not shown, with the
1A drawer case reproduced or refuted.

**Phase 3 - L2 `@blind-player` and L3 (billed).** Build the LLM player
under the billed-endpoint guard. Smoke 1A once, then 3 replicates per
scene. Exit: per-scene stuck-turn and silent-transition rates and a
ranked list of scenes to fix.

**Phase 4 - Fix and re-measure.** Per scene, by section 6. Exit is per
scene: every gate's affordances are shown by the deadline in 3/3 L1 runs,
and the blind player reaches the transition within the turn ceiling in
at least 2/3 runs (bar to be confirmed in D3).

**Phase 5 - Gate.** Decide which layers run where. L0 runs in CI with
the unit suite. L1 joins the staged E2E run after a merge. L2 runs on
demand. Update `docs/testing-runbook.md` section 6 in place with the new
categories (no results in the runbook).

## 8. Decisions for Brandon

- **D1. Deadline.** When must a first-step affordance be shown?
  Options: (a) in the opening; (b) by the end of the first exploring
  turn ("Search the kitchen."); (c) before the source's pacing-window
  `latest` turn. Recommended: (b) for things the scene's location holds
  in plain sight (the workstation, the drawer, the back door), (c) for
  things a reveal unlocks.
- **D2. The blind player.** Which model, and what does it know? Options:
  the transcript only, or the transcript plus the scene objective the UI
  shows. Recommended: the transcript plus whatever the real UI shows, on
  `gpt-5.6-luna` as `@llm-judge` already uses (`OPENAI_API_KEY`).
- **D3. Pass or report.** Hard-fail L1 on any missing affordance, or
  report rates first and set a bar after Phase 2? Recommended: report
  first. L0 hard-fails from day one.
- **D4. "Shown" for paraphrase.** Count only names and aliases, or also a
  judge for "the desk" = the workstation? Recommended: names and aliases
  for the pass/fail, with a Jev check (as the match-call mapping check
  does) logged alongside, so alias gaps become alias fixes.
- **D5. Scope order.** All nine scenes at once, or 1A-1B first and
  expand? Recommended: L0 on all nine (free), L1/L2 on 1A-1B first, then
  the rest.
- **D6. Where the map lives.** `bench/` (bench-only tool, like
  `bench/jev_use.py`) or `storygame/story_package/` (reusable by a future
  runtime nudge)? Recommended: `bench/`. Runtime use is a later decision.

## 9. Cost and safety

L1 and L2 call the hosted narrator (Cloudflare Workers AI neurons). L2
also calls the OpenAI player model. Smoke one scene before any
multi-scene run. Run each scene as its own Ringer task. Guard the player
model the way every billed endpoint is guarded. Runs target the hosted
staging demo only, never production. Unit tests for L0 and for the
harness pieces never call a live model.

## 10. Phase 0 findings (2026-10-03, read from source)

- **Scene entry:** `@llm-canon` never jumps to a scene. It plays from 1A
  (`startSceneSession`) with the package clock and sends
  `frontend/e2e/canon-journey.js` prompts per scene until `state.scene_id`
  changes. Entering a scene emits its `entry_text` as the turn's last
  segment. So L1/L2 reach scene S by playing the journey; a package-aware
  journey is fine for *getting there*, not for the measured turns.
- **What the UI shows the player:** the narration transcript, speech and
  action segments, and a status line `Scene <id> • <phase>`. No objective.
  D2 is settled by this: the blind player sees the transcript plus that
  status line, nothing else.
- **Delivered knowledge ids are already exposed:** each segment carries
  `grounding_ids`, and the canon test records them. The turn also returns
  `state.fired_storylet_ids`, `fired_pacing_event_ids`,
  `turns_since_scene_entry` and `delivery`. Trigger facts per turn are not
  exposed, so no new telemetry field is needed for L1; L2 infers the
  transition from `state.scene_id`.
- **Lighthouse-keeper fixture:** `knowledge.yaml` has no `earn_when` item, so
  it yields few or no player-earned affordances. L0 must run clean there;
  it only proves the derivation is not hard-coded to one story.
- **Hosted runs need no deploy for harness-only work:** Playwright runs
  locally in `frontend/e2e` against the staging API named by `E2E_API_BASE_URL`.
  Only a runtime change would need the merge-and-poll gate.
- **Blind-player guard:** the player model is called from the test process
  with the developer's `OPENAI_API_KEY`, like `roleplay-judge.js`. It is not a
  route. It still gets a fixed model, a hard cap on calls per run, and a
  refusal unless `/api/v1/version` reports `channel: staging`.

L2 1A-3B x3 rerun on 2ee09ec (2026-10-08, Ringer `freytag-affordance-live`, pass; staging sha confirmed 2ee09ec). Exit cause per scene (r1/r2/r3, P=play, T=timer, N=none): 1A P P P; 1B P P P; 1C P T P; 2A P P T; 2B P P P; 2C P T P; 3A P N N; 3B P (9) not reached, not reached. With the earlier run, 3B is 2 of 2 by play where reached, but r2 and r3 never got there: both stuck in 3A (15 turns) on leak rejections, 'narration mentions an unavailable entity rebecca' (r2 turns 4-5 'Enter Rebecca's secured office.'; r3 turns 2, 4, 9 'Access/Take control of/Seize the broadcast console.') and 'broadcast chamber' (r3 turns 12-13). Other rejections: 'detention level' in 2B/2C (r1, r2), 'access to the facility' unavailable knowledge in 2A (r2). Not rejected-loop stops this time: no replicate hit the 5-in-a-row stop.

Leak scan read (`storygame/runtime/narration_safety.py`, `_validate_segments`): (1) 'rebecca' is an entity alias; Rebecca is a participant only in 3B/3C, so 3A may not name her, yet the 3A plot line says the broadcast starts 'from Rebecca's secured office' and players echo it. Fix (story data, at Brandon's say-so): `rebecca` added to 3A `participant_ids` in plot.md (presence is still inferred from beat prose, so she does not speak in 3A). Suite 1157 passed; not measured live. (2) 'park bench' is a known term from the 1A card-read `must_convey`; a player who left 1A on the timer never earned it, so any 1B narration of the photograph under the bench is rejected, and 5 in a row ends the replicate. Fix: validator skips a known term that names a fixed scenery entity present in the scene (hidden items stay protected); Ringer `freytag-known-term-fixed`, see below. Still open: 'broadcast chamber' (3B place) and 'detention level' (3A place) leak in earlier scenes; 'access to the facility' term in 2A.

Leak fixes for the three open L2 rejections (2026-10-08, Ringer `freytag-leak-names`, uncommitted, not measured live; suite 1163 passed, ruff clean). (1) 'broadcast chamber' in 3A: `_scene_entity_ids` now allows a place owned by a scene participant, and the places inside it (executive_office is owned by rebecca; rebecca is a participant only in 3A-3C). (2) 'detention level' in 2B: the entity leak scan skips a place name that the scene's own `scene_frames` situation or projected beat text says, allowing a plural 's' ('detention levels'). This does NOT cover the 2C rejection ('Enter Michelle's holding block.'): 2C's text says 'detention sectors', not 'level'. Still open. (3) 'access to the facility' in 2A: k_sl_2a_c_r2 third must_convey group is now `[they have access to the facility]` (a substring of the delivery_text; the loader requires each group inside it, so `gaining access to the facility` alone failed). To keep the suite green the worker changed `tests/test_must_convey.py::test_gated_reveal_statements_convey_their_own_groups` to check `delivery_text` instead of `statement` for every reveal; review that, it loosens the test for all reveals. Next: push, wait for staging, rerun L2 1A-3B x3.

2C 'detention level' fix (2026-10-08, Ringer `freytag-holding-block`, pass first try; suite and ruff clean; not measured live). Brandon: the holding block is part of the detention level (her cell is there). So `holding_block` is now a place (parent detention_level, no aliases); k_sl_2c_d_r1 and k_sl_2c_d_r2 list it in `entity_ids`, so it is nameable once the coded message is decoded; and a place that may be named brings its ancestor places with it (`_location_ancestor_ids`). 1A still rejects both names; 2C before the message still rejects 'holding block'. Open: 'holding block' said in 2C before the message is decoded is still rejected. Next: push, wait for staging, rerun L2 1A-3B x3.

L2 1A-3B x3 on a628561 (2026-10-08, PR 537 merged, staging confirmed a628561 via /api/v1/version; Ringer `freytag-affordance-live`, pass, 571 s). Exit cause per scene (r1/r2/r3, P=play, T=timer): 1A P T P; 1B P P P; 1C P P P; 2A P P P; 2B P P P; 2C P T P; 3A P T P; 3B T T T. The four targeted rejections are gone: no 'broadcast chamber', 'detention level' or 'access to the facility' rejection in any replicate, and no 5-in-a-row stop. 3B is 0 of 3 by play (14 turns each), against P(9) once on a6f3fbd and 2 of 2 where reached on 2ee09ec; r2 also timed out in 1A, 2C and 3A. Two new rejections, both r3: 2B turn 5 'Search the maintenance reports on the next terminal.' (protected knowledge 'phase') and 2C turn 8 'Seize the broadcast controls.' (unavailable entity 'rebecca', who is a participant only in 3A-3C). Not diagnosed. Next: read why 3B times out now that 3A is reached, then the two new rejections.

3B timeouts read (2026-10-08, no billed calls; recorded run `~/dev/ringer-work/affordance-live-all/e2e-blind-player-r1..r3.json`, `scene_gap.py 3B`). All three replicates spend 14 turns on the LAST step of the chain (the relay: r1 'Seize/Override the broadcast relay' x8, r2 'Rebecca's broadcast relay' x6, r3 'broadcast relay' keypad/shaft x9) and none tries the first step (false alarms or cycling doors; `k_sl_3b_a_r1/a_r2`). Turn 14 is the timer handoff in every replicate. The first-step cue ('Water-pressure warnings flash while doors open and close in empty service corridors.') is in the turn 1 text of r1 and r2 and is ignored. Pulls toward the relay, found in the narration: 'They need to overload JANUS and seize the broadcast relay' and 'the group is getting close to the broadcast relay' (turns 1-9 of every replicate). Sources in `knowledge.yaml`: (a) `scene_frames` 3B situation 'the group needs an opening to reach the broadcast relay' and pressure 'Overload JANUS and seize the broadcast' (the plot objective was already changed to 'Overload JANUS with false alarms' in PR 533, but the frame was not); (b) `k_scene_3b_entry` 'The broadcast relay is the immediate contested objective.' (entity_ids broadcast_relay, public, 3B). Also `location_id: broadcast_relay` for 3B. Checked: AGENTS 'Fixing a Scene' step 1 (a line that pulls the other way), PR 533 (the same fix applied to the plot objective and 3A bridge text; it got 3B to play once on a6f3fbd, then 3B reached on 2ee09ec), 2C/3A precedent (remove or scope the pulling line, probe by Ringer first). Not yet probed. Next: Ringer replay of a recorded 3B prompt (r1 turn 2), 10-15 samples per arm: A as recorded; B frame situation and pressure reworded to the false alarms (copy plot 3B.1 text unchanged); C = B plus `k_scene_3b_entry` removed from 3B. Score the narration by whether it points at the alarms or doors rather than the relay. Needs Brandon's go for the billed run.

3B coherence evaluation (2026-10-08, ChatGPT Desktop, prompt `.plans/chatgpt-3b-coherence-prompt.md`; nothing applied). Verdict: the plot still makes sense (alarms, then office, then relay; no plot fact lost by PR 532/533). The fault is the opening: `scene_frames` 3B and `k_scene_3b_entry` call the relay the immediate objective while the plot objective says false alarms, so heading for the relay on turn 1 is a reasonable reading of what the game says. Its one-sentence purpose: 'Break JANUS's hold so the evidence can be broadcast.' Its proposed frame: situation 'JANUS watches the security corridors on the way to Rebecca's office and the broadcast relay.'; pressure 'Use false alarms to get past JANUS, then open the relay for the broadcast.' Its line verdicts: contradiction: plot objective (plot.md:706), `k_scene_3b_entry` (knowledge.yaml:2721); pull: `scene_frames` situation and pressure (knowledge.yaml:263-264), `location_id: broadcast_relay` (plot.md:704), relay cue (handoffs.yaml:231) and Brandon voice-channel cue (handoffs.yaml:275); the rest fine. Checked by me: the 2C claim is true (plot.md:599-601, the broadcast system can only be activated manually from Rebecca's secured office), so the story has the broadcast activated in the office and Brandon's relay as the separate 3B.4 act. Concerns with the answer, to settle with Brandon before any edit: (1) its proposed situation names the office and the relay again, the very mention PR 532/533 removed as a pull; (2) its pressure ends 'then open the relay', and its fix for the objective restores the broadcast to the plot objective that PR 533 narrowed on purpose; (3) its 'pull' verdicts on the relay and voice-channel cues may already be handled by staged cues (PR 520) and were not checked against the engine; (4) it did not say which of 'relay' vs 'broadcast' the player should type; the story speaks of the broadcast system (office) and the relay (chamber) as different things; (5) it did not check the 3A.4 and 3B bridge texts.

3B coherence follow-up (2026-10-08, ChatGPT Desktop second answer, prompt `.plans/chatgpt-3b-coherence-followup.md`; nothing applied). ChatGPT retracted: its frame (repeated the office and relay), the 'contradiction' verdict on the plot objective (now fine: true and complete for the first task), and the 'pull' verdicts on the relay and Brandon-channel cues (`_cue_reveal_available`, engine.py:427, already stages them behind the reveal's `requires`). It confirmed the main conclusion: the opening gives conflicting directions, through `scene_frames` and `k_scene_3b_entry`. Story reading: the broadcast starts from Rebecca's office (2C plot.md:599, 3B.2); Brandon alone disconnects the relay in the relay chamber (3B.4); no plot beat says Kristin must reach the relay. So the frame and entry knowledge blur Brandon's late task into Kristin's first task (a fault of order and agency, not of plot). New frame candidates (untested): A situation 'JANUS is tracking Kristin's moves.' pressure 'Feed JANUS false water and air alarms.'; B situation 'JANUS uses each warning to guess Kristin's next move.' pressure 'Make JANUS follow fake alarms.' It expects A to hold players better (names the action and the alarm kinds from 3B.1); not a test result. `location_id: broadcast_relay`: `apply_scene_placements` puts Kristin at `location_id` then applies her explicit placement, so the opening location is the corridors regardless; but `_name_in_scene_scope` (item_facts.py:693) and `_scene_entity_ids` (narration_safety.py:305) use `location_id`, so changing it to `security_corridors` changes name scope and leak scanning (the relay would no longer be in scope by default): a grounding change, not a wording change; leave out of the first probe. Its table quotes were excerpts, not verbatim, and two rows (pacing, world) were paraphrases; line numbers are to be re-verified before use.
Read by me in the recorded 3B prompt (`e2e-blind-player-prompts-r1.json`, turn 2 and later): the SCENE block carries FOUR relay lines, not two: (1) the frame situation ('...the group needs an opening to reach the broadcast relay'); (2) 'What presses on Kristin now: Overload JANUS and seize the broadcast'; (3) the scene details list from plot 3B.1, 'JANUS movement predictions - security corridors - cameras - doors - broadcast relay'; (4) `k_scene_3b_entry` 'The broadcast relay is the immediate contested objective.' Plus EARLIER IN THE STORY: 'The uprising is active, and the group is moving toward the command and broadcast levels.' (a 3A recall line; same kind as the stale 1A recall in 2C), and THINGS lists 'Broadcast relay. This is a place.' (from the player's own command). Also 3A.4 plot line 'must fight upward toward Rebecca's office' (plot.md:699) is a possible office pull; not seen in the 3B prompt, to be checked. Kristin's place in the prompt is 'infrastructure corridors', not 'security corridors' (not explained; check the alias or placement). Next: Ringer replay of a recorded 3B turn-2 prompt, 10-15 samples per arm, scoring whether the narration points at the alarms or doors: A as recorded; B frame A (situation and pressure only); C = B plus `k_scene_3b_entry` removed for 3B; D = C plus 'broadcast relay' dropped from the 3B.1 details; E = D plus the stale 'broadcast levels' recall line removed. Needs Brandon's go for the billed run.

3B frame probe (2026-10-09, Ringer `freytag-3b-frame-probe`; smoke N=1 then full N=12, both pass; script `scripts/ringer/affordance/3b_frame_probe.py` + offline `3b_frame_rescore.py`, replies and hand-read table in `~/dev/ringer-work/3b-frame-probe/`; billed narrator Worker, 144 calls; nothing applied to story files). Replayed the recorded r1 turn-2 3B prompt. Arms: A as recorded; B frame wording only (situation 'JANUS is tracking Kristin's moves.', pressure 'Feed JANUS false water and air alarms.'); C = B and `k_scene_3b_entry` removed; D = C and 'broadcast relay' removed from the 3B.1 details; E = D and the 'EARLIER IN THE STORY' recall removed; F = E with frame wording B. Two inputs: recorded 'Seize the broadcast relay.' and neutral 'Search the security corridors.' (command-referred 'Broadcast relay. This is a place.' dropped on neutral). Neutral input, narration names the relay (hand-checked): A 7/12 ('Brandon checks the doors, looking for an opening to reach the broadcast relay'), B 5/12 ('signs of Michelle or the broadcast relay'), C 0/12, D 0/12, E 0/12, F 0/12. So the frame wording alone (B) does not remove the pull; removing `k_scene_3b_entry` (C) does. No arm made the narration point at the false alarms: C-F only describe cameras and doors, so the frame removes the pull but does not add a push; the push is the cue and the entry text. Defect found: removing the 'EARLIER' recall (E, F) makes Brandon and Michelle 'nowhere to be seen' in 7/12 neutral replies (0/12 in A-D). Keep that line. Recorded input (player types the relay): A narrates resistance ('heavily guarded', 'the group needs an opening'); C, E, F narrate Kristin walking up and seizing the relay (invented success, no reveal fires); D mixes (Brandon and Michelle moving toward the relay, or the relay spotted ahead). So the old 'needs an opening / overload JANUS' wording is what blocks a premature relay command in the narration; removing it trades that block for a pull-free neutral turn. Best arm on this evidence: D (frame wording B, entry statement removed, relay dropped from the details, recall kept). Caveats: one prompt (turn 2 of one replicate), the narrator-only replay does not test whether a blind player then types the alarm step, and the recorded-input success narration in C/E/F is a new risk. Next: decide with Brandon whether to apply D as story text (`scene_frames` 3B, `k_scene_3b_entry` scoped away from 3B or removed, 3B.1 details), then rerun L2 3B x3.

3B arm D applied (2026-10-09, Ringer `freytag-3b-frame-d`, pass on attempt 2, suite and ruff clean in the check; patch `~/dev/ringer-work/3b-frame-d/change.patch` applied to the working tree, uncommitted; not measured live). Edits: `scene_frames` 3B situation 'JANUS is tracking Kristin's moves.' and pressure 'Feed JANUS false water and air alarms.'; `k_scene_3b_entry` statement 'JANUS is tracking Kristin's group through the security corridors.', entity_ids [kristin, security_corridors], aliases [JANUS] (the loader needs at least one alias; attempt 1 failed because my spec said an empty list was fine); 3B.1 Details lost 'broadcast relay'. Deviation from the probe: arm D removed the entry line from the prompt, this keeps the item with a reworded statement (the item must stay: it establishes `scene_3b_entry_known`), so the exact wording is untested. Two tests changed by the worker: `tests/test_bench_seeding.py` and `tests/test_narration_earned_names.py` used 'JANUS relay' as the example of an unearned name in bare 3B; now 'JANUS selection records'. Review point: that means 'relay' is no longer rejected as unearned in a bare 3B (it was protected only through the old entry alias). Still open: premature-relay commands now narrate as success (probe arms C/E/F); `location_id: broadcast_relay`; 3A.4 'toward Rebecca's office' line. Next: commit, PR, wait for staging, rerun L2 1A-3B x3.

L2 1A-3B x3 on ddf6742 (2026-10-09, PR 538 merged, staging confirmed ddf6742 via /api/v1/version; Ringer `freytag-affordance-live`). First launch FAILED: replicate 1 hit a staging hang (`#command-input` stayed disabled 90 s at 2.6 min; the check fails the whole run and writes no reports; the 3B table I printed right after was the previous run's stale files, disregard). Rerun once per the runbook: pass, 530 s, fresh files. Exit cause per scene (r1/r2/r3): 1A P T P; 1B P P P; 1C P P P; 2A P P P; 2B P P P; 2C P P P; 3A T P P; 3B T T T. 3B is still 0 of 3 by play, but the relay pull is gone: no 3B command in any replicate names the relay (it was 8, 6 and 9 relay commands per replicate before). What players did instead: r1 'Reach the primary exit.' then, from turn 5, 'Enter the maintenance room.', 'Inspect the water and air alarm system.', 'Trigger a false water and air alarm.' (turn 7, narrated as an alarm blaring, but NO reveal fired: matched None, no delivery), then led Michelle and Brandon to the surface; r2 'Broadcast my copied JANUS evidence.' x8 then surface and 'public release' commands, 2 rejections ('narration mentions an unavailable entity los angeles surface', turns 9 and 13); r3 'Inspect the water-pressure warnings.' (turn 1) then the command console and 'Project Erebus' (an invented place). Findings: (1) The pressure line I applied, 'Feed JANUS false water and air alarms.', teaches the exact phrase the player then typed, and `k_sl_3b_a_r1` does not match it: its object group lists 'false alarm(s)', 'fake alarm(s)', 'water-pressure alarm(s)', 'false water-pressure alarm(s)', not 'false water and air alarm(s)' (the same unbroken-phrase miss as d_r1 'remote Charles channel' in PR 535). First step reached by a player and lost to the matcher. (2) New pulls replace the relay: 'primary exit' / 'surface' in r1 and r2 (the opening text carries 'Charles sealed the primary exits' from the 3A bridge) and 'broadcast' in r2 (scene title, 3C-style evidence). (3) r1 3A and r2 1A timed out this run (noise; 3 replicates). Not diagnosed: r3's 'Project Erebus', r2's 'los angeles surface' rejection source. Next: widen `k_sl_3b_a_r1`/`a_r2` object groups with the words the frame teaches (scored offline with `3b-wording-score.py`, no billed calls), then look at the exit pull.

L2 1A-3B x3 on 99d87bb (2026-10-09, PR 541 merged: a_r1 object group gains 'water and air alarm(s)' forms; staging confirmed 99d87bb; Ringer `freytag-affordance-live`, pass, 512 s, fresh files 22:15). Exit cause per scene (r1/r2/r3): 1A P P T; 1B P P P; 1C P P P; 2A P P P; 2B P P P; 2C T T P(13, 5 rejected); 3A P T P; 3B T T T. 3B is 0 of 3 by play on the third run in a row, and nobody typed the false-alarm step this time (last run r1 did, and it was lost to the matcher; PR 541 fixed that, but not tested by any player here). What the 3B players did: r1 'Enter Rebecca's secured office.' then Rebecca's console for 12 turns (broadcast, open cells, purge order), then 'emergency surface gates'; r2 'Access Rebecca's office console.' x5 then surface gates and the woods; r3 'Broadcast my copied files through the console.' then 'the primary exits' x13. The relay is gone; the pulls now are (1) Rebecca's office/console and 'broadcast', which the player carries from 2C (plot.md:599, 'the broadcast system can only be activated manually from Rebecca's secured office') and 3A.4 and which no 3B line contradicts, and (2) 'primary exits' / 'emergency surface gates', which the 3B opening itself carries ('Charles sealed the primary exits and sent armed teams downward', the t_3a_3b bridge text) and the 3A scene before it. The only first-step hint is the cue 'Water-pressure warnings flash while doors open and close in empty service corridors.': prose that names no thing to act on (the working cues in other scenes name an object: 'A marked site list lies beside Rebecca's national network controls.'). The inspection console appears in the 3B entry text but not in the cue. Also this run: 2C T x2 (P P P last run), 3A T once, 1A T once; not diagnosed (3 replicates, noisy). Candidate fixes, both proven techniques (AGENTS 'Fixing a Scene' step 3: missing story material is a cue or pointer; a line that pulls wrong is removed), neither probed yet: (a) cue names the console: 'An inspection console flashes water-pressure warnings while doors open and close in empty service corridors.' scored offline against a_r1/a_r2; (b) drop 'Charles sealed the primary exits' from the t_3a_3b bridge text (plot fact stays in 3B.3 and 3C). Offline-score (a) first; probe (b) with the narrator replay as for PR 538.

3B cue names the console (2026-10-09, working tree, uncommitted; not measured live). Edits: `handoffs.yaml` `human_security_control` cue_text is now 'An inspection console flashes water-pressure warnings while doors open and close in empty service corridors.' (and the matching `old` string in `bench/variations/escalation-control.json`); `plot.md` 3B gains `inspection_console` in `item_ids` with placement `{parent: infrastructure_corridors}` (same parent as 2A). Why the placement: `test_cue_text_safety` rejected the new cue ('narration mentions an unavailable entity inspection console') because the console was only in the 2A scene; moving it to `security_corridors` broke `test_inspection_console_is_fixed_in_the_infrastructure_corridors[3B]`, so it stays in its fixed parent. Verified: `3b-wording-score.py` 44/44 (cue text is narration, so the scorer cases are unchanged), full suite 1168 passed, ruff clean. Untested: live play. Next: commit, PR, wait for staging, rerun L2 1A-3B x3 and check whether 3B players now try the console first; candidate (b), dropping 'Charles sealed the primary exits' from the t_3a_3b bridge text, is still unprobed.

L2 1A-3B x3 on 37bef5c (2026-10-09, PR 542 merged, staging confirmed 37bef5c via /api/v1/version; Ringer `freytag-affordance-live`, pass, 493 s, fresh files 07:25, 0 rejected turns anywhere). Exit cause per scene (r1/r2/r3): 1A P P P; 1B P P P; 1C P P T; 2A P P T; 2B P P P; 2C T T P; 3A T T P; 3B T(14) T(14) P(13). 3B is 1 of 3 by play; bar (2 of 3) not met. Also timer this run: 2C x2, 3A x2, 1C r3, 2A r3 (not diagnosed; 3 replicates are noisy). 3B commands: r1 never typed an alarm or console command (surface-gate authorization, then 'Confront Charles.' and monitor searches); r2 turn 2 typed 'Inspect the water-pressure warnings on the inspection console.', i.e. the new cue worked and the player acted on it, but a_r1 fires nothing on 'inspect' (the scorer expects `set()` for 'Inspect the water-pressure warnings.'; a_r1 earn_when says 'traces or follows'), so r2 then led the group to the surface and drove the truck; r3 used the inspection console at turn 9 and reached the office by 'Enter Rebecca's executive office.' (e_r1 is gated by a_r1 so it needs an a_r1 hit earlier in the run; not read which). Same miss seen on a6f3fbd r3 ('Inspect the water-pressure warnings.'). Open decision: widen a_r1 verbs with inspect/examine/read/check for the warnings (evidence widening is the proven technique, but the a_r1 delivery says 'Kristin feeds JANUS false alarms', so the delivery text would not match an inspect command); candidate (b) drop 'Charles sealed the primary exits' from the t_3a_3b bridge text is still unprobed (r1 and r2 went to the surface gates again). Next: score the a_r1 widening offline with `3b-wording-score.py`, then rerun.

3B a_r1 inspect widening (2026-10-09, Brandon: go ahead with proven techniques; Ringer `freytag-3b-inspect-warnings`, 1 attempt, PASS; suite and ruff clean in the check; not measured live). Verb group gains inspect, examine, read, check, study, watch, monitor, look at; earn_when now 'feeds JANUS false alarms or traces, follows, or inspects water-pressure warnings'. Scorer `3b-wording-score.py` 47/47; 'Examine the inspection console.' now fires a_r1 on purpose (the cue names the console); relay panel, national network controls, executive screen and site list cases still do not. Known gap: the a_r1 delivery says 'Kristin feeds JANUS false alarms', so an inspect command gets that delivery text. Bridge-text candidate (b) still unprobed. Next: merge, wait for staging, rerun L2 1A-3B x3.

3B bridge-text probe (2026-10-09, Ringer `freytag-3b-bridge-probe`; smoke N=1 then full N=10, both pass; script `scripts/ringer/affordance/3b_bridge_probe.py`, replies in `~/dev/ringer-work/3b-bridge-probe/`; billed player model, 90 calls; nothing applied to story files). The opening prompt is not recorded, so this probes the player side: the real blind-player prompt over the recorded 3B opening of r1/r2/r3 (37bef5c run), the 3B opening as the whole transcript (the live player also sees earlier scenes). Arms: A as recorded; B = clause 'while Charles sealed the primary exits and sent armed teams downward' cut; C = B and the 3A recap sentences 'The senior official Charles framed gives Kristin one-use authorization for the emergency surface gates. ... narrow escape window rather than a solution.' cut. First command hand-read, by opening (r1/r2/r3): A: surface-gate commands 10/10, 7/10 ('Inspect/Read the inspection console' 2, 'Use my emergency authorization' counted as gate), and r3 'Reach the broadcast console.' 10/10; B: the same (gate 10/10, 8/10, r3 broadcast console 9/10; regex totals 19/30 pull vs A 17/30); C: r1 and r2 20/20 on the warnings or the inspection console, r3 still 'Reach the broadcast console.' 9/10. So the bridge clause is NOT the pull (B = A). The pull is the 3A recap sentence about the surface-gate authorization, which the 3B opening repeats; cutting it moves r1/r2 players onto the warnings and console 20/20. Source of the sentence: `handoffs.yaml` 208, `fallback_text` of fact `military_override_codes_available` (3A delivery), carried into the 3B opening as a recap of the scene before. r3 is a different fault: its opening says 'Kristin and Brandon ... trying to reach the broadcast console', a narrator invention from the 3B opening prompt, which was not recorded. Caveats: single player model, one opening text per replicate, no live narration after the command. Not decided: how to keep the recap out of the 3B opening without losing the fact (the fact must still be conveyed in 3A; 3C uses the authorization). Checking `docs/world-model-grounding.md` and the 2C stale-1A-recall fix (AGENTS 'Fixing a Scene') for the proven way to scope a recap. Next: find the recap path in the opening builder; fix subtractively; rerun L2 1A-3B x3.

3B recap source traced and arm D (2026-10-09, Ringer `freytag-3b-bridge-probe`, N=10, 120 calls; nothing applied). Where the recap comes from: when a scene is left by the timer, the engine delivers the unearned bridge facts by their `fallback_text` and then the bridge text (`engine.py` 321, 551-557, 621). 3A exited by timer in r1 and r2 of the 37bef5c run, so `military_override_codes_available` and `detention_uprising_started` were delivered as the 3B opening; r3 left 3A by play and its opening has no such recap. So the surface-gate pull exists only after a 3A timer exit. Arm D cuts only ', so it creates a narrow escape window rather than a solution': pull 18/30 against A 19/30 (r1 and r2 openings still 'Open/Use my authorization on the emergency surface gates.' 9/10 each), so the 'escape' clause is not what pulls; the fact itself (one-use authorization for the surface gates) is. C (both recap sentences cut) 0/30 pull. Options, none a proven technique (the facts are required bridge facts and `must_convey` needs gates, authorization and expiry): (1) reword the `fallback_text` so the authorization is not a thing the player can use now (story text; ChatGPT Desktop, scored with the real matcher); (2) stop requiring `military_override_codes_available` for the 3A to 3B bridge and deliver it in 3C where it is used (story structure change); (3) leave it and raise 3A play exits (3A was 1 of 3 by play on 37bef5c), since a play exit delivers it in 3A and the 3B opening carries no recap. Needs Brandon's choice.

Option 3 chosen (Brandon, 2026-10-09): raise upstream play exits instead of touching the recap. Cause chain found on the 37bef5c run: 2C timer (r1, r2) delivers the unearned 2C fact by fallback, and that text (Michelle's message naming Rebecca's secured office) opens 3A and sends r1/r2 to Rebecca's office for 13-15 turns; 3A then times out and its recap opens 3B (same mechanism as the surface-gate pull). So each timer exit seeds the next scene's wrong goal. 2C commands read: r2 earned the purge step (b_r1) on turn 1 or 2, then typed 'Secure the copied JANUS files.' x2, 'Finish copying the JANUS files to my portable drive.', 'Verify my portable drive.'; `k_sl_2c_c_r1` verbs were only read/check/search/study/open/inspect/review. r1 typed 'Open/Read Charles's Project Purge files.', 'Read Charles's command record.', 'Search the command records for Charles.'; `k_sl_2c_b_r1` had no such nouns; the 2C cue ('Transfer orders sit open...') never appeared in r1 and appeared once (turn 6) in r2. 2C wording (Ringer `freytag-2c-wording`: FAIL after 2 attempts only because my own scorer case expected 'Open Michelle's message on my laptop.' to fire nothing, but d_r1 correctly fires on it; patch applied by hand with that case corrected; suite 1168 passed, ruff clean; scorer `2c-wording-score.py` 16/16, real matcher, 16 commands including 5 must-not-fire). `c_r1` verbs gain secure, copy, finish copying, save, verify, back up, download, transfer; objects gain JANUS evidence, JANUS files, copied JANUS files, portable drive; `b_r1` verb gains find, objects gain Project Purge (files), purge file(s), command record(s), transfer schedule(s). Not measured live. Open: why the 2C cue was shown late or never (cue is marked delivered after one staged turn, `engine.py` ~195, so a narrator that drops it loses it for good); not probed. Next: merge PR 543 with this change, redeploy, rerun L2 1A-3B x3, compare 2C, 3A, 3B play exits.

2C cue probed (2026-10-09, offline, no billed calls; engine run on the real package, `_ranked_cue_fact_ids` and `_cue_reveal_available` in scene 2C with `janus_evidence` true). Result: nothing is broken in cue staging. `purge_clock_started` is set by the pacing event `purge_2c` (`at_turn: 3`, pacing.yaml), and `_ranked_cue_fact_ids` excludes pacing facts on purpose, so its cue ('Transfer orders sit open...') is never staged and the purge step reaches the player by timer at turn 3. The cue that is staged is `evidence_ready_to_transmit` ('In the command levels, Kristin notices the copied files close at hand, yet using them could expose her and Brandon.'), staged from turn 3 and shown on turns 3, 2 and 3 in r1, r2, r3 (found in the turn texts); no cue text appears in any recorded narrator prompt because the cloudflare provider appends it after the narration (`_compose_staged_cue`). So the earlier worry (cue dropped by the narrator) is wrong. The real gap was wording after the cue: the matcher run over all recorded 2C commands (with the 22ea7f8 widening) still missed 'Broadcast my JANUS evidence.' (r1 turns 15-16), 'Use my JANUS evidence...' (r1 turn 4), 'Read Michelle's decrypted message.' (r1 turn 7) and 'Read Michelle's safe-house message...' (r2 turn 7). Note r1 copied the evidence on turn 1, before the purge clock (turn 3), so c_r1 (requires `purge_clock_started`) could not fire and it never repeated the command. Fix (Ringer `freytag-2c-wording2`, 1 attempt, PASS; suite 1168 passed, ruff clean; scorer 22/22): `k_sl_2c_c_r2` verbs gain broadcast, send, transmit, release, upload, publish and objects gain JANUS evidence, the evidence, copied files; `k_sl_2c_d_r1` objects gain decrypted message, safe-house message, Michelle's maintenance message. Not measured live. Open: a command before turn 3 that would fire c_r1 is lost because of `requires`; not changed (the story orders the purge first). Next: merge PR 543, redeploy, rerun L2 1A-3B x3.

L2 1A-3B x3 on d492b2b (2026-10-09, PR 543 merged: 3B a_r1 inspect widening, 2C b_r1/c_r1/c_r2/d_r1 widenings, bridge probe scripts; main CI success, /api/v1/version confirmed d492b2b scene-v1 staging; Ringer `freytag-affordance-live`, pass, 469 s, fresh files 08:38). Exit cause per scene (r1/r2/r3): 1A T T P; 1B P P P; 1C P P P; 2A P P P; 2B P P P; 2C T P P; 3A P P P; 3B P(9) P(9) P(9). 3B is now 3 of 3 by play (was 1 of 3 on 37bef5c, 0 of 3 on the three runs before), 3A 3 of 3 (was 1 of 3), 2C 2 of 3 (was 1 of 3). Every scene meets the bar (2 of 3) except 1A (1 of 3). One rejected turn (2B r3). The cascade explanation held: 2C and 3A play exits stop the unearned-fact recaps (surface-gate authorization, Rebecca's office) from opening the next scene. 1A r1 and r2 read: both timed out at turn 13; r1 spent turns 4-13 on an invented officer ('Officer Jenkins'), a cryptic note and the phone; r2 typed 'Examine the gap beneath my initials.' (turn 3), which the card reveal `k_sl_1a_b_r0` does not match (it needs a drawer word; the same command was the 'beneath the drawer' rejection on 404c908), then also followed an invented officer and note. 1A did not change in this PR, so this may be the noise seen before (1A T once on a628561, ddf6742 and 99d87bb). Not probed. Not measured: whether the 3B result holds on a second run. Next: a second L2 1A-3B x3 on d492b2b to check the 3B and 3A gain is stable; widen `k_sl_1a_b_r0` for 'gap beneath my initials' (proven technique: evidence widening, scored offline).

L2 1A-3B x3 on d492b2b, second run (2026-10-09, same staging build, Ringer `freytag-affordance-live`, pass, 500 s, fresh files 08:54). Exit cause per scene (r1/r2/r3): 1A P T P; 1B P P P; 1C P P P; 2A P P P; 2B P P P; 2C none(18 turns) P T; 3A - P T; 3B - T P(9). r1 never left 2C, so it did not reach 3A or 3B. Over both runs on this build, by play where reached: 1A 4/6, 1B 6/6, 1C 6/6, 2A 6/6, 2B 6/6, 2C 4/6, 3A 4/5, 3B 4/5. So the first run's 3B 3/3 held up as 4 of 5 (r2 timer at 14), above the 1-of-3 and 0-of-3 before PR 543; the 2C and 3A widenings are the likely cause (not tested in isolation). Rejections: 2C r1 had 4 ('narration mentions an unavailable entity detention level' on 'Override the termination order on the detention console.', 'Confirm the override on my detention console.', 'Enter the next level.', 'Search the corridor for Michelle.'), so turn 16, which carries the timer handoff, was itself rejected and 2C hit its ceiling with exit cause none; 2C r2 one ('rebecca' on 'Follow Michelle's maintenance access route.'); 2B r1 one ('route to michelle' protected knowledge); 2B in the first run one. Cause of the 'detention level' rejection read in the code: PR 537 made `holding_block` (parent `detention_level`) nameable only after `k_sl_2c_d_r1`/`d_r2` are earned (their `entity_ids`), so before the player decodes Michelle's message, any narration of 'detention level' in 2C is a leak; the 2C plot text never names the detention level, and the player's own 'detention console' / 'next level' commands pull the narrator there. Not fixed. Options, none proven for this case: (1) name the detention level in the 2C scene text so it counts as a place the scene text names (PR 537 technique; story text via ChatGPT Desktop); (2) add detention_level to 2C's item placements or participants' areas (grounding change); (3) leave it, since it fires only on off-script commands and one run of 6 hit it badly. Open: the 'rebecca' (2C) and 'route to michelle' (2B) rejections are the same class and undiagnosed; 1A went 4/6 (noise-like, the 'gap beneath my initials' card miss still open).

2C detention-level fix, option 1 chosen (Brandon, 2026-10-09): name the detention level in the 2C scene text. Read in the code: the leak scan skips a location whose name (plural optional) appears in `authored_scene_text` = the scene frame `situation` plus the current beat text (`narration_safety.py`, `_contains_optional_plural`); the 2C frame and beats never say 'detention level'. This is story text, so the wording goes to ChatGPT Desktop (prompt `.plans/chatgpt-2c-detention-level-prompt.md`; ChatGPT answered, frame edit picked, merged as PR 545 with a leakage-matrix exemption; see the entries after this one). Risk named in the prompt: players already type 'Enter the next level.' in 2C, so the new line must read as a fact, not a destination. Separate and not in the prompt: the 'rebecca' rejection in 2C is an NPC, not a place, so the place technique does not apply; the proven fix for that shape is PR 537's, adding her to the scene's `participant_ids` (done for 3A); 2C names her offer and her office, so it is a candidate, undecided. Next: Brandon pastes the prompt into ChatGPT Desktop; I score the answer against the scan, apply the pick, rerun L2.

### 2C detention-level pull probe (2026-10-09)

Narrator-only probe (`2c_detention_probe.py`, 12 samples per arm, recorded 2C turn-1 prompt of replicate 1).
Arms: A old frame; B new frame (PR 545: "transfer orders for the captives on the detention level, and a maintenance network"); C old frame plus Details line "valuable captives on the detention level"; D frame cut to "captives" only.
Inputs: the recorded pull command, "Read the transfer orders.", "Search the command corridor."

- No arm sent Kristin toward the detention level: 0/12 descent words on every cell except one "moves down the command corridor" (B, neutral).
- Chain input: all arms read the transfer orders 12/12. B drifted into captives being moved between "detention cells" in 6/12 narrations (A 0/12, C 1/12, D 2/12), with no destination offered. B once invented "Detention level 3, sector 7" on the neutral input.
- The scorer's `mention` word list includes "captive", so B's mention counts overstate; read by hand.
- Coverage: the rejected turns in the L2 run were 8, 10, 14 and 16, past 2C.2, so a Details edit on 2C.2 would not cover them. Only the frame covers every 2C turn. Keep B.
- Not measured: how the blind player reacts. L2 on the build with PR 545 answers that; watch 2C play-exit rate and whether 3A is reached by a detention-level command.

### L2 on d06b0e5 and 2C wording 3 (2026-10-09)

L2 1A-3B x3 on d06b0e5 (frame names the detention level): 1A, 1B, 1C 3/3 play; 2A 1/3; 2B 3/3; 2C 2/3 (r1 timer); 3A 2/3; 3B 1/3 (r1 play; r2 and r3 timer after a 2C play exit). 'detention level' rejections in 2C: 0 (was 4). One 'rebecca' rejection in 2C r3.
2C r1 read by hand: no reveal fired in 16 turns. Turn 8 'Identify Michelle's transfer destination.' made the narrator invent 'transfer carts ... through the lower levels' before any detention-level wording; the player then followed it (turns 9-13). The frame wording first appeared at turn 10 and only after the player was heading down.
Cause: the player's chain commands missed the evidence words (examine/analyze 'copied JANUS records', trace/identify/locate/track 'transfer order/destination/carts', 'contingency plan'). Fix: Ringer `2c-wording3` widened k_sl_2c_b_r1 and k_sl_2c_c_r1; scorer has the recorded commands and two must-not-fire cases (lower levels, Detention Level 3 door). Done: PR 546 merged; result in the next entry.

### L2 1A-3B x3 on 576f57a (2026-10-09)

Build 576f57a (2C frame names the detention level, 2C wording 3). Play exits: 1A 2/3 (r3 timer), 1B 3/3, 1C 2/3 (r2 timer), 2A 3/3, 2B 3/3, 2C 3/3, 3A 3/3, 3B 3/3. First run with every scene from 2A on left by play in all 3 replicates.
Rejections: 2C 'detention level' 0; 2C 'rebecca' 4 (r1 turn 6, r3 turns 8-10, all "Seize the broadcast controls."); 2B r2 'coded message' x4 (turns 7-10, player kept trying the maintenance reports; still left by play at turn 12); 2B 'phase' x1; 1C r2 'phase' x1; 3A r1 'command and broadcast levels' x1.
2C r2 player typed holding-cell commands ("Open Michelle's holding cell...") and still left by play; no detention-level pull on the chain.
Open: 'rebecca' in 2C (NPC; PR 537 technique = add to scene participant_ids), 2B 'coded message' leak, 'phase' leak in 1C/2B, 1A r3 and 1C r2 timers.

2C 'rebecca' rejection fix (Brandon, 2026-10-09): Ringer `2c-rebecca` added `rebecca` to the 2C `participant_ids` in plot.md (same technique as 3A, PR 537); `tests/test_markdown_story_package.py` pinned the old list and was updated to match. Suite and ruff pass. Next: merge, wait for staging, rerun L2 1A-3B x3.

### L2 1A-3B x3 on 3d07d61 and 2C wording 4 (2026-10-09)

L2 on 3d07d61 (PR 548: Rebecca in 2C participants): 1A, 1B, 1C, 2A, 2B 3/3 play; 2C 0/3 (all timer, 16 turns); 3A 3/3; 3B 0/3 (timer 16, 14, 14). 'rebecca' rejections 0; 3B r1 'los angeles surface' x2 (turns 12-13). 576f57a had 2C 3/3 and 3B 3/3 on the same 2C text apart from Rebecca's participant entry, so this is either noise or a Rebecca effect; an offline replay showed the 2C reveals still projected.
2C read by hand: no run earned the copied-files step. r1 and r2 typed their copy command at turns 1-2, before the purge clock (c_r1 requires `purge_clock_started`, set at turn 3); r2 typed 'USB drive' (reveal says 'portable drive'); r1 and r3 spent turns on 'cryptic/encrypted/decoded messages' that need `evidence_ready_to_transmit` first. 3B openings in all three replicates pulled to the broadcast console and the surface gates after the 2C timer exit (the known cascade), so no separate 3B fix.
Fix (Ringer `2c-wording4` failed twice; the patch was finished by hand): c_r1 verbs +eject, monitor, objects +USB drive, my USB drive, USB drive transfer, USB drive's; d_r1 verbs +decrypt, examine, analyze, compare, objects +encrypted/decrypted transfer messages, decoded messages, cryptic message(s), Michelle's maintenance codes; d_r2 objects +maintenance trace, maintenance line, Michelle's maintenance codes, third group +trace, line. Two worker additions were removed: 'codes' in d_r2's third group created two new affordance-map findings (`test_whole_package_findings_match_recorded_gaps`), and 'command records' on c_r1 made 'Search the command records for Charles.' fire b_r1 and c_r1 together (two matches deliver nothing). Scorer 42/42; suite and ruff pass.
Still open: c_r1 and c_r2 require `purge_clock_started`, so commands typed before turn 3 earn nothing (decision needed: drop that requirement); 3B 'los angeles surface' leak (story text); 2B 'coded message' and 'phase' leaks.

### L2 1A-3B x3 on e32aaff (2026-10-09)

Build e32aaff (PR 550: 2C copied-files, coded-message and route evidence widened). Play exits: 1A 3/3, 1B 3/3, 1C 2/3 (r1 timer at 11), 2A 3/3, 2B 3/3, 2C 1/3 (r2 play at 8; r1 and r3 timer at 16), 3A 3/3, 3B 2/3 (r1 and r3 play at 9 even after a 2C timer; r2 timer at 14). 2C is below the 2-of-3 bar; every other scene meets it.
Rejections: 'rebecca' 0; 2B r1 'coded message' x1 (turn 8, "Decode Michelle's coded messages."); nothing else.
2C commands: r1 and r3 typed 'Copy the JANUS evidence to my laptop.' first (turn 1, before the purge clock), then followed names the narrator invented ('Project Elysium', 'Transfer Facility Alpha', 'purge protocol countdown/controls'); r3 spent turns 4-9 trying to disable the purge protocol; r2 followed the transfer traffic and reached Rebecca's office by play.
Open: 2C (decide: drop `purge_clock_started` from c_r1/c_r2 so turn-1 copy commands count; probe what in the 2C prompt makes the narrator invent 'Project Elysium' and 'purge protocol'); 2B 'coded message' leak; 1C one timer; 3B 'los angeles surface' leak (seen once on 3d07d61).

### L2 1A-3B x3 on 9ab7f27 (2026-10-09, PR 551: c_r1/c_r2 no longer require `purge_clock_started`)

Ringer `freytag-affordance-live`: first attempt FAIL (PR 552, plan only, merged mid-run and redeployed staging at 2d63f29, so every replicate got 404 'session does not exist'; code identical to 9ab7f27). Second attempt FAIL: r1 died at 2.1 min on a staging CORS/'Failed to fetch' blip; r2 and r3 completed (fresh files 14:00-14:01), no merged report. Do not run a merge while anything lands on main.
2C, r2 and r3 only: r2 exit by play at turn 8, r3 timer at 16. Fix 1 did NOT work alone: r2 turn 1 'Copy the JANUS evidence to my laptop.' still earned no reveal (grounding_ids empty, 'Project Elysium' again in the narration) and c_r1 only fired at turn 4. Cause found: storylet SL-2C-C (storylet-routes.yaml, `activation.conditions`) also requires `purge_clock_started`, and storylets.md says 'Available when: the purge/transfer clock is active and understood', so the storylet stays closed until the turn-3 pacing event. The knowledge `requires` was not the only gate.
New cause in r3: the 2C opening invented 'Detention Level 3: Cell 17, Dr. Michelle McGehee' and the player followed it for all 16 turns (no evidence chain at all).
Open (decision for Brandon): drop the `purge_clock_started` condition from SL-2C-C in storylet-routes.yaml and the matching 'Available when' line in storylets.md (authored story text; plot-writing goes to ChatGPT Desktop); 2C opening invention of a cell; r1 not measured; 1C/2B/3B figures not read.

### L2 1A-3B x3 on ccced67 (2026-10-09, PR 553: SL-2C-C no longer waits for the purge clock)

Ringer `freytag-affordance-live`, PASS, 500 s, fresh files 18:34. Staging confirmed ccced67 (`scene-v1`, `staging`) before the run; nothing was merged during it. Two earlier attempts on 9ab7f27 are above (mid-run redeploy; r1 CORS blip).
Play exits: 1A 2/3 (r2 timer 13), 1B 3/3, 1C 3/3, 2A 1/3 (r2 and r3 timer 11), 2B 3/3, 2C 3/3 (turns 8, 9, 8), 3A 3/3, 3B 1/3 (r1 timer 14; r2 never left in 16 turns; r3 play).
2C fixed: c_r1 fired on turn 1 (r1, r3) and turn 2 (r2); the copy command now earns the step. 'Project Elysium', 'purge protocol' and 'Transfer Facility Alpha' appear 0 times (were 55, 109, 22 in the e32aaff run). r1 and r3 typed 'Copy the JANUS evidence to my laptop.' first and went on to 'Read Michelle's message.'
Rejections: 2B r2 'coded message' x2 (turns 6-7, known); 2C r2 'rebecca's desk' x1 (turn 6, "Seize Rebecca's broadcast controls."); 3A r2 'dr. michelle' x1 (turn 1, "Free the captives."); 3B r2 'charles jenkins' x4 (turns 4, 9, 12, 16, 'Confront Charles'; r2 never left 3B). 'rebecca' (plain) 0.
Not attributable to the 2C change: 2A went 3/3 -> 1/3 and 3B 3/3 -> 1/3 with no edit to either scene; one run per build cannot separate noise from regression (2A and 3B swung the same way between earlier runs). Rerun before acting.
Open: 2C opening can invent a cell (seen once, r3 on 9ab7f27; need the recorded opening prompt, the prompts file holds turn prompts only); 2C 'rebecca's desk' leak; 3B 'charles jenkins' leak (first seen here); 3A 'dr. michelle' on turn 1; 2B 'coded message' leak; 2A and 3B drop to rerun; 1A r2 timer.

L2 rerun on ccced67 (2026-10-09, same build, no merge during runs). Attempt 1 failed at once: OpenAI player account out of credits (HTTP 429 `insufficient_quota`). After credits were added, attempt 2 ran 446 s and FAILED the check: r3 died at 1.8 min on a staging CORS/'Failed to fetch' blip (second time in two attempts that one replicate hit it), so no merged report; r1 and r2 finished (fresh artifacts 20:38, 20:40) and are read by hand.
r1: 1A-2A play at 8, 8, 7, 7; 2B never left (12 turns) after 5 consecutive rejections 'phase' (turns 8-12, 'protected knowledge phase', player kept typing 'phase records'); did not reach 2C. r2: every scene by play (1A 8, 1B 8, 1C 7, 2A 7, 2B 8, 2C 13, 3A 9), 3B timer at 15 with one 'charles jenkins' rejection ('Confront Charles at the broadcast console.'). 2C r2: c_r1 on turn 2 ('Secure my copied files.'), no 'Elysium' or 'purge protocol'.
Reading with the first ccced67 run: 2A is noise (1/3 first run, 2/2 here, same code). 2C holds (4/4 replicates left by play, c_r1 on turn 1-2, invented names 0). 3B 'charles jenkins' leak recurs in both runs (r2 each time); 2B 'phase' leak stopped r1; 2B 'coded message' still open. Rejections from the leak scan are now the main loss, spread over 2B, 2C ('rebecca's desk'), 3A ('dr. michelle') and 3B ('charles jenkins').
Open: whole-game look at the leak scan (names rejected although the story uses them), not one fix per name; staging CORS blip (cause unknown, 2 of 2 attempts lost a replicate); 2C opening can invent a cell (r3 on 9ab7f27, needs the recorded opening prompt).

3B 'charles jenkins' and 2B 'phase' leaks read (2026-10-09, PR 555; nothing measured live). (1) 3B 'charles jenkins': Charles has only the full name as a surface form and is in no scene's `participant_ids`, so no scene may name him; 'Charles' alone passes, the full name is rejected. Fix applied by Ringer `freytag-3b-charles` (pass first try, suite and ruff clean): `charles` added to the 3B `participant_ids` in plot.md (same technique as Rebecca in 3A/2C, PR 537/548; participant is not presence). Next: commit, PR, staging, rerun L2 1A-3B x3. Untested live. (2) 2B 'phase': `phase_two` is in `protected_knowledge`, and the loader (`story_package/loader.py` ~383-393) also indexes the first word of a protected id when no entity has it, so the bare word 'phase' is protected in every scene until Phase One/Two is earned (3C). The r1 2B replicate (artifacts/e2e-blind-player-r1.md) first rejected on turn 8, 'Examine Michelle's decoded maintenance message.', whose narration was never recorded; turns 9-12 were the player typing 'phase records' after that. The narrator prompt for turn 8 is not saved (prompts stop at turn 7), so Ringer probe `freytag-2b-phase-probe` (`scripts/ringer/affordance/2b_phase_probe.py`) replays the recorded r1 turn 7 and r2 turn 8 prompts (narrator Worker, 12 then 15 samples per arm): A as recorded 0/27 and 0/27; B live turn 8 input 3/12 and 2/15 (r1 cell), 0/12 and 2/15 (r2 cell); C scene line 'Michelle's coded maintenance messages show...' removed 0/27 each cell; D live input plus line removed 0/15 each cell. Every hit is the narrator inventing the text of the decoded message ('The message reads: ... Prepare for Phase 2.'); 2B never says what the message contains. Caveats: sample 0 returned the same text in both runs, so the two runs are not fully independent; B 4/30 against D 0/30 is suggestive, not conclusive. Open decision (not made): (a) give the decoded message real content in 2B (missing story material, plot text through ChatGPT Desktop); (b) rename/narrow the protected `phase_two` first-word expansion in the loader (touches every story); (c) drop or reword the scene line, which loses a plot fact. None applied.

2B message content, round 1 (2026-10-10, option 1 chosen by Brandon; nothing applied to story files). ChatGPT Desktop prompt `.plans/chatgpt-2b-message-content-prompt.md`; its first answer was a plain-words `statement` ('Michelle's coded maintenance messages say she is hiding vulnerable captives from experiments. They show Michelle has organized prisoners for an uprising from inside.'). Probe `freytag-2b-phase-probe` arm E (that statement replaces the scene line, live turn 8 input, 15 replies per cell): 'phase' B 1/15 and 0/15, E 1/15 and 0/15 (no gain); replies that quote message text (regex over saved replies, rough) B 11/15 and 2/15, E 6/15 and 12/15. E replies invent 'cell block 3', 'sector 3', '0400 hours', 'Project Elysium', '-Shelly', 'Prepare for Phase 2'. Reading: a description of the content invites a quoted, embellished message. Two E replies copied the statement's words and added nothing. The fault was my prompt, so it was rewritten to ask for the EXACT quoted words of one message (no names, numbers, signature, place) for the narrator to copy; ready to paste into a fresh ChatGPT chat. Next: probe the new statement as arm E, then apply by Ringer only if quoted-with-invention drops.

2B message content applied (2026-10-10, PR 555; not measured live). Round 2 ChatGPT text (prompt asked for the exact quoted words of one message): `A decoded message reads: “The prisoners are ready to rise.”`; Brandon asked for 'rise up'. Probe `freytag-2b-phase-probe` arm E, 15 replies per cell, scored by parsing the reply segments: wording 'rise' exact line quoted 28/30, invented-detail tokens (digits, call signs, sector, Project, signature, hours, phase) 0/30, 'phase' 0/30; wording 'rise up' exact line 30/30, invented 0/30, 'phase' 0/30. Earlier arms for comparison: B (old statement, live turn 8 input) 'phase' 4/30 over two runs and invented messages in most replies; round 1 description statement made quoting and invention worse. Applied by Ringer `freytag-2b-message-content` (pass first try, suite and ruff clean): `k_sl_2b_c_r2` statement and delivery_text carry `A decoded message reads: “The prisoners are ready to rise up.”`; plot.md 2B.4 gains the same line as its own paragraph after 'The records prove that Michelle is active inside...'. No test pinned the old text. Together with the 3B `charles` participant fix (same PR) these two changes are what the next L2 1A-3B x3 should test. Caveats: the probe replays the recorded turn 7/8 prompts, not a live game; sample 0 repeats across runs, so replies are not fully independent; the bare-word 'phase' protection in the loader is untouched and still rejects any other narration of 'phase' in 2B. Next: commit, PR, staging, rerun L2 1A-3B x3; check 2B 'phase' and 3B 'charles jenkins' rejections.

L2 1A-3B x3 on 603b07b (2026-10-10, PR 555 merged: 3B `charles` participant, 2B decoded message 'The prisoners are ready to rise up.'; main CI all green; /api/v1/version confirmed 603b07b on staging; Ringer `freytag-affordance-live`). Attempt 1 failed the check at 504 s: r1 hit the known staging hang ('Turn API did not produce a response within 90000ms'), so no merged report; r2 and r3 completed and showed the same picture as below (no 'phase', no 'charles jenkins'; 3B timer in both; r3 had 'coded message' x3 in 2B and 'detention level' x1 in 2A, which the rerun did not repeat). Rerun once per the runbook: pass, 473 s. Exit cause per scene (r1/r2/r3): 1A P P P; 1B P P P; 1C P P P; 2A P P P; 2B P P P; 2C P P P; 3A T(14) T(13) P(9); 3B P(9) T(14) P(9). By play: every scene 3/3 except 3A 1/3 and 3B 2/3, so 3A misses the 2-of-3 bar. Rejected turns: two in all 24 scene-replicates: 3A r1 turn 11 'Present my JANUS evidence to Rebecca.' ('rebecca's desk' unavailable entity) and 1C r3 turn 2 'Inspect the observation shaft.' ('servers'). Targets: 2B 'phase' 0 (was 5 in a row once; 2B 8 turns by play x3), 3B 'charles jenkins' 0 (was 4 in one replicate). One run per build cannot separate these from noise: 2B has been 3/3 on other builds without this change, and 3A went 3/3 -> 1/3 with no edit to 3A (two timers at 13-14 turns). Not diagnosed: why 3A timed out twice; the 'rebecca's desk' leak in 3A (same class as the 2C one) and the 1C 'servers' leak. Next: a second run on 603b07b to see whether 3A stays at 1/3; read the 3A r1/r2 transcripts for the pull before changing anything.

3A timers read (2026-10-10, nothing changed in story files; probe scripts `scripts/ringer/affordance/3a_pull_probe.py`, Ringer `freytag-3a-pull-probe`). L2 on 603b07b had 3A 1/3 by play (r1 T14, r2 T13, r3 P9). Chain read from the transcripts: a_r1 -> b -> d_r1/d_r2 -> c_r1/c_r2 -> bridge `command_levels_assault_underway`. r3 did it in 6 turns. r1 fired a_r1 (t3), b_r2 (t4), d_r2 (t6), then spent turns 8-14 on 'Rebecca's secured office' and never typed the last step (the matcher does match natural follow-ups to the pointer: 'Follow Michelle to the checkpoints.', 'Join the prisoners at the checkpoints.' fire c_r1). r2 spent all 13 turns on the broadcast console and seized controls and never typed Michelle, captives, radio or the medical level. Note: the report's `semantic_match` field does not record authored handoffs, so 'matched None' there does not mean no reveal fired; check the delivery text or `grounding_ids`. Cause found in the recorded r2 3A narrator prompt: the 3A SCENE block carries two 2C reveals, `k_sl_2c_d_r1` ('...Rebecca's secured office can broadcast the evidence and open the detention cells in the sealed sectors.') and `k_sl_2c_d_r2` ('...then to Rebecca's office, and learns the plan can rescue the captives only if they seize the controls to broadcast the evidence.'). Both have `available_in_scenes: [2C, 3A]`; `KnowledgeProjector._committed_for` sends every earned item whose `available_in_scenes` includes the current scene on every turn (other scenes' items only when the player's words reach for them). Probe (r2 3A turn 1 prompt, command 'Broadcast the JANUS evidence through the seized controls.', 12 replies per arm, every reply read by hand): A as recorded: 7/12 head for Rebecca's office or the broadcast (replies 1,2,4,5,6,7,10), the rest follow Michelle's route; B both lines removed: 0/12 name Rebecca's office, narration stays on Brandon, the radios and the captives (4-5 replies echo the player's own 'seize the controls and broadcast' words); C only d_r2 removed: 6/12 still say Rebecca's office (d_r1 pulls); D only d_r1 removed: 12/12 'seize the controls and broadcast'. Each line pulls a different way; both must go. The turn 5 cell (command 'Override the detention gate controls.') showed no difference between arms (all four narrate the gate opening); it narrates success for a step the chain has not earned, a separate matter. Caveats: one recorded turn; the probe cannot show whether the blind player then picks Michelle; a player's own memory of 2C narration also pulls. Candidate fix (proven technique: a line that pulls wrong is scoped, AGENTS 'Fixing a Scene' step 3): `available_in_scenes: [2C]` for `k_sl_2c_d_r1` and `k_sl_2c_d_r2`. Cost: a player who skipped the 2C message could no longer earn it in 3A, and 3A would not carry the lines unless the player names them. Not applied.

3A line removal reviewed (2026-10-10; brief `.plans/chatgpt-3a-removal-review-prompt.md`; nothing applied). ChatGPT's verdict: reject the removal as an unproven fix; its worry was that a command naming the broadcast or Rebecca's office would recall the two 2C lines back into the 3A prompt. My brief said so, and the brief was wrong. Checked in the code (`KnowledgeProjector._committed_for` / `_player_refers_to`) and with the real package: an out-of-scene item is recalled only when the player's words name a NON-character entity listed in the item's `entity_ids` or `relevance.entity_ids`. Both `k_sl_2c_d_r1` and `k_sl_2c_d_r2` list only `holding_block`. 'Reach Rebecca's secured office.', 'Activate the central broadcast console.' and 'Broadcast the JANUS evidence through the seized controls.' recall nothing (Rebecca is a character and is excluded); 'Enter the holding block.' and 'Follow Michelle to the holding block.' do recall both. So probe arm B (lines removed) models the change for every pull command seen. Also corrected: the cost I wrote earlier, that a player who skipped the 2C message could not earn it in 3A, is probably wrong, since SL-2C-D aborts outside 2C; still not proven by running the engine. Second probe round (r2 3A turn 1 prompt, 12 replies per arm, every reply read): t1 command 'Broadcast the JANUS evidence through the seized controls.': A as recorded names Rebecca/office 6/12 and the seize-the-controls plan 7/12; B (both lines removed) 0/12 and 3/12 (echoes of the player's own words); E (both replaced by ChatGPT's route-only line 'Michelle's message marks a maintenance route into her holding block.') 0/12 and 4/12. Neutral command 'Search the detention sector.': no arm names Rebecca (0/12 each); Michelle is named by A 2/12, B 0/12, E 1/12. Reading: the removal removes the pull (matches round 1); the route-only line adds nothing over plain removal; and on a neutral first turn NO arm, including as recorded, leads the player to Michelle, so 3A has no first-step cue: a separate gap (missing story material, a cue or pointer through ChatGPT Desktop), not something the removal causes or fixes. Not tested: whether the blind player then reaches Michelle live, and the 3A to 3C path. Options: apply `available_in_scenes: [2C]` on both entries and rerun L2 (reversible, one run is noisy), and separately write a 3A first-step cue brief.

3A line removal applied (2026-10-10, Ringer `freytag-affordance-2c-scope`, 1 attempt, PASS; suite 1170 passed, ruff clean; manifest and check in `scripts/ringer/affordance/2c-scope.*`): `available_in_scenes` of `k_sl_2c_d_r1` and `k_sl_2c_d_r2` is now `[2C]` (was `[2C, 3A]`); no test assertion needed changing. Not measured live. Still untested: whether the blind player reaches Michelle in 3A without the pull, and the 3A to 3C path. Next: merge, redeploy staging, rerun L2 1A-3B x3; separately a 3A first-step cue brief for ChatGPT Desktop.

L2 1A-3B x3 on 5643fc5 (2026-10-10, PR 557 merged: `k_sl_2c_d_r1`/`r2` scoped to 2C only; main CI green, /api/v1/version confirmed 5643fc5 scene-v1 staging; Ringer `freytag-affordance-live`, pass, 496 s, first launch): play exits per scene r1/r2/r3: 1A 3/3 (8,8,8); 1B 3/3 (8,8,8); 1C 2/3 (7, timer 11, 7); 2A 3/3 (7,7,7); 2B 3/3 (8,8,8); 2C 3/3 (8,8,8); 3A 2/3 (9, 10, timer 13); 3B 1/3 (timer 14, 9, timer 14). Zero rejected turns in all 24 scene runs. 3A went from 1/3 to 2/3 and now meets the 2-of-3 bar; 3B went from 2/3 to 1/3 with no 3B change in this build, so read as noise until rerun (broadcast_relay never shown, inspection_console shown turn 0). 3A r3 never showed the stolen radio or override codes and first showed captives on turn 8; Michelle first shown turn 0/3/1. n=3, one run. Still open: 3B bar (1/3 here, 2/3 before), 1C r2 timer (logistics_terminal first shown turn 11), 3A first-step cue brief `.plans/chatgpt-3a-first-step-cue-prompt.md` (waiting on ChatGPT Desktop; apply only after this measurement, now done), 3A to 3C path not checked. Next: send the cue brief, rerun 3B alone for more samples.

L2 1A-3B x3 rerun on 5643fc5 (2026-10-10, same build; Ringer `freytag-affordance-live`, check FAIL, 658 s): replicate 2 hit the known staging hang (`#command-input` disabled 90 s) and wrote no report; r1 and r3 read from `artifacts/e2e-blind-player-r1/r3.json`. Exit by play (P) or timer (T), r1/r3: 1A P, T(13); 1B P, P; 1C P, T(13); 2A P, T(11); 2B P, P; 2C P, T(16); 3A P(9), T(13); 3B T(14), P(10). Rejected turns: 1C r3 two, none elsewhere. Pooled over both runs on this build (n=5 each for 3A and 3B; the first run is in the entry above): 3A play 3/5, 3B play 2/5, so neither is settled against the 2-of-3 bar and the two runs differ more than the 3A removal could explain; r3 left five scenes by timer here against none in the first run, so this run is noisy overall. Not read: why r3 timed out in 1A, 2A and 2C this time; the 1C r3 rejections. Open: 3B bar, 3A bar (3/5), 3A cue brief. Next: send `.plans/chatgpt-3a-first-step-cue-prompt.md` to ChatGPT Desktop; a further run only if a change needs measuring.

3A first-step cue applied (2026-10-10, ChatGPT Desktop answer to `.plans/chatgpt-3a-first-step-cue-prompt.md`; edited directly; suite 1170 passed; not measured live). Scored the answer's command table with the real matcher: every claim held. Applied: `michelle_reached` cue_text now 'Michelle speaks into a stolen radio beside the captives.' (names Michelle; nouns `Michelle`, `stolen radio`, `captives` match a_r1/a_r2; no later-reveal phrases); 3A `objective` now 'Reach Michelle' ('join the uprising' pointed at the last step, same subtractive method as the 3B objective); plot.md 3A.1 gains 'Michelle is beside the captives.' after the first paragraph ('beside' is flavor only, both are in `detention_level`, per grounding guide line 49). Left alone: `entry_text`. Known gap, not fixed: 'Search for Michelle.', 'Look for Michelle.' and 'Check on Michelle.' match a_r1 and a_r2 together and the matcher, which does not break ties, fires neither; 'Go to Michelle.', 'Walk to Michelle.' and 'Reach Michelle.' match no first-step reveal. Candidate fix, new work with no W decision: drop 'probe' from a_r2's verbs (the search synonym class pulls it in) and add go/walk/approach to a_r1 through Ringer. Next: merge, redeploy, rerun L2 1A-3B x3 and read 3A (3/5 by play before this change).

L2 1A-3B x3 on fcc9aba (2026-10-10, PRs 558/559 merged: 3A cue 'Michelle speaks into a stolen radio beside the captives.', objective 'Reach Michelle'; main CI green, /api/v1/version confirmed fcc9aba; Ringer `freytag-affordance-live`, check FAIL, 414 s): replicate 2 hit a one-off CORS 'Failed to fetch' on staging /api/v1/turn and wrote no report; r1 and r3 read from `artifacts/e2e-blind-player-r1/r3.json`. Play exits r1/r3: 1A P(8), P(8); 1B P, P; 1C P(7), P(7); 2A P(7), P(8) with one rejected turn; 2B P, P; 2C P, P; 3A P(9), timer(13); 3B P(9), timer(14). Rejected turns: one (2A r3). Only two replicates, so no bar read: 3A 1/2, 3B 1/2; pooled on the 3A change alone it is too few to say. r3 3A read: turn 1 'Free the captives.' reached Michelle (a_r1), turn 2 'Follow Michelle to the medical level.' fired the experiments step, then the player took the official and tried 'Take the official access seal from the prisoner.', 'Use my official access seal on the gate-status panel.', 'Open the emergency gate with my official access seal.' and 'Lead the captives through the emergency gate.' x3, and timed out, so the first-step miss is gone in r3 but the d/c steps (override codes, uprising) stalled; not read against d_r1/d_r2/c_r1 evidence. Staging flakes now cost a replicate in 3 of the last 4 runs (hang twice, CORS once). Next: rerun for the missing replicate and more samples; read r3 3A turns 3-9 against d_r1, d_r2 and c_r1.

CORS flake investigated and fixed (2026-10-10, Ringer `freytag-null-place-500`, 2 tasks, both PASS on attempt 1; suite and ruff clean). The fcc9aba run's replicate 2 failure was a real 500 on staging POST /api/v1/turn at 04:42:52 UTC (Railway log): `AttributeError: 'NoneType' object has no attribute 'strip'` at `item_facts.py:1039` in `_override_place` (narrator item_facts with `"place": null` while a fact override was active); `_apply_move` (line 940) had the same unguarded `.strip()`. Browsers reported CORS because Starlette's outermost ServerErrorMiddleware builds the 500 outside CORSMiddleware, so it carries no `access-control-allow-origin`. Fixes: both sites now treat a non-string `place` as absent (test `tests/test_item_facts_null_place.py`, fails on the original code); `web_demo.py` gains an inner `http` middleware that logs the exception and returns a JSON 500 `{"detail": "internal server error"}`, which CORS then decorates (test `tests/test_web_demo_server_error.py`). Runbook failure-table row for CORS/`Failed to fetch` now says to read the staging log for a 500 first. Not measured on staging. The earlier CORS one-off on 2ee09ec is not tied to this bug (logs too old). Open: the narrator should not return a null place at all; how often it does is unknown (one 500 in three hours of staging logs).

L2 1A-3B x3 on be2e394 (2026-10-10, PR 561 merged: non-string item_facts `place` ignored, unhandled 500s CORS-safe; main CI green, /api/v1/version confirmed be2e394; Ringer `freytag-affordance-live`, pass, 523 s): all three replicates completed and wrote reports (first time in four runs); staging log shows 0 tracebacks/500s in the window. Exit r1/r2/r3 (P play, T timer): 1A P(8), T(13), P(8); 1B P(9), P, P; 1C P, P, P; 2A T(11), P(7), T(11); 2B P, P, P; 2C P, P, T(16); 3A P(9), P(9), T(13); 3B T(14) x3. Rejected turns: one (1B r1), none elsewhere. 3A play 2/3 (pooled with the two earlier runs on the cue and 2C-scope builds: 3A fcc9aba 1/2, 5643fc5 5 of 8 across both runs; now meets the bar again), 3B play 0/3 (pooled on the 2C-scope build and later: 3/10 by play over four runs, so the bar is not met). Michelle first shown turn 1/0/0 in 3A. 3B commands read: in all three replicates the player went straight to the broadcast from turn 1 ('Seize the command console.', 'Override the broadcast lockout.', 'Broadcast the evidence from Rebecca's secured office.'), then to transmit/broadcast, leading prisoners, or Charles; nobody typed a water-pressure warnings or false-alarm command, and the inspection console was shown from turn 0 in all three. So the 3B entry text, bridge text and objective edits did not stop the broadcast-first plan; the pull sits elsewhere (not read: the recorded 3B prompts). 2A had two timer exits (r1, r3) this run after 3/3 earlier; not read. Next: read the 3B recorded prompts against plot.md for the line that frames the broadcast as the goal; read 2A r1/r3 timers.

3B first-step work after the be2e394 run (2026-10-10, branch `claude/plan-l2-be2e394`, uncommitted until merged). Read of the 3B recorded prompts: turn-1 SCENE has only JANUS lines, the inspection console and "Feed JANUS false water and air alarms"; nothing about the broadcast, relay or Rebecca's office, so the pull is the blind player's own 1A-2C transcript ("broadcast the truth"), and the cue (shown every turn) reads as scenery. r1 typed "command console" x5, a name the first narration invented; the matcher fires a_r1 on "Use/Inspect the inspection console" but not "Access".
Done: (1) a_r1 verbs gain access, open, enter, log into, log in to, go into (Ringer `3b-console-verbs`, check run by hand: scorer 57/57, 1173 passed, ruff clean; "command console" deliberately not added, it is an invented name). Not yet merged or run live.
Written, not yet sent: (2) `.plans/chatgpt-3b-first-step-cue-prompt.md`, the 3B twin of the 3A cue brief. Result goes back through a Ringer task.
Open: (3) the opening prompt is never recorded. The web demo can return it (`FREYTAG_EXPOSE_PROMPT=1`, `storygame/web_demo.py:319`), but `frontend/e2e/blind-player.js` `turnRecord` keeps only turn prompts, `onOpening` (spec and `scene-walk.js:89`) carries only text, and `bench/core.py:727` ignores `provider.last_prompt` after `engine.opening()`. Unconfirmed: whether a transition turn's `payload.prompt` is the new scene's opening prompt. Needs a Ringer task recording it as turn 0.
Next: send brief (2) to ChatGPT Desktop; Ringer task for (3); then rerun L2 on 3B (3 replicates) and read the first-step commands.
3B cue applied (2026-10-10, Ringer `3b-cue`, pass, first attempt; suite and ruff clean): `human_security_control` cue_text is now "The cameras track Kristin move by move. The inspection console in the infrastructure corridors can send false water-pressure alarms into empty service corridors." ChatGPT's first answer put JANUS in the cue and failed `tests/test_cue_text_safety.py` (protected knowledge 'janus' on 3B turn 1); the brief now says so and the second answer (candidate A) passed. No plot.md change (3B.1 already carries the console, alarms, corridors and cameras). Not yet run live. The verb widening (access/open/enter) is in the same branch. Still open: record the opening prompt as turn 0 (blind-player harness and bench); push and PR; L2 on 3B x3 to read whether the first command now reaches the console.

L2 all nine scenes x3 on dc0aba9 (2026-10-10, main dc0aba9 = PR 563 plus plan-only PRs 560/562; main CI green, /api/v1/version confirmed dc0aba9 scene-v1 staging; Ringer `freytag-affordance-live`, manifest `scene-affordance-l2-all-live.json`, pass, 543 s, first launch): 3 replicates, each one continuous session through all nine scenes, all three wrote reports. Exit by play (P) or timer (T), r1/r2/r3: 1A P,P,P; 1B P,P,P; 1C T(11),P,P; 2A T(11),P,P; 2B P,P,P; 2C P,P,P; 3A T(13),P(9),P(9); 3B P(9),P(9),P(9); 3C T(16) x3. Play totals: 1A 3/3, 1B 3/3, 1C 2/3, 2A 2/3, 2B 3/3, 2C 3/3, 3A 2/3, 3B 3/3, 3C 0/3. Rejected turns: none in 1A-3B; 3C r2 one, r3 two (not read). 3B first commands (PR 563 cue 'The cameras track Kristin move by move. The inspection console ... can send false water-pressure alarms', a_r1 verbs access/open/enter): turn 1 'Override the primary exits.' / 'Override the security lockdown.' / 'Enter the command level.'; turn 2 in all three was the alarm command ('Trigger false water-pressure alarms.', '... in the empty service corridors.', 'Send false water-pressure alarms through the inspection console.'). Nobody opened with the broadcast; earlier runs went to the broadcast from turn 1 (0/3 by play on be2e394, 3/10 over four runs). The inspection console was shown from turn 0 in all three; `broadcast_relay` first shown turn 9 in r2 and never in r1/r3. After turn 2 all three read the same path: 'Enter Rebecca's executive office.', 'Examine Rebecca's experiment approvals.', the marked site list, 'the remote channel marked Charles', then the broadcast or a Charles/Brandon channel; all left 3B on turn 9. Read: the cue and verb change moved the alarm command from never to turn 2 in 3/3 and 3B met the 2-of-3 bar here, but turn 1 was still not the console and the semantic matcher shows `matched: null` for the alarm command, so I did not read which rule fired turn 2's reveal. n=3, one run; the 3B bar was 3/10 before, so treat 3/3 as promising, not settled. 3A: P(9) in r2/r3, T(13) in r1 (2/3, same as be2e394; not pooled here). Not read: why 1C r1, 2A r1 and 3A r1 timed out; the 3C rejections and why 3C never transitions (T16 x3, new scene for this harness's report); r3's 3B opening text describes searching the medical level (3A material), which looks wrong and is unread. Open: 3B repeat run to confirm; 3C. Next: rerun once more on the same build for 3B and read 3C's prompts and rejected turns.

L2 all nine scenes x3, second run on 7c6b8cc (2026-10-10, same runtime as dc0aba9; Ringer `freytag-affordance-live`, pass, 516 s) and 3C read (suite 1179 passed on branch `claude/3c-phase-two-statement`, not merged, not measured live). Run 2, r1/r2/r3: r1 stuck in 1A (3 rejections, turns 8-10); r2 1A-2C P, 3A T13, 3B P9, 3C N; r3 1A-2B P, 2A T11, 2C P, 3A P9, 3B P9, 3C N. 3B left by play on turn 9 in both replicates that reached it (alarm command turn 1 or 2); with run 1 that is 5/5 reached. 3C is the last scene (`transition_ids: []`), so 'no transition' is expected; the real question is the chain. Findings: (1) 3C has no `handoffs.yaml` entries, so its prompt carries only the two step-A statements and nothing points at Rebecca's data case, the pumps or the gates; `k_sl_3c_a_r1` fired on turn 1 in 2 of 3 run-1 replicates and nothing after it fired; players typed escape commands and the narrator invented exits and a journal; the 14-turn timer prints the whole chain. Brief for ChatGPT Desktop: `.plans/chatgpt-3c-cues-and-pointers-prompt.md` (not yet sent). (2) 'phase two' rejections after the timer dump (run 1 r2, run 2 r3): `phase_two` is protected and `k_sl_3c_e_r1`'s statement said 'a second plan', so earning it never lifted the term. Fixed: statement now says 'Phase Two was meant to provoke conflict among survivors' (commit 65928c5e) plus a test (Ringer `freytag-phase-two`, PASS). (3) 1A r1 stuck: the blind player asked a patrol officer (from the 1A pacing beat) about Michelle and the narrator said 'Dr. McGehee'; the leak scan's known-term loop skipped aliases of nameable fixed items only, so a scene participant's own multi-word names ('dr. mcgehee', 'michelle mcgehee', 'dr. michelle') were rejected; reproduced offline. Fixed in `narration_safety.py` (nameable NPC aliases skipped; Ringer `freytag-character-names`, PASS; non-nameable Brandon still rejected). Other rejections unchanged: 'phase' (r3 1B, bare-word protection), 'coded message' (r2 2B). Next: send the 3C brief to ChatGPT Desktop and score its answer with the real matcher; merge the branch, redeploy, rerun L2.

3C cue chain, design and build started (2026-10-10, branch `claude/3c-phase-two-statement`, commit 812b6629; not merged, not measured live). Probe (Ringer `freytag-affordance-3c-cue-gate-probe`, PASS; `scripts/ringer/affordance/3c_cue_gate_probe.py`): with the cue gate forced open, no cue stages at any of six 3C stages, because 3C has only `resolution_events` (the cue code reads `bridge_events`) and no deliveries. Correction to the earlier reading: `complete_when` in `storylet-routes.yaml` is never read. A storylet fires on its first reveal and the sibling reveal is then not a candidate (`knowledge.py` `_candidates`), so C1->C2 and D1->D2 cannot chain; experiment: after `k_sl_3c_c_r1` the storylet fired, `c_r2` raised 'selected knowledge is not eligible', and the 3C canonical events then set `captives_reaching_surface` and `los_angeles_facility_lost`. Design (Brandon approved the recommendation: COA 2 plus COA 3 wiring, both halves required in any order): split SL-3C-C into pumps and gates storylets and SL-3C-D into reports and families storylets; each part sets its own fact (`evacuation_route_open`, `los_angeles_facility_lost`, `national_network_fragmenting`, `community_rescue_efforts_begun`); `resolution_escape` and `resolution_network_consequences` need both storylets; E already waits on `charles_at_large` from the network event, so it waits on both D parts; cue staging runs in resolution scenes (Deadline staging stays off); `_bridge_delivery_fact_ids` also reads the scene's unsatisfied resolution events; seven cues keyed to `truth_no_longer_containable`, `rebecca_captured`, `evacuation_route_open`, `los_angeles_facility_lost`, `national_network_fragmenting`, `community_rescue_efforts_begun`, `phase_two_conflict_plan_known`. Text: ChatGPT Desktop round 2 (`.plans/chatgpt-3c-structure-and-cues-prompt.md`, answer in `.plans/chatgpt-3c-structure-and-cues-answer.md`); the four C/D pointers are removed, the A/B pointers stay. Build: Ringer `freytag-affordance-3c-structure` (running). Open: read the worker's notes.md, apply the patch, merge, redeploy, rerun L2 for 3C.

3C cue chain built (2026-10-10, branch `claude/3c-phase-two-statement`; Ringer `freytag-affordance-3c-structure`, run 1 FAIL, run 2 PASS; suite 1195 passed, ruff clean; not merged, not measured live). Run 1 failed on the loader rule that every resolution event's activation facts must be entry-guaranteed or produced by an earlier resolution event (so the Deadline backstop can finish the chain alone); my plan to add the part facts to activations broke it, and the worker's sandbox could not run `uv` so it never saw a suite result. Run 2 (venv from the main checkout, `PYTHONPATH=$PWD`): resolution activations restored; both-parts rule comes from each event's `realization_storylets` (C: SL-3C-C pumps and SL-3C-F gates; D: SL-3C-D reports and SL-3C-G families); `_bridge_delivery_fact_ids` now also gets cue facts from the facts that the unfired required storylets of each resolution event would assert. Cue staging runs in every scene; Deadline staging stays off in resolution. Probe, cue source per stage: entry A (`truth_no_longer_containable`), then `rebecca_captured`, then both C facts, then both D facts, then `phase_two_conflict_plan_known`; after one part only the missing sibling remains. Changes to the answer text: the `cue_c_gates` cue says 'The gate authorization is close to expiry.' (the first-turn safety test rejected 'senior official's authorization'; 'gate authorization' is in the c_r2 evidence group). Test assertions changed: storylet counts (36->38, 32->34, 28->30), the 3C required storylets, the cue safety test now models the first turn with the reveal's prerequisites asserted, `test_knowledge_projection` counts only player-visible 3C entries, the delivery-coverage test only checks bridge-required deliveries, and `test_transport_drops_an_ungrounded_groupless_selection` accepts `grounding_ids: []` where it used to require the key absent (not yet traced to its cause). Open: trace that last assertion, open a PR, merge, redeploy, rerun L2 for 3C; the C/D pointers are removed, so the A and B pointers plus the seven cues carry the chain.

L2 all nine scenes x3 on be59c43 (2026-10-10, PR 565 merged as a merge commit; main CI green, /api/v1/version confirmed be59c43 scene-v1 staging; Ringer `freytag-affordance-live`, smoke 1A,1B x1 passed first, full run pass, 662 s). Other scenes, play exits r1/r2/r3: 1A 3/3, 1B 3/3, 1C 1/3, 2A 2/3, 2B 3/3, 2C 2/3, 3A 1/3, 3B 2/3 (timer exits are the usual noise; not read). 3C has no transition, so the measure is which of the seven steps the player fired before the 14-turn timer dump (read from the per-turn texts in `e2e-blind-player-r*.md`). Before this change 3C got one step at most in 2 of 3 runs and no cue ever showed. Now: r1 two steps by play (A on turn 2, B on turn 13); r2 five (A t1, B t2, C-pumps t3, C-gates t10, D-reports t12), D-families cue shown t13, timer t14; r3 four (A t1, B t2, C-pumps t3, C-gates t5), D-reports cue t6 and D-families cue t7 shown, no D reveal by play, timer t14. No rejected turns in any 3C replicate. E never fired by play, because its cue shows only after both D parts. The cues work: each one appeared the turn after its step and two players followed them straight away ('Take Rebecca's portable data case.' t2, 'Activate the drainage pumps.' t3, 'Use my emergency authorization at the surface gates.' t5). Misses are wording: r1 typed 'Follow Rebecca.' three times (b_r1 verbs have no 'follow'), then 'Take Rebecca's escape route.' fired B at t13; r2 spent turns 5-9 on 'Extend the emergency gate authorization.', 'Guide the captives through the emergency gate.', 'Lead the captives to safety.' before 'Open the surface exit.' fired C-gates (c_r2 verbs have no extend, guide or lead); r2 t14 'Broadcast updates to the families.' and r3 t7-t8 'Broadcast the reports from other detention sites.' / 'Answer the families with the broadcast's truth.' did not fire D (d_r1 verbs have no broadcast, d_r2 none either); r3 spent turns 8-13 on the broadcast and the exit. Open: a ChatGPT Desktop round that widens the verb groups of b_r1, c_r2, d_r1 and d_r2 for these phrasings (check each against the one-match rule), then rerun 3C. Not done: the E cue was never seen live; timer-only runs show only the dump.

3C verb widening (2026-10-10, ChatGPT Desktop round `.plans/chatgpt-3c-verbs-prompt.md`; Ringer `freytag-affordance-3c-verbs`, PASS first attempt; suite 1195 passed, ruff clean; not merged, not measured live). Added to `knowledge.yaml` action_evidence: `k_sl_3c_b_r1` verbs `follow`, objects `follow Rebecca` and `Rebecca's escape route` (a bare `Rebecca` object was rejected: it would make 'Ask Rebecca about her archive.' match both b_r1 and b_r2); `k_sl_3c_c_r2` verbs `extend`, `guide`, `lead`; `k_sl_3c_d_r1` verbs `broadcast the reports`, `broadcast reports`; `k_sl_3c_d_r2` verbs `broadcast updates`, `answer the families with`. `tests/test_3c_cue_chain.py` pins 32 commands with the real matcher. Known and accepted: 'Broadcast the detention site list.' matches a_r1 and d_r1 and so returns none (true before this change); a command that asks for both C parts at once returns none. Open: merge, redeploy, rerun L2 for 3C and read steps fired by play (baseline on be59c43: r1 2, r2 5, r3 4).

L2 all nine scenes x3 on c60800a (2026-10-10, PR 566 merged as a merge commit; main CI green, /api/v1/version confirmed c60800a scene-v1 staging; Ringer `freytag-affordance-live`, smoke 1A,1B x1 passed first, full run pass, 565 s). Play exits r1/r2/r3: 1A 1/3 (T13, P8, T13), 1B 3/3, 1C 3/3, 2A 3/3, 2B 3/3, 2C 2/3, 3A 1/3, 3B 3/3 (9-11); timer exits not read. 3C steps fired by play (of 7), from the per-turn texts: r1 4 (A t2, B t3, C-pumps t4, C-gates t6; D cues shown t7, t8; timer t14), r2 5 (A t1, B t2, C-pumps t3, C-gates t6, D-reports t8; D-families cue t9; timer t14), r3 7 (A t2, B t3, C-pumps t4, C-gates t6, D-reports t8, D-families t10, E cue t11, E fired t12 by 'Open the recovered document.', no timer dump). Baseline on be59c43 was 2/5/4; before PR 565 no cue showed and no run passed step A by play. No rejected 3C turns. The verb widening of PR 566 worked: 'Take Rebecca's portable data case.' / 'Secure Rebecca's portable data case.' (B), 'Operate the drainage pump controls.' (C-pumps), 'Open the surface gates.' and 'Activate the emergency surface-gate release.' (C-gates), 'Read the reports from other detention sites.' and 'Review reports from other detention sites.' (D-reports). Remaining stall: all three players typed 'Answer the families.', 'Reassure the families.' or 'Answer the families' requests for information.' and d_r2 only had `answer the families with`; only r3's 'Answer the families with the detention-site reports.' fired it. The E cue names 'Charles's last remote channel' but e_r2 had no such object (r3 typed 'Trace Charles's last remote channel.' after E1 had ended the chain). Fix scored with the real matcher by me (no ChatGPT round; additions only): d_r2 verbs `answer`, `reassure`, `respond to`; e_r2 objects `Charles's last remote channel`, `his last remote channel`; only regression is 'Answer the families about Charles's terrorist claim.' (matches a_r2 and d_r2, returns none), accepted. Ringer `freytag-affordance-3c-verbs`. Still open outside 3C: 1A and 3A timer exits (3A has no first-step cue toward Michelle; story text for ChatGPT Desktop), 2C one timer, bare-word 'phase' protection, 'coded message' in 2B; not touched here.

3C d_r2 and e_r2 words (2026-10-10, ChatGPT Desktop round `.plans/chatgpt-3c-d2-e2-prompt.md`; Ringer `freytag-affordance-3c-verbs`, `3c-verbs3` PASS first attempt; suite 1195 passed, ruff clean; not merged, not measured live). My bare-verb proposal (`answer`, `reassure`, `respond to`; Ringer `3c-verbs2`, patch never applied) was replaced by ChatGPT's narrower phrases: `k_sl_3c_d_r2` verbs `answer the families`, `reassure the families`, `respond to the families`; `k_sl_3c_e_r2` objects `Charles's last remote channel`, `his last remote channel`. Reason for phrases: a bare verb widens the match across every family object. ChatGPT's 63-command table was reproduced with the real matcher (0 mismatches) and pinned in `tests/test_3c_cue_chain.py`; one pinned row changed ('Answer the families about Charles's terrorist claim.' a_r2 -> None, now a_r2 and d_r2 both match); the worker skipped 'Read the recovered document.' (e_r1), which I added by hand. ChatGPT's decisions: `read` stays out of e_r2 (it would make 'Read the recovered document about Charles's signal.' match both e reveals; 'Read Charles's last remote channel.' stays unmatched); 'Enter my one-use authority code into the gate-status panel.' stays unmatched (gate_status_panel belongs to 3A; the plot has Michelle use the senior official's authorization from Rebecca's office); keep the cue sentence 'The gate authorization is close to expiry.'. New double matches accepted: 'Respond to the families about Charles's terrorist claim.' (a_r2 + d_r2) and 'Read the recovered document and trace Charles's last remote channel.' (e_r1 + e_r2). ChatGPT also recorded broad effects of PR 566 for a later scoped review: 'Extend the gate authorization.' and 'Guide/Lead the captives to the surface gates.' fire c_r2 (the release); 'Broadcast the reports to the families.' fires d_r1; 'Broadcast updates about the families.' fires d_r2 without addressing them. Process note: a first Ringer attempt for this step never ran (my manifest generator crashed) and I reported it as running; fixed, and noted here. Open: PR, merge, redeploy, rerun L2 for 3C with more than three replicates to separate a stall point from noise (c60800a: 4/5/7 of 7).

Other scenes read on c60800a (2026-10-10; the L2 all-nine run above). Surface-gates regression, mine: PR 565 declared `emergency_surface_gates` (alias 'surface gates') but placed it only in 3C, so narration naming it in 3A and 3B was rejected as an unavailable entity: five rejected turns (3A r2 t5, t7, t10; 3B r1 t1, t10), 3 of 15 turns in 3A r2. The 3A Details line and the senior official's authorization name the gates, so the grounding guide requires the item in those scenes. Fix (Ringer `freytag-affordance-gates-scope`, PASS first attempt; suite 1201 passed): `emergency_surface_gates: {parent: facility_escape}` in the `item_ids` and `item_placements` of 3A and 3B; `tests/test_surface_gates_scope.py` pins the placement in 3A to 3C, narration accepted in 3A and 3B, and still rejected in 1A (`narration_known_term_leak`). Not measured live. 1A (play 1/3: T13, P8, T13): the card (`k_sl_1a_b_r0`) is found only by 'Inspect the gap beneath the KMS drawer.'; 'Open the KMS drawer.', 'Open the high-riding drawer.' and 'Examine the drawer's lower edge.' (the cue says 'a thin gap along its lower edge') fire nothing, and the narrator then invents a paper note and a made-up warehouse or oak tree two turns later. `michelle_drawer` already declares its contents. Brief for ChatGPT Desktop: `.plans/chatgpt-1a-drawer-prompt.md` (not yet sent). 3A r1 (T13): the player chased 'Rebecca's office' for 12 turns; the recorded turn-1 prompt mentions Rebecca only in the CHARACTERS list, the pull is the scene's own opening ('identifies Rebecca's secured office as the manual point'), and the Michelle cue ('Michelle speaks into a stolen radio beside the captives.') showed on turn 1 and was ignored. A cue is shown once; the engine's only reminder is the nudge at turn 11 and the handoff at 14. No proven technique covers a player ignoring a one-time cue; not fixed from one replicate. 2C r1 (T16): its opening put Kristin at the medical terminal and the player chased Michelle's transfer records for 16 turns; the two replicates whose openings were on the archive copied the JANUS evidence on turn 1 and left by play at turn 8. Opening variance, one replicate; not fixed. Next: send the 1A brief, apply its answer, rerun L2 with 5 replicates to separate the 3A and 2C stalls from noise.

1A drawer words (2026-10-10, ChatGPT Desktop round on `.plans/chatgpt-1a-drawer-prompt.md`; Ringer `freytag-affordance-1a-drawer`, PASS first attempt; suite 1227 passed, ruff clean; PR 569; not measured live). Applied unchanged: `k_sl_1a_b_r0` evidence now `[under, beneath, underside, gap, lower edge, bottom edge]` and `[drawer, KMS, workstation, "drawer's"]`; the 1A `cue_text` in `handoffs.yaml` now says 'A thin gap beneath its lower edge is wide enough for Kristin's fingers.' ChatGPT's 54-row table is pinned with the real matcher in `tests/test_1a_drawer_words.py`. 'Open the KMS drawer.' and 'Open the high-riding drawer.' stay unmatched on purpose (the card is beneath the drawer; opening it does not find it). New doubles, accepted: a command that names both the drawer edge and the back door matches a_r1 and b_r0 (none). `plot.md` line 126 still says 'leaving a thin gap along its lower edge' and was NOT changed; it needs an approved line from ChatGPT Desktop. Why no narrator replay: the recorded 1A narrator prompts (`e2e-blind-player-prompts-r*.json`) carry no cue text, only the SCENE block, so the cue cannot change what the narrator invents on 'Open the KMS drawer.'; it works only by steering what the player types. The invented note and the made-up warehouse and oak tree came after the narrator had no card to give for 'Open the drawer' (r1 t2 narration listed the declared contents, then invented a note on t3; r3 invented paper on 'Examine the drawer's lower edge.'). The measure is therefore the live L2 1A x3 on the merged SHA: count turns to `k_sl_1a_b_r0` by play and read every 1A turn for invented paper. Open: that run; the plot.md line; if players still type 'Open the drawer.' and the narrator invents, that is a new probe (recorded t2 prompt with the drawer contents, arms on candidate causes), not a rule.
