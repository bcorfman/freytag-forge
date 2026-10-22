# Follow-up for ChatGPT Desktop: Option A needs two deadline deliveries (N-1 and N-2)

Paste everything below the line into the SAME chat where you gave the Option A answer for N-1 and N-2. It relies on
that conversation and does not repeat the plot beats, YAML or protected-knowledge lists you already have.

---

We applied your Option A edits exactly as written (both `bridge_1c_infiltration_needed` and `bridge_2b_archive_crisis`),
and the story package no longer loads. One of your statements was wrong: you said no edits were needed to
`handoffs.yaml`. Please re-analyze with the facts below.

## What failed

The loader rejects the package with:

`scene 1C bridge-required fact 'architects_strategy_known' has no FactDelivery`

The rule: **every player-visible fact named in a bridge activation, in `all_facts_true` or in `any_of`, must have a
`FactDelivery` (the authored deadline backstop) in that scene.** Only world-only facts are exempt. Neither
`architects_strategy_known` (1C) nor `kristin_was_bait` (2B) has a delivery today. The loader stopped at the first error,
so N-2 is expected to fail the same way (not yet run).

## How the backstop chooses (this affects your answer)

At the deadline the engine delivers the smallest set of missing facts that satisfies the activation. It fills `any_of`
shortfalls **in list order**, skipping facts already true. So:

- N-1: `any_of: [national_detention_network_known, architects_strategy_known]`, `at_least: 1`. With neither known, the
  backstop delivers only `national_detention_network_known`. The new `architects_strategy_known` delivery would never
  fire at the deadline, but the loader still requires it.
- N-2: `any_of: [brandon_janus_role_known, brandon_claimed_reform_motive, michelle_resistance_known, kristin_was_bait]`,
  `at_least: 2`. `kristin_was_bait` is delivered only when it is needed to reach two and the earlier facts are
  already true or already chosen.

## Format of a FactDelivery (existing example)

```yaml
- fact_id: national_detention_network_known
  scene_id: 1C
  source_kind: observation
  source_entity_id: kristin        # must be a participant of the scene
  must_convey:                     # each group needs at least one phrase verbatim in fallback_text
  - [logistics computer]
  - [regional hub, detention network]
  costs: []                        # optional, e.g. {op: assert, fact_id: evidence_gap_..., value: true}
  fallback_text: >-
    The logistics computer shows Kristin that Los Angeles is one regional hub. The detention network spans the country.
  cue_text: A logistics computer hums by the service entrance. It may be worth reading.
```

`cue_text` is one or two sentences about something concrete the player can already see, at a 12th-grade reading level.
It points toward the fact without stating it. Other deliveries in these scenes use costs to record what the backstop
cost the player, for example `evidence_gap_*` facts and a retracted `trust_brandon`.

## What I need from you

1. **Reconsider the recommendation.** Option A now forces two new authored deliveries, one of which is dead code at the
   deadline. Compare: (a) keep A and write the deliveries; (b) Option B for either issue (R2 or R3 also sets the missing
   fact, so the bridge rule stays unchanged and no new delivery is needed); (c) A with the new fact listed first in
   `any_of`, so the backstop would deliver it; (d) accept the forced exit as a known limitation. Pick one per issue and
   say what the player sees at the deadline under it. You may recommend different options for N-1 and N-2.
2. **If any issue stays on A or C, write its `FactDelivery` block**: `fact_id`, `scene_id`, `source_kind`,
   `source_entity_id` (a real participant of that scene), `must_convey` groups, `fallback_text`, `cue_text`, and `costs`
   only if you can justify them. The fallback must say no more than the earned delivery text you already know and must
   keep every protected boundary. Plain words, one idea per sentence.
3. **Ordering table.** For each issue you keep on A or C, list which facts the backstop delivers for each combination of
   already-known facts. Flag any case where the player gets an alternative you did not intend, and give the `any_of`
   order you want.
4. **Wording.** Say whether the scene's `bridge_text` or fallback text needs a change now. Give the minimal replacement,
   or say none.

Answer with the recommendation per issue, the exact YAML to insert, the ordering table, and anything you would check
before we apply it.
