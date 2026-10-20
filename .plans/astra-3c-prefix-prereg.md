# Preregistration: Stage 7 Scene 3C carried-state prefix (prerequisite for Step 8 of `.plans/chatgpt-3c-stuck-turns-plan.md`)

Written 2026-10-20 before any run. Brandon: "write the prefix preregistration and manifest."
Nothing here is billed. It does not decide the Step 8 comparison; it produces the common starting state Step 8 needs.

## Why a prefix, and what the plan asks for
Step 8 requires a real carried 3B state: committed reveal history, fact store, world parents and the player-visible transcript,
entered through the real 3B->3C transition so the 3C opening is rendered. Synthetic `entry`/`posta` starts assert 3C facts but
commit no 3B reveals (open question: does that cause the `unavailable knowledge 'relay open'` rejections?).
Search result (2026-10-20): no usable save exists. `runs/*.sqlite` are August saves from an earlier schema, `state_snapshots`
is empty; the Oct 12 canonical bundles hold fact names only (no values or parents) at a code SHA 22 story commits old.

## Two ways to get the prefix
**A (this registration): scripted canon journey, free.** Drive the real engine and real commit path through 1A -> 3B with the
scripted provider that `tests/test_canon_journey.py` already uses, stop at the last 3B turn before the transition, and save the
state with the real `RuntimeStateSqliteStore` (`storygame/runtime/persistence.py`, schema version 5). No model call.
Limits: the player-visible transcript is authored delivery text, not live narration; one history is shared by all Step 8 rows;
the journey uses `legacy_package(PACKAGE, {"k_sl_1a_a_r1"})` as the canon test does, which must be checked to leave 3B knowledge
and world parents identical to the real package.
**B (not registered, needs Brandon's spend go): live prefix.** A raw player plays 1A-3B on Cloudflare narration, roughly 65
accepted turns plus rejections. Only worth buying if A's carried state fails the checks below or Step 8 needs live-written
history. Its caps would be preregistered separately.

## Build (hermetic, one Ringer task)
`scripts/ringer/stage7/three_c_prefix.py`, `--out DIR`:
1. Bootstrap the current package, replay the 3A/3B tail of the canon journey with the scripted provider, stopping at the last
   turn before the scene changes to 3C. Save to `DIR/checkpoint.sqlite` (session id `stage7-3c-prefix`) and write
   `DIR/prefix.json`: package id and content hash, git SHA, turn index, scene, committed reveal ids, fact predicates with
   values, world parents of every tracked thing, `relay_open` and `janus_selection` knowledge status, transcript lines.
2. Cross the transition from a loaded copy with one scripted turn; record the rendered 3C `entry_text` and `bridge_text`.
No network, no `data/` or `src/` edits, no `uv`.

## Free checks (all must pass before Step 8 is built)
1. Save/load round trip: loaded state's model dump equals the saved dump; payload hash verifies.
2. Loading the checkpoint with the current package works; with a package whose content differs it fails loudly (do not patch a fingerprint).
3. The loaded state is in 3B, not 3C, with the 3B reveals and exit-condition facts committed by the real path (not asserted).
4. One scripted turn from the loaded copy ends in 3C and the transition text includes the real 3C entry text.
5. Report whether `relay_open` is already a committed or available knowledge at 3C entry in this carried state, and whether the
   Step 2/3 rejections (`relay open`, `card`) would still be unavailable. This answers the open synthetic-state question for free.
6. Running the build twice gives byte-identical `prefix.json` (deterministic).

## Bar and reporting
Pass = checks 1-4 and 6. Check 5 is reported, not scored. If check 3 fails (the scripted journey cannot reach 3B without asserting
facts), stop and report; do not fall back to asserting 3B reveals. If A passes but the transcript limitation matters for Step 8, the
decision to buy B belongs to Brandon with its own preregistered caps.

## Not decided here
Step 8 caps, arms and its harness changes (carried-start support in `three_c_probe.py`, checker, tests) get their own
preregistration after this passes. The alias-family smoke still needs Brandon's spend authorization.
