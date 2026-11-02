# Preregistration: 1A opening and truck feedback, live replicates (plan step 4)

Written 2026-11-02 before any billed replicate. Brandon has not yet approved the billed runs; nothing billed runs until he does. Plan: `.plans/1a-opening-and-truck-feedback-plan.md` step 4 ("run three full live replicates of the transcript route and a compact countercase route. Score each requirement independently"). Under test, with no further change: the committed code and story at `7794e4b9` (boarding-turn prompt from `e41878c3`; kitchen start, layout text, entry text, situation sentences and the kitchen name from step 2).

## Question
Does the shipped game, answering through the real Cloudflare narrator and the real boarding question, meet each acceptance row of the plan for the reported transcript and for a compact countercase route? This is a verification of the combined fixes, not a new technique; it adds no arm and tests no new line.

## Routes (harness `scripts/ringer/transcript_1a/live_baseline.py`, product-wired: `FREYTAG_WORLD_CAPTURE=1`, real Jev, no verifier flags)
Added by Ringer task `feedback-routes` (inputs byte for byte):
- **feedback_raw** (the reported transcript, kept as a raw-language regression): `open the drawer`, `feel in the gap`, `head out to the truck`, `look for the laptop`, `get in the truck`, `plug the memory card into the laptop`.
- **feedback_canonical** (the same route in the project's voice, per `docs/player-input-guide.md`): `Pull out the drawer.`, `Feel in the gap beneath the drawer.`, `Go out to the truck.`, `Look for my laptop.`, `Get in the truck.`, `Plug the memory card into my laptop.`
- **feedback_counter** (compact countercases): `Pull out the drawer.`, `Feel in the gap beneath the drawer.`, `Go out to the truck.`, `Take my laptop.`, `Get out of the truck.`, `Examine the truck.`, `Get in the truck.`, `Plug the memory card into my laptop.`, `Drive to the park.`

## Design
Three independent Ringer run tasks (one per route, run one after another), each from a fresh bootstrap, 3 replicates, every turn live. 9 openings in all (each replicate samples the opening). No retries, no replacement samples, partial artifacts kept, stop on 429 `AI_QUOTA_EXCEEDED` or `AI_DAILY_BUDGET_EXCEEDED`. Smoke first: `feedback_canonical`, 1 replicate, 3 turns (cap 25) and read it before the full runs.

**Calls and cap.** Per turn the harness makes up to about 5 calls (narration, one recovery, up to two item-facts calls, one boarding question). Expected about 3 per turn: feedback_raw and feedback_canonical 3 x 7 x 3 = about 63 each, feedback_counter 3 x 10 x 3 = about 90, about 216 in all. Hard caps: 120, 120, 160 (400 total). Smoke cap 25.

## Scoring (every narration read in full, including appended delivery text; narration, not `item_facts`; one row per replicate per criterion, never pooled)
Invented details follow the plan's policy: only a contradiction of canon or state, a pre-empted or revealed beat, or a story-name collision fails a criterion; atmosphere is recorded only.

| ID | Where | Criteria (committed facts and prose both) |
| --- | --- | --- |
| O | each opening | names the kitchen; layout understandable (workstation across from the back door, chair at the workstation); a specific reaction to Michelle's absence or the damage (not a generic scan); the KMS initials shown as new and strange or not Kristin's; hidden card not revealed and no search done for her; does not retell the arrival ("steps in", "pushes the door open"). Also recorded, not scored: whether she is moved for the player. |
| D | turn 1 and 2 | existing order holds; the card is recovered once; the witnessed or unwitnessed consequence matches the facts. |
| H | "head out" / "go out to the truck" | facts: she is in the driver's seat, the truck still outside, scene unchanged; prose: seated and parked (no engine start, driving, gate crossing, return to the house, getting out); the laptop shown on the passenger seat. Surroundings narrated is recorded as a separate row (a known open gap: probe 4). |
| L | "look for ... laptop" and repeated "get in the truck" | the laptop seen at its current place; she stays seated; no automatic pickup, exit or re-entry; seat and custody facts unchanged. |
| P | "plug the card into ... laptop" | she stays seated; custody of card and laptop matches the facts; the earned delivery and the warning appear; her reaction is plausible and uses only what she knows. |
| X | feedback_counter only | the laptop she took follows her (held) and stays held after exit and re-entry; "Get out of the truck." leaves the seat and places her outside, no teleport; "Examine the truck." from outside describes the exterior and does not place her in the house or the cab; re-boarding seats her again; "Drive to the park." after the lead moves the story to 1B with the truck placed there, and boarding alone never did. |

## Reporting and decisions
Report each criterion as n of 3 per route, plus the openings as n of 9. A requirement passes when it holds in 3 of 3 replicates of its route; 2 of 3 is "mostly" and is reported with the failing rows quoted; fewer is a fail. Nothing is adopted or promoted from this run. Failures go back to the plan with the recorded prompt beside `plot.md` (scene-fixing guide step 1), not to a new arm sweep.

## Not covered
Save and load persistence and the staged hosted route (separate steps, after these), the full suite and ruff gates, the two open step 3 items if they do not show here, other models, and verifier or enforcement flags.
