# Freytag Forge Architecture and Refactor Plan

## 1. Executive Summary
Freytag Forge already has the right *pieces* for a deterministic, proposal-first story engine, but they are arranged in a way that keeps reintroducing contradiction and parser-first feel. The core split is that canonical state currently lives in four places at once: `GameState.player/world/active_goal`, `GameState.world_facts`, `GameState.world_package`, and post-hoc narration/opening repair. The refactor should therefore start by making one mutation path authoritative, then move scene/dramatic state into facts, then collapse ordinary turns to one structured LLM proposal call plus deterministic validation/commit/narration.

Repository-specific conclusion:
- Keep: `storygame.engine.facts.apply_fact_ops` as the seed of a commit authority, `storygame.engine.turn_runtime.execute_turn_proposal` as the seed of proposal-first execution, `storygame.engine.triggers`, bootstrap plan validation in `storygame.engine.bootstrap`, typed LLM contracts in `storygame.llm.contracts`, and the explicit split between `storygame.web` and `storygame.web_demo`.
- Eliminate or demote: `rebuild_facts_from_legacy_views` / `sync_legacy_views` as normal runtime control flow, `world_package` fallbacks as runtime truth, `extract_narration_fact_ops` as a hot-path repair mechanism, parser-authored `advance_turn` as the default authored experience, and multi-call coherence/critic workflows on ordinary turns.

## 2. Current Effective Architecture
The repo's *real* runtime architecture today is:

- `storygame.engine.state.GameState` is the true hub. It stores mutable object graphs (`player`, `world`), fact state (`world_facts`), story metadata (`world_package`), scalar story metrics (`progress`, `tension`), and fallback story copy (`active_goal`).
- `storygame.engine.facts.initialize_world_facts`, `rebuild_facts_from_legacy_views`, and `sync_legacy_views` continuously translate between facts and mutable objects. This is the clearest split-source-of-truth anti-pattern.
- `storygame.engine.world.build_default_state` and `build_state_from_bootstrap_plan` still build object graphs first, then derive facts, then sync objects again.
- `storygame.cli.run_turn` is the real turn orchestrator. It chooses between:
  - proposal-first freeform resolution through `resolve_freeform_roleplay_with_proposals`, or
  - parser/action advancement through `storygame.engine.simulation.advance_turn`.
- `storygame.engine.freeform` is proposal-first in shape, but not yet in expressive power. The LLM planner produces `dialog_proposal` and `action_proposal`, then `_envelope_for_action` often reduces outcomes to flags and small trust deltas rather than scene consequences.
- `storygame.engine.turn_runtime.execute_turn_proposal` is the cleanest proposal executor in the codebase, but it still starts with `rebuild_facts_from_legacy_views`, which means facts are not yet primary.
- `storygame.llm.story_director.StoryDirector.compose_opening` runs a bootstrap bundle call, a bootstrap critic call, and a room-presentation call, then mutates facts, `world_package`, and mutable NPC/item state. It also uses `_reconcile_opening_facts` and `_sync_opening_room_presentation` to make accepted prose authoritative after the fact.
- `storygame.cli.run_turn` still commits prose-derived state through `storygame.llm.narration_state.extract_narration_fact_ops`, which is explicitly `narrate -> extract -> repair`.
- `storygame.engine.simulation` still drives beat selection and narrative incidents from `progress` / `tension`, with `_goal_bundle` and `_story_plan_bundle` falling back from facts to `llm_story_bundle` to `world_package`.
- `storygame.engine.parser` + `storygame.engine.rules` still define the strongest deterministic interaction path, which is why the product still feels room/verb-first.

## 3. Current Feel vs Target Feel
| Current feel | Why it happens now | Target feel |
|---|---|---|
| Room-first | `_room_lines`, parser verbs, `advance_turn`, room-local item resolution dominate output and state changes | Scene-first: the current scene, its pressure, and who is present should frame the turn |
| Command-first | `parse_command` and `apply_action` still define the richest deterministic behavior | Intent-first: player intent should be interpreted socially/dramatically before being reduced to bounded ops |
| Puzzle/local-object centric | `rules.py` and item/location helpers own most reliable consequences | Consequence-centric: social stance, reveals, scene pressure, and beat role should matter as much as objects |
| Narrative as overlay | narration is generated after state handling, then sometimes repaired back into facts | Narration from committed truth: prose should describe already-committed state and approved consequences |
| Parser fallback safety net | freeform path often collapses to generic flags; parser path still feels more "real" | Proposal-first safety: deterministic validators should make freeform reliable without dropping into parser-authored experience |

