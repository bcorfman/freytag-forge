# External Story-Data Migration Plan

## Objective

Make every story-specific world, opening, character, knowledge, document, and
presentation decision declarative validated package data. Shared runtime code
must only load package data, realize it into canonical facts, validate generic
invariants, resolve typed player intents, and render fact-backed projections.

This migration applies to every genre in `data/story_outlines.yaml`; mystery is
an initial fixture, not a special runtime path.

## Non-negotiable boundaries

- Facts remain the sole mutable runtime authority.
- Story packages are validated inputs; they never mutate runtime truth directly.
- No shared module may branch on a story name, character name, room id, item id,
  vehicle type, or genre to author prose, setup, or a player action.
- Opening prose, room text, NPC dialogue, and document summaries are projections
  of observer-permitted committed facts.
- Generic policies may validate categories such as custody, exposure, document
  knowledge, map reachability, and NPC availability, but never individual named
  examples.

## Phase 0 — Baseline and inventory

### Work

- [x] Add a static audit test that reports story-specific string/identifier branches
  in `storygame/engine`, `storygame/llm`, and `storygame/cli.py`.
- [x] Classify each current branch as generic policy, temporary compatibility path,
  or authoring data to migrate in [`docs/external-story-data-inventory.md`](../docs/external-story-data-inventory.md).
- [x] Record baseline package projections and fixed-seed opening/turn transcripts for
  mystery, fantasy, sci-fi, and romance fixtures in [`data/phase0_baseline.json`](../data/phase0_baseline.json).

### Exit criteria

- [x] Every known embedded story element has an owner phase and replacement schema.
- [x] The audit allows only documented generic policy and temporary compatibility
  seams, with a removal date/phase.

## Phase 1 — Package schema and validation

### Work

- [x] Extend the package schema with declarative sections for:
  - map rooms, paths, room presentation, and spatial item placement;
  - characters, traits, appearances, roles, relationships, scene purposes, and
    initial epistemic facts;
  - items, document/reveal contracts, initial custody/state, and affordances;
  - opening setup, arrival order, public briefing, pending knowledge, and
    protected knowledge;
  - intent aliases and typed effect/reveal templates.
- [x] Load these sections from external YAML/package files and validate references,
  cardinality, schema shape, and cross-section consistency before realization.
- [x] Keep `opening_setup.yaml` as a compatibility input only while its fields are
  absorbed into the package schema.

### Exit criteria

- [x] Invalid ids, duplicate custody, missing referenced NPCs, invalid map paths,
  and protected facts exposed as public briefing fail package validation.
- [x] At least one non-mystery package declares every new section.

## Phase 2 — Generic world realization

### Work

- Replace `world.py` mystery branches with one package-to-facts realization
  service.
- Realize room names/descriptions, items, initial custody/state, characters,
  relationships, scene purposes, opening contexts, and case/document facts from
  package data.
- Remove hard-coded Daria, mansion, sedan, case-file, ledger-page, and
  protagonist setup from runtime realization.

### Exit criteria

- Two packages with different rooms, contacts, vehicles/documents, and opening
  order initialize through identical engine code.
- No `genre == "mystery"` setup branch remains in `world.py`.

## Phase 3 — Generic presentation and opening contracts

### Work

- Move room-copy, item-location, NPC focus, name-introduction, and opening
  briefing constraints into generic fact-aware presentation policies.
- Package data supplies room copy, short/long presentation, document visibility,
  active NPC scene purpose, and public briefing content.
- Retire front-steps/mansion-specific CLI copy and named opening-coherence rules.

### Exit criteria

- Openings cannot repeat room/map content, disclose protected document facts, or
  contradict custody/knowledge in any fixture.
- A full-name introduction establishes a stable unambiguous display name across
  opening, room, narration, and dialogue without story-specific exceptions.

## Phase 4 — Documents, affordances, and semantic intents

### Work

- Replace `case_file`/`ledger_page` intents and regexes in `freeform.py` with
  package-declared readable-item/reveal contracts.
- Generalize vehicle, door, and location phrase handling through visible-item and
  exit affordance data.
- Ensure reading any declared document commits its configured discovery,
  knowledge, and context facts through typed policy.

### Exit criteria

- Mystery documents, fantasy scrolls, sci-fi logs, and romance letters use the
  same intent/effect machinery.
- No item id or setting noun appears in shared freeform routing or effect code.

## Phase 5 — Generic coherence and environmental policy

### Work

- Replace named front-steps/ledger/Daria checks with generic predicates for
  exposure, weather, fragility, custody, access, and observer knowledge.
- Move ambient-source mappings and geography-specific text to map/package data.
- Keep only generic validators for physically impossible staging, role drift,
  duplicate location/custody, and knowledge leakage.

### Exit criteria

- Equivalent invalid staging is rejected for multiple genres without named-item
  logic.
- Ambient and room presentation derive only from map and item facts.

## Phase 6 — Remove compatibility paths and certify migration

### Work

- Delete legacy mystery setup, item aliases, prose, and fallback branches after
  package parity is proven.
- Update contributor documentation and the static audit so new embedded
  story-specific runtime data fails CI.
- Run full evaluation fixtures, replay/save-load checks, local/hosted surface
  parity, and package validation across all genres.

### Exit criteria

- `rg`/static audit finds no named story entities or genre-authored presentation
  branches in shared runtime modules.
- All packages initialize, play, save/load, and render through the same generic
  contracts.
- `TMPDIR=/tmp uv run pytest -q` passes with coverage at or above 90%.

## Delivery order

Complete Phases 0–2 before changing player-facing behavior broadly; then Phases
3–5; remove compatibility code only in Phase 6 after cross-genre regression
coverage proves package parity.
