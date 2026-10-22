# Preregistration: Stage 7 Scene 3C A-R1 broadcast-line prompt screen (follow-up to Step 11a of `.plans/chatgpt-3c-stuck-turns-plan.md`)

Written 2026-10-20 before any billed call. Preregistration only: no harness change, billed run, adoption or deploy is authorized by this file. Spending needs Brandon's go.

## Why
The C1 screen (`.plans/astra-3c-recall-live-prereg.md`) missed: C1-scoped finished 3/12 against shipped 6/12. Its replies pointed at a different pull.
In the recorded turn-6 prompt (`bench/results/stage7-3c-blind-raw-f918c663/attempt-1/`, 3C turn 6, narration stage) the A-R1 statement
`Michelle broadcasts captives, JANUS records, planning sessions, and detention locations to independent networks.` appears three times: once in SCENE and twice as permitted
NPC speech (Dr. McGehee and Rebecca Jenkins). It is a completed action stated in the present tense. In the C1 screen, recall rows 1, 3, 8 and 9 had Michelle broadcasting to the networks
instead of leading the captives out, and rows 1 and 9 echoed the new C1 sentence aloud. Hypothesis, not a finding: repeated completed-broadcast recall pulls the narrator back to Michelle's console work.
The plan's section C already lists this exact A-R1 replacement as a retained candidate (technique: scope or remove completed-action recall, as in 1A #668 and 2C). It has never been run.

## Change under test (one change only)
`knowledge.yaml` A-R1 `statement` (`bench/variations/stage7-3c-broadcast-live.json`, YAML single-quote escaped):
- Old: `Michelle broadcasts captives, JANUS records, planning sessions, and detention locations to independent networks.`
- New: `Independent networks have the captives' video, JANUS records, planning sessions, and detention locations.`
Delivery text, evidence, effects, C1, C2 and the separate B-R1 delivery line "Michelle sends its prisoner locations to independent networks" are unchanged.
Known confounds, recorded not fixed: (1) the B-R1 line recurs twice in NPC speech in the same prompt and is a second possible pull, so a null result cannot clear the broadcast idea entirely; (2) "video" is a word the old line did not carry. If Brandon rejects it, use `the captives, JANUS records, ...` unchanged otherwise, before any run.

## Frozen input
Same recorded turn-6 narrator request, same command (`Lead Michelle and the captives through the open surface gates to safety.`), same THINGS. Arms: `pump` (shipped data/, fresh replies, interleaved) versus `broadcast` (the A-R1 replacement in all three occurrences).
12 replies per arm. The recording is the pump arm byte-for-byte; the broadcast arm differs only by the three A-R1 occurrences. Do not pool with the C1 screen's rows; shipped control is re-sampled.

## Free checks before any billed call
1. The old statement occurs once in `knowledge.yaml` (checked 2026-10-20: 1) and the new line parses as one YAML string (checked: yes).
2. Dry run proves the three replaced occurrences and zero residual `Michelle broadcasts captives` in the broadcast arm, and byte-identity of the pump arm with the recording.
3. A-R1 effects/evidence/delivery hashes unchanged; A-R1 still earns and fires on the A command; existing 3C cue-chain tests pass.
Harness: generalize `scripts/ringer/stage7/three_c_recall_replay.py` to accept an arm definition (old/new strings and expected occurrence count) with `--confirm` guard and checker preserved; the C1 arm stays reproducible. This is a Ringer build task, run only after Brandon approves this file.

## Caps
Smoke 1 reply per arm (cap 4 requests), read in full. Then 48 Cloudflare requests total (one normal plus at most one recovery per reply), zero player calls, no semantic judge. Stop on budget response; keep partial rows; no replacements, no top-ups.

## Scoring (by hand, prose only, no keyword gates)
Per reply: (a) finishes = the group is through the gates on the surface, coherent, no pump or barrier reset; (b) drift = Michelle broadcasts or sends material to networks instead of leading the group; (c) malformed JSON after recovery.
Bar (triage, not significance): broadcast arm finishes >= 10/12 and >= 3 more than the re-sampled pump arm, with drift in fewer broadcast rows than pump rows and no new story-breaking error.
The C1 screen's pump arm finished 6/12; a similar control would need 9+ to clear +3, so 10/12 is the binding bar. A miss or tie stops the broadcast hypothesis; do not follow with a bundle of C1+A-R1.

## If it wins
Continuation (labelled reconstruction through turn 5, 12 raw continuations per arm, deadline 14) is a separate preregistration modelled on Step 11a item 3. No adoption from a prompt screen alone.

## Limits
One recorded prompt, one story, 12 replies per arm. Says nothing about player progression, completion rate, or the B-R1 line.

## Result (2026-10-20)
Smoke (1 per arm, 3 requests) and screen (`bench/results/stage7-3c-broadcast-live-screen/`, 12 per arm, 27 of 48 Cloudflare requests, 0 player/judge calls, stop `complete`, checker OK).
(The Ringer task reported FAIL only because its check line still said 1 row per arm; the run itself was complete and the checker passes with 12.)
Hand read of all 24 replies. Finish = group through the gates on the surface, coherent, no pump or barrier reset:
- pump (re-sampled shipped): 7/12 (rows 0, 3, 4, 7, 8, 10, 11). Row 2 reaches the surface but also has Kristin move the watertight barrier again, so it is not counted. Rows 1, 5, 6, 9 stop short. Malformed-JSON replies: 2 (rows 3, 11; recovered).
- broadcast (A-R1 scoped): 5/12 (rows 3, 4, 6, 8, 11; row 8 narrates gates and sunlight out of order and is borderline; row 6 had one recovered JSON error). Rows 0, 1, 2, 5, 7, 9, 10 stop in the tunnel or at the gates.
- Broadcast drift (Michelle broadcasting to networks instead of leading the group): 0/12 in both arms. No reply in either arm mentions networks.
Bar was broadcast >= 10/12 and >= 3 above pump, with less drift. Broadcast is 2 below pump and there was no drift to remove. **Miss: the broadcast-line hypothesis is stopped.**
Reading: the drift seen in the C1 screen's recall arm did not come from the A-R1 line; with the C1 line scoped the A-R1 line was still present, and with A-R1 scoped alone it never appeared. Two screens of this one prompt now show shipped pump finishing about 6-7/12 and neither scoped statement helping. Unscoped pulls left in the prompt (B-R1 "prisoner locations to independent networks" x2 in NPC speech, C2 statement, SCENE pressure lines) are untested and stay hypotheses; do not bundle them.
