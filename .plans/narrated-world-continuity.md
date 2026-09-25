# Narrated world continuity: implementation plan

Status (2026-09-24): Phase 0 bench work is through round 9 and
single-mechanism runs v11-v32, all on branch `round9`, not merged. A new
session should start at "State at hand-off (2026-09-23) - START HERE" in
Phase 0. It lists what changed in v21-v26, the next steps in order, the
story-package authoring rules any ChatGPT story prompt must state, and how
to run a measurement. Round 8's code is merged to `main` (PR #469,
PR #470). For history read "Round 9", "Round 9 as built", "Round 9 run" and
"Round 9 follow-up" at the end of Phase 0.

Round 8 measured no net improvement. Scored by Brandon's own comments in both
rounds, turns with a real failure were 25/48 in round 7 and 25/48 in round 8;
the reports' own headline numbers (23 then 27) are not comparable because the
judges were retuned between them, from 27.2%/82.9% agreement with Brandon to
96.5%/95.6%. Three mechanisms round 8 removed are genuinely gone (the hidden
card in the drawer, the invented `closed` on the laptop, "shattered" flattened
to `broken`); an equal weight came back, and two prompt fixes (B2, C2) did not
work. Round 9 attacks the three mechanisms behind 17 of the 25 remaining
failures.

Rounds 5-7 for context: round 6 (cc1e422) cut turns with a real failure from
26/47 to 19/46; round 7 (f5df910) fixed the plumbing round 6 exposed -
rejections 2 -> 0, recoveries 11 -> 3 - but turns with a real failure were
23/48 by its own judges, and Brandon's review showed most of that rise was
judge error rather than capture, which is what round 8 fixed first.

Four changes now ARE in the shipped game (everything else is still bench-only):
the compound-command splitter in `RuntimeEngine.turn`, the empty-reply-key
tolerance in `CloudflareTurnProvider`, the owner rule that no longer names
hidden items (`dafcc77`), a turn's beats chosen from authored realization links
instead of shared words (`c7ec63f`), and the turn rule "Finish each action the
player gives." (`a5df264`). The earlier bench experiment is recorded in
`.plans/narrated-world-changes-experiment.md`. This plan is self-contained so
it can be picked up in a new chat with no other context.

## Contents

1. The problem
2. Principles (settled by Brandon; do not re-litigate)
3. Working rules for this project
4. What is already known (evidence and engine facts)
5. Target design
6. Phases 0-8, each with decisions, tasks, files and exit criteria
7. Parallel track: defects the loop does not fix
8. Risks
9. Reference: commands and files

---

## 1. The problem

freytag-forge is interactive roleplay with free-text player input. A small
non-reasoning model (`@cf/meta/llama-3.1-8b-instruct-fast` on Cloudflare Workers
AI) narrates every turn live. The engine owns world state deterministically:
`FactStore`, authored item placements, setting facts and knowledge deliveries in
the story package.

Nothing the narration says reaches that state. If Kristin picks up Michelle's
phone - because the player asked or because the narrator added it - the next
prompt still says the phone is on the kitchen floor, in several authored places.
The narrator obeys, the phone is back on the floor, and the player watches the
world forget what they just read.

Goal: every change the narration shows the player persists in the world, the
story cannot be broken by a change without the right response, and the narrator
is always told the current state.

## 2. Principles (settled by Brandon; do not re-litigate)

1. **Every narrated change is part of the world.** Whoever caused it, a change
   that reached the player persists until something changes it again. Ignoring a
   change "destroys continuity and therefore believability". The only reason to
   refuse a change is that it breaks the story.
2. **A story-breaking change is handled by who caused it.**
   - Narrator-caused (model variability): regenerate the narration without that
     change, silently, before the player sees the turn.
   - Player-caused (the command asked for it): the player may not know the
     command breaks the story, so use the existing game-break warning, which
     explains the risk and lets them confirm or rewind.
3. **The engine owns state.** Captured changes are validated and recorded by the
   engine and sent back to the narrator by the engine. An earlier design in which
   the narrator returned world facts was dropped as unreliable; it is revived here
   only because the experiment measured a format that works.
4. **Fixing narration defects, in order:** a short concrete prompt rule; then an
   LLM semantic check of the narrated turn; keyword or regex scanning of narration
   last and treated as wrong. A lexical scan is acceptable only as an offline
   measurement read by a human, never as a runtime gate.
5. **Remove a mechanism before adding a rule.** The narrator's instruction budget
   is small: hand it material rather than rules about material, and replace rules
   rather than append them.
6. **Narrator rules use an 8th-grade reading level**, in the CHARACTERS, SCENE,
   CONSTRAINTS layout of plain prose lines.
7. **Token cost is a design constraint** (Workers AI budget).
8. **Everything works on any story package**, not tuned to continuity-initiative.
9. **`plot.md` is where world truth is settled first**; package files are one
   co-equal specification and changes propagate out from `plot.md`.
10. **Narrative bugs need a test-layer fix too**: judge and E2E coverage, with a
    deterministic structural check wherever the property allows one.

## 3. Working rules for this project

- **Every code change is a Ringer task** on GPT-5.6 Luna (`"engine": "codex"`,
  `"model": "gpt-5.6-luna"`). Claude writes a self-contained spec and a check
  script that executes the artifact and fails loudly with reasons, confirms the
  check fails on the unmodified build, reviews the patch, then applies and
  commits it. Worktrees start detached at HEAD: commit before running.
- **Raise a slow check's timeout explicitly.** A Ringer check is killed after 60
  seconds unless the task sets `"check_timeout_s": 900` or the run sets
  `RINGER_CHECK_TIMEOUT_S=900`; `timeout_s` covers only the worker. Both
  settings exist as of `~/dev/ringer` commit 6b3f85e (merged locally on
  2026-09-19, not upstream), proven by a run whose check slept 75 seconds and
  still reported. On any other machine, check that `check_timeout_for` exists
  in `ringer.py` first: while it did not, two checks in round 8 were killed
  mid-suite and retried for nothing, which is indistinguishable from a failing
  check.
- **Billed runs**: smoke-test one replicate and read the artifacts before any
  larger run. Keep only successful rows in `bench/results/ledger.jsonl`; remove
  failed rows and smoke-run rows.
