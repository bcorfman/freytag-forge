# Richer narration with bounded invention

Status: in progress, 2026-11-02. Branch `richer-narration-1`.
**Direction change (2026-11-02, Brandon):** richness comes from the plot itself, not runtime embellishment.
The current story is treated as an outline and drafted richer, scene by scene, in `plot.md` first.
First slice: `.plans/richer-plot-1a-slice.md` (draft awaiting his reaction). Step 3 below (prompt work)
and step 4 (prop pools) are deferred; steps 1 and 2 stay built and unused until then.
Steps 1, 2a, 2b, 2c and the condition routing of 2d are done (see Progress). Resume here:
the small cleanup listed under Progress, then step 3 (shared prompt helper for all six narration
paths, prose validation and judge coverage). Refusing unknown ordinary things waits for bench data.
The full suite with coverage has not been run yet; run it once at the very end. This change spans all narration paths and
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
- **Step 2c done, `0c5a3a46` (after `9679062a`):** `embellishments` reply field accepted by
  `ItemFactsProvider`, typed in `storygame/runtime/embellishments.py`, checked before commit inside
  the narration retry loop (`embellishment_rejected`/`embellishment_malformed` retry, then fail
  closed), committed after capture with a whole-turn rollback (`embellishment_diverged`), and applied
  by `opening()`. Tests: `tests/test_embellishments_capture.py` (23, fixed acceptance file).
  The worker's lines that cleared staged handoffs on any reply with embellishments were removed:
  they dropped authored reveals; the test that seemed to need them used a narration that skipped a
  scheduled handoff turn. A package with no policy rejects any embellishments. Prompts are untouched,
  so live behavior is unchanged until step 3.
- **Step 2d, condition routing done, `5a926922`:** `World.route_condition_phrases` (worldkeeper) and
  `_apply_state` (storygame). Under a package policy, a phrase equal to exactly one approved facet value
  becomes that facet; the rest stay conditions on existing things; incidental props take facets only;
  every dropped phrase is an issue. Tests: `tests/test_condition_facets.py`,
  `packages/worldkeeper/tests/test_incidental_phrases.py`. No policy: behavior unchanged.
