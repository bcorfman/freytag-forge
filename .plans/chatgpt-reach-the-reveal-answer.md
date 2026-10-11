# Reach-the-reveal review

Status: diagnosis and proposals only, 2026-10-11. No story or runtime changes applied. No billed calls made. Offline checks used HEAD `75142a719e3e155682ed41d1b8de5fb1b63332d7`; the reviewed story data, matcher, engine and Cloudflare provider have no diff from `1c10272f`.

**2A — the supervisor step, not the credentials step.**
In [latest r2](../../ringer-work/l2-1c10272f/e2e-blind-player-r2.json), 2A t4 prepares the forms and t5 reaches the perimeter.
T6 presents forms; it never explains the inspection. Neither corridor-access reveal matches t6–t11.
T6 narration nevertheless grants passage; t7–t10 follow invented doors and another checkpoint.
The t5 delivery names the supervisor's question but gives no explicit next action; there is no `restricted_corridor_access` cue in `handoffs.yaml`.
Contrast [r1](../../ringer-work/l2-1c10272f/e2e-blind-player-r1.json) t4 and [r3](../../ringer-work/l2-1c10272f/e2e-blind-player-r3.json) t8: both explain the unscheduled inspection and earn `k_sl_2a_c_r1`.
Add a next-step sentence to the perimeter delivery. Do not make presenting forms or entering any door grant corridor access.
This exact latest failure has one instance; earlier 2A timers include different, already-fixed wording gaps ([plan](scene-affordance-e2e.md), entries at lines 237–245).
The [r2 prompts](../../ringer-work/l2-1c10272f/e2e-blind-player-prompts-r2.json), t5–t11, are name-matching prompts, so a missing narrator instruction is not established.

**2C — the verb gap is fixed offline; returning to the files is still unproven.**
The [80f5c64c record](scene-affordance-e2e.md:1294) describes two timer runs: retrieve/take/use did not earn the evidence step; r1 then followed transfer orders.
Those three phrasings now match `k_sl_2c_c_r1`, with `janus_evidence` required. No further verb patch is justified by those commands.
In latest r1/r2/r3, 2C t1 earns the evidence step; all then try Michelle's message at t2 and follow the route marker at t4 ([r1](../../ringer-work/l2-1c10272f/e2e-blind-player-r1.json), [r2](../../ringer-work/l2-1c10272f/e2e-blind-player-r2.json), [r3](../../ringer-work/l2-1c10272f/e2e-blind-player-r3.json)).
None tests recovery after missing the file step. R1's Echelon-file command uses the existing semantic fallback, not the exact matcher.
A delivered cue never repeats in the same scene. `nudge_after_turns: 9` does not schedule a reminder; the runtime does not read it.
The remaining plausible gap is attention: the frame names transfer orders and the maintenance network, while the actionable copied-file cue is one-shot.
Probe the existing sentence “Kristin can check the copied files.” in the scene frame. Do not add bare “files” or “drive” without evidence.
Keep the transmission consequences and Rebecca's route behind their existing reveals; the proposed frame says only that the copies can be checked.

**1A — plain “drawer” already works; the remaining concern is redirection.**
Latest [r1](../../ringer-work/l2-1c10272f/e2e-blind-player-r1.json), 1A t1–t2, uses “Open the drawer.” then “Examine the gap beneath the drawer.”; both match directly.
Latest [r2](../../ringer-work/l2-1c10272f/e2e-blind-player-r2.json), t2–t3, opens the drawer then reaches beneath it; the second command uses the existing semantic fallback.
Older [41240bb r2](../../ringer-work/l2-41240bb/e2e-blind-player-r2.md), t2–t3, **does touch the drawer** before fetching the laptop at t4 and chasing invented email at t6–t12.
Its [t2 narrator prompt](../../ringer-work/l2-41240bb/e2e-blind-player-prompts-r2.json) gives the drawer's contents but no gap line. PR 577's separate opening/initials handoff now supplies that line.
All three latest runs find the card. This older miss does not prove that PR 577 still fails on the same path.
Remove the laptop sentence from the pre-card cue; the card delivery already supplies it. Probe the public gap description in the frame if the player still drifts.
Keep the card hidden, keep its fact-controlled reveal, and retain the opening handoff. Opening the drawer must not itself reveal the card.
“Search the drawer.” and “Search the KMS drawer.” have the same exact-matcher result: neither; both can use the existing fallback. No KMS qualifier is required.

