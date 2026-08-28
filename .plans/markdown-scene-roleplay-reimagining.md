# Markdown scene roleplay reimagining plan

## Goal

Rebuild Freytag Forge as a story-agnostic, LLM-driven roleplay engine whose
input is a Markdown plot such as `.plans/plot.md`, plus declarative Freytag
  pacing and a Markdown storylet companion. The player always plays the story's protagonist.
The engine keeps a validated mutable world model, decides when a scene may
advance, warns before a choice would make the authored story unsatisfiable, and
only gives the narration model the scene-relevant slice of world state.

Keep the existing Python 3.12/FastAPI/React/Cloudflare-worker/SQLite stack and
the core safety rule: state changes are provider proposals, locally validated
and atomically committed before the response is displayed.

## LLM-first turn authority

Except for persistence (`save` and `load`) and the explicit resolution of an
already-issued game-break warning, **every player roleplay input is sent to the
LLM**. There is no command parser for movement, talking, inspecting, using,
taking, attacking, waiting, help, quitting, or any other in-world action. The
engine must not maintain fixed action tables, keyword affordances, or
deterministic text-to-action normalization.

The engine's role on a normal turn is deliberately narrow: select the safe
scene-relevant fact/pacing context, call the LLM, validate the returned JSON
proposal, prevent an unsatisfiable authored story, commit accepted facts, and
render the LLM's narration. Facts and pacing constrain and enrich the LLM's
roleplay; they do not replace it with engine-authored gameplay.

Game-break confirmation is a necessary, narrow UI/API state choice rather than
a roleplay parser. Once the engine has issued a warning, the client submits a
typed `proceed` or `return_to_scene` resolution against that warning ID; no
ordinary natural-language input is interpreted until it is resolved. This is
the sole non-persistence exception required to deliver the requested explicit
player choice safely.

## Product decisions and boundaries

- Make a **scene** the unit of authored progression. It has an objective,
  location, participant and item references, completion triggers, optional
  exits, and a default next scene. Scenes are not parser commands or fixed
  player action menus.
- Keep the Freytag spine as declarative pacing data: exposition, inciting
  incident, rising action, crisis, climax, falling action, and resolution.
  Pacing events can advance or complicate a scene after declared conditions,
  deadlines, or pressure ranges are reached.
- Model storylets as optional, bounded scene situations. They can add pressure,
  reveal context, move an NPC/item, or satisfy a scene trigger, but never
  become a required fixed action table unless explicitly named as a scene
  completion trigger.
- Treat `.plans/continuity-initiative-storylets.md` as the prototype for the
  storylet source format. Its Scene/Storylets-for grouping, stable `SL-<scene>-<letter>`
  ID, source-beat link into `plot.md`, and its labelled sections (`Allowed
  scene`, `Available when`, `Participants / items`, `Dramatic purpose`,
  `Possible realizations`, `Effects`, `Completion`, `Abort`, and `Protected
  boundary`) are the author-facing contract. The loader extracts structured
  values from those sections; it never treats them as a player-visible menu.
- Treat a `game_breaking` proposal as a two-step decision, not an immediate
  rejection. Store an immutable pre-turn snapshot and return a warning with
  `proceed` and `return_to_scene` choices. `proceed` commits the validated
  destructive branch and marks the session as non-canonical; `return_to_scene`
  restores the snapshot and narrates the returned position. Do not silently
  undo a player action.
- A destructive action is game-breaking only when validation proves it makes a
  required future scene impossible: for example, leaving a scene before a
  required transition, destroying a required item with no declared substitute,
  or permanently incapacitating a required NPC without a declared fallback.
  Warnings must state the concrete dependency at risk, without revealing
  protected future plot details.
- No story, character, genre, or premise branches in shared Python/JS code.
  Kristin, Michelle, JANUS, and the Continuity Initiative belong solely in the
  Markdown/declarative package used as the acceptance fixture.
