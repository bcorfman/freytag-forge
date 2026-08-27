# Fact-backed knowledge projection and progressive revelation

## Status

Proposed architecture plan. Implement as five small, sequential PRs. Do not
ship the provider-context cutover until the package migration and shadow
projection are complete.

## Problem statement

The current runtime has a sound transactional fact boundary but an unsound
knowledge boundary. `SceneContextBuilder.build()` sends `scene.prose` as
`plot_beats`, includes every realization of each active storylet, and carries
accepted narration forward as `RuntimeState.narrative_history`. The provider is
therefore exposed to author-only beats, route effects that have not happened,
and prior free prose that was never a canonical truth source. Prompt text asks
the model not to use information that the engine has already disclosed to it.

The existing `_is_safe_fact()` filter cannot repair this. It infers secrecy from
a small hard-coded predicate list and exact string matches against
`protected_knowledge`; it does not represent who knows a fact, when that fact
may be learned, or which scene-local reveal establishes it. Likewise, validating
route operations protects canonical mutation but does not prove that the
returned narration describes only committed or atomically selected knowledge.

This is the architectural source of the Scene 1A acceptance failure recorded in
`docs/testing-runbook.md`: JANUS and future system purpose appeared before the
facts that authorize those revelations, and later-scene requests were accepted
without scene-local causality.

## Non-negotiable invariants

1. Package prose is authoring reference, never runtime knowledge and never a
   prompt input.
2. Facts remain the sole mutable authority. Knowledge is a projection of
   committed facts plus the exact reveal selected in the current candidate
   transaction; it is not a parallel mutable cache.
3. The player view and each speaking character have explicit audiences. A fact
   may be true in the world without being known to either audience.
4. A normal turn receives only the immediate public scene frame, permitted
   local entities, audience-safe committed knowledge, safe fact-derived
   continuity, and a bounded set of currently eligible reveal candidates.
5. Player input is intent, not authority. Mentioning an unrevealed person,
   place, system, objective, or event cannot add it to the projection.
6. Selecting a reveal is a typed proposal. Its exact package-authored effects,
   prerequisites, scene availability, and audience are validated on a cloned
   fact store and committed atomically.
7. Narration is validated against the projected post-candidate knowledge before
   canonical mutation or rendering. A failed narration check commits nothing
   and is never appended to provider memory.
8. NPC dialogue can use only that speaker's sayable projection. Author-private
   knowledge and private NPC knowledge are not sent merely with an instruction
   to conceal them.
9. Shared Python and JavaScript remain story-agnostic. All story-, character-,
   and genre-specific reveal policy lives in validated package data.
10. The normal provider budget remains one inference plus the existing single
    recovery request. The external E2E judge is acceptance evidence, not a
    runtime safety authority.

## Target package contract

Add a typed `knowledge.yaml` source (or an equivalently isolated `knowledge`
section if implementation evidence favors one file). Keep `plot.md` and
`storylets.md` for human authoring, but require every runtime-revealable claim to
be represented by a declarative unit. Do not duplicate executable effects
between Markdown and YAML.

```yaml
schema_version: "2.0"
knowledge:
  - id: K-1A-SARAH-WARNING
    statement: Jeremiah has recovered Sarah's warning not to trust emergency broadcasts.
    entity_ids: [jeremiah, sarah, sarah_phone]
    aliases: [Sarah's warning, emergency broadcast warning]
    audience:
      kind: characters
      character_ids: [jeremiah]
      player_visible: true
    available_in_scenes: [1A]
    requires:
      - fact_id: sarah_phone_accessible
        equals: true
    establishes:
      - op: assert
        fact_id: sarah_warning_known
        value: true
    source:
      storylet_id: SL-1A-B
      realization_id: SL-1A-B-R1
    relevance:
      entity_ids: [sarah_phone, sarah]
      priority: 20
```

The final Pydantic names may differ, but the contract must preserve these
concepts:

- `KnowledgeDefinition`: stable ID, concise player-safe statement, referenced
  entity IDs, aliases/terms used by leak detection, audience, scene
  availability, required established facts, exact fact effects, source route,
  and deterministic relevance metadata.
- `Audience`: `public`, `characters`, or `world_only`, with explicit character
  IDs and whether the protagonist/player view may receive it. Avoid
  open-ended visibility strings.
