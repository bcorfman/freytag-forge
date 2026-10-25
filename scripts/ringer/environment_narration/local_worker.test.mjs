import assert from "node:assert/strict";
import { once } from "node:events";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import test from "node:test";

import { createLocalWorker, startLocalServer } from "./local_worker.mjs";

const TOKEN = "test-worker-token";
const ACCOUNT_ID = "test-account";
const AI_TOKEN = "test-ai-token";
const MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";

function fakeWorkersAiFetch(calls) {
  return async (url, init) => {
    calls.push({ url, init });
    if (String(url).endsWith("/ai/run")) {
      return new Response(JSON.stringify({
        success: true,
        result: {
          state: "Completed",
          result: {
            answers: { first: "Jev answer" },
            model: "typesafe/jev",
            usage: { input_tokens: 12 }
          }
        }
      }));
    }
    return new Response(JSON.stringify({
      success: true,
      result: { response: "REPLY-SECRET" }
    }));
  };
}

function makeEnv(overrides = {}) {
  return {
    CLOUDFLARE_WORKER_TOKEN: TOKEN,
    CLOUDFLARE_ACCOUNT_ID: ACCOUNT_ID,
    CLOUDFLARE_AI_TOKEN: AI_TOKEN,
    DAILY_BUDGET_USD: "0.10",
    ...overrides
  };
}

function requestBody(overrides = {}) {
  return {
    system: "SYSTEM-REQUEST-SECRET",
    user: "USER-REQUEST-SECRET",
    max_tokens: 64,
    ...overrides
  };
}

async function callRunner(runner, { path = "/", body = requestBody(), token = TOKEN, method = "POST" } = {}) {
  const server = createServer((request, response) => {
    runner.handle(request, response).catch((error) => {
      response.statusCode = 500;
      response.end(String(error));
    });
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address();
  const response = await fetch(`http://127.0.0.1:${address.port}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json"
    },
    body: method === "GET" ? undefined : JSON.stringify(body)
  });
  const text = await response.text();
  await new Promise((resolve) => server.close(resolve));
  return { response, body: text ? JSON.parse(text) : null };
}

test("POST accepts the token, calls the default 70B, and omits response_format", async () => {
  const calls = [];
  const runner = createLocalWorker({ env: makeEnv(), fetchImpl: fakeWorkersAiFetch(calls) });

  const result = await callRunner(runner);

  assert.equal(result.response.status, 200);
  assert.equal(result.body.narration, "REPLY-SECRET");
  assert.equal(result.body.model, MODEL);
  const upstreamBody = JSON.parse(calls[0].init.body);
  assert.deepEqual(upstreamBody.messages, [
    { role: "system", content: "SYSTEM-REQUEST-SECRET" },
    { role: "user", content: "USER-REQUEST-SECRET" }
  ]);
  assert.equal(upstreamBody.max_tokens, 64);
  assert.equal("response_format" in upstreamBody, false);
});

test("/jev uses the same Worker call path and returns Jev answers", async () => {
  const calls = [];
  const runner = createLocalWorker({ env: makeEnv(), fetchImpl: fakeWorkersAiFetch(calls) });

  const result = await callRunner(runner, {
    path: "/jev",
    body: { input: { state: "start", questions: { next: "What happens?" } } }
  });

  assert.equal(result.response.status, 200);
  assert.deepEqual(result.body.answers, { first: "Jev answer" });
  assert.equal(calls.length, 1);
  assert.match(calls[0].url, /\/ai\/run$/);
});

test("wrong token returns 401 without calling Workers AI", async () => {
  const calls = [];
  const runner = createLocalWorker({ env: makeEnv(), fetchImpl: fakeWorkersAiFetch(calls) });

  const result = await callRunner(runner, { token: "wrong-token" });

  assert.equal(result.response.status, 401);
  assert.equal(calls.length, 0);
});

test("the daily budget rejects the second 1-micro-USD call before Workers AI", async () => {
  const calls = [];
  const runner = createLocalWorker({
    env: makeEnv({
      DAILY_BUDGET_USD: "0.000001",
      MODEL_PRICES_JSON: JSON.stringify({ [MODEL]: { input: 0, output: 0.01 } })
    }),
    fetchImpl: fakeWorkersAiFetch(calls)
  });

  const first = await callRunner(runner);
  const second = await callRunner(runner);

  assert.equal(first.response.status, 200);
  assert.equal(second.response.status, 429);
  assert.equal(second.body.code, "AI_DAILY_BUDGET_EXCEEDED");
  assert.equal(calls.length, 1);
});

test("/__spent reports a positive amount after a call", async () => {
  const runner = createLocalWorker({ env: makeEnv(), fetchImpl: fakeWorkersAiFetch([]) });

  await callRunner(runner);
  const result = await callRunner(runner, { path: "/__spent", method: "GET" });

  assert.equal(result.response.status, 200);
  assert.ok(result.body.spent_micro_usd > 0);
  assert.equal(result.body.max_usd, 0.1);
});

test("request log includes path and status but no request, reply, or token text", async () => {
  const calls = [];
  const runner = createLocalWorker({ env: makeEnv(), fetchImpl: fakeWorkersAiFetch(calls) });
  const writes = [];
  const originalWrite = process.stdout.write;
  process.stdout.write = (chunk, ...args) => {
    writes.push(String(chunk));
    return true;
  };
  try {
    await callRunner(runner);
  } finally {
    process.stdout.write = originalWrite;
  }

  const log = writes.join("");
  assert.match(log, /\/ 200/);
  assert.doesNotMatch(log, /SYSTEM-REQUEST-SECRET|USER-REQUEST-SECRET|REPLY-SECRET|test-worker-token/);
});

test("direct startup without --max-usd fails without printing secrets", async () => {
  const child = spawn(process.execPath, ["scripts/ringer/environment_narration/local_worker.mjs"], {
    cwd: "/home/bcorfman/dev/freytag-forge",
    env: {
      PATH: process.env.PATH,
      CLOUDFLARE_WORKER_TOKEN: "SECRET-ONE",
      CLOUDFLARE_ACCOUNT_ID: "SECRET-TWO",
      CLOUDFLARE_AI_TOKEN: "SECRET-THREE"
    },
    stdio: ["ignore", "pipe", "pipe"]
  });
  let stdout = "";
  let stderr = "";
  child.stdout.on("data", (chunk) => { stdout += chunk; });
  child.stderr.on("data", (chunk) => { stderr += chunk; });
  const [code] = await once(child, "close");

  assert.notEqual(code, 0);
  assert.equal(stdout, "");
  assert.doesNotMatch(stderr, /SECRET-ONE|SECRET-TWO|SECRET-THREE/);
});

test("the server binds to loopback only", async () => {
  const server = startLocalServer({
    port: 0,
    maxUsd: 0.1,
    env: makeEnv(),
    fetchImpl: fakeWorkersAiFetch([])
  });
  await once(server, "listening");
  try {
    assert.equal(server.address().address, "127.0.0.1");
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});
