Read before coding:
- Refer to `/docs` for any context or patterns before implementation.

Design priorities (in order): dev experience, simplicity, fit with underlying APIs, API quality, testability, best practices.

Structure/complexity:
- Keep modules around ~500 lines and functions around ~20 cyclomatic complexity.
- Split modules/functions intelligently to avoid high complexity or large files.
- If splitting would reduce clarity, ask for a decision before doing it.

Hard rules:
- Avoid dataclasses unless there is a clear, documented benefit.
- Avoid runtime type/attribute checks (hasattr/getattr/isinstance/EAFP-with-pass).
- No silent EAFP; `except AttributeError: pass` is forbidden.
- Use `uv run python` (never plain `python`).
- Define and use explicit Protocols/adapters for interfaces; validate at boundaries instead of ad-hoc attribute probes.
- Ordinary gameplay turns must remain LLM-proposal-first. Do not introduce parser-first or command-table-first routing for normal story turns.
- Deterministic systems are commit authorities for NPC initial locations, NPC stable traits, timed story events, player characteristics, item locations/characteristics, map topology/room characteristics, story goals, puzzles, clues, and world-state mutations through the fact store. LLM outputs may propose dialogue, action framing, and bounded consequences around those facts; deterministic code validates and commits accepted deltas.
- Parser handling must stay limited to control-plane commands (`save`, `load`, `quit`, `help`) and proposal-failure fallback. Do not let parser fallback become the dominant authored path.
- NPC dialogue should generally be LLM-authored from deterministic context. Do not replace ordinary in-scope conversations with canned deterministic lines unless explicitly required as a validated fallback.
- Opening prose, turn narration, NPC dialogue, and in-scope action framing should be LLM-authored from deterministic facts. Do not let narration invent parallel state that is not representable in the fact store.
- Fallback dialogue must not auto-target the nearest NPC for unrelated player actions. If the player did not clearly address someone, keep the reply narrator-scoped or ask for clarification.
- Preserve protagonist/assistant identity continuity in narrator context and output editing. Do not let room-entry or reviewed prose invent replacement names for already-canonical characters.
- Mystery bootstrap/opening should preserve a canonical male detective identity and name consistently across opening prose, turn narration, and reviewed output. Use `Detective Elias Wren` unless an explicitly approved contract changes that canon everywhere.
- Preserve role and clue continuity across bootstrap text, opening text, and turn-based text. Do not let the same character be both assistant and suspect at once without an explicit in-story change, and do not let the same clue be both held by a character and simultaneously placed elsewhere in the scene.
- Opening/bootstrap planning should prefer a single cached story-bootstrap agent call over multiple narrow planning calls. Do not reintroduce seeded setup/objective/public-setting text as the authoritative runtime story plan.
- The player must be allowed to attempt any gameplay action or story move. Do not treat surprising, disruptive, or goal-breaking prompts as forbidden at the gameplay layer.
- High-impact actions must require explicit confirmation before state mutation only when they would break the current story goals beyond repair.
- When confirmation is required, interrupt before generating the official LLM-authored response to the original prompt. On `PROCEED`, commit disruption facts, replan if needed, then generate the official response to that same player prompt.
- If the player prompt does not break current goals beyond repair, the engine must adapt the fact database and story state to the prompt rather than refusing it as out-of-scope.
- Preserve explicit typed proposal/validation boundaries. Prefer contract types and adapters for runtime turn proposals over ad-hoc dict plumbing or special-case command branches.
- Goals, clues, puzzle state, NPC locations, NPC relationships, discovered leads, event flags, reveal state, and item possession/location must remain assertable/retractable fact-store data, and narration must read from those facts rather than carrying its own competing truth.
- Deterministic item validation should resolve unique visible shorthand naturally (for example `take key` -> `route_key` when unambiguous) instead of forcing the player to restate full internal item labels.
- Treat `storygame.web` and `storygame.web_demo` as separate deployment surfaces with different narrator/backend assumptions. Shared helpers are allowed only below that adapter boundary.
- Do not centralize bootstrap/opening generation in a way that makes hosted demo depend on local OpenAI story-agent credentials. Hosted demo must remain playable without `OPENAI_API_KEY` when configured to use the Cloudflare Worker / Llama path.
- When refactoring web surfaces, preserve story/output parity where possible, but do not erase legitimate deployment differences such as hosted fail-closed behavior, Cloudflare-backed narration, or credential boundaries.
- Treat sub-10-second total story-agent latency per turn as an engineering goal. Prefer fewer LLM round-trips, cached bootstrap outputs, and shared contracts over multi-call orchestration when behavior can be preserved.
- Opening/story editors and judge-critic passes must make the full opening cohesive before display and should treat role contradictions, duplicated clue locations, and impossible scene facts as blocking coherence failures, not minor polish issues.

Dependency/testability:
- Write tests first, then write the code to match the tests (TDD), then update the docs to reflect the new/updated code once it works.
- Sustain project-wide test coverage at `>=90%` on every change; verify with `uv run pytest -q` and do not merge changes that drop coverage below this threshold.
- Accept dependencies via constructors; avoid hidden instantiation inside methods.
- Avoid circular dependencies.
- Prefer composition over inheritance for dependencies.
