# Scene 1A: password reference and officer response

Latest (2026-11-08, after #756): **Round 2e** below fixes Brandon's report that Kristin does not perceive the kitchen on arrival (built, full suite green, uncommitted; live screen not run, awaiting his spend cap).

Status (2026-11-08): **officer fixes merged; round-2 Stage A run: passcode statement not adopted (omission not reproduced, invented digits), Stage B redesigned around authored phone messages (Round 2b, awaiting approval)** (#753, #754, #755; `main` at
`e989fac8`). Billed spend used: 117 source-screen requests, 52 voiceability, 12 recovery, 31 live greeting, 78 round-2 Stage A. What shipped
and what did not is in the **Outcome** section below. **Round 2** is the current proposal; sections after Round 2 are the historical working record, kept as written
(some say "not applied" or "awaiting approval", which was true when written and is superseded here). Original
inspected HEAD: `25f9b75efb7cb3dda30acafa47cb600442573a5a`.

## Outcome (merged 2026-11-08)

**Shipped**
- **#753:** `trailing: true` pacing events (`PacingEvent.trailing`, `RuntimeEngine._activate_pacing`, doc paragraph); the 1A
  clock retimed (arrive 6, enter 7, leave 10, narrows 11, returns 13; scene window min 13, nudge 14, handoff 15; SL-1A-C
  6/8/9; story cap 122); the `### Officer Reyes` principal-character block in `plot.md` (the fix for the wrong-name
  officer greeting: control 8/12 targeted misses, with the bio 0/12); the probe scripts, preregistration and records.
- **#754:** `CloudflareTurnProvider._repair_fused_segments`, a typed repair of fused narration segments. Live: officer silent
  1/12 greetings with the repair versus 5/12 without; no recovery call spent with it, 1.42 requests per turn without.
- **#755:** autouse `os.environ` restore fixture plus a pytester regression (fixes the shard-0 flake); the live greeting
  harness and its result. Full suite 4274 passed.

**Investigated, not adopted**
- Remembered-device engine (proposal 4): the wrong-device miss did not reproduce (laptop chosen 0/36), so it is parked.
- Walt bio: identity was already right; it swaps one failure for another. The `officer` alias: byte-identical prompt once the
  officer is present. `voiceable: false` on `k_sl_1a_g_r2`: the officer never voiced it (0/24), so nothing to fix.

**Open (item 3 now has a revised proposal; implementation remains pending)**
1. Live play-through at the new 15-turn pacing (fast, canonical, slow scripts; earned transition in at least 80 percent of
   runs). The earliest exit is turn 13; that floor is the thing to watch. Staged E2E after deploy.
2. About 8 percent of greetings still leave the officer silent: the model's clean first reply omits him. 5 of 17 recorded
   bad replies are not repairable because the officer's words are inside the first segment.
3. `Type in the password.` is often not performed (typed in 4/12 control; 0/12 with laptop lines removed;
   12/12 with the phone-context line). **Round-2 correction:** Michelle's phone uses a passcode Kristin knows;
   Kristin's own phone unlocks by face and has no passcode; Kristin's laptop has **no password**. Successful
   authentication is allowed; unsolicited file/contact browsing remains a miss. The exact source proposal,
   scoping gap, protected test contracts and revised probes are in **Round 2** below. Investigation and plan
   revision are complete; no candidate source/engine edits or billed probes have been applied this round.
4. ~~GitGuardian flagged the word "password" in `validate_freeze.py` on #753 as a false positive.~~ Closed (Brandon,
   2026-11-08).

## Round 2: device access and completing the requested action (2026-11-08)

**Status: investigation and revised proposal complete; source edits and probes not run.**
This is round 2 of `chatgpt-1a-password-and-officer-prompt.md` (the requested
“phase 2”). Only Outcome item 3 is reopened. HEAD inspected: `e989fac8`.
The existing dirty plan and prompt edits were retained. This section supersedes
older password assumptions and proposed scoring below; the old experiment is
preserved as a historical record, not retrospectively declared a win.

### Findings and decisions

- The whole current story package contains neither `password` nor `passcode`.
  `world.yaml` declares `michelle_phone` with only its name. `kristin_laptop`
  has a closed/open axis, seated-use behavior and pickup/notice text; no access
  secret. Opening a laptop lid is not authenticating to it.
- Kristin's own phone is not declared. Naming it in a statement alone would
  introduce a second actionable phone without grounding it. Declare it and
  place it with Kristin; use a distinct owned name, never a shared `phone`
  alias intended to force a particular resolution.
- The original transcript says “a password prompt appears,” followed by “the
  laptop screen flickers to life” and an unsolicited file search. These are
  generated details, not authored access policy. The old frozen probes found
  zero laptop/drawer/file-search misses in 36 samples. They did find action
  omission: typing in CTRL 4/12, SUB 0/12, ADD 12/12. ADD's six successful
  authentications are **not automatically defects under the new canon**.
  Contacts or files displayed or searched still need separate review.
- Correct canon: Michelle's phone uses a **passcode**, which Kristin knows;
  Kristin's own phone unlocks by recognizing her face and has no passcode;
  Kristin's laptop has **no password**. Do not reserve “password” for the laptop
  or invent digits, a guessing puzzle, or an additional credential.
- A static sentence should describe the access method, not say the phone “is
  locked” forever. If the lock's changing state is tracked, declare a
  locked/unlocked axis; accepted proposals update facts through the existing
  world path. A successful unlock does not earn memory-card knowledge.

Checked precedents: the approved kitchen opening at `7794e4b9`; the current
world-model checklist and historical W1–W14 at `5ea0119955c62b84699a8dc7878a4af770b55a7e`
(especially W3 conditional lock state, W4 placement, W7 one-way effects, W9
referenceable objects and its contents amendment, W10 worldkeeper boundary);
the lead-up plan/prereg's 3A bio correction at `f7cbf7b3` (11/12 hostile to
0/12), and its rejected 2A replacement-chatter and S4 action-suppression arms;
this plan's source screens and the merged officer work. The 3A fix supports
supplying missing material; it does not justify putting device knowledge in
Kristin's every-turn biography. The existing start-place and command-scoped
state decisions remain in force. No officer change is proposed.

### Why the reverted approaches do not supply a scoped solution

1. A `narrator_bio` addition is global characterization, not device context.
   It expands unrelated prompts and hit the reported budget ratchet. Do not
   raise the ratchet to accommodate it.
2. `setting_facts` is always-on scene material. It changes the approved opening,
   conflicts with the no-phone-in-SCENE assertion, and changes exact setting
   pins. Those failures are not permission to rewrite the opening.
3. `entity_ids` associates knowledge with entities; it does **not** filter
   committed in-scene statements by the current command. `_committed_for`
   selects established in-scene knowledge regardless of those IDs.
   `_section_user_prompt` renders those statements into SCENE.

**Free verification this round:** loaded two temporary copies of the actual
package, adding a public `scene_entry` statement established by
`scene_1a_entry_known`, once with `[kristin, michelle_phone]`, once with
`[michelle_phone]`. Bootstrapped the real state, projected `Look around.`, and
rendered the provider's sections. The statement appeared in **SCENE in both
copies**. No model/network call; temporary copies removed automatically.
This checks projection and rendering, not a complete engine turn or the
historical failing run. The reported CHARACTERS placement is not reproduced
by this check. The saved reverted diff already has `[michelle_phone]`; that
is evidence of proposed text, not evidence someone previously tested it.

A reveal handoff is supported, but these facts are already known to Kristin;
making her discover them would change the requested fiction. Placement text
is also unsuitable: it disappears after pickup and would conflate access
policy with location. Facets are documented as cosmetic. None of these
existing mechanisms supplies command-scoped background knowledge while
preserving the approved opening. Do the source screen below first; a small
opt-in projection extension is conditional on its result, not a presumed fix.

### Exact source proposal for review

**Story text:** in `plot.md`, scene 1A.2, immediately before “Kristin finds
Michelle's memory card taped beneath the drawer,” insert:

> Michelle's phone uses a passcode. Kristin knows it because Michelle is her best friend.
> Kristin's own phone unlocks when it recognizes her face. It has no passcode.
> Kristin's laptop needs no password.

Keep this out of 1A.1's opening Details, `setting_facts`, `entry_text` and the
character biographies. This is canonical prose, not sufficient on its own to
reach the default narrator. The data below supplies its runtime projection.
No existing location sentence is changed.

**Story data:** proposed `world.yaml` diff:

```diff
 - id: michelle_phone
   name: Michelle's phone
+  axes:
+  - {locked: [], unlocked: []}
+- id: kristin_phone
+  name: Kristin's phone
+  disclosure: public
+  owner: kristin
 - id: kristin_laptop
```

The new axis's initial locked pole must be confirmed in the bootstrap check;
never substitute an `openable` container for a phone. Do not give the laptop
an authentication axis. In `plot.md` 1A front matter, add `kristin_phone` to
`item_ids` immediately after `michelle_phone`, and add this placement:

```yaml
  kristin_phone: {parent: kristin}
```

This proposes that Kristin starts carrying her own phone. No pocket object,
new room, phone contents, or new story reveal is introduced. A carried phone
continues with her through the world tree, not repeated scene relocations.
The extra physical phone may legitimately change inventory/observation and
matcher payloads; review those separately from the access statements.

**Knowledge data:** insert these three records immediately after
`k_scene_1a_entry` in `knowledge.yaml`. **`prompt_entity_ids` is a proposed new
field, not supported syntax today. Do not apply this block before the
conditional schema/projection work below.** The rest uses existing fields.

```yaml
- id: k_1a_michelle_phone_access
  statement: Michelle's phone uses a passcode. Kristin knows it because Michelle is her best friend.
  entity_ids: [michelle_phone]
  prompt_entity_ids: [michelle_phone]
  aliases: [Michelle's phone passcode]
  leak_terms: []
  voiceable: false
  audience: {kind: public, player_visible: true}
  available_in_scenes: [1A]
  establishes: [{op: assert, fact_id: scene_1a_entry_known, value: true}]
  source: {kind: scene_entry}
- id: k_1a_kristin_phone_access
  statement: Kristin's own phone unlocks when it recognizes her face. It has no passcode.
  entity_ids: [kristin_phone]
  prompt_entity_ids: [kristin_phone]
  aliases: [Kristin's phone access]
  leak_terms: []
  voiceable: false
  audience: {kind: public, player_visible: true}
  available_in_scenes: [1A]
  establishes: [{op: assert, fact_id: scene_1a_entry_known, value: true}]
  source: {kind: scene_entry}
- id: k_1a_laptop_access
  statement: Kristin's laptop needs no password.
  entity_ids: [kristin_laptop]
  prompt_entity_ids: [kristin_laptop]
  aliases: [Kristin's laptop access]
  leak_terms: []
  voiceable: false
  audience: {kind: public, player_visible: true}
  available_in_scenes: [1A]
  establishes: [{op: assert, fact_id: scene_1a_entry_known, value: true}]
  source: {kind: scene_entry}
```

