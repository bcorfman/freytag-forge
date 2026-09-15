import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const FACT_TRACKING_CRITERIA = [
  "facts_after_correct",
  "missed_change",
  "invented_change",
  "narration_contradicts_given_facts",
  "dropped_true_condition",
  "kept_ended_condition",
  "state_as_place",
];
const VERDICTS = ["yes", "no"];
const CAUSES = ["command", "narrator"];
const FACT_TRACKING_SCHEMA = {
  type: "object",
  properties: {
    turns: {
      type: "array",
      items: {
        type: "object",
        properties: {
          turn: { type: "integer" },
          facts_after_correct: { type: "string", enum: VERDICTS },
          missed_change: { type: "string", enum: VERDICTS },
          invented_change: { type: "string", enum: VERDICTS },
          narration_contradicts_given_facts: { type: "string", enum: VERDICTS },
          dropped_true_condition: { type: "string", enum: VERDICTS },
          kept_ended_condition: { type: "string", enum: VERDICTS },
          state_as_place: { type: "string", enum: VERDICTS },
          changes: {
            type: "array",
            items: {
              type: "object",
              properties: {
                thing: { type: "string" },
                change: { type: "string" },
                cause: { type: "string", enum: CAUSES },
              },
              required: ["thing", "change", "cause"],
              additionalProperties: false,
            },
          },
          reason: { type: "string" },
        },
        required: ["turn", ...FACT_TRACKING_CRITERIA, "changes", "reason"],
        additionalProperties: false,
      },
    },
  },
  required: ["turns"],
  additionalProperties: false,
};

const SYSTEM_MESSAGE =
  "You check whether a story game tracked the state of things correctly, one turn at a time. Each turn gives the player's command, the narration, item_facts_before (the facts the narrator was given) and item_facts_after (the facts the game kept after the turn). For every turn answer yes or no and give one short reason. facts_after_correct: yes if item_facts_after matches what item_facts_before plus this turn's narration shows about each thing. missed_change: yes if the narration clearly changed a thing's place, holder or condition but item_facts_after did not record it. invented_change: yes if item_facts_after adds or changes a place, holder or condition phrase that the narration did not show. A condition that is only missing from item_facts_after is not an invented change; judge that under dropped_true_condition. A condition kept after the narration ended it is judged under kept_ended_condition. A state put in where is judged under state_as_place. narration_contradicts_given_facts: yes if the narration states something about a thing that conflicts with item_facts_before without showing it change during the turn. dropped_true_condition: yes if item_facts_after no longer lists a condition phrase from item_facts_before for a thing, and the narration did not show that condition stop being true. kept_ended_condition: yes if item_facts_after still lists a condition phrase that the narration showed stop being true, such as charging after the phone is unplugged, or shut after the drawer is opened. state_as_place: yes if a thing's where in item_facts_after is a state or condition rather than a place or a holder, such as open, cracked or charging, or if a where from item_facts_before was replaced by such a state. A thing may appear in item_facts_after even when it was not in item_facts_before if the narration introduced that thing. Recording it with the place and condition the narration showed is correct and is not an invented change. If the narration introduced and placed a thing but item_facts_after does not list it, judge that as a missed change. In changes, list each change the narration showed, with a cause for each. Use cause command only when the player's command itself asks for that change, such as picking up the phone after the command pick up the phone. Looking at, examining, searching, or checking a thing does not ask for moving, taking, opening, or damaging it, so a change like that is cause narrator. Wording differences that mean the same thing are not errors.";

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
  if (!apiKey) throw new Error("E2E fact-tracking judge requires OPENAI_API_KEY.");
  return { apiKey, model: environment.E2E_JUDGE_MODEL || "gpt-5.4" };
}

function playerVisibleTurn(turn) {
  return {
    player_input: turn.player_input,
    narration: turn.narration,
    item_facts_before: turn.item_facts_before,
    item_facts_after: turn.item_facts_after,
    ...(Object.hasOwn(turn, "scene_id") ? { scene_id: turn.scene_id } : {}),
  };
}

function validateVerdict(verdict, expectedLength) {
  if (!verdict || !Array.isArray(verdict.turns) || verdict.turns.length !== expectedLength) {
    throw new Error("E2E fact-tracking judge returned an invalid verdict.");
  }
  if (
    !verdict.turns.every(
      (item) =>
        item &&
        Number.isInteger(item.turn) &&
        FACT_TRACKING_CRITERIA.every((criterion) => VERDICTS.includes(item[criterion])) &&
        typeof item.reason === "string" &&
        Array.isArray(item.changes) &&
        item.changes.every(
          (change) =>
            change &&
            typeof change.thing === "string" &&
            typeof change.change === "string" &&
            CAUSES.includes(change.cause),
        ),
    )
  ) {
    throw new Error("E2E fact-tracking judge returned an invalid verdict.");
  }
  return verdict;
}

export async function judgeFactTracking(
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
          name: "fact_tracking_judgment",
          strict: true,
          schema: FACT_TRACKING_SCHEMA,
        },
      },
    }),
  });
  if (!response.ok) throw new Error(`E2E fact-tracking judge request failed with HTTP ${response.status}.`);
  return validateVerdict(JSON.parse(outputText(await response.json())), turns.length);
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

export function packageCanon(sceneId, packagePath, extraSceneIds = []) {
  const root = resolve(packagePath);
  const plot = readFileSync(resolve(root, "plot.md"), "utf8");
  const sceneIds = [...plot.matchAll(/^## Scene ([1-9][A-Z])\b/gm)].map((match) => match[1]);
  const nextScene = sceneIds[sceneIds.indexOf(sceneId) + 1];
  const selectedSceneIds = [
    sceneId,
    ...extraSceneIds.filter((extraSceneId, index) => extraSceneId !== sceneId && extraSceneIds.indexOf(extraSceneId) === index),
  ];
  return {
    scene_id: sceneId,
    plot: selectedSceneIds
      .map((selectedSceneId) => {
        const nextSelectedScene = sceneIds[sceneIds.indexOf(selectedSceneId) + 1];
        return sceneBlock(
          plot,
          `## Scene ${selectedSceneId}`,
          nextSelectedScene ? `## Scene ${nextSelectedScene}` : "\u0000",
        );
      })
      .join(""),
  };
}

async function main() {
  const input = JSON.parse(readFileSync(argument("--input"), "utf8"));
  const judgments = [];
  const extraSceneIds = [];
  for (const run of input.runs) {
    for (const turn of run.turns) {
      if (typeof turn.scene_id === "string" && !extraSceneIds.includes(turn.scene_id)) {
        extraSceneIds.push(turn.scene_id);
      }
    }
  }
  const canon = packageCanon(input.scene_id, input.package_path, extraSceneIds);
  for (const run of input.runs) {
    judgments.push(
      await judgeFactTracking(
        { sceneId: input.scene_id, opening: run.opening, turns: run.turns },
        { canon },
      ),
    );
  }
  writeFileSync(argument("--output"), JSON.stringify({ judgments, judge_calls: judgments.length }, null, 2) + "\n");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
