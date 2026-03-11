# World Builder Plan

## Summary
- [ ] Define and implement a high-flexibility world builder pipeline that generates playable story worlds from genre-selected outlines, runs gameplay on a fact-based KB, preserves rich roleplay dialog, and uses deterministic validation/policy gates for safe state updates.
- [ ] Target artifact path: `.plans/world_builder.md`.

## Key Changes
- [x] Introduce a pregame generation pipeline:
- [x] Ask player for `genre` plus optional `tone` and `session_length`.
- [x] Select matching outlines from `story_outlines.yaml`.
- [x] Select a compatible plot-curve template from `plot_curves.yaml`.
- [x] Generate a world package in one pass from outline+curve: entities, map, goals, beat candidates, item graph, and trigger seeds.

- [x] Replace object-centric runtime world state with KB facts:
- [x] Store dynamic simulation truth as predicates only.
- [x] Keep events/triggers, but convert effects to fact operations: `assert`, `retract`, `numeric_delta`.
- [x] Make command handlers query facts (`inventory`, movement, social state, goal status) instead of mutating nested objects directly.

- [ ] Keep roleplay flexibility for non-command input:
- [ ] Parse known commands first.
- [ ] Route parse failures to `freeform_roleplay`.
- [ ] LLM returns in-character response plus constrained action proposal.
- [ ] Engine maps proposal through policy/rules into approved fact updates.

- [ ] Add predicate schema and rule packs:
- [ ] Use a layered ontology: core predicates + genre predicate packs + story extensions.
- [ ] Define predicate-schema-rule bindings in external YAML.
- [ ] Disallow unconstrained runtime predicate invention.

- [ ] Add NPC voice-card model with policy constraints:
- [ ] Represent NPC behavior as facts with two classes: inviolable core traits and flexible adaptive traits.
- [ ] Keep a small typed presentation layer for narration stability.
- [ ] Allow adaptive trait and goal changes through bounded policy checks.

- [ ] Add planning adaptation for unexpected player behavior:
- [ ] Detect major divergence from current beat realization.
- [ ] Re-plan near-term beat realizations while preserving curve shape constraints.
- [ ] Keep story solvable by opening alternate evidence/progression routes.

## Public Interfaces and Types
- [x] `story_outlines.yaml`: genre-indexed story seeds and framing metadata.
- [x] `plot_curves.yaml`: reusable pacing/beat-shape templates by genre and length.
- [x] `predicates/core.yaml`: global predicate definitions, arity, arg types, invariants.
- [x] `predicates/genres/<genre>.yaml`: genre-specific predicate extensions.
- [x] `rules/core_rules.yaml`: cross-genre condition->effect rules.
- [x] `rules/genres/<genre>_rules.yaml`: genre behavior mappings and consequences.
- [x] `npc_voice_cards.yaml`: core identity traits, adaptive state defaults, dialog policy limits.
- [x] LLM output contracts:
- [x] `ActionProposal` for interpreted player intent.
- [x] `DialogProposal` for in-character response.
- [x] `StateUpdateEnvelope` for approved fact deltas before commit.

## Test Plan
- [ ] Generation validity:
- [ ] Generated world package always validates against schema contracts.
- [ ] Generated map/goals/beats are internally consistent and playable from start state.
- [ ] Runtime safety:
- [ ] Invalid fact updates are rejected with typed errors and no partial commits.
- [ ] Rule conflicts resolve deterministically per declared precedence.
- [ ] Freeform roleplay behavior:
- [ ] Non-command text yields in-world dialog, not generic rejection, unless impossible by policy.
- [ ] Allowed social acts produce bounded, schema-valid state changes.
- [ ] Story adaptation:
- [ ] Unexpected actions trigger local re-planning and preserve forward progress paths.
- [ ] Curve adherence stays within soft pacing constraints over multiple divergences.
- [ ] NPC coherence:
- [ ] Core traits remain unchanged without explicit authorized narrative events.
- [ ] Adaptive traits evolve within per-turn and per-session bounds.

## Assumptions and Defaults
- [ ] Replay determinism is not a product requirement for this phase.
- [ ] Freytag is used as soft scaffolding via curated curve templates, not hard graph enforcement.
- [ ] YAML is the primary declarative source for predicate/rule packs and generation inputs.
- [ ] LLM may propose updates, but only engine-validated updates are committed.
- [ ] This plan is decision-complete and intended to be saved as `.plans/world_builder.md` once execution mode permits file edits.
