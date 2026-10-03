import test from "node:test";
import assert from "node:assert/strict";
import { BudgetLedger, DEFAULT_MODEL_PRICES, callCostMicroUsd, estimateInputTokens } from "../src/budget.js";
import worker, { DailyBudget } from "../src/index.js";

class Storage {
  constructor() { this.values = new Map(); }
  async get(key) { await new Promise((resolve) => setImmediate(resolve)); return this.values.get(key); }
  async put(key, value) { await new Promise((resolve) => setImmediate(resolve)); this.values.set(key, structuredClone(value)); }
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
  storage(id) { return id ? this.objects.get(id)?.storage : this.objects.values().next().value?.storage; }
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

function request(body = {}) {
  return new Request("https://worker.test", {
    method: "POST",
    headers: { Authorization: "Bearer secret", "Content-Type": "application/json" },
    body: JSON.stringify({ system: "Guide the player.", user: "Search the room.", max_tokens: 64, ...body })
  });
}

test("cost maths uses byte-based input estimates and whole micro-dollars", () => {
  assert.equal(estimateInputTokens("a€"), 2);
  assert.equal(callCostMicroUsd(DEFAULT_MODEL_PRICES, "@cf/meta/llama-3.1-8b-instruct-fast", 10, 20), 20);
  assert.equal(callCostMicroUsd({}, "unknown", 10, 20), null);
});

test("ledger refuses a reservation past the limit", async () => {
  const ledger = new BudgetLedger(new Storage());
  assert.deepEqual(await ledger.reserve(11, 10), { ok: false });
});

test("parallel reservations never overshoot an awaiting storage", async () => {
  const ledger = new BudgetLedger(new Storage());
  const results = await Promise.all(Array.from({ length: 20 }, () => ledger.reserve(1, 10)));
  assert.equal(results.filter((result) => result.ok).length, 10);
});

test("settling removes the reservation and counts the actual cost", async () => {
  const storage = new Storage();
  const ledger = new BudgetLedger(storage);
  const reservation = await ledger.reserve(10, 20);
  await ledger.settle(reservation.id, 3);
  assert.equal(await storage.get("spent"), 3);
  assert.deepEqual(await storage.get("reservations"), {});
});

test("missing token is refused before reading the body", async () => {
  const response = await worker.fetch(new Request("https://worker.test", { method: "POST", body: "not json" }), env({ DEMO_SHARED_TOKEN: "" }));
  assert.equal(response.status, 500);
  assert.equal((await response.json()).code, "WORKER_CONFIGURATION_ERROR");
});

test("spent budget returns 429 without an AI call", async () => {
  let aiCalls = 0;
  const namespace = new Namespace();
  const day = new Date().toISOString().slice(0, 10);
  const reservationResponse = await namespace.get(day).fetch("https://budget/reserve", {
    method: "POST",
    body: JSON.stringify({ amount: 1, limit: 1 })
  });
  const reservation = await reservationResponse.json();
  await namespace.get(day).fetch("https://budget/settle", {
    method: "POST",
    body: JSON.stringify({ id: reservation.id, amount: 1 })
  });
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => { aiCalls += 1; throw new Error("AI should not be called"); };
  try {
    const response = await worker.fetch(request(), env({ DAILY_BUDGET: namespace, DAILY_BUDGET_USD: "0.000001" }));
    assert.equal(response.status, 429);
    assert.equal((await response.json()).code, "AI_DAILY_BUDGET_EXCEEDED");
    assert.equal(aiCalls, 0);
  } finally { globalThis.fetch = originalFetch; }
});

test("missing or failing counter returns 503 without an AI call", async () => {
  let aiCalls = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => { aiCalls += 1; return new Response("{}", { status: 200 }); };
  try {
    const missing = await worker.fetch(request(), env({ DAILY_BUDGET: undefined }));
    assert.equal(missing.status, 503);
    const failing = await worker.fetch(request(), env({ DAILY_BUDGET: { idFromName() { throw new Error("down"); } } }));
    assert.equal(failing.status, 503);
    assert.equal(aiCalls, 0);
  } finally { globalThis.fetch = originalFetch; }
});

test("an unpriced model returns configuration error without an AI call", async () => {
  let aiCalls = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => { aiCalls += 1; return new Response("{}", { status: 200 }); };
  try {
    const response = await worker.fetch(request(), env({ CF_AI_MODEL: "custom-model" }));
    assert.equal(response.status, 500);
    assert.equal((await response.json()).code, "WORKER_CONFIGURATION_ERROR");
    assert.equal(aiCalls, 0);
  } finally { globalThis.fetch = originalFetch; }
});

test("successful AI usage settles to actual cost", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({ success: true, result: { response: "Done.", usage: { prompt_tokens: 1, completion_tokens: 2 } } }), { status: 200 });
  const namespace = new Namespace();
  try {
    const response = await worker.fetch(request(), env({ DAILY_BUDGET: namespace }));
    assert.equal(response.status, 200);
    assert.equal(await namespace.storage().get("spent"), 2);
  } finally { globalThis.fetch = originalFetch; }
});

