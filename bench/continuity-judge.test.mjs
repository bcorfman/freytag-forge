import assert from "node:assert/strict";
import test from "node:test";

import { judgeContinuity, packageCanon } from "./continuity-judge.mjs";

function response(value) {
  return new Response(JSON.stringify({ output_text: JSON.stringify(value) }), { status: 200 });
}

const verdict = {
  turns: [
    {
      turn: 1,
      contradicts_stated_fact: "no",
      protagonist_acts_beyond_command: "yes",
      restarts_scene: "no",
      reason: "The narration picks up the phone.",
    },
  ],
};

test("continuity judge uses a strict schema and only sends player-visible turn fields", async () => {
  let request;
  const turns = [
    {
      player_input: "Look at the phone.",
      narration: "The phone lies on the floor.",
      candidates_offered: ["must not leak"],
      selected_knowledge_ids: ["must not leak"],
    },
  ];
  const result = await judgeContinuity(
    { sceneId: "1A", opening: "A quiet house.", turns },
    {
      environment: { OPENAI_API_KEY: "test-key" },
      canon: { scene_id: "1A", plot: "The canon." },
      fetchImpl: async (_url, options) => {
        request = JSON.parse(options.body);
        return response(verdict);
      },
    },
  );

  assert.deepEqual(result, verdict);
  assert.equal(request.model, "gpt-5.4");
  assert.equal(request.store, false);
  assert.equal(request.text.format.type, "json_schema");
  assert.equal(request.text.format.strict, true);
  assert.deepEqual(request.text.format.schema.required, [
    "turns",
  ]);
  assert.equal(request.text.format.schema.additionalProperties, false);
  assert.equal(request.text.format.schema.properties.turns.items.additionalProperties, false);
  assert.deepEqual(JSON.parse(request.input[1].content).turns, [
    { player_input: "Look at the phone.", narration: "The phone lies on the floor." },
  ]);
});

test("packageCanon returns the whole scene block", () => {
  const canon = packageCanon("1A", "data/stories/continuity-initiative");
  assert.match(canon.plot, /Michelle's phone is not damaged\./);
  assert.doesNotMatch(canon.plot, /## Scene 1B/);
});

test("continuity judge rejects the wrong number of turns and invalid verdicts", async () => {
  const options = { environment: { OPENAI_API_KEY: "test-key" }, fetchImpl: async () => response({ turns: [] }) };
  await assert.rejects(
    judgeContinuity({ sceneId: "1A", opening: "Opening.", turns: [{ player_input: "Look.", narration: "Seen." }] }, options),
    /invalid verdict/,
  );
  await assert.rejects(
    judgeContinuity(
      { sceneId: "1A", opening: "Opening.", turns: [{ player_input: "Look.", narration: "Seen." }] },
      {
        ...options,
        fetchImpl: async () => response({ turns: [{ ...verdict.turns[0], contradicts_stated_fact: "maybe" }] }),
      },
    ),
    /invalid verdict/,
  );
});
