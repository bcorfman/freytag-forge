# Richer narration with bounded invention

Status: in progress. Last updated 2026-11-02 (end of the session). Branch `richer-narration-1` (HEAD `05f1f0b2` plus this note).
Whole suite at `05f1f0b2`: 3984 passed, 26 skipped, Ruff clean. The full suite with coverage has NOT been run; run it once at the very end.

**Direction (Brandon, 2026-11-02):** richness comes from the plot itself, not runtime embellishment. The current story is an outline;
Claude drafts it richer scene by scene, `plot.md` first, settling story problems itself and reporting afterwards. Steps 1 and 2 of
the original embellishment design are built but unused; step 3 (prompt work) and step 4 (prop pools) are deferred. The standing
rules for every scene are in "Richness rules" below and in the `richer-scene-checklist` memory.

## Resume here (in order)

1. **1B probe is run and read (2026-11-02); result is in `.plans/richer-1b-probe-prereg.md`.** Outcome: richness NOT supported yet and a
   defect found. The candidate never delivered the gate escape (0/4; baseline 3/4): every loss is `narration_known_term_leak` on
   "dead drop" (leak term of the 1A card reveal, unearned under the default `bare` bench entry; real-play effect is an unchecked hypothesis).
   The narrator also recites reveal statements as Brandon's dialogue, repeats the picnic image 3 times, and the engine delivery text
   repeats what the narrator just wrote. Brandon's rule (2026-11-02, `richer-means-added-value-not-more-stuff`): richer means details with a job.
