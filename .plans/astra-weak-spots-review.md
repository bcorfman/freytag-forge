**Recommendation:** Try a clearer reading pointer in 1C’s first reveal delivery. Scope `photo` and `photograph` to the photograph item. Leave 1A’s warehouse drift unchanged for now. The first two have close precedents; the warehouse evidence does not yet identify a source line to fix. [Prior pointer fix](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1326), [alias precedent](/home/bcorfman/dev/freytag-forge/.plans/design-review-implementation.md:174), [warehouse evidence](/home/bcorfman/dev/freytag-forge/.plans/chatgpt-weak-spots-prompt.md:47)

This is a read-only review. I changed no files and made no billed calls. The command scores below are manual source-based scores, not executed tests.

**1C: the player follows the route, but the reveal requires reading evidence**

The strongest diagnosis is a mismatch between the player’s immediate goal and the required action:

- The opening explicitly says they are “looking for a way into whatever lay below.” Scene 1C.1 also sends them searching for a route into the service level. Those lines support movement. [plot.md:255](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:255), [plot.md:283](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:283)
- The `a_r1` delivery points out people passing below. It does not say Kristin can already read their numbers from the shaft. The cue and scene frame do say the numbers are visible, so they point toward observation rather than descent. [knowledge.yaml:838](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:838), [handoffs.yaml:84](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/handoffs.yaml:84), [knowledge.yaml:256](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:256)
- Scene 1C.2 places the discovery at the observation shaft. It permits copying the numbers from that view. Kristin’s wish to enter comes afterward, and Brandon stops her. The intended event is therefore observation before further entry. [plot.md:291](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:291)

My inference is that “below” and the opening’s search for entry can outweigh the observation cue. That is plausible for a human trying to reach Michelle. I cannot estimate how often humans would do this from six model-player runs. The supplied commands demonstrate the model-player behavior, not human incidence. [Recorded evidence](/home/bcorfman/dev/freytag-forge/.plans/chatgpt-weak-spots-prompt.md:30)

There is also a useful correction to the brief: the matcher expands closed synonym classes. For example, `inspect`, `examine`, `search`, and `look` can satisfy the same inspection group. These misses are mostly missing objects, not missing verbs. [candidate_matcher.py:42](/home/bcorfman/dev/freytag-forge/storygame/runtime/candidate_matcher.py:42), [candidate_matcher.py:137](/home/bcorfman/dev/freytag-forge/storygame/runtime/candidate_matcher.py:137)

For the table:

- `b_r1`: **V** = inspection/comparison/recording verb; **O** = prisoners, uniforms, or identification numbers; **N** = records or identification numbers.
- `b_r2`: **V** = search/inspection verb; **M** = Michelle; **L** = processing line, processing area, or observation shaft.

These are the current groups, including synonym expansion. Assume `facility_proof` is true and neither B reveal has been earned. [b_r1](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:872), [b_r2](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:903)

| Command | Missing `b_r1` groups | Missing `b_r2` groups | Exact verdict |
|---|---|---|---|
| Inspect the observation shaft and look for a way down into the processing area. | O, N | M | None |
| Examine the locked stairs and the surrounding service level for a way to unlock or bypass them. | O, N | M, L | None |
| Climb down the ladder from the observation shaft to the service level. | V, O, N | V, M | None |
| Inspect the service level for a safe route toward the processing line and any signs of the missing people. | O, N | M | None |
| Stay hidden and follow the processing line to see where the restrained people are being taken. | V, O, N | V, M | None |
| Open the ajar ventilation grille and slip through it with Brandon before the guards reach the service level. | V, O, N | V, M, L | None |
| Inspect the observation shaft. | O, N | M | None |
| Examine the processing line. | O, N | M | None |
| Find an entrance to the processing line. | V, O, N | M | None |
| Enter the biohazard containment zone. | V, O, N | V, M, L | None |
| Use the transit token on the access panel. | V, O, N | V, M, L | None |

None of these completes `a_r1` either. The ventilation command supplies its object but lacks an inspection verb. The other commands lack its activity objects. The token command supplies `a_r2`’s verb and token, but “access panel” does not satisfy its service-entrance group. [A reveal groups](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:811)

The semantic fallback should not generally rescue these commands. It asks whether the command performs the **whole** authored action. Finding stairs, following people, or inspecting a shaft does not compare records, read numbers, or specifically search for Michelle. Treating those actions as enough would change what earns the reveal. Actual fallback execution remains unknown without the turn telemetry: configuration, the call budget, and the shortlist can also prevent a match. [Semantic question](/home/bcorfman/dev/freytag-forge/storygame/runtime/jev_questions.py:60), [fallback gates](/home/bcorfman/dev/freytag-forge/storygame/runtime/cloudflare.py:431)

**Rank 1 candidate: replace the shared closing pointer in the two A deliveries.**

