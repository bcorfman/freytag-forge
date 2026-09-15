import test from "node:test";
import assert from "node:assert/strict";
import { judgeFactTracking, packageCanon } from "./fact-tracking-judge.mjs";

const turns = [
  {
    player_input: "Look at the lantern.",
    narration: "The lantern feels warm.",
    item_facts_before: { lantern: ["lit"] },
    item_facts_after: { lantern: ["warm"] },
    secret: "must not be sent",
  },
];

function verdict(overrides = {}) {
  return {
    turns: [
      {
        turn: 1,
        facts_after_correct: "yes",
        missed_change: "no",
        invented_change: "no",
        narration_contradicts_given_facts: "no",
        dropped_true_condition: "no",
        changes: [{ thing: "lantern", change: "warm", cause: "command" }],
        reason: "The warmth is carried forward.",
        ...overrides,
      },
    ],
  };
}

function fakeFetch(result, capture) {
  return async (_url, options) => {
    capture.push(JSON.parse(options.body));
    return { ok: true, status: 200, json: async () => ({ output_text: JSON.stringify(result) }) };
  };
}

test("filters turn fields and uses the default model with the strict schema", async () => {
  const requests = [];
  const result = await judgeFactTracking(
    { sceneId: "1A", opening: "ignored", turns },
    { environment: { OPENAI_API_KEY: "test-key" }, fetchImpl: fakeFetch(verdict(), requests) },
  );
  const body = requests[0];
  const sent = JSON.parse(body.input[1].content).turns[0];

  assert.equal(result.turns.length, 1);
  assert.equal(body.model, "gpt-5.4");
  assert.equal(body.store, false);
  assert.match(body.input[0].content, /Use cause command only when the player's command itself asks for that change/);
  assert.match(body.input[0].content, /Looking at, examining, searching, or checking a thing does not ask for moving/);
  assert.deepEqual(Object.keys(sent).sort(), ["item_facts_after", "item_facts_before", "narration", "player_input"]);
  assert.deepEqual(body.text.format.schema.properties.turns.items.required, [
    "turn",
    "facts_after_correct",
    "missed_change",
    "invented_change",
    "narration_contradicts_given_facts",
    "dropped_true_condition",
    "changes",
    "reason",
  ]);
  assert.equal(body.text.format.strict, true);
  assert.equal(body.text.format.schema.additionalProperties, false);
  assert.equal(body.text.format.schema.properties.turns.items.additionalProperties, false);
  assert.equal(
    body.text.format.schema.properties.turns.items.properties.changes.items.additionalProperties,
    false,
  );
});

test("rejects a verdict with the wrong turn count", async () => {
  await assert.rejects(
    judgeFactTracking(
      { sceneId: "1A", opening: "", turns },
      { environment: { OPENAI_API_KEY: "test-key" }, fetchImpl: fakeFetch({ turns: [] }, []) },
    ),
    /invalid verdict/,
  );
});

test("rejects a verdict with a bad enum", async () => {
  await assert.rejects(
    judgeFactTracking(
      { sceneId: "1A", opening: "", turns },
      {
        environment: { OPENAI_API_KEY: "test-key" },
        fetchImpl: fakeFetch(verdict({ missed_change: "maybe" }), []),
      },
    ),
    /invalid verdict/,
  );
});

test("rejects a verdict missing dropped_true_condition", async () => {
  const incomplete = verdict();
  delete incomplete.turns[0].dropped_true_condition;
  await assert.rejects(
    judgeFactTracking(
      { sceneId: "1A", opening: "", turns },
      { environment: { OPENAI_API_KEY: "test-key" }, fetchImpl: fakeFetch(incomplete, []) },
    ),
    /invalid verdict/,
  );
});

test("passes scene_id when present and omits it otherwise", async () => {
  const requests = [];
  await judgeFactTracking(
    {
      sceneId: "1A",
      opening: "",
      turns: [{ ...turns[0], scene_id: "1B", secret: "must not be sent" }, turns[0]],
    },
    {
      environment: { OPENAI_API_KEY: "test-key" },
      fetchImpl: fakeFetch({ turns: [verdict().turns[0], verdict().turns[0]] }, requests),
    },
  );
  const sent = JSON.parse(requests[0].input[1].content).turns;
  assert.equal(sent[0].scene_id, "1B");
  assert.equal(Object.hasOwn(sent[1], "scene_id"), false);
  assert.equal(Object.hasOwn(sent[0], "secret"), false);
});

test("packages selected and extra scene blocks", () => {
  const withoutExtras = packageCanon("1A", "data/stories/continuity-initiative");
  assert.doesNotMatch(withoutExtras.plot, /## Scene 1B/);
  const withExtras = packageCanon("1A", "data/stories/continuity-initiative", ["1B", "1B", "1A"]);
  assert.match(withExtras.plot, /## Scene 1A/);
  assert.match(withExtras.plot, /## Scene 1B/);
  assert.doesNotMatch(withExtras.plot, /## Scene 1C/);
});

test("rejects a change with a bad cause", async () => {
  await assert.rejects(
    judgeFactTracking(
      { sceneId: "1A", opening: "", turns },
      {
        environment: { OPENAI_API_KEY: "test-key" },
        fetchImpl: fakeFetch(
          verdict({ changes: [{ thing: "lantern", change: "warm", cause: "story" }] }),
          [],
        ),
      },
    ),
    /invalid verdict/,
  );
});
