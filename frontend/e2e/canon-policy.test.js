import assert from "node:assert/strict";
import { join } from "node:path";
import test from "node:test";

import { requiredPacingEvents } from "./canon-policy.js";
import { loadPackagePacing } from "./package-clock.js";

const repoRoot = join(import.meta.dirname, "../..");

function fakePacing(events) {
  const eventById = new Map(events.map((event) => [event.id, event]));
  return {
    sceneOrder: ["A", "B", "C"],
    eventOrder: events.map((event) => event.id),
    eventPoint(eventId) {
      return eventById.get(eventId);
    },
  };
}

test("does not require an event in a scene left before its target turn", () => {
  const pacing = fakePacing([{ id: "source_late", scene_id: "A", target_turn: 5 }]);

  assert.deepEqual(
    requiredPacingEvents({
      pacing,
      sourceSceneId: "A",
      reachedSceneId: "B",
      observedTurns: 0,
      turnsSinceSceneEntry: 2,
    }),
    [],
  );
});

test("requires an event once the player remains in its scene past its target turn", () => {
  const pacing = fakePacing([{ id: "source_late", scene_id: "A", target_turn: 5 }]);

  assert.deepEqual(
    requiredPacingEvents({
      pacing,
      sourceSceneId: "A",
      reachedSceneId: "A",
      observedTurns: 5,
      turnsSinceSceneEntry: 4,
    }),
    ["source_late"],
  );
});

test("requires a source event when departure is exactly its due turn", () => {
  const pacing = fakePacing([{ id: "departure_due", scene_id: "A", target_turn: 3 }]);

  assert.deepEqual(
    requiredPacingEvents({
      pacing,
      sourceSceneId: "A",
      reachedSceneId: "B",
      observedTurns: 0,
      turnsSinceSceneEntry: 2,
    }),
    ["departure_due"],
  );
  assert.deepEqual(
    requiredPacingEvents({
      pacing,
      sourceSceneId: "A",
      reachedSceneId: "B",
      observedTurns: 0,
      turnsSinceSceneEntry: 1,
    }),
    [],
  );
});

test("does not require events from scenes after or before the reached scene", () => {
  const pacing = fakePacing([
    { id: "earlier", scene_id: "A", target_turn: 0 },
    { id: "future", scene_id: "C", target_turn: 0 },
  ]);

  assert.deepEqual(
    requiredPacingEvents({
      pacing,
      sourceSceneId: "B",
      reachedSceneId: "B",
      observedTurns: 10,
      turnsSinceSceneEntry: 10,
    }),
    [],
  );
});

test("does not compare a destination turn counter with source-scene events", () => {
  const pacing = fakePacing([
    { id: "source_late", scene_id: "A", target_turn: 5 },
    { id: "destination_entry", scene_id: "B", target_turn: 0 },
  ]);

  assert.deepEqual(
    requiredPacingEvents({
      pacing,
      sourceSceneId: "A",
      reachedSceneId: "B",
      observedTurns: 0,
      turnsSinceSceneEntry: 2,
    }),
    ["destination_entry"],
  );
});

test("does not re-require an event from an earlier scene after advancing", () => {
  const pacing = fakePacing([{ id: "already_handled", scene_id: "A", target_turn: 0 }]);

  assert.deepEqual(
    requiredPacingEvents({
      pacing,
      sourceSceneId: "B",
      reachedSceneId: "C",
      observedTurns: 0,
      turnsSinceSceneEntry: 0,
    }),
    [],
  );
});

test("does not require transfer_window_1c after the real 1C early exit", () => {
  const pacing = loadPackagePacing({ storyId: "continuity_initiative", repoRoot });

  const required = requiredPacingEvents({
    pacing,
    sourceSceneId: "1C",
    reachedSceneId: "2A",
    observedTurns: 0,
    turnsSinceSceneEntry: 2,
  });

  assert.equal(required.includes("transfer_window_1c"), false);
  assert.deepEqual(required, []);
});
