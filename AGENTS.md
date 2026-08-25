# Freytag Forge contributor rules

- Read `/docs` before implementation. Start with `docs/PRD.md`, then use the
  focused authoring, test, transport, or deployment runbook for the task. The
  contributor rules in this file are the authoritative migration and
  architecture guardrails.
- Treat documentation as a concise map, not an executable authority. Before
  changing a CLI, environment variable, test/CI behavior, hosted endpoint, or
  deployment flow, verify its current behavior in command help, configuration,
  source, or workflow YAML; update the focused runbook in the same change.
- Build one story-agnostic interactive-fiction engine. Every engine behavior, rule, contract, validator, and test added for one outline or genre must generalize to every outline in `data/story_outlines.yaml`; do not add mystery- or story-specific runtime branches unless they are declarative, validated story-package data.
- Preserve the distinct authoring, runtime, and artifact boundaries: facts are the sole canonical mutable runtime truth; packages and prose are inputs or projections, never competing authorities.
- Keep ordinary gameplay LLM-proposal-first. Restrict parser handling to control-plane commands (`save`, `load`, `quit`, `help`); normalize deterministic affordances such as direction, inventory, and unambiguous visible-item aliases through the shared proposal/commit contract.
- Let players attempt any story move. Validate and commit bounded consequences, clarify ambiguity when needed, and require confirmation only for irreparable goal breaks; never replace story interpretation with a fixed command table.
- Let LLMs propose intent, framing, dialogue, and bounded effects. Deterministic policy validates and commits every accepted state delta before rendering; narration must not create uncommitted truth or leak observer- or speaker-protected knowledge.
- Treat every model/provider response as untrusted at the JSON boundary. Select structured output through an explicit typed adapter option, never by inspecting prompt text. Normalize supported envelopes (plain text, fenced JSON, nested `result.response`, `choices[].message.content`, and structured objects) before parsing; never pass a language-specific object representation such as Python `repr` to a JSON parser. Request provider JSON-object mode for syntax, not a deeply nested provider-side schema; local typed contract validation remains authoritative for semantics. If a provider rejects JSON mode, retry once without that option while keeping the JSON-only instruction. That fallback, malformed-output repair, and transient-error retries share one recovery budget: an ordinary player turn makes at most two provider requests that may reach inference. Parse locally before any state commit. Keep this recovery bounded and test empty, fenced, structured, malformed, schema-rejected, and retry-budget-exhausted responses end to end. Surface exhausted provider failures as typed fail-closed errors, never as a successful turn with unchanged or fabricated state.
- Keep NPC dialogue LLM-authored from the addressed NPC's permitted context. Reject prompt parroting, wrong-speaker, off-scene, role-violating, or unavailable-model fallbacks rather than fabricating dialogue or narration.
- Model world state, discovery, knowledge, relationships, tasks, NPC roles, goals, clues, items, events, and dramatic state as assertable/retractable facts. Validate canonical changes through typed contracts and explicit policy families.
- Preserve canonical identity, role, location, custody, and clue continuity within each story package. Do not encode a fixed protagonist, gender, genre, or mystery premise in shared runtime behavior.
- Put story-specific opening setup in validated external story-package data: character relationships, traits, prior arrival/order, public briefings, protected knowledge, item custody, and scene purpose must be declared as facts or package inputs, not embedded as names, prose, or conditional behavior in shared engine code. Shared code may only realize, validate, and render those declarations through generic contracts.
- When a story's compiled output is inadequate, change the authored outline or the story compiler/contracts that generate it; do not hand-edit generated candidate, reviewed, compiled-story, or other artifact projections. If the outline itself lacks the needed material, enrich the outline first. This rule applies to every story and genre.
- Make accepted opening/bootstrap corrections commit back to facts before display. Validate openings for contradictions across roles, locations, custody, and scene facts; keep critique/editor passes at authoring, evaluation, or bounded recovery boundaries, not on the ordinary-turn fast path.
- Prefer one LLM call on the normal turn path and at most one bounded recovery call. Target under ten seconds total story-agent latency per normal turn.
- Keep `storygame.web_demo` as the hosted deployment adapter. Share code only below that boundary and preserve hosted fail-closed behavior and its independent credential/backend requirements.
- Treat `StoryState.json`, `STORY.md`, traces, and transcripts as integrity-checked, orchestrator-written projections of facts and accepted decisions, not mutation authorities.
- Use explicit Protocols/adapters and constructor-injected dependencies. Validate at boundaries; avoid runtime type/attribute probes, hidden instantiation, circular dependencies, silent exception handling, and unnecessary dataclasses.
- Keep modules near 500 lines and functions near 20 cyclomatic complexity. Split only when it improves clarity; ask before a split that would make the design less clear.
- Follow this priority order: developer experience, simplicity, fit with underlying APIs, API quality, testability, best practices.
- Write tests first, implement to the tests, then update documentation. Add varied cross-genre regression coverage for generalized behavior.
- Maintain project-wide coverage of at least 90%; verify with `uv run pytest -q`. Use `uv run python`, never plain `python`.
- As the final implementation stage for every feature change, run Ruff in autofix mode: `uv run ruff check --fix . && uv run ruff format .`. Do this after tests and documentation updates, then rerun any focused verification affected by the fixes.
- Do not pin CI, benchmark, documentation, or local pytest commands to a fixed
  collected-test count. The collection guard must enforce test quality through
  tiers and duplicate detection, while collection totals remain informational.
- Keep documentation current and non-duplicative: put product/runtime contracts
  in `docs/PRD.md`; keep authoring, Cloudflare, test, staging, and promotion
  details in their focused documents; link rather than restating them. Preserve
  historical release records as records, not current operating guidance.
- In this WSL environment, pytest's temporary capture files can be created under
  the Windows-mounted `TMPDIR` and cause collection/capture-cleanup failures.
  Always use `TMPDIR=/tmp` when running pytest, for example:
  `TMPDIR=/tmp uv run pytest tests/test_event_selection.py -q --no-cov`.
