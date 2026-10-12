# Playthrough quality before human players: plan

Status (2026-10-12): not started. Branch `qc-playthrough` off main `bd69bc82`. Goal (Brandon): a complete, good playthrough 1A to 3C before human players use the game. Production promotion is out of scope. Staging is the test target. Every code or data change runs through Ringer; billed runs are smoke-tested first, one Ringer task per run unit; record results here after each phase.

## What is known to be unproven

Taken from `design-review-implementation.md`:

- 3A, 3B, 3C have never been played live in a continuous journey on current main (hosted runs stop at 2C).
- No full 1A-3C hosted journey exists after Steps 4, 5, 7, 8.
- A player who skips the 2C copy step; the 3A medical records item; `medical level` and `medical terminal` outside their scenes.
- `timer` exits and the rare selection outcomes were never observed live.
- All live evidence is model players, three replicates per arm.
- Staging turn cap variable is still 60 (set by hand for Step 9).

## Phases and gates

### Phase 0: baseline (offline, cheap)
- Full suite, coverage gate, ruff check and format on main.
- Confirm staging runs main (`/api/v1/version` sha and Railway deployment list, not GitHub status alone).
- Decide and restore the staging turn cap.
- Gate: all green; staging SHA equals main.

### Phase 1: offline audit of 3A-3C and the whole package
- Reachability: every scene's exit and every reveal reachable by an earned path (existing `reveal_coverage.py`, `sibling_reachability.py`, `scene_gap.py`).
- Disclosure matrix and narration corpus fresh and passing; read the 3A-3C rows by hand.
- Pacing: sum the per-scene turn budgets against the 2-hour target; list every forced handoff and what it costs later.
- Save and load round trip at each scene boundary; scene re-entry.
- Gate: no unreachable reveal, no stale generated file; a written list of 3A-3C risks to probe live.

### Phase 2: live segments 2C to 3C (billed, smoke first)
- Local bench, real narrator, three continuations each for 3A, 3B, 3C from an earned entry state, then linked 2C to 3C.
- Include the player who skips the copy step and the Michelle-first start.
- Read every prose turn at the pointer, reveal and exit; note rejections and their codes.
- Gate: no rejected turn on ordinary words; reveals land; each scene exits; defects listed with evidence.

### Phase 3: fix loop
- One Ringer task per defect, measured before the next fix, using the proven techniques in the scene-fixing guide and grounding guide. Plot or story text goes to ChatGPT Desktop.
- Gate: each fix has a live or bench check showing the failed path now works.

### Phase 4: full journey on staging (billed)
- Hosted blind player, canonical profile, 1A to 3C, three continuous replicates; raw profile, three more.
- Judge runs per the hosted canon judge procedure and the capture accuracy bar (92%).
- Read two complete transcripts end to end for continuity, tone and the ending.
- Gate: at least 2 of 3 per profile reach the end by earned exits, zero rejected turns on ordinary words, no premature secrets, within the pacing budget.

### Phase 5: report
- One short sign-off section here: what passed, what did not, what remains untested (human play always remains).

## Results log

(Append per phase.)

### Phase 0 (2026-10-12)
- Main `bd69bc82`: 1569 tests passed. Ruff check failed on two lint items in `scripts/ringer/design-review-step9/profile_compare.py` (unused loop variable, `zip` without `strict`); fixed by hand, ruff check and format now clean. Coverage percentage not read from this run.
- Staging `/api/v1/version`: sha `bd69bc82...`, runtime `scene-v1`, channel `staging`. Equals main.
- Staging turn cap stays at 60 (needed for the hosted runs below); restore it at the end of Phase 5 by deleting `FREYTAG_RATE_LIMIT_PER_MINUTE` (default 10).

