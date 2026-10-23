# Phase 0 deliverable: revised 1C incident contract

Status: accepted design baseline, 2026-10-22. This document is a design
contract for Phase 1. It does not authorize runtime or package edits by itself.

## Incident

`I-1C-freight-transfer` — **The Transfer Window**

Scene: `1C`, at `freight_terminal`, with Brandon accompanying Kristin.

### Entry situation

Kristin and Brandon arrive at the freight terminal identified by Michelle's
lead. Fresh tire tracks, humming ventilation, and an abnormal electrical load
show that the abandoned terminal is active. They are at the loading docks.

The observation shaft overlooks a processing line below. A transfer of living
captives will pass through before security searches the upper level. The entry
may establish only the terminal's activity and the opportunity to observe; it
must not claim that Kristin has entered the service level, read the logistics
computer, confirmed a captive's identity, or learned a route.

The required grounding declarations are listed below. Every place or thing
named by the entry, opportunities, bridge, or delivery text must resolve in
the scene and have an explicit placement.

### Objective and free observation

Confirm that the terminal is being used to move living captives, then leave
with one advantage before the transfer window closes:

1. stronger corroboration that can support a later public case; or
2. a credible service-level approach that improves the later infiltration.

Studying the captives is a free, unconditioned observation, not an access
puzzle. It establishes `facility_proof`, `captives_confirmed_alive`, and
`michelle_possible_sighting` when the uncertain resemblance is present. The
player then has one consequential action while the transfer is in view.

## Supported outcomes

### A — secure corroboration

The player copies the visible prisoner numbers and matches them to the
missing-person records before the transfer disappears.

Assert:

- `processing_numbers_copied`
- `facility_infiltration_needed`

The observation facts remain true. The numbers are an advantage in 2A's
inspection confrontation and can strengthen the later public case. Kristin
does not learn the service-level route. The cost is represented by the absence
of `service_level_access_known`; no invented negative fact is added.

### B — secure the route

The player asks Brandon about the transfer route or directs him to use the
transit token at the service entrance while the transfer is still moving.

Assert:

- `service_level_access_known`
- `evidence_gap_processing_numbers`
- `facility_infiltration_needed`

The observation facts remain true. Brandon's useful knowledge also applies the
existing `trust_brandon` relationship change. The route is an advantage in
2A's approach confrontation and can reduce scrutiny. The cost is the existing
evidence-gap fact: the complete number set is lost when Brandon diverts
Kristin's attention to the entrance. The action is one authored outcome, not a
login, search, access, and download sequence.

The two outcomes are exclusive because the transfer is visible for one
decision window: copying requires sustained observation, while route-finding
requires Brandon to open and identify the service approach immediately. A
player may observe the captives first, but cannot complete both consequential
actions before the transfer closes.

### Missed window

If the player makes no supported choice before the authored pressure event,
the transfer leaves. The engine commits `facility_proof` and
`captives_confirmed_alive` only if the free observation occurred, then
records the pressure consequence and withdraws the pair to the terminal's safe
edge. It does not award `processing_numbers_copied`,
`service_level_access_known`, or `facility_infiltration_needed`, and it
does not force the 2A handoff. The next accepted action must create a grounded
recovery opportunity or an honest failure/return path. A deadline never
supplies an unearned advantage.

## Completion, pressure, and successor

The incident completes immediately after outcome A, outcome B, or the missed
window is resolved. Completion must not wait for a seven-turn floor. The
turn-3 security beat and turn-7 terminal sweep are replaced by one authored
pressure event tied to the transfer window; rejected proposals,
clarifications, and transport retries do not advance it. The existing
automatic `evidence_gap_processing_numbers` cost is removed from the
general captives delivery and is bound only to outcome B.

Outcomes A and B converge on `t_1c_2a` when `facility_proof`,
`captives_confirmed_alive`, and `facility_infiltration_needed` are true.
The bridge no longer requires `national_detention_network_known` or
`architects_strategy_known`. It preserves Brandon, custody, all earned
facts, and the explicit outcome provenance.

2A has two entry variants:

- with `processing_numbers_copied`: Kristin has proof but still needs a way in;
- with `service_level_access_known`: they know how to approach but have
  weaker corroboration.

Neither entry asks the player to repeat 1C. The two facts are consumed by the
2A inspection/approach confrontation, and the carried advantage remains
available to the later public-case and ending variants. No score meter is
introduced.

## Protected information and payoff

1C must not reveal JANUS, Brandon's development role, Kristin's deliberate use
as bait, Michelle's organized resistance, Michelle's confirmed location, the
full national detention network, or Charles and Rebecca's full strategy. The
uncertain Michelle resemblance is not an identity confirmation.

Kristin leaves knowing the facility is active, living captives are being moved,
and observation alone cannot rescue them. A supported outcome gives one clear
advantage and one clear loss. The scene releases into preparation for entry;
it does not ask for another search, terminal login, file opening, or repeated
access attempt.

## New or revised declarations

New physical declarations, all requiring grounding review:

- `processing_line` area under `service_level`;
- a 1C placement for the `captives` group at `processing_line`;
- `prisoner_number_record`, initially hidden at the processing line and
  revealed/moved only by outcome A;
- a traversable service connection from `freight_terminal` through the fixed
  `service_entrance` to `service_level`, gated by
  `service_level_access_known`.

New or revised story declarations:

- incident and outcome identities for outcome A, outcome B, and the missed
  window;
- `processing_numbers_copied`;
- outcome-scoped binding of `evidence_gap_processing_numbers`;
- bridge activation by either supported outcome, replacing the current C-fact
  dependency;
- 2A entry and inspection variants keyed to the two earned advantages;
- removal of the general `captives_confirmed_alive` evidence-gap cost;
- replacement of fixed turn-3/turn-7 pressure with the single transfer-window
  pressure event.

No `service_route_unresolved` fact is needed: the absence of
`service_level_access_known` is the authoritative state. The existing
`trust_brandon` and `michelle_possible_sighting` effects are retained where
their conditions occur. The Charles-and-Rebecca recording must be relocated
to a later scene with a declared physical or remote source before it can be
offered; it is not part of 1C's completion path.

## Phase 1 implementation boundary

The current package format has no first-class incident outcome or
outcome-scoped cost contract. Phase 1 must add those typed declarations and
validation before editing the 1C package. It must also add the minimum
traversal contract and the 2A consumer together with tests. This is a scoped
engine capability required by the accepted design, not permission to add
story-specific runtime branches.
