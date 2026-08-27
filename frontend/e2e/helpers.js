import { expect } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const TURN_TIMEOUT_MS = Number.parseInt(process.env.E2E_TURN_TIMEOUT_MS || "30000", 10);

function isTurnRequest(candidate) {
  return candidate.method() === "POST" && candidate.url().endsWith("/api/v1/turn");
}

function waitForTurnOutcome(page) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      cleanup();
      reject(new Error(`Turn API did not produce a response within ${TURN_TIMEOUT_MS}ms.`));
    }, TURN_TIMEOUT_MS);
    const cleanup = () => {
      clearTimeout(timeout);
      page.off("response", onResponse);
      page.off("requestfailed", onFailure);
    };
    const onResponse = (response) => {
      if (!isTurnRequest(response.request())) return;
      cleanup();
      resolve(response);
    };
    const onFailure = (request) => {
      if (!isTurnRequest(request)) return;
      cleanup();
      reject(
        new Error(
          `Turn API request failed for ${request.url()}: ${request.failure()?.errorText || "unknown browser network failure"}`,
        ),
      );
    };
    page.on("response", onResponse);
    page.on("requestfailed", onFailure);
  });
}

export async function startSceneSession(page) {
  await page.goto("/");
  await page.getByRole("button", { name: "New Session" }).click();
  await expect(page.locator("#status-line")).toContainText("Scene 1A");
  await expect(page.locator("#transcript")).not.toBeEmpty();
}

export async function submitTurn(page, action) {
  const consoleErrors = [];
  const captureConsoleError = (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  };
  page.on("console", captureConsoleError);
  await expect(page.locator("#command-input")).toBeEnabled({ timeout: TURN_TIMEOUT_MS });
  await page.locator("#command-input").fill(action);
  const response = waitForTurnOutcome(page);
  await page.getByRole("button", { name: "Send" }).click({ timeout: TURN_TIMEOUT_MS });
  let apiResponse;
  try {
    apiResponse = await response;
  } catch (error) {
    const status = await page.locator("#status-line").textContent();
    const diagnostics = consoleErrors.length ? ` Browser errors: ${consoleErrors.join(" | ")}` : "";
    throw new Error(
      `${error instanceof Error ? error.message : String(error)} UI status: ${status || "(empty)"}.${diagnostics}`,
    );
  } finally {
    page.off("console", captureConsoleError);
  }
  const payload = await apiResponse.json().catch(() => ({}));
  if (!apiResponse.ok()) {
    const detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload);
    throw new Error(`Turn API returned HTTP ${apiResponse.status()}: ${detail}`);
  }
  await expect(page.locator("#command-input")).toBeEnabled({ timeout: TURN_TIMEOUT_MS });
  return payload;
}

export async function resolveWarningIfPresent(page) {
  const warning = page.locator("#game-break-panel");
  if (!(await warning.isVisible())) return false;
  await page.getByRole("button", { name: "Return to scene" }).click();
  await expect(warning).toBeHidden();
  return true;
}

export async function writeCategoryReport(category, evidence) {
  const root = resolve(import.meta.dirname, "../..");
  const json = resolve(root, `artifacts/e2e-${category}.json`);
  const markdown = resolve(root, `artifacts/e2e-${category}.md`);
  await mkdir(dirname(json), { recursive: true });
  await writeFile(json, `${JSON.stringify(evidence, null, 2)}\n`);
  await writeFile(markdown, `# ${category} E2E evaluation\n\n\`\`\`json\n${JSON.stringify(evidence, null, 2)}\n\`\`\`\n`);
}