### Journey smoke, 1A to 3C (2026-10-12, staging `bd69bc82`, Ringer `playthrough-journey-smoke`, 1 canonical replicate, 546 s)
- First continuous run through 3A, 3B, 3C on current main. Report: `~/dev/ringer-work/playthrough-journey-smoke/out/e2e-blind-player.json` (the folder also holds stale `-r2`/`-r3` files from earlier runs, ignore them).
- 0 rejected turns in all 9 scenes (118 turns). Every exit 1A to 3B was earned: 1A 8, 1B 8, 1C 7, 2A 10, 2B 8, 2C 8, 3A 13, 3B 9 turns. 3A's exit came on turn 13, the handoff turn itself, and the bundle calls it earned. Sum of exits is well inside the 2-hour budget at about a minute a turn (about 71 turns to 3C).
- 3C: 16 turns, no ending. `k_sl_3c_a_r1` fired turn 2, `k_sl_3c_b_r1` turn 12, `k_sl_3c_c_r1` turn 13, the scene's authored deliveries ran on turn 14, and the Phase Two reveal came from "Examine the recovered JANUS file." on turn 15. Turns 3 to 11 (nine turns) were evacuate/exit commands that matched nothing; the narrator repeated "Kristin looks around the broadcast chamber" in near-identical prose.
- Defects seen in 3C prose: turn 1 says "Michelle, still held captive" although Michelle triggered the uprising in 3B and is Kristin's companion; turn 2 has Kristin hand Michelle "a small package"; the same authored sentence ("Rebecca is leaving the executive office with the Portable data case") appears on three turns.
- Open design question: the engine has no ending. `ending_reachable` in the @spine spec only means the last scene is 3C. Nothing tells a player the story is over, and 3C's handoffs fire at turn 14 with `transitions: []`. Needs a decision from Brandon before a 3C "complete" gate can be written.

### Story ending mechanism (2026-10-12, branch `qc-playthrough`)
- Brandon chose option A: an authored closing beat plus an end marker. Closing text and marker are NOT written yet; the brief for ChatGPT Desktop is `.plans/chatgpt-ending-prompt.md`. The shipped story has no `ending:` block until that comes back, so the game still has no ending in the live package.
- Engine (Ringer `story-ending-engine`, codex, 1 attempt, PASS, 354 s): pacing document gets optional `ending` (`scene_id`, `when`, `text`, `marker`); loader checks scene, facts, no outgoing transition and the text safety scan; `story_complete` on state, snapshot and attempt bundle; the closing paragraph is the last segment of the turn that satisfies `when` (also after a forced handoff); later turns are a provider-free 200 no-op carrying the marker; web turn and session responses expose `story_complete` and `ending_marker`. `tests/test_story_ending.py` added; full suite 1575 passed, ruff clean.
- Frontend and blind-player (Ringer `story-ending-frontend`, 2 attempts): Ringer marked it FAIL only because its check ran without `frontend/node_modules` in the worktree; the patch it exported applies cleanly and `npm test` passes here (92 of 92). Shows the marker as its own entry, disables input at the end, blind-player stops the scene and records `ending_reached` per scene and per run.
- Untested: any live run with an ending; the browser rendering (no Playwright run); a package where `when` is satisfied by a handoff on the final scene in a hosted game.

### Ending text applied (2026-10-12)
- ChatGPT's closing paragraph and marker "The story ends here." are in `pacing.yaml` unchanged in words. My first spec ran the ending text through the narration safety scan, which refused "Phase Two"; Brandon pointed out the ending is closing narrative shown only after the final reveal, so Ringer `story-ending-data` removed that scan (structure checks stay). Ringer marked the task FAIL (its worker also edited `docs/testing-runbook.md`, outside the owned files, and left a transition-graph fixture fix out of the exported patch); I applied the patch minus the runbook edit and fixed `test_loader_rejects_invalid_transition_graph` by hand (extra transitions now go before the trailing `ending:` block). Full suite 1578 passed, ruff clean.
- Untested: the ending firing in a live game; the browser view.