## 4. Current vs Target Architecture
**Current**
- `GameState` mixes runtime DB, projections, bootstrap metadata, and UI caches.
- Facts are authoritative only sometimes.
- Bootstrap/opening uses LLM prose plus post-hoc reconciliation.
- Normal turns can take a proposal-first path, but the engine still privileges parser/action structures and multi-stage narration review.
- Freytag is mostly `progress`/`tension` metadata plus beat-template selection.

**Target**
- `GameState` holds canonical fact-backed runtime state plus deterministic logs/RNG/persistence handles.
- Facts are the only mutable source of runtime truth.
- Bootstrap produces validated fact proposals; opening prose is generated from committed facts.
- Ordinary turns use one structured LLM proposal call, deterministic validation/commit, trigger/beat execution, then narration from the committed state.
- Freytag is represented as canonical dramatic state that affects available consequences, NPC stance, reveal budgets, and scene framing.

## 5. Source Of Truth Refactor
### Target state model
Make the fact store the only canonical mutable runtime state for:
- player location/profile/inventory
- room topology and room traits
- item placement, custody, discovery
- NPC location, stable traits, current stance/trust/availability
- puzzle state, leads, clues, event flags
- goals, active goal, beat phase, reveal schedule
- current scene and dramatic state

### Concrete repository changes
- Split `storygame.engine.facts` into three responsibilities:
  - fact storage/query
  - typed fact ops and cardinality rules
  - projection helpers for legacy callers during migration
- Introduce a single commit service, replacing "free-form fact ops + sync":
  - `ValidatedFactCommitter.commit(ops, source)`
  - `InvariantValidator.validate_pre_commit(state, ops)`
  - `ProjectionUpdater.refresh_from_facts(state)` as a temporary adapter only
- Stop writing canonical runtime truth directly into:
  - `GameState.player`
  - `GameState.world.rooms[*].item_ids`
  - `GameState.world.rooms[*].npc_ids`
  - `GameState.active_goal`
  - `GameState.world_package["goals"]`, `["story_plan"]`, `["llm_story_bundle"]` as truth sources
- Keep `world_package` only for:
  - bootstrap seed inputs
  - presentation cache
  - non-canonical surface metadata

### Immediate anti-patterns to remove
- `rebuild_facts_from_legacy_views` at the start of runtime actions
- `sync_legacy_views` as part of every commit
- `_goal_bundle` / `_story_plan_bundle` fallback chains in `simulation.py`
- direct room/NPC/item mutation in `StoryDirector._apply_contacts_to_world` and `_apply_clue_placements_to_world`

## 6. Scene + Dramatic State Design
Add first-class canonical facts for scene/dramatic state. Suggested predicates:

- `current_scene(scene_id)`
- `scene_location(scene_id, room_id)`
- `scene_objective(scene_id, text)`
- `dramatic_question(scene_id, text)`
- `scene_pressure(scene_id, level)`
- `beat_phase(phase)`
- `beat_role(scene_id, role)`
- `current_obstacle_mode(mode)`
- `active_conflict(conflict_id)`
- `player_approach(mode)`
- `npc_scene_goal(npc_id, text)`
- `npc_stance(npc_id, player, stance)`
- `npc_trust(npc_id, player, score_bucket)`
- `reveal_opportunity(thread_id, scene_id)`
- `scene_participant(scene_id, actor_id)`

Design intent:
- `progress` and `tension` stop being the main dramatic model and become derived/secondary metrics.
- `build_narration_context` should read scene facts first, not infer scene from room + raw events.
- NPC replies should key off `npc_scene_goal`, `npc_stance`, and `active_conflict`, not only nearby-room presence and a trust delta.
- `plot/beat_manager.py` should choose or advance beat roles based on dramatic facts, not only phase buckets.

## 7. Turn Pipeline Refactor
### Target hot-path loop
1. input gateway
2. deterministic command classification
3. one `TurnProposalV2` LLM call for ordinary turns
4. deterministic proposal validation
5. canonical fact commit
6. deterministic trigger / beat / timed-event execution
7. narration rendering from committed state
8. save/replay persistence

