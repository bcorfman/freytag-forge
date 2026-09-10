import test from "node:test";
import assert from "node:assert/strict";

import { buildKnowledgeTimelineReport, recordTurnOutcome } from "./knowledge-timeline-record.js";

test("records a committed redacted audit without segment text", () => {
  const record = recordTurnOutcome({
    input: "Search the drawer for Michelle's research.",
    status: 200,
    headers: {},
    body: {
      knowledge_audit: {
        context_candidate_ids: ["k_sl_1a_b_r2"],
        provider_selected_ids: ["k_sl_1a_b_r2"],
        resolved_source_ids: ["k_sl_1a_b_r2/pkg"],
        accepted_segments: [{ kind: "narration", speaker_id: null, grounding_ids: ["k_sl_1a_b_r2"], text: "secret" }],
        result: "committed",
        rejection_code: null,
        recovery_used: false,
      },
    },
    version: { sha: "abc", channel: "staging" },
  });
  assert.deepEqual(record.provider_selected_ids, ["k_sl_1a_b_r2"]);
  assert.deepEqual(record.accepted_segments, [{ kind: "narration", speaker_id: null, grounding_ids: ["k_sl_1a_b_r2"] }]);
  assert.equal("text" in record.accepted_segments[0], false);
});

test("records a rejected turn from its rejection header", () => {
  const record = recordTurnOutcome({
    input: "Check the front gate.",
    status: 409,
    headers: { "x-freytag-rejection-code": "UNKNOWN_KNOWLEDGE_SELECTION" },
    body: { detail: "rejected" },
    version: { sha: "abc" },
  });
  assert.equal(record.rejection_code, "UNKNOWN_KNOWLEDGE_SELECTION");
  assert.deepEqual(record.context_candidate_ids, []);
  assert.equal(record.result, null);
});

test("records diagnostic-off responses with empty and null audit values", () => {
  const record = recordTurnOutcome({ input: "Examine Michelle's phone.", status: 200, headers: {}, body: {}, version: {} });
  assert.deepEqual(record.context_candidate_ids, []);
  assert.deepEqual(record.accepted_segments, []);
  assert.equal(record.rejection_code, null);
  assert.equal(record.recovery_used, null);
  assert.deepEqual(buildKnowledgeTimelineReport({}, [record]).records, [record]);
});
