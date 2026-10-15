**1. Verdict**

The plan supports continued repairs, but not an architectural adoption decision. Its strongest evidence concerns specific failure mechanisms; its weakest evidence concerns reliability and generalization. The biggest risk is treating a green traversal or successful classifier screen as proof that player actions produce correct, earned outcomes. The cap diagnosis is substantially correct, but its fix grants broader authority than its description acknowledges. The retry also conflicts with the documented shared recovery budget.

Labels below: **V** = verified in files; **N** = not verifiable from available evidence; **I** = inference or recommendation.

**2. Findings, ordered by severity**

| # | Severity | Claim or decision | What the evidence shows | Evidence | Label |
|---|---|---|---|---|---|
| 1 | Major | Cap exception represents an exact authored match | Semantic-model selections receive the same marker, including after an exact-match tie. The resolver therefore accepts more than the stated exact-match exception. | [cloudflare.py:341](/home/bcorfman/dev/freytag-forge/storygame/runtime/cloudflare.py:341), [cloudflare.py:499](/home/bcorfman/dev/freytag-forge/storygame/runtime/cloudflare.py:499), [validation.py:208](/home/bcorfman/dev/freytag-forge/storygame/runtime/validation.py:208) | V |
| 2 | Major | One guard retry is a bounded recovery | Each engine attempt can independently invoke provider recovery and transient retries. There is no shared two-request ceiling. | [engine.py:191](/home/bcorfman/dev/freytag-forge/storygame/runtime/engine.py:191), [cloudflare.py:1196](/home/bcorfman/dev/freytag-forge/storygame/runtime/cloudflare.py:1196), [contributor-guide.md:54](/home/bcorfman/dev/freytag-forge/docs/contributor-guide.md:54) | V |
| 3 | Major | Retry preserves narrator information boundaries | It sends the complete rejection message, including protected vocabulary, back into the narrator prompt. This conflicts with the PRD’s narrator boundary. | [cloudflare.py:306](/home/bcorfman/dev/freytag-forge/storygame/runtime/cloudflare.py:306), [narration_safety.py:263](/home/bcorfman/dev/freytag-forge/storygame/runtime/narration_safety.py:263), [PRD.md:18](/home/bcorfman/dev/freytag-forge/docs/PRD.md:18) | V |
| 4 | Major | Phase 3 provides a comparison-ready harness | The current arm reports empty state and hard-codes one request. It cannot yet measure the proposed state or total-cost comparison faithfully. | [runner.py:57](/home/bcorfman/dev/freytag-forge/bench/pipeline_eval/runner.py:57) | V |
| 5 | Major | Later refusal work followed frozen rules | The mixed freeze permitted tuning only if `names_other_action` missed. The next freeze retrospectively describes permission to tune both classifiers. Default adoption later drops another gate explicitly. | [mixed freeze:26](/home/bcorfman/dev/freytag-forge/.plans/astra-engine-refusal-mixed-freeze.md:26), [tuning freeze:3](/home/bcorfman/dev/freytag-forge/.plans/astra-engine-refusal-tuning-freeze.md:3), [plan:270](/home/bcorfman/dev/freytag-forge/.plans/astra-implementation-plan.md:270) | V |
| 6 | Major | Billed-run checks establish experimental validity | The shared checker counts old capture messages, reporting zero refusals even for the successful engine-refusal arm. It does not enforce treatment activation or expected turn counts. | [checker:25](/home/bcorfman/dev/freytag-forge/scripts/ringer/astra/p4-refusal-measure-check.sh:25), [saved output:49](/home/bcorfman/dev/ringer-work/astra-p4-2-measure/fe4-full-fe4eng.out:49) | V |
| 7 | Minor | Marker control totals are internally consistent | Listed counts total **3/24, 7/24, 1/24**, not **2/24, 4/24, 1/24**, if “stuck, then opens” counts as stated. Rejection of all variants still follows. | [plan:185](/home/bcorfman/dev/freytag-forge/.plans/astra-implementation-plan.md:185), [saved control:3](/home/bcorfman/dev/ringer-work/astra-p4-2-measure/wv-ctl-wva.out:3) | V |
| 8 | Minor | Plan is an accurate operational handoff | Its opening status and several “not merged” entries contradict later entries; the reverted test still repeats the disproved established-reveal diagnosis. | [plan:4](/home/bcorfman/dev/freytag-forge/.plans/astra-implementation-plan.md:4), [test_2c_assess_verbs.py:33](/home/bcorfman/dev/freytag-forge/tests/test_2c_assess_verbs.py:33) | V |

**3. Answers to A–D**

**A. Conclusions**

1. **Keep the 1C pointer — partly supported.** **V:** Re-scoring saved batches reproduces baseline 10/12 play exits, treatment 11/12 twice, and subsequent safety builds 11/12 and 12/12. Treatment B reveals generally occur earlier. The scorer counts grounding IDs and recorded exit causes ([weak1c_compare.py:20](/home/bcorfman/dev/freytag-forge/scripts/ringer/playthrough-quality/weak1c_compare.py:20)). **I:** Keeping a small, intelligible authoring repair is reasonable; claiming demonstrated improvement is not. One fewer forced exit, repeated runs on the same starts, intervening changes, and no paired effect analysis leave causality weak. “No harm” is also stronger than these samples establish.

