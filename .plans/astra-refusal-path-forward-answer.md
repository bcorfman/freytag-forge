# ChatGPT answer: audit of the refuse-fixed-move evidence and path forward

Input from the user, 2026-10-13, in reply to `.plans/chatgpt-refusal-path-forward-prompt.md`. Saved verbatim. My review of it is at the end.

### 1. Audit of the evidence

I read the earlier answer, recorded results, relevant runtime functions, and guides. I did not run the game, independently rescore raw replies, or edit files.

| Claim | Verdict |
|---|---|
| Candidate fails its bars | **Supported:** 7/16 coherent refusals; destination/push 0/6. |
| Transport/Bring/Shove fail through narrator disobedience | **Supported by recorded evidence:** correct classification and delivered refusal text, followed by success claims. Code confirms the delivery mechanism. |
| Candidate causes no control over-refusal | **Partly supported:** all sampled controls succeeded, but two false classifications supplied inappropriate refusal text. An engine-owned response would turn those mistakes into blocked actions. |
| Candidate and `renarrate` are complementary | **Partly supported:** different successes suggest a hypothesis. Their combination could change both narration and capture triggers; success rates cannot be added. |
| Seat-control failure makes `renarrate` unfit as default | **Supported as a release decision**, not proof it is irreparable. Residual false claims and missed detection strengthen the case against adoption. |

Blind reading helps; one reader and recognizable refusal wording leave judgment bias possible. Near-identical replicates provide little additional breadth. Sorting by substrings is acceptable only if every reply receives full review. Classifier errors properly count against end-to-end performance, but must remain separate from narrator errors.

Capture's 13 flags across 32 turns are **not a recall estimate**: some flags concern controls. Cue presence on 30/32 turns likewise does not establish preservation without identifying when delivery was due.

One discrepancy needs reconciliation: the brief says **"Seat myself…"**, while the plan records **"Get into…"**.

### 2. Where your earlier answer stands

The earlier answer correctly anticipated narrator override, source/destination confusion, temporary lifts, and prerequisite-ordering risks. Its recommendation to measure the step was reasonable; the experiment rejected its hoped-for advantage.

I would withdraw the optimism that an outcome sentence would solve destination commands. I would retain the drop rule and move to engine-owned refusal. The existing `None` handling still records an issue and continues; that unresolved risk needs explicit treatment.

### 3. Path forward

**Choose option 1: one bounded engine-owned-refusal experiment.**

1. Resolve targets and obtain a model proposal distinguishing wholly prohibited relocation, ordinary use, mixed action, and uncertainty. Check fixedness against canonical declarations.
2. For wholly prohibited relocation, return deterministic refusal text before prerequisites or narration. This removes the measured narrator-override failure.
3. For mixed commands, clarify which allowed action to pursue; execute nothing partially or silently.
4. Refusal and clarification consume no story turn. Preserve facts, pacing, cues, and must-convey obligations. Deliver pending text on the next eligible accepted turn, exactly once.
5. Preserve this behavior across save/load; roll back any premature mutations.
6. Treat `None` as unresolved: clarification for ambiguity, a retryable failure for service unavailability. Never silently route it into ordinary narration. Guard every billed call.

This remains dependent on classification quality; it is not yet an established fix.

### 4. Measurement plan for your pick

Freeze these **16 fresh commands**, expectations, and valid starting states before running:

| Category | Commands |
|---|---|
| Lift | `Hoist the workstation overhead.` / `Lift the passenger seat briefly, then set it back.` |
| Remove | `Remove the back door from its frame.` / `Pull the drawer completely free of the workstation.` |
| Destination | `Carry the driver's seat into the kitchen.` / `Move the workstation beside the truck.` |
| Push | `Slide the workstation across the kitchen.` / `Push the passenger seat out of the truck.` |
| Two fixed things | `Carry the drawer and the passenger seat into the kitchen.` |
| Fixed destination | `Lay my laptop on the workstation.` / `Put my laptop on the passenger seat.` |
| Fixed source | `Collect my laptop from the workstation.` |
| Use in place | `Slide the drawer closed.` / `Pull the back door shut.` |
| Mixed | `Hoist the workstation, then open my laptop.` / `Carry the drawer and my laptop into the truck.` |

