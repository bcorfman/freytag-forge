// Prompts are grouped by scene, not by turn number. The narration model may
// legitimately satisfy a scene's outgoing bridge in fewer turns than the
// authored maximum, so a fixed turn-indexed script produces false failures the
// moment a valid faster ordering is chosen. The harness reads the scene the
// runtime reports and sends that scene's next prompt.
//
// Each scene's prompts follow its authored beat order in plot.md, one beat per
// prompt. A prompt must never presuppose a beat that has not happened yet: the
// canon judge reads a player action that already knows a later reveal as the
// scene contradicting its own authored order. Asking to watch "the marked gate"
// on the first turn of 1A failed exactly that way, because the patrol has not
// visited and marked it until 1A.4.
export const scenePrompts = {
  // 1A.1 empty house -> 1A.2 hidden card -> read its files -> 1A.3 damaged recording -> 1A.4 patrol and gate marker
  "1A": [
    "Search the kitchen and the back door for concrete signs of what happened here - the overturned chair, the forced lock, her phone left on the floor.",
    "Search under the drawer in her workstation.",
    "Read the files on Michelle's memory card.",
    "Play the damaged recording on Michelle's memory card.",
    "Hide what you found from the official asking questions about Michelle's work, then watch what they do at the gate as they leave.",
  ],
  // 1B.1 dead drop -> 1B.2 the man following -> 1B.3 his warning -> 1B.4 ambush and escape
  "1B": [
    "Examine the photograph beneath the bench.",
    "Show Michelle's photograph to the man and ask who he is.",
    "Match the transit token to the handwritten number sequence.",
    "Get out through the storm drains and watch how he opens the secured gate.",
  ],
  // 1C.1 transport route -> 1C.2 captives -> 1C.3 nationwide network -> 1C.4 architects
  "1C": [
    "Inspect the electrical load and fresh ventilation at the loading docks.",
    "Compare the identification numbers on the uniforms in the processing area against the missing-person records.",
    "Read the logistics computer to trace the transports beyond this site.",
    "Play the recording the logistics computer has stored.",
  ],
  // 2A.1 hideout -> 2A.2 infiltration plan -> 2A.3 entering under cover
  "2A": [
    "Search the servers and leaked documents in Brandon's hideout.",
    "Build the inspector credentials and complete the inspection forms.",
    "Drive Brandon to the facility checkpoint and show the guard.",
    "Tell the supervisor about the cooling-water problem during the unscheduled inspection.",
  ],
  // 2B.1 selection algorithm -> 2B.2 Kristin was bait -> 2B.3 his role -> 2B.4 Michelle's resistance
  "2B": [
    "In the records archive, open the selection files and read how people were sorted, and why Michelle was among them.",
    "Read my own record in the archive.",
    "Read the JANUS development records and Brandon's records.",
    "Inspect the corrupted prisoner files on the medical terminal.",
  ],
  // 2C.1 the offer -> 2C.3 evidence or rescue -> 2C.4 Michelle's combined plan
  "2C": [
    "Assess the executive channel's private offer and whether the people running this are turning on each other.",
    "Assess the cost of transmitting our evidence right now to the people still held here.",
    "Read Michelle's coded message and commit to the plan it describes.",
  ],
  // 3A.1 reach Michelle -> 3A.2 experiments -> 3A.3 override codes -> 3A.4 uprising
  "3A": [
    "Get down into the detention sector and find Michelle where she is running her network.",
    "Go to the medical level and document what was done to the prisoners there.",
    "Meet the imprisoned official and request the emergency gate authorization.",
    "Signal the prisoners to start the uprising at the checkpoints.",
  ],
  // 3B.1 overload JANUS -> 3B.2 Rebecca's office -> 3B.3 betrayal -> 3B.4 relay
  "3B": [
    "Set off false alarms across the infrastructure.",
    "Reach the executive office and confront her with what she personally approved.",
    "Take the detention-site locations she is suddenly willing to trade after her own side locks her out and writes off this site.",
    "Check Charles's remote channel on the executive screen.",
    "Tell Brandon to send his confession through the relay chamber.",
  ],
  // 3C.1 transmission -> 3C.2 archive and confrontation -> 3C.3 collapse -> 3C.4 resolution
  "3C": [
    "Open the broadcast with Michelle and push the evidence out - the captives, the selection records, the locations.",
    "Stop her leaving with the portable archive and copy it out to independent networks.",
    "Hold the emergency supports while the prisoners are led up through the maintenance tunnels.",
    "Assess what this has changed across the country, and what it has not.",
    "Read the recovered fragment describing what was meant to follow all of this.",
  ],
};

// A scene may need more turns than it has authored prompts - a reveal can be
// gated on a pacing event that only lands later in the scene. Cycling re-offers
// the earlier intents once that gate opens, where clamping to the last prompt
// would strand a beat the scene still needs.
export function promptFor(sceneId, usedCount) {
  const prompts = scenePrompts[sceneId];
  if (!prompts) throw new Error(`No authored prompts for scene ${sceneId}.`);
  return prompts[usedCount % prompts.length];
}