In [knowledge.yaml:838](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:838) and [knowledge.yaml:871](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:871), replace this exact final sentence:

```text
The observation shaft overlooks the processing line, where people in uniforms pass below.
```

with:

```text
The observation shaft overlooks the processing line. Kristin can read the identification numbers on the uniforms below.
```

This is one pointer change applied to both alternative first reveals. It changes player-visible delivery text. It preserves the opening, bridge, events, prerequisites, effects, pacing, and matcher groups.

The technique is the earlier 2A fix that put the next actionable step into the preceding reveal’s delivery. The 1C shaft-frame probe also supports naming what can be seen from the shaft. Neither precedent proves this particular wording will work. [2A pointer precedent](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1326), [1C probe](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1291)

The new pointer names only the view and numbers already exposed by the current cue. It does not name sedated prisoners, confirm their identity, or introduce a later location. The shaft is already a declared place. This supports its safety on inspection; composed-turn validation is still required. [Existing cue](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/handoffs.yaml:84), [shaft declaration](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/world.yaml:80), [leak-review rule](/home/bcorfman/dev/freytag-forge/docs/world-model-grounding.md:140)

The main risk is behavioral: players may still descend, or may follow a more explicit instruction without understanding the scene. No new exact-match ties arise because no evidence group changes.

These controls show that the proposed pointer invites an existing unique action:

| Command | Expected result | Manual matcher verdict |
|---|---|---|
| Read the identification numbers on the uniforms below. | `b_r1` | Unique `b_r1`; all three groups hit |
| Copy the ID numbers. | `b_r1` | Unique `b_r1`; numbers satisfy O and N |
| Compare the prisoners with missing-person records. | `b_r1` | Unique `b_r1` |
| Search the processing line for Michelle. | `b_r2` | Unique `b_r2`; `b_r1` lacks O and N |
| Inspect the uniforms. | None | `b_r1` lacks N; `b_r2` lacks M and L |
| Check the ID numbers and look for Michelle in the processing line. | None | Both B reveals match; tie |

The four positive commands lack `a_r1`’s activity objects and `a_r2`’s token/entrance combination. The mixed command illustrates an existing tie; the pointer does not invite it. [A groups](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:814), [B groups](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:875), [tie rule](/home/bcorfman/dev/freytag-forge/storygame/runtime/candidate_matcher.py:100)

**Cheapest offline check:** score these commands with the real matcher. Then validate each changed A delivery in a 1C state where `facility_proof` has just been earned but `captives_confirmed_alive` remains false. Use the state-exact fixture pattern, leak tests, and package checks. A text-only matcher pass cannot establish delivery safety. [Fixture helpers](/home/bcorfman/dev/freytag-forge/tests/test_design_review_fixtures.py:26), [testing boundaries](/home/bcorfman/dev/freytag-forge/docs/testing-runbook.md:58)

I would leave the entry and plot wording alone in the first experiment. Searching for access is a real plot event. The proposed delivery supplies the next step after that search succeeds. I would also leave the matcher unchanged: widening it to accept generic route-finding would award evidence the command never sought. [Plot sequence](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:283), [required action](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:874)

**1A phone: a common noun is guarded as a particular item**

The photograph declaration gives `photo` and `photograph` global aliases. The physical item is placed under the park bench in 1B. That explains why ordinary phone narration can collide with the unavailable item in 1A. [world.yaml:213](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/world.yaml:213), [plot.md:180](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:180)

`Photograph` has the same declaration problem as `photo`. `Picture` does not have that same global alias declaration. It occurs in the photograph reveals’ `action_evidence`; action evidence is distinct from the guard inventory. Longer phrases containing “picture” still need their own checks. [knowledge.yaml:634](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:634), [guard inventory](/home/bcorfman/dev/freytag-forge/scripts/disclosure_matrix.py:70)

**Rank 1 candidate: scope both common aliases.**

Replace the item block at [world.yaml:213](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/world.yaml:213) with:

```yaml
- id: michelle_photograph
  name: Michelle's photograph
  scoped_aliases: [photograph, photo]
```

This exactly follows the medical-records fix and the grounding guide. The distinctive name stays guarded. The common aliases resolve while the item is placed and in scope. [Medical-records fix](/home/bcorfman/dev/freytag-forge/.plans/design-review-implementation.md:174), [grounding guide](/home/bcorfman/dev/freytag-forge/docs/world-model-grounding.md:74), [scoped-alias tests](/home/bcorfman/dev/freytag-forge/tests/test_scoped_aliases.py:41)

The principal risk is 1B reference handling. Scoped aliases do not serve every recall path that global aliases do. Existing action-evidence matches remain intact, but inspect/show/follow-up interactions should still be checked in 1B. Also, a 1A sentence containing the full name “Michelle’s photograph” can still be rejected. This change deliberately addresses the common nouns only. [Known scoped-alias limitation](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1336), [full-name guard test](/home/bcorfman/dev/freytag-forge/tests/test_scoped_aliases.py:68)

