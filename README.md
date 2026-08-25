# Freytag Forge

> Interactive fiction with freedom, memory, and consequences.

Freytag Forge lets you write what your character tries—not choose from a tiny
verb menu—and turns every attempt into a grounded, persistent story beat.

## Why it plays differently

- **Say it your way.** Investigate, flirt, bluff, flee, bargain—or try the move
  nobody thought to put on a menu.
- **Consequences with receipts.** Every accepted clue, promise, wound, item, and
  relationship shift becomes durable story truth.
- **Characters with boundaries.** NPC replies stay tied to the right speaker,
  current scene, and knowledge they have actually earned.
- **Voices built to hold up.** Authors shape distinct manners, rhythms, word
  choices, and physical tells—without freezing characters into canned lines.
- **Conversations with momentum.** Dramatic interactions can open, continue,
  change course, fail forward, or end cleanly instead of collapsing into one
  disposable reply.
- **Your move stays yours.** Engage, refuse, redirect, interrupt, or walk away;
  story pressure creates opportunity without turning dialogue into a menu.
- **Worlds with a pulse.** Authors can declare who is where, what can be
  examined, and which evidence is genuinely available—so future scenes have
  solid ground beneath the drama.
- **Drama that finds you.** Pressure, timed events, alternate routes, and
  failure-forward turns keep the story moving without stealing agency.
- **Secrets worth uncovering.** Protected revelations stay hidden until your
  actions actually earn them.
- **Continuity you can trust.** Save, reload, and replay without prose quietly
  rewriting the world behind your back.
- **One engine, every genre.** Mystery, fantasy, sci-fi, and relationship drama
  share the same fact-backed rules—no one-story tricks.

**Less prompt luck. More character, consequence, and playable drama.**

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
