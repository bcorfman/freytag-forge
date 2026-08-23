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
- Test a whole library of stories for coherence before anyone promotes them.
- Fix broken story connections without losing the good work around them.
- Check story logic before it reaches players, with clear guidance when a
  connection points at the wrong thing.
- Catch broken story connections in named categories, then protect unrelated
  authored work when a repair is needed.
- Shape stories around causes, discoveries, alternate approaches, and endings
  that can actually be reached.
- Start every new story already oriented: who you are, why you arrived, who is
  with you, what is public, and what you can try next.
- Meet opening contacts as real continuity anchors, with declared roles,
  relationships, knowledge, locations, and anything they are carrying.

**Less prompt luck. More playable story.**

## Every clue has a home

Phase 2 gives the world a memory you can trust. Items have real custody. Your
inventory is never a prose guess. Clues become discoveries only when you earn
them, and readable documents disclose only what the right person can actually
know.

- Take the case file, find the ledger page, and carry the consequences forward.
- Ask for a document disclosure and get a grounded fact—not a lucky hallucination.
- Move, save, reload, and keep the same evidence, goals, relationships, and
  knowledge boundaries.

The result: a story that remembers not just what was said, but what became
true.

## Drop into the story, not a loading screen

Phase 1 makes the first moment count. The hosted experience now serves a
spoiler-safe opening scene directly from the reviewed story package—no fake
automatic `look`, no wasted turn, no mystery about what to do next. Every
genre gets the same crisp launch: a grounded arrival, a public briefing, a
present cast, and meaningful first moves.

## The world remembers what you’ve already seen

Freytag Forge is being sharpened around the details that make interactive
fiction feel alive:

- First arrival earns the full scene. Coming back keeps the pace moving with a
  concise update; type `LOOK` when you want the complete view again.
- Rooms and items can be rich, visual, and useful without repeating the same
  paragraph every time you cross a doorway.
- NPCs are people in the scene—not wallpaper. They have a place, a point of
  view, knowledge they can share, and reactions that change when you keep
  pressing the same question.
- The story moves through people and places. Ask sharper questions, earn trust,
  catch contradictions, and explore with intent; objects and puzzles can enrich
  the journey, but the game is not a scavenger hunt or a lock-and-key checklist.
- Every discovery and relationship turn is grounded in the story’s facts, so
  the prose can surprise you without quietly rewriting the world.

The [Phase 0 parity ledger](.plans/v1-parity-ledger.yaml) captures these
capabilities as the V2 target: more texture, more continuity, less repetition.

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
