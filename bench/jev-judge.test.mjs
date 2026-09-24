import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { combineContinuity, combineFact, hiddenCanon, judgeInput, parseEnvelope, THRESHOLD } from "./jev-judge.mjs";

const yes = (names) => Object.fromEntries(names.map((name) => [name, true]));
const item = (answersTrue, extra = {}) => ({ thing: "phone", trackedBefore: true, trackedAfter: true, placeChanged: false, conditionsChanged: false, newConditions: [], goneConditions: [], keptConditions: [], answersTrue, ...extra });

test("combineContinuity applies all rules", () => {
  assert.equal(combineContinuity(yes(["given_conflict", "beyond_command", "arrives", "rediscovers", "repeats_trip", "needs_other", "names_place"]), { firstTurnInScene: false, hasHiddenCanon: false }).contradicts_stated_fact, "yes");
  assert.equal(combineContinuity(yes(["arrives"]), { firstTurnInScene: true, hasHiddenCanon: false }).restarts_scene, "no");
  assert.equal(combineContinuity(yes(["own_part_done", "needs_other", "take_from_other"]), { firstTurnInScene: false, hasHiddenCanon: false }).command_not_finished, "no");
  assert.equal(combineContinuity(yes(["own_part_done", "needs_other"]), { firstTurnInScene: false, hasHiddenCanon: false }).command_not_finished, "yes");
  assert.equal(combineContinuity(yes(["own_part_done", "names_place"]), { firstTurnInScene: false, hasHiddenCanon: false }).command_not_finished, "yes");
  assert.equal(combineContinuity(yes(["hidden_shown"]), { firstTurnInScene: false, hasHiddenCanon: false }).reveals_hidden_canon, "no");
  assert.equal(combineContinuity(yes(["hidden_shown"]), { firstTurnInScene: false, hasHiddenCanon: true }).reveals_hidden_canon, "yes");
});

test("combineFact applies tracking rules and causes", () => {
  const result = combineFact([
    item({ moved: true, command_asks: true }, { placeChanged: true }),
    item({ condition_changed: true, command_asks: false }, { thing: "drawer", conditionsChanged: true, newConditions: ["open"], goneConditions: ["shut"], keptConditions: ["cracked"] }),
    item({ new_condition_0: false }, { thing: "lamp", newConditions: ["on"] }),
    item({ gone_condition_0: false }, { thing: "box", goneConditions: ["sealed"] }),
    item({ kept_condition_0: true }, { thing: "gate", keptConditions: ["shut"] }),
    item({ place_is_condition: true }, { thing: "screen" }),
  ]);
  assert.equal(result.facts_after_correct, "no");
  assert.equal(result.invented_change, "yes");
  assert.equal(result.dropped_true_condition, "yes");
  assert.equal(result.kept_ended_condition, "yes");
  assert.equal(result.state_as_place, "yes");
  assert.deepEqual(result.changes, [
    { thing: "phone", change: "moved", cause: "command" },
    { thing: "drawer", change: "condition changed", cause: "narrator" },
  ]);
  assert.equal(combineFact([item({ moved: true, after_place_right: true }, { trackedBefore: false, trackedAfter: true, placeChanged: true })]).invented_change, "no");
  assert.equal(combineFact([item({ moved: false }, { trackedBefore: true, trackedAfter: true })]).facts_after_correct, "yes");
});

test("hiddenCanon extracts one scene only", () => {
  const plot = "## Scene 1A\n**Hidden canon:** a key is under the rug.\n## Scene 1B\nVisible text.";
  assert.equal(hiddenCanon(plot, "1A"), "a key is under the rug.");
  assert.equal(hiddenCanon(plot, "1B"), "");
  assert.equal(hiddenCanon(plot, "9Z"), "");
});

test("parseEnvelope accepts success and rejects each failure", () => {
  const good = { success: true, errors: [], result: { state: "Completed", result: { model: "jev-1", answers: { a: { type: "noul", noul: THRESHOLD } }, usage: { input_tokens: 1 } } } };
  assert.deepEqual(parseEnvelope(200, good, ["a"]).model, "jev-1");
  for (const [status, json, part] of [[500, good, "HTTP"], [200, { ...good, success: false, errors: [{ message: "bad" }] }, "bad"], [200, { ...good, result: { ...good.result, state: "Failed" } }, "Failed"], [200, { ...good, result: { ...good.result, result: { ...good.result.result, answers: {} } } }, "missing answer"]]) {
    assert.throws(() => parseEnvelope(status, json, ["a"]), new RegExp(part));
  }
});