- `FactDefinition`: stable predicate ID and purpose. Separate world-state facts
  from knowledge-establishing facts so a true internal condition is not
  automatically narratable.
- `RevealSource`: one eligible storylet realization, pacing event, scene entry,
  or other typed authored source. There must be exactly one executable owner
  for each reveal effect.
- `SceneFrame`: a short, explicitly player-safe immediate situation and local
  dramatic pressure. Replace runtime use of author objective, entry prose, and
  plot prose. Scene entry itself is a typed initial reveal whose facts are
  committed before its opening text is rendered.

`world.protected_knowledge` becomes a validated catalog of author-only
knowledge IDs/aliases or is removed after all protection is expressed through
the typed knowledge catalog. It must not remain a bare string deny list that
competes with audience metadata.

### Loader validation

Package loading fails closed when any of the following is true:

- a knowledge unit references an unknown scene, entity, fact, storylet,
  realization, audience character, or source;
- its source route is not available in every declared scene, or its exact
  `establishes` operations differ from that realization's operations;
- a reveal can establish its own prerequisite, has a prerequisite/reveal cycle,
  or depends on a fact unreachable from scene entry and earlier reachable
  reveals;
- an author-only/world-only fact is marked player-visible without an explicit
  reveal source;
- two knowledge units claim the same source/effect tuple ambiguously;
- an entity or protected concept lacks the aliases needed for deterministic
  known-term screening;
- a scene frame, opening reveal, storylet realization, pacing event, or
  transition references knowledge not available in that scene;
- a reveal's audience conflicts with the fact it establishes, such as a
  character-private disclosure being marked public;
- the source schema version is mixed or unsupported.

Compile immutable indexes at load time: knowledge by ID, facts to knowledge,
source realization to knowledge, scene to candidates, entity/alias to knowledge,
audience to known terms, and prerequisite dependents. Runtime code consumes
these indexes rather than rescanning Markdown or interpreting prose.

## Target runtime design

Introduce a focused `KnowledgeProjector` below the provider boundary. It reads
the immutable package indexes and the canonical `FactStore`; it never mutates
state.

```text
RuntimeState + player input
        |
        v
eligible routes/pacing + unambiguous established references
        |
        v
KnowledgeProjector
  - player-visible committed knowledge
  - per-speaker sayable knowledge
  - local entities supported by that knowledge
  - bounded fact-derived continuity
  - next eligible reveal candidates only
        |
        v
TurnKnowledgeContext -> one provider request
        |
        v
typed TurnProposal (segments + grounding + selected reveal/effects)
        |
        v
clone -> validate effects -> project candidate knowledge -> validate narration
        |
        +---- reject: no mutation, no render, typed failure
        |
        v
dependency check -> atomic commit -> render accepted segments
```

### Projection rules

`KnowledgeProjector.project(state, audience, player_input)` returns only:

- current scene ID/phase and the scene's explicitly safe `SceneFrame`;
- current location and participants/items whose presence is established by
  committed facts or the safe scene-entry reveal;
- committed `KnowledgeDefinition.statement` values visible to the requested
  audience;
- current observable pressure whose facts are committed;
- continuity records derived from committed reveal/fact IDs, not prior
  narration prose;
- unambiguous off-scene references only when the referenced entity has already
  been established for that audience;
- a bounded candidate list filtered by current scene, unfired source,
  prerequisites, audience, pacing window, and relevance.

Candidate relevance must stay declarative and story-agnostic. First retain
candidates connected to an already-established entity unambiguously referenced
by the input; then fill a small package-configured maximum by priority and
pacing urgency. This is context selection, not an action parser: it never
chooses the player's action, commits an effect, or maps phrases to fixed moves.
Stable ID ordering breaks ties. Tests must enforce a byte/token budget and
ensure future candidates do not enter the payload.

Do not include `Scene.prose`, all active storylet realizations, future route
effects, raw `narrative_history`, world-only facts, or private speaker facts in
the player projection. For dialogue, provide each present speaker a separate
sayable list. A secret the speaker knows but is not permitted to disclose is
absent unless an eligible reveal candidate explicitly authorizes disclosure on
that turn.

### Canonical knowledge state

