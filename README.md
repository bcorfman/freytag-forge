# Freytag Forge

> Interactive fiction with freedom, memory, and consequences.

Freytag Forge lets you write what your character tries—not choose from a tiny
verb menu—and turns each attempt into a grounded, persistent story beat.

## Why it’s fun

- **Write anything:** investigate, bargain, lie, help, run, refuse—or invent a
  move no menu anticipated.
- **NPCs with boundaries:** question present characters; they answer from their
  own role, relationships, scene, and earned knowledge.
- **Consequences with a clock:** goals, clues, pressure, timed events, and
  failure-forward choices keep the story moving.
- **Real objects and clues:** inspect or take declared items; readable
  documents reveal only what the right speaker can know.
- **Clarification over guesswork:** ambiguous actions stay open for a clearer
  attempt instead of silently taking the wrong branch.
- **Fail-forward stories:** a bad approach changes the situation without
  needlessly ending the story.
- **Progressive scenes:** first arrivals earn texture; revisits stay brisk;
  `LOOK` brings the full view back.
- **Every genre, one engine:** mystery, fantasy, sci-fi, and relationship drama
  share the same fact-backed rules.
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
