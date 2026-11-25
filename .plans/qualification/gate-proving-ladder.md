# Gate-proving ladder: prove the gates before trusting them with the story

Part of the [qualification plan](../dark-factory-diagnostic-qualification-plan.md). Proposed 2026-11-23 after the owner doubted that much prose or many story beats could pass the full gate stack; approved by the owner the same day. **Progress:** R0 done; R1 sub-rounds R1a to R1c and R1e done, R1b-2 and R1d open ([results](gate-r1-results.md)); R2 to R7 not started.

**Read this when:** you add, change or remove a gate; before any step that sends real story work through the full line (Steps 4, 5, 7 and 8); or when good content is blocked.

## The problem in one number

Each gate is a classifier, and classifiers sometimes block good content. The stack compounds those false blocks. Fifteen gates that each wrongly block 5% of good beats pass only 46% of good beats (0.95^15). Twenty gates at 5% pass 36%. The stack also flattens: the cheapest way to clear many gates at once is dull, safe content.

The record already shows this risk. The first full run of a real ticket through the line (1A, rounds 19m to 19p in the parent plan) hit six defects before it reached a story question. Most of them were in the gates and stations themselves: the empty-`sets` compile failure, beat position, stale worktrees and the false quota sleep.

So the gates must be proven the way a classifier is proven: on labelled good and bad examples, one at a time first, then together, then at growing story size. Two rules hold throughout:

- **When good content is blocked, fix or demote the gate.** Never edit good content to get it through; that is flattening.
- **Every gate must earn its place.** It names the failure it exists for, catches its seeded version, and catches something no other gate catches.

## Test sets labelled by how they are built, not by a person

This is a dark factory, so no test set needs human labelling. Fun is also scene-specific: what makes 1C good is not what makes 3B good. So no universal list of good traits exists. Every label below comes from one of two places:
- **how the test item was built**, so the right answer is known by construction;
- **the scene's own authored intent**: `plot.md`, which stays ground truth, and the scene contract (feeling line, bond beats, setups and payoffs, character cards; fun requirement 7).

The owner's standing rules (the parent plan and the recorded decisions) are the specification. The owner approves this method once, as policy, and labels nothing.

1. **Good set (G).** Content already judged good by an independent evaluator, not by the factory being tested: scenes judged healthy (1B, 2A, and 1C replicates 1 and 3). It also includes saved turns where the narrator took initiative or added a harmless detail and the standing rules say that is not a failure.
2. **Seeded faults (B).** One minimal change per gate purpose, so exactly one gate should fire. The label is the change itself. Examples: remove a fact's producer (reachability), voice a bookkeeping line as dialogue (provenance), name a later-scene thing in earlier narration (leak scan), drop the cost passage from a recovery ("delay costs you").
3. **Meaning-preserving variants (V).** Rewrites that keep the scene's facts, exits and contract: paraphrased narration, independent beats reordered, synonyms in player commands written to the player-input guide. No label is needed. **Every gate must give the same verdict on a variant as on its original.** A gate that flips is reacting to surface wording, not to the defect it exists for.
4. **Subtracted twins (D), per scene.** Take one setup, payoff, twist or bond beat that this scene's own contract names, and remove it. Facts and exits stay intact. The label is what was removed. The fun gates are tested by comparison, not by an absolute grade: shown the full scene and its twin blind, in random order, the gate must prefer the full one and name what is missing. The correctness gates must pass both. This shows the stack protects each scene's designed fun without anyone deciding what fun means in general.

Subtracted twins need the scene contracts, which do not exist yet (every value in `factory/contracts/template.json` is `TODO`). So the correctness gates can be proven now on G, B and V, and fun-gate proving starts once fun requirement 7's contracts are authored.

## The rungs

Each rung is written test first: fixtures and expected verdicts before any gate change. Each rung reports a **funnel**:

- each gate's pass rate on G, B, V and D;
- the joint pass rate;
- every block, judged as a true or false block;
- attempts to pass, time and cost.

