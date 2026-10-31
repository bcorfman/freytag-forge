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
- When a verification procedure changes, edit its existing runbook entry in
  place in the same change. Never append dated results, test counts, or phase
  logs to the runbook; record outcomes in the plan, PR, or commit message.
  Keep product/runtime contracts in the PRD and link to focused documents
  instead of duplicating them.
- Preserve historical release records as records, not current operating
  guidance.

## Detail files

- [Runtime and authoring boundaries](contributor-guide/runtime-and-authoring-boundaries.md): read this when changing the story engine, package declarations, world-model logic, generated artifacts, or hosted adapter.
- [Gameplay, model, and interaction safety](contributor-guide/gameplay-model-and-interaction-safety.md): read this when changing player input, turn inference, provider responses, narration, dialogue, opening checks, or guard retries.
- [Design and verification](contributor-guide/design-and-verification.md): read this when designing modules or dependencies, changing complexity or coverage expectations, or running tests and formatting.