Do not add a mutable `known_knowledge_ids` set. A knowledge unit is committed
when its exact `establishes` facts exist for its declared audience. If an
explicit audit marker is needed, represent it as an ordinary typed fact such as
`revealed_to(K-..., character_id)` and include that operation in the authored
effect tuple. Save/load continues to serialize the fact store; package schema
identity/version protects interpretation.

Replace `narrative_history: list[str]` as a prompt memory source with bounded
`TurnRecord` data containing accepted reveal IDs, affected entity IDs, event
IDs, transition ID, and committed fact keys. The transcript text may remain for
display/audit, but the projector must never treat it as truth or resend it as
knowledge. Existing saves need an explicit version migration or fail-closed
compatibility decision; do not silently reinterpret legacy prose.

## Provider and output contract

Replace `SceneContext` with a narrower `TurnKnowledgeContext`. Remove
`plot_beats`, raw `entry_text`, author objective, generic protected-boundary
instructions, and realization prose. A candidate exposes only its safe reveal
statement, stable IDs, audience, and exact route-authorized operations needed
for proposal construction.

Make narration structured at the provider boundary:

```json
{
  "segments": [
    {
      "kind": "narration",
      "text": "...",
      "speaker_id": null,
      "grounding_ids": ["scene:1A", "K-1A-SARAH-WARNING"]
    }
  ],
  "events": [
    {
      "event_id": "SL-1A-B",
      "realization_id": "SL-1A-B-R1",
      "knowledge_ids": ["K-1A-SARAH-WARNING"],
      "operations": ["exact package-authorized operations"]
    }
  ],
  "operations": [],
  "transition": null,
  "narrative_seconds": 60
}
```

Preserve a derived `narration`/`lines` compatibility field only at the API
edge. Runtime validation and rendering use accepted segments. Require each
segment to cite the scene frame, committed knowledge, selected reveal, or an
explicit `incidental` grounding category. Dialogue segments require a
`speaker_id` and are checked against that speaker's candidate projection.

Incidental sensory color remains allowed, but it cannot introduce a named
package entity, a durable state change, evidence, history, relationship,
objective, organization, or protected concept. Durable creative consequences
remain LLM-proposal-first through typed fact operations and are visible only
after those operations validate.

### Narration safety validator

Add a deterministic `NarrationSafetyValidator` that runs after all proposal
effects validate on a clone and before commit/render. It must:

1. Build the post-candidate projection from the cloned fact store.
2. Reject unknown grounding IDs, grounding not visible to the player, and
   dialogue grounding not sayable by its speaker.
3. Scan normalized segment text against the package's compiled entity names,
   aliases, protected terms, and knowledge aliases; reject a known term unless
   its entity/knowledge is in that segment's allowed projection.
4. Require every selected knowledge ID to be backed by one eligible source and
   its exact effect tuple; reject narration grounded in an unselected candidate.
5. Reject segment claims of durable change unless the proposal contains the
   corresponding validated operations/event/transition.
6. Reject narration that describes a requested transition before its trigger is
   valid in the candidate fact store.
7. Return a typed failure with no proposal mutation. Do not repair narration by
   dropping facts or silently stripping text.

Structured grounding plus known-term screening creates an enforceable boundary
for authored canon. It cannot mathematically classify every possible euphemism
in unrestricted prose, so packages must declare meaningful aliases and tests
must include paraphrased leak fixtures. The staged LLM-canon judge remains a
defense-in-depth quality check, not permission to render or mutate.

## Phased implementation

### Phase 1 / PR 1: Declarative knowledge schema and package migration

- [x] Add knowledge, audience, source, prerequisite, scene-frame, and fact
  definition models in `storygame/story_package/models.py`; split models if the
  module would exceed the contributor-guide size target.
- [x] Parse `knowledge.yaml` in `storygame/story_package/loader.py` and extract
  loader validation into focused validators rather than extending the current
  high-complexity `_validate()` function.
- [x] Compile immutable lookup indexes on `StoryPackage` or a dedicated package
  index object.
- [x] Migrate every Continuity Initiative world fact and storylet realization.
  Split compound realizations into atomic knowledge units when their effects
  have different audiences or reveal timing; do not copy scene prose into
  `statement` fields.
