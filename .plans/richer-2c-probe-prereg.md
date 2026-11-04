# Preregistration: the richer scene 2C, the command corridor

Written 2026-11-03 before any billed 2C run. Same method and instruments as `.plans/richer-2b-probe-prereg.md` (including the
1B value rule: presence is necessary but not sufficient; every added detail must do a job). Read every turn by hand with
`.plans/richer-probe-report.py`; report replicates separately, never pooled.

**Smoke (free).** `bench describe` runs on both variations (package hashes: baseline `a663a8b5...`, candidate `b03eaf57...`). Offline, `tests/test_richer_2c.py` hands each of the five script
commands to its intended reveal (H, C, F, G, D rescue) given the facts the earlier commands establish. Whole quick suite on the branch:
4094 passed, 31 skipped; ruff clean. Both arms use `entry_state: thorough`. The thorough entry state does NOT earn the optional 2B reveals (checked offline:
`held_transfers_seen`, `ticket_header_matched` are false at 2C entry), so the candidate arm sets `entry_facts` to those two facts
(this earns `k_sl_2b_f_r1` and `k_sl_2b_g_r1`, which is what lets "sensor fault" and "ticket header" be said without a guard
rejection). The frozen baseline does not declare those facts, so its arm cannot set them; the baseline has nothing authored for
tags or the ticket form anyway.

## What changed in 2C (each addition has a job)
- **Corridor camera** (F, 2C.2, needs Brandon's yes): it holds on Brandon during the offer and swings back to its sweep when he says
  yes. Pays off the 2A camera that "turned toward Brandon and stays on him". Tells Kristin Rebecca called off the watch, not whether
  she believes him. Declared thing: `corridor_camera`.
- **Cart tags** (G, 2C.3, needs the held transfers seen): each tag carries a transfer date a week old and the code "sensor fault". Pays
  off 2B.2: these are the transfers that were held. Declared thing: `cart_tags`.
- **Uplink monitor light** (H, 2C.3): one outbound channel, steady amber, "whatever goes out will be seen". A clue to the cost of
  transmitting, so the transmit-or-rescue choice is informed. Declared thing: `monitor_light`.
- **Ticket form of Michelle's second message** (2C.5, edits the commitment deliveries `k_sl_2c_d_r3`/`r4` and the first
  `purge_window_2c` text): the route arrives as a maintenance ticket on the uplink panel, the cart latch display, or a wall panel. A
  player who matched the header in the archive is told it has that header and the same closing code. Everyone else is told only that
  a maintenance ticket scrolls up. (The unmatched text omits "sensor fault" and "ticket header" on purpose: they are guarded terms and
  an unearned echo is rejected as unavailable knowledge; this was found by the whole-suite run, not by the acceptance tests.)
- F, G, H are optional, priority -1, not voiceable, short statements with the images in the delivery text. Windows 0/6/6 (the purge
  window closes at turn 5). Targets are >= 6 because of the 2B lesson (forward activation waits on every earlier-target storylet).

## Questions
- **Q1 Invented material.** Plain things resolved new, and specifics the narrator invents (what the tags say, what the monitor shows,
  what the camera does), old versus new 2C. The baseline has nothing authored for a camera, a monitor light or tags.
