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
const GATE_INPUT = "Lead the captives through the emergency gate.";
const TARGET_3A_REVEAL_ID = "k_sl_3a_c_r1";

async function requireStaging(baseUrl, category) {
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/v1/version`);
  const version = await response.json();
  if (version.channel !== "staging") {
    throw new Error(`${category} refuses to run unless the hosted API is staging; got channel ${String(version.channel)}.`);
  }
  return version;
}

function rejectionPayload(error) {
  return error?.payload && typeof error.payload === "object" ? error.payload : null;
}

async function walkToScene(page, { targetScene, category }) {
  const version = await requireStaging(process.env.E2E_API_BASE_URL, category);
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

  for (let index = 0; index < MAX_WALK_TURNS && sceneId !== targetScene; index += 1) {
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
        throw new Error(`${category} did not reach scene ${targetScene}: 4 consecutive walk turns were rejected at turn ${index + 1}.`);
      }
    }
  }

  if (sceneId !== targetScene) {
    throw new Error(`${category} did not reach scene ${targetScene} after ${MAX_WALK_TURNS} walk turns.`);
  }

  return { identity, sceneId, walkTurns };
}

test("walks to 2C and records the Project Echelon copy matcher @reference-copy", async ({ page }) => {
  test.skip(!process.env.E2E_API_BASE_URL, "requires E2E_API_BASE_URL; hosted reference-copy check is skipped without it");
  test.setTimeout(20 * 60_000);

  const { identity, walkTurns } = await walkToScene(page, {
    targetScene: "2C",
    category: "@reference-copy",
  });

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

test("walks to 3A and records the emergency-gate evidence matcher @reference-gate", async ({ page }) => {
  test.skip(!process.env.E2E_API_BASE_URL, "requires E2E_API_BASE_URL; hosted reference-gate check is skipped without it");
  test.setTimeout(30 * 60_000);

  const { identity, sceneId, walkTurns } = await walkToScene(page, {
    targetScene: "3A",
    category: "@reference-gate",
  });
  expect(sceneId, "the scripted spine must reach scene 3A before the gate probe").toBe("3A");

  for (let index = 0; index < 3; index += 1) {
    const input = promptFor("3A", index);
    try {
      const payload = await submitTurn(page, input);
      const sceneOut = payload.state?.scene_id ?? sceneId;
      walkTurns.push({ input, scene_in: "3A", scene_out: sceneOut, payload, rejected: false });
      await resolveWarningIfPresent(page);
      if (sceneOut !== "3A") {
        throw new Error(`@reference-gate left scene 3A after spine prompt ${index + 1}; got ${sceneOut}.`);
      }
    } catch (error) {
      const payload = rejectionPayload(error);
      if (!payload || Number(error?.status) < 400) throw error;
      const sceneOut = payload.state?.scene_id ?? sceneId;
      walkTurns.push({
        input,
        scene_in: "3A",
        scene_out: sceneOut,
        payload,
        rejected: true,
        status: error.status,
      });
      await resolveWarningIfPresent(page);
      if (sceneOut !== "3A") {
        throw new Error(`@reference-gate left scene 3A after rejected spine prompt ${index + 1}; got ${sceneOut}.`);
      }
    }
  }

  let gatePayload;
  try {
    const payload = await submitTurn(page, GATE_INPUT);
    gatePayload = { ...payload, input: GATE_INPUT, scene_in: "3A" };
    await resolveWarningIfPresent(page);
  } catch (error) {
    const payload = rejectionPayload(error);
    if (!payload) throw error;
    gatePayload = {
      ...payload,
      input: GATE_INPUT,
      scene_in: "3A",
      rejected: true,
      status: error.status,
    };
    await resolveWarningIfPresent(page);
  }

  const summary = summarizeReferenceCopy({
    identity,
    walkTurns,
    copyPayload: gatePayload,
    targetRevealId: TARGET_3A_REVEAL_ID,
    sceneIn: "3A",
  });
  await writeCategoryReport("reference-gate", summary);
  console.log(`@reference-gate path=${summary.path}`);
  expect(sceneId, "the reference-gate walk must reach scene 3A").toBe("3A");
  expect(summary.earned_target, "the gate turn must commit k_sl_3a_c_r1").toBe(true);
});
