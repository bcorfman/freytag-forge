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

test("builds scene judge inputs and skips scenes without usable narration", () => {
  const [first, second] = buildSceneJudgments({
    replicates: [{ replicate: 1, scenes: [
      { scene: "1A", opening_text: "Opening", transition_turn: 3, turns: [
        { turn: 1, input: "look", text: "Looked", grounding_ids: ["z", "a"] },
        { turn: 2, input: "bad", text: "ignored", rejected: true, grounding_ids: ["bad"] },
        { turn: 3, input: "leave", text: "Leaving", grounding_ids: ["a", "b"] },
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
    revealedKnowledgeIds: ["a", "b", "bad", "c", "z"],
  });
  assert.equal(second.skipped, true);
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
