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
