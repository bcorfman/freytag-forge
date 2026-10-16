import assert from "node:assert/strict";
import test from "node:test";

import { isQuestionTurn, nextPending, turnRequestBody } from "./clarification.js";

const clarification = {
  original_command: "Open the terminal.",
  noun: "terminal",
  options: [
    { id: "archive", name: "archive terminals" },
    { id: "medical", name: "medical terminal" },
  ],
  round: 2,
};

test("builds a normal turn request and adds pending clarification fields", () => {
  assert.deepEqual(turnRequestBody("session-1", "medical", null), {
    session_id: "session-1",
    player_input: "medical",
  });
  assert.deepEqual(turnRequestBody("session-1", "medical", { original_command: "Open the terminal.", round: 2 }), {
    session_id: "session-1",
    player_input: "medical",
    clarifies: "Open the terminal.",
    clarification_round: 2,
  });
});

test("extracts pending clarification only from a valid question payload", () => {
  assert.deepEqual(nextPending({ clarification }), { original_command: "Open the terminal.", round: 2 });
  assert.equal(nextPending({}), null);
  assert.equal(nextPending({ clarification: null }), null);
  assert.equal(nextPending({ clarification: { ...clarification, original_command: "" } }), null);
  assert.equal(nextPending({ clarification: { ...clarification, round: "2" } }), null);
  assert.equal(nextPending({ clarification: { ...clarification, options: [{ id: "archive" }] } }), null);
  assert.equal(nextPending({ clarification: [] }), null);
  assert.equal(nextPending(null), null);
});

test("recognizes valid question turns and rejects malformed or absent clarification", () => {
  assert.equal(isQuestionTurn({ clarification }), true);
  assert.equal(isQuestionTurn({ lines: ["A normal turn."] }), false);
  assert.equal(isQuestionTurn({ clarification: { ...clarification, round: 1.5 } }), false);
  assert.equal(isQuestionTurn({ clarification: "question" }), false);
});
