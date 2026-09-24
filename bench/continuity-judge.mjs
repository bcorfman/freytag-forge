import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const CONTINUITY_CRITERIA = [
  "contradicts_stated_fact",
  "protagonist_acts_beyond_command",
  "restarts_scene",
  "command_not_finished",
  "reveals_hidden_canon",
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
          command_not_finished: { type: "string", enum: CONTINUITY_VERDICTS },
          reveals_hidden_canon: { type: "string", enum: CONTINUITY_VERDICTS },
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
  "You judge the narrator of an interactive roleplay, one player turn at a time. For every turn in turns, answer five questions with yes or no and give one short reason. Use the canon block for that turn's scene_id. A change of scene_id means the story moved to a new scene; arriving in the new scene is not a restart. The canon is reference only and is never narration; it is the story's ground truth. item_placements and setting_facts only say where things start in a scene. given_facts is the current truth at the start of each turn and wins over item_placements, setting_facts and earlier narration. A more specific place or state that fits inside the given one is consistent, not a contradiction and not an invented change. For example, on the passenger seat is inside the truck, parked on the street is outside the house, and broken is a correct general word for a cracked or shattered screen. story_text lists sentences the story itself wrote at the end of this turn. They are not part of narration. They are canon. Use them to decide command_not_finished and what is true after the turn. Answer every other question from narration alone. contradicts_stated_fact: answer yes if the turn's narration states something about the physical state or position of a thing that conflicts with the canon, the opening, an earlier turn's narration, or given_facts. A detail the canon never mentions is not a contradiction. A command from an earlier turn is not evidence that its action happened; only narration and given_facts are evidence. For example, if the command said to hand the phone to the man but the narration only showed her holding it out, she still has it. protagonist_acts_beyond_command: answer yes if the narration has the player character physically do something the player's command did not ask for, such as picking up, moving, opening or taking an object, or going somewhere else. This is never by itself a contradiction. Looking, noticing, thinking, feeling, and small movements needed to carry out the command are not beyond it. restarts_scene: answer yes if the narration describes the player character arriving at, entering, or stepping into the scene's location, or discovering something already described in the opening or an earlier turn as though it were new. Continuing to act inside the location is not a restart. Repeating a journey the story already finished is also a restart. For example, narrating a drive through the city to reach a truck parked outside the house she is already in is yes. command_not_finished: answer yes if the narration stops before the action the command asked for is done. A command to look at, examine, search or check a thing is finished when the narration shows her attending to that thing. She does not have to describe what she sees, and picking the thing up as well does not make it unfinished. She must reach the place the command named, hand over the thing, put it where the command said, or bring it where the command said. When the command names a place to go to or to bring a thing to, the narration must name that place as where she arrives or is clearly heading. For example, drives away from the house does not finish drive to the park, while carries the laptop back out to the truck does finish a command that names the truck. If the command needs another character to act, such as taking a thing or answering, the narration must show how that character responds. She cannot control another character. A refusal, a struggle or silence is still a response, and it finishes the command. She must still do her own part, such as asking the question or reaching for the thing. When she tries to take a thing from another character, trying is her whole part. The narration does not have to say whether she gets it. Only holding a thing out, with no response shown, is not finished. reveals_hidden_canon: answer yes if the narration shows a thing the canon marks as hidden in a Hidden canon line before the player's own action reaches its hidden spot, or puts that thing somewhere other than its hidden spot. For example, if a memory card is taped beneath a drawer, narration that finds it inside the drawer when she opens it is yes.";

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

function playerVisibleTurn(turn, index, sceneId) {
  return {
    turn_number: Number.isInteger(turn.turn_number) ? turn.turn_number : index + 1,
    scene_id: turn.scene_id ?? sceneId,
    player_input: turn.player_input,
    narration: turn.narrator_narration ?? turn.narration,
    story_text: turn.story_text ?? [],
    given_facts: turn.item_facts_before ?? {},
  };
}

function validateVerdict(verdict, expectedTurns) {
  if (!verdict || !Array.isArray(verdict.turns)) {
    throw new Error("E2E continuity judge returned an invalid verdict.");
  }
  if (
    !verdict.turns.every(
      (item) =>
        item &&
        CONTINUITY_CRITERIA.every((criterion) => CONTINUITY_VERDICTS.includes(item[criterion])) &&
        typeof item.reason === "string",
    )
  ) {
    throw new Error("E2E continuity judge returned an invalid verdict.");
  }
  const expected = new Set(expectedTurns);
  const actualCounts = new Map();
  for (const item of verdict.turns) {
    if (Number.isInteger(item.turn)) actualCounts.set(item.turn, (actualCounts.get(item.turn) || 0) + 1);
  }
  const missing = expectedTurns.filter((turn) => !actualCounts.has(turn));
  const unexpected = [...actualCounts]
    .filter(([turn, count]) => !expected.has(turn) || count > 1)
    .flatMap(([turn, count]) => Array(Math.max(1, count - (expected.has(turn) ? 1 : 0))).fill(turn));
  if (
    verdict.turns.length !== expectedTurns.length ||
    missing.length ||
    unexpected.length ||
    verdict.turns.some((item) => !Number.isInteger(item.turn))
  ) {
    return { missing, unexpected };
  }
  const byTurn = new Map(verdict.turns.map((item) => [item.turn, item]));
  return { verdict: { turns: expectedTurns.map((turn) => byTurn.get(turn)) } };
}

function turnMismatchError(mismatch) {
  return `E2E continuity judge returned the wrong turn numbers (missing: ${mismatch.missing.join(", ") || "none"}; unexpected: ${mismatch.unexpected.join(", ") || "none"}).`;
}

export async function judgeContinuity(
  { sceneId, opening, turns },
  { environment = process.env, fetchImpl = fetch, canon } = {},
) {
  void sceneId;
  const { apiKey, model } = judgeConfiguration(environment);
  const expectedTurns = turns.map((turn, index) => (Number.isInteger(turn.turn_number) ? turn.turn_number : index + 1));
  const requestBody = {
    model,
    store: false,
    input: [
      { role: "system", content: `${SYSTEM_MESSAGE} Copy each turn's turn_number into turn.` },
      {
        role: "user",
        content: JSON.stringify({
          canon: { scene_id: canon?.scene_id, plot: canon?.plot },
          opening,
          turns: turns.map((turn, index) => playerVisibleTurn(turn, index, sceneId)),
        }),
      },
    ],
    text: { format: { type: "json_schema", name: "scene_continuity_judgment", strict: true, schema: CONTINUITY_SCHEMA } },
  };
  async function requestVerdict() {
    const response = await fetchImpl("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify(requestBody),
    });
    if (!response.ok) throw new Error(`E2E continuity judge request failed with HTTP ${response.status}.`);
    return JSON.parse(outputText(await response.json()));
  }
  let mismatch;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const checked = validateVerdict(await requestVerdict(), expectedTurns);
    if (checked.verdict) return checked.verdict;
    mismatch = checked;
  }
  throw new Error(turnMismatchError(mismatch));
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
    judgments.push(await judgeContinuity({ sceneId: input.scene_id, opening: run.opening, turns: run.turns }, { canon }));
  }
  writeFileSync(argument("--output"), JSON.stringify({ judgments, judge_calls: judgments.length }, null, 2) + "\n");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