- **Q2 Authored details delivered when earned (candidate).** H on command 1, F on command 3 (after Brandon's yes on command 2), G on
  command 4. Each lands on the command that asks for it. Record the turn each landed and whether F was refused before the yes.
- **Q3 No regression.** Required path is the answer to Rebecca (`k_sl_2c_c_r1`) and the commitment (`k_sl_2c_d_r4`, rescue). Record per
  replicate: the turn each landed, whether the scene was left by an earned transition, and whether the ticket form (and, in the
  candidate, the matched-header variant) appears in the commitment turn.
- **Q4 Value.** For each detail: does it plant, pay off, deepen or set mood, or is it an inert prop? Is the narration better, flat or
  busier than baseline? Watch the known faults: Brandon or the narrator reciting statements as dialogue, the engine's delivery text
  repeating what the narrator just wrote (echo), the same image repeated, the narrator inventing what a thing shows, and the narrator
  naming Michelle as the author of the ticket before Kristin could know (the unmatched variant must not).

## Design
Arms `richer-2c-baseline` (frozen story from `159695e4`, `bench/frozen/continuity-pre-richer-2c/`) and `richer-2c-candidate` (current
story, `entry_facts` held_transfers_seen and ticket_header_matched), script `richer-2c-corridor` (five imperative commands): `Check the
monitor light.` `Tell Rebecca nothing.` `Look at the camera.` `Read the cart tags.` `Head to the transfer carts and free a cart of
captives.` 4 replicates per arm, both judges on, shipped transports, no retries, partial rows kept, one opening request each.
Projected cost at 11 neurons per turn, opening included: 6 turns x 4 replicates = 264 per arm, 528 in all. Request cap 150 narrator
and matcher requests per run; judge calls separate. Stop on HTTP 429 `AI_QUOTA_EXCEEDED` or `AI_DAILY_BUDGET_EXCEEDED` until 00:00
UTC. The answer to Rebecca is command 2 (turn 1), inside its window (latest turn 2).

## Decision rule (triage only; nothing is adopted from this probe)
- Richness is supported if the candidate resolves no more plain things as new than the baseline, Q2 holds in at least 3 of 4
  replicates for each detail, and Q4 finds the details mostly do a job.
- A candidate failure of the existing path (the answer, the commitment, the ticket form) is a defect to fix before 3A.
- Record every narrator prompt's length against `tests/test_prompt_budget.py` (narrator <= 5000, item-matching <= 3500), and name any
  turn over 5,000.
- With four replicates a one- or two-point judge gap is not reported as real.

## Not covered
The transmit branch (`k_sl_2c_d_r3`) and the missed-window path under the new details, later scenes (the plants pay off in 3A, 3B
and 3C), hosted staging, other models, wording tuning. Offline tests cover both branches and the missed-window text.

## Owed to other scenes (so the plants pay off)
3A: the carts' captives are alive because the transfers were held; a sedated cart's tag is the same one Kristin read. 3B/3C: the
facility's eye on its own traffic (the monitor light) can surface when Kristin sends the final broadcast: every outbound channel is
watched, so the broadcast must be forced from the office. The supervisor on the purge list (a payoff for the 2A alarm log) was left
out because Rebecca's tablet leaves with her.

## Result (run 2026-11-03, branch `richer-narration-2c`, commit `1899f1dc`)
Outputs `bench/results/richer-2c-probe/{baseline,candidate}` (gitignored), 4 replicates each, none failed, 0 rejected turns and 0 guard
rejections in either arm, 528 projected neurons. Every turn of both arms read by hand (scratchpad reports, not in the repo). Replicates
reported separately; the judge scores are not real signal (4 replicates). Each arm had one malformed narration segment that the transport
dropped and logged.

**Headline: richness is supported on the 2C path. All three details, and the ticket form, landed on the command that asks for them in 4 of 4
replicates, the existing path did not regress, and the baseline's invented material (including a story-breaking name) is gone. Two
defects: the monitor light echo (4/4) and the narrator prompt at the commitment turn (6,630 characters).**

- **Q1 Invented material.** Plain things resolved new: baseline 0 in 20 turns, candidate 2 in 20 (`guards`, command 2, replicates 2 and 3;
  the entry text names them and no 2C thing is declared for them, so the matcher made a group; harmless but it breaks the "no more than
  baseline" rule on its face). What the baseline narrator made up where the candidate has authored text:
  command 1 (monitor light): "flashing rapidly" and a panicked "What's going on?" with Brandon answering "it's not good" (4/4, no information);
  command 3 (camera): "the camera's lens is turned toward the gate" (3/4; the matcher resolved the 2A security camera, and the continuity
  judge flagged `contradicts_stated_fact` on command 3 in 4/4 baseline replicates against 0/4 candidate);
  command 4 (cart tags): "the names of several people, including Dr. Michelle McGehee" (2/4, a story-breaking invention), "encrypted" (1/4),
  "numbers and codes, but no names" (1/4). The candidate invents nothing concrete on those commands.
- **Q2 Authored details delivered when earned.** Monitor light on command 1: 4/4. Camera after Brandon's yes, command 3: 4/4. Cart tags,
  command 4: 4/4 (with `held_transfers_seen` seeded). Answer to Rebecca (`k_sl_2c_c_r1`) on command 2 and the rescue commitment
  (`k_sl_2c_d_r4`) on command 5: 4/4 in both arms. The matched-header ticket variant appeared on command 5 in 4/4 candidate replicates; the
  baseline has no ticket. Not exercised live: the camera before Brandon's yes (refused offline), the transmit branch, the missed-window path.
- **Q3 No regression.** The required answer landed on command 2 (turn 1, inside its window) and the commitment on command 5 in every
  replicate of both arms. Both arms left the scene on command 5 (`left_scene` true in 4/4, same as baseline). The curiosity commands cost
  nothing here because the purge window (turn 5) is not reached by five commands.
- **Q4 Value.**
  - Monitor light: does a job (a fair-play clue about the cost of transmitting) and replaces an invented, empty alarm. Weakness: **echo, 4/4**.
    The narrator writes "It's steady amber, indicating the facility's eye is on its own traffic" and the delivery then says it again in
    nearly the same words. Same known fault and same cure as the 1C door and 2B badge deliveries (put the image in the thing's placement
    text and shorten the delivery to what is new); not applied, because it needs a billed re-probe (the 1C fix backfired twice before it
    was probed).
  - Camera: does a job (pays off 2A; "Brandon does not look up"). Its only blemish is harmless narrator filler ("tries to read the
    expression of the guard below it", 3/4) and, once, an invented line for Kristin ("We're being watched", replicate 4).
  - Cart tags: does a job (pays off the 2B held transfers; "These are the transfers that were held" lands cleanly). No echo.
  - Ticket form: appears once on the commitment turn; it does not name Michelle's authorship beyond the existing "Michelle's route"
    sentence. The wording "the ticket header Kristin matched in the archive" is stilted but accurate.
  - Narration is busier than baseline, but each addition is a clue or payoff; the baseline's busyness was invented filler.
- **Judges.** Candidate 2, 3, 4, 3 against baseline 3, 3, 2, 2 (means 3.0 and 2.5). With four replicates this is not reported as a real gap.
  Continuity: only the baseline camera flag above. Fact tracking: `missed_change` 0 and `invented_change` 0 in both arms; the
  `narration_contradicts_given_facts` flag on command 5 (`detention captives:start_conflict`) appears in 3/4 baseline and 4/4 candidate
  replicates and is older than 2C (it concerns the existing "partly unsecured detention sector" sentence).
- **Prompt budget.** Narrator prompt (system plus user): median 5,251 candidate against 5,309 baseline, max 6,630 against 6,326; over 5,000
  on 16 of 20 turns in both arms. **The candidate's command 5 is 6,630 in every replicate (baseline 6,310 to 6,326) and its command 2 is
  6,208 in two replicates (baseline 5,309), so command 5 is 130 over the 6,500 worst-case cap and command 2 is under it.**
  `tests/test_prompt_budget.py` passes (it measures at scene start, not on these turns). The extra on command 5 is the ticket sentence and
  the resolved tags and light lines (about 300 characters). Follow-up: compact the 2C item lines or the commitment delivery's variants.

**Defects and follow-ups (none done):**
1. Monitor light echo (4/4): apply the placement-text technique and re-probe (about 6 narrator calls per replicate to compare).
2. Commitment-turn narrator prompt 6,630 characters, 130 over the worst-case cap in live play (the baseline was already 6,326).
3. `guards` is made a new group in 2 of 20 candidate turns; declaring them in 2C would remove the one regression in Q1.
4. Not covered live: the transmit branch, the missed-window ticket text, the unmatched-header ticket text (offline tests cover them).
