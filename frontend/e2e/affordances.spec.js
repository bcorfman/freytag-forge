import { test } from "@playwright/test";
import { readdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

import { installPackageClock, startSceneSession, submitTurn, resolveWarningIfPresent, writeCategoryReport } from "./helpers.js";
import { formatMarkdown, loadAffordanceMap, measureScene, exploreInput } from "./affordances.js";
import { loadPackagePacing } from "./package-clock.js";
import { walkScenes } from "./scene-walk.js";

const repoRoot = resolve(import.meta.dirname, "../..");
const storyId = "continuity_initiative";

async function storyPackageDir() {
  const root = resolve(repoRoot, "data/stories");
  for (const entry of await readdir(root, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const candidate = resolve(root, entry.name);
    try {
      const map = loadAffordanceMap(candidate);
      if (map.story_id === storyId) return candidate;
    } catch {
      // A non-story directory is not a package candidate.
    }
  }
  throw new Error(`Could not find story package with story_id ${storyId}.`);
}

async function requireStaging(baseUrl) {
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/v1/version`);
  const version = await response.json();
  if (version.channel !== "staging") {
    throw new Error(`@affordances refuses to run unless the hosted API is staging; got channel ${String(version.channel)}.`);
  }
}

test("shows the player what each scene needs @affordances", async ({ page }) => {
  test.skip(!process.env.E2E_API_BASE_URL, "requires E2E_API_BASE_URL; hosted affordance checks are skipped without it");
  const baseUrl = process.env.E2E_API_BASE_URL;
  await requireStaging(baseUrl);
  const sceneIds = (process.env.E2E_AFFORDANCE_SCENES || "1A").split(",").map((id) => id.trim()).filter(Boolean);
  const replicates = Number.parseInt(process.env.E2E_AFFORDANCE_REPLICATES || "1", 10);
  if (replicates > 3) throw new Error("@affordances refuses more than 3 replicates because the endpoint is billed.");
  if (replicates < 1) throw new Error("E2E_AFFORDANCE_REPLICATES must be at least 1.");
  test.setTimeout(20 * 60_000);

  const map = loadAffordanceMap(await storyPackageDir());
  const pacing = loadPackagePacing({ storyId });
  const mapScenes = new Map(map.scenes.map((scene) => [scene.scene_id, scene]));
  for (const sceneId of sceneIds) {
    if (!mapScenes.has(sceneId)) throw new Error(`Affordance map has no scene ${sceneId}.`);
  }
  const firstScene = map.scenes[0]?.scene_id;
  const needsClock = sceneIds.some((sceneId) => pacing.sceneOrder.indexOf(sceneId) > pacing.sceneOrder.indexOf(firstScene));
  if (needsClock && !process.env.E2E_PACKAGE_CLOCK) throw new Error("@affordances needs E2E_PACKAGE_CLOCK for scenes after the first scene.");

  const scenes = [];
  for (let replicate = 1; replicate <= replicates; replicate += 1) {
    const controller = needsClock ? await installPackageClock(page) : null;
    const shown = new Map();
    const turnsByScene = new Map();
    await walkScenes({
      page,
      pacing,
      controller,
      sceneIds,
      maxTurns: 20 * sceneIds.length,
      exploreFor: (sceneId) => exploreInput(mapScenes.get(sceneId)),
      startSession: startSceneSession,
      submitTurn,
      resolveWarning: resolveWarningIfPresent,
      onOpening: ({ scene_id, text }) => {
        if (!text) throw new Error(`Scene ${scene_id} has no opening text.`);
        if (!shown.has(scene_id)) shown.set(scene_id, []);
        shown.get(scene_id).push({ turn: 0, text });
      },
      onTurn: ({ scene_id, turn, input, text, payload }) => {
        const count = (turnsByScene.get(scene_id) || 0) + 1;
        turnsByScene.set(scene_id, count);
        if (count > 20) throw new Error(`@affordances refuses more than 20 turns for scene ${scene_id} in one replicate.`);
        if (!text) throw new Error(`Scene ${scene_id} has no narration on its explore turn.`);
        if (!shown.has(scene_id)) shown.set(scene_id, []);
        shown.get(scene_id).push({ turn, input, text, payload });
      },
    });
    for (const sceneId of sceneIds) {
      const entry = mapScenes.get(sceneId);
      scenes.push({ replicate, ...measureScene({ sceneEntry: entry, shownLog: shown.get(sceneId) || [] }) });
    }
  }
  const evidence = { story_id: map.story_id, scenes };
  await writeCategoryReport("affordances", evidence);
  await writeFile(resolve(repoRoot, "artifacts/e2e-affordances.md"), `# affordances E2E evaluation\n\n${formatMarkdown(evidence)}`);
});