function jevRequest(input, token = "secret") {
  return new Request("https://worker.test/jev", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ input })
  });
}

test("jev route returns answers and posts the Jev input to Workers AI", async () => {
  const input = { state: { scene: "hall" }, questions: { safe: "Is it safe?" } };
  let aiRequest;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    aiRequest = { url, init };
    return new Response(JSON.stringify({
      success: true,
      result: { state: "Completed", model: "typesafe/jev", result: { answers: { safe: { type: "noul", noul: 0.8 } }, usage: { input_tokens: 2 } } }
    }), { status: 200 });
  };
  try {
    const response = await worker.fetch(jevRequest(input), env());
    assert.equal(response.status, 200);
    assert.deepEqual((await response.json()).answers, { safe: { type: "noul", noul: 0.8 } });
    assert.equal(aiRequest.url, "https://api.cloudflare.com/client/v4/accounts/account/ai/run");
    assert.deepEqual(JSON.parse(aiRequest.init.body), { model: "typesafe/jev", input });
  } finally { globalThis.fetch = originalFetch; }
});

test("jev budget reserves and settles, then refuses a spent budget without Workers AI", async () => {
  const namespace = new Namespace();
  let aiCalls = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    aiCalls += 1;
    return new Response(JSON.stringify({ success: true, result: { state: "Completed", result: { answers: {}, usage: { input_tokens: 1 } } } }));
  };
  try {
    const first = await worker.fetch(jevRequest({ state: "hall", questions: { safe: "?" } }), env({ DAILY_BUDGET: namespace }));
    assert.equal(first.status, 200);
    assert.deepEqual(await namespace.storage().get("reservations"), {});
    assert.equal((await namespace.storage().get("spent")) > 0, true);
    const second = await worker.fetch(jevRequest({ state: "hall", questions: { safe: "?" } }), env({ DAILY_BUDGET: namespace, DAILY_BUDGET_USD: "0.000001" }));
    assert.equal(second.status, 429);
    assert.equal((await second.json()).code, "AI_DAILY_BUDGET_EXCEEDED");
    assert.equal(aiCalls, 1);
  } finally { globalThis.fetch = originalFetch; }
});

test("jev unauthorized returns 401 without calling Workers AI", async () => {
  let aiCalls = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => { aiCalls += 1; throw new Error("AI should not be called"); };
  try {
    const response = await worker.fetch(jevRequest({ state: "hall", questions: { safe: "?" } }, "wrong"), env());
    assert.equal(response.status, 401);
    assert.equal(aiCalls, 0);
  } finally { globalThis.fetch = originalFetch; }
});

test("jev oversized returns 413 without calling Workers AI", async () => {
  let aiCalls = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => { aiCalls += 1; throw new Error("AI should not be called"); };
  try {
    const response = await worker.fetch(jevRequest({ state: "x".repeat(90001), questions: { safe: "?" } }), env());
    assert.equal(response.status, 413);
    assert.equal(aiCalls, 0);
  } finally { globalThis.fetch = originalFetch; }
});

test("jev invalid returns 400 when questions are missing", async () => {
  const response = await worker.fetch(jevRequest({ state: "hall" }), env());
  assert.equal(response.status, 400);
  assert.equal((await response.json()).code, "INVALID_REQUEST");
});

test("narration route unchanged returns narration and model", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({ success: true, result: { response: "Done." } }));
  try {
    const response = await worker.fetch(request(), env());
    const body = await response.json();
    assert.equal(response.status, 200);
    assert.equal(body.narration, "Done.");
    assert.equal(body.model, "@cf/meta/llama-3.1-8b-instruct-fast");
  } finally { globalThis.fetch = originalFetch; }
});
