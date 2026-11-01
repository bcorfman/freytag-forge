import assert from "node:assert/strict";
import test from "node:test";

import { buildKnowledgeTimeline, loadCanonSources } from "./knowledge-available.js";
import { judgeSceneNarration, sceneCanon } from "./roleplay-judge.js";

const { knowledgePackage, routePackage } = loadCanonSources();

function committedBundle(knowledgeIds, facts = []) {
  return {
    outcome: "committed",
    selected_reveal: { knowledge_ids: knowledgeIds },
    committed_delta: { fact_predicates: facts },
  };
}

function entry(id) {
  return knowledgePackage.knowledge.find((candidate) => candidate.id === id);
}

function miniPlaythrough() {
  const deluge = entry("k_sl_3b_d_r1");
  return [
    ["2C", {
      turns: [{
        prompt: "Search the private message.",
        player_input: "Search the private message.",
        narration: "The message is not for Kristin.",
        bundle: committedBundle(["k_sl_2c_a_r1"], ["rebecca_offer_active"]),
        segments: [],
      }],
    }],
    ["3B", {
      turns: [{
        prompt: "Read Charles's remote channel.",
        player_input: "Read Charles's remote channel.",
        narration: deluge.delivery_text,
        authored_spans: [{ text: deluge.delivery_text, source_kind: "delivery", source_id: deluge.id }],
        bundle: committedBundle([deluge.id], ["charles_abandoned_rebecca"]),
        segments: [],
      }],
    }],
    ["3C", {
      turns: [
        {
          prompt: "Find a way through the flooding.",
          player_input: "Find a way through the flooding.",
          narration: "Water rises through the corridor.",
          bundle: committedBundle([], ["facility_collapse_escalating"]),
          segments: [],
        },
        {
          prompt: "Inspect the recovered file.",
          player_input: "Inspect the recovered file.",
          narration: "The file explains Phase Two.",
          bundle: committedBundle(["k_sl_3c_e_r1"], ["phase_two_conflict_plan_known"]),
          segments: [],
        },
      ],
    }],
  ];
}

test("builds chronological public knowledge and keeps same-turn deliveries out of before-turn evidence", () => {
  const timeline = buildKnowledgeTimeline({ scenes: miniPlaythrough(), knowledgePackage, routePackage });
  const scene2C = timeline.byScene.get("2C");
  const scene3B = timeline.byScene.get("3B");
  const scene3C = timeline.byScene.get("3C");
  const privateOffer = entry("k_sl_2c_a_r1");
  const phaseTwo = entry("k_sl_3c_e_r1");
  const privateOfferProtected = scene2C.turns[0].protected_facts.find(({ id }) => id === privateOffer.id);

  assert.equal(scene2C.turns[0].knowledge_available_before_turn.some(({ id }) => id === privateOffer.id), false);
  assert.equal(scene2C.turns[0].knowledge_available.some((id) => id === privateOffer.id), false);
  assert.deepEqual(privateOfferProtected, { id: privateOffer.id, statement: privateOffer.statement, world_only: true });
  assert.equal(scene3B.turns[0].knowledge_available_before_turn.some(({ id }) => id === "k_sl_3b_d_r1"), false);
  assert.equal(scene3B.turns[0].knowledge_available.includes("k_sl_3b_d_r1"), true);
  assert.equal(scene3C.turns[0].knowledge_available_before_turn.some(({ id }) => id === "k_sl_3b_d_r1"), true);
  assert.equal(scene3C.turns[0].knowledge_available_before_turn.some(({ id }) => id === privateOffer.id), false);
  assert.equal(scene3C.turns[0].protected_facts.some(({ id, statement }) => id === phaseTwo.id && statement === phaseTwo.statement), true);
  assert.equal(scene3C.turns[0].knowledge_available_before_turn.some(({ id }) => id === phaseTwo.id), false);
  assert.equal(scene3C.turns[1].knowledge_available_before_turn.some(({ id }) => id === phaseTwo.id), false);
  assert.deepEqual(scene3B.turns[0].runtime_deliveries.authored_spans, [delugeText()]);

  const canon = sceneCanon("2C", [privateOffer.id], undefined, {
    knowledgeAvailableBeforeTurn: [scene2C.turns[0].knowledge_available_before_turn],
  });
  assert.deepEqual(
    canon.protected_facts.find(({ id }) => id === privateOffer.id),
    { id: privateOffer.id, statement: privateOffer.statement, world_only: true },
  );
});

function delugeText() {
  return entry("k_sl_3b_d_r1").delivery_text;
}

test("reconstructed scene judge request carries typed evidence and no raw prompt", async () => {
  const timeline = buildKnowledgeTimeline({ scenes: miniPlaythrough(), knowledgePackage, routePackage });
  const scene = timeline.byScene.get("3C");
  let request;
  await judgeSceneNarration(
    { sceneId: "3C", opening: "The facility is collapsing.", turns: scene.turns.map((turn, index) => ({
      ...turn,
      prompt: `Raw prompt ${index + 1}`,
      player_input: "Inspect the evidence.",
      narration: "The narrator responds.",
      segments: [],
      bundle: committedBundle([], []),
    })) },
    {
      environment: { OPENAI_API_KEY: "test-key" },
      canon: sceneCanon("3C", [], undefined, { knowledgeAvailableBeforeTurn: scene.turns.map((turn) => turn.knowledge_available_before_turn) }),
      fetchImpl: async (_url, options) => {
        request = JSON.parse(options.body);
        return new Response(JSON.stringify({ output_text: JSON.stringify({ verdict: "pass", reasons: [] }) }), { status: 200 });
      },
    },
  );

  const sent = JSON.parse(request.input[1].content);
  assert.equal(sent.turns[0].knowledge_available_before_turn.some(({ id }) => id === "k_sl_3b_d_r1"), true);
  assert.equal(sent.turns[0].protected_facts.some(({ id }) => id === "k_sl_3c_e_r1"), true);
  assert.equal(sent.turns.every((turn) => !Object.hasOwn(turn, "prompt")), true);
  assert.deepEqual(sent.turns[0].runtime_deliveries, { authored_spans: [], committed_facts: ["facility_collapse_escalating"] });
});
