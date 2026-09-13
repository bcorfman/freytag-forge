import { readFileSync, writeFileSync } from "node:fs";

import { judgeSceneNarration } from "../frontend/e2e/roleplay-judge.js";
import { canonForInput } from "./judge-canon.mjs";

function argument(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || !process.argv[index + 1]) throw new Error(`Missing ${name}.`);
  return process.argv[index + 1];
}

const input = JSON.parse(readFileSync(argument("--input"), "utf8"));

const judgments = [];
for (const run of input.runs) {
  judgments.push(await judgeSceneNarration({
    sceneId: input.scene_id,
    opening: run.opening,
    turns: run.turns,
  }, {
    canon: canonForInput(input),
  }));
}
writeFileSync(argument("--output"), JSON.stringify({ judgments, judge_calls: judgments.length }, null, 2) + "\n");
