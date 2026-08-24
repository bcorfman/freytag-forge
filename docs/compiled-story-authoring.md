# V2 compiled-story authoring

`storygame.authoring` is the Phase 2 offline boundary for V2 story input. It
does not read V1 world facts, proposals, policies, or runtime package contracts.
Its only model integration is an injected `CompilerTransport` with
`generate(prompt)`. Provider adapters remain transport concerns.

`CompiledStory` remains a reduced, immutable bridge fixture while the Phase-1
Story Blueprint contract is introduced. It does not encode a genre's full
causal solution or alternate realization routes. Its public API remains
available, and `compiled_story_as_blueprint` provides a one-way reduced
projection into `story-blueprint-v1` while consumers migrate; neither format
becomes runtime mutation authority. The authority map, Vale Mansion omissions,
and later success measures are documented in
[genre-blueprint authoring](genre-blueprint-authoring.md).

## Contract

`CompiledStory` is an immutable `compiled-story-v1` object. It contains:

- a stable story ID and version;
- premise, central question, genre, and initial world state;
- stable-ID characters;
- protected revelations released only after declared completion tags; and
- beats with Freytag phase, required dependencies/unlocks, completion tags,
  central-question resolution flag, and pacing thresholds.

Validation is local and fails descriptively before any session can use the
story. It rejects duplicate IDs, unknown beat or tag references, cycles,
missing crisis/climax/resolution phases, an independent climax, a resolution
that does not answer the central question, missing/duplicate completion tags,
and non-increasing pacing thresholds.

## Fixtures and optional compilation

Checked-in deterministic fixtures are versioned under
`data/compiled_stories/v1/` for mystery, fantasy, sci-fi, and relationship
stories. Load one with `load_compiled_story_fixture(genre)`.

For an offline authoring experiment, inject a transport into
`CompiledStoryCompiler` and set `FREYTAG_ENABLE_LIVE_COMPILER=1` before calling
`compile_live`. This explicit switch keeps model costs outside normal tests and
runtime execution. `compile` remains available for injected deterministic
transports used by authoring tests.

## Phase-0 source selection

The offline compiler has one immutable `NormalizedStorySource` boundary. An
explicit `--outline-id` selects exactly one entry from
`data/story_outlines.yaml`; an explicit `--story path/to/brief.yaml` selects
one standalone `freytag-story-brief-v1` document. The selectors are mutually
exclusive. Both paths validate the declared genre/profile locally and produce
stable source ID, source format, a SHA-256 content hash, and a deliberately
limited provenance path (inventory name plus ID, or brief filename).

A Story Brief requires `schema_version`, stable `id`, `genre`, `profile`,
`premise`, and `opening_public_boundary`. It may add `world_notes`,
`cast_notes`, `hard_truths`, `protections`, `ending_constraints`,
`dramatic_beats`, `possibility_library`, and `author_notes`. The hard-truth,
protection, and ending fields are compiler constraints; all note, beat, and
possibility fields are non-canonical creative direction. Extra top-level keys
are rejected. Open-ended metadata belongs only under `extensions`, whose keys
must be namespaced, such as `author.palette`.

`vale_mansion_rebuild` is an `authoring_only` raw inventory entry. It may be
selected by the offline source selector. Its approved causal artifact is
registered in `data/compiled_stories/v2/runtime-fixtures.json`; the normal
mystery runtime fixture loader validates that reviewed artifact and realizes a
read-only projection into the runtime's existing `CompiledStory` contract.
Other genres continue to load their reviewed `data/compiled_stories/v1/`
fixtures. Candidate artifacts live under `data/story_blueprints/candidates/`
as versioned `*.candidate.json` files and never become runtime input directly.

The existing Vale artifact is deliberately not source authority. Its absent west
gallery, prose-only upper gallery and long hall, unreachable evidence locations,
and unprovable solution graph are recorded as failures a later causal artifact
must reject rather than patch with narration.

Use Phase 0 to inspect a source without constructing a provider:

```text
uv run storygame-blueprint --outline-id vale_mansion_rebuild
uv run storygame-blueprint --story path/to/brief.yaml
```

`storygame.runtime.bootstrap_runtime_state` retains `CompiledStory` as its
public bridge input and can additionally receive a validated Story Blueprint.
The blueprint is realized into the runtime's fact-backed progression map; the
immutable inputs remain authoring data, never mutation authorities.

The V2 `mystery` fixture is a declarative projection of the retained authored
Vale Mansion case: Detective Elias Wren, Daria Stone, Emma Vale's death, the
case file and ledger-payment clues, the groundskeeper accusation, and the
evidence-gated resolution. It is data, not a mystery-specific runtime branch.
The V1 package/fact runtime remains the production fallback until the V2 hosted
path has passed staging promotion and its observation window.

