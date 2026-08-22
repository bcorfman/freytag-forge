# Freytag Forge

> Interactive fiction with freedom, memory, and consequences.

## Write anything. Keep the story true.

Freytag Forge is a story simulation where you can investigate, bargain, lie,
help, run, refuse, or change the plan completely. Say what your character
tries in ordinary language. The story responds—and remembers what happened.

No tiny menu of approved verbs. No hand-waving away impossible consequences.
Just a living story that meets you where you are.

## What you can do

- Play in natural language. Attempt any move that makes sense for the scene.
- Explore mystery, fantasy, sci-fi, relationship drama, and new worlds built
  from the same flexible foundation.
- Talk to characters who have their own knowledge, motives, relationships, and
  limits.
- Discover information at the right moment, through the people and objects
  that can actually reveal it.
- Make choices that stick. The world remembers movement, discoveries,
  relationships, setbacks, and turning points.
- Follow different paths to an ending. A failed approach can change the story
  without ending it prematurely.
- Build and review new stories before they become playable.
- Fix broken story connections without losing the good work around them.
- Check story logic before it reaches players, with clear guidance when a
  connection points at the wrong thing.
- Shape stories around causes, discoveries, alternate approaches, and endings
  that can actually be reached.

**Less prompt luck. More playable story.**

## Play online

Freytag Forge is delivered as a hosted web experience. [Open the live
story](https://bcorfman.github.io/freytag-forge/) and write what your character
tries; everything else belongs to the story.

## Built for stories that hold together

Freytag Forge keeps the freedom of open-ended play while protecting the things
that make a story satisfying:

- Characters do not know what they have not learned.
- Important discoveries arrive through believable routes.
- Choices create lasting consequences.
- The world does not quietly rewrite what already happened.
- New genres and stories come from authored content, not special cases.

## Create the next world

Stories can be drafted, checked, and reviewed before they reach players. That
means authors can experiment boldly while players get worlds that are coherent,
surprising, and worth revisiting.

## Requirements

To play, you only need a web browser. The hosted experience provides the web
app, story service, and model access; players do not need Python, uv, or an API
key.

Python 3.12+ and [uv](https://docs.astral.sh/uv/) are contributor requirements
for the offline story compiler and project tests. Running the live compiler
also requires `OPENAI_API_KEY` and explicit compiler opt-in. Those credentials
are never needed for hosted play.

## For contributors

| Command | Description |
| --- | --- |
| `uv sync` | Install dependencies. |
| `TMPDIR=/tmp uv run pytest -q` | Run the test suite. |
| `uv run ruff check .` | Check the code. |
| `uv run ruff format .` | Format the code. |