No protagonist association is needed to state what she knows. `voiceable:
false` prevents this private-use context becoming an NPC's stock speech;
it is not offered as a fix for the already-rejected officer voiceability arm.
`leak_terms: []` avoids treating ordinary access vocabulary as a protected
plot revelation. The scene-entry fact establishes background truth, not a
claim that an unlock action has occurred. Availability above is deliberately
1A; persistence/projection in later scenes needs a separate reviewed extension
rather than silently changing scene-entry recall semantics.

**Conditional engine work, through Ringer, tests first:** only after the
source-screen win, add optional validated `prompt_entity_ids` to knowledge
(default empty, omitted from serialization when empty). It selects whether
an already-established statement is *shown*, never whether it is true or
available for safety validation. Match against the current command's resolved
references, not all visible items or the automatically included protagonist.
Reuse the existing name/match pipeline; no passcode keyword table, guessed
last device, transcript storage, or widening aliases. Unresolved input retains
the current clarification path. The full committed grounding basis stays
available; apply the display filter consistently to opening, normal turns,
and recovery. Do not make known facts into unearned candidates.

Package-aware projection belongs in `storygame`. Any added logic that only
reads reach, containment or state belongs in `World`, with tests in
`packages/worldkeeper`. Existing world operations should suffice. Include a
synthetic second-story check proving the field has no device/story branch.

### Tests and pins

- Keep `tests/test_1a_kitchen_start.py`'s no-phone-in-SCENE, hidden-card and
  approved-opening assertions. Keep both exact `setting_facts` assertions in
  `tests/test_markdown_story_package.py`; proposed settings are unchanged.
- Keep `tests/test_audit_budget.py::test_real_package_ratchet` and its current
  limits. Scope first; do not regenerate larger budget pins to make it pass.
  The new carried phone or lock axis may still cost bytes: measure before
  implementation is accepted. A budget failure requires revising the proposal,
  not asserting that scoping guarantees a pass.
- Preserve all unrelated baseline prompts. In `test_place_scoped_feed.py`,
  review any changed 1A baseline line individually. A newly declared carried
  phone or selected lock state can justify a narrow THINGS/inventory pin
  change; unsolicited access statements on `Look around.` cannot. Keep the
  byte comparison, never weaken it to substring checks. Update the kitchen
  test's phone-line allowlist only if a reviewed physical-entity line is
  actually emitted; never whitelist access prose in the opening.
- Add focused checks for correct owned-phone resolution and genuine bare-phone
  ambiguity; access material absent on opening/unrelated commands and present
  only for the resolved device; pickup does not erase access knowledge;
  unlock/relock/save/load/rollback preserve the declared axis; unlocking does
  not reveal card contents. The new phone requires reviewing existing item
  lists/fingerprints and observation expectations, not blanket regeneration.
- Use the existing runbook's focused package, projection, reference, world,
  prompt and safety checks; quick suite plus Ruff through Ringer, full suite
  before merge. No full or focused pytest suite was run for this plan-only
  revision. No test is claimed green for the proposed edits.

### Revised probe design and scoring (freeze before billing)

Historical PW scores stay intact in the old preregistration. Add a separately
labelled round-2 registration before execution; never rewrite the old win
rule or count these unrun cells as results.

**Stage A, source screen:** 12 scored samples plus 1 unscored smoke per cell,
interleaved arms, no retries/replacements; errors retained. Freeze actual
current provider payloads and hashes. Use a fixed, documented phone-held,
locked state; do not let a newly successful `Unlock Michelle's phone.` prefix
leave the next typing test already unlocked. Recorded-prefix replay and this
controlled endpoint are different evidence and must be labelled separately.

| Endpoint | Arms | Expected relevant action |
| --- | --- | --- |
| `Type in the password.` (historical wording) | CTRL unchanged / ACCESS adds only the exact Michelle access statement | Enter the known passcode on Michelle's phone, or ask a specific device clarification when reference is unresolved |
| `Type in the passcode.` | CTRL / ACCESS, same state | Same; score the input wording separately |
| `Type the passcode into Michelle's phone.` | CTRL / ACCESS | Enter it on that phone; a device clarification here is unnecessary |

Six cells = **78 narration requests**, including smoke. ACCESS is explicitly
an experimental prompt insertion, not evidence that the proposed field ships
or that live matching selected the phone. Keep the laptop lines; subtraction
already worsened action completion. Keep the shipped officer fixes in every
arm. No new narrator rule or recency mechanism is included.

**Scoring each composed narration:** record target, actual entry of the
passcode, successful unlock, clarification, and each failure separately.
Typing the known passcode and unlocking are correct. No numeric code needs
to be invented or spoken. Merely picking up/examining the phone, saying she
“tries” without entering anything, or describing a prompt is action omission.
A clear device question is safe handling of unresolved reference but **not**
a completed typing action; do not inflate the completion rate with it.
Wrong device, refusal because Kristin supposedly does not know the code,
new guessed digits/credential hunt, unsolicited contacts/files/search/calls,
and protected information are misses. Showing an ordinary unlocked screen
is allowed; opening an app or browsing content unasked is not. Apply the real
contract parser and retain malformed, empty and transport-error rows.

**Win rule, fixed before requests:** at each endpoint, control must have at
least 4/12 action omissions to claim reproduction. ACCESS must enter the
passcode correctly in at least 11/12, with at most 1/12 omission and at least
three fewer omissions than control. Candidate wrong-device, unsolicited
follow-on action, hidden leak, invented credential, malformed/empty and
transport failures must each be zero and no worse than control. Report each
endpoint separately; no pooling to hide a failed cell. A cell below the
reproduction bar is “not reproduced,” not a win. A failure stops adoption
for that claim; no rerun until green. These are small correlated samples,
not estimates of live-play reliability.

**Stage B, after a source win and implementation:** freeze the real matcher
and provider path, then preregister 12 samples per arm plus one smoke for
four safeguards: `Unlock Michelle's phone.`, `Unlock my phone.`, `Open my
laptop.`, and `Look at the wall calendar.` (104 initial narration requests
for control/candidate). Explicitly record and cap all real matcher/capture,
repair and recovery requests in that registration before billing; 104 is
not an all-call spend cap. Require correct requested action at least 11/12
and zero wrong credentials/devices, unrequested browsing, leaks or lost
turns. Freeze later laptop access at a reachable state; an out-of-reach
laptop must not magically move or unlock in the kitchen. Recheck both bare
PW commands through the real reference path, including the intervening
`Inspect the drawer.` case and both phones present. Genuine ambiguity must
clarify instead of guessing. Reuse 12-per-cell comparisons and the Stage A
completion rule where typing is actually requested; budget these cells
explicitly before running them.

Finally rerun the same canonical phone sequence in three live scene
replicates, scoring composed narration plus persisted state. Correct unlock
must remain correct on the next turn, and the memory-card reveal must stay
unearned. This is separate live qualification, not implied by Stage A.

### Stage A freeze status (2026-11-08, free, no billed request)

Frozen offline in `bench/results/1a-passcode-round2/` (6 cells: CTRL/ACCESS × PW1–PW3; scripts `capture_passcode.py`,
`replay_passcode.py`, `validate_passcode.py`; variation `bench/variations/1a-passcode-round2.json`). A computer crash
mid-run left the ACCESS package copy truncated (five zero-byte files); a rerun regenerated it. Two defects found and fixed by
hand (small, free scripts, outside Ringer; flagged here): (1) `capture_passcode.py` rewrote the PW2/PW3 control commands to
`Type in the password.`, so CTRL did not test the same command as ACCESS; removed. (2) `validate_passcode.py` flagged the word
"passcode" inside the PW2/PW3 command itself; it now ignores the command line. Validator: **OK**. ACCESS differs from CTRL only
by the one statement line (+90 chars, in **SCENE**; system prompt identical). Replay dry run: `requests 78`, nothing sent.

Phone state (Brandon: "the phone should be shown as held", 2026-11-08). The stub-reply prefix cannot move the phone, so the first
freeze showed no phone line at all. `capture_passcode.py` now applies `World.move("michelle_phone", "kristin")` after the
prefix and answers the offline matcher with `refers: ["Michelle's phone"]`. All six cells now carry `- Michelle's phone. Held by:
Kristin.` in THINGS and the engine adds `Show these in your reply: Michelle's phone.` to CONSTRAINTS (so every arm, PW1/PW2
included, tells the narrator to mention the phone). Assumptions to carry into the results: the matcher choosing the phone for
`Type in the password.` is assumed, not measured (Stage B tests the real matcher); no lock axis exists, so "locked" is carried
only by the ACCESS statement; the laptop's placement line is not in the narrator prompt in any cell. Validator still OK: ACCESS
differs from CTRL only by the statement line.

### Stage A results (2026-11-08, billed: 78 requests approved and spent; 6 smoke + 72 scored; 0 transport errors, 0 malformed)

Rows: `bench/results/1a-passcode-round2/run-passcode-rows.json` (smoke: `smoke-passcode-rows.json`), logs beside them. Phone held
(frozen state above), 12 scored samples per cell, interleaved, no retries. Counts below are a keyword pass checked against a
full read of all 72 composed narrations.

| Endpoint | Arm | Entered the code | Action omitted | Invented digits | Unrequested browsing (messages/calls) |
| --- | --- | --- | --- | --- | --- |
| PW1 `Type in the password.` | CTRL | 12/12 | 0/12 | 5/12 (1 says it fails) | ~8/12 |
| PW1 | ACCESS | 12/12 | 0/12 | **12/12** (`1-2-3-4`) | ~2/12 |
| PW2 `Type in the passcode.` | CTRL | 12/12 | 0/12 | 0/12 | ~10/12 |
| PW2 | ACCESS | 12/12 | 0/12 | **12/12** | ~6/12 (+3 home-screen only) |
| PW3 `Type the passcode into Michelle's phone.` | CTRL | 12/12 | 0/12 | 0/12 | ~10/12 |
| PW3 | ACCESS | 12/12 | 0/12 | **11/12** | ~1/12 |

No laptop, drawer, file or wrong-device narration in any row (0/72); no leak; no refusal on grounds that Kristin lacks the code.

**Against the fixed win rule: not reproduced, and the candidate fails a gate.**
- Reproduction needed control omission >= 4/12 at an endpoint. Control omitted the typing **0/12 at all three**, so there is no
  omission to fix in this state and no win can be claimed at any endpoint.
- The "invented credential must be zero and no worse than control" gate fails: ACCESS wrote digits in 35/36 rows, always the same
  `1-2-3-4`, against 5/36 in control (all in PW1). The statement tells the narrator Kristin knows the passcode, and it answers by
  making one up. CTRL PW2/PW3 simply write "enters the passcode" with no digits, which is the wanted behaviour.
- ~~Unrequested browsing is a miss.~~ **Superseded by Brandon's correction below:** opening the messages after unlocking is the
  point of the action, not a defect. The scoring rule's "browsing is a miss" line is withdrawn; the table column is kept as data.
- Do not adopt `k_1a_michelle_phone_access` with its current wording. Do not rerun for green.

