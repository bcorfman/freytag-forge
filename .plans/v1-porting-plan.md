# V1 feature-porting plan

## Objective

Restore the valuable player-facing V1 capabilities in V2 without reviving two
competing runtimes. Every port must preserve the V2 authority model:
`RuntimeState` and its validated facts remain the only mutable truth; story
outlines, compiled artifacts, prose, transcripts, and saves remain inputs or
integrity-checked projections.

The target is V1 feature parity where it improves play, not source-level
compatibility with deleted V1 modules. V1 behavior should be re-expressed as
typed V2 contracts, injected adapters, and declarative story-package metadata.

## Guardrails

- Keep one story-agnostic engine. No mystery-specific runtime branches.
- Preserve proposal-first freeform play. Parser handling remains limited to
  control-plane commands; deterministic affordances normalize through the same
  proposal/commit boundary.
- Keep facts as the canonical mutable state. Do not make `STORY.md`,
  `StoryState.json`, transcripts, package objects, or narration authorities.
- Keep provider responses untrusted, locally parsed, schema-validated, and
  fail-closed within the two-request recovery budget.
- Keep authoring, runtime, and deployment adapters separate.
- Port tests before implementation and retain varied mystery, fantasy, sci-fi,
  and relationship coverage.
- Do not restore V1 code wholesale. Treat the V1 production release and
  historical tests as characterization evidence only.

## Feature inventory

| V1 capability | V2 status | Port decision | V2 destination |
| --- | --- | --- | --- |
| Opening setup: protagonist, arrival, companion, situation, first lead | Partially lost; opening metadata now exists | Restore as typed authoring metadata and public opening rendering | `OpeningMetadata`, compiled story, runtime context |
| Declared opening contact and NPC continuity | Missing in the V2 runtime slice | Restore generically through package-declared companions, roles, location, knowledge, and dialogue policy | Story blueprint + runtime facts |
| Fact-backed world truth | Replaced by minimal `WorldState` fields | Restore typed assert/retract facts incrementally, without a second authority | `RuntimeState` fact projection and policies |
| NPC dialogue and protected knowledge | Minimal narration only | Restore addressed-NPC proposal and speaker/knowledge validation | Dialogue contract and runtime validation |
| Items, custody, inventory, clues, readable documents | Minimal item holder support | Restore declarative item affordances, custody, discovery, and disclosure facts | Blueprint metadata + runtime policies |
| Goals, clues, tasks, dramatic state | Beat tags only | Restore generic fact-backed goals/tasks and scene state, then project beats | Runtime facts + pacing context |
| Map movement and deterministic affordances | Movement aliases recently restored | Expand to inventory, visible items, routes, and unambiguous aliases | Shared affordance normalizer |
| Freeform actions and bounded effects | Present in minimal form | Expand proposal schema and policy families; retain player agency | Turn proposal/commit contracts |
| Save/load and artifacts | SQLite runtime snapshots exist; restart rehydration recently restored | Add versioned integrity-checked projections and migration coverage | Persistence adapters |
| CLI and local web adapter | Removed intentionally | Do not restore by default; add only if a current product need is approved | Separate adapter, if authorized |
| Story-package realization | Replaced by blueprint projection | Restore needed package declarations through compiler output, not legacy runtime packages | Offline compiler and fixtures |
| Evaluation/replay traces | Partial runtime event support | Restore parity metrics and deterministic replay evidence after core contracts | Evaluation and persistence |

## Sequenced work

### Phase 0 — Characterization and parity ledger — complete

- [x] Define the ledger as intended V2 capability targets, not as claims that
  unreliable historical V1 behavior worked.
- [x] Record rich opening, room, item, progressive-description, explicit
  `LOOK`, NPC continuity, NPC memory/relationship, conversation-led
  exploration, freeform, fact-authority, and persistence contracts.
- [x] Record player-visible examples, authoring declarations, canonical V2
  state, proposal/validation contracts, persistence/artifact impact,
  cross-genre cases, and intentional V2 differences for every target.
- [x] Use the pinned release, historical tests, retained package data, and docs
  only as product-intent and retirement evidence.
- [x] Record the retirement decision for the legacy CLI and local-web adapters.
- [x] Add a schema regression test for the machine-readable ledger.
- [x] Add the Phase 0 decision record and update product/technical docs.

Create a machine-readable inventory of intended V2 capabilities, informed by
the pinned V1 release, historical tests, `data/story_packages.yaml`, and
existing docs. Historical material is evidence about product intent and
retirement decisions, not a claim that V1 behavior worked. For
each behavior record:

- player-visible example;
- required authoring declarations;
- canonical V2 fact/state representation;
- proposal and validation contract;
- persistence and artifact impact;
- cross-genre test cases;
- intentional V2 differences.

Deliverable: [`.plans/v1-parity-ledger.yaml`](v1-parity-ledger.yaml) plus the
[Phase 0 decision record](v1-porting-phase0-decision.md). The ledger is
intentionally a V2 target ledger; it does not certify the historical V1
implementation.

Continue this plan from the [Phase 0 decision record](v1-porting-phase0-decision.md)
and [parity ledger](v1-parity-ledger.yaml); they define the interpretation of
the completed checklist and the contracts subsequent phases must preserve.

- [x] Exit criteria: no implementation begins with an undocumented assumption
  about whether a capability is a V2 target, an intentional retirement, or
  merely an unreliable historical behavior.

