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
  if (model.includes("deepseek")) {
    return { success: true, result: { choices: [{ message: { content: "Deep narration" } }] } };
  }
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

test("llama 3.3 extracts result.response", async () => {
  const environment = env({ CF_AI_MODEL: "@cf/meta/llama-3.3-70b-instruct-fp8-fast" });
  const response = await runWithFetch(aiResponse({ success: true, result: { response: "Seventy billion narration" } }), () =>
    worker.fetch(request(), environment)
  );
  assert.equal(response.status, 200);
  assert.equal((await response.json()).narration, "Seventy billion narration");
});

test("deepseek uses final content and ignores a longer reasoning field", async () => {
  const environment = env({ CF_AI_MODEL: "@cf/deepseek-ai/deepseek-v4.1-flash-1017" });
  const response = await runWithFetch(aiResponse({
    success: true,
    result: { choices: [{ message: { reasoning: "A very long private chain", content: "Final narration" } }] }
  }), () => worker.fetch(request(), environment));
  assert.equal(response.status, 200);
  assert.equal((await response.json()).narration, "Final narration");
});

test("reasoning-only deepseek response is AI_EMPTY_RESPONSE", async () => {
  const environment = env({ CF_AI_MODEL: "@cf/deepseek-ai/deepseek-v4.1-flash-1017" });
  const response = await runWithFetch(aiResponse({
    success: true,
    result: { choices: [{ message: { reasoning: "Only reasoning" } }] }
  }), () => worker.fetch(request(), environment));
  assert.equal(response.status, 502);
  assert.equal((await response.json()).code, "AI_EMPTY_RESPONSE");
});

test("deepseek length finish keeps narration and reports truncation", async () => {
  const environment = env({ CF_AI_MODEL: "@cf/deepseek-ai/deepseek-v4.1-flash-1017" });
  const response = await runWithFetch(aiResponse({
    success: true,
    result: { choices: [{ finish_reason: "length", message: { content: "Partial narration" } }] }
  }), () => worker.fetch(request(), environment));
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.narration, "Partial narration");
  assert.equal(body.truncated, true);
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

test("deepseek usage settles at its actual priced cost", async () => {
  const model = "@cf/deepseek-ai/deepseek-v4.1-flash-1017";
  const environment = env({ CF_AI_MODEL: model });
  const response = await runWithFetch(aiResponse({
    success: true,
    result: { choices: [{ message: { content: "Done" } }], usage: { prompt_tokens: 10, completion_tokens: 20 } }
  }), () => worker.fetch(request(), environment));
  assert.equal(response.status, 200);
  assert.equal(await environment.DAILY_BUDGET.storage(new Date().toISOString().slice(0, 10)).get("spent"), callCostMicroUsd(DEFAULT_MODEL_PRICES, model, 10, 20));
});

test("missing usage settles the reservation", async () => {
  const environment = env();
  const expected = callCostMicroUsd(DEFAULT_MODEL_PRICES, "@cf/meta/llama-3.1-8b-instruct-fast", estimateInputTokens("Guide the player.Search the room."), 64);
  await runWithFetch(aiResponse({ success: true, result: { response: "Done" } }), () => worker.fetch(request(), environment));
  assert.equal(await environment.DAILY_BUDGET.storage(new Date().toISOString().slice(0, 10)).get("spent"), expected);
});

test("deepseek clamps to 4096 while other models clamp to 2048", async () => {
  const deepseekEnv = env({ CF_AI_MODEL: "@cf/deepseek-ai/deepseek-v4.1-flash-1017" });
  const llamaEnv = env();
  const deepseek = await runWithFetch(aiResponse(successFor(deepseekEnv.CF_AI_MODEL)), (calls) => worker.fetch(request({ max_tokens: 9000 }), deepseekEnv).then(() => JSON.parse(calls[0].init.body)));
  const llama = await runWithFetch(aiResponse(successFor("llama")), (calls) => worker.fetch(request({ max_tokens: 9000 }), llamaEnv).then(() => JSON.parse(calls[0].init.body)));
  assert.equal(deepseek.max_completion_tokens, 4096);
  assert.equal(llama.max_tokens, 2048);
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
  ["unlisted", { CF_BENCH_MODELS: "@cf/meta/llama-3.1-8b-instruct-fast" }],
  ["unpriced", { CF_BENCH_MODELS: "@cf/deepseek-ai/deepseek-v4.1-flash-1017", MODEL_PRICES_JSON: JSON.stringify({ "@cf/deepseek-ai/deepseek-v4.1-flash-1017": null }) }]
]) {
  test(`benchmark model is rejected when ${name}`, async () => {
    const environment = env(overrides);
    const namespace = environment.DAILY_BUDGET;
    let aiCalls = 0;
    const response = await runWithFetch(() => { aiCalls += 1; return aiResponse(successFor("llama")); }, () =>
      worker.fetch(request({}, { "X-Bench-Model": "@cf/deepseek-ai/deepseek-v4.1-flash-1017" }), environment)
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
  assert.equal((await response.json()).model, "@cf/meta/llama-3.1-8b-instruct-fast");
});
