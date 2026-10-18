# Preregistration: Stage 7 merged-state transition screen

Written 2026-10-18, before any billed run of this screen. Brandon asked for a local
screen of the merged state before merging PR 670. Harness: new experiment `merged` in
`scripts/ringer/stage7/door_probe.py`, built on the `details` experiment
(`.plans/astra-2b-details-prereg.md`) and the `transition` experiment
(`.plans/astra-2a-grounded-transition-prereg.md`), which still govern the player, the
20-command cap, the timer, clarification forwarding, the disabled semantic fallback and
the measures.

## Question

Does the state PR 670 would ship (2A cooling-service archive panel, 2B.1 Details
subtraction, main's explicit 2B entry text from #666, plus the narration-only prompt
rule) leave 2B by an earned transition in at least 9 of 12 full continuations, and how
does it compare with the pre-details package?

## Arms (frozen)

- **baseline:** `bench/frozen/continuity-pre-details/` (HEAD `1c08389d` package: old 2B
  entry text, old Details). Same arm and variation file as the details screen.
- **details (= merged state):** the working-tree package `data/stories/continuity-initiative`
  at the PR 670 merge commit, via `bench/variations/stage7-door-grounded.json`. In this
  experiment the arm named `details` means the merged state, not only the Details edit.
- Both arms use the SAME recorded 2A turn-7 prompt, the same raw player and fresh 2B
  state. The 2B entry text, 2B Details and knowledge.yaml differ between arms by
  construction, so the 2A screen the player reads ends in a different 2B entry text in
  each arm. The harness records the package file delta and the bridge text of both arms
  and does NOT assert that they are equal. It still asserts identical 2A prompt hashes.
- Because the narration-only system rule is in the shipped provider code, BOTH arms
  carry it (the provider code is shared); this screen does not isolate that rule.

## Sample, caps and spend

N = 12 per arm (24 rows), once, no extension. Caps as the transition screen: 480
Cloudflare, 408 player requests (that screen used 319 and 297; the details screen
290 and 285). Cloudflare ceiling about $0.96 at $0.0020 per request. A 3-call-class
smoke (n=1, 2 rows, caps 40 and 36) runs first because the harness code changed.

## Counted measures (deterministic)

`earned_exit`, `timer_exit`, `no_exit` per arm from the runtime's `transition_cause`;
`segments_dropped_by_turn`. Explanatory: first-reveal turn, first-command target,
hardware-chase length, rows with a clarification.

## Keep rule

The merged state passes at **earned_exit >= 9/12** (Brandon, 2026-10-18). Also report
`merged - baseline` earned exits; a gap under 3 rows is "not distinguishable at this n".
With N=12 a true 75% rate clears 9/12 about 65% of the time, so a miss is not proof of
failure. Do not extend N after seeing results.

## Known limits

Replayed 2A, fresh 2B state, semantic fallback disabled (the hosted game enables it),
one raw-player prompt, one story. The arm contrast bundles several edits (panel carried
in both, Details subtraction, new entry text), so a difference cannot be credited to one
edit. The earlier transition and details results used the old entry text and are not
pooled with this one.

## Stop rules

Stop and report on malformed output, quota or outage, a cap error, a row that cannot
record `transition_cause`, or a dry run whose 2A prompt hashes differ across arms.
Record aborted attempts; no pooling with earlier screens.
