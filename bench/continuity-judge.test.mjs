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
      command_not_finished: "no",
      reveals_hidden_canon: "no",
      reason: "The narration picks up the phone.",
    },
  ],
};

test("continuity judge uses a strict schema and sends scene and given fields only", async () => {
  let request;
  const turns = [
    {
      player_input: "Look at the phone.",
      narration: "The phone lies on the floor.",
      story_text: ["The story adds this sentence."],
      scene_id: "1A",
      item_facts_before: { phone: { place: "her hands" } },
      item_facts_after: { phone: { place: "floor" } },
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
    {
      turn_number: 1,
      scene_id: "1A",
      player_input: "Look at the phone.",
      narration: "The phone lies on the floor.",
      given_facts: { phone: { place: "her hands" } },
      story_text: ["The story adds this sentence."],
    },
  ]);
  assert.doesNotMatch(request.input[0].content, /when no player command moved it/);
  assert.match(request.input[0].content, /story_text lists sentences at the end of the narration that the story itself wrote for this turn/);
  assert.match(request.input[0].content, /A command to look at, examine, search or check a thing is finished when the narration shows her attending to that thing/);
  assert.match(request.input[0].content, /She cannot control another character/);
  assert.match(request.input[0].content, /When she tries to take a thing from another character, trying is her whole part/);
  assert.match(request.input[0].content, /The narration does not have to say whether she gets it/);
  assert.match(request.input[0].content, /A refusal, a struggle or silence is still a response/);
  assert.doesNotMatch(request.input[0].content, /the narration must show what that character does; only holding a thing out is not finished/);
  assert.match(request.input[0].content, /drives away from the house does not finish drive to the park/);
  assert.match(request.input[0].content, /Repeating a journey the story already finished is also a restart/);
  assert.deepEqual(request.text.format.schema.properties.turns.items.required, [
    "turn",
    "contradicts_stated_fact",
    "protagonist_acts_beyond_command",
    "restarts_scene",
    "command_not_finished",
    "reveals_hidden_canon",
    "reason",
  ]);
});

test("packageCanon returns the whole scene block", () => {
  const canon = packageCanon("1A", "data/stories/continuity-initiative");
  assert.match(canon.plot, /Michelle's phone is not damaged\./);
  assert.doesNotMatch(canon.plot, /## Scene 1B/);
});

test("packageCanon includes extra scene blocks", () => {
  const canon = packageCanon("1A", "data/stories/continuity-initiative", ["1B"]);
  assert.match(canon.plot, /## Scene 1A/);
  assert.match(canon.plot, /## Scene 1B/);
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
