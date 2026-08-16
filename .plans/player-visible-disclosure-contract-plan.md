# Player-visible disclosure contract and E2E quality plan

## Objective

Make newly learned story information a bounded, fact-backed state transition,
not an incidental property of LLM prose. Establish a reusable acceptance matrix
that catches opening-turn failures across every story package before staging or
production promotion.

## Problem statement

The current `read` affordance commits declared document knowledge, but a
conversation can render an NPC's knowledge without committing it to the player.
This permits dialogue to create uncommitted truth. Existing tests exercise
individual adapters and fact operations, but do not consistently assert the
player-visible, committed outcome of an opening interaction through the web
turn boundary.

## Non-goals

- Do not parse free prose after rendering to infer state.
- Do not add story- or mystery-specific runtime branches.
- Do not add unbounded provider retries or a narration fallback that fabricates
  dialogue.
- Do not require a live provider for ordinary unit or CI test runs.

## Design

### 1. Declarative disclosure data

Extend readable-document package data with a typed disclosure policy that names
the fact keys an on-scene holder may disclose when asked about that document.
Validation must require that each disclosure key is:

- declared by the readable document;
- a canonical `case_fact` in the package;
- known by the disclosing NPC; and
- not already public at the opening when it is presented as a new discovery.

The policy is package data, so the same runtime contract applies to every
genre. Migrate the mystery case-file holder to this data and add at least one
non-mystery fixture with a document/NPC disclosure path.

### 2. Structured proposal and fact commit

Add an optional typed `disclosed_knowledge` field to a conversational action
proposal. For a direct question about a readable document, the planner may
select only one policy-declared key. Deterministic policy validates speaker,
location, document access, NPC knowledge, and player novelty; it then asserts
`knows(player, key)` before rendering. The event records the committed
disclosure key.

The dialogue validator rejects a response that claims a selected fact without
the matching valid disclosure operation. It also rejects a direct
document-briefing response that selects no available disclosure when the
package marks the NPC as a briefing source. A single retry may repair the
structured proposal within the existing shared recovery budget.

### 3. Projection and continuity

Player context, narration context, save/load, `StoryState.json`, and `STORY.md`
must all derive the disclosure from committed facts. Later turns must be able
to use the fact, while an NPC lacking the fact cannot reveal it. The readable
document path and NPC briefing path must converge on the same player knowledge
fact without creating duplicate or contradictory state.

### 4. Generic behavior matrix

Create reusable test helpers that run each applicable package against this
matrix:

| Scenario | Required result |
| --- | --- |
| Opening observation | New document fact absent from narration and player knowledge. |
| Read accessible document | Exactly declared fact committed and rendered. |
| Ask authorized on-scene holder | Exactly declared fact committed and rendered in the holder's reply. |
| Ask unauthorized/uninformed NPC | No protected or document-only fact revealed or committed. |
| Ask after discovery | No duplicate commit; later context retains the fact. |
| Save/load after discovery | Knowledge and projection remain intact. |
| Short name/full name/`ask X about Y` | Same addressed-NPC and disclosure result. |
| Provider envelopes | `narration`, `result.response`, choices, and direct structured output reach the same outcome. |
| Malformed/transient response | At most two inference-reaching requests; typed fail-closed error; no state change. |

Use deterministic provider fixtures for CI. Add a narrowly scoped hosted-demo
E2E test for the complete `/api/v1/session` and `/api/v1/turn` sequence.

### 5. Staging and promotion

Extend the staging evaluator with a short opening disclosure script for every
genre/package that declares one. Its gate must fail on a 503, missing committed
knowledge, repeated-only public briefing, leaked protected knowledge, or
incorrect deployment SHA. Preserve request and trace IDs in the report.

## Implementation sequence

1. [x] Add failing engine and web E2E tests for committed NPC disclosure and no
   duplicate/leak behavior.
2. [x] Extend typed proposal contracts and generic fact policy/committer support.
3. [x] Add package schema validation and migrate package fixtures.
4. [x] Implement planner prompting, local validation, and bounded disclosure commit.
5. [x] Add matrix helper coverage across applicable genres, persistence, and
   provider-envelope paths.
6. [x] Extend staging evaluation and documentation.
7. [x] Run the complete suite with `TMPDIR=/tmp uv run pytest -q`; record coverage
   and staging fixture results.

## Completion criteria

- [x] No narration or NPC reply can introduce a selected disclosure fact before its
  validated commit.
- [x] Every declared document briefing path has a passing player-visible E2E test.
- [x] Cross-genre matrix tests cover all applicable packages.
- [x] Provider failures remain fail-closed, bounded, observable, and state-safe.
- [x] The full suite meets the 90% coverage floor and the staging gate includes the
  disclosure script.

## Verification record

- `TMPDIR=/tmp uv run pytest -q`: 717 passed, 1 skipped, 1 xfailed; 90.07% coverage.
- Deterministic staging-evaluator fixture suite: 6 passed, including the
  package-derived mystery and fantasy opening disclosure scripts.
