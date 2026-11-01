import assert from "node:assert/strict";
import test from "node:test";

import { classifyFailure, evaluateSpine, loadExpectedReveals } from "./spine-record.js";

test("classifies infrastructure failures and quota stops", () => {
  const cases = [
    ["Turn API returned HTTP 503: unavailable", "HTTP 503"],
    ["Turn API returned HTTP 429: rate limited", "HTTP 429"],
    ["Turn API did not produce a response within 30000ms.", "turn_timeout"],
    ["Turn API request failed for https://staging.example/turn: ECONNRESET", "request_failed"],
    ["TypeError: Failed to fetch", "fetch_failed"],
    ["Access blocked by CORS policy", "network_error"],
    ["net::ERR_FAILED while loading resource", "network_error"],
  ];
  for (const [message, code] of cases) {
    assert.deepEqual(classifyFailure(new Error(message)), { class: "infrastructure", code });
  }
  for (const code of ["AI_QUOTA_EXCEEDED", "AI_DAILY_BUDGET_EXCEEDED", "BUDGET_UNAVAILABLE"]) {
    assert.deepEqual(classifyFailure(new Error(`HTTP 429 ${code}`)), { class: "infrastructure", code, quotaStop: true });
  }
});

test("classifies gameplay assertions and conflict rejections", () => {
  assert.deepEqual(classifyFailure(new Error("expected scene order")), { class: "gameplay", code: "other" });
  assert.deepEqual(classifyFailure(new Error("Turn API returned HTTP 409: rejected")), { class: "gameplay", code: "other" });
});

const expected = {
  "1A": ["a1", "a2"],
  "2C": ["k_sl_2c_c_r1"],
  "3C": ["c1"],
};

function turn(scene_in, scene_out, bundle, latency_ms, delivery = {}) {
  return { scene_in, scene_out, bundle, state_story_complete: false, latency_ms, delivery };
}

test("evaluates a fully committed reveal chain and latency statistics", () => {
  const result = evaluateSpine({
    sceneOrder: ["1A", "2C", "3C"],
    expected,
    perTurn: [
      turn("1A", "1A", { outcome: "committed", transition_cause: null, story_complete: false, selected_reveal: { knowledge_ids: ["a2", "a1"] } }, 10),
      turn("2C", "2C", { outcome: "committed", transition_cause: "earned", story_complete: false, selected_reveal: { knowledge_ids: ["k_sl_2c_c_r1"] } }, 20),
      turn("3C", "3C", { outcome: "committed", transition_cause: "timer", story_complete: true, selected_reveal: { knowledge_ids: ["c1"] } }, 30),
    ],
  });
  assert.deepEqual(result.committed_by_scene, { "1A": ["a1", "a2"], "2C": ["k_sl_2c_c_r1"], "3C": ["c1"] });
  assert.deepEqual(result.chain_misses, {});
  assert.deepEqual(result.exits, { none: 1, earned: 1, timer: 1 });
  assert.equal(result.story_complete, true);
  assert.equal(result.observation_committed, true);
  assert.deepEqual(result.latency, { min: 10, median: 20, max: 30, total: 60 });
});

test("reports a missing 2C c_r2 and ignores rejected bundle reveals", () => {
  const result = evaluateSpine({
    sceneOrder: ["1A", "2C"],
    expected,
    perTurn: [
      turn("1A", "2C", { outcome: "rejected", transition_cause: "earned", story_complete: false, selected_reveal: { knowledge_ids: ["a1"] } }, 4),
      turn("2C", "2C", { outcome: "committed", transition_cause: "earned", story_complete: false, selected_reveal: { knowledge_ids: [] } }, 8),
    ],
  });
  assert.deepEqual(result.committed_by_scene, { "1A": [], "2C": [] });
  assert.deepEqual(result.chain_misses, { "1A": ["a1", "a2"], "2C": ["k_sl_2c_c_r1"] });
  assert.equal(result.observation_committed, false);
});

test("counts no-bundle turns, null exits, completion sources, and unreached scenes", () => {
  const stateComplete = evaluateSpine({
    sceneOrder: ["1A"],
    expected: { "1A": ["a1"], "2C": ["c2"] },
    perTurn: [
      { scene_in: "1A", scene_out: "1A", bundle: null, state_story_complete: true, latency_ms: 5, delivery: {} },
      turn("1A", "1A", { outcome: "committed", transition_cause: null, story_complete: false, selected_reveal: { knowledge_ids: ["a1"] } }, 15),
    ],
  });
  assert.equal(stateComplete.story_complete, true);
  assert.equal(stateComplete.no_bundle_turns, 1);
  assert.equal(stateComplete.delivery.no_bundle_turns, 1);
  assert.deepEqual(stateComplete.exits, { none: 1 });
  assert.deepEqual(stateComplete.chain_misses, {});

  const bundleComplete = evaluateSpine({
    sceneOrder: ["1A"],
    expected: { "1A": [] },
    perTurn: [turn("1A", "1A", { outcome: "rejected", transition_cause: null, story_complete: true, selected_reveal: {} }, 1)],
  });
  assert.equal(bundleComplete.story_complete, true);
});

test("loads the generated expected reveal mapping", async () => {
  const loaded = await loadExpectedReveals();
  assert.equal(loaded["2C"].includes("k_sl_2c_c_r1"), true);
});
