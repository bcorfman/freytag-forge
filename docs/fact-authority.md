# Fact authority

Canonical runtime state lives in `GameState.world_facts`. Location, custody,
goals, flags, scene state, roles, and other asserted world state are changed
through `ValidatedFactCommitter`, which validates invariants before refreshing
compatibility projections.

Grounded-turn-contract Phase 0 has recorded the remaining narration-integrity
gap: the current V1 freeform planner has a temporary regex custody guard, but
not yet a typed material-staging claim contract for custody, environment,
access, and events. The Phase 1 contract will validate those claims against a
candidate post-effect fact state; until then, the relation-family gap is kept
as strict expected-failure tests. The audit and current provider-call baseline
are in [grounded turn-contract baseline](grounded-turn-contract-baseline.md).

`GameState.player`, room collections, and `active_goal` are read-after-commit
projections. `world_package` is authoring/session input, not a second runtime
authority. Control-plane command handling is separate from semantic turn
execution, which reads canonical facts only.

Persistence may import values missing from old object-view saves through the
explicit `persistence_projection_migration` source. Canonical facts win when
both representations contain a value. `StoryState.json` and `STORY.md` render
runtime location, inventory, flags, room contents, and active goal from facts;
their existing integrity hash chain remains enforced.

The immutable Story Blueprint compiles offline from a raw outline and genre
profile, then realizes its declarations into the V2 blueprint fact map at
bootstrap. Route discoveries, evidence availability/custody, participant
knowledge, scene state, clocks, completed revelations, and beat state mutate
only through that map. Neither a raw outline, `WorldPackage`, legacy
`StoryPackage`, `CompiledStory`, nor Blueprint prose can mutate a live session.
The complete Phase-0 authority map and Vale Mansion causality baseline are in
[genre-blueprint authoring](genre-blueprint-authoring.md).

Phase-3 compiler candidates are also immutable offline artifacts. Their
provenance envelope (source hash, prompt/model metadata, diagnostics, critic
results, and repair record) is review evidence, not session state. A compiler
or critic rejection cannot be loaded as a package or realized into facts.

Proposal state deltas pass through the Phase 2 predicate-policy registry before
they reach the committer. Each declarative predicate identifies its family,
legal commit sources, normalization mode, invariants, and derived-update owner.
Unknown or proposal-forbidden predicates are rejected without changing the
fact store. Intent families similarly map to bounded effects; they do not grant
the model permission to invent arbitrary predicates.

An ordinary freeform planner turn has a shared recovery budget of two provider
requests: the initial proposal and, at most, one locally directed retry. JSON,
contract, wrong-speaker, and in-world dialogue validation all consume that same
budget. If it is exhausted, the runtime raises the typed
`ORDINARY_TURN_RECOVERY_EXHAUSTED` error and retains the pre-turn facts; any
follow-up belongs to offline evaluation, never a runtime fallback.

Story-agent provider responses are normalized at the JSON boundary before local
contract parsing. Supported envelopes include `narration`, `result.response`,
`choices[].message.content`, and direct structured proposal objects.

## Observer and evidence boundaries

`storygame.engine.perception.ObservationResolver` derives an observer's
existence, location, accessibility, perceptibility, observation, recognition,
and interpretation status from facts. `observer_context_slice` and
`speaker_context_slice` are the only supported projections for model context:
protected case truth is included only when the observer knows its key, while
scene facts are included only when the observer can perceive their entities.
For a direct NPC question, short visible-name aliases resolve to that NPC and
the conversational action target is bound to the same addressee; planner input
includes only that NPC's epistemic facts because scene facts are supplied
separately.
When an NPC is meant to brief the player on a document, that document-only
fact must be declared in the NPC's knowledge as well as in the document's
readable contract; otherwise the NPC may only repeat the public briefing.
The package validator rejects a disclosure whose key is not document-declared,
a canonical `case_fact`, known by its named NPC, or still non-public at the
opening. The planner may select only this validated declaration, and local
validation consumes its existing one-retry recovery budget when it omits a
required briefing disclosure.

Concealment, exposure, lighting, weather, sensory blocking, portals, traces,
discovery, evidence state, and contamination are declared in the core policy
pack. Evidence placement continues to use the existing custody/room
cardinality rules, and evidence state is single-valued so transformations do
not leave contradictory canonical states.

## Consequences and affordances

`storygame.engine.consequences.apply_consequences` runs validated declarative
rules after a direct semantic effect and before turn triggers. Rule conditions
bind only against canonical facts; effects are normalized through the
predicate-policy registry and committed through `ValidatedFactCommitter`.
Each rule binding fires at most once per pass in stable rule order. Narration-
only turns do not run the pass, so prose cannot create downstream truth.

Universal rules live in `data/rules/core_rules.yaml`; genre extensions live in
`data/rules/genres/`. `build_affordance_context` derives legal exits, locks,
visible items, addressable NPCs, and inventory from facts for model context.
It is advisory context, not a mutation authority.

