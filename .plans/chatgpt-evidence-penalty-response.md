# Timer penalty paid in evidence: writing handoff

Status (2026-10-10): implemented in story data (Ringer run
`evidence-penalty-data`, codex worker; it edited the main checkout rather than
its worktree, so Ringer's own check failed on an empty worktree, and I
re-verified in place). Verification: `scripts/ringer/evidence-penalty/check.py`
matches the plan exactly; full suite 1287 passed; ruff check and format clean.
New `tests/test_evidence_penalty.py` (4 tests); two existing tests updated
(`test_markdown_story_package.py` allows the four pacing-only gap facts;
`test_pacing_handoff.py` now reads the default realization as the last entry).

Resume here: not yet done are the section 4 live replicates (three per
script/state: no gaps, each gap alone, all gaps), reading selected versus
displayed lines and the section 5 questions. No engine or runtime change.

Use four gaps in supporting evidence. Preserve the evidence that makes the
ending possible. A gap records what Kristin missed at that earlier moment;
it does not claim that no later witness or archive can supply corroboration.
The payoff makes Michelle acknowledge the weakness on the public broadcast.
That is an immediate reputational cost, not a new rescue obligation.

This uses the brief's existing forced-delivery costs and conditional pacing
realizations. I checked the world-model grounding guide, the W decisions
(especially W7's one-way fact effects), and the earlier scene-fix record in
`.plans/world-model.md`. Those support keeping the change in story data and
supplying concrete material rather than adding narrator rules. None establishes
these four penalties: the sentences below are proposed new story text.

## 1. Gaps and forced-delivery additions

Declare these four fresh boolean story facts through the existing package fact
declarations, initially unset/false. They have no world movement, custody,
visibility, or access effects. No existing story source uses these names.
Their definitions are historical losses at the named forced handoff, not
claims about the permanent contents of the entire archive.

| Scene / delivery | New fact | Why this loss fits the plot |
|---|---|---|
| 1C / `captives_confirmed_alive` | `evidence_gap_processing_numbers` | 1C.2 shows identification numbers in a brief, obscured view of the processing line. Seeing living captives does not require retaining a full record of those numbers. Keep the sighting and the later captive video. |
| 2B / `brandon_janus_role_known` | `evidence_gap_development_record` | 2B.3 puts Brandon's name in the original development records. His spoken admission survives, but Kristin loses her chance to copy that separate documentary support. Keep his later confession and its power to authenticate Michelle's evidence. |
| 2C / `evidence_ready_to_transmit` | `evidence_gap_copy_check` | 2C.3–4 explicitly distinguish obtaining sufficient evidence from deciding what to do with the copied evidence under time pressure. The package remains usable; Kristin misses a comparison of her copies with the originals. |
| 3B / `detention_locations_secured` | `evidence_gap_marked_site_list` | Rebecca's marked site list is already beside the national network controls. A hurried bargain can deliver every location while leaving Kristin no copy of the marked source list to back up Rebecca's account. No address is lost. |

Append exactly one space and the following sentence to each existing decoded
`fallback_text`. Preserve every existing character before the append.

**1C — `captives_confirmed_alive`:**

> Time runs out before Kristin can copy the full set of prisoner numbers from the processing line.

Add:

```yaml
costs:
- {op: assert, fact_id: evidence_gap_processing_numbers, value: true}
```

**2B — `brandon_janus_role_known`:**

> Time runs out before Kristin can copy the development record bearing Brandon's name.

Preserve the existing trust cost; the complete proposed cost list is:

```yaml
costs:
- {op: retract, fact_id: trust_brandon, value: true}
- {op: assert, fact_id: evidence_gap_development_record, value: true}
```

**2C — `evidence_ready_to_transmit`:**

> Time runs out before Kristin can check the copied evidence against the original files.

Add:

```yaml
costs:
- {op: assert, fact_id: evidence_gap_copy_check, value: true}
```

**3B — `detention_locations_secured`:**

> Time runs out before Kristin can copy Rebecca's marked site list.

Add:

```yaml
costs:
- {op: assert, fact_id: evidence_gap_marked_site_list, value: true}
```

Only forcing that particular missing delivery incurs its gap. A timer ending
does not charge for a selected delivery already earned. In particular, 2B can
advance through other Brandon/Michelle facts; this is not a universal tax on
every slow 2B run. Preserve the existing handoff selection behavior.

The additions are best-effort display text. The cost must persist even when
the narrator already satisfies `must_convey` and the fallback is not shown.
Do not add the penalty sentence to `must_convey` to force its display.

## 2. Ordered 3C payoff

Use the two existing events. Keep their event-level conditions, effects,
scene IDs, and turns unchanged. Add no third event. Each conditional line
contains one public acknowledgment of a gap and the existing water pressure.
Michelle speaks on the already established broadcast, so this does not require
placing Kristin beside her or inventing a receiver, anchor, or new character.
The statements refer to earlier missed collection/checking opportunities;
they do not promise that later archive publication cannot repair the damage.

For `collapse_3c` at turn 4, replace only the realization list with:

```yaml
realizations:
- when:
  - {fact_id: evidence_gap_processing_numbers, equals: true}
  text: >-
    Water seeps under the outer doors. On the broadcast, Michelle says,
    "Kristin could not copy the full set of prisoner numbers from the processing line."
- when:
  - {fact_id: evidence_gap_development_record, equals: true}
  text: >-
    Water seeps under the outer doors. On the broadcast, Michelle says,
    "Kristin left without a copy of the development record bearing Brandon's name."
- text: Water seeps under the outer doors. Charles's emergency deluge is becoming real.
```

For `routes_collapse_3c` at turn 10, replace only the realization list with:

```yaml
realizations:
- when:
  - {fact_id: evidence_gap_marked_site_list, equals: true}
  text: >-
    Rising water closes a maintenance passage behind the fleeing captives.
    On the broadcast, Michelle says, "Rebecca gave us the locations, but Kristin
    left without a copy of her marked site list."
- when:
  - {fact_id: evidence_gap_copy_check, equals: true}
  text: >-
    Rising water closes a maintenance passage behind the fleeing captives.
    On the broadcast, Michelle says, "Kristin had no time to check her copied
    evidence against the original files."
- text: Rising water closes a maintenance passage behind the fleeing captives. The remaining routes are narrowing fast.
```

The order favors the concrete missing records over the less concrete missed
check. Disjoint pairs prevent the same gap from being selected twice. All
four gaps select the processing-number line at turn 4 and marked-list line
at turn 10. Two facts can remain unmentioned; that is the intended bound.
The two default strings above are copied verbatim from `pacing.yaml`.

These lines expose no new protected plot knowledge. Kristin already saw the
processing line, received Brandon's admission, obtained the copied evidence,
and received Rebecca's locations before entering 3C. A fallback sentence being
omitted does not erase the gap fact. The payoff can be its first visible notice.

## 3. Plot and reachability check

3C.1 still broadcasts captive video, JANUS selection records, detention
locations, planning sessions, experiment evidence, and Brandon's confession.
It still answers Charles's terrorist accusation with live revolts. The missing
processing-number record is not missing video; the development record is not
the confession; the unchecked copies are not unusable files; the marked list
is not the location data Rebecca delivered.

3C.2 still preserves and distributes Rebecca's portable archive. 3C.3 still
uses the pumps, barrier, maintenance tunnel, and gate authorization. 3C.4
still publishes the archive and opens the wider rescue effort. No proposed
sentence says the complete archive is destroyed or permanently incomplete.

All existing 3C reveals retain their eligibility, subject to their existing
requirements: send the evidence package, answer Charles, publish the site
locations, confession and transfer records, secure/distribute the archive,
stop Rebecca, open the evacuation route and surface gates, receive the network
and rescue reports, and discover Phase Two. The penalties grant none of these
reveals early and retract none of their prerequisites.

With all four gaps true, the existing resolution chain is unchanged:

1. `broadcast_started`, `brandon_confession_available`, and
   `detention_locations_secured` activate `resolution_exposure_holds`.
2. `truth_no_longer_containable` activates archive preservation/Rebecca's
   capture and escape.
3. Exposure plus `captives_reaching_surface` activates network consequences.
4. `national_network_fragmenting` plus `charles_at_large` activates Phase Two.
5. Those existing outcomes activate `resolution_complete`.

No transition trigger, bridge/resolution activation, reveal `requires`, or
storylet activation may read a gap fact. Only the four realization predicates
read them. The other references are declarations and forced-cost writes.
No clock, route, resolution fallback, reveal delivery, cue, or plot line changes.
This is a source-level reachability argument, not a completed engine test.

## 4. Offline scoring matrix for the implementation

Abbreviations: P = processing numbers; D = development record;
C = copy check; M = marked site list. Every unlisted gap is false/unset.

For pacing rows, initialize an otherwise valid 3C state with the event unspent.
Exercise the real turn path at each event's due turn, first without a competing
complication. Compare the decoded text exactly with the YAML above.

| State/setup | Scene / boundary | Expected result |
|---|---|---|
| Selected fact missing at forced handoff | 1C / `captives_confirmed_alive` | Assert P. When fallback is used, preserve its old prefix and append the exact prisoner-number sentence. |
| Selected fact missing at forced handoff | 2B / `brandon_janus_role_known` | Assert D and retain the existing trust retraction. When fallback is used, append the exact development-record sentence. |
| Selected fact missing at forced handoff | 2C / `evidence_ready_to_transmit` | Assert C. When fallback is used, append the exact copy-check sentence. |
| Selected fact missing at forced handoff | 3B / `detention_locations_secured` | Assert M. When fallback is used, append the exact marked-list sentence. |
| Each selected reveal earned before its handoff | Its source scene | Its new gap remains unset; earned reveal text is unchanged. |
| Each forced reveal; narrator already satisfies `must_convey` | Its source scene | Gap is still asserted; omission of the fallback addition is allowed. |
| P | 3C / turns 4, 10 | Processing-number variant; original routes default. |
| D | 3C / turns 4, 10 | Development-record variant; original routes default. |
| C | 3C / turns 4, 10 | Original collapse default; copy-check variant. |
| M | 3C / turns 4, 10 | Original collapse default; marked-list variant. |
| P + D | 3C / turns 4, 10 | Processing-number variant wins; original routes default. |
| C + M | 3C / turns 4, 10 | Original collapse default; marked-list variant wins. |
| P + D + C + M | 3C / turns 4, 10 | Processing-number variant; marked-list variant. Exactly two gap lines if both events display. |
| No gaps | 3C / turns 4, 10 | Both default texts byte-identical to the current package. |
| All gaps, existing progress prerequisites | 3C / resolution chain | Every existing resolution event remains eligible in the same order; `resolution_complete` is reachable. |
| Any selected gap, another complication occupies its due turn | 3C / pacing collision | Existing competing text may replace the gap line; event remains spent. No promised retry. |
| Any state, event already spent | 3C / later turn | No second payoff from that event. |

Also enumerate all 16 gap combinations: turn 4 chooses P, else D, else its
default; turn 10 chooses M, else C, else its default. Compare progress-gate
eligibility with the no-gap state while holding all other facts constant.

The implementation audit should allow only the four new declarations, four
cost writes, four fallback suffixes, and four conditional realizations. Preserve
existing costs and all other decoded payload strings. No-gap equality means
the selected authored text and unaffected payloads match; stochastic narrator
outputs are not promised to match byte for byte across live requests.

## 5. Not checked; live measurements

I read the full 3C plot, the relevant earlier plot beats, delivery sources,
pacing sources, knowledge requirements, and resolution declarations. I did
not implement the proposal, replay the engine, run a matcher, or call a live
narrator. No engine change is justified by this writing task.

The configured 3C turns are 4 and 10, with minimum 10 and handoff 14. That
does not prove both lines display on every playthrough: turn ordering, scene
completion, or another complication may consume the opportunity. Measure
selected versus actually displayed lines separately.

Run three live replicates per script/state after offline checks, including
no gaps, each gap alone, and all gaps. Read the composed player-visible turns:

- Does Michelle's public admission feel like weaker evidence, even though the
  ending still succeeds? This is a proposed dramatic effect, not a proven one.
- Does narration keep the video, records, exact locations, and confession
  intact, rather than expanding a supporting gap into loss of the main proof?
- Does the payoff remain coherent if Kristin has already left the broadcast
  chamber, or Michelle has already distributed Rebecca's archive?
- Does freeform play already record or copy the supposedly missed material
  before its associated reveal is earned? If so, this cost is too broad for
  that delivery. Reject or revise that gap; do not overwrite earned evidence.
- Do protected-knowledge validation and fact persistence accept the additions,
  including when the forced fallback sentence was not shown?
- How often do pacing collisions hide the penalty, and how often does a
  no-gap control receive an invented penalty from the narrator?

If a line fails, inspect its recorded prompt beside the plot, then probe the
specific cause under the existing scene-fix procedure before adding rules.
