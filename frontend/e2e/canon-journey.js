// Prompts are grouped by scene, not by turn number. The narration model may
// legitimately satisfy a scene's outgoing bridge in fewer turns than the
// authored maximum, so a fixed turn-indexed script produces false failures the
// moment a valid faster ordering is chosen. The harness reads the scene the
// runtime reports and sends that scene's next prompt, asserting the invariants
// that actually matter: the spine never regresses, never skips a scene, and
// ends at the authored resolution.
//
// Each scene lists prompts in authored beat order. They name only evidence the
// player can already have in that scene, so the run never smuggles in a future
// reveal.
export const scenePrompts = {
  "1A": [
    "I search the house for concrete signs Michelle was taken - the overturned chair, the forced back door - and I stay hidden while I watch the marked front gate for the patrol's return.",
    "I retrieve the hidden memory card taped beneath the drawer, preserve Michelle's research, and use it to identify an actionable lead away from the house.",
    "I go back over the kitchen and her work area for anything I have not yet accounted for.",
  ],
  "1B": [
    "At the park dead drop I take the transit card and the photograph, and when the stranger from the photo intervenes against the patrol I demand to know who he is and whether the missing are still alive.",
    "I escape with him through the storm drains and watch closely as he unlocks the secured maintenance gate with a specialized code no civilian should have, following the route toward the freight terminal.",
    "I press him on the handwritten sequence and the dates until the route it points to is unambiguous.",
  ],
  "1C": [
    "I use the transit card at the freight terminal and slip into the service level to confirm the site is active beneath the abandoned surface.",
    "From the observation shaft I document the rows of sedated prisoners being moved and match their identification numbers against the missing-person files.",
    "I read the logistics terminal and the recorded conference to understand how far this network reaches and who is directing it.",
  ],
  "2A": [
    "At the hideout I take stock of how long he has been preparing for this and what he has been hoarding against it.",
    "I build false inspector identities around the facility's real cooling and support-column failure risk so we can enter as technical specialists.",
    "We enter under the inspection cover and I convince the questioning supervisor that a progressive support-column collapse is imminent, gaining access to the restricted infrastructure corridors.",
  ],
  "2B": [
    "In the records archive I open the selection files to learn why Michelle was taken and why I was left behind.",
    "I confront my ally with his name in the original development records and demand the truth about his role and his motives.",
    "I trace the corrupted prisoner files and equipment failures and recognize Michelle's phrasing in them - she has been resisting from inside.",
  ],
  "2C": [
    "I stay close to Brandon as he fields the private executive channel and judge whether the architects are turning on each other.",
    "I follow Michelle's coded maintenance message and commit to the combined plan: broadcast the evidence from the secured executive office while opening the detention sectors for the rescue.",
    "I take stock of exactly what evidence we are carrying and what transmitting it will cost us.",
  ],
  "3A": [
    "I descend into the detention block and reach Michelle where she is coordinating the prisoners through stolen radios and coded announcements.",
    "Michelle leads me through the medical level; I document the behavioral experiments and copy the imprisoned official's emergency override authorization before it expires.",
    "With the override codes about to lose their value, Michelle triggers the coordinated uprising and we fight upward toward the command and broadcast levels.",
  ],
  "3B": [
    "I create conflicting infrastructure emergencies - flooded corridors, structural alarms, power cuts - to overload the predictive security system until human operators take control.",
    "In Rebecca's office I confront her over the experiments she approved while Charles locks her out and abandons her, and I secure her record of the detention-site locations.",
    "Brandon reaches the relay chamber, disconnects it from the automated network, and transmits his confession while holding the relay open for us.",
  ],
  "3C": [
    "Michelle starts the national broadcast through the open relay - the captives, the selection records, the detention locations - until the truth can no longer be contained.",
    "I stop Rebecca from leaving with the portable archive, and rather than destroy it we copy it out to independent networks.",
    "I hold the emergency supports while Michelle leads the captives up through the maintenance tunnels to the surface.",
    "I take account of what this has changed across the country and what it has not.",
    "I read the recovered fragment describing what was planned to follow all of this.",
  ],
};

// A scene's prompts are exhausted only if the model needs more turns there than
// authored; repeating the last prompt keeps the run moving without inventing
// new player intent.
export function promptFor(sceneId, usedCount) {
  const prompts = scenePrompts[sceneId];
  if (!prompts) throw new Error(`No authored prompts for scene ${sceneId}.`);
  return prompts[Math.min(usedCount, prompts.length - 1)];
}

// The unclocked spine run advances 60 authored seconds per turn and cannot skip
// ahead, so it walks the same prompts in authored scene order.
export const spineJourney = [
  scenePrompts["1A"][0],
  "I keep watch from cover and reassess the physical evidence without leaving the house.",
  ...Object.values(scenePrompts).flat(),
];
