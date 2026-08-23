# Causal compiler symbol resolution and bound-IR plan

## Status and decision

**Status:** proposed follow-on architecture work. This plan changes only the
offline authoring compiler. It does not authorize runtime changes, new provider
calls during play, mutation of facts from authoring data, or story-specific
compiler behavior.

This plan complements the completed causal-story compiler work in
[`openai-causal-story-compiler-plan.md`](openai-causal-story-compiler-plan.md).
The current compiler correctly fails closed, but it validates a large
model-generated object through many string-reference checks. The resulting
diagnostics can surface one unrelated graph defect per bounded repair attempt.
The follow-on replaces that ad-hoc reference handling with compiler-style name
resolution, a typed bound intermediate representation (IR), and pass-oriented
semantic analysis.

## Problem statement

Blueprint candidates define several namespaces whose values are connected by
references: truths, participants, locations, map routes, events, evidence
opportunities, realization routes, revelations, outcomes, beats, and endings.
The provider may confuse namespaces or regenerate valid sections while fixing a
different defect. Prompt guidance and repair ID ledgers reduce that risk but do
not provide binding, dependency analysis, or a stable repair surface.

The compiler must therefore:

- resolve every reference against the namespace appropriate to its field;
- report all bindable reference failures in one deterministic diagnostic pass;
- distinguish an unknown symbol from a symbol in the wrong namespace and offer
  a deterministic replacement only when the mapping is unambiguous;
- construct semantic passes over typed references rather than repeatedly
  scanning raw string fields; and
- keep the provider output untrusted and fail closed after the existing two
  request recovery budget.

## Scope and invariants

- The artifact remains immutable offline authoring input. Facts remain the
  runtime's sole mutable authority.
- The design is profile-driven and cross-genre. No compiler branch may name a
  story, mystery premise, protagonist, or fixed role.
- Provider JSON-object mode remains a syntax aid. Local syntax, binding,
  semantics, and critic checks remain authoritative.
- A provider JSON-mode rejection alone may use the existing no-JSON-mode
  fallback. All other recovery requests retain JSON-object mode. The total
  budget remains two inference requests.
- Binding and repair preparation are read-only projections. They never silently
  add, rename, remove, or reassign story declarations.
- The final candidate remains a complete JSON object; this plan does not add a
  deeply nested provider-side schema or a partial-patch protocol.

## Target architecture

```text
untrusted JSON candidate
        |
        v
syntax contract parse --> normalized raw blueprint
        |
        v
symbol definition pass --> typed symbol tables + duplicate diagnostics
        |
        v
reference binding pass --> bound IR + grouped namespace diagnostics
        |
        v
semantic passes --> topology, causality, knowledge, proof, ending, profile checks
        |
        v
critics + deterministic repair context --> accepted candidate or fail-closed diagnostic
```

The bound IR is a short-lived validation projection, not a second authoring or
runtime authority. It retains the validated raw artifact and replaces repeated
string lookups with typed links to symbol definitions.

The symbol registry exposes explicit namespaces and field domains. Examples:

| Field family | Required namespace |
| --- | --- |
| event inputs/outputs, map prerequisites, knowledge, protections | truth |
| event actors, opportunity holders, hypothesis participants | participant |
| map endpoints, event locations, opportunity locations | location |
| opportunity ownership, failure-forward alternatives | realization route |
| route opportunities | evidence opportunity |
| route and beat revelation references | revelation |
| beat and end-state outcomes | required outcome |
| revelation gates | required beat |
| prerequisites and timeline constraints | causal event |

## Phased implementation

### Phase 0 — Characterization and diagnostic baseline

- [x] Capture invalid fixtures for each reference namespace, including known,
  wrong-namespace, ambiguous, and multiple-error candidates.
- [x] Record current compiler diagnostics and repair request count for cross-genre
  fixtures without fixing candidate content in test code.
- [x] Define deterministic diagnostic ordering and error-code compatibility rules.

**Exit criteria:** [x] tests prove a single candidate can report multiple
reference problems in stable order; [x] the baseline contains mystery,
fantasy, sci-fi, and relationship coverage.

