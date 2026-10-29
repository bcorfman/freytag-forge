# T9h: confirmation of enforced observation on scenes and containers not yet measured: preregistration (DRAFT written 2026-10-28, before any build and before any billed call)

Status: draft for Brandon's approval. Nothing below is built. No billed call has been made. It does not change the T9, T9b, T9c, T9d or T9e preregistrations or their data; those numbers are never pooled with these. Billed stages wait for Brandon's go, the merge of the free build (merge commit), staging deployed and recorded for the merge SHA, and no merge during a run. Code SHA at drafting: `e2c78b21` (T9g timing split merged; T9f merged earlier).

## Why

Every enforced run so far (T9 stage 1, T9b, T9c, T9d, T9e) used scene 1A: the drawer, the truck, the passenger seat and the laptop. T9d stage F and T9e passed their gates only after K2 and clause 6 were waived by Brandon. The switch `FREYTAG_OBSERVATION_ENFORCE` is off by default and unset on the hosted app. Before it is turned on for staging, and before the default changes, enforcement needs a measurement on **things it has not seen**: other containers and supporters, in other scenes, with commands written after the wording was fixed. That is what this document asks for. It also gives the first live read of the T9g per-call timings and the first live read of T9f.

"Fresh seeds": the bench has no seed; replicates differ by model sampling only. Fresh here means new commands, new targets, new scenes and new replicates, never a rerun of an earlier route.

## What is fixed now

**Code under test:** `main` at the merge SHA recorded for staging. No wording or engine change is made in this stage. If the free build finds one is needed, this document is stopped and rewritten.

**Not covered, on purpose:** route B `inspect the drawer` after the card is found (the dangling "decides to open it", T9f finding 1) stays an open defect and is excluded from every gate. It is printed.

## Routes (commands are imperative with a direct object, `docs/player-input-guide.md`)

Targets come from `world.yaml`: `workstation` (kind desk, supporter) and `workstation chair` (kind seat, supporter) in scene 1A; `park bench` (seat, `disclosure: public`, fixed) in scene 1B; `executive desk` (kind desk, supporter) in scene 3B. The engine asks the open question only for a container focus, so supporters test `searches_underneath` and the rule that a look or search never opens anything. The drawer is the only container in the story data; the cooling-service archive panel is an openable `thing`, not a container kind, and is **not** a gated target (the free build prints whether the engine treats it as a container; if it does, a fifth route is proposed in a separate addendum, not added silently).

- **Route D (scene 1A, new targets, 6 turns):** inspect the workstation / search the workstation / look under the workstation / examine the workstation chair / check the workstation chair / look under the workstation chair.
- **Route E (scene 1B, 6 turns):** inspect the park bench / look under the park bench / search the park bench / check the park bench / look under the park bench / inspect the storm drain. The storm drain is a fixed non-container, non-supporter thing and serves as a control: a look must not open it, move it or invent contents.
- **Route F (scene 3B, 6 turns):** inspect the executive desk / search the executive desk / look under the executive desk / examine the executive desk / check the executive desk / look under the executive desk.
- **Route C regression (scene 1A drawer, existing `observe_look_inside_under`, 6 turns):** unchanged. Its only purpose is the first live read of T9f and of the timing split.

## Stage P: supporter underside probe (billed, tiny)

The earlier probes grid-tested `searches_underneath` on containers. Supporters were never in a list. Asks the product's Jev client 2 samples per case, `searches_underneath` only (the engine asks nothing else for a supporter), no narration. Corpus `underside_probe_v4` (new; v1 to v3 untouched; every command below is absent from the v1 to v3 lists and a free test asserts it and asserts each occurs in this document).

**US (12, must be true):** Look under the workstation. / Search under the park bench. / Check beneath the executive desk. / Feel under the sofa. / Look under the coffee table. / Inspect underneath the bed. / Look beneath the bookshelf. / Search under the chair. / Check under the stool. / Feel beneath the counter. / Look under the picnic table. / Examine below the bench.

