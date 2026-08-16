# Freytag Forge

Project docs: [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/bcorfman/freytag-forge)

## Write anything. Keep the story true.

Freytag Forge is an interactive-fiction engine for stories that need to feel
open-ended without becoming incoherent. Players can negotiate, investigate,
improvise, travel, deceive, help, refuse, and take the scene in unexpected
directions. The next runtime answers with model-authored narration—but only
after local validation has accepted the state changes.

The bet is simple: compelling AI storytelling does not need to choose between
freedom and continuity. Put mutable session truth in a typed runtime state; let
models propose the move and write the moment; commit only what the story schema
can support.

This is not an LLM text generator wrapped around a command parser. It is a
story simulation with an open language interface, durable consequences, and a
clear boundary between immutable authored possibility, canonical runtime state,
and prose.

Phase 3 of the V2 migration provides the standalone in-process runtime.
Versioned `CompiledStory` fixtures bootstrap its sole mutable authority,
`RuntimeState`; model turns use one structured request plus at most one shared
recovery request and fail closed without partial commits. The V2 mystery
fixture now carries the authored Vale Mansion investigation (Elias Wren, Daria
Stone, Emma Vale, and the ledger-payment case) rather than a replacement
placeholder. The existing package/fact web product remains the fallback until
the V2 hosted path passes staging promotion and its observation window.

Phases 0–2 of genre-blueprint authoring are complete. The project has an
explicit authority map, a cross-genre offline authoring-quality suite, and an
immutable, locally validated `StoryBlueprint` contract with minimal mystery,
fantasy, sci-fi, and relationship fixtures. The contract validates causal
references, revelation cycles, protected-fact release ordering, route
reachability, ending viability, and optional-beat purpose. It remains
offline-only: blueprint prose cannot mutate a session, and facts remain the
sole mutable session truth.

Phase 2 adds versioned declarative profiles for mystery, fantasy, sci-fi, and
relationship stories. An injected authoring validator registry checks each
profile's causal roles, revelation and evidence routes, Freytag turning points,
phase order, and viable genre endings—without introducing runtime genre
branches.

Phase 3 adds the offline-only `BlueprintCompiler`. It requests an explicit
JSON-object response, performs at most one plain-JSON recovery request, locally
validates the blueprint and selected genre profile, and reviews route fairness
before emitting a reviewable candidate. Candidate provenance records the source
outline hash, prompt version, model metadata, validation diagnostics, critics,
and any single repair. `storygame-blueprint` requires both `--live` and
`FREYTAG_ENABLE_LIVE_COMPILER=1`, and refuses to overwrite files or write a
candidate under a reviewed-fixture name.

Phase 4 adds the editor-reviewed Vale Mansion blueprint at
`data/story_blueprints/v1/vale_mansion_case.yaml`. It records the complete
crime solution, party knowledge, bounded timeline, evidence custody, location
classes, protected truth, and two fair routes through every pivotal revelation.
Its authoring acceptance suite verifies that a solved case follows declared
evidence rather than a narration or completion tag.

Phase 5 realizes an accepted blueprint into a dedicated fact map at V2
bootstrap. The shared turn contract carries a declared `route_id`, optional
`evidence_ids`, and a failed-route signal. `ProgressionValidator` accepts only
currently legal authored routes, atomically commits their satisfiers or bounded
failure-forward facts, and rejects bare completion tags. Runtime prompts expose
only player-earned truths and legal route metadata; protected canon remains out
of model context until its declared revelation completes.

Grounded-turn-contract Phase 0 is complete. Its boundary audit maps the CLI,
local web, hosted demo, freeform adapter, opening agents, and Story Director;
it records the current one-call normal / two-call bounded-recovery budget. The
audit keeps custody, environment, access, and event contradiction cases as
strict expected-failure specifications until the Phase 1 typed `staging_claims`
contract replaces the temporary phrase-based custody guard. See the
[grounded turn-contract baseline](docs/grounded-turn-contract-baseline.md).

## Why it’s different

