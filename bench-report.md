# Phase 7 live benchmark

## Commands run

1. `TMPDIR=/tmp .venv/bin/python -m bench run --variation bench/variations/authored-handoff-phase1.json --scene 1A --replicates 4 --script candidate-selection-repro --out bench/results/phase7-live-1a --confirm` — ran once; exited 2.
2. Scene 1B command was not run because command 1 failed, as required by the hard rules.

## Scene 1A result

- Replicate 1: completed; 5 narration turns. `k_sl_1a_b_r2` appeared on player input “Recover the damaged recording and listen to it.” Other turns had no handoff. Failure reason: none.
- Replicate 2: did not complete; 1 narration turn. No authored handoff appeared. Failure reason: `narration_known_term_leak: narration mentions unavailable knowledge 'memory card'`
- Replicate 3: did not complete; 1 narration turn. No authored handoff appeared. Failure reason: `narration_known_term_leak: narration mentions unavailable knowledge 'memory card'`
- Replicate 4: completed; 5 narration turns. `k_sl_1a_b_r2` appeared on player input “Recover the damaged recording and listen to it.” Other turns had no handoff. Failure reason: none.

## Scene 1B result

Not run because the first billed command failed.

## Failures observed

`narration_known_term_leak: narration mentions unavailable knowledge 'memory card'`

## Assessment

Among the handoffs that fired, each corresponded to the matching “Recover the damaged recording and listen to it” action. No turn composed a handoff for an action that did not earn it in the produced records. This is not a complete Phase 7 assessment because Scene 1B was not run and two Scene 1A replicates failed.
