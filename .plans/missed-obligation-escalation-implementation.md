# Missed-obligation escalation — implementation plan

Phased execution of the decisions recorded in
[missed-obligation-escalation.md](missed-obligation-escalation.md) (design and
the answered open questions Q1–Q16) plus the Scene 1A hiding-spot fix decided on
2026-09-13. The design doc says *why*; this doc says *what ships, in what order,
and how each step is proven*. Tick boxes as work lands.

## Execution record (2026-09-13)

Every phase except the Phase 9 live run is committed on the local branch
`obligation-escalation-integration` (24 commits from `main`), with 495 tests
green and ruff clean. Nothing is pushed or merged: the owner asked to keep
everything local, so "merged" boxes stay unticked and phase branches
`obligation-escalation-phase1..3` exist only for Phases 1–3. Every code and
package change was a GPT-5.6 Luna Ringer task with an executed check. Offline
persona drives found and fixed several stranded exits along the way; the design
doc's "Carried-forward defects" section lists them with commits.

## Ground rules for every phase

- Every code or package change is a Ringer manifest run on GPT-5.6 Luna
  (`"engine": "codex"`, `"model": "gpt-5.6-luna"`). Claude writes the brief and
  the check, reviews the patch, and commits; Claude does not type the change.
- `worktrees: true` builds from HEAD: commit the phase branch before each run.
  The check exports `git diff` to a patch outside the worktree.
- Each phase is its own branch and PR, merged before the next phase starts
  unless the phase says it can run in parallel.
- Evidence has two gates. **Deterministic** tests (structural, scripted engine
  runs) are authoritative and must pass before merge. **Live** runs (bench,
  hosted E2E) are quality evidence only and never gate a merge on their own.
