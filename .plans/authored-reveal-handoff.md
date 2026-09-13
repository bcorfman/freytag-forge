# Authored reveal handoff

## Status

**Phases 6 and 7 complete (2026-09-12). The deterministic suite passes and the
live benchmark is clean: Scene 1A completed 4 of 4 replicates with the authored
handoff composed on every one, the unrelated control completed 2 of 2, and no
replicate failed. All six Scene 1A candidates are now migrated, and a live
benchmark of all of them runs clean (see the end of Phase 7).**

This plan replaces further prompt-only work for candidates that have explicit,
authored action evidence.

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

- [x] Exit gate: met 2026-09-12. The live benchmark shows accepted delivery
  where the previous one- and two-pass model paths produced empty selections,
  with no fact committed on unmatched or ambiguous actions. Evidence is under
  `bench/results/phase6-live-1a/` and `bench/results/phase6-live-1b/`.

#### Phase 6 resolution

The handoff design was never the problem. Three unrelated defects stopped every
live run before it reached the recording turn; all three are fixed and covered
by executed checks.

1. **The grounding repair was bypassed on the handoff path.**
   `_parse_eligible_proposal` returned early via `_ordinary_handoff_proposal`
   before `_auto_attribute_committed_knowledge` ran, so a handoff turn naming an
   already-committed term was rejected with `uncited_knowledge`. Identical prose
   grounded `k_scene_1a_entry` on the legacy path and nothing on the handoff
   path. This is what produced the `'kitchen floor'` failures: they occurred on
   turn 3, the recording turn itself, not before it.
2. **Authored prose named knowledge the scene had not committed.** The engine
   hands the narrator each scene's `entry_text`, beats and knowledge-frame
   `situation`, then rejected it for writing from that material. Eleven
   collisions across eight scenes, the worst registering the two protagonists'
   names as knowledge aliases, which is what killed the 1B control. Fixed in the
   package data, and generalized by the new loader lint
   `_validate_narration_term_traps` so no package can reintroduce the class.
3. **`bench` misreported.** Prompt previews read a stale hand-copy of the turn
   rules, and failed replicates never reached `aggregate_runs`, so a 4-of-4
   failure summarized identically to a run that never executed. The summary now
   carries `failed_replicates`, the real `failure_reason` strings, and an
   `entry_state` disclosure of the deliberately bare arrival state.

Live result, `bench/variations/authored-handoff-phase1.json`:

| Measure | Before | After |
| --- | --- | --- |
| Scene 1A replicates completed | 0 of 4 | 3 of 4 |
| Authored handoff composed | never | 3 of 3 reaching turn 3 |
| False-positive handoffs | n/a | 0 across 13 non-matching turns |
| Scene 1B control | 0 of 1 | 2 of 2 |

The delivered turn carried `model_selected_knowledge_ids: []` with
`selected_knowledge_ids: ['k_sl_1a_b_r2']` and the authored `delivery_text`
verbatim, confirming the runtime, not the model, owned the reveal.

**Residual, carried to Phase 7, not a handoff defect.** One Scene 1A replicate
in four failed with `narration_known_term_leak: narration mentions unavailable
knowledge 'michelle's research'`. No fact was committed. This is the older
select-or-don't-mention problem: the term belonged to an
uncommitted legacy candidate, `k_sl_1a_d_r1`. That specific alias was removed
because it named the scene's own invitation to search rather than the secret,
but the class remains for any legacy candidate and is the reason to keep
migrating candidates to authored handoff.

#### Live verification of that residual — 2026-09-12

Two further four-replicate runs of the same script confirmed the alias fix and
found one more defect that the deterministic suite could not have caught.

- `bench/results/phase6-verify-research/`: `michelle's research` did not recur.
  But two replicates failed on `memory card` / `the memory card`, and one of
  those had already composed the handoff on turn 3 and was rejected on turn 4
  for naming the card it had just legitimately earned.
- Root cause: the term index keyed on the leading determiner, so `memory card`
  was owned by four reveals including the earned one while `the memory card` was
  owned only by an uncommitted sibling. Fixed by normalizing one leading
  determiner at index time and merging owners — a subtractive fix that removes
  the determiner sensitivity rather than adding a matching rule. Guarded
  multi-word terms rose from 202 to 204, so protection widened. Two sibling
  instances, `the exchange point` and `her information drop`, were fixed by the
  same change.
- `bench/results/phase6-verify-determiner/`: 3 of 4 completed, and all 3 that
  reached turn 3 composed `k_sl_1a_b_r2`. The post-earn rejection is gone.

What remains is a single, well-understood failure mode: roughly one replicate in
four, the narrator names a legacy candidate's guarded term on turn 2 before the
player has earned it. It commits no facts and is exactly what Phase 7's
migration exists to remove.

### Phase 7: Rollout and authoring expansion

- [x] Close the hole that made migration necessary but not sufficient.
  `_model_candidates` hid a migrated candidate only on the turn its matcher
  fired. On every other turn the narrator was still offered it, so its wording
  entered the prompt for an unearned reveal, and the model could select the ID
  through the legacy path and commit the fact with no authored delivery at all.
  A migrated candidate is now neither shown to nor selectable by the model on
  any turn, across the opening, the output examples and the recovery path, while
  remaining in the projection the matcher runs against.
- [x] Migrate candidates incrementally, prioritizing concrete investigation
  actions and short, player-visible payoffs. `k_sl_1a_b_r1`, the saved-files
  reveal, is migrated: its `action_evidence` was already disjoint from
  `k_sl_1a_b_r2`, so only its `delivery_text` had to be authored.
