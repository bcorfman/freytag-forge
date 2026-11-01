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
    "Read the remaining research fragments on Michelle's memory card.",
    "Read the files on Michelle's memory card.",
    "Play the damaged recording on Michelle's memory card.",
    "Watch the officers ask about Michelle's research.",
  ],
  // 1B.1 dead drop -> 1B.2 the man following -> 1B.3 his warning -> 1B.4 ambush and escape
  "1B": [
    "Examine the photograph beneath the bench.",
    "Show Michelle's photograph to the man and ask who he is.",
    "Match the transit token to the handwritten number sequence.",
    "Get out through the storm drains and watch how he opens the secured gate.",
  ],
  // 1C.1 loading docks -> 1C.2 study the captives -> copy their numbers
  "1C": [
    "Inspect the electrical load and fresh ventilation at the loading docks.",
    "Study the prisoners on the processing line through the observation shaft.",
    "Copy the prisoner numbers from the processing line.",
  ],
  // 2A incident: supervisor at the gate -> inspect the real cooling fault -> diagnose it to the supervisor
  "2A": [
    "Drive to the facility perimeter.",
    "Meet the shift supervisor at the facility gate.",
    "Feel the cooling lines and read the gauge at the cooling manifold.",
    "Diagnose the real cooling-water pressure fault and ventilation problem to the supervisor.",
  ],
  // 2B incident: Kristin's own file and the build record -> the whispered name choice -> Michelle's one reply
  "2B": [
    "Pull my own file at the archive terminals.",
    "Keep Brandon's name in the build record.",
    "Type one reply to Michelle on the medical terminal.",
    "Read the archive situation and wait for Michelle's route.",
    "Study the medical terminal's maintenance line again.",
  ],
  // 2C incident: Rebecca's offer and the purge order -> commit by acting -> Michelle's route widens the options
  "2C": [
    "Tell Rebecca my answer to her offer.",
    "Head to the broadcast uplink and transmit the copied JANUS files.",
    "Reach the transfer carts and rescue the prisoners.",
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
  // 3C.1 broadcast -> 3C.2 archive -> 3C.3 drainage pumps -> 3C.4 surface gates -> 3C.5 detention-site reports -> 3C.6 families -> 3C.7 recovered document
  "3C": [
    "Send the evidence package.",
    "Copy Rebecca's archive.",
    "Restore the drainage pumps.",
    "Open the surface gates.",
    "Check reports from other detention sites.",
    "Call the families of the missing.",
    "Open the recovered document.",
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
