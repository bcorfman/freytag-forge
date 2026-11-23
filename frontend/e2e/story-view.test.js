import assert from "node:assert/strict";
import test from "node:test";
import { resolve } from "node:path";

import { loadAuthoringView } from "./story-view.js";

test("loads and caches the live authoring view", () => {
  const view = loadAuthoringView();
  assert.deepEqual(Object.keys(view).sort(), ["frames", "handoffs", "knowledge", "pacing", "routes"]);
  assert.strictEqual(loadAuthoringView(), view);
});

test("reports an unusable FREYTAG_PYTHON descriptively", () => {
  const previous = process.env.FREYTAG_PYTHON;
  process.env.FREYTAG_PYTHON = resolve("/tmp", "missing-freytag-python");
  try {
    assert.throws(
      () => loadAuthoringView(resolve("/tmp", "story-view-bad-python")),
      /missing-freytag-python.*failed with exit status/s,
    );
  } finally {
    if (previous === undefined) delete process.env.FREYTAG_PYTHON;
    else process.env.FREYTAG_PYTHON = previous;
  }
});
