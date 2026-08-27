# AGENTS.md

## Tech Stack

- Python 3.12 / FastAPI / React / Cloudflare hosted adapter
## Running Tests

- `TMPDIR=/tmp uv run pytest -q`; finish feature work with `uv run ruff check --fix . && uv run ruff format .`.
## Architecture

- Start with [the PRD](docs/PRD.md); use the focused runbook and [contributor guide](docs/contributor-guide.md) for the change.
- Facts are the sole mutable truth; shared runtime stays story-agnostic and LLM-proposal-first.
## Forbidden Patterns

- No story/genre-specific runtime branches, fixed action tables, hand-edited generated artifacts, or prose as canonical truth.
- No unvalidated provider output, protected-knowledge leak, or fact change after rendering.
## Common Mistakes

- Verify CLI, environment, CI, and endpoint behavior in source/help/workflows; update the focused runbook with the change.
- Use `TMPDIR=/tmp` for pytest, never pin collection counts, and use `uv run python` rather than `python`.
- For a staging-verified change, merge the implementation PR first and poll the `main` CI workflow until its SHA-bound staging deployment succeeds before running staged E2E tests. Update the testing runbook only after those E2E results are observed. Commit that documentation as a final follow-up; do not rerun deployment/E2E solely for the documentation-only commit.
