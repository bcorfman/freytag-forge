import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const ESCALATION_CRITERIA = [
  "cue_points_to_missing_thread",
  "complication_creates_pressure_without_unearned_knowledge",
  "no_pre_reveal_disclosure",
];
const ESCALATION_VERDICTS = ["yes", "no", "not_applicable"];
const ESCALATION_SCHEMA = {
  type: "object",
  properties: {
    cue_points_to_missing_thread: { type: "string", enum: ESCALATION_VERDICTS },
    complication_creates_pressure_without_unearned_knowledge: { type: "string", enum: ESCALATION_VERDICTS },
    no_pre_reveal_disclosure: { type: "string", enum: ESCALATION_VERDICTS },
    reasons: { type: "array", items: { type: "string" } },
  },
  required: [...ESCALATION_CRITERIA, "reasons"],
  additionalProperties: false,
};

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
  if (!apiKey) throw new Error("E2E escalation judge requires OPENAI_API_KEY.");
  return { apiKey, model: environment.E2E_JUDGE_MODEL || "gpt-5.4" };
}

const SYSTEM_MESSAGE =
  "Judge only turns with cue_fact_id or complication_text for the first two criteria. " +
  "Use not_applicable when no such turn exists. " +
  "A cue passes when the narration shows its visible detail and points toward the missing fact without stating it. " +
  "A complication passes when it adds observable pressure and reveals nothing the player has not earned. " +
  "no_pre_reveal_disclosure is no if narration before the reveal turn discloses a hidden item's existence or location named in the canon's Hidden canon.";

export async function judgeEscalation(
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
        { role: "user", content: JSON.stringify({ canon, opening, turns }) },
      ],
      text: {
        format: {
          type: "json_schema",
          name: "scene_escalation_judgment",
          strict: true,
          schema: ESCALATION_SCHEMA,
        },
      },
    }),
  });
  if (!response.ok) throw new Error(`E2E escalation judge request failed with HTTP ${response.status}.`);
  const verdict = JSON.parse(outputText(await response.json()));
  if (
    !verdict ||
    ESCALATION_CRITERIA.some((criterion) => !ESCALATION_VERDICTS.includes(verdict[criterion])) ||
    !Array.isArray(verdict.reasons) ||
    !verdict.reasons.every((reason) => typeof reason === "string")
  ) {
    throw new Error("E2E escalation judge returned an invalid verdict.");
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

async function main() {
  const input = JSON.parse(readFileSync(argument("--input"), "utf8"));
  const judgments = [];
  const canon = packageCanon(input.scene_id, input.package_path);
  for (const run of input.runs) {
    judgments.push(
      await judgeEscalation(
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