**Ranked fixes — expected benefit, not measured gains**

1. **2A: strengthen the perimeter delivery.** One short, local pointer targets the only latest timer. It preserves the existing action and secrecy boundary. This uses the established delivery-pointer technique, not a new rule.
2. **1A: remove the premature laptop pointer.** One deletion removes a competing destination. The old r2 t4–t12 detour supports testing it, but the latest runs show no gain left to demonstrate. Keep PR 577's proven handoff unchanged ([plan](scene-affordance-e2e.md:1260), opening t2 followed by card t3–t4 in its nine-run check).
3. **Shared 1A/2C probe: put the first-step affordance in the scene frame.** This uses the successful 1C shaft-frame technique ([plan](scene-affordance-e2e.md:1264)); it does not add repeating-cue machinery. The concrete gap/file sentences are unmeasured in these scenes. A frame gives the narrator material; it does not guarantee a player-visible reminder.

No numeric “exits gained / cost” estimate is defensible from these samples. The ranking weighs one latest 2A failure against no latest 1A/2C failures. I checked the W decisions, the “Brandon chose” records in [world-model.md](world-model.md), the [grounding guide](../docs/world-model-grounding.md), and the earlier scene fixes. W7 keeps hidden-item disclosure fact-controlled; W9 already gives drawer contents and rejects a closed list banning every invented object. Neither supports adding a new container restriction here.

**Paste-ready data**

Replace only `k_sl_2a_e_r1.delivery_text` in `knowledge.yaml`:

```yaml
delivery_text: >-
  Kristin and Brandon are at the facility perimeter. Their false identities
  pass the first security checks. A supervisor questions why their inspection
  was not scheduled. Kristin can explain the unscheduled inspection to the
  supervisor.
```

Replace only the `continuity_initiative_known` delivery's `cue_text` in `handoffs.yaml`:

```yaml
cue_text: >-
  Kristin's initials, KMS, are carved into a drawer of Michelle's workstation.
  The drawer rides high in its frame. A thin gap beneath its lower edge is wide
  enough for Kristin's fingers.
```

For the **frame probe**, append these sentences to the existing `scene_frames` situations in `knowledge.yaml`. These are additions to existing scalar fields, not new YAML keys or entries:

```text
1A: The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers.
2C: Kristin can check the copied files.
```

No `action_evidence`, `requires`, leak terms, facts, placements or timer changes are proposed. “KMS” remains an inscription in the fiction, not a required player word. Suggested player commands are “Open the drawer.” and “Search under the drawer.” The card's existing delivery still points to the laptop after discovery.

**Exact cue behavior**

[`RuntimeEngine._activate_pacing`](../storygame/runtime/engine.py:345) stages at most one eligible, missing cue. It preserves an already-staged cue while valid. Otherwise `_ranked_cue_fact_ids` ranks missing bridge/resolution deliveries by eligible source windows, excluding pacing-produced facts. `_cue_reveal_available` checks prerequisites and rejects spent/already-established reveals; delivery costs also count when finding the associated reveal (important for the 1A card).

There is no initial nudge wait. A cue can be staged on turn 1. The Cloudflare provider appends it verbatim after ordinary prose, except when it composes an authored reveal handoff instead. The engine marks it delivered after an accepted same-scene turn with neither an authored handoff nor projected deadline deliveries. Rejection restores the snapshot. A handoff does not consume the cue; it may appear on a later ordinary turn if still needed. Scene changes strip the outgoing cue rather than showing it in the next scene. Scene entry resets cue bookkeeping.

Once its fact ID is in `delivered_cue_ids`, it cannot be selected again in that scene. Thus a player who missed the cue can receive another story-authored pointer, but **not a repeat from this cue mechanism**. The 2C order deliveries already end “The copied files lie close at hand”; they are a conditional second pointer, not a periodic reminder. The t3 purge event and t8 transfer event concern danger, not checking the copies. At t16 the deadline stages missing deliveries; it supplies progress rather than another opportunity to discover the step. `nudge_after_turns` is declared and validated but has no runtime reader.

**Offline verification and limits**

