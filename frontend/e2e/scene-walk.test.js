import assert from "node:assert/strict";
import test from "node:test";

import { walkScenes } from "./scene-walk.js";

const pacing = {
  sceneOrder: ["1A", "1B"],
  eventOrder: [],
  scenePoint(scene_id, point) { return { kind: "scene_point", scene_id, point, target_turn: point === "handoff" ? 100 : 0 }; },
};

function fakePage(opening = "House opening") {
  return { locator: () => ({ first: () => ({ textContent: async () => opening }) }) };
}

function harness(responses) {
  const inputs = [];
  return {
    inputs,
    startSession: async () => ({ state: { scene_id: "1A" } }),
    submitTurn: async (_page, input) => { inputs.push(input); return responses.shift(); },
    resolveWarning: async () => false,
  };
}

function response(scene_id, text, { enter = false, committed = 1 } = {}) {
  return {
    state: { scene_id, turns_since_scene_entry: enter ? 0 : 1, fired_storylet_ids: Array(committed).fill("reveal") },
    segments: enter ? [{ kind: "narration", text: `${text} leaves.` }, { kind: "narration", text: `${scene_id} opening.` }] : [{ kind: "narration", text }],
  };
}

test("walks 1A and uses exploration as its first turn", async () => {
  const h = harness([response("1A", "Exploration result")]);
  const turns = [];
  await walkScenes({ page: fakePage(), pacing, sceneIds: ["1A"], exploreFor: () => "Search the House.", ...h, onTurn: (turn) => turns.push(turn) });
  assert.deepEqual(h.inputs, ["Search the House."]);
  assert.equal(turns[0].scene_id, "1A");
});

test("walks 1A then 1B and opens the destination from the final segment", async () => {
  const h = harness([response("1A", "first"), response("1B", "departure", { enter: true }), response("1B", "explore")]);
  const openings = [];
  const turns = [];
  await walkScenes({ page: fakePage(), pacing, sceneIds: ["1A", "1B"], exploreFor: (id) => `Search the ${id}.`, ...h, onOpening: (opening) => openings.push(opening), onTurn: (turn) => turns.push(turn) });
  assert.deepEqual(h.inputs, ["Search the 1A.", "Look for anything Michelle hid deliberately, checking under the drawers and behind her work area for materials she did not want found.", "Search the 1B."]);
  assert.equal(openings[0].via, "entry-output");
  assert.equal(openings[1].text, "1B opening.");
  assert.equal(turns[1].text, "departure leaves.");
});

test("reports a stall rather than spending the turn budget", async () => {
  const h = harness(Array.from({ length: 6 }, () => response("1A", "still here", { committed: 0 })));
  await assert.rejects(() => walkScenes({ page: fakePage(), pacing, sceneIds: ["1B"], maxTurns: 10, exploreFor: () => "Search the House.", ...h }), /stalled/);
});
