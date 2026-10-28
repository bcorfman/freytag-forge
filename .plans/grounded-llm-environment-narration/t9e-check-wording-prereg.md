# T9e: a wording fix for `Check the glove box.` and a fresh probe: preregistration (written 2026-10-28, before any build and before any billed call of this stage)

Status: written on Brandon's instruction ("I do want to do your recommendations in A after all, but don't stop the existing smoke", 2026-10-28), after the T9d stage P v2 probe failed K2 on one phrase (`Check the glove box.`, `opens_container` true at 0.64 and 0.62) and Brandon waived K2 for that run (T9d stages S and F are running on the T9d wording, from `main` at `2cef88ec`; their results are recorded separately and are not changed by this document). Nothing below is built. No billed call of this stage has been made. Billed stages wait for the merge (Brandon's instruction, merge commit), staging deployed and recorded for the merge SHA, and no merge during a run (the T9d runs must have finished). It does not change `t9d-search-opens-prereg.md` or its data.

## Why

`Check the glove box.` is the only one of 64 bare `Inspect`, `Examine`, `Check` and `Look at` samples (`Check` was on 16 containers) that `opens_container` answered true. A glove box is something people check by looking inside, so Jev read the phrase that way. In the game the kind `open` makes the engine open a closed openable container; for `check` that is a harmless extra (the supplies are shown), but it contradicts Brandon's rule that `check` is a look verb, and a container that people usually open is exactly where Jev leans true. The T9d wording names `checks` only inside a long false list. This change states the contrast in the instructions themselves, which is where Jev reads first (`docs/jev-guard-rules.md`: one sentence stating the job, make "yes" mean the thing sought).

## The change (fixed now)

**1. `opens_container` wording (code, Ringer).** In `storygame/runtime/jev_questions.py` the three strings become:
- instructions: `Decide whether the command has the player open the container. Opening it, pulling it open or out, searching it, or going inside, in, into, or through it counts. Checking, inspecting, examining, or looking at it does not.`
- true: unchanged: `The command opens the container, pulls it open, pulls it out, searches it, or says inside, in, into, or through the container. The player looks, feels, or reaches there.`
- false: `The command does not open the container, does not search it, and does not say inside, in, into, or through. A command that only checks, inspects, examines, looks at, closes, locks, touches, moves, carries, or talks about the container, or goes behind or on top of it, is false.`
Name, signature, return type and the `noul` type are unchanged. `searches_underneath` and the engine are unchanged.

**2. Nothing else changes.** The under-first order, the engine open step, the nudge, the report and the gates of T9d stay as they are.

## Stage P (probe v3, billed, tiny)

Corpus `opens_probe_v3` (`opens_container_probe.py --corpus v3`; v1 and v2 stay untouched). Player-input voice (imperative with a direct object; `docs/player-input-guide.md`). The fresh lists below were written after the wording; none of their commands appears in the T9c or T9d lists. Container names in brackets.

**FL: fresh bare look-group negatives (24, `opens_container` only, must be false), on containers people usually open:** Check the mailbox. [mailbox] / Check the fuse box. [fuse box] / Check the jewelry box. [jewelry box] / Check the safe. [safe] / Check the refrigerator. [refrigerator] / Check the oven. [oven] / Check the backpack. [backpack] / Check the purse. [purse] / Check the handbag. [handbag] / Check the wardrobe. [wardrobe] / Check the nightstand. [nightstand] / Check the toy box. [toy box] / Inspect the safe. [safe] / Inspect the refrigerator. [refrigerator] / Inspect the backpack. [backpack] / Inspect the wardrobe. [wardrobe] / Examine the fuse box. [fuse box] / Examine the jewelry box. [jewelry box] / Examine the purse. [purse] / Examine the toy box. [toy box] / Look at the mailbox. [mailbox] / Look at the oven. [oven] / Look at the handbag. [handbag] / Look at the nightstand. [nightstand].

**FS: fresh search positives (8, `opens_container` only, must be true):** Search the mailbox. [mailbox] / Search the fuse box. [fuse box] / Search the jewelry box. [jewelry box] / Search the safe. [safe] / Search the refrigerator. [refrigerator] / Search the backpack. [backpack] / Search the purse. [purse] / Search the wardrobe. [wardrobe].

