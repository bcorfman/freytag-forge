import assert from "node:assert/strict";
import test from "node:test";

import { summarizeNegationScope } from "./negation-scope.js";

const identity = { sha: "abc123", runtime: "scene-v1", channel: "staging" };

function payload(overrides = {}) {
  return {
    input: "Open the drawer, but do not take anything yet.",
    scene_in: "1A",
    attempt_bundle: {
      outcome: "committed",
      selected_reveal: { knowledge_ids: ["k_sl_1a_f_r1"] },
      committed_delta: { fact_predicates: ["drawer_open"] },
    },
    semantic_match: { ran: false, matched: "k_sl_1a_f_r1" },
    ...overrides,
  };
}

function turns(overrides = {}) {
  return [
    {
      input: "Do not open the drawer.",
      expect: "blocked",
      payload: payload({
        input: "Do not open the drawer.",
        attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: [] }, committed_delta: {} },
        semantic_match: { ran: false, matched: null },
        ...overrides.first,
      }),
    },
    {
      input: "Open the drawer, never mind.",
      expect: "blocked",
      payload: payload({
        input: "Open the drawer, never mind.",
        attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: [] }, committed_delta: {} },
        semantic_match: { ran: false, matched: null },
        ...overrides.second,
      }),
    },
    {
      input: "Open the drawer, but do not take anything yet.",
      expect: "earned",
      payload: payload(overrides.third),
    },
  ];
}

test("summarizes all three negation-scope turns as ok", () => {
  const summary = summarizeNegationScope({ identity, turns: turns() });

  assert.equal(summary.all_ok, true);
  assert.deepEqual(summary.turns.map(({ ok }) => ok), [true, true, true]);
  assert.deepEqual(summary.turns.map(({ path }) => path), ["none", "none", "exact"]);
});

test("marks a blocked turn that wrongly earns as not ok", () => {
  const summary = summarizeNegationScope({
    identity,
    turns: [{ ...turns()[0], payload: payload({ input: "Do not open the drawer." }) }],
  });

  assert.equal(summary.turns[0].earned_target, true);
  assert.equal(summary.turns[0].ok, false);
  assert.equal(summary.all_ok, false);
});

test("marks an earned turn that earns nothing as not ok", () => {
  const summary = summarizeNegationScope({
    identity,
    turns: [{
      ...turns()[2],
      payload: payload({
        attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: [] }, committed_delta: {} },
        semantic_match: { ran: false, matched: null },
      }),
    }],
  });

  assert.equal(summary.turns[0].earned_target, false);
  assert.equal(summary.turns[0].ok, false);
  assert.equal(summary.all_ok, false);
});

test("marks a rejected turn as not ok", () => {
  const summary = summarizeNegationScope({
    identity,
    turns: [{
      ...turns()[0],
      payload: payload({
        input: "Do not open the drawer.",
        rejected: true,
        status: 409,
        attempt_bundle: { outcome: "rejected", selected_reveal: { knowledge_ids: [] }, committed_delta: {} },
      }),
    }],
  });

  assert.equal(summary.turns[0].rejected, true);
  assert.equal(summary.turns[0].ok, false);
  assert.equal(summary.all_ok, false);
});

test("passes identity through unchanged", () => {
  const summary = summarizeNegationScope({ identity, turns: turns() });

  assert.strictEqual(summary.identity, identity);
  assert.deepEqual(summary.identity, { sha: "abc123", runtime: "scene-v1", channel: "staging" });
});
