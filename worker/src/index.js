import {
  BudgetLedger,
  DEFAULT_MODEL_PRICES,
  callCostMicroUsd,
  estimateInputTokens,
  utcDay
} from "./budget.js";

const MAX_BODY_BYTES = 256 * 1024;

export default {
  async fetch(request, env) {
    const traceId = makeTraceId(request);
    const workerRevision = getWorkerRevision(env);
    const respondError = (code, message, status, errorTraceId, details = {}, extraHeaders = {}) =>
      errorJson(code, message, status, errorTraceId, details, extraHeaders, workerRevision);
    if (!asString(env.DEMO_SHARED_TOKEN).trim()) {
      return respondError("WORKER_CONFIGURATION_ERROR", "Worker token is not configured", 500, traceId);
    }
    if (request.method !== "POST") {
      return respondError("METHOD_NOT_ALLOWED", "Use POST", 405, traceId);
    }
    const authorization = request.headers.get("authorization") || "";
    if (authorization !== `Bearer ${env.DEMO_SHARED_TOKEN}`) {
      return respondError("UNAUTHORIZED", "Invalid token", 401, traceId);
    }
    const contentLength = Number(request.headers.get("content-length") || 0);
    if (contentLength > MAX_BODY_BYTES) {
      return respondError("REQUEST_TOO_LARGE", "Request body is too large", 413, traceId);
    }
    let body;
    try {
      const rawBody = await request.text();
      if (new TextEncoder().encode(rawBody).byteLength > MAX_BODY_BYTES) {
        return respondError("REQUEST_TOO_LARGE", "Request body is too large", 413, traceId);
      }
      body = JSON.parse(rawBody);
    } catch {
      return respondError("BAD_JSON", "Invalid JSON body", 400, traceId);
    }
    const system = asString(body?.system);
    const user = asString(body?.user);
    const maxTokens = boundedInteger(body?.max_tokens, 512, 64, 2048);
    const responseFormat = body?.response_format && typeof body.response_format === "object" ? body.response_format : null;
    const accountId = asString(env.CF_ACCOUNT_ID).trim();
    const apiToken = asString(env.CF_API_TOKEN).trim();
    const model = asString(env.CF_AI_MODEL).trim() || "@cf/meta/llama-3.1-8b-instruct-fast";
    if (!accountId || !apiToken) {
      return respondError("WORKER_CONFIGURATION_ERROR", "Workers AI credentials are not configured", 500, traceId);
    }
    if (!system || !user) {
      return respondError("INVALID_REQUEST", "Both system and user prompts are required", 400, traceId);
    }

    const prices = modelPrices(env, respondError, traceId);
    if (prices instanceof Response) return prices;
    const reservedAmount = callCostMicroUsd(prices, model, estimateInputTokens(system + user), maxTokens);
    if (reservedAmount === null || !Number.isFinite(reservedAmount) || reservedAmount < 0) {
      return respondError("WORKER_CONFIGURATION_ERROR", "The configured model has no price", 500, traceId);
    }
    const limit = dailyLimit(env.DAILY_BUDGET_USD);
    let budget;
    try {
      if (!env.DAILY_BUDGET) throw new Error("DAILY_BUDGET is missing");
      budget = env.DAILY_BUDGET.get(env.DAILY_BUDGET.idFromName(utcDay(new Date())));
      const reserveResponse = await budget.fetch("https://budget/reserve", {
        method: "POST",
        body: JSON.stringify({ amount: reservedAmount, limit })
      });
      if (!reserveResponse.ok) throw new Error(`reserve returned ${reserveResponse.status}`);
      const reservation = await reserveResponse.json();
      if (!reservation.ok) {
        return respondError("AI_DAILY_BUDGET_EXCEEDED", "The daily model budget is spent", 429, traceId);
      }
      const reservationId = reservation.id;
      let settlementAmount = reservedAmount;
      try {
        let aiResponse;
        try {
          aiResponse = await callWorkersAi({ accountId, apiToken, model, system, user, maxTokens, responseFormat });
        } catch (error) {
          console.error("Workers AI network failure", { trace_id: traceId, error: String(error) });
          return respondError("AI_NETWORK_ERROR", "Workers AI could not be reached", 502, traceId);
        }
        const upstreamRequestId = aiResponse.headers.get("cf-ray") || aiResponse.headers.get("x-request-id") || "";
        const rawResponse = await aiResponse.text();
        const parsedResponse = tryParseJson(rawResponse);
        if (aiResponse.ok && parsedResponse?.success !== false) {
          const usage = parsedResponse?.result?.usage;
          if (Number.isFinite(usage?.prompt_tokens) && Number.isFinite(usage?.completion_tokens)) {
            const actualAmount = callCostMicroUsd(prices, model, usage.prompt_tokens, usage.completion_tokens);
            if (actualAmount !== null) settlementAmount = actualAmount;
          }
        }
        if (!aiResponse.ok) {
          const upstreamErrors = extractErrors(parsedResponse);
          const upstreamCode = firstErrorCode(upstreamErrors);
          const upstreamMessage = firstErrorMessage(upstreamErrors);
          const classification = classifyUpstreamFailure(aiResponse.status, upstreamCode, upstreamMessage);
          console.error("Workers AI upstream failure", { trace_id: traceId, upstream_request_id: upstreamRequestId, upstream_status: aiResponse.status, upstream_code: upstreamCode, upstream_message: upstreamMessage });
          const headers = {};
          const retryAfter = aiResponse.headers.get("retry-after");
          if (retryAfter) headers["Retry-After"] = retryAfter;
          return respondError(classification.code, classification.message, classification.httpStatus, traceId, {
            upstream_status: aiResponse.status,
            upstream_code: upstreamCode || undefined,
            upstream_request_id: upstreamRequestId || undefined
          }, headers);
        }
        if (!parsedResponse || parsedResponse.success === false) {
          const upstreamErrors = extractErrors(parsedResponse);
          const upstreamCode = firstErrorCode(upstreamErrors);
          const upstreamMessage = firstErrorMessage(upstreamErrors);
          const classification = classifyUpstreamFailure(502, upstreamCode, upstreamMessage);
          console.error("Workers AI returned an unsuccessful envelope", { trace_id: traceId, upstream_request_id: upstreamRequestId, upstream_code: upstreamCode, upstream_message: upstreamMessage });
          return respondError(classification.code, classification.message, classification.httpStatus, traceId, {
            upstream_status: 502,
            upstream_code: upstreamCode || undefined,
            upstream_request_id: upstreamRequestId || undefined
          });
        }
        const narration = extractNarration(parsedResponse);
        if (!narration) {
          console.error("Workers AI returned no narration", { trace_id: traceId, upstream_request_id: upstreamRequestId, response_keys: Object.keys(parsedResponse || {}) });
          return respondError("AI_EMPTY_RESPONSE", "Workers AI returned no narration", 502, traceId, { upstream_request_id: upstreamRequestId || undefined });
        }
        return json({ narration, model, trace_id: traceId, upstream_request_id: upstreamRequestId || undefined }, 200, { "X-Worker-Revision": workerRevision });
      } finally {
        try {
          const settleResponse = await budget.fetch("https://budget/settle", { method: "POST", body: JSON.stringify({ id: reservationId, amount: settlementAmount }) });
          if (!settleResponse.ok) throw new Error(`settle returned ${settleResponse.status}`);
        } catch (error) {
          console.error("Daily budget settlement failed", { trace_id: traceId, error: String(error) });
        }
      }
    } catch (error) {
      console.error("Daily budget counter failure", { trace_id: traceId, error: String(error) });
      return respondError("BUDGET_UNAVAILABLE", "The daily budget counter is unavailable", 503, traceId);
    }
  }
};

