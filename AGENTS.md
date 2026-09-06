# AGENTS.md

## Tech Stack

- Python 3.12 / FastAPI / React / Cloudflare hosted adapter
## Running Tests

- `TMPDIR=/tmp uv run pytest -q`; finish feature work with `uv run ruff check --fix . && uv run ruff format .`.
## Architecture

- Start with [the PRD](docs/PRD.md); use the focused runbook and [contributor guide](docs/contributor-guide.md) for the change.
- Facts are the sole mutable truth; shared runtime stays story-agnostic and LLM-proposal-first.
## Writing Player Input

Player input is what a person types at the game. Every test, probe, bench
script, and example must be written in that voice, because these strings are
matched against world entity names to decide what knowledge is recalled and are
handed to the narrator as the action to answer. Wrong-register inputs exercise a
distribution the real game never sees, so a defect that only appears for real
phrasing hides behind a green suite.

- **Imperative, not first person.** `Search the kitchen for signs of a
  struggle.` Never `I search the kitchen...`. The second is the player writing
  the story, which is the narrator's job.
- **An active move, never a restraint.** Strip any `do not ...`, `without
  ...`, `avoid ...` clause and keep the action that remains. Declining to do
  something is not a turn.
- **Verb plus direct object.** `Pursue the agent.`, `Park the truck.`,
  `Photograph the evidence.` Not `Brace for the pursuit.` Ordinary
  prepositions are fine (`Listen to the recording.`, `Look under the
  workstation.`); the sentence should still be a verb acting on an object.
- **No non-events.** `Wait.`, `Stand still and listen.`, `Keep watch.`,
  `Continue waiting.`, `Think back to the memory card.` are all the same
  mistake: nothing happens in the world because of them.

That last rule cannot be checked mechanically, and no lint should claim to. An
action is active when it causes a world change that would not have happened
anyway, so the *same verb* is active in one scene and passive in another:
`Listen.` is a move when something is really there to hear and commits a fact,
and a non-event when nothing is. A change that a Freytag beat or timed pacing
event would have produced regardless does not count, and narrative colour that
commits no fact is not an effect. Judge each input against the scene it runs
in; if you want the question answered at scale, measure it in `bench` by
comparing a turn against a deliberate null control, or ask the LLM judge.

## Forbidden Patterns

- No story/genre-specific runtime branches, fixed action tables, hand-edited generated artifacts, or prose as canonical truth.
- No unvalidated provider output, protected-knowledge leak, or fact change after rendering.
## Common Mistakes

- Verify CLI, environment, CI, and endpoint behavior in source/help/workflows; update the focused runbook with the change.
- Use `TMPDIR=/tmp` for pytest, never pin collection counts, and use `uv run python` rather than `python`.
- For a staging-verified change, merge the implementation PR first and poll the `main` CI workflow until its SHA-bound staging deployment succeeds before running staged E2E tests. Update the testing runbook only after those E2E results are observed. Commit that documentation as a final follow-up; do not rerun deployment/E2E solely for the documentation-only commit.
