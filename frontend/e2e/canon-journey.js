// One turn per authored knowledge selection: the runtime commits at most one
// storylet realization per turn, so every scene needs as many turns as the
// facts its outgoing bridge requires. Inputs steer the provider toward the
// intended candidate without naming knowledge the player cannot have yet.
export const canonJourney = [
  {
    input:
      "I search the house for concrete signs Michelle was taken - the overturned chair, the forced back door - and I stay hidden while I watch the marked front gate for the patrol's return.",
    clock: { eventId: "pressure_1a" },
    expectedSceneId: "1A",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input:
      "I retrieve the hidden memory card taped beneath the drawer, preserve Michelle's research, and use it to identify an actionable lead away from the house.",
    clock: { sceneId: "1B", point: "target" },
    expectedSceneId: "1B",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input:
      "At the park dead drop I take the transit card and the photograph, and when the stranger from the photo intervenes against the patrol I demand to know who he is and whether the missing are still alive.",
    clock: { sceneId: "1B", point: "latest" },
    expectedSceneId: "1B",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input:
      "I escape with him through the storm drains and watch closely as he unlocks the secured maintenance gate with a specialized code no civilian should have, following the route toward the freight terminal.",
    clock: { sceneId: "1C", point: "target" },
    expectedSceneId: "1C",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input:
      "I use the transit card at the freight terminal and slip into the service level to confirm the site is active beneath the abandoned surface.",
    clock: { sceneId: "1C", point: "latest" },
    expectedSceneId: "1C",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input:
      "From the observation shaft I document the rows of sedated prisoners being moved and match their identification numbers against the missing-person files, accepting that we need controlled deeper access rather than a reckless rescue.",
    clock: { sceneId: "2A", point: "target" },
    expectedSceneId: "2A",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input:
      "At the hideout I build false inspector identities around the facility's real cooling and support-column failure risk so we can enter as technical specialists.",
    clock: { sceneId: "2A", point: "latest" },
    expectedSceneId: "2A",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input:
      "We enter under the inspection cover and I convince the questioning supervisor that a progressive support-column collapse is imminent, gaining access to the restricted infrastructure corridors.",
    clock: { sceneId: "2B", point: "target" },
    expectedSceneId: "2B",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input:
      "In the records archive I open the selection files to learn why Michelle was taken and why I was left behind.",
    clock: { sceneId: "2B", point: "latest" },
    expectedSceneId: "2B",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input:
      "I confront my ally with his name in the original development records and demand the truth about his role and his motives.",
    clock: { sceneId: "2B", point: "latest" },
    expectedSceneId: "2B",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input:
      "I trace the corrupted prisoner files and equipment failures and recognize Michelle's phrasing in them - she has been resisting from inside.",
    clock: { sceneId: "2C", point: "target" },
    expectedSceneId: "2C",
    expectedEventIds: ["pressure_1a", "purge_2c"],
  },
  {
    input:
      "I stay close to Brandon as he fields the private executive channel and judge whether the architects are turning on each other.",
    clock: { sceneId: "2C", point: "latest" },
    expectedSceneId: "2C",
    expectedEventIds: ["pressure_1a", "purge_2c"],
  },
  {
    input:
      "I follow Michelle's coded maintenance message and commit to the combined plan: broadcast the evidence from the secured executive office while opening the detention sectors for the rescue.",
    clock: { sceneId: "3A", point: "target" },
    expectedSceneId: "3A",
    expectedEventIds: ["pressure_1a", "purge_2c"],
  },
  {
    input:
      "I descend into the detention block and reach Michelle where she is coordinating the prisoners through stolen radios and coded announcements.",
    clock: { eventId: "override_deadline_3a" },
    expectedSceneId: "3A",
    expectedEventIds: ["pressure_1a", "purge_2c", "override_deadline_3a"],
  },
  {
    input:
      "Michelle leads me through the medical level; I document the behavioral experiments and copy the imprisoned official's emergency override authorization before it expires.",
    clock: { sceneId: "3A", point: "latest" },
    expectedSceneId: "3A",
    expectedEventIds: ["pressure_1a", "purge_2c", "override_deadline_3a"],
  },
  {
    input:
      "With the override codes about to lose their value, Michelle triggers the coordinated uprising and we fight upward toward the command and broadcast levels.",
    clock: { sceneId: "3B", point: "target" },
    expectedSceneId: "3B",
    expectedEventIds: ["pressure_1a", "purge_2c", "override_deadline_3a"],
  },
  {
    input:
      "I create conflicting infrastructure emergencies - flooded corridors, structural alarms, power cuts - to overload the predictive security system until human operators take control.",
    clock: { eventId: "destruction_3b" },
    expectedSceneId: "3B",
    expectedEventIds: ["pressure_1a", "purge_2c", "override_deadline_3a", "destruction_3b"],
  },
  {
    input:
      "In Rebecca's office I confront her over the experiments she approved while Charles locks her out and abandons her, and I secure her record of the detention-site locations.",
    clock: { sceneId: "3B", point: "latest" },
    expectedSceneId: "3B",
    expectedEventIds: ["pressure_1a", "purge_2c", "override_deadline_3a", "destruction_3b"],
  },
  {
    input:
      "Brandon reaches the relay chamber, disconnects it from the automated network, and transmits his confession while holding the relay open for us.",
    clock: { sceneId: "3C", point: "target" },
    expectedSceneId: "3C",
    expectedEventIds: ["pressure_1a", "purge_2c", "override_deadline_3a", "destruction_3b"],
  },
  {
    input:
      "Michelle starts the national broadcast through the open relay - the captives, the selection records, the detention locations - until the truth can no longer be contained.",
    clock: { sceneId: "3C", point: "latest" },
    expectedSceneId: "3C",
    expectedEventIds: ["pressure_1a", "purge_2c", "override_deadline_3a", "destruction_3b"],
  },
];

// The unclocked spine run advances 60 authored seconds per turn, so it needs
// one extra holding turn in Scene 1A before the 120-second storylet window.
export const spineJourney = [
  canonJourney[0].input,
  "I keep watch from cover and reassess the physical evidence without leaving the house.",
  ...canonJourney.slice(1).map((step) => step.input),
];