2. **“Renarrate removes the false claim” — not supported literally.** **V:** Its own cue-restored result includes one successful-move claim and three contradictions; later saved replies show prohibited movement surviving when capture misses it ([plan:138](/home/bcorfman/dev/freytag-forge/.plans/astra-implementation-plan.md:138), [saved replies:6](/home/bcorfman/dev/ringer-work/astra-p4-2-measure/fr-full-frren.out:6)).  
   **“Engine-owned refusal meets its bars” — supported as a screen.** I inspected all engine-arm replies for the 16-command, mixed, and tuning experiments. The tuning records support 4/4 mixed, 4/4 simple refusals, and 4/4 narrated controls, with no narrator prompt on refused turns ([example record:16](/home/bcorfman/dev/ringer-work/astra-p4-2-measure/fe4-full-fe4eng/fe4eng/k1/all-turn-records.json:16)). **I:** This establishes observed behavior, not classifier reliability. One scene, one reader, partial blinding, and four controls cannot justify a general false-refusal rate.

3. **Marker not adopted — supported.** **V:** Each variant has at least one control failure, so none qualifies under the frozen zero-over-refusal rule; H2 need not run ([plan:170](/home/bcorfman/dev/freytag-forge/.plans/astra-implementation-plan.md:170)). Correct the arithmetic. **I:** “These variants failed” is justified; “wording is not the lever” is too general.

4. **`@spine` passes — partly supported, with narrow meaning.** **V:** It submits scene-specific commands and asserts valid scene names and arrival at 3C. It does not assert reveal ownership, complete scene order, ending completion, refusal quality, or acceptable delivery counts. `dead_end` merely tests whether the scene list is empty ([scene-runtime.spec.js:81](/home/bcorfman/dev/freytag-forge/frontend/e2e/scene-runtime.spec.js:81)). The saved artifact confirms 95 turns, four fallback turns, twelve misses, and zero guard retries ([artifact:486](/home/bcorfman/dev/freytag-forge/artifacts/e2e-spine.json:486)).  
   Thus: it supports successful scripted traversal after the journey/vocabulary fixes; it does not establish engine-refusal quality, retry rescue rate, or that `assess` earned its reveal. The cited `813d0751` run **predates the cap-fix commit `7345632d`**, so it cannot validate that fix.

5. **Turn-48 diagnosis — partly supported overall; mechanism supported.** **V:** The projector computes an eligible universe and caps only `candidates` at four. The provider matches the full universe. The regression reproduces a beyond-cap handoff using existing wording. A delivered cue is not an established canonical fact ([knowledge.py:194](/home/bcorfman/dev/freytag-forge/storygame/runtime/knowledge.py:194), [test:38](/home/bcorfman/dev/freytag-forge/tests/test_established_reveal_match.py:38)). The correction properly abandons the original diagnosis.

   The resolver change is small and retains universe membership, grounding, content, and effect validation. But:
   - **V:** Ordinary narrator JSON cannot directly set the marker; model selections are stripped on handoff turns ([cloudflare.py:1708](/home/bcorfman/dev/freytag-forge/storygame/runtime/cloudflare.py:1708)).
   - **V:** A semantic-model answer can obtain it: one shortlisted match becomes `AuthoredHandoff`, then receives the same beyond-cap privilege. The shortlist can contain six candidates.
   - **V:** Exact ties also enter semantic fallback. A single semantic answer can therefore resolve a tie that the PRD says commits nothing.
   - **V:** Failed turns restore runtime state without clearing provider `authored_handoff`. Ordinary subsequent prompt assembly overwrites it, and opening clears it. **I:** I found retained stale state, but no demonstrated stale-marker acceptance on the normal sequential path. Reuse, early failures, and custom subclasses remain untested.
   
   **I:** Correct for the exact-match case; insufficiently specified and tested as a trust-boundary change.

**B. Process**

1. **V:** The `assess` test only matches YAML evidence groups; it never executes projection, composition, eligibility, or commit ([test:17](/home/bcorfman/dev/freytag-forge/tests/test_2c_assess_verbs.py:17)). **I:** A stubbed-provider engine turn at the relevant 2C state, including a fifth eligible candidate, would have caught the defect before merge. Extend the existing journey/pacing coverage with that boundary. Disclosure and leakage matrices check vocabulary safety, not selection-to-commit correctness.

2. **V:** Most entries explicitly limit their claims. Exceptions include “removes the false claim,” the estimated 40% combined-arm saving without measuring the combination, and treating a screen as sufficient for default adoption ([plan:157](/home/bcorfman/dev/freytag-forge/.plans/astra-implementation-plan.md:157), [plan:270](/home/bcorfman/dev/freytag-forge/.plans/astra-implementation-plan.md:270)). **I:** Near-identical repeats do not replace independent command families or varied states.