## Blueprint compilation candidates

`CompiledStoryCompiler` remains the reduced-fixture bridge. Full causal
blueprints use the separate offline `BlueprintCompiler`, an injected genre
profile registry, and an explicit JSON-object transport request. It validates
the raw-outline ID/hash and all generic/profile semantics locally, runs
injected full-blueprint critics plus route-fairness review, and permits only one
repair/revalidation pass. It records a non-playable candidate envelope with
compiler provenance rather than overwriting a checked-in reviewed fixture.

## Phase-2 OpenAI candidate command

The first-party `OpenAIBlueprintTransport` uses the OpenAI Responses API at the
offline authoring boundary. It receives an explicit `OpenAICompilerConfig`
(API key, quality-tier-selected model, optional base URL, finite timeout) and implements the
`BlueprintCompilerTransport.generate(prompt, *, json_object)` protocol. It
normalizes plain text, fenced JSON, structured output, nested `result.response`,
and chat-choice envelopes before local parsing. Refusals, empty output,
timeouts, malformed envelopes, and rejected JSON mode are typed failures.

Run a paid compilation only when both the environment gate and the command
acknowledgement are present:

```text
OPENAI_API_KEY=... FREYTAG_ENABLE_LIVE_COMPILER=1 \
  uv run storygame-blueprint --outline-id vale_mansion_rebuild \
  --quality-tier preferred --live
```

`--quality-tier` is required for every promotable live compiler run: `preferred` resolves
to `gpt-5.6-sol` and `minimum` resolves to `gpt-5.6-terra`. Both use high
reasoning effort for the complete candidate and any bounded repair request.
There is deliberately no `--model` override or compiler-model environment
variable, so every inference-capable stage in one run uses the same reviewed
tier policy. `OPENAI_BASE_URL` optionally selects a compatible Responses
endpoint. `--timeout-seconds` sets a finite per-request timeout (default: 600
seconds). The compiler creates and polls an OpenAI background Response by
default, avoiding one long-lived HTTP connection. It requires a project without
Zero Data Retention because OpenAI retains that request briefly for polling.
Pass `--no-background` only for a compatible direct-response endpoint, or
`--background` to state the default explicitly. `--transport-factory module.path:factory`
is a mutually exclusive test/custom seam and still requires a model selection
(`--quality-tier` or `--debug`) and the same live gate. The normal non-live
command remains a source inspection tool.

For a low-cost end-to-end compiler smoke, pass `--debug` instead of
`--quality-tier`. Debug resolves every provider request in that run to
`gpt-5.6-luna` with low reasoning effort. Its candidates and exhausted
diagnostics are marked as debug and cannot be reviewed, promoted, or used as
runtime input:

```text
OPENAI_API_KEY=... FREYTAG_ENABLE_LIVE_COMPILER=1 \
  uv run storygame-blueprint --outline-id vale_mansion_rebuild \
  --debug --live --output data/story_blueprints/candidates/vale_debug.candidate.json
```

The compiler owns one shared recovery budget: it requests JSON-object mode,
then at most once retries without it. It locally validates the result and writes
only a fresh `data/story_blueprints/candidates/*.candidate.json` envelope. The
envelope records source format, ID, path, SHA-256 hash, provider, configured
model, prompt version, response ID when available, and local validation result.
It never includes API keys, headers, or a reviewed fixture overwrite. CI and
ordinary play do not invoke the live command; operator-owned smoke use is
deliberately skipped without credentials.

## Phase-5 diagnostics and troubleshooting

Full causal blueprints are checked in stages: syntax, symbol definitions,
reference binding, semantic passes, and critics. Binding uses explicit
namespaces for truths, participants, locations, map routes, causal events,
evidence opportunities, realization routes, revelations, outcomes, beats, and
end states. A binding diagnostic names the source path, expected namespace,
supplied ID, supplied namespace when known, and an unambiguous replacement when
one exists. `UNKNOWN_REFERENCE` remains the compatibility code for an ID that
does not bind; syntax and binding failures prevent later passes from masking
the original problem.

Repair requests receive the rejected candidate plus current and prior symbol
ledgers. The local structural audit classifies declaration additions,
removals, renames, ownership changes, and reference changes by namespace. It
rejects unrelated destructive edits as `UNRELATED_REPAIR_CHANGE`; it does not
silently merge or restore candidate content. The prompt supplies semantic
repair guidance, while the ledger and structural audit enforce identity and
scope locally.

