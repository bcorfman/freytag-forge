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
  // 1A.1 empty house -> 1A.2 hidden research -> 1A.3 damaged recording -> 1A.4 patrol and gate marker
  "1A": [
    "Search the kitchen and the back door for concrete signs of what happened here - the overturned chair, the forced lock, her phone left on the floor.",
    "Look for anything Michelle hid deliberately, checking under the drawers and behind her work area for materials she did not want found.",
    "Recover the interrupted message she was recording, and listen to whatever survives of it.",
    "Hide what you found from the official asking questions about Michelle's work, then watch what they do at the gate as they leave.",
  ],
  // 1B.1 dead drop -> 1B.2 the man following -> 1B.3 his warning -> 1B.4 ambush and escape
  "1B": [
    "At the bench her files pointed to, search underneath for whatever she left there and study every item of it.",
    "Break for the service tunnels when the man watching from across the park moves, then demand to know who he is when he intervenes.",
    "Press him on what actually happened to the missing people, and whether any of them are still alive.",
    "Get out through the storm drains and watch how he opens the secured gate.",
  ],
  // 1C.1 transport route -> 1C.2 captives -> 1C.3 nationwide network -> 1C.4 architects
  "1C": [
    "Use the transit token at the freight terminal and work down into the service level, reading the site for signs it is still active.",
    "From the observation shaft, watch the processing floor and match what you see against the missing-person records.",
    "Get into a logistics terminal and follow where the transports actually go beyond this site.",
    "Play back the recorded conference between the people directing this operation and listen to what they intend next.",
  ],
  // 2A.1 hideout -> 2A.2 infiltration plan -> 2A.3 entering under cover
  "2A": [
    "At his hideout, take stock of the servers, the salvaged hardware, and how long he has been preparing for this.",
    "Work the facility's cooling and support-column weakness into credentials that present you as the inspectors it would have to admit.",
    "Go in under that cover, and when a supervisor challenges the unscheduled inspection, make the collapse risk sound imminent enough to earn the restricted corridors.",
  ],
  // 2B.1 selection algorithm -> 2B.2 Kristin was bait -> 2B.3 his role -> 2B.4 Michelle's resistance
  "2B": [
    "In the records archive, open the selection files and read how people were sorted, and why Michelle was among them.",
    "Look for your own name in those records and find out what they expected you to do.",
    "Put his name in the development records in front of him and demand the truth about what he built.",
    "Trace the corrupted prisoner files and equipment failures until you recognize whose hand is behind them.",
  ],
  // 2C.1 the offer -> 2C.3 evidence or rescue -> 2C.4 Michelle's combined plan
  "2C": [
    "Assess the executive channel's private offer and whether the people running this are turning on each other.",
    "Assess the cost of transmitting our evidence right now to the people still held here.",
    "Follow Michelle's coded message through the maintenance network and commit to the plan it describes.",
  ],
  // 3A.1 reach Michelle -> 3A.2 experiments -> 3A.3 override codes -> 3A.4 uprising
  "3A": [
    "Get down into the detention sector and find Michelle where she is running her network.",
    "Follow Michelle through the medical level and document what was done to the prisoners there.",
    "Find the imprisoned official among the captives and secure the authorization he is carrying before it lapses.",
    "With that window closing, Michelle gives the signal and we move with the prisoners toward the upper levels.",
  ],
  // 3B.1 overload JANUS -> 3B.2 Rebecca's office -> 3B.3 betrayal -> 3B.4 relay
  "3B": [
    "Set off contradictory emergencies across the infrastructure until the system predicting you has to hand control back to people.",
    "Reach the executive office and confront her with what she personally approved.",
    "Take the detention-site locations she is suddenly willing to trade after her own side locks her out and writes off this site.",
    "He goes for the relay chamber to cut it loose from the network and put his own confession on the wire.",
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

// The unclocked spine run advances 60 authored seconds per turn and cannot skip
// ahead, so it walks the same prompts in authored scene order.
export const spineJourney = [
  scenePrompts["1A"][0],
  "Search the room for anything you have not yet accounted for.",
  ...Object.values(scenePrompts).flat(),
];
