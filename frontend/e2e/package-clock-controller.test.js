import assert from "node:assert/strict";
import test from "node:test";

import {
  assertExclusiveClockMode,
  createPackageClockController,
} from "./package-clock-controller.js";

function state(elapsed, overrides = {}) {
  return {
    scene_id: "1A",
    story_elapsed_seconds: elapsed,
    pending_game_break: false,
    fired_pacing_event_ids: [],
    ...overrides,
  };
}

test("computes a forward package-clock delta from the observed elapsed time", () => {
  const controller = createPackageClockController();
  controller.observeState(state(120));
  controller.arm({ kind: "scene_point", scene_id: "1B", point: "target", target_seconds: 195 });

  assert.equal(controller.deltaForRequest(), 75);
});

test("allows a zero delta when the observed time equals the target", () => {
  const controller = createPackageClockController();
  controller.observeState(state(195));
  controller.arm({ kind: "scene_point", scene_id: "1B", point: "target", target_seconds: 195 });

  assert.equal(controller.deltaForRequest(), 0);
});

test("rejects a target earlier than the observed elapsed time", () => {
  const controller = createPackageClockController();
  controller.observeState(state(195));
  controller.arm({ kind: "pacing_event", scene_id: "2C", event_id: "purge_2c", target_seconds: 150 });

  assert.throws(
    () => controller.deltaForRequest(),
    (error) =>
      error instanceof Error &&
      error.message.includes("195") &&
      error.message.includes("150") &&
      error.message.includes("2C") &&
      error.message.includes("purge_2c"),
  );
});

test("requires an observed session or turn state before computing a delta", () => {
  const controller = createPackageClockController();
  controller.arm({ kind: "scene_point", scene_id: "1B", point: "target", target_seconds: 195 });

  assert.throws(
    () => controller.deltaForRequest(),
    /elapsed|session|state|observed/i,
  );
});

test("rejects arming a second milestone", () => {
  const controller = createPackageClockController();
  controller.arm({ kind: "scene_point", scene_id: "1B", point: "target", target_seconds: 195 });

  assert.throws(
    () => controller.arm({ kind: "scene_point", scene_id: "1C", point: "target", target_seconds: 240 }),
    /arm/i,
  );
});

test("enforces the upper delta bound while allowing exactly 3600 seconds", () => {
  const tooLarge = createPackageClockController();
  tooLarge.observeState(state(0));
  tooLarge.arm({ kind: "scene_point", scene_id: "1B", point: "target", target_seconds: 3601 });
  assert.throws(() => tooLarge.deltaForRequest(), /3600/);

  const exactLimit = createPackageClockController();
  exactLimit.observeState(state(0));
  exactLimit.arm({ kind: "scene_point", scene_id: "1B", point: "target", target_seconds: 3600 });
  assert.equal(exactLimit.deltaForRequest(), 3600);
});

test("records an accepted turn that reaches the requested target exactly", () => {
  const controller = createPackageClockController();
  const milestone = { kind: "scene_point", scene_id: "1B", point: "target", target_seconds: 195 };
  controller.observeState(state(120));
  controller.arm(milestone);
  assert.equal(controller.deltaForRequest(), 75);

  const outcome = controller.observeTurnResponse({ state: state(195, { scene_id: "1B" }) });

  assert.deepEqual(outcome, {
    reached: true,
    elapsed_seconds: 195,
    requested_milestone: milestone,
  });
  assert.deepEqual(controller.history(), [
    {
      requested_milestone: milestone,
      prior_elapsed_seconds: 120,
      sent_delta_seconds: 75,
      returned_elapsed_seconds: 195,
      scene_id: "1B",
      fired_pacing_event_ids: [],
      reached: true,
    },
  ]);
  assert.equal(controller.armed(), null);
});

test("reports an accepted turn landing short of its milestone", () => {
  const controller = createPackageClockController();
  controller.observeState(state(120));
  controller.arm({ kind: "scene_point", scene_id: "1B", point: "target", target_seconds: 195 });
  controller.deltaForRequest();

  const outcome = controller.observeTurnResponse({ state: state(180) });

  assert.equal(outcome.reached, false);
  assert.equal(outcome.elapsed_seconds, 180);
  assert.equal(controller.history()[0].returned_elapsed_seconds, 180);
});

test("keeps a pending game break anchored to its actual elapsed time", () => {
  const controller = createPackageClockController();
  const milestone = { kind: "pacing_event", scene_id: "2C", event_id: "purge_2c", target_seconds: 690 };
  controller.observeState(state(600));
  controller.arm(milestone);
  assert.equal(controller.deltaForRequest(), 90);

  const outcome = controller.observeTurnResponse({
    state: state(600, { pending_game_break: true, scene_id: "2C" }),
  });

  assert.equal(outcome.reached, false);
  assert.equal(outcome.elapsed_seconds, 600);
  assert.equal(controller.history()[0].returned_elapsed_seconds, 600);
  assert.equal(controller.armed(), null);
});

test("uses the real elapsed value for a subsequent delta after a game break", () => {
  const controller = createPackageClockController();
  controller.observeState(state(600));
  controller.arm({ kind: "pacing_event", scene_id: "2C", event_id: "purge_2c", target_seconds: 690 });
  controller.deltaForRequest();
  controller.observeTurnResponse({ state: state(600, { pending_game_break: true }) });

  controller.arm({ kind: "scene_point", scene_id: "2D", point: "target", target_seconds: 650 });
  assert.equal(controller.deltaForRequest(), 50);
});

test("rejects a malformed turn response state", () => {
  const controller = createPackageClockController();

  assert.throws(
    () => controller.observeTurnResponse({ state: { scene_id: "1A" } }),
    /elapsed|missing|malformed/i,
  );
});

test("updates the anchor for an unarmed turn without fabricating history", () => {
  const controller = createPackageClockController();

  const outcome = controller.observeTurnResponse({ state: state(120) });

  assert.equal(outcome.reached, false);
  assert.equal(outcome.elapsed_seconds, 120);
  assert.equal(outcome.requested_milestone, null);
  assert.deepEqual(controller.history(), []);

  controller.arm({ kind: "scene_point", scene_id: "1B", point: "target", target_seconds: 195 });
  assert.equal(controller.deltaForRequest(), 75);
});

test("rejects mixing package and scalar clock modes", () => {
  assert.throws(
    () =>
      assertExclusiveClockMode({
        E2E_PACKAGE_CLOCK: "package.json",
        E2E_TEST_CLOCK_SECONDS: "120",
      }),
    /E2E_PACKAGE_CLOCK.*E2E_TEST_CLOCK_SECONDS|E2E_TEST_CLOCK_SECONDS.*E2E_PACKAGE_CLOCK/,
  );
  assert.doesNotThrow(() => assertExclusiveClockMode({ E2E_PACKAGE_CLOCK: "package.json" }));
  assert.doesNotThrow(() => assertExclusiveClockMode({ E2E_TEST_CLOCK_SECONDS: "120" }));
  assert.doesNotThrow(() => assertExclusiveClockMode({}));
});
