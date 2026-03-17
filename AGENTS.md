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
- Deterministic systems are commit authorities, not primary turn authors. LLM outputs may propose dialogue, story actions, events, and bounded consequences; deterministic code validates and commits accepted deltas.
- Parser handling must stay limited to control-plane commands (`save`, `load`, `quit`, `help`) and proposal-failure fallback. Do not let parser fallback become the dominant authored path.
- NPC dialogue should generally be LLM-authored from deterministic context. Do not replace ordinary in-scope conversations with canned deterministic lines unless explicitly required as a validated fallback.
- High-impact or out-of-scope actions must require explicit confirmation before state mutation, then trigger deterministic replan markers so goals, NPC behavior, and consequences can adapt coherently.
- Preserve explicit typed proposal/validation boundaries. Prefer contract types and adapters for runtime turn proposals over ad-hoc dict plumbing or special-case command branches.

Dependency/testability:
- Write tests first, then write the code to match the tests (TDD), then update the docs to reflect the new/updated code once it works.
- Sustain project-wide test coverage at `>=90%` on every change; verify with `uv run pytest -q` and do not merge changes that drop coverage below this threshold.
- Accept dependencies via constructors; avoid hidden instantiation inside methods.
- Avoid circular dependencies.
- Prefer composition over inheritance for dependencies.
