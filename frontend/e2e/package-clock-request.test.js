import assert from "node:assert/strict";
import test from "node:test";

import { applyTestClock, isTurnRequest } from "./package-clock-request.js";

test("recognizes only the exact turn endpoint and POST method", () => {
  assert.equal(isTurnRequest("https://story.example/api/v1/turn", "POST"), true);
  assert.equal(isTurnRequest("https://story.example/api/v1/turn?session_id=test", "POST"), true);
  assert.equal(isTurnRequest("/api/v1/turn", "POST"), true);

  assert.equal(isTurnRequest("https://story.example/api/v1/session", "POST"), false);
  assert.equal(isTurnRequest("https://story.example/api/v1/game-break", "POST"), false);
  assert.equal(isTurnRequest("https://story.example/api/v1/turn/extra", "POST"), false);
  assert.equal(isTurnRequest("https://story.example/api/v1/turnish", "POST"), false);
  assert.equal(isTurnRequest("https://story.example/api/v1/turn", "GET"), false);
  assert.equal(isTurnRequest("https://api.openai.com/v1/responses", "POST"), false);
  assert.equal(isTurnRequest("https://api.openai.com/api/v1/turn", "POST"), false);
  assert.equal(isTurnRequest("not a URL", "POST"), false);
});

test("replaces the clock fields while preserving nested command input and other fields", () => {
  const original = {
    session_id: "session-1",
    player_input: { command: "inspect", args: ["desk", { side: "left" }] },
    metadata: { tags: ["one", { enabled: true }], count: 2 },
    test_clock_seconds: 99,
    test_clock_token: "old-token",
  };

  const rewritten = JSON.parse(
    applyTestClock(JSON.stringify(original), { deltaSeconds: 0, token: "new-token" }),
  );

  assert.deepEqual(rewritten, {
    ...original,
    test_clock_seconds: 0,
    test_clock_token: "new-token",
  });
});

test("omits the token field when no non-empty token is configured", () => {
  const body = { session_id: "session-1", test_clock_token: "old-token" };

  for (const token of [undefined, null, ""]) {
    const rewritten = JSON.parse(applyTestClock(JSON.stringify(body), { deltaSeconds: 12, token }));
    assert.equal(rewritten.test_clock_seconds, 12);
    assert.equal(Object.hasOwn(rewritten, "test_clock_token"), false);
  }
});

test("rejects malformed JSON with a diagnostic", () => {
  assert.throws(
    () => applyTestClock("{not-json", { deltaSeconds: 1 }),
    /request body is not valid JSON/i,
  );
});

test("rejects a non-integer clock delta with a diagnostic", () => {
  for (const deltaSeconds of [1.5, "2", null, undefined]) {
    assert.throws(
      () => applyTestClock("{}", { deltaSeconds }),
      /deltaSeconds must be an integer/i,
    );
  }
});
