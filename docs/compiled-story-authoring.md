# Compiled-story authoring

`storygame.authoring` is an offline boundary. It validates immutable sources
and reviewed artifacts; it neither reads runtime truth as source material nor
mutates a live session. See the [PRD](PRD.md) for runtime behavior and
[genre-blueprint authoring](genre-blueprint-authoring.md) for the causal schema.

## Inputs and artifacts

`CompiledStory` is the stable `compiled-story-v1` bridge used by legacy
fixtures. It contains identity, premise, initial world state, characters,
protected revelations, and Freytag beats. Local validation rejects duplicate or
unknown IDs, dependency cycles, invalid phase structure, invalid completion
tags, and malformed pacing.

Full reviewed stories use `story-blueprint-v2`, selected from either one
`data/story_outlines.yaml` entry or one `freytag-story-brief-v1` document:

```text
uv run storygame-blueprint --outline-id <id>
uv run storygame-blueprint --story path/to/brief.yaml
```

Selectors are mutually exclusive and record stable source ID, format, and
SHA-256 provenance. Source notes guide the compiler but never become runtime
truth. Candidates are `*.candidate.json`; reviewed fixtures are selected only
through `data/compiled_stories/v2/runtime-fixtures.json`. Neither raw sources
nor candidates are runtime inputs.

Outline entries may add namespaced `extensions` for explicit authoring
direction that does not belong in the shared schema. The compiler forwards that
data unchanged; a source-declared `opening_setup.first_action_suggestions` map
is projected into the candidate before local validation so advertised opening
actions remain bound to declared targets. This is an authoring constraint, not
a runtime mutation path.

## Live compilation

Live compilation requires both `OPENAI_API_KEY` and
`FREYTAG_ENABLE_LIVE_COMPILER=1`, plus `--live` and either a quality tier or
`--debug`:

```text
OPENAI_API_KEY=... FREYTAG_ENABLE_LIVE_COMPILER=1 \
  uv run storygame-blueprint --outline-id <id> \
  --quality-tier preferred --live
```

`preferred` and `minimum` use the repository's reviewed model-tier policy.
`--debug` uses the non-promotable low-cost path. `OPENAI_BASE_URL`,
`--timeout-seconds`, `--background`/`--no-background`, and
`--transport-factory` are explicit integration controls; inspect
`uv run storygame-blueprint --help` for the current interface.

The compiler requests JSON-object mode, validates locally, and allows at most
one shared recovery request. It normalizes supported provider envelopes, then
runs binding, semantic, spatial, and interaction critics. An exhausted or
rejected run is a non-playable diagnostic artifact. It never overwrites a
reviewed fixture or exposes credentials in its output.

Incremental repair contracts are authoring evidence, not runtime inputs. A
revision binds a typed proposal to one base SHA-256 and approved stable-ID
semantic scope, applies only to a deep clone, and records its structural diff,
lineage, and unchanged-section digests. Unknown IDs, duplicate operations,
out-of-scope paths, and node-budget breaches fail closed. Supervisor routing
and CLI repair controls arrive in later phases.

For eligible low-risk work, Luna may propose that typed patch while Sol remains
the sole classifier and acceptance authority. Sol writes machine-executable
value, preservation, and diagnostic-clearance assertions before delegation. A
failed Luna patch receives one retry brief with failing assertion IDs and
expected/observed values; exhaustion records diagnostics and never promotes an
artifact. The existing `--live` gate remains the only route to a provider.

## Audit, diagnostics, and promotion

Run a read-only audit when a candidate needs review evidence:

```text
uv run storygame-blueprint-audit --candidate path/to/story.candidate.json
```

Use `--format json` for machine-readable output. Audits bootstrap the same full
runtime narrative projection used by play and require its participants, scene
subjects, evidence realizations/custody, groups, and declared opening targets
to be fact-backed. They also check compiler validation, terminal outcomes
(including every outcome's required truth), protected knowledge, route
diversity, failure-forward behavior, and map reachability; they do not call a
provider or alter the candidate.

An exhausted paid run may write a new `.diagnostic.json` with
`--diagnostic-output`; replay it locally with `--replay-diagnostic`. Diagnostic
files are never promotable.

`--autopromote` promotes only an accepted, non-debug candidate after local
revalidation, writes a new reviewed envelope, and atomically updates the
runtime-fixture map. To promote an existing accepted candidate without a model
request, use `--autopromote-candidate path/to/candidate.json`. Existing
artifacts receive timestamped names rather than being overwritten.

The authoring-only inventory evaluation command requires the same live gate and
a required output path:

```text
uv run storygame-blueprint-evaluate --live --quality-tier minimum \
  --output path/to/evaluation.json
```

It writes evidence only; it cannot create a runtime fixture. Run full tests and
the staging promotion process after any reviewed-package change.

Conversation-quality evidence is another offline-only promotion input. A
semantic policy driver runs isolated real-engine sessions; an independent critic
receives the accepted segments, authored profiles, and reviewed context, then
returns typed rubric scores with turn/segment citations. Write each immutable
result as `*.conversation.json`; never feed it into runtime state. Review the
individual, group, refusal, movement, and follow-up transcripts alongside the
fixture's audit before promotion.