- **Player input in scripts, tests and probes is imperative** ("Look at the back
  door."), never first-person narration.
- **Phase evidence has two gates**: deterministic structural tests are
  authoritative; staged or live runs are integration and quality evidence only.
- **Browser E2E runs against the hosted demo only**, never a local API.
- **Commands**: `TMPDIR=/tmp uv run pytest -q`; finish with
  `uv run ruff check --fix . && uv run ruff format .`. Serena MCP is preferred for
  code navigation.

## 4. What is already known

### 4.1 Capture works in one narration call with the right format

The bench-only harness `bench/item_facts.py` (`ItemFactsProvider`, a subclass of
`storygame.runtime.cloudflare.CloudflareTurnProvider`) adds a THINGS section to
the narrator prompt and reads changed facts back from the narrator's reply. Each
tracked thing has one `place` phrase and up to two `condition` phrases:

```text
THINGS:
- Michelle's phone. Where: on the kitchen floor. Condition: not damaged.
```

The narrator returns `item_facts` for only the things its story changed, for
example `{"Michelle's phone": {"where": "in Kristin's hand", "condition": ["not
damaged"]}}`. Two system-prompt lines ask for it:

- "Also return item_facts for each thing in THINGS that your story changed. Use
  only the names in THINGS."
- "For each one, give where it is now and up to two short condition phrases.
  Example: if she picks up the lantern from the table, the lantern is {"where":
  "in her hand", "condition": ["lit"]}."

Scene 1A, 4 replicates x 12 turns of "Look carefully at Michelle's phone." /
"Search for Michelle's work bag and any clue to where she went." / "Look at the
back door.", graded by `bench/fact-tracking-judge.mjs` and
`bench/continuity-judge.mjs` (GPT-5.4):

| | Single call | Separate second 8B call |
|---|---|---|
| Kept facts correct | 42 of 47 | 21 of 34 |
| Changes missed / invented | 3 / 1 | 4 / 9 |
| Narration contradicts its given facts | 1 | 8 |
| Narrated phone changes recorded | 4 of 4 | 5 of 6 |
| Kristin acts beyond the command | 18 of 47 | 26 of 34 |
| Scene restarts | 15 of 47 | 12 of 34 |

A free-phrase-list format scored only 21 of 46 with one call, and cutting the
rule list to six did not help. Decision recorded in the experiment plan: **a
second call is not necessary.** Once facts were carried, the narrator followed
them ("Kristin looks at Michelle's phone in her hand").

Limits of that evidence: one scene, one script, four hand-picked things, one
real change (a pickup), a grader calibrated on five constructed cases, and bench
overrides that deleted the phone's location from authored prose.

### 4.2 Engine facts the design depends on

- **Prompt assembly**: `storygame/runtime/cloudflare.py`,
  `CloudflareTurnProvider` - `_section_user_prompt`, `_turn_rules`,
  `_placement_rules`, `_setting_fact_rules`, `_scene_setting`, `opening`,
  `_system_prompt`, `_dispatch` (one bounded recovery request).
- **Reply contract**: `TurnProposal` in `storygame/runtime/contracts.py` -
  segments and `selected_knowledge_ids` only, strict, unknown keys rejected.
- **Turn flow**: `RuntimeEngine.turn` in `storygame/runtime/engine.py` - provider
  call, reveal resolution, `ProgressionValidator.validate_effects`, narration
  safety on a candidate state (`NarrationSafetyValidator`), then
  `ProgressionValidator.validate` for future dependencies; an at-risk result
  becomes a `GameBreakWarning` with a pending break (resolved by
  `resolve_break`). Rejections restore the snapshot; the web API answers 409.
- **Story-break check today**: `ProgressionValidator.unsatisfied_dependencies`
  in `storygame/runtime/validation.py` collects `required_dependencies` (entity
  IDs) from every transition reachable from the current scene. An entity is
  unavailable only when a fact with predicate `destroyed` or `incapacitated`
  names it, unless one of its `fallback_ids` is still available. Example:
  `memory_card` lists `michelle_phone` as a fallback in `world.yaml`.
- **Placements**: `item_placements` per scene in `plot.md`; an `ItemPlacement`
  may carry `while_fact_false` (`storygame/story_package/models.py`).
- **Saves**: `storygame/runtime/persistence.py`, `SCHEMA_VERSION = 4`.
- **Hosted E2E**: `frontend/e2e/scene-runtime.spec.js` already has
  `@world-state` ("Pick up Michelle's phone and keep it with you." then "Check
  that you still have Michelle's phone.") but asserts only that a scene ID
  exists.
- **Authoring docs**: `docs/markdown-story-authoring.md`.

## 5. Target design

Each normal turn:

1. **Prompt** carries THINGS: every tracked thing's current `place` and
   `condition`, from engine state. No other prompt line states a tracked thing's
   changeable facts.
2. **Narrate and capture in one call.** The reply adds `item_changes`: for each
   changed thing, its new `place`, up to two `condition` phrases, a closed
   `status`, and `cause` (`command` or `narrator`).
3. **Validate the capture** deterministically: known names only, format, status
   in its closed list. Malformed entries are dropped and recorded, never guessed.
4. **Check the story**: apply the changes to a candidate state, map `status` to
   the dependency predicates (`destroyed`, `incapacitated`, and any added), and run
   the existing future-dependency analysis.
5. **Route a story-breaking change by cause**: `narrator` - regenerate once with a
   plain hint naming the change to avoid, then fall back; `command` - raise the
   existing game-break warning.
6. **Commit** the thing changes atomically with the rest of the turn; a rejected
   turn changes nothing.
7. **Carry** the new state into the next prompt, across turns and scene
   transitions, and into saves.

Defaults recommended below are proposals; each phase lists the decisions Brandon
confirms before it starts.

---

## 6. Phases

### Phase 0 - Breadth measurement on the bench (billed, small)

**Why first.** Only a pickup in one scene has been tested. If the format fails
for other change types, the design changes before any engine work.

**Decisions before starting**: none.

**Tasks**
- [x] Ringer: extend `bench/item_facts.py` so a variation can seed THINGS from
  the package's own `item_placements` and setting facts for the scene instead of
  a hand-written seed, excluding anything the player has not been shown.
  (49333a0: `seed_from_package`; guarded placements are skipped.)
- [x] Ringer: add a two-scene variation and script that exercises opening a
  drawer, taking the laptop to the truck, damaging something, handing a thing to
  another character, and leaving the scene; carry tracked state across the
  transition in the bench. (49333a0: `item-facts-package-two-scene.json`, 8
  turns in 1A, offline advance, 4 turns in 1B.)
- [x] Ringer: add a long-session variation (at least 40 fixed turns) to expose
  drift and the two-condition cap pushing out a still-true condition.
  (49333a0: `item-facts-package-long.json`; judge adds
  `dropped_true_condition`.)
- [x] Calibrate `bench/fact-tracking-judge.mjs` on constructed cases for each new
  change type before trusting it. (13 cases: drawer, laptop move, damage,
  hand-off, scene exit, cap push-out. First pass 66 and 67 of 68: a dropped
  condition also counted as invented. fd95156 made the two criteria disjoint;
  then 68 of 68 twice, after correcting one label that the new wording made
  wrong - a replaced condition is invented, not dropped.)
- [x] Smoke one replicate per variation, read transcripts, then 4 replicates.
  (Two-scene: 48 judged turns, c7e49cf. Long: b11d04f keeps the session in
  1A and 5829d38 records an invalid proposal as a rejected turn; 157 judged
  turns.)

**Exit criteria**
- [x] Per-change-type accuracy table (kept facts correct, missed, invented) recorded
  in `.plans/narrated-world-changes-experiment.md`.
- [ ] Any change type below an accuracy Brandon accepts has a proposed format change,
  re-measured the same way. (Round 2 re-measured format v2: still below 92% for
  every change type except checking a carried thing. Open until Brandon picks
  the next strategy.)

**Round 2: format v2 (approved by Brandon, not started)**

Accepted accuracy: **92% "kept facts correct" per change type** (Brandon,
2026-09-15). Round 1 results are in `.plans/narrated-world-changes-experiment.md`:
only "check a carried thing" reached it; overall 31/48 (two-scene) and 99/157
(40-turn). Brandon approved building all four proposals below through Ringer.
State at hand-off: HEAD 8969afb, clean tree, nothing running.

- [x] Ringer task A (worktree; owns `bench/item_facts.py`, `bench/README.md`,
  `tests/test_bench_item_facts.py`):
  - `ItemFactsProvider._things_block`: a thing with no conditions renders as
    `- <name>. Where: <where>.` with no Condition part (today it renders
    `Condition: none.`, and the narrator copies `none` back as a condition).
  - Replace the two `_SINGLE_CALL_RULES` lines with exactly:
    1. `Also return item_facts for each thing in THINGS that your story changed. Copy each name exactly as it is written in THINGS.`
    2. `For each one, give where it is now and up to two short condition phrases. Keep any condition that is still true. Example: if she picks up the lantern from the table, the lantern is {"where": "in her hand", "condition": ["lit"]}.`
  - Leave `_SECOND_CALL_SYSTEM`, `apply_item_facts`, `package_seed` and
    `validate_item_facts` unchanged; update the tests and the README sentence
    about `Condition: none.`
  - Check (offline): `bench prompt --scene 1A --variation
    bench/variations/item-facts-single.json` gives THINGS exactly
    `- Michelle's phone. Where: on the kitchen floor. Condition: not damaged.` /
    `- Michelle's workstation drawers. Where: in Michelle's workstation. Condition: shut.` /
    `- the back door. Where: at the back of the kitchen. Condition: forced open, frame splintered.` /
    `- Kristin's laptop. Where: in Kristin's truck outside the house.`;
    both rule lines are present verbatim and "Use only the names in THINGS" is
    gone; the `example.json` prompt and `_SECOND_CALL_SYSTEM` are unchanged
    against the main checkout; full suite and ruff pass; only the owned files
    changed; export the patch. Confirmed failing on 8969afb.
- [x] Ringer task B (worktree, parallel with A; owns only the `overrides` of
  `bench/variations/item-facts-package-two-scene.json` and
  `item-facts-package-long.json`; never edits `data/`):
  - Add `{"old": "Michelle's workstation drawers are shut.", "new": "Michelle's carved drawer is shut."}`
    to each file's `overrides["plot.md"]["replacements"]`, keeping every
    existing replacement. The old text occurs once, in the 1A front matter of
    `plot.md`. The narrator acts on one drawer and kept reporting "drawer",
    which was dropped as an unknown name. The possessive name matches the other
    things, and a leading "The" would break exact name matching. If this wins,
    Phase 3 makes the real `plot.md` change.
  - Check (offline): for both variations the 1A package seed is, in order,
    Michelle's phone (on the kitchen floor; not damaged), Kristin's laptop (in
    Kristin's truck outside the house; no conditions), Michelle's carved drawer
    (in Kristin and Michelle's shared house; shut), with no seed issues; the
    effective 1A setting facts no longer mention the workstation drawers; a
    stubbed run (patch `CloudflareTurnProvider._request`, dummy
    `CLOUDFLARE_WORKER_URL`/`TOKEN`) plays every fixed turn; existing overrides
    are kept and nothing outside `overrides` changes. Confirmed failing on
    8969afb.
- [x] Review both patches, apply, commit. (40efb98; both passed first attempt,
  both checks confirmed failing on cab3e34.)
- [x] Smoke one replicate of each variation and read the transcripts, then run
  4 replicates of each: `--scene 1A --script change-types` for two-scene and
  `--script long-session` for long, output to
  `bench/results/item-facts-v2-{two-scene,long}-1a`. (Smoke rows removed from
  the ledger; both full runs passed their checks.)
- [x] Tally per change type against 92%, record both tables and the comparison
  with round 1 in the experiment record, and state the turn count behind each
  rate. (Two-scene 27/47, 40-turn 101/154; only "check a carried thing" meets
  92%.)
- [ ] Types below 92% go to the next strategy rank (an LLM semantic check of
  the narrated turn) or more replicates for thin samples. Decide with Brandon.

**Round 3: capture that records the world, not the narrator's wording (approved
by Brandon, 2026-09-15)**

Round 2 showed the remaining failures are engine capture, not narrator
compliance. Decisions:

- **Names are the engine's job.** Brandon does not care whether the narrator
  copies names; the engine must record the change against the right thing.
  "drawer" must resolve to Michelle's carved drawer.
- **Narrated things persist** (1c), so an unmatched name is either an existing
  thing under another name or a new thing, never silently dropped.
- **THINGS is selected per turn**, never the whole store. Always included: the
  current scene's authored things, progression dependencies, things the
  protagonist carries, and things changed last turn. Anything else only when
  the player's command refers to it.
- **One merged match call** decides both open questions, before narration: in,
  the command, the tracked names and last turn's unresolved names; out, the
  names the command refers to and, for each unresolved name, the tracked thing
  it is or `new`. A variant-name change therefore lands one turn late, but
  before the next prompt is built. The call is skipped when no tracked thing
  sits outside the always-included groups and nothing is unresolved, so a
  typical turn is one narration call and the worst case two.
  - **Bookmark (fallback if the merged call does not pan out):** separate
    calls - a refer call before narration and a resolve call straight after
    it - giving up to three calls a turn but no one-turn delay.
- **Partial entries**: a reply entry may omit `place` (place kept) or
  `condition` (conditions kept); an empty entry is ignored. Replace the rule
  example with one where only a condition changes and another condition is
  kept, so a state cannot wipe a place and a new condition does not erase a
  still-true one.
- **Judge**: split the loose `dropped_true_condition` label into dropped
  still-true condition, kept ended condition, and state recorded as a place;
  recalibrate on constructed cases before trusting it.
- **No cancelling facts**: a scripted state change must not run against an
  authored fact asserting the opposite. "Michelle's phone is not damaged." is
  removed from the two-scene variation (adb992f) and from the 40-turn one.

Tasks:
- [x] Ringer task C: remove the not-damaged fact from the two-scene variation
  (adb992f); 4 replicates recorded in
  `bench/results/item-facts-v2-nodamage-two-scene-1a`.
- [x] Ringer task D: the same removal in the 40-turn variation.
- [x] Ringer task E: judge label split (e1f835c), calibrated on 21 constructed
  cases: 149/151 and 151/151 after fixing one case; residual misses are
  `kept_ended_condition` over-firing on drawer-opened cases.
- [x] Ringer task F: partial entries, new example, merged match call, per-turn
  THINGS selection, persistence of narrated things, per-turn call counts.
- [x] Ringer task G: the rule line names both reply keys (7727375); the first
  v3 smoke had lost `where` to invented keys.
- [ ] Re-smoke findings (7727375) decided by Brandon, 2026-09-15:
  - **Omissions** (a change narrated but not reported, about 1 turn in 5): a
    short rule first, replacing line 1; if it does not hold, the next turn's
    match call also reads the last narration and adds changes the reply left
    out.
  - **Carried** is decided by the match call, not by the protagonist's name in
    a place ("in Kristin's truck" was wrongly carried). The call already fires
    exactly when things sit outside the other groups; it gets their places and
    the player character's name and returns the ones being held or carried.
  - **Scoring stays whole-state**: a persistent capture error keeps failing
    later turns.
  - Also: replace the rule example with an opened box so a state goes in
    `condition`, and add a judge calibration case for a correct capture after
    narration that contradicts the given facts.
- [x] Ringer task H: omission rule, opened-box example, carried from the match
  call. Judge recalibrated with the contradictory-narration case: 158/158 in
  both passes, no judge change needed.
- [x] Smoke, then 4 replicates of each variation; tally against 92%.
  - Before the place key: two-scene 28/47 = 60%; 40-turn 64/155 = 41%, where
    three of four replicates recorded the drawer's state as its place on the
    same turn and the replicate that did not scored 27/38 = 71%. The judge
    needed a retry fix first (a84c90c).
  - After the place key, match-call carried things and place normalisation
    (417e4f1): two-scene 26/48 = 54%; 40-turn 71/156 = 46%. No change type
    reaches 92% in either run; the best is 75% on three two-scene types.
  - The normalisation does not work: 81 of 156 turns still carry a state in a
    place field, and the corrections that did fire were wrong. The match call
    runs on the same 8B narrator model, so the semantic check is done by the
    model that made the error.
  - Round 3 did not beat round 2 on the 40-turn script (63% then, 46% now);
    the comparison is indicative, not clean, because the package overlays and
    the judge criteria both changed.
  - Round 4, binary state axes (f461739): two-scene 28/47 = 60%; 40-turn
    105/159 = 66%, the best 40-turn figure of the project, past round 2's 63%.
    State as place is 0 of 206 turns and kept-ended conditions are 0 and 3.
    Only open or close reaches 92%, on 4 two-scene turns, which is too thin to
    count; the best broad figures are move between places 88% and check a
    carried thing 75%. The axes themselves fired rarely - 0 fixes in two-scene,
    6 across 159 turns - so the gain came from DELETING the failed place
    normalisation and from an empty condition list clearing a stale pole, not
    from routing a pole out of the place field.
- [x] A state landing in `place`: resolved by declared binary axes plus the
  round 6 changes; state_as_place was 0 of 46 turns in round 6.

**Rounds 5-7: one word for place, reply changes that land, tight context
(2026-09-16/17, branch `narration-phone-fixes`)**

Decisions Brandon made in these rounds (all saved as standing rules):
- A thing's location is `place` in every layer - prompts, store, recorded JSON,
  judges, reports, docs. `where` is gone, with no alias (e655ec5).
- There is one drawer in the story; it is named `drawer`, and `plot.md`,
  `knowledge.yaml` and `pacing.yaml` never say "drawers" (e655ec5, 1c82bd8).
- Compound player commands are split into one sentence per action by the
  engine, deterministically, never by an LLM. Evidence: "Go out to your truck
  and bring your laptop inside." finished 2/6 joined vs 6/6 as "Go out to your
  truck. Bring your laptop inside." (`bench/results/split-command-1a`).
  Implemented with a spaCy parse in `storygame/runtime/command_split.py`,
  called from `RuntimeEngine.turn`; spaCy and en_core_web_sm are locked runtime
  dependencies (8a5b1d4). Bench records keep `narrated_command` (cc1e422).
- Every well-formed change a narrator reply reports must land in state on that
  turn; a dropped change is a severe failure however rare. New names resolve in
  the same call; a self-mapped, omitted or unmatched name becomes a new thing;
  a condition-only new thing has `place: None` (f7dda9c).
- THINGS carries a tracked thing only when the command refers to it (match
  call `refers`) or a reachable transition requires it. Not scene placement,
  not being held, not changed last turn, not a projected beat. "Only send the
  laptop when the command mentions it." The match call no longer asks for
  `carried` (716c0ba).
- Fix order for narration defects: a short prompt rule first, then an LLM
  semantic check, never regex over narration. The thrown phone was fixed at
  rank 1 by replacing the narrator's example with a thrown cup that "breaks and
  falls" to `{"place": "on the floor", "condition": ["broken"]}` (f7dda9c).
- Characters join the containment tree (decision 1e below, not built yet).

Also done: judges send and must echo real `turn_number`s with one retry
(4e27f99); `bench/failure_report.py` builds the per-round failure report and
prints both judges' reasons (`--section LABEL=DIR`, `--facts`, `--title`,
`--preamble-file`, `--out`); a fixed thing no longer logs a refusal when its
current place is repeated.

Round 6 measurement (`bench/results/item-facts-v7-two-scene-1a`,
`bench/results/round6-failures.md`): thrown phone recorded on the floor broken
4/4; receipt and note recorded on the turn they appear 4/4; THINGS about one
line a turn. Remaining failures, worst first:
1. The matcher merged a narrated "USB drive" (place "in drawer") into `drawer`
   in 2/4 replicates, losing the drive and putting its condition on the drawer.
2. Turns rejected with INVALID_PROPOSAL for forbidden top-level reply keys.
3. `closed` added to the laptop without narration (declared axis).
4. Narration drift the judges flag: phone left "on the passenger seat" then
   handed over without being picked up; the continuity judge also overreaches on
   details it was not given (passenger seat, the bench scene).

Round 7 (in progress):
- [x] Rejection diagnosis probe, 10 replicates x 8 Scene 1A turns, raw replies
  captured (scratch probe, not in repo): 0/80 turns rejected but 7/97 narration
  replies had forbidden top-level keys, each costing a recovery request (8
  recoveries in 80 turns): empty `grounding_ids` (3), empty `known` (1), an item
  change at top level such as `"truck": {"place": "on the road", ...}` (2, lost
  even when recovery succeeds), `"Michelle's phone": {"owner": "Michelle"}` (1).
- [x] Fix: `CloudflareTurnProvider._clean_reply` drops empty extra top-level
  keys (counted in `reply_keys_dropped`); `ItemFactsProvider` lifts top-level
  place/condition entries into `item_facts` (counted in `item_facts_lifted`,
  never overriding an existing entry); other non-empty extras still fail
  (6d670de).
- [x] Matcher wording bake-off, 8 fixed cases x 10 calls per prompt, scored as
  the engine resolves (self-map = new): current 61/80; wording A ("the very same
  object ... A thing that is in, on or under another thing is a different
  object, like a key in a box.") 67/80, USB drive kept separate 10/10 vs 1/10,
  small regressions (memory card 8/10, note 9/10); wording B (keep "means the
  same thing", add the in/on/under sentence) 60/80, USB drive 0/10 - rejected.
  A "card" taped under the drawer never maps to Michelle's memory card under any
  wording: an open short-name problem.
- [x] Wording A installed in `_MATCH_SYSTEM`, and `ItemFactsProvider._request`
  no longer creates an empty `item_facts` unless an entry is lifted (2f85fec,
  634 tests pass).
- [x] Re-ran the rejection probe on the fixed code (10 x 8 Scene 1A turns,
  raw keys captured before cleaning). Real improvement in cost and risk, not in
  model behaviour: recovery requests 8 -> 1 per 80 turns; replies with forbidden
  top-level keys 7/97 -> 8/90 (the model still emits them), but now handled
  without a retry - empty values dropped (grounding_ids 2, known 2, and one reply
  dumping 17 SCENE detail names as empty objects), one misplaced item entry
  lifted; rejections 0 -> 0 (not a discriminating number at this sample).
  "Narrator omitted item_facts" issues 1 -> 2, now honestly recorded.
- [x] Four-replicate two-scene round with judges (smoke first) at f5df910:
  `bench/results/item-facts-v8-two-scene-1a`, `bench/results/round7-failures.md`.
  - Plumbing fixed: rejected turns 2 -> 0; recovery requests 11 -> 3; the
    USB drive in the drawer resolves as a new thing 2/2 (round 6: 0/2, merged
    into `drawer`); kept-ended conditions 3 -> 0; dropped still-true 1 -> 0.
  - Headline did not improve: turns with a real failure 19/46 -> 23/48;
    facts-after-wrong 7 -> 12, invented 8 -> 11, canon contradictions 11 -> 18,
    missed 3 -> 2.
  - Replicates are highly correlated in both rounds (turn 1 narration identical
    4/4 both rounds; several turns 1-2 distinct first sentences), so a single
    command moving 2 -> 4 is within noise. Four replicates here are closer to
    one or two independent samples.
  - Most of the rise is not capture. Real capture defects: the invented
    `closed` on the laptop (turn 4, flagged 3/4) and one laptop move
    arguably missed (r3 turn 5). The rest:
    - Narration invents a place to pick up from: "Pick up Michelle's phone.
      Put it in your pocket." gives "reaches for Michelle's phone on the
      table" 4/4, because turn 1's "Look carefully" already put it in her
      hands. The fact judge also marks facts-after wrong although the pocket
      is recorded correctly.
    - Laptop "on the passenger seat" narration contradicts "in Kristin's
      truck" 3/4 (same as round 6).
    - Continuity judge overreach: turn 12 "Check who has Michelle's phone"
      4/4 flagged because the command said hand it over, while the narration
      only held it out (3/4 omit item_facts, correctly no change); turn 7
      "shattered into pieces" cannot be picked up 3/4; broken vs shattered.
    - Design disagreements: the fact judge calls a narrated new `truck`
      (moving, on the road) invented; narrated things persist by decision 1c.
    - Canon leak not flagged by either judge: the narrator finds "memory card"
      IN the drawer 2/4 (canon: taped beneath, hidden until found), recorded
      as a new `memory card` separate from the hidden tracked card - the
      short-name problem again, now also a protected-knowledge leak.
- [ ] Next candidates, in Brandon's priority order once he picks: decision 1e
  (containment tree with characters, including container-shaped
  `{"kitchen counter": {"contents": [...]}}` replies, which are still dropped);
  the invented `closed` on the laptop; the "card" short-name mapping (now
  also an early reveal of the hidden memory card); the narrator inventing a
  pick-up source for a thing already held; judge overreach on ungiven details
  and on commands the narration did not complete; more independent replicates
  before trusting per-command swings. (Superseded by Round 8 below.)

**Round 8: fixes from Brandon's round 7 review (approved 2026-09-19)**

Source: every round 7 turn with Brandon's comments, `bench/results/round7.md`.
Each finding below was traced to its mechanism before a fix was proposed.

Findings and decisions:
- **A. Hidden-card leak (shipped runtime).** `CloudflareTurnProvider._owner_rules`
  names every item in the scene's `item_ids`, so every 1A and 1B prompt ends
  "Say who owns a thing the first time you name it: Michelle's memory card,
  ...". The narrator then finds the card IN the drawer (r2, r3) or a USB drive
  in its place (r1, r4); canon has it taped beneath, hidden until found. Fix:
  name only items with a placement in the current scene that no
  `while_fact_false` guard hides. A found item carried into a later scene loses
  its owner hint until Phase 4 tracks carried things. Brandon also changed
  the 1A.1 detail "KMS initials in drawer" to "KMS initials carved in drawer"
  in `plot.md`.
- **B1. Invented `closed` on the laptop (4/4).** `ItemFactsProvider._things_block`
  renders a thing whose axis value is unknown as `Condition: closed or open.`,
  which asks the narrator to pick one. Fix: no Condition part for an unknown
  axis value.
- **B2. Invented pick-up source.** "Pick up Michelle's phone." while THINGS says
  it is in her hands gives "reaches for the phone on the table" (4/4); the
  laptop "from the desk" (r3 t5). "On the table" comes from the output example
  "She looks at the lantern on the table."; "Keep each object where the scene
  puts it." points at nothing once the bench strips placements from SCENE.
  Fix, replacing not adding: example "She looks at the lantern. Its light has
  gone out."; the rule becomes "Each thing starts at the place THINGS gives
  it."
- **B3. "Shattered into pieces" recorded as `broken` (4/4).** The narrator copies
  "broken" from the thrown-cup example. Fix: an example whose condition reuses
  its own story's words: if she drops a cup and it cracks in two, the cup is
  `{"place": "on the floor", "condition": ["cracked in two"]}`. Decided for
  Phase 1a/2: smashing Michelle's phone (the memory card's fallback) raises
  the game-break warning; if the player goes ahead, the phone is in pieces and
  destroyed as a whole.
- **B4. Stale AFTER in the report.** On a reply with no `item_facts`,
  `apply_item_facts` returns early without clearing `_changed_last_turn`, so
  `bench/core.py` shows the previous turn's changes (receipt, note) as this
  turn's AFTER. Stored state is unaffected. Fix: a missing `item_facts` means
  no change; clear the set; record the issue as "narrator omitted item_facts".
- **C1. Receipt and "old warehouse at midnight" (4/4, not in the package).**
  Investigate: 1B turns project beats 1B.2 and 1B.3 but never 1B.1 (Michelle's
  Dead Drop), so SCENE never describes the bench; the fitting candidate
  `k_sl_1b_a_r2` (a photograph in the dead drop) was offered 16 times and
  picked 0. The watching man's only permitted speech is the scene frame "The
  park is an immediate place of pursuit and uncertainty." Findings (read-only
  investigation, 2026-09-19; prompt rebuilt offline after the bench's own
  offline 1A->1B advance):
  1. **The dead drop never reaches the narrator.** `_candidate_beats` sends a
     storylet's source beat only when the candidate's words and the beat
     prose share at least two content words. SL-1B-A's only source beat,
     1B.1, shares zero with both of its candidates (the prose never says
     dead drop, photograph, token or sequence), so it is always dropped;
     SL-1B-B's Brandon beats 1B.2 and 1B.3 pass. The one committed statement
     about the card says only "learns the place she used to trade
     information", never "a dead drop at a bench". Nothing links the bench
     to the photograph candidate, so "anything Michelle left" gets a stock
     clue. This gate is a keyword match over authored text (not narration)
     used as a runtime gate. Options for Brandon: give each realization an
     authored source-beat link in `storylet-routes.yaml` and drop the word
     overlap; or always send a single-beat storylet's beat; or author the
     dead drop into the 1B.1 prose (`plot.md` first).
  2. **Stale 1A material in the 1B prompt.** SCENE still carries 1A's entry
     statement "The house is quiet and Michelle is missing.", and CONSTRAINTS
     carries a 1A complication as "This happens now. Show it in the scene:
     The patrol is checking parked vehicles and speaking to neighbors. The
     house is no longer the only place under watch." Not yet known whether
     this is the bench's offline advance or the runtime.
  3. **Scene-entry knowledge becomes NPC speech.** `k_scene_1b_entry` is
     public, so every NPC present "may say this aloud"; Brandon's only
     permitted line is the scene frame. Candidate fix: exclude
     `source.kind: scene_entry` knowledge from NPC sayable lines.
  4. Identical narration 4/4 is the model's default for an identical prompt;
     replicates are not independent samples.
- **C2. Commands left unfinished** (r3 t5 laptop never reaches the truck; t8
  never names the park 3/4; t11 handoff only held out 4/4). Fix: replace
  "Answer what the player did." with "Finish each action the player gives."
- **Judges** (measurement only; Brandon agreed there is no tie-break vote, the
  two judges get disjoint scopes and the same GIVEN facts, and a judge never
  edits narration - runtime correction is decision 1d's regeneration):
  1. The continuity judge reads 1A canon for 1B turns (`packageCanon` uses the
     run's starting scene). Give each turn its own scene's canon and mark the
     transition.
  2. Its rubric calls a thing away from its placement "when no player command
     moved it" a contradiction, against principle 1. Send each turn's GIVEN
     facts and state that they are the current truth over authored placements
     and earlier narration.
  3. Both judges: a more specific place or state inside the given one is not a
     contradiction (passenger seat in the truck; street outside the house;
     broken for a cracked screen).
  4. Fact judge: a narrated new thing is not invented (1c);
     `facts_after_wrong` means AFTER does not match the narration, not that
     the narration contradicts GIVEN.
  5. Acting beyond the command is never a contradiction; add
     `command_not_finished` and `reveals_hidden_canon` labels. Recalibrate on
     cases taken from round 7, labelled by Brandon's comments.

Order:
- [x] Step 1, no billing: Ringer tasks for A (with the test and overlay
  updates Brandon's `plot.md` change needs), B1 and B4; the read-only C1
  investigation. (A dafcc77, B1+B4 e3dec65; full suite 642 passed with the
  env-dependent test deselected.)
- [x] C1 option (a), approved by Brandon 2026-09-19: each realization names
  its `source_beats` in `storylet-routes.yaml` (required when its storylet
  has more than one beat, fail closed at load); `_candidate_beats` uses those
  links and no word overlap (c7ec63f, 647 passed). The 1B dead-drop
  candidates now project beat 1B.1. Open story question for Brandon: beat
  2B.2 "Kristin Was Bait" is a source of SL-2B-B, but neither realization
  reveals it (both assert only Brandon's JANUS role), so no realization links
  it and it never reaches the narrator.
- [x] Step 2: judge fixes (cd33b32) and tuning (2b8d6b3), then round 7's saved
  turns re-judged (8 judge calls each time). Scored against Brandon's round 7
  comments turned into labels (114 continuity, 113 fact cells; labels and
  scorer in the session scratchpad):

  | Judge | Round 7 judges | After fixes | After tuning |
  |---|---|---|---|
  | continuity | 27.2% | 91.2% | **96.5%** |
  | fact | 82.9% | 89.4% | **95.6%** |

  Brandon's label rulings, 2026-09-19: a look command is finished whether or
  not Kristin picks the thing up; an invented USB drive in the drawer IS a
  hidden-canon reveal, because the only drive in the story is the one taped
  beneath the drawer; its own condition is then moot. The four remaining
  fact-judge misses all call a condition the narration never showed
  (`crumpled`, `handwritten`, `found`) invented, which the tuned rule makes
  correct and the labels too lenient. Caveat: the rubric examples come from
  round 7, so these rates are optimistic for a new story.
- [x] Step 3 code: B2, B3 and C2 prompt changes (a5df264, 649 passed). The
  turn rule is "Finish each action the player gives."; the bench replaces the
  scene-placement rule with "Each thing starts at the place THINGS gives it."
  through a shared `_object_place_rule()` the bench overrides, so both the turn
  and opening paths change; the reply example is a cup that cracks in two; both
  variations' output examples drop "on the table".
- [x] Step 3 measurement, run at 4dc062d after a one-replicate smoke
  (`bench/results/item-facts-v9-resmoke-two-scene-1a`): 4 replicates into
  `bench/results/item-facts-v9-two-scene-1a`, every turn written up with
  Brandon's comments in `bench/results/round8.md`. Answers to the questions it
  was run for: no invented USB drive 4/4, though r2 still narrated the hidden
  memory card in the drawer; the invented pick-up source survives 4/4 in a new
  form; the laptop never arrives `closed`; the hand-over completes 0 of 4. The
  full scoring and the mechanisms behind what remains are in Round 9 below.
- [ ] Also done outside this repo: Ringer gained `check_timeout_s` per task and
  `RINGER_CHECK_TIMEOUT_S` as a run default (branch `check-timeout-override`,
  1d074ea, 269 tests pass). Until that reaches Ringer's main, AGENTS.md's
  instruction to raise the check timeout does not work: the limit is the
  hard-coded 60 seconds, so task checks run only the affected test files and
  Claude runs the full suite before applying each patch.

**Round 9: the three mechanisms behind two thirds of the failures (proposed
2026-09-21, awaiting Brandon's approval)**

Source: `bench/results/round8.md` with Brandon's inline comments, plus a
re-scoring of `bench/results/round7.md` against his round 7 comments so both
rounds are graded by the same standard.

**Round 8 measured no net improvement.** The report's headline (23/48 -> 27/48)
is not comparable, because round 7 was labelled by judges scoring 27.2% and
82.9% against Brandon's rulings and round 8 by judges at 96.5% and 95.6%.
Scored by Brandon's own comments in both rounds:

| | Round 7 | Round 8 |
|---|---|---|
| Turns with a real failure (Brandon's labels) | 25 / 48 | 25 / 48 |
| Turns the round's judges reported | 23 | 27 |

Round 8's judge count differs from Brandon's by six cells: four wrongly failed
(r1 t2, r1 t10, r3 t2, r3 t10) and two wrongly cleaned (r1 t1, r3 t7).

The composition did move. Three mechanisms round 8 removed are gone, and an
equal weight came back elsewhere:

| Defect | R7 | R8 | |
|---|---|---|---|
| Hidden card or USB drive in the drawer | 4/4 | 1/4 | fixed (A) |
| Invented `closed` on the laptop | 4/4 | 0/4 | fixed (B1) |
| "shattered" flattened to `broken` | 4/4 | 1/4 | fixed (B3) |
| Thrown phone lands on the floor | 4/4 | 4/4 | held |
| Narration contradicts the GIVEN place | 4/4 (t3 only) | 9 turns, t3/t5/t6/t9/t12 | worse |
| t8 "drive to the park" unfinished | 3/4 | 4/4 | worse |
| Hand-over completed | 0/4 | 0/4 | unmoved |
| Invented receipt at the bench | 4/4 | 3/4 | unmoved |
| Duplicate entity ("laptop" vs "Kristin's laptop") | 0 | 1 | new |

So B2 and C2 did not work. B2 ("Each thing starts at the place THINGS gives
it.") did not remove the invented pick-up source, it mutated it: "on the table"
became "reaches into her pocket and pulls out", which in r3 t3 and r4 t3 is the
exact inverse of the command. C2 ("Finish each action the player gives.") left
the hand-over at 0/4 and made the park turn worse.

Root cause of all 25 round 8 failures:

| Mechanism | Turns |
|---|---|
| 1. Narration contradicts the GIVEN place | 9 |
| 2. t8 travels to the *next scene* | 4 |
| 3. Hand-over never completes | 4 |
| 4. Scene restart or stale 1A colour | 2 |
| 5. Physically impossible state (both judges missed) | 2 |
| 6. Name resolution duplicate | 1 |
| 7. Hidden canon in the drawer | 1 |
| 8. Capture reports mid-turn, not end-of-turn | 1 |
| 9. Other unfinished command | 1 |

Mechanisms 1-3 are 17 of 25. They are why the same defects recur round after
round.

**A measurement finding that conditions everything below.** Turn 1's narration
was byte-identical across all four replicates in both rounds, and most turns
differ only in the first sentence. Four replicates of a fixed 12-command script
is closer to 12 observations than 48, so every "4/4" and "3/4" in these reports
is near enough one sample. Widen the script with distinct commands before
adding replicates; more replicates buy more copies of the same sample.

Decisions Brandon settled on 2026-09-21, before Round 9 started:
- [x] R9-1 replaces the impossible turn AND widens the script, at two
  replicates instead of four. Strict comparability with rounds 1-8 is given up
  deliberately: the measurement finding above says the fourth replicate buys
  another copy of the same sample, so the round trades it for six more distinct
  turns. 1A now runs 12 distinct commands and 1B 6, so the round measures 18
  distinct turns at 2 replicates (36 turns) against round 8's 12 at 4 (48).
- [x] R9-4 ships the owner-key rule only; the head-noun rule is NOT built. A
  bare name still goes to the match call. Checked against the code first: no
  card is tracked at seed in 1A, so the head-noun rule could never have
  resolved hidden canon - it would only have merged a later bare "card" into a
  card the narration had already created. That is worth less than the risk of
  silently merging two things that share a head noun.
- [x] The C1 finding "scene-entry knowledge becomes NPC speech" stays parked.
  R9-3 ships the concrete hand-over rule alone, so the hand-over's 0/8 across
  two rounds is attributable to one change. If it still fails, excluding
  `source.kind: scene_entry` from NPC sayable lines is round 10's first
  candidate, with clean evidence behind it.

---

**R9-1. Remove the impossible turn from the bench script (no billing, do first)**

Turn 8 is `"Leave the house and drive to the park with Michelle's phone."`, the
last 1A turn, with 1B reached by the bench's own offline advance
(`bench/variations/item-facts-package-two-scene.json`). The park is in 1B's
SCENE. The 1A narrator cannot arrive there whatever rule it is given, so those
four turns have been guaranteed failures for two rounds and have cost two
rounds of signal. Real cross-scene travel is an engine capability, not a
narrator rule; it belongs to Phase 1 and later, and is recorded in the parallel
track below.

- Ringer task (worktree; owns only the `scripts` block of
  `bench/variations/item-facts-package-two-scene.json` and its test):
  replace the eighth 1A input with `"Carry Michelle's phone out to the truck."`
  Leave every other input, the `continue_to` block and the overrides untouched.
- Check (offline, deterministic): the 1A script has exactly 8 inputs, the
  eighth is the new text, the other seven are unchanged byte for byte against
  the main checkout, `continue_to` and `overrides` are unchanged; a stubbed run
  (patch `CloudflareTurnProvider._request`, dummy `CLOUDFLARE_WORKER_URL` and
  `TOKEN`) plays all twelve turns; full suite and ruff pass.

**R9-2. The GIVEN place goes in the PLAYER block, not in THINGS (no billing to
build; measured in the round 9 run)**

Mechanism 1, nine turns, the largest bucket. Rank 1 has been tried three rounds
running: the `place` rename in round 5, then B2 and the deletion of the "on the
table" example in round 8. It has not moved. The prompt order is CHARACTERS ->
SCENE -> THINGS -> CONSTRAINTS (about twenty rule lines) -> PLAYER
(`_section_user_prompt`, `storygame/runtime/cloudflare.py`). A thing's current
place is the first thing the model reads and the command is the last.

This is a subtractive, material-first change under principle 5, not another
rule: attach each referred thing's place to the command itself.

```text
PLAYER:
- Pick up Michelle's phone. Put it in your pocket.
- Michelle's phone is in Kristin's hands right now.
```

- Ringer task (worktree; owns `bench/item_facts.py`, `bench/README.md`,
  `tests/test_bench_item_facts.py`): `ItemFactsProvider` appends one
  `<name> is <place> right now.` line to the PLAYER block for each thing the
  turn's THINGS block carries that has a place, in THINGS order, through a
  narrow hook on the base provider rather than a copy of
  `_section_user_prompt`. A thing with no place contributes no line. THINGS
  itself is unchanged, so nothing is added to the token budget beyond these
  lines.
- Check (offline, deterministic): `bench prompt --scene 1A --variation
  bench/variations/item-facts-package-two-scene.json` prints the PLAYER block
  with the command first and one place line per placed thing in THINGS order;
  a thing seeded with `place: None` produces no line; the CHARACTERS, SCENE and
  CONSTRAINTS blocks are byte-identical to the main checkout; the shipped
  `CloudflareTurnProvider` prompt (no bench subclass) is unchanged; full suite
  and ruff pass.
- Honest limit, per principle 4: this check proves the prompt says it, never
  that the model obeyed. Only the billed run measures the nine turns.

**R9-3. One concrete rule for the hand-over, replacing the inert generic one
(no billing to build)**

Mechanism 3, four turns, 0/4 in both rounds. All four replicates write
"Kristin wonders if he'll take it" almost verbatim: a model default for an
unresolved social beat. "Finish each action the player gives." is generic and
demonstrably inert, so this replaces it rather than appending, per principle 5,
and names the act concretely at an 8th-grade level per principle 6.

- Ringer task (worktree; owns `storygame/runtime/cloudflare.py` turn rules and
  their tests): in `_turn_rules`, replace
  `"Finish each action the player gives. Only show <protagonist> doing what the
  player said."` with `"Finish each action the player gives."` plus
  `"When the player gives a thing to someone, that person takes it."`, keeping
  the protagonist clause as its own line so no line joins two demands. Apply to
  every narrating path per AGENTS.md: `_turn_rules`, `opening()`,
  `_system_prompt` and `_recover_malformed_response` as each applies, built in
  one helper called from both the turn and opening paths.
- Check (offline, deterministic): a rendered turn prompt and a rendered opening
  prompt both contain the new line verbatim; no rule line contains two
  sentences joined by "and"; the old joined line appears nowhere in the
  repository; full suite and ruff pass.
- Likely companion cause, still undecided (C1 finding 3): `k_scene_1b_entry` is
  public, so the watching man's only permitted line is the scene frame. The
  narrator has nothing for him to do, so it writes suspense. Excluding
  `source.kind: scene_entry` knowledge from NPC sayable lines is the
  subtractive half of this fix and is a separate task if Brandon wants it in
  scope.

**R9-4. Name resolution is deterministic and happens before the match call (no
billing)**

Mechanism 6. r1 t5's reply was
`{"laptop": {"owner": "Kristin", "place": "in the truck"}}`. `_add_new_item`
(`bench/item_facts.py`) discards the `owner` key, the 8b match call is asked
the question, and a second laptop is invented; AFTER then holds two laptops and
the turn fails `facts_after_wrong`, `missed_change` and `invented_change` at
once. Resolving a narrated name to a tracked thing is the engine's job, not the
narrator's and not an 8b call's.

- Ringer task (worktree; owns `bench/item_facts.py` and
  `tests/test_bench_item_facts.py`): before `_resolve_new_items` builds its
  match payload, resolve deterministically and remove the resolved names from
  the call:
  1. an entry carrying `owner: "X"` under bare name `n` resolves to tracked
     `"X's n"` when exactly one such tracked name exists;
  2. a bare name that is the head noun of exactly one tracked name resolves to
     that name ("laptop" -> "Kristin's laptop", "phone" -> "Michelle's phone");
     two or more candidates fall through to the match call unchanged.
  Record each deterministic resolution in `last_item_facts_match["resolutions"]`
  with its own marker so the reports can tell it from a model resolution, and
  count it.
- Check (offline, deterministic): with tracked `Kristin's laptop` and
  `Michelle's phone` and a stubbed `_request` that fails the test if it is
  called, `{"laptop": {"owner": "Kristin", "place": "in the truck"}}` merges
  into `Kristin's laptop` and creates no new thing; `{"phone": {...}}` merges
  into `Michelle's phone`; with two tracked laptops, `{"laptop": {...}}` still
  reaches the match call; `{"USB drive": {"place": "in the drawer"}}` still
  reaches the match call and still resolves as a new thing, so round 7's
  wording-A behaviour (a thing in, on or under another thing is a different
  object) is not regressed; full suite and ruff pass.
- This also closes round 7's open short-name problem for "card", subject to the
  decision above.

**R9-5. The capture reports the end-of-turn state (no billing, fold into an
existing line)**

Mechanism 8, r2 t6: the narration throws the phone and then picks it up, and
the reply reports "on the floor". Nothing asks for the state at the end of the
turn.

- Ringer task (worktree; owns `bench/item_facts.py`, `bench/README.md`,
  `tests/test_bench_item_facts.py`): amend `_SINGLE_CALL_RULES[0]` so it asks
  for where each changed thing is when the story ends, without adding a line.
- Check (offline): the rendered system prompt contains the amended line
  verbatim and still contains exactly two single-call rule lines; the second
  line and `_SECOND_CALL_SYSTEM` are unchanged against the main checkout; full
  suite and ruff pass.

**R9-6. The test layer: three judge gaps and the calibration corpus (no
billing except the judge calls)**

Per principle 10, these are test-layer bugs, not engine bugs.

- Both judges missed two physically impossible states Brandon caught by hand: a
  phone that is "locked" while it needs charging (r1 t1) and a phone
  "shattered" but "still functional" (r3 t7, and the same slip in r4 t6 where
  the screen in pieces was read as the phone in pieces). One rubric point
  covers all of them: a narrated state must be physically possible given the
  thing's recorded conditions.
- The continuity judge missed a scene restart: "navigating through the
  emergency-clogged streets" for a walk to a truck parked out front (r1 t4).
- Reproducible fact-judge bug, flagged twice by Brandon on r1 t10: it called
  the bench and the paper untracked when both are in AFTER. The scope rule
  ("`facts_after_wrong` means AFTER does not match the narration") is already
  in the rubric; the judge is not applying it to newly tracked things.
- Carry the calibration corpus into the repository. Round 7's labels (114
  continuity and 113 fact cells) plus `check_calib.py` and `rejudge.py` exist
  only in a session scratchpad and will be lost with it; this is open item 4
  from the round 8 hand-off and is now two rounds old. Move them to
  `bench/calibration/` and add round 8's 96 cells from `round8.md`, including
  the six cells where Brandon overruled the judges, so any later judge change
  is re-scorable offline.
- Check (offline for the corpus, then billed for the judges): the corpus loads,
  every labelled cell names a real turn in a committed results directory, and
  `check_calib.py` scores a saved judge output and exits non-zero below the
  bar; the rubric change is re-scored over both rounds' cells and must not drop
  either judge below its round 8 figure (96.5% continuity, 95.6% fact).
- Caveat to keep stating: the rubric examples come from rounds 7 and 8, so
  these rates are optimistic for a new story. Per the standing rule that audits
  must generalise, do not tune further against continuity-initiative turns.

**R9-7. The semantic check, held behind a free offline bake-off (decide after
the round 9 run)**

If R9-2 does not hold for mechanism 1, the next strategy rank is an LLM
semantic check of the narrated turn, which is decision 1d and already approved
in principle. It must not be built or billed on faith:

- Rounds 7 and 8 give 96 saved turns with their GIVEN facts, their narration
  and Brandon's labels. Run the candidate check prompt over those records
  offline and measure it before any engine work or billed round.
- The round 3 caveat applies directly and is the thing being tested: a check on
  the same 8b model is the model grading its own error, which is exactly how
  the place normalisation failed. If the bake-off cannot separate r1 t3
  (narration contradicts GIVEN) from r1 t7 (narration consistent with GIVEN),
  do not build it.
- Only if it separates them: one check call per turn, and a second narration
  call only when a conflict fires, with a plain hint naming the thing and its
  place. Cost belongs in the decision, per principle 7.

**Round 9 as built (2026-09-21, branch `round9`, no billing spent yet)**

Batches 1 and 2 are merged into `round9` and the full suite is green at 654
tests. Brandon stopped the round after batch 2, before any billed run.

| Task | Commit | What landed |
|---|---|---|
| R9-4 + R9-5 | `1ceccf8` | owner-key resolution in the engine; capture asks for the end of the turn |
| R9-6a | `0fcf7ad` | the calibration corpus, in `bench/calibration/` |
| R9-1 | `71ea009` | the widened 12 + 6 script, park turn gone |
| R9-3 | `132914f` | the hand-over rule, the joined rule split |
| R9-2 | `194b19b` | each referred thing's place in the PLAYER block |

R9-4 and R9-5 were merged into one task rather than two, because both edit
`bench/item_facts.py` and two workers on one file collide on apply. They target
different mechanisms (6 and 8), so the round can still attribute them.

Two things worth knowing next session:

- The round 7 calibration labels were recovered from the round 8 session's
  scratchpad, which had not yet been cleaned. `bench/calibration/` now holds
  them, round 8's 96 cells derived from `round8.md` plus the six cells Brandon
  overruled, a `check_calib.py` that scores a saved judge output against either
  and exits non-zero below a bar, and a `rejudge.py`.
- R9-2's bench hook returns early unless the payload carries `scene_setting`.
  Every real turn does and a committed test pins the PLAYER block, but if that
  key ever leaves the turn payload the place lines would disappear silently
  rather than fail loudly.

**R9-6b, built but NOT applied.** The three judge rubric gaps were written and
verified offline (probe: the three sentences reach the rubric, no existing
sentence lost or reworded, node and python suites green) but the patch was not
committed, because Brandon stopped the round at batch 2. It is at
`scratchpad/out/task-r9f.patch` in session `57b1ddff`, which is session-scoped
and will be lost with it; the manifest beside it regenerates the work in about
five minutes if it is gone. The billed half of R9-6b - re-scoring both rounds'
cells with the changed rubric, which must not drop either judge below 96.5%
continuity or 95.6% fact - has NOT been run.

Nothing has been billed in round 9. The run itself (one smoke replicate, read
the transcripts, then two replicates into
`bench/results/item-facts-v10-two-scene-1a`, then the every-turn report) is
still ahead.

**Round 9 run (2026-09-21, billed, awaiting Brandon's comments)**

R9-6b was applied from the saved patch (`3b550e8`) and re-graded offline over
both rounds' labels. It first failed the round 7 fact floor (90.3% against
95.6%). Brandon chose to drop the fact rubric's "a thing is new" sentence and
to correct two round 8 label cells that contradicted his written comments
(r1 t4 is a restart; r2 t11 has no missed change), in `a9c63e7`. The checker
also learned to skip cells he left unlabelled (`8893b03`). A control re-grade
with round 8's own unchanged rubric then showed the floor itself was noise:

| Rubric | R7 continuity | R7 fact | R8 continuity | R8 fact |
|---|---|---|---|---|
| Round 8's, re-run today (control) | 95.6% | 92.0% | 97.9% | 97.0% |
| Round 9's (`a9c63e7`) | 98.2% | 92.9% | 97.9% | 95.8% |

So a single judge re-grade moves by three or four cells, and the round 8
figures (96.5%/95.6%) are one sample, not a floor. The round 9 rubric is
kept. Any later rubric gate should compare against a control run in the same
session, not against a remembered figure.

The smoke (`bench/results/item-facts-v10-smoke-two-scene-1a`, `75bebaf`) and
the two-replicate run (`bench/results/item-facts-v10-two-scene-1a`) completed
with 0 rejected turns. The judges report 21/36 turns with a real failure; the
round is scored by Brandon's comments in `bench/results/round9.md`, against
25/48 for round 8. First reading, before his review:

- Hand-over completes on r2 t15, the first time in three rounds.
- The GIVEN-place contradiction is not fixed: turn 3 still picks the phone up
  "from the floor" 2/2 after turn 1 put it in her hand.
- The laptop stays one thing 2/2; the owner-key resolver fired on r2 t5.
- End-of-turn capture held on r2 t10 (thrown and picked up in one turn).
- The hidden memory card is narrated inside the drawer 2/2 (round 8: 1/4).
- NEW, caused by R9-1: turn 12 "Carry Michelle's phone out to the truck."
  leaves the phone on the passenger seat 2/2, so 1B opens with the phone in
  the truck and turns 13, 15, 16 and 17 are set up to contradict. The
  replacement turn needs to keep the phone on Kristin (for example "Put
  Michelle's phone in your pocket and walk out to the truck.") before round
  10 can read the hand-over cleanly.
- Stalled one-sentence narration is the largest judge bucket
  (command_not_finished 12), mostly a single sentence that stops partway.

**Round 9 follow-up: why commands went unfinished (2026-09-21)**

Diagnosed from the round 9 records: every unfinished 1A turn narrated only the
first step of a two-step command (lifts the laptop, never carries it out).
Two changes, measured one live replicate and then two:

- `b5eb396` puts each referred thing's place BEFORE the command and drops
  "right now". One replicate (`item-facts-v11-reorder-two-scene-1a`): not a
  fix on its own. The model now obeys the given place firmly, so one stall
  (t4 leaves the laptop in the truck) cascades into t5, t6 and t9.
- `6507612` swaps the reply example's one-segment look ("She looks at the
  lantern. Its light has gone out.") for a finished two-step action in two
  segments. Two replicates (`item-facts-v12-example-two-scene-1a`), against
  round 9: one-sentence turns 14/36 -> 0/36, command_not_finished 12 -> 6,
  judge-failed turns 21 -> 18. No example words (lantern, porch, rail)
  leaked into narration. Of the 6 left, one is a dropped second step (r2 t4,
  never brings the laptop inside); the rest are the 1B man (t15 hand-over not
  shown taken once, t17 resisting twice, t18 silent twice).
- `8bc471a` saves each turn's narration system and user prompt in the bench
  records (`prompt_system`, `prompt_user`), so a turn can be read exactly.

- `21efd11` moves the 14 rules that are the same on every turn (and the
  opening's 11) out of the user CONSTRAINTS block into the system prompt,
  word for word, behind a bench flag; the shipped prompts are byte-identical.
  Two replicates (`item-facts-v13-sysrules-two-scene-1a`), against v12:
  judge-failed turns 18 -> 17 (a wash overall), command_not_finished 6 -> 3,
  restarts_scene 4 -> 1, contradicts_stated_fact 1 -> 4. Every 1A command
  finished in both replicates; the hand-over completed 2/2 for the first
  time; the three unfinished turns are all the 1B man (t17 resists 2/2, t18
  silent once). New slip, 2/2 on t16: "his cracked screen" for the phone.

- `d0f4211` makes the reply example flip a state ("She lights it. It glows."
  -> condition "lit"). Two replicates (`item-facts-v14-flip-two-scene-1a`),
  against v13: the drawer is captured open 2/2 and shut 2/2 (0/2 before,
  and 0/6 since round 9), but judge-failed turns rose 17 -> 21. The example's
  three-word sentences leaked into style (sentences of five words or fewer
  8% -> 17%), including one degenerate loop (r2 t12 "She gets in. She starts
  the engine. ... She drives back to the truck."). The laptop (0/2) and the
  chair (0/2) are still not captured, and the records show why: THINGS gives
  the drawer a current state ("shut") to flip, but gives the laptop no
  condition at all and does not track the chair, whose "overturned" state
  lives only in SCENE prose.

- `ef3f902` gives 1A's laptop a starting state (closed) and tracks the
  workstation chair (overturned), in plot.md and world.yaml, and rewrites the
  example with normal sentences. Two replicates
  (`item-facts-v15-states-two-scene-1a`), against v14: chair captured upright
  2/2 (0/2), drawer still 2/2, choppy sentences 17% -> 2%, missed_change
  13 -> 6, facts_after_wrong 13 -> 6; judge-failed turns 21 -> 20. The laptop
  is still never captured open, because turn 4's reply sends
  `"condition": []` and the engine takes an empty list as clearing "closed"
  (the same empty list drops the phone's "cracked screen" on r1 t3). The rise
  in contradicts (8) and restarts (7) sits almost entirely in 1B: r1 carried
  the phone to the truck on turn 12 (the known script defect), and both
  hand-over replies (t15) omitted item_facts, so the man's taking the phone
  was never recorded and t16-t17 contradict the stale facts.

- `97f22ba` (an empty condition list keeps a two-state thing's state),
  `d93bb3f` (turn 12 becomes "Put Michelle's phone in your pocket and walk
  out to the truck.") and `6dc19ac` (the splitter now splits compound
  commands carrying a possessive name, which spaCy's small model misparsed).
  Two replicates (`item-facts-v16-axis-two-scene-1a`), against v15: every
  scripted state change is now captured 2/2 (laptop kept closed on t4 and
  opened on t6, drawer, chair, phone pocketed on t12); restarts 7 -> 1,
  missed_change 6 -> 2; judge-failed turns 20 -> 20 as reported, but all 8
  kept_ended_condition labels are fact-judge false positives on records
  identical to v15's (AFTER is ["open"], the judge says "shut" was kept), so
  the real count is about 15. Still open: the hand-over reply omitted
  item_facts on t15 in all four replicates of v15 and v16; an empty list
  still wipes a non-axis condition (the phone's crack, 3 turns); the 1B man
  never answers or gives the phone back; t6 types Michelle's password into
  Kristin's laptop 2/2.

- `f5f1582` completes a narration reply that only lacks its closing
  brackets (a replay of the hand-over prompt, 12 samples, showed the model
  writes item_facts but omits the final brace in 5 of 12; the decoder's
  mid-word salvage then dropped item_facts). `8849944` anchors the fact
  judge's kept_ended_condition to the words in AFTER (re-grade of v16: 0
  false positives, against 1 for the old rubric re-run as a control, so the
  original 8 were mostly one noisy grading). Two replicates
  (`item-facts-v17-close-two-scene-1a`): omitted item_facts 2 -> 0,
  kept_ended_condition 8 -> 0, judge-failed turns 20 -> 18. The hand-over
  reply now arrives but says the phone is still "in Kristin's pocket" while
  the narration has the man take it (2/2, and 4 of 6 v16 replay samples):
  it copies the place line given just before the command. New judge false
  positives from the kept_ended wording: dropped_true_condition on four r2
  flips (shut -> open etc.), where the judge calls a replaced pole dropped.

What now leads is capture, not narration: the narrator's own reply reports
the drawer still "shut" after opening it (r1 t2), puts "open" in the drawer's
place (r2 t2), and never reports the laptop open (t6, 2/2).

**Order and exit for Round 9**

1. R9-1, R9-4, R9-5 in parallel Ringer tasks; each owns disjoint files. No
   billing.
2. R9-2 and R9-3 next, as separate tasks, because both touch prompt text and a
   combined patch cannot be attributed in the measurement.
3. R9-6's corpus move before the run, so the round 9 turns can be labelled into
   it straight away.
4. One smoke replicate, read the transcripts, then four replicates into
   `bench/results/item-facts-v10-two-scene-1a`, then the every-turn report with
   `bench/failure_report.py` for Brandon's comments.
5. R9-7's bake-off only after that run, and only on its result.

What the run answers: does the place in the PLAYER block cut mechanism 1 from
nine turns; does the concrete give-and-take rule complete the hand-over; does
the deterministic resolver keep the laptop as one thing; does removing the
impossible park turn leave any unfinished command that is really a narrator
defect.

Exit: the round 9 report is scored by Brandon's labels, not the judges' counts,
and compared against 25/48 on the same basis. Phase 0's exit criterion of 92%
per change type remains unmet and remains the gate; at 48% clean, round 9 is a
mechanism round, not the round that meets it.

**State at hand-off (2026-09-23) - START HERE**

*Where things stand.* Branch `round9`, tree clean, full suite green
(705 passed), ruff clean, nothing running, not merged to `main`. The last
measurement is v26 (the "v26" entry below). This session's commits, oldest
first:
- `6236d02`: a failed judge's reason is written into `summary.json`
  (`judge_failure_reason`, and each failure record is marked failed).
- `4473aae`: a narrator rule, "<owner>'s <thing> stores only <owner>'s
  things.", on the turn and opening paths; `_turn_rules` is built from
  named rule groups instead of slices.
- `5bad989`: one sentence splitter shared by the plain and masked paths.
- `20d3c90`: a reply naming both poles of an axis keeps the pole that
  differs from the state before the reply; an echo that leaves no condition
  changes none.
- `404ee5b`: beat details naming a world item that is not placed in the
  scene and not established are withheld from the narrator.
- `8368be4` (shipped runtime): a runtime-owned reveal's source beats reach
  the prompt only on the turn its handoff matches; the scene's opening beat
  is always sent; narrator-selected candidates are unchanged.
- `d9b70bf`, then `31b0a34`: the two-scene bench script and the story
  package now find the memory card (SL-1A-E, `k_sl_1a_b_r0`, "Look beneath
  the KMS drawer.") separately from reading it (`k_sl_1a_b_r1`, "Read the
  files on Michelle's memory card with my laptop."). ChatGPT authored this
  and Brandon approved it, including two phrase fixes: R0 owns "Michelle's
  card", "the card" and "hidden card".
- `d192126`: a `while_fact_true` placement guard (one helper shared by the
  runtime and the bench seed); on a matched reveal's turn, guards are judged
  as if that reveal's asserted facts already held; the bench starts
  tracking a placed thing the first time it becomes visible.

*Next steps, in order:*
1. DONE in `0117d51`, measured as v26 (the "v26" entry below): the copied
   example on reveal turns is gone. Reveal turns use the variation's
   example, and the default example is story-neutral.
2. DONE in `3c99b23` and `3253adb` (the "Judge story_text" entry below):
   the continuity judge reads only the narrator's prose plus story_text,
   and its remaining reveal-turn flags now cite the narrator's own
   sentences. Two real gaps the fact judge exposed stay open: the find
   reveal's text says the card "is taped beneath" but the story places it
   "with Kristin" (a story fix for the step 3 ChatGPT prompt), and changes
   that only story_text shows (the drive to the park) are never captured,
   because capture comes from the narrator's reply, written before the
   story text is appended.
3. DONE in `1b45b71` and `6ddd0b2`, measured as v27 (the "v27" entry
   below): the drawer's contents are authored, the frame no longer points
   at research, and the find reveal has Kristin take the card. Open from
   v27: the narrator re-enters the house or re-walks to the truck on the
   reveal turns (restarts_scene 7 cells), and once invents Michelle's
   laptop open with a "Confidential" folder at t13.
3a. PARTLY DONE in `d09db55`, measured as v28 (the "v28" entry below):
   the 1A scene frame described an arrival ("has reached the house ...
   not been searched yet") and is sent every turn; it now describes only
   the place. The t1/t2 re-approach is gone. Still open, with one cause:
   the narrator never learns where Kristin is or what the last turn did.
   So t13 still walks back into the house from the truck (1/2), and 1B
   t19 re-approaches "the watching man" (2/2). The candidate fix is to
   give the narrator the player character's place, or last turn's
   command, in PLAYER. That is a shipped runtime change and needs
   Brandon's go-ahead.
3b. DONE in `9eb2b1e`: the judges default to `gpt-5.6-luna`, for cost
   (see "Luna judge calibration" below). Tallies up to v27 are gpt-5.4's
   and are not comparable with v28 onward.
4. Phase 0's exit gate (92% per change type) is still unmet. Decide
   whether `round9` is merged to `main` before Phase 1's decisions.
5. Small review nits, none urgent. `_candidate_beats` reads
   `self._forced_beat_anchors` directly, so a provider built with
   `__new__` and given candidates would fail. `_turn_grounding_rule`
   misnames the "A character may only say..." rule. The splitter's
   `_drop_separator` keeps an unused no-map branch. `_mark_judge_failures`
   uses `setdefault`, so an explicit `failure_reason: None` would survive.
   Reveal-turn visibility and the bench's mid-scene tracking are covered
   only by the bench test and not by unit tests of their own.

*Story-package authoring rules.* The loader and tests enforce these. Every
ChatGPT story prompt must state them, because ChatGPT does not know them and
each one cost a round trip this session:
- Delivering any realization of a storylet fires the whole storylet
  (`state.py` `apply_proposal`), and a reveal is offered only while its
  storylet is active and not fired (`knowledge.py`). Two reveals that must
  both happen need separate storylets.
- A storylet no scene transition depends on is dropped after its
  `latest_turn`, and its `latest_turn` must be below the scene's
  `handoff_after_turns` (1A: 13). The scene's deadline ends it at that turn.
- Within a scene, storylet `target_turn`s must be unique and increase in
  file order; `earliest_turn <= target_turn <= handoff_after_turns`.
- A reveal realization without `source_beats` falls back to its
  storylet's `source_links`, and those beats are sent on its reveal turn.
- A reveal's `statement` must contain a phrase from every `must_convey`
  group (groups naming "under the drawer" are exempt).
- A multi-word `must_convey` phrase is owned by its knowledge. A scene's
  entry text and frame may use it only if the owner is established at that
  scene's entry, and narration naming it is rejected unless an owner is
  committed, the phrase is in a projected beat, or the turn's reveal text
  contains it. Dropping a phrase from every owner leaves it unguarded.
- `action_evidence`: one player sentence must hold a phrase from every
  group; phrases match as whole words, ignoring case, with no stemming;
  compound commands are split into sentences first; a sentence containing
  not/no/never/without/avoid/cannot/don't/do never matches. Exactly one
  candidate may match, or none is delivered.
- Story text changes go to ChatGPT Desktop with a self-contained prompt
  that states the relevant rules above. Apply its blocks verbatim, and
  check them against the loader before a worker applies them.

*How to run a measurement now.* The script is 19 turns: 13 in 1A (t1 open
the KMS drawer, t2 find the card, t3-t12 the old middle turns, t13 read the
card) then 6 in 1B. One Ringer task per run, `engine: codex`,
`model: gpt-5.6-luna`, `task_type: probe`, `full_access: true`,
`max_attempts: 1`, from the repo root:
`set -a; [ -f .env ] && . ./.env; set +a; TMPDIR=/tmp .venv/bin/python -m bench run --variation bench/variations/item-facts-package-two-scene.json --scene 1A --replicates 2 --script change-types --out bench/results/item-facts-v<N>-<name>-two-scene-1a --confirm`
Run `--replicates 1` into a `-smoke-` directory first and read it. The
check never calls a model. It asserts the replicate count, 19 turns each,
no rejected turns, both judgment files, no `judge_failure_reason`, and a
non-empty `prompt_user` containing "PLAYER:" on every turn. It then prints
the judge tallies and the t2/t6/t13 narrations. A run takes about 2 minutes
per replicate. Code changes go through a worktree Ringer task whose check
exports a patch; review the patch, then apply it and commit on `round9`.
Two gotchas:
- A fresh worktree's `uv run` can fail to download `en_core_web_sm` (TLS
  error), which fails a check that is otherwise fine. Confirm by applying
  the exported patch to the main checkout and running the probes and the
  suite with the main `.venv`.
- A worker told to make the suite pass may weaken a test or monkeypatch
  away the path under test (it happened in `31b0a34`'s first attempt).
  Review every changed assertion, and forbid both in the spec.

**State at hand-off (2026-09-22)** (superseded; kept for history)

*Round 9 review (2026-09-23).* Brandon's per-turn comments in
`bench/results/round9.md` (local only, not in git) score round 9 at 18/36 turns with a
real failure (50%), against 25/48 (52%) for round 8: flat. The judges agreed
with him on 31 of 36 turns; they missed r1 t3 and wrongly failed r2 t5,
r2 t14, r2 t17 and r2 t18. His rulings:
- The tracked place overrides the plot's authored place (t3, r2 t11).
  Already fixed by `b5eb396`: in v20b turn 3 takes the phone "from her hand"
  2/2.
- The chair was never given as overturned (t7): fixed by `ef3f902`.
- GIVEN must carry only what the command refers to, never everything tracked
  (r1 t13, r1 t18, r2 t16). His "objects in the scene or that Kristin is
  holding" was pushback on round 9 sending the whole store, not a widening of
  the 2026-09-16 rule. Measured on v20b: 34/36 turns sent only referred
  things; the leak was the match call over-listing on questions about people.
- The player character cannot control an NPC: a refusal, a struggle or
  silence finishes the command (r2 t17, r2 t18). The 1B man not answering or
  not giving the phone back is therefore not a narrator defect (see the open
  item below).

Acted on:
- `f122923` adds `bench/calibration/labels-round9.json` (the judge verdicts
  plus his eight overrules; three cells he did not rule on are unlabelled).
- `267c956` tells the continuity judge a refusal, struggle or silence
  finishes the command. Re-grade against a same-session control
  (`bench/results/probes/npc-rubric-regrade/`): continuity 99.1/99.0/93.0%
  -> 98.2/97.9/92.3% on rounds 7/8/9, fact 93.3/95.8/95.6% ->
  96.2/96.1/96.0%, all within the 3-5 cell noise. Round 9
  command_not_finished stays 31/35: r2 t18 is fixed, r2 t17 is not (the
  judge still wants to see whether she gets the phone back).
- `b2e6c96` fixes r2 t17: trying to take a thing from another character is
  her whole part, and the narration need not say whether she gets it.
  Re-grade against a same-session control
  (`bench/results/probes/take-attempt-regrade/`): r2 t17 goes yes -> no
  ("Trying to take it back is her whole part"); round 9
  command_not_finished 30/35 -> 32/35; rounds 7/8 command_not_finished
  unchanged at 21/22 and 48/48. Continuity 98.2/97.9/95.1% ->
  99.1/98.4/93.0%, fact 96.2/95.5/93.6% -> 95.2/97.3/95.6%. The round 9
  continuity dip is restarts_scene 35/36 -> 31/36, a rule the change does
  not touch; `267c956`'s own re-grade also scored it 31/36, so it is noise.
- `c643dea` tells the match call to list only the things the command names,
  and `b0fa318` resolves a shortened name ("laptop", "my laptop", "chair")
  to the one tracked name it means, because the narrower prompt made the
  model drop owners and exact-only matching then lost the thing. Live A/B
  (`bench/results/probes/match-overselect-ab.json`, 18 commands x 5
  samples, one late-game store): unrelated things on who-questions 5/10 ->
  0/10, named things kept 86/95 -> 95/95. Measured together in v21 below.

*v21 (2026-09-23, `bench/results/item-facts-v21-matchfix-two-scene-1a`,
every-turn report `bench/results/v21.md`, awaiting Brandon's comments).*
Built on three commits: `6236d02` writes a failed judge's reason into
`summary.json` (`judge_failure_reason`, and each failure record is marked
failed with it; v20b's own summary still shows the old silent failure);
`4473aae` adds one narrator sentence per owned thing after the owner rule
("Michelle's phone stores only Michelle's things. Kristin's laptop stores
only Kristin's things.", turn and opening paths) for the t6 password/tabs
defect, and builds `_turn_rules` from named groups instead of slicing;
`5bad989` shares one splitter between the plain and masked paths.
- t6 "Open my laptop." shows Kristin's own login or desktop 2/2 (v20b: 1/2
  drifted into Michelle's tabs).
- GIVEN carried only the named things on every turn; t14 got none, the
  who-questions only "man".
- Judge-failed turns 29/36 (v20b 24/36); leaving out
  protagonist_acts_beyond_command, 20/36 (v20b 16/36), inside this
  bench's noise.
- Two new faults, each identical word for word in both replicates, so
  effectively one sample each: t2's reply puts "open" in the drawer's place
  and keeps it shut (the known state_as_place fault; it cascades into t8,
  "shut an already shut drawer"), and t3's narration puts Michelle's hidden
  memory card on the desk (reveals_hidden_canon). Not attributed: t2 and
  t3's prompts differ from v20b only by the new owner sentence and the
  match-call changes, and no replay tool exists to A/B them.

*v22 (2026-09-23, `bench/results/item-facts-v22-drawerfix-two-scene-1a`
plus smoke `item-facts-v22-smoke-two-scene-1a`, 3 replicates in all).*
Brandon picked one fix per v21 fault: `20d3c90` keeps the narrated pole when
one reply names both poles of an axis (the echo of the pre-reply pole is
dropped; an echo that leaves no condition changes none); `404ee5b` drops any
beat detail that names a world item neither placed in the scene nor
established by committed knowledge, on the turn and opening paths.
- Drawer: captured open at t2 and shut at t8 in 3/3 (v21 0/2). v22 r2 t2
  sent v21's exact bad reply (`place: open`, `condition: [shut]`) and it
  landed as open, so the merge fix is confirmed live; the other two sent a
  clean reply.
- Card: never named in 1A narration, 0/3 (v21 2/2, one sample).
- New leak by the same look-ahead: the card's CONTENTS still reach SCENE as
  beat details that are not tracked items ("voice recording",
  "Continuity Initiative files"), and the narrator puts them on the desk
  (t3, 2/3) or on Kristin's laptop (t6/t9, 3 turns). The item filter
  cannot catch these; the next lever is projecting a beat's details only
  once the player's action reaches that beat.
- Judge-failed turns leaving out protagonist_acts_beyond_command: 18/36
  (v21 20/36), within noise.

*v23 (2026-09-23, `bench/results/item-facts-v23-beatgate-two-scene-1a`
plus smoke `item-facts-v23-smoke-two-scene-1a`).* Brandon approved gating
beats on the player's action: `8368be4` sends a runtime-owned reveal's
source beats only on the turn its handoff matches the player's input; the
scene's opening beat is still sent, narrator-selected candidates (1B) are
unchanged, and bench-forced beats are exempt. This change is in the
SHIPPED runtime (`_candidate_beats`).
- 1A SCENE carries no later-beat detail on any turn; 1A narration names
  none of the card's contents (v22: 7 turns across 2 replicates; the only
  hits left are "research notes" in the opened drawer, which the scene frame
  itself places there and no judge flagged).
- reveals_hidden_canon 0 (v22 1, v21 2); contradicts_stated_fact 2 (v22 7,
  v21 10).
- Drawer still open at t2 and shut at t8, 3/3.
- Judge-failed turns leaving out protagonist_acts_beyond_command: 13/36
  (v22 18/36, v21 20/36); smoke 5/18.
- Not yet exercised live: the reveal turn itself (no scripted command
  matches the card handoff's action evidence); the offline probe covers it.

*v24 (2026-09-23, `bench/results/item-facts-v24-cardturn-two-scene-1a`
plus smoke `item-facts-v24-smoke-two-scene-1a`).* `d9b70bf` appends 1A turn
13, "Read the saved files on the memory card.", which matches the card
reveal's action evidence; the script is now 13 + 6 turns, so totals are not
comparable with v10-v23. The reveal mechanism works live 3/3: t13 matches
handoff `k_sl_1a_b_r1` and beats 1A.2/1A.3 reach SCENE only on that turn.
1A->1B is no longer advanced offline, but scene 1A's deadline
(`handoff_after_turns: 13`) also falls on turn 13, so the run cannot show
whether the reveal or the deadline ended the scene; 1A holds at most 13
turns. The reveal TURN fails every judge 3/3:
- The narrator's own prose restarts the arrival at the house ("steps out of
  her truck and onto the cracked driveway") and never reads anything; once
  it put the card on the desk. Its prompt names the card only in PLAYER:
  no THINGS entry, no place, nothing saying the card was just found.
- `_compose_authored_handoff` then appends the authored delivery text
  verbatim: it narrates in past tense that the card "was taped under the
  drawer", and because the reveal now ends 1A, the 1A->1B `bridge_text`
  ("Kristin travels there while avoiding checkpoints ...") follows it, so
  the turn reads as a restart plus bolted-on exposition.
- The reply's item_facts are empty, so the card is never captured
  (missed_change); the judges also call the sanctioned reveal
  reveals_hidden_canon, a judge gap.
- Discoverability: the reveal's action evidence needs the player to say
  "memory card" or "the card", but nothing before the reveal tells the
  player a card exists, so the scripted command is one a real player could
  not know to type.

*v25 (2026-09-23, `bench/results/item-facts-v25-cardsplit-two-scene-1a`
plus smoke `item-facts-v25-smoke-two-scene-1a`).* The card is found and read
in two steps, authored with ChatGPT and approved by Brandon. `d192126` adds
the `while_fact_true` placement guard, and on a matched reveal's turn it
shows the things that reveal places. `31b0a34` adds storylet SL-1A-E: "Look
beneath the KMS drawer." (`k_sl_1a_b_r0`) sets custody and places the card
"with Kristin". SL-1A-B's reveals now need custody. R0 owns the card
phrases the old reveals owned, so the leak guard still stops the card being
named before it is found. The bench's 1A is now 13 turns (the scene
deadline): the find at t2, the read at t13, and the old opening "Look
carefully at Michelle's phone." is gone.
- Both reveals match live 3/3, the card is tracked "with Kristin" from t2,
  and 1A.2/1A.3 reach SCENE only at t13.
- t13 (read) no longer restarts the house arrival. In all 3 replicates
  Kristin walks to the truck, boots her laptop and inserts the card, then
  the authored reveal and the bridge follow. The judges still flag
  restarts_scene on 2/3 (walking back to the truck) and
  protagonist_acts_beyond_command.
- t2 (find): the narrator copied `DEFAULT_OUTPUT_EXAMPLE` word for word, 2/2
  in the full run ("The drawer sticks, then gives. Inside, under a curl of
  packing tape ..."). `_output_example()` forces that example on every
  authored-handoff turn, overriding the variation's lantern example, and its
  content is this story's own taped-under-the-drawer scene. That is a
  story-specific string in the shipped runtime, and on the find turn it
  becomes a template. Open item for Brandon.
- Judge-failed turns, leaving out protagonist_acts_beyond_command: 22/38
  (v24 18/38); smoke 9/19. t2's copied example accounts for part of the
  rise.

*v26 (2026-09-23, `bench/results/item-facts-v26-example-two-scene-1a` plus
smoke `item-facts-v26-smoke-two-scene-1a`).* `0117d51` (approved by
Brandon): reveal turns use the variation's own output example, like every
other turn; only the candidate-selection example stays off them.
`DEFAULT_OUTPUT_EXAMPLE` is now a story-neutral lantern example. The
handoff privacy test keeps its whole-prompt assertions, with a neutral
variant example.
- t2 (find): no copied example, 0/3 (v25 2/2). Every reveal-turn prompt
  carries the variation's example, so the find turn is also shown
  `item_facts`.
- New at t2, 3/3: the narrator opens the drawer and invents "a small piece
  of paper" (once with the message "They're watching."), captured as a
  tracked `paper` on the floor. This is next step 3's invented drawer
  contents moving to the find turn: the only source in the t2 prompt is
  the frame's "the places she kept her research". The judges flag t2 for
  invented_change, missed_change and reveals_hidden_canon.
- t13 (read) is unchanged from v25: the walk to the truck, then the
  authored reveal; restarts_scene 2/2 in the full run.
- Judge-failed turns, leaving out protagonist_acts_beyond_command: 13/38
  (v25 22/38); smoke 7/19 (v25 9/19). Two replicates are within judge noise
  of each other, so read this as "no worse" rather than a measured gain.

*Judge story_text (2026-09-23, `3c99b23`, re-grade of v26 in
`bench/results/probes/story-text-regrade/{ctl,new}`).* `bench/judge_input.py`
`judge_turns` builds the judges' view of each turn: `story_text` (the
reveal's `delivery_text`, then the scene's `bridge_text`, looked up by id)
and an `item_facts_before` without the things the turn's reveal made
visible (placements whose `while_fact_true` the reveal asserts). `bench run`
and `rejudge.py` both use it; saved records are unchanged. The continuity
rubric gains Brandon's approved sentence: story_text is canon, and never a
reason for contradicts_stated_fact, protagonist_acts_beyond_command,
restarts_scene or reveals_hidden_canon. The fact rubric is unchanged.
Same-session control (old judges) against new, both over the saved v26
records:
- Judge-failed turns leaving out protagonist_acts_beyond_command: 16/38
  both (the original v26 grading was 13/38, so the noise is 3 cells).
- Fixed: "given facts already place the card with Kristin" at t2 is gone;
  command_not_finished at t13 2 -> 0.
- Not fixed: r2 t2 is still reveals_hidden_canon, and r2 t13 still cites
  the bridge's drive to the park as restart and beyond-command. The rubric
  sentence does not hold reliably.
- Real, not judge error: r1 t13's narrator walks back to the truck she is
  already at; t2's invented paper (next step 3); the find reveal's text
  never says Kristin takes the card although the story places it with her.
- The fact judge now flags the bridge's drive to the park as an uncaptured
  change (missed_change 8 -> 11).
- `3253adb` (approved by Brandon): the sentence did not hold, so the
  continuity judge now reads `narrator_narration`, the narration minus the
  exact story_text suffix (left whole if it is not an exact suffix), with
  story_text sent as its own field. The rubric sentence now reads:
  story_text is not part of narration, is canon, and is used only for
  command_not_finished and what is true after the turn. The fact judge
  keeps the full narration. Re-grade in `.../story-text-regrade/strip`:
  16/38 again, but every t2/t13 continuity flag now cites the narrator's
  own prose. The drawer paper put in the card's hidden spot is
  reveals_hidden_canon 2/2. The re-walk to the truck is r1 t13 restart.
  No flag cites the bridge or the reveal text any more.

*v32 (2026-09-24, `bench/results/item-facts-v32-stranger-two-scene-1a` plus
smoke `item-facts-v32-smoke-two-scene-1a`).* Two changes:
- `144caf5` renames the 1B beat detail "watching man" to "stranger in the
  park".
- `d2dd943` has Jev ask the protagonist "leaving the room <Name> was in"
  (Brandon's wording, with the name for "she").

Read by hand over 3 replicates:
- 1B t19 "approaches the stranger": 3/3, and t18 3/3. The rename hypothesis
  is falsified. The narrator copies whatever the man is called and still
  opens with "approaches", even when her tracked place is "near the
  stranger". Neither a rule nor a rename reaches it.
- t13: no walk back into the house, 3/3. The smoke invents a drive to a
  coffee shop (1/3); both replicates read the card where she is.
- Her place capture still misses t4, t9 and t13 in nearly every replicate.
- Smoke t17 ("Check who has Michelle's phone now.") narrates only the
  pacing line "The pursuers are closing in through the park." That is
  unrelated to this change; watch for it.

*v31 (2026-09-24, `bench/results/item-facts-v31-startrule-two-scene-1a` plus
smoke `item-facts-v31-smoke-two-scene-1a`).* `89b1c68` adds, on turns only,
"Kristin starts this turn at the place PLAYER gives. Do not have Kristin walk
there again." The protagonist sentence is now gender-neutral. The Jev fact
judge asks the protagonist "changing locations", not "moving". Read by hand
over 3 replicates:
- t13 walk back into the house: 0/3 (v30 1/3, v28 1/2). But 2/3 instead
  invent a drive "to a nearby parking lot" before reading, which is not a
  restart.
- 1B t19 "approaches the watching man": 3/3, and t18 "approaches" 3/3. The
  rule does not reach it. A likely mechanism: the 1B beat detail "watching
  man" is sent every turn, and her tracked place reads "near the watching
  man". The narration copies that exact phrase, "approaches the watching
  man". This is authored story text, so a rename is a ChatGPT story task.
- Her place capture still misses real moves: t4 (out to the truck and back),
  t9 (carries the laptop to the truck) and t13 (drives off), 3/3 each.
- Jev's location question no longer fires on small steps inside a room (the
  v30 t6 false alarms are gone). Its remaining Kristin flags match those
  real misses.

*v30 (2026-09-24, `bench/results/item-facts-v30-kristin-two-scene-1a` plus
smoke `item-facts-v30-smoke-two-scene-1a`).* `22a057b`: the bench now tracks
the protagonist like a thing. She is seeded at "in <scene location>", given
in THINGS and PLAYER every turn (Brandon approved this one exception to the
refers-only rule), moved by the narrator's own item_facts reply, and reset at
the scene change. One rule sentence asks the narrator to report her new
place. Judge spend: 4 OpenAI calls and 97 Jev requests. Read by hand over
all 3 replicates:
- t13 walk back into the house: 1/3 (r1). Its prompt said "Kristin is in
  the truck" and the laptop was "on the passenger seat", and it still walked
  her into the house. v28: 1/2. The given place alone does not stop it.
- 1B t19 "approaches the man": 2/3 (both v30 replicates; the smoke said
  "stands near"), even with "Kristin is near the man watching her" given.
  t18 opens with "approaches" 3/3.
- Capture of her place works but misses real moves. She walks into the
  kitchen (smoke t3), carries the laptop to the truck but is left "in
  Michelle's house" or "in the kitchen" (t9, 3/3), and drives off (smoke
  t13). A stale place then fails later turns under the whole-state bar.
- Jev's `moved` answer for Kristin sits at 0.51-0.55 on small steps inside
  a room, which adds missed_change false alarms.
- Follow-up: the rule sentence says "the place she is". That assumes a
  female protagonist; make it gender-neutral before any runtime version.

Next, by Brandon's ranking (a rule first, then an LLM check):
- a plain rule that she starts the turn where PLAYER says, so she is not
  walked there again;
- check whether beat details sent on t13 ("someone entering house") pull
  her back inside.

*v29 (2026-09-24, `bench/results/item-facts-v29-jevfacts-two-scene-1a` plus
smoke `item-facts-v29-smoke-two-scene-1a`).* This is the first run with the
fact judge on Jev (`35f2de9`; see `.plans/jev-judge-trial.md`); continuity
is still judged by Luna. The narration code is the same as v28. Judge
spend: 4 OpenAI calls and 58 Jev requests. Read by hand:
- t13: both replicates read the card at the truck. Neither walks back into
  the house (v28: 1/2). The same code gave a different sample, so this is
  noise, not a fix.
- 1B t19: "approaches the watching man" 2/2 again. Luna did not flag it,
  the same miss it made in v28.
- t2: the invented paper under the drawer, 3/3 including the smoke.
- Luna's continuity flags include r1 t4 restarts_scene, where "bring my
  laptop inside" was the command. Luna made the same false alarm in v28.
- Jev's fact flags: t9 "closed" was invented 2/2 (context only). t6
  `narration_contradicts_given_facts` fired 2/2 on "walks over to Michelle's
  workstation and opens her laptop" (before_conflict 0.68-0.70). That looks
  like a Jev false alarm near threshold. r1 t13 missed the laptop being
  opened. That one is correct.

*v28 (2026-09-24, `bench/results/item-facts-v28-frame-two-scene-1a` plus
smoke `item-facts-v28-smoke-two-scene-1a`, first run judged by Luna).*
`d09db55` replaces the 1A frame with "Michelle's home is otherwise
untouched, but its back door frame shows recent damage. Michelle is
missing, and her tablet and work bag are gone. A drawer on Michelle's
workstation has Kristin's initials, KMS, newly carved into it."
(ChatGPT-authored, Brandon-approved; "forced entry" is a guarded phrase
of `k_sl_1a_a_r1` and cannot appear in a frame). Six variations lost a
dead replacement that patched the old frame's phone sentence. Read by
hand, since the judge changed:
- t2: no re-approach and no re-opened drawer, 3/3 including the smoke
  (v27: r2 t1 and t2 re-walked to the desk).
- t13: walks back into the house from the truck 1/2 (r1) and reads the
  card at the workstation; the prompt carries no arrival text, and
  nothing in it says Kristin is at the truck. r2 reads it in the truck.
- 1B t19: "approaches the watching man" 2/2 after two turns of talking.
- The invented paper under the drawer is back at t2, 3/3 including
  the smoke (v26 and v27: 0/3). An invented password prompt appears at
  t6, 3/3.
- Luna judge: 13/38 turns with a failed cell. It flagged r1 t4
  (commanded "bring my laptop inside") as restarts_scene and let the t2
  paper through.

*Luna judge calibration (2026-09-24,
`bench/results/probes/luna-calibration/r7`-`r9`).* `rejudge.py` plus
`check_calib.py` on HEAD `d09db55`, against the round 7-9 labels:

| Round | Continuity | Fact |
|---|---|---|
| r7 | 111/114 = 97.4% | 91/105 = 86.7% |
| r8 | 184/192 = 95.8% | 315/336 = 93.8% |
| r9 | 132/142 = 93.0% | 236/251 = 94.0% |
| total | 427/448 = 95.3% | 642/692 = 92.8% |

The closest gpt-5.4 scores are `probes/take-attempt-regrade/new`: 96.9%
continuity and 96.4% fact overall, on an older rubric (before `3c99b23`
and `3253adb`), so this is not a same-rubric control. Luna's repeated
misses: `narration_contradicts_given_facts` on the t3 pocket turn (every
replicate of r7, plus r8 and r9); a "crumpled" receipt condition called
invented in r7 t10 (4 replicates); and restarts_scene misses in r9 1B.
Brandon chose Luna for cost, so these are fixed through the rubric and
the labels, not by changing the model.

*v27 (2026-09-23, `bench/results/item-facts-v27-drawer-two-scene-1a` plus
smoke `item-facts-v27-smoke-two-scene-1a`).* `1b45b71` (ChatGPT-authored,
Brandon-approved, applied verbatim): a 1A setting fact "The drawer holds
pens, binder clips, a stapler, and spare batteries.", the frame's last
sentence is now "Michelle's work area has not been searched yet. The KMS
drawer is worth a look.", and the find delivery_text is "Kristin finds
Michelle's memory card taped beneath the KMS drawer. She takes it with
her." The smoke run showed the bench never sent that setting fact:
`ItemFactsProvider` sends setting facts only as tracked THINGS, and it
cannot parse a contents sentence. `6ddd0b2` makes the seed parser report
the setting facts it did not track, and the bench sends exactly those as
text, as production does. The full run is on `6ddd0b2`.
- t1 (open the drawer): no invented research, 2/2 (v23 research notes 3/3).
  One replicate names exactly the authored contents; the other says
  "revealing the contents inside".
- t2 (find): no invented paper, 3/3 including the smoke (v26 3/3). The
  card is tracked "with Kristin" after the find.
- New: restarts_scene 7 cells. The narrator re-approaches the workstation
  or re-enters the house at t2 and t13, and r2 t13 walks back from the
  truck into the house. r1 t13 invents Michelle's laptop open on the desk
  with a "Confidential" folder.
- Judge-failed turns leaving out protagonist_acts_beyond_command: 15/38
  (v26 13/38, within noise).

Branch `round9` at `31b0a34`, tree clean, full suite green, nothing running.
Not merged to `main`. Every measurement below is two live replicates of the
18-turn two-scene script (`bench/variations/item-facts-package-two-scene.json`,
12 turns in 1A then 6 in 1B), each run in `bench/results/item-facts-v<N>-*`,
and every turn record now saves its exact narration prompts
(`prompt_system`, `prompt_user`).

*Both decisions below were RESOLVED on 2026-09-22 in `faa01dd` (option 1 and
the proposed rubric sentence) and measured as v18
(`bench/results/item-facts-v18-handover-two-scene-1a`):*
- Hand-over: t15's reply now gives the phone "in the man's hand" 2/2 (v17:
  "in Kristin's pocket" 2/2). No choppy-prose leak seen in t15.
- v18 fact judge: 7/36 turns with a failed cell (v17: 12/36, same script,
  new rubric vs old, so part of that drop is the rubric). Continuity:
  21/36 including protagonist_acts_beyond_command (v17: 24/36). New in
  v18: restarts_scene 2 (r1 t18, r2 t12) and the chair called "empty"
  while canon says overturned (t5, 2/2).
- Re-grade with a same-session control (old rubric from `5b54d85`),
  `bench/results/probes/dropped-opposite-regrade.md`: dropped_true_condition
  yes on v17 fell 9 -> 1 turns; round 8 dropped_true_condition 43/48 ->
  47/48, fact judge 95.2% -> 96.4%; round 7 fact judge 95.2% -> 94.3%
  (invented_change only, which the change does not touch - noise). The
  unchanged continuity judge moved 3 cells on round 8, the noise floor.

*Decision 1 (resolved, see above): the hand-over reply copies the place it was given.*
Since `f5f1582` the hand-over turn (t15, "Walk over to the man watching you.
Hand him Michelle's phone.") no longer loses its item_facts. The reply now
arrives, but in v17 it says the phone is still "in Kristin's pocket" while
the narration says "The man takes the phone" (2/2), and the replay in
`bench/results/probes/handover-t15-replay.json` shows the same in 4 of 6 v16
samples. The reply copies the place line written just before the command
("- Michelle's phone is in Kristin's pocket."), which R9-2 added to stop
narration contradicting where things are. Options, all inside the single
narration call (a second capture call is ruled out by Brandon):
  1. Add a hand-over to the reply example (recommended): the example's
     lantern ends up taken by someone, and its reply place is that person's
     hand. The reply example is the lever that has moved this model every
     time (one-sentence turns 14/36 -> 0/36, state flips 0/2 -> 2/2), and it
     teaches with material rather than a rule. Watch style leakage: the v14
     example's three-word sentences doubled choppy prose until v15 fixed it.
  2. Take the place line out of the PLAYER block and keep it in THINGS only.
     Simpler, but may bring back the pick-up-source contradictions R9-2 was
     for.
  3. A short narrator rule such as "When someone takes a thing, give that
     person's hand as its place." First in Brandon's ranking, but examples
     have beaten rules on this model so far.

*Decision 2 (resolved, see above): a fact-judge false positive introduced by `8849944`.*
The new kept_ended_condition wording ("read ... word for word") leaked into
dropped_true_condition: on four r2 flips in v17 (drawer shut -> open, laptop
closed -> open, chair overturned -> upright, drawer open -> shut) the judge
says the old state was "dropped rather than ended", though the new state
correctly replaced it. Proposed fix: one rubric sentence in
`bench/fact-tracking-judge.mjs`, under dropped_true_condition, saying a
condition replaced by its opposite (shut becoming open) is not dropped. Then
re-grade v17 offline, plus both labelled rounds, with a same-session control
(see the note on judge noise below).

*Player input is now first person* (`2a60d30`): the scripted commands said
"your laptop" and "your truck", a game master's voice; they now say "my
laptop" and "the truck". This changes the 1A/1B scripts, so v20 and later are
not strictly comparable with v18/v19. Measured as v20b
(`bench/results/item-facts-v20b-firstperson-two-scene-1a`): hand-over still
gives "in the man's hand" 2/2; fact judge 9/36 turns with a failed cell
(v18 7/36, v19 13/36 - inside this bench's noise); continuity 23/36
including protagonist_acts_beyond_command. "Open my laptop." made t6 better
in one run of two: Kristin now types her OWN password, where "Open your
laptop." typed Michelle's 2/2. The other run still drifts into Michelle's
tabs, so the t6 item below stands.

*The bench hides a judge failure*: when the OpenAI account ran out of
credits, three runs narrated all their turns and then died in the judge
stage, and `summary.json` recorded `failed_replicates` with `status: "ok"`
and `failure_reason: null` - the HTTP 429 text went only to stdout. The
judge's failure reason should be written into the summary. Two unjudged
runs from that outage (`item-facts-v20-firstperson-two-scene-1a` and
`item-facts-v20c-diag-two-scene-1a`) are left in `bench/results/` untracked;
they hold usable 1A turn records and can be judged offline with
`bench/calibration/rejudge.py`, or deleted.

*Other open items, in rough order:*
- RESOLVED in `29aca63`: an empty condition list wiped the phone's crack
  (every loss in v15-v18 was a `condition: []` reply). An empty list is now
  no condition change at all. v19 (`item-facts-v19-emptykeep-two-scene-1a`)
  lost no phone condition, but the model sent no empty list for the phone
  that run, so the unit tests are the evidence the path works.
- RESOLVED in `fdb2547`: dropped_true_condition fired when the
  phone's damage was split, merged, reworded or made worse ("cracked in two,
  shattered" vs "cracked in two", "shattered"), leaked from
  kept_ended_condition's "word for word". That sentence is now scoped to
  kept_ended_condition, and dropped_true_condition compares meaning. Re-grade
  against a same-session control (`bench/results/probes/dropped-meaning-regrade/`):
  the three split/merge cells (v19 r2 t11, r2 t15; round 8 r3 t12) went to
  0. The real drops from before `29aca63` (v16 r1 t3, r1 t17, r2 t17; v17 r2
  t3) are still caught, and kept_ended_condition stays 0 everywhere. Fact
  agreement went 96.2/95.5/94.8% -> 93.3/95.2/96.0% on rounds 7/8/9. The
  round 7 dip is invented_change on the "crumpled" receipt, which the change
  does not touch. One new wrong cell: round 9 r1 t2 (drawer opened, reply put
  "open" in the place), which the control also flagged on r2 t2. The
  control graded v19 at 2 dropped cells, not the original 5, so part of the
  original 5 was one noisy grading.
- The 1B man never answers "Ask the man who he is." and resists "Take
  Michelle's phone back from the man." (t17, t18, every run). Brandon ruled
  this is not a narrator failure (she cannot control him), so it is no longer
  a defect to fix. Whether he should ever have something to say is the
  parked C1 story question: excluding `source.kind: scene_entry` knowledge
  from NPC sayable lines leaves him nothing to say.
- t6 "Open your laptop." types Michelle's password into Kristin's laptop 2/2
  (invented detail).
- Two code nits from review: `storygame/runtime/command_split.py` duplicates
  `_split_sentence` as `_split_masked_sentence` instead of sharing it with an
  offset map; `_turn_rules` in `storygame/runtime/cloudflare.py` rebuilds its
  rule list by slicing `_constant_turn_rules()` at fixed positions.

*What changed in the SHIPPED game this session* (everything else is
bench-only): `plot.md`/`world.yaml` 1A now track the workstation chair
(overturned) and say the laptop starts closed (`ef3f902`, Brandon's ruling);
the compound-command splitter handles possessive names (`6dc19ac`); a reply
missing only its closing brackets is completed instead of truncated
(`f5f1582`); `CloudflareTurnProvider` gained helper methods and a no-op
`_system_rules` hook with byte-identical prompts (`21efd11`).

*Where the numbers stand* (judge-failed turns of 36; the judges are a guide,
not the score):

| Run | Change | Failed | Note |
|---|---|---|---|
| v10 (round 9) | R9-1..R9-5 | 21 | 12 command_not_finished |
| v12 | two-step reply example | 18 | one-sentence turns 14 -> 0 |
| v13 | constant rules into system prompt | 17 | every 1A command finished; hand-over 2/2 |
| v14 | example flips a state | 21 | drawer captured; choppy prose 17% |
| v15 | laptop/chair starting states, smoother example | 20 | chair captured; choppy 2% |
| v16 | two-state keep, turn 12, splitter | 20 (~15 real) | every scripted state change captured 2/2 |
| v17 | complete unclosed replies, kept_ended rubric | 18 | omitted item_facts 0; hand-over echo; new judge FP |

*Judge noise, measured this session:* a single re-grade of the same records
moves by 3-5 cells, and the old rubric re-run as a control scored 95.6%/92.0%
on round 7 where a remembered figure was 96.5%/95.6%. Gate any rubric change
against a control run in the same session, never against a remembered
figure. Round 7's 8 "laptop invented closed" cells are superseded
(`5b54d85`) now that canon says it starts closed.

*How to run a live measurement* (the session's manifests lived in a
scratchpad and are gone). One Ringer task per run, `engine: codex`,
`model: gpt-5.6-luna`, `task_type: probe`, `full_access: true`,
`max_attempts: 1`; the worker runs exactly once, from the repo root:
`set -a; [ -f .env ] && . ./.env; set +a; TMPDIR=/tmp .venv/bin/python -m bench run --variation bench/variations/item-facts-package-two-scene.json --scene 1A --replicates 2 --script change-types --out bench/results/item-facts-v18-<name>-two-scene-1a --confirm`
The check never calls a model: it asserts 2 replicates with 18 turns each,
no rejected turns, both judgment files present, and a non-empty
`prompt_user` containing "PLAYER:" on every turn, and prints the judge
tallies. Code changes go through a separate worktree Ringer task whose check
exports a patch; review it, then apply and commit on `round9` before the
live run. Re-grading saved records offline:
`bench/calibration/rejudge.py --results <dir> --out <dir>` then
`bench/calibration/check_calib.py --labels bench/calibration/labels-round{7,8}.json --judgments <dir> --records <results>/all-turn-records.json`.

*This session's commits on `round9`, oldest first:* `3b550e8` `8893b03`
`75bebaf` `a9c63e7` `bfeccdb` (round 9 run and report), `b5eb396` `8bc471a`
`f3b6882` (place line before the command; prompts saved), `6507612` `5035bb8`
(two-step example), `21efd11` `21fc17b` (rules to system prompt), `d0f4211`
`ad29804` (state-flip example), `ef3f902` `c54911f` (laptop/chair states),
`97f22ba` `d93bb3f` `6dc19ac` `8768a8a` (two-state keep, turn 12, splitter),
`8849944` `f5f1582` `b10e595` (kept_ended rubric, unclosed replies), `5b54d85`
(superseded labels).

**State at hand-off (2026-09-19)**

`main` at `38bf187`, nothing running, tree clean, full suite green (649
tests). Round 8 reached main through PR #469 (`narration-phone-fixes`) and PR
#470 (`narrated-beat`, Brandon's 2B.2 writing fix plus a stale-beat test
revision); round 7's smoke directory is now committed.

Round 8 commits, oldest first:

| Commit | What |
|---|---|
| `2604417` | Round 7 results, the every-turn report with Brandon's comments, `bench/failure_report.py` changes |
| `7fda86a` | Brandon's `plot.md` wording "KMS initials carved in drawer"; the round 8 plan |
| `cd33b32` | Judge faults 1-5: per-scene canon, `given_facts` per turn, refinement rule, fact-judge scope, `command_not_finished` and `reveals_hidden_canon` |
| `e3dec65` | B1 no "closed or open" offer in THINGS; B4 a reply with no `item_facts` means no change |
| `dafcc77` | A: the owner rule names only visible placed items (the hidden memory card no longer reaches the narrator) |
| `c7ec63f` | C1(a): `source_beats` per realization, loader fails closed, `_candidate_beats` drops the word-overlap gate |
| `2b8d6b3` | The bench test is hermetic; four judge rubric points from Brandon's label rulings |
| `a5df264` | B2, B3, C2 prompt changes |
| `5ce8de0`, `17ccf84`, `45f431a` | This plan |

Open items, in the order to pick them up:

1. ~~**Billed measurement of round 8.**~~ DONE 2026-09-21 at `4dc062d`:
   resmoke then four replicates in `bench/results/item-facts-v9-two-scene-1a`,
   written up as `bench/results/round8.md` with Brandon's comments and scored
   in "Round 9" above. The next billed run is Round 9's, which needs Brandon's
   go-ahead. Rebuild its manifests the same way. Smoke one replicate, read it,
   then four. The round 8 manifests were written
   and linted but live in the session scratchpad
   (`.../scratchpad/r8/manifest_smoke.json`, `manifest_round8.json`, check
   `check_bench.py`); if the scratchpad is gone, rebuild them from the round 7
   live task recorded in `~/.ringer/runs/freytag-round7-live-*.json`
   (`full_access: true`, `max_attempts: 1`, one bench command run exactly once,
   the check reads the artifacts and never calls a model). The command:
   `set -a; [ -f .env ] && . ./.env; set +a; TMPDIR=/tmp .venv/bin/python -m bench run --variation bench/variations/item-facts-package-two-scene.json --scene 1A --replicates 4 --script change-types --out bench/results/item-facts-v9-two-scene-1a --confirm`
   Questions it answers: is the invented USB drive gone from the drawer now
   that the card is not named in the prompt (Brandon: the only drive in the
   story is the one taped beneath the drawer, so an invented one is a failure);
   does the narrator still invent a pick-up source; does the laptop still
   arrive `closed`; is the hand-over completed; does the 1B bench still invent
   a receipt now that beat 1B.1 reaches the prompt. Then build the round 8
   report with `bench/failure_report.py` and put Brandon's comments in it as in
   round 7.
2. ~~**Beat 2B.2 "Kristin Was Bait" reaches no realization.**~~ DONE by
   Brandon in ChatGPT Desktop, merged as PR #470 (`5407346`). SL-2B-B gained a
   third realization SL-2B-B-R3 with
   `source_beats: [scene-2b2--kristin-was-bait]`, asserting a new fact
   `kristin_was_bait` declared in `world.yaml`, `knowledge.yaml` and the
   route file's `new_fact_ids`; knowledge record `k_sl_2b_b_r3` is modelled on
   `k_sl_2b_b_r1` and gated on `janus_evidence`; the storylet's completion
   became `any_fact_true: [brandon_janus_role_known, kristin_was_bait]`, so
   either revelation can complete it; `storylets.md` gained the matching
   realization and effect lines. Verified: the package loads, every beat of
   every storylet is now linked by some realization (none orphaned), and the
   full suite passes.
3. ~~**Merge Ringer's `check-timeout-override`.**~~ DONE 2026-09-19: merged to
   the local Ringer main (`6b3f85e`), README credit added for the project's
   contributor rule (`d368115`), 269 tests pass, and a proof run confirmed a
   check may now sleep 75 seconds. AGENTS.md and the working rule above now
   describe `check_timeout_s`. Not pushed: `origin` is
   NateBJones-Projects/ringer, so upstreaming it is a PR Brandon opens.
4. **Carry the judge calibration into the repo.** (Now Round 9 task R9-6,
   which also adds round 8's cells and the three judge gaps Brandon caught by
   hand.) Brandon's round 7 rulings are
   encoded as labels (114 continuity cells, 113 fact cells) in the session
   scratchpad, with `check_calib.py` (scores judge output against them and
   fails below a bar) and `rejudge.py` (re-runs both judges over saved turn
   records, 8 billed calls). They are not in git and will be lost with the
   scratchpad. A Ringer task should move them to `bench/calibration/` so any
   later judge change can be re-scored. The rulings themselves, in case the
   labels must be rebuilt from `bench/results/round7.md`: a look command is
   finished whether or not Kristin picks the thing up; an invented USB drive in
   the drawer is `reveals_hidden_canon`; a condition the narration never showed
   is invented; an attempted hand-over nobody takes changes nothing; a more
   specific place or state inside the given one is consistent; world facts
   override canon and earlier commands.
5. **Round 9** (above), then **Phase 1**, whose decisions are still open: 1a (story-break status and
   declared axes), 1b, 1d, 1e (containment tree, including the
   `{"kitchen counter": {"contents": [...]}}` replies still dropped). 1c is
   decided. Phase 0's exit criterion - every change type at 92% - is still
   unmet, and the round 8 run is the next measurement against it.

Round 8 defects that are fixed in code but NOT yet confirmed live: the USB
drive and memory card in the drawer, the invented pick-up source, the invented
`closed`, the flattened "broken", the unfinished commands, and the invented
receipt at the bench. Only the billed run can confirm any of them, and the
replicates are highly correlated, so treat a 4-replicate move as weak evidence.

Two C1 findings were investigated but NOT fixed, and neither has been decided:
stale 1A material in the 1B prompt (1A's entry statement and a 1A complication
rendered as "This happens now"), and scene-entry knowledge becoming NPC speech
(`k_scene_1b_entry` is public, so Brandon's only permitted line is the scene
frame; candidate fix is to exclude `source.kind: scene_entry` from NPC sayable
lines).

Operational lessons from round 1 (apply to every live run):
- Put `"max_attempts": 1` on any Ringer task that runs a billed bench. A failed
  check otherwise retries and reruns the whole spend. Lint does not flag an
  unknown field such as `"retries"`.
- A burst of judge failures can be an exhausted OpenAI balance (HTTP 429
  `insufficient_quota` / `credit_balance_exhausted`), not a rate limit.
  Diagnose it with one request before rerunning.
- After each run, keep only successful non-smoke rows in
  `bench/results/ledger.jsonl`.
- Change type comes from the scripted command, never from narration. Map each
  script input to a type and count the fact-tracking judge's verdicts per type.
- A check that runs a single pytest file must pass `--no-cov`; the repo's 90%
  coverage gate fails otherwise.
- Checks that stub `_request` must count their own stub calls, because the
  base provider's `request_count` increments inside `_request`.
- Write briefs and scripts with QUOTED heredocs (`<<'EOF'`). An unquoted
  heredoc ran backtick-quoted commands inside a brief (`uv add spacy`) against
  the real repository; it had to be reverted with git checkout and uv sync.
- Never wait on a run with `pgrep -f <manifest name>` from a shell whose own
  command line contains that name; it matches itself and never exits.
- A judge's verdict `turn` field was positional before 4e27f99; older result
  files must be matched to turns by position, never by that number.
- `git add -A -- . ':(exclude).venv'` fails when `.venv` is gitignored; use
  plain `git add -A`.
- The bench's `ItemFactsProvider._request` sits between the HTTP call and
  proposal validation, so structural reply fixes for the bench go there and
  shipped-provider fixes go in `CloudflareTurnProvider._request`.

### Phase 1 - Design decisions

**Why.** Three questions must be settled before engine code. Present options to
Brandon with the Phase 0 evidence; do not build until decided.

**1a. Story-break status.** Recommended: add a closed `status` per tracked thing
- `intact`, `destroyed`, `lost`, `carried` - alongside free-text `place` and
`condition`. The engine maps `destroyed` and `lost` to the `destroyed` predicate
the dependency analysis already reads (add `lost` as its own predicate only if the
story needs to tell them apart). Alternatives: an LLM judgement per change to a
dependency-bearing thing (principle 4, second rank); package-declared breaking
words (brittle, last). Decide also which things carry dependencies beyond
transition `required_dependencies` (for example reveal sources).

**1a candidate: declared state axes** (added 2026-09-16, from the `supersede()` /
single-valued-fact idea on MemPalace's knowledge-graph page; Brandon asked for it
to be recorded here). A package declares, per tracked item, one or more sets of
mutually exclusive state values - `open|closed` for a drawer, `damaged|not
damaged` for the phone. Two engine consequences, both deterministic and free of
model calls:

- A captured condition on an axis **supersedes** the other value on that axis
  instead of accumulating. This is the kept-ended-condition class: `shut`
  surviving after the drawer is opened, 12 of 155 turns in the round-3 40-turn
  run.
- A captured `place` whose text exactly equals a declared state value for that
  thing is recorded as that thing's **condition**, not its place. This is the
  "Close the drawer." -> `{"place": "closed"}` case, the single defect that cost
  three of four replicates most of their score.

If both hold, this **replaces** the match-call place normalisation rather than
adding to it. That normalisation is measured: of three corrections in one live
replicate, one was right (the drawer) and two destroyed correct locations
(Michelle's phone at "on the kitchen counter" judged a state), and it costs about
0.9 extra model calls per turn.

Relation to the `status` proposal above: `status` is itself one such axis, so
declared axes generalise it; decide whether `status` stays a separate closed
field or becomes the reserved axis every item has.

**Measured in the bench (round 4, f461739):** declared axes were built into the
item-facts harness with the declaration in the variation rather than the package
schema. Brandon settled three points during the build: an axis is exactly two
opposite poles with aliases, never a list; an axis value occupies a slot of its
own and evicts only its opposite, because "lit" is not the opposite of "open";
and an empty condition list clears the axis value, so a state reads unknown
rather than stale. Results above.

**Open, not decided:**
- Whether a NON-empty condition reply that names no pole should also clear the
  axis value. Today it preserves it, which is deliberate but asymmetric with the
  empty-list rule.
- Matching a returned field against an authored closed vocabulary is lexical.
  It is not the thing principle 4 rules out - that is scanning free-form
  narration prose - but it is adjacent, and Brandon has not ruled on it.
- Where axes are declared (`world.yaml` item field, or `plot.md` front matter,
  with `plot.md` settled first per principle 9).
- What happens to a captured condition that is on no axis: presumably free text
  that coexists, still capped at two phrases.
- What happens when an axis value is also a legitimate place for some thing
  (a boat whose place is "open water"): the rule must be per item, not global.
- Authoring cost is one declaration per openable or breakable item, and it
  generalises across packages with no per-story code.

**1b. Authored text that states changeable facts.** Scene 1A examples: placement
`michelle_phone: on the kitchen floor`; setting fact "Michelle's phone is not
damaged."; the 1A scene frame in `knowledge.yaml` ("Michelle's undamaged phone is
lying on the kitchen floor"); the scene-entry statement ("...Michelle's phone
remains on the kitchen floor"); the 1A.1 beat details and bullet in `plot.md`;
delivery text ("Michelle's phone is still here, and it is not damaged").
Recommended: an authoring rule that a tracked thing's changeable facts live only
in its seed (placement and setting facts), with prose around it not restating
them, plus a package audit. Alternatives: render those parts of prose from state;
or keep prose and tell the narrator THINGS wins (a rule against the prompt's own
material; conflicts with principle 5). Decide whether reveal statements and
delivery text may state changeable facts, and how the audit finds restatements on
any package without runtime keyword gating (an offline audit a human reads is
allowed).

**1c. Which things are tracked.** Recommended: seed from each scene's
`item_placements` and the setting facts about those items; exclude anything not
yet shown to the player; do not add narrator-invented things at runtime. Carried
things (status `carried`) follow the character across scenes; untaken things stay
with their scene. Alternatives: let a reply add a capped number of new things;
track places as well as things. Decide whether narrator-invented objects should
persist at all, and the prompt-size cap.

**1c decision (Brandon, 2026-09-15).** Narrated things persist: a thing the
narration introduces becomes a tracked thing rather than a dropped unknown name,
and the tracked store may grow. The prompt does not grow with it. Each turn's
THINGS carries only the tracked things the player's input refers to and those a
current story beat or progression involves; nothing is ranked and truncated to
a cap. Consequence: the engine must resolve a reply's name to an existing thing
before creating a new one ("drawer" and "Michelle's carved drawer" must not
become two things), and it must not rely on the narrator copying names exactly.

**1d. Cause and regeneration.** Recommended: the narrator labels `cause` in the
same reply (measured in Phase 2 before relying on it); one regeneration with a
one-line hint, sharing or separate from the existing recovery budget (decide),
then fall back to accepting the turn with that single change refused and the
narration regenerated a second time only if Brandon accepts the cost.

**1e. Containment: characters and things share one tree.** Asked for by Brandon
on 2026-09-16, after a run recorded the laptop "in her hand" with no record of
whether Kristin was at the truck or in the house: "The truck contains Kristin, or
the house contains Kristin, or even the 'outside' contains Kristin. That way,
when Kristin is holding something like a phone, that object is in the same
location as Kristin is." Settled: characters are tracked with a place exactly
like things, a held or carried thing's container is the character, and where
anything is in the world is found by walking up the chain (phone in Kristin,
Kristin in the truck, truck outside the house). Moving Kristin moves what she
holds without touching those things' records.

The same model absorbs the dropped container-shaped replies from round 5,
`{"kitchen counter": {"contents": ["Michelle's phone"]}}`: each listed thing's
container becomes the kitchen counter.

Open, with recommended defaults:
- **What a place stores.** Recommended: keep the narrator-facing place phrase
  ("in Kristin's hand", "on the kitchen counter") and add a resolved `container`
  naming a tracked thing, character or authored area. The narrator keeps reading
  natural phrases; the engine reasons over containers. Alternative: replace the
  phrase with container plus a relation word (in, on, under, with).
- **Where the tree is authored.** Recommended: areas with a parent in
  `world.yaml` (house > kitchen; outside the house > Kristin's truck), and each
  scene's placements naming their immediate container, added scene by scene as
  problems surface. Alternative: derive areas from placement phrases at load.
- **How a place phrase resolves to a container.** Recommended: the existing
  match call also maps each new place phrase to a tracked container name, since
  this is meaning, not wording. A phrase that resolves to nothing records the
  place with no container rather than guessing the scene.
- **The player character in THINGS.** Recommended: the player character's own
  line (for example "Kristin. Place: in the kitchen.") is sent every turn,
  because every command is about what she does and where. Other characters and
  containers follow the reference rule in 1c.
- **Scope of the first build.** Recommended: the bench item-facts harness first,
  as with declared axes, then the runtime in Phase 4.

**Exit criteria**
- Each decision recorded in this plan under its heading, with the chosen option
  and the reason.
- `docs/markdown-story-authoring.md` updated for 1b and 1c.

### Phase 2 - Measure cause labels and regeneration on the bench (billed, small)

**Decisions before starting**: 1a and 1d.

**Tasks**
- [ ] Ringer: add `cause` and `status` to the bench reply format and the
  fact-tracking judge.
- [ ] Build labelled cases with both causes, including "Pick up Michelle's
  phone." versus "Look carefully at Michelle's phone." followed by a pickup, and
  commands that invite story-breaking changes ("Smash Michelle's phone.", "Throw
  Michelle's phone out the back door.").
- [ ] Ringer: a bench probe that detects a story-breaking change with the
  existing dependency analysis on a candidate state and regenerates once with a
  hint; record success, calls and latency.
- [ ] Smoke, then 4 replicates.

**Exit criteria**
- Cause-label agreement and status accuracy stated as numbers with sample sizes,
  accepted by Brandon.
- Regeneration success rate, extra calls and latency recorded; the retry budget
  and fallback in 1d confirmed or changed.

### Phase 3 - Story package: tracked things and authoring cleanup

**Decisions before starting**: 1b and 1c.

**Tasks**
- [ ] Ringer: package model support for whatever 1a and 1c require (for example a
  per-item flag or an explicit tracked-things list, and status predicates), with
  loader validation that fails closed on unknown items or statuses.
- [ ] Ringer: the package audit from 1b, runnable on any package, reporting prose
  that restates a tracked thing's changeable facts (offline, human-read).
- [ ] Authoring pass on continuity-initiative, `plot.md` first, removing
  restatements across all nine scenes; one Ringer task per scene or small group.
- [ ] Update `docs/markdown-story-authoring.md`.

**Exit criteria (structural, authoritative)**
- Package loads; loader tests cover the new fields and fail-closed cases.
- The audit reports zero restatements for continuity-initiative, and a
  deliberately broken fixture package is reported.

### Phase 4 - Runtime state and persistence

**Tasks**
- [ ] Ringer: add tracked-thing state to `RuntimeState` (`place`, `condition`,
  `status` per tracked thing), initialised from the package on scene entry,
  carried across transitions per 1c, included in snapshots so rejected turns and
  rewinds restore it.
- [ ] Ringer: persist it; bump `SCHEMA_VERSION` from 4 to 5 in
  `storygame/runtime/persistence.py`, following how earlier bumps treat old saves.
- [ ] Ringer: expose tracked-thing state in the web API state summary so hosted
  E2E can assert on it.

**Exit criteria (structural)**
- Tests: initialisation, snapshot restore after a rejected turn, rewind after a
  game break, transition carry, save/load round trip, old-schema handling.

### Phase 5 - Prompt and reply contract

**Tasks**
- [ ] Ringer: render THINGS in `CloudflareTurnProvider._section_user_prompt`
  (after SCENE, before CONSTRAINTS) from runtime state, for openings and turns.
- [ ] Ringer: stop sending `_placement_rules` and `_setting_fact_rules` lines for
  tracked things (untracked placements unchanged).
- [ ] Ringer: extend the reply contract with optional `item_changes` (new model
  next to `TurnProposal`, strict), and add the system-prompt lines from 4.1 plus
  the `status` and `cause` wording chosen in Phase 2, replacing rather than adding
  rules where possible; update the output example so it does not show the
  protagonist handling an object unprompted.
- [ ] Update the bench so its default provider path exercises the real game
  implementation, and retire the duplicated logic in `bench/item_facts.py`.

**Exit criteria (structural)**
- Prompt tests: THINGS present and exact; no line outside THINGS states a tracked
  thing's changeable fact, for every scene of the package.
- Contract tests: valid, malformed, unknown-name, over-cap and missing
  `item_changes` replies.
- The bench offline replay shows only the intended prompt differences.

### Phase 6 - Capture, validation and routing in the turn

**Tasks**
- [ ] Ringer: in `RuntimeEngine.turn`, validate `item_changes` deterministically,
  apply them to the candidate state, and map `status` to dependency predicates.
- [ ] Ringer: run the existing future-dependency analysis on that candidate.
  - Narrator-caused story break: regenerate per 1d; on failure, the chosen
    fallback.
  - Player-caused story break: existing `GameBreakWarning` and pending break,
    with the warning naming the concrete dependency without revealing protected
    knowledge.
- [ ] Ringer: commit thing changes atomically with the turn; rejected and
  regenerated turns leave no partial state.
- [ ] Ringer: record per-turn telemetry (changes captured, dropped entries,
  regenerations, warnings) in the turn delivery record for bench and E2E.

**Exit criteria (structural)**
- Tests with a scripted provider: a pickup persists to the next prompt; a
  narrator-caused destruction of a dependency without a fallback regenerates; a
  player-caused one raises a warning; a destruction covered by a fallback commits;
  malformed and unknown entries are dropped and recorded; rejected turns change
  nothing; the regeneration budget is bounded.

### Phase 7 - Test layer and evaluation

**Tasks**
- [ ] Ringer: make hosted `@world-state` meaningful - after "Pick up Michelle's
  phone and keep it with you." the state summary shows the phone carried, and the
  follow-up narration does not put it back on the floor (judged, not
  keyword-matched).
- [ ] Ringer: add a story-break E2E ("Smash Michelle's phone.") asserting the
  game-break warning appears.
- [ ] Add fact-tracking and continuity criteria to the hosted canon judge
  (`@llm-canon`) or a new judged category, following its discard rules.
- [ ] Bench: rerun the Phase 0 variations against the game implementation and
  compare with the bench-harness numbers.

**Exit criteria**
- Structural suite green (authoritative).
- Live evidence: bench accuracy within an agreed margin of Phase 0; hosted E2E
  passes on staging.

### Phase 8 - Rollout

**Tasks**
- [ ] Deploy to staging; run `@smoke`, `@world-state`, the story-break E2E and a
  bench smoke against staging.
- [ ] Record token and latency cost per turn against the pre-change baseline
  (principle 7).
- [ ] Update `docs/PRD.md`, `README.md` and `docs/testing-runbook.md` (keep the
  runbook short: edit procedures in place, no dated logs).
- [ ] Mark `.plans/narrated-world-changes-experiment.md` complete and retire this
  plan's finished phases.

**Exit criteria**
- Staging evidence recorded; Brandon approves promotion.

---

## 7. Parallel track: defects the loop does not fix

Independent narration fixes; each follows principles 4 and 5 and needs its own
small plan or task.

- **Scene restarts.** About one turn in three re-narrates arriving at or stepping
  into the house, in every arm. Resending the scene entry text each turn was
  already removed (commit 2a63ce7). Next: find what else in the prompt reads as an
  arrival (the 1A scene frame "Kristin has reached the house..."), measure with
  the continuity judge before and after.
- **Acting beyond the command.** Kristin still does unrequested things on about
  38% of turns. Under principle 1 those actions will now persist, which makes the
  defect more consequential. Suspected cause: the narrator's output example in
  `cloudflare.py` (`DEFAULT_OUTPUT_EXAMPLE`: "She works it loose and turns it over
  in the light") shows the protagonist handling an object. Replace it with an
  example that only looks, then measure.
- **A command that travels to the next scene.** "Leave the house and drive to
  the park." cannot be finished by the narrator: the park is in 1B's SCENE and
  the command runs in 1A, so the turn is unfinishable whatever rule the narrator
  is given, and it failed 3/4 then 4/4 in rounds 7 and 8. Scene transitions are
  the engine's, so this is an engine capability (recognise a command naming the
  next scene's location and run the transition), not a narrator rule. Round 9
  task R9-1 takes it out of the bench script so it stops consuming a third of
  the `command_not_finished` count; the capability itself belongs to Phase 1 or
  later and is undesigned.
- **Scene openings failing on a known-term leak.** An opening that says "forced
  entry" fails narration safety before any turn. Whether narrating a visibly
  forced door counts as unearned knowledge is a story-data decision for Brandon
  (`plot.md` first). The bench's `fixed_turns` mode does not cover openings.

## 8. Risks

- **Prompt growth**: THINGS adds lines every turn; cap tracked things per scene.
- **Output tokens and truncation**: `item_changes` lengthens replies; the
  existing truncation salvage keeps finished segments but may drop the changes.
  Measure reply length and set `max_tokens` accordingly.
- **Grader trust**: every live number depends on GPT-5.4 judges calibrated on
  small constructed sets; recalibrate whenever the reply format changes.
- **Sample size**: 4 replicates per arm detects only large effects; narrow gaps
  mean more replicates, not a decision.
- **Narrator ignoring THINGS**: observed once in 47 turns with single-value
  fields; watch it in long sessions.
- **Hidden things**: tracking must never list or narrate a thing the player has
  not been shown (for example the memory card before it is found).

## 9. Reference: commands and files

- Prompt preview, no model call:
  `TMPDIR=/tmp uv run python -m bench prompt --scene 1A --variation <file> --text`
- Bench run, billed:
  `TMPDIR=/tmp .venv/bin/python -m bench run --variation <file> --scene 1A --replicates 4 --script phone-bag-door --out bench/results/<name> --confirm`
- Bench options (`bench/README.md`): `fixed_turns`, `item_facts`,
  `continuity_judge`, `fact_tracking_judge`.
- Variations: `bench/variations/item-facts-single.json`,
  `item-facts-second.json`, `item-facts-single-minimal.json`,
  `continuity-1a.json`.
- Results: `bench/results/item-slots-{single,second}-1a`,
  `bench/results/item-facts-*-1a`, `bench/results/continuity-1a-*-entry-text-cut`.
- Experiment record: `.plans/narrated-world-changes-experiment.md`.
- Ringer: `/home/bcorfman/dev/ringer/ringer.py` (`lint`, `run`, `hud`).
- Current bench variation for this work:
  `bench/variations/item-facts-package-two-scene.json` (8 turns in 1A, 4 in
  1B; run with `--scene 1A`, `continue_to` plays 1B) and
  `bench/variations/item-facts-package-long.json` (40 turns).
- Failure report:
  `.venv/bin/python -m bench.failure_report --title "Round N failures" --preamble-file <txt> --section two-scene=bench/results/<dir> --out bench/results/roundN-failures.md`
- Round results: `bench/results/round5-failures.md`,
  `bench/results/round6-failures.md`, `bench/results/item-facts-v7-two-scene-1a`,
  `bench/results/split-command-1a`.
- Round 7, the source of every round 8 fix: `bench/results/round7.md` (every
  turn, with Brandon's own comment under each) and
  `bench/results/round7-failures.md`; records in
  `bench/results/item-facts-v8-two-scene-1a/`.
- Round 8 output directory to create: `bench/results/item-facts-v9-two-scene-1a`
  (smoke into `item-facts-v9-smoke-two-scene-1a`, whose ledger row is removed
  afterwards).
- Re-judging saved turns without replaying narration: run
  `bench/continuity-judge.mjs` and `bench/fact-tracking-judge.mjs` with
  `--input <run>/all-turn-records.json --output <file>`, after setting the
  record's `package_path` to the variation's effective package
  (`load_variation(...)["_package_path"]`), because the run's own temporary
  package is gone. Two judge calls per replicate.
- Judge scopes, as of round 8: the fact judge owns tracked-thing state
  (`facts_after_correct`, `missed_change`, `invented_change`,
  `narration_contradicts_given_facts`, `dropped_true_condition`,
  `kept_ended_condition`, `state_as_place`); the continuity judge owns narration
  against canon and earlier turns (`contradicts_stated_fact`,
  `protagonist_acts_beyond_command` as context only, `restarts_scene`,
  `command_not_finished`, `reveals_hidden_canon`). `bench/failure_report.py`
  counts every continuity label except `protagonist_acts_beyond_command`, which
  it prints as "[narrator initiative]".