**Arms:** baseline and engine-owned refusal; one run per command per arm, **32 initial requests**, plus prescribed follow-ups for both mixed cases. Prefer additional unseen commands over duplicate replicates.

**Predeclared bars:** 9/9 honest refusals; 5/5 control successes; 2/2 appropriate mixed-action clarifications; zero prohibited-success claims, false refusals, or unintended mutations. Zero narrator calls on refusals/clarifications. All cue, pacing, rollback, save/load, and injected-`None` checks must pass. These are screening bars, not reliability estimates.

Before reading outcomes, inspect classifier payloads for correct targets, source/destination roles, and complete compound commands. Confirm refused requests have **no narrator prompt or call**; ordinary turns have no leaked refusal instruction.

Score every reply blind, preferably with two independent readers. Separately record target-resolution errors, classification errors, routing failures, and narrator contradictions. Count every scheduled case, including service failures. Record calls and latency.

### 5. What result would make you stop

After this bounded experiment, any dishonest relocation, blocked ordinary control, or state/delivery failure should end refusal work for Phase 4: retain opt-in status and proceed to the next items. Passing earns broader validation across another package and multi-turn sequences, not immediate default adoption. Keep `renarrate` off by default.

---

## Review of this answer (Claude, 2026-10-13)

Checked against `.plans/astra-implementation-plan.md:193`, `storygame/runtime/fixed_refusal.py` and `world.yaml`.

**Holds up**
- The "Seat myself" vs "Get into" discrepancy is not a real one. The brief quoted ChatGPT's earlier list. The plan substitutes "Get into the driver's seat." to match the player-input guide. The failing control was "Get into…".
- The 13 capture flags are not a recall estimate. They mix true flags with control flags. They only show that capture undercounts.
- `fixed_refusal.py` records an issue and continues on `None`. That is right for the prompt-line step and wrong for an engine-owned refusal, so the plan must say what happens on an unanswered question.
- Classifier errors were harmless in the step but would become blocked actions in an engine-owned refusal. The two "Retrieve my laptop" false positives are the example.

**Concerns**
1. It bundles a four-way classifier (prohibited, ordinary use, mixed, uncertain), mixed-command clarification, turns that consume nothing, deferred cue delivery and save/load into one "bounded" experiment. The existing classifier is yes/no and misfired 4 times in 16. A four-way classifier is untested. Clarification and cue deferral are separate designs, and how the engine handles either today is unchecked.
2. The stop rule is too strict. Any single misclassified command would end the work. Classifier accuracy and engine-owned path mechanics should be judged separately.
3. Several commands send things to "the kitchen". `world.yaml` has the kitchen in `mcgehee_home`. Whether it is reachable from scene 1A's truck and workstation is unchecked. Freeze the list only after that is settled.
4. One run per command, 9 refusal / 5 control / 2 mixed, is a screen and not evidence for a default.

**Proposed smaller first experiment (not yet built)**
- Keep the yes/no classifier. Tighten it on the two known failure patterns: lift-then-lower, and "from the passenger seat" (source versus fixed thing).
- When it says a fixed thing is relocated, return a fixed refusal line with no narrator call.
- Mixed commands fall through to the existing path with no special handling.
- An unanswered classifier means normal narration plus a recorded issue, the same as the step today.
- Use ChatGPT's fresh commands once the kitchen question is settled.
- Bars: 9/9 refusals, 5/5 controls, 0 narrator calls on refused turns.
- If it passes, mixed commands, cue deferral and save/load become a second, separate experiment. If it fails on the classifier alone, the narrator is not the blocker.

Open decisions: whether to build the smaller experiment; whether `renarrate` becomes a web default (ChatGPT says keep it off, and I agree on current evidence).
