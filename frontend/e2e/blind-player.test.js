import assert from "node:assert/strict";
import test from "node:test";
import { aggregate, aggregateByScene, analyseRun, askPlayer, formatMarkdown, playerPrompt, sceneIdsForRun, turnLog, turnRecord, unseenTerms, validateCommand } from "./blind-player.js";

const response = (command) => ({ ok: true, status: 200, json: async () => ({ output_text: JSON.stringify({ command }) }) });
const fakeMap = { scenes: [{ scene_id: "SECRET", location: { name: "Vault" }, gates: [{ sources: [{ id: "SECRET_SOURCE", player_earned: true }] }] }] };

test("player prompt contains only screen data", () => {
  const prompt = playerPrompt({ transcript: "A plain room.", status: "Scene S1 • rising" });
  assert.equal(prompt.system.includes("SECRET"), false);
  assert.equal(JSON.stringify(prompt).includes("Vault"), false);
  assert.equal(JSON.stringify(prompt).includes("SECRET_SOURCE"), false);
  assert.equal(JSON.stringify(fakeMap).includes("SECRET"), true);
});

test("validates player input rules", () => {
  for (const command of ["Search the desk.", "Open my laptop."]) assert.equal(validateCommand(command).ok, true);
  for (const command of ["I search the desk.", "Wait.", "Keep watch.", "Search without touching.", "Search the desk"]) assert.equal(validateCommand(command).ok, false);
});

test("turnRecord carries semantic fallback and prompt metadata", () => {
  const payload = { state: { scene_id: "A" }, segments: [{ grounding_ids: ["desk"] }], delivery: { x: 1 }, semantic_match: { ran: true, matched: "desk" }, prompt: "full prompt" };
  assert.deepEqual(turnRecord({ turn: 1, input: "Search the desk.", payload, text: "The desk is here." }), {
    turn: 1, input: "Search the desk.", text: "The desk is here.", state: { scene_id: "A" }, grounding_ids: ["desk"], delivery: { x: 1 }, semantic_match: { ran: true, matched: "desk" }, prompt: "full prompt",
  });
  assert.deepEqual(turnRecord({ turn: 2, input: "Search the room.", payload: {}, text: "Nothing." }).semantic_match, null);
  assert.equal(turnRecord({ turn: 2, input: "Search the room.", payload: {}, text: "Nothing." }).prompt, null);
});

test("turnLog emits the contract without prompt, delivery, or state", () => {
  const normal = { turn: 1, input: "Search the desk.", text: "The desk is here.", state: { scene_id: "A" }, grounding_ids: ["desk"], delivery: { hidden: true }, semantic_match: { ran: true, matched: "desk" }, prompt: "secret prompt" };
  const rejectedTurn = { turn: 2, input: "Search the room.", text: "", rejected: true, rejection: "bad response", state: null, grounding_ids: [], delivery: {}, semantic_match: null, prompt: "another secret" };
  const withoutMatch = { turn: 3, input: "Open the door.", text: "The door opens.", state: { scene_id: "B" }, grounding_ids: ["door"], semantic_match: undefined };
  const result = turnLog([normal, rejectedTurn, withoutMatch]);
  assert.deepEqual(result, [
    { turn: 1, input: "Search the desk.", text: "The desk is here.", rejected: false, rejection: null, scene_id: "A", semantic_match: { ran: true, matched: "desk" }, grounding_ids: ["desk"] },
    { turn: 2, input: "Search the room.", text: "", rejected: true, rejection: "bad response", scene_id: null, semantic_match: null, grounding_ids: [] },
    { turn: 3, input: "Open the door.", text: "The door opens.", rejected: false, rejection: null, scene_id: "B", semantic_match: null, grounding_ids: ["door"] },
  ]);
  for (const entry of result) assert.deepEqual(Object.keys(entry).sort(), ["grounding_ids", "input", "rejected", "rejection", "scene_id", "semantic_match", "text", "turn"]);
  assert.equal(JSON.stringify(result).includes("prompt"), false);
});