Ran the actual `uniquely_matched_authored_handoff` against every recorded latest 2A and 2C command. The tables below report all lexical hits before eligibility. Also checked 2A post-perimeter and 2C pre/post-purge fixtures through the real `KnowledgeProjector`; these are controlled fixtures, not reconstructions of every live world fact.

The brief's “exact matcher only” summary is incomplete: [`assemble_turn_prompt`](../storygame/runtime/cloudflare.py:286) tries the existing `_semantic_authored_handoff` after an exact miss. Latest 2C r1 t1 and 2A r3 t6 explicitly record semantic selections. I neither changed nor invoked that billed fallback.

For 2A, abbreviations below mean `k_sl_2a_<suffix>`. `—` means no lexical hit.

| Run/turn | Recorded command | Lexical hits |
| --- | --- | --- |
| r1 t1 | Examine Brandon's leaked Continuity Initiative documents. | a_r1 |
| r1 t2 | Review the cooling-water and ventilation readings. | b_r1 |
| r1 t3 | Show my inspector credentials at the facility checkpoint. | b_r2, e_r1 |
| r1 t4 | Explain the unscheduled inspection to the supervisor. | c_r1 |
| r1 t5 | Enter the service corridor. | c_r2 |
| r1 t6 | Trace the cooling-water pipes. | — |
| r1 t7 | Open the maintenance hatch. | — |
| r2 t1 | Examine Brandon's Continuity Initiative documents. | a_r1 |
| r2 t2 | Read Brandon's Continuity Initiative documents. | a_r1 |
| r2 t3 | Examine the blank inspector forms. | — |
| r2 t4 | Fill out the blank inspector forms. | b_r2 |
| r2 t5 | Present my inspector credentials at the facility checkpoint. | b_r2, e_r1 |
| r2 t6 | Present my inspection forms to the supervisor. | b_r2 |
| r2 t7 | Follow the supervisor through the nearby door. | — |
| r2 t8 | Enter the authorized personnel door. | — |
| r2 t9 | Follow the supervisor through the authorized personnel door. | — |
| r2 t10 | Present my inspector credentials to the guard. | b_r2, e_r1 |
| r2 t11 | Follow the supervisor through the security checkpoint. | — |
| r3 t1 | Examine Brandon's Continuity Initiative documents. | a_r1 |
| r3 t2 | Cross-reference Michelle's detention record with Brandon's Continuity documents. | — |
| r3 t3 | Fill out the blank inspector forms. | b_r2 |
| r3 t4 | Collect my inspector credentials. | — |
| r3 t5 | Copy my inspector credentials. | — |
| r3 t6 | Take my inspector credentials. | —; live semantic e_r1 |
| r3 t7 | Present my inspector credentials to the supervisor. | b_r2, e_r1 |
| r3 t8 | Explain my unscheduled inspection to the supervisor. | c_r1 |

Do not call r2 t5 a tie: B was spent at t4, leaving E as the sole matching projected candidate. At t6 B is spent, so its lexical hit earns nothing. At t10 B and E are both spent. The post-perimeter fixture confirms t6/t7/t8/t10 return no handoff; “Explain the unscheduled inspection to the supervisor.” must match C1 and “Enter the service corridor.” must match C2 while C is available. These outcomes must remain unchanged by the pointer proposal. A two-hit command must still return no exact match when both candidates really are offered.

For 2C, abbreviations mean `k_sl_2c_<suffix>`.

| Run/turn | Recorded command | Lexical hits |
| --- | --- | --- |
| r1 t1 | Copy the encrypted Project Echelon file to my laptop. | —; live semantic c_r1 |
| r1 t2 | Read Michelle's waiting message. | — |
| r1 t3 | Decrypt Michelle's encrypted message on my laptop. | d_r1 |
| r1 t4 | Follow Michelle's route marker. | d_r2 |
| r1 t5–t6 | Enter Rebecca's office. | — |
| r1 t7 | Confront Rebecca about the purge order. | — |
| r1 t8 | Demand Rebecca's purge order. | — |
| r2 t1 | Copy the JANUS evidence to my laptop. | c_r1 |
| r2 t2 | Read Michelle's message. | d_r1 |
| r2 t3 | Open Michelle's message. | d_r1 |
| r2 t4 | Examine the route marker. | d_r2 |
| r2 t5 | Access the broadcast controls. | — |
| r2 t6 | Seize the broadcast controls. | — |
| r2 t7–t8 | Broadcast the JANUS evidence. | c_r2 |
| r3 t1 | Download the JANUS evidence. | c_r1 |
| r3 t2 | Read Michelle's waiting message. | — |
| r3 t3 | Decode Michelle's message. | d_r1 |
| r3 t4 | Trace Michelle's route marker. | d_r2 |
| r3 t5 | Seize the broadcast controls. | — |
| r3 t6 | Find the broadcast controls. | — |
| r3 t7 | Access the broadcast controls. | — |
| r3 t8 | Broadcast my JANUS evidence. | c_r2 |