**UB (12, must be false):** Inspect the workstation. / Search the park bench. / Examine the executive desk. / Check the sofa. / Look at the coffee table. / Inspect the bed. / Search the bookshelf. / Examine the chair. / Check the stool. / Look at the counter. / Search the picnic table. / Inspect the bench.

**Counts and cost.** 24 cases x 2 samples = **48 requests**, `--max-calls 48 --max-usd 0.01` (under $0.001). Stop on 429, auth failure or the cap; no rerun, no replacement samples. Output `bench/results/environment-narration/t9h/probe/`.

**Gate P (set now).** P1: at least 22 of 24 US samples true. P2: at least 22 of 24 UB samples false. A `None` counts as not true; every miss is named with its score. `probe gate: PASS` only if both hold. If it fails, no enforced run starts, I do not waive it, and only Brandon can.

## Stages S and F: enforced runs

Same engine, product wiring, enforcing verifier, local Worker, 70B JSON off, 20 s timeout and no retry on a timeout as T9d and T9e; output `bench/results/environment-narration/t9h/{smoke,full}/{c,d,e,f}`; a new port. `--enforce` is on, so every row carries `call_timings` (T9g).

| stage | route C | route D | route E | route F | `--max-usd` |
| --- | --- | --- | --- | --- | --- |
| S (smoke) | 1 replicate, `--max-calls 50` | 2, `--max-calls 90` | 2, `--max-calls 90` | 2, `--max-calls 90` | 0.07 |
| F (full) | 5, `--max-calls 250` | 10, `--max-calls 450` | 10, `--max-calls 450` | 10, `--max-calls 450` | 0.45 |

Stage F is 210 turns. Expected spend about **$0.23**, from T9d's planned $0.22 for 200 turns (an estimate, not a measurement). No reruns; stop on any quota code, 429, 5xx or cap. Procedure as T9d: blind sheets, I read every turn, freeze the labels hash before any verdict is opened, then `join` per route. Labels as in T9d with `command_opens` true only when the command text opens the container, pulls it open or out, searches it, or says inside, in, into or through it; for supporter routes every `command_opens` is false.

