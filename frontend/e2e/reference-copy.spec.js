import { expect, test } from "@playwright/test";

import { promptFor } from "./canon-journey.js";
import {
  resolveWarningIfPresent,
  startSceneSession,
  submitTurn,
  writeCategoryReport,
} from "./helpers.js";
import { summarizeReferenceCopy } from "./reference-copy.js";

const MAX_WALK_TURNS = 90;
const COPY_INPUT = "Copy the encrypted Project Echelon file to my laptop.";

async function requireStaging(baseUrl) {
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/v1/version`);
  const version = await response.json();
  if (version.channel !== "staging") {
    throw new Error(`@reference-copy refuses to run unless the hosted API is staging; got channel ${String(version.channel)}.`);
  }
  return version;
}

function rejectionPayload(error) {
  return error?.payload && typeof error.payload === "object" ? error.payload : null;
}

test("walks to 2C and records the Project Echelon copy matcher @reference-copy", async ({ page }) => {
  test.skip(!process.env.E2E_API_BASE_URL, "requires E2E_API_BASE_URL; hosted reference-copy check is skipped without it");
  test.setTimeout(20 * 60_000);

  const version = await requireStaging(process.env.E2E_API_BASE_URL);
  const identity = {
    sha: version.sha ?? null,
    runtime: version.runtime ?? null,
    channel: version.channel ?? null,
  };

  await startSceneSession(page);
  const walkTurns = [];
  const promptsUsed = new Map();
  let sceneId = "1A";
  let consecutiveRejections = 0;

  for (let index = 0; index < MAX_WALK_TURNS && sceneId !== "2C"; index += 1) {
    const sceneIn = sceneId;
    const used = promptsUsed.get(sceneId) || 0;
    const input = promptFor(sceneId, used);
    promptsUsed.set(sceneId, used + 1);
    try {
      const payload = await submitTurn(page, input);
      const sceneOut = payload.state?.scene_id ?? sceneId;
      walkTurns.push({ input, scene_in: sceneIn, scene_out: sceneOut, payload, rejected: false });
      await resolveWarningIfPresent(page);
      consecutiveRejections = 0;
      sceneId = sceneOut;
    } catch (error) {
      const payload = rejectionPayload(error);
      if (!payload || Number(error?.status) < 400) throw error;
      const sceneOut = payload.state?.scene_id ?? sceneId;
      walkTurns.push({
        input,
        scene_in: sceneIn,
        scene_out: sceneOut,
        payload,
        rejected: true,
        status: error.status,
      });
      await resolveWarningIfPresent(page);
      sceneId = sceneOut;
      consecutiveRejections += 1;
      if (consecutiveRejections >= 4) {
        throw new Error(`@reference-copy did not reach scene 2C: 4 consecutive walk turns were rejected at turn ${index + 1}.`);
      }
    }
  }

  if (sceneId !== "2C") {
    throw new Error(`@reference-copy did not reach scene 2C after ${MAX_WALK_TURNS} walk turns.`);
  }

  let copyPayload;
  try {
    const payload = await submitTurn(page, COPY_INPUT);
    copyPayload = { ...payload, input: COPY_INPUT, scene_in: "2C" };
  } catch (error) {
    const payload = rejectionPayload(error);
    if (!payload) throw error;
    copyPayload = {
      ...payload,
      input: COPY_INPUT,
      scene_in: "2C",
      rejected: true,
      status: error.status,
    };
  }

  const summary = summarizeReferenceCopy({ identity, walkTurns, copyPayload });
  await writeCategoryReport("reference-copy", summary);
  console.log(`@reference-copy path=${summary.path}`);
  expect(summary.reached_2c).toBe(true);
  expect(summary.earned_c_r1, "the first 2C Echelon copy turn must commit k_sl_2c_c_r1").toBe(true);
});
