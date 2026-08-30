import assert from "node:assert/strict";
import test from "node:test";

import { isTurnRequest } from "./package-clock-request.js";

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