### Phase 1 — Symbol registry and reference binding

- [x] Introduce explicit symbol-table and reference-site contracts below the
  authoring boundary.
- [x] Define every collection once, reject duplicate definitions locally, and bind
  every known reference field through its declared namespace.
- [x] Emit grouped diagnostics with path, expected namespace, supplied ID, and an
  unambiguous suggestion where one exists (for example, an opportunity ID maps
  to its declared truth ID in a knowledge field).
- [x] Preserve current public validation entry points during migration.

**Exit criteria:** [x] generic binding replaces raw `_references` scans for all
reference families; [x] wrong-namespace diagnostics identify both source and target
namespaces; [x] no candidate is accepted when a reference remains unbound.

### Phase 2 — Bound IR and semantic-pass migration

- [x] Construct an immutable bound blueprint projection only after Phase 1 binding
  succeeds.
- [x] Migrate map reachability, causal ordering, evidence ownership, knowledge and
  protection checks, endings, profile checks, and fairness/completeness critics
  to consume the bound IR.
- [x] Keep semantic diagnostics aggregated by pass so a repair receives the full
  set of independent defects within its bounded request budget.

**Exit criteria:** [x] semantic passes contain no repeated raw-ID lookup loops
for bound fields; [x] existing valid fixtures preserve behavior; [x] invalid
cross-genre fixtures identify all independent failures in their relevant pass.

### Phase 3 — Stable repair context and change audit

- [x] Derive the repair ID ledger from the symbol registry rather than ad-hoc raw
  collection scans.
- [x] Add a deterministic candidate-to-candidate structural diff that classifies
  declaration additions, removals, renames, ownership changes, and reference
  changes by namespace.
- [x] Present the prior valid symbols and the allowed repair scope to the model.
  Locally reject an unrelated destructive change unless it is necessary for the
  reported diagnostic; do not silently restore or rewrite it.
- [x] Retain full-object repair responses and the current request budget.

**Exit criteria:** [x] repairs of a reference error retain unrelated valid symbol
definitions; [x] diagnostics name prohibited unrelated changes; [x] approved
repairs remain fully validated and critic-reviewed.

### Phase 4 — Staged live evaluation and authoring promotion

- [x] Run the compiler against a varied, authoring-only outline corpus with the
  normal live gate; retain diagnostics and structural diffs as evaluation data.
- [x] Compare first-pass acceptance, repair acceptance, error-category frequency,
  and request-budget exhaustion against the Phase 0 baseline.
- [x] Require generated candidates to be manually reviewed before promotion; no candidate becomes a
  runtime input merely because it binds successfully.

**Exit criteria:** [x] a real opted-in evaluation run shows fewer
wrong-namespace and unrelated-repair failures without weakened semantic rules;
[x] reviewed cross-genre artifacts pass the existing promotion workflow.

### Phase 5 — Documentation and cleanup

- [x] Update authoring documentation with namespace rules, bound-IR diagnostics,
  repair-diff behavior, and operator troubleshooting.
- [x] Remove superseded prompt-only repair instructions once their behavior is
  represented by symbol-ledger and structural-diff context.
- [x] Keep concise compatibility notes for diagnostic code changes.

**Exit criteria:** [x] `TMPDIR=/tmp uv run pytest -q` retains at least 90% project
coverage; [x] Ruff passes; [x] documentation describes the actual compiler
pipeline.

## Risks and decisions requiring review

- A repair-diff policy must distinguish legitimate additions needed to complete
  a proof chain from unrelated regeneration. Its initial mode should diagnose
  and reject, not silently merge candidate versions.
- Bound IR classes should remain small, explicit, and constructor-injected.
  They must not become a mutable graph database or a replacement artifact
  format.
- Error aggregation must avoid masking prerequisite failures: syntax errors
  precede binding, binding precedes semantics, and semantics precede critics.
- Live evaluation is authoring-only and must not broaden provider-call behavior
  in hosted gameplay.
