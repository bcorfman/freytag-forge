# Act 2 redesign: 2A, 2B, 2C as three incidents

Part of the [game reimagination plan](../game-reimagination-plan.md). Read this when
rewriting scenes 2A, 2B or 2C, or authoring their incidents. Pacing rules and the
consequence ledger are in [whole-story-pacing.md](whole-story-pacing.md).

Status: proposed design, 2026-10-31. Not canon until approved and written to
`plot.md`.

**Build shape:** each scene becomes one `incidents.yaml` entry modelled on
`i_1c_freight_transfer`: an observation that cannot be missed, two outcomes with
advantages and costs, a recovery storylet, a missed-window event and a successor
transition. Same engine path as 1C, so Act 2 is content work, not engine work.

## Why Act 2 is boring now

All three scenes end on a screen: the inspection console, the archive terminals,
the copied files. The player spends Act 2 asking machines for paragraphs. Nothing
pushes back except a supervisor who is persuaded in one line. The midpoint twists
(Kristin was bait; Brandon built JANUS; Michelle is fighting) are true and strong
but are *read*, so they land as lore.

The fix: each scene is a confrontation with a person, the documents arrive as the
*price or prize* of that confrontation, and Michelle steps out of the files and
answers.

## 2A — The Real Leak (was "False Identities")

**Open in motion.** Bridge text covers the hideout and forged credentials in two
sentences. The scene opens with the van already at the facility gate, a shift
supervisor walking out with a tablet and a frown. "Nobody scheduled you."

**Set piece.** The supervisor will not take the paperwork; he walks them to the
cooling manifold and says "Show me." The twist that makes it fun: **the fault is
real.** Kristin's Army infrastructure background is the weapon. The player
diagnoses a genuine pressure problem with her own words and hands (feel the pipe,
read the gauge, trace the vent), not credentials. A good answer earns respect; a
vague one earns a minder.

**1C payoff.** If `processing_numbers_copied`, Kristin can recognise the
processing-line codes on the supervisor's work orders (the numbers mean something
in her hands). If `service_level_access_known`, Brandon steers them past the second
checkpoint and the supervisor notices the shortcut.

**Dramatic irony.** During the inspection a camera turns toward Brandon and stays
on him. The narration shows it; neither character remarks on it (Rebecca's
observation stays protected).

**Outcomes (incident):**

- `inspection_convincing` — supervisor waves them into the infrastructure
  corridors and the inspection console. Advantage: `restricted_corridor_access`.
- `inspection_doubted` — they get through, but the supervisor logs them for a
  follow-up audit. Advantage: `restricted_corridor_access`; cost: `cover_suspected`
  (picks the harsher 2B entry variant).

**Missed window:** the supervisor's patience ends; he escorts them in himself
"to watch." Same as `inspection_doubted`. No dead end.

**Cut:** SL-2A-A hideout exposition as a scene beat (one bridge line instead),
SL-2A-B cover building, SL-2A-E reach-the-facility. Keep SL-2A-C as the incident's
storylet. Console limits sentence stays (3B needs it).

## 2B — The Audit (was "Evidence and Betrayal")

**Open in motion.** They come through the cooling-service panel into the archive
as the lights come up: the supervisor and two staff have started an audit sweep at
the far end. (Sooner and closer if `cover_suspected`.) They have a few minutes in
the stacks.

**One sharp discovery, not a search.** Kristin pulls her *own* file first (one
action). It is short and devastating: **RETAINED — predicted to lead investigators
to CORFMAN.** Below it, the build record for JANUS, author: Brandon Corfman.
`janus_known`, `kristin_was_bait` and the Brandon reveal arrive together in one
committed outcome. No chain of terminal queries.

**Set piece: the whispered confrontation.** The audit is coming down the aisle.
Kristin confronts Brandon crouched between shelves, in whispers, while footsteps
pass. Every loud move risks discovery. This is the betrayal scene, played under
pressure instead of at a desk.

**The choice (ledger).** Brandon asks her to let him delete his name from the build
record before they copy the files. "Let me fix this one thing."

- `brandon_name_kept` — Kristin refuses. Brandon complies, stung. The evidence is
  intact; trust is colder.
- `brandon_name_erased` — Kristin lets him. Trust warms; his 3B confession becomes
  the only proof of his role.

Either outcome copies the files (`copied_janus_files`, already carried into 2C).

**Release: Shelly answers.** As they slip out, the `medical_terminal` in the
archive prints a maintenance line in Michelle's private phrasing, ending in
"Shelly" (the name only Kristin uses). Kristin can type one reply. Michelle answers
once: she is alive, active, and will send a route. This is the midpoint lift after
the betrayal low. It replaces SL-2B-C's reading of old corrupted files. The uprising
plan and broadcast solution stay protected.

**Missed window:** the audit reaches them; the supervisor sees them and *does not*
raise the alarm (seed: he is one of Michelle's sympathetic workers; payoff optional
in 3A). They leave with the files; the name choice defaults to kept.

**Cut:** SL-2B-A and SL-2B-B as separate storylets (merged into the one discovery
and confrontation). SL-2B-C becomes the Shelly reply.

## 2C — Rebecca (was "The Trap Closes")

**Open in motion.** Guards close both ends of a command corridor. Rebecca walks in
herself. She has watched since the camera turned in 2A.

**Set piece: the negotiation.** Rebecca makes her offer to Brandon *in front of
Kristin*: help remove Charles, and Michelle goes free. The player can talk, bluff,
threaten or stay silent. Mid-conversation the purge order arrives on Rebecca's own
tablet, and it includes her people. Her face changes. This merges 2C.1 and 2C.2
into one live scene and gives the antagonists a face before 3B.

**Brandon's yes.** Brandon "accepts" and the guards stand down. Kristin cannot tell
if it is a ploy. (Their 2B ledger fact colours how he says it.)

**The choice (ledger), made by doing, not debating.** Released into the corridor
with the purge clock running, Kristin commits physically:

- `committed_to_transmit` — she heads for the uplink and starts sending. Cost: the
  detention sectors seal.
- `committed_to_rescue` — she heads for the transfer carts. Advantage: a cart of
  captives freed. Cost: nothing has been sent; the outside world knows nothing until
  3C. (Deliberately not a file seizure: conditional custody of `copied_janus_files`
  across 3A to 3C would need new placement logic.)

**Then Michelle changes the choice**, through the channel opened in 2B: the
broadcast system in Rebecca's office can do both, and here is the route. Because
the commitment already happened, its cost and advantage stand. Michelle expands the
options; she does not erase the decision. Transition to 3A.

**Missed window:** the purge alarm forces them out; Michelle's route arrives; no
ledger fact set (neutral 3A variant).

**Cut:** SL-2C-C's open-ended argument and SL-2C-B's separate clock storylet
(the clock is the tablet moment).

## Authoring checklist

- `plot.md` 2A to 2C rewritten first (ChatGPT Desktop prompt), then incidents,
  storylets, knowledge and handoffs.
- Declare and place the shift supervisor. Verify `medical_terminal` is placed in
  the archive (it is) and that Michelle's reply is a scoped delivery, not a new
  device.
- Three incidents, four entry variants (2B ×2, 3A, 3B). Reuse the 1C incident tests
  as templates; add only the tests the consolidation rule allows.
