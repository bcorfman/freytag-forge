# AGENTS.md

## Tech Stack

- Python 3.12 / FastAPI / React / Cloudflare hosted adapter
## Running Tests

- `TMPDIR=/tmp uv run pytest -q`; finish feature work with `uv run ruff check --fix . && uv run ruff format .`.
- Ringer kills a task's check after 60 s by default, and manifest `timeout_s` covers only the worker. The full suite takes about 3 minutes, so any Ringer check that runs it (or a replay or build) needs a raised limit: put `"check_timeout_s": 900` on the task, or set `RINGER_CHECK_TIMEOUT_S=900` for a whole run. Time the check once against the unmodified build and set the limit well above that. Both settings arrived with `~/dev/ringer` commit 6b3f85e, which is merged locally but not upstream, so on any other machine verify `check_timeout_for` exists in `ringer.py` before relying on them.
## Tooling

- Prefer Serena MCP tools over `grep`/`sed`/`cat` for anything code-shaped:
  `find_symbol`, `get_symbols_overview`, `find_declaration` to locate
  functions/classes; `find_referencing_symbols`, `find_implementations` to
  find call sites; `search_for_pattern` for a textual sweep;
  `replace_symbol_body`, `insert_before_symbol`, `insert_after_symbol`,
  `rename_symbol` to edit a whole symbol. Shell tools remain right for tests,
  git, builds, and package managers — things Serena doesn't cover.

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
- Name the player's own things in the first person: `my laptop`, `my pocket`,
  never `your laptop`. Use a plain article when ownership need not be said:
  `Go out to the truck.`
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

## Writing Narrator Rules

The narrator is a small, non-reasoning Llama-class model. Every string that
reaches it as an instruction — `_turn_rules` entries, the system prompt, the
opening, and any retry hint — must be written at an 8th-grade reading level,
or it will not reliably hold.

- **Short, common words.** `thing`/`object`, not `entity`. `say who owns it`,
  not `attribute ownership`. `the story says`, not `the authored material
  states`.
- **Short sentences, one idea each.** Never join two demands with `and`; the
  model reliably obeys the first half and drops the second.
- **No project jargon.** `authored`, `grounding`, `segment`, `candidate`,
  `convey`, `durable evidence`, `container contents` are our vocabulary, not
  the model's. Where a technical term is unavoidable because it names a JSON
  field, keep the surrounding sentence plain.
- **Name the thing, don't describe the category.** Hand the model the
  concrete noun it must use, not a description of a class of situation.

Apply any change to narrator instructions to *every* path that narrates, not
just the turn path: `_turn_rules`, `opening()` (builds its own separate rule
list — easiest to forget), `_system_prompt`, `_section_user_prompt`,
`_scene_setting`, and `_recover_malformed_response`. Where two paths need the
same rule, build it in one helper and call it from both.

## Forbidden Patterns

- No story/genre-specific runtime branches, fixed action tables, hand-edited generated artifacts, or prose as canonical truth.
- No unvalidated provider output, protected-knowledge leak, or fact change after rendering.
## Common Mistakes

- Verify CLI, environment, CI, and endpoint behavior in source/help/workflows. When a verification procedure changes, edit its existing entry in `docs/testing-runbook.md` in place; add an entry only for a new verification boundary.
- Never append results to the runbook: no dated observations, test counts, coverage figures, phase evidence, or diagnosis narratives. Record outcomes in the plan, PR, or commit message. The runbook must stay short enough to read whole.
- Use `TMPDIR=/tmp` for pytest, never pin collection counts, and use `uv run python` rather than `python`.
- For a staging-verified change, merge the implementation PR first and poll the `main` CI workflow until its SHA-bound staging deployment succeeds before running staged E2E tests. Record the observed E2E outcome in the plan or PR; if the procedure itself changed, update its runbook entry as a final documentation-only commit, and do not rerun deployment/E2E for that commit.
