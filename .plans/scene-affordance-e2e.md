# Scene affordance E2E tests: plan

Latest (2026-10-08, main 11aaf97): opening retry merged (PR 524); L2 1A-2A x3 shows 1A, 1B play x3, 1C play 2/3, 2A timer/timer/none; see 'L2 1A-2A x3 on 11aaf97'. Next: 2A 'the supervisor' leak.

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
