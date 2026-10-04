import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import test from "node:test";
import { aggregate } from "./blind-player.js";
import { mergeReports, replicatePlan } from "./merge-blind-player.js";

const execFileAsync = promisify(execFile);
const run = (replicate, scene = "1A") => ({
  replicate,
  scene,
  commands: [`Search the room ${replicate}.`],
  turns: [{ turn: 1, input: `Search the room ${replicate}.`, text: "A result.", scene_id: scene }],
  turn_count: 1,
  transition_fired: replicate === 1,
  transition_turn: replicate === 1 ? 1 : null,
  affordances: [],
  stuck_runs: [],
  silent_transition: false,
  rejected_count: 0,
  stopped_on_rejections: false,
  unseen_command_count: 0,
});
const report = (replicate, scene = "1A") => ({ story_id: "continuity_initiative", scene, replicates: [run(replicate, scene)], aggregate: {} });

test("replicatePlan selects either the configured range or one indexed replicate", () => {
  assert.deepEqual(replicatePlan({ E2E_BLIND_REPLICATES: "3" }), { indices: [1, 2, 3], category: "blind-player" });
  assert.deepEqual(replicatePlan({ E2E_BLIND_REPLICATE_INDEX: "2", E2E_BLIND_REPLICATES: "3" }), { indices: [2], category: "blind-player-r2" });
  for (const value of ["0", "4", "abc"]) assert.throws(() => replicatePlan({ E2E_BLIND_REPLICATE_INDEX: value }), /between 1 and 3/);
});

test("mergeReports renumbers runs and recomputes aggregate and markdown", () => {
  const merged = mergeReports([report(7), report(8)]);
  assert.deepEqual(merged.replicates.map((item) => item.replicate), [1, 2]);
  assert.deepEqual(merged.aggregate, aggregate(merged.replicates));
  assert.match(merged.markdown, /# blind-player E2E evaluation/);
  assert.throws(() => mergeReports([]), /empty/);
  assert.throws(() => mergeReports([report(1), report(2, "1B")]), /same story_id and scene/);
  assert.throws(() => mergeReports([{ story_id: "x", scene: "1A" }]), /replicates array/);
});

test("merge CLI writes merged JSON and markdown", async () => {
  const dir = await mkdtemp(join(tmpdir(), "merge-blind-player-"));
  await writeFile(resolve(dir, "e2e-blind-player-r1.json"), JSON.stringify(report(1)));
  await writeFile(resolve(dir, "e2e-blind-player-r2.json"), JSON.stringify(report(2)));
  const script = resolve(import.meta.dirname, "merge-blind-player.js");
  await execFileAsync(process.execPath, [script, dir, "2"]);
  const merged = JSON.parse(await readFile(resolve(dir, "e2e-blind-player.json"), "utf8"));
  assert.deepEqual(merged.replicates.map((item) => item.replicate), [1, 2]);
  assert.match(await readFile(resolve(dir, "e2e-blind-player.md"), "utf8"), /```json/);
});

test("merge CLI names a missing replicate and writes nothing", async () => {
  const dir = await mkdtemp(join(tmpdir(), "merge-blind-player-"));
  await writeFile(resolve(dir, "e2e-blind-player-r1.json"), JSON.stringify(report(1)));
  await writeFile(resolve(dir, "e2e-blind-player-r2.json"), JSON.stringify(report(2)));
  const script = resolve(import.meta.dirname, "merge-blind-player.js");
  await assert.rejects(execFileAsync(process.execPath, [script, dir, "3"]), (error) => {
    assert.equal(error.code, 1);
    return true;
  });
  await assert.rejects(readFile(resolve(dir, "e2e-blind-player.json")));
  await assert.rejects(readFile(resolve(dir, "e2e-blind-player.md")));
});