| Player freedom | Narrative intelligence | World integrity |
| --- | --- | --- |
| Players write natural-language intentions, not a small list of verbs. They can attempt any story move. | Models return narration and bounded typed effects in one structured turn contract. | Local validation commits only approved paths, custody changes, and ordered beat updates to `RuntimeState`. |
| Pacing directives nudge, advance, escalate, or force a consequence without dictating the player action. | Active beats, rolling events, summaries, and revelation protections are the only story context sent to the turn model. | Narration never mutates state; protected revelations, invalid paths, and out-of-order beats fail closed. |
| One normal model call keeps the loop responsive. | JSON-object mode is explicit transport metadata, with one plain-JSON fallback when rejected. | Runtime events retain prompt version/token estimates; later saves are projections rather than authorities. |

**Less prompt luck. More playable story.**

## Highlights

| Build worlds | Run scenes | Trust the result |
| --- | --- | --- |
| Validated external story packages declare maps, characters, roles, knowledge boundaries, custody, discoveries, rules, and endings. | Proposal-first turns keep ordinary play expressive while bounded policy commits only legal, coherent consequences. | Fact-backed persistence, deterministic replay, artifact integrity checks, and cross-genre regression fixtures make behavior inspectable. |
| One story-agnostic engine supports mystery, fantasy, sci-fi, relationship scenes, and new genres without shared-runtime genre branches. | Observer-scoped perception and knowledge prevent the player or an NPC from receiving information they have not earned. | Provider responses are untrusted at the JSON boundary; malformed output gets at most one repair request, then fails closed with a typed error rather than fabricating a successful turn. |
| Offline authoring and evaluation can use frontier models; runtime packages remain locally validated. | NPCs operate under explicit role contracts for goals, knowledge, location, capabilities, limitations, and delegated work. | Local web and hosted-demo adapters stay separate while sharing the same engine contracts below the deployment boundary. |

Direct NPC briefings about readable documents use the same fact-commit boundary
as reading the document. A proposal names at most one declared, still-unknown
fact; the engine verifies the addressed on-scene speaker and document, commits
`knows(player, key)`, then renders the reply. The hosted-demo API contract test
confirms that this player-visible reply is committed before it can be saved.
Package validation requires each briefing key to be a document-declared,
canonical fact known by its holder and absent from the opening briefing. The
mystery case file and fantasy warded scroll demonstrate the same generic route.
The staging gate derives these opening questions from package data and verifies
both the rendered fact and its committed `known_facts` API projection.

## The core loop

```text
Player intent
    ↓
Bounded RuntimeContext + structured model result
    ↓
Typed validation + clone-first commit
    ↓
`RuntimeState` commit
    ↓
Committed event, summary, and response
```

No response establishes world truth by itself. If a result is rejected, the
engine preserves the byte-identical prior runtime state and returns a typed
fail-closed error.

Phase 1 of the grounded turn contract is complete: material staging claims for
custody, environment, access, and events are checked against canonical facts
on a cloned post-effect candidate before narration can be accepted. This is
structured relation validation, not prose keyword matching.

## Start here

- [Product and architecture reference](docs/PRD.md)
- [LLM-first migration plan](.plans/gpt-refactor.md)
- [V1 production rollback baseline](docs/release-baseline.md)
- [V2 acceptance matrix](docs/v2-acceptance-matrix.md)
- [V2 migration scorecard](docs/v2-acceptance-scorecard.md)
- [Fact-authority contract](docs/fact-authority.md)
- [Grounded turn-contract plan](.plans/grounded-turn-contract-plan.md)
- [Grounded turn-contract boundary](docs/grounded-turn-contract-baseline.md)
- [Frozen evaluation baseline](docs/evaluation-baseline.md)
- [Offline package authoring and playability](docs/offline-package-authoring.md)
- [V2 compiled-story authoring](docs/compiled-story-authoring.md)
- [Genre-blueprint authoring baseline](docs/genre-blueprint-authoring.md)
- [Tiered refactor plan](.plans/tiered-refactor-plan.md)
- [Test-suite conventions and performance guide](docs/test-suite-performance-guide.md)

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

