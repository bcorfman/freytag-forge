# Scene affordance E2E tests: plan

Status (2026-10-04): L0-L2 are merged (PR 510, main 3a82bc5). Brandon's rule:
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

Open, not yet known (the first item is answered above): (1) whether the semantic fallback ran on r3 turns 3-4
(staging returns `semantic_match` and `prompt` per turn, but
`blind-player.spec.js:99` drops both from the turn record; the harness needs
to save them, then rerun);
(2) the recorded prompts for r3 turns 3-4; (3) the L1 x3 result.

## Resume here (2026-10-04)

Latest: Jev probe and L2 rerun are recorded above. Next: probe Jev arms (names
removed; on-screen wording "crooked drawer" added), replay the exact runtime
names from a recorded prompt, then fix at the source the probe points to and
rerun L2 x3. The uncommitted harness changes (turn log, semantic_match
recording, digest) and the probe files are not committed yet.

Next: (1) Brandon merges the `claude/gates-judge-names` PR and waits for the
staging deploy; (2) rerun L2 on 1A with 3 replicates, then more, and L1 with 3;
read results with `scripts/ringer/affordance/digest.py`; (3) extend L0 and run
L1/L2 on 1B and later (the map has gates only in 1A, 2A, 2C; the rest leave on
bridge events); (4) the other 67 reveals have the same word-group structure,
so check each scene's gate commands with natural phrasings. L2 runs need
`scripts/ringer/affordance/scene-affordance-l2-live.sh <replicates>`: it raises
staging's per-session turn cap (default 10 a minute) for the run and restores
it, and waits for the redeploy to settle. Unseen-word flags on verbs such as
retrieve and insert are false positives; ignore them.

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
