# Authored reveal handoff

## Status

**Phase 6 implementation complete. Deterministic gates pass; the live benchmark
exit gate remains open until pre-recording narration-safety failures are fixed.**

This plan replaces further prompt-only work for candidates that have explicit,
authored action evidence. It complements (and supersedes the uncompleted
deterministic-selection portion of) `narration-candidate-selection-reliability.md`.

## Decision

For a candidate with both:

- a complete, high-precision `action_evidence` definition; and
- an authored `delivery_text` that proves its `must_convey` requirements,

the runtime, not the narrator, will decide whether the player earned it. When
the matcher finds exactly one currently eligible candidate, the runtime will
insert that package-owned delivery text as a normal narration segment and pass
the composed turn through the existing validation and atomic commit path.

The LLM remains responsible for scene prose around the handoff. It no longer
selects a durable fact, writes a candidate ID, or proves the reveal text for
this class of candidate.

This is a deliberate exception to LLM-proposal-first behavior. It is bounded
by package evidence, does not use story-specific runtime branches, and fails
closed whenever the evidence is incomplete or ambiguous.

## Why this change

The completed experiments establish three separate facts:

1. Llama 3.1 8B can emit an offered ID in a 32-token selection-only reply.
2. It is not a safe semantic selector with more than one option: it can select
   an unearned candidate for an unrelated action.
3. Even after a matcher-backed first call supplies the correct ID, it often
   narrates only the search and omits the required reveal. The normal validator
   then correctly drops the selection.

More prompt rules, candidate narrowing, grounding removal, and a two-pass LLM
path did not improve accepted delivery. The system must therefore make durable
delivery an authored runtime operation, not another small-model instruction.

## Invariants

- Facts remain the only mutable truth.
- The runtime considers only the candidate projection eligible on this turn.
- A candidate may be handed off only if every authored evidence group matches,
  no negation guard matches, and exactly one candidate matches.
- A tie, no match, missing `delivery_text`, malformed package data, or failed
  validation produces no reveal and no fact change.
- The authored delivery segment is rendered before effects commit, has the
  candidate's existing `grounding_ids`, and must satisfy the same
  `must_convey`, selection, safety, effect, and cloned-state checks as any
  other turn.
- The model receives no future candidate statement, delivery text, or source
  ID. The UI receives no new bookkeeping fields.
- The shared runtime must not branch on a story ID, character, location, or
  candidate ID.

## Target turn shape

```text
player action
  -> project currently eligible candidates
  -> exact authored matcher
  -> none or one candidate
  -> one normal narrator call for surrounding prose
  -> append package-owned delivery segment when one candidate matched
  -> validate the composed proposal
  -> apply package effects and commit facts atomically
```

The delivery segment uses the existing public `kind: "narration"` and existing
grounding ID. Its package origin is an internal construction detail; do not add
an `origin`, `reveal`, or other new label to the LLM contract or player-facing
JSON.

## Phased implementation

### Phase 0: Lock the contract and migration boundary

- [x] Record the decision above in the PRD or contributor guidance: authored
  evidence may determine a reveal only for candidates explicitly marked for
  authored handoff. All other candidates retain the current LLM-proposal path.
- [x] Decide package compatibility: new `delivery_text` is optional globally,
  but mandatory whenever `action_evidence` opts a candidate into authored
  handoff. Existing packages therefore continue to load unchanged.
- [x] Confirm that a pre-existing save containing one of these fact IDs remains
  valid. The handoff changes delivery, not the fact ID or package effect.

- [x] Exit gate: the PRD documents exactly which candidates can bypass LLM
  selection and why that does not authorize unvalidated fact mutation.

### Phase 1: Add package-owned delivery data and loader checks

- [x] Add `delivery_text: str | None` to `KnowledgeDefinition` and its runtime
  projection type. Keep it out of model serialization.
- [x] Treat a candidate as authored-handoff eligible only when both
  `action_evidence` and non-empty `delivery_text` exist.
- [x] At package load time, reject handoff candidates when:
  - evidence groups are empty;
  - delivery text is blank;
  - delivery text does not satisfy every non-empty `must_convey` group;
  - a delivery string contains implementation-only IDs or bookkeeping labels.
- [x] Reuse the project's existing conveyance matcher for the loader check;
  do not introduce a second incompatible interpretation of `must_convey`.
- [x] Extend authoring documentation with a short example showing evidence,
  delivery text, and the requirement to author conservative aliases.

- [x] Exit gate: loader tests prove that incomplete delivery text is rejected
  before the game can start, and legacy candidates without this opt-in still
  load.