### Repository-specific orchestration changes
- Split `storygame.cli.run_turn` into:
  - `TurnGateway`
  - `TurnOrchestrator`
  - `NarrationRenderer`
  - `TurnPersistence`
- Parser handling remains only for:
  - `save`
  - `load`
  - `quit`
  - `help`
  - deterministic movement/inventory aliases that are normalized into the same turn-op contract instead of a separate authored experience
- Replace `simulation.advance_turn` as the default ordinary-turn path with a deterministic post-commit phase runner:
  - `TriggerEngine`
  - `BeatPolicy`
  - `TimedEventEngine`
- Keep `advance_turn` temporarily as a compatibility adapter until both surfaces use the new orchestrator.

## 8. LLM Integration Refactor
### Structured proposal schema
Replace the current split between `action_proposal` / `dialog_proposal` / ad-hoc envelopes with a single runtime contract, evolved from `storygame.llm.contracts.TurnProposal`:

```json
{
  "turn_id": "string",
  "mode": "scene|conversation|physical|social|investigation",
  "player_intent": {
    "summary": "string",
    "addressed_npc_id": "string",
    "target_ids": ["string"],
    "item_ids": ["string"],
    "location_id": "string"
  },
  "scene_framing": {
    "focus": "string",
    "dramatic_question": "string",
    "player_approach": "string"
  },
  "semantic_actions": [
    {
      "action_id": "string",
      "action_type": "move_to|take_item|give_item|show_item|inspect_item|question_npc|accuse_npc|use_item|trigger_scene_shift",
      "actor_id": "player|npc_id",
      "target_id": "string",
      "item_id": "string",
      "location_id": "string"
    }
  ],
  "state_delta": {
    "assert": [{"fact": ["predicate", "arg1", "arg2"]}],
    "retract": [{"fact": ["predicate", "arg1", "arg2"]}],
    "numeric_delta": [{"key": "metric", "delta": 0.05}],
    "reasons": ["string"]
  },
  "npc_dialogue": {
    "speaker_id": "npc_id",
    "text": "string"
  },
  "narration": "string",
  "beat_hints": {
    "escalation": "none|soft|hard",
    "reveal_thread_ids": ["string"],
    "obstacle_mode": "string"
  }
}
```

### Validation rules
- LLM may only reference visible/reachable entities unless it explicitly proposes a scene shift.
- Dialogue turns addressing a visible NPC must return that NPC as `npc_dialogue.speaker_id`.
- `narration` is presentation only; canonical change must already appear in `semantic_actions` or `state_delta`.
- Proposal validator rejects prompt-parroting dialogue, off-screen speakers, duplicate item placement, impossible movement, and invalid beat hints.

### What moves out of the LLM
- item shorthand resolution
- visibility/presence checks
- trust/stance clamping
- trigger firing
- beat legality
- custody/location uniqueness
- save/load/replay bookkeeping

## 9. Opening / Bootstrap Refactor
### Current issue
`StoryDirector.compose_opening` currently lets bootstrap prose and clue placement rewrite facts after generation via `_reconcile_opening_facts` and related helpers. That is still "prose first."

### Target bootstrap flow
- Bootstrap LLM call returns a `BootstrapWorldProposal` with:
  - protagonist facts
  - cast facts
  - clue/item placement facts
  - goals
  - timed events
  - initial scene/dramatic state
  - opening prose draft
- Deterministic validator commits the fact proposal first.
- Opening prose is accepted only if it matches committed facts.
- If prose and facts disagree, bootstrap fails closed and retries/rejects before display.
- `StoryDirector` stays as the bootstrap/orchestration boundary, but it should no longer reconcile prose into truth.

### Repository-specific changes
- Remove the need for:
  - `StoryDirector._reconcile_opening_facts`
  - `StoryDirector._sync_opening_room_presentation`
  - `opening_coherence.cohere_opening_lines` as a truth-repair step
- Keep `opening_coherence_issues` as a validator/checker, not as a fixer.
- Keep separate surface adapters:
  - local web can use OpenAI/Ollama bootstrap
  - hosted demo must keep Cloudflare-compatible bootstrap
  - both consume the same canonical bootstrap fact contract