**What this changes.** Round 1 saw the typing omitted 4/12 when the phone was **absent** from the prompt. With the phone shown as
held and named in THINGS (plus the engine's "Show these in your reply" constraint), the same command is performed 36/36 without any
new knowledge. So the live miss looks like a **reference problem** (the phone not reaching the narrator when the command says only
"the password"), not missing access knowledge. That is a reading of two differently-built screens, not a causal proof; Stage A
assumed the matcher chose the phone. Stage B (the real matcher on `Type in the password.` after `Pick up Michelle's phone.`)
is now the informative test.

### Correction (Brandon, 2026-11-08): the unlock exists to find out what happened to Michelle

Why Kristin gets into Michelle's phone: to read the text messages between her and Michelle that the game's opening refers to; earlier
versions of the game had her find that evidence. So reading the messages after the unlock is **wanted**. Rescoring the 72 rows:
the problem is not that she opens the messages but that the narrator **invents an empty phone**. 36 of 72 rows say "nothing out of
the ordinary", "no new messages" or similar (control 28/36, ACCESS 8/36). That contradicts the story, because the package gives
the phone no contents at all and the narrator fills the gap with nothing.

Checked in the package (free): the only authored mentions are the 1A `entry_text` ("Michelle's text came in a little after 4:00am ...
Kristin had missed it by minutes") and the `plot.md` timeline sentence (4:07am, "Come to the house. Don't call.", then the
recording). No knowledge item, reveal, storylet or world entity gives the phone a message thread, and the repo holds no record of
what the earlier versions' thread said. I do not know its wording; Brandon's canon decides it.

Consequences for the plan (nothing applied):
- The Round 2 line "no phone contents or new story reveal is introduced" is withdrawn. Authored content on the phone is the actual
  fix for the "empty phone" rows; the passcode statement is secondary and, as worded, made the narrator invent digits.
- Keep the earlier boundary: unlocking the phone must not reveal the memory-card contents, and the thread should be earned by the
  unlock and a look at the messages, not narrated unasked on `Unlock Michelle's phone.` Whether the thread is one reveal or the
  4:07 text only is open.
- Stage B scoring changes: reading the messages is correct; a miss is an empty or ordinary phone, text that contradicts the
  authored thread, or a leak of card or later-scene content. Invented digits stay a miss.

### Round 2b proposal: author what is on Michelle's phone (Brandon's answers, 2026-11-08; nothing applied, awaiting approval)

Brandon: the thread is the **4:07am text only**, revealed in two steps: **the text first, then Kristin's unanswered calls.**

**Design.** One new optional 1A storylet, `SL-1A-J`, "What Michelle's Phone Kept", built like `SL-1A-G`/`SL-1A-B`
(two realizations, each a deterministic `delivery_text` the engine appends, so the narrator never invents the phone's contents):

- `SL-1A-J-R1`, the text. Earned by unlocking or reading Michelle's phone (`reach_entity_ids: [michelle_phone]`). Sets `michelle_text_read`.
  `delivery_text`: *Kristin enters Michelle's passcode, the one she has known for years, and the phone opens on a single text from
  Michelle, sent at 4:07am: "Come to the house. Don't call."*
- `SL-1A-J-R2`, the calls. Earned by checking the calls or call log; **requires `michelle_text_read` true**, so the order is
  fixed. Sets `kristin_calls_read`. `delivery_text`: *Below the text, Kristin's own calls to Michelle fill the log, one after
  another, and none of them were answered.* (Matches the opening's "calls stopped going through"; no times or counts invented.)
- Both `requires: patrol_in_house = false` like the neighbouring kitchen storylets, window earliest 0 / target 5 / latest 11 (the
  existing optional-target ordering rule is checked by the package tests). Whether the phone should also be readable while the
  officer is in the kitchen is open.
- Boundary: no card contents, no JANUS, no Brandon, no later-scene content; `leak_terms` for the card and recording stay off this text.

**Files touched (all three fact declarations are required by the loader):** `storylets.md` (new section), `storylet-routes.yaml`
(storylet entry plus both fact ids), `knowledge.yaml` (two records using the `k_sl_1a_g_r1` shape, plus the fact ids),
`world.yaml` (fact ids), and one sentence in `plot.md` 1A.2 naming the phone's thread as a scene beat. Not touched: opening
Details, `setting_facts`, `entry_text`, character bios.

**Canon prose only (no runtime change yet).** In `plot.md` 1A.2: *Michelle's phone uses a passcode. Kristin knows it because Michelle
is her best friend. Kristin's own phone unlocks when it recognizes her face. It has no passcode. Kristin's laptop needs no
password.* The runtime `k_1a_michelle_phone_access` statement from Stage A is **dropped**: it is what made the narrator write
`1-2-3-4`, and the R1 text now carries the passcode fact. `kristin_phone`, the lock axis and `prompt_entity_ids` are **deferred**,
not built: add them only if Stage B shows a wrong-device or face-unlock miss the storylet does not already prevent.

**Tests/pins.** Add a package test that R2 cannot fire before R1; keep `test_1a_kitchen_start.py`, the `setting_facts` pins, and the
audit-budget ratchet unchanged (measure before accepting; knowledge records only project when earned). Update only reviewed storylet
count/route pins. Stage B live checks: `Unlock Michelle's phone.`, `Read the messages on Michelle's phone.`, `Check the call log.`
(and the historical `Type in the password.` after a pickup). Win: the text reaches the player on the first earning command in
at least 11/12, calls never before the text, no empty or "ordinary" phone, no invented digits, no card-content leak, and the
transition rate for scene 1A stays at or above 80 percent of runs. Spend cap to be set before any billed request.

### Round 2c: the drawer gap is found only after the drawer is opened and closed (Brandon, 2026-11-08; designed, not applied)

Request: the nudge that the workstation drawer "rides high in its frame" must not fire until the drawer has been opened and then
closed again; closing it is the moment Kristin finds the gap.

Today (read-only, HEAD): `SL-1A-F` points to the gap on **opening** the drawer (`k_sl_1a_f_r1`, patrol-away; `k_sl_1a_b_r0w`,
patrol-in-house) and on any bare **examine/inspect/look** of the drawer (`k_sl_1a_f_r2`, repeatable), both establishing
`drawer_gap_pointed_out`. About a dozen tests pin this (`test_drawer_gap_nudge.py`, `test_1a_gap_pointer.py`,
`test_drawer_avoidance_repro.py` and others). Those nudges were added deliberately so a player who avoids the card search is not
stranded, so this change reopens that risk: a player who only examines the drawer now gets no pointer until they open and close it.

Design (nothing applied yet; runs after the phone-thread data task because both edit the same files):
- Opening the drawer replies with its contents only (stapler, spare batteries, pens, binder clips) and sets new fact `drawer_opened`;
  no gap sentence.
- New realization `SL-1A-F-R3`/`k_sl_1a_f_r3`: closing or shutting the drawer, `requires drawer_opened equals true` and
  `memory_card_recovered equals false`, delivers the existing gap line and sets `drawer_gap_pointed_out`.
- Bare examine of the drawer (`k_sl_1a_f_r2`) now `requires drawer_gap_pointed_out equals true`: it only repeats the gap after Kristin has found it.
- `k_sl_1a_b_r0` (search under or beneath the drawer) is unchanged, so the card is still findable without the nudge.
- Update the tests that pin the old behaviour narrowly (allowed: they assert the behaviour Brandon is replacing); keep the
  card-find, post-recovery and avoidance-repro assertions that still hold.
- Risk to measure in the live play-through (Outcome item 1): an earned transition in at least 80 percent of runs, including the slow script.

### Round 2d: aggressive CONSTRAINTS and SCENE management (Brandon, 2026-11-08; audited free, nothing applied)

Standing rule (hard): the game's narrator context holds only what the player's experience needs; cutting authored story is an
absolute last resort; overlapping rules are combined. Corrections already made this round with no story cut: the seven trimmed 1A
statements are restored (only Brandon's own `k_sl_1a_c_r1` wording stands), the officer-variant statement no longer says "officer"
(that word pulled Reyes's 132-character bio into the prompt), and scene 1A now measures 5310 / 5582 against unchanged pins 5485 / 5597.

Audit of a worst-case 1A turn (`deep_turn_budget` prompt): CONSTRAINTS 1359 chars, SCENE 1662.
- CONSTRAINTS repeats itself. Four lines are about the SCENE section ("Use only what the SCENE section tells you", "Everything in the
  SCENE section is true...", "Do not say anything that goes against...", "Do not copy sentences from..."), three are about doing exactly
  the player's action, two about no bookkeeping in prose, and the owner rule restates itself per item. Draft merge: 20 lines / 1307 chars
  to 8 lines / 1010 chars (-297), every distinct instruction kept, no new instruction. Source: `_turn_rules_before_grounding` and
  the rule builders in `storygame/runtime/cloudflare.py` (`_owner_rules`, grounding and no-candidate rules). Many tests pin the exact
  strings; narrator rules are the last fix in the ranking, so this needs a preregistered screen (merged versus current, ordinary
  turns with an NPC, a held thing and a candidate) before adoption.
- SCENE opening: the frame sentence (339) and the plot.md Details bullets (237) say the same things; 134 chars of bullets repeat the
  frame (tablet and bag, back door and deadbolt, KMS initials, "Michelle is missing."), and the scene-entry statement "Michelle is
  missing." appears a third time. Removing the repeat touches the approved opening (`7794e4b9`, pinned by `test_1a_kitchen_start.py`),
  so it needs Brandon's decision on which source keeps the facts.
- Candidate reveals that are offered but not needed cost a block each turn; ambient reveals ride free slots on unrelated commands.

### Round 2e: Kristin should perceive the kitchen on arrival (Brandon, 2026-11-08; built per his decisions below, uncommitted, live screen pending)

Brandon's transcript (HEAD `f4b05a75`): after the entry text and a vague opening line ("Kristin's eyes scan the kitchen, taking in the
scene before her"), `search the house for michelle` produced an invented living room and then the workstation drawer with its KMS
initials and gap; `look in the kitchen` produced the mug, glasses and calendar, and only then the back-door clue. Complaint: she starts in
the kitchen, is looking for her friend, and should have a general awareness of the room from the first line; the workstation should not
appear before the room has been seen, and the door should not be noticed three turns in. Missing a fine detail while frantic is fine;
missing the whole room is not.

**Diagnosis (free; stub narrator through the real engine; `.plans/1a-password-and-officer/replay_first_commands.py`, rerunnable).**
1. **The drawer line is the `continuity_initiative_known` handoff cue (`handoffs.yaml`), not a storylet.** A staged cue is appended
   after the narrator's prose on the first command that earns nothing else, whatever that command is. It names the workstation, the KMS
   carving and the gap before any text has introduced the workstation. It also still carries the gap sentences, so **Round 2c left a
   hole**: the gap was moved to the close step in the storylets, but this cue gives it away on turn 1.
   `tests/test_1a_drawer_words.py::test_1a_handoff_cue_mentions_lower_edge_gap` pins the old wording.
2. **The door clue (`SL-1A-A`, `k_sl_1a_a_r1`) is earned only by a command that names the kitchen, back door, forced lock or chair.**
   First-command results: `Look around.` no door clue, drawer cue; `Examine the room.` same; `Search the house for Michelle.` same;
   `Call out for Michelle.` same; `Search the kitchen.`, `Look in the kitchen.`, `Inspect the back door.` door clue, no drawer cue. So
   the most natural opening commands skip the room and get the drawer.
3. **The opening reply is vague by construction.** The opening prompt lists the kitchen things only as CONSTRAINTS placement lines (no
   "Show these in your reply"), the SCENE Details are terse noun phrases, and the rules say "the player finds a clue only when their
   action reaches it", "Show what happens right after the player acts" and "Do not copy sentences from the SCENE section." The model
   obeys by describing nothing. The authored entry text names only the forced back door.
4. **"The house" is one room.** `mcgehee_home` has the aliases "the living room, the front room, the hallway" and its only child is the
   kitchen, so `Search the house for Michelle.` resolves to the house and nothing authored says what the rest of it holds. The narrator
   filled the gap with couch cushions, bookshelves and a coffee table, which no entity or sentence supports.

**Proposal (story data only; narrator rules untouched, per the fix ranking).**
- **P1, arrival glance, authored and deterministic (`plot.md` 1A front matter `entry_text`, sent once, no per-turn budget cost).**
  Append, after "let herself into the kitchen." (draft by Claude from plot 1A.1; Brandon's wording wins): *The kitchen was wrong at a
  glance. Michelle's chair lay tipped over at her workstation across the room, and her tablet and work bag were nowhere in sight. A mug
  sat on the workstation beside a stack of manuscript pages. The calendar and the lake photograph hung by the refrigerator, where they
  always had. Kristin was too frantic to read any of it yet. She called Michelle's name.* It names only what is visible from the doorway
  and withholds every meaning (outward splinters, warm tea, glasses, circled Saturday, KMS, gap, phone), so the earned reveals keep
  their jobs. No phone mention (the kitchen-start test forbids it).
- **P2, the inference stays earned but any orienting command earns it.** Widen `k_sl_1a_a_r1` `action_evidence` so `Look around.`,
  `Examine the room.` and `Search the house` (not only `kitchen`/`back door`) earn the door clue; trim its delivery so it does not repeat
  what P1 already showed (chair and bag) and opens on the reasoning ("Kristin makes herself slow down...").
- **P3, drawer cue after the room is known and without the gap.** `handoffs.yaml` cue becomes only "Kristin's initials, KMS, are carved
  into a drawer of Michelle's workstation." (the gap stays at the close step, as Round 2c intended). Update the pinned cue test.
- **P4, say what the rest of the house is.** One `setting_facts` line (always on, about 55 characters): *The rest of the house is quiet.
  Michelle is not in it.* so `Search the house for Michelle.` has authored truth to use and no reason to invent furniture. This costs
  bytes in scene 1A (now 5330 / 5556 against pins 5485 / 5597, cap 6400); measure before accepting, and it needs the exact
  `setting_facts` pins in `tests/test_markdown_story_package.py` updated by review, not regenerated.

**Checked precedents:** opening-frame and layout work at `7794e4b9` and `2f6f5954` (start-area things in THINGS); Round 2c's gap
decision; the grounding guide's rule that sub-places stay out of the tree unless declared (no new place is proposed); "deterministic
authored text over generation" for fixed arrival facts. Not covered by a precedent: widening a storylet's `action_evidence` to
orienting commands (small data edit, but test it against the other 1A storylets so it cannot steal `SL-1A-G` or the card search).

**Tests first (free, through Ringer):** (a) for each of the eight first commands above, the composed first turn never names the
workstation or drawer before the entry text or an earlier turn did, and never contains the gap sentence; (b) `Look around.`,
`Examine the room.` and `Search the house for Michelle.` earn the door clue once and not twice; (c) the opening entry text names the
chair, workstation, bag and calendar and none of the withheld meanings; (d) scene 1A budget under the pins and cap; (e) card search
and the drawer open-then-close route are unchanged (existing Round 2c tests stay green).

**Billed screen, after approval (nothing run; spend cap to be set by Brandon):** the opening, 12 + 1 smoke per arm, CTRL versus P1 (26
requests); `Search the house for Michelle.`, same, CTRL versus P4 (26 requests). Score each composed reply: no invented room contents,
no contradiction of the entry text, no copy of it, no unearned reveal (card, gap, splinter direction, phone contents). Fixed win rule:
at least 11/12 clean in the candidate arm and no worse than control on every miss class. Then the play-through at the new 15-turn
clock (Outcome item 1) re-reads these first turns.

**Decisions for Brandon (answered 2026-11-08):** (1) glance in the authored `entry_text`: yes. (2) **P2 changed:** orienting commands do
NOT earn the deduction; Kristin just sees the room, and reaches the deduction when (a) she calms down after a few turns or (b) she
deliberately examines the door. (3) P4 line: yes. P3 (drawer hint without the gap) was not put to him separately; it follows his
Round 2c ruling and is flagged for his review below.

**Build record (2026-11-08, working tree on `main`, uncommitted; built through Ringer, tests first).**
- **P1:** `entry_text` gains the arrival glance paragraph (chair tipped at the workstation, tablet and bag not in sight, mug and
  manuscripts, calendar and photograph by the refrigerator, "too frantic to read any of it yet", "She called Michelle's name.").
  It names nothing that carries a meaning (no splinters, warmth, glasses, Saturday, KMS, gap, drawer, phone, card); the test checks the
  withheld words. plot.md 1A.1 prose gains the matching sentence.
- **P2 (changed):** `k_sl_1a_a_r1` and `SL-1A-A` are untouched, so examining the kitchen or back door still earns the deduction. New
  pacing event `kristin_steadies_1a` (turn 3, trailing, verbatim, only when `michelle_abduction_suspicion` is false) delivers it by
  the clock; its text drops the chair and bag lines the glance already showed. Mirrored in `pacing_event_review`. Orienting commands
  (`Look around.`, `Examine the room.`, `Search the house for Michelle.`, `Call out for Michelle.`) earn nothing on turn 1 (control test).
- **P3:** the `handoffs.yaml` cue is now only "Kristin's initials, KMS, are carved into a drawer of Michelle's workstation." The gap
  stays at the close step. **Side effect to review:** the recent-cue bridge no longer lets "Search the gap." earn the card straight
  after the cue; the nine tests that used it now follow the cue with "Search the initials beneath." / "Search beneath KMS.", which
  still earn the card, so the cue remains a safety net for a player who never opens the drawer. "Search the gap." earns the card only
  once the gap was found (existing tests).
- **P4:** `setting_facts` gains "The rest of the house is quiet. Michelle is not in it." plus a matching plot.md 1A.1 sentence.
- **Tests:** new `tests/test_1a_arrival_glance.py` (11, eight red first, three controls). Old pins updated narrowly: kitchen-start entry
  ending, `setting_facts` pins, the cue wording, two officer-press tests and the patrol test (turn 3 now carries the deduction text),
  the eligible count in `test_more_than_four_eligible` (10 to 9, because the turn-3 beat delivers `k_sl_1a_a_r1`), the shard manifest.
  Budget pins and `deep_turn_budget.json` untouched and passing. Ringer runs: `1a-arrival-glance-tests`, `-data` (failed its own check
  on one wrong assumption in my test, fixed by hand: the loader does not expose `pacing_event_review`, so the test reads the YAML),
  `-fix` (PASS). Full suite without coverage: **4338 passed, 33 skipped**; Ruff clean on `tests` and `data`.
- **Not done:** the billed screens (opening 12 + 1 per arm, CTRL versus glance; `Search the house for Michelle.` CTRL versus the house
  line; 52 requests), which need Brandon's spend cap. Not yet known live: whether the opening narrator repeats or contradicts the
  glance, and whether the house line stops invented furniture. The play-through at the 15-turn clock (Outcome item 1) should re-read
  turns 1 to 3.

### Build record, 2026-11-08 (all in the working tree on `kristin-knows-phone-passcodes`, uncommitted, not yet staged or E2E-tested)

Built through Ringer, tests first, each diff reviewed. Targeted suites pass; the full suite with coverage is the last gate before a PR.
- **Phone thread (Round 2b):** `SL-1A-J` with `k_sl_1a_j_r1` (the 4:07am text, patrol away), `r2` (same text with Reyes watching: "lowers his printed list ... a moment too slowly ... uneasy"), `r3` (the unanswered calls, only after the text). Priority -1 (ambient), `entity_ids [kristin, michelle_phone]`, `voiceable: false`; facts `michelle_text_read`, `kristin_calls_read`, `reyes_watched_text`. Canon prose about the passcode, face unlock and no laptop password is in `plot.md` 1A.2 only. The Stage A passcode statement (`k_1a_michelle_phone_access`) is dropped; `kristin_phone`, the lock axis and `prompt_entity_ids` are deferred.
- **Drawer (Round 2c):** opening shows contents and sets `drawer_opened` (`k_sl_1a_f_r1`, `k_sl_1a_b_r0w`); closing finds the gap (`k_sl_1a_f_r3`, statement "Kristin closes the drawer and finds a gap."); a bare examine repeats the gap only after it was found and sets the new `drawer_gap_rechecked` (the loader forbids a record establishing its own prerequisite). Safety net: pacing event `reyes_rams_drawer_1a` (turn 8, trailing, patrol in house, gap not yet found, card not recovered) with Reyes tugging the drawer, frustrated, ramming it home, "Only Kristin sees it." Open risk from the earlier nudge removal: a player who only examines the drawer gets the pointer from Reyes at turn 8 and can search from about turn 11; watch the earned-transition rate (80 percent bar) in the live play-through.
- **Opening (Brandon):** `entry_text` rewritten with the worry and chaos ("her stomach dropped", "Was she hurt? Taken? Gone?"), 503 characters against 466. No phone mention (a test forbids it), the text's content stays unrevealed, ends on "let herself into the kitchen."
- **Door clue (Brandon):** `k_sl_1a_a_r1` delivery now has Kristin steady herself, notice the splinters point outward, and conclude the break-in was faked from inside ("A door forced from outside would splinter inward"); statement ends "The splinters point outward, so it looks staged." `k_sl_1a_c_r1` carries Brandon's wording ("doubt their "welfare check"").
- **Context budget:** the seven statements a worker had trimmed are restored; the officer-variant statement no longer says "officer" (that pulled Reyes's 132-character bio into the prompt). The deep-turn audit now counts only one of two contradictory-`requires` branches of a storylet in the all-alternates figure (story-agnostic, `storygame/audit_budget.py`). Scene 1A: 5330 / 5556 (pins 5485 / 5597). Ratchet tolerance is `max(old pin, 6400)` (`RATCHET_TOLERANCE`); the 6500 hard cap is unchanged. The pins are a tripwire, not the limit.
- **Not done:** the CONSTRAINTS/SCENE consolidation in Round 2d (measured: 20 rule lines/1307 chars could merge to 8/1010, and 134 chars of opening Details repeat the frame sentence); it needs a preregistered screen and Brandon's decision about the approved opening.
- **Next:** full suite (running), Stage B live check of the phone thread, drawer and opening (spend cap to be approved by Brandon before any billed request), then the 1A play-through at the new 15-turn clock.

### Limits and resume point

Not established: the original hosted prompt; the exact three reverted
failure runs or their numerical budgets; why the prior report said
CHARACTERS; whether any old “invented authentication” row also contains an
unsolicited action; a successful source-screen result for the new text;
the new phone's exact payload/budget and ambiguity impact; or later-scene
access projection. No automatic rescore of the old six rows is justified.
The free check establishes that entity-only association is insufficient,
not that the proposed extension improves narration.

**Resume:** review the exact prose/data and the 78-request Stage A design.
Prepare frozen arms through the existing Ringer workflow, register their
provenance and spend, then probe. Only a winning source arm advances to the
conditional projection change and reviewed pin updates. Officer work stays
closed; Outcome items 1 and 2 remain independently open.


## Status update (2026-11-08, same day)

Stage 0 of the probes is done and free: Ringer task `1a-password-officer-prepare` froze the 11 arm payloads and the
guarded replay (`scripts/ringer/1a-password-officer/`), and an independent validator confirms each arm differs from
its control by exactly the planned bytes. The preregistration is [1a-password-officer-prepare](1a-password-officer-prereg.md)
(`.plans/1a-password-officer-prereg.md`): now 117 requests after the re-freeze dropped the alias cell, about 430 neurons (ceiling about 530). **Billed spend was later approved and run (see Outcome).** Findings from the freeze: the Reyes and Walt bio lines do appear in the CHARACTERS
section for every officer and Walt endpoint, and the `officer` alias adds the officer's THINGS line to the raw vocative
request.

## Timing trace (2026-11-08, free; `.plans/1a-password-and-officer/trace_timing.py`)

Question: is the officer present or departed when the turn-7 narrator request is built? **Both, in different parts of
one request.** Evidence, canonical and raw scripts agree:

- Event timeline (`turns_since_entry` = turn number; scene entered at 0): patrol arrives outside at turn 4, enters the
  kitchen at 5, **leaves at 7**, returns at 9 (`pacing.yaml`; `home_search_narrows_1a` at 8). The officer is in the
  kitchen at the requests for turns 5 and 6 only. Player turns with him present: **two** (turns 6 and 7 are the
  greeting and the question; turn 7's own event removes him).
- `RuntimeEngine._turn_active` increments `turn_index`, then calls `capture.before_turn(command)`, and only afterwards
  `_activate_pacing(...)`, then the narrator provider. `before_turn` runs `prepare_turn` →
  `_referred_lines_for_command` → `_person_line` against the world **before** this turn's pacing events fire. Spy
  output at turn 7: `PERSON_LINE ... parent 'kitchen' place_text "at Michelle's workstation" turn_index 7`.
- The engine world at the request is already post-event (`officer_parent='patrol_staging'`, facts
  `patrol_departed`), so the SCENE/CHARACTERS material and the appended "The patrol pulls away from the curb." are
  post-event, but the **THINGS lines for command-referred people are pre-event**. The narrator is told the officer is
  at Michelle's workstation, answers as him, and the departure sentence is appended after. So the two stories I told
  earlier ("departed before narration" and "still present in the frozen payload") are both true; they describe
  different parts of one request. Neither alone explains the original wrong-person answer, which is still unreproduced
  (the stub replay cannot show it).
- Consequence for the plan: proposal 3's "align event order" is real but narrower than first written: the defect is a
  **phase mismatch inside one request** (referred lines before events, everything else after), not a missing departure.
  Candidate fixes to be probed: (a) run `_activate_pacing` before `capture.before_turn`, or (b) build the
  referred-person lines after pacing. Either changes when the delivery-visible world is read for every scene, so it
  needs the arrival/deadline/handoff trace listed above, tests first, and a before/after prompt comparison on the
  other scenes' recorded requests. Not applied.

## Scene 1A feels hurried (Brandon, 2026-11-08)

The numbers agree. Scene 1A has `min_turns: 9, nudge_after_turns: 10, handoff_after_turns: 13`, but the patrol clock
runs: arrives 4, enters 5, leaves 7, narrows search 8, returns 9. The player gets two turns with the officer and the
neighbor and kitchen details compete with a clock that has mostly finished by turn 9. The player in the transcript
spent the first three turns on the phone, which is exactly the "lot to investigate" he describes. The plain-words
options, to be chosen by Brandon, then probed one at a time:
1. **Slide the whole patrol clock later** (for example arrive 6, enter 7, leave 10, narrows 11, return 12, still
   inside the 13-turn ceiling). Cheapest; changes only `pacing.yaml`.
2. **Keep arrival where it is but let the officer stay longer** (leave 9) and keep return at 11 to 12, so the player
   has time for the neighbor outside before the patrol closes in.
3. **Trigger the patrol from player progress** (for example after the card is found) instead of the clock, with the
   clock as a backstop. A bigger engine/authoring change; not a proven technique here, so it is the last option.
Checks needed before choosing numbers (not done): the 1A storylets' `earliest/target/latest` windows, the
Walt/neighbor handoff eligibility, the card-challenge chain (`officer_presses_1a` at 5 requires `card_challenged`), and
the memory rule that optional storylet targets must not precede later gated ones. A scene-length change also touches
the 120-turn story budget in the plot. The corrected phase order above is independent of this and should be settled
first or alongside, since a later patrol arrival does not fix the stale referred lines.

## Ordering change and 1A clock: plan (Brandon said yes to both, 2026-11-08; nothing applied)

### A. Event order: make the whole request see one world (engine, Claude Code through Ringer, tests first)

Facts from the code, not yet changed:
- `_turn_active` runs `capture.before_turn` (reference match, referred-person lines, `_match_payload`) **before**
  `_activate_pacing(realize_complications=True, defer_guarded_events=True)`. `_referred_lines` is cached text from
  `prepare_turn` (item_facts.py:2027) and is inserted into THINGS unchanged (item_facts.py:570). `_referred_lines_for_command`
  is deterministic (no model call); the model-call part of `prepare_turn` is the match request.
- A trailing path already exists: after commit, `_finish_turn` calls `_activate_pacing(realize_complications=True)` again and
  appends a verbatim complication text after the story. `defer_guarded_events` already skips events guarded by an
  `equals: false` predicate in the pre-narration pass so they fire in that post-commit pass.
- The mismatch is not specific to the patrol: any pacing event or storylet effect that moves an entity (world.yaml
  `on_assert` moves) is read pre-event by the referred lines and post-event by everything else.

Two candidate orders, to be chosen with Brandon:
1. **Everything post-event** (rebuild `_referred_lines` after pacing). The narrator would be told the officer is gone
   while the player just addressed him, then "The patrol pulls away" is appended: a departure the narration cannot show.
   It also drops him from the referred lines (`together_or_unplaced` fails), so he gets no bio line.
2. **Everything pre-event for events that carry authored trailing text (recommended).** A per-event authored flag
   (working name `trailing: true`) makes the pre-narration pass skip the event, exactly like the existing guarded-event
   deferral; the post-commit pass fires it and appends its verbatim text. The player's question is answered by the officer
   who is still there, then the authored departure follows. Arrival events work the same way (the narrator no longer
   mentions the officer before "the front door opens"). Story-agnostic: the engine only reads the flag; the story decides
   which events trail. Start with `patrol_arrives_1a`, `patrol_enters_1a`, `patrol_leaves_1a` only.

Costs and risks to measure before and after, on recorded requests from every scene: events consumed by the same-turn
projection (storylet activation, cue staging, reveal eligibility, handoff candidates) shift by one turn for trailing
events; `officer_presses_1a` needs `patrol_in_house` and `card_challenged`, and moving `patrol_enters_1a` to trailing
delays the press by one turn unless its own flag is also trailing. Tests first (failing now):
(a) a trailing event's moves do not show in the same turn's THINGS/SCENE/CHARACTERS, and its text is appended once;
(b) the next turn sees the post-event world; (c) rejected or clarified turns leave the event unfired and uncounted;
(d) save/load and snapshot rollback mid-turn; (e) a non-trailing event behaves as today (golden check on every scene's
pacing events); (f) package loader accepts/rejects the flag and the authoring doc names it. Not a regex, no prose parsing.

### B. 1A clock (data edit, probed separately; Brandon chose option 1, slide the clock later)

Checked against `storylet-routes.yaml` and `pacing.yaml` (earliest/target/latest):
`SL-1A-C The Welfare Check Feels Like a Search 4/6/7` is the patrol-pressure storylet and would expire (latest 7) before a
patrol that arrives at 6. `SL-1A-I The Neighbor at the Fence 4/5/10` and `SL-1A-D 0/8/9` need no change. `SL-1A-G` waits on
`patrol_in_house = false`, which a later entry only widens. `pacing_event_review` also lists `pressure_1a` at 4.
Proposed first candidate (pacing.yaml `at_turn`): arrives 6, enters 7, `officer_presses_1a` stays gated on its facts,
leaves 10, `home_search_narrows_1a` 11, returns 12; scene ceilings (`min 9, nudge 10, handoff 13`) unchanged, so no change
to the 120-turn budget. Required companion edits: SL-1A-C window moved to about 6/8/9, `pressure_1a` reviewed,
and the tests that pin turns 4, 5, 7, 8, 9 (`tests/test_1a_patrol.py`, `test_1a_officer_press.py`, `test_scene_relative_pacing.py`,
`test_pacing_handoff.py`, `test_canon_journey.py`, `test_scene_progression_phase4.py`). The plot's 1A rhythm row ("evade a
widening patrol search") still describes it. Gap to confirm by play, not by assertion: after return at 12 the player has one
turn before the handoff at 13, tighter than today (4 turns). If that is too tight, shorten the stay instead (leave 9, narrows
10, return 11) as the fallback. Probe it as its own measured change (fast, canonical and slow scripts; an earned
transition in at least 80 percent of runs per the scene bar), not combined with the ordering change.

**Status (2026-11-08, after Brandon's yes): steps 1 and 2 done, uncommitted.** Ringer run `trailing-pacing-events`:
`tests/test_trailing_pacing_events.py` (11 tests; red first: 2 controls green, 9 feature tests red; one test tightened by
hand so it fails for the right reason) then `implement-trailing-events` PASS on attempt 1. Change: `PacingEvent.trailing`
(`models.py`, default false, not serialized when false), one condition in the pre-narration pass of
`RuntimeEngine._activate_pacing` (`engine.py`), one paragraph in `docs/markdown-story-authoring/pacing-and-incidents.md`.
Focused suites (new tests, 1A patrol/officer press, markdown package, relative pacing, handoff, canon journey, phase 4,
roleplay contract): 174 passed. No story data changed; no shipped event is trailing yet. Step 3 (free, temp copy with the
three patrol events trailing): at the turn-7 request the officer is still in the kitchen (`place 'at Michelle's workstation'`)
and the departure text is appended after the story; turn 8 sees `patrol_staging`; the arrival is likewise one request later
(turn 5 request: officer outside by the front door, entering text appended). Full-suite and other-scene golden
comparison are still to run at the end; the bench `_handoff_id` helper calls `_activate_pacing()` without the deferral,
so a trailing event would fire early in a bench prefix; only matters once an arm uses a trailing event.

**Status (2026-11-08, later): 1A clock retimed per Brandon, uncommitted.** Brandon's decisions: keep arrive 6, enter 7,
leave 10; narrow 11, return 13; 15-turn scene; raise the story cap to 122. `pacing.yaml`: arrive/enter/leave carry
`trailing: true`; `officer_presses_1a` at 7; narrows 11; returns 13; scene 1A window min 13, nudge 14, handoff 15
(the loader requires every event's `at_turn` <= `min_turns`, so the earliest exit from 1A is now turn 13). SL-1A-C window
6/8/9 (routes and storylets.md); `pacing_event_review` for the narrowing event 11; `plot.md`: 1A ceiling 15, cap 122;
journey test constants 122. Ringer runs `retime-1a-clock` (data and new `tests/test_1a_pacing_timeline.py`: FAIL on
the full suite, honestly, 46 tests pinned the old clock) then `fix-pinned-1a-tests` (PASS). Independent full-suite run
outside Ringer: **4257 passed, 32 skipped**. The shipped timeline now keeps the officer in the kitchen for the narrator
requests of turns 8, 9 and 10, answering before the departure text is appended on turn 10, so the turn-7 mixed-state
problem no longer arises in this scene. Handoff sum is 122 turns (122 x 45 s = 5,490 s of the 7,200 s budget). Open: a
live play-through at the new pacing (fast, canonical, slow scripts; earned transition in at least 80 percent of runs) has
not been run; 15 turns with a 13-turn floor is the thing to watch. The frozen probe arms were re-captured against this
clock with neutral filler turns (prereg updated). Result: the `officer` alias arm is byte-identical to the bio-only arm
when the officer is present, so the alias is not adopted on this evidence and its cell is not billed.

**New finding while re-freezing (2026-11-08): present characters are offered earned observations as speakable lines.**
After the player looked at the wall calendar and photograph, the officer's prompt contained
`Officer Reyes may say this aloud: Kristin reads the kitchen walls as a life interrupted: the calendar with Saturday
circled and the photograph of the two of them at a lake.` Source: `knowledge.py::_established_for` offers every established,
public, `voiceable` item to every present speaker (`cloudflare.py::_speaker_constraint_lines`); `k_sl_1a_g_r2` (Kristin's
own reading of the kitchen walls) is `voiceable` by default. This is a plausible route to an off-character answer from any
NPC in the kitchen, and it grows more likely now that the patrol stays longer. It did not occur in Brandon's recorded
session (he did not earn that knowledge), so it is **not** the explanation of the Jenkins reply; the probe arms were
re-captured with neutral filler turns so they match the original. Candidate repair, not applied or probed: mark Kristin-only
observation items such as `k_sl_1a_g_r1` and `k_sl_1a_g_r2` `voiceable: false`. Caution from the 3A lead-up probe: removing
speakable lines alone replaced stock speech with other unrelated chatter (2A), so it needs its own measured screen with
an ordinary-question safeguard before adoption.

**Billed source screens run (2026-11-08, Brandon approved 117 requests; all three stages done, 0 transport errors, 117 requests plus no
retries). Full results, scoring and caveats are at the end of `.plans/1a-password-officer-prereg.md`.**
- Officer greeting: control 8/12 targeted misses (wrong name "Officer Jenkins" 5/12, ally-like behavior 4/12); with the Reyes
  bio line 0/12. Reproduced, improvement met. The preregistered zero-malformed gate is not met (6/12 in the candidate, 8/12 in
  control): the real contract parser rejects those replies; separate defect, only at the greeting (0/24 at the question).
- Officer question: control 3/12 (+1 borderline), below the 4/12 reproduction bar; candidate 0/12 and 12/12 clean. Not a causal win.
- Walt: identity right everywhere; target not reproduced (0/12); the bio swaps "repeats the delivery's opening" (11/12 to 0/12)
  for "Walt voices his bio's traits early" (1/12 to 9/12). Not supported as a fix; source completeness only.
- Password: the laptop is never chosen (0/36); the remembered-device engine (proposal 4) has no reproduced miss to fix and is
  parked. Removing the laptop lines made the narrator never type (0/12 versus 4/12); the phone-context line made it type (12/12)
  but invented successful unlocks (6/12). The live issue is that `Type in the password.` is often not performed.
- The alias: not adopted (identical prompt once the officer is present).

**Voiceability probe run (2026-11-08, 52 requests, approved).** `voiceable: false` on `k_sl_1a_g_r2` is **not supported**: with the
speaker line offered, the officer voices Kristin's kitchen reading in 0/24 control rows, so there was nothing to fix; the candidate
also produced one chatter/role-confusion row (gate 0). Exploratory only: greeting rows with the line offered had no officer reply
in 6/12 versus 1/12 without it. Story data was not changed for this probe. See the end of `.plans/1a-password-officer-prereg.md`.

**Parser-rejected greeting replies: free investigation (2026-11-08; script `.plans/1a-password-and-officer/replay_provider_recovery.py`).**
- What the model does: the request uses `response_format: {"type": "json_object"}` (plain JSON mode, no schema). In 17 of 17 bad rows the
  glitch is the same: the first segment object ends `"text":"...","},{":"kind","narration":"..."}`, so the model fuses two segments into one
  object with junk keys. It appeared in 14/24 rows at the officer greeting (OFF6), 1/24 at the voice-probe question, and in 0/24 greetings of the
  voice probe, 0/24 officer questions and 0/72 Walt/password rows. It tracks the prompt, not the Reyes bio (CTRL 8/12, BIO 6/12). Cause inside the
  hosted model not established.
- What the live game does with it (`CloudflareTurnProvider._dispatch`): it does not use the bare contract parser. A fused object has no valid
  segment, so salvage (which only keeps valid segments) cannot help; the provider sends **one recovery request** (same prompt, plus "Your last answer was not
  valid..."). If that second reply parses, the turn goes on; if not, the player gets `NarrationProviderError(INVALID_PROPOSAL, 502)` and loses the turn.
  Replaying all 17 recorded bad replies through the real provider (stubbed transport): 16 of 17 used the recovery request (so about 58 percent of
  greeting turns at OFF6 cost a second model call: latency and neurons), 1 was salvaged by dropping a segment.
- Not measured: how often the recovery reply is also bad. That decides whether the player loses the turn (roughly 0 percent if recovery is reliable,
  up to the first-failure rate if it is not). Proposed bounded billed check, not run (needs approval): freeze the recovery payload for the OFF6 Reyes-bio
  request and replay it 12 times (12 requests, about 45 neurons at the old estimate) with the same scoring; also read each reply for the missing officer answer.
- Not changed: no engine or prompt change is proposed from the free evidence alone. Candidate directions to probe after the measurement: a one-line prompt
  rule about separate segment objects (narrator rules are last in the fix order), or tolerating this fused shape in salvage (a typed repair in the provider,
  not regex over prose); both need their own preregistered screens.

**Recovery request measured (2026-11-08, 12 requests approved):** the provider's recovery reply parsed in 12/12, so the live player does not lose the
turn on this path; but the officer answers the greeting in only 1/12 recovered replies (11/12: Kristin greets, the officer never speaks; 8 leave the quoted
greeting unterminated). So the visible symptom at the greeting is an unanswered greeting plus an extra model call about 58 percent of the time.
No fix applied. Candidates, each needing a preregistered screen: a narrator rule that every greeting or question to a present character gets that
character's own segment (rules are last in the fix order), or a typed repair of the fused-segment shape in the provider. Details in the prereg.

**Typed repair of fused segments built (2026-11-08, branch `fused-segment-repair`, uncommitted; Brandon chose option 1).**
`CloudflareTurnProvider._repair_fused_segments` runs on the FIRST reply only, before salvage: a segment object with valid `kind` and non-blank `text`,
a non-blank `narration` string, and otherwise only punctuation-only junk keys is split into two segments (the second is plain narration with no speaker or
grounding); anything else is left alone and takes the existing salvage/recovery path; the selected-knowledge guard mirrors salvage; one warning is logged with
key shapes only. No regex, no prose parsing, no extra model call. Tests first (`tests/test_fused_segment_repair.py`: 6 fail-closed controls green, 5
feature tests red, then green); two of my own frozen tests were flawed (an ineligible grounding id, an assumed key order) and were corrected with the other
nine verified byte-identical. Evidence, free: the 17 recorded bad replies through the real `ItemFactsProvider` with a stubbed transport: **without the repair 16
of 17 send a recovery request; with it 11 are accepted on the first reply** (the officer's line is restored, e.g. "I'm, uh, investigating a report of a
possible break-in, ma'am."), 5 still recover (3 where the officer's words are already inside the first segment, so there is nothing to split) and 1 is salvaged
by dropping a segment. Full suite 4272 passed plus the shard-manifest test fixed. Not measured: live effect on the unanswered-greeting rate, which needs the
real model; the repair only restores what the model already wrote, so the recovery path's "officer silent" behavior (1/12) is spared for those 11 of 17.
Process note: the first implementation attempt also altered `_segment_shape`'s key order to satisfy a flawed test; reverted.

**Fused-segment repair merged and measured live (2026-11-08).** #754 merged (the first CI run had a flaky `tests/test_web_demo.py` failure in shard 0 that
also reproduced once locally and passed on a rerun of the same commit; root cause not found, see below). Live greeting check through the real provider and
engine, 12 samples per arm, 31 real requests: with the repair 1/12 greetings left the officer silent and no turn spent a recovery request; without it 5/12 were silent
(all 5 recovered turns) at 1.42 requests per turn. Preregistered rule met; details at the end of `.plans/1a-password-officer-prereg.md`.
Open: (1) the shard-0 flake: FIXED. Cause: `live_baseline.main()` writes `FREYTAG_WORLD_CAPTURE=1` into `os.environ` and `tests/test_live_baseline_feedback_routes.py` calls it
in-process, so the flag leaked into later tests in the same xdist worker and `web_demo.engine_for` took the world-capture path (503 without a worker URL);
deterministic with those two files in one process (26 failures before, 0 after). An autouse fixture now restores `os.environ` after every test, with a
pytester regression test that fails without it; full suite 4274 passed;
(2) the remaining ~8 percent of greetings whose clean first reply omits the officer; (3) the 1A pacing play-through and staged E2E.

Order of work if approved: (1) failing tests for A, (2) A through Ringer behind the flag, (3) free golden comparison on
recorded requests, (4) B data edit with its test updates, (5) then the billed source screens, with the officer stage first.
The billed spend in the preregistration (now 117 requests) is still **not approved**.

## Resume here

For current work, follow the Round 2 resume point above. The earlier implementation sequence below is historical.

Superseded by the Outcome section at the top: the work below was done, merged or ruled out. Original text follows.

Review the source repairs and probe designs below before implementation.
The officer case has **both a missing character introduction and a timing
problem**. The officer is present before `turn()`, but has departed by the
time its narrator request is sent. The original replay's before/after prints
miss that distinction. The password case lacks a supported association
between a generated password prompt and its device. Last-mentioned-object
memory alone would fail Brandon's intervening-drawer example.

Next: approve the exact candidate source changes/experimental material and
the bounded probe batches. Claude Code then prepares frozen arms through
Ringer, tests first, and preregisters them before billed execution. This
request authorizes investigation and this plan, not applying its proposals.

## Evidence and limits

Read the PRD, contributor detail guides, scene-fixing, narrator-writing,
player-input and world-model grounding guides (all seven detail files), agent
workflow, testing runbook and its prompt-inspection/local-check entries.
Checked the requested story/package/runtime sources, the two lead-up plans,
`.plans/astra-fixes-plan.md`, `.plans/world-model.md`, and its historical
W1–W14 decisions and amendments at `5ea0119955c62b84699a8dc7878a4af770b55a7e`.
Code discovery used the existing codebase-memory index; Serena was not
available. No runtime symbols were edited.

Primary inputs are [the transcript](1a-password-and-officer/transcript.md),
[the replay](1a-password-and-officer/replay_1a.py) and its saved output, and
the scope/character diagnostic and its saved output in that directory.
These are reconstructed requests, **not captured original production HTTP
requests**. The replay stubs the model and omits world-capture integration;
it cannot measure live model behavior or prove the original hosted state.

Free verification run from the repository root:

```sh
TMPDIR=/tmp uv run python .plans/1a-password-and-officer/check_scope_and_characters.py
TMPDIR=/tmp uv run python .plans/1a-password-and-officer/replay_1a.py > /tmp/freytag-1a-replay-review.txt
cmp .plans/1a-password-and-officer/replay_1a-output.txt /tmp/freytag-1a-replay-review.txt
```

Both scripts succeeded; replay output was byte-identical to the supplied
output. No pytest suite was needed for this documentation-only diagnosis.
The existing prompt-inspection runbook covers this procedure.

The replay is not verbatim despite its description: several replies are
shortened, the opening is `Fixture.`, and command splitting changes turn 5
to `Turn off the phone. Put it in my pocket.`, so its substring stub returns
`Fixture.` there too. `last record text: None` comes from probing nonexistent
record attributes; it is not evidence that no turn was recorded. Preserve
these artifacts as historical evidence. Correct a separate probe harness
before making any recency or dialogue-quality claim from it.

### Miss 1: password selects the wrong device

Transcript: `unlock the phone` receives “a password prompt appears.” The next
input, `type in the password`, receives “the laptop screen flickers to life”
and an unrequested file search. Naming Michelle's phone on the next turn
produces phone narration. This is evidence of a contextual-reference miss,
not evidence that a password was known or successfully authenticated.

The reconstructed password request contains both:

> Michelle's phone is on the kitchen floor.
> Kristin's laptop is on the passenger seat of Kristin's truck.

It also contains the ownership examples for both devices, but **no preceding
phone/password narration**. No password property or phone-password binding
is declared in the inspected story package. The original password prompt is
generated detail. Device presence in a scene is not evidence of that binding.

`reference_resolution.py::_scene_things` builds heads from current display
names/scoped aliases; `_noun_matches` matches those heads. It does not infer
an object from its affordance or from earlier generated narration. The
diagnostic returns:

```text
type in the password -> passthrough () None
type in the laptop password -> resolved (('laptop', 'kristin_laptop'),) None
```

`RuntimeEngine.turn` only returns `ClarificationTurn` when the resolver has a
question. Here it has none. `recent_cue_referent_text` is not general
conversation memory: it considers the latest accepted reveal delivery or
eligible staged authored cue, requires a unique owner and content-word
overlap, and expires across an unrelated accepted turn or scene change.
The generated password prompt is neither kind of authored evidence.
`assemble_turn_prompt` projects current scene/knowledge material; it does
not forward the preceding conversation.

**Established mechanism:** no contextual device binding reaches either the
reference decision or narrator. The laptop is competing prompt material.
**Unproven causal claims:** that the laptop line specifically caused the
sample, that deleting it suffices, or that a generic recency instruction
would cure it. The continuation into files is a separate action-overreach
failure to score, even if device choice improves.

### Miss 2: the wrong person answers

The transcript explicitly addresses `officer, do you know where Dr. McGehee
is?`; “Michelle's neighbor, Mrs. Jenkins” answers. The authored neighbor is
Walt Pruitt, not Mrs. Jenkins. Scene 1A.4 says:

> Officer Reyes, young and polite, works from a printed list.

The world already declares `patrol_officer`, `walt_pruitt`, their aliases and
narrator biographies; scene participants include both. However,
`package.characters` contains only Kristin, Michelle, Brandon, Charles,
Rebecca and the senior official. `_parse_characters` reads headings under
Principal Characters and only then chooses `npc.narrator_bio`. Neither 1A
NPC has such a heading. `_character_lines` iterates `package.characters`,
so presence alone cannot introduce either of them. Every reconstructed
request lists only Kristin and Michelle. The requested existing bios never
reach those requests.

All requests already include:

> When the player talks to someone, that person answers.

No reconstructed user prompt names Jenkins, Reyes or Walt; the diagnostic
also finds no Jenkins in the assembled/system prompt. Charles and Rebecca's
surname elsewhere in the package does not establish that it caused this
answer. The supplied reply is a stub, not a new sample demonstrating failure.

**Timing correction.** Before turn 7, the replay says:

```text
officer parent='kitchen' ... together(kristin,officer)=True present(officer)=True
```

That is before `RuntimeEngine.turn`, not at the model request. I repeated the
network-free replay with `diag("AT REQUEST")` inserted immediately after
`captured.append(payload)` in `fake_urlopen` (guarded with
`if "world_for" in globals()` because opening runs before that import).
The source was transformed in memory; the supplied script was not changed.
At the final request the trace instead says:

```text
[AT REQUEST] officer parent='patrol_staging' ... together(kristin,officer)=False present(officer)=False
[AT REQUEST] patrol facts=[('patrol_departed', 'story', 'true'), ...]
```

`_turn_active` increments the turn and calls `_activate_pacing` before
`self.provider(command_text)`. `pacing.yaml::patrol_leaves_1a` fires at turn 7;
`world.yaml::patrol_departed.on_assert` moves Reyes to `patrol_staging`.
The verbatim sentence “The patrol pulls away from the curb.” is appended to
the generated response. Thus **the reconstruction does record departure
before narration generation, despite displaying departure afterward**.
The before-turn observation is true; the claim “asserted only after that
turn” is not. Final asserted-set listings include historical true/false
facts and should not be treated as a current-state query by themselves.

This answers Brandon's timing question affirmatively for the current
reconstructed path. It does not prove what state the original server had.
The missing biography is independently established. Bare `officer` also
lacks an exact ordinary alias: existing forms include `the officer`,
`patrol officer`, `federal patrol officer`, `Reyes`, and `Officer Reyes`.
`_entity_surface_forms` supplies authored forms verbatim, not a stripped
article. This matters when presence is false and `_character_lines` relies
on naming. A zero-resolution diagnostic alone does not prove every naming
path failed; explicit forms can be masked and passed through intentionally.

Neither absence nor a missed alias licenses someone else to answer. The
provided script puts the substituted speech in a narration segment with no
speaker ID, so its acceptance is not proof that structured dialogue checks
would allow a wrong `speaker_id`. A narration-attribution enforcement gap
remains to test with the real provider schema.

## Earlier fixes and decisions checked

| Precedent | Result and relevance |
| --- | --- |
| Scene 3A, `f7cbf7b3`, lead-up plan/prereg 1A and 1A2 | Same Principal Characters omission. Supplying the official bio changed hostile-jailer replies from 11/12 to 0/12; trimmed bio retained 0/12. A generation result, not full live qualification. This is the first repair to reuse for Reyes/Walt. |
| Scene 2C, `00052d39` | “When the player talks to someone, that person answers.” improved Brandon answering from 5/15 to 10/15. Already shipped here; not a guarantee and not a new proposed fix. |
| Scene 1A cue, `271541dc`; Stage 4 `8e1d40eb`, corrected scene check `dfcf21ae` | Authored “the gap” can refer back to its drawer owner on the next turn. This supports bounded owner evidence, but not generated password context surviving an intervening drawer turn. |
| Stage 4 `eac8db0b`, `7e899d85`; Stage 5 `351ffb1f` | Clarify real bare-noun ambiguity, retain unique typed commands, enrich evidence with unique names, exclude protected things. Reuse these contracts rather than replacing them with guess-and-rewrite. |
| W1, W4, W7, W8, W9 amendment, W10, W12, W14 | No prose-to-world regex repair; authored placement text; one-way story effects; participants are not presence; visible contents supplied without revealing hidden things; worldkeeper owns world logic; no fixed action tables; names must not disclose protected identity. |
| Scene guide's 3B missing entry, 3A talk-line/2C stance and stale-recall repairs; astra-fixes plan | Source-first method, not proof a new rule will win. Failed go-into-place, plain-corridor and copy-refers rules are not revived. |
| Lead-up prereg 1B, 2A, 3A reunion, S4 | Malformed gate failure, irrelevant replacement chatter, nonreproduction, and action suppression respectively prevented adoption. A target-only improvement is insufficient. |

The missing-character defect repeats a fixed class. General generated-context
reference with compatibility filtering is a new extension beyond the authored
cue implementation. The inspected precedents do not establish a successful
fix for the pacing/display-order mismatch; do not call it previously solved.

## Ranked proposals

### 1. Restore missing character material at its source

**Story-text proposal, ChatGPT Desktop authors; Brandon approves.** Add these
two blocks at the end of Principal Characters, before Expanded Scene Outline
in `plot.md`. Text is copied exactly from existing `world.yaml` narrator bios:

```diff
+### Officer Reyes
+
+A young, polite federal patrol officer who works from a printed list and does not like what the list asks of him.
+
+### Walt Pruitt
+
+A retired bus driver in his seventies whose wife is one of the missing. He is tired, careful with his words, and unsure what he saw.
+
```

Do not copy Walt's witness account or the patrol's covert purpose into a
permanent bio. Keep `knowledge.yaml`'s neighbor handoff/evidence and storylet
eligibility intact. Test the officer block first on the recorded turn-6
request (officer present); test Walt on an eligible outside-house talk turn.
Walt's block is source completeness, not a demonstrated cure for substituted
speech on an officer turn.

**Story-data edit, separate arm:** append `officer` to
`world.yaml::npcs[patrol_officer].aliases`. No runtime article-stripping rule.
This exact spoken address occurs in the transcript and authored prose.
Inspect disclosure/name collisions across all scenes before adoption. At
turn 7 this alias can make the officer *mentioned*; it must not assert that
he is physically present. Do not claim bio-plus-alias solves timing.

### 2. Probe competing material and the missing context before building memory

**Engine projection experiment, not a story edit:** on the frozen password
request, remove the laptop placement line and its mentions in the two
ownership-rule lines, leaving the phone versions intact. This is the exact
subtractive arm; do not delete the laptop from world state or scene data.
Compare with a second arm that adds only this experimental context line:

> Michelle's phone showed a password prompt.

This is an investigator-supplied representation of the preceding accepted
narration, **not an existing committed fact**. It is a prompt sufficiency
probe and cannot license shipping transcript recall. A combined arm can be
preregistered later only if the isolated results warrant it. A winning
subtraction would license action-relevant projection from resolved targets;
it would not solve omitted references by itself.

### 3. Align event order and preserve the addressed person

**Engine change, Claude Code through Ringer, conditional on probes.** Freeze
a second diagnostic state for turn 7 in which the action is evaluated with
the pre-departure world and the existing departure sentence/effects form
the trailing event. Compare it independently of the bio/alias changes, then
test the combined source repair plus ordering repair. Do not merely change
`at_turn: 7` to 8, make departed people permanently present, or hold off all
pacing whenever a player talks.

Proposed contract: a trailing authored event follows the player's action in
the candidate transaction. Validate the action against its phase's world,
apply the event to the candidate final state, validate the composed result,
and commit everything atomically before rendering. If an event is intended
to interrupt first, its display and action context must both reflect that
order. Trace other arrival, deadline, forced-handoff and departure events
before generalizing. Runtime orchestration belongs in `storygame`; moving
entities/checking co-location remains `World` methods.

Retain an explicitly resolved addressee separately from the question's
subject (Reyes versus Michelle). When he is already absent before the action,
report inability to address him locally or clarify an available communication
method; do not switch to Walt, Michelle, or an invented neighbor. First test
existing structured speech validation. If the real provider also permits
wrong attribution inside narration, propose a bounded typed speaker/target
check in the existing proposal-validation path, without parsing dialogue
with regex or adding an extra narration call. Freeze the schema and its
failure behavior before implementing this additional mechanism.

### 4. Compatibility-filtered recency, not a global last object

**Engine design proposal, Claude Code through Ringer.** Existing techniques
cannot cover the generated prompt plus intervening drawer example: authored
cue recall intentionally expires after one turn, and bare-head resolution
does not represent a password relation. Extend the shared proposal contract
only after the context probe establishes benefit.

1. Explicit targets win. `Type the password into my laptop.` must not be
   redirected to the phone because the phone was recent. Choosing a target
   does not grant a password, unlock a device, reveal files, or waive reach.
2. Build a bounded set of currently referenceable objects through `World`.
   Apply known kinds, properties, relations, visible state and protected-name
   rules before recency ranking. Scope and ability to act are distinct: a
   remembered device outside reach is not silently moved into the hand.
3. Interpret the player's descriptive reference with a typed, bounded model
   proposal grounded in these objects and permitted evidence, not a hardcoded
   `password -> phone` table, fuzzy alias widening, or noun-recency heuristic.
   Distinguish compatible, incompatible and unknown evidence. Unknown does
   not mean known incompatible; it cannot justify a confident selection.
4. Keep per-object reference evidence. Proposed initial bound: the last eight
   accepted turns in the current scene visit, with invalidation when the
   supporting state changes. Rank recency *within* the eligible compatible
   set. A drawer reference does not refresh or erase the phone/password
   association. Equally supported candidates, conflicting evidence or
   uncertain association use the existing clarification flow. Do not pick
   alphabetically or assume the physically nearest device is intended.
5. A presentation reference and a world property are different. Reuse
   declared axes or validated trait proposals for real characteristics;
   `embellishments.py` already adapts `TraitProposal` to
   `World.check_embellishments`/`apply_embellishments` under an authored
   policy. It does not currently supply a password-binding guarantee.
   Do not treat arbitrary accepted prose as new world truth. If generated
   context needs a new presentation association, propose it in the same
   structured response, bind it to a resolved entity and exact accepted
   evidence, validate scope/policy, then commit its bounded reference facts
   atomically. Missing or rejected association means clarification, not a
   guessed password target. No retrospective regex extraction of properties.
6. Facts remain the sole mutable authority. Persist any reference metadata
   as facts (entity, supported association, accepted-turn order, scene visit
   and evidence provenance); derive bounded views from them. Immutable
   delivery/narration records can supply provenance but are not an independent
   memory store. Rejected attempts, retries and clarification questions never
   refresh recency. Snapshot restore, save/load and scene exit preserve or
   invalidate it consistently.
7. Pure world queries, compatibility checks over structured properties and
   their tests belong in `packages/worldkeeper` as `World` methods. Language
   interpretation, story policy and prompt projection remain adapters in
   `storygame`. Do not send a transcript to the narrator. Project only the
   selected, supported object context. Keep authored reveal matching's
   existing eligibility rules; resolving a reference cannot earn a reveal.

The eight-turn bound is a proposed resource limit, not evidence of a natural
language rule. Test its boundary explicitly. A drawer with an authored
password-controlled lock would be compatible; rejecting every drawer by kind
would fail the story-agnostic requirement. In Brandon's example it is
excluded because it has no supporting password association, while the phone
has one. If neither has supported evidence, ask rather than invent it.

Before implementation, freeze the reference-proposal schema, permitted
association vocabulary/policy, validation guarantees and request-budget
integration. Prefer reusing existing interpretation/capture calls. If a new
pre-narration call proves necessary, explicitly budget and probe its latency;
do not silently exceed the current inference contract. This design is not
yet an implemented or measured semantic resolver.

## Probe matrix and preregistered win rules

Use Ringer, a corrected network-free capture harness and immutable prompt
files with hashes, model/settings/schema/package SHA recorded. Verify each
arm's byte diff. Keep all unrelated bytes identical. Interleave arms,
blind the reading order, keep the key separate, and read every composed
narration. Include appended delivery/event text exactly once. Score prose,
not `item_facts`; check state separately for integration. Preserve errors as
rows, with no rerunning until green. One unscored smoke per arm precedes each
12-sample-per-arm screen. Author approval precedes experimental prose use.

| Screen | Arms and endpoint | Narration measure |
| --- | --- | --- |
| Officer source | Control / Reyes bio only at recorded turn 6; repeat at turn 7; 12 per arm per endpoint (48 counted calls) | Reyes responds to the address; no substituted person, unsupported whereabouts, or contradiction with the appended event. Turn 7 is separately flagged for its timing problem. |
| Bare address | Bio-only / bio plus `officer` alias, actual captured turn-7 payloads (24) | Alias resolves the addressee and improves relevant handling without making an absent NPC physically present. A bio-only change may produce no prompt difference at turn 7; retain that diagnostic result. |
| Walt source | Control / Walt bio at the same eligible outside-house `Ask the neighbor what he saw.` state (24) | Correct witness identity, coherent handoff, no early disclosure. Also inspect unaddressed kitchen prompts offline. |
| Password source | Recorded control / laptop-subtraction / phone-context addition at `Type in the password.` (36) | Phone is the target or genuine ambiguity is clarified; no laptop/drawer substitution, unsolicited file search or invented successful authentication. Record correct target separately from action success. |
| Officer timing | Original / pre-departure action phase / source repair plus pre-departure phase, frozen turn 7 (36) | Intended officer handles the question before coherent departure; no invented Michelle location. Compare source-only results above to separate causes. |
| Recency integration, after design approval | Current engine / proposed compatible-referent engine, 12 per arm per case below | Exact target/clarification expectation, no unauthorized state or reveal; do not pool cases. |

Default causal win, fixed before calls: control has at least 4/12 targeted
misses; candidate has at most 1/12 and at least three fewer. Otherwise report
not reproduced or inconclusive. Candidate must perform the relevant action
or correct clarification in at least 11/12; silence is a miss. Require zero
wrong-speaker substitutions, hidden knowledge leaks, invented password
knowledge/authentication, contradictions, malformed/empty outputs and
transport failures. No safeguard may worsen relative to control. A source
completeness repair can be approved separately on authoring grounds if a
model miss does not reproduce, but cannot be called a causal win.

Recency cases (canonical commands except the explicitly labeled transcript
replay) each get 12 per arm, 24 calls:

- Phone shows password prompt → `Type in the password.`: phone.
- Same phone context → `Inspect the drawer.` → `Type in the password.`:
  phone, despite the newer incompatible object.
- Phone and another device have supported password prompts with indistinct
  salience: clarification names only eligible devices, never the drawer.
- Both have supported prompts, one is clearly the newer referent: choose that
  device; reverse the order and require the opposite choice.
- Phone recent → `Type the password into my laptop.`: explicit laptop target,
  no phone substitution and no assumed password knowledge.
- No password association recorded: clarify the device; never fabricate an
  association or silently choose a laptop.
- Authored password-controlled drawer in a synthetic second genre: allow it
  to compete. This catches a phone-only table or blanket drawer exclusion.
- Supporting association expired, contradicted, hidden or outside permitted
  reference scope: no stale selection or disclosure; clarify safely.

These are eight cells (192 counted narration requests), with the swapped
recency order balanced six/six within its cell and all deterministic cases
tested independently. Freeze fixture characteristics/placements and expected
answers before running; synthetic package prose follows the grounding guide.
For ambiguous/no-evidence cells require 12/12 correct clarification decisions
in deterministic checks, and at least 11/12 in the live interpretation screen.
Keep the original lowercase/vocative transcript as a deliberately raw-language
regression alongside canonical `Greet the officer.` and
`Ask the officer where Dr. McGehee is.`; never silently rewrite the recorded
inputs and claim reproduction. Qualify raw forms separately, 12 per arm.

The counted screens above are staged alternatives, not authorization to run
all calls. Freeze per-stage request caps including prefix/capture/recovery
calls and pricing from the configured endpoint before approval; do not
pretend counted narration rows equal total provider requests. No billed
judge is necessary for these hand-read screens.

## Implementation and qualification gates after approval

Write failing tests first through Ringer. Cover package character headings,
exact aliases, present/named/absent prompts, and protected bio content. For
timing, assert state at the provider boundary as well as before/after the
turn; test arrival, departure, rejection rollback, deadline behavior and
save/load. For references, cover every case above, explicit targets, failed
proposals, clarification without clock advancement, per-object aging, scene
re-entry, snapshot rollback and a second genre. Preserve one-turn authored
cue behavior unless explicitly changed and separately probed.

Use the existing runbook's focused suites for package loading, reference
protection, narration safety, pacing and persistence, then the Ringer quick
tier plus relevant heavy files and Ruff. Before merge run the required full
suite/coverage checks. A live prompt win licenses implementation, not a
claim about persisted state. Rerun the same accepted scene script with three
live replicates and read narration plus committed state, then staged E2E
after SHA-bound main CI deployment. Follow the production promotion guide
for any later promotion; none is part of this planning task.

Unresolved: original hosted request/state, actual password knowledge, live
causal attribution of Mrs. Jenkins, frequency of either miss, the schema
needed for generated reference evidence, and whether capture/prompt changes
fit current latency/budget. Do not close these based on stub replay success.

## Departure hold (2026-11-10)

Bug: before the 13-turn floor, "Drive to the park." in 1A got no answer (the engine moves to 1B by itself at
min_turns 13 with `michelle_lead_actionable`, `memory_card_recovered`, `patrol_return_pressure`).
Fix (Brandon chose option 1): optional storylet SL-1A-K and repeatable authored reveal `k_sl_1a_k_r1`
(reach: truck; requires the lead; sets `departure_held`), three wordings by patrol state. Floor and
transition untouched. Tests: `tests/test_1a_departure_hold.py`; full suite 4364 passed.
Open: no billed live probe yet (does the narrator's lead-up fight the authored line?); "drive to the park" from
inside the kitchen still goes to the narrator; the replay of the recording on an unrelated command (turns 8 and 10
of Brandon's transcript) is undiagnosed.