2. **Next, in order:** (a) rerun only the candidate with `entry_state: thorough` as a second run (billed, about 350 neurons; ask Brandon);
   (b) read the recorded prompt and remove the doubled statement (SCENE fact plus "may say aloud"), so the narrator stops reciting it; tests
   first, through Ringer; (c) held items keep a one-line depiction (the narrator describes Michelle's face, contradicting the reveal);
   (d) give the picnic image a payoff or cut it; (e) rerun the candidate and rescore Q2, Q3, Q5. Not before 1C.
3. **Small owed follow-ups** (each a tests-first Ringer task): mark the 1A `lake_photograph` `fixed: true` (the narrator "moves" it
   in 3 of 4 replicates; harmless but recurring); replace the private `_matches_all` import in `storygame/runtime/knowledge.py` with a
   public helper from `candidate_matcher.py`; 1A keeps two older `beat_overprojection` findings (SL-1A-E earliest turn 1 against
   0 for its siblings); if the 1B probe shows invented photograph content, make held items keep a one-line depiction.
4. **Scenes 1C, 2A, 2B, 2C, 3A, 3B, 3C** (seven left). For each: read the scene in `plot.md`, write the richer beats (plot first,
   plain names, plant a payoff for each plant, Details lines of 3 to 7 items, keep the turn ceiling), write acceptance tests first,
   then one Ringer propagation task whose spec states every priority (-1 for ambient reveals), the exact evidence groups, and the
   lessons below; review the patch for possessives and over-broad renames; run the whole suite; then preregister and run a probe.
   Planted payoffs so far: the looping broadcast (1A radio, 1B loudspeaker) pays off in 3B/3C; Brandon mouthing the words and
   the keypad he never looks at pay off when his role surfaces (2B); the clipboard and skipped houses pay off in 2B's selection
   list; the lemon-cake calendar is a candidate private proof in 3A or 3C; Officer Reyes could glimpse Kristin again at a checkpoint.
5. **Still deferred:** refusing unknown ordinary things (blocked because item-facts capture runs after the turn is applied; the
   measured upper bound is 3.4 percent of turns and falling as scenes are authored); compacting the item-matching prompt if a scene
   nears its budget; embellishment prompt work (step 3) and prop pools (step 4).

**Where the tooling lives (outside the repo).** `~/dev/ringer-work/richer-narration-2/` holds every Ringer manifest
(`manifest_*.json`), check script (`check_*.sh`), `common.sh` helpers and run output. To start a new task, copy the closest manifest
(`manifest_rank.json` for an engine change, `manifest_1b.json` for scene data), copy its `check_*.sh`, update the fixed-test hash with
`sha256sum`, lint with `~/dev/ringer/ringer.py lint`, and run with `ringer.py run <manifest> --identity claude-orchestrator`
(background). A worker's own run cannot be trusted: always re-run the whole suite on the branch before committing. Ringer cannot
launch unsandboxed (billed) workers from Claude; bench runs are plain commands. Disclosure: two unplanned partial live bench runs
(about 20 to 30 requests) happened on 2026-11-02, recorded in `.plans/richer-1a-probe-prereg.md`.

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
- **Done, `945a7912` (was queued):** make
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
- **Done, `519a6c60` (was owed):** rename the kitchen "snapshot" to "photograph" (Brandon's choice; name "lake photograph",
  scoped_aliases photograph and photo so 1B's michelle_photograph still resolves in its own scene) and drop the
  possessive in "On Kristin's truck radio ..." (the scene-aware lint no longer needs it).
- **1A opening probe, 2026-11-02:** preregistered in `.plans/richer-1a-probe-prereg.md` (with Amendment 1 and a
  disclosure of two unplanned partial live runs, about 20 to 30 requests). Bench bug fixed (`e982d51a`: a walk between
  places in runtime mode). Smoke row (one candidate replicate, pre-fix) read by hand; it found the photograph invented
  as a landscape, the kitchen reveal delivered as one block, and Walt unreachable once the patrol entered; all fixed in
  `1bb68d81`. Full run (4 replicates per arm, 7 commands, baseline `richer-1a-baseline` vs `richer-1a-candidate`) is
  awaiting Brandon: Claude cannot launch an unsandboxed Ringer worker, so he runs the two bench commands himself with
  `!`; then Claude reads every turn and writes the result into the prereg.
- **1A neighbor fix applied, `b13ba90c`:** Walt's reveal now needs only two evidence groups, his placement text says he
  is the elderly neighbor, and the calendar is a paper calendar. The candidate arm is to be rerun (4 replicates, output
  `bench/results/richer-1a-probe/candidate-run2`) by Brandon, reported as a second run and not pooled.
- **1B in progress (2026-11-02):** plot prose committed (`128ff1f2`): an abandoned park (bicycle, empty dog leash, a picnic
  with one cup tipped and one half full), the looping loudspeaker with Brandon mouthing the words a half-beat ahead (plants
  his hidden role and the 3B/3C broadcast fight), an emergency-water thermos that corroborates his warning, and the keypad he
  never looks at plus a freshly oiled drain latch. Acceptance tests `tests/test_richer_1b.py` committed failing
  (`c3bad43d`); the propagation task carries the 1A lessons (plain names, scoped aliases, exact evidence groups, aligned
  windows). Check the 1B photograph depiction in the next probe: a held item shows only "Held by", so what it shows must
  live in its name or reveal text.
- **1B propagation partially landed, `e97be597`:** world, knowledge, routes, front matter and pins; the worker's priorities
  (1, 30, 30) were wrong and are now -1. Remaining: `tests/test_richer_1b.py` thermos and stranger tests and
  `test_hidden_bench_matcher_probe` wait on the evidence-ranking engine task (`tests/test_candidate_ranking.py`, committed
  failing). After it lands: offline replay, then the 1B probe (`.plans/richer-1b-probe-prereg.md`).
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
8. Optional ambient reveals use `relevance.priority: -1` and the spec says so; the projector offers four candidates ranked by established-and-mentioned, priority, id (and, once the ranking task lands, evidence match first). A worker's priorities of 1, 30 and 30 once crowded out story-critical reveals.
9. A held item shows only "Held by" to the narrator: put what it shows in its name or reveal text.
10. Probe each scene (preregistered baseline versus candidate, offline replay as smoke, every turn read).

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
