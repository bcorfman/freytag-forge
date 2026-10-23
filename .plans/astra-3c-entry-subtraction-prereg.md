# Preregistration: Stage 7 Scene 3C entry-line subtraction replay (DRAFT, not approved)

Written 2026-10-22 before any billed run. Brandon has not approved this document. Nothing billed runs until he does.
Source: `.plans/chatgpt-3c-after-escape-plan.md`, ranked fix 1 and order-of-work steps 1-3.

## Question
Does removing the shipped line `- Exposure and escape are both immediate under the collapsing operation.` from the Scene 3C narrator prompt change whether the narrator finishes a requested movement to the surface after the escape is complete?

## Free checks (done 2026-10-22, Ringer run `3c-entry-subtraction-free`)
- Variation `bench/variations/stage7-3c-entry-world-only.json`: `k_scene_3c_entry` audience `public` -> `world_only`, nothing else.
- Hermetic tests `tests/test_3c_entry_subtraction.py` (7 passed): the real narrator payload for post-C 3C differs from shipped by exactly that one line; the system payload is unchanged; `scene_3c_entry_known` is still asserted; the reveal universe is unchanged.
- Dry replay `scripts/ringer/stage7/3c_entry_replay_probe.py --dry`: the recorded turn-11 prompt (row `item-facts` of `bench/results/stage7-3c-escape-close-smoke`, command "Continue through the maintenance tunnel to the surface") contains the line once; the subtraction prompt is the control minus that one line; the diff is one removed line, nothing added.
- The Ringer check itself failed once on a `pipefail`/`diff` exit code bug in my check script, not on the worker's output; the items above were re-run by hand.

## Billed design (one Ringer task, no retries, no replacement samples)
Recorded-prompt replay, 12 samples per arm, interleaved control/subtraction, 24 calls, cap 24 Cloudflare calls, no player calls. Both arms send the same recorded system prompt; only the one line differs.

## Read by hand, every reply in full
Does the reply finish Kristin's requested movement to the surface? Does it restart the pumps, gates or rescue? Does it invent a device or place? Does its `item_facts` place Kristin at the surface (item_facts without surface prose does not pass)? Unusable replies count as failures.

## Decision rule (triage only)
Candidate passes if at least 10/12 replies coherently finish the movement and that is at least 3 more than control, with no new pump/gate reset, rescue restart, device invention or grounding failure. A tie or miss stops this candidate. A pass proceeds to a separate post-C continuation screen (12 rows per arm, product capture, semantic ON, no scripted first command, escape close kept in both arms), not to adoption.

## Not covered
Earned endings, D2, whole-game quality, rates.

## Approved (Brandon, 2026-10-22: "yes")
Ringer run `3c-entry-subtraction-replay`, manifest `scripts/ringer/stage7/3c-entry-subtraction-replay.json`, 24 Cloudflare calls, no player calls.

## RESULT (2026-10-22, `bench/results/stage7-3c-entry-subtraction/rows.json`, 24 rows, 0 errors)
Read by hand, every reply. Finished the movement to the surface: control 0/12, subtraction 0/12. Every reply in both arms ends with Kristin still in the maintenance tunnel ("moves forward", "leads Michelle through the tunnel"); none arrives, and every `item_facts` places Kristin at "maintenance tunnel" or omits the place.
Subtraction-only problems: "carries Michelle" 3/12 (two also set Michelle `held_by` Kristin, a person held by a person), "holds the watertight barrier" restart 1/12, "Michelle leads the captives" 3/12. Control had none of the carrying/barrier items.
Rule: pass needed 10/12 and +3 over control. Missed (0/12, +0). Candidate stopped: not shown to matter, and it added grounding failures. The entry line is not the cause of the non-arrival in this prompt; shipped data unchanged. No bundle with C1/A1 (they lost earlier).
Caveat: the recorded prompt already places Kristin in the maintenance tunnel, so this replay shows the narrator does not complete a tunnel-to-surface move in one turn in either arm; it does not test later turns.
