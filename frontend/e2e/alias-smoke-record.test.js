import assert from "node:assert/strict";
import test from "node:test";

import { summarizeAliasSmoke, usesPhotoWord } from "./alias-smoke-record.js";

test("detects when text has no photo words", () => {
  assert.equal(usesPhotoWord("Inspect Michelle's phone."), false);
  assert.equal(usesPhotoWord("Search the kitchen for evidence."), false);
});

test("detects photo, photograph, and picture forms", () => {
  assert.equal(usesPhotoWord("Look at the photo."), true);
  assert.equal(usesPhotoWord("Check the photographs."), true);
  assert.equal(usesPhotoWord("Review the pictures."), true);
});

test("counts a term-leak rejection among photo prompts", () => {
  const summary = summarizeAliasSmoke({
    photoTurns: [
      { input: "Look through the photos.", status: 409, rejection_code: "narration_known_term_leak", narration: "" },
      { input: "Check the phone.", status: 200, rejection_code: null, narration: "The phone is cold." },
    ],
  });
  assert.equal(summary.photo_prompts, 2);
  assert.equal(summary.photo_prompts_rejected, 1);
  assert.equal(summary.photo_rejections_term_leak, 1);
  assert.equal(summary.narrations_with_photo_word, 0);
  assert.equal(summary.elicited, false);
});

test("distinguishes committed and missing 1B reveals", () => {
  const summary = summarizeAliasSmoke({
    oneBTurns: [
      { status: 200, committed_knowledge_ids: ["k_sl_1b_a_r2"] },
      { status: 409, committed_knowledge_ids: [] },
    ],
  });
  assert.equal(summary.one_b_a_r2_committed, true);
  assert.equal(summary.one_b_b_r1_committed, false);
  assert.equal(summary.one_b_rejected, 1);
});

test("summarizes empty inputs", () => {
  assert.deepEqual(summarizeAliasSmoke(), {
    photo_prompts: 0,
    photo_prompts_rejected: 0,
    photo_rejections_term_leak: 0,
    narrations_with_photo_word: 0,
    elicited: false,
    one_b_a_r2_committed: false,
    one_b_b_r1_committed: false,
    one_b_rejected: 0,
  });
});