**FI: fresh inside positives (8, `opens_container` only, must be true):** Look inside the mailbox. [mailbox] / Check inside the fuse box. [fuse box] / Inspect inside the jewelry box. [jewelry box] / Examine inside the safe. [safe] / Look inside the refrigerator. [refrigerator] / Check inside the oven. [oven] / Examine inside the backpack. [backpack] / Look inside the toy box. [toy box].

**FU: fresh underside commands (8, `searches_underneath` only, must be true; `opens_container` is not asked because the engine asks the underside question first):** Search under the wardrobe. [wardrobe] / Check beneath the nightstand. [nightstand] / Inspect underneath the refrigerator. [refrigerator] / Look under the safe. [safe] / Examine below the oven. [oven] / Feel under the toy box. [toy box] / Search beneath the handbag. [handbag] / Check under the backpack. [backpack].

**Retained, seen, labelled regression (not part of the fresh gates):** the miss `Check the glove box.` [glove box] (`opens_container` must be false); the T9d regression set R (12 commands on `drawer`: opens true for Open the drawer. / Pull out the drawer. / Look inside the drawer. / Search the drawer. / Search inside the drawer.; opens false for Inspect the drawer. / Examine the drawer. / Check the drawer. / Look at the drawer. / Close the drawer.; `searches_underneath` true for Search under the drawer. / Look under the drawer.); the T9c opening positives O (20) and non-opening negatives N (22) exactly as in `t9d-search-opens-prereg.md`.

**Counts and cost.** FL 24 x 2 = 48; FS 8 x 2 = 16; FI 8 x 2 = 16; FU 8 x 1 question x 2 = 16; glove box 1 x 2 = 2; R (10 opens + 2 under question-cases) x 2 = 24; O 20 x 2 = 40; N 22 x 2 = 44. Total **206 requests**, `--max-calls 206 --max-usd 0.01` (estimate under $0.001). Stop on 429, auth failure or the cap; no rerun, no replacement samples. Output `bench/results/environment-narration/t9e-check/probe/`.

**Gate P (set now).**
- **M1: zero `opens_container` true answers among the 48 FL samples, and `Check the glove box.` false on both samples.** (One-sided 95% bound about 6% for zero of 48.) Every true answer named with its score.
- **M2: FS at least 14 of 16 true; FI at least 14 of 16 true; FU `searches_underneath` at least 15 of 16 true.**
- **M3: R all 10 true-labelled and all 10 false-labelled `opens_container` samples right and all 4 `searches_underneath` samples true; O at least 38 of 40 true; N zero true of 44.**
- A `None` counts as not true; report their number and every score. `probe gate: PASS` only if M1, M2 and M3 all pass. If any fails, no enforced run starts, and I do not waive a gate myself; a further wording change needs another fresh list and preregistration, and only Brandon can waive a gate.

## After a pass

The wording is part of what ships, so stages S and F are rerun once each from `main` at the new staged merge SHA with the T9d gates and caps unchanged (`t9d-search-opens-prereg.md`, "Stages S and F"; `$0.07` smoke and `$0.45` full, expected about `$0.24` in total). The T9d stage script writes under `t9d-search/`, which would overwrite the T9d rows, so a copy `enforce_t9e.sh` and run manifests writing under `bench/results/environment-narration/t9e-check/{smoke,full}` are built after the probe passes (a small free Ringer task, same caps, same checks). Procedure as T9d: blind sheets, every turn read, labels hash frozen before `join`. The T9d F result stands on its own as the measurement of the T9d wording.

## Build (free, Ringer, tests first)

(1) The wording change in `jev_questions.py`, with the test that pins the three strings and any older test that pins the T9d text (every changed assertion listed). (2) Probe v3: `--corpus v3` in `opens_container_probe.py`, `opens_probe_v3/cases.jsonl` and lock, gates M1 to M3, dry-run count 206, a test that every fresh command occurs in this document and none occurs in the v1 or v2 corpora, and the runner manifest `run-t9e-probe-live.json` from a generator (output next to the generator).
