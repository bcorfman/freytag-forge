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
  "You check whether a story game tracked the state of things correctly, one turn at a time. Each turn gives the player's command, the narration, item_facts_before (the facts the narrator was given) and item_facts_after (the facts the game kept after the turn). For every turn answer yes or no and give one short reason. facts_after_correct: answer only whether item_facts_after matches what the narration shows. Do not mark it no because the narration conflicts with item_facts_before; judge that only under narration_contradicts_given_facts. For example, if the narration says she picks the phone up from the table and puts it in her pocket while GIVEN had it in her hands, recording it in her pocket is correct. A more specific place or state that fits inside the given one is consistent, not a contradiction and not an invented change. For example, on the passenger seat is inside the truck, parked on the street is outside the house, and broken is a correct general word for a cracked or shattered screen. A thing the narration introduces this turn and item_facts_after now lists is tracked. Do not answer no because a thing is new; answer only on whether item_facts_after matches what the narration shows. missed_change: yes if the narration clearly changed a thing's place, holder or condition but item_facts_after did not record it. An action the narration only attempts changes nothing. An attempted handover that nobody takes changes nothing. For example, she holds a phone out to a man and the narration never shows him taking it, so the phone is still hers and recording no change is correct. invented_change: yes if item_facts_after adds or changes a place, holder or condition phrase that the narration did not show. A condition the narration never shows is an invented change even when it is the likely or ordinary state of the thing. For example, recording a laptop as closed when the narration only shows her carrying it out of the truck is invented. A thing that is not in item_facts_before but that the narration introduces is never an invented change when item_facts_after records it as narrated. It exists, and recording it is correct. A condition that is only missing from item_facts_after is not an invented change; judge that under dropped_true_condition. A condition kept after the narration ended it is judged under kept_ended_condition. A state put in place is judged under state_as_place. narration_contradicts_given_facts: yes if the narration states something about a thing that conflicts with item_facts_before without showing it change during the turn. A state the narration gives a thing must also be possible with the conditions item_facts_before records for it. For example, a phone whose conditions say shattered is not also still working, and a phone that needs charging is not also showing a locked screen. dropped_true_condition: yes if item_facts_after no longer lists a condition phrase from item_facts_before for a thing, and the narration did not show that condition stop being true. kept_ended_condition: yes if item_facts_after still lists a condition phrase that the narration showed stop being true, such as charging after the phone is unplugged, or shut after the drawer is opened. state_as_place: yes if a thing's place in item_facts_after is a state or condition rather than a place or a holder, such as open, cracked or charging, or if a place from item_facts_before was replaced by such a state. If the narration introduced and placed a thing but item_facts_after does not list it, judge that as a missed change. In changes, list each change the narration showed, with a cause for each. Use cause command only when the player's command itself asks for that change, such as picking up the phone after the command pick up the phone. Looking at, examining, searching, or checking a thing does not ask for moving, taking, opening, or damaging it, so a change like that is cause narrator. Wording differences that mean the same thing are not errors.";

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

function playerVisibleTurn(turn, index) {
  return {
    turn_number: Number.isInteger(turn.turn_number) ? turn.turn_number : index + 1,
    player_input: turn.player_input,
    narration: turn.narration,
    item_facts_before: turn.item_facts_before,
    item_facts_after: turn.item_facts_after,
    ...(Object.hasOwn(turn, "scene_id") ? { scene_id: turn.scene_id } : {}),
  };
}

function validateVerdict(verdict, expectedTurns) {
  if (!verdict || !Array.isArray(verdict.turns)) {
    throw new Error("E2E fact-tracking judge returned an invalid verdict.");
  }
  if (
    !verdict.turns.every(
      (item) =>
        item &&
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
  return `E2E fact-tracking judge returned the wrong turn numbers (missing: ${mismatch.missing.join(", ") || "none"}; unexpected: ${mismatch.unexpected.join(", ") || "none"}).`;
}

export async function judgeFactTracking(
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
  };
  async function requestVerdict() {
    const response = await fetchImpl("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify(requestBody),
    });
    if (!response.ok) throw new Error(`E2E fact-tracking judge request failed with HTTP ${response.status}.`);
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