test("askPlayer handles key, cap, retry, and invalid responses", async () => {
  await assert.rejects(() => askPlayer({ transcript: "", status: "", environment: {}, fetchImpl: async () => response("Search the desk.") }), /OPENAI_API_KEY/);
  const counter = { calls: 0 };
  assert.equal(await askPlayer({ transcript: "", status: "", environment: { OPENAI_API_KEY: "x" }, counter, fetchImpl: async () => response("Search the desk.") }), "Search the desk.");
  assert.equal(counter.calls, 1);
  await assert.rejects(() => askPlayer({ transcript: "", status: "", cap: 1, counter, environment: { OPENAI_API_KEY: "x" }, fetchImpl: async () => response("Search the desk.") }), /cap/);
  let calls = 0;
  const retryCounter = { calls: 0 };
  assert.equal(await askPlayer({ transcript: "", status: "", environment: { OPENAI_API_KEY: "x" }, counter: retryCounter, fetchImpl: async () => response(++calls === 1 ? "I search." : "Search the desk.") }), "Search the desk.");
  await assert.rejects(() => askPlayer({ transcript: "", status: "", environment: { OPENAI_API_KEY: "x" }, fetchImpl: async () => response("Wait.") }), /twice/);
});

const scene = { scene_id: "A", gates: [{ affordances: [{ entity_id: "door", name: "door", terms: ["door"] }], sources: [{ id: "reveal", player_earned: true }] }] };
test("reports play, timer, none, and unknown exit causes", () => {
  const handoffScene = { ...scene, handoff_after_turns: 13 };
  assert.equal(analyseRun({ sceneEntry: handoffScene, turns: [committed(8, "B")] }).exit_cause, "play");
  assert.equal(analyseRun({ sceneEntry: handoffScene, turns: [committed(13, "B")] }).exit_cause, "timer");
  assert.equal(analyseRun({ sceneEntry: handoffScene, turns: [committed(13)] }).exit_cause, "none");
  assert.equal(analyseRun({ sceneEntry: scene, turns: [committed(8, "B")] }).exit_cause, "unknown");
  assert.equal(analyseRun({ sceneEntry: handoffScene, turns: [committed(8, "B")] }).handoff_after_turns, 13);
  assert.equal(analyseRun({ sceneEntry: scene, turns: [committed(8, "B")] }).handoff_after_turns, null);
});

test("aggregates play and timer exit rates", () => {
  const handoffScene = { ...scene, handoff_after_turns: 13 };
  const runs = [
    analyseRun({ sceneEntry: handoffScene, turns: [committed(8, "B")] }),
    analyseRun({ sceneEntry: handoffScene, turns: [committed(13, "B")] }),
    analyseRun({ sceneEntry: handoffScene, turns: [committed(13)] }),
  ];
  assert.equal(aggregate(runs).play_exit_rate, 1 / 3);
  assert.equal(aggregate(runs).timer_exit_rate, 1 / 3);
});

test("aggregates all-mode runs by scene", () => {
  const runs = aggregateByScene([
    { scenes: [{ scene: "1A", transition_fired: true, exit_cause: "play" }, { scene: "1B", transition_fired: true, exit_cause: "timer" }] },
    { scenes: [{ scene: "1A", transition_fired: false, exit_cause: "none" }] },
  ]);
  assert.equal(runs["1A"].replicates, 2);
  assert.equal(runs["1A"].play_exit_rate, 0.5);
  assert.equal(runs["1B"].timer_exit_rate, 1);
});

test("validates the optional all-mode scene prefix", () => {
  assert.deepEqual(sceneIdsForRun(["1A", "1B", "1C"], "1A,1B"), ["1A", "1B"]);
  assert.deepEqual(sceneIdsForRun(["1A", "1B"], "all"), ["1A", "1B"]);
  assert.throws(() => sceneIdsForRun(["1A", "1B"], "1B"), /prefix/);
  assert.throws(() => sceneIdsForRun(["1A", "1B"], "1A,NOPE"), /scene ids/);
});

