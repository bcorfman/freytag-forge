import { expect } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

import { isTurnRequest } from "./package-clock-request.js";
import { createPackageClockController } from "./package-clock-controller.js";

const TURN_TIMEOUT_MS = Number.parseInt(process.env.E2E_TURN_TIMEOUT_MS || "30000", 10);
const packageClockControllers = new WeakMap();

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
      const request = response.request();
      if (!isTurnRequest(request.url(), request.method())) return;
      cleanup();
      resolve(response);
    };
    const onFailure = (request) => {
      if (!isTurnRequest(request.url(), request.method())) return;
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

function sessionResponseFor(page, controller) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const cleanup = () => page.off("response", onResponse);
    const finish = (callback, value) => {
      if (settled) return;
      settled = true;
      cleanup();
      callback(value);
    };
    const onResponse = async (response) => {
      const request = response.request();
      let pathname;
      try {
        pathname = new URL(response.url()).pathname;
      } catch {
        return;
      }
      if (request.method() !== "POST" || pathname !== "/api/v1/session") return;

      try {
        const payload = await response.json();
        if (!response.ok()) {
          finish(reject, new Error(`Package clock could not observe session state: HTTP ${response.status()}.`));
          return;
        }
        controller.observeState(payload.state);
        finish(resolve, payload);
      } catch (error) {
        finish(
          reject,
          new Error(
            `Package clock could not observe session state: ${error instanceof Error ? error.message : String(error)}.`,
          ),
        );
      }
    };
    page.on("response", onResponse);
  });
}

export async function installPackageClock(page, { controller } = {}) {
  const packageClockController = controller ?? createPackageClockController();
  packageClockControllers.set(page, packageClockController);
  return packageClockController;
}

export async function startSceneSession(page) {
  await page.goto("/");
  const controller = packageClockControllers.get(page);
  const sessionState = controller ? sessionResponseFor(page, controller) : null;
  await page.getByRole("button", { name: "New Session" }).click();
  if (sessionState) await sessionState;
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
  const controller = packageClockControllers.get(page);
  if (controller) {
    try {
      controller.observeTurnResponse(payload);
    } catch (error) {
      throw new Error(
        `Package clock could not observe turn response: ${error instanceof Error ? error.message : String(error)}.`,
      );
    }
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
