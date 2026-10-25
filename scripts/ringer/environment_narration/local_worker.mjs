import { createServer } from "node:http";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

import worker, { DailyBudget } from "../../../worker/src/index.js";

const DEFAULT_PORT = 8787;
const REQUIRED_CREDENTIALS = [
  "CLOUDFLARE_WORKER_TOKEN",
  "CLOUDFLARE_ACCOUNT_ID",
  "CLOUDFLARE_AI_TOKEN"
];

class Storage {
  constructor() {
    this.values = new Map();
  }

  async get(key) {
    return this.values.get(key);
  }

  async put(key, value) {
    this.values.set(key, structuredClone(value));
  }
}

class Namespace {
  constructor() {
    this.objects = new Map();
  }

  idFromName(name) {
    return name;
  }

  get(id) {
    if (!this.objects.has(id)) {
      const storage = new Storage();
      this.objects.set(id, { object: new DailyBudget({ storage }, {}), storage });
    }
    return this.objects.get(id).object;
  }

  storage(id) {
    return this.objects.get(id)?.storage;
  }
}

let fetchQueue = Promise.resolve();

function positiveNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

function buildWorkerEnv(source, maxUsd, namespace) {
  const workerEnv = {
    DEMO_SHARED_TOKEN: source.CLOUDFLARE_WORKER_TOKEN ?? source.DEMO_SHARED_TOKEN ?? "",
    CF_ACCOUNT_ID: source.CLOUDFLARE_ACCOUNT_ID ?? source.CF_ACCOUNT_ID ?? "",
    CF_API_TOKEN: source.CLOUDFLARE_AI_TOKEN ?? source.CF_API_TOKEN ?? "",
    DAILY_BUDGET_USD: String(maxUsd),
    DAILY_BUDGET: namespace
  };
  if (source.MODEL_PRICES_JSON !== undefined) workerEnv.MODEL_PRICES_JSON = source.MODEL_PRICES_JSON;
  return workerEnv;
}

export function createLocalWorker({ env = process.env, fetchImpl } = {}) {
  const source = env || {};
  const maxUsd = positiveNumber(source.DAILY_BUDGET_USD) || 5;
  const namespace = new Namespace();
  const workerEnv = buildWorkerEnv(source, maxUsd, namespace);
  const spentMicroUsd = () => Number(namespace.storage(namespace.idFromName(todayKey()))?.values.get("spent") || 0);

  return {
    async handle(nodeRequest, nodeResponse) {
      const started = performance.now();
      const requestUrl = new URL(nodeRequest.url || "/", `http://${nodeRequest.headers.host || "127.0.0.1"}`);
      let status = 500;
      let response;

      try {
        if (nodeRequest.method === "GET" && requestUrl.pathname === "/__spent") {
          response = new Response(JSON.stringify({
            spent_micro_usd: spentMicroUsd(),
            max_usd: maxUsd
          }), { headers: { "Content-Type": "application/json; charset=utf-8" } });
        } else {
          const headers = new Headers();
          for (const [name, value] of Object.entries(nodeRequest.headers)) {
            if (value !== undefined) headers.set(name, Array.isArray(value) ? value.join(", ") : value);
          }
          const chunks = [];
          if (nodeRequest.method !== "GET" && nodeRequest.method !== "HEAD") {
            for await (const chunk of nodeRequest) chunks.push(chunk);
          }
          const body = chunks.length ? Buffer.concat(chunks) : undefined;
          const webRequest = new Request(requestUrl, {
            method: nodeRequest.method,
            headers,
            body,
            ...(body ? { duplex: "half" } : {})
          });
          response = await invokeWorker(webRequest, workerEnv, fetchImpl);
        }

        status = response.status;
        const responseBody = Buffer.from(await response.arrayBuffer());
        const responseHeaders = {};
        for (const [name, value] of response.headers) responseHeaders[name] = value;
        nodeResponse.writeHead(status, responseHeaders);
        nodeResponse.end(responseBody);
        logRequest(requestUrl.pathname, status, started, responseBody);
      } catch {
        const errorBody = Buffer.from(JSON.stringify({ status: "error" }));
        nodeResponse.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
        nodeResponse.end(errorBody);
        logRequest(requestUrl.pathname, status, started, errorBody);
      }
    },

    spentMicroUsd
  };
}

async function invokeWorker(request, env, fetchImpl) {
  let release;
  const previous = fetchQueue;
  fetchQueue = new Promise((resolve) => { release = resolve; });
  await previous;

  const originalFetch = globalThis.fetch;
  if (fetchImpl !== undefined) globalThis.fetch = fetchImpl;
  try {
    return await worker.fetch(request, env);
  } finally {
    globalThis.fetch = originalFetch;
    release();
  }
}

function logRequest(pathname, status, started, responseBody) {
  let model = "-";
  try {
    const payload = JSON.parse(responseBody.toString("utf8"));
    if (payload && payload.model !== undefined) model = String(payload.model);
  } catch {
    // The response is opaque to the log when it is not JSON.
  }
  const safePath = String(pathname).replace(/[\r\n]/g, " ");
  const safeModel = String(model).replace(/[\r\n]/g, " ");
  process.stdout.write(`${new Date().toISOString()} ${safePath} ${status} ${Math.round(performance.now() - started)}ms model=${safeModel}\n`);
}

export function startLocalServer({ port = DEFAULT_PORT, maxUsd, env = process.env, fetchImpl } = {}) {
  const runner = createLocalWorker({
    env: { ...env, DAILY_BUDGET_USD: String(maxUsd) },
    fetchImpl
  });
  const server = createServer((request, response) => {
    runner.handle(request, response).catch(() => {
      if (!response.headersSent) {
        response.writeHead(500, { "Content-Type": "application/json; charset=utf-8" });
        response.end(JSON.stringify({ status: "error" }));
      }
    });
  });
  server.localWorker = runner;
  return server.listen(port, "127.0.0.1");
}

function parseArgs(args) {
  let maxUsd;
  let port = DEFAULT_PORT;
  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (argument === "--max-usd") maxUsd = args[++index];
    else if (argument.startsWith("--max-usd=")) maxUsd = argument.slice("--max-usd=".length);
    else if (argument === "--port") port = args[++index];
    else if (argument.startsWith("--port=")) port = argument.slice("--port=".length);
    else throw new Error("Unknown argument");
  }

  const parsedMaxUsd = positiveNumber(maxUsd);
  if (parsedMaxUsd === null) throw new Error("--max-usd must be a positive number");
  const parsedPort = Number(port);
  if (!Number.isInteger(parsedPort) || parsedPort < 0 || parsedPort > 65535) {
    throw new Error("--port must be an integer from 0 to 65535");
  }
  return { maxUsd: parsedMaxUsd, port: parsedPort };
}

function runDirect() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
    return;
  }

  const missing = REQUIRED_CREDENTIALS.filter((name) => !process.env[name]);
  if (missing.length) {
    process.stderr.write(`Missing required environment variables: ${missing.join(", ")}\n`);
    process.exitCode = 1;
    return;
  }

  const server = startLocalServer({ ...options, env: process.env });
  const shutdown = () => {
    process.stdout.write(`final spent_micro_usd=${server.localWorker.spentMicroUsd()}\n`);
    server.close(() => process.exit(0));
  };
  process.once("SIGINT", shutdown);
  process.once("SIGTERM", shutdown);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) runDirect();