## 10. Freytag Operationalization
Freytag must move from "beat label + progress/tension" to "deterministic dramatic policy."

### Proposed behavior
- `beat_phase` determines allowed escalation/reveal ranges.
- `beat_role` determines what kind of turn consequence is favored:
  - exposition: orientation, relationship anchoring, lead surfacing
  - rising action: obstruction, counter-move, pressure, partial reveal
  - climax: confrontation, irreversible move, high-cost truth
  - falling action: fallout, pursuit, unraveling
  - resolution: closure, aftermath, remaining truth
- `scene_pressure` and `current_obstacle_mode` constrain NPC behavior and narration tone.
- `reveal_opportunity` and `reveal_schedule` gate hidden thread exposure.
- `npc_scene_goal` changes what an NPC will admit, dodge, or escalate.

### Concrete repo touchpoints
- Replace `plot.beat_manager.select_beat` random selection with a deterministic `BeatPolicy`.
- Move `_refresh_active_goal`, `_story_reveal_events`, and `_timed_story_events` out of `simulation.py` fallback logic and into a beat/scene service that reads facts only.
- Keep `engine.incidents` and `engine.triggers`, but make them consume scene/beat facts rather than raw progress alone.

## 11. Data Model / Schema
### Canonical fact ops
- `AssertFact(predicate, args...)`
- `RetractFact(predicate, args...)`
- `ReplaceUnique(predicate, key_args..., value_args...)`
- `AddMetric(metric_key, delta)`
- `EmitEvent(event_type, metadata)` as a derived artifact, not canonical state

### Scene state
- scene id
- location anchor
- participants
- objective
- dramatic question
- pressure level
- obstacle mode
- active conflict
- player approach

### Beat state
- current phase
- current beat role
- reveal budget / reveal schedule
- escalation budget
- irreversible choice marker
- resolution eligibility

### Trigger schema
Keep the current `storygame.engine.triggers` shape, but add:
- scene predicates
- beat predicates
- stance/trust predicates
- reveal-window predicates

### Public interface changes
- `storygame.llm.contracts.TurnProposal` becomes `TurnProposalV2`
- `storygame.engine.turn_runtime.execute_turn_proposal` becomes the sole ordinary-turn executor
- `storygame.llm.narration_state.extract_narration_fact_ops` becomes migration-only or debug-only
- `GameState.active_goal` becomes a projection of fact state, not a fallback store

## 12. Target Module Layout
Keep the current package split, but reorganize responsibilities like this:

- `storygame.engine.fact_store`
  - fact storage, indexing, query API
- `storygame.engine.fact_commit`
  - typed ops, commit authority, invariant validation
- `storygame.engine.fact_projection`
  - temporary object projections for legacy adapters
- `storygame.engine.scene_state`
  - scene/dramatic predicates and projections
- `storygame.engine.turn_orchestrator`
  - input classification, proposal validation, commit, trigger/beat execution
- `storygame.engine.turn_policy`
  - deterministic legality/presence/custody rules
- `storygame.engine.triggers`
  - keep, but consume canonical facts only
- `storygame.engine.incidents`
  - keep, but driven by beat/scene state
- `storygame.plot.beat_policy`
  - replaces today's random beat manager
- `storygame.llm.turn_generator`
  - one per-turn structured proposal call
- `storygame.llm.story_director`
  - bootstrap/replan only, not ordinary turns
- `storygame.llm.opening_validator`
  - bootstrap/opening consistency checker
- `storygame.cli`
  - surface adapter only
- `storygame.web_runtime`
  - shared surface adapter only
- `storygame.web` / `storygame.web_demo`
  - remain separate deployment surfaces

