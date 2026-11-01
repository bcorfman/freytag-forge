import test from "node:test";
import assert from "node:assert/strict";

import { loadAuthoredText } from "./authored-spans.js";
import { partitionTransitionSegments } from "./scene-partition.js";

const authored = loadAuthoredText();
// The saved staging transition 1C -> 2A: four action segments, the authored bridge,
// the base entry, then the satisfied entry variant. Authored strings are read from the
// package so this fixture cannot drift from the story.
const fixture = {
  source_scene: "1C",
  target_scene: "2A",
  payload_segments: [
    { kind: "narration", text: "Kristin looks down at the processing line." },
    { kind: "narration", text: "She spots a woman who resembles Michelle." },
    { kind: "narration", text: "Her grip on the railing tightens." },
    { kind: "narration", text: "Kristin copies the visible prisoner numbers." },
    { kind: "narration", text: authored.bridgeTextsByScenePair.get("1C>2A") },
    { kind: "narration", text: authored.entryTexts.get("2A") },
    { kind: "narration", text: authored.entryVariantTextsBySceneId.get("2A")[0] },
  ],
};

test("partitions the saved 1C to 2A transition at the bridge", () => {
  const result = partitionTransitionSegments(fixture.payload_segments, {
    sourceSceneId: fixture.source_scene,
    targetSceneId: fixture.target_scene,
    authored,
  });

  assert.equal(result.method, "bridge");
  assert.equal(result.departure.length, 5);
  assert.equal(result.departure.at(-1).text, authored.bridgeTextsByScenePair.get("1C>2A"));
  assert.equal(result.arrival.length, 2);
  assert.equal(result.arrival[0].text.trim(), authored.entryTexts.get("2A").trim());
  assert.equal(result.arrival.at(-1).text, authored.entryVariantTextsBySceneId.get("2A")[0]);
});

test("partitions a transition with one entry segment", () => {
  const bridge = authored.bridgeTextsByScenePair.get("3B>3C");
  const entry = authored.entryTexts.get("3C");
  const result = partitionTransitionSegments([{ text: "Action." }, { text: bridge }, { text: entry }], {
    sourceSceneId: "3B",
    targetSceneId: "3C",
    authored,
  });

  assert.equal(result.method, "bridge");
  assert.deepEqual(result.departure.map((segment) => segment.text), ["Action.", bridge]);
  assert.deepEqual(result.arrival.map((segment) => segment.text), [entry]);
});

test("keeps a turn with no transition whole", () => {
  const segments = [{ text: "First." }, { text: "Second." }];
  const result = partitionTransitionSegments(segments, {
    sourceSceneId: "2A",
    targetSceneId: "2A",
    authored,
  });

  assert.equal(result.method, "none");
  assert.deepEqual(result.departure, segments);
  assert.deepEqual(result.arrival, []);
});

test("uses the entry boundary when a verbatim event drops the bridge", () => {
  const segments = [
    ...fixture.payload_segments.slice(0, 4),
    fixture.payload_segments[5],
    fixture.payload_segments[6],
  ];
  const result = partitionTransitionSegments(segments, {
    sourceSceneId: fixture.source_scene,
    targetSceneId: fixture.target_scene,
    authored,
  });

  assert.equal(result.method, "entry");
  assert.equal(result.departure.length, 4);
  assert.equal(result.arrival.length, 2);
});

test("falls back to the last segment when no boundary is identifiable", () => {
  const segments = [{ text: "Action." }, { text: "Unrecognized ending." }];
  const result = partitionTransitionSegments(segments, {
    sourceSceneId: "A",
    targetSceneId: "B",
    authored,
  });

  assert.equal(result.method, "fallback");
  assert.deepEqual(result.departure, [segments[0]]);
  assert.deepEqual(result.arrival, [segments[1]]);
});

test("preserves order and does not mutate input", () => {
  const segments = fixture.payload_segments.map((segment) => ({ ...segment }));
  const before = structuredClone(segments);
  const result = partitionTransitionSegments(segments, {
    sourceSceneId: fixture.source_scene,
    targetSceneId: fixture.target_scene,
    authored,
  });

  assert.deepEqual(segments, before);
  assert.deepEqual([...result.departure, ...result.arrival], segments);
});
