import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const CONTINUITY_CRITERIA = [
  "contradicts_stated_fact",
  "protagonist_acts_beyond_command",
  "restarts_scene",
];
const CONTINUITY_VERDICTS = ["yes", "no"];
const CONTINUITY_SCHEMA = {
  type: "object",
  properties: {
    turns: {
      type: "array",
      items: {
        type: "object",
        properties: {
          turn: { type: "integer" },
          contradicts_stated_fact: { type: "string", enum: CONTINUITY_VERDICTS },
          protagonist_acts_beyond_command: { type: "string", enum: CONTINUITY_VERDICTS },
          restarts_scene: { type: "string", enum: CONTINUITY_VERDICTS },
          reason: { type: "string" },
        },
        required: ["turn", ...CONTINUITY_CRITERIA, "reason"],
        additionalProperties: false,
      },
    },
  },
  required: ["turns"],
  additionalProperties: false,
};

const SYSTEM_MESSAGE =
  "You judge the narrator of an interactive roleplay, one player turn at a time. For every turn in turns, answer three questions with yes or no and give one short reason. The canon is reference only and is never narration; it is the story's ground truth, including the scene's item_placements and setting_facts. contradicts_stated_fact: answer yes if the turn's narration states something about the physical state or position of a thing that conflicts with the canon, the opening, or an earlier turn's narration. Examples: an object described as damaged or cracked when setting_facts say it is not damaged; an object somewhere other than its item_placements when no player command moved it. A detail the canon never mentions is not a contradiction. protagonist_acts_beyond_command: answer yes if the narration has the player character physically do something the player's command did not ask for, such as picking up, moving, opening or taking an object, or going somewhere else. Looking, noticing, thinking, feeling, and small movements needed to carry out the command are not beyond it. restarts_scene: answer yes if the narration describes the player character arriving at, entering, or stepping into the scene's location, or discovering something already described in the opening or an earlier turn as though it were new. Continuing to act inside the location is not a restart.";

function outputText(response) {
  if (typeof response?.output_text === "string") return response.output_text;
  for (const item of response?.output || []) {
    for (const content of item?.content || []) {
      if (content?.type === "output_text" && typeof content.text === "string") return content.text;
    }
  }
  return "";
}

function judgeConfiguration(environment) {
  const apiKey = environment.OPENAI_API_KEY;
  if (!apiKey) throw new Error("E2E continuity judge requires OPENAI_API_KEY.");
  return { apiKey, model: environment.E2E_JUDGE_MODEL || "gpt-5.4" };
}

function playerVisibleTurn(turn) {
  return { player_input: turn.player_input, narration: turn.narration };
}

export async function judgeContinuity(
  { sceneId, opening, turns },
  { environment = process.env, fetchImpl = fetch, canon } = {},
) {
  void sceneId;
  const { apiKey, model } = judgeConfiguration(environment);
  const response = await fetchImpl("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({
      model,
      store: false,
      input: [
        { role: "system", content: SYSTEM_MESSAGE },
        {
          role: "user",
          content: JSON.stringify({
            canon: { scene_id: canon?.scene_id, plot: canon?.plot },
            opening,
            turns: turns.map(playerVisibleTurn),
          }),
        },
      ],
      text: {
        format: {
          type: "json_schema",
          name: "scene_continuity_judgment",
          strict: true,
          schema: CONTINUITY_SCHEMA,
        },
      },
    }),
  });
  if (!response.ok) throw new Error(`E2E continuity judge request failed with HTTP ${response.status}.`);
  const verdict = JSON.parse(outputText(await response.json()));
  if (
    !verdict ||
    !Array.isArray(verdict.turns) ||
    verdict.turns.length !== turns.length ||
    !verdict.turns.every(
      (item) =>
        item &&
        CONTINUITY_CRITERIA.every((criterion) => CONTINUITY_VERDICTS.includes(item[criterion])) &&
        typeof item.reason === "string",
    )
  ) {
    throw new Error("E2E continuity judge returned an invalid verdict.");
  }
  return verdict;
}

function argument(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || !process.argv[index + 1]) throw new Error(`Missing ${name}.`);
  return process.argv[index + 1];
}

function sceneBlock(source, heading, nextHeading) {
  const start = source.indexOf(heading);
  if (start < 0) return "";
  const end = source.indexOf(nextHeading, start + heading.length);
  return source.slice(start, end < 0 ? undefined : end);
}

export function packageCanon(sceneId, packagePath) {
  const root = resolve(packagePath);
  const plot = readFileSync(resolve(root, "plot.md"), "utf8");
  const sceneIds = [...plot.matchAll(/^## Scene ([1-9][A-Z])\b/gm)].map((match) => match[1]);
  const nextScene = sceneIds[sceneIds.indexOf(sceneId) + 1];
  return {
    scene_id: sceneId,
    plot: sceneBlock(plot, `## Scene ${sceneId}`, nextScene ? `## Scene ${nextScene}` : "\u0000"),
  };
}

async function main() {
  const input = JSON.parse(readFileSync(argument("--input"), "utf8"));
  const judgments = [];
  const canon = packageCanon(input.scene_id, input.package_path);
  for (const run of input.runs) {
    judgments.push(await judgeContinuity({ sceneId: input.scene_id, opening: run.opening, turns: run.turns }, { canon }));
  }
  writeFileSync(argument("--output"), JSON.stringify({ judgments, judge_calls: judgments.length }, null, 2) + "\n");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