## 13. Incremental Migration Plan
### Phase 1: Canonical Commit Boundary
- [x] Introduce a validated canonical fact commit layer (`ValidatedFactCommitter`, `InvariantValidator`, `ProjectionUpdater`)
- [x] Route `engine.facts.apply_fact_ops` through the validated commit boundary
- [x] Route `engine.facts.replace_fact_group` / `set_active_story_goal` through the validated commit boundary
- [x] Remove `rebuild_facts_from_legacy_views` from the ordinary proposal path in `engine.turn_runtime.execute_turn_proposal`
- [x] Route bootstrap clue placement in `llm.story_director` through canonical fact commits instead of room-object mutation plus rebuild
- [x] Add invariant/regression tests for player-location uniqueness, item-container uniqueness, active-goal uniqueness, role exclusivity, and proposal-path fact authority
- [x] Route every remaining runtime mutation path through the validated commit boundary
- Goal: make one mutation gateway authoritative without rewriting the whole runtime.
- Files: `engine/facts.py`, `engine/state.py`, `engine/world.py`, `engine/rules.py`, `engine/turn_runtime.py`, `llm/story_director.py`
- Risks: hidden direct mutations to `rooms`, `player`, `active_goal`
- Tests: new invariant tests for item placement, NPC location uniqueness, role exclusivity, active-goal uniqueness
- Done criteria: every runtime mutation route goes through one validated fact commit service

### Phase 2: Scene/Dramatic Facts
- [x] Introduce canonical scene-state helpers and seed default/bootstrap states with scene and dramatic facts
- [x] Route `build_narration_context` through canonical scene facts with NPC stance/trust lookups
- [x] Make beat selection prefer canonical `beat_phase` / `beat_role` facts before legacy `progress` fallback
- [x] Add a fuller dramatic-policy module and route parser/proposal/freeform turns through it before beat selection
- [x] Move direct-address conversational behavior onto explicit scene facts (`player_approach`, `dramatic_question`, `beat_role`) beyond context shaping
- Goal: add first-class scene and dramatic state while keeping current gameplay working
- Files: new `engine/scene_state.py`, `plot/beat_manager.py` replacement, `llm/context.py`, `engine/simulation.py`
- Risks: narration context drift during transition
- Tests: scene fact projections, beat/scene transitions, direct-address NPC context tests
- Done criteria: `build_narration_context` reads scene facts; Freytag behavior no longer depends only on `progress`/`tension`

### Phase 3: Turn Proposal V2
- [x] Introduce `TurnProposalV2` shape in `llm/contracts.py` with compatibility parsing for legacy callers
- [x] Route freeform proposal construction through the V2 runtime contract
- [x] Route ordinary deterministic turns through proposal execution plus post-commit beat/event handling instead of `advance_turn`
- [x] Keep parser handling limited to control-plane commands while preserving deterministic movement/inventory/take/use affordances through proposal normalization
- [x] Add regression coverage for V2 contract parsing, V2 NPC dialogue surfacing, and no-`advance_turn` ordinary directional turns
- Goal: make ordinary turns uniformly proposal-first
- Files: `llm/contracts.py`, `engine/freeform.py`, `engine/turn_runtime.py`, `cli.py`, `engine/interfaces.py`
- Risks: breaking directional aliases and current freeform affordances
- Tests: conversational turns, physical action turns, no-parser-fallback tests, NPC speaker correctness
- Done criteria: ordinary turns no longer route through `advance_turn`; parser is control-plane only

### Phase 4: Bootstrap/Openings From Facts
- [ ] In progress
- [x] Canonical bootstrap clue placement now commits through the fact boundary
- [ ] Remove opening truth-repair helpers (`_reconcile_opening_facts`, `_sync_opening_room_presentation`) from the accepted-opening path
- [ ] Replace repair-oriented opening assertions with validator-oriented behavior
- Goal: remove prose-first opening reconciliation
- Files: `llm/story_director.py`, `llm/story_agents/agents.py`, `llm/opening_coherence.py`, `engine/world.py`, `web_runtime.py`
- Risks: stricter bootstrap validation may increase bootstrap failure rate before prompts are adjusted
- Tests: varied opening coherence categories, opening-to-fact parity, hosted/local surface compatibility
- Done criteria: accepted opening prose never mutates canonical truth after the fact

### Phase 5: Freytag Operationalization
- [ ] Not started
- Goal: replace beat metadata with deterministic dramatic policy
- Files: `plot/beat_manager.py`, `engine/incidents.py`, `engine/triggers.py`, `engine/simulation.py`, `llm/context.py`
- Risks: over-constraining scenes and making turns feel repetitive
- Tests: reveal timing, escalation legality, scene-pressure-driven NPC behavior, beat-role consequence tests
- Done criteria: beat phase measurably changes scene framing, reveal timing, obstacle mode, and allowed consequence classes

