# Narrated world continuity: implementation plan

Status: Phase 0 rounds 1 and 2 measured and recorded. Format v2 did not reach
the 92% bar for any change type except checking a carried thing; the next
strategy is awaiting Brandon's decision - see Phase 0. Nothing below is in the
game yet. The bench experiment
that justifies the design is complete and recorded in
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
- **Raise the Ringer check timeout** when a check runs the full suite (about 3
  minutes): `RINGER_CHECK_TIMEOUT_S=900 ./ringer.py run manifest.json ...`.
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
tracked thing has one `where` phrase and up to two `condition` phrases:

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

1. **Prompt** carries THINGS: every tracked thing's current `where` and
   `condition`, from engine state. No other prompt line states a tracked thing's
   changeable facts.
2. **Narrate and capture in one call.** The reply adds `item_changes`: for each
   changed thing, its new `where`, up to two `condition` phrases, a closed
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
- **Partial entries**: a reply entry may omit `where` (place kept) or
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
- [ ] Ringer task D: the same removal in the 40-turn variation.
- [ ] Ringer task E: judge label split, then calibrate.
- [ ] Ringer task F: partial entries, new example, merged match call, per-turn
  THINGS selection, persistence of narrated things, per-turn call counts.
- [ ] Smoke, then 4 replicates of each variation; tally against 92%.

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

### Phase 1 - Design decisions

**Why.** Three questions must be settled before engine code. Present options to
Brandon with the Phase 0 evidence; do not build until decided.

**1a. Story-break status.** Recommended: add a closed `status` per tracked thing
- `intact`, `destroyed`, `lost`, `carried` - alongside free-text `where` and
`condition`. The engine maps `destroyed` and `lost` to the `destroyed` predicate
the dependency analysis already reads (add `lost` as its own predicate only if the
story needs to tell them apart). Alternatives: an LLM judgement per change to a
dependency-bearing thing (principle 4, second rank); package-declared breaking
words (brittle, last). Decide also which things carry dependencies beyond
transition `required_dependencies` (for example reveal sources).

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
- [ ] Ringer: add tracked-thing state to `RuntimeState` (`where`, `condition`,
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