export class DailyBudget {
  constructor(ctx, env) {
    this.ledger = new BudgetLedger(ctx.storage);
  }

  async fetch(request, init) {
    if (typeof request === "string") request = new Request(request, init);
    if (request.method !== "POST") return json({ status: "error" }, 405);
    let body;
    try {
      body = await request.json();
    } catch {
      return json({ status: "error" }, 400);
    }
    try {
      if (new URL(request.url).pathname === "/reserve") return json(await this.ledger.reserve(body.amount, body.limit));
      if (new URL(request.url).pathname === "/settle") return json(await this.ledger.settle(body.id, body.amount) || { ok: true });
      return json({ status: "error" }, 404);
    } catch {
      return json({ status: "error" }, 500);
    }
  }
}

function modelPrices(env, respondError, traceId) {
  const prices = { ...DEFAULT_MODEL_PRICES };
  if (!env.MODEL_PRICES_JSON) return prices;
  try {
    return { ...prices, ...JSON.parse(env.MODEL_PRICES_JSON) };
  } catch {
    return respondError("WORKER_CONFIGURATION_ERROR", "MODEL_PRICES_JSON is invalid", 500, traceId);
  }
}

function dailyLimit(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric > 0 ? Math.floor(numeric * 1_000_000) : 5_000_000;
}

