# Gate-proving ladder: R1 results

Part of the [gate-proving ladder](gate-proving-ladder.md). Gate numbers refer to the [inventory](gate-inventory.md). Each round records its estimate, actual cost, evidence path and finding.

**Read this when:** you need a measured false-block or miss rate for a gate, or you are deciding which gate to fix or replace first.

## R1a: the two live stuck measures (2026-11-23)

**What was measured.** Gate 18 (the hosted stuck heuristic, `analyseRun`, read by the station 7 live gate) and gate 20 (the probe stuck measure, `summarize_arm`, read by the station 12 keep rule). Both were run unchanged on the 27 frozen outcome-contract examples (`tests/fixtures/outcome_contract/cases.json`, sha256 prefix `b2c8cd3b954fe5ed`). Those examples carry the right answer by construction.

**How.** Ringer run `gate-ladder-r1`, task `r1a-stuck-gates`, Codex (Luna, high effort). It passed on the first attempt: 80,910 tokens, 6 minutes, no model call inside the task, no dollars. Builder: `scripts/ringer/gates-r1/build_r1a_stuck_gates.py`. Evidence (scripts, per-case JSON, report, the worker's notes): `qual-20261122/gates/r1a/`.

The check verified four things:
- all 27 cases are present;
- two defects predicted by hand reproduce;
- gate 20's per-turn flags match an independent recomputation;
- every derived field is consistent.

**One correction to the worker's summary.** Its totals counted three cases whose right answer is "unresolved" (missing telemetry, no continuation offered, pacing window missing) as wrongly blocked. Flagging those is not a false block, so the figures below exclude them.

**The live gate counts every flagged turn.** `live_playtest.py:373-411` takes `len(stuck_turns)` per run and requires 0 in every replicate, so one flagged turn fails the scene. It does not use the three-in-a-row `stuck_runs`.

| | Gate 18 (live gate input) | Gate 20 (probe input) |
|---|---|---|
| Good runs wrongly blocked | **12 of 15** | **12 of 15** |
| Stuck runs wrongly passed | 2 of 6 (`futile_named_object_repeated`, `prior_delivered_knowledge`) | 1 of 6 (`prior_delivered_knowledge`) |
| Stuck runs with a missed turn | 1 (`timed_reveal_masks_futile_action`, turn 2) | 1 (same) |

The only good runs that pass are `exploration_new_description`, `earned_reveal` and `player_ignores_authored_order`: runs where every turn grounds something new.

**Why good runs are blocked.** Both measures count a turn as stuck when it reveals nothing new, whatever else it did. So each of these fails a scene:
- a successful world action ("Open the door.", defect M3);
- a quiet turn below any pacing window;
- the turn before a costed recovery;
- a clarifying question (gate 20 only; gate 18 skips question turns);
- an ordinary turn in a run that ends well.

The fixtures are short. Real scenes run 10 to 13 turns, so a real scene has more chances to contain one such turn, not fewer. The seeded 3B run's earned-exit replicate still had 4 flagged turns.

**Why stuck runs pass.**
- Gate 18 exempts any command that names a shown object, so a futile "Examine the console." repeated four times is never flagged (M2).
- Both gates count a re-grounded, already-delivered reveal as new progress (`prior_delivered_knowledge`).
- Both credit a timed reveal to the futile command that happened to coincide with it (M4).

**Consequence for the ladder.** Today the station 7 live gate cannot be passed by good play, because its stuck input is wrong in both directions. This is a measurement defect, not a story defect. No amount of story repair fixes it, and a factory optimizing against it would learn to make every turn reveal something, which is the flattening the plan forbids.

The fix is already planned: the outcome contract (gate 22) replaces gates 18 and 20 (Step 2 tasks 2.2 to 2.4, after 2.2b telemetry capture). It passes all 27 examples by construction. That makes Step 2's remaining tasks the highest-value work for "can story get through the gates". Until it lands, no live-gate result should be read as evidence about story quality.

## R1b: runtime narration rejections (gate 16) in saved records (2026-11-23)

**How.** Ringer run `gate-ladder-r1`, task `r1b-runtime-rejections`, Codex (Luna, high). The worker's measurement was correct, but both attempts failed on a bug in my check. My independent recount skipped the separate `rejected_turns` list that bench records keep, so it came up 19 short. I fixed the check in the builder (`scripts/ringer/gates-r1/build_r1bc.py`) and ran the corrected check by hand on the worker's kept tree; it passed. Cost: 164,689 tokens over two attempts, no model call inside the task, no dollars. Evidence: `qual-20261122/gates/r1b/`.

**Data covered.** 590 turns: 428 bench turns with in-turn retry telemetry, from 44 distinct source files dated 2026-10-14 to 11-23, plus 162 hosted blind-player turns.

**Results.**

| | Bench | Hosted |
|---|---|---|
| Turns with an in-turn guard rejection | 68 of 428 (15.9%) | not recorded |
| Rejections the retry recovered | 72% | — |
| Player-visible rejected turns | 19 of 428 (4.4%) | 1 of 162 (0.6%) |

**What this does and does not show.**
- **Only one of the 31 codes appears in the retry telemetry:** `narration_known_term_leak`, all 68. Either it is the only guard the bench retry path records, or it dominates. The other 30 codes are unmeasured, not shown to be rare.
- **The bench data are biased toward problems.** Much of it comes from guard-retry and open-issue experiments (`astra-guard-retry-*`, `3a-open-issues-*`), so the 4.4% is not a fair estimate of ordinary play. The hosted 0.6% is closer to ordinary play but too small a sample to estimate from.
- **It matters through the live gate.** The gate fails a scene on one visible rejection in any replicate. At 4.4% per turn, a 12-turn scene has about a 42% chance of at least one; at 0.6%, about 7%.
- **A pattern to adjudicate.** In 3 of the 4 sampled term-leak rejections, the rejected narration repeats words from the player's own command:
  - "coded note" for "Look for Michelle's coded note in the kitchen.";
  - "maintenance access route";
  - "start the uprising at the checkpoints".

  If the guard treats the player's own words as a leak, those are false rejections. Four samples prove nothing, but they say where to look first.
- **Adjudication is possible.** The rejected narration is recorded in `guard_rejections[].rejected_narration`, beside the accepted narration of the same turn.

## R1c: test files that pin the real story (gate 11) (2026-11-23)

**How.** Same run, task `r1c-test-pinning`. It passed on attempt 2: 121,157 tokens, no model call, no dollars. Static parse of all 400 `tests/test_*.py` files against 518 long and 9 short real-story IDs from the compiled package. Evidence: `qual-20261122/gates/r1c/`.

| Class | Files |
|---|---|
| Asserts on a real-story ID (`pins_story`) | **268** (249 of them run on every PR, not nightly) |
| Loads the story but asserts on no story ID | 66 |
| Story-free | 66 |

The most-pinned records are scene IDs (1A appears in about 4,000 pinning places), core entities (`kitchen`, `kristin`, `memory_card`, `kristin_truck`) and 1A storylets.

**How to read it.** This is an upper bound on structure pinning, not a count of tests that block prose:
- A short ID like `1A` matched by equality, or a common ID like `kitchen`, over-counts.
- The tests pin IDs, not authored sentences. Copied prose is down to 3 files and 4 sentences.
- A repair that keeps IDs and changes text or adds records will mostly not trip these asserts.
- A repair that renames, removes or re-gates a record will, and two-thirds of the suite is positioned to catch it.

The real false-block rate of the suite as a story gate needs the dynamic test in R1e: run the suite against meaning-preserving variants of the story and count failures.

## R1e: deterministic gates on good, seeded-fault and variant stories (2026-11-24)

**How.** Ringer run `gate-ladder-r1`, two Codex tasks (Luna, high), builder `scripts/ringer/gates-r1/build_r1e.py`. No model call inside the tasks. Evidence: `qual-20261122/gates/r1e/` (`faults/`, `variants/`).

The first launch swamped the 16-core machine (load 32): pyproject's `-n auto` gives pytest 16 workers, and `carry_matrix()` defaults to a 16-process pool that station 5 never caps. I stopped it and relaunched with fixed shares (10 and 4 cores) that the check measures.

| Task | Result | Tokens | Wall time |
|---|---|---|---|
| `r1e-seeded-faults` | Passed on attempt 2; peak 4.6 cores | 646,043 | 1 h 42 m |
| `r1e-variants-suite` | Failed on my core sampler | 320,496 | 2 h 45 m |

The variants measurement itself completed in 1,040 s.

**Two of my bugs, one of the worker's.**
- *My sampler:* it counted a process only while its working directory was the worktree. Eight test files `chdir` out and back, so a returning pytest worker's whole CPU time landed in one window (false peak of 35 cores). I ran the check's remaining steps by hand on the kept tree; they pass.
- *My check:* it was too weak to catch the worker's bug below.
- *The worker's bug:* `measure.py:339-340` inverts the rerun labels. A test that fails on the variant rerun and passes on the original rerun is a real variant failure, but it was filed under `env_failures`. The figures below are reclassified from the saved JUnit files. The original story fails 0 of 5,096 tests.

### Seeded faults (gates 1 to 10)

- **No false block on the good story.** G passes all nine gates in the battery.
- **Six faults blocked by their intended gate and nothing else:** F1 (layer 1), F2 (layer 2), F5 (gap rules), F6 (carry matrix), F8 (prompt cap) and F10 (unreachable ratchet).
- **Gates 3 and 4 are one gate in practice.** F4 (story/ownership scene-set mismatch) and F9 (a later-scene name in 1A's situation) were stopped at "compile" with code `LOADER::loader`. The load validators run inside compilation, so neither fault reached its own gate. Gate 9's leak tests were therefore never tested alone: the load-time narration term trap catches the same fault first. This is overlap, not a miss.
- **No compile-only fault exists.** The worker found no edit that passes layers 1 and 2 but fails compilation (F3), which makes gate 3 a merge candidate with 4.
- **Slowest gates on G:** carry matrix 51 s at 4 workers, prompt cap tests 37 s, leak tests 12 s.

### Variants (gates 1 to 5 and the full suite, gate 11)

All four rule-built variants are meaning-preserving by compiled diff:
- `layout`: no compiled value changed;
- `contractions`: 82 prose values changed;
- `synonyms`: 106 prose values changed;
- `reorder`: 108 `items`/`participants` positions changed.

Gates 1 to 5 give every variant the same verdict as the original: no layer diagnostics, compile and load succeed, 4 gap results and none new.

The full suite blocks every variant: 34, 34, 39 and 40 failures respectively.

**The same 34 tests fail on all four variants, including `layout`.** They react to any change in the source bytes, not to wording:
- *Entry-snapshot fingerprint (about 20 tests):* `test_entry_snapshot_errors.py` (9), `test_entry_snapshots.py` (5), `test_3c_surface_binding.py` (5) and four 3C/start-scene tests. They fail with "entry snapshot source_fingerprint does not match the loaded package". `storygame/runtime/entry_snapshots.py::write_entry_snapshots` regenerates the snapshots, but nothing in `factory/` or the story CLI calls it. **So every factory story edit fails CI until the snapshots are regenerated.** This is the main false-block source found, and the fix is a process step, not a gate change.
- *Canonical-format checks (10 tests):* `story_source/test_cmd_fmt.py`, `test_cmd_new.py`, `test_cli_set.py` and `test_yamlio.py`. The variant writer did not emit the story CLI's canonical YAML, and an edit made through the story CLI would be formatted. These are artifacts of how the variants were written, not blocks a factory edit would meet.

**True wording and order pins, beyond the 34:**
- `contractions`: 0.
- `synonyms`: 5. These are `test_1a_arrival_glance.py` (2, exact entry text), `test_2b_delivery_repeat.py` (an exact `earn_when` string), `test_richer_3a.py` (exact delivery text) and `test_place_scoped_feed.py` (a byte-identical prompt baseline).
- `reorder`: 6. Three in `test_cloudflare_transport.py` and one in `test_1a_kitchen_start.py` pin the order of possessive item names in a narrator rule ("Michelle's phone, Kristin's laptop"); two more are `test_place_scoped_feed.py` baselines.

So with snapshots regenerated and canonical formatting, a prose rewrite would probably meet about 5 test failures and a list reorder about 6, all in files R1c classed as `pins_story`. That expectation is reasoned from the failure messages, not yet measured.

**Next (small, free).** Remeasure the four variants with `story fmt` and `write_entry_snapshots` applied after each variant, and the label bug fixed, to confirm the 5 and 6. Then decide whether the factory's station 5 regenerates entry snapshots. *Both done in R1e-2 below.*

## R1e-2: station 5 regenerates entry snapshots; variants remeasured (2026-11-24)

**How.** The owner decided that station 5 regenerates entry snapshots. Ringer run `gate-ladder-r1`, two Codex tasks (Luna, high), builder `scripts/ringer/gates-r1/build_r1e2.py`, with 4 and 10 core shares measured by the check. Both passed on the first attempt. Evidence: `qual-20261122/gates/r1e2/` (`station5/`, `variants/`).

| Task | Result | Tokens | Wall time |
|---|---|---|---|
| `r1e2-station5-snapshots` | Passed, attempt 1 | 101,873 | 7 m |
| `r1e2-variants-remeasure` | Passed, attempt 1 | 151,029 | 55 m |

**Station 5 change** (`factory/stations/free_gates.py`, patch applied to the working tree, not yet committed):
- After the source checks and before the gap rules, station 5 calls `write_entry_snapshots` when the ticket has its own tree and the story lies inside it. It then calls `check_entry_snapshots`, and any problem fails the station with check `entry_snapshots`.
- With no ticket tree it never writes, so stale snapshots fail the station.
- Payload `entry_snapshots: false` skips the step.
- Deliver commits the regenerated files with the repair, because it stages the whole tree diff.
- Four new tests in `tests/test_factory_stations.py`. The check also ran an independent probe of the same four behaviours.

**Variants, with canonical format and fresh snapshots after each one.** The original control was already canonical: fmt changed nothing and regeneration changed no snapshot byte. Each variant had 19 files reformatted and none refused, and no snapshot problems remained after regeneration. Gates 1 to 6 give every variant the original's verdict.

| Variant | R1e failing tests | R1e-2 failing tests | Real (rerun-confirmed) |
|---|---:|---:|---:|
| layout | 34 | 0 | 0 |
| contractions | 34 | 0 | 0 |
| synonyms | 39 | 5 | 5 |
| reorder | 40 | 6 | 6 |

No flaky and no environment failures. The labels now follow the rerun results, and the check verified this along with the JUnit counts.

**The 5 and 6 are confirmed, and they are the same tests R1e named.**
- *Synonyms (`pins_authored_text`):* `test_1a_arrival_glance.py` (2), `test_2b_delivery_repeat.py`, `test_richer_3a.py` and the 1B opening baseline in `test_place_scoped_feed.py`. These are tests written to freeze a particular authored text after a fix.
- *Reorder (`pins_order`):* all six trace to one surface. The narrator's possessive rule lists owned items in the scene's item order ("Michelle's phone, Kristin's laptop"), so reversing `items` changes the prompt text. Three `test_cloudflare_transport.py` tests, `test_1a_kitchen_start.py` and two `test_place_scoped_feed.py` baselines catch it. The world is unchanged but the prompt is not. That makes this a real prompt change the baselines are meant to see, rather than a pure false block.

**What this means for the factory.** With station 5 regenerating snapshots and edits saved in canonical format, formatting and contraction-level rewrites pass the whole suite. A repair that rewrites the prose a freeze test was written to protect meets 1 to 5 failures. Those tests sit in files R1c classed `pins_story`, and the repair's test-update allowance has to cover them. Reordering scene items changes the narrator prompt and meets the 6 baseline tests.

**Follow-up the same day: the story CLI is the only edit path** (owner's decision; Ringer run `story-tool-only-edits`, builders `scripts/ringer/story-tool/`; branch `story-tool-only-edits`, 3 commits, not yet pushed). Enforced on the result, since no check can see who typed an edit:
- Station 5 applies the CLI's canonical format (`cmd_fmt.format_source_tree`) in the ticket tree before regenerating snapshots. It fails on a file whose reformatting would change a value. Outside a ticket tree it only checks.
- `story_cli new beat ... --at-turn N` places the beat itself, so the wiring brief no longer asks for a move by hand.
- The wiring worker records every remaining hand edit in `hand_edits.json`, written in its worktree. The check validates the file and copies it beside `plan.json`, and the station's result reports `hand edits: N` with each refused command, which shows which CLI commands are missing.
- CI's static job runs `story_cli fmt --check` and `entry_snapshots check` as named steps. `AGENTS.md` and the authoring-boundaries guide state the rule.
- Full PR suite on the branch: 5,265 passed, 26 skipped.

**Open.**
- Hand-edit fallbacks remain for refused CLI fields. Their log will show which commands to add next.
- The worker noted that `.plans/qualification/gate-inventory.md` is untracked, so it is absent from Ringer worktrees.

## Still to do in R1

See the task list in the [ladder](gate-proving-ladder.md#tasks): runtime rejections (gate 16) on saved good narration, the count of story-naming tests that pin behaviour (gate 11), the fun review's calibration (gate 21; Opus designs it, figures first), and the remaining deterministic gates on the good set, seeded faults and meaning-preserving variants.

## R1b-2: adjudicating the recorded term-leak rejections (2026-11-24)

**How.** A deterministic labelling rule, no model and no human (Ringer run `qual-step6-ledger-r1b2`, task `r1b2-term-leak-adjudication`, Codex, 71,525 tokens over two attempts; the second attempt failed only my check, which demanded a literal phrase in the report; I verified the worker's tree by hand). Tool, tests, labels and report: `qual-20261122/gates/r1b2/`. For each of the 68 term-leak rejections: `player_echo` (the leaked term is in the player's own command), `previously_visible` (in earlier player-visible text of the run), `unearned_new` (neither), `undecidable`. My independent recount of `player_echo` against the player input agreed on all 68.

| Label | Count | Share | Recovered by the retry |
|---|---:|---:|---:|
| `player_echo` | 43 | 63.2% | 100% |
| `previously_visible` | 0 | 0% | n/a |
| `unearned_new` | 25 | 36.8% | 100% |
| `undecidable` | 0 | 0% | n/a |

**What it shows.** Most term-leak rejections (43 of 68) are candidate false rejections: narration repeating a word the player typed ("memory card", "maintenance access route", "Michelle"). Every one was recovered by the in-turn retry, so they cost a retry, not a player-visible failure. Only 1 of the 19 player-visible bench rejections is a candidate false one (19 of 428 would become 18 of 428, 4.4% to 4.2%), so the visible-rejection rate is driven by genuine `unearned_new` leaks (for example "printed list" in 1A officer questioning, 15 of the 25). **What it does not show:** `player_echo` being false is a policy judgment about what the guard is for, not a proof; changing the guard to ignore the player's own words needs the guard owner's decision and a test that a player cannot launder an unearned term through their own command. The hosted 1 of 162 rejection was not adjudicated (its record has no rejected narration). `previously_visible` is 0 probably because most saved bench turns lack the earlier-turn text, so treat that count as a floor.

