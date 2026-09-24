import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { combineContinuity, combineFact, hiddenCanon, judgeInput, parseEnvelope, THRESHOLD } from "./jev-judge.mjs";

const yes = (names) => Object.fromEntries(names.map((name) => [name, true]));
const item = (answersTrue, extra = {}) => ({ thing: "phone", trackedBefore: true, trackedAfter: true, placeChanged: false, conditionsChanged: false, newConditions: [], goneConditions: [], keptConditions: [], answersTrue, ...extra });
const splitCriteriaSuffixes = {
  names_place: {
    true: 'Example: "Carry the lamp up to the tower" names the tower.',
    false: 'Example: in "Look around the dock for anything left behind", "around the dock" says where to look, '
      + "so no place is named.",
  },
  needs_other: {
    true: 'Example: "Hand the letter to the captain" needs the captain to take it.',
  },
  take_from_other: {
    true: 'Example: "Take the key back from the captain."',
    false: 'Example: "Pick up the key from the table" takes it from a table, not from a person.',
  },
  own_part_done: {
    true: 'Example: told to look closely at the lamp, she studies it and then lifts it; '
      + 'looking was her whole part. Example: told to take the key back from the captain, '
      + 'she reaches for it and he closes his fist; trying was her whole part.',
  },
  other_responds: {
    true: 'Example: she reaches for the key and the captain closes his fist around it; refusing is a response.',
    false: 'Example: she holds the letter out to the captain and nothing else happens.',
  },
  given_start_conflict: {
    true: 'Example: the facts say the key is in her hand, but she picks it up from the table.',
  },
  rediscovers: {
    false: 'Example: she already saw the cracked lens, and now glances at it again while she works; '
      + 'that is not treating it as new.',
  },
  arrives: {
    true: 'Example: she is already in the lamp room, but the narration has her step into it and spot the lens.',
    false: 'Example: the command sends her down to the dock, and she walks there.',
  },
  repeats_trip: {
    true: 'Example: the opening had her row across the bay and tie up at the lighthouse dock; '
      + 'rowing across the bay again to reach that boat repeats the trip.',
  },
};
const commandRubric = [
  "A command is finished when she does her own part of it. Looking at, examining, searching or checking a thing is finished when she pays attention to it, even if she also picks it up. ",
  "Trying to take a thing from another character is her whole part, whether or not she gets it. When the command needs another character to act, any response counts, including a refusal, a struggle or silence; only holding a thing out with nothing shown in return is unfinished. ",
  "When the command names a place to go to or to bring a thing to, she must arrive there or clearly head there. `story_text` is written by the story after the narrator, and it counts as what happened.",
].join("");
const commandUnfinished = {
  type: "noul",
  instructions: "Does `narration` stop before the action that `command` asked for is done?",
  criteria: {
    true: [
      "The action is not done. She does not do her own part, she does not reach or clearly head to the place `command` names, ",
      "or `command` needs another character to act and no response from that character is shown. Only holding a thing out, ",
      "with nothing shown in return, is not done.",
    ].join(""),
    false: [
      "The action is done. Paying attention to a thing finishes a command to look at, examine, search or check it, even if she ",
      "also picks it up. Trying to take a thing from another character is her whole part. A refusal, a struggle or silence from ",
      "another character is still a response. `story_text` counts as what happened.",
    ].join(""),
  },
};

