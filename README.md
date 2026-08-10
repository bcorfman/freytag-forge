# Freytag Forge

## Write anything. Keep the story true.

Freytag Forge is a fact-backed interactive-fiction engine for stories that
need to feel open-ended without becoming incoherent. Players can negotiate,
investigate, improvise, travel, deceive, help, refuse, and take the scene in
unexpected directions. The engine answers with model-authored narration—but
only after deterministic policy has decided what can become true.

The bet is simple: compelling AI storytelling does not need to choose between
freedom and continuity. Put the world in explicit, validated facts; let models
propose the move and write the moment; commit only what the world can support.

This is not an LLM text generator wrapped around a command parser. It is a
story simulation with an open language interface, durable consequences, and a
clear boundary between authored possibility, canonical state, and prose.

## Why it’s different

| Player freedom | Narrative intelligence | World integrity |
| --- | --- | --- |
| Players write natural-language intentions, not a small list of verbs. They can attempt any story move. | Models propose intent, dialogue, framing, and bounded effects in one structured turn contract. | Typed deterministic policy validates every accepted change before it is committed to canonical facts. |
| Clear directions, inventory, and unique visible references are convenient affordances—not a separate parser era. | NPC dialogue is generated from the addressed character’s permitted context and role. | Narration is post-commit projection: prose cannot invent state, reveal protected knowledge, or quietly rewrite history. |
| Ambiguity gets a clarification; irreparable goal breaks get an explicit confirmation. | Freytag-aware dramatic policy responds to pressure, obstacles, reveals, and scene goals without prescribing player intent. | Saves, replay signatures, transcripts, and `STORY.md` are integrity-checked projections, never mutation authorities. |

**Less prompt luck. More playable story.**

## Highlights

| Build worlds | Run scenes | Trust the result |
| --- | --- | --- |
| Validated external story packages declare maps, characters, roles, knowledge boundaries, custody, discoveries, rules, and endings. | Proposal-first turns keep ordinary play expressive while bounded policy commits only legal, coherent consequences. | Fact-backed persistence, deterministic replay, artifact integrity checks, and cross-genre regression fixtures make behavior inspectable. |
| One story-agnostic engine supports mystery, fantasy, sci-fi, relationship scenes, and new genres without shared-runtime genre branches. | Observer-scoped perception and knowledge prevent the player or an NPC from receiving information they have not earned. | Provider responses are untrusted at the JSON boundary; malformed output gets at most one repair request, then fails closed with a typed error rather than fabricating a successful turn. |
| Offline authoring and evaluation can use frontier models; runtime packages remain locally validated. | NPCs operate under explicit role contracts for goals, knowledge, location, capabilities, limitations, and delegated work. | Local web and hosted-demo adapters stay separate while sharing the same engine contracts below the deployment boundary. |

## The core loop

```text
Player intent
    ↓
Structured model proposal
    ↓
Typed validation + deterministic policy
    ↓
Canonical fact commit
    ↓
Post-commit narration and dialogue
```

No response establishes world truth by itself. If a proposal is rejected, the
engine preserves truth and returns a bounded outcome or clarification.

## Start here

- [Product and architecture reference](docs/PRD.md)
- [Fact-authority contract](docs/fact-authority.md)
- [Frozen evaluation baseline](docs/evaluation-baseline.md)
- [Tiered refactor plan](.plans/tiered-refactor-plan.md)
- [Test-suite conventions and performance guide](docs/test-suite-performance-guide.md)

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

To play with OpenAI, set `OPENAI_API_KEY`. To play locally, install and run an
Ollama model, then pass `--narrator ollama`. The engine keeps provider
integrations behind injected adapters, so deterministic tests and offline
package validation do not require paid inference.

## Commands

| Command | Description |
| --- | --- |
| `uv sync` | Install runtime and development dependencies. |
| `uv run storygame --genre fantasy --tone epic` | Start a CLI story session with OpenAI. |
| `uv run storygame --narrator ollama --genre fantasy --tone epic` | Start a CLI story session with local Ollama. |
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

`save`, `load`, `help`, and `quit` are the only control-plane commands. The
story itself is open language.

## Quality that travels across genres

Freytag Forge freezes representative mystery, fantasy, sci-fi, and relationship
fixtures with prompts, adapter revisions, sampling settings, and seeds.
Evaluation measures proposal validity, direct acceptance, bounded-repair
success, protected-information leakage, role drift, latency, and token use.
Those measurements are informational baselines, not disguised release gates.

The ordinary runtime uses a single shared proposal/validation/commit contract
for freeform moves and deterministic affordances. It permits one recovery
request; if both planner responses are unusable, it preserves facts and raises
`ORDINARY_TURN_RECOVERY_EXHAUSTED` for offline evaluation instead of inventing
a fallback story response.

The project protects the contracts that matter: facts, turn execution, prompt
scoping, NPC dialogue, persistence, replay, and local/hosted surface parity.
New story packages should add validated data—not one more special-case branch
to the engine.

## Project map

```text
storygame/
├── engine/        # facts, policy, proposal/commit, perception, NPCs, rules
├── llm/           # typed adapters, constrained context, prompts, coherence
├── persistence/   # save state and artifact projections
├── plot/          # Freytag phases, beats, tension, dramatic policy
├── web.py         # local web adapter
└── web_demo.py    # hosted-demo adapter

data/              # validated story, rule, predicate, and evaluation inputs
tests/             # unit, component, integration, and evaluation contracts
docs/              # product, operational, and engineering reference
```

## The principle

Stories are allowed to surprise the engine. The engine is not allowed to lose
track of what happened.
