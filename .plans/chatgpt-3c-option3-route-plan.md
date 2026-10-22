# Scene 3C: Option 3 notification, return route, and evacuation close

Status: recommendation complete. Delivery implemented 2026-10-21 on branch `3c-option3-escape-close` (worktree `../freytag-forge-opt3`, uncommitted; Ringer run `3c-option3-escape-close`, manifest `scripts/ringer/stage7/3c-option3-escape-close.json`): new optional `CanonicalRouteEvent.delivery_text`, shown once when the event commits; `resolution_escape` carries the section 3 text; frozen fixture and `stage7-3c-carried-dry` proof regenerated; full local suite and ruff green. Brandon's relay voice approved (sent before his fate is decided). Live three-location verification pending (needs a prereg). Still unauthored: relay audibility at pumps/maintenance/surface, and post-flood maintenance access.
Source: [route prompt](chatgpt-3c-option3-route-prompt.md).

## 1. Notification

Use Brandon over the relay, within the escape-event delivery. This gives
Kristin an audible source wherever she is, while Brandon stays at the relay.
Treat the line as his message at that moment, not proof of his later escape.

Exact notification:

> Over the relay, Brandon tells you, “Reports from other detention sites are reaching the broadcast chamber. Families of the missing are calling there for news.”

Michelle calling out from the surface gates would require a committed move
from Rebecca's office and proximity to Kristin. Neither is guaranteed, and
it would not explain how Michelle learned about the calls. A bare statement
at the end of the evacuation delivery would repeat the existing cue problem:
it tells the reader something, but gives Kristin no way to hear it. Putting
Brandon's message in that delivery supplies the missing carrier.

Author the relay's reach to Kristin at the pumps, in the maintenance network,
and at the surface; the fact that Brandon maintains a broadcast does not by
itself establish that she can hear him at all three locations. Use existing
declared communications equipment if the package requires a physical receiver.
Do not invent a radio or speaker in narration.

## 2. Return route

Proposed route in one sentence: From the pumps or the surface gates, Kristin
returns through the maintenance network to Rebecca's executive office and
enters the broadcast chamber inside it.

The world-model movement contract does not require adjacency edges between
areas: `World.move` and `World._check` in
`packages/worldkeeper/src/worldkeeper/model.py` validate the destination and
placement, not a traversed route. No new connection entity is required.
“Go to the broadcast chamber.” is sufficient destination language, provided
the existing chamber resolves in scene scope and the model proposes the move.
This is not a guarantee of live model behavior.

The facility tree establishes containment, not a usable passage after the
flood. Explicitly author the continuing access through the maintenance
network before shipping this line. Keep it true after the escape event marks
the facility lost.

Exact player-visible route text:

> The maintenance network still leads back to Rebecca's executive office. The broadcast chamber inside remains reachable.

This offers a destination without moving Kristin or issuing a command.

## 3. Evacuation close and final delivery

Keep the proposed closing line. Show it when the canonical escape event sets
`captives_reaching_surface`, not when Michelle releases the gates: opening
the gates does not yet establish completed evacuation.

Exact final escape-event delivery, after its facts commit:

> The captives have emerged into Los Angeles. News drones, civilians, and local responders begin arriving. Over the relay, Brandon tells you, “Reports from other detention sites are reaching the broadcast chamber. Families of the missing are calling there for news.” The maintenance network still leads back to Rebecca's executive office. The broadcast chamber inside remains reachable.

Leave Michelle's gate delivery unchanged. The notification requires the
reports and calls to be available by this event; if their existing readiness
facts occur later, deliver the notification then instead of announcing them
early. Hearing this notification does not earn D1 or D2. Retain the two
existing cues until the corresponding player actions earn them.

## 4. Contradiction check

- Brandon's message establishes that he is alive when he speaks. It does not
  settle his later fate. If “initially uncertain” specifically requires his
  condition to be unknown at this exact moment, this carrier is incompatible
  and must not ship as written.
- “Water closes the facility around them” and the facility-lost fact are the
  route risk. The proposed access must remain possible. If either means all
  return access is destroyed, Option 3 needs that plot conflict resolved;
  sharing a tree parent cannot resolve it.
- No sentence moves Michelle from the office, moves Brandon from the relay,
  places Kristin in the chamber, or puts anyone in two places. The eventual
  Kristin–Michelle reunion still requires their actual placements to agree.
- The closing line agrees with 3C.3 only after the escape fact commits. The
  reports and calls agree with 3C.4 only when their availability is committed.

## Resume here

Confirm relay audibility, post-flood access, report/call timing, and the
intended interval of Brandon's uncertain fate in the package. Then implement
the delivery in authoring sources and verify the return from all three
starting locations under the testing runbook. Check that the escape close
fires once, the return changes Kristin's tracked place, and D1/D2 still need
their own actions. No story/runtime files were changed for this plan. No
tests or live playthroughs were run; movement source was inspected only.