### Phase 1 — Opening, cast, and scene continuity

Complete the opening metadata port:

1. Extend the outline source contract with protagonist context, opening
   companions, public briefing, arrival context, scene purpose, and first
   available actions.
2. Require the causal compiler to emit typed, spoiler-safe opening metadata.
3. Declare an opening contact in the selected story package, including
   location, relationship, public knowledge, and any item custody.
4. Bootstrap those declarations into facts before the first rendering.
5. Render the opening orientation without echoing the automatic `look` command.
6. Add opening and continuity tests for all supported genres.

Exit criteria: a new session explains who the player is, why they are present,
what is happening, who is present, and at least one legal next step; no protected
truth is disclosed.

### Phase 2 — Facts, inventory, clues, and documents

Introduce a minimal typed fact layer beneath `RuntimeState` for generic
assertable/retractable facts:

- identity, role, location, presence, custody, possession;
- knows/unknown knowledge boundaries;
- discovered clues and leads;
- active goals/tasks and scene objective;
- relationship and NPC availability.

Port item affordances and readable-document disclosures from the package data.
All writes must pass explicit policy families and update compatibility views in
one commit. Add tests for custody uniqueness, unavailable items, wrong-speaker
disclosures, knowledge leaks, and save/load round trips.

Exit criteria: V1 case-file, ledger-page, inventory, clue discovery, and
document disclosure flows work through V2 contracts without package lookups at
runtime.

### Phase 3 — NPC dialogue and freeform action parity

Add a typed dialogue proposal containing addressed target, speaker, permitted
context, dialogue, and bounded effects. Validate:

- target is visible and addressed;
- speaker matches the target;
- speaker knows only permitted facts;
- response is not prompt parroting or narrator substitution;
- effects commit before dialogue is rendered.

Expand ordinary freeform proposals to support V1 action families while keeping
the model as the interpreter. Deterministic normalization may handle only
unambiguous movement, inventory, visible-item, and control-plane affordances.

Exit criteria: players can question a present declared NPC, inspect or take declared items,
attempt arbitrary in-scope actions, receive clarification for ambiguity, and
get typed fail-closed responses for invalid or unsafe proposals.

### Phase 4 — Goals, dramatic state, and progression parity

Port V1 goals, tasks, clues, scene purpose, dramatic question, pressure,
relationships, and timed event declarations into generic compiled metadata and
fact-backed runtime state. Preserve the V2 beat/pacing model as a projection or
advisory layer rather than a second authority.

Add cross-genre progression fixtures proving that the same policy families
support investigation, fantasy quest, science-fiction crisis, and relationship
choice without genre branches.

Exit criteria: each fixture has a playable setup, rising progression, crisis,
climax, resolution, failure-forward alternatives, and a valid ending.

### Phase 5 — Persistence, artifacts, and replay parity

Version runtime snapshots and migrate older V2 snapshots. Restore integrity-
checked projections for story state, story summary, traces, and transcripts.
Ensure projections can be regenerated from facts and accepted decisions.
Add restart/reload tests, corruption rejection, replay signature checks, and
artifact parity checks.

Exit criteria: a session survives process restart, load, replay, and artifact
regeneration without treating any projection as mutation authority.

### Phase 6 — Adapter and release parity

Keep the hosted adapter as the public surface. Evaluate whether CLI or local web
is still needed; restore either only as a separately approved adapter sharing
contracts below the adapter boundary. Update frontend behavior, API contracts,
deployment smoke tests, staging evaluation, and production promotion records.

Exit criteria: hosted staging demonstrates the approved parity ledger, V1
rollback remains available, and no root/`/dev/` channel contract regresses.

## Testing strategy

- Add characterization tests before each port and preserve them as V2 contract
  tests after implementation.
- Keep unit tests for contracts/policies, component tests for dialogue and
  projection boundaries, integration tests for persistence and hosted APIs, and
  evaluation tests for cross-genre playability.
- Cover both accepted and rejected paths: ambiguity, unavailable actors/items,
  protected knowledge, invalid custody, malformed provider output, restart,
  and recovery exhaustion.
- Run `TMPDIR=/tmp uv run pytest -q` for the full suite and maintain at least
  90% project coverage.
- Finish every implementation phase with `uv run ruff check --fix . && uv run
  ruff format .`, then rerun affected focused tests.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Recreating V1 and V2 as competing authorities | Port behavior into V2 contracts only; reject legacy runtime imports |
| Story-specific branching during parity work | Put names, contacts, clues, and setup in validated package data |
| Opening prose leaks protected facts | Compile public opening fields separately and validate before rendering |
| Feature parity expands ordinary-turn latency | Keep one normal provider call and one bounded recovery; normalize only deterministic affordances |
| Old saves become unreadable | Version snapshots and test explicit migrations before deployment |
| Restoring retired adapters expands scope | Require a product decision in Phase 6 and keep adapters thin |

## Immediate next actions

1. Build the parity ledger from the V1 release baseline and historical package
   data.
2. Add typed opening companion/protagonist metadata to the source and causal
   compiler contracts.
3. Port one package-declared opening contact and its opening flow as the first
   vertical slice.
4. Add a hosted restart test and a cross-genre opening acceptance test.
5. Record the first approved parity milestone before starting facts/inventory.
