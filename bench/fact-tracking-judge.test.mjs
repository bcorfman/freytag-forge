import test from "node:test";
import assert from "node:assert/strict";
import { judgeFactTracking, packageCanon } from "./fact-tracking-judge.mjs";

const turns = [
  {
    player_input: "Look at the lantern.",
    narration: "The lantern feels warm.",
    item_facts_before: { lantern: ["lit"] },
    item_facts_after: { lantern: ["warm"] },
    story_text: ["The story adds this sentence."],
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
        kept_ended_condition: "no",
        state_as_place: "no",
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
  assert.deepEqual(Object.keys(sent).sort(), ["item_facts_after", "item_facts_before", "narration", "player_input", "story_text", "turn_number"]);
  assert.deepEqual(sent.story_text, ["The story adds this sentence."]);
  assert.deepEqual(body.text.format.schema.properties.turns.items.required, [
    "turn",
    "facts_after_correct",
    "missed_change",
    "invented_change",
    "narration_contradicts_given_facts",
    "dropped_true_condition",
    "kept_ended_condition",
    "state_as_place",
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

test("fact rubric separates given conflicts and allows introduced refinements", async () => {
  const requests = [];
  await judgeFactTracking(
    { sceneId: "1A", opening: "", turns },
    { environment: { OPENAI_API_KEY: "test-key" }, fetchImpl: fakeFetch(verdict(), requests) },
  );
  const rubric = requests[0].input[0].content;
  assert.match(rubric, /facts_after_correct: answer only whether item_facts_after matches what the narration shows/);
  assert.match(rubric, /judge that only under narration_contradicts_given_facts/);
  assert.match(rubric, /A state the narration gives a thing must also be possible with the conditions item_facts_before records for it/);
  assert.match(rubric, /more specific place or state that fits inside the given one is consistent/);
  assert.match(rubric, /Compare meaning, not wording/);
  assert.match(rubric, /a cracked screen that later shatters is not dropped/);
  assert.doesNotMatch(rubric, /word for word/);
  assert.match(rubric, /not in item_facts_before but that the narration introduces is never an invented change/);
  assert.match(rubric, /An action the narration only attempts changes nothing/);
  assert.match(rubric, /An attempted handover that nobody takes changes nothing/);
  assert.match(rubric, /recording a laptop as closed when the narration only shows her carrying it out of the truck is invented/);
  assert.match(rubric, /item_facts_after listing open is no/);
});

test("rejects a verdict with the wrong turn count", async () => {
  const requests = [];
  await assert.rejects(
    judgeFactTracking(
      { sceneId: "1A", opening: "", turns },
      { environment: { OPENAI_API_KEY: "test-key" }, fetchImpl: fakeFetch({ turns: [] }, requests) },
    ),
    /missing: 1; unexpected: none/,
  );
  assert.equal(requests.length, 2);
});

test("retries a short verdict once and accepts the complete retry", async () => {
  const requests = [];
  let calls = 0;
  const fetchImpl = async (_url, options) => {
    requests.push(options);
    calls += 1;
    const result = calls === 1 ? { turns: [] } : verdict();
    return { ok: true, status: 200, json: async () => ({ output_text: JSON.stringify(result) }) };
  };
  const result = await judgeFactTracking(
    { sceneId: "1A", opening: "", turns },
    { environment: { OPENAI_API_KEY: "test-key" }, fetchImpl },
  );
  assert.equal(result.turns.length, 1);
  assert.equal(requests.length, 2);
});

test("uses one request for a complete verdict", async () => {
  const requests = [];
  await judgeFactTracking(
    { sceneId: "1A", opening: "", turns },
    { environment: { OPENAI_API_KEY: "test-key" }, fetchImpl: fakeFetch(verdict(), requests) },
  );
  assert.equal(requests.length, 1);
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

test("rejects a verdict missing kept_ended_condition", async () => {
  const incomplete = verdict();
  delete incomplete.turns[0].kept_ended_condition;
  await assert.rejects(
    judgeFactTracking(
      { sceneId: "1A", opening: "", turns },
      { environment: { OPENAI_API_KEY: "test-key" }, fetchImpl: fakeFetch(incomplete, []) },
    ),
    /invalid verdict/,
  );
});

test("rejects a verdict missing state_as_place", async () => {
  const incomplete = verdict();
  delete incomplete.turns[0].state_as_place;
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
      fetchImpl: fakeFetch({ turns: [{ ...verdict().turns[0], turn: 1 }, { ...verdict().turns[0], turn: 2 }] }, requests),
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

function numberedTurns(numbers) {
  return numbers.map((turn_number) => ({ ...turns[0], turn_number }));
}

test("sends and returns real turn numbers across a gap", async () => {
  const requests = [];
  const result = await judgeFactTracking(
    { sceneId: "1A", opening: "", turns: numberedTurns([1, 2, 3, 5]) },
    {
      environment: { OPENAI_API_KEY: "test-key" },
      fetchImpl: fakeFetch({ turns: [5, 1, 3, 2].map((turn) => verdict().turns[0] && { ...verdict().turns[0], turn }) }, requests),
    },
  );
  assert.deepEqual(JSON.parse(requests[0].input[1].content).turns.map((turn) => turn.turn_number), [1, 2, 3, 5]);
  assert.deepEqual(result.turns.map((turn) => turn.turn), [1, 2, 3, 5]);
});

test("retries positional numbers once and names missing and unexpected turns", async () => {
  const requests = [];
  await assert.rejects(
    judgeFactTracking(
      { sceneId: "1A", opening: "", turns: numberedTurns([1, 2, 3, 5]) },
      { environment: { OPENAI_API_KEY: "test-key" }, fetchImpl: fakeFetch({ turns: [1, 2, 3, 4].map((turn) => ({ ...verdict().turns[0], turn })) }, requests) },
    ),
    /missing: 5; unexpected: 4/,
  );
  assert.equal(requests.length, 2);
});

test("uses positional turn numbers when records have none", async () => {
  const requests = [];
  await judgeFactTracking(
    { sceneId: "1A", opening: "", turns: [{ ...turns[0] }, { ...turns[0] }] },
    {
      environment: { OPENAI_API_KEY: "test-key" },
      fetchImpl: fakeFetch({ turns: [{ ...verdict().turns[0], turn: 1 }, { ...verdict().turns[0], turn: 2 }] }, requests),
    },
  );
  assert.deepEqual(JSON.parse(requests[0].input[1].content).turns.map((turn) => turn.turn_number), [1, 2]);
});
