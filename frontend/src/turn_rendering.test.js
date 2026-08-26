import assert from "node:assert/strict";
import test from "node:test";

import { turnBlocks } from "./turn_rendering.js";

test("preserves accepted narration and ordered speech and action blocks", () => {
  const blocks = turnBlocks({
    lines: ["The relay groans.", "compatibility only"],
    segments: [
      {
        kind: "speech",
        speaker: { id: "engineer", name: "Iris Vale" },
        addressees: [{ id: "player", name: "You" }],
        text: "We decide together.",
      },
      {
        kind: "action",
        actor: { id: "engineer", name: "Iris" },
        grounding: "expressive",
        text: "She studies the warning display.",
      },
    ],
  });

  assert.deepEqual(blocks.map((block) => block.kind), ["speech", "action"]);
  assert.equal(blocks[0].speaker.name, "Iris Vale");
  assert.equal(blocks[1].grounding, "expressive");
});

test("uses structured narration before compatibility lines", () => {
  assert.deepEqual(turnBlocks({ lines: ["legacy"], segments: [{ kind: "narration", text: "accepted" }] }), [
    { kind: "narration", text: "accepted" },
  ]);
});

test("falls back to compatibility lines for non-interaction turns", () => {
  assert.deepEqual(turnBlocks({ lines: ["The next choice is yours."], segments: [] }), [
    { kind: "narration", text: "The next choice is yours." },
  ]);
});
