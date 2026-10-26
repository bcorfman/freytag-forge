import test from "node:test";
import assert from "node:assert/strict";
import worker, { DailyBudget } from "../src/index.js";
import { DEFAULT_MODEL_PRICES, callCostMicroUsd, estimateInputTokens } from "../src/budget.js";
import { MODEL_PROFILES } from "../src/models.js";

class Storage {
  constructor() { this.values = new Map(); }
  async get(key) { return this.values.get(key); }
  async put(key, value) { this.values.set(key, structuredClone(value)); }
}

class Namespace {
  constructor() { this.objects = new Map(); }
  idFromName(name) { return name; }
  get(id) {
    if (!this.objects.has(id)) {
      const storage = new Storage();
      this.objects.set(id, { object: new DailyBudget({ storage }, {}), storage });
    }
    return this.objects.get(id).object;
  }
  storage(id) { return this.objects.get(id)?.storage; }
}

function env(overrides = {}) {
  return {
    DEMO_SHARED_TOKEN: "secret",
    CF_ACCOUNT_ID: "account",
    CF_API_TOKEN: "api-token",
    DAILY_BUDGET: new Namespace(),
    ...overrides
  };
}

function request(body = {}, headers = {}) {
  return new Request("https://worker.test", {
    method: "POST",
    headers: { Authorization: "Bearer secret", "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ system: "Guide the player.", user: "Search the room.", max_tokens: 64, ...body })
  });
}

async function runWithFetch(response, run) {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return typeof response === "function" ? response({ url, init }) : response;
  };
  try {
    return await run(calls);
  } finally {
    globalThis.fetch = originalFetch;
  }
}

function aiResponse(payload, status = 200) {
  return new Response(typeof payload === "string" ? payload : JSON.stringify(payload), { status });
}

function successFor(model) {
  return { success: true, result: { response: "Llama narration" } };
}

test("each profile emits its documented Workers AI request body", async () => {
  for (const model of Object.keys(MODEL_PROFILES)) {
    const environment = env({ CF_AI_MODEL: model });
    const result = await runWithFetch(aiResponse(successFor(model)), async (calls) => ({
      response: await worker.fetch(request(), environment),
      call: calls[0]
    })
    );
    const response = result.response;
    assert.equal(response.status, 200);
    const body = JSON.parse(result.call.init.body);
    assert.deepEqual(body.messages, [
      { role: "system", content: "Guide the player." },
      { role: "user", content: "Search the room." }
    ]);
    if (model.includes("deepseek")) {
      assert.equal(body.max_completion_tokens, 64);
      assert.equal(body.reasoning_effort, "low");
      assert.equal("max_tokens" in body, false);
    } else {
      assert.equal(body.max_tokens, 64);
      assert.equal("max_completion_tokens" in body, false);
    }
  }
});

test("70B ignores JSON response format and temperature", async () => {
  const environment = env({ CF_AI_MODEL: "@cf/meta/llama-3.3-70b-instruct-fp8-fast" });
  const result = await runWithFetch(aiResponse(successFor(environment.CF_AI_MODEL)), async (calls) => ({
    response: await worker.fetch(request({ response_format: { type: "json_object" } }), environment),
    body: JSON.parse(calls[0].init.body)
  }));
  assert.equal(result.response.status, 200);
  assert.deepEqual(result.body.messages, [
    { role: "system", content: "Guide the player." },
    { role: "user", content: "Search the room." }
  ]);
  assert.equal(result.body.max_tokens, 64);
  assert.equal("response_format" in result.body, false);
  assert.equal("temperature" in result.body, false);
});

test("allowed benchmark 70B ignores JSON response format", async () => {
  const model = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
  const environment = env({ CF_BENCH_MODELS: model });
  const result = await runWithFetch(aiResponse(successFor(model)), async (calls) => ({
    response: await worker.fetch(request({ response_format: { type: "json_object" } }, { "X-Bench-Model": model }), environment),
    body: JSON.parse(calls[0].init.body)
  }));
  assert.equal(result.response.status, 200);
  assert.equal("response_format" in result.body, false);
  assert.equal("temperature" in result.body, false);
});

