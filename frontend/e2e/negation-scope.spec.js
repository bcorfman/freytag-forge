import { expect, test } from "@playwright/test";

import {
  resolveWarningIfPresent,
  startSceneSession,
  submitTurn,
  writeCategoryReport,
} from "./helpers.js";
import { summarizeNegationScope } from "./negation-scope.js";

const INPUTS = [
  { input: "Do not open the drawer.", expect: "blocked" },
  { input: "Open the drawer, never mind.", expect: "blocked" },
  { input: "Open the drawer, but do not take anything yet.", expect: "earned" },
];

async function requireStaging(baseUrl) {
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/v1/version`);
  const version = await response.json();
  if (version.channel !== "staging") {
    throw new Error(`@negation-scope refuses to run unless the hosted API is staging; got channel ${String(version.channel)}.`);
  }
  return version;
}

function rejectionPayload(error) {
  return error?.payload && typeof error.payload === "object" ? error.payload : null;
}

test("keeps leading and retracting negations from earning the drawer reveal @negation-scope", async ({ page }) => {
  test.skip(!process.env.E2E_API_BASE_URL, "requires E2E_API_BASE_URL; hosted negation-scope check is skipped without it");
  test.setTimeout(10 * 60_000);

  const version = await requireStaging(process.env.E2E_API_BASE_URL);
  const identity = {
    sha: version.sha ?? null,
    runtime: version.runtime ?? null,
    channel: version.channel ?? null,
  };

  await startSceneSession(page);
  const turns = [];

  for (const { input, expect: expected } of INPUTS) {
    try {
      const payload = await submitTurn(page, input);
      turns.push({ input, expect: expected, payload: { ...payload, input, scene_in: "1A" } });
    } catch (error) {
      const payload = rejectionPayload(error);
      const status = Number(error?.status);
      if (!payload || status < 400 || status >= 500) throw error;
      turns.push({
        input,
        expect: expected,
        payload: { ...payload, input, scene_in: "1A", rejected: true, status },
      });
    }
    await resolveWarningIfPresent(page);
  }

  const summary = summarizeNegationScope({ identity, turns });
  await writeCategoryReport("negation-scope", summary);
  console.log(`@negation-scope all_ok=${summary.all_ok} path3=${summary.turns[2]?.path}`);
  for (const [index, turn] of summary.turns.entries()) {
    expect(turn.ok, `negation-scope turn ${index + 1} should satisfy its ${turn.expect} expectation`).toBe(true);
  }
});
