# Preregistration: Stage 7 2A grounded-route screen (cooling-service archive panel)

Written 2026-10-18 before any further billed run. Story commit `ad8d0c76`
(revised bridge, ten `setting_facts`, 2A.3 paragraph removed); earlier panel
commit `3692b4c0`; harness `cf9960b5` plus `ad8d0c76`. Supersedes the aborted
N=12 attempt (4 of 24 rows, killed on purpose, not analysed) and the first
smoke (old design: only four CONSTRAINTS lines, no THINGS line).

## Arms (frozen)

- **control:** recorded 2A turn-7 prompt, package `bench/frozen/continuity-pre-2a-panel/`
  (equals commit `abb3fd7c`): old bridge, old 2B entry.
- **grounded:** the same recorded prompt plus the lines the current package adds,
  derived by diff (1 THINGS line for the panel, 11 CONSTRAINTS lines), package
  `data/stories/continuity-initiative/`: new route-neutral bridge.
- Same system prompt, model, temperature, recorded player command, raw blind
  player, and a real 2B continuation of at most two commands. Arms interleave
  rep by rep. Do not edit the recorded search command.

## Known limits of the design (stated up front)

- The THINGS panel line is a **best-case assumption**: it is what the runtime
  renders if the per-turn match call refers "access panel" to the panel (checked
  offline with a stubbed reply). The real selection rate is not measured here.
- The replay patches a recorded prompt, so it does not run the hosted match call,
  pacing or semantic fallback. This is a wording/material screen, not hosted
  validation.
- The bridge differs between arms by design (the old bridge is part of control).

## Spend ceilings

Hard request caps (unchanged from the astra-fixes plan): smoke 10 Cloudflare /
4 player; screen 120 Cloudflare / 48 player; raw 2 / 24.

Cloudflare dollar ceiling, from `worker/src/budget.js` prices for
`@cf/meta/llama-3.1-8b-instruct-fast` (input $0.282 and output $0.827 per
million tokens, priced high on purpose): assume at most 4,000 input tokens
(measured raw 2A prompts are about 1,800) and 1,024 output tokens (the request
`max_tokens`) per request.
Per request at most $0.00113 + $0.00085 = about $0.0020.
Smoke (10 requests): at most about $0.02. Screen (120 requests): at most about
$0.24. The Worker also enforces `DAILY_BUDGET_USD` (default $5) and refuses
unpriced models.

Player calls (`gpt-5.6-luna`, up to 4 and 48) are billed outside the Worker; their
per-token price is not in the repo, so they carry a request cap only. Brandon to
supply a dollar figure if one is needed.

## Stop rules (read every smoke narration plus appended delivery first)

Stop and report, with no replacement samples or pooling, on: malformed output,
quota/outage/cap error, missing evidence, premature disclosure, or contradictory
delivery that the **grounded arm introduces** (appended 2B delivery landing on
command 1 in both arms is the existing baseline defect and is reported, not
counted against the candidate by itself; Brandon decides whether it blocks).
Run the fixed N=12 once only after the smoke is read and Brandon says go. One
Ringer task per smoke or screen; one attempt each; record aborted attempts.

## Counted measures (per row, verdict files written by a reviewer who reads the row)

`earned_by_command_2` (exactly one eligible `k_sl_2b_a_r1` reveal; inspect the
committed delivery, not `item_facts`), `declared_panel_used`,
`invented_access_object`, `reached_archive_without_new_credential`,
`premature_disclosure`, `contradictory_delivery`, plus upstream, inherited and
downstream-new invention counted separately. A row with any unsupported access
invention counts once in the combined invention measure. Also report how often a
door/panel appears in both arms; a supported door must not hide a continuing
dead-end chase.

## Keep rule

Grounded is kept only if all hold: earned_by_command_2 >= 10/12;
reached_archive_without_new_credential >= 10/12; invented_access_object <= 2/12;
zero premature disclosures and zero contradictory deliveries; and grounded beats
the fresh control by at least 3 earned rows without more invention. The 3-row
margin is an engineering screen, not statistical significance. Do not extend N
after seeing results. A screen win is not completion: next come the focused
runbook checks, payload diff, SHA-bound staging, and three linked free-text
2A-2B replicates.
