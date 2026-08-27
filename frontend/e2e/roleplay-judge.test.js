import assert from "node:assert/strict";
import test from "node:test";

import { judgeRoleplayTurn, judgeSceneNarration } from "./roleplay-judge.js";

test("roleplay judge sends the transcript and parses a passing structured verdict", async () => {
  let request;
  const verdict = await judgeRoleplayTurn(
    { opening: "The room is quiet.", playerInput: "I inspect the desk.", narration: "You open the desk drawer." },
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
  assert.equal(request.model, "gpt-5.4");
  assert.equal(request.store, false);
  assert.match(request.input[0].content, /Creative additions are allowed/);
  assert.equal(JSON.parse(request.input[1].content).player_input, "I inspect the desk.");
});

test("scene canon judge sends only the current scene canon and parses its verdict", async () => {
  let request;
  const verdict = await judgeSceneNarration(
    { sceneId: "1A", opening: "A tense house.", turns: [{ player_input: "I search.", narration: "A clue." }] },
    {
      environment: { OPENAI_API_KEY: "test-key" },
      canon: { scene_id: "1A", plot: "canon", storylets: "guidance", routes: "routes", pacing: "pace", world: "world" },
      fetchImpl: async (_url, options) => {
        request = JSON.parse(options.body);
        return new Response(JSON.stringify({ output_text: JSON.stringify({ verdict: "pass", canon_consistent: true, scene_local: true, progressive: true, rich: true, protected_safe: true, missing_or_wrong: [], reasons: [] }) }), { status: 200 });
      },
    },
  );
  assert.equal(verdict.verdict, "pass");
  assert.equal(JSON.parse(request.input[1].content).canon.scene_id, "1A");
});
