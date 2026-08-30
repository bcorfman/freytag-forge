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
