# AGENTS.md

## Tech Stack

- Use Python 3.12, FastAPI, React, and the Cloudflare hosted adapter.

## Running Tests

- Follow the [testing runbook](docs/testing-runbook.md) for commands and verification procedures.

## Tooling

- Use Serena for code discovery and symbol-level edits; use shell tools for tests, git, builds, and package managers.

## Architecture

- Start with [the PRD](docs/PRD.md); use the focused runbook and [contributor guide](docs/contributor-guide.md) for the change.
- Facts are the sole mutable truth; shared runtime stays story-agnostic and LLM-proposal-first.
- Before declaring or placing any story thing, place or NPC, or writing any narrator, match-call or judge prompt line about places, read [the world-model grounding guide](docs/world-model-grounding.md).

## Player Input

- Write every player action in tests, probes, bench scripts, and examples to the [player-input guide](docs/player-input-guide.md).

## Narrator Rules

- Write and update narrator instructions according to the [narrator-writing guide](docs/narrator-writing-guide.md).

## Fixing a Scene

- Diagnose scene misses with the proven workflow in [the scene-fixing guide](docs/scene-fixing-guide.md).

## Design Boundaries

- Follow the [contributor guide](docs/contributor-guide.md) for runtime boundaries, safety rules, and implementation practices.

## Plans and Releases

- Keep the active plan current and follow the [agent workflow guide](docs/agent-workflow-guide.md) and [production promotion guide](docs/railway-production-promotion.md) for staging requirements.
