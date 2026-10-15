import test from "node:test";
import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";

import { buildSceneJudgments, judgeJourneys } from "./judge-journeys.js";

const fixed = {
  verdict: "pass",
  protected_safe: true,
  exit_motivated: true,
  rewards_investigation: true,
  scene_local: true,
  progressive: true,
  canon_consistent: true,
  rich: true,
};

test("builds scene judge inputs from committed reveal evidence and skips scenes without usable narration", () => {
  const [first, second] = buildSceneJudgments({
    replicates: [{ replicate: 1, scenes: [
      { scene: "1A", opening_text: "Opening", transition_turn: 3, turns: [
        { turn: 1, input: "look", text: "Looked", grounding_ids: ["ignored"], attempt_bundle: {
          outcome: "committed", selected_reveal: { knowledge_ids: ["z", "a"] },
        } },
        { turn: 2, input: "bad", text: "ignored", rejected: true, grounding_ids: ["bad"] },
        { turn: 3, input: "leave", text: "Leaving", grounding_ids: ["ignored-too"], attempt_bundle: {
          outcome: "rejected", selected_reveal: { knowledge_ids: ["bad-bundle"] },
        } },
        { turn: 4, input: "empty", text: "", grounding_ids: ["c"] },
      ] },
      { scene: "1B", opening_text: "Next", transition_turn: null, turns: [{ turn: 1, input: "no", text: "", rejected: true }] },
    ] }],
  });
  assert.deepEqual(first, {
    replicate: 1, scene_id: "1A", sceneId: "1A", opening: "Opening",
    turns: [
      { player_input: "look", narration: "Looked", left_scene: false, beats_projected: [] },
      { player_input: "leave", narration: "Leaving", left_scene: true, beats_projected: [] },
    ],
    revealedKnowledgeIds: ["a", "c", "z"],
    reveal_evidence: "mixed",
  });
  assert.equal(second.skipped, true);
});

test("uses committed bundle knowledge ids, ignores rejected and non-committed turns", () => {
  const [scene] = buildSceneJudgments({ replicates: [{ replicate: 1, scenes: [{ scene: "1A", turns: [
    { text: "committed", attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: ["k2", "k1"] } }, grounding_ids: ["wrong"] },
    { text: "rejected", rejected: true, attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: ["bad"] } }, grounding_ids: ["bad-grounding"] },
    { text: "broken", attempt_bundle: { outcome: "game_break", selected_reveal: { knowledge_ids: ["game-break"] } }, grounding_ids: ["wrong-too"] },
    { text: "failed", attempt_bundle: { outcome: "operational_failure", selected_reveal: { knowledge_ids: ["failure"] } }, grounding_ids: ["wrong-three"] },
  ] }] }] });
  assert.deepEqual(scene.revealedKnowledgeIds, ["k1", "k2"]);
  assert.equal(scene.reveal_evidence, "committed_bundles");
});

test("marks runtime-authored delivery reasons and omits them otherwise", () => {
  const [scene] = buildSceneJudgments({ replicates: [{ replicate: 1, scenes: [{ scene: "1A", turns: [
    { turn: 1, input: "forced", text: "forced", attempt_bundle: { outcome: "committed", transition_cause: "forced" } },
    { turn: 2, input: "timer", text: "timer", attempt_bundle: { outcome: "committed", transition_cause: "timer" } },
    { turn: 3, input: "end", text: "end", attempt_bundle: { outcome: "committed", story_complete: true } },
    { turn: 4, input: "cue", text: "cue", attempt_bundle: { outcome: "committed", cue_stage: { delivered: true } } },
    { turn: 5, input: "delivery", text: "delivery", attempt_bundle: { outcome: "committed", selected_reveal: { delivery_fact_ids: ["fact-1"] } } },
    { turn: 6, input: "plain", text: "plain", attempt_bundle: { outcome: "committed" } },
    { turn: 7, input: "rejected", text: "rejected", attempt_bundle: { outcome: "rejected", transition_cause: "forced", cue_stage: { delivered: true } } },
    { turn: 8, input: "broken", text: "broken", attempt_bundle: { outcome: "game_break", story_complete: true } },
    { turn: 9, input: "legacy", text: "legacy" },
  ] }] }] });
  assert.deepEqual(scene.turns.slice(0, 5).map((turn) => turn.authored_delivery), [
    ["forced_handoff"],
    ["timer_handoff"],
    ["ending"],
    ["cue_delivered"],
    ["delivery_facts"],
  ]);
  assert.equal("authored_delivery" in scene.turns[5], false);
  assert.equal("authored_delivery" in scene.turns[6], false);
  assert.equal("authored_delivery" in scene.turns[7], false);
  assert.equal("authored_delivery" in scene.turns[8], false);
});

test("marks authored delivery on a joined bundle", () => {
  const [scene] = buildSceneJudgments({ replicates: [{ replicate: 1, scenes: [{ scene: "1A", turns: [
    { turn: 1, input: "leave", text: "Leaving" },
  ], bundles: [{ turn: 1, attempt_bundle: { outcome: "committed", transition_cause: "forced" } }] }] }] });
  assert.deepEqual(scene.turns[0].authored_delivery, ["forced_handoff"]);
});

test("falls back to grounding ids without bundles and marks mixed reports", () => {
  const [scene] = buildSceneJudgments({ replicates: [{ replicate: 1, scenes: [{ scene: "1A", turns: [
    { text: "bundled", attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: ["committed"] } }, grounding_ids: ["not-knowledge"] },
    { text: "legacy", grounding_ids: ["legacy", "committed"] },
    { text: "rejected", rejected: true, grounding_ids: ["bad"] },
  ] }] }] });
  assert.deepEqual(scene.revealedKnowledgeIds, ["committed", "legacy"]);
  assert.equal(scene.reveal_evidence, "mixed");
});

