# Preregistration: Stage 7 Scene 3C relay access and open route (DRAFT, not approved)

Written 2026-10-22 before any billed run. Brandon has not approved this document or its caps. Nothing billed runs until he does.
Source: `.plans/chatgpt-3c-option3-route-plan.md` section 3 (branch `3c-relay-access`).

## Change under test
Shipped, not an arm: `resolution_escape` delivery now says Brandon's voice comes through the emergency speakers, falls silent, and
Kristin's barrier holds the way from the maintenance network to the executive office open for now. New fixed things
`emergency_speakers` (parent facility) and `watertight_barrier` (maintenance network), placed in 3C only.

## Free checks (done or required before any billed call)
1. Focused 3C tests, full suite and ruff green on the branch (see plan section 3).
2. Both things resolve in scene 3C and nowhere else; no earlier-scene narration trips their scoped aliases.

## Live check (one Ringer task, no retries, no replacement rows)
Labelled synthetic post-C start, raw blind player, semantic fallback ON, from the command that leads to the escape. Smoke 1 row
(80 Cloudflare / 40 player), then n=6 (about 6x those caps) only if the smoke harness is clean. Stop and ask Brandon on any
harness problem.

## Read by hand, every row, in full
- After the escape text: does the player's next reply keep Kristin consistent with her tracked place (pumps, maintenance network,
  surface, or chamber), with no claim that she cannot hear Brandon?
- Does any reply place a person or thing at `emergency_speakers` or `watertight_barrier` as a container, or move them?
- Does a "go to the broadcast chamber" command after the escape succeed without a refusal, and does a reply claim the route is closed?
- Do the reports and families cues still fire only on the player's action?

## Bar
No false reveals, no new grounding failures (item_facts_unplaced, wrong match-call resolutions), and the chamber return is not
refused. Report counts and quote every failing turn.

## Not covered
Whole-game quality, fresh-entry effect, hosted deadline telemetry.
