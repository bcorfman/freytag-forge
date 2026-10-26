# T8 live shadow sample of the observation verifier: preregistration (unapproved)

Status: written 2026-10-25 for Brandon's approval. No billed call has been made for this sample. The harness (`--shadow`, route `observe`) and the report script are built and tested offline.

**Question.** On real 70B narration produced by the product path, does the shadow observation verifier (Jev, `observation-relation-v1`, accept > 0.65, reject < 0.35, unchanged from T7) agree with a hand reading well enough to be trusted as an enforcing guard? T7 showed this on written cases; this sample checks it on live prose.

**What runs.** The real engine with product wiring (world capture, Jev matcher, observation mode on) against a local Worker on 127.0.0.1 with a hard dollar cap (`local_worker.mjs --max-usd`), exactly as in the earlier live check. `WorldCapture.shadow_verifier` is on, so every observation turn records the verdicts; the verifier never changes a turn, so the narration is what the product would show. `enforcing_verifier` stays off.

**Route (frozen).** `observe`, 13 imperative commands in order: inspect the drawer, pull out the drawer, feel under the drawer, feel under the drawer, go outside, inspect the truck, enter the truck, inspect the passenger seat, examine my laptop, get out of the truck, examine the truck, go inside, inspect the drawer. It covers the T2 matrix rows that the 1A package can express: closed and opened drawer, a search that earns the card, a repeat search after recovery (held item, empty scope), boarding, a seat, a held laptop, and look-at on the truck from outside and after getting out. Commands whose observation request depends on the match model may not set a request; those turns are listed as skipped, not replaced.

**Counts and cost.**
- 5 replicates x 13 turns = 65 turns. Expected observation turns about 40 to 50; expected required relations about 60 to 90.
- Calls: about 70 per replicate (4.6 narrator, match and Jev calls per turn from the 2026-10-25 live check, plus about one verifier request per observation turn). Cap `--max-calls 450`.
- Cost: the live check was $0.0354 for 145 calls, so about $0.09 expected. Local Worker ceiling `--max-usd 0.25`, no retries, no replacement samples. All caps are maxima.
- Smoke first (small, billed): `--route observe --shadow --replicates 1 --turns 4 --max-calls 40` (about $0.01) to confirm the rows carry `observation_shadow` and `observation_relations`. Then the full run once; never rerun after a partial result.
- Stops on any quota code, HTTP 429 or 5xx from the Worker, or the caps.

**Procedure.**
1. Dry run (free): `live_baseline.py --route observe --shadow --replicates 1 --dry-run` (48 calls; proves wiring only).
2. Smoke, then the full run, each as one Ringer probe task (`live_check`-style script with the local Worker). Artifacts under `bench/results/environment-narration/shadow-sample/` (gitignored).
3. Blind reading: `shadow_report.py sheet rows.json` prints narration and relations with no verdict content. I read every observation turn and write a label per relation (true = the narration presents that thing as present at the stated place or holder; false otherwise) into a labels file, and also note by hand any invented object, unrequested move or contradiction. Labels are frozen (file hash recorded) before `join` is run.
4. `shadow_report.py join rows.json labels.json` prints the confusion table, false accepts, strict rejections, would-reject rate, latency and the gate.
5. Every turn is read and reported per requirement, not pooled; the T8 plan record gets the numbers and the exact limits.

**Gate (set now, before any data).** The verifier may be designed in as an enforcing guard (T9) only if all hold:
1. Zero false accepts: no relation with verdict accept whose hand label is false.
2. Strict rejection of good turns at most 10%: among turns whose labels are all true, the share with any relation not accepted or a shadow outcome other than ok. With one recovery attempt and independent attempts, 10% per attempt means about 1% of turns fail, which is the T9 target; independence is assumed, not shown.
3. Verifier request latency p95 at most 2.0 s (the normal path target is a whole-turn p95 under 10 s).
4. At least 30 labelled relations (otherwise the sample is reported as inconclusive, not as a pass).

If the gate fails, enforcement stays off and the report says which clause failed and for which relation types; a second sample needs a new preregistration. A pass does not turn enforcement on: T9 is a separate confirmation.

**Stated limits.** About 70 relations is a small sample: zero false accepts bounds the true rate only to roughly 4% (one-sided 95%, `1 - 0.05^(1/n)`), and relations in one turn are correlated. One story, one route, the 70B narrator only. The labels come from one reader (me), who knows the aim of the sample; the blind sheet removes verdicts but not the context. The verifier cannot detect unreported inventions, so the hand notes on inventions are reported next to, not inside, the gate. The attempt-independence assumption in clause 2 is untested. Outcomes depend on the current prompt, model revision and Jev version, all recorded per row.

## Addendum A (2026-10-25, written after the smoke stage and before the full run)

The smoke stage (1 replicate, 4 turns, 24 calls, $0.0048, run id `grounded-environment-narration-20261026T020351Z-p1212110`) showed the harness works: rows carry `observation_shadow`, `observation_relations` and `observation_request`. It also showed what the gate above would miss. On "feel under the drawer" the observation request was `look` at the drawer, so the required relations were the drawer's visible contents (stapler, pens, spare batteries, binder clips). The narration, reasonably, did not list them, and the verifier rejected all four at scores 0.02 to 0.03. Under enforcement that good narration would be rejected twice and the turn would fail. Gate clause 2 only looks at turns whose labels are all true, so this kind of over-demanding requirement would be hidden inside "not a good turn".

