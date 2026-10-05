import { test } from "@playwright/test";
import { readdir } from "node:fs/promises";
import { resolve } from "node:path";
import { loadAffordanceMap, firstStepAffordances, laterAffordances, exploreInput } from "./affordances.js";
import { askPlayer, analyseRun, aggregate, aggregateByScene, formatMarkdown, sceneIdsForRun, turnLog, turnRecord } from "./blind-player.js";
import { startSceneSession, submitTurn, resolveWarningIfPresent, writeCategoryReport } from "./helpers.js";
import { loadPackagePacing } from "./package-clock.js";
import { walkScenes } from "./scene-walk.js";
import { replicatePlan } from "./merge-blind-player.js";

const repoRoot = resolve(import.meta.dirname, "../..");
const storyId = "continuity_initiative";

async function storyPackageDir() {
  for (const entry of await readdir(resolve(repoRoot, "data/stories"), { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const candidate = resolve(repoRoot, "data/stories", entry.name);
    try {
      if (loadAffordanceMap(candidate).story_id === storyId) return candidate;
    } catch {
      // Directory is not a story package.
    }
  }
  throw new Error(`Could not find story package with story_id ${storyId}.`);
}

async function requireStaging(baseUrl) {
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/v1/version`);
  const version = await response.json();
  if (version.channel !== "staging") {
    throw new Error(`@blind-player refuses to run unless the hosted API is staging; got channel ${String(version.channel)}.`);
  }
}

async function playScene({ page, map, pacing, sceneId, openingText, totalCounter }) {
  const sceneEntry = map.scenes.find((scene) => scene.scene_id === sceneId);
  const nextSceneEntry = map.scenes.find((scene) => scene.scene_id === pacing.sceneOrder[pacing.sceneOrder.indexOf(sceneId) + 1]);
  const ceiling = Math.min(20, pacing.scenePoint(sceneId, "handoff").target_turn + 2);
  const firstStep = firstStepAffordances(map, sceneId);
  const later = laterAffordances(map, sceneId);
  const turns = [];
  const counter = { calls: 0 };
  let consecutiveRejections = 0;
  let stoppedOnRejections = false;
  for (let turn = 1; turn <= ceiling; turn += 1) {
    const transcript = (await page.locator("#transcript").textContent()) || "";
    const status = (await page.locator("#status-line").textContent()) || "";
    const input = await askPlayer({ transcript, status, counter, totalCounter, totalCap: 200 });
    let payload;
    try {
      payload = await submitTurn(page, input);
    } catch (error) {
      const rejection = String(error?.message || "").match(/HTTP 409:\s*([\s\S]*)$/);
      if (!rejection) throw error;
      turns.push({ turn, input, rejected: true, rejection: rejection[1], text: "", state: null, grounding_ids: [], delivery: {}, semantic_match: null, prompt: null });
      consecutiveRejections += 1;
      if (consecutiveRejections >= 3) {
        stoppedOnRejections = true;
        break;
      }
      continue;
    }
    await resolveWarningIfPresent(page);
    consecutiveRejections = 0;
    const text = (payload.segments || [])
      .filter((segment) => ["narration", "action", "dialogue", "speech"].includes(segment.kind))
      .map((segment) => segment.text).filter(Boolean).join(" ").trim();
    turns.push(turnRecord({ turn, input, payload, text }));
    if (payload.state?.scene_id !== sceneId) break;
  }
  return {
    replicate: undefined,
    scene: sceneId,
    opening_text: openingText,
    commands: turns.map((turn) => turn.input),
    prompts: turns.filter((turn) => typeof turn.prompt === "string" && turn.prompt.trim()).map((turn) => ({ turn: turn.turn, prompt: turn.prompt })),
    turns: turnLog(turns),
    turn_count: turns.length,
    ...analyseRun({ sceneEntry, nextSceneEntry, turns, firstStep, later, openingText, stopped_on_rejections: stoppedOnRejections, sceneMapSources: sceneEntry.gates?.flatMap((gate) => gate.sources || []) || [] }),
  };
}

test("a player who only reads the screen can leave the scene @blind-player", async ({ page }) => {
  test.skip(!process.env.E2E_API_BASE_URL || !process.env.OPENAI_API_KEY, "requires E2E_API_BASE_URL and OPENAI_API_KEY");
  const baseUrl = process.env.E2E_API_BASE_URL;
  await requireStaging(baseUrl);
  const requestedScene = process.env.E2E_BLIND_SCENE || "1A";
  const allMode = requestedScene === "all";
  const { indices: replicateIndices, category } = replicatePlan(process.env);
  test.setTimeout(allMode ? 60 * 60_000 : 20 * 60_000);
  const map = loadAffordanceMap(await storyPackageDir());
  const pacing = loadPackagePacing({ storyId });
  const sceneIds = allMode ? sceneIdsForRun(pacing.sceneOrder, process.env.E2E_BLIND_SCENES) : [requestedScene];
  for (const sceneId of sceneIds) {
    if (!map.scenes.some((scene) => scene.scene_id === sceneId)) throw new Error(`Affordance map has no scene ${sceneId}.`);
  }
  const runs = [];
  for (const replicate of replicateIndices) {
    let openingText = "";
    if (!allMode && requestedScene !== "1A") {
      const targetIndex = pacing.sceneOrder.indexOf(requestedScene);
      await walkScenes({
        page,
        pacing,
        sceneIds: pacing.sceneOrder.slice(0, targetIndex + 1),
        maxTurns: 20 * (targetIndex + 1),
        exploreFor: (id) => exploreInput(map.scenes.find((scene) => scene.scene_id === id)),
        startSession: startSceneSession,
        submitTurn,
        resolveWarning: resolveWarningIfPresent,
        onOpening: ({ scene_id, text }) => { if (scene_id === requestedScene) openingText = text; },
      });
    } else {
      await startSceneSession(page);
      openingText = (await page.locator(".entry-output").first().textContent())?.trim() || "";
    }
    const totalCounter = { calls: 0 };
    const sceneRuns = [];
    let stoppedReason = null;
    for (const sceneId of sceneIds) {
      const run = await playScene({ page, map, pacing, sceneId, openingText, totalCounter });
      run.replicate = replicate;
      sceneRuns.push(run);
      if (run.stopped_on_rejections) {
        stoppedReason = `scene ${sceneId} rejected three times in a row`;
        break;
      }
      if (!run.transition_fired) {
        stoppedReason = `scene ${sceneId} had no transition by its ceiling`;
        break;
      }
      const next = sceneIds[sceneIds.indexOf(sceneId) + 1];
      if (!next) {
        stoppedReason = "last scene finished";
        break;
      }
      openingText = run.turns.find((turn) => turn.turn === run.transition_turn)?.text || "";
    }
    if (allMode) runs.push({ replicate, scenes: sceneRuns, stopped_reason: stoppedReason });
    else runs.push(sceneRuns[0]);
  }
  const report = allMode
    ? { story_id: map.story_id, scene: "all", replicates: runs, by_scene: aggregateByScene(runs) }
    : { story_id: map.story_id, scene: requestedScene, replicates: runs, aggregate: aggregate(runs) };
  await writeCategoryReport(category, { ...report, markdown: formatMarkdown(report) });
});