test("combineContinuity applies all rules", () => {
  assert.equal(combineContinuity(yes(["given_conflict", "beyond_command", "arrives", "rediscovers", "repeats_trip", "needs_other", "names_place"]), { firstTurnInScene: false, hasHiddenCanon: false }).contradicts_stated_fact, "yes");
  assert.equal(combineContinuity(yes(["arrives"]), { firstTurnInScene: true, hasHiddenCanon: false }).restarts_scene, "no");
  assert.equal(combineContinuity(yes(["own_part_done", "needs_other", "take_from_other"]), { firstTurnInScene: false, hasHiddenCanon: false }).command_not_finished, "no");
  assert.equal(combineContinuity(yes(["own_part_done", "needs_other"]), { firstTurnInScene: false, hasHiddenCanon: false }).command_not_finished, "yes");
  assert.equal(combineContinuity(yes(["own_part_done", "names_place"]), { firstTurnInScene: false, hasHiddenCanon: false }).command_not_finished, "yes");
  assert.equal(combineContinuity(yes(["hidden_shown"]), { firstTurnInScene: false, hasHiddenCanon: false }).reveals_hidden_canon, "no");
  assert.equal(combineContinuity(yes(["hidden_shown"]), { firstTurnInScene: false, hasHiddenCanon: true }).reveals_hidden_canon, "yes");
});