The hosted demo uses Cloudflare Workers AI. Configure its Worker endpoint and
token before running a live session; deterministic tests and offline package
validation do not require inference.

## Commands

| Command | Description |
| --- | --- |
| `uv sync` | Install runtime and development dependencies. |
| `uv run storygame --genre fantasy --tone epic` | Start a CLI story session through the Cloudflare Worker. |
| `FREYTAG_ENABLE_LIVE_COMPILER=1 uv run storygame-blueprint --live --outline-id 123 --genre mystery --transport-factory package.module:factory --output data/story_blueprints/candidates/mystery_123.candidate.json` | Opt in to compile one raw outline into a non-overwriting reviewed-candidate envelope. |
| `make run` | Start the local web app at `http://127.0.0.1:8000`. |
| `TMPDIR=/tmp uv run pytest -q` | Run the full test suite with the required WSL temporary-directory setting. |
| `uv run ruff check .` | Check lint rules. |
| `uv run ruff format .` | Format the codebase. |

For reproducible CLI play, supply a seed:

```text
uv run storygame --seed 123 --genre sci-fi --tone tense --session-length short
```

Inside a story, write what your character tries:

```text
Ask the guide what they noticed.
Follow the lantern-lit path.
Examine the strange device.
```

`/save`, `/load`, `/help`, and `/quit` are the only control-plane commands.
The slash keeps them outside the story, so dialogue such as “leave me alone,”
“save your breath,” or “take a seat” remains open-language play.

## Quality that travels across genres

Freytag Forge freezes representative mystery, fantasy, sci-fi, and relationship
fixtures with prompts, adapter revisions, sampling settings, and seeds.
Evaluation measures proposal validity, direct acceptance, bounded-repair
success, protected-information leakage, role drift, latency, and token use.
Those measurements are informational baselines, not disguised release gates.
The frozen adapter matrix compares the Cloudflare Workers AI revision on every
fixture turn. Its 95% direct-or-one-
repair validation target is an informational SLO; scheduled runs are
credential-free, while any paid provider experiment must be explicitly enabled
with a bounded request budget.

The ordinary runtime uses a single shared proposal/validation/commit contract
for freeform moves and deterministic affordances. It permits one recovery
request; if both planner responses are unusable, it preserves facts and raises
`ORDINARY_TURN_RECOVERY_EXHAUSTED` for offline evaluation instead of inventing
a fallback story response.

The project protects the contracts that matter: facts, turn execution, prompt
scoping, NPC dialogue, persistence, replay, and local/hosted surface parity.
New story packages should add validated data—not one more special-case branch
to the engine.

Offline package validation projects every frozen fixture's declared map,
presentation, character role and knowledge boundaries, item custody,
discoveries, causal rules, and endings into one authoring contract. Frontier
models may propose packages or category-scoped repairs only offline; local
validation remains the acceptance authority. Playability checks exercise six
scripted player styles for every frozen fixture.

## Project map

```text
storygame/
├── authoring/     # V2 immutable compiled-story contracts and compiler
├── runtime/       # V2 RuntimeState, context, pacing, validation, and engine
├── engine/        # facts, policy, proposal/commit, perception, NPCs, rules
├── llm/           # typed adapters, constrained context, prompts, coherence
├── persistence/   # save state and artifact projections
├── plot/          # Freytag phases, beats, tension, dramatic policy
├── web.py         # local web adapter
└── web_demo.py    # hosted-demo adapter

data/              # validated story, rule, predicate, and evaluation inputs
├── compiled_stories/ # immutable V2 fixtures, grouped by schema version
├── story_blueprints/ # immutable Phase-1 causal contract fixtures
tests/             # unit, component, integration, and evaluation contracts
docs/              # product, operational, and engineering reference
```

## The principle

Stories are allowed to surprise the engine. The engine is not allowed to lose
track of what happened.
