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
