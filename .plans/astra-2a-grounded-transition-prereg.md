# Preregistration: Stage 7 2A grounded-route transition screen (cooling-service archive panel)

Written 2026-10-18, before any billed run of this screen. Story commit
`a9dc5023` (adds the 2B "opens with a push" setting fact); harness commit `c1352e1a`
plus the transition-screen change that this document gates. Supersedes the
two-command screen of `.plans/astra-2a-grounded-route-prereg.md` as the adoption
measure; that file's arms, known limits and spend notes still apply where this
file does not say otherwise.

## Why the measure changed (Brandon, 2026-10-18)

Only inventions that stop the story progressing matter, and a player chasing
something in a scene is fine. A scene passes when **earned (non-timeout) scene
transitions occur in at least 80% of runs.** The old screen asked whether
`k_sl_2b_a_r1` was committed by command 2, which counts a short chase as a
failure. It does not decide adoption.

## Question

Does the grounded package leave scene 2B by an earned transition in at least 80%
of full continuations, and is it not clearly worse than the control package?

## Arms (frozen, unchanged)

- **control:** recorded 2A turn-7 prompt, package `bench/frozen/continuity-pre-2a-panel/`.
- **grounded:** the same recorded prompt plus the derived panel additions, package
  `data/stories/continuity-initiative/`.
- Same system prompt, model, temperature, recorded 2A player command, raw blind
  player (`door_ask_player.mjs`, profile `raw`). Arms interleave rep by rep.
- Fresh 2B state per row (as in the old screen). Semantic fallback stays disabled,
  as before; the hosted game has it, so this is conservative for earned rate
  (Brandon accepted this on 2026-10-18).

## Procedure per row

1. One raw 2A narration, bridge and 2B entry text form the opening screen (as before).
2. Loop: the raw player reads the whole transcript so far (screen, every command,
   every response) and issues one command; `engine.turn` runs it, with
   `clarifies=<original command>` forwarded for the answer to a clarification.
3. Stop when the scene is no longer 2B, the story completes, or the command count
   reaches **20** (the 2B timer handoff fires at turn 15, so 20 leaves margin for
   clarification turns).
4. Record for each row: `final_scene`, `ended_by` = the attempt bundle's
   `transition_cause` on the turn that left 2B (`earned`, `forced`, `timer`) or
   `none` if the row never left 2B, `transition_turn`, `commands`,
   `clarification_turns`, committed reveal ids per turn, and whether the 2B panel
   was named in any command.

## Counted measures (all deterministic; no reviewer needed)

- **earned_exit:** `ended_by == earned`. Primary measure.
- **timer_exit:** `ended_by` is `forced` or `timer`.
- **no_exit:** the row never left 2B within 20 commands.
- Report separately: commands to exit, rows where any command names the panel, and
  rows with at least one clarification.

## Sample size and caps

N = 12 per arm (24 rows), run once, no extension after results. A smoke of one row
per arm (2 rows) runs first and is read before N=12.

Worst case per row: 1 raw 2A narration + 20 turns, each possibly one retry; so at
most about 21 Cloudflare and 20 player calls per row, before recovery.
Hard request caps: smoke 40 Cloudflare / 36 player; N=12 screen 480 Cloudflare /
408 player. Cloudflare dollar ceiling at $0.0020 per request (priced high on
purpose, see the old prereg): smoke $0.08, N=12 $0.96. Player calls carry a
request cap only; Brandon to supply a price if needed. One Ringer task per smoke or
screen, one attempt, no replacement samples; a cap or quota error stops the run
and is recorded.

## Keep rule

Grounded is kept if **earned_exit >= 10/12 (83%)** in the grounded arm. This is a
screen, not a power calculation: with N=12 a true 80% rate passes about half the
time, and a true 90% rate about 89% of the time. Read a miss of 9/12 as
"borderline", not as proof of failure, and say so in the report.

The panel edits are flagged for Brandon's review, not auto-kept, if the grounded
arm's earned_exit is **3 or more rows below control**, or if grounded `no_exit`
exceeds control `no_exit` by 2 or more rows. Control is a reference for harm, not
a second adoption gate.

A screen pass is not completion: next come the focused runbook checks, payload
diff, SHA-bound staging, and the hosted blind-player 2A-2B replicates.

## Known limits (state them in the report)

- Replays a recorded 2A prompt; the hosted match call, pacing events and
  semantic fallback are not exercised. The panel THINGS line is the best-case
  assumption from the old prereg.
- A fresh 2B state is not the state a real 2A play ends in.
- The raw player is one model prompt, not a human; its stalls and persistence
  differ from real players.
- Earned vs forced is read from the runtime's own `transition_cause`; the screen
  does not judge narration quality, canon consistency or invention.

## Stop rules

Stop and report on malformed output, quota or outage, a cap error, missing
evidence, or a row that cannot record `transition_cause`. No pooling with earlier
screens. Record aborted attempts.