- [x] Declare safe scene frames and scene-entry reveals. Tag facts such as
  `rebecca_observing_infiltrators` as world-only until a later authored reveal
  establishes player knowledge.
- [x] Bump package schema/save compatibility metadata and update
  `docs/markdown-story-authoring.md`, the PRD contract summary, and contributor
  links.
- [x] Add loader tests for all invalid references, effect mismatches, visibility
  conflicts, duplicate ownership, prerequisite cycles, unreachable reveals,
  missing aliases, mixed versions, and cross-scene leaks.

Exit gate: [x] the package loads into a complete typed knowledge graph; every
runtime-revealable authored claim has exactly one scene-valid source and exact
effects; malformed or ambiguous visibility fails closed. Live prompts are
unchanged in this PR.

Phase evidence: [x] deterministic coverage proves the entry fact is committed
before render and the entry catalog omits the warning, JANUS, and future-scene
terms. [x] Run the persistent Scene 1A browser fixture after this revision is
deployed to staging; it must retain the same timeline evidence. Non-game-breaking
local clues may be invented and persisted as ordinary facts.

### Phase 2 / PR 2: Fact-derived projection in shadow mode

- [x] Add `storygame/runtime/knowledge.py` with `KnowledgeProjector`, typed
  projections, eligibility/relevance selection, and audience-specific views.
- [x] Derive committed knowledge solely from facts. Add any required typed
  reveal/audience facts through the normal route operations and persistence
  model.
- [x] Add structured `TurnRecord` continuity and stop adding new raw narration
  to provider memory. Preserve transcript text only for UI/audit compatibility.
- [x] Integrate projection creation into `RuntimeEngine`/the provider adapter in
  shadow mode: build it, measure it, and compare it in tests, but continue
  sending the old context until the exit gate is met.
- [x] Add observability containing counts/IDs and payload size only—never
  protected statements, player text, or raw narration.
- [x] Add table-driven cross-genre fixtures proving public, character-private,
  world-only, already-revealed, same-turn-reveal, ambiguous-reference, pacing,
  and save/load behavior.

Exit gate: [x] for every deterministic fixture, the shadow projection contains all
and only audience-authorized knowledge, candidate selection is bounded and
stable, and save/load reproduces the same projection. No provider behavior
change yet.

Phase evidence: [x] run the same fixture against the shadow payload and retain a
redacted ID-only diff. Before the recording, Sarah's warning must be absent;
before a patrol arrival/search, patrol tape must be absent.

### Phase 3 / PR 3: Provider-context cutover

- [x] Replace `SceneContext` with `TurnKnowledgeContext` in
  `storygame/runtime/context.py`; delete `plot_beats` and all wholesale scene,
  storylet, route, and history prose from the serialized payload.
- [x] Change `CloudflareTurnProvider.__call__()` to send the safe scene frame,
  committed player projection, per-speaker sayable projections, and only the
  bounded eligible candidates.
- [x] Move long story-policy prose out of `cloudflare.py`; keep concise generic
  instructions that describe the typed contract, since prompt warnings are no
  longer the secrecy mechanism.
- [x] Update `TurnProposal`/Worker JSON schema with structured segments,
  grounding IDs, and selected knowledge IDs while preserving the existing one
  call plus one recovery budget.
- [x] Keep API `segments` primary and derive migration-era `narration`/`lines`
  only after acceptance. Update Cloudflare transport fixtures to assert absence
  of future names, plot prose, unselected effects, and raw narrative history.
- [x] Remove the shadow/legacy context path once cutover tests pass; do not leave
  two selectable knowledge policies.

Exit gate: [x] a captured deterministic Scene 1A provider payload contains no JANUS, later-scene
purpose, future route effect, or full plot/storylet prose; it stays within the
declared budget and still supplies the next eligible local reveal needed to
respond substantively.

Phase evidence: [x] run the deterministic fixture through the provider/API harness and retain the
captured payload IDs. The drawer/recording turn must offer the damaged-warning
candidate without exposing it earlier.

### Phase 4 / PR 4: Pre-commit narration safety and atomic rendering

- [ ] Add `NarrationSafetyValidator` and package alias indexes. Validate each
  narration/dialogue segment against the cloned post-candidate audience
  projection.
