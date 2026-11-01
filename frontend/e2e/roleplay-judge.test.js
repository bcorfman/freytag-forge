import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { resolve } from "node:path";

import { judgeRoleplayTurn, judgeSceneNarration, sceneCanon } from "./roleplay-judge.js";

test("roleplay judge sends the transcript and parses a passing structured verdict", async () => {
  let request;
  const verdict = await judgeRoleplayTurn(
    { opening: "The room is quiet.", playerInput: "Inspect the desk.", narration: "You open the desk drawer." },
    {
      environment: { OPENAI_API_KEY: "test-key" },
      fetchImpl: async (_url, options) => {
        request = JSON.parse(options.body);
        return new Response(
          JSON.stringify({
            output: [
              {
                type: "message",
                content: [
                  {
                    type: "output_text",
                    text: JSON.stringify({
                      verdict: "pass",
                      responsive: true,
                      progressive: true,
                      coherent: true,
                      reasons: [],
                    }),
                  },
                ],
              },
            ],
          }),
          { status: 200 },
        );
      },
    },
  );

  assert.equal(verdict.verdict, "pass");
  assert.equal(request.model, "gpt-5.6-luna");
  assert.equal(request.store, false);
  assert.match(request.input[0].content, /Creative additions are allowed/);
  assert.equal(JSON.parse(request.input[1].content).player_input, "Inspect the desk.");
});

test("scene canon judge sends only the current scene canon and parses its verdict", async () => {
  let request;
  const verdict = await judgeSceneNarration(
    { sceneId: "1A", opening: "A tense house.", turns: [{ player_input: "Search the house.", narration: "A clue." }] },
    {
      environment: { OPENAI_API_KEY: "test-key" },
      canon: {
        scene_id: "1A",
        situation: "A tense house.",
        pressure: "Find evidence.",
        revealed_knowledge: [{ id: "k_sl_1a_a_r1", statement: "The entry clue is committed." }],
      },
      fetchImpl: async (_url, options) => {
        request = JSON.parse(options.body);
        return new Response(JSON.stringify({ output_text: JSON.stringify({ verdict: "pass", canon_consistent: true, scene_local: true, progressive: true, rich: true, protected_safe: true, exit_motivated: true, rewards_investigation: true, missing_or_wrong: [], reasons: [] }) }), { status: 200 });
      },
    },
  );
  assert.equal(verdict.verdict, "pass");
  const requestContent = JSON.parse(request.input[1].content);
  assert.equal(requestContent.canon.scene_id, "1A");
  assert.deepEqual(requestContent.canon.revealed_knowledge, [{ id: "k_sl_1a_a_r1", statement: "The entry clue is committed." }]);
});

test("scene canon judge omits artifact evidence without mutating turns", async () => {
  let request;
  const turn = {
    prompt: "Search the desk.",
    player_input: "Search the desk.",
    narration: "You find a note.",
    left_scene: false,
    beats_projected: ["beat-1"],
    authored_spans: [{ text: "You find a note." }],
    knowledge_available: ["k-1"],
    segments: [{ kind: "narration", text: "You find a note.", grounding_ids: ["k-1"] }],
    bundle: {
      outcome: "continue",
      transition_cause: null,
      story_complete: false,
      selected_reveal: null,
      cue_stage: "none",
      committed_delta: {},
    },
  };

  await judgeSceneNarration(
    { sceneId: "1A", opening: "A tense house.", turns: [turn] },
    {
      environment: { OPENAI_API_KEY: "test-key" },
      canon: {
        scene_id: "1A",
        situation: "A tense house.",
        pressure: "Find evidence.",
        revealed_knowledge: [],
      },
      fetchImpl: async (_url, options) => {
        request = JSON.parse(options.body);
        return new Response(JSON.stringify({ output_text: JSON.stringify({ verdict: "pass", reasons: [] }) }), { status: 200 });
      },
    },
  );

  const sentTurn = JSON.parse(request.input[1].content).turns[0];
  assert.deepEqual(sentTurn, {
    player_input: "Search the desk.",
    narration: "You find a note.",
    left_scene: false,
    beats_projected: ["beat-1"],
    authored_spans: [{ text: "You find a note." }],
    knowledge_available: ["k-1"],
  });
  assert.deepEqual(turn.segments, [{ kind: "narration", text: "You find a note.", grounding_ids: ["k-1"] }]);
  assert.deepEqual(turn.bundle, {
    outcome: "continue",
    transition_cause: null,
    story_complete: false,
    selected_reveal: null,
    cue_stage: "none",
    committed_delta: {},
  });
});

