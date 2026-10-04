import assert from "node:assert/strict";
import test from "node:test";
import { aggregate, analyseRun, askPlayer, formatMarkdown, playerPrompt, unseenTerms, validateCommand } from "./blind-player.js";

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