### Phase 6: Latency + Surface Cleanup
- [ ] Not started
- Goal: hit the hot-path budget and remove normal-turn multi-agent/coherence overhead
- Files: `cli.py`, `llm/coherence.py`, `llm/story_director.py`, `web_runtime.py`, `web.py`, `web_demo.py`
- Risks: losing some prose polish during transition
- Tests: turn-path call counting, fail-closed behavior, web surface parity, hosted-demo adapter coverage
- Done criteria: ordinary turns use one LLM call on the fast path, optional second only on recoverable failure

## 14. Testing Strategy
### Invariant-Based Testing
Shift tests toward commit-boundary categories, not transcript strings. The strongest tests should validate:
- fact cardinality
- fact exclusivity
- presence/visibility legality
- narrative/rendering parity with canonical facts
- replay stability from canonical artifacts only

Add repo-level enforcement:
- add `--cov-fail-under=90` to `pyproject.toml`
- keep branch coverage
- add a focused invariant test module around the new commit service

### From Transcript Bugs to Architectural Invariants
| Failure | Invariant | Enforcement layer | Generalized test |
|---|---|---|---|
| "Daria holds the ledger page" and "ledger page is on the ground" both appear | An item has exactly one container at a time: room, player, NPC, or hidden-offstage location | `ValidatedFactCommitter` | Parameterized test over all item move/custody ops and opening/bootstrap proposals |
| NPC replies while not present | A visible conversational speaker must be present in the current scene | proposal validator + scene membership validator | Direct-address tests for visible, absent, moved, and ambiguous NPCs |
| Assistant is described as suspect in opening | Exclusive role facts cannot conflict without an explicit role-change event | bootstrap validator | Generate mixed contact/assistant/suspect assignments and assert rejection unless a role-change fact exists |
| Opening prose says assistant is beside player while facts place them elsewhere | Opening text must be a projection of committed facts, not a correction of them | opening validator | Build bootstrap facts with mismatched opening text and assert fail-closed bootstrap |
| Accepted narration says NPC takes the key but no canonical op exists | Prose cannot introduce canonical state outside structured proposal/commit | turn proposal validator | Accept narration with/without corresponding `semantic_actions` and assert only the latter can commit |
| A clue is both discovered and still unclaimed as hidden scene evidence in incompatible ways | Discovery, custody, and environment placement must remain globally consistent | fact commit layer + clue policy | Sequence tests across inspect/take/give/hide/reveal operations |

### What to keep from the current suite
- `tests/test_fact_runtime.py` already points in the right direction for custody/location invariants
- `tests/test_turn_runtime.py` already proves narration-only text should not mutate state
- `tests/test_web_surface_parity.py` correctly protects the shared surface contract
- `tests/test_opening_coherence.py` and `tests/test_story_director_orchestration.py` provide good failure categories, but their repair-oriented assertions should become validator-oriented assertions

## 15. Latency Strategy
### Hot-path design
- One LLM call per ordinary turn in `llm.turn_generator`
- Optional second call only when:
  - the first result is non-JSON / contract-invalid
  - deterministic validation returns a bounded revision request
- No multi-critic, judge, editor, and extractor chain on ordinary turns

### Call budget
- Ordinary turn fast path: 1 call
- Ordinary turn recovery path: 2 calls max
- Bootstrap: 1 structured bootstrap call, optional 1 bootstrap validation/critique call
- Major replan: 1 call

### What moves to deterministic code
- visibility/presence checks
- map legality and movement
- item resolution/shorthand resolution
- container/custody uniqueness
- clue discovery bookkeeping
- trust/stance bounds
- trigger firing
- beat advancement
- timed events
- save/load/replay artifacts

### Repository-specific latency cuts
- remove `build_default_coherence_gate()` from the ordinary-turn hot path in `cli.run_turn`
- stop doing `extract_narration_fact_ops` on every accepted narration
- keep `StoryDirector` off the ordinary-turn path
- preserve `web` vs `web_demo` differences below the adapter boundary only

## 16. First Refactor To Implement
### Highest leverage, minimal disruption
Implement a validated canonical commit layer and route all state mutation through it.