Readable-item contracts are also realized into canonical facts: `item_affordance`,
`item_alias`, document discovery, knowledge, lead, and context facts. The one
generic `read` intent validates current access (including an on-scene holder)
and commits only those declared effects. Path aliases are likewise package data
realized as facts for natural-language exit resolution.

Package validation applies a genre-neutral physical-placement invariant:
readable documents and weather-sensitive items cannot begin in an outdoor room
unless their declarative `placement_security` is `protected`. Player or NPC
custody is already protected; `protected` covers an authored secure, enclosed,
anchored, or locked placement without hard-coding its form.

An authored readable document that grants knowledge must include at least one
fact absent from the opening briefing. The planner receives those still-unknown,
declared facts only when the player requests that accessible document, so reading
advances information without leaking it through ordinary scene context.

## Post-commit rendering

Ordinary rendering receives observer-scoped context after direct effects,
consequences, triggers, and dramatic updates have committed. The fast gate uses
deterministic validators only and allows one bounded model revision when a
candidate conflicts with committed exits, inventory, visibility, or recent
events. Critic, extractor, and editor passes are not part of the normal path.

Accepted narration and NPC dialogue are projections of committed results; they
are never parsed back into facts. The retired narration-to-fact extraction path
is absent from the runtime. Any visible item, location, relationship, or
revelation must arrive through a validated structured proposal and fact commit
before it can be rendered. Opening/bootstrap retains its separate structured
proposal, validation, commit, and prose-validation sequence.

## Story-package authoring and evaluation

Phase 1 runtime package inputs are loaded from the declarative templates in
[`data/story_packages.yaml`](../data/story_packages.yaml). `build_world_package`
expands the selected template with outline and curve inputs, then
`validate_world_package` checks map paths, character locations, item custody,
opening knowledge boundaries, aliases, and effect-template shapes before world
realization. Opening setup is declared in the validated story package and is
not a runtime authority.

Opening presentation is turn-aware: turn-zero narration introduces the
protagonist before the setting and establishes visible contacts once. Later
turns continue from that context rather than reintroducing people, repeating
opening stakes, or replaying atmospheric setup. A contact's opening scene
purpose is declarative package data; packages that defer document review state
any privacy constraint there so narration keeps protected discussion away from
witnesses.

Every non-control-plane player input receives an LLM proposal. Deterministic
affordance recognition may normalize and commit a document-read effect, but it
does not author the player-facing reply. A proposal that merely echoes the
player's statement is invalid, uses the bounded recovery request, and fails
closed if the retry is also an echo.

`storygame.story_packages` is an offline-only authoring boundary. Its generated
packages are validated inputs, never runtime mutation authorities: only their
subsequent realization may assert canonical facts. Package validation requires
typed characters with motivations and role contracts, world rules, secrets,
clues and revelation paths, causal assumptions, beats, and viable endings. A
resilient revelation must retain two distinct clue paths.

The authoring pipeline injects the frontier generator, three specialist critics
(continuity, causality, dialogue fit), and an optional recoverer. Critics run in
parallel; the existing deterministic weighted judge applies a versioned rubric
and critical floors. Round, token, and wall-clock budgets bound review. Any
recovery records preserved, modified, and discarded fact categories and passes
full package validation again. `evaluate_fixture_playability` retains the
structured artifacts from all six scripted player styles for regression use.

## NPC roles and delegated work

`storygame.engine.npc` provides the Phase 5 boundary contracts and policy
services. `RoleContract` installs goals, capabilities, limitations, initiative,
relationship, advisory style, autonomy, stable traits, and bounded adaptive
traits as facts. `record_epistemic_fact` records explicit `knows`, `believes`,
`suspects`, `conceals`, and `may_infer` facts; `speaker_context_slice` exposes
only the addressed NPC's permitted epistemic slice.

`offer_task`, `accept_task`, `progress_task`, `complete_task`, `fail_task`, and
`cancel_task` enforce the task lifecycle through canonical `task` facts and
durable result/consequence facts. `validate_npc_action` is side-effect free
and checks role capability, knowledge, location, target visibility, resources,
obligations, and autonomous-action permission before a caller commits an
accepted proposal.

## Dramatic policy

`storygame.plot.beat_policy.BeatPolicy` reads canonical dramatic facts for
phase, beat role, pressure, obstacle mode, active conflict, reveal opportunity
and budget, and NPC scene goals. Its output is a deterministic legal beat
decision with consequence classes and a selection reason; it does not select or
reject player actions. Reveal and timed-event eligibility are evaluated in one
fact-driven pass, so a turn cannot consume one progression category while
silently suppressing another. Legacy `progress` and `tension` fields remain
compatibility projections for persistence and clients; policy decisions are
bounded by canonical dramatic state and validated consequences.
