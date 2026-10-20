# Preregistration: Stage 7 Scene 3C carried-state comparison, `pump` vs `families` (DRAFT, not approved)

Written 2026-10-20 before any billed run. Implements Step 8 of `.plans/chatgpt-3c-stuck-turns-plan.md`.
Brandon has not approved this document or its caps. Nothing billed runs until he does.

## Harness (built, free, uncommitted)
`scripts/ringer/stage7/three_c_probe.py --start carried`, built by Ringer run `stage7-3c-stuck-turns-20261020T013217Z-p970532`
(1 attempt, PASS). Dry run: `bench/results/stage7-3c-carried-dry/`.
Each row replays the scripted 1A-3B canon journey (63 turns) on that arm's own package, then crosses into 3C through the real
transition, so the arm's opening text is rendered. It does not load `checkpoint.sqlite`: arm packages differ in content hash
and the fingerprint is not patched. The raw blind player then plays from scene turn 1. No 3C fact is asserted.
Limits: the 3B transcript is authored text; all rows share one history; this is not a live save.

## Arms (interleaved row by row)
- `pump` (baseline): entry text + custody delivery + pump-need sentence.
- `families`: `pump` + three D-R2 phrases (`broadcast a message/a response/an update to the families`).
Only D-R2 evidence differs. Semantic fallback ON, deadline 14 accepted 3C turns, 20 attempts per row, unchanged player prompt.

## Free checks already passed
Hermetic tests (carried replay per arm, 3B reveal ids equal `prefix.json`, `relay_open` committed, determinism, checker
rejects tampered label/cap, families-minus-pump diff is exactly the three phrases) and the dry run + checker.

## Live work
1. Smoke: `--n 1`, both arms, caps 80 Cloudflare / 40 player. Read every row in full (narration plus cues) first.
   Stop and ask Brandon on any harness problem; do not fix and relaunch alone.
2. Screen: `--n 12`, caps 960 Cloudflare / 480 player (about $1.92 Cloudflare at ~$0.002 per request; player calls carry a
   request cap only). One Ringer task per run, no replacement rows, partial results preserved on cap/quota/outage.

CLI:
`.venv/bin/python scripts/ringer/stage7/three_c_probe.py --n {1|12} --start carried --arms pump,families --semantic on --confirm --out bench/results/stage7-3c-carried-{smoke|n12}`

## Measures (engine data only)
Earned ending vs deadline vs none (earned = `story_complete` through eligible E after A, B, both C, both D with no
`deadline_event_ids` supplying a link; unknown provenance is not earned). Also: first-attempt A, B reach, repeated case
commands, both C by turn 10, D1/D2/E scene turns, rejections with provenance (including any `relay open`), clarifications.

## Bar
At least 10/12 earned endings, no false reveals, no new grounding failures. Report `pump` beside `families`.
A gap under 3 rows is not distinguishable; if both pass within 3 rows, prefer `pump` without the aliases.
If both miss, identify the dominant failure from saved prompts and preregister one supported source change; do not guess
wording and do not screen deadline 16 unless rows reach D1/D2 too late with evidence that more turns would finish.
Nothing is adopted into `data/` before this bar and the applicable checks pass.

## Not covered
Whole-game quality from one reused history, live-written 3B narration, hosted deadline telemetry, the four pump rows that
wander (01/02/04/06), and the hosted semantic-selection check beyond what the smoke exercises.
