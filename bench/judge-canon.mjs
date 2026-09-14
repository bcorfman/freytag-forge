import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { sceneCanon } from "../frontend/e2e/roleplay-judge.js";

function sceneBlock(source, heading, nextHeading) {
  const start = source.indexOf(heading);
  if (start < 0) return "";
  const end = source.indexOf(nextHeading, start + heading.length);
  return source.slice(start, end < 0 ? undefined : end);
}

export function packageCanon(sceneId, packagePath) {
  const root = resolve(packagePath);
  const read = (name) => readFileSync(resolve(root, name), "utf8");
  const plot = read("plot.md");
  const sceneIds = [...plot.matchAll(/^## Scene ([1-9][A-Z])\b/gm)].map((match) => match[1]);
  const nextScene = sceneIds[sceneIds.indexOf(sceneId) + 1];
  const storylets = read("storylets.md");
  const routes = read("storylet-routes.yaml");
  return {
    scene_id: sceneId,
    plot: sceneBlock(plot, `## Scene ${sceneId}`, nextScene ? `## Scene ${nextScene}` : "\u0000"),
    storylets: sceneBlock(storylets, `### SL-${sceneId}`, nextScene ? `### SL-${nextScene}` : "\u0000"),
    routes: sceneBlock(routes, `- id: SL-${sceneId}`, nextScene ? `- id: SL-${nextScene}` : "\u0000"),
    pacing: read("pacing.yaml"),
    world: read("world.yaml"),
  };
}

export function canonForInput(input) {
  return typeof input.package_path === "string" && input.package_path.length > 0
    ? packageCanon(input.scene_id, input.package_path)
    : sceneCanon(input.scene_id);
}