async function packageDir(plot = "## Scene 1A\nVisible.") {
  const dir = await mkdtemp(join(tmpdir(), "jev-judge-")); await writeFile(join(dir, "plot.md"), plot); return dir;
}
function stubFetch(seen, failureAt = 0) {
  return async (url, options) => {
    seen.push({ url, options }); if (failureAt && seen.length === failureAt) return { status: 500, json: async () => ({ success: false, errors: [{ message: "stop" }] }) };
    const body = JSON.parse(options.body); const answers = Object.fromEntries(Object.keys(body.input.questions).map((name) => [name, { type: "noul", noul: 0.1 }]));
    return { status: 200, json: async () => ({ success: true, errors: [], result: { state: "Completed", result: { model: "jev-1", answers, usage: {} } } }) };
  };
}

test("judgeInput is offline, sequential, and builds scoped continuity state", async () => {
  const dir = await packageDir("## Scene 1A\n**Hidden canon:** key under rug.\n## Scene 1B\nNone."); const seen = [];
  const input = { runs: [{ replicate: "r", opening: "start", turns: [
    { scene_id: "1A", player_input: "Look at the desk.", narration: "n0", narrator_narration: "v0", story_text: [], item_facts_before: {}, item_facts_after: {} },
    { scene_id: "1A", player_input: "Look at the rug.", narration: "n1", narrator_narration: "v1", story_text: [], item_facts_before: {}, item_facts_after: {} },
    { scene_id: "1A", player_input: "Look at the key.", narration: "n2", narrator_narration: "v2", story_text: [], item_facts_before: {}, item_facts_after: {} },
    { scene_id: "1B", player_input: "Look around.", narration: "n3", narrator_narration: "v3", story_text: [], item_facts_before: {}, item_facts_after: {} },
  ] }] };
  const result = await judgeInput(input, { packagePath: dir, environment: { CLOUDFLARE_ACCOUNT_ID: "a", CLOUDFLARE_AI_TOKEN: "t" }, fetchImpl: stubFetch(seen) });
  assert.equal(result.continuity.judge_calls, 4); assert.equal(result.fact.judge_calls, 0); assert.equal(result.raw.length, 4);
  const states = seen.map((x) => JSON.parse(x.options.body).input.state);
  assert.equal(states[0].opening, "start"); assert.deepEqual(states[2].earlier_narration, ["v0", "v1"]); assert.equal(states[3].opening, ""); assert.ok(!Object.hasOwn(JSON.parse(seen[3].options.body).input.questions, "hidden_shown"));
  await rm(dir, { recursive: true, force: true });
});

test("judgeInput stops on first error, guards size, and checks credentials", async () => {
  const dir = await packageDir(); const input = { runs: [{ replicate: "r", opening: "", turns: [{ player_input: "Look at the desk.", narration: "x", scene_id: "1A" }] }] };
  const seen = []; await assert.rejects(() => judgeInput(input, { packagePath: dir, environment: { CLOUDFLARE_ACCOUNT_ID: "a", CLOUDFLARE_AI_TOKEN: "t" }, fetchImpl: stubFetch(seen, 1) }), /HTTP/); assert.equal(seen.length, 1);
  await assert.rejects(() => judgeInput(input, { packagePath: dir, environment: {} }), /required/);
  const huge = { runs: [{ turns: [{ ...input.runs[0].turns[0], narration: "x".repeat(130000) }] }] }; const guarded = [];
  await assert.rejects(() => judgeInput(huge, { packagePath: dir, environment: { CLOUDFLARE_ACCOUNT_ID: "a", CLOUDFLARE_AI_TOKEN: "t" }, fetchImpl: stubFetch(guarded) }), /30000/); assert.equal(guarded.length, 0);
  await rm(dir, { recursive: true, force: true });
});

test("judgeInput rejects a later Jev model version", async () => {
  const dir = await packageDir(); let calls = 0;
  const fetchImpl = async (_url, options) => {
    calls += 1;
    const questions = JSON.parse(options.body).input.questions;
    const answers = Object.fromEntries(Object.keys(questions).map((name) => [name, { type: "noul", noul: 0.1 }]));
    return { status: 200, json: async () => ({ success: true, errors: [], result: { state: "Completed", result: { model: calls === 1 ? "jev-1" : "jev-2", answers, usage: {} } } }) };
  };
  const input = { runs: [{ turns: [{ scene_id: "1A", player_input: "Look at the desk.", narration: "x", item_facts_before: {}, item_facts_after: {} }, { scene_id: "1A", player_input: "Look at the door.", narration: "y", item_facts_before: {}, item_facts_after: {} }] }] };
  await assert.rejects(() => judgeInput(input, { packagePath: dir, environment: { CLOUDFLARE_ACCOUNT_ID: "a", CLOUDFLARE_AI_TOKEN: "t" }, fetchImpl }), /model changed/);
  assert.equal(calls, 2);
  await rm(dir, { recursive: true, force: true });
});
