import assert from "node:assert/strict";
import test from "node:test";

import { createPackageClockController } from "./package-clock-controller.js";

function state(turnIndex, turnsSinceSceneEntry, overrides = {}) {
  return {
    scene_id: "1A",
    turn_index: turnIndex,
    turns_since_scene_entry: turnsSinceSceneEntry,
    pending_game_break: false,
    fired_pacing_event_ids: [],
    ...overrides,
  };
}

test("reports the further turns needed for an armed milestone", () => {
  const controller = createPackageClockController();
  controller.observeState(state(1, 1));
  controller.arm({ kind: "scene_point", scene_id: "1A", point: "nudge", target_turn: 3 });

  assert.equal(controller.turnsUntilMilestone(), 2);
});

test("allows zero further turns when the observed scene-relative turn equals the target", () => {
  const controller = createPackageClockController();
  controller.observeState(state(3, 3));
  controller.arm({ kind: "scene_point", scene_id: "1A", point: "handoff", target_turn: 3 });

  assert.equal(controller.turnsUntilMilestone(), 0);
});

test("rejects a milestone for a different scene", () => {
  const controller = createPackageClockController();
  controller.observeState(state(2, 2));
  controller.arm({ kind: "pacing_event", scene_id: "2C", event_id: "purge_2c", target_turn: 2 });

  assert.throws(
    () => controller.turnsUntilMilestone(),
    (error) =>
      error instanceof Error &&
      error.message.includes("1A") &&
      error.message.includes("2C") &&
      error.message.includes("purge_2c"),
  );
});

test("requires an observed session or turn state before computing remaining turns", () => {
  const controller = createPackageClockController();
  controller.arm({ kind: "scene_point", scene_id: "1A", point: "min", target_turn: 2 });

  assert.throws(
    () => controller.turnsUntilMilestone(),
    /session|state|observed/i,
  );
});

test("rejects a target earlier than the observed scene-relative turn", () => {
  const controller = createPackageClockController();
  controller.observeState(state(3, 3));
  controller.arm({ kind: "pacing_event", scene_id: "1A", event_id: "pressure_1a", target_turn: 2 });

  assert.throws(
    () => controller.turnsUntilMilestone(),
    (error) => error instanceof Error && error.message.includes("3") && error.message.includes("2"),
  );
});

test("rejects arming a second milestone", () => {
  const controller = createPackageClockController();
  controller.arm({ kind: "scene_point", scene_id: "1A", point: "min", target_turn: 2 });

  assert.throws(
    () => controller.arm({ kind: "scene_point", scene_id: "1A", point: "nudge", target_turn: 3 }),
    /arm/i,
  );
});

test("rejects malformed milestones and obsolete absolute targets", () => {
  const controller = createPackageClockController();
  for (const milestone of [
    null,
    { kind: "scene_point", scene_id: "1A", point: "target", target_turn: 2 },
    { kind: "scene_point", scene_id: "1A", point: "min", target_turn: "2" },
    { kind: "scene_point", scene_id: "1A", point: "min", target_seconds: 120 },
    { kind: "pacing_event", scene_id: "1A", target_turn: 2 },
  ]) {
    assert.throws(() => controller.arm(milestone), /malformed|target_turn/i);
  }
});

test("records a turn that reaches the requested target exactly", () => {
  const controller = createPackageClockController();
  const milestone = { kind: "scene_point", scene_id: "1A", point: "nudge", target_turn: 2 };
  controller.observeState(state(1, 1));
  controller.arm(milestone);
  assert.equal(controller.turnsUntilMilestone(), 1);

  const outcome = controller.observeTurnResponse({ state: state(2, 2) });

  assert.deepEqual(outcome, {
    reached: true,
    scene_id: "1A",
    turn_index: 2,
    turns_since_scene_entry: 2,
    requested_milestone: milestone,
  });
  assert.deepEqual(controller.history(), [
    {
      requested_milestone: milestone,
      prior_scene_id: "1A",
      prior_turn_index: 1,
      prior_turns_since_scene_entry: 1,
      scene_id: "1A",
      turn_index: 2,
      turns_since_scene_entry: 2,
      fired_pacing_event_ids: [],
      reached: true,
    },
  ]);
  assert.equal(controller.armed(), null);
});

test("reports a valid turn landing short of its milestone", () => {
  const controller = createPackageClockController();
  controller.observeState(state(1, 1));
  controller.arm({ kind: "scene_point", scene_id: "1A", point: "handoff", target_turn: 3 });
  assert.equal(controller.turnsUntilMilestone(), 2);

  const outcome = controller.observeTurnResponse({ state: state(2, 2) });

  assert.equal(outcome.reached, false);
  assert.equal(outcome.turns_since_scene_entry, 2);
  assert.equal(controller.history()[0].turns_since_scene_entry, 2);
});

test("does not mark a pending game break as reaching a milestone", () => {
  const controller = createPackageClockController();
  const milestone = { kind: "pacing_event", scene_id: "1A", event_id: "pressure_1a", target_turn: 2 };
  controller.observeState(state(1, 1));
  controller.arm(milestone);
  assert.equal(controller.turnsUntilMilestone(), 1);

  const outcome = controller.observeTurnResponse({
    state: state(2, 2, { pending_game_break: true }),
  });

  assert.equal(outcome.reached, false);
  assert.equal(controller.history()[0].reached, false);
  assert.equal(controller.armed(), null);
});

test("updates the observed state for an unarmed turn without fabricating history", () => {
  const controller = createPackageClockController();

  const outcome = controller.observeTurnResponse({ state: state(1, 1) });

  assert.deepEqual(outcome, {
    reached: false,
    scene_id: "1A",
    turn_index: 1,
    turns_since_scene_entry: 1,
    requested_milestone: null,
  });
  assert.deepEqual(controller.history(), []);

  controller.arm({ kind: "scene_point", scene_id: "1A", point: "handoff", target_turn: 3 });
  assert.equal(controller.turnsUntilMilestone(), 2);
});

test("accepts a scene transition and records that the old milestone was not reached", () => {
  const controller = createPackageClockController();
  controller.observeState(state(2, 2));
  controller.arm({ kind: "scene_point", scene_id: "1A", point: "handoff", target_turn: 3 });

  const outcome = controller.observeTurnResponse({
    state: state(3, 0, { scene_id: "1B" }),
  });

  assert.equal(outcome.reached, false);
  assert.equal(controller.history()[0].scene_id, "1B");
  assert.equal(controller.history()[0].turns_since_scene_entry, 0);
});

test("rejects malformed reported turn state", () => {
  const controller = createPackageClockController();

  for (const reportedState of [
    { scene_id: "1A", turn_index: 1 },
    { scene_id: "1A", turn_index: 1, turns_since_scene_entry: 1.5 },
    { scene_id: "1A", turn_index: 1, turns_since_scene_entry: 2 },
  ]) {
    assert.throws(
      () => controller.observeTurnResponse({ state: reportedState }),
      /turn state|missing|malformed/i,
    );
  }
});
