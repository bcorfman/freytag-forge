# Worldkeeper boundary moves

**Rule (Brandon, 2026-10-31, firm):** world-model logic (anything that reads or changes only world state) is a `World`
or `WorldSchema` method in `packages/worldkeeper` with tests there; `storygame` only adapts and calls it. Written into
`docs/contributor-guide.md` and `AGENTS.md` in PR #734 (open, not merged).

## Status (2026-10-31, stopped by Brandon mid-work)

Branch `worldkeeper-boundary-moves` (local only, not pushed, no PR). Ringer run name `worldkeeper-boundary`.

- **Audit (done):** read-only review of ten storygame modules. Reports in
  `scripts/ringer/worldkeeper-boundary/audit-reports/*.json` (move / split / stay per function).
- **Round 1 (done, `aeaf6bf2`):** 15 helpers added with tests in `packages/worldkeeper/tests/test_boundary_helpers.py`
  (`World.descendants`, `contains`, `under_contents`, `open_state`, `is_item`, `observable_items`,
  `required_observations`, `moved_since`, `current_seat`, `reachable_from_seat`, `takeable_items`,
  `fixed_visible_items`, `visible_vehicle_seats`; `WorldSchema.related_areas`, `area_ancestors`). Parity with the old
  storygame code checked on the Continuity Initiative package; see `round1-notes.md`.
- **Round 2 (done, `cabbc64f`):** item_facts, capture, observation, traversal, narration_safety, seating, taking and
  fixed_refusal call the helpers; the private tree walks are deleted. Ringer marked all three tasks FAIL only because
  `check_round2.py` restricted PATH and hid `node` from one test; with the check fixed, all three pass (1,277 focused
  tests). Reviewed by hand. One fix of mine: `focus_open_state_after` keeps its container-only contract (capture.py).
- **Round 3 (done, uncommitted until the commit below):** taking.py fallback removed, `tests/test_taking.py` rewritten on
  the real worldkeeper `World`, `World.reachable_from_seat` returns ids (seating.py maps to names). Ringer marked it FAIL
  only because `check_round3.sh` grepped `.pyc` files in `tests/__pycache__` into the pytest args ("no tests ran"); the
  grep now uses `--include="*.py"`. With the check fixed: 1,277 focused tests, Ruff check and format pass. Reviewed by hand.

## Next

1. The full pytest+cov suite once, Ruff, push, PR (merge commit, on Brandon's instruction only).
2. Not covered by the audit: `_fact_move_overrides` companion filter and `item_facts._apply_move` seat pick stay as
   client calls by design.

## Other state from this session

- Staged `@spine` and `@timed-events` PASS on `21377382` (recorded in the main plan, in PR #734).
- PR #734 (docs progressive disclosure + this rule): open, CI not yet checked.
- Dependabot alerts 23–28 dismissed (fix in `a536d9d5`); 0 open.