- The engine never selects or performs a player action. It may deterministically
  determine whether an LLM-proposed effect is legal, whether it triggers a
  pacing event, and whether it makes future scenes impossible.

## Target source package

Create a source directory such as `data/stories/continuity-initiative/`:

```text
plot.md                 # Human-readable premise, cast, and scene prose
pacing.yaml             # Freytag phases, scheduled/conditional world events
storylets.md            # Optional scene-local dramatic situations linked to plot.md
world.yaml              # NPC, item, location, and protected-knowledge seeds
```

`plot.md` remains the author-facing canonical plot and retains the headings in
the supplied file (`# Scene 1`, `## Scene 1A`, etc.). Add a small YAML
frontmatter block to each playable scene heading, containing stable `scene_id`,
`location_id`, `freytag_phase`, player objective, NPC/item IDs, entry text,
and its transition IDs. Keep narrative prose in Markdown; never infer runtime
IDs, requirements, ownership, or availability from prose. The compiler/parser
rejects missing or mismatched declarations.

Define the companion schemas as follows:

- `world.yaml`: locations; NPC characteristics and initial location/status;
  per-NPC knowledge/beliefs; items, characteristics, holder/location and
  destructibility; facts/flags; protected knowledge; and explicit substitutes
  or fallbacks for required NPCs/items.
- `pacing.yaml`: ordered Freytag phases, scene membership, target elapsed-game
  timestamps, pressure bounds, turns/deadlines, and typed world events. A
  world event has preconditions, effects, an optional scene transition, and a
  pacing window.
- `storylets.md`: use the exact companion structure in
  `.plans/continuity-initiative-storylets.md`, with Markdown links back to the
  relevant `plot.md` scene and source beats. Add two required labelled sections
  to each `SL-*` entry: **Pacing window** (`earliest`, `target`, and `latest`
  elapsed-game timestamps) and **Pacing impact** (`none`, `brief_delay`,
  `pressure_increase`, or `advance_readiness`). The prose in each existing
  labelled section remains author guidance; the loader converts its declared
  entity IDs, conditions, effects, completion/abort conditions, protected
  boundary, and pacing metadata into typed package data. Storylets remain
  optional, are capped by their local pacing window, and are never emitted as a
  player action menu.
- Scene transition declarations: source scene, target scene, one or more
  semantic triggers, and the required future dependencies that must remain
  satisfiable. A trigger is a typed predicate over committed world facts, not a
  substring match on player input.

Use Pydantic models to parse these files into one immutable `StoryPackage`.
Give every entity, event, storylet, transition, and trigger a stable ID. Build a
validated dependency index (required scene -> required NPC/item/fact and
fallbacks) while loading the package.

## Twenty-minute main-path pacing contract

The first story package must target **20 minutes of active play** for a
reasonable reader/typist following the main spine: approximately 18–22 normal
LLM turns, normally one to two turns per playable scene, plus no more than one
short optional storylet realization per scene. This is a target, not a real
time cutoff: measure active client time (excluding request latency, tab-hidden
time, save/load time, and game-break deliberation) and use turn count as the
server-side fallback. Never force a late player forward simply because their
typing is slow.

Maintain `story_elapsed_seconds` as a canonical pacing fact advanced after an
accepted normal turn by a package-declared narrative increment (nominally 60
seconds; 40 seconds for a terse continuation and 80 seconds for a substantial
scene-changing turn). Calibrate the Continuity Initiative package so its
efficient 18-turn, typical 20-turn, and reflective 22-turn main-spine paths
all land in the 19–21 minute target band. The frontend additionally reports
active elapsed time for analytics and adaptive prompting only; it is not an
authoritative mutation source. The pacing controller exposes the current target
window to the LLM and can fire only authored, validated pacing events—not
invent new events or choose the player's action.

Use these target timestamps for the Continuity Initiative main storyline:

