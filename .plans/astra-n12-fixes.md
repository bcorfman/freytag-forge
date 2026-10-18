**The grounded arm still fails the keep rule, but “6 earned versus 2” understates its reveal delivery.** The main causes are screen bookkeeping and clarification handling—not a missing panel-access fact. I inspected only the saved N=12 per arm and ran offline checks. No files changed or live calls made.

**1. Why eligibility differs**

Ranked by affected rows; counts overlap:

| Cause | Rows affected | Classification |
|---|---:|---|
| Eligibility sampled before runtime activation | All 24 first commands; mislabels 6 actual first-command reveals | Screen |
| Players continue pursuing panels or other invented objects | 8 rows: control 4–6, 9, 12; grounded 6, 8, 12 | Writing / generated narration |
| Ambiguous “terminal(s)” triggers clarification | 6 grounded rows: 3, 4, 5, 7, 9, 11 | Engine reference mechanics |
| Clarification answer loses the original search request | Grounded 4, 5, 7, 9 | Screen integration |

There is **no missing bridge or panel prerequisite**:

- `SL-2B-A` has no activation conditions and `earliest_turn: 0`. Its two reveals have `requires: []`.
- `SL-2B-B` requires `janus_evidence`.
- `SL-2B-C` also requires `janus_evidence`, with later pacing.
- `t_2a_2b` depends on `restricted_corridor_access`, not panel discovery or opening.

The current and frozen packages have byte-identical `knowledge.yaml`, `storylet-routes.yaml`, and `pacing.yaml`. See [storylet activation declarations](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/storylet-routes.yaml:1395).

The screen checks eligibility **before** `engine.turn()`. The engine activates storylets inside the turn, before projecting reveal candidates. Consequently, a fresh-state `source_inactive` result does not mean the command cannot earn the reveal. See [screen scoring](/home/bcorfman/dev/freytag-forge/scripts/ringer/stage7/door_continuation.py:67) and [runtime activation](/home/bcorfman/dev/freytag-forge/storygame/runtime/engine.py:1014).

Grounded reps 1, 2, 3, 10, and 11 already commit `a_r1` on command 1. On command 2, it is correctly `already_established`; its sibling is `storylet_spent`.

For grounded reps 4, 5, 7, and 9, command 1 returns:

> Do you mean the archive terminals or the medical terminal?

That return happens **before activation or state mutation**, explaining the empty eligibility list before command 2.

**2. Is “earned” a fair comparison?**

Not as currently reported.

The scorer requires:

```python
earned = len(matched) == 1 and committed == matched
```

Here, `matched` comes from the stale pre-turn eligibility check. It therefore misses every first-command reveal. It also accepts **any** matching reveal, whereas the preregistration names `k_sl_2b_a_r1`.

The saved ledger gives:

| Measure | Control | Grounded |
|---|---:|---:|
| Reported `earned` | 6 | 2 |
| `a_r1` actually committed by command 2 | **7** | **5** |
| `a_r1` committed on command 1 | 1 | 5 |

These are diagnostic recounts, not replacement adoption criteria. Grounded still fails.

I checked the actual `_matches_all` function against every saved command. “Search the terminals for Michelle’s selection file” matches `a_r1` by wording. **“Inspect” and “examine” also match**, through the matcher’s existing synonym class.

For the requested grounded rows:

| Rep | Diagnosis |
|---|---|
| 2 | Command 1 commits `a_r1`. Command 2 repeats Michelle’s search; `a_r1` is already established, and the wording matches no eligible B reveal. |
| 3 | Command 1 commits `a_r1`. Command 2 lexically matches that spent reveal and additionally triggers terminal clarification. |
| 4 | Command 1 lexically matches `a_r1`, but terminal ambiguity stops execution. Command 2 loses the original search intent. |
| 5 | Same clarification failure; “The archive terminals” is submitted alone, without the search request. |
| 6 | Both commands pursue a seam/panel. Neither supplies selection-file evidence. A is eligible on command 2; this is not an eligibility defect. |
| 7 | Command 1 matches `a_r1` by wording but triggers clarification. The standalone answer loses the search intent. |
| 8 | Both commands pursue invented access hardware. No reveal wording match. |
| 9 | “Examine…” matches `a_r1` through existing synonyms. Clarification blocks it; the standalone answer loses the request. |
| 11 | Command 1 commits `a_r1`. Command 2 matches eligible `b_r1`, but terminal clarification prevents execution. |

The screen calls `engine.turn(command)` without forwarding `clarifies`. The runtime explicitly keeps pending clarification context with the caller. Offline, passing the saved original command and saved answer through that supported interface reconstructs an `a_r1`-matching search in **all four** affected rows. That establishes lost intent, not guaranteed counterfactual delivery. See [clarification handling](/home/bcorfman/dev/freytag-forge/storygame/runtime/reference_resolution.py:254).

**3. Why rep 11 matches but remains unearned**

Its second command says “the terminal.” Both archive terminals and the medical terminal are in scope.

Reference resolution returns a clarification before narration or reveal commitment. Thus:

- Eligible: B reveals.
- Exact match: `b_r1`.
- Committed reveals: none.
- Facts changed: none.

There is no additional hidden knowledge prerequisite. The failed condition is **actual commitment after the match**. See [early clarification return](/home/bcorfman/dev/freytag-forge/storygame/runtime/engine.py:212).

**4. Smallest authored change—and the mechanics questions**

A small, supported wording candidate is to use the declared object’s full name in the existing 2B entry sentence.

Old:

> Rows of terminals held the Initiative's selection files - and, somewhere in them, the answers to why Michelle was taken and who helped build the system that chose her.

New:

> The archive terminals held the Initiative's selection files. Those files held answers to why Michelle was taken and who helped build the system that chose her.

Location: [2B `entry_text`](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:450).

**Precedent:** the grounding guide’s concrete-name rule and the earlier 2B entry repair recorded at `62cae8ae`. This replaces vague material with an existing declared name; it introduces no object, alias, narrator rule, or eligibility change. Its effect on player wording remains unproven.

**Screen corrections take priority:** measure the named reveal at the runtime’s actual selection/commit boundary, and preserve clarification context using the existing API. The precedent is the implemented Stage 4 clarification lifecycle in [the active plan](/home/bcorfman/dev/freytag-forge/.plans/implementation_plan.md:430). Neither requires changing shared engine behavior.

**Explicit engine question:** should a search whose file target identifies the archive still require clarification for “terminal”? Current mechanics say yes. Changing that policy would be a separate reference-resolution change; these rows do not justify silently adding an inference or keyword gate.

Keep the screen’s limitations attached: replayed 2A, assumed THINGS selection, fresh 2B state, and disabled semantic fallback. The evidence supports reduced invention, but neither isolates the slotted-face sentence nor establishes hosted success.