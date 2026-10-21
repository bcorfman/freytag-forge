# Preregistration: Stage 7 Scene 3C changed-context C1 prompt screen (Step 11a of `.plans/chatgpt-3c-stuck-turns-plan.md`)

Written 2026-10-20 before any billed call. Authorized by the plan's Step 11a caps; no continuation, adoption or deploy is authorized by this file.

## Why
Staged journey (`bench/results/stage7-3c-blind-raw-f918c663/attempt-1/`): turn 6 command `Lead Michelle and the captives through the open surface gates to safety.`
is a semantic refusal (universe/shortlist 2/2) and narration then resets to tunnel travel for turns 6-13. C1's recurring statement is one of several competing pulls.
Step 5 tested this exact C1 text on a synthetic start and lost (D by turn 10 3/12 vs 7/12; earned 2/12 vs 5/12). This is a changed-context retest, not a new candidate.

## Change under test
`knowledge.yaml` C1 statement `Kristin restores power to drainage pumps and holds one watertight barrier while Michelle leads captives through the maintenance tunnel.`
becomes `The drainage pumps have power. The evacuation route is open.` (`bench/variations/stage7-3c-recall-live.json`). Delivery, C2, effects, evidence unchanged. No C2, alias, binding or deadline change.

## Frozen input
Recorded turn-6 narrator request (stage `narration`, system + user) from the bundle above, same command, same THINGS. Arms `pump` (shipped data/) vs `recall` (variation), interleaved,
12 replies each, temperature/settings as the live narrator. Frozen prompt is byte-identical except the C1 statement occurrences (SCENE and permitted NPC speech).
Stop before any billed call if that isolation cannot be shown.

## Caps
48 Cloudflare requests total (one normal + at most one recovery per reply), zero player calls, no semantic judge call. Stop on budget response; preserve partial rows; no replacements. Smoke 1 reply per arm first.

## Scoring (by hand, prose not keywords)
Read all 24 replies: does the requested passage finish; do people stay consistent with that action; does it reset pumps/gates or invent a new obstacle?
Bar (triage, not significance): recall >= 10/12 coherent finishes AND >= 3 more than pump, with no new story-breaking error. Failure or tie stops C1 and retains Step 5's loss.

## Limits
One recorded prompt, one story, 12 replies per arm; says nothing about player progression or a completion rate.

## Result (2026-10-20)
Smoke (1 per arm, 2 requests) and screen (`bench/results/stage7-3c-recall-live-screen/`, 12 per arm, 30 of 48 Cloudflare requests, 0 player/judge calls, stop `complete`, checker OK).
Hand read of all 24 replies, "finishes the passage" = the group is through the gates on the surface, coherent, no pump/barrier reset:
- pump (shipped): 6/12 finish (rows 2, 3, 4, 6, 7, 9; rows 3 and 9 had a JSON error after the recovery). Resets or stops short: 0, 1, 5 (holds the barrier again), 8, 10, 11.
- recall (C1-scoped): 3/12 finish (rows 6, 7, 10; row 6 had a JSON error). Four rows stop short with the group still heading to the gates (0, 1, 5, 11); rows 3, 8, 9 drift into Michelle "broadcasting to independent networks" (rows 1 and 9 also echo the new C1 sentence aloud); rows 2 and 4 returned no usable reply.
- Malformed-JSON replies: pump 2/12, recall 4/12.
Bar was recall >= 10/12 and >= 3 above pump. Recall is 3 below pump. **Miss: C1 stops, Step 5's loss stands.** Triage on 12 replies, not significance; the direction is wrong, so no repeat is warranted.
Residual pull seen in the surviving prompt: replies in both arms narrate approach and open gates, and the A-R1 "broadcasts ... to independent networks" statement shows up in recall rows 1, 3, 9. That is a hypothesis for a separately preregistered A-R1 subtraction, not an authorised next step.
