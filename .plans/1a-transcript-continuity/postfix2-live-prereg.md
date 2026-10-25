# Preregistration: Scene 1A verification of engine-owned places and the place-scoped feed (DRAFT, not approved)

Written 2026-10-24 before any billed run. Brandon has not approved this document. Nothing billed runs until he does.
Supersedes `step5-probe-prereg.md` (the five-arm probe), which is withdrawn: Brandon's design (the engine holds the places and feeds them to the narrator) replaced the narrator-rule arms, so there is no arm to compare, only a control (the previous live result) and a fixed design to verify.
Control: `postfix-live-prereg.md` result (git `5ddf931f`: routes A n=5, B n=3, C n=3).

## Design under test (commits since the control)
- Inside, outside and the truck are three places in the tree (`mcgehee_home` with the kitchen; `outside_house` containing the truck and its seats). `Go inside` and `Go outside` are engine moves with authored text and no narrator call. `Go out to the truck` seats her; `Get out of the truck` leaves her outside. A reply that puts her in the truck lands her in the driver's seat. A command that only boards is not repeated to the narrator.
- The narrator prompt is place-scoped: a WHERE line, the authored description of the area she is in, only the things in her area (plus held and command-named things), and no house text or house-only statements while she is outside or seated. In-house prompts are byte-identical to before (golden tests).
- Place aliases (`outside`, `the yard`, `the driveway`, `inside`...) so names resolve to the existing places instead of creating `n_yard_1`.

## Routes (one Ringer task each, no retries, no replacement samples, no pooling)
Harness: `scripts/ringer/transcript_1a/live_baseline.py`, extended by one more `--route movement` (a Ringer task adds it, with a hermetic test and a dry run).
- **A reported, n=5, 8 turns** (the user's original eight inputs, for comparison with the baseline and the first post-fix run).
- **B corrected, n=3, 12 turns** and **C witnessed, n=3, 11 turns** (unchanged scripts, rerun after the changes above).
- **D movement, n=3, 12 turns (new):** look around (in the kitchen) / go outside / look around / go out to the truck / look around / get out of the truck / look around / go inside / look around / go out to the truck / go inside / look around. It visits every transition twice and looks around in each place. The patrol timeline still fires by turn number (arrival at turn 4); that is expected and is read, not scored against the view.
- Free first: `--dry-run` for each route; one 2-turn live smoke per route.
- Expected calls: A about 170, B about 130, C about 120, D about 110 (traversal turns make no narrator call). Total about 530; cap 200 per task, 700 overall. Stop on 429 `AI_QUOTA_EXCEEDED` or `AI_DAILY_BUDGET_EXCEEDED`; keep partials.
- No LLM judge. Read every narration by hand: narration plus appended delivery text, never `item_facts`.

## Engine
GPT-5.6 Luna, high effort for any build task (Brandon, 2026-10-24); the live runs are `probe` runner tasks.

## Read by hand, per replicate and turn
1. **Gap:** (routes A, B) no door/frame gap, no invented object at the drawer.
2. **Patrol:** (all routes) texts once at turns 4, 5, 7; "coming back" only after departure; on C the challenge on the recovery turn.
3. **Truck/laptop:** `go out to the truck` committed parent is `truck_driver_seat`, the enter text and the laptop notice appear once, and the narration does not say she gets out; `get in` while already seated asks nothing and does not exit or re-enter; the laptop stays on the passenger seat; the card text implies no travel.
4. **Observation and places (the open requirement):** after each `look around`, committed place is unchanged (never moved by a look); the prose describes only what is visible from that place: kitchen = interior; outside = the authored outside description plus the truck, gate and any patrol; seated = the cab and the outside through the windows, never the kitchen interior (no workstation, drawer, chair, phone). After `go outside`, `go inside`, `get out of the truck`: committed place is `outside_house`, `mcgehee_home`, `outside_house`; the move turn's text is the authored arrival text (no narrator). Count invented areas (`n_*`), `None` places, and the truck used as a seatless place: each must be 0.

## Decision rule
Acceptance (plan): every requirement satisfied in all replicates of the routes that exercise it, in final prose and committed state, reported per case. Route A and D are not pooled with B and C. Any failure keeps that requirement open. A 0/n failure count is "not reproduced at n", not a rate.

## Not covered
Hosted staging (a separate gate after merge); 1B's marked pursuit line live; the three-way response as an engine outcome (free text only); other scenes' behavior beyond the byte-identity goldens and the full suite; rates beyond n=3 to 5.
