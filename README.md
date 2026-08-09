# Freytag Forge

Freytag Forge is an interactive-fiction game. Write what your character tries;
the story responds while keeping the world consistent from turn to turn.

## Playing

Open the game in your browser, then describe an action in plain language:

```text
Ask the guide what they noticed.
Follow the lantern-lit path.
Examine the strange device.
```

You can also use `save`, `load`, `help`, or `quit`.

Each story can take a different shape—from a mystery to a fantasy journey, a
technical crisis, or a relationship scene. Your choices guide the scene; the
game remembers their consequences consistently from turn to turn.

## Runtime guarantees

Ordinary turns are structured proposals: the story model supplies intent,
references, candidate effects, dialogue, narration claims, and beat hints in
one typed `TurnProposalV2` contract. Deterministic policy validates the
proposal before anything is committed. Canonical facts—not narration,
`STORY.md`, or package metadata—remain the runtime authority.

Predicate and rule packs are validated before a session is realized. Policies
cover world truth, perception, knowledge, relationships, tasks, traces, and
dramatic state, with explicit source permissions, normalization, invariants,
and derived-update ownership. Movement, examination, communication,
manipulation, transfer, concealment, assistance, opposition, and waiting are
bounded intent families; they are not a fixed command table. Unique visible
aliases resolve deterministically, while ambiguous references ask for
clarification.

Perception is observer-specific and fact-backed. The engine distinguishes an
entity's existence, location, accessibility, perceptibility, observation,
recognition, and interpretation. Concealment, exposure, lighting, weather,
traces, portals, and discovery are canonical predicates; player and NPC model
prompts receive only their permitted context slice. Evidence can move,
transform, become contaminated, or be reinterpreted through validated commits.

Post-action consequences run through a deterministic declarative rule engine
after direct effects and before triggers. Universal rules cover access paths,
environmental traces, information exposure, item discovery, and social stance;
genre packs extend the same validated schema without story-specific runtime
branches. The model also receives fact-derived affordances for legal exits,
locks, visible portable items, addressable NPCs, and held items.

Rendering is post-commit. Deterministic affordances such as `look`, named-place movement,
inventory, and unique visible-item aliases use the shared proposal path and then
make one story-model rendering call. The normal renderer uses deterministic
committed-state validation and permits one bounded repair call; critic,
extractor, and output-editor passes are excluded from ordinary turns. Narration
and dialogue cannot create facts after display, so visible changes require
accepted structured claims and committed deltas.

Freytag progression is also fact-driven. `BeatPolicy` selects a stable legal
beat from the current phase, role, pressure, obstacle, conflict, reveal budget,
and NPC scene goals; it does not prescribe the player’s approach. Reveal
scheduling and timed story events are evaluated together from canonical facts,
and progress/tension are derived presentation metrics rather than free-form
commit authorities.

NPCs use fact-backed role contracts for goals, capabilities, limitations,
initiative, relationships, advisory style, and permitted autonomy. Explicit
observer-scoped facts model what each NPC knows, believes, suspects, conceals,
or may infer; stable identity traits remain separate from bounded adaptive
traits. Delegated work follows a durable offer, acceptance, progress, result,
failure, or cancellation lifecycle. NPC actions are validated against role,
knowledge, location, resources, obligations, visibility, and scene state.

Story packages are authored and evaluated offline before they are realized into
runtime facts. The injected frontier-model pipeline produces typed characters,
motivations, rules, secrets, revelations, causal assumptions, role contracts,
beat plans, and endings; deterministic validation checks availability,
clue/revelation reachability, causal ending viability, and resilient alternate
information paths. Continuity, causality, and dialogue-fit specialists run in
parallel and a versioned deterministic rubric with critical floors decides
acceptance. Recovery is bounded by rounds, tokens, and wall-clock time, records
preserved/modified/discarded fact categories, and revalidates the candidate.
The evaluation harness also runs exploratory, goal-focused, social, adversarial,
avoidant, and chaotic scripted players against every frozen fixture.