- **Slip measurement done (decision 2A, option a), 2026-11-02, offline from recorded bench rows:** of 2,202
  recorded turns, 75 (3.4%) resolved at least one name as new; 70 were plain things (many look like authored
  things the matcher missed, such as key, lantern, Michelle's laptop, Janus file). Upper bound only: older
  prompts and configs. Script: scratchpad `slips.py` (reads `match_info.resolutions` in `bench/results`).
- **Refusing unknown ordinary things is NOT built (blocked finding):** they are created in
  `apply_item_facts`, which runs in `capture.after_commit`, after the turn is applied, so the retry loop
  cannot refuse them; only `preview_commit` runs capture before commit, and only with an enforcing verifier.
  Options: (b) refuse inside the preview path (needs enforcement on), (c) post-commit rollback that fails
  the turn. Decide after a bench round on the step 3 prompts shows the real slip rate.
- **Routing cleanup done:** one shared `_apply_facet` for traits and phrase routing, the import moved to
  module level, and a facet-only reply keeps existing conditions. Known edge left: `_apply_state` still
  calls `set_conditions` when a phrase was only refused (`elif routed.leftover or routed.refused`), which
  clears existing conditions; the intended rule is to skip the call whenever nothing is left over. Add a
  test and fix it in the next code task.
- **Queued after the 1A propagation lands (Ringer, engine, tests first):** make
  `storygame/audit.py::_ambiguous_owned_item_findings` scene-aware. It currently flags a bare noun in any scene
  when an owned item of that name exists anywhere in the package (scene 1A was flagged for 1B's
  `michelle_photograph`). Count an owned item only for scenes where it is listed or placed. Brandon's rule:
  the engine scopes similar items by scene and asks to clarify; authors must not contort nouns. Then the 1A kitchen
  "snapshot" may be renamed "photograph" if he prefers it.
- **Richer 1A propagated, commit below the lint commit `945a7912`:** world.yaml, knowledge.yaml, storylets.md,
  storylet-routes.yaml, scene 1A front matter, and 24 files of pins; whole suite passes (3940). Audit deltas to
  tune: two new `beat_overprojection` findings (1A.3 projects at turn 2, reveal earnable at turn 3; 1A.4 projects at
  turn 2, reveal earnable at turn 4: align storylet windows or conditions), and 1A's estimated turn payload grew
  22,539 to 27,854 characters (the audit's budget is 12,000 and was already exceeded): check how the payload is
  bounded per turn before adding more per-scene material.
- **Owed next (Ringer):** rename the kitchen "snapshot" to "photograph" (Brandon's choice; name "lake photograph",
  scoped_aliases photograph and photo so 1B's michelle_photograph still resolves in its own scene) and drop the
  possessive in "On Kristin's truck radio ..." (the scene-aware lint no longer needs it).
- Decisions taken 2026-11-02: 1A, 2A (refuse unknown ordinary things, measure slips first, only when
  the package declares a policy), 3A.
- Ringer notes: the first run failed twice on my spec (a `notes.md` the check
  forbade; a test fixture whose alias contradicted a template name, which the worker
  worked around by editing the schema). Fixed in the fixture and spec; patch rejected.
- Open questions for step 2: where the narrator-facing allowance counts reset
  for the opening (counted as a turn); how legacy `item_facts` creation of unknown
  things is closed without breaking authored-name matching; the compatibility policy
  for existing free `condition` strings.

## Richness rules for every scene (standing; saved 2026-11-02)

Same list as the `richer-scene-checklist` memory. Apply to 1B through 3C.

1. Plot first, inside the scene; everything new is an optional storylet; Details lines hold 3 to 7 items; keep the 120-turn ceiling.
2. Plain names; no possessives or `owner:` fields to quiet the audit; the engine scopes by scene and clarifies; bare common words go in `scoped_aliases`.
3. Declare what the narrator invents anyway (recorded slips: paper, lock, splinters, lantern, key).
4. Storylets sharing a source beat share `earliest_turn`; `audit_package` `beat_overprojection` must not rise (1A's two older findings remain).
5. Prompt budgets are a test (`tests/test_prompt_budget.py`): narrator <= 5000 characters (worst case 6500), item-matching <= 3500, <= 30 listed things. Baseline: narrator 4.0 to 4.4k in all nine scenes, matcher 1.9 to 2.1k except 1A at 2.85k. The narrator sees only things the matcher resolved; the matcher lists every scene thing, so richer scenes grow it. If near the cap, compact the matching block and verify on the bench.
6. Check the physical logic of every clue and that scene frames agree with the plot.
7. Tests first, Ringer for code and tests, whole suite as the check, review each patch for possessives and over-broad renames.

## Step 3 proposal (needs Brandon's approval before any prompt edit)

Design rule from his memories: the narrator is a small non-reasoning model, rules often lose, and
handing it concrete material wins. So give it a short list and one example, not new prohibitions.

- **Where choices appear:** as dash-led lines in the varying CONSTRAINTS section (the same place that
  already says "Show these in your reply"), only when the package has a policy and allowance is left:
  `- You may add one small thing if it fits: tea cup (on the bench or in the parlour).`
  `- The tea cup can be white or blue.` One line per eligible template, at most three templates per
  turn, picked by what the scene and the player's action touch (same relevance bound as THINGS).
- **Established traits:** shown with the thing where the THINGS block already shows its condition,
  as `Looks: brown, worn` (stored facets plus authored values), so the narrator repeats them. Only for
  visible things; no transcript-derived truth.
- **Reply shape:** when choices are offered, the output example gains
  `"embellishments":{"props":[{"template":"tea cup","parent":"bench"}],"traits":[...]}`; without
  choices the example is unchanged and the narrator is not told the field exists.
- **One rule edit, built in one helper used by all six paths** (`_turn_rules`, `opening()`,
  `_system_prompt`, `_section_user_prompt`, `_scene_setting`, `_recover_malformed_response`): the
  existing line "Do not make up new objects, clues, or things inside containers." gets one added
  sentence only when choices are offered: "The only new thing you may add is one from the list." No
  other ban is relaxed (clues, containers, topology, protected reveals stay as they are).
- **Richness:** a separate, second arm, not part of the first candidate: "Add one or two small
  details of sight, sound or touch that fit what the player did." Reason: his memories show added
  rules can lower quality, so measure it alone against the props-and-traits arm.
- **Checks:** judge coverage for uncaptured props, invented functional properties and
  prose/proposal disagreement, using the existing capture judges (no regex over prose).
- **Evaluation (billed, needs his go-ahead):** frozen rubric and cost estimate first; arms are
  baseline, props-and-traits, and props-and-traits plus the richness line; paired samples across all
  nine scenes; gates as listed under Acceptance. Also read the real slip rate here (decision 2A).

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
