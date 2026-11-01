import assert from "node:assert/strict";
import test from "node:test";

import { walkScenes } from "./scene-walk.js";

const pacing = {
  sceneOrder: ["1A", "1B"],
  eventOrder: [],
  scenePoint(scene_id, point) { return { kind: "scene_point", scene_id, point, target_turn: point === "handoff" ? 100 : 0 }; },
  eventPoint(event_id) { return { kind: "pacing_event", scene_id: "1A", event_id, target_turn: 0 }; },
  isConditional() { return false; },
};

function pacingWithEvent(event_id, target_turn, conditional) {
  return {
    ...pacing,
    eventOrder: [event_id],
    scenePoint(scene_id, point) {
      return { kind: "scene_point", scene_id, point, target_turn: point === "min" ? 0 : point === "nudge" ? 4 : 100 };
    },
    eventPoint(id) { return { kind: "pacing_event", scene_id: "1A", event_id: id, target_turn }; },
    isConditional() { return conditional; },
  };
}

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

function response(scene_id, text, { enter = false, turnsSinceEntry = enter ? 0 : 1, committed = 1, firedPacingEventIds = [] } = {}) {
  return {
    state: {
      scene_id,
      turns_since_scene_entry: turnsSinceEntry,
      fired_storylet_ids: Array(committed).fill("reveal"),
      fired_pacing_event_ids: firedPacingEventIds,
    },
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
  assert.deepEqual(h.inputs, ["Search the 1A.", "Search under the drawer in her workstation.", "Search the 1B."]);
  assert.equal(openings[0].via, "entry-output");
  assert.equal(openings[1].text, "1B opening.");
  assert.equal(turns[1].text, "departure leaves.");
});

test("fails with the bounded terminal error when the target scene is never reached", async () => {
  const h = harness(Array.from({ length: 4 }, () => response("1A", "still here", { committed: 0 })));
  await assert.rejects(
    () => walkScenes({ page: fakePage(), pacing, sceneIds: ["1B"], maxTurns: 4, exploreFor: () => "Search the House.", ...h }),
    /exceeded its \d+-turn limit/,
  );
  assert.equal(h.inputs.length, 4);
});

test("allows a reveal-free interval before entering 1B", async () => {
  const h = harness([
    ...Array.from({ length: 6 }, () => response("1A", "still here", { committed: 0 })),
    response("1B", "departure", { enter: true, committed: 0 }),
    response("1B", "explore", { committed: 0 }),
  ]);
  const openings = [];
  await walkScenes({ page: fakePage(), pacing, sceneIds: ["1A", "1B"], exploreFor: (id) => `Search the ${id}.`, ...h, onOpening: (opening) => openings.push(opening) });
  assert.equal(openings[1].text, "1B opening.");
});

test("arms a conditional event only while strictly ahead of its due turn", async () => {
  const event = pacingWithEvent("conditional", 2, true);
  const armed = [];
  const h = harness([
    response("1A", "one", { turnsSinceEntry: 1, committed: 0 }),
    response("1A", "two", { turnsSinceEntry: 2, committed: 0 }),
    response("1A", "three", { turnsSinceEntry: 3, committed: 0 }),
    response("1B", "departure", { enter: true, committed: 0 }),
    response("1B", "explore", { committed: 0 }),
  ]);
  await walkScenes({ page: fakePage(), pacing: event, controller: { arm: (milestone) => armed.push(milestone) }, sceneIds: ["1A", "1B"], exploreFor: () => "Search the House.", ...h });
  assert.deepEqual(armed.slice(0, 3), [event.eventPoint("conditional"), event.eventPoint("conditional"), event.scenePoint("1A", "nudge")]);
});

test("arms an unconditional event due at the current turn", async () => {
  const event = pacingWithEvent("unconditional", 0, false);
  const armed = [];
  const h = harness([response("1A", "still here", { committed: 0 })]);
  await walkScenes({ page: fakePage(), pacing: event, controller: { arm: (milestone) => armed.push(milestone) }, sceneIds: ["1A"], exploreFor: () => "Search the House.", ...h });
  assert.deepEqual(armed[0], event.eventPoint("unconditional"));
});

test("stops arming a fired pacing event", async () => {
  const event = pacingWithEvent("fired", 2, false);
  const armed = [];
  const h = harness([
    response("1A", "one", { committed: 0, firedPacingEventIds: ["fired"] }),
    response("1A", "two", { committed: 0 }),
    response("1B", "departure", { enter: true, committed: 0 }),
    response("1B", "explore", { committed: 0 }),
  ]);
  await walkScenes({ page: fakePage(), pacing: event, controller: { arm: (milestone) => armed.push(milestone) }, sceneIds: ["1A", "1B"], exploreFor: () => "Search the House.", ...h });
  assert.deepEqual(armed.slice(0, 2), [event.eventPoint("fired"), event.scenePoint("1A", "nudge")]);
});
