# Freytag Forge

> V2 cutover complete: the hosted V2 runtime is the only executable product surface. `RuntimeState` is its sole mutable authority; V1 engine, CLI, local-web, fact-policy, and proposal runtime code have been retired. All authored material under `data/` is intentionally retained as immutable V2 input or source data. The historical material below is pending consolidation; it must not be read as a current runtime contract.

Project docs: [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/bcorfman/freytag-forge)

## Write anything. Keep the story true.

Freytag Forge is an interactive-fiction engine where you can try the wild idea
without breaking the story. Investigate, bargain, lie, help, run, refuse, or
change the plan entirely. The story answers in the moment—and remembers what
actually happened.

The promise is simple: player freedom with consequences that stick. Models
write the scene; the engine keeps the world honest.

It is a story simulation with an open-language interface, durable choices, and
no tiny menu of approved verbs.

## Why it’s different

| Player freedom | Narrative intelligence | World integrity |
| --- | --- | --- |
| Players write natural-language intentions, not a small list of verbs. They can attempt any story move. | Models return narration and bounded typed effects in one structured turn contract. | Local validation commits only approved paths, custody changes, and ordered beat updates to `RuntimeState`. |
| Pacing directives nudge, advance, escalate, or force a consequence without dictating the player action. | Active beats, rolling events, summaries, and revelation protections are the only story context sent to the turn model. | Narration never mutates state; protected revelations, invalid paths, and out-of-order beats fail closed. |
| One normal model call keeps the loop responsive. | JSON-object mode is explicit transport metadata, with one plain-JSON fallback when rejected. | Runtime events retain prompt version/token estimates; later saves are projections rather than authorities. |

**Less prompt luck. More playable story.**

## Build the story before you run it

Every future causal story starts with an immutable source, never a runtime
shortcut. Pick an inventory outline or bring a standalone Story Brief; either
one resolves to a hash-bound, reviewable compiler input with its own declared
genre profile. Hard truths and ending constraints stay hard. World notes,
beats, possibilities, and author experiments stay creative direction—not
hidden mutable state.

The new Vale Mansion rebuild begins the same way: a distinct,
`authoring_only` raw outline, not an inferred copy of its old fixture. It can
be compiled offline and reviewed on its merits, while the hosted game continues
to boot only checked-in, reviewed `CompiledStory` artifacts.

Phase 1 gives that review a real spine. The new immutable `story-blueprint-v2`
contract names the map, connected routes, participants, causal events, timeline,
evidence custody, knowledge protections, outcomes, and Freytag gates. Local
critics prove terminal truths have evidence-backed routes and reject one-path
revelations, premature knowledge, impossible timelines, dead-end failures, and
optional detours masquerading as endings. Genre profiles set the obligations;
the engine stays genre-agnostic.

Phase 2 turns that spine into an intentional, paid drafting room—not a hidden
runtime dependency. The offline `storygame-blueprint` command can call OpenAI's
Responses API only when you explicitly acknowledge `--live` and enable it with
`FREYTAG_ENABLE_LIVE_COMPILER=1`. It binds each unreviewed candidate to its
source hash, selected model, prompt version, response ID when available, and
local validation record. Secrets and raw headers never enter the artifact.

```text
OPENAI_API_KEY=... FREYTAG_COMPILER_MODEL=gpt-5.6 FREYTAG_ENABLE_LIVE_COMPILER=1 \
  uv run storygame-blueprint --outline-id vale_mansion_rebuild --provider openai --live
```

That command writes a new `*.candidate.json` under
`data/story_blueprints/candidates/`; it will not overwrite a reviewed story.
The compiler asks OpenAI for JSON-object output first, then gets exactly one
plain-JSON recovery attempt if the provider rejects that mode or the response
is unusable. Gameplay and CI never make the call.

Phase 3 makes every draft earn its ending. The compiler plans backward—from
terminal truth, through cause and proof, to reachable opportunities—then locks
those discoveries to Freytag gates. Local causal, route-fairness, and
progression critics get one bounded repair pass with structured diagnostics.
Pass, and the candidate is marked locally validated. Fail, and it is still a
clearly non-playable review artifact with the exact obligations it missed.

Phase 4 makes acceptance deliberate. A locally valid candidate still cannot
become a reviewed story by accident: `storygame-blueprint-review` reruns the
causal, profile, fairness, and Freytag checks; records the candidate's SHA-256;
requires a named reviewer; and requires an explicit check of terminal roles,
knowledge boundaries, route diversity, failure-forward behavior, and map/custody.
It writes a fresh immutable reviewed artifact and never overwrites a prior one.
The Vale source now states the intended solution as raw compiler constraints—
not as inherited prose—and stays `authoring_only` until that human review happens.

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

The grounded turn contract checks material staging claims for custody,
environment, access, and events against a cloned post-effect world before
rendering accepted prose. It uses structured relations, not prose keyword
matching. Every staging candidate then plays all four genre fixtures through
the public hosted surface; SHA-bound evidence must clear the two-request cap,
integrity checks, under-ten-second p95 target, and the project’s 90% coverage
gate before it can be promoted.

## Start here

- [Product and architecture reference](docs/PRD.md)
- [LLM-first migration plan](.plans/gpt-refactor.md)
- [V1 production rollback baseline](docs/release-baseline.md)
- [V2 acceptance matrix](docs/v2-acceptance-matrix.md)
- [V2 migration scorecard](docs/v2-acceptance-scorecard.md)
- [Fact-authority contract](docs/fact-authority.md)
- [Grounded turn-contract plan](.plans/grounded-turn-contract-plan.md)
- [Grounded turn-contract boundary](docs/grounded-turn-contract-baseline.md)
- [Phase 5 staging and promotion gate](docs/phase-5-staging-evaluation.md)
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
| `uv run storygame-blueprint --outline-id vale_mansion_rebuild` | Inspect one immutable inventory source and its hash-bound compiler provenance; no provider is constructed. |
| `uv run storygame-blueprint --story path/to/brief.yaml` | Validate one standalone `freytag-story-brief-v1` source with its declared profile; no provider is constructed. |
| `uv run storygame-blueprint-review --help` | Review and promote one locally valid candidate with an explicit, SHA-bound human approval. |
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