These are not claims that every lexical hit was eligible. The actual t2/t3 narrator prompts offer no candidates for the message commands; the route handoff occurs at t4. Later C2 hits cannot re-earn spent C. That timing is a separate issue from the missing copy step.

Required regression checks before billing:

- With JANUS evidence and C1 available: “Retrieve my copied JANUS files.”, “Take the copied files.” and “Use my copied files on the purge-control console.” each match C1. They match nothing without `janus_evidence`.
- With both C candidates offered: “Send the copied files.” matches C2; “Ask Brandon to retrieve the copied files.” ties and returns no exact handoff. “Open the purge-control console.” matches neither; “Check Michelle's transfer order.” lexically matches B1, not C.
- Test the **offered list**, too. The default projector caps candidates at four. In an early 2C fixture with JANUS evidence but no purge fact, C2 is omitted: “Send the copied files.” misses, while the ask/retrieve command uniquely matches C1. After the purge fact removes B's established reveals, C2 is offered and the tie applies. An all-package matcher test alone cannot prove live behavior.
- “Open the drawer.” and “Pull the drawer open.” match F1, not the card. “Examine the initials.” matches F2. “Search under the drawer.” and “Examine the gap beneath the drawer.” match the card. Neither “Search my laptop.” nor a drawer-opening command should reveal the card. Preserve plain `drawer` in both evidence and world naming.

Validation completed: 105 focused tests passed using `TMPDIR=/tmp uv run pytest -q tests/test_candidate_matcher.py tests/test_1a_gap_pointer.py tests/test_cue_text_safety.py tests/test_cue_spent_reveal.py`. The existing [runbook](../docs/testing-runbook.md:52) covers this verification boundary; its procedure did not change. Draft additions were loaded from a temporary package copy and passed literal narration safety checks in seeded 1A, 2A and 2C states. The temporary copy was deleted. These checks do not prove narrator obedience or increased play exits.

**Probes before implementation**

- **2A:** first obtain the actual narrator prompt for the post-perimeter forms turn. The saved r2 t6 is a name matcher request, so replaying it as narration would test the wrong thing. Compare baseline against the approved plot material for the supervisor's unanswered question, one change per arm, 10–15 samples via Ringer. Separately compare the current t5 delivery with the proposed pointer using the blind player's next action; the pointer's intended effect is on the player.
- **1A:** use a saved narrator workstation prompt, such as 41240bb r3 t1. Compare baseline with only the existing gap sentence added to SCENE. Read every reply for invented clues and an actionable gap. For the laptop-pull hypothesis, compare the same player-visible transcript with only the cue's laptop sentence removed; a narrator-only replay cannot test that hypothesis. Test the combined arm only after the single changes.
- **2C:** start with the recorded failed retrieve/take commands, after JANUS evidence is earned. The matcher checks are free and now pass. To test returning to the files, compare unchanged framing with the one-sentence file affordance in SCENE, then continue the same blind-player setup for three replicates. Score the C handoff and narration, not reported item facts.
- **Capture prerequisite, if needed:** a worker should retain narrator and name-matcher requests separately, tagged by scene, turn and call kind. Hermetic test: stub a turn with a narrator call followed by a name-match call; assert that both requests survive and the narrator record contains the actual narrator system/user payload. This is a logging repair request, not evidence that a new gameplay rule is needed.

No repeating-cue engine change is recommended yet. Its absence is certain; its contribution to the remaining failure rate is not. The data-only arms above use existing, measured techniques and preserve the protected discoveries.