### Weak spots: ChatGPT analysis and fixes built (2026-10-12, branch `qc-weak-spots`)
- Brief: `.plans/chatgpt-weak-spots-prompt.md`. ChatGPT's answer (read-only) recommended: 1C pointer sentence in both A deliveries, scope `photo`/`photograph`, leave the 1A warehouse drift alone until the source of the invented place is found. I scored its command table with the real matcher: every verdict matched. Gap I found: "Read the numbers on the uniforms." and "Check the uniforms for numbers." matched nothing (b_r1 needed 'identification numbers', 'ID numbers' or 'records'), so the new pointer would have invited commands that fail.
- Fix 1, phone (Ringer `weak-spot-photo`): `michelle_photograph` uses `scoped_aliases: [photograph, photo]` instead of `aliases`. Tests: 'a photo'/'a photograph' accepted in a real 1A state, 'Michelle's photograph' still rejected in 1A, 1B resolves both words and both photograph reveals still match, nine-scene sweep accepted. Disclosure matrix moves exactly two rows (entity_name to scoped_alias) and was regenerated.
- Fix 2, 1C (Ringer `weak-spot-1c`): both A deliveries end 'The observation shaft overlooks the processing line. Kristin can read the identification numbers on the uniforms below.'; `k_sl_1c_b_r1`'s third group gains the word `numbers`. Tests pin about 20 commands with the real matcher: 'Read the numbers on the uniforms.', 'Check the uniforms for numbers.', 'Record the numbers on the prisoners' uniforms.' now give exactly b_r1; the quoted route-building commands still give none; the 'check the ID numbers and look for Michelle' tie is documented. Known miss: 'Read the prisoner numbers.' still matches nothing (the object group needs plural prisoners or uniforms).
- Full suite 1587 passed, ruff clean. Not measured live. Plan: baseline = hosted raw-profile 1A,1B,1C x12 on staging `ef75c854` (current), then merge, redeploy, same run x12 on the treatment.

