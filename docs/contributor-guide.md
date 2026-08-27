# Contributor guide

This guide keeps repository-wide engineering rules concise. Start with the
[PRD](PRD.md), then use the focused documentation for the boundary being
changed: [Markdown story authoring](markdown-story-authoring.md),
[Cloudflare narration](cloudflare-narration-worker.md), and the
[test-suite guide](test-suite-performance-guide.md), and the
[testing runbook](testing-runbook.md).

## Before changing code or operations

- Treat documentation as a map, not executable authority. Before changing a
  CLI, environment variable, test/CI behavior, endpoint, or deployment flow,
  verify it in source, command help, configuration, or workflow YAML.
- Update the focused runbook in the same change. Keep product/runtime contracts
  in the PRD and link to focused documents instead of duplicating them.
- Preserve historical release records as records, not current operating
  guidance.

## Runtime and authoring boundaries

- Build one story-agnostic engine for every Markdown package. Story, character,
  premise, and genre behavior belongs only in validated package data.
- Facts are the sole canonical mutable runtime state. Packages, prose, saves,
  artifacts, traces, and transcripts are immutable inputs or integrity-checked
  projections; never treat them as competing mutation authorities.
- Put opening setup, public presentation, protected knowledge, relationships,
  location, custody, pacing, and scene purpose in validated package declarations.
  Correct authoring sources, never generated projections.
- Keep the hosted adapter as a thin boundary when it is rebuilt. Share code
  only below that boundary and preserve fail-closed behavior.

## Gameplay, model, and interaction safety

- Keep ordinary play LLM-proposal-first. Only `save`, `load`, `quit`, and
  `help` are parser control commands; normalize deterministic affordances via
  the shared proposal/commit contract.
- Let players attempt story moves freely. Validate bounded consequences,
  clarify ambiguity, and reserve confirmation for irreparable goal breaks; do
  not replace interpretation with a fixed command table.
- Validate all accepted state deltas before rendering. Narration, dialogue, and
  action segments cannot create uncommitted truth or leak observer- or
  speaker-protected knowledge.
- Treat provider responses as untrusted JSON-boundary input. Use an explicit
  typed structured-output adapter; normalize supported envelopes; parse and
  validate locally before commit. Provider JSON-object mode is syntax help, not
  semantic validation.
- A normal turn makes at most one inference request plus one shared recovery
  request for JSON-mode fallback, malformed output, or transient failure.
  Exhaustion is a typed fail-closed error, never fabricated success. Target
  under ten seconds on the normal path.
- Generate NPC dialogue only from the addressed NPC's permitted current
  context. Reject parroting, wrong speakers, off-scene or role violations, and
  unavailable-model fallbacks rather than fabricating a response.

## Design and verification

- Use typed contracts, explicit Protocols/adapters, and constructor-injected
  dependencies. Validate at boundaries; avoid attribute probes, hidden
  instantiation, circular dependencies, and silent exception handling.
- Keep modules near 500 lines and functions near 20 cyclomatic complexity;
  split only when clarity improves.
- Write tests first, add cross-genre regression coverage, maintain at least 90%
  project coverage, and keep collection totals informational rather than gates.
- Run tests with `TMPDIR=/tmp` in WSL, use `uv run python`, and finish every
  feature change with Ruff autofix and formatting before rerunning affected
  verification.
