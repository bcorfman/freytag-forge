import assert from "node:assert/strict";
import test from "node:test";

import { blindEntryState, installStartSceneRoute, sessionBodyWithStart, startSceneSession } from "./helpers.js";

function fakePage() {
  const registrations = [];
  return {
    registrations,
    route: async (pattern, handler) => registrations.push({ pattern, handler }),
  };
}

function fakeRoute({ method = "POST", url = "https://api.example/api/v1/session", body = '{"story_id":"story"}' } = {}) {
  const fallbacks = [];
  return {
    fallbacks,
    request: () => ({ method: () => method, url: () => url, postData: () => body }),
    fallback: async (...args) => fallbacks.push(args),
  };
}

test("does not install a session route without start options", async () => {
  const page = fakePage();
  assert.equal(await installStartSceneRoute(page), false);
  assert.deepEqual(page.registrations, []);
});

test("rewrites a session body while preserving its existing fields", async () => {
  const page = fakePage();
  assert.equal(await installStartSceneRoute(page, { startScene: "2B" }), true);
  assert.equal(page.registrations[0].pattern, "**/api/v1/session");

  const route = fakeRoute();
  await page.registrations[0].handler(route);
  assert.deepEqual(JSON.parse(route.fallbacks[0][0].postData), {
    story_id: "story",
    start_scene: "2B",
    start_state: "canonical",
  });
});

test("supports the requested seeded states", () => {
  for (const startState of ["canonical", "thorough", "bare"]) {
    assert.deepEqual(JSON.parse(sessionBodyWithStart('{"story_id":"story"}', "3A", startState)), {
      story_id: "story",
      start_scene: "3A",
      start_state: startState,
    });
  }
});

test("rejects an unknown seeded state before registering a route", async () => {
  const page = fakePage();
  await assert.rejects(
    () => installStartSceneRoute(page, { startScene: "2B", startState: "mystery" }),
    /Unknown startState "mystery"; expected canonical, thorough, or bare\./,
  );
  assert.deepEqual(page.registrations, []);
});

test("defaults the blind-player entry state to canonical and validates overrides", () => {
  const previousState = process.env.E2E_BLIND_ENTRY_STATE;
  try {
    delete process.env.E2E_BLIND_ENTRY_STATE;
    assert.equal(blindEntryState(), "canonical");
    process.env.E2E_BLIND_ENTRY_STATE = "bare";
    assert.equal(blindEntryState(), "bare");
    process.env.E2E_BLIND_ENTRY_STATE = "mystery";
    assert.throws(
      () => blindEntryState(),
      /Unknown startState "mystery"; expected canonical, thorough, or bare\./,
    );
  } finally {
    if (previousState === undefined) delete process.env.E2E_BLIND_ENTRY_STATE;
    else process.env.E2E_BLIND_ENTRY_STATE = previousState;
  }
});

test("passes non-POST and non-session requests through untouched", async () => {
  const page = fakePage();
  await installStartSceneRoute(page, { startScene: "2B" });
  const handler = page.registrations[0].handler;

  const getRoute = fakeRoute({ method: "GET" });
  await handler(getRoute);
  const otherPathRoute = fakeRoute({ url: "https://api.example/api/v1/turn" });
  await handler(otherPathRoute);
  assert.deepEqual(getRoute.fallbacks, [[]]);
  assert.deepEqual(otherPathRoute.fallbacks, [[]]);
});

test("fails before registering routes when a seeded start has no test token", async () => {
  const previousToken = process.env.FREYTAG_TEST_CLOCK_TOKEN;
  delete process.env.FREYTAG_TEST_CLOCK_TOKEN;
  try {
    await assert.rejects(
      () => startSceneSession({}, { startScene: "2B" }),
      /FREYTAG_TEST_CLOCK_TOKEN.*HTTP 403/,
    );
  } finally {
    if (previousToken === undefined) delete process.env.FREYTAG_TEST_CLOCK_TOKEN;
    else process.env.FREYTAG_TEST_CLOCK_TOKEN = previousToken;
  }
});
