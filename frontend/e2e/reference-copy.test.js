import assert from "node:assert/strict";
import test from "node:test";

import { summarizeReferenceCopy } from "./reference-copy.js";

const identity = { sha: "abc123", runtime: "scene-v1", channel: "staging" };
const input = "Copy the encrypted Project Echelon file to my laptop.";

function payload(overrides = {}) {
  return {
    input,
    scene_in: "2C",
    state: { scene_id: "2C" },
    attempt_bundle: {
      outcome: "committed",
      selected_reveal: { knowledge_ids: ["k_sl_2c_c_r1"] },
      committed_delta: { fact_predicates: ["evidence_copied"] },
    },
    semantic_match: { ran: false, matched: "k_sl_2c_c_r1" },
    segments: [
      { kind: "narration", text: "The encrypted file copies across." },
      { kind: "action", text: "Your laptop receives it." },
      { kind: "dialogue", text: "Michelle says, \"It is done.\"" },
      { kind: "system", text: "not narration" },
    ],
    ...overrides,
  };
}

test("summarizes the exact-match path", () => {
  const summary = summarizeReferenceCopy({
    identity,
    walkTurns: [{ scene_out: "1A" }, { scene_out: "2C" }],
    copyPayload: payload(),
  });

  assert.equal(summary.path, "exact");
  assert.equal(summary.earned_c_r1, true);
  assert.equal(summary.reached_2c, true);
  assert.deepEqual(summary.committed_reveal_ids, ["k_sl_2c_c_r1"]);
  assert.equal(summary.narration, 'The encrypted file copies across. Your laptop receives it. Michelle says, "It is done."');
});

test("summarizes the semantic-match path", () => {
  const summary = summarizeReferenceCopy({
    walkTurns: [{ state: { scene_id: "2C" } }],
    copyPayload: payload({ semantic_match: { ran: true, matched: "k_sl_2c_c_r1" } }),
  });

  assert.equal(summary.path, "semantic");
  assert.equal(summary.walk_turn_count, 1);
});

test("reports none when the target reveal was not earned", () => {
  const summary = summarizeReferenceCopy({
    copyPayload: payload({
      attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: ["other"] }, committed_delta: {} },
      semantic_match: { ran: true, matched: "other" },
    }),
  });

  assert.equal(summary.path, "none");
  assert.equal(summary.earned_c_r1, false);
});

test("reports unknown when a committed target has no semantic-match field", () => {
  const summary = summarizeReferenceCopy({ copyPayload: payload({ semantic_match: undefined }) });

  assert.equal(summary.path, "unknown");
  assert.equal(summary.semantic_match, null);
});

test("reports a rejected payload and does not count its selected reveal", () => {
  const summary = summarizeReferenceCopy({
    copyPayload: payload({
      status: 409,
      rejected: true,
      attempt_bundle: { outcome: "rejected", selected_reveal: { knowledge_ids: ["k_sl_2c_c_r1"] }, committed_delta: {} },
    }),
  });

  assert.equal(summary.rejected, true);
  assert.equal(summary.earned_c_r1, false);
  assert.equal(summary.path, "none");
});

test("passes identity through unchanged", () => {
  const summary = summarizeReferenceCopy({ identity, copyPayload: payload() });

  assert.strictEqual(summary.identity, identity);
  assert.deepEqual(summary.identity, { sha: "abc123", runtime: "scene-v1", channel: "staging" });
});
