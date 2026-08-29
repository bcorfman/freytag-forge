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
    "I search the kitchen and the back door for concrete signs of what happened here - the overturned chair, the forced lock, her phone left on the floor.",
    "I look for anything Michelle hid deliberately, checking under the drawers and behind her work area for materials she did not want found.",
    "I try to recover the interrupted message she was recording, and listen to whatever survives of it.",
    "Someone official is at the door asking questions about her work; I keep what I found hidden, then watch what they do at the gate as they leave.",
  ],
  // 1B.1 dead drop -> 1B.2 the man following -> 1B.3 his warning -> 1B.4 ambush and escape
  "1B": [
    "At the bench her files pointed to, I search underneath for whatever she left there and study every item of it.",
    "The man watching me from across the park moves when I do; I break for the service tunnels, and when he intervenes I demand to know who he is.",
    "I press him on what actually happened to the missing people, and whether any of them are still alive.",
    "A tactical team closes in; I get us out through the storm drains and watch how he opens the secured gate.",
  ],
  // 1C.1 transport route -> 1C.2 captives -> 1C.3 nationwide network -> 1C.4 architects
  "1C": [
    "I use the transit card at the freight terminal and work down into the service level, reading the site for signs it is still active.",
    "From the observation shaft I watch the processing floor and match what I see against the missing-person records.",
    "I get into a logistics terminal and follow where the transports actually go beyond this site.",
    "I play back the recorded conference between the people directing this operation and listen to what they intend next.",
  ],
  // 2A.1 hideout -> 2A.2 infiltration plan -> 2A.3 entering under cover
  "2A": [
    "At his hideout I take stock of the servers, the salvaged hardware, and how long he has been preparing for this.",
    "I work the facility's cooling and support-column weakness into credentials that present us as the inspectors it would have to admit.",
    "We go in under that cover, and when a supervisor challenges the unscheduled inspection I make the collapse risk sound imminent enough to earn the restricted corridors.",
  ],
  // 2B.1 selection algorithm -> 2B.2 Kristin was bait -> 2B.3 his role -> 2B.4 Michelle's resistance
  "2B": [
    "In the records archive I open the selection files and read how people were sorted, and why Michelle was among them.",
    "I look for my own name in those records and find out what they expected me to do.",
    "I put his name in the development records in front of him and demand the truth about what he built.",
    "I trace the corrupted prisoner files and equipment failures until I recognize whose hand is behind them.",
  ],
  // 2C.1 the offer -> 2C.3 evidence or rescue -> 2C.4 Michelle's combined plan
  "2C": [
    "I stay close while the executive channel makes its private offer, and judge whether the people running this are turning on each other.",
    "I weigh what transmitting our evidence right now would cost the people still held here.",
    "I follow Michelle's coded message through the maintenance network and commit to the plan it describes.",
  ],
  // 3A.1 reach Michelle -> 3A.2 experiments -> 3A.3 override codes -> 3A.4 uprising
  "3A": [
    "I get down into the detention sector and find Michelle where she is running her network.",
    "She walks me through the medical level, and I document what was done to the prisoners there.",
    "I find the imprisoned official among the captives and secure the authorization he is carrying before it lapses.",
    "With that window closing, Michelle gives the signal and we move with the prisoners toward the upper levels.",
  ],
  // 3B.1 overload JANUS -> 3B.2 Rebecca's office -> 3B.3 betrayal -> 3B.4 relay
  "3B": [
    "I set off contradictory emergencies across the infrastructure until the system predicting us has to hand control back to people.",
    "We reach the executive office and I confront her with what she personally approved.",
    "Her own side locks her out and writes off this site; I take the detention-site locations she is suddenly willing to trade.",
    "He goes for the relay chamber to cut it loose from the network and put his own confession on the wire.",
  ],
  // 3C.1 transmission -> 3C.2 archive and confrontation -> 3C.3 collapse -> 3C.4 resolution
  "3C": [
    "Michelle opens the broadcast and we push the evidence out - the captives, the selection records, the locations.",
    "I stop her leaving with the portable archive, and rather than destroy it we copy it out to independent networks.",
    "I hold the emergency supports while the prisoners are led up through the maintenance tunnels.",
    "I take account of what this has changed across the country, and what it has not.",
    "I read the recovered fragment describing what was meant to follow all of this.",
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
  "I keep looking over the room for anything I have not yet accounted for.",
  ...Object.values(scenePrompts).flat(),
];
