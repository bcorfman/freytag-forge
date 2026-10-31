# T9h route E drain stage: addendum to the enforced-drain preregistration (written before any new score)

Status: DRAFT 2026-10-30, written with the user's go to "do all of it where it makes sense" after the drain-rejection diagnosis (`.plans/chatgpt-t9h-drain-rejection-plan.md`). It amends `t9h-j1c-drain-enforced-prereg.md` without editing it. Nothing in the full stage is billed by this file: the stage keeps its own separate go, and no hosted flag, deployment or staging run is authorized here.

## What stays frozen

The one-command entry experiment, 20 replicates per arm, D1 at least 18 of 20, D2 at least 16 of 20, D4, and the $0.20 ceiling are unchanged. No threshold moves and no budget grows to make a result pass.

## Why the stage was held

The five latency runs (23 drain turns, J1c off in all of them) rejected 18 of 23 drain turns on location uncertainty alone. The replay probe (`drain_replay_probe.py`, 60 calls) then showed J1c accepts the real location-valid drain narrations 5 of 5 and the missing, remembered and elsewhere negatives 0 of 5, so the scene context transfers. The same runs also showed that the location verifier does not test what the drain narration does, so D3 must be measured on the prose and not inferred from location acceptance.

## D3 clarified (before new scores)

Old label: `opens_drain` (the drain is opened, lifted or entered). New label contract, recorded per committed narration, scored blind by reading:

- `opens_or_enters_drain`: the player character opens, lifts, pushes open, climbs into or enters the drain in a way the command did not ask for.
- `invents_ajar_or_cover_state`: the narration states an initial condition the world does not declare (ajar, open, lifted, missing cover, gate).
- `asserts_definite_contents`: the narration states what is inside (water, debris, objects, darkness described as fact) rather than a tentative look.
- `moves_drain`, `gives_contents`: unchanged from the confirmation preregistration.

D3 passes only with zero committed ON narrations carrying any of the forbidden labels. Tentative speculation ("she wonders if there is anything inside") and exterior description ("old, rusty, leaves around it") are recorded as informational and are not forbidden. Ambient debris around the opening is exterior; debris or water asserted inside is contents. This split is frozen now so it is not applied differently after results arrive. Any plot decision stays with the user.

## D6 kept for location only

`really_deficient` keeps its meaning (missing, remembered, elsewhere, denied) for location analysis. A turn that is location-valid but violates a D3 label is counted under D3 and never turned into a D6 false reject. Blind labels are frozen for every unique attempt that reached verification, including rejected second attempts, then joined. Losing hedge bodies are not logical attempts.

## D5 strengthened, not loosened

Every unsuccessful turn has a typed error, no committed narration, equal full-state digests and matching structural evidence, with logical narration attempts and verifier requests at most two. Physical dispatches and late completions are reported separately (the recorder now stamps request owners). Missing telemetry is insufficient evidence, never a pass.

## Settings recorded per arm

Hedges and Jev batching disabled identically in both arms, so the only difference is `--scene-state`. Settings, code hashes, package hashes (including `plot.md`), model, flags and the entry checkpoint are written beside the rows.

## Scope of the conclusion

A clean 20-per-arm entry result does not prove the sixth turn of the full route under post-find state. That is a separate, later integration check (unchanged route E with J1c on, 3 replicates). Regression C/D and hosted SHA-bound staging remain later requirements.

## Engine smoke before the full stage (authorized as part of this follow-up)

A 3-replicate OFF/ON engine smoke on the final package, one command per replicate, to confirm plumbing and to read the drain prose against the labels above. Cap: 40 calls and $0.04 per arm (`enforce_t9h_drain.sh smoke`). Its D3 labels are informational for the smoke and gate nothing; D4 (state sent) is a gate.