### Phase 2: Make matching an explicit, fail-closed runtime decision

- [x] Promote the existing `candidate_matcher.py` from shadow-only telemetry
  to an internal decision helper for handoff-eligible projected candidates.
- [x] Preserve its current safety contract: every phrase group is required,
  declared aliases are allowed, negated actions do not match, and more than
  one match returns none.
- [x] Run the matcher after projection, never against all package knowledge.
  A protected or future candidate cannot be selected because it is absent from
  the input set.
- [x] Return a small internal result carrying either no candidate or the
  projected candidate and its authored delivery text. Do not expose this
  result to the narrator or API.
- [x] Keep shadow telemetry for non-opted-in candidates during migration so
  package authors can see missed matches without changing play.

- [x] Exit gate: tests cover positive exact phrases, authored aliases, partial
  input, negation, no offered candidate, two matching candidates, and a
  candidate that is in the package but not currently projected.

### Phase 3: Compose the authored segment before existing validation

- [x] Refactor the provider/turn boundary so model prose is parsed as an
  ordinary proposal with no candidate selection duty for a matched handoff.
- [x] When the matcher returned one candidate, append one normal narration
  segment with `text=delivery_text` and `grounding_ids=[candidate.id]`, and set
  `selected_knowledge_ids=[candidate.id]` on the composed proposal.
- [x] When there is no matcher result, compose nothing and retain the legacy
  model-proposal behavior until that candidate is migrated.
- [x] Send the composed proposal through the current prechecks, resolver,
  narration-safety checks, package effects, cloned fact-state validation, and
  atomic commit. Do not add a parallel commit path.
- [x] Ensure rendering observes the composed segment before state effects are
  committed. A failed render/validation leaves the state unchanged.
- [x] Keep model-generated prose separate from the package segment internally
  only as needed for construction and test assertions; do not add metadata to
  the JSON schema.

- [x] Exit gate: an accepted handoff uses the same validator and effects path as
  a model-selected reveal, while a rejected composed proposal changes no facts.

### Phase 4: Simplify the narrator contract for handoff turns

- [x] For a matcher-backed handoff, omit candidate statements, `must_convey`
  lists, candidate IDs, selection rules, and grounding rules from the narrator
  prompt. The model receives only the scene material it needs to write the
  surrounding action.
- [x] Preserve the existing prompt for legacy candidates until they migrate.
- [x] Confirm opening, normal turn, malformed-response recovery, and every
  alternate narration path use the same split. A recovery must not reintroduce
  candidate details or ask the model to select.
- [x] Keep narrator instructions at the existing eighth-grade reading level.
  The only added behavior should be ordinary scene narration, not a new JSON
  relationship.

- [x] Exit gate: prompt snapshots show no candidate ID or delivery wording
  reaches the model for an authored-handoff turn, while the player-facing
  composed result contains the exact authored reveal.

### Phase 5: Migrate one narrow Scene 1A slice

- [x] Start with `k_sl_1a_b_r2`, the damaged-recording warning, because it has
  an existing exact matcher path and a clear `must_convey` set.
- [x] Author delivery text that directly states Michelle, the memory card, the
  damaged recording, and the emergency-broadcast warning.
- [x] Tighten overlapping Scene 1A candidate evidence before enabling both
  recording outcomes. `k_sl_1a_b_r2` requires recovery, the damaged recording,
  and listening; `k_sl_1a_b_r1` separately requires the saved files and reading,
  so card recovery alone cannot earn the files outcome.
- [x] Decide whether to split the memory-card discovery, the recording warning,
  and the dead-drop files into separate player-visible candidates. Use the
  atomized path for the first handoff: `k_sl_1a_b_r2` delivers only the warning;
  `k_sl_1a_b_r1` remains legacy until it gets its own authored delivery.
- [x] Preserve IDs and effects for any existing persisted fact unless a
  migration is explicitly authored and tested.

- [x] Exit gate: the recording action has exactly one match; recovering the
  card, reading files, partial actions, and negated actions have the intended
  safe outcomes. The focused Phase 5 suite passes 183 tests.

### Phase 6: Test and benchmark

- [x] Unit-test schema/loader checks, matcher behavior, prompt exclusion,
  composed-segment shape, validation failure, and atomic no-commit behavior.
- [x] Add an engine-level test proving the selected fact and package effects
  commit only after the composed delivery passes all existing validators.
- [x] Add an API/UI regression test that the player sees the authored sentence
  as ordinary narration and never sees source IDs or a new segment kind.
- [x] Add a benchmark variation for authored handoff. Its records must include
  `authored_handoff_candidate_id` as bench telemetry only.