| Active-play timestamp | Plot/Freytag milestone | Main-path scene window |
| --- | --- | --- |
| 00:00–02:00 | Exposition and inciting discovery: Michelle is gone; abduction and Continuity evidence become credible. | 1A |
| 02:00–04:30 | Rising action: dead drop, Brandon contact, and park escape. | 1B |
| 04:30–06:30 | Rising action: facility proof and the conspiracy's scale. | 1C |
| 06:30–08:30 | Rising action: prepare/enter under false identities. | 2A |
| 08:30–10:30 | Midpoint reversal: JANUS, Kristin-as-bait, Brandon's guilt, Sarah's resistance. | 2B |
| 10:30–13:00 | Crisis: purge clock, evidence-versus-rescue conflict, combined mission. | 2C |
| 13:00–15:00 | Final rise: reunite with Michelle, learn the stakes, begin uprising. | 3A |
| 15:00–17:30 | Climax: overload JANUS, seize broadcast, Brandon opens the relay. | 3B |
| 17:30–19:00 | Falling action: national exposure, archive decision, facility escape. | 3C (A–C) |
| 19:00–20:00 | Resolution: network fractures, reunion/new mission, Phase Two hook. | 3C (D–E) |

Each storylet must declare a timestamp window contained within its parent scene
window. Storylets that simply deepen atmosphere use `brief_delay` and have a
maximum one-turn realization; storylets that introduce an authored deadline or
threat use `pressure_increase`; and storylets that disclose already-permitted
information can use `advance_readiness`. At a scene's `latest` timestamp, the
engine does not skip player input or force an action: it activates an authored
pacing event/complication, gives that event to the LLM as urgent context, and
allows the LLM's next validated proposal to move the story forward. The next
scene's entry only occurs on a legal trigger or declared pacing transition.

## Runtime design

Replace the V2 `CompiledStory`/beat runtime with a smaller fact-backed state:

```text
RuntimeState
  story_package (immutable input identity)
  facts (only mutable authority)
  current_scene_id
  current_freytag_phase
  active_storylet_ids
  scheduled_pacing_event_ids / fired_event_ids
  recent_events and bounded summary (derived accepted-turn history)
  pending_game_break (snapshot ID + proposed effects + warning)
```

Represent NPC traits, knowledge/beliefs, items, locations, pacing events, and
player-caused story events as typed facts or typed entities referenced by facts.
Static characteristics stay immutable package data; their mutable status,
location, custody, health, knowledge, beliefs, and relationships are facts.
Do not retain an independently mutable `WorldState` compatibility object.

For each normal turn:

1. Recognize only explicit persistence requests (`save` and `load`). For every
   other normal input, call the model unchanged. A pending game-break warning
   is resolved only by the separate typed confirmation API action described
   above.
2. Build the scoped context: current scene contract; present/relevant NPCs;
   local items; active storylets; phase/pressure events; recent accepted events;
   a compact summary; and only player-safe knowledge.
3. Detect explicit references in player input to known off-scene NPCs, items,
   events, or locations. Add only the matched entity's public/currently-known
   facts and a concise relation/history slice; do not disclose protected or
   NPC-private knowledge merely because a name was typed.
4. Ask the LLM for player-visible narration plus a strict JSON `TurnProposal`.
   The proposal contains semantic intent, entity references, fact operations,
   story-event proposals, storylet realization, and an optional requested scene
   transition. Maintain the existing one JSON-mode call + one shared recovery
   call policy.
5. Validate the proposal on a cloned state: entity existence and visibility,
   permitted fact paths, knowledge boundaries, item/NPC availability,
   storylet eligibility, trigger satisfaction, pacing event eligibility, and
   scene transition legality.
6. Run a future-satisfiability check after applying the candidate effects. If a
   required future dependency becomes unavailable and has no declared fallback,
   persist a pending-break record and return a warning without committing the
   candidate. Otherwise commit facts/events/scene transition atomically, then
   render the narration and structured segments.