**Gate (set now; per route D, E, F unless it says route C).**
- **G1 unsuccessful turns:** at most 1 of the 60 observation turns on the route (a turn that ends with no committed narration after recovery). Wilson upper bound printed.
- **G2 presents_required:** zero committed narrations that fail it.
- **G3 tags:** zero `leak`, `wrong_custody`, `unrequested_move`; at most 1 `refind` and 1 `invented_object` per route.
- **G4 rollback:** every unsuccessful turn leaves `places_after == places_before`, a typed error, no narration, and the next turn runs. Zero violations.
- **G5 budget:** no turn uses more than 2 narration attempts or 2 verifier requests. Zero violations.
- **G6 latency (the plan's target, unchanged):** end-to-end p95 of turns that needed no recovery at most 10 s, per route and pooled over C, D, E, F. Not self-waived: a FAIL stays FAIL in the record. The `call timing` block is printed with it; whether the tail is single slow Jev calls, narration retries or time outside calls decides what is fixed next.
- **G7 false rejects:** at most 1 of the rejected first attempts labelled not `really_deficient`; inconclusive if fewer than 5 are rejected.
- **G8 engine audit (all four routes):** zero turns where the engine opened a container and `command_opens` is false; zero engine opens on routes D, E, F (they hold no container).
- **G9 control (route E):** on the storm drain turn, zero committed narrations that open the drain, move it, or give it contents.
- **G10 T9f (route C only):** zero committed narrations in which a present officer speaks `k_sl_1a_f_r1` or `k_sl_1a_f_r2` (the drawer-gap statements), counted from the prose by me. T9e had 3 of 15 `look inside the drawer` turns. Route C's older gates (N1 to N6 of T9c and T9d) are printed, not re-gated, because 5 replicates cannot hold the T9d thresholds.
- **Printed, not gated:** first-attempt rejection rate, recovery success, handoff outcomes, kind distribution by route, narrator-set opens, `searches_underneath` and `opens_container` request counts, the `call timing` block per route (counts, per-kind p50/p95/max, turn time outside calls, slowest five turns and Jev calls).

A pass of P, S and F does not deploy anything and does not turn any switch on. It permits writing Stage H. A FAIL on G1, G2, G3 or G4 on any route is a stop, with the rows and labels recorded and nothing rerun.

## Stage H: staging only (not specified here, needs its own addendum and Brandon's explicit instruction)

After a pass: set `FREYTAG_OBSERVATION_ENFORCE=1` on **staging only** (a deploy-config change, never done without Brandon's explicit instruction), then one scripted browser session on the hosted staging demo against the 1A route, and the existing staged E2E suite. The pass criteria, session length and who watches it are fixed in the addendum after the E2E runbook is read; they are not set here because I have not read it for this purpose. Changing the default in `web_demo.py` and the production deploy config is a third, separate instruction.

## Expected, not measured

- G6 is the weak gate. T9e passed it on neither route that mattered (p95 27.10 s route A, 16.43 s route C at stage F), and Jev latency moves between runs (p50 154 ms to 839 ms). Expect G6 to fail or to be borderline; the point of this run on that clause is the timing split.
- Supporters ask only `searches_underneath`; an under word Jev misses gives kind `look`, and the narrator may then describe the underside without the engine's under handling. Stage P tests it on 24 phrasings.
- Scene 1B and 3B start state: see the build item below; a scene that cannot be started without hand-set facts has its route dropped, not weakened.

## Stated limits

One story, 70B only, one reader who knows the aim, correlated replicates from one start per scene, hand-made lists, and a single container in the whole story data. 60 observation turns per route bound a zero count only to about 5% (one-sided 95%). Passing here does not prove enforcement for stories with more container kinds; it shows it does not break on the supporters and scenes of this one.

## Build (free, Ringer, tests first; checked before any billed stage)

1. **Start a replicate in a named scene.** The harness always bootstraps scene 1A (`RuntimeState.bootstrap` takes the first scene; `ROUTES` in `live_baseline.py` has no start option). Routes E and F need a start built from the story's own scene entry (`apply_scene_placements` and the scene entry fact), not hand-set facts. Two paths already exist in the tests: constructing `RuntimeState(package, current_scene_id=..., phase=...)` (as `tests/test_3a_records_followup.py` does) and replaying a journey (`tests/journey_prefix.py`). Expected: one small Ringer task plus tests, no billed cost. First free step: check scene 1B and scene 3B separately. 3B may depend on facts earned in 2C and 3A (its `item_ids`), so a placements-only start could leave the world thinner than a real player's; a replayed journey would be more faithful but slower and more fragile. Report which path each scene needs. If a scene can only be started with hand-set facts, drop that scene's route and return to Brandon; keep the others.
2. **Does the observation intent engage on these targets?** Free, hermetic: with a stub Jev, confirm the focus resolves for `workstation`, `park bench` and `executive desk` and that the container and supporter branches are as expected (no names in engine code).
3. **Routes D, E, F** added to `ROUTES` with a test that pins the command lists above.
4. **Report generalisation.** `enforce_report.py` N-clauses are written around the drawer. Add G1 to G10 per route, scoped by route, without changing any old gate; tests on synthetic rows including a failed turn, a recovered turn, an engine open on a supporter route and an officer quote.
5. **Probe v4:** `underside_probe_v4/cases.jsonl` and lock, gates P1 and P2, dry-run count 48, a test that each command occurs in this document and in no v1 to v3 list.
6. **Stage script and run manifests** from a generator, with a row-count or stop-reason check and a credential-leak check, as `enforce_t9e.sh`.
7. Plan record after each item.

## Decisions for Brandon

1. Approve this draft, or change the targets, replicate counts or gates.
2. G6: keep the 10 s p95 as a gated clause (my recommendation: a FAIL then needs your explicit waiver before staging, as before), or move latency to printed-only for this stage and set its gate after the timing split is read.
3. Routes E and F stay in (decided 2026-10-28). The scene-start build is modest and free; if scene 3B proves awkward, route F alone is dropped and the run goes ahead with C, D and E, after a note in the plan.
