# Richer narration with bounded invention

Status: in progress, 2026-11-02. Branch `richer-narration-1`.
Steps 1, 2a and 2b are done (see Progress). Resume here: step 2c (the
`embellishments` reply field, typed boundary, pre-commit check, post-capture commit,
opening) then 2d (refuse unknown ordinary things, route facet-matching conditions). This change spans all narration paths and
all nine scenes; shared runtime must remain story-agnostic.

## Progress

- **Step 1, worldkeeper layer: done, `c4f80d8f`.** New `worldkeeper/incidental.py`
  (policy, templates, per-turn/scene/game allowances, immutable facets,
  all-or-nothing batch on a cloned backend, resolver never called), a `clone()` on
  `FactBackend`/`MemoryBackend`, and `wk_incidental`/`wk_facet`/`wk_fixed` facts.
  Tests: `packages/worldkeeper/tests/test_incidental.py` (fixed acceptance file,
  tests-first commit `69b75213`, fixture fix after). Verified: 112 worldkeeper tests,
  Ruff, and five storygame world suites; Ringer check also ran the quick tier.
  Not yet done: the storygame adapter (`world_model.py`) that builds a policy from
  the package, and routing any narrator creation through `apply_embellishments`.
  Full suite and coverage not run (run once at the end).
- **Step 2a/2b done, `e16335d7`:** worldkeeper cleanup (no placeholder facts, one clone
  per batch) and the package side: `props:` in world.yaml, per-item `facets` and
  `authored_facets`, scene `prop_pool`, loader checks, `incidental_policy_for(package)`
  in `storygame/runtime/world_model.py`, and `docs/markdown-story-authoring/incidental-props-and-facets.md`.
  Tests: `tests/test_incidental_package.py` (fixed acceptance file) plus the quick tier
  (3625 passed). New test files must be registered with
  `scripts/regen_shard_durations.py --missing-only` (it refuses while a test cannot import).
- **Step 2c/2d not started.** Verified facts that shape them: the engine retries a rejected
  narration inside `_turn_active`'s attempt loop (before commit), so embellishments are
  checked there with `check_embellishments` on the candidate state, raising a
  `ProposalValidationError` (retry, then fail closed); they are committed right after
  `capture.after_commit` (after item facts and scene placements), rolling the turn back like
  `observation_diverged` if they drift. `engine.opening()` runs once per session and
  `web_demo` saves the state right after, so the opening applies its embellishments to that
  state (decision 1A). Decisions taken 2026-11-02: 1A, 2A (refuse unknown ordinary things,
  measure slips first, only when the package declares a policy), 3A (facet-matching phrases
  become facets; existing conditions unchanged; new props take facets only).
- Ringer notes: the first run failed twice on my spec (a `notes.md` the check
  forbade; a test fixture whose alias contradicted a template name, which the worker
  worked around by editing the schema). Fixed in the fixture and spec; patch rejected.
- Open questions for step 2: where the narrator-facing allowance counts reset
  for the opening (counted as a turn); how legacy `item_facts` creation of unknown
  things is closed without breaking authored-name matching; the compatibility policy
  for existing free `condition` strings.

## Recommendation and evidence

Allow the narrator to introduce a few persistent, harmless props and enrich
existing objects with persistent cosmetic traits. Use package-approved choices
for what can exist; let the model choose when to introduce them and write the
prose freely. This bounds consequences without requiring authors to place every
incidental object beforehand. Arbitrary free-text invention plus a model's
claim that it is harmless is not a reliable safety boundary.

At reviewed HEAD `398b88c4`, `cloudflare.py` forbids new objects in both turn and
opening rules. Yet `ItemFactsProvider.apply_item_facts()` can create unknown
things and places, and `_apply_state()` stores unmatched state text as free
conditions. `World.create()` checks structural validity, not invention budgets;
`World.set_conditions()` limits length/count, not meaning. Build on these paths,
but close those bypasses before relaxing prompts. Existing uncommitted changes
in `model.py` and `item_facts.py`, plus their new tests, belong to other work:
preserve and reconcile them before implementation.

## Contract

- **Proposed defaults:** at most one new incidental object per accepted turn,
  three per scene over its lifetime, twelve per game. Opening counts as a turn.
  Revisit, movement, disposal, retries and save/load never replenish allowances.
  Existing objects and aliases consume no new allowance. Zero is valid; never
  fill a quota merely because space remains.
- **Safe props:** immutable package templates define permitted names, ordinary
  `thing` kind, allowed parent scope and basic handling. Scene data selects a
  small eligible pool. Each template may instantiate once per scene. No invented
  places, openings, containers, characters, tools, credentials, readable clues,
  resources or items required for progression through this channel. Review pools
  against each scene's puzzles; “ordinary object” alone does not mean harmless.
- **Richer characteristics:** package-approved facets such as color, surface
  finish and decorative pattern; at most three persistent facets per object,
  with one value per facet. Authored values win. New values are selected from
  that object's allowed palette and then stay stable. Do not infer material
  strength, capacity, damage, working status, inscriptions, ownership, history
  or hidden contents from cosmetic traits. Functional changes still use declared
  axes and existing consequence validation.