7. After each committed turn, deterministically fire eligible pacing events,
   re-evaluate active storylets and scene triggers, and record their accepted
   effects before the next context is built. If more than one transition is
   eligible, resolve with a package-declared priority and fail package loading
   on ties.

Do not let narration itself create a scene transition, destroy an item, change
knowledge, or create a story event. The JSON proposal is still untrusted input;
the engine's accepted facts are the only source of the next scene and context.

## Implementation phases

### 1. Establish the replacement contract and fixture

- [x] Add `storygame/story_package/` (or rename the existing authoring boundary)
  with Pydantic source models, `plot.md` and `storylets.md` extraction, YAML
  loaders for world/pacing declarations, stable IDs, error types, and
  cross-reference/dependency validation.
- [x] Transcribe `.plans/plot.md` into the first package under
  `data/stories/continuity-initiative/`. Keep its prose intact while adding
  declarative scene metadata and companion YAML. Copy/adapt
  `.plans/continuity-initiative-storylets.md` as that package's `storylets.md`,
  preserve its links/sections/`SL-*` IDs, and add the required pacing window
  and pacing-impact sections to every storylet.
- [x] Write package-load tests for all scene headings, entity references, trigger
  predicates, fallback rules, dependency-cycle rejection, and deterministic
  transition priority. Include malformed Markdown/frontmatter and YAML cases,
  invalid storylet headings/links/sections, timestamp ordering violations, and
  storylet windows that escape their parent scene window.
- [x] Document the new package format in `docs/markdown-story-authoring.md` and
  update the PRD and contributor guide to make it the product contract.

### 2. Replace the runtime state and proposal schema

- [x] Simplify `storygame/runtime/contracts.py`, `facts.py`, and `state.py` around
  `StoryPackage`, typed facts, `SceneTransitionProposal`, `StoryEventProposal`,
  and `GameBreakWarning`. Preserve strict Pydantic parsing and provider-envelope
  normalization.
- [x] Replace `RuntimeState.active_beats`, `BeatRuntime`, legacy `WorldState`, and
  the generic completion-tag machinery with `current_scene_id`, phase state,
  active/fired events, and a canonical fact store.
- [x] Add snapshot records to the SQLite persistence schema and version the saved
  payload. A pending break must survive process restart and only be resolved by
  `proceed` or `return_to_scene`; normal turns must be rejected while it is
  pending.
- [x] Test atomicity: invalid model JSON, invalid operations, invalid transitions,
  failed pacing effects, and warnings must leave canonical facts unchanged.

### 3. Build scene context and reference-aware memory

- [x] Replace `RuntimeContextBuilder` in `storygame/runtime/context.py` with a
  `SceneContextBuilder`. Its default projection is strictly scene-local,
  including only entities that are present, owned, locally relevant, active in
  a storylet, or needed by a currently eligible pacing event.
- [x] Implement deterministic entity reference resolution over package aliases and
  public names. Resolve only unambiguous references; ambiguous references ask
  the model to clarify without adding either entity's private state.
- [x] Add public history snippets for referenced prior entities/events and retain
  the existing protected-revelation and speaker-private filtering guarantees.
- [x] Define and test a JSON-schema-sized prompt contract so Cloudflare receives
  narration instructions plus an explicit, bounded change schema—not the whole
  story or a free-form state dump.

### 4. Implement progression, pacing, and game-break analysis

- [x] Replace `storygame/runtime/validation.py` with focused validators for fact
  operations, event eligibility, storylet effects, trigger evaluation, scene
  transitions, and future satisfiability.
- [x] Add a generic dependency-analysis service that checks the remaining reachable
  scene graph after candidate effects. It must understand declared fallbacks
  (replacement item, alternative NPC, alternate trigger) and not consider an
  optional storylet or nonessential prop game-critical.