Added reading (the run, route, counts, caps and the four clauses above are unchanged): for every observation turn I also record `acceptable` (true/false), judged from the command and the narration alone: would a player find the narration an acceptable answer to the command, with nothing invented that breaks the story, no unrequested move, and no contradiction of the world facts shown on the sheet. This is written before the verdicts are opened, with the relation labels.

New clause 2b, same threshold as 2: among turns with `acceptable` true, the share that enforcement would reject (any relation not accepted, or shadow outcome other than ok, or `no_relations` is NOT a rejection) is at most 10%. Clause 2 stays as written. The report prints both. If 2b fails because required relations are over-demanding for the command, that is a finding about the observation context (T3), not about the verifier, and is reported as such. The smoke turns are not part of the full run's data and are not counted in any rate.

Smoke observations recorded now, before the full run (not gate data): "inspect the drawer" on turn 1 already earned the memory card (the reveal fires on inspect), so turns 3 and 4 "feel under the drawer" are searches of an emptied drawer and both re-found the card in the narration (the known open defect); turn 4 also appended the patrol arrival text.

## Result (2026-10-25, code SHA `7faf10cc`, Ringer smoke `...T020351Z-p1212110`, full `grounded-environment-narration-20261026T020505Z-p1215565`)

Run as preregistered: route `observe`, 5 replicates x 13 turns = 65 turns, 336 real calls (cap 450), no errors, no quota stop, local-Worker spend **$0.0633** (ceiling $0.25). 55 observation turns, 76 required relations, 26 verifier requests (the summary says 31; see harness defect below). Rows `bench/results/environment-narration/shadow-sample/full/rows/rows.json` (sha256 `aaca5776240d1a347bc21c7c61c609ffa7be3f3ffc8f757b591ff3702e4a447b`), labels `labels.json` sha256 `60ed673e767a4a9370a7a38122fd8ac3dcd1f0fb48600dc627bdd3dbfb2105a3` frozen before `join` was run, report `report.md`, all gitignored.

**Gate: FAIL, on clause 2b only.**
1. False accepts: **0 of 76** relations (one-sided 95% upper bound 3.9%, relations within a turn are correlated). PASS.
2. Good-turn strict reject: 4/42 = 9.5%. PASS (borderline).
2b. Acceptable turns enforcement would reject: **9/42 = 21.4%** (limit 10%). FAIL.
3. Verifier latency p95 0.27 s. PASS.
4. 76 labelled relations (at least 30). PASS.

**Why 2b failed (every one of the 9 is listed in `report.md`; none is a false accept):**
- 5 of the 5 scene-transition turns (`inspect the drawer` as turn 13: the engine moves Kristin to the next scene) were rejected. The required relations are still the old drawer's contents (stapler, pens, spare batteries, binder clips) and the authored entry text rightly does not mention them. Those turns are acceptable and the requirement is stale: a structural defect in the observation context (it is built after the scene changed or without regard to it), not the verifier.
- 4 of 10 true holder relations were rejected or uncertain: the memory card held by Kristin on `enter the truck` (scores 0.46 uncertain, 0.33, 0.04, and accepted twice) and the laptop in her hands on one `examine my laptop` (0.27). Place-type relations were separated cleanly: all 60 drawer-content relations agreed with the hand label (0 disagreements) and the laptop at the passenger seat was accepted 6 of 6; the only 4 verdict/label disagreements in the whole sample are the holder relations. The holder relation is rendered with place and holder both set to the character's full name ("at place Kristin Schweitzer and held by Kristin Schweitzer"); that is the likely weak spot but it is a hypothesis, not tested.

**What the verifier cannot judge (reported next to the gate, not inside it).** 13 of the 55 observation turns are not acceptable by hand reading: all 10 `feel under the drawer` turns re-find the memory card that Kristin already holds (five replicates x two searches; some quote the scene sentence as speech or add "the one she already had"), and 3 of 5 `inspect the passenger seat` turns invent an object (a piece of paper; scraps of paper and a water bottle; strands of hair). The required relations for `feel under the drawer` are the drawer's contents, so the verifier accepted two of those re-find turns (they listed the contents) and rejected eight (they did not). Its verdict there is unrelated to the real defect. Enforcement as designed would neither catch these nor fix them.

**Harness defects found (free to fix, not billed):** (1) the two engine-authored move turns per replicate (`go outside`, `go inside`, 10 turns) make no narrator call, `after_commit` does not run for them, and the harness copied the previous turn's `capture.last_after` shadow record and stale `observation_request` into their rows; the summary's 31 requests includes 5 such copies, the true count is 26. The join ignores those rows. (2) The first report script treated zero-relation turns as rejections; fixed and tested before the join was run.

**Decision (per the preregistration).** Enforcement stays off. A second sample needs a new preregistration. Before one: stop requiring stale relations when the scene or the protagonist's area changed, test the holder-relation wording on the frozen T7 corpus plus the 10 holder cases found here, and decide separately how the re-find and invented-object defects are to be fixed, because the verifier does not address them.
