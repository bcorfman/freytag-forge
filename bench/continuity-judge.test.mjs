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
    { turn_number: 1, player_input: "Look at the phone.", narration: "The phone lies on the floor." },
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
    /wrong turn numbers/,
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

function continuityVerdict(turn) {
  return { ...verdict.turns[0], turn };
}

test("continuity judge sends and returns saved turn numbers across a gap", async () => {
  const requests = [];
  const result = await judgeContinuity(
    { sceneId: "1A", opening: "", turns: [1, 2, 3, 5].map((turn) => ({ turn_number: turn })) },
    {
      environment: { OPENAI_API_KEY: "test-key" },
      fetchImpl: async (_url, options) => {
        requests.push(JSON.parse(options.body));
        return response({ turns: [5, 1, 3, 2].map(continuityVerdict) });
      },
    },
  );
  assert.deepEqual(JSON.parse(requests[0].input[1].content).turns.map((turn) => turn.turn_number), [1, 2, 3, 5]);
  assert.deepEqual(result.turns.map((turn) => turn.turn), [1, 2, 3, 5]);
});

test("continuity judge retries positional numbers once and names the mismatch", async () => {
  let calls = 0;
  await assert.rejects(
    judgeContinuity(
      { sceneId: "1A", opening: "", turns: [1, 2, 3, 5].map((turn) => ({ turn_number: turn })) },
      {
        environment: { OPENAI_API_KEY: "test-key" },
        fetchImpl: async () => {
          calls += 1;
          return response({ turns: [1, 2, 3, 4].map(continuityVerdict) });
        },
      },
    ),
    /missing: 5; unexpected: 4/,
  );
  assert.equal(calls, 2);
});

test("continuity judge retries a short first reply", async () => {
  let calls = 0;
  const result = await judgeContinuity(
    { sceneId: "1A", opening: "", turns: [{ turn_number: 1 }, { turn_number: 2 }] },
    {
      environment: { OPENAI_API_KEY: "test-key" },
      fetchImpl: async () => response({ turns: calls++ === 0 ? [continuityVerdict(1)] : [continuityVerdict(1), continuityVerdict(2)] }),
    },
  );
  assert.deepEqual(result.turns.map((turn) => turn.turn), [1, 2]);
  assert.equal(calls, 2);
});

test("continuity judge falls back to positions when turn_number is absent", async () => {
  let sent;
  await judgeContinuity(
    { sceneId: "1A", opening: "", turns: [{}, {}, {}, {}] },
    {
      environment: { OPENAI_API_KEY: "test-key" },
      fetchImpl: async (_url, options) => {
        sent = JSON.parse(options.body);
        return response({ turns: [1, 2, 3, 4].map(continuityVerdict) });
      },
    },
  );
  assert.deepEqual(JSON.parse(sent.input[1].content).turns.map((turn) => turn.turn_number), [1, 2, 3, 4]);
});