test("analyses stuck runs, silent and clean transitions, and L3", () => {
  const turns = [1, 2, 3].map((turn) => ({ turn, input: "Search the floor.", text: "Nothing changes.", state: { scene_id: "A", fired_storylet_ids: [], fired_pacing_event_ids: [] }, grounding_ids: [], delivery: { must_convey_misses: [] } }));
  const stuck = analyseRun({ sceneEntry: scene, nextSceneEntry: { entry_text: "New room." }, turns, firstStep: scene.gates[0].affordances, later: [] });
  assert.equal(stuck.stuck_runs.length, 1);
  const cleanTurns = [{ turn: 1, input: "Open the door.", text: "The door opens. New room.", state: { scene_id: "B", fired_storylet_ids: ["reveal"], fired_pacing_event_ids: [] }, grounding_ids: ["door"], delivery: { must_convey_misses: [] } }];
  const clean = analyseRun({ sceneEntry: scene, nextSceneEntry: { entry_text: "New room." }, turns: cleanTurns, firstStep: scene.gates[0].affordances, later: [] });
  assert.equal(clean.transition_fired, true);
  assert.equal(clean.silent_transition, false);
  assert.equal(clean.l3.transition.no_skip_or_restart, true);
  assert.equal(aggregate([stuck, clean]).transition_rate, 0.5);
});

const committed = (turn, scene_id = "A", text = "Nothing changes.") => ({
  turn,
  input: "Search the floor.",
  text,
  state: { scene_id, fired_storylet_ids: [], fired_pacing_event_ids: [] },
  grounding_ids: [],
  delivery: { must_convey_misses: [] },
});
const rejected = (turn, rejection = "narration mentions an unavailable entity photo") => ({
  turn,
  input: "Search the floor.",
  rejected: true,
  rejection,
  text: "",
  state: null,
  grounding_ids: [],
  delivery: {},
});

test("rejected turns in the middle are reported and do not become stuck or affect state deltas", () => {
  const result = analyseRun({
    sceneEntry: scene,
    nextSceneEntry: { entry_text: "New room." },
    turns: [committed(1), rejected(2), committed(3)],
    firstStep: scene.gates[0].affordances,
  });
  assert.deepEqual(result.rejected_turns, [{ turn: 2, input: "Search the floor.", rejection: "narration mentions an unavailable entity photo" }]);
  assert.equal(result.rejected_count, 1);
  assert.deepEqual(result.stuck_turns, [1, 3]);
  assert.equal(result.transition_fired, false);
});

test("a rejection right before transition does not hide the transition or affordance", () => {
  const result = analyseRun({
    sceneEntry: scene,
    nextSceneEntry: { entry_text: "New room." },
    turns: [committed(1, "A", "The door is here."), rejected(2), { ...committed(3, "B", "The door opens. New room."), input: "Open the door." }],
    firstStep: scene.gates[0].affordances,
  });
  assert.equal(result.transition_fired, true);
  assert.equal(result.transition_turn, 3);
  assert.equal(result.affordances[0].first_shown_turn, 1);
  assert.equal(result.l3.transition.final_segment_matches_entry, true);
});

test("three consecutive rejections are retained and a stopped run is marked", () => {
  const result = analyseRun({
    sceneEntry: scene,
    nextSceneEntry: { entry_text: "New room." },
    turns: [rejected(1), rejected(2), rejected(3)],
    firstStep: scene.gates[0].affordances,
    stopped_on_rejections: true,
  });
  assert.equal(result.rejected_count, 3);
  assert.equal(result.rejected_turns.length, 3);
  assert.equal(result.stopped_on_rejections, true);
  assert.deepEqual(result.stuck_turns, []);
  assert.equal(result.transition_fired, false);
});

test("aggregate and Markdown report rejected turns", () => {
  const withRejection = { ...analyseRun({ sceneEntry: scene, turns: [committed(1), rejected(2)] }), turn_count: 2, stopped_on_rejections: true };
  const withoutRejection = { ...analyseRun({ sceneEntry: scene, turns: [committed(1)] }), turn_count: 1, stopped_on_rejections: false };
  const summary = aggregate([withRejection, withoutRejection]);
  assert.equal(summary.rejected_count, 1);
  assert.equal(summary.rejected_turn_rate, 1 / 3);
  assert.equal(summary.stopped_on_rejections_count, 1);
  const markdown = formatMarkdown({ replicates: [withRejection, withoutRejection], aggregate: summary });
  assert.match(markdown, /Rejected turns: 1/);
  assert.match(markdown, /narration mentions an unavailable entity photo/);
  assert.match(markdown, /Semantic reveal fallback/);
  assert.match(markdown, /did not return it/);
});

