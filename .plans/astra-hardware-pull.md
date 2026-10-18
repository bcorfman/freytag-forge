**The evidence supports a hardware-chase loop, but it does not establish that another panel description will break it.** I recommend one small subtractive material probe before considering a narrator change. This is a proposal for the Ringer handoff; I changed no files and made no billed calls.

I read the requested guides, 2B plot and reveals, world declarations, handoffs, saved transition results, earlier prompt reconstruction, and the world-model decisions and amendments.

One correction: **seven timer rows earned no first reveal; one earned it too late to finish.** In `stage7-door-02-control`, `k_sl_2b_a_r1` committed on command 12. The saved results therefore support “failure to reach and complete the evidence chain,” rather than “all eight never earned the first reveal.”

| Hypothesis | Assessment |
|---|---|
| **1. Nothing declared to chase** | Partially supported for invented consoles and keypads. Insufficient for the panel: it already has a declaration, aliases, state and push-opening fact. Grounded rep 5 explicitly names that declared panel, then invents another hidden panel and its controls. Declaration alone did not close the chase. |
| **2. Vivid hardware dominates the screen** | Strongest behavioral evidence. Hardware supplies an unfinished task; the terminals supply background information. This is stronger than a literal recency explanation: the entry comes after the hardware, yet players still choose hardware. The shared detention goal cannot explain which rows stall. |
| **3. “Finish each action” sustains the chase** | Plausible, untested. The instruction could also make opening resolve promptly. Neither the comparison nor the reconstruction isolates its effect. |
| **4. The appended cue is weak** | Supported as a practical limitation. It cannot influence command 1, and the earlier cue probes give little reason to expect another wording round to recover subsequent commands. |
| **5. Other material competes with the investigation** | The 2B.1 Details line offers unfamiliar system files, government data and financial data. Those provide material for login, maintenance and access-code elaboration without directing discovery toward an eligible reveal. This is a plausible amplifier, not an established cause. |

**First proposal: subtract the competing 2B.1 Details.**

Touch only [plot.md:478](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:478).

Old:

```markdown
**Details:** restricted records archive; unfamiliar system files; government data; financial data; Michelle’s research
```

New:

```markdown
**Details:** restricted records archive; Michelle’s research
```

This removes three broad elaboration targets while preserving the scene and its existing research focus. The full JANUS explanation remains in the plot; protected delivery remains in `knowledge.yaml`. It introduces neither an object nor a reveal.

This is deliberately a **low-confidence subtraction probe**. It gives the narrator less material for extending a hardware search. It does not supply a finished answer for every console the player names, and I cannot honestly promise that it makes hardware commands resolve in one turn.

The earlier diagnosis identified these competing Details, but the documented live experiment changed the appended cue. Removing the narrator’s competing material is a distinct intervention.

**Second preference, only if subtraction fails: replace the entry’s spatial ambiguity.**

Touch only [plot.md:456](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:456), in a separate arm.

Old:

```yaml
entry_text: "The records archive hummed behind the restricted corridor. The archive terminals held the Initiative's selection files. Those files held answers to why Michelle was taken and who helped build the system that chose her.\n\n"
```

New:

```yaml
entry_text: "Kristin and Brandon were inside the records archive. The archive terminals held the Initiative's selection files. Those files held answers to why Michelle was taken and who helped build the system that chose her.\n\n"
```

This makes arrival explicit in the player-visible entry. It preserves the existing information about selection files and adds no instruction. Character placement belongs in this once-only entry, as the grounding guide specifies.

Confidence is also low: the grounded bridge already says they continued into the archive. This tests whether the entry’s “behind the restricted corridor” framing weakens that completion. It does **not** repeat the proposed instruction to search named reveal targets.

For these two proposals, the risks differ:

| Boundary | Details subtraction | Entry replacement |
|---|---|---|
| Normal 2B progression | Could reduce useful investigative texture or make research narration repetitive. | Could fail to overcome the unfinished hardware task; could conflict with an anomalous arrival state. |
| `t_2b_2c` | No predicate or delivery changes; behavioral progression could still worsen. | Same. |
| Cue and nudge staging | Timing and text stay intact. Their government/financial wording may dilute the subtraction. | Staging stays intact; only the initial player screen changes. |
| Affordance map | No entity or placement changes; check whether generated textual evidence changes. | Same; verify arrival against actual placements. |
| Frozen control | Apply the edit only to the changed package. Preserve the frozen package and verify its hash. | Same; preserve the control entry verbatim. |

I would **not propose a narrator rule yet**. Material fixes have not been exhausted, and neither the completion instruction nor the paragraph-length requirement has a causal result supporting a replacement.

Before measurement, capture the shipped payloads with the network stubbed. Confirm that the Details subtraction reaches the relevant 2B prompts; the saved `prompts/` files in this transition run describe the 2A generation, and the earlier 2B reconstruction predates the push fact.

Then use the same **N=12 full transition screen**, retaining its raw player, command cap, timer, clarification behavior and disabled semantic fallback. Keep the changed arm only at **at least 10/12 earned exits**. Report first-reveal turn and hardware-chase length as explanations, not substitute acceptance criteria.

My judgment: **a small 2B material improvement remains plausible, but a reliable one-turn hardware resolution is unsupported.** If these narrowly scoped probes fail, the stronger next diagnosis is the generated 2A unfinished task and the narrator’s continuation behavior. Semantic fallback deserves separate measurement; a search for a door code should not earn Michelle’s evidence merely to improve the exit rate.