const JUDGE_SCHEMA = {
  type: "object",
  properties: {
    verdict: { type: "string", enum: ["pass", "fail"] },
    responsive: { type: "boolean" },
    progressive: { type: "boolean" },
    coherent: { type: "boolean" },
    reasons: { type: "array", items: { type: "string" } },
  },
  required: ["verdict", "responsive", "progressive", "coherent", "reasons"],
  additionalProperties: false,
};

const CANON_SCHEMA = {
  type: "object",
  properties: {
    verdict: { type: "string", enum: ["pass", "fail"] },
    canon_consistent: { type: "boolean" },
    scene_local: { type: "boolean" },
    progressive: { type: "boolean" },
    rich: { type: "boolean" },
    protected_safe: { type: "boolean" },
    // The player must be able to read why the story left this scene, and apt searching
    // must actually turn something up. Both failed silently before they were graded.
    exit_motivated: { type: "boolean" },
    rewards_investigation: { type: "boolean" },
    missing_or_wrong: { type: "array", items: { type: "string" } },
    reasons: { type: "array", items: { type: "string" } },
  },
  required: [
    "verdict",
    "canon_consistent",
    "scene_local",
    "progressive",
    "rich",
    "protected_safe",
    "exit_motivated",
    "rewards_investigation",
    "missing_or_wrong",
    "reasons",
  ],
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
  if (!apiKey) {
    throw new Error("E2E judge requires OPENAI_API_KEY.");
  }
  return { apiKey, model: environment.E2E_JUDGE_MODEL || "gpt-5.4" };
}

export async function judgeRoleplayTurn({ opening, playerInput, narration }, { environment = process.env, fetchImpl = fetch } = {}) {
  const { apiKey, model } = judgeConfiguration(environment);
  const response = await fetchImpl("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({
      model,
      store: false,
      input: [
        {
          role: "system",
          content:
            "You are a strict interactive-fiction QA judge. Creative additions are allowed; do not reject them merely " +
            "because they are not in the opening. Fail when narration does not directly respond to player_input, merely " +
            "repeats/rephrases the opening, or contradicts supplied grounding.",
        },
        { role: "user", content: JSON.stringify({ opening, player_input: playerInput, narration }) },
      ],
      text: {
        format: { type: "json_schema", name: "roleplay_turn_judgment", strict: true, schema: JUDGE_SCHEMA },
      },
    }),
  });
  if (!response.ok) throw new Error(`E2E judge request failed with HTTP ${response.status}.`);
  const judgeResponse = await response.json();
  const rawVerdict = outputText(judgeResponse);
  if (typeof rawVerdict !== "string") throw new Error("E2E judge returned no text payload.");
  const verdict = JSON.parse(rawVerdict);
  if (
    !verdict ||
    !["pass", "fail"].includes(verdict.verdict) ||
    typeof verdict.responsive !== "boolean" ||
    typeof verdict.progressive !== "boolean" ||
    typeof verdict.coherent !== "boolean" ||
    !Array.isArray(verdict.reasons)
  ) {
    throw new Error("E2E judge returned an invalid verdict.");
  }
  return verdict;
}

function sceneBlock(source, heading, nextHeading) {
  const start = source.indexOf(heading);
  if (start < 0) return "";
  const end = source.indexOf(nextHeading, start + heading.length);
  return source.slice(start, end < 0 ? undefined : end);
}

export function sceneCanon(sceneId, root = resolve(import.meta.dirname, "../..")) {
  const storyRoot = resolve(root, "data/stories/continuity-initiative");
  const read = (name) => readFileSync(resolve(storyRoot, name), "utf8");
  const plot = read("plot.md");
  const scenes = ["1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"];
  const nextScene = scenes[scenes.indexOf(sceneId) + 1];
  return {
    scene_id: sceneId,
    plot: sceneBlock(plot, `## Scene ${sceneId}`, nextScene ? `## Scene ${nextScene}` : "\u0000"),
    storylets: sceneBlock(read("storylets.md"), `### SL-${sceneId}`, nextScene ? `### SL-${nextScene}` : "\u0000"),
    routes: sceneBlock(read("storylet-routes.yaml"), `- id: SL-${sceneId}`, nextScene ? `- id: SL-${nextScene}` : "\u0000"),
    pacing: read("pacing.yaml"),
    world: read("world.yaml"),
  };
}

export async function judgeSceneNarration(
  { sceneId, opening, turns },
  { environment = process.env, fetchImpl = fetch, canon = sceneCanon(sceneId) } = {},
) {
  const { apiKey, model } = judgeConfiguration(environment);
  const response = await fetchImpl("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({
      model,
      store: false,
      input: [
        {
          role: "system",
          content:
            "You are a strict interactive-fiction acceptance judge. Evaluate only the supplied scene-local canon. " +
            "Require characters, items, plot events, dialogue, and setting to remain consistent with the five source files. " +
            "When an opening is supplied, require substantial sensory scene establishment; always require responsive consequences on ordinary turns, " +
            "and progressive revelation rather than dumping future beats or racing a transition. Protected knowledge must " +
            "never be revealed early. Do not require every optional storylet or every beat in a single turn. " +
            "A turn marked left_scene is the one the story departed on: fail unless the narration the player actually " +
            "read gives them a reason to go, naming in prose what was found and where it points. A discovery the " +
            "player is never told has not happened, however plainly the canon implies it. Fail too when repeated apt " +
            "searching of what this scene's canon says is here keeps returning nothing the player can act on.",
        },
        { role: "user", content: JSON.stringify({ canon, opening, turns }) },
      ],
      text: { format: { type: "json_schema", name: "scene_canon_judgment", strict: true, schema: CANON_SCHEMA } },
    }),
  });
  if (!response.ok) throw new Error(`E2E canon judge request failed with HTTP ${response.status}.`);
  const verdict = JSON.parse(outputText(await response.json()));
  if (!verdict || !["pass", "fail"].includes(verdict.verdict) || !Array.isArray(verdict.reasons)) {
    throw new Error("E2E canon judge returned an invalid verdict.");
  }
  return verdict;
}
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
