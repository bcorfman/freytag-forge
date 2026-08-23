# Freytag Forge

> Interactive fiction with freedom, memory, and consequences.

Freytag Forge lets you write what your character tries—not choose from a tiny
verb menu—and turns each attempt into a grounded, persistent story beat.

## The feature list

- **Freeform play:** investigate, bargain, lie, help, run, refuse, or invent
  your own move.
- **NPCs with boundaries:** question present characters; they answer from their
  own role, relationships, scene, and earned knowledge.
- **Consequences that stick:** movement, inventory, discoveries, goals,
  relationships, and setbacks survive the next turn.
- **Real objects and clues:** inspect or take declared items; readable
  documents reveal only what the right speaker can know.
- **Clarification over guesswork:** ambiguous actions stay open for a clearer
  attempt instead of silently taking the wrong branch.
- **Fail-forward stories:** a bad approach changes the situation without
  needlessly ending the story.
- **Progressive scenes:** first arrivals earn texture; revisits stay brisk;
  `LOOK` brings the full view back.
- **Genre-agnostic foundations:** mystery, fantasy, sci-fi, relationship drama,
  and future worlds use the same engine.
- **Authoring with guardrails:** compile, review, audit, and test stories before
  they reach players.
- **Spoiler-safe continuity:** facts—not prose, prompts, packages, or saves—
  decide what becomes true.

**Less prompt luck. More playable story.**

## Play online

[Open the live story](https://bcorfman.github.io/freytag-forge/) and write what
your character tries.

## For contributors

Python 3.12+ and [uv](https://docs.astral.sh/uv/) are required for the offline
compiler and test suite. Hosted play needs only a browser.

| Command | Description |
| --- | --- |
| `uv sync` | Install dependencies. |
| `TMPDIR=/tmp uv run pytest -q` | Run the full suite. |
| `uv run ruff check .` | Check the code. |
| `uv run ruff format .` | Format the code. |
