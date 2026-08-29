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
scenes:
  - scene_id: A
    earliest_seconds: 0
    target_seconds: 10
    latest_seconds: 20
events:
  - id: event_a
    scene_id: A
    at_seconds: 15
`;

test("loads the real package and resolves irregular scene and event milestones", () => {
  const projection = loadPackagePacing({ storyId: "continuity_initiative", repoRoot });

  assert.deepEqual(projection.sceneOrder, ["1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"]);
  assert.deepEqual(projection.scenePoint("1B", "earliest"), {
    kind: "scene_point",
    scene_id: "1B",
    point: "earliest",
    target_seconds: 120,
  });
  assert.deepEqual(projection.scenePoint("1B", "target"), {
    kind: "scene_point",
    scene_id: "1B",
    point: "target",
    target_seconds: 195,
  });
  assert.deepEqual(projection.scenePoint("1B", "latest"), {
    kind: "scene_point",
    scene_id: "1B",
    point: "latest",
    target_seconds: 270,
  });
  assert.deepEqual(projection.eventPoint("purge_2c"), {
    kind: "pacing_event",
    scene_id: "2C",
    event_id: "purge_2c",
    target_seconds: 690,
  });
  assert.equal(Object.isFrozen(projection), true);
  assert.equal(Object.isFrozen(projection.sceneOrder), true);
  assert.equal(Object.isFrozen(projection.scenePoint("1B", "target")), true);
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
  assert.throws(() => projection.scenePoint("9Z", "target"), /9Z/);
  assert.throws(() => projection.scenePoint("1A", "midpoint"), /midpoint/);
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
    earliest_seconds: 0
    target_seconds: 1
    latest_seconds: 2
  - scene_id: A
    earliest_seconds: 2
    target_seconds: 3
    latest_seconds: 4
`,
    "A",
    "duplicate scene id",
  );
  assertFixtureError(
    `${validScene}  - id: event_a
    scene_id: A
    at_seconds: 16
`,
    "event_a",
    "duplicate event id",
  );
});

test("reports missing scene and event identifier fields", () => {
  assertFixtureError(
    `scenes:
  - earliest_seconds: 0
    target_seconds: 1
    latest_seconds: 2
`,
    "scene_id",
    "missing scene scene_id field",
  );
  assertFixtureError(
    `scenes:
  - scene_id: A
    earliest_seconds: 0
    target_seconds: 1
    latest_seconds: 2
events:
  - scene_id: A
    at_seconds: 1
`,
    "event id",
    "missing event id field",
  );
});

test("reports timestamps that are not non-negative integers", () => {
  assertFixtureError(
    `scenes:
  - scene_id: A
    earliest_seconds: 0.5
    target_seconds: 1
    latest_seconds: 2
`,
    "A",
    "earliest_seconds must be a non-negative integer",
  );
  assertFixtureError(
    `scenes:
  - scene_id: A
    earliest_seconds: 0
    target_seconds: 1.0
    latest_seconds: 2
`,
    "A",
    "target_seconds must be a non-negative integer",
  );
  assertFixtureError(
    `scenes:
  - scene_id: A
    earliest_seconds: 0
    target_seconds: -1
    latest_seconds: 2
`,
    "A",
    "target_seconds must be a non-negative integer",
  );
  assertFixtureError(
    `scenes:
  - scene_id: A
    earliest_seconds: 0
    target_seconds: 1
    latest_seconds: 2
events:
  - id: event_a
    scene_id: A
    at_seconds: 1.5
`,
    "event_a",
    "at_seconds must be a non-negative integer",
  );
});

test("reports scene and event timestamps outside their declared windows", () => {
  assertFixtureError(
    `scenes:
  - scene_id: A
    earliest_seconds: 10
    target_seconds: 9
    latest_seconds: 20
`,
    "A",
    "target_seconds must fall within",
  );
  assertFixtureError(
    `scenes:
  - scene_id: A
    earliest_seconds: 10
    target_seconds: 15
    latest_seconds: 20
events:
  - id: event_a
    scene_id: A
    at_seconds: 21
`,
    "event_a",
    "at_seconds must fall within",
  );
});

test("reports events that name undeclared scenes", () => {
  assertFixtureError(
    `scenes:
  - scene_id: A
    earliest_seconds: 0
    target_seconds: 10
    latest_seconds: 20
events:
  - id: event_missing_scene
    scene_id: B
    at_seconds: 10
`,
    "event_missing_scene",
    "undeclared scene",
  );
});
