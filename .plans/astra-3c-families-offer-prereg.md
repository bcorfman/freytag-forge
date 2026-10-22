# Preregistration: Stage 7 Scene 3C families-offer cue, frozen-transcript player-choice screen (DRAFT, not approved)

Written 2026-10-22 before any billed run. Brandon has not approved this document. Nothing billed runs until he does.
Source: `.plans/chatgpt-3c-after-escape-plan.md`, ranked fix 2 and order-of-work step 5. Proposal 1 (entry-line subtraction) was stopped first: `.plans/astra-3c-entry-subtraction-prereg.md`.

## Question
Does adding `Kristin can answer the families with news of the captives.` to the D2 cue (`handoffs.yaml`, `community_rescue_efforts_begun`) make a blind player more likely to choose a command that answers or contacts the families?

## Free checks (done 2026-10-22, Ringer run `3c-families-offer-free`; its own check script had a quoting bug in the last line, so I re-ran the tests by hand)
- Variation `bench/variations/stage7-3c-families-offer.json`: only the `cue_text` line changes.
- `tests/test_3c_families_offer.py` (9 passed; 174 with the neighbouring suites): the variation differs from shipped only by the appended sentence; must_convey and protected-word checks hold; the composed reply differs only by that sentence and does not deliver D2's text; E waits for both D parts in both D orders.
- Selector table for `Answer the families with news of the captives.`: D1 unspent -> D2, D1 spent -> D2, D2 spent -> none, C not complete -> none. Identical for shipped and variation. Finding: the shipped package already selects D2 for this command, so the cue change only has to make players choose such an action; no matching change is needed or proposed.

## Billed design (player calls only, no Cloudflare narration calls)
Frozen transcript from row A (`bench/results/stage7-3c-escape-close-smoke`, arm `item-facts`) through turn 10, only the final cue differs; 12 independent player choices per arm (control cue, offer cue), interleaved. The competing tunnel task stays in the transcript. Needs a new small probe script (a Ringer code task, free) before any billed call; the call cap will be set there at 24 player requests.

## Read by hand
Each chosen command in full: does it genuinely answer or contact the families (the word "families" alone does not count)? Run each raw action through the real projected selector separately. Note any newly induced hardware/search thread or tunnel command.

## Decision rule (triage only)
Pass: at least 10/12 choices genuinely answer or contact the families, at least 3 more than control, no newly induced hardware/search thread. Tie or miss stops the wording. A pass leads to a continuation screen, not adoption.

## Not covered
Earned endings, the tunnel loop, hosted semantic fallback, rates.

## Approved (Brandon, 2026-10-22: "build the probe script, commit then run the 24 player calls")
Probe `scripts/ringer/stage7/3c_families_offer_probe.py` (Ringer run `3c-families-offer-probe`, committed). Screen run `3c-families-offer-screen`, 24 player requests, no narration calls.

## RESULT (2026-10-22, `bench/results/stage7-3c-families-offer/`, 24 rows, 0 errors)
The Ringer run reports FAIL only because its check (a `python -` heredoc) exited nonzero; the command itself exited 0 and rows.json holds all 24 rows with no errors.
Read by hand, every command. Control: 0/12 answer the families; all 12 are tunnel commands ("Continue through the maintenance tunnel to the surface" and variants). Offer: 11/12 answer the families ("Answer the families with news of the captives" or "Answer the families' calls with news of the captives"), 1/12 ("Keep moving toward the surface") a tunnel command. The real selector picks `k_sl_3c_d_r2` for all 11, none for the other 13.
No hardware/search thread was induced. Caveat: 8 of the 11 offer commands repeat the cue sentence's words nearly verbatim, so this shows the player takes the action when it is offered, not that it would find it unprompted. Rule: needed 10/12 and +3 over control. Met (11/12, +11). Passes the local screen; not adoption. Next: a continuation screen (12 rows per arm, product capture, semantic ON, no scripted first command, close kept in both arms) with its own prereg.