- [x] Run the isolated recording probe first; then run the established Scene 1A
  script and at least one unrelated scene. Diagnose pre-recording narration
  safety failures separately rather than treating them as selection outcomes.
- [x] Require zero false-positive handoffs in deterministic cases and 100%
  successful composed delivery for the exact recording action before expanding
  migration. Judge surrounding prose quality separately from selection
  correctness. The deterministic suite is at zero false positives and 100%
  exact composed delivery; the live scripts stopped before that turn on
  separate narration-safety failures.

Suggested commands after implementation:

```bash
TMPDIR=/tmp uv run pytest -q tests/test_candidate_matcher.py tests/test_cloudflare_transport.py tests/test_bench.py
uv run ruff check --fix . && uv run ruff format .
TMPDIR=/tmp uv run pytest -q
uv run python -m bench run --variation bench/variations/authored-handoff-phase1.json \
  --scene 1A --replicates 4 --script candidate-selection-repro \
  --out bench/results/authored-handoff-phase1 --confirm
```

- [ ] Exit gate: the isolated probe and live benchmark show accepted delivery
  where the previous one- and two-pass model paths produced empty selections,
  with no fact committed on unmatched or ambiguous actions. The live benchmark
  currently stops before the recording turn on `uncited_knowledge` and
  `narration_known_term_leak` failures; keep migration opt-in until a rerun
  reaches the exact action.

#### Current Phase 6 blocker

The deterministic gate is complete, but the live gate is not. The live runs
were made with `bench/variations/authored-handoff-phase1.json`:

- The isolated selection probe reached the worker and reported no offered
  candidate plus the shadow match `k_sl_1a_b_r2`. This confirms the authored
  handoff is hidden from model selection.
- Four Scene 1A `candidate-selection-repro` replicates stopped before the
  recording action with `uncited_knowledge: narration does not ground the
  knowledge term 'kitchen floor'`.
- The direct `authored-recording-exact` arm also stopped before handoff
  projection with `narration_known_term_leak: narration mentions unavailable
  knowledge 'dead drop'`.
- The unrelated Scene 1B control stopped before handoff with
  `narration_known_term_leak: narration mentions unavailable knowledge
  'kristin and brandon'`.

These are pre-recording narrator-safety failures. They are not false-positive
handoffs and did not commit facts. Do not weaken narration safety or authored
matching to make the benchmark continue. Fix or isolate the pre-recording
prompt/scene-safety failures, then rerun the exact recording action and confirm
`authored_handoff_candidate_id: k_sl_1a_b_r2` with the authored delivery before
checking the exit gate. The captured live records are under
`bench/results/authored-handoff-phase1/`,
`bench/results/authored-handoff-exact/`, and
`bench/results/authored-handoff-phase1-1b/`; repeatable commands and the
deterministic results are in `docs/testing-runbook.md`.

### Phase 7: Rollout and authoring expansion

- [ ] Keep the behavior opt-in by candidate data during the first release.
- [ ] Review telemetry for unmatched player phrasings; add only explicit,
  author-reviewed aliases. Do not replace the exact matcher with a similarity
  score or LLM semantic judgment.
- [ ] Migrate candidates incrementally, prioritizing concrete investigation
  actions and short, player-visible payoffs.
- [ ] Remove the two-pass benchmark path only after the authored-handoff path
  has sufficient evidence; it is useful diagnostic evidence until then, but
  must not be enabled in production.

## Explicit non-solutions

- Do not randomly select an eligible candidate.
- Do not use the selection-only LLM reply as proof that an action earned a
  fact.
- Do not auto-select from vague or partial narration.
- Do not send future or protected candidate text to the narrator.
- Do not add more LLM-facing JSON labels to explain the relationship between
  selection and grounding.
- Do not create story-specific branches, fixed action tables, or a second fact
  commit path.
- Do not weaken `must_convey`, narration safety, effect validation, or atomic
  commit merely to accept a reveal.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Exact matching misses natural player phrasing | Treat as a safe no-reveal; add author-reviewed aliases from telemetry. |
| Evidence rules overlap | Return no candidate on a tie; revise package data or atomize the reveals. |
| Authored text is stale or incomplete | Validate `delivery_text` against `must_convey` at package load and cover it in tests. |
| Model prose contradicts the delivery | Run the complete composed proposal through existing narration-safety and validation checks before commit. |
| Migration changes pacing | Start with one candidate and measure the resulting scene before migrating adjacent outcomes. |
| The LLM still leaks candidate-like details | Do not give it candidate data for handoff turns; reject unsupported details through existing safety checks. |
