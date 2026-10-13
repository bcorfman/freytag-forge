## 1. Verdict on the candidate

**Measure it next, but treat it as a promising experiment—not an established fix.** I read the named implementation, guides, world declarations, and recorded results. I did not run the game, call billed models, or edit files.

The candidate changes something meaningful: the narrator receives a resolved outcome for this attempt instead of a permanent property it must apply to the command. That could help with destination and push commands.

However, that is a hypothesis. Existing prerequisite steps accomplish something that enables the requested action; this step says the requested action has already failed. The narrator still receives the original command and might interpret it as another attempt, then narrate success. The measured destination failures make that a substantial risk.

Three qualifications to the brief:

- **Over-refusal should decrease, but remains possible.** Ordinary use avoids refusal text only when the classifier correctly distinguishes moving an object from using it.
- **Cost is potentially one question per fixed object, not per turn.** Two fixed objects require separate decisions unless the request batches them. Controls naming fixed objects also incur classification cost.
- **The current ordering matters.** [WorldCapture.before_turn](/home/bcorfman/dev/freytag-forge/storygame/runtime/capture.py:40) runs prerequisite mutations before `prepare_turn`. Reusing that match call does not automatically provide targets before those mutations. A transport command could cause boarding before the refusal is established.

The [prompt assembly](/home/bcorfman/dev/freytag-forge/storygame/runtime/item_facts.py:543) confirms that prerequisite text reaches the narrator as “Just before this.” It does not establish that the narrator respects failed-action outcomes.

## 2. Ways it fails

| Player command | Failure to watch for |
|---|---|
| `Put my laptop on the workstation.` | Classifies the fixed destination as the object being moved. |
| `Take my laptop off the passenger seat.` | Treats removal from a fixed object as removal of that object. |
| `Push the back door open.` | Confuses ordinary operation with relocating the door. |
| `Pull the drawer open.` | Treats a container’s opening motion as detachment. |
| `Move the workstation chair beside the workstation.` | Confuses the movable chair with the fixed workstation, especially through overlapping names. |
| `Carry the drawer and my laptop to the truck.` | Refuses both objects, or narrates both moving after receiving a refusal for only the drawer. |
| `Lift the workstation and the drawer.` | Checks one fixed object and misses the other. |
| `Carry the workstation to the truck, then open my laptop.` | Boarding or seated-use prerequisites execute even though the action that motivated travel failed. |
| `Lift the workstation, then lower it back into place.` | Prose falsely claims success while the final placement remains unchanged, escaping capture-based scoring. |

An unanswered classifier is another distinct failure. Existing prerequisite functions can receive `None`. That must remain an unresolved decision; treating it as “ordinary use” would silently restore the original defect.

Also distinguish **fixed attachment from absolute position**: a truck seat can travel with the truck while remaining attached. The question must concern relocating the seat independently, not every change in its geographic position.

## 3. Other candidates

**One alternative is worth keeping: an engine-owned refusal response for a wholly disallowed action.**

Mechanism:

1. Resolve the objects and classify the requested relocation.
2. Validate fixedness against canonical world facts.
3. For an unambiguous command consisting entirely of prohibited relocation, return a deterministic refusal through the normal response interface.
4. Keep the attempt from advancing story state or consuming delivery obligations. Handle mixed or ambiguous commands separately; clarification consumes no story turn.

This differs from the measured appended clause: **there is no preceding narrator prose claiming success.**

**Cost:** target resolution plus the necessary small-model classification; no narrator call on eligible refused requests. Other turns retain their normal cost.

**What it could break:**

- A false positive blocks legitimate use completely.
- Mixed commands could lose their allowed action if the gate rejects the entire request.
- Bypassing normal turn handling could accidentally consume or omit authored cues and must-convey delivery.
- Refusals that consume no turn change pacing policy.
- Any prerequisite mutation made before rejection must be rolled back; save/load must preserve the same state and pending obligations.

