import assert from "node:assert/strict";
import test from "node:test";

import { installApiToken } from "./api-token.js";

test("does not install a route without a token", async () => {
  const page = { route: () => assert.fail("route should not be registered") };
  assert.equal(await installApiToken(page, { apiBaseUrl: "https://api.example", token: "" }), false);
});

test("installs the API token route and falls back with the header", async () => {
  let pattern;
  let handler;
  const page = {
    route: async (routePattern, routeHandler) => {
      pattern = routePattern;
      handler = routeHandler;
    },
  };
  assert.equal(await installApiToken(page, { apiBaseUrl: "https://api.example///", token: "secret" }), true);
  assert.equal(pattern, "https://api.example/api/v1/**");

  let fallbackOptions;
  const route = {
    request: () => ({ headers: () => ({ accept: "application/json" }) }),
    fallback: async (options) => {
      fallbackOptions = options;
    },
  };
  await handler(route);
  assert.deepEqual(fallbackOptions, {
    headers: { accept: "application/json", "x-freytag-test-clock-token": "secret" },
  });
});

test("requires an API base URL when a token is set", async () => {
  await assert.rejects(
    () => installApiToken({ route: () => assert.fail("route should not be registered") }, { token: "secret" }),
    /API base URL/,
  );
});
