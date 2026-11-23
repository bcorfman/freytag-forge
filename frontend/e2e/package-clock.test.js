import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { canonTurnBudget, loadPackagePacing, nextPendingEvent } from "./package-clock.js";

const repoRoot = join(import.meta.dirname, "../..");

function withFixture(source, callback) {
  const directory = mkdtempSync(join(tmpdir(), "freytag-package-clock-"));
  const pacingPath = join(directory, "pacing.yaml");
  writeFileSync(pacingPath, source);
  try {
    return callback(pacingPath);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

function withSourceFixture(sceneSources, callback, storyScenes = Object.keys(sceneSources)) {
  const directory = mkdtempSync(join(tmpdir(), "freytag-source-pacing-"));
  const sourceDirectory = join(directory, "data", "stories", "fixture-story", "source");
  const scenesDirectory = join(sourceDirectory, "scenes");
  mkdirSync(scenesDirectory, { recursive: true });
  writeFileSync(join(sourceDirectory, "story.yaml"), `scenes:\n${storyScenes.map((id) => `- ${id}`).join("\n")}\n`);
  for (const [sceneId, source] of Object.entries(sceneSources)) {
    writeFileSync(join(scenesDirectory, `${sceneId}.yaml`), source);
  }
  try {
    return callback(directory);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

function sourceScene(sceneId, turns = "min: 0\n  nudge: 1\n  handoff: 2", beats = "") {
  return `scene: ${sceneId}\nturns:\n  ${turns}\nbeats:\n${beats}`;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function assertFixtureError(source, identifier, expectedText = identifier) {
  withFixture(source, (pacingPath) => {
    assert.throws(
      () => loadPackagePacing({ storyId: "fixture_story", pacingPath }),
      (error) => {
        assert.match(error.message, /fixture_story/);
        assert.match(error.message, /pacing\.yaml/);
        assert.match(error.message, new RegExp(escapeRegExp(expectedText)));
        assert.match(error.message, new RegExp(escapeRegExp(identifier)));
        return true;
      },
    );
  });
}

const validScene = `
budget_seconds: 60
scenes:
  - scene_id: A
    min_turns: 0
    nudge_after_turns: 1
    handoff_after_turns: 2
events:
  - id: event_a
    scene_id: A
    at_turn: 2
`;

test("loads the real package and resolves turn milestones", () => {
  const projection = loadPackagePacing({ storyId: "continuity_initiative", repoRoot });

  assert.deepEqual(projection.sceneOrder, ["1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"]);
  assert.equal(projection.scenePoint("1A", "handoff").target_turn, 15);
  assert.equal(projection.eventOrder[0], "kristin_steadies_1a");
  assert.deepEqual(projection.scenePoint("1B", "min"), {
    kind: "scene_point",
    scene_id: "1B",
    point: "min",
    target_turn: 8,
  });
  assert.deepEqual(projection.scenePoint("1B", "nudge"), {
    kind: "scene_point",
    scene_id: "1B",
    point: "nudge",
    target_turn: 10,
  });
  assert.deepEqual(projection.scenePoint("1B", "handoff"), {
    kind: "scene_point",
    scene_id: "1B",
    point: "handoff",
    target_turn: 13,
  });
  assert.deepEqual(projection.eventPoint("purge_window_2c"), {
    kind: "pacing_event",
    scene_id: "2C",
    event_id: "purge_window_2c",
    target_turn: 5,
  });
  assert.equal(Object.hasOwn(projection.scenePoint("1B", "min"), "target_seconds"), false);
  assert.equal(Object.hasOwn(projection.eventPoint("purge_window_2c"), "target_seconds"), false);
  assert.equal(Object.isFrozen(projection), true);
  assert.equal(Object.isFrozen(projection.sceneOrder), true);
  assert.equal(Object.isFrozen(projection.scenePoint("1B", "handoff")), true);
  assert.equal(Object.isFrozen(projection.eventPoint("purge_window_2c")), true);
  assert.deepEqual(Object.keys(projection), [
    "storyId",
    "sceneOrder",
    "eventOrder",
    "scenePoint",
    "eventPoint",
    "isConditional",
  ]);
  assert.equal(Object.isFrozen(projection.eventOrder), true);
  assert.deepEqual(
    [...projection.eventOrder],
    [
      "kristin_steadies_1a",
      "patrol_arrives_1a",
      "patrol_enters_1a",
      "officer_presses_1a",
      "reyes_rams_drawer_1a",
      "patrol_leaves_1a",
      "patrol_returns_1a",
      "home_search_narrows_1a",
      "drawer_gap_returns_1a",
      "pursuit_1b",
      "park_lockdown_1b",
      "transfer_window_1c",
      "transfer_nudge_1c",
      "transfer_withdrawal_1c",
      "supervisor_impatience_2a",
      "inspection_window_2a",
      "inspection_nudge_2a",
      "inspection_recovery_2a",
      "audit_window_2b",
      "audit_nudge_2b",
      "audit_recovery_2b",
      "purge_window_2c",
      "purge_nudge_2c",
      "purge_recovery_2c",
      "override_deadline_3a",
      "detention_lockdown_3a",
      "destruction_3b",
      "relay_power_3b",
      "collapse_3c",
      "evacuation_window_3c",
      "evacuation_recovery_3c",
      "evacuation_nudge_3c",
      "routes_collapse_3c",
    ],
  );
});

test("loads pacing from the compiled source tree", () => {
  withSourceFixture({
    A: sourceScene("A", "min: 1\n  nudge: 2\n  handoff: 3", "- id: first\n  at_turn: 1\n  when:\n    ready: true\n- id: second\n  at_turn: 3\n"),
    B: sourceScene("B"),
  }, (directory) => {
    const pacing = loadPackagePacing({ storyId: "fixture_story", repoRoot: directory });
    assert.deepEqual(pacing.sceneOrder, ["A", "B"]);
    assert.equal(pacing.scenePoint("A", "min").target_turn, 1);
    assert.equal(pacing.scenePoint("A", "handoff").target_turn, 3);
    assert.deepEqual(pacing.eventOrder, ["first", "second"]);
    assert.equal(pacing.eventPoint("first").target_turn, 1);
    assert.equal(pacing.isConditional("first"), true);
    assert.equal(pacing.isConditional("second"), false);
  });
});

test("validates source pacing with the legacy pacing errors", () => {
  const assertSourceError = (scenes, expected) => withSourceFixture(scenes, (directory) => {
    assert.throws(() => loadPackagePacing({ storyId: "fixture_story", repoRoot: directory }), new RegExp(expected));
  });
  assertSourceError({ A: sourceScene("A", "min: 2\n  nudge: 1\n  handoff: 3") }, "turn points must be ordered");
  assertSourceError({ A: sourceScene("A", "min: -1\n  nudge: 1\n  handoff: 3") }, "min_turns must be a non-negative integer");
  assertSourceError({ A: "scene: A\nbeats: []\n" }, "missing turns block");
  assertSourceError({ A: sourceScene("A", "min: 0\n  nudge: 1\n  handoff: 2", "- id: duplicate\n  at_turn: 0\n- id: duplicate\n  at_turn: 1\n") }, "duplicate event id");
  assertSourceError({ A: sourceScene("A", "min: 0\n  nudge: 1\n  handoff: 2", "- id: late\n  at_turn: 3\n") }, "at_turn must fall within");
  assertSourceError({ A: "scene: B\nturns:\n  min: 0\n  nudge: 1\n  handoff: 2\n" }, "undeclared scene");
  withSourceFixture({ A: sourceScene("A") }, (directory) => {
    assert.throws(() => loadPackagePacing({ storyId: "fixture_story", repoRoot: directory }), /duplicate scene id/);
  }, ["A", "A"]);
  withSourceFixture({ A: sourceScene("A") }, (directory) => {
    assert.throws(() => loadPackagePacing({ storyId: "fixture_story", repoRoot: directory, pacingPath: join(directory, "missing.yaml") }), /pacing\.yaml could not be read/);
  }, ["A", "A"]);
});

test("prefers legacy pacing and an explicit pacingPath over source pacing", () => {
  withSourceFixture({ A: sourceScene("A") }, (directory) => {
    const legacyPath = join(directory, "data", "stories", "fixture-story", "pacing.yaml");
    writeFileSync(legacyPath, validScene.replaceAll("scene_id: A", "scene_id: LEGACY"));
    assert.equal(loadPackagePacing({ storyId: "fixture_story", repoRoot: directory }).sceneOrder[0], "LEGACY");
    const explicitPath = join(directory, "explicit.yaml");
    writeFileSync(explicitPath, validScene.replaceAll("scene_id: A", "scene_id: EXPLICIT"));
    assert.equal(loadPackagePacing({ storyId: "fixture_story", repoRoot: directory, pacingPath: explicitPath }).sceneOrder[0], "EXPLICIT");
  });
});

test("reports conditional events in the real package pacing", () => {
  const projection = loadPackagePacing({ storyId: "continuity_initiative", repoRoot });

  assert.equal(projection.isConditional("officer_presses_1a"), true);
  assert.equal(projection.isConditional("transfer_nudge_1c"), true);
  assert.equal(projection.isConditional("patrol_arrives_1a"), false);
  assert.equal(projection.isConditional("purge_window_2c"), false);
});

test("selects pending real-package events by conditionality and turn", () => {
  const pacing = loadPackagePacing({ storyId: "continuity_initiative", repoRoot });

  const atTurnFive = nextPendingEvent(pacing, "1A", 5, new Set());
  assert.equal(atTurnFive?.event_id, "patrol_arrives_1a");
  assert.notEqual(atTurnFive?.event_id, "officer_presses_1a");

  const atTurnFour = nextPendingEvent(pacing, "1A", 4, new Set());
  assert.equal(atTurnFour?.event_id, "patrol_arrives_1a");
  assert.equal(atTurnFour?.target_turn, 6);
  assert.equal(pacing.isConditional(atTurnFour.event_id), false);

  const afterPatrolArrives = nextPendingEvent(
    pacing,
    "1A",
    4,
    new Set(["patrol_arrives_1a"]),
  );
  assert.equal(afterPatrolArrives?.event_id, "patrol_enters_1a");
  assert.equal(afterPatrolArrives?.target_turn > 4, true);
  assert.equal(pacing.isConditional(afterPatrolArrives.event_id), true);
});

test("reports whether fixture pacing events are conditional", () => {
  withFixture(
    `${validScene}  - id: event_conditional
    scene_id: A
    at_turn: 1
    when:
      - fact: true
  - id: event_unconditional
    scene_id: A
    at_turn: 2
`,
    (pacingPath) => {
      const projection = loadPackagePacing({ storyId: "fixture_story", pacingPath });

      assert.equal(projection.isConditional("event_conditional"), true);
      assert.equal(projection.isConditional("event_unconditional"), false);
    },
  );
});

test("calculates the canon turn budget from scene handoffs", () => {
  const pacing = {
    sceneOrder: ["A", "B"],
    scenePoint(sceneId, point) {
      return point === "handoff" ? { scene_id: sceneId, target_turn: sceneId === "A" ? 2 : 4 } : undefined;
    },
  };

  assert.equal(canonTurnBudget(pacing), 13);
  assert.equal(canonTurnBudget(pacing, 2), 10);
  assert.throws(
    () => canonTurnBudget({ sceneOrder: ["A"], scenePoint: () => undefined }),
    /Scene "A" has no handoff point/,
  );
});

test("budgets every scene in the real package pacing", () => {
  const pacing = loadPackagePacing({ storyId: "continuity_initiative", repoRoot });
  const handoffTotal = pacing.sceneOrder.reduce(
    (total, sceneId) => total + pacing.scenePoint(sceneId, "handoff").target_turn,
    0,
  );

  assert.ok(canonTurnBudget(pacing) >= handoffTotal);
  assert.ok(canonTurnBudget(pacing) > 45);
});

test("reports unknown story, scene, event, and point identifiers", () => {
  assert.throws(
    () => loadPackagePacing({ storyId: "no_such_story", repoRoot }),
    /no_such_story/,
  );

  const projection = loadPackagePacing({ storyId: "continuity_initiative", repoRoot });
  assert.throws(() => projection.scenePoint("9Z", "handoff"), /9Z/);
  assert.throws(() => projection.scenePoint("1A", "target"), /target/);
  assert.throws(() => projection.eventPoint("no_such_event"), /no_such_event/);
  assert.throws(() => projection.isConditional("no_such_event"), /no_such_event/);
});

test("reports a missing pacing file with story and path context", () => {
  withFixture(validScene, (pacingPath) => {
    rmSync(pacingPath);
    assert.throws(
      () => loadPackagePacing({ storyId: "missing_fixture", pacingPath }),
      (error) => /missing_fixture/.test(error.message) && /pacing\.yaml/.test(error.message) && /identifier/.test(error.message),
    );
  });
});

test("reports malformed YAML", () => {
  assertFixtureError("scenes: [\n", "pacing.yaml", "malformed YAML");
});

test("reports duplicate scene and event identifiers", () => {
  assertFixtureError(
    `scenes:
  - scene_id: A
    min_turns: 0
    nudge_after_turns: 1
    handoff_after_turns: 2
  - scene_id: A
    min_turns: 0
    nudge_after_turns: 1
    handoff_after_turns: 2
`,
    "A",
    "duplicate scene id",
  );
  assertFixtureError(
    `${validScene}  - id: event_a
    scene_id: A
    at_turn: 1
`,
    "event_a",
    "duplicate event id",
  );
});

test("reports missing scene and event identifier fields", () => {
  assertFixtureError(
    `scenes:
  - min_turns: 0
    nudge_after_turns: 1
    handoff_after_turns: 2
`,
    "scene_id",
    "missing scene scene_id field",
  );
  assertFixtureError(
    `scenes:
  - scene_id: A
    min_turns: 0
    nudge_after_turns: 1
    handoff_after_turns: 2
events:
  - scene_id: A
    at_turn: 1
`,
    "event id",
    "missing event id field",
  );
});

test("reports turn counts that are not non-negative integers", () => {
  assertFixtureError(
    `scenes:
  - scene_id: A
    min_turns: 0.5
    nudge_after_turns: 1
    handoff_after_turns: 2
`,
    "A",
    "min_turns must be a non-negative integer",
  );
  assertFixtureError(
    `scenes:
  - scene_id: A
    min_turns: 0
    nudge_after_turns: 2.0
    handoff_after_turns: 2
`,
    "A",
    "nudge_after_turns must be a non-negative integer",
  );
  assertFixtureError(
    `scenes:
  - scene_id: A
    min_turns: 0
    nudge_after_turns: 1
    handoff_after_turns: -1
`,
    "A",
    "handoff_after_turns must be a non-negative integer",
  );
  assertFixtureError(
    `scenes:
  - scene_id: A
    min_turns: 0
    nudge_after_turns: 1
    handoff_after_turns: 2
events:
  - id: event_a
    scene_id: A
    at_turn: 1.5
`,
    "event_a",
    "at_turn must be a non-negative integer",
  );
});

test("rejects the old absolute-seconds schema", () => {
  assertFixtureError(
    `scenes:
  - scene_id: A
    earliest_seconds: 0
    target_seconds: 1
    latest_seconds: 2
`,
    "A",
    "min_turns must be a non-negative integer",
  );
});

test("reports scene turn points outside their declared order", () => {
  assertFixtureError(
    `scenes:
  - scene_id: A
    min_turns: 2
    nudge_after_turns: 1
    handoff_after_turns: 3
`,
    "A",
    "turn points must be ordered",
  );
  assertFixtureError(
    `scenes:
  - scene_id: A
    min_turns: 0
    nudge_after_turns: 3
    handoff_after_turns: 2
`,
    "A",
    "turn points must be ordered",
  );
});

test("reports events outside their scene handoff window", () => {
  assertFixtureError(
    `scenes:
  - scene_id: A
    min_turns: 0
    nudge_after_turns: 1
    handoff_after_turns: 2
events:
  - id: event_a
    scene_id: A
    at_turn: 3
`,
    "event_a",
    "at_turn must fall within",
  );
});

test("reports events that name undeclared scenes", () => {
  assertFixtureError(
    `scenes:
  - scene_id: A
    min_turns: 0
    nudge_after_turns: 1
    handoff_after_turns: 2
events:
  - id: event_missing_scene
    scene_id: B
    at_turn: 1
`,
    "event_missing_scene",
    "undeclared scene",
  );
});