- [ ] Refactor `RuntimeEngine.turn()` to execute: parse -> normalize structural
  envelope only -> validate exact operations/events -> apply to clone -> build
  post-candidate projection -> validate narration -> dependency analysis ->
  atomic commit -> append transcript/render.
- [ ] Ensure game-break candidates do not render their candidate narration until
  `proceed`; `return_to_scene` restores facts, knowledge projection, continuity,
  and transcript position exactly.
- [ ] Remove normalization that can infer a canonical route from a model's
  leaked/partial canonical operations unless the proposal explicitly selects
  one unique eligible knowledge source. Recovery may repair JSON structure, not
  infer narrative authorization.
- [ ] Add adversarial tests for future entity aliases, protected paraphrases,
  uncited knowledge, wrong-speaker dialogue, unselected candidate effects,
  premature transitions, invented game-breaking evidence, durable incidental claims, and
  rejected-turn atomicity.
- [ ] Add API/frontend tests proving rejected narration never reaches
  `segments`/`lines` and accepted segments preserve their validated structure.

Exit gate: no narration is rendered or remembered unless its grounding and
same-turn effects validate against the candidate projection; every failure
leaves facts, scene, events, continuity, transcript, and persistence unchanged.

Phase evidence: run the fixture with adversarial provider replies: an invented
clue that incorrectly completes a required dependency, a premature warning,
and patrol tape without an arrival/search event. The game-breaking and
premature claims must be rejected atomically; ordinary local clues remain
valid, and a grounded recording reveal commits before it renders.

### Phase 5 / PR 5: Staged acceptance, rollout, and cleanup

- [ ] Add deterministic package-wide leakage matrices that build a context for
  every scene/audience before and after each reveal and assert all future known
  terms are absent.
- [ ] Add context snapshots/diffs to local test artifacts using IDs and redacted
  statements, and make payload-size regression thresholds explicit.
- [ ] Update `frontend/e2e/roleplay-judge.js` so the judge evaluates the reached
  scene against the committed reveal timeline rather than receiving all of
  `world.yaml`, all scene routes, and author-only source as undifferentiated
  canon. Keep the judge unable to authorize runtime output.
- [ ] Deploy to staging and run `@smoke`, focused safety/NPC-knowledge cases,
  the full spine, and finally `@llm-canon`. Preserve artifacts from each gate;
  stop rollout on the first knowledge leak or future-beat jump.
- [ ] Exercise player prompts that name every future character, place, system,
  and objective from Scene 1A. Verify the inputs reach the model unchanged but
  none of those names enter context or accepted narration before their reveal.
- [ ] After final staging evidence, update `docs/testing-runbook.md` with the
  exact commands, environment, outcomes, artifacts, safety classification, and
  cleanup. Promote only the verified revision, then repeat the smoke and
  knowledge-safety probes against production.
- [ ] Remove legacy `protected_knowledge` string filtering,
  `_PRIVATE_PREDICATES`, raw narration memory, compatibility context fields, and
  temporary schema adapters after persisted-session policy is complete.

Exit gate: deterministic leakage tests pass across all scenes and audiences;
staged `@llm-canon` passes progressive revelation and protected safety without
rushing future beats; the exact promoted revision passes production smoke and
knowledge probes; the focused runbook records only observed final evidence.

Phase evidence: run browser `@knowledge-timeline` and its OpenAI judge variant
against staging, then production after promotion. Preserve JSON/Markdown
artifacts and stop on the first failed assertion.

### Persistent Scene 1A knowledge-timeline acceptance harness

Keep this scenario through every phase; it is a regression contract, not a
one-off prompt. Use deterministic providers in PRs 1–4 and browser/API plus the
judge path in PR 5.

| Step | Player input | Required evidence | Must remain absent |
| --- | --- | --- | --- |
| Opening | Start a session | Quiet house, Sarah missing, phone on the kitchen floor; entry fact committed. | Unrevealed warning, JANUS, future facilities. |
| Physical search | Inspect the back door and room | A concrete local consequence; non-game-breaking invented clues may persist as ordinary facts. | A clue that completes a canonical dependency or leaks future knowledge. |
| Phone | Examine Sarah's phone | Phone-specific result; no warning unless its realization is selected. | Sarah's warning or a patrol event. |
| Drawer/recording | Search desk/drawer for research or recording | Damaged-warning candidate is offered; its fact commits before narration. | Warning before that commit. |
| Gate | Check the gate after a patrol arrival/search | Arrival/search precedes any patrol tape or recording. | Patrol tape without causal arrival/search. |
| Follow-up | Repeat a clue or wait | A distinct local consequence or bounded pressure, not generic recycled prose. | Future names, objectives, and unsupported facts. |

