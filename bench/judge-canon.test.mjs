import assert from "node:assert/strict";
import test from "node:test";
import { resolve } from "node:path";

import { canonForInput, packageCanon } from "./judge-canon.mjs";

const relativeStoryRoot = "data/stories/continuity-initiative";
const absoluteStoryRoot = resolve(relativeStoryRoot);

function assertSceneOneBCanon(canon) {
  assert.match(canon.plot, /## Scene 1B/);
  assert.doesNotMatch(canon.plot, /## Scene 1C/);
  assert.notEqual(canon.storylets, "");
  assert.notEqual(canon.routes, "");
  assert.notEqual(canon.pacing, "");
  assert.notEqual(canon.world, "");
}

test("package canon uses the selected scene from an absolute package path", () => {
  assertSceneOneBCanon(packageCanon("1B", absoluteStoryRoot));
});

test("package canon resolves a relative package path from the current directory", () => {
  assertSceneOneBCanon(packageCanon("1B", relativeStoryRoot));
});

test("package canon keeps the final scene plot block", () => {
  const canon = packageCanon("3C", relativeStoryRoot);

  assert.match(canon.plot, /## Scene 3C/);
  assert.ok(canon.plot.length > "## Scene 3C".length);
});

test("canon selection falls back to the scene canon without a package path", () => {
  const canon = canonForInput({ scene_id: "1A" });

  assert.equal(typeof canon.situation, "string");
  assert.ok(canon.situation.length > 0);
});
