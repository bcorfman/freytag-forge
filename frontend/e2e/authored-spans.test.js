import test from "node:test";
import assert from "node:assert/strict";

import {
  attributeNarration,
  eligibleAuthoredTexts,
  knowledgeAvailableByTurn,
  loadAuthoredText,
} from "./authored-spans.js";

const authored = {
  knowledgeDeliveryTexts: new Map([["k", "A secret delivery."]]),
  cueTexts: new Map([["cue", "A cue arrives."]]),
  handoffFallbackTexts: new Map([["handoff", "The handoff is forced."]]),
  bridgeTextsByScenePair: new Map([["A>B", "The bridge begins."]]),
  entryTexts: new Map([["B", "The new scene opens."]]),
  routeFallbackTexts: new Map([["done", "The ending lands."]]),
  routeFallbacks: [{ text: "The ending lands.", event_id: "ending", fact_ids: ["done"] }],
};

function bundle(overrides = {}) {
  return {
    outcome: "committed",
    transition_cause: "none",
    selected_reveal: { knowledge_ids: [], delivery_fact_ids: [] },
    cue_stage: { delivered: false },
    pre_state: { staged_handoff_fact_ids: [] },
    committed_delta: { fact_predicates: [], scene_from: null, scene_to: null },
    story_complete: false,
    ...overrides,
  };
}

test("loads structural package text and scene-pair bridge", () => {
  const real = loadAuthoredText();
  assert.match(real.bridgeTextsByScenePair.get("3B>3C"), /began the broadcast/);
  assert.equal(real.bridgeTexts.get("t_3b_3c"), real.bridgeTextsByScenePair.get("3B>3C"));
  assert.ok(real.entryTexts.has("3C"));
});

test("loads entry variants by scene", () => {
  const real = loadAuthoredText();
  assert.ok(real.entryVariantTextsBySceneId.get("2A").includes(
    "Kristin still has the copied prisoner numbers. She needs a way into the facility.",
  ));
});

test("attributes the authored ending only on a completed turn", () => {
  const real = loadAuthoredText();
  const completed = eligibleAuthoredTexts(bundle({ story_complete: true }), real);
  const ending = completed.find((item) => item.source.kind === "ending");
  assert.equal(ending.text, real.endingText);
  assert.deepEqual(ending.source, { kind: "ending", id: real.endingSceneId });
  const spans = attributeNarration(real.endingText, completed);
  assert.deepEqual(spans.find((span) => span.origin === "authored").source, {
    kind: "ending",
    id: "3C",
  });
  assert.equal(spans.find((span) => span.origin === "authored").text, real.endingText);
  assert.equal(eligibleAuthoredTexts(bundle(), real).some((item) => item.text === real.endingText), false);
});

test("attributes only verbatim pacing realizations for fired events", () => {
  const real = loadAuthoredText();
  const patrol = real.pacingRealizations.get("patrol_returns_1a")[0];
  const narration = `${patrol} A detective arrives and tells her to leave.`;
  const eligible = eligibleAuthoredTexts(bundle({ pacing_event_ids: ["patrol_returns_1a"] }), real);
  const spans = attributeNarration(narration, eligible);
  assert.deepEqual(spans.find((span) => span.origin === "authored").source, {
    kind: "pacing",
    id: "patrol_returns_1a",
  });
  assert.equal(spans.find((span) => span.origin === "authored").text, patrol);
  assert.equal(spans.find((span) => span.text === " A detective arrives and tells her to leave.").origin, "narrator");
  assert.equal(attributeNarration(patrol, eligibleAuthoredTexts(bundle(), real))[0].origin, "narrator");
});

test("completion does not license an uncommitted route fallback", () => {
  const completed = eligibleAuthoredTexts(bundle({ story_complete: true }), authored);
  assert.equal(completed.some((item) => item.source.kind === "route_fallback"), false);
  const committed = eligibleAuthoredTexts(bundle({
    committed_delta: { fact_predicates: ["done"], scene_from: null, scene_to: null },
  }), authored);
  assert.deepEqual(committed.find((item) => item.source.kind === "route_fallback"), {
    text: authored.routeFallbacks[0].text,
    source: { kind: "route_fallback", id: authored.routeFallbacks[0].event_id },
  });
});

