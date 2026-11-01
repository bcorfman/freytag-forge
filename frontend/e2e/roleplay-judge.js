import { resolve } from "node:path";

import { loadCanonSources, protectedFactsForScene } from "./knowledge-available.js";

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
  return { apiKey, model: environment.E2E_JUDGE_MODEL || "gpt-5.6-luna" };
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

export function sceneCanon(
  sceneId,
  revealedKnowledgeIds = [],
  root = resolve(import.meta.dirname, "../.."),
  { knowledgeAvailableBeforeTurn = [], runtimeDeliveries = [] } = {},
) {
  const { knowledgePackage } = loadCanonSources(root);
  const sceneFrame = knowledgePackage.scene_frames.find((frame) => frame.scene_id === sceneId);
  const revealedIds = new Set(revealedKnowledgeIds);
  const firstTurnKnowledge = knowledgeAvailableBeforeTurn[0] || [];
  const publicKnowledgeIds = new Set(knowledgePackage.knowledge
    .filter((entry) => entry?.audience?.player_visible === true && entry.audience.kind !== "world_only")
    .map((entry) => entry.id));
  const knownBeforeScene = new Set([
    ...revealedIds,
    ...firstTurnKnowledge.map((entry) => typeof entry === "string" ? entry : entry?.id),
  ].filter((id) => publicKnowledgeIds.has(id)));
  const protectedFacts = protectedFactsForScene({
    entries: knowledgePackage.knowledge,
    sceneId,
    availableIds: knownBeforeScene,
  });
  return {
    scene_id: sceneId,
    situation: sceneFrame.situation,
    pressure: sceneFrame.pressure,
    revealed_knowledge: knowledgePackage.knowledge
      .filter((entry) => entry.available_in_scenes.includes(sceneId) && revealedIds.has(entry.id))
      .map(({ id, statement }) => ({ id, statement })),
    protected_facts: protectedFacts,
    knowledge_available_before_turn: knowledgeAvailableBeforeTurn,
    runtime_deliveries: runtimeDeliveries,
  };
}

export async function judgeSceneNarration(
  {
    sceneId,
    opening,
    turns,
    revealedKnowledgeIds = [],
    knowledgeAvailableBeforeTurn = [],
    runtimeDeliveries = [],
    protectedFactsByTurn = [],
  },
  { environment = process.env, fetchImpl = fetch, canon: suppliedCanon } = {},
) {
  const { apiKey, model } = judgeConfiguration(environment);
  const effectiveKnowledgeAvailableBeforeTurn = knowledgeAvailableBeforeTurn.length
    ? knowledgeAvailableBeforeTurn
    : turns.map((turn) => turn.knowledge_available_before_turn || []);
  const effectiveRuntimeDeliveries = runtimeDeliveries.length
    ? runtimeDeliveries
    : turns.map((turn) => turn.runtime_deliveries || { authored_spans: [], committed_facts: [] });
  const canon = suppliedCanon || sceneCanon(sceneId, revealedKnowledgeIds, undefined, {
    knowledgeAvailableBeforeTurn: effectiveKnowledgeAvailableBeforeTurn,
    runtimeDeliveries: effectiveRuntimeDeliveries,
  });
  const turnsWithBeatContext = turns.map((turn, index) => {
    const turnForJudge = { ...turn };
    delete turnForJudge.segments;
    delete turnForJudge.bundle;
    delete turnForJudge.prompt;
    if (!turnForJudge.knowledge_available_before_turn && knowledgeAvailableBeforeTurn[index]) {
      turnForJudge.knowledge_available_before_turn = knowledgeAvailableBeforeTurn[index];
    }
    if (!turnForJudge.runtime_deliveries && runtimeDeliveries[index]) {
      turnForJudge.runtime_deliveries = runtimeDeliveries[index];
    }
    if (!turnForJudge.protected_facts && protectedFactsByTurn[index]) {
      turnForJudge.protected_facts = protectedFactsByTurn[index];
    }
    return {
      ...turnForJudge,
      beats_projected: turn.beats_projected || [],
    };
  });
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
            "Require characters, items, plot events, dialogue, and setting to remain consistent with the supplied canon and the committed timeline. Judge runtime-authored text for quality, but do not attribute it to the narrator. " +
            "When an opening is supplied, require substantial sensory scene establishment; always require responsive consequences on ordinary turns, " +
            "and progressive revelation rather than dumping future beats or racing a transition. Protected knowledge must " +
            "never be revealed early. knowledge_available_before_turn lists public knowledge already disclosed to the player. runtime_deliveries lists the authored text delivered on this turn and its committed facts. Earlier disclosures remain known in later scenes. A later disclosure cannot excuse an earlier leak. " +
            "Fail protected_safe only when narrator text discloses a protected fact from the supplied protected-fact inventory before it is available. Identify the fact, turn and exact narrator text. Runtime deliveries are exempt from narrator-disclosure penalties. " +
            "Inventory items marked world_only are facts the player can never be told directly; narrator text that states one as established fact fails protected_safe. " +
            "An ordinary invented detail that is not an authored protected fact, such as a color, a minor object, or a bit of atmosphere, is not premature disclosure and must not fail protected_safe. " +
            "Turns may carry authored_spans, knowledge_available_before_turn, runtime_deliveries, protected_facts, and arrival_narration, which is the opening of the scene the player entered. The supplied runtime_deliveries identify text inserted by the runtime. Exempt only those spans from narrator-disclosure penalties. Judge all other text normally. Use knowledge available before the turn. Read the full turn when judging exit motivation and other quality checks. " +
            "Text the narrator wrote itself that states a protected fact from the supplied protected-fact inventory before it is available is still premature disclosure. " +
            "Contradiction of established canon still fails canon_consistent. Do not require every optional storylet or every beat in a single turn. " +
            "Judge each TURN against the beat it was actually given. A turn that dramatises its assigned beat poorly still fails; being given a beat is not credit for using it. " +
            "Judge the SCENE on whether its authored beats were covered in order across its turns. A scene that skips beats entirely still fails. " +
            "For a turn marked left_scene, read the departure and its arrival together with earlier discoveries in this scene. " +
            "Require a player-visible reason to leave and a clear destination or route. Earned access, immediate danger, or a discovery can supply the reason. " +
            "Do not require the same discovery to be repeated on the departure turn. Cite the exact player-visible text that supplies the reason and the destination; fail when no such text exists anywhere in the departure, the arrival or the earlier turns. " +
            "A discovery the player is never told has not happened, however plainly the canon implies it. Fail too when repeated apt " +
            "searching of what this scene's canon says is here keeps returning nothing the player can act on.",
        },
        { role: "user", content: JSON.stringify({ canon, opening, turns: turnsWithBeatContext }) },
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