test("marks all-legacy reports as grounding fallback evidence", () => {
  const [scene] = buildSceneJudgments({ replicates: [{ replicate: 1, scenes: [{ scene: "1A", turns: [
    { text: "legacy", grounding_ids: ["legacy"] },
  ] }] }] });
  assert.deepEqual(scene.revealedKnowledgeIds, ["legacy"]);
  assert.equal(scene.reveal_evidence, "grounding_fallback");
});

test("marks all-bundle reports as committed bundle evidence", () => {
  const [scene] = buildSceneJudgments({ replicates: [{ replicate: 1, scenes: [{ scene: "1A", turns: [
    { text: "committed", attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: ["k1"] } } },
  ] }] }] });
  assert.equal(scene.reveal_evidence, "committed_bundles");
});

test("joins real report bundles to turn-log turns", () => {
  const [scene] = buildSceneJudgments({ replicates: [{ replicate: 1, scenes: [{ scene: "1A", turns: [
    { turn: 1, text: "committed", grounding_ids: ["wrong"], outcome: "committed" },
    { turn: 2, text: "also committed", grounding_ids: ["wrong-too"], outcome: "committed" },
  ], bundles: [
    { turn: 1, attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: ["k2", "k1"] } } },
    { turn: 2, attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: ["k3"] } } },
  ] }] }] });
  assert.deepEqual(scene.revealedKnowledgeIds, ["k1", "k2", "k3"]);
  assert.equal(scene.reveal_evidence, "committed_bundles");
});

test("joined rejected and game-break bundles contribute nothing", () => {
  const [scene] = buildSceneJudgments({ replicates: [{ replicate: 1, scenes: [{ scene: "1A", turns: [
    { turn: 1, text: "rejected", grounding_ids: ["wrong"] },
    { turn: 2, text: "broken", grounding_ids: ["wrong-too"] },
  ], bundles: [
    { turn: 1, attempt_bundle: { outcome: "rejected", selected_reveal: { knowledge_ids: ["rejected"] } } },
    { turn: 2, attempt_bundle: { outcome: "game_break", selected_reveal: { knowledge_ids: ["game-break"] } } },
  ] }] }] });
  assert.deepEqual(scene.revealedKnowledgeIds, []);
  assert.equal(scene.reveal_evidence, "committed_bundles");
});

test("partial joined bundles retain grounding fallback as mixed evidence", () => {
  const [scene] = buildSceneJudgments({ replicates: [{ replicate: 1, scenes: [{ scene: "1A", turns: [
    { turn: 1, text: "committed", grounding_ids: ["wrong"] },
    { turn: 2, text: "legacy", grounding_ids: ["legacy"] },
  ], bundles: [{ turn: 1, attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: ["committed"] } } }] }] }] });
  assert.deepEqual(scene.revealedKnowledgeIds, ["committed", "legacy"]);
  assert.equal(scene.reveal_evidence, "mixed");
});

test("inline bundles win over joined bundles and unmatched bundles are ignored", () => {
  const [scene] = buildSceneJudgments({ replicates: [{ replicate: 1, scenes: [{ scene: "1A", turns: [
    { turn: 1, text: "inline", attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: ["inline"] } } },
    { turn: 2, text: "first duplicate", grounding_ids: ["fallback"] },
  ], bundles: [
    { turn: 1, attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: ["joined"] } } },
    { turn: 2, attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: ["first"] } } },
    { turn: 2, attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: ["duplicate"] } } },
    { turn: 99, attempt_bundle: { outcome: "committed", selected_reveal: { knowledge_ids: ["unmatched"] } } },
  ] }] }] });
  assert.deepEqual(scene.revealedKnowledgeIds, ["first", "inline"]);
  assert.equal(scene.reveal_evidence, "committed_bundles");
});

test("judges sequentially, scores booleans, and records failures", async () => {
  const calls = [];
  const report = { replicates: [{ replicate: 1, scenes: [
    { scene: "1A", opening_text: "A", turns: [{ turn: 1, input: "a", text: "A" }] },
    { scene: "1B", opening_text: "B", turns: [{ turn: 1, input: "b", text: "B" }] },
  ] }] };
  const result = await judgeJourneys(report, { judge: async ({ sceneId }) => {
    calls.push(sceneId);
    if (sceneId === "1B") throw new Error("boom");
    return fixed;
  } });
  assert.deepEqual(calls, ["1A", "1B"]);
  assert.equal(result.replicates[0].score, 7);
  assert.equal(result.replicates[0].max_score, 7);
  assert.equal(result.score, 7);
  assert.equal(result.max_score, 7);
  assert.equal(result.replicates[0].scenes[1].error, "boom");
});

test("builds all nine scenes from the recorded report when available", async (t) => {
  const path = "/home/bcorfman/dev/ringer-work/keep/canonical-x3/e2e-blind-player.json";
  try { await access(path); } catch { t.skip("recorded report is absent"); return; }
  const report = JSON.parse(await readFile(path, "utf8"));
  const scenes = buildSceneJudgments({ replicates: [report.replicates.find((replicate) => replicate.replicate === 1)] });
  assert.equal(scenes.length, 9);
  assert.ok(scenes.every((scene) => scene.opening.length > 0));
  assert.ok(Array.isArray(scenes.find((scene) => scene.sceneId === "3C").revealedKnowledgeIds));
});
