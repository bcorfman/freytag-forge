**Issue 1: replace R2’s `delivery_text` with:**

> A partially recovered JANUS file labels the disappearances Phase One. Phase Two was designed to provoke conflict among those who remained. From an unknown location, Charles watches the unrest, believing frightened people may yet ask him to restore order.

This preserves the required content in three sentences. The last sentence combines Charles’s observation and belief to meet the sentence limit.

**Change `dramatic_intent` to:**

> Reveal the Phase One label and the Phase Two plan through the partially recovered JANUS file. Show Charles watching the unrest from an unknown location, hoping frightened people will ask him to restore order.

Tracing Charles must not establish his location: it remains unknown.

**Issue 2: recommend option 1, provided an existing, usable communication connection reaches Kristin.** It preserves the broadcast chamber’s role while making the reports and families actionable. The supplied plot establishes a live broadcast, but does **not** establish that Kristin can hear it or answer callers from the exit. Cue wording alone cannot supply that missing capability.

The alternatives below distinguish those staging requirements from plot contradictions.

**Option 1 — relay through the existing broadcast**

Use these cues only after establishing that Kristin can receive the broadcast and respond to families from her current position.

| Fact | Exact `cue_text` | Exact `fallback_text` |
|---|---|---|
| `national_network_fragmenting` | “Michelle's broadcast carries reports from other detention sites to you.” | “Reports from other detention sites reach the broadcast chamber. Detention sites surrender or release prisoners as the national network breaks apart.” |
| `community_rescue_efforts_begun` | “Through Michelle's broadcast, families of the missing ask you for word.” | “Families of the missing call for news. Families and communities organize independent rescue efforts. Many of the missing are still alive.” |

The existing `must_convey` phrases fit both cues. No quoted plot line is contradicted. However, receiving and answering through the broadcast is an **additional staging requirement**, not something the plot already guarantees. Do not introduce a radio or move Michelle merely to make these sentences work.

**Option 2 — direct openings at the exit**

These cues require reports to be available to Kristin and families to be present at the exit.

| Fact | Exact `cue_text` | Exact `fallback_text` |
|---|---|---|
| `national_network_fragmenting` | “Reports from other detention sites are available for you to read at the surface gates.” | “Detention sites surrender or release prisoners as the national network breaks apart.” |
| `community_rescue_efforts_begun` | “Families of the missing ask you for word at the surface gates.” | “Families and communities organize independent rescue efforts. Many of the missing are still alive.” |

For D1, replace the cue requirements with `"reports from other detention sites"` and `"read / surface gates"`. D2’s existing phrases fit.

No quoted plot line directly contradicts this staging, but the plot does not establish reports at the gates or identify the arriving civilians as families. This option therefore needs more authoring than a wording change. It also only works while Kristin is actually at the gates.

**Option 3 — preserve the chamber as the interaction site**

If no remote connection or exit interaction is supported, retain the chamber’s role and let Kristin choose to return through an established route.

| Fact | Exact `cue_text` | Exact `fallback_text` |
|---|---|---|
| `national_network_fragmenting` | “Reports from other detention sites reach the broadcast chamber.” | “Reports from other detention sites reach the broadcast chamber. Detention sites surrender or release prisoners as the national network breaks apart.” |
| `community_rescue_efforts_begun` | “Families of the missing call the broadcast chamber for word.” | “Families of the missing call for news. Families and communities organize independent rescue efforts. Many of the missing are still alive.” |

Both existing `must_convey` sets fit. Nothing contradicts the plot. However, these lines still do not explain how Kristin learns about the calls from outside. This option needs an established notification and a readable return route; it does not solve the problem through replacement text alone.

**Yes, close the evacuation explicitly.** When the evacuation is committed as complete, show:

> The captives have emerged into Los Angeles. News drones, civilians, and local responders begin arriving.

Attach this to evacuation completion, not merely to the gates opening. It marks the passage as finished without moving Kristin or Michelle. Persistent scene facts must also reflect that completion so later narration does not restart the tunnel passage.

These are recommendations and replacement text only; no repository files were changed.