- [x] Refactor `RuntimeEngine.turn` to coordinate proposal -> clone -> validate ->
  break warning or commit -> deterministic pacing. Retain the existing single
  recovery budget and post-commit rendering ordering. Remove the existing
  `_movement_affordance`, `_item_affordance`, inspection normalization, and all
  equivalent text/keyword action routing; a normal `turn` must always call the
  LLM exactly once (plus its one permitted recovery call).
- [x] Add end-to-end tests for: normal action-triggered transition; a deadline or
  pressure-triggered transition; optional storylet effect; leaving early;
  destroying the required memory card; incapacitating Gabriel before a required
  use; accepted `proceed`; and exact `return_to_scene` restoration.
- [x] Add pacing simulations using representative 18-, 20-, and 22-turn main-path
  transcripts. They must reach resolution in the 00:19:00–00:21:00 narrative
  target range, preserve all Freytag milestone ordering, cap optional
  storylets within their windows, and demonstrate that a slow real-world typist
  is prompted with urgency rather than forcibly advanced.

### 5. Keep and adapt hosting, worker transport, and UI

- [x] Retain `storygame/web_demo.py` as the single FastAPI product surface and
  `storygame/runtime/cloudflare.py` as the Cloudflare Worker adapter. Change
  session creation to choose a `story_id` rather than a legacy genre fixture;
  retain health/version, CORS, rate limiting, fail-closed model behavior, and
  SQLite session restoration.
- [x] Extend `/api/v1/turn` responses with a typed `game_break` payload and current
  scene/phase summary. Preserve `segments` as the primary rendering contract;
  keep `lines` only during the migration if existing clients require it.
- [x] Update `frontend/src/main.js`, `turn_rendering.js`, styles, and browser tests
  to show scene/phase context, render structured narration, and present a clear
  Proceed / Return-to-scene confirmation panel. Disable normal input while a
  warning is unresolved; never implement the safety decision only in the UI.
- [x] Update API/Cloudflare deployment docs and tests after confirming the actual
  endpoint/environment behavior in source and CI.

### 6. Remove superseded complexity after the replacement is proven

- [x] Delete legacy V1 fixture selection, genre profiles/predicates, causal
  blueprint compiler, candidate review/audit/repair pipeline, spatial
  interaction compiler projections, beat/tag runtime, and tests/docs that only
  support those paths. Retain `data/compiled_stories/v2/` as archived reference
  data; it is not a supported runtime path.
- [x] Retain, after adapting names and contracts: fact storage, strict provider
  parsing, failure taxonomy, Cloudflare HTTP transport, SQLite integrity
  checks, artifact derivation, FastAPI adapter, React renderer, and their
  focused test coverage.
- [x] Do this only after the Markdown package integration suite covers sessions,
  saves/loads, transitions, warnings, context scoping, and structured output.
  Avoid parallel legacy and new runtime paths beyond a short, explicit migration
  window.

## Acceptance criteria

### Phase 1 exit criteria

- [x] The Continuity Initiative Markdown package loads with stable scene,
  entity, transition, and storylet IDs and no story-specific runtime branch.
- [x] Every `SL-*` storylet has valid plot links, labelled sections, and a
  scene-contained pacing window/impact.
- [x] Malformed Markdown/YAML, references, windows, cycles, and tied transition
  priorities fail closed in package-load tests.

### Phase 2 exit criteria

- [x] Strict provider-envelope parsing produces only valid typed proposals;
  malformed JSON fails closed.
- [x] Runtime state consists of package identity, current scene/phase, active
  and fired events, canonical facts, and an optional pending game break.
- [x] SQLite restores a versioned, integrity-checked pending warning and blocks
  normal turns until `proceed` or exact `return_to_scene` restoration.
- [x] Invalid transitions and warnings leave canonical facts unchanged.

### Phase 3 exit criteria

- [x] Default prompts contain only the current scene’s public entities and
  relevant committed facts; protected and speaker-private facts are excluded.
