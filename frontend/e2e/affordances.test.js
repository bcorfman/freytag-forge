import assert from "node:assert/strict";
import test from "node:test";

import {
  exploreInput,
  firstStepAffordances,
  formatMarkdown,
  laterAffordances,
  loadAffordanceMap,
  measureScene,
  mentions,
} from "./affordances.js";

const scene = {
  scene_id: "S1",
  location: { name: "The Workshop" },
  gates: [
    { transition_id: "go", fact_id: "found", affordances: [
      { entity_id: "drawer", name: "KMS drawer", aliases: ["evidence drawer"], kind: "item", visible_at_entry: true },
      { entity_id: "bench", name: "Workbench", aliases: ["work bench"], kind: "item", visible_at_entry: true },
    ] },
    { transition_id: "go", fact_id: "other", affordances: [
      { entity_id: "drawer", name: "KMS drawer", aliases: ["evidence drawer"], kind: "item", visible_at_entry: true },
      { entity_id: "card", name: "Memory card", aliases: [], kind: "item", revealed_by: "drawer", visible_at_entry: false },
    ] },
  ],
};

test("mentions matches names and aliases, but only whole words", () => {
  assert.equal(mentions("Michelle's workstation has a drawer.", ["workstation"]), true);
  assert.equal(mentions("The WORK BENCH is dusty.", ["work bench"]), true);
  assert.equal(mentions("A benched player waits.", ["bench"]), false);
  assert.equal(mentions("The drawer is here.", ["DRAWER"]), true);
  assert.equal(mentions("The ‘workshop’ is quiet — for now.", ["workshop"]), true);
});

test("first and later affordances deduplicate by entity", () => {
  assert.deepEqual(firstStepAffordances({ scenes: [scene] }, "S1").map((item) => item.entity_id), ["drawer", "bench"]);
  assert.deepEqual(firstStepAffordances({ scenes: [scene] }, "missing"), []);
  assert.deepEqual(laterAffordances({ scenes: [scene] }, "S1").map((item) => item.entity_id), ["card"]);
});

test("measureScene records opening, turn, late, and missing matches", () => {
  const measured = measureScene({
    sceneEntry: scene,
    shownLog: [
      { turn: 0, text: "The workbench waits beside the KMS drawer." },
      { turn: 1, text: "You search the room." },
      { turn: 3, text: "The memory card is under the bench." },
    ],
  });
  assert.equal(measured.first_step[0].first_shown_turn, 0);
  assert.equal(measured.first_step[0].deadline_met, true);
  assert.equal(measured.first_step[1].first_shown_turn, 0);
  assert.equal(measured.later[0].first_shown_turn, 3);
  assert.equal(measured.later[0].snippet.includes("memory card"), true);
  assert.equal(measured.summary.never_shown, 0);
  const missing = measureScene({ sceneEntry: scene, shownLog: [{ turn: 0, text: "Nothing is named." }] });
  assert.equal(missing.first_step[0].first_shown_turn, null);
  assert.equal(missing.first_step[0].deadline_met, false);
  assert.equal(missing.summary.never_shown, 3);
});

test("exploreInput is imperative and strips a leading article", () => {
  assert.equal(exploreInput(scene), "Search Workshop.");
  assert.match(exploreInput(scene), /^Search /);
  assert.match(exploreInput(scene), /\.$/);
  assert.doesNotMatch(exploreInput(scene), /\bI\b/);
  assert.throws(() => exploreInput({ scene_id: "S1" }), /no location/);
});

test("exploreInput uses natural articles for location names", () => {
  assert.equal(exploreInput({ location: { name: "Michelle's house" } }), "Search Michelle's house.");
  assert.equal(exploreInput({ location: { name: "the kitchen" } }), "Search the kitchen.");
  assert.equal(exploreInput({ location: { name: "freight terminal" } }), "Search the freight terminal.");
  assert.equal(exploreInput({ location: { name: "Michelle’s house" } }), "Search Michelle’s house.");
});

test("formatMarkdown renders a compact scene table", () => {
  const markdown = formatMarkdown({ scenes: [{ scene_id: "S1", first_step: [{ name: "Drawer", first_shown_turn: null, snippet: null }], later: [] }] });
  assert.match(markdown, /\| Scene \| Affordance/);
  assert.match(markdown, /\| S1 \| Drawer \| NEVER \|/);
});

test("loadAffordanceMap parses injected command output and explains failures", () => {
  const calls = [];
  const map = loadAffordanceMap("data/stories/example", {
    cwd: "/repo",
    exec: (...args) => {
      calls.push(args);
      return Buffer.from('{"story_id":"example","scenes":[]}');
    },
  });
  assert.equal(map.story_id, "example");
  assert.equal(calls[0][0], "uv");
  assert.equal(calls[0][1].at(-1), "data/stories/example");
  assert.equal(calls[0][2].cwd, "/repo");
  assert.equal(calls[0][2].env.TMPDIR, "/tmp");
  assert.throws(() => loadAffordanceMap("bad", { exec: () => { throw new Error("python failed"); } }), /Could not load affordance map.*python failed/);
});