async function callWorkersAi({ accountId, apiToken, model, system, user, maxTokens, responseFormat }) {
  return fetch(`https://api.cloudflare.com/client/v4/accounts/${encodeURIComponent(accountId)}/ai/run/${model}`, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json", Authorization: `Bearer ${apiToken}` },
    body: JSON.stringify({ messages: [{ role: "system", content: system }, { role: "user", content: user }], max_tokens: maxTokens, ...(responseFormat ? { response_format: responseFormat, temperature: 0 } : {}) })
  });
}

function getWorkerRevision(env) { return String(env.CF_VERSION_METADATA?.id || "unknown"); }

function classifyUpstreamFailure(status, code, message) {
  const normalizedMessage = String(message || "").toLowerCase();
  const numericCode = Number(code);
  if (status === 429 && (numericCode === 3036 || normalizedMessage.includes("quota") || normalizedMessage.includes("daily free allocation"))) return { code: "AI_QUOTA_EXCEEDED", message: "Workers AI quota exceeded", httpStatus: 429 };
  if (status === 429 && numericCode === 3040) return { code: "AI_CAPACITY_EXCEEDED", message: "Workers AI is temporarily out of capacity", httpStatus: 429 };
  if (["json mode", "json schema", "response_format", "couldn't be met"].some((term) => normalizedMessage.includes(term))) return { code: "AI_JSON_MODE_REJECTED", message: "Workers AI could not satisfy the structured JSON response format", httpStatus: 502 };
  if (status >= 400 && status < 500) return { code: "AI_REQUEST_REJECTED", message: "Workers AI rejected the request", httpStatus: status };
  return { code: "AI_UPSTREAM_ERROR", message: "Workers AI returned an upstream error", httpStatus: 502 };
}

function extractNarration(payload) {
  for (const value of [payload?.result?.response, payload?.result?.text, payload?.response]) {
    if (typeof value === "string" && value.trim()) return value.trim();
    if (value && typeof value === "object") return JSON.stringify(value);
  }
  return "";
}

function extractErrors(payload) { return payload && Array.isArray(payload.errors) ? payload.errors.slice(0, 5).map((error) => ({ code: error?.code ?? null, message: String(error?.message || "Workers AI error").slice(0, 500) })) : []; }
function firstErrorCode(errors) { return errors.length ? errors[0].code : ""; }
function firstErrorMessage(errors) { return errors.length ? errors[0].message : ""; }
function tryParseJson(value) { try { return JSON.parse(value); } catch { return null; } }
function asString(value) { return typeof value === "string" ? value : ""; }
function boundedInteger(value, fallback, minimum, maximum) { const numeric = Number(value); return Number.isInteger(numeric) ? Math.max(minimum, Math.min(maximum, numeric)) : fallback; }
function makeTraceId(request) { const supplied = request.headers.get("x-trace-id") || ""; return /^[A-Za-z0-9._:-]{1,128}$/.test(supplied) ? supplied : crypto.randomUUID(); }
function json(payload, status = 200, extraHeaders = {}) { return new Response(JSON.stringify(payload), { status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...extraHeaders } }); }
function errorJson(code, message, status, traceId, details = {}, extraHeaders = {}, workerRevision = "unknown") { return json({ status: "error", code, message, trace_id: traceId, ...details }, status, { "X-Trace-ID": traceId, "X-Worker-Revision": workerRevision, ...extraHeaders }); }
