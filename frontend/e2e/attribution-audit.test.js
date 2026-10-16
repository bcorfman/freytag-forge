import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { auditAttribution } from "./attribution-audit.js";

test("audits joined turns, skips missing bundles, and reports suspicious forced turns", () => {
  const dir = mkdtempSync(join(tmpdir(), "attribution-audit-"));
  const scenes = { "rep-1": { "1A": { turns: [
    { turn: 1, text: "No bundle." },
    { turn: 2, text: "Michelle's phone is still here, and it is not damaged. Her tablet and work bag are gone. Her chair is tipped over and the back door was forced, but nothing else was taken. This was not looting. Someone came for Michelle." },
    { turn: 3, text: "Forced narrator only.", rejected: false },
  ] } } };
  const bundles = { "rep-1": { "1A": { bundles: [
    { turn: 2, attempt_bundle: { outcome: "committed", transition_cause: "none", selected_reveal: { knowledge_ids: ["k_sl_1a_a_r1"], delivery_fact_ids: [] }, cue_stage: {}, pre_state: {}, committed_delta: {}, story_complete: false } },
    { turn: 3, attempt_bundle: { outcome: "committed", transition_cause: "forced", selected_reveal: {}, cue_stage: {}, pre_state: {}, committed_delta: {}, story_complete: false } },
  ] } } };
  writeFileSync(join(dir, "e2e-blind-player-r1.json"), JSON.stringify(scenes));
  writeFileSync(join(dir, "e2e-blind-player-bundles-r1.json"), JSON.stringify(bundles));
  const report = auditAttribution(dir);
  assert.equal(report.totals.turns_skipped_no_bundle, 1);
  assert.equal(report.totals.turns_audited, 2);
  assert.equal(report.totals.eligible_texts_found, 1);
  assert.equal(report.totals.suspicious_forced_timer_or_complete_without_authored_span.length, 1);
});
