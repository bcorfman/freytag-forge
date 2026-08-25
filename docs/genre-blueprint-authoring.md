# Genre-blueprint authoring

`story-blueprint-v2` is the immutable, reviewed causal package for all genres.
It declares provenance, truths and protections, participants, locations and
routes, causal events, evidence opportunities, revelations, realization routes,
beats, outcomes, storylets, interaction frames, and viable endings. Facts remain
the only mutable session truth. See [compiled-story authoring](compiled-story-authoring.md)
for operating the compiler and the [PRD](PRD.md) for runtime behavior.

## Generic contract

The authoring validator first binds references through explicit namespaces, then
validates the immutable bound graph. It rejects duplicate/unknown IDs,
unreleased protected facts, impossible map or event order, invalid custody,
route-less required revelations, invalid endings, unsupported opening targets,
and failure-forward cycles.

Spatial declarations are complete rather than inferred from prose: participants
have public presentation, initial placement, availability, and optional
movement plans; scene subjects and evidence realizations have location/custody;
groups require co-present members. Public descriptions and performance profiles
cannot repeat protected truths.

Storylets declare availability, realization modes, bounded consequences,
lifecycle markers, and alternatives. Dialogue-capable storylets use interaction
frames with a profiled initiator, participants, locations, objective, tactics,
response obligations, agency exits, and fact-backed completion/abort behavior.
These declarations guide the model; they do not prescribe player commands or
execute effects.

## Genre profiles and compilation

Versioned YAML profiles in `data/genre_profiles/` inject genre-specific causal
requirements through validation adapters, never runtime branches. New genres
need a profile, any necessary injected validator adapter, and valid/invalid
fixtures. The shared contract still enforces source provenance, protected
knowledge, route fairness, and viable endings.

`BlueprintCompiler` plans terminal truths and geography before revelations,
beats, storylets, and interaction frames. It receives an injected transport,
uses JSON-object mode as syntax assistance, locally validates every response,
and shares one recovery request among JSON-mode fallback, malformed output,
semantic repair, and transport failure. Repairs receive typed diagnostics and a
symbol ledger; unrelated destructive changes are rejected rather than merged.

Spatial-continuity and interaction-viability critics run at compilation, audit,
and promotion. They verify reachable actors/evidence/witnesses/opening targets,
and coherent profiled dialogue with safe knowledge, tactics, exits, and legal
movement. A package that fails these checks cannot become reviewed input.

## Authority and verification

| Material | Role | Mutable during play? |
| --- | --- | --- |
| Raw outline or Story Brief | Offline source | No |
| Candidate/reviewed blueprint | Immutable authoring package | No |
| `CompiledStory` | Legacy-compatible runtime bridge | No |
| `RuntimeState.facts` | Canonical session truth | Yes, through validation only |
| Saves, artifacts, traces, transcripts | Integrity-checked projections | No |

Authoring-quality tests cover every supported genre. Run them with:

```text
TMPDIR=/tmp uv run pytest -q --no-cov -m authoring_quality
```

Collection totals are informational. The full suite and the 90% coverage floor
remain required before staging.
