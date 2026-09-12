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

test("renders an authored handoff as ordinary narration", () => {
  const authoredText =
    "Michelle's hidden memory card holds a damaged recording that warns Kristin not to trust emergency broadcasts.";
  const blocks = turnBlocks({
    lines: [authoredText],
    segments: [{ kind: "narration", text: authoredText, grounding_ids: ["k_sl_1a_b_r2"] }],
  });

  assert.deepEqual(blocks.map(({ kind, text }) => ({ kind, text })), [{ kind: "narration", text: authoredText }]);
  assert.equal(blocks[0].kind, "narration");
  assert.equal(blocks[0].text.includes("k_sl_1a_b_r2"), false);
});

test("falls back to compatibility lines for non-interaction turns", () => {
  assert.deepEqual(turnBlocks({ lines: ["The next choice is yours."], segments: [] }), [
    { kind: "narration", text: "The next choice is yours." },
  ]);
});

test("shows only the game-break warning, never its pending candidate prose", () => {
  assert.deepEqual(
    turnBlocks({
      game_break: { warning_id: "future_dependency_at_risk", reason: "Choose how to continue." },
      lines: ["The risky candidate must not render."],
      segments: [{ kind: "narration", text: "The risky candidate must not render." }],
    }),
    [],
  );
});
