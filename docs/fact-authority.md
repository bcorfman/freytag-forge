# Fact authority

Canonical runtime state lives in `GameState.world_facts`. Location, custody,
goals, flags, scene state, roles, and other asserted world state are changed
through `ValidatedFactCommitter`, which validates invariants before refreshing
compatibility projections.

`GameState.player`, room collections, and `active_goal` are read-after-commit
projections. `world_package` is authoring/session input, not a second runtime
authority. Control-plane command handling is separate from semantic turn
execution, which reads canonical facts only.

Persistence may import values missing from old object-view saves through the
explicit `persistence_projection_migration` source. Canonical facts win when
both representations contain a value. `StoryState.json` and `STORY.md` render
runtime location, inventory, flags, room contents, and active goal from facts;
their existing integrity hash chain remains enforced.

Proposal state deltas pass through the Phase 2 predicate-policy registry before
they reach the committer. Each declarative predicate identifies its family,
legal commit sources, normalization mode, invariants, and derived-update owner.
Unknown or proposal-forbidden predicates are rejected without changing the
fact store. Intent families similarly map to bounded effects; they do not grant
the model permission to invent arbitrary predicates.

## Observer and evidence boundaries

`storygame.engine.perception.ObservationResolver` derives an observer's
existence, location, accessibility, perceptibility, observation, recognition,
and interpretation status from facts. `observer_context_slice` and
`speaker_context_slice` are the only supported projections for model context:
protected case truth is included only when the observer knows its key, while
scene facts are included only when the observer can perceive their entities.

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