Progress:
- [x] Implement validated canonical commit layer
- [x] Move uniqueness-sensitive commit rules out of ad-hoc `apply_fact_ops` branches
- [x] Change `storygame.engine.turn_runtime.execute_turn_proposal`
- [x] Change `storygame.llm.story_director._apply_clue_placements_to_world`
- [ ] Change `storygame.engine.rules.apply_action`
- [ ] Change `storygame.llm.story_director._apply_story_bundle_facts`
- [ ] Change `storygame.cli.run_turn` narration commit site

### Concrete sketch
- Introduce `FactCommitter` and `InvariantValidator` around the existing `apply_fact_ops` logic.
- Move today's hidden uniqueness rules from `apply_fact_ops` into explicit invariant checks:
  - player has one location
  - NPC has one location
  - item has one container
  - active goal has one value
  - role exclusivity rules
- Change these callers first:
  - `storygame.engine.rules.apply_action`
  - `storygame.engine.turn_runtime.execute_turn_proposal`
  - `storygame.llm.story_director._apply_story_bundle_facts`
  - `storygame.llm.story_director._apply_clue_placements_to_world`
  - `storygame.cli.run_turn` narration commit site
- Leave projections in place temporarily, but make them read-after-commit only.

### Why this is first
It directly attacks issue #1 and issue #4 without forcing a full rewrite. It also makes every later change easier:
- scene state can be added canonically
- bootstrap can validate facts before prose
- turn proposals can commit richer consequences safely
- parser and proposal paths can share one authority

## 17. Tables
### Table A
| Concern | Current module | Problem | Target module | Phase |
|---|---|---|---|---|
| Canonical truth | `engine.state`, `engine.facts`, `engine.world`, `llm.story_director` | truth split across objects, facts, bundle metadata, repair logic | `engine.fact_store` + `engine.fact_commit` | 1 |
| Ordinary turn routing | `cli.run_turn`, `engine.simulation`, `engine.freeform` | dual parser/proposal architecture keeps parser dominant | `engine.turn_orchestrator` | 3 |
| Freeform consequences | `engine.freeform` | rich inputs collapse to flags/trust deltas | `engine.turn_policy` + `llm.turn_generator` | 3 |
| Opening/bootstrap | `llm.story_director`, `llm.story_agents.agents`, `llm.opening_coherence` | prose-first reconciliation mutates truth after generation | `llm.story_director` + `llm.opening_validator` | 4 |
| Freytag behavior | `plot.beat_manager`, `engine.simulation`, `engine.incidents` | beat is mostly metadata/random selection | `plot.beat_policy` + `engine.scene_state` | 5 |
| Narration/state boundary | `cli.run_turn`, `llm.narration_state` | narration still backfills state | `llm.turn_generator` + deterministic commit | 3 |
| Latency | `cli.run_turn`, `llm.coherence`, `llm.story_director` | multi-stage narration/coherence and bootstrap chain overhead | `llm.turn_generator` fast path | 6 |
| Surface parity | `web_runtime`, `web`, `web_demo` | easy to over-centralize and break deployment differences | keep separate surface adapters over shared core | 6 |

### Table B
| Invariant | Why | How to test |
|---|---|---|
| Item has one canonical container | prevents duplicate custody/location contradictions | commit-layer parameterized tests across assert/retract/transfer/bootstrap ops |
| NPC speaker must be scene-present | prevents off-screen dialogue and wrong-speaker replies | direct-address turn tests with visible/absent/ambiguous NPCs |
| Opening text matches committed facts | prevents prose-first runtime truth | bootstrap validator tests with contradictory openings |
| Narration cannot add uncaptured state | enforces propose -> validate -> commit -> narrate | turn proposal tests with matching vs missing state deltas |
| Role exclusivity is explicit | prevents assistant/suspect drift | bootstrap and replan tests with conflicting roles |
| Active goal is single canonical fact | prevents fallback drift between facts and strings | save/load + render tests that read only fact-backed goal |

## Assumptions And Defaults
- This plan is based on static inspection of the repo, `docs/PRD.md`, and the current tests; I did not execute the full suite or profile runtime latency in this pass.
- `storygame.web` and `storygame.web_demo` remain separate surface adapters.
- No rewrite-from-scratch: the plan preserves working pieces and migrates in place.
- New work should avoid adding more dataclass-shaped mutable truth carriers; use typed contracts and adapters at boundaries instead.
