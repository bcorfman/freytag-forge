# Held-out controls: proposal (2026-11-24; all three answered, two controls signed off 2026-11-25)

Part of the [qualification plan](../dark-factory-diagnostic-qualification-plan.md). The owner chose option 2 for the nine inconclusive sign-offs (rebuild controls and defects from new evidence) and asked to see the proposed controls before anything is implemented. **Nothing below has been run or built.**

**Read this when:** you rebuild the held-out set, generate fresh seeded runs for controls, or change what counts as a healthy control.

## Why the old controls failed (sign-off, 2026-11-24)
They were whole three-replicate scene runs labelled healthy as a unit, and each held a real problem a fresh reader found:
- **1C:** replicate 2 stalled and took the costly forced fallback.
- **2A:** a wording gap sent replicate 1 through the missed-window fallback.
- **1B:** the reader flagged a turn-7 exit against `min_turns` 8. Checked on the engine: the default journey leaves 1B at exactly 8 turns since entry, so the floor holds and the reader over-found. The hosted records count turns differently; the cause is not found.

## Proposal
1. **A control is one replicate, not a scene run.** Mechanical screen: earned exit (no forced exit), zero stuck turns, zero guard rejections, zero game breaks, no turn where candidates were offered and none matched. In the saved reports only 1C r1 and r3 (now development), 2B r1 to r3 and 2C r1 to r3 pass, and 2B and 2C are the narration-provenance defect scenes. So held-out controls need fresh runs.
2. **Fresh seeded runs on the shipped guard** (after PR #831 merges and deploys to staging): scenes 1B, 2B, 3A, 3C in that fixed order, three replicates each, about $0.05 per scene at the measured seeded rate, batch cap $0.50, estimate written before the run (calibration table). Some of these scenes have known defects elsewhere; only the replicate has to be clean.
3. **Admission takes two blind readers.** A fresh Opus evaluator writes the answer record for the first mechanically clean replicate of each scene; a second fresh session signs it off (`run_signoff.py`); a control needs `healthy` from both. A first reader that finds a defect makes it a defect candidate, not a control.
4. **Pre-registered selection.** Scenes in the fixed order, stop at the first two controls that sign off, record every failure. Expected 2 to 3 candidates at about 70k tokens each (evaluator plus sign-off); worst case 4 candidates, about 280k.
5. **Old cases become development cases:** 1B, 1C, 2A plus `dev-1C-healthy-r1` and `r3`. They are no longer held out.
6. **Pin the turn-count definition first.** Add the engine's `turns_since_entry` to every exported turn record in `make_case.py` (small Ringer round, hosted-record compatible), so a reader cannot misread a `min_turns` floor as the 1B reader did.

## Defects (same option)
Sketch only. A defect candidate counts only when two blind readers agree on the verdict and on one repair-level criterion ("an acceptable fix must change X"), not on a class label, because the class labels did not reproduce between readers (2B, 3A, 3B).

## Decisions needed from the owner
1. ~~Merge PR #831 first?~~ Done 2026-11-24.
2. ~~Approve the $0.50 cap and the fixed scene order?~~ Approved 2026-11-24 with 2B swapped for 1C (order 1B, 1C, 3A, 3C). Result 2026-11-25: controls `heldout-ctrl-1C-r1` and `heldout-ctrl-3C-r1` signed off healthy by two blind readers; about $0.17 spent.
3. ~~Add `turns_since_entry` to the exported records now (item 6)?~~ Done 2026-11-24 (owner said yes): the hosted harness records the engine clock (round 34d); a clock worked out from records was wrong on hosted 1B and was dropped (round 34c).
