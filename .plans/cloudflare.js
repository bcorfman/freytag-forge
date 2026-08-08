const MAX_BODY_BYTES = 256 * 1024;

export default {
  async fetch(request, env) {
    const traceId = makeTraceId(request);
    const workerRevision = getWorkerRevision(env);
    const respondError = (
      code,
      message,
      status,
      traceId,
      details = {},
      extraHeaders = {},
    ) => errorJson(
      code,
      message,
      status,
      traceId,
      details,
      extraHeaders,
      workerRevision,
    );

    if (request.method !== "POST") {
      return respondError(
        "METHOD_NOT_ALLOWED",
        "Use POST",
        405,
        traceId,
      );
    }

    if (env.DEMO_SHARED_TOKEN) {
      const authorization = request.headers.get("authorization") || "";
      if (authorization !== `Bearer ${env.DEMO_SHARED_TOKEN}`) {
        return respondError("UNAUTHORIZED", "Invalid token", 401, traceId);
      }
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
    const accountId = asString(env.CF_ACCOUNT_ID).trim();
    const apiToken = asString(env.CF_API_TOKEN).trim();
    const model = (
      asString(env.CF_AI_MODEL).trim() ||
      "@cf/meta/llama-3.1-8b-instruct-fast"
    );

    if (!accountId || !apiToken) {
      return respondError(
        "WORKER_CONFIGURATION_ERROR",
        "Workers AI credentials are not configured",
        500,
        traceId,
      );
    }

    if (!system || !user) {
      return respondError(
        "INVALID_REQUEST",
        "Both system and user prompts are required",
        400,
        traceId,
      );
    }

    const aiUrl =
      `https://api.cloudflare.com/client/v4/accounts/` +
      `${encodeURIComponent(accountId)}/ai/run/${model}`;

    let aiResponse;

    try {
      aiResponse = await fetch(aiUrl, {
        method: "POST",
        headers: {
          "Accept": "application/json",
          "Content-Type": "application/json",
          "Authorization": `Bearer ${apiToken}`,
        },
        body: JSON.stringify({
            messages: [
            { role: "system", content: system },
            { role: "user", content: user },
          ],
          max_tokens: maxTokens,
          ...(body?.response_format ? { response_format: body.response_format } : {}),
        }),
      });
    } catch (error) {
      console.error("Workers AI network failure", {
        trace_id: traceId,
        error: String(error),
      });

      return respondError(
        "AI_NETWORK_ERROR",
        "Workers AI could not be reached",
        502,
        traceId,
      );
    }

    const upstreamRequestId =
      aiResponse.headers.get("cf-ray") ||
      aiResponse.headers.get("x-request-id") ||
      "";

    const rawResponse = await aiResponse.text();
    const parsedResponse = tryParseJson(rawResponse);

    if (!aiResponse.ok) {
      const upstreamErrors = extractErrors(parsedResponse);
      const upstreamCode = firstErrorCode(upstreamErrors);
      const upstreamMessage = firstErrorMessage(upstreamErrors);

      const classification = classifyUpstreamFailure(
        aiResponse.status,
        upstreamCode,
        upstreamMessage,
      );

      console.error("Workers AI upstream failure", {
        trace_id: traceId,
        upstream_request_id: upstreamRequestId,
        upstream_status: aiResponse.status,
        upstream_code: upstreamCode,
        upstream_message: upstreamMessage,
      });

      const headers = {};
      const retryAfter = aiResponse.headers.get("retry-after");
      if (retryAfter) headers["Retry-After"] = retryAfter;

      return respondError(
        classification.code,
        classification.message,
        classification.httpStatus,
        traceId,
        {
          upstream_status: aiResponse.status,
          upstream_code: upstreamCode || undefined,
          upstream_request_id: upstreamRequestId || undefined,
        },
        headers,
      );
    }

    if (!parsedResponse || parsedResponse.success === false) {
      const upstreamErrors = extractErrors(parsedResponse);
      const upstreamCode = firstErrorCode(upstreamErrors);
      const upstreamMessage = firstErrorMessage(upstreamErrors);
      const classification = classifyUpstreamFailure(
        502,
        upstreamCode,
        upstreamMessage,
      );

      console.error("Workers AI returned an unsuccessful envelope", {
        trace_id: traceId,
        upstream_request_id: upstreamRequestId,
        upstream_code: upstreamCode,
        upstream_message: upstreamMessage,
      });

      return respondError(
        classification.code,
        classification.message,
        classification.httpStatus,
        traceId,
        {
          upstream_status: 502,
          upstream_code: upstreamCode || undefined,
          upstream_request_id: upstreamRequestId || undefined,
        },
      );
    }

    const narration = extractNarration(parsedResponse);

    if (!narration) {
      console.error("Workers AI returned no narration", {
        trace_id: traceId,
        upstream_request_id: upstreamRequestId,
        response_keys: Object.keys(parsedResponse || {}),
      });

      return respondError(
        "AI_EMPTY_RESPONSE",
        "Workers AI returned no narration",
        502,
        traceId,
        {
          upstream_request_id: upstreamRequestId || undefined,
        },
      );
    }

    return json(
      {
        narration,
        model,
        trace_id: traceId,
        upstream_request_id: upstreamRequestId || undefined,
      },
      200,
      { "X-Worker-Revision": workerRevision },
    );
  },
};

function getWorkerRevision(env) {
  return String(env.CF_VERSION_METADATA?.id || "unknown");
}

function classifyUpstreamFailure(status, code, message) {
  const normalizedMessage = String(message || "").toLowerCase();
  const numericCode = Number(code);

  if (
    status === 429 &&
    (numericCode === 3036 ||
      normalizedMessage.includes("quota") ||
      normalizedMessage.includes("daily free allocation"))
  ) {
    return {
      code: "AI_QUOTA_EXCEEDED",
      message: "Workers AI quota exceeded",
      httpStatus: 429,
    };
  }

  if (status === 429 && numericCode === 3040) {
    return {
      code: "AI_CAPACITY_EXCEEDED",
      message: "Workers AI is temporarily out of capacity",
      httpStatus: 429,
    };
  }

  if (
    normalizedMessage.includes("json mode") ||
    normalizedMessage.includes("json schema") ||
    normalizedMessage.includes("response_format") ||
    normalizedMessage.includes("couldn't be met")
  ) {
    return {
      code: "AI_JSON_MODE_REJECTED",
      message: "Workers AI could not satisfy the structured JSON response format",
      httpStatus: 502,
    };
  }

  if (status >= 400 && status < 500) {
    return {
      code: "AI_REQUEST_REJECTED",
      message: "Workers AI rejected the request",
      httpStatus: status,
    };
  }

  return {
    code: "AI_UPSTREAM_ERROR",
    message: "Workers AI returned an upstream error",
    // 5xx from the AI API is represented as a gateway failure by this Worker.
    httpStatus: 502,
  };
}

function extractNarration(payload) {
  const candidates = [
    payload?.result?.response,
    payload?.result?.text,
    payload?.response,
  ];

  for (const value of candidates) {
    if (typeof value === "string" && value.trim()) return value.trim();
    if (value && typeof value === "object") return JSON.stringify(value);
  }
  return "";
}

function extractErrors(payload) {
  if (!payload || !Array.isArray(payload.errors)) return [];

  return payload.errors.slice(0, 5).map((error) => ({
    code: error?.code ?? null,
    message: String(error?.message || "Workers AI error").slice(0, 500),
  }));
}

function firstErrorCode(errors) {
  return errors.length ? errors[0].code : "";
}

function firstErrorMessage(errors) {
  return errors.length ? errors[0].message : "";
}

function tryParseJson(value) {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function asString(value) {
  return typeof value === "string" ? value : "";
}

function boundedInteger(value, fallback, minimum, maximum) {
  const numeric = Number(value);
  if (!Number.isInteger(numeric)) return fallback;
  return Math.max(minimum, Math.min(maximum, numeric));
}

function makeTraceId(request) {
  const supplied = request.headers.get("x-trace-id") || "";
  if (/^[A-Za-z0-9._:-]{1,128}$/.test(supplied)) return supplied;
  return crypto.randomUUID();
}

function json(payload, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      ...extraHeaders,
    },
  });
}

function errorJson(
  code,
  message,
  status,
  traceId,
  details = {},
  extraHeaders = {},
  workerRevision = "unknown",
) {
  return json(
    {
      status: "error",
      code,
      message,
      trace_id: traceId,
      ...details,
    },
    status,
    {
      "X-Trace-ID": traceId,
      "X-Worker-Revision": workerRevision,
      ...extraHeaders,
    },
  );
}