3. **V:** Initial engine-refusal bars and fresh commands are documented; mixed and tuning stages retain their numerical bars. However, the tuning permission changed after two classifiers failed, and the second-package/default gate was subsequently waived. These are disclosed policy changes, not strict adherence to the original preregistration. **N:** The files alone do not prove no earlier exposure to the held-out commands.

4. **V/I:** There is a systematic preflight gap: checks frequently establish “command ran/file exists,” leaving treatment activation, completeness, scoring validity, and provenance to manual inspection. The incorrect zero-refusal summary is a current example, not merely historical bad luck.

**C. Scope and ordering**

1. **I:** Phase 5 remains a reasonable question, but building C now is premature. The strongest argument for cutting it is that several observed failures have specific authoring or boundary fixes, while the comparison harness cannot yet measure the proposed advantage. The plan’s keep/drop conditions require held-out gains without increased false reveals, inventions, or refusal burden ([plan:294](/home/bcorfman/dev/freytag-forge/.plans/astra-implementation-plan.md:294)). Those conditions lack numerical margins and cannot support a reliability decision with the present samples.

2. **I — ranking by value/cost:**
   1. Repair the third 2C spine command’s mismatch with the authored reading action; first verify actual semantic-path behavior.
   2. Re-add `assess` to C-R2 only with the full selection-to-commit regression.
   3. Measure guard-retry rescue rate on known rejection cases after fixing its budget.
   4. Phase 4.3: narrowly test recent-cue reference resolution.
   5. Phase 4.4: first reproduce concealment/discovery confusion before implementing.
   6. Leave `hideout` unchanged until an actual failure exists.
   7. Keep `renarrate` off; stop further adoption work on its current evidence.

   The D-R1 contract says “decodes or reads”; absence of `follow` alone does not justify awarding that reveal ([knowledge.yaml:1706](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:1706)).

3. **I:** Repeating uninformative phone probes, pursuing `renarrate` adoption, or widening verbs solely to green the spine would close checklist items without demonstrated player benefit. Recent-reference work has an evidenced player problem, but its record must remain a bounded projection of accepted material, consistent with facts as truth and the PRD’s transcript-memory exclusion.

**D. Project rules**

**V:** Besides findings 1–3:

- `isinstance(CloudflareTurnProvider)` preserves story independence but couples shared runtime to a concrete adapter; `getattr(note_rejection)` also conflicts with the explicit-Protocol guidance ([engine.py:198](/home/bcorfman/dev/freytag-forge/storygame/runtime/engine.py:198), [contributor-guide.md:64](/home/bcorfman/dev/freytag-forge/docs/contributor-guide.md:64)).
- The billed refusal wrapper uses `--confirm`, but its direct Jev path has no per-endpoint budget guard and swallows request errors. Worker protection does not cover this separate endpoint ([wrapper:13](/home/bcorfman/dev/freytag-forge/scripts/ringer/astra/p4-refusal-measure-check.sh:13), [jev_use.py:20](/home/bcorfman/dev/freytag-forge/bench/jev_use.py:20)); this conflicts with the plan’s own guard-every-endpoint rule.
- The runbook still says rejected narration turns are never retried ([testing-runbook.md:325](/home/bcorfman/dev/freytag-forge/docs/testing-runbook.md:325)). Update that entry in place; the runbook has otherwise avoided becoming a results log.
- The inspected regression tests stub transport, and the autouse fixture blocks urllib and Cloudflare transport calls ([conftest.py:476](/home/bcorfman/dev/freytag-forge/tests/conftest.py:476)). No hermeticity violation found there.
- No story-specific branch or fixed command table was found in these changes. Exact authored handoffs are explicitly permitted by the PRD; their existence is not itself an LLM-proposal-first violation.

**4. What is sound**

**V:** The cap/universe distinction; retaining canonical facts over cue bookkeeping; stripping narrator-owned selections on authored handoffs; separating guard-retry telemetry from provider recovery; rejecting all marker variants; and recording the mixed-refusal failures rather than averaging them away.

**5. Recommended next three actions**

1. **Resolve handoff authority and tie behavior.** Cheapest confirmation: hermetic cases for exact beyond-cap success, semantic beyond-cap selection, exact ties, forged JSON, and provider reuse after rejection.
2. **Unify recovery accounting and sanitize retry feedback.** Cheapest confirmation: scripted malformed/transient/guard-failure sequences asserting total requests, rollback, and protected prompt content.
3. **Repair evidence gates before further architecture spending.** Require treatment activation, complete scheduled cases, correct telemetry, and SHA-bound artifacts; fix Phase 3’s empty-state/one-request observations. Then measure known failures rather than rerunning an uninformative spine.

**6. What I could not assess**

**N:** Independent human agreement, human-player benefit, cross-story reliability, every historical deployment identity, and the exact original turn-48 canonical snapshot were not established. The available spine artifact lacks build identity; the regression reconstructs the relevant mechanism rather than replaying the exact original command and snapshot. I inspected code and saved artifacts and re-scored existing batches; I did not run tests, deploy, or make billed calls.