- [x] An unambiguous public name adds only that entity’s safe history; an
  ambiguous name adds neither entity’s state.
- [x] The provider prompt contains narration instructions and the strict,
  JSON-schema-sized `TurnProposal` change contract rather than a story dump.

### Phase 4 exit criteria

- [x] Player actions can satisfy scene triggers and move through the scene graph;
  package-declared pacing events can also cause declared complications or moves.
- [x] Aside from explicit save/load requests and an already-pending game-break
  resolution, every submitted player input results in one provider call.
- [x] Breaking a required story dependency produces a persistent warning with
  explicit Proceed/Return behavior; return restores the exact pre-action state
  and proceed commits the validated candidate.
- [x] An 18-turn representative main-spine simulation reaches resolution in the
  19–21 minute narrative-time range without requiring optional storylets.

### Phase 5 exit criteria

- [x] The FastAPI surface creates sessions by `story_id`, restores scene-runtime
  state from SQLite, and preserves health/version, CORS, and fail-closed Worker
  transport behavior.
- [x] Turns return structured segments, migration-compatible lines, a scene/phase
  summary, and a typed game-break payload when a warning is pending.
- [x] The browser renders structured narration and scene context, disables normal
  input during a warning, and sends Proceed/Return decisions to the API.
- [x] API/Worker documentation and adapter/frontend tests describe and verify the
  deployed scene-runtime contract.

### Phase 6 exit criteria

- [x] Legacy V1 source packages, fixtures, profiles, compiler inputs, and obsolete
  test-suite classifications are absent; Markdown packages are the sole supported
  authoring/runtime path. Archived V2 data remains outside that runtime path.
- [x] Fact storage, strict provider parsing, Cloudflare transport, SQLite
  integrity checks, FastAPI, and the React renderer retain focused coverage.
- [x] The Markdown-package suite covers session creation, persistence,
  transitions, game-break decisions, context scoping, and structured output.

- The supplied Continuity Initiative Markdown package loads without any
  story-specific Python conditionals and starts Kristin in Scene 1A.
- Player actions can satisfy scene triggers and move through the scene graph;
  deterministic pacing events can also cause declared complications or moves.
- The Continuity Initiative package parses `plot.md` plus its linked
  `storylets.md` companion; every `SL-*` storylet has valid source-beat links,
  scene-local entities, protected boundaries, and a pacing window/impact.
- Every accepted model turn has valid narration and a validated JSON change
  proposal; failed/repaired calls never mutate state or render invented facts.
- Aside from explicit save/load requests and an already-pending game-break
  resolution, every submitted player input results in an LLM call. Tests prove
  that movement, item use, NPC interaction, violence, waiting, and arbitrary
  free-form phrasing are never handled by a deterministic action parser.
- Current-scene prompts exclude unrelated NPC/item/event state, while an
  unambiguous player reference adds only its permitted, concise context.
- Breaking a required story dependency produces a persistent warning with
  explicit Proceed/Return behavior; the return option restores the exact
  pre-action state and the proceed option is auditable.
- NPC traits, mutable knowledge/beliefs, item characteristics/location,
  Freytag/pacing events, and player-caused events are represented in the world
  model and survive save/load.
- A representative main-spine simulation reaches the resolution in roughly 20
  minutes of active narrative time (target 19–21 minutes) without requiring
  optional storylets or forcing player text into deterministic actions.
- FastAPI, React, Cloudflare Worker transport, and SQLite persistence remain
  the deployed stack. `TMPDIR=/tmp uv run pytest -q`, Ruff, frontend tests, and
  deployment-contract checks pass without fixed test-count assertions.

## Migration note

This is intentionally a product reimagining, not an additive feature. Do not
attempt to make Markdown scenes another input shape for the existing compiled
blueprint/storylet system. Preserve its proven transaction/transport/persistence
boundaries, but replace the story-authoring and progression abstractions in one
controlled migration.