It could beat the candidate because, after correct classification, narrator obedience is no longer required. Its broader turn-policy implications make it a second experiment rather than my first choice.

## 4. A measurement plan

**Top pick: the proposed prerequisite outcome, isolated from other prevention techniques.**

Use these 16 fresh commands. Establish valid, matched starting states: objects accessible, laptop available, drawer closed for opening and open for closing, and seating controls started outside the target seat.

| Category | Command | Expected result |
|---|---|---|
| Lift | `Raise the workstation off the floor.` | Coherent refusal |
| Remove | `Detach the driver's seat from the truck.` | Coherent refusal |
| Remove | `Extract the drawer from the workstation.` | Coherent refusal |
| Destination | `Transport the workstation into the truck.` | Coherent refusal |
| Destination | `Bring the drawer to the passenger seat.` | Coherent refusal |
| Push | `Shove the workstation toward the back door.` | Coherent refusal |
| Two fixed objects | `Lift the drawer and the back door together.` | Both attempts refused |
| Temporary displacement | `Lift the workstation, then lower it back into place.` | Refusal; no successful lift |
| Fixed destination | `Place my laptop on the workstation.` | Laptop placement succeeds |
| Fixed destination | `Set my laptop on the passenger seat.` | Laptop placement succeeds |
| Fixed source | `Retrieve my laptop from the passenger seat.` | Laptop retrieval succeeds |
| Use in place | `Pull the drawer open.` | Drawer opens |
| Use in place | `Push the drawer shut.` | Drawer closes |
| Use in place | `Push the back door open.` | Door opens |
| Use in place | `Seat myself in the driver's seat.` | Player sits; seat stays attached |
| Two named things | `Move the workstation chair beside the workstation.` | Chair moves; workstation stays |

**Arms:** baseline with prevention and recovery off; candidate alone; existing `renarrate` with authored-cue restoration and no fixed marker.

**Samples:** two independent runs per command per arm: **96 evaluated turns**. Reset between commands. Interleave arms and keep model settings identical. Report by command and category; near-identical replicates are not broad evidence.

**Predeclared screening bars:**

- At least **15/16 coherent honest refusals**, with **zero claims of successful prohibited relocation**. The possible remaining failure may be off-topic, not dishonest.
- Destination and push commands must achieve **6/6 coherent refusals**.
- Controls must achieve **16/16 intended successes**, with zero invented fixedness obstacles or seat displacement.
- Authored text due on a turn must be preserved exactly; delivery bookkeeping must agree with what the player sees.
- No unintended prerequisite movement, progression, or persistent-state discrepancy.
- Candidate adds no narrator call. Record actual classifier calls, latency, and failures rather than assuming its cost.

These are screening thresholds, not evidence of a production reliability rate. A baseline control failure should be reported separately, but it does not make that control pass.

**Validate the experiment before scoring.** Inspect recorded narrator payloads to confirm correct target selection and refusal-line delivery. Separate target-resolution misses, classifier errors, and narrator disobedience. Report end-to-end results over every scheduled case, not only cases where capture recorded a refusal.

Read every reply with arm labels concealed. A coherent refusal must address the requested attempt, show failure, and avoid contradiction or successful displacement anywhere in the prose. Compare prose with facts separately: unchanged facts cannot prove an honest reply.

Before adoption, require a fresh command set plus multi-turn checks covering mixed actions, cue delivery, progression, and save/load. I have not verified those paths experimentally.

## 5. Recommendation

Build and measure the candidate as an opt-in experiment first, with explicit handling of target selection, prerequisite ordering, and unanswered classification. It is the smallest untested change with a plausible advantage over the failed THINGS markers. Drop this version if correctly classified destination or push commands still produce successful-move prose, or if ordinary-use controls fail the declared bar. If classification works but narration still overrides the outcome, measure the engine-owned refusal response next; the recorded wording experiments give little reason to keep tuning fixedness sentences.