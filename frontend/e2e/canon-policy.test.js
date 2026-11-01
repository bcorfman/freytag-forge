import assert from "node:assert/strict";
import { join } from "node:path";
import test from "node:test";

import { answerClarifications, requiredPacingEvents } from "./canon-policy.js";
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

test("returns a non-clarification payload without submitting an answer", async () => {
  const payload = { state: { turn_index: 4 } };
  let submitCalls = 0;

  const result = await answerClarifications({
    payload,
    submit: async () => {
      submitCalls += 1;
      return { state: { turn_index: 5 } };
    },
  });

  assert.equal(result.payload, payload);
  assert.deepEqual(result.answers, []);
  assert.equal(submitCalls, 0);
});

test("answers one clarification with its first option name", async () => {
  const finalPayload = { state: { turn_index: 5 } };
  const submitted = [];

  const result = await answerClarifications({
    payload: {
      clarification: {
        original_command: "Meet the official.",
        noun: "gate",
        options: [{ id: "facility", name: "facility gate" }],
      },
    },
    submit: async (input) => {
      submitted.push(input);
      return finalPayload;
    },
  });

  assert.equal(result.payload, finalPayload);
  assert.deepEqual(result.answers, ["facility gate"]);
  assert.deepEqual(submitted, ["facility gate"]);
});

test("answers chained clarifications in order", async () => {
  const submitted = [];
  const secondClarification = {
    clarification: {
      original_command: "Open the gate.",
      noun: "authorization",
      options: [{ id: "emergency", name: "emergency authorization" }],
    },
  };
  const finalPayload = { state: { turn_index: 8 } };

  const result = await answerClarifications({
    payload: {
      clarification: {
        original_command: "Open the gate.",
        noun: "gate",
        options: [{ id: "surface", name: "surface gate" }],
      },
    },
    submit: async (input) => {
      submitted.push(input);
      return submitted.length === 1 ? secondClarification : finalPayload;
    },
  });

  assert.equal(result.payload, finalPayload);
  assert.deepEqual(result.answers, ["surface gate", "emergency authorization"]);
  assert.deepEqual(submitted, ["surface gate", "emergency authorization"]);
});

test("throws with the original command and noun when clarification exceeds maxRounds", async () => {
  await assert.rejects(
    answerClarifications({
      payload: {
        clarification: {
          original_command: "Meet the imprisoned official.",
          noun: "gate",
          options: [{ id: "facility", name: "facility gate" }],
        },
      },
      submit: async () => ({
        clarification: {
          original_command: "Meet the imprisoned official.",
          noun: "gate",
          options: [{ id: "surface", name: "surface gate" }],
        },
      }),
      maxRounds: 1,
    }),
    /Meet the imprisoned official[\s\S]*gate/,
  );
});

test("throws when clarification options are empty", async () => {
  await assert.rejects(
    answerClarifications({
      payload: {
        clarification: {
          original_command: "Open the gate.",
          noun: "gate",
          options: [],
        },
      },
      submit: async () => ({ state: {} }),
    }),
    /options are empty/,
  );
});

test("throws when the first clarification option has no name", async () => {
  await assert.rejects(
    answerClarifications({
      payload: {
        clarification: {
          original_command: "Open the gate.",
          noun: "gate",
          options: [{ id: "facility" }],
        },
      },
      submit: async () => ({ state: {} }),
    }),
    /first option name must be a non-empty string/,
  );
});