test("Markdown lists and truncates per-turn text", () => {
  const longText = "x".repeat(250);
  const markdown = formatMarkdown({ replicates: [{ replicate: 1, turns: [{ turn: 1, input: "Search the desk.", text: `first\n${longText}` }] }] });
  assert.match(markdown, /## Turns — replicate 1/);
  const line = markdown.split("\n").find((value) => value.startsWith("- t1 "));
  assert.equal(line.length, "- t1 Search the desk. -> ".length + 200);
  assert.equal(line.endsWith("x"), true);
  assert.equal(markdown.includes("first\n"), false);
});

test("analyseRun reports semantic fallback matches only when returned", () => {
  const result = analyseRun({ sceneEntry: scene, turns: [
    { ...committed(1), semantic_match: { ran: true, matched: "door" } },
    { ...committed(2), semantic_match: { ran: true, matched: null } },
    committed(3),
  ] });
  assert.deepEqual(result.semantic_matches, [
    { turn: 1, input: "Search the floor.", ran: true, matched: "door" },
    { turn: 2, input: "Search the floor.", ran: true, matched: null },
  ]);
});

test("opening affordances use turn 0 and the turn 0/1 deadline", () => {
  const affordance = { entity_id: "drawer", name: "drawer", terms: ["drawer"] };
  const entry = { scene_id: "A", gates: [{ affordances: [affordance], sources: [{ id: "reveal", player_earned: true }] }] };
  const report = analyseRun({ sceneEntry: entry, openingText: "A desk has a drawer.", turns: [{ turn: 1, input: "Open the drawer.", text: "The door opens.", state: { scene_id: "B" } }], firstStep: [affordance] });
  assert.deepEqual(report.affordances[0], { entity_id: "drawer", first_shown_turn: 0, deadline_met: true });
  assert.equal(report.silent_transition, false);
  const late = analyseRun({ sceneEntry: entry, turns: [{ turn: 3, input: "Open the drawer.", text: "The drawer is here." }], firstStep: [affordance] });
  assert.equal(late.affordances[0].first_shown_turn, 3);
  assert.equal(late.affordances[0].deadline_met, false);
});

const reportAffordance = (entity_id, terms = [entity_id]) => ({ entity_id, name: entity_id, terms });
const reportScene = {
  scene_id: "1A",
  gates: [{
    affordances: [
      reportAffordance("kristin_laptop", ["laptop"]),
      reportAffordance("michelle_drawer", ["drawer"]),
      reportAffordance("workstation_chair", ["chair"]),
      reportAffordance("michelle_workstation", ["workstation"]),
      reportAffordance("memory_card", ["memory card"]),
    ],
    sources: [{ id: "earned", player_earned: true }],
  }],
};
const reportTurns = ({ chairShown }) => [
  { turn: 1, input: "Inspect the workstation.", text: `${chairShown ? "The chair is overturned beside the workstation. " : ""}The drawer is ajar. Kristin's laptop is in her truck.`, state: { scene_id: "1A" } },
  { turn: 2, input: "Examine the papers in the drawer.", text: "The workstation holds a drawer. Kristin finds the memory card.", state: { scene_id: "1A" } },
  { turn: 8, input: "Take the package.", text: "The park bench leads to the next scene.", state: { scene_id: "1B" } },
];

test("replicate 1 is not silent when every first-step affordance was shown", () => {
  const firstStep = reportScene.gates[0].affordances.slice(0, 4);
  const result = analyseRun({ sceneEntry: reportScene, turns: reportTurns({ chairShown: true }), firstStep, later: [reportScene.gates[0].affordances[4]] });
  assert.equal(result.transition_fired, true);
  assert.equal(result.transition_turn, 8);
  assert.equal(result.silent_transition, false);
});

test("replicate 3 stays silent when a first-step affordance was never shown", () => {
  const firstStep = reportScene.gates[0].affordances.slice(0, 4);
  const result = analyseRun({ sceneEntry: reportScene, turns: reportTurns({ chairShown: false }), firstStep, later: [reportScene.gates[0].affordances[4]] });
  assert.equal(result.affordances.find((item) => item.entity_id === "workstation_chair").first_shown_turn, null);
  assert.equal(result.silent_transition, true);
});

test("silent transition ignores earned-gate affordances absent from shown", () => {
  const shownItem = reportAffordance("shown_item", ["item"]);
  const absentItem = reportAffordance("absent_item", ["absent"]);
  const result = analyseRun({
    sceneEntry: { scene_id: "A", gates: [{ affordances: [shownItem, absentItem], sources: [{ player_earned: true }] }] },
    turns: [{ turn: 1, input: "Inspect the item.", text: "The item is here.", state: { scene_id: "B" } }],
    firstStep: [shownItem],
  });
  assert.equal(result.silent_transition, false);
});

test("unshown later affordances do not make a transition silent", () => {
  const firstStep = reportAffordance("first_item", ["first"]);
  const laterItem = reportAffordance("later_item", ["later"]);
  const result = analyseRun({
    sceneEntry: { scene_id: "A", gates: [{ affordances: [firstStep, laterItem], sources: [{ player_earned: true }] }] },
    turns: [{ turn: 1, input: "Inspect the first item.", text: "The first item is here.", state: { scene_id: "B" } }],
    firstStep: [firstStep],
    later: [laterItem],
  });
  assert.equal(result.affordances.find((item) => item.entity_id === "later_item").first_shown_turn, null);
  assert.equal(result.silent_transition, false);
});

test("a run without a transition is not silent", () => {
  const item = reportAffordance("item", ["item"]);
  const result = analyseRun({ sceneEntry: { scene_id: "A", gates: [{ affordances: [item], sources: [{ player_earned: true }] }] }, turns: [{ turn: 1, input: "Search the room.", text: "Nothing changes.", state: { scene_id: "A" } }], firstStep: [item] });
  assert.equal(result.transition_fired, false);
  assert.equal(result.silent_transition, false);
});

test("unseenTerms checks content words with grammar stops and simple plurals", () => {
  assert.deepEqual(unseenTerms({ command: "Open the drawer.", readText: "A drawer is in the desk." }), []);
  assert.deepEqual(unseenTerms({ command: "Open the lantern.", readText: "A drawer is here." }), ["lantern"]);
  assert.deepEqual(unseenTerms({ command: "Open the drawers.", readText: "A drawer is here." }), []);
  assert.deepEqual(unseenTerms({ command: "Open the drawer's lock.", readText: "A drawer is here." }), ["lock"]);
  assert.deepEqual(unseenTerms({ command: "Search my desk and look around.", readText: "A room." }), ["desk"]);
  assert.deepEqual(unseenTerms({ command: "Open the drawer’s lock.", readText: "A drawer." }), ["lock"]);
});

test("analyseRun reports unseen commands without rejected text in read history", () => {
  const report = analyseRun({
    sceneEntry: { scene_id: "A" }, openingText: "A desk is here.", turns: [
      { turn: 1, input: "Open the lantern.", text: "The lantern is visible." },
      { turn: 2, input: "Open the secret.", text: "The secret appears.", rejected: true },
      { turn: 3, input: "Open the secret.", text: "The secret appears." },
    ],
  });
  assert.deepEqual(report.unseen_commands, [
    { turn: 1, input: "Open the lantern.", unseen_terms: ["lantern"] },
    { turn: 2, input: "Open the secret.", unseen_terms: ["secret"] },
    { turn: 3, input: "Open the secret.", unseen_terms: ["secret"] },
  ]);
  assert.equal(report.unseen_command_count, 3);
});

test("aggregate reports unseen command rate and Markdown lists unseen commands", () => {
  const runs = [{ commands: ["Open the lantern.", "Open the drawer."], unseen_command_count: 1, unseen_commands: [{ turn: 1, input: "Open the lantern.", unseen_terms: ["lantern"] }] }];
  assert.equal(aggregate(runs).unseen_command_rate, 0.5);
  assert.match(formatMarkdown({ replicates: runs }), /Open the lantern.*unseen: lantern/);
});