The external story-data migration is tracked in
[`.plans/external-story-data-migration.md`](.plans/external-story-data-migration.md).
Phase 0 freezes four package projections and deterministic turn transcripts in
[`data/phase0_baseline.json`](data/phase0_baseline.json), and the static seam
inventory is documented in
[`docs/external-story-data-inventory.md`](docs/external-story-data-inventory.md).
Phase 1 package templates are stored in
[`data/story_packages.yaml`](data/story_packages.yaml). They declare map,
character, item, opening, intent-alias, and bounded-effect sections. The
builder expands and validates those sections before a package can be realized.
Phase 2 realizes every package through the same package-to-facts service:
room presentation, character placement and roles, item custody/state, opening
context, and document/case facts are committed from the package rather than
from genre-specific world setup. The former `opening_setup.yaml` is retained as
a migration reference only; runtime package construction no longer reads it.
Phase 3 makes presentation observer-aware and roleplay-forward. Public
briefings are explicit `knows(player, fact_key)` grants; opening and ordinary
turn prompts receive only the relevant observer or addressed-NPC fact slice.
Packages declare room short/long copy, NPC scene purpose, briefing facts, and
document visibility. Shared prompt policy permits expressive performance but
never treats it as a state mutation: visible changes and knowledge revelations
still require accepted fact commits.
Phase 4 replaces named document commands with package-declared readable-item
contracts. Their aliases, discovery, knowledge grants, context updates, and
leads are realized as facts; a single `read` intent commits those configured
effects for mystery files, fantasy scrolls, sci-fi logs, and romance letters.
Visible vehicle interaction and natural-language exit references likewise use
fact-derived item and path affordances rather than story-specific routing.
Phase 5 moves environmental coherence into the same boundary: every package
declares each room's exposure and optional ambient source, which are realized
as canonical facts. Ambient event prose reads those facts rather than room-name
keywords, while package validation rejects weather-sensitive items staged in
exposed rooms. Custody, location, role, and observer-knowledge conflicts remain
generic fact-policy failures across every genre.

The local web surface and hosted demo remain separate adapters. For the
development commands and API contracts, see [docs/PRD.md](docs/PRD.md) and
[docs/fact-authority.md](docs/fact-authority.md).

## Cutover and release gate

The proposal/commit runtime is the default for CLI, local web, and hosted-demo
turns. The retired narration-to-fact extractor has been removed: narration and
dialogue are render-only projections, and every visible state change must be
present in an accepted `TurnProposalV2` before commit.

CI enforces fatal lint checks, the full branch-coverage suite, deterministic
fixture and behavioral-evaluation reports, local/hosted API smoke tests, and
artifact-integrity checks. The selected cutover report is uploaded as the
`cutover-contracts` artifact.

## Test tiers and performance

Tests are tagged as `unit`, `component`, `integration`, or `evaluation`. Run
the fast feedback set with:

```text
TMPDIR=/tmp uv run pytest -m "unit or component" -q
```

For a repeatable collection and timing report, use:

```text
TMPDIR=/tmp uv run pytest --collect-only -q
TMPDIR=/tmp uv run pytest -q --cov --tier-report=artifacts/test-suite-health.json
```

The report records separate setup/call/teardown timings, CPU and wall time,
ranked top-20 setup/call tables, per-test runtime counts for full-world builds,
complete turns, SQLite stores, and TestClient constructions,
orchestration-contract classifications, plus source-level SQLite/web diagnostics.
The required CI gate uses ordinary coverage and remains coverage-gated at 90%.
An informational CI job retains the more expensive per-test coverage contexts.
Narrow policy and state tests use the synthetic factories in
[`tests/fast_fixtures.py`](tests/fast_fixtures.py); SQLite, web, artifact, and
complete-turn checks remain in the integration tier. See the
[test-suite performance guide](docs/test-suite-performance-guide.md) for the
fixture, CI jobs, and measurement conventions.
