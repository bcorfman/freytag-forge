import assert from "node:assert/strict";
import test from "node:test";
import { aggregate, analyseRun, askPlayer, playerPrompt, validateCommand } from "./blind-player.js";

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