The deterministic fixture records `input`, segments, selected knowledge IDs,
operations, facts before/after, and rejection reason. Browser runs also record
provider payload IDs and a redacted transcript. The judge is quality evidence;
structural assertions remain authoritative.

## PR dependency and rollback boundaries

| PR | Depends on | Runtime behavior change | Safe rollback |
| --- | --- | --- | --- |
| 1. Schema/package | None | None | Revert schema and package together. |
| 2. Shadow projection | PR 1 | Internal shadow data only | Remove projector integration; facts remain compatible. |
| 3. Context cutover | PR 2 | Provider payload/schema | Revert deployment to the prior revision; do not feature-flag two policies long-term. |
| 4. Safety validator | PR 3 | New fail-closed rejection boundary | Roll back PR 3 and 4 together if provider schema compatibility requires it. |
| 5. Rollout/cleanup | PR 4 | Acceptance and removal of legacy paths | Restore the last verified revision; never bypass validation to recover availability. |

Package/schema changes and provider changes must not share a PR. The narration
validator must land before any production promotion of the new provider
contract. A rollback may restore a previously verified binary, but must never
re-enable wholesale authoring prose as an emergency fallback.

## Verification matrix

Run affected tests during each PR, then the full suite and formatting commands
from `AGENTS.md` before handoff:

```bash
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix .
uv run ruff format .
TMPDIR=/tmp uv run pytest -q
cd frontend && npm test
cd frontend && npm run build
```

The focused deterministic matrix must cover at least:

| Scenario | Context expectation | Proposal/render expectation |
| --- | --- | --- |
| Scene entry | Only safe frame and entry reveal | Opening renders after entry facts commit. |
| Eligible but unselected reveal | Candidate only, not established knowledge | Effects/narration cannot describe it as true. |
| Selected reveal | Candidate and exact source/effects | Post-candidate narration may cite it; effects commit atomically. |
| Future name in input | Name absent unless already established | Input remains unchanged; narration cannot echo or reveal it. |
| NPC private fact | Absent from player and other speakers | Only an eligible disclosure candidate can make it sayable. |
| World-only fact | Available to eligibility logic only | Never narratable until a typed reveal establishes audience knowledge. |
| Rejected narration | No mutation | No segment, transcript entry, history, or persistence write. |
| Save/load | Same fact store and package identity | Projection and candidate set are identical after restore. |
| Game break | Candidate held outside canonical state | Proceed commits and renders; return restores exactly. |
| Scene transition | Target entry knowledge still absent pre-commit | Target opening reveal occurs only after legal transition. |

Do not pin collection counts. Focused pytest commands may fail only because the
repository-wide coverage threshold applies; use the full suite for the passing
coverage gate. Live E2E calls are billed/external and must use the staged order
and environment documented in `docs/testing-runbook.md`.

## Completion criteria

- No runtime provider payload contains `Scene.prose`, complete storylet prose,
  all active realization guidance, future route effects, or raw narration
  history.
- Every player-visible canonical claim maps to committed audience knowledge or
  one exact selected reveal in the current atomic candidate.
- Every speaking character's dialogue is grounded only in that character's
  sayable projection.
- Player input cannot expand knowledge availability, even when it accurately
  names future canon.
- Known protected entities/terms are deterministically rejected before render
  when absent from the post-candidate projection.
- Rejected provider output cannot change facts, events, scene, continuity,
  transcript, save state, or API output.
- Package validation proves source ownership, scene availability,
  prerequisites, audience, and exact established effects for every reveal.
- Cross-genre fixtures prove the engine contains no Continuity Initiative or
  genre-specific runtime branch.
- Staging and production evidence demonstrate progressive local narration and
  no early JANUS/future-purpose leakage from Scene 1A.