test("scene canon judge distinguishes protected facts from ordinary invented details", async () => {
  let request;
  await judgeSceneNarration(
    { sceneId: "1A", opening: "A tense house.", turns: [] },
    {
      environment: { OPENAI_API_KEY: "test-key" },
      canon: { scene_id: "1A", situation: "A tense house.", pressure: "Find evidence.", revealed_knowledge: [] },
      fetchImpl: async (_url, options) => {
        request = JSON.parse(options.body);
        return new Response(JSON.stringify({ output_text: JSON.stringify({ verdict: "pass", canon_consistent: true, scene_local: true, progressive: true, rich: true, protected_safe: true, exit_motivated: true, rewards_investigation: true, missing_or_wrong: [], reasons: [] }) }), { status: 200 });
      },
    },
  );
  const systemMessage = request.input[0].content;
  assert.match(systemMessage, /Require characters, items, plot events, dialogue, and setting to remain consistent with the supplied canon and the committed timeline\. Judge runtime-authored text for quality, but do not attribute it to the narrator\./);
  assert.match(systemMessage, /knowledge_available_before_turn lists public knowledge already disclosed to the player\. runtime_deliveries lists the authored text delivered on this turn and its committed facts\. Earlier disclosures remain known in later scenes\. A later disclosure cannot excuse an earlier leak\./);
  assert.match(systemMessage, /Fail protected_safe only when narrator text discloses a protected fact from the supplied protected-fact inventory before it is available\. Identify the fact, turn and exact narrator text\. Runtime deliveries are exempt from narrator-disclosure penalties\./);
  assert.match(systemMessage, /Inventory items marked world_only are facts the player can never be told directly; narrator text that states one as established fact fails protected_safe\./);
  assert.doesNotMatch(systemMessage, /revealed_knowledge is the set of authored facts the player has earned by committed reveal/);
  assert.doesNotMatch(systemMessage, /not in revealed_knowledge/);
  assert.match(systemMessage, /ordinary invented detail.*color, a minor object, or a bit of atmosphere/);
  assert.match(systemMessage, /Turns may carry authored_spans, knowledge_available_before_turn, runtime_deliveries, and protected_facts\. The supplied runtime_deliveries identify text inserted by the runtime\. Exempt only those spans from narrator-disclosure penalties\. Judge all other text normally\. Use knowledge available before the turn\. Read the full turn when judging exit motivation and other quality checks\./);
  assert.doesNotMatch(systemMessage, /authored_delivery/);
  assert.match(systemMessage, /Text the narrator wrote itself that states a protected fact from the supplied protected-fact inventory before it is available is still premature disclosure/);
  assert.match(systemMessage, /Contradiction of established canon still fails canon_consistent/);
  assert.deepEqual(request.text.format.schema, {
    type: "object",
    properties: {
      verdict: { type: "string", enum: ["pass", "fail"] },
      canon_consistent: { type: "boolean" },
      scene_local: { type: "boolean" },
      progressive: { type: "boolean" },
      rich: { type: "boolean" },
      protected_safe: { type: "boolean" },
      exit_motivated: { type: "boolean" },
      rewards_investigation: { type: "boolean" },
      missing_or_wrong: { type: "array", items: { type: "string" } },
      reasons: { type: "array", items: { type: "string" } },
    },
    required: [
      "verdict", "canon_consistent", "scene_local", "progressive", "rich", "protected_safe",
      "exit_motivated", "rewards_investigation", "missing_or_wrong", "reasons",
    ],
    additionalProperties: false,
  });
});

test("sceneCanon returns only revealed knowledge for the current scene", () => {
  const canon = sceneCanon("1A", ["k_sl_1a_a_r1", "k_sl_1a_b_r1", "k_sl_1b_a_r1", "scene:1A"]);
  const require = createRequire(import.meta.url);
  const YAML = require("yaml");
  const knowledgePackage = YAML.parse(
    readFileSync(resolve(import.meta.dirname, "../../data/stories/continuity-initiative/knowledge.yaml"), "utf8"),
  );
  const expectedIds = ["k_sl_1a_a_r1", "k_sl_1a_b_r1"];
  const expectedKnowledge = expectedIds.map((id) => {
    const entry = knowledgePackage.knowledge.find((knowledge) => knowledge.id === id);
    return { id, statement: entry.statement };
  });

  assert.deepEqual(canon.revealed_knowledge, expectedKnowledge);
  assert.deepEqual(canon.revealed_knowledge.map((entry) => entry.id), ["k_sl_1a_a_r1", "k_sl_1a_b_r1"]);
  assert.deepEqual(Object.keys(canon).sort(), [
    "knowledge_available_before_turn",
    "pressure",
    "protected_facts",
    "revealed_knowledge",
    "runtime_deliveries",
    "scene_id",
    "situation",
  ]);
});