**Advance rule.** A rung passes when:
- every G item passes every hard gate (deterministic gates at 100%; model gates at their calibrated lower bound);
- every B item is blocked by its intended gate;
- every V item gets the same verdict as its original;
- every D item passes correctness, and the fun gates prefer the full scene and name what the twin lost;
- no conflict between two gates is still open.

### R0. Inventory (free)

List every gate:
- the load validators;
- story CLI layers 1 and 2;
- the 6,500-token prompt cap and the declared-name leak scan;
- station 5: source, gap delta, Ruff, tests, carry matrix, `twin_reveals`, journeys and the unreachable ratchet;
- the probe keep rule, the live playtest gate and the outcome contract;
- station 10's eight checks;
- the planned whole-game fun gate and delivery validator.

For each gate, record:
- what it reads;
- whether it is hard or report-only;
- whether it is deterministic or model-based;
- its cost;
- the incident it exists for.

Flag any two gates that read the same signal. The output is a table in this folder.

### R1. Each gate alone (free, except calibration of model gates)

- Run each gate on G, on its own B items, on V and on D.
- A deterministic gate must block 100% of its own B items, pass 100% of G, and give unchanged verdicts on V.
- A model gate (station 10, judges) needs measured miss and false-block rates with lower bounds, from the same construction-labelled sets. Opus designs that calibration, as the standing rule requires.
- A gate that blocks a G item is repaired or demoted before R2.

### R2. Gates together (free)

- **Measure mode.** Add a measure mode to the line: every gate runs on every fixture and returns its full verdict vector, with no fail-fast. Fail-fast hides the second and third blocker, so a repair for the first one can walk into the next. This is the one new piece of code the ladder needs, and it goes through Ringer.
- **Repair test.** For each B item, apply the minimal repair the factory would make. Then run every gate again. A repair that trips a different gate is a **conflict**.
- **Known tensions.** Test each of these with one fixture that must satisfy both sides:
  - the token cap against richer prose;
  - zero stuck turns against the anti-flattening guards;
  - the declared-name leak scan against plain names;
  - owned items needing their owner against no possessives;
  - narrator initiative against invented changes;
  - delight against "keep each object where the scene puts it".

  If no such fixture can be written, the pair is impossible as specified. The owner decides which gate changes.

### R3. One tracer beat through the real line (about $0.10 plus one capped Opus call)

- First, one storylet in a fixture story, from diagnosis to fun review.
- Then one beat in a real scene (1C) that pays off a setup the 1C contract names.
- Record joint pass, attempts, cost and every block.

### R4. One scene (about $0.30 to $0.60)

- Healthy 1C, unchanged, must pass every gate.
- Then seed one fault. The right gate must block it, the factory must repair it within its attempt budget, and the repaired scene must still pass every gate, fun included.
- Then add an enrichment that delivers something the 1C contract asks for. It must pass, and the fun gates must prefer it over the scene before enrichment.

### R5. Two scenes with real carry (about $0.50 to $1)

1C into 2A, played continuously. This adds continuity between scenes, the carry matrix and the between-scene fun check.

### R6. One act (about $1 to $3)

Act 1 (1A to 1C), played continuously. Pacing numbers are read against the F2 bounds, and fun is judged across the act.

### R7. Whole game

This is the Step 8 sample, with the whole-game fun gate. It starts only after R6 passes.

## How the ladder gates the other steps

| Step | Rung that must pass first |
| --- | --- |
| Step 4 (structural repair, N-3) | R4 |
| Step 5 (held-out trials) | R4, so a solver's correct repair isn't failed by a wrong gate |
| Step 7 (scene repairs) | R5, and R6 before an act-wide campaign |
| Step 8 (delivery) | R7 setup, i.e. R6 passed and the fun gate calibrated |

Steps 1 to 3 and the rest of Step 2 can continue alongside R0 to R2.

## Gate pruning

- A gate that, across R1 to R4, catches nothing another gate does not also catch is proposed for merging or demotion to report-only.
- A gate whose false-block rate on G cannot be brought to its bar is demoted until it can.
- Every demotion is listed for the owner's word. None is silent.

## Tasks