- The whole repo stays ruff-formatted; `uv run pytest` passes at every merge.
- Narrator-facing text (rules, realization text, cue text) is written at an
  8th-grade reading level and states what *is* true (design Decision #6).
- Player input in every test, script and example is an imperative command
  ("Search the workstation"), never first-person narration.
- Validation added here must work zero-shot on any story package; never tune it
  to continuity-initiative.

## Dependency map

```
Phase 0 prep
 ├─ Phase 1 hiding-spot fix ─────────────────────────────┐ (independent)
 ├─ Phase 2 delete pacing_impact ─────────────────────────┤ (independent)
 └─ Phase 3 pacing reaction window                        │
     └─ Phase 4 backstop invariant (Q14/Q13)              │
         └─ Phase 5 latest_turn expiry + resolution gate (Q2/Q9)
             ├─ Phase 6 Cue layer (Q1/Q4/Q10)
             └─ Phase 7 Complication realizations (Q7/Q6)
                 └─ Phase 8 deterministic persona harness (Q15)
                     └─ Phase 9 live quality measurement (Q15/Q16)
Phase 10 carried-forward defects — independent track, any time after Phase 0
```

---

## Phase 0 — Preparation

- [x] Create branch `obligation-escalation-prep` from `main`; confirm
      `uv run pytest` and `uv run ruff format --check` are green as a baseline.
      (403 passed.)
- [x] Commit both plan documents on that branch. (Already on `main` via #463.)
- [x] **Home for the "drawers are shut" sentence** — decided 2026-09-13: a new
      optional scene-metadata `setting_facts` list, rendered as rules beside
      placement rules (Phase 1). Not the 1A scene frame; not skipped.
- [x] **Home for cue text** — decided 2026-09-13: optional `cue_text` on
      `FactDelivery` in `handoffs.yaml` (Phase 6).
- [x] **Beat leak path confirmed** (2026-09-13): beat 1A.2 is linked from
      `SL-1A-A` (open from turn 0), `SL-1A-B` and `SL-1A-D`; `_candidate_beats`
      iterates every projected candidate, including runtime-owned reveals.
      Decided fix: strip the card's location and "hidden" wording from 1A.2
      (Phase 1).
- [x] **Hidden-item placement loader check** — decided 2026-09-13: none; the
      rule goes in the authoring guide (Phase 1).
- [x] **Keep `plot.md` canonical for the card's location** — decided
      2026-09-13: a scene-level `**Hidden canon:**` line in Scene 1A.
- [x] **Parser check** (2026-09-13): `_parse_scenes` splits a scene into front
      matter and body; beats are `### Scene <id>.<n> — …` sections, each running
      to the next beat heading or the end of the scene. Text between the front
      matter and the first beat heading (`**Setting:**`, `**Characters:**`,
      `**Plot:**`) belongs to no beat, and no runtime path reads it: prompts use
      beats, the opening beat's details, front-matter `entry_text` and scene
      frames; `_is_present` and narration safety read beats only. The audit's
      plot vocabulary reads all of `plot.md`, and `bench/judge-cli.mjs` sends the
      whole scene block to the judge. **Trap:** text after the last beat is
      absorbed into that beat's prose, so the line goes before
      `### Scene 1A.1`.

---

## Phase 1 — Stop leaking the memory card's hiding spot (option 1 + visible-state sentence)

**Problem.** `_placement_rules` sends "Hidden memory card is taped under a
drawer in Michelle's workstation." in every 1A prompt until custody, and the
card's display name advertises a hidden object. Beat 1A.2 also locates the card
("hidden memory card; taped drawer"; "taped beneath a drawer") and is linked
from `SL-1A-A` (open from turn 0), `SL-1A-B` and `SL-1A-D`, so
`_candidate_beats` can project it from the first turn. The narrator is handed
the location before the player searches.

**Decision (2026-09-13).** Remove the standing location and strip it from the
beat. The location reaches the narrator only through the reveal
`delivery_text` the runtime inserts when the card is earned, or the Deadline
fallback. Add one true, visible-state sentence through a new `setting_facts`
list. No loader check for hidden-item placements.

Brief 1 — package and prompt (`f8fd3ce`):
- [x] Delete the `memory_card` entry from 1A `item_placements` in `plot.md`
      (keep `michelle_phone` and `kristin_laptop`).
- [x] Rename the `memory_card` display name in `world.yaml` from "Hidden memory
      card" to "Michelle's memory card"; check the owner rule's output for it.
- [x] Add the location to both `SL-1A-B` reveal `delivery_text` entries in
      `knowledge.yaml` (e.g. "Michelle's memory card was taped under the
      drawer carved with Kristin's initials, KMS.") and add a location group to
      their `must_convey`. (Group later narrowed to hidden-location terms only,
      so narrating the visible carving is not rejected — `112ff66`.)
- [x] Add the location to the 1A `continuity_initiative_known` fallback text in
      `handoffs.yaml`, so the Deadline path locates the card too.
- [x] Add `setting_facts: tuple[str, ...] = ()` to `SceneMetadata`, parsed from
      scene front matter in `plot.md`; loader rejects empty strings. Render
      each sentence verbatim as a rule immediately after the placement rules,
      in both the opening prompt and `_turn_rules`.
- [x] Add `setting_facts: ["Michelle's workstation drawers are shut."]` to 1A.
- [x] Strip the card's location and "hidden" wording from beat 1A.2 in
      `plot.md`: the `taped drawer` and `hidden memory card` details and the
      "taped beneath a drawer" prose. Keep at least three details (model
      minimum) and keep the beat's other content. (Beat 1A.4's "taped
      undersides" was stripped too.)
- [x] Add a scene-level line to Scene 1A in `plot.md`, after `**Plot:**` and
      before `### Scene 1A.1` (done 2026-09-13):
      `**Hidden canon:** Michelle hid a memory card for Kristin, taped beneath
      the workstation drawer carved with Kristin's initials, KMS. It stays
      hidden until Kristin finds it.` (Confirmed by Brandon 2026-09-13: the card
      is under the KMS drawer.)
      Nothing parses it; it keeps `plot.md` ground truth for the location.
      Verified it belongs to no 1A beat; `uv run pytest` 403 passed. It is the
      only Hidden canon line the current plot needs: no other beat is losing a
      hidden location.
- [x] Update `SL-1A-A`/`SL-1A-B`/`SL-1A-D` source-beat links only if the loader
      or audits require it after the edit. (Not required.)
- [x] Update the authoring doc (`docs/markdown-story-authoring.md`): a hidden
      item's location belongs in its reveal, not in `item_placements` or in beat
      text; record it in `plot.md` as a scene-level `**Hidden canon:**` line
      before the first beat (for humans, audits and the bench judge; never sent
      to the narrator; never after the last beat, which would absorb it);
      document `setting_facts`.

Brief 1 — tests (check command runs all of these):
- [x] Replace the placement-sentence assertions in
      `tests/test_cloudflare_transport.py` (~L1696–1722) and
      `tests/test_markdown_story_package.py` (~L45–106) so they use a synthetic
      fixture item rather than the real card.
- [x] New deterministic test: drive scene 1A with a scripted provider through
      turns that do not earn the card, capture every prompt the transport
      builds (opening and each turn), and assert none contains "taped",
      "hidden memory card", or the workstation-drawer location; assert the
      drawers-shut sentence is present in the rules.
- [x] Loader and render tests for `setting_facts` with a synthetic scene: parsed,
      empty string rejected, rendered after placement rules, absent when unset.
- [x] Structural test on the real package: Scene 1A's `**Hidden canon:**`
      sentence appears in no beat's prose or details (including the opening
      beat), and no 1A prompt built in the scripted run contains it.
- [x] New deterministic test: on the reveal turn, the prompt contains the
      location via the reveal's delivery text; after custody, it does not.
- [x] New deterministic test: the Deadline fallback for 1A names the location.

Verification:
- [ ] `uv run pytest` green; ruff clean; patch reviewed; merged. (Green,
      reviewed and committed on `obligation-escalation-phase1` and the
      integration branch; not merged — kept local.)
- [ ] Live disclosure measurement (quality gate, not merge gate): bench arms of
      n ≥ 50 each — control is a package override restoring the old placement
      and name; treatment is the merged package. Measure the rate of pre-reveal
      turns whose narration discloses the card's existence or location, judged
      by LLM, and compare with `bench compare`. (Folded into Phase 9: the
      escalation judge's `no_pre_reveal_disclosure` criterion.)
- [ ] Update the design doc's carried-forward note to "fixed" with the measured
      rates. (Marked fixed; rates pending Phase 9.)

---

## Phase 2 — Delete `pacing_impact` (Q8)

Independent of Phases 1 and 3; may run in parallel. (`026d2c3`, `a1fbc92`.)

- [x] Remove the `**Pacing impact**` section from all 30 storylets in
      `storylets.md`.
- [x] Remove `pacing_impact` from the `Storylet` model and the loader's section
      parsing and required-section list.
- [x] Update tests and fixtures that construct or assert `pacing_impact`.
- [x] Check: `uv run pytest` green, and a repo search for `pacing_impact` in
      `storygame/`, `data/` and `tests/` returns nothing.
- [x] `pressure_role` and `helps_transition_triggers` are **not** removed here
      (not decided).

---

## Phase 3 — Pacing reaction window (decided 2026-09-08, not shipped)

Prerequisite for Phase 5: expiry is only safe once every scene shows a visible
threat two turns before its deadline and every optional storylet's
`latest_turn` leaves a turn before `handoff_after_turns`. Required storylets
(Q2 amendment) do not expire, so their windows are not constrained here and are
not re-authored. (`95a496e`.)

- [x] Add pacing events: `pursuit_1b` (turn 2, does not resolve the pursuit), a
      1C security escalation, visible 2A scrutiny (Rebecca stays hidden), and a
      3C collapse escalation — all at turn 2 — each asserting a new pressure
      fact declared in `knowledge.yaml` purposes.
- [x] Move `destruction_3b` from turn 4 to turn 3.
- [x] Widen 1B to `2/4/5` and 3C to `2/4/6`.
- [x] Raise `budget_seconds` to 1890.
- [x] Update `tests/test_scene_relative_pacing.py`: `expected_windows`, the
      over-budget probe (`1890` → `1889`), and relax sum-equals-budget to `<=`.
- [x] New structural test (any package): every *optional* storylet's
      `latest_turn` is strictly less than its scene's `handoff_after_turns`
      (a storylet is required when a realization asserts a fact in its scene's
      bridge activation; required storylets are exempt), and every scene with a
      pacing event has it at least two turns before `handoff_after_turns`. Fix
      any authored window that fails.
- [ ] Check: `uv run pytest` green; patch reviewed; merged. (Green and
      committed; not merged.)

---

## Phase 4 — Backstop invariant: expiry can never strand an exit (Q14, Q13)

(`3f2f1bc`; runtime counterpart `864854e`.)

- [x] Add a loader validation, generic over packages, that raises
      `StoryPackageError` naming the scene and fact when:
  - [x] a fact in a scene's bridge-event `activation` (`all_facts_true` and
        every `any_of` member) has no `handoffs.yaml` delivery — **except** a
        world-only fact asserted by a world-only knowledge entry available in
        that scene (design doc, Implementation notes, Q14); or
  - [x] a transition trigger is not asserted by that scene's bridge-event
        operations, by a pacing-event effect, or by a delivery `cost`.
- [x] Loader tests with synthetic packages for each failure and for a valid
      package; the real package must load unchanged.
- [x] Record Q13's rule in the engine docstring where ranking will live
      (Phase 6): ranking only foregrounds content whose activation conditions
      already hold and never activates past a guard.
- [ ] Check: `uv run pytest` green; patch reviewed; merged. (Green and
      committed; not merged.)

---

## Phase 5 — `latest_turn` expiry and the resolution-phase gate (Q2, Q9)

(`c513a4d`.)

- [x] Add one derived predicate, shared by engine and tests: a storylet is
      **required** when any realization asserts a fact in its scene's bridge
      activation (`all_facts_true` or `any_of`); otherwise it is **optional**.
      (`storygame/story_package/obligations.py`; later widened to storylets
      named by canonical event realizations — 24 required.)
- [x] In `_activate_pacing`, once `turns_since_entry > latest_turn`, an
      *optional* storylet no longer activates, and if active but unfired it is
      removed from `active_event_ids`. *Required* storylets never expire; they
      stay open until fired or the scene is left. Expiry never commits a fact or
      forces a realization.
- [x] Confirm the `earned_forward` path cannot re-open an expired storylet.
- [x] Add one engine predicate for escalation eligibility: a scene whose
      `freytag_phase` is `resolution` gets no Cue, no Complication realization
      selection and no Deadline staging. Phases 6 and 7 must use it. (Owner
      decision: authored Complication realizations are exempt; see Phase 7.)
- [x] Deterministic tests: an optional storylet is a candidate at
      `latest_turn` and not after; a required storylet (e.g. SL-1A-B, `2/2/2`)
      is still a candidate after `latest_turn` and through
      `handoff_after_turns - 1`; the required/optional predicate classifies the
      real package's 19 bridge-feeding storylets as required; a `resolution`
      scene stages nothing; snapshot restore after a rejected turn does not
      resurrect or double-expire a storylet.
- [x] Existing canon-journey tests stay green (they prove no exit is lost).
- [ ] Check: `uv run pytest` green; patch reviewed; merged. (Green and
      committed; not merged.)

---

## Phase 6 — Cue layer (Q1, Q3, Q4, Q10)

(`3b6439d`; cue text safety `dfb56d8`, `13e57f7`.)

Brief 1 — engine:
- [x] Keep derivation in the engine (Q3): extend `_bridge_delivery_fact_ids`
      output into a ranked list — exclude facts asserted by any pacing event;
      order by the soonest `latest_turn` among eligible, unfired source
      storylets for each fact; break ties (including facts with no open source)
      by `minimal_undelivered_facts()` order (Q1). Required storylets do not
      expire (Phase 5), so the tie-break usually decides for bridge facts.
- [x] Add `delivered_cue_ids: tuple[str, ...]` to `RuntimeState` and
      `RuntimeSnapshot`, cleared on scene entry beside the staged tiers; bump
      `SNAPSHOT_VERSION` so older persisted snapshots are rejected (Q4).
      (Persistence actually gates on `RuntimeStateSqliteStore.SCHEMA_VERSION`,
      now 4.)
- [x] From `nudge_after_turns`, stage at most one cue per turn: the
      highest-ranked missing fact that has cue text and is not in the ledger.
      Record it in the ledger only when the turn is accepted.
- [x] Remove the every-turn hint instruction ("Hint at the evidence with
      something a character says, notices, or hears on a radio. Do not make it
      a fact yet.") and its hint-tier staging; replace with a Cue instruction
      that passes the single cue text. Update `TurnDelivery` (`hint_staged` →
      cue field) and the bench fields that read it.
- [x] Respect Phase 5's resolution gate.

Brief 2 — package:
- [x] Add optional `cue_text: str | None` to `FactDelivery`; loader rejects an
      empty string.
- [x] Add `cue_text` in `handoffs.yaml` for every delivery fact that a scene can
      still be missing at `nudge_after_turns`. Each cue re-presents something
      the player can already see or has already been told; it never states the
      missing fact itself.
- [x] 1A `continuity_initiative_known` cue carries the KMS carving (Q10), e.g.
      "Kristin's initials, KMS, are carved into a drawer of Michelle's
      workstation." It must not mention the card or what is under the drawer.
      Canon places the card beneath that same drawer, so the cue points at the
      right spot without saying why.
- [x] Deliveries without `cue_text` produce no cue; add a test that pins this.

Tests:
- [x] Ranking unit tests over synthetic activation rules and storylet windows.
- [x] A cue is delivered exactly once per scene visit; a rejected turn does not
      consume it; a game-break restore does not consume it.
- [x] Old snapshot versions are rejected by persistence.
- [x] No 1A prompt before the cue turn contains the KMS cue text; the cue turn's
      prompt contains it and not the card's location.
- [ ] Check: `uv run pytest` green; patches reviewed; merged. (Green and
      committed; not merged.)

---

## Phase 7 — Complication realizations on `PacingEvent` (Q7, Q6)

(`4e3dc53`; complication text safety `5f23718`.)

Brief 1 — schema and engine:
- [x] Add `realizations: tuple[PacingRealization, ...]` to `PacingEvent`; each
      has optional `when: tuple[FactPredicate, ...]` and required `text`.
- [x] Loader: if `realizations` is non-empty, the last entry must have no
      `when`; every `when` fact must be a declared fact.
- [x] Engine: when an event fires, select the first realization whose `when`
      matches current facts and pass only that text to the narrator on that
      turn. `effects` apply unconditionally, as today. Respect the resolution
      gate. (Owner decision: authored realizations still play in resolution
      scenes; the gate covers only generated cues and Deadline staging.)
- [x] Keep today's early-exit behaviour (Q6): an unfired event is dropped when
      its scene is left; add a test that pins it.

Brief 2 — package (scene by scene, 1A first):
- [x] `pressure_1a` realizations, in order: card not in Kristin's custody → an
      officer lingers at Michelle's workstation drawers (salient, never opened);
      lead already actionable → plain exit pressure; card in custody → the
      patrol searches for something Kristin now carries; default entry last.
      (Lead-actionable moved ahead of custody: it implies custody, so the
      original order could never select it.)
- [x] One default realization for each other pacing event (`purge_2c`,
      `override_deadline_3a`, `destruction_3b`, and Phase 3's new events). Add
      state-specific entries only as play surfaces the need.
- [x] Authoring rule in `docs/markdown-story-authoring.md`: realization text
      creates observable pressure, never unearned knowledge; a bridge narrates
      only pressure facts its activation requires (Q6).

Tests:
- [x] First-match selection, default fallback, and loader rejection of a guarded
      last entry — synthetic fixtures.
- [x] 1A: each custody/lead state yields the matching realization text and only
      that text in the prompt.
- [ ] Check: `uv run pytest` green; patches reviewed; merged. (Green and
      committed; not merged.)

---

## Phase 8 — Deterministic persona harness (Q15, authoritative gate)

(`c80cac7`: `storygame/personas.py`, `python -m storygame.personas --out`.)

- [x] Build scripted player personas on the `tests/test_canon_journey.py`
      engine harness (scripted provider, real package):
  - [x] **thorough** — earns each scene's facts early;
  - [x] **staller** — takes unrelated actions until the Deadline;
  - [x] **wrong-lead** — pursues a plausible but non-required thread.
- [x] Assert per scene: the thorough persona exits before any Deadline staging
      and receives no cue; the staller receives at most one cue per missing
      fact, a Complication realization matching its state, then a Deadline
      delivery with its cost applied; no persona is stranded; turns-to-exit
      falls within each scene's pacing window.
- [x] Emit a small per-scene summary (layer reached, cue count, turns to exit)
      as a test artifact for the bench to reuse.
- [ ] Check: `uv run pytest` green; patch reviewed; merged. (Green and
      committed; not merged.)

---

## Phase 9 — Live quality measurement (Q15, Q16, quality evidence only)

- [x] Bench variation for the treatment arm (merged package).
      (`bench/variations/escalation-treatment.json`, `64a5364`; bench turn
      records and the opt-in escalation judge `b077fdd`.)
- [x] Control arm: same variation with a package `overrides` entry that strips
      cue text and `PacingEvent` realizations. Engine-only behaviour (expiry,
      hint removal, ledger) is proven by Phase 8, not here.
      (`bench/variations/escalation-control.json`.)
- [ ] Run n ≥ 50 per arm concurrently; analyse with `bench compare`. (Option B
      scope chosen by the owner: scenes 1A, 1B, 2B, 3B; about 28,000 neurons
      and 800 judge calls. Manifest ready, single attempt; waiting for the
      owner's go-ahead. Option C, all eight exit scenes, follows if B works.)
- [ ] LLM-judged metrics: the cue points at the missing thread; complication
      narration creates pressure without unearned knowledge; no pre-reveal
      disclosure of hidden item locations (reuses Phase 1's judge). (Judge
      built; results pending the run.)
- [ ] Record results in the bench ledger; summarise the outcome in one line in
      the design doc (do not append result logs to the testing runbook).

---

## Phase 10 — Carried-forward defects (independent track)

Each ships as its own brief. Re-verify before briefing; Phases 6–7 may rewrite a
scene's bridge.

- [x] **3C resolution cascade.** Design choice still open: sequence the six
      `canonical_resolution_events`, or require each one's player-visible
      realization before it commits. Decide, then brief. Includes adding a
      `portable_archive` item (custody starts at Rebecca) and introducing it
      before Kristin must secure it. (Owner chose realization-gated with a
      Deadline backstop; 3B's exit now guarantees exposure's prerequisites —
      `9f3f995`, `6afb008`.)
- [x] **Bridges claim more than their activation guarantees** (`t_1b_1c`,
      `t_2b_2c`, `t_2c_3a`): each bridge states only facts its activation
      guarantees; a fallback that supplies a fact also supplies its item.
      (`57d02ae`, `2af3597`.)
- [x] **Stale item declarations:** remove `memory_card` from 2B, 2C and 3C, and
      `override_codes` from 3B. (`f2e2916`.)
- [ ] Deferred until surfaced in play: 2A credentials created by `SL-2A-B`; a
      1B transit-card placement behind `while_fact_false`.

---

## Done when

- [ ] Phases 1–8 merged with deterministic evidence green. (Evidence green on
      the local integration branch; not merged.)
- [ ] Phase 9 live comparison recorded.
- [ ] Design doc status updated to "implemented", with any decision that changed
      during implementation recorded against its question number. (Status and
      Implementation notes updated 2026-09-13; final once Phase 9 is recorded.)