test("eligibility includes only committed, turn-local authored sources", () => {
  const eligible = eligibleAuthoredTexts(bundle({
    selected_reveal: { knowledge_ids: ["k"], delivery_fact_ids: ["handoff"] },
    cue_stage: { fact_id: "cue", delivered: true },
    pre_state: { staged_handoff_fact_ids: ["other"] },
    committed_delta: { scene_from: "A", scene_to: "B", fact_predicates: ["done"] },
    transition_cause: "earned",
    story_complete: true,
  }), authored);
  assert.deepEqual(eligible.map((item) => item.source.kind), ["delivery", "cue", "handoff_fallback", "bridge", "entry", "route_fallback"]);
  for (const outcome of ["rejected", "game_break", "operational_failure"]) {
    assert.deepEqual(eligibleAuthoredTexts(bundle({ outcome }), authored), []);
  }
  assert.deepEqual(eligibleAuthoredTexts(bundle({ committed_delta: { fact_predicates: ["other"], scene_from: "A", scene_to: "B" } }), authored).map((x) => x.source.kind), ["bridge", "entry"]);
});

test("forced 1A handoff fallback is eligible from a committed fact predicate", () => {
  const real = loadAuthoredText();
  const forced = bundle({
    transition_cause: "forced",
    selected_reveal: { knowledge_ids: [], delivery_fact_ids: [] },
    pre_state: { staged_handoff_fact_ids: [] },
    committed_delta: { fact_predicates: ["continuity_initiative_known"], scene_from: null, scene_to: null },
  });
  const eligible = eligibleAuthoredTexts(forced, real);
  assert.deepEqual(eligible.filter((item) => item.source.kind === "handoff_fallback").map((item) => item.source.id), ["continuity_initiative_known"]);
  assert.match(eligible.find((item) => item.source.id === "continuity_initiative_known").text, /Continuity Initiative/);
  assert.deepEqual(eligibleAuthoredTexts({ ...forced, committed_delta: { fact_predicates: [] } }, real), []);
  assert.deepEqual(eligibleAuthoredTexts({ ...forced, outcome: "rejected" }, real), []);
});

test("eligibility de-duplicates authored text and keeps its first source", () => {
  const duplicate = "The same authored sentence.";
  const result = eligibleAuthoredTexts(bundle({
    selected_reveal: { knowledge_ids: ["knowledge"], delivery_fact_ids: ["handoff"] },
    committed_delta: { fact_predicates: ["handoff", "knowledge"], scene_from: null, scene_to: null },
  }), {
    knowledgeDeliveryTexts: new Map([["knowledge", duplicate]]),
    handoffFallbackTexts: new Map([["handoff", duplicate]]),
    cueTexts: new Map(),
    bridgeTextsByScenePair: new Map(),
    entryTexts: new Map(),
    routeFallbackTexts: new Map(),
    routeFallbacks: [],
  });
  assert.deepEqual(result, [{ text: duplicate, source: { kind: "delivery", id: "knowledge" } }]);
});

test("attributes normalized quotes and whitespace, preferring the longer overlap", () => {
  const narration = "Before. A  “secret delivery.” After.";
  const spans = attributeNarration(narration, [
    { text: "secret delivery.", source: { kind: "cue", id: "short" } },
    { text: 'A “secret delivery.”', source: { kind: "delivery", id: "long" } },
  ]);
  assert.equal(spans.find((span) => span.origin === "authored").source.id, "long");
  assert.equal(spans.map((span) => span.text).join(""), narration);
});

test("does not excuse narrator rewrites and preserves exact reconstruction", () => {
  const narration = "The secret delivery was changed.";
  const spans = attributeNarration(narration, [{ text: "The secret delivery.", source: { kind: "delivery", id: "k" } }]);
  assert.ok(spans.every((span) => span.origin === "narrator"));
  assert.equal(spans.map((span) => span.text).join(""), narration);
});

test("knowledge becomes available only after its committed turn", () => {
  assert.deepEqual(knowledgeAvailableByTurn([
    { turn: 1, bundle: bundle({ selected_reveal: { knowledge_ids: ["later"] } }) },
    { turn: 2, bundle: bundle({ outcome: "rejected", selected_reveal: { knowledge_ids: ["never"] } }) },
    { turn: 3, bundle: bundle({ selected_reveal: { knowledge_ids: ["now", "later"] } }) },
  ]), [
    { turn: 1, available: ["later"] },
    { turn: 2, available: ["later"] },
    { turn: 3, available: ["later", "now"] },
  ]);
});