### Weak-spot baseline, hosted raw 1A,1B,1C x12 (2026-10-12, staging `ef75c854`, Ringer `weak1c-baseline-x12`, 4 batches of 3, about 11 minutes)
- 1A 12 of 12 by play, 1B 12 of 12, 1C 10 of 12 by play (2 forced). 0 rejected turns in 36 scene runs, none about photos. In the 10 by-play 1C runs the `b_r1`/`b_r2` reveal landed on turn 3 (7 runs) or 4 (3 runs) after the first reveal.
- So the earlier 1C picture (4 forced of 6 in the full journeys) was a worse draw than the 12-start baseline suggests: pooled raw 1C is 5 forced of 15. The fix has little headroom: at best 2 of 12 move. A 12-start treatment run can show harm (a drop) or an earlier `b_r*` turn; it cannot prove a gain by itself.
- Scorer: `scripts/ringer/playthrough-quality/weak1c_compare.py`.
### Phase 2/4 results: full journey with the ending (2026-10-12, staging `ef75c854`, Ringer `playthrough-ending-smoke|x3|raw-x3`)
- Smoke (first attempt) died because the e2e `submitTurn` waited for the input to be enabled after the final turn, which the page now disables on purpose; fixed in `frontend/e2e/helpers.js` (PR #613). The harness runs from the checkout against the staging API, so the reruns used the branch.
- Smoke rerun, 1 canonical replicate: 9 scenes, 0 rejected, every exit earned, ending fired on 3C turn 14 right after the Phase Two delivery, `ending_reached: true`.
- Canonical x3: 3 of 3 reached the ending; 3C took 14, 12, 12 turns; 1 rejected turn in 81 (1A, 'Examine Michelle's phone.', narration named an unavailable entity 'photo'); forced exits 2 (1A in rep 1 at turn 14: the player wandered to an invented 'old warehouse' and never found the cue-able items; 1C in rep 3 at turn 11). The 3C stall and 'Michelle, still held captive' from the first smoke did not recur ('held captive' once, correctly about the remaining detainees).
- Raw x3: 3 of 3 reached the ending; 0 rejected turns; 250 turns; forced exits 4: 1C in all three (turn 11) and 3A once (turn 13). The raw 1C players earned `k_sl_1c_a_r1` on turn 1 in every replicate (checked with the real matcher), then built long routes (ladders, catwalks, keypads, vents) and never used the transit token or the processing line. The forced handoff carried them on, and every later scene worked.
- Repetition: sentences repeated on 3+ turns of a scene: 3 (canonical) and 6 (raw), mostly stock 1B tunnel lines and 3C authored lines.
- Not done: judge runs (`@llm-canon`, the 92% capture bar), reading a full transcript end to end, human play, 12-paired-scenario statistics. Staging cap is still 60.
- Open, not fixed: 1C after `k_sl_1c_a_r1` for players who write long, route-building commands (4 forced exits in 6 raw/canonical replicates across 1C); the 'photo' rejection on the 1A phone; 1A drift to invented places when the cue is missed.

### Weak-spot treatment and narration-safety false positives (2026-10-12)
- Treatment (staging `49d7126b`, #613 and #614 merged), two runs of the same 12 raw 1A-1C starts: 1C by play 11 of 12 in both (baseline 10), `b_r*` reveal on turn 2-4 (baseline 3-4); 1A 11 and 12 of 12; rejected turns 5 and 1 (baseline 0). The 5 to 1 drop on identical code says most rejections were run-to-run variance. The live Jev fallback was already on (`FREYTAG_SEMANTIC_REVEAL` defaults on; it ran on about 40% of turns, granted 2 reveals, both 1A). `FREYTAG_CONTRACT_SHADOW` only records and only 2C has a contract, so it would not change these runs.
- The 6 rejected narrations all come from the narration safety scan, not from reveal matching. Reproduced locally with the real narrator (wrapper `validate` to print the rejected text): `beneath the drawer` 3 of 3 (narrator echoes the pointer "gap beneath the drawer's lower edge"), `enter the facility` 2 of 2 (narrator repeats the player's words), `forced entry` in the 1A opening, `servers` (a 2A item named with a bare common word), `phase` (the loader protects the first word of every multi-word protected entry, so `phase_two` protected bare "phase").
- Fix (data only, branch `qc-narration-safety`): `leak_terms` on k_sl_1a_b_r0, k_sl_1a_a_r1 and k_bridge_1c_infiltration; `hideout_servers` renamed "hideout servers" with scoped alias `servers`; protected entry `phase_two` renamed `janus_phase_two` (also in storylet-routes). First patch dropped the guard on "the card" (explicit `leak_terms` replace the defaults) and flipped an existing test; a second Ringer task restored it. Suite 1593 passed, ruff clean.
- Local bench replay on the fixed data: drawer command 3 of 3 accepted (was 0 of 3), 1C control-room script 4 of 4 (the `enter the facility` command was rejected 2 of 2 before). The 1A officer script: 2 of 3 completed; one run was rejected on a new term, `damaged recording`, from the scripted command "Recover the damaged recording." (same class: the narrator repeats the player's words). Not fixed yet.

### Narration-safety fix on staging (2026-10-12, staging `2e90fd97`, hosted raw 1A-1C)
- Two runs of the same 12 starts. `safety1`: 1A 11 by play (1 forced), 1B 12, 1C 11 (1 forced), 1 rejected turn (`freight terminal` in 1B, "Ask Brandon where the missing people are being taken."). `safety2`: 12 of 12 by play in all three scenes, 0 rejected turns, `b_r*` reveal on turn 2-4.
- Rejected turns by arm: baseline 0, treatment 5 and 1, after the fix 1 and 0. None of the five fixed causes (`beneath the drawer`, `enter the facility`, `forced entry`, `servers`, `phase`) recurred. Open: `freight terminal` (later-scene place guarded in 1B) and `damaged recording` (local bench only; the narrator repeats the player's words). Both are the same class as the fixed ones.
- `safety1` had a slow 1C tail (`b_r*` on turn 8 and 10 in three runs); `safety2` did not. No claim either way.
- Harness findings, not game defects: (1) the hosted e2e needs more than 20 sessions per IP per day; staging got `FREYTAG_SESSIONS_PER_IP_PER_DAY=500` for the reruns and the variable was deleted afterwards (the running instance keeps 500 until the next deploy). The per-minute cap stays 60. (2) One 1B replicate stalled for 90 s on a game-break panel (`future_dependency_at_risk`, transit card; the narrator invented a locker hall at a transit station). The blind player cannot click Return to scene or Proceed. This was the first game break seen in about 140 replicates; the harness does not record game breaks, so the true rate is unknown.
