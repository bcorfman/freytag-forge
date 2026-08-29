export function isTurnRequest(url, method) {
  if (method !== "POST") return false;

  let parsedUrl;
  try {
    parsedUrl = new URL(url, "http://playwright.invalid");
  } catch {
    return false;
  }

  return parsedUrl.hostname !== "api.openai.com" && parsedUrl.pathname === "/api/v1/turn";
}

export function applyTestClock(rawBody, { deltaSeconds, token } = {}) {
  if (!Number.isInteger(deltaSeconds)) {
    throw new Error(`Cannot apply test clock: deltaSeconds must be an integer; received ${String(deltaSeconds)}.`);
  }

  let body;
  try {
    body = JSON.parse(rawBody);
  } catch (error) {
    throw new Error(
      `Cannot apply test clock: request body is not valid JSON (${error instanceof Error ? error.message : String(error)}).`,
    );
  }

  if (body === null || typeof body !== "object" || Array.isArray(body)) {
    throw new Error("Cannot apply test clock: request body must be a JSON object.");
  }

  body.test_clock_seconds = deltaSeconds;
  if (typeof token === "string" && token.length > 0) {
    body.test_clock_token = token;
  } else {
    delete body.test_clock_token;
  }

  return JSON.stringify(body);
}
