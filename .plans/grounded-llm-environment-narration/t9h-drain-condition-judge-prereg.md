# T9h drain condition judge preregistration

Status: FROZEN before any score exists. Written 2026-10-30 for Step 2 of the T9h drain-condition experiment. This document fixes the question, cases, scoring, gate, budget, stop rules, and limits. It does not authorize a billed run by itself.

## Question

For one narrated turn, does the narration stay inside what the world declares for a thing? The typed Jev question has type `noul`. TRUE means consistent with the declared state. FALSE means the narration states an open, ajar, lifted, covered, entered, or contents claim that the declared state does not support. A high score therefore means consistent.

The implementation uses the `noul` shape from `storygame/runtime/jev_questions.py` and sends one question for one narration. It does not parse narration text to make a label.

## Frozen sources and hashes

The cases are built from these read-only, adjudicated inputs:

| Source | SHA-256 |
| --- | --- |
| `bench/results/environment-narration/t9h-drain-condition/corpus/corpus-adjudicated.json` | `1a9b38c98a2f14fbfb8ed4a39e6ad1bc74264eec3f523d94400e6496af2adcc9` |
| `bench/results/environment-narration/t9h-drain-condition/heldout/heldout-labeled.json` | `936f6ace84c934b2f9ecce3873c3790ad64c10b17345054a8eeb877217958166` |

The frozen generated case file is `scripts/ringer/environment_narration/drain_condition_judge/cases.jsonl`. Its SHA-256 is `c5387f4236bb386e52c690dc702ff28143b0b3ab4540594fcf20f12c1cff669b`, recorded in the adjacent `lock.json`; a run or report requires that lock to match. The case file contains 100 drain rows and 40 held-out rows. A drain row is forbidden when any of `opens_or_enters_drain`, `invents_ajar_or_cover_state`, or `asserts_definite_contents` is true in its frozen `final_label`. Held-out rows use their frozen `forbidden` label.

Each case has exactly: `id`, `set`, `thing`, `command`, `narration`, `declared`, `forbidden`, and `source_ref`. Drain cases use the real narration, `storm drain`, `inspect the storm drain`, and this declaration: `the storm drain has no open or closed value, no declared contents, and is fixed in place.` Held-out cases use the real thing name and narration. Their declaration is rendered as:

`Declared before the turn: <thing> was <closed|open|has no open/closed value>; <N> declared item(s)<, some hidden>; <fixed in place|not fixed in place>. The engine <did|did not> open it this turn.`

The recorded `open_state_after` field is not copied into a case or payload. It reflects the narration's own claim and is not authorization.

## Frozen question variants

Every variant returns a state and one `noul` question named `condition_consistent`. The text below is verbatim, apart from interpolation of values into state fields. No variant text contains a story-specific word; the same wording must work for a drawer, truck, laptop, or drain.

### Variant A: bare

State: `{narration, thing}`.

Instructions:

> Decide whether the narration stays inside what is declared for the thing named in the state. Treat a claim that the thing is open, ajar, lifted, covered, or entered, or a claim about what is inside it, including what can be seen, heard or smelled there, such as darkness, water, objects, sounds or smells, as a violation when the narration states it as fact.

TRUE criterion:

> The narration does not state that the thing is open, ajar, lifted, covered, or entered, and does not state what is inside it, including what can be seen, heard or smelled there, such as darkness, water, objects, sounds or smells, as fact.

FALSE criterion:

> The narration states that the thing is open, ajar, lifted, covered, or entered, or states what is inside it, including what can be seen, heard or smelled there, such as darkness, water, objects, sounds or smells, as fact.

### Variant B: declared-state context, pre-declared candidate

State: `{narration, thing, command, declared}`.

Instructions:

> Decide whether the narration is consistent with the declared sentence for the thing named in the state. It is consistent when it does not state any open, ajar, lifted, covered, or entered condition, or state what is inside it, including what can be seen, heard or smelled there, such as darkness, water, objects, sounds or smells, unless the declared sentence supports it. The declared sentence says whether the engine opened the thing this turn, and an opening the engine performed is supported. Looking at, approaching, kneeling beside, touching the outside, or wondering what might be inside are consistent.

TRUE criterion:

> The narration is consistent with the declared sentence. It does not state an unsupported open, ajar, lifted, covered, or entered condition or what is inside it, including what can be seen, heard or smelled there, such as darkness, water, objects, sounds or smells, as fact.

FALSE criterion:

> The narration is not consistent with the declared sentence. It states an unsupported open, ajar, lifted, covered, or entered condition or what is inside it, including what can be seen, heard or smelled there, such as darkness, water, objects, sounds or smells, as fact.

Variant B is the declared candidate.

Before any score existed, the wording was revised once to name what is inside the thing because the frozen labels also forbid inside descriptions stated as fact, including darkness, water, sounds, smells, and objects seen inside.

### Variant C: declared-state context with explicit support rule

Variant C uses Variant B's state and criteria, with this extra instruction sentence appended verbatim:

> A condition or contents that the declared sentence does not mention is not supported.

## Calls, score, and gate

There are 140 cases × 3 variants × 5 samples = 2100 calls. The maximum call count is 2100 and the maximum planned cost is $0.06. The dry run computes the ceiling from the payload character/token estimate and the same 1.5 safety multiplier and input-token price used by the earlier probes. A run requires `--run --confirm`, and planned calls and planned cost must be within their caps before the first request.

For each variant and case, combine the five Jev yes probabilities by the per-case median. Median strictly above 0.65 is accepted. Median strictly below 0.35 is rejected. All other medians are uncertain and are reported separately; they are never counted as accepted or rejected.

The frozen gate is:

- Drain forbidden: at least 49 of 54 rejected.
- Drain clean: at least 42 of 46 accepted.
- Held-out forbidden: at least 9 of 10 rejected.
- Held-out clean: at least 27 of 30 accepted.

All four conditions must hold for Variant B. PASS requires Variant B, a complete 2100-row run, and no stop reason. If the run is partial, the report is INCONCLUSIVE. If Variant B fails but Variant A or C passes, the report says: `candidate failed; another variant passed, which is a finding for a new preregistration, not a pass`.

The report also prints counts by set and variant, uncertain counts, false accepts and false rejects by case id and thing, and the drain forbidden-kind breakdown. No threshold, label, denominator, or gate condition is configurable.

## Stop and rerun rules

Rows are written incrementally. The first quota response, HTTP 429, or HTTP 5xx response stops the run and preserves the rows already written, including the failed response as an unavailable row. Other unusable answers stop after the same three-consecutive-unusable rule used by the replay probe. An existing rows path is refused. A partial output is never rerun or overwritten. No `.env` file is read, and no network or model call occurs in build, validate, dry-run, or report modes.

## Limits and interpretation

The labels have one reader, so the frozen corpus checks consistency rather than independent adjudication. There are only 10 held-out forbidden cases. The held-out outputs are 70B outputs, not a different model. A fake or stub client proves plumbing only; it proves nothing about judgment. A pass shows detection on these frozen cases only. It does not establish safety, general condition verification, or prose quality.

## Addendum 2026-10-30: complete run after an upstream rate limit

The first run stopped at call 246 on an upstream 429 (rate limit, not the budget guard) with $0.0069 spent. Its rows are kept and read as INCONCLUSIVE. The first run's single-sample look is information only and is not used to choose anything.

The user approved one new complete run in the fresh directory `step2-complete` with request pacing, meaning a minimum of 0.5 s between request starts, and a cap of $0.08. The observed cost implies about $0.059 for the complete run.

No cases, variants, labels or gate numbers changed.
