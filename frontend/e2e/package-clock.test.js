import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { loadPackagePacing } from "./package-clock.js";

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
  assert.deepEqual(projection.scenePoint("1B", "min"), {
    kind: "scene_point",
    scene_id: "1B",
    point: "min",
    target_turn: 2,
  });
  assert.deepEqual(projection.scenePoint("1B", "nudge"), {
    kind: "scene_point",
    scene_id: "1B",
    point: "nudge",
    target_turn: 3,
  });
  assert.deepEqual(projection.scenePoint("1B", "handoff"), {
    kind: "scene_point",
    scene_id: "1B",
    point: "handoff",
    target_turn: 4,
  });
  assert.deepEqual(projection.eventPoint("purge_2c"), {
    kind: "pacing_event",
    scene_id: "2C",
    event_id: "purge_2c",
    target_turn: 2,
  });
  assert.equal(Object.hasOwn(projection.scenePoint("1B", "min"), "target_seconds"), false);
  assert.equal(Object.hasOwn(projection.eventPoint("purge_2c"), "target_seconds"), false);
  assert.equal(Object.isFrozen(projection), true);
  assert.equal(Object.isFrozen(projection.sceneOrder), true);
  assert.equal(Object.isFrozen(projection.scenePoint("1B", "handoff")), true);
  assert.equal(Object.isFrozen(projection.eventPoint("purge_2c")), true);
  assert.deepEqual(Object.keys(projection), [
    "storyId",
    "sceneOrder",
    "eventOrder",
    "scenePoint",
    "eventPoint",
  ]);
  assert.equal(Object.isFrozen(projection.eventOrder), true);
  assert.deepEqual([...projection.eventOrder], ["pressure_1a", "purge_2c", "override_deadline_3a", "destruction_3b"]);
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