**Cheapest offline check:**

- Compare disclosure matrices before and after. Expect only the two alias classifications to change.
- Validate fixed sentences containing `photo`, `photograph`, `picture`, and `Michelle's photograph` across all nine scenes.
- Confirm 1B resolution for both scoped aliases.
- Run `tests/test_scoped_aliases.py`, `tests/test_leak_terms.py`, `tests/test_design_review_fixtures.py`, and `tests/test_narration_corpus.py`.

The matrix exposes guard ownership; the corpus protects previously accepted narration. The corpus uses late-scene states, so it does not replace the early-1A checks. [Matrix inventory](/home/bcorfman/dev/freytag-forge/scripts/disclosure_matrix.py:70), [corpus state construction](/home/bcorfman/dev/freytag-forge/tests/test_narration_corpus.py:29)

Leave `picture` unchanged. Adding an alias without an evidenced resolution failure would expand this fix unnecessarily.

**1A warehouse drift: a recovery concern, not yet a diagnosed authoring defect**

The run shows a real failure to recover the intended scene. It does not show that accepting an unauthored place is itself forbidden. The world model explicitly supports new places and things; W9 rejects a closed list of allowed objects. [Grounding guide](/home/bcorfman/dev/freytag-forge/docs/world-model-grounding.md:56), [W9 decision](/home/bcorfman/dev/freytag-forge/.plans/world-model.md:5382)

The current 1A cue already points to the marked drawer and its gap. The distracting laptop sentence was previously removed. There is no remaining warehouse-directed source line identified in the supplied evidence. [Current cue](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/handoffs.yaml:13), [subtractive precedent](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1328)

The escalation mechanism is proven to deliver a repeated pointer. Its three successful 1A recovery runs used a scripted pointer-following command. They did not prove that a blind player would follow it. [Escalation behavior](/home/bcorfman/dev/freytag-forge/.plans/design-review-implementation.md:187), [recovery limitation](/home/bcorfman/dev/freytag-forge/.plans/design-review-implementation.md:201)

**Recommendation: no change yet.** I would not add a narrator restriction or draft stronger escalation text from this one run. First inspect the narration that introduced the warehouse, the actual pointer turn, and the following player command. The project’s scene-fixing workflow calls for identifying that source before changing it. [scene-fixing-guide.md:16](/home/bcorfman/dev/freytag-forge/docs/scene-fixing-guide.md:16)

**Smallest useful live tests—proposed, not run**

| Proposal | Test | Count and decision |
|---|---|---|
| 1C delivery pointer | Hosted blind-player 1A–1C sequence, using the existing L2 harness. Match starting state and player profile across baseline and treatment. | Use **12 paired raw-profile starts** for the primary comparison. Count B reveals earned before turn 8, play exits, forced exits, route detours, and rejections. Drop the proposal if it produces no improvement in early B reveals or forced exits, or introduces disclosure failures. Add three canonical runs only as a smoke check. |
| Phone aliases | Fixed “Examine Michelle’s phone.” prompt through the local narration bench. Validate generated prose against both package versions. Follow with linked hosted 1A–1B smoke runs. | Use **12 samples per arm** for the fixed-prompt probe. Count alias-only rejections separately from real disclosures. Drop or revise if ordinary `photo`/`photograph` still rejects, the full-name guard weakens, or 1B reference handling regresses. Three linked runs check integration only. |
| Warehouse drift | No new billed test yet. Inspect the saved failing sequence. | If it identifies a reproducible prompt conflict, use **10–15 samples per arm** to probe that conflict before proposing a change. |

The hosted wrapper accepts one to three replicates per invocation, so twelve requires four batches of three per arm. The old shaft probe tests narrator framing, not whether a player follows an appended delivery; rerunning it unchanged would answer the wrong question here. [Hosted wrapper](/home/bcorfman/dev/freytag-forge/scripts/ringer/affordance/scene-affordance-l2-all-live.sh:90), [shaft-probe scope](/home/bcorfman/dev/freytag-forge/scripts/ringer/affordance/1c_shaft_probe.py:1), [local bench](/home/bcorfman/dev/freytag-forge/docs/testing-runbook.md:91), [required sample rules](/home/bcorfman/dev/freytag-forge/.plans/chatgpt-weak-spots-prompt.md:65)

Offline scoring can establish exact matches, ties, eligibility, alias ownership, and acceptance of particular sentences. It cannot establish whether the narrator invents a compelling detour, whether the player follows a pointer, or how humans respond. Those remain live behavioral questions. [Grounding guide’s verification limit](/home/bcorfman/dev/freytag-forge/docs/world-model-grounding.md:251)