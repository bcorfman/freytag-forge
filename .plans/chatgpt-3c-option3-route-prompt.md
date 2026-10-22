# Prompt for ChatGPT Desktop: how the player learns of the reports and the families, and gets back to the chamber (scene 3C)

Paste everything below the line into a fresh ChatGPT Desktop chat. It is self-contained.

---

You are helping finish a fix in the last scene (3C) of an interactive story. You cannot see the repository, so everything you need is here. Answer with a recommendation and exact text; do not rewrite anything beyond what is asked.

## What we already decided

In an earlier round you offered three ways to make the end-of-story "reports" and "families" moments playable. We chose your **Option 3: keep the broadcast chamber as the place where those moments happen**, and now ship these cue lines (the cue is a short observation appended to narration until the player acts on it):

- Reports cue: "Reports from other detention sites reach the broadcast chamber."
- Families cue: "Families of the missing call the broadcast chamber for word."

You warned that Option 3 still needs (a) an established way for Kristin to learn about the reports and calls when she is not in the chamber, and (b) a readable route back to the chamber. Those two things are what this prompt asks for. We also want (c) your closing evacuation line placed.

## Facts you must work inside

- Player character: Kristin. Companion: Michelle. Brandon holds the communications relay in a separate area (the "Broadcast relay"); the plot says he "remains at the relay so the broadcast stays live" and that his fate is "initially uncertain". Rebecca is in her executive office.
- Places: the **broadcast chamber** is a room inside Rebecca's executive office. The captives start in the **maintenance network** (the tunnels). The **emergency surface gates** are at the **Los Angeles surface** (both are parts of the same facility tree). Kristin starts the scene in the broadcast chamber.
- Plot 3C.3: Kristin restores power to the drainage pumps and holds one watertight barrier. Michelle leads the prisoners through the tunnel. "From Rebecca's office, Michelle uses the senior official's expiring authorization to release the emergency surface gates once. Brandon remains at the relay so the broadcast stays live. Thousands of captives emerge into Los Angeles as news drones, civilians, and local responders begin arriving."
- Plot 3C.4: "Reports from other detention sites reach the broadcast chamber as families of the missing call for news." Kristin and Michelle reunite. Michelle publishes the archive; Kristin joins teams opening the remaining facilities.
- Engine rules: a storylet fires once; facts are the only truth; the narrator (a small language model) cannot move people to places it was not told about, and nobody may be in two places. A new place or person must be declared in the package, and we avoid new names. Authored delivery text is preferred over leaving the narrator to improvise.
- Mechanics: the player earns D1 (reports) by checking, reading, watching or relaying the reports from the detention sites, and D2 (families) by answering or calling the families. The evacuation is "complete" when the fact `captives_reaching_surface` is set. A canonical escape event sets it (the same event also marks the facility lost); in the recorded run it had fired by the turn after the gates opened. The gate delivery is (Michelle's delivery: "Michelle uses the senior official's authorization to release the surface gates. Brandon keeps the relay open while water closes the facility around them.").

## Evidence of the problem

In the one recorded full playthrough, after the gates opened the player stayed in the tunnel and at the surface with Michelle and the captives and spent eight turns asking to lead them through the gates again. The narrator re-described the tunnel each time. The two cue lines above (then worded "…ask the broadcast chamber for word") appeared but nobody was in the chamber, so the player never acted on them. Nothing told the player the evacuation was finished or where the next thing happens.

## What to answer

1. **Notification (a).** Using only established characters and places, propose the smallest delivery text that tells Kristin, where she is, that the reports and calls are arriving at the chamber. Candidate carriers: Brandon over the relay, Michelle calling out as she leaves the surface gates, or the final lines of the evacuation delivery. Choose one and say why the others fail the plot. Give the exact text.
2. **Return route (b).** State in one sentence how Kristin gets back to the chamber from the pumps, the tunnel or the surface under the facility tree above (the chamber and the maintenance network are in different areas). Say whether any existing area needs a declared connection, or whether "go to the broadcast chamber" is already enough for the engine, and what the player-visible line should be so the opening is readable without being a command.
3. **Closing line (c).** Confirm or correct your earlier closing line, "The captives have emerged into Los Angeles. News drones, civilians, and local responders begin arriving." Say which delivery it belongs to (Michelle's gate delivery above, or a new line shown when the escape event fires), and give the exact final text of that delivery.
4. **Contradiction check.** List any plot line that your text or route would contradict, and any sentence that places two people in one place they cannot be.

Constraints: plain words, 12th grade reading level, one idea per sentence, no new names or places, short.
