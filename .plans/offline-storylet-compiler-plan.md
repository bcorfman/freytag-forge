# Offline storylet compiler and fact-backed drama runtime plan

## Status and decision

**Status:** proposed. This plan extends the reviewed offline authoring path and adds generic runtime realization. It does not authorize story-specific runtime branches, provider calls outside the existing ordinary-turn budget, or mutation authority outside canonical facts.

## Required design companion

Read [storylet.md](storylet.md) before implementing this plan. It is the
conceptual design record for this work: its Façade-inspired dramatic beats,
Failbetter-inspired quality-controlled storylets, two-speed dramatic structure,
cross-genre examples, and linked reference material define the intended
narrative experience. This plan translates that design into Freytag Forge's
authoring, fact-authority, validation, review, and runtime boundaries.

Where this plan is more specific, its implementation constraints govern:

- The slow layer in the companion document is the immutable dramatic spine:
  required/optional beats, causal revelations, and end-state obligations.
- Its fast layer is the immutable storylet pool: reusable dramatic situations
  selected from facts, not a menu of permitted player commands.
- Its suggested mutable qualities (trust, danger, preparedness, awareness,
  and similar dramatic dimensions) must be expressed as typed canonical facts,
  never as a second mutable state store.
- LLMs create candidate authoring data offline and propose a bounded runtime
  realization; deterministic policy remains the authority for eligibility and
  committed consequences.

The Storylet contract below is intentionally an implementation-shaped version
of the companion document's beat and storylet examples. It preserves their
required detail: situation, conflict/question, participants, availability,
priority and tension, several realization patterns, bounded effects, abort
conditions, and failure-forward alternatives.

The existing story-blueprint-v2 compiler already creates truths, protections, revelations, realization routes, beats, and endings. Its reviewed artifact is projected into a smaller CompiledStory, whose runtime context exposes broad beats and completion tags. That loses the reusable dramatic situations needed for rich narrative.

This plan adds a two-speed, story-agnostic drama model:

~~~text
immutable Story Brief / outline
        |
        v
OpenAI offline compiler -> reviewed Narrative Blueprint
        |                    causal spine + storylet pools
        v
immutable runtime narrative projection
        |
        v
deterministic selector over canonical facts -> eligible storylets
        |
        v
ordinary-turn LLM proposes one bounded realization -> policy commits facts
        |
        v
rendered narration
~~~

OpenAI is the initial provider for offline storylet generation because it is already the first-party, explicitly gated authoring transport. The provider remains replaceable through the existing typed transport boundary. Runtime narration may continue to use Cloudflare AI or another compatible provider; it does not generate canonical storylet content during play.

## Product outcome

Each reviewed story supplies:

- A dramatic spine of major required and optional beats.
- A pool of storylets: coherent dramatic situations, not fixed commands or prewritten scenes, associated with each beat.
- Declared alternatives, failures, pacing pressure, participants, location requirements, protected knowledge, and bounded fact consequences.
- Enough variety that conversation, investigation, relationships, travel, conflict, and failure can meaningfully change the path to the same valid dramatic outcome.

The player remains free to attempt any story move. The selector offers context to the model; it does not replace interpretation with a command table. A turn that cannot fit a current storylet may still be narrated and committed through the ordinary proposal/commit contract, but it cannot invent protected knowledge or advance an undeclared dramatic outcome.

## Non-negotiable boundaries

- Storylets, beat definitions, prose guidance, and realization modes are immutable reviewed authoring data. They are never mutable session state.
- Facts remain the sole canonical mutable runtime truth. Availability, activation, completion, repetition prevention, relationships, pressure, and every material consequence are facts and commit through the existing atomic policy boundary.
- Storylets may name fact predicates and approved consequence IDs; they may not carry executable effects, arbitrary runtime paths, or narration that asserts uncommitted truth.
- Ordinary gameplay retains its one-request normal path and one shared recovery request. Storylet selection and validation are local and deterministic.
- The compiler retains its current one initial provider request plus at most one repair request for an authoritative candidate. Do not add hidden prompt chains to compensate for a thin source outline.
- Raw outlines, candidates, reviewed blueprints, STORY.md, traces, and saves remain inputs or projections, never mutation authorities.
- Shared code remains genre- and story-agnostic. Genre requirements belong in profile data; named characters, locations, and dramatic content belong only in source and reviewed artifact data.

## Target authoring model

### Enriched source direction

Keep compact inventory outlines supported, but use freytag-story-brief-v1 as the reliable source for rich compilation. Extend it with typed optional creative direction that is explicitly non-canonical until reviewed:

| Source area | Required content for rich compilation |
| --- | --- |
| Character arcs | Wants, fears, vulnerabilities, relationships, secrets, and likely changes. |
| Conflict | Opposition, stakes, costs, escalation sources, and irreversible breaks. |
| Dramatic spine | Candidate turning points, dramatic questions, intended revelations, and ending constraints. |
| World | Setting texture, locations, institutions, resources, and recurring pressures. |
| Possibilities | Social, investigative, environmental, conflict, failure, and transition seeds. |
| Presentation | Voice, sensory palette, motifs, pacing boundaries, and content constraints. |

Hard truths, protections, and terminal constraints remain explicit compiler constraints. The compiler may elaborate creative direction into candidate content, but it may not replace declared identities, causes, motivations, methods, or ending constraints.

For legacy compact outlines, create a separate authoring-only brief-draft command if desired. Its output is a noncanonical draft for human editing into a Story Brief; it cannot be promoted or used as runtime input. This preserves the authoritative compile budget for one full candidate plus one repair.

### Storylet contract

Add an immutable Storylet contract to the causal blueprint. Its fields should be declarative and refer only to declared symbols:

~~~yaml
id: witness_withdraws
beat_id: theory_under_pressure
purpose: social_complication
availability:
  required_truth_ids: [player_knows_timeline_gap]
  absent_truth_ids: [witness_has_withdrawn]
  participant_ids: [witness]
  location_ids: [witness_quarters, archive]
  pressure: { minimum: 35, maximum: 70 }
priority: 70
dramatic_question: "What is the witness protecting?"
realization_modes: [direct_questioning, observed_argument, intercepted_message]
consequence_ids: [witness_trust_lowered, player_knows_witness_fear]
abort_truth_ids: [witness_has_left]
failure_forward_storylet_ids: [examine_witness_correspondence]
~~~

Define generic, bounded enums for purpose and realization modes. Profiles may constrain their minimum mix, but no runtime branch may inspect genre names. Consequence IDs resolve to declared fact-change templates below the policy boundary; they are not freeform provider operations.

The corresponding beat gains authoring fields for its dramatic situation, active conflict, question, participant role requirements, target pressure band, and completion conditions. Existing causal revelations and realization routes remain the proof/revelation substrate; storylets package playable dramatic ways to pursue, complicate, defer, or satisfy them.

## GPT-5.6 tier policy

