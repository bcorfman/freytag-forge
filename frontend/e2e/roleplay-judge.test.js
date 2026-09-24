import assert from "node:assert/strict";
import test from "node:test";

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

test("sceneCanon returns only revealed knowledge for the current scene", () => {
  const canon = sceneCanon("1A", ["k_sl_1a_a_r1", "k_sl_1a_b_r1", "k_sl_1b_a_r1", "scene:1A"]);

  assert.deepEqual(canon.revealed_knowledge, [
    {
      id: "k_sl_1a_a_r1",
      statement:
        "Kristin traces the forced entry, overturned chair, missing tablet and work bag, and Michelle’s undamaged phone to a removal too deliberate to be looting.",
    },
    {
      id: "k_sl_1a_b_r1",
      statement:
        "Kristin finds and secures Michelle's memory card, then reads its damaged recording and files; the card points to a dead drop at a bench in the park.",
    },
  ]);
  assert.deepEqual(Object.keys(canon).sort(), ["pressure", "revealed_knowledge", "scene_id", "situation"]);
});
