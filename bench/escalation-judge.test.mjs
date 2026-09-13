import assert from "node:assert/strict";
import test from "node:test";

import { judgeEscalation } from "./escalation-judge.mjs";

const verdict = {
  cue_points_to_missing_thread: "yes",
  complication_creates_pressure_without_unearned_knowledge: "not_applicable",
  no_pre_reveal_disclosure: "yes",
  reasons: [],
};

function response(value) {
  return new Response(JSON.stringify({ output_text: JSON.stringify(value) }), { status: 200 });
}

test("escalation judge sends the transcript with the strict schema", async () => {
  let request;
  const canon = { scene_id: "1A", plot: "**Hidden canon:** under the floorboard" };
  const turns = [{ cue_fact_id: "missing_fact", cue_text: "A loose floorboard." }];
  const result = await judgeEscalation(
    { sceneId: "1A", opening: "A quiet kitchen.", turns },
    {
      environment: { OPENAI_API_KEY: "test-key" },
      canon,
      fetchImpl: async (_url, options) => {
        request = JSON.parse(options.body);
        return response(verdict);
      },
    },
  );

  assert.deepEqual(result, verdict);
  assert.equal(request.model, "gpt-5.4");
  assert.equal(request.store, false);
  assert.equal(request.input[0].role, "system");
  assert.match(request.input[0].content, /not_applicable/);
  assert.deepEqual(JSON.parse(request.input[1].content), { canon, opening: "A quiet kitchen.", turns });
  assert.equal(request.text.format.type, "json_schema");
  assert.equal(request.text.format.name, "scene_escalation_judgment");
  assert.equal(request.text.format.strict, true);
  assert.deepEqual(request.text.format.schema.required, [
    "cue_points_to_missing_thread",
    "complication_creates_pressure_without_unearned_knowledge",
    "no_pre_reveal_disclosure",
    "reasons",
  ]);
  assert.equal(request.text.format.schema.additionalProperties, false);
});

test("escalation judge honors the model override", async () => {
  let request;
  await judgeEscalation(
    { sceneId: "1A", opening: "Opening.", turns: [] },
    {
      environment: { OPENAI_API_KEY: "test-key", E2E_JUDGE_MODEL: "test-model" },
      fetchImpl: async (_url, options) => {
        request = JSON.parse(options.body);
        return response(verdict);
      },
    },
  );
  assert.equal(request.model, "test-model");
});

test("escalation judge rejects an invalid verdict", async () => {
  await assert.rejects(
    judgeEscalation(
      { sceneId: "1A", opening: "Opening.", turns: [] },
      {
        environment: { OPENAI_API_KEY: "test-key" },
        fetchImpl: async () => response({ ...verdict, no_pre_reveal_disclosure: "maybe" }),
      },
    ),
    /invalid verdict/,
  );
});

test("escalation judge rejects a missing API key before fetching", async () => {
  let called = false;
  await assert.rejects(
    judgeEscalation(
      { sceneId: "1A", opening: "Opening.", turns: [] },
      {
        environment: {},
        fetchImpl: async () => {
          called = true;
          return response(verdict);
        },
      },
    ),
    /OPENAI_API_KEY/,
  );
  assert.equal(called, false);
});