When troubleshooting a failed run, start with the earliest stage in the
diagnostic report: provider syntax/schema failures, then binding errors, then
semantic or critic findings. The compiler allows one initial request and one
recovery request. An exhausted run remains a non-playable diagnostic artifact
and must be corrected and reviewed before promotion.

When a paid compilation exhausts, an operator may explicitly retain its raw
model attempts and typed local errors as a non-playable diagnostic artifact:

```text
uv run storygame-blueprint --outline-id vale_mansion_rebuild --live \
  --diagnostic-output data/story_blueprints/diagnostics/vale_mansion.diagnostic.json
```

The path must end in `.diagnostic.json` and cannot overwrite an existing file.
Replay it without a provider request with:

```text
uv run storygame-blueprint \
  --replay-diagnostic data/story_blueprints/diagnostics/vale_mansion.diagnostic.json
```

Diagnostic artifacts are debugging data only: they cannot be reviewed, promoted,
or used as runtime input.

For an OpenAI HTTP 429 response, the command reports only the safe diagnostic
allowlist: `request_id`, request/token limit, remaining, and reset values, plus
the corresponding project-token values when OpenAI supplies them. It never
prints the API key, authorization header, or arbitrary response headers. Use
the request ID and reset values to distinguish a temporary limit from a
project-level capacity problem.

To exercise that provider boundary intentionally, an operator may run the
following only with a disposable budget and explicit opt-in; without both the
flag and credentials it skips without a request:

```text
FREYTAG_RUN_LIVE_SMOKE=1 TMPDIR=/tmp uv run pytest tests/test_openai_live_smoke.py -q --no-cov
```

## Phase-4 candidate review and promotion

Before review, authors can run the authoring-only Phase 4 evaluation across the
entire outline inventory. It uses the same bounded compiler path as an
individual live compilation and writes an evidence report containing first-pass
and repair acceptance, request-budget exhaustion, diagnostic categories, and
the structural diffs observed during repairs:

```text
FREYTAG_ENABLE_LIVE_COMPILER=1 \
uv run storygame-blueprint-evaluate \
  --live --quality-tier minimum \
  --output data/story_blueprints/evaluations/phase4.evaluation.json
```

The command requires the explicit live opt-in and never writes a candidate,
reviewed artifact, or runtime input. It also refuses to overwrite an existing
report. Compare its summary with the embedded Phase 0 baseline and retain the
report with the authoring run.

Pass `--autopromote` to the live compiler to promote only an accepted,
non-debug candidate. The compiler revalidates it, writes an immutable
`reviewed-story-blueprint-v2` artifact bound to the candidate SHA-256, and
updates the matching genre entry in `data/compiled_stories/v2/runtime-fixtures.json`:

```text
FREYTAG_ENABLE_LIVE_COMPILER=1 \
uv run storygame-blueprint --outline-id vale_mansion_rebuild \
  --quality-tier preferred --live --autopromote
```

Autopromotion rejects an unaccepted, malformed, or debug candidate and failed
revalidation. Existing candidate and reviewed artifacts receive timestamped
filenames rather than being overwritten. The runtime fixture map is the sole
runtime link; Phase 5 remains responsible for hosted staging evaluation.

## Repeatable candidate audit

Run the read-only audit command against any candidate when additional evidence
is useful:

```text
uv run storygame-blueprint-audit \
  --candidate data/story_blueprints/candidates/vale_mansion_rebuild.candidate.json \
  --output data/story_blueprints/audits/vale_mansion_rebuild.audit.md
```

The default output is a human-readable Markdown review packet. Use
`--format json` when another tool needs the machine-readable report:

```text
uv run storygame-blueprint-audit \
  --candidate data/story_blueprints/candidates/vale_mansion_rebuild.candidate.json \
  --format json \
  --output data/story_blueprints/audits/vale_mansion_rebuild.audit.json
```

The command makes no provider requests and never modifies the candidate. It
writes a hash-bound `story-blueprint-audit-v1` report and exits zero only when
all automated checks pass:

- `compiler_validation`: contract, symbol binding, profile, causal, timeline,
  completeness, fairness, and Freytag validation;
- `terminal_roles`: every ending outcome resolves to a truth required by that
  ending;
- `knowledge_boundaries`: protected truths are absent from the opening and
  have declared release revelations;
- `route_diversity`: required revelations have the profile-defined number of
  independent opportunity kinds;
- `failure_forward`: each route has a bounded consequence or alternate route,
  and no route points to itself;
- `map_and_custody`: every evidence opportunity is held by a declared
  participant and located in the reachable map.

The report is diagnostic evidence, not a reviewed artifact and cannot be used
as runtime input. A malformed or locally rejected candidate reports the
compiler check as failed and marks dependent checks as skipped.
