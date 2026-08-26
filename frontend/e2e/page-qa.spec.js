import { expect, test } from "@playwright/test";

const versionRoute = "**/api/v1/version";
const sessionRoute = "**/api/v1/session";
const turnRoute = "**/api/v1/turn";

test("QA: Story Feed initial, loaded, error, and responsive states @page-qa", async ({ page }) => {
  let releaseVersion;
  const versionReady = new Promise((resolve) => {
    releaseVersion = resolve;
  });
  let turnRequests = 0;

  await page.route(versionRoute, async (route) => {
    await versionReady;
    await route.fulfill({ json: { api: "v1", runtime: "scene-v1", channel: "production" } });
  });
  await page.route(sessionRoute, (route) =>
    route.fulfill({
      json: {
        session_id: "local-page-qa",
        state: { scene_id: "1A", phase: "setup" },
        opening: { text: "A local QA opening." },
      },
    }),
  );
  await page.route(turnRoute, async (route) => {
    turnRequests += 1;
    const body = route.request().postDataJSON();
    await route.fulfill({
      json: {
        state: { scene_id: "1A", phase: "setup" },
        segments: [{ kind: "narration", text: `Accepted: ${body.player_input}` }],
      },
    });
  });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/", { waitUntil: "commit" });
  await expect(page.locator("#status-line")).toHaveText("Creating session...");
  await expect(page.locator("#command-input")).toBeDisabled();
  await page.screenshot({ path: "../artifacts/e2e-page-qa-loading-1440.png", fullPage: true });

  releaseVersion();
  await expect(page.locator("#status-line")).toContainText("Scene 1A");
  await expect(page.locator("#command-input")).toBeEnabled();
  await expect(page.locator("#transcript")).toContainText("A local QA opening.");

  await page.locator("#command-input").fill("I inspect the evidence.");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.locator("#transcript")).toContainText("Accepted: I inspect the evidence.");

  await page.locator("#command-input").fill("   ");
  await page.getByRole("button", { name: "Send" }).click();
  expect(turnRequests).toBe(1);

  const edgeInput = "x".repeat(2048);
  await page.locator("#command-input").fill(edgeInput);
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.locator("#transcript")).toContainText(`Accepted: ${edgeInput}`);
  expect(turnRequests).toBe(2);
  await page.screenshot({ path: "../artifacts/e2e-page-qa-loaded-1440.png", fullPage: true });

  await page.setViewportSize({ width: 375, height: 812 });
  const inputBox = await page.locator("#command-input").boundingBox();
  const sendBox = await page.getByRole("button", { name: "Send" }).boundingBox();
  expect(inputBox).not.toBeNull();
  expect(sendBox).not.toBeNull();
  expect(sendBox.y).toBeGreaterThan(inputBox.y);
  await page.screenshot({ path: "../artifacts/e2e-page-qa-loaded-375.png", fullPage: true });

  await page.unroute(versionRoute);
  await page.route(versionRoute, (route) => route.fulfill({ status: 503, json: { detail: "Service unavailable." } }));
  await page.reload();
  await expect(page.locator("#status-line")).toHaveText("Service unavailable.");
  await expect(page.locator("#command-input")).toBeEnabled();
  await expect(page.getByRole("button", { name: "Send" })).toBeDisabled();
  await page.screenshot({ path: "../artifacts/e2e-page-qa-error-375.png", fullPage: true });
});
