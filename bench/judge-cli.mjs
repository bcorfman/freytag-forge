import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { judgeSceneNarration, sceneCanon } from "../frontend/e2e/roleplay-judge.js";

function argument(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || !process.argv[index + 1]) throw new Error(`Missing ${name}.`);
  return process.argv[index + 1];
}

const input = JSON.parse(readFileSync(argument("--input"), "utf8"));
const defaultCanonRoot = resolve(import.meta.dirname, "../data/stories/continuity-initiative");
function sceneBlock(source, heading, nextHeading) {
  const start = source.indexOf(heading);
  if (start < 0) return "";
  const end = source.indexOf(nextHeading, start + heading.length);
  return source.slice(start, end < 0 ? undefined : end);
}

function packageCanon(sceneId, packagePath) {
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

const judgments = [];
for (const run of input.runs) {
  const canon = input.package_path && resolve(input.package_path) !== defaultCanonRoot
    ? packageCanon(input.scene_id, input.package_path)
    : sceneCanon(input.scene_id);
  judgments.push(await judgeSceneNarration({
    sceneId: input.scene_id,
    opening: run.opening,
    turns: run.turns,
  }, {
    canon,
  }));
}
writeFileSync(argument("--output"), JSON.stringify({ judgments, judge_calls: judgments.length }, null, 2) + "\n");