test("judgeInput supports continuity variants and judge selection", async () => {
  const dir = await packageDir("## Scene 1A\n**Hidden canon:** card under rug.");
  const turn = {
    scene_id: "1A",
    player_input: "Look at the desk.",
    narration: "She looks at the desk.",
    item_facts_before: {},
    item_facts_after: {},
  };
  const input = { runs: [{ opening: "", turns: [turn] }] };
  const options = {
    packagePath: dir,
    environment: { CLOUDFLARE_ACCOUNT_ID: "a", CLOUDFLARE_AI_TOKEN: "t" },
  };
  const baselineSeen = [];
  const baseline = await judgeInput(input, { ...options, fetchImpl: stubFetch(baselineSeen) });
  const preambleSeen = [];
  const preamble = await judgeInput(input, { ...options, variant: "preamble", fetchImpl: stubFetch(preambleSeen) });
  const preambleInput = JSON.parse(preambleSeen[0].options.body).input;
  assert.equal(preambleInput.state.task, "You are a continuity editor for an interactive story. A player types a command, and a narrator writes what happens next. You check one turn at a time: did the narrator carry out the command, keep the story consistent with what is already true, and continue from where the story left off?");
  assert.deepEqual(Object.keys(preambleInput.state), ["task", "command", "narration", "story_text", "given_facts", "opening", "earlier_narration", "hidden_canon"]);

  const preambleRequest = JSON.parse(preambleSeen[0].options.body).input;
  const newVariants = ["preamble-rubric", "preamble-holistic", "preamble-rubric-holistic"];
  for (const variant of newVariants) {
    const seen = [];
    const result = await judgeInput(input, { ...options, variant, fetchImpl: stubFetch(seen) });
    const request = JSON.parse(seen[0].options.body).input;
    const hasRubric = variant.includes("rubric");
    const hasHolistic = variant.includes("holistic");
    const expectedTask = hasRubric ? `${preambleInput.state.task} ${commandRubric}` : preambleInput.state.task;
    assert.equal(request.state.task, expectedTask);
    assert.deepEqual(Object.keys(request.state), Object.keys(preambleInput.state));
    assert.deepEqual(Object.keys(request.questions), hasHolistic
      ? [...Object.keys(preambleInput.questions), "command_unfinished"]
      : Object.keys(preambleInput.questions));
    if (hasHolistic) {
      assert.deepEqual(request.questions.command_unfinished, commandUnfinished);
    }
    assert.deepEqual(verdicts(result), verdicts(preamble));
    assert.equal(result.raw.every((record) => record.variant === variant), true);
  }
  assert.deepEqual(JSON.parse(preambleSeen[0].options.body).input, preambleRequest);

  for (const answer of [0.1, 0.9]) {
    const seen = [];
    const result = await judgeInput(input, {
      ...options,
      variant: "preamble-holistic",
      fetchImpl: answerFetch(seen, answer),
    });
    assert.deepEqual(verdicts(result), verdicts(preamble));
    assert.equal(result.raw[0].answers.command_unfinished.noul, answer);
    assert.equal(JSON.parse(seen[0].options.body).input.questions.command_unfinished.type, "noul");
  }

  const requestsByVariant = {};
  const resultsByVariant = {};
  for (const variant of ["split", "split-examples", "split-criteria"]) {
    const seen = [];
    const result = await judgeInput(input, { ...options, variant, fetchImpl: stubFetch(seen) });
    const requests = seen.map((entry) => JSON.parse(entry.options.body).input);
    requestsByVariant[variant] = requests;
    resultsByVariant[variant] = result;
    assert.equal(requests.length, 3);
    assert.deepEqual(requests.map((request) => Object.keys(request.state)), [
      ["command"],
      ["command", "narration", "story_text", "given_facts"],
      ["command", "narration", "opening", "earlier_narration", "hidden_canon", "given_facts"],
    ].map((keys) => variant === "split-examples" ? [...keys, "examples"] : keys));
    assert.deepEqual(requests.map((request) => Object.keys(request.questions)), [
      ["needs_other", "take_from_other", "names_place"],
      ["given_conflict", "given_start_conflict", "beyond_command", "own_part_done", "other_responds", "reaches_place"],
      ["earlier_conflict", "arrives", "rediscovers", "repeats_trip", "hidden_shown", "hidden_lookalike"],
    ]);
    assert.deepEqual(result.continuity.judgments, baseline.continuity.judgments);
    assert.equal(result.raw.every((record) => record.variant === variant), true);
    if (variant === "split-examples") assert.equal(requests[0].state.examples[0].answer, false);
    if (variant === "split-criteria") assert.deepEqual(requests.map((request) => request.state),
      requestsByVariant.split.map((request) => request.state));
  }
  assert.deepEqual(resultsByVariant["split-criteria"].continuity.judgments,
    resultsByVariant.split.continuity.judgments);
  for (const [variant, requests] of Object.entries(requestsByVariant)) {
    if (variant === "split" || variant === "split-examples") continue;
    for (let i = 0; i < requests.length; i++) {
      for (const [name, splitQuestion] of Object.entries(requestsByVariant.split[i].questions)) {
        const criteria = requests[i].questions[name].criteria;
        const suffixes = splitCriteriaSuffixes[name];
        for (const [side, text] of Object.entries(splitQuestion.criteria)) {
          assert.equal(criteria[side], suffixes?.[side] ? `${text} ${suffixes[side]}` : text);
        }
      }
    }
  }

  const continuitySeen = [];
  const continuityOnly = await judgeInput(input, { ...options, judges: "continuity", fetchImpl: stubFetch(continuitySeen) });
  assert.equal(continuitySeen.length, 1);
  assert.deepEqual(continuityOnly.fact.judgments, [{ turns: [] }]);
  assert.equal(continuityOnly.raw[0].variant, "baseline");
  const factSeen = [];
  const factInput = {
    runs: [{ turns: [{ ...turn, item_facts_before: { desk: { place: "room", condition: [] } }, item_facts_after: {} }] }],
  };
  const factOnly = await judgeInput(factInput, { ...options, judges: "fact", fetchImpl: stubFetch(factSeen) });
  assert.equal(factSeen.length, 1);
  assert.deepEqual(factOnly.continuity.judgments, [{ turns: [] }]);
  assert.equal(factOnly.raw[0].judge, "fact");
  await assert.rejects(() => judgeInput(input, { ...options, variant: "nope", fetchImpl: stubFetch([]) }), /Unknown continuity variant/);
  await rm(dir, { recursive: true, force: true });
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
  assert.equal(combineFact([item({ before_conflict: true })]).facts_after_correct, "yes");
  assert.equal(combineFact([item({ start_conflict: true })]).narration_contradicts_given_facts, "yes");
  assert.equal(combineFact([item({ start_conflict: true })]).facts_after_correct, "yes");
  assert.equal(combineFact([item({ same_as_other: true }, { trackedBefore: false, trackedAfter: true })]).invented_change, "yes");
  assert.equal(combineFact([item({}, { trackedBefore: false, trackedAfter: true })]).invented_change, "no");
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

function answerFetch(seen, unfinishedAnswer) {
  return async (url, options) => {
    seen.push({ url, options });
    const body = JSON.parse(options.body);
    const answers = Object.fromEntries(Object.keys(body.input.questions).map((name) => [name, {
      type: "noul", noul: name === "command_unfinished" ? unfinishedAnswer : 0.1,
    }]));
    return { status: 200, json: async () => ({
      success: true, errors: [], result: { state: "Completed", result: { model: "jev-1", answers, usage: {} } },
    }) };
  };
}

function verdicts(result) {
  return result.continuity.judgments.map((run) => ({
    turns: run.turns.map(({ reason, ...turn }) => turn),
  }));
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
  const continuityQuestions = JSON.parse(seen[0].options.body).input.questions;
  assert.ok(Object.hasOwn(continuityQuestions, "given_start_conflict"));
  assert.ok(Object.hasOwn(continuityQuestions, "hidden_lookalike"));
  await rm(dir, { recursive: true, force: true });
});

test("judgeInput sends start and duplicate-name fact questions", async () => {
  const dir = await packageDir();
  const seen = [];
  const input = {
    runs: [{ turns: [{
      scene_id: "1A",
      player_input: "Take the laptop.",
      narration: "She takes the laptop.",
      item_facts_before: { "Kristin's laptop": { place: "desk", condition: [] } },
      item_facts_after: {
        "Kristin's laptop": { place: "desk", condition: [] },
        laptop: { place: "hands", condition: [] },
      },
    }] }],
  };
  await judgeInput(input, {
    packagePath: dir,
    environment: { CLOUDFLARE_ACCOUNT_ID: "a", CLOUDFLARE_AI_TOKEN: "t" },
    fetchImpl: stubFetch(seen),
  });
  const factRequests = seen.slice(1).map((entry) => JSON.parse(entry.options.body).input);
  const existingThing = factRequests.find((request) => request.state.thing === "Kristin's laptop");
  const newThing = factRequests.find((request) => request.state.thing === "laptop");
  assert.deepEqual(existingThing.state.other_things, ["laptop"]);
  assert.deepEqual(newThing.state.other_things, ["Kristin's laptop"]);
  assert.ok(Object.hasOwn(existingThing.questions, "start_conflict"));
  assert.ok(Object.hasOwn(newThing.questions, "same_as_other"));
  await rm(dir, { recursive: true, force: true });
});

test("hidden look-alike only reveals hidden canon when canon exists", async () => {
  const withCanon = await packageDir("## Scene 1A\n**Hidden canon:** card under rug.");
  const withoutCanon = await packageDir();
  const seen = [];
  const base = { scene_id: "1A", player_input: "Look around.", narration: "x", item_facts_before: {}, item_facts_after: {} };
  const options = { environment: { CLOUDFLARE_ACCOUNT_ID: "a", CLOUDFLARE_AI_TOKEN: "t" }, fetchImpl: stubFetch(seen) };
  await judgeInput({ runs: [{ turns: [base] }] }, { packagePath: withCanon, ...options });
  await judgeInput({ runs: [{ turns: [base] }] }, { packagePath: withoutCanon, ...options });
  assert.ok(Object.hasOwn(JSON.parse(seen[0].options.body).input.questions, "hidden_lookalike"));
  assert.ok(!Object.hasOwn(JSON.parse(seen[1].options.body).input.questions, "hidden_lookalike"));
  await rm(withCanon, { recursive: true, force: true });
  await rm(withoutCanon, { recursive: true, force: true });
});

test("repeats_trip wording names opening", async () => {
  const dir = await packageDir();
  const seen = [];
  await judgeInput({ runs: [{ opening: "She drove to the house.", turns: [{ scene_id: "1A", player_input: "Look around.", narration: "x", item_facts_before: {}, item_facts_after: {} }] }] }, {
    packagePath: dir,
    environment: { CLOUDFLARE_ACCOUNT_ID: "a", CLOUDFLARE_AI_TOKEN: "t" },
    fetchImpl: stubFetch(seen),
  });
  const question = JSON.parse(seen[0].options.body).input.questions.repeats_trip;
  assert.match(question.instructions, /opening/);
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