- **Interaction:** incidental props can be examined and, if their template
  permits, carried, dropped or given through normal world operations. They
  grant no capability, knowledge, dependency satisfaction or route. A player may
  attempt creative use; ordinary outcome validation must establish its effects
  independently. Never report an unearned solution because a prop was present.
- **Continuity:** accepted props and traits are facts, shown again only when
  relevant and visible. No transcript-derived truth. Mere phrasing, metaphor and
  sensory emphasis need not persist, but concrete claims about an object's
  enduring properties must be captured. Never describe a new prop omitted from
  the structured proposal.

## Implementation

1. **Constrain the world model first.** In `packages/worldkeeper`, add immutable
   policy/template definitions and `World` operations to propose/check/create
   incidental objects and set cosmetic facets. Record origin, originating scene,
   template identity and allowance consumption as facts. Persist consumption
   even after disposal. Validate the whole batch on a clone, including nested
   contents and new names used as parents; require existing legal visible
   parents and respect hidden/exhausted/complete-content boundaries. Keep
   generic `World.create()` for trusted seeding, but route every narrator-driven
   creation through the constrained operation. Do not globally disable unrelated
   existing character/group behavior: audit its separate authorization and ensure
   it cannot be reached by cosmetic proposals. Put all world-only checks/tests
   here, with `storygame/runtime/world_model.py` only adapting facts/package data.

2. **Add package policy and atomic capture.** Extend the typed story package and
   Markdown compiler with optional scene prop pools and per-item facet palettes;
   absent policy means no new enrichment. Validate references, collisions with
   declared names/aliases, template kinds and contradictory facets at load time.
   Add optional `embellishments` to the existing narration reply: `props` entries
   select a supplied template name and parent name; `traits` entries name an
   existing object, facet and supplied value. Models receive readable labels,
   never internal IDs. Normalize at the typed JSON boundary. In `item_facts.py`
   and `capture.py`, resolve existing names first, coalesce references to approved
   new props, validate enrichment together with the normal projected turn, then
   commit once. Reject unauthorized creation through legacy `item_facts` too.
   Prevent unmatched `state`/`condition` strings from bypassing facet or axis
   rules; retain supported existing conditions via an explicit compatibility
   policy. Never silently discard a rejected detail while displaying its prose.
   Use the existing shared recovery allowance; exhaustion rolls back the entire
   turn, including budgets. Preserve existing save integrity/version rules.

3. **Give every narration path richer material.** Add one shared enrichment
   projection/rule helper for `_turn_rules`, `opening()`, `_system_prompt`,
   `_section_user_prompt`, `_scene_setting` and `_recover_malformed_response`.
   Supply relevant established traits, eligible prop choices and remaining
   allowance. Replace the blanket object ban with the constrained permission;
   preserve clue, concealed-content and topology restrictions. Use short plain
   instructions per the narrator-writing guide. Encourage one or two concrete
   sensory details tied to the action, spatial context and an observable response;
   reuse established details and vary emphasis rather than spawning new nouns.
   Do not force length, extra action, new events or repetitive description on
   brief turns. Keep existing call budgets and model settings. Extend existing
   prose validation/judge coverage to detect uncaptured props, invented functional
   properties and prose/proposal disagreement; never treat model self-labelling
   as proof of safety or add regex extraction of world state from prose.

4. **Author and qualify across the game.** Review each scene's visible objects,
   puzzles and empty-search boundaries; add a small compatible prop pool and
   useful facet palettes in authored sources. Include an unrelated synthetic
   package to prove portability. Update the grounding guide's blanket declaration
   rule to distinguish authored objects from runtime-approved incidental objects,
   and document the new contract in the PRD/authoring guide. Preserve protected
   reveals and delivery text. Update this plan after each completed step with
   commit, checks, remaining work and Resume here.

## Acceptance and verification

- Worldkeeper tests: all limits, alias deduplication, illegal parents/kinds,
  immutable traits, disposal/revisit/save-load continuity, and exact rollback.
  Runtime tests: opening/normal/handoff/recovery parity, legacy-field bypasses,
  malformed/omitted proposals, empty and hidden containers, authored-state
  precedence, and attempts to use cosmetics or props as puzzle solutions.
- Follow `docs/testing-runbook.md` for focused checks and final suite/CI; extend
  existing tests where possible. Capture shipped prompts with network stubbed.
  Use imperative player inputs such as “Examine the cup.” and “Pick up the cup.”
  in fixtures that actually declare or approve that object.
- Prepare matched baseline/candidate samples spanning every scene, opening,
  inspection, dialogue, action and transition, plus a carried full-game run.
  Freeze settings, rubric and cost estimate before any billed evaluation.
  Require zero observed unauthorized creations, functional inventions, leaks or
  continuity losses; counts must stay within limits. Blind comparison should
  prefer candidate richness on at least two-thirds of paired samples, with no
  scene consistently worse and no increased repetition. Report recovery rates,
  latency and cost separately; preserve the under-ten-second normal-path target.
  These are proposed gates, not measured results or proof of universal safety.
- Release only after deterministic checks and model evaluation pass, followed
  by the repository's SHA-bound staging workflow. Planning authorizes no paid
  runs or production promotion. This handoff changes documentation only; no
  implementation, tests or live model calls have been performed.
