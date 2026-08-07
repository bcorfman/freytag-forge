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

The local web surface and hosted demo remain separate adapters. For the
development commands and API contracts, see [docs/PRD.md](docs/PRD.md) and
[docs/fact-authority.md](docs/fact-authority.md).