OpenAI positions GPT-5.6 Sol as its frontier tier, GPT-5.6 Terra as the
intelligence/cost balance, and GPT-5.6 Luna for cost-sensitive high-volume
workloads. See the [official model guidance](https://developers.openai.com/api/docs/models).
For this plan, **Preferred** is the quality/cost choice to use by default;
**Minimum** is the lowest tier allowed for the stated purpose, not a claim of
equal narrative quality. All authoring model uses remain explicitly gated and
reviewed.

| Phase | Preferred | Minimum | Rationale and operating rule |
| --- | --- | --- | --- |
| 0 — Characterization | No provider required | No provider required | Fixtures, diagnostics, and source editing must be deterministic. If the optional noncanonical Brief-draft tool is built, use Terra; Luna is acceptable only for throwaway brainstorming that a human rewrites. |
| 1 — Contracts | No provider required | No provider required | Schema, validators, bound IR, profiles, and audit reports must never depend on model output. |
| 2 — Offline generation and review | **Sol, high reasoning** | **Terra, high reasoning** | This is the quality-critical generation of causal structure, dramatic beats, and storylet pools. Use Sol for vertical slices, final candidates, or thin/complex source material. Terra may produce promotable candidates only after the same local validation, critic, simulation, and editorial review. Luna may produce noncanonical prompt/volume experiments, never the candidate submitted for promotion. |
| 3 — Runtime projection and selector | No provider required | No provider required | Projection, eligibility, ranking, and player-visible context are deterministic runtime behavior. |
| 4 — Proposal, validation, and commit | No new offline provider use | No new offline provider use | The ordinary runtime model is not authoring storylets. For optional live smoke/manual playthroughs, prefer Terra at medium reasoning; Luna is sufficient only for transport or fail-closed tests, not narrative-quality evaluation. |
| 5 — Simulation and promotion | **Terra, high reasoning** for batch candidate evaluation; **Sol, high reasoning** for final narrative comparison or recompilation | **Terra, high reasoning** | Deterministic simulation itself needs no model. Use Terra to control evaluation cost across the outline corpus; reserve Sol for the final candidate/repair when editorial review or simulation shows that richer dramatic content is needed. Do not use Luna to decide promotion quality. |

Reasoning effort is intentionally part of the recommendation: structured causal
and storylet generation benefits from high reasoning, while model use outside
those tasks is either unnecessary or should be treated as a low-cost transport
test. The tier is recorded in candidate provenance so Phase 5 can compare
acceptance, repair rate, route/storylet coverage, and editorial outcomes by
model and reasoning effort rather than assuming one tier is equivalent to
another.

The live compiler interface must expose this as `--quality-tier preferred` or
`--quality-tier minimum`, not an arbitrary `--model` parameter. The selected
tier resolves once per run and configures every inference-capable compiler call,
including the bounded repair request. The compiler records the resolved model,
tier, and generation mode in its non-playable candidate/diagnostic provenance.

For end-to-end debugging, the compiler also exposes `--debug` as an explicit
alternative to `--quality-tier`. It resolves every compiler request in that run
to Luna at low reasoning effort and marks the candidate/diagnostic as debug.
Debug artifacts are intentionally non-promotable and cannot become runtime
input; use them to find transport, parsing, binding, or validation defects
before spending tokens on Terra or Sol.

## Delivery phases

### Phase 0 — Characterization and acceptance vocabulary

- [x] Write tests first for desired behavior using mystery, fantasy, sci-fi, and relationship fixtures: multiple eligible situations, free-form actions outside a storylet, protected knowledge, failure-forward, and non-repetition.
- [x] Record current runtime context size, normal-turn model-call count, material-progress rate, active-beat behavior, and baseline narrative samples as diagnostics, not golden prose assertions.
- [x] Define measurable acceptance criteria: every required beat has two or more distinct advancement paths where appropriate; a player can finish via distinct route families; no protected fact leaks; a repeated storylet is not selected after its completion fact; and normal turns retain the provider-call budget.
- [x] Select one authoring-only vertical-slice outline and one reviewed fixture for migration. Do not alter generated candidates or reviewed artifacts by hand; improve their source Brief or compiler output instead.

**Exit criteria:** [x] A cross-genre test vocabulary exists before contract changes, and the chosen vertical slice has explicit author-approved dramatic direction.

### Phase 1 — Source and immutable contracts

- [x] Extend the Story Brief schema and normalizer with the typed creative direction above, preserving strict unknown-field rejection outside extensions and preserving source provenance/hash behavior.
- [x] Add DramaticSpine, Storylet, availability predicates, consequence declarations, and fact-backed activation/completion markers to the causal contracts and bound IR.
- [x] Add symbol namespaces and binding diagnostics for every new reference: beat, storylet, consequence, participant, location, truth, and failure-forward target.
- [x] Introduce generic profile requirements such as minimum storylet variety, maximum unbroken pressure span, and required alternate progression paths. Store them in versioned profile data rather than genre checks.
- [x] Add local semantic validation: satisfiable availability, participant and location compatibility, declared fact effects only, protected-fact safety, no failure-forward cycles without an exit, idempotence of completion markers, and viable routes to each required end state.
- [x] Update the candidate review/audit report to show storylet coverage by beat, purpose, realization mode, route family, and failure-forward chain.

**Tests:** source validation; complete binding diagnostics; unknown and wrong-namespace references; unsatisfiable predicates; invalid consequence template; protected leak; cyclic failure forward; route-less required beat; and every profile's minimum variety rules.

**Exit criteria:** [x] A valid reviewed candidate can represent rich storylets without any new runtime authority, and invalid content fails locally before review or bootstrap.

### Phase 2 — Offline OpenAI candidate generation and review

- [ ] Extend the blueprint compiler prompt to request a coherent dramatic spine and bounded storylet pool only after it has planned causal truths, locations, revelations, and endings. Include the source's creative direction and hard constraints explicitly.
- [ ] Require complete JSON contracts, not prose fragments or provider-specific schemas. Local contracts remain authoritative.
- [ ] Extend repair context, symbol ledger, and structural-diff policy so a repair may add declarations needed by a diagnostic but cannot rewrite unrelated accepted causal content.
- [ ] Add deterministic storylet critics: coverage/diversity, dramatic escalation, participant continuity, protected-knowledge safety, and failure-forward viability. Critics report all independent diagnostics in stable order within the existing repair budget.
- [ ] Preserve candidate/review/provenance workflow. Generated storylets remain unplayable until the full artifact has passed validation and editor review.
- [ ] Update the review checklist to require human inspection of dramatic questions, participant agency, repeated-content risk, consequence quality, and distinct paths, not merely valid JSON and causal reachability.

**Tests:** prompts include hard constraints and creative direction; provider-envelope failures retain current recovery bounds; model candidates with invalid storylets receive deterministic diagnostics; repair scope rejects unrelated rewrites; review rejects a causal-but-storylet-incomplete candidate.

**Exit criteria:** a paid, explicitly gated run can produce one reviewable vertical-slice candidate containing a validated dramatic spine and storylet pool, with no runtime change yet.

### Phase 3 — Runtime narrative-package projection and selector

- [ ] Replace the lossy reviewed-blueprint-to-CompiledStory projection with a backward-compatible immutable runtime narrative projection that retains the reviewed spine, storylets, consequence templates, and provenance binding. CompiledStory remains supported while consumers migrate.
- [ ] Bootstrap immutable storylet definitions into RuntimeState only as a read-only package reference. Seed all mutable selection state—active, completed, aborted, discovered, relationship, and pressure markers—as facts.
- [ ] Add a constructor-injected StoryletSelector that receives the immutable projection and FactStore, deterministically returns a small ranked eligible set, and never mutates state or invokes a provider.
- [ ] Rank by active beat, availability predicates, participant/location validity, declared pressure range, priority, recent-use facts, and failure-forward urgency. Define stable ID tie-breaking for replayability.
- [ ] Make the selector degrade safely: when no storylet is eligible, provide ordinary freeform context without inventing an objective or forcing a transition.
- [ ] Extend runtime context with active beat situation, top eligible storylets, their allowed realization modes/consequences, and only player-visible facts. Do not send protected or unavailable storylet content to the model.

**Tests:** deterministic selection; no mutation during selection; location and presence filtering; stable ties; completion/non-repetition facts; protected storylets absent from model context; empty-pool freeform behavior; and cross-genre bootstrap.

**Exit criteria:** an immutable reviewed narrative package survives bootstrap, and runtime exposes relevant dramatic opportunities without changing state.

### Phase 4 — Proposal, validation, and commit integration

- [ ] Extend the ordinary turn-result contract with an optional storylet realization containing a selected storylet ID, realization mode, declared consequence IDs, and evidence for claimed completion/abort. Do not allow raw runtime paths or undeclared facts through this field.
- [ ] Add a generic validation policy that verifies selection eligibility at the current fact snapshot, realization mode, participant presence, consequence authorization, completion/abort rules, required revelation gates, and failure-forward conditions before committing.
- [ ] Translate accepted consequence templates into typed fact operations and commit atomically with ordinary validated operations. The renderer receives only post-commit state.
- [ ] Let freeform LLM proposals remain valid when they do not select a storylet. They cannot assert a storylet's protected truth or mark it complete without passing the new policy.
- [ ] Update pacing and beat progression to consume committed fact outcomes, not model-declared beat tags alone. Preserve existing save/load, trace, and integrity-projection guarantees.
- [ ] Keep storygame.web_demo thin; it should consume the shared runtime response and require no storylet-specific deployment branch.

**Tests:** valid realization commits every fact before narration; stale or ineligible selection fails closed; unknown storylet/mode/consequence fails closed; no protected leakage through prose or dialogue; failure forward opens the declared alternative; freeform turns remain proposal-first; recovery stays at two provider calls; save/load preserves selection facts; all tests span the four supported genres.

**Exit criteria:** a reviewed storylet can influence progression safely during ordinary play without changing the free-form player contract or fact authority.

### Phase 5 — Simulation, vertical slice, and promotion

- [ ] Build an authoring-only simulation harness that drives the deterministic selector and validation policy with goal-focused, exploratory, social, avoidant, aggressive, and chaotic-but-legal policies. It must not require paid or runtime LLM calls.
- [ ] Measure ending reachability, dead ends, revelation order, storylet reuse, selection diversity, pressure trajectory, blocked-action rate, and distinct paths to climax. Emit versioned, non-runtime evaluation reports.
- [ ] Compile and review the vertical-slice Story Brief. Run simulation and manual narrative playthroughs before promotion; correct the source Brief or compiler/contracts, never generated candidate/reviewed artifacts directly.
- [ ] Add parallel cross-genre fixtures and regression cases. Only after all profiles pass the generic contract can this become the default authoring and runtime path.
- [ ] Update authoring, operational, and runtime documentation. Then run TMPDIR=/tmp uv run pytest -q, uv run ruff check --fix ., uv run ruff format ., and focused tests affected by formatting.

**Exit criteria:** the vertical slice demonstrates materially richer, non-repetitive narrative with fact-backed continuity; simulation and manual review show multiple viable paths; full cross-genre regression coverage and project coverage remain at least 90%.

## Migration decisions

1. Do not convert every outline at once. First prove the complete flow for one reviewed vertical slice, then migrate one fixture per supported genre.
2. Do not create a mutable quality store. If an author wants a quality such as trust, danger, or preparedness, represent it as a typed fact/predicate family with explicit policy and serialized fact-state behavior.
3. Do not use storylets as a replacement parser. They constrain proposed consequences, not what the player may attempt.
4. Do not make runtime LLMs select truth. The deterministic selector determines eligibility; validation determines commit; the model supplies intent, framing, dialogue, and prose.
5. Do not add automatic multi-pass provider planning to the authoritative compiler. Improve the source Brief and one complete candidate contract; retain the bounded repair path and human review gate.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Thin outlines produce generic content | Require enriched Story Brief direction; use a noncanonical draft tool and editorial review. |
| Giant candidates exceed provider reliability | Bound pool size per beat, compile one complete typed object, and validate/repair within the existing budget. |
| Runtime context becomes too large | Selector sends only the active situation and a small eligible set, never the whole pool. |
| Storylets feel like a command menu | Preserve freeform input; use storylets as opportunity/consequence constraints, not accepted-command lists. |
| Repetition or pacing stalls | Fact-backed use markers, priority/pressure bands, simulation metrics, and profile-level diversity rules. |
| New data bypasses canonical truth | Keep storylets immutable; authorize only typed fact templates at the existing atomic commit boundary. |

## Completion definition

This plan is complete only when an editor-reviewed, OpenAI-compiled story contains a fact-backed dramatic spine and storylet pool; the generic runtime selects and validates those situations while preserving free-form play; and cross-genre tests plus deterministic simulations show that the system remains winnable, knowledge-safe, non-repetitive, and within the existing ordinary-turn provider budget.
