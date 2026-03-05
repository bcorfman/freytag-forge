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

Dependency/testability:
- Write tests first, then write the code to match the tests (TDD), then update the docs to reflect the new/updated code once it works.
- Accept dependencies via constructors; avoid hidden instantiation inside methods.
- Avoid circular dependencies.
- Prefer composition over inheritance for dependencies.