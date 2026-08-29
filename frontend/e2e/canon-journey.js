export const canonJourney = [
  {
    input: "I stay concealed in Michelle's house and watch the marked gate for the federal patrol's return without leaving or following a lead.",
    clock: { eventId: "pressure_1a" },
    expectedSceneId: "1A",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input: "I retrieve the hidden memory card from beneath the drawer, preserve it, and use Michelle's research to identify an actionable lead away from the house while noting the patrol mark.",
    clock: { sceneId: "1B", point: "target" },
    expectedSceneId: "1B",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input: "I follow Michelle's park dead drop, take the transit card, identify Brandon from her photograph, and escape the ambush with him so we can depart for the freight terminal.",
    clock: { sceneId: "1C", point: "target" },
    expectedSceneId: "1C",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input: "I confirm living captives and the nationwide facility network, then conclude that Brandon and I need controlled deeper access rather than a reckless rescue attempt.",
    clock: { sceneId: "2A", point: "target" },
    expectedSceneId: "2A",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input: "I prepare false inspector identities around the facility's real cooling risk, enter under that cover, and convince the supervisor to give us restricted infrastructure-corridor access.",
    clock: { sceneId: "2B", point: "target" },
    expectedSceneId: "2B",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input: "I secure the JANUS archive evidence, learn that Kristin was deliberately left behind, confront Brandon about helping build JANUS and his claimed reform motive, and recognize Michelle's active resistance in the corrupted prisoner records.",
    clock: { sceneId: "2C", point: "earliest" },
    expectedSceneId: "2C",
    expectedEventIds: ["pressure_1a"],
  },
  {
    input: "I read and verify Charles's purge and transfer order from the coordinated movement, treating the deadline as active while keeping the evidence and rescue mission together.",
    clock: { eventId: "purge_2c" },
    expectedSceneId: "2C",
    expectedEventIds: ["pressure_1a", "purge_2c"],
  },
  {
    input: "I follow Michelle's coded message and make the combined plan explicit: use Rebecca's secured office to broadcast the evidence while opening the detention sectors for the rescue.",
    clock: { sceneId: "3A", point: "earliest" },
    expectedSceneId: "3A",
    expectedEventIds: ["pressure_1a", "purge_2c"],
  },
  {
    input: "I reunite with Michelle, document the behavioral experiments and conditioned-release plan, and secure the emergency military override codes while understanding that they expire with Charles's new authority.",
    clock: { eventId: "override_deadline_3a" },
    expectedSceneId: "3A",
    expectedEventIds: ["pressure_1a", "purge_2c", "override_deadline_3a"],
  },
  {
    input: "I launch Michelle's coordinated detention uprising and lead the resistance upward toward the command and broadcast levels, using the override codes to keep the assault moving.",
    clock: { sceneId: "3B", point: "target" },
    expectedSceneId: "3B",
    expectedEventIds: ["pressure_1a", "purge_2c", "override_deadline_3a"],
  },
  {
    input: "I create conflicting infrastructure emergencies to overwhelm JANUS, reach Rebecca's office, secure her detention-site locations after Charles abandons her, and help Brandon open the relay and transmit his confession without starting the national broadcast yet.",
    clock: { eventId: "destruction_3b" },
    expectedSceneId: "3B",
    expectedEventIds: ["pressure_1a", "purge_2c", "override_deadline_3a", "destruction_3b"],
  },
  {
    input: "I start Michelle's national broadcast through Brandon's open relay, transmit the JANUS evidence and detention locations, rescue the captives, and escape as the facility collapses.",
    clock: { sceneId: "3C", point: "target" },
    expectedSceneId: "3C",
    expectedEventIds: ["pressure_1a", "purge_2c", "override_deadline_3a", "destruction_3b"],
  },
];