- [x] Keep the behavior opt-in by candidate data during the first release.
  Six candidates are migrated, every Scene 1A reveal.
  `test_authored_handoff_candidates_are_exactly_the_reviewed_set` fails if that
  set changes, so a further migration cannot land unnoticed.
- [x] Review telemetry for unmatched player phrasings; add only explicit,
  author-reviewed aliases. Do not replace the exact matcher with a similarity
  score or LLM semantic judgment. Sixty-seven recorded live turns produced nine
  correct compositions and no false positives, but three natural phrasings
  earned nothing because the shared first evidence group accepted only
  recover/retrieve. Adding `memory card` and `the card` to that group on both
  candidates fixes all three without creating a tie; the matcher is unchanged.
- [x] Remove the two-pass benchmark path now that the authored-handoff path has
  sufficient evidence. Deleted outright rather than left behind a disabled flag.

- [x] Gather live evidence from `bench/manifests/phase7-live-bench.json`,
  orchestrated through Ringer rather than executed by hand. The run on
  2026-09-12 is the first completely clean one: Scene 1A completed 4 of 4
  replicates with `k_sl_1a_b_r2` composed on every one, and the unrelated
  Scene 1B control completed 2 of 2. No replicate failed for any reason.
  Artifacts are under `bench/results/phase7-live-1a/` and
  `bench/results/phase7-live-1b/`.

  The run that immediately preceded it completed only 2 of 4, both failures
  being `narration_known_term_leak: 'memory card'` on turn 2. That turn
  projects the beat whose own authored prose reads "Kristin finds a hidden
  memory card taped beneath a drawer", so the engine was rejecting the
  narrator for using the words it had just been handed. Licensing a projected
  beat's vocabulary removed the contradiction and the failures with it.

**Scene 1A is fully migrated (2026-09-12).** The four candidates left on the
legacy path above are now authored handoffs, each unblocked for the reason that
had blocked it.

*Outcome variants folded.* `k_sl_1a_a_r2` and `k_sl_1a_d_r2`, with their
realizations `SL-1A-A-R2` and `SL-1A-D-R2`, are deleted. Each pair was one
player action with two tellings, so no evidence could tell the members apart
and migrating both would have made the matcher tie. They were also one reveal
in practice: both `a` candidates set only `michelle_abduction_suspicion`, and
the extra fact `d_r1` sets is already true by the time `SL-1A-D` can activate.
`k_sl_1a_a_r1` and `k_sl_1a_d_r1` keep their IDs, statements and effects, so
saves are unaffected.

*Distinct actions authored.* `k_sl_1a_c_r1` (noticing what the patrol asks
about) and `k_sl_1a_c_r2` (checking the gate after it leaves) set different
facts and have disjoint evidence. `c_r1` and `a_r1` gained `must_convey`,
chosen so each candidate's own statement still conveys every group.

`test_authored_handoff_candidates_are_exactly_the_reviewed_set` fails if the
migrated set changes, and `test_scene_1a_migrated_reveal_composes_through_engine`
proves each new reveal composes and commits through the engine. Tests that
covered the legacy path with these candidates now run against
`tests/_legacy_package.py`, a package copy that makes the named candidates
legacy again.

Fail-closed gaps left on purpose: a command carrying two reveals' evidence
("Inspect the gate and read the files") composes nothing, and the matcher
counts "do" as a negation, so "watch what they do at the gate" earns nothing.

**Live evidence for full Scene 1A (2026-09-12).** `bench/variations/authored-handoff-scene1a.json`
has two five-turn scripts that between them reach every migrated reveal. The
first live run exposed two grounding defects, each fixed and covered by a test
that drives a committed turn:

1. Composed delivery text naming committed knowledge was never auto-grounded,
   because the repair ran before the delivery segment was appended.
2. Narration echoing a term owned only by the reveal being handed off (the
   gate script's "front gate") was left uncited. Counting the candidate as a
   co-owner then broke shared terms such as "dr. mcgehee", so committed owners
   are now chosen first and the candidate only when no committed knowledge
   owns the term.

The third run, `bench/results/scene1a-handoff-live3-1a/` and `-1b/`, is clean:
all six Scene 1A replicates and both Scene 1B controls completed, every reveal
composed on every turn that reached its command (`a_r1` 6/6, `b_r2` 6/6, `c_r1`
3/3, `c_r2` 3/3, `d_r1` 6/6), and no turn composed a reveal its command did not
earn. Offline probes with a stub narrator, one of which echoes each command,
reproduce both defects and pass on the fixed runtime.

**Reliability (2026-09-13).** Thirty live replicates of each Scene 1A script,
in `bench/results/scene1a-reliability-1a-chunk{1,2,3}/` with a four-replicate
Scene 1B control in `scene1a-reliability-1b/`. A reveal counts as delivered
only when it composed and its turn committed; intervals are Wilson 95%.

| Reveal | Delivered | 95% interval |
| --- | --- | --- |
| `k_sl_1a_a_r1` | 60/60 | 94.0-100% |
| `k_sl_1a_b_r2` | 60/60 | 94.0-100% |
| `k_sl_1a_c_r1` | 30/30 | 88.6-100% |
| `k_sl_1a_c_r2` | 30/30 | 88.6-100% |
| `k_sl_1a_d_r1` | 59/60 | 91.1-99.7% |
| All pooled | 239/240 | 97.7-99.9% |

No turn composed a reveal its command did not earn. The gate script completed
30/30 replicates, the officers script 29/30, and the control 4/4. The single
failure was `protected_narration_leak` on the protected term 'phase' in the
narrator's own prose on the files turn; no delivery text contains that word,
so it is a narration-safety rejection rather than a handoff defect. The lower
bounds reflect sample size, not observed failures.

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