- [x] Owner approves this ladder and where it sits in the plan (2026-11-23).
- [x] R0 gate inventory table, with redundant gates flagged (2026-11-23: [gate-inventory.md](gate-inventory.md); 22 content gates, about 360 rules, five R1 priorities).
- [ ] Good set: healthy-scene beats and accepted narrator-initiative turns exported from saved, evaluator-judged runs.
- [ ] Seeded faults: one per gate purpose, each expected to trip exactly one gate.
- [ ] Meaning-preserving variants: generated by rule for each good item, written to the player-input guide where they touch commands.
- [ ] Scene contracts authored (fun requirement 7; Opus designs the set, Claude drafts from `plot.md`). This blocks the subtracted twins only.
- [ ] Subtracted twins, one per named setup, payoff, twist or bond beat in each contract, built by rule from the contract.
- [ ] Measure mode for the line (full verdict vector, no fail-fast), test first through Ringer.
- [ ] R1 passes: every deterministic gate at 100% on its own faults and on G; model-gate calibration designed by Opus, with figures approved first. Sub-rounds, results in [gate-r1-results.md](gate-r1-results.md):
  - [x] R1a: the two live stuck measures (gates 18 and 20) on the 27 frozen examples (2026-11-23). Both wrongly block 12 of 15 good runs; gate 18 passes 2 of 6 stuck runs. Fix is Step 2's outcome-contract wiring, not story work.
  - [x] R1b: runtime rejections (gate 16) in saved records (2026-11-23). Only `narration_known_term_leak` appears in retry telemetry (68 of 428 bench turns, 72% recovered); visible rejections 4.4% of bench turns, 0.6% hosted. The other 30 codes are unmeasured.
  - [x] R1b-2 (2026-11-24, see [gate-r1-results.md](gate-r1-results.md#r1b-2-adjudicating-the-recorded-term-leak-rejections-2026-11-24)): 43 of 68 term-leak rejections are candidate false (the player's own words), all recovered by retry; 25 are unearned-new. Original text: adjudicate the recorded term-leak rejections true or false, starting with the pattern of narration repeating the player's own words. Needs a labelled method that is not human labelling; design it before running anything billed.
  - [x] R1c: story-pinning test files (gate 11), static parse (2026-11-23). 268 of 400 assert on real-story IDs (249 run on every PR); an upper bound on structure pinning, not on prose blocking.
  - [ ] R1d: fun review (gate 21) calibration, designed by Opus (estimate first, owner's word on figures).
  - [x] R1e (2026-11-24): the good story passes gates 1 to 10; six of nine seeded faults are blocked by exactly their own gate; gates 3 and 4 act as one gate (load validators run inside compile, so the leak fault never reached gate 9). Gates 1 to 5 hold on all four variants. The full suite blocks every variant, mostly (34 tests) because nothing in the factory regenerates entry snapshots after a source edit; true wording and order pins are about 5 and 6 tests. R1e-2 (2026-11-24): station 5 now regenerates entry snapshots in the ticket tree (patch applied, uncommitted). With that and canonical format, the variants fail 0, 0, 5 and 6 tests, confirming the pins: five text-freeze tests, and six prompt-order tests, all from one possessive narrator rule. Original task: remaining deterministic gates on the good set, seeded faults and meaning-preserving variants. Includes the dynamic suite test that R1c could not do: run the full suite against meaning-preserving story variants and count failures.
- [ ] R2 passes: the repair test and the six known tensions, each with a fixture that satisfies both sides, or an owner decision on the impossible pair.
- [ ] R3 passes (estimate written first).
- [ ] R4 passes (estimate written first).
- [ ] R5 passes.
- [ ] R6 passes.
- [ ] Gate pruning list reviewed by the owner.

## Rough cost

R0 to R2 are free in dollars: about 2 to 4 working days and roughly 300k to 600k Ringer tokens, plus one Opus calibration design session. R3 to R6 total roughly $2 to $5 in narration, plus capped Opus fun calls. These are planning ranges. Each billed rung gets its own estimate before it runs and its actual after.
