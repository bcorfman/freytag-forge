export async function installApiToken(page, { apiBaseUrl, token }) {
  if (!token) return false;
  if (!apiBaseUrl) throw new Error("E2E API base URL is required when a test token is set.");

  const base = apiBaseUrl.replace(/\/+$/, "");
  await page.route(`${base}/api/v1/**`, (route) =>
    route.fallback({
      headers: { ...route.request().headers(), "x-freytag-test-clock-token": token },
    }),
  );
  return true;
}