test("llama 3.3 extracts result.response", async () => {
  const environment = env({ CF_AI_MODEL: "@cf/meta/llama-3.3-70b-instruct-fp8-fast" });
  const response = await runWithFetch(aiResponse({ success: true, result: { response: "Seventy billion narration" } }), () =>
    worker.fetch(request(), environment)
  );
  assert.equal(response.status, 200);
  assert.equal((await response.json()).narration, "Seventy billion narration");
});

test("malformed upstream JSON uses the existing upstream error", async () => {
  const response = await runWithFetch(aiResponse("not json"), () => worker.fetch(request(), env()));
  assert.equal(response.status, 502);
  assert.equal((await response.json()).code, "AI_UPSTREAM_ERROR");
});

test("quota 429 remains AI_QUOTA_EXCEEDED", async () => {
  const response = await runWithFetch(aiResponse({ errors: [{ message: "daily quota exceeded" }] }, 429), () =>
    worker.fetch(request(), env())
  );
  assert.equal(response.status, 429);
  assert.equal((await response.json()).code, "AI_QUOTA_EXCEEDED");
});

test("missing usage settles the reservation", async () => {
  const environment = env();
  const expected = callCostMicroUsd(DEFAULT_MODEL_PRICES, "@cf/meta/llama-3.3-70b-instruct-fp8-fast", estimateInputTokens("Guide the player.Search the room."), 64);
  await runWithFetch(aiResponse({ success: true, result: { response: "Done" } }), () => worker.fetch(request(), environment));
  assert.equal(await environment.DAILY_BUDGET.storage(new Date().toISOString().slice(0, 10)).get("spent"), expected);
});

test("allowed benchmark model is called and reported", async () => {
  const model = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
  const environment = env({ CF_BENCH_MODELS: model });
  const response = await runWithFetch(aiResponse(successFor(model)), (calls) => worker.fetch(request({}, { "X-Bench-Model": model }), environment).then(async (result) => ({ result, body: JSON.parse(calls[0].init.body) })));
  assert.equal(response.result.status, 200);
  assert.equal(response.body.max_tokens, 64);
  assert.equal((await response.result.json()).model, model);
});

for (const [name, overrides] of [
  ["feature off", {}],
  ["unlisted", { CF_BENCH_MODELS: "@cf/meta/llama-3.3-70b-instruct-fp8-fast" }],
  ["unpriced", { CF_BENCH_MODELS: "@cf/meta/llama-3.3-70b-instruct-fp8-fast", MODEL_PRICES_JSON: JSON.stringify({ "@cf/meta/llama-3.3-70b-instruct-fp8-fast": null }) }]
]) {
  test(`benchmark model is rejected when ${name}`, async () => {
    const environment = env(overrides);
    const namespace = environment.DAILY_BUDGET;
    const benchModel = name === "unpriced"
      ? "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
      : "made-up-model-without-a-profile";
    let aiCalls = 0;
    const response = await runWithFetch(() => { aiCalls += 1; return aiResponse(successFor("llama")); }, () =>
      worker.fetch(request({}, { "X-Bench-Model": benchModel }), environment)
    );
    assert.equal(response.status, 400);
    assert.equal((await response.json()).code, "BENCH_MODEL_REJECTED");
    assert.equal(aiCalls, 0);
    assert.equal(namespace.objects.size, 0);
  });
}

test("no benchmark header keeps the default model", async () => {
  const response = await runWithFetch(aiResponse(successFor("llama")), () => worker.fetch(request(), env({ CF_BENCH_MODELS: "@cf/meta/llama-3.3-70b-instruct-fp8-fast" })));
  assert.equal(response.status, 200);
  assert.equal((await response.json()).model, "@cf/meta/llama-3.3-70b-instruct-fp8-fast");
});
