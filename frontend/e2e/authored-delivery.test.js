import test from "node:test";
import assert from "node:assert/strict";

import { authoredDeliveryReasons } from "./authored-delivery.js";

test("returns each authored delivery reason from a committed bundle", () => {
  assert.deepEqual(authoredDeliveryReasons({
    outcome: "committed",
    transition_cause: "forced",
    story_complete: true,
    cue_stage: { delivered: true },
    selected_reveal: { delivery_fact_ids: ["fact-1"] },
  }), ["forced_handoff", "ending", "cue_delivered", "delivery_facts"]);
  assert.deepEqual(authoredDeliveryReasons({ outcome: "committed", transition_cause: "timer" }), ["timer_handoff"]);
});

test("returns nothing for non-committed bundles", () => {
  for (const outcome of ["rejected", "game_break", "operational_failure"]) {
    assert.deepEqual(authoredDeliveryReasons({
      outcome,
      transition_cause: "forced",
      story_complete: true,
      cue_stage: { delivered: true },
      selected_reveal: { delivery_fact_ids: ["fact-1"] },
    }), []);
  }
});

test("returns nothing for missing or non-object bundles", () => {
  for (const bundle of [undefined, null, "committed", 42, true, [], () => {}]) {
    assert.deepEqual(authoredDeliveryReasons(bundle), []);
  }
});

test("keeps reasons in stable handoff, ending, cue, delivery order", () => {
  assert.deepEqual(authoredDeliveryReasons({
    outcome: "committed",
    transition_cause: "timer",
    story_complete: true,
    cue_stage: { delivered: true },
    selected_reveal: { delivery_fact_ids: ["fact-1"] },
  }), ["timer_handoff", "ending", "cue_delivered", "delivery_facts"]);
});
