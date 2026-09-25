import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

export const THRESHOLD = 0.5;

const CONTINUITY_NAMES = [
  "given_conflict", "given_start_conflict", "earlier_conflict", "beyond_command",
  "arrives", "rediscovers", "repeats_trip", "own_part_done", "needs_other",
  "take_from_other", "other_responds", "names_place", "reaches_place", "hidden_shown",
  "hidden_lookalike",
];
const FACT_NAMES = [
  "moved", "condition_changed", "after_place_right", "before_conflict", "start_conflict",
  "place_is_condition", "command_asks", "same_as_other",
];

const CONTINUITY_PREAMBLE = [
  "You are a continuity editor for an interactive story. A player types a command, and a narrator writes what happens next. ",
  "You check one turn at a time: did the narrator carry out the command, keep the story consistent with what is already true, ",
  "and continue from where the story left off?",
].join("");
const COMMAND_RUBRIC = [
  "A command is finished when she does her own part of it. Looking at, examining, searching or checking a thing is finished when she pays attention to it, even if she also picks it up. ",
  "Trying to take a thing from another character is her whole part, whether or not she gets it. When the command needs another character to act, any response counts, including a refusal, a struggle or silence; only holding a thing out with nothing shown in return is unfinished. ",
  "When the command names a place to go to or to bring a thing to, she must arrive there or clearly head there. `story_text` is written by the story after the narrator, and it counts as what happened.",
].join("");
const COMMAND_UNFINISHED = {
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
const CONTINUITY_VARIANTS = [
  "baseline", "preamble", "preamble-rubric", "preamble-holistic",
  "preamble-rubric-holistic",
  "split", "split-examples", "split-criteria",
];
const CONTINUITY_EXAMPLES = {
  command: [
    {
      command: "Look around the dock for anything left behind.", question: "names_place", answer: false,
      why: "\"Around the dock\" says where to look. It is not a place she must go to or put something.",
    },
    {
      command: "Carry the lamp up to the tower.", question: "names_place", answer: true,
      why: "The tower is where she must bring the lamp.",
    },
    {
      command: "Hand the letter to the captain.", question: "needs_other", answer: true,
      why: "The captain has to take the letter.",
    },
    {
      command: "Take the key back from the captain.", question: "take_from_other", answer: true,
      why: "She is told to take a thing from someone.",
    },
    {
      command: "Pick up the key from the table.", question: "take_from_other", answer: false,
      why: "The key is on a table, not held by another character.",
    },
  ],
  turn: [
    {
      command: "Look closely at the lamp.", narration: "Ana studies the lamp, then lifts it to check the base.",
      question: "own_part_done", answer: true,
      why: "Looking at the lamp is her whole part. Picking it up as well does not undo that.",
    },
    {
      command: "Take the key back from the captain.",
      narration: "Ana reaches for the key, but the captain closes his fist around it.",
      question: "own_part_done", answer: true, why: "Trying to take it is her whole part.",
    },
    {
      command: "Take the key back from the captain.",
      narration: "Ana reaches for the key, but the captain closes his fist around it.",
      question: "other_responds", answer: true, why: "Refusing is a response.",
    },
    {
      command: "Hand the letter to the captain.", narration: "Ana holds the letter out to him.",
      question: "other_responds", answer: false,
      why: "Holding it out, with no reaction shown, is not a response.",
    },
    {
      command: "Put the key in my pocket.", given_facts: { key: { place: "in Ana's hand", condition: [] } },
      narration: "Ana picks the key up from the table and pockets it.", question: "given_start_conflict", answer: true,
      why: "The facts say the key was in her hand, but the narration takes it from the table.",
    },
  ],
  history: [
    {
      earlier_narration: ["Ana climbs to the lamp room and sees the cracked lens."],
      narration: "Ana works on the lamp, glancing again at the cracked lens.", question: "rediscovers", answer: false,
      why: "Noticing something already known is not treating it as new.",
    },
    {
      earlier_narration: ["Ana climbs to the lamp room and sees the cracked lens."],
      narration: "Ana steps into the lamp room and spots a cracked lens.", question: "arrives", answer: true,
      why: "She is already in the lamp room, but the narration has her enter it as if new.",
    },
    {
      command: "Go down to the dock.", earlier_narration: ["Ana climbs to the lamp room."],
      narration: "Ana walks down the stairs to the dock.", question: "arrives", answer: false,
      why: "The command sent her to the dock.",
    },
    {
      opening: "Ana rows across the bay to the lighthouse and ties up at its dock.",
      narration: "Ana rows across the bay again to fetch her bag from the boat at the dock.",
      question: "repeats_trip", answer: true,
      why: "The boat is at the lighthouse dock, so crossing the bay again repeats a finished trip.",
    },
  ],
};
const CONTINUITY_GROUPS = {
  command: {
    state: ["command"], questions: ["needs_other", "take_from_other", "names_place"],
  },
  turn: {
    state: ["command", "narration", "story_text", "given_facts"],
    questions: [
      "given_conflict", "given_start_conflict", "beyond_command", "own_part_done", "other_responds", "reaches_place",
    ],
  },
  history: {
    state: ["command", "narration", "opening", "earlier_narration", "hidden_canon", "given_facts"],
    questions: ["earlier_conflict", "arrives", "rediscovers", "repeats_trip", "hidden_shown", "hidden_lookalike"],
  },
};
const SPLIT_CRITERIA_SUFFIXES = {
  names_place: {
    true: 'Example: "Carry the lamp up to the tower" names the tower.',
    false: 'Example: in "Look around the dock for anything left behind", "around the dock" says where to look, '
      + 'so no place is named.',
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

function nounl(instructions, truth, falsity) {
  return { type: "noul", instructions, criteria: { true: truth, false: falsity } };
}

export function hiddenCanon(plotText, sceneId) {
  const match = plotText.match(new RegExp(`^## Scene ${sceneId}\\b[\\s\\S]*?(?=^## Scene |(?![\\s\\S]))`, "m"));
  if (!match) return "";
  const line = match[0].match(/^\*\*Hidden canon:\*\*\s*(.*)$/m);
  return line ? line[1].trim() : "";
}

export function parseEnvelope(httpStatus, json, asked = []) {
  const errors = Array.isArray(json?.errors)
    ? json.errors.map((error) => typeof error === "string" ? error : error?.message || JSON.stringify(error)).join("; ")
    : "";
  const fail = (message) => {
    throw new Error(`Jev request failed with HTTP ${httpStatus}: ${message}${errors ? ` (${errors})` : ""}`);
  };
  if (httpStatus < 200 || httpStatus >= 300) fail("HTTP error");
  if (json?.success !== true) fail("success was not true");
  if (json?.result?.state !== "Completed") fail(`result state was ${json?.result?.state || "missing"}`);
  const result = json.result.result;
  if (!result || typeof result.model !== "string" || !result.answers || typeof result.answers !== "object") {
    fail("missing result");
  }
  for (const name of asked) if (!Object.hasOwn(result.answers, name)) fail(`missing answer ${name}`);
  return { model: result.model, answers: result.answers, usage: result.usage };
}

export function combineContinuity(a, { firstTurnInScene, hasHiddenCanon }) {
  const yes = (name) => Boolean(a[name]);
  return {
    contradicts_stated_fact: yes("given_conflict") || yes("given_start_conflict") || yes("earlier_conflict")
      ? "yes" : "no",
    protagonist_acts_beyond_command: yes("beyond_command") ? "yes" : "no",
    restarts_scene: !firstTurnInScene && (yes("arrives") || yes("rediscovers") || yes("repeats_trip")) ? "yes" : "no",
    command_not_finished: !yes("own_part_done")
      || (yes("needs_other") && !yes("take_from_other") && !yes("other_responds"))
      || (yes("names_place") && !yes("reaches_place")) ? "yes" : "no",
    reveals_hidden_canon: hasHiddenCanon && (yes("hidden_shown") || yes("hidden_lookalike")) ? "yes" : "no",
  };
}

export function combineFact(items) {
  const verdict = {
    missed_change: false,
    invented_change: false,
    narration_contradicts_given_facts: false,
    dropped_true_condition: false,
    kept_ended_condition: false,
    state_as_place: false,
  };
  const changes = [];
  for (const item of items) {
    const q = item.answersTrue;
    const moved = Boolean(q.moved);
    const conditionChanged = Boolean(q.condition_changed);
    const missed = (moved && !item.placeChanged && (item.trackedAfter || item.trackedBefore))
      || (moved && !item.trackedAfter)
      || (conditionChanged && !item.conditionsChanged);
    const invented = (item.placeChanged && !q.after_place_right)
      || item.newConditions.some((_, i) => q[`new_condition_${i}`] === false)
      || (!item.trackedBefore && item.trackedAfter && q.same_as_other);
    const dropped = item.goneConditions.some((_, i) => q[`gone_condition_${i}`] === false);
    const kept = item.keptConditions.some((_, i) => q[`kept_condition_${i}`]);
    verdict.missed_change ||= missed;
    verdict.invented_change ||= invented;
    verdict.narration_contradicts_given_facts ||= Boolean(q.before_conflict) || Boolean(q.start_conflict);
    verdict.dropped_true_condition ||= dropped;
    verdict.kept_ended_condition ||= kept;
    verdict.state_as_place ||= Boolean(q.place_is_condition);
    if (moved || conditionChanged) {
      changes.push({
        thing: item.thing,
        change: moved && conditionChanged ? "moved and condition changed" : moved ? "moved" : "condition changed",
        cause: q.command_asks ? "command" : "narrator",
      });
    }
  }
  const out = {};
  out.missed_change = verdict.missed_change ? "yes" : "no";
  out.invented_change = verdict.invented_change ? "yes" : "no";
  out.narration_contradicts_given_facts = verdict.narration_contradicts_given_facts ? "yes" : "no";
  out.dropped_true_condition = verdict.dropped_true_condition ? "yes" : "no";
  out.kept_ended_condition = verdict.kept_ended_condition ? "yes" : "no";
  out.state_as_place = verdict.state_as_place ? "yes" : "no";
  out.facts_after_correct = [
    "missed_change", "invented_change", "dropped_true_condition", "kept_ended_condition", "state_as_place",
  ].some((name) => verdict[name]) ? "no" : "yes";
  return { ...out, changes };
}

function narrationOf(turn, full = false) {
  if (full) return turn.narration;
  return typeof turn.narrator_narration === "string" ? turn.narrator_narration : turn.narration;
}
function story(turn) { return Array.isArray(turn.story_text) ? turn.story_text.join(" ") : ""; }
function turnNumber(turn, index) { return Number.isInteger(turn.turn_number) ? turn.turn_number : index + 1; }
function phrases(before, after) {
  const norm = (x) => String(x).trim().toLowerCase();
  const b = (before?.condition || []).map(norm);
  const a = (after?.condition || []).map(norm);
  return {
    newConditions: a.filter((x) => !b.includes(x)),
    goneConditions: b.filter((x) => !a.includes(x)),
    keptConditions: b.filter((x) => a.includes(x)),
  };
}
function questionSet(state, questions) { return { state, questions }; }

function orderedObject(source, names) {
  return Object.fromEntries(
    names.filter((name) => Object.hasOwn(source, name)).map((name) => [name, source[name]]),
  );
}

function continuityRequests(state, questions, variant) {
  if (variant === "baseline") return [{ state, questions }];
  if (variant.startsWith("preamble")) {
    const rubric = variant.includes("rubric");
    const holistic = variant.includes("holistic");
    const preambleQuestions = holistic ? { ...questions, command_unfinished: COMMAND_UNFINISHED } : questions;
    return [{
      state: { task: rubric ? `${CONTINUITY_PREAMBLE} ${COMMAND_RUBRIC}` : CONTINUITY_PREAMBLE, ...state },
      questions: preambleQuestions,
    }];
  }
  const requests = Object.entries(CONTINUITY_GROUPS).map(([groupName, group]) => {
    const groupState = orderedObject(state, group.state);
    if (variant === "split-examples") groupState.examples = CONTINUITY_EXAMPLES[groupName];
    return {
      state: groupState,
      questions: orderedObject(questions, group.questions),
    };
  });
  if (variant !== "split-criteria") return requests;
  return requests.map((request) => ({
    ...request,
    questions: Object.fromEntries(Object.entries(request.questions).map(([name, question]) => {
      const suffixes = SPLIT_CRITERIA_SUFFIXES[name];
      if (!suffixes) return [name, question];
      return [name, {
        ...question,
        criteria: Object.fromEntries(Object.entries(question.criteria).map(([side, text]) => [
          side, suffixes[side] ? `${text} ${suffixes[side]}` : text,
        ])),
      }];
    })),
  }));
}

function continuityQuestions(state, hasHidden) {
  const q = {
    given_conflict: nounl(
      "Does `narration` put a thing from `given_facts` in a different place or holder, or give it a different condition, than `given_facts` says, without showing that change happen during this turn?",
      "`narration` conflicts with `given_facts` about a thing's place, holder or condition.",
      "`narration` agrees with `given_facts`, does not mention the thing, or shows the thing change. A more specific place inside the given one agrees: on the passenger seat is inside the truck. A general word for the same condition agrees: broken fits a cracked screen.",
    ),
    given_start_conflict: nounl(
      "Does `narration` say or imply that a thing from `given_facts` was somewhere else at the start of this turn than `given_facts` says?",
      "`narration` shows the thing being taken from, found in, or used from a place or holder that differs from `given_facts`. For example, she picks it up from a table while `given_facts` says it is in her hands, or she hands over a thing that `given_facts` puts somewhere she has not fetched it from.",
      "`narration` takes or uses the thing from the place `given_facts` gives, or does not say where it was. A more specific place inside the given one agrees.",
    ),
    earlier_conflict: nounl(
      "Does `narration` state where a thing is, or its physical state, in a way that conflicts with `opening` or `earlier_narration`?",
      "`narration` contradicts `opening` or `earlier_narration` about a thing's place or physical state.",
      "No conflict. A detail that `opening` and `earlier_narration` never mention is not a conflict. If `given_facts` agrees with `narration`, it is not a conflict.",
    ),
    beyond_command: nounl(
      "Does `narration` have the player character physically do something that `command` did not ask for?",
      "She picks up, moves, opens, takes or uses an object, or goes to another place, and `command` did not ask for it.",
      "She does only what `command` asks. Looking, noticing, thinking, feeling, and small movements needed to carry out `command` do not count.",
    ),
    arrives: nounl(
      "Does `narration` describe the player character arriving at, entering, or approaching the place where she already is, as if she were not already there?",
      "`narration` has her arrive, enter or approach as if new to the place.",
      "She simply keeps acting where she is, or `command` asked her to go there.",
    ),
    rediscovers: nounl(
      "Does `narration` present something already described in `opening` or `earlier_narration` as though she were finding it for the first time?",
      "Something already described is found again as if new.",
      "Nothing already described is treated as new.",
    ),
    repeats_trip: nounl(
      "Does `narration` repeat a trip that `opening` or `earlier_narration` already finished, when `command` did not ask for that trip?",
      "She travels again along a route the story already finished. For example, `narration` has her drive through the city to reach a truck that is parked outside the house she is already in.",
      "No finished trip is repeated. Going where `command` sends her is not a repeat.",
    ),
    own_part_done: nounl(
      "Does `narration` or `story_text` show the player character doing her own part of `command`?",
      "She does her part. For a command to look at, examine, search or check a thing, paying attention to that thing is enough. For a command to take a thing from another character, trying to take it is enough.",
      "She does not do her part, or stops before it is done.",
    ),
    needs_other: nounl(
      "Does `command` ask for something that only another character can do, such as taking a thing she hands over or answering her question?",
      "`command` needs another character to act.",
      "`command` needs only her own actions.",
    ),
    take_from_other: nounl(
      "Does `command` ask her to take a thing from another character?",
      "Yes, she is told to take a thing from someone.",
      "No.",
    ),
    other_responds: nounl(
      "Does `narration` or `story_text` show how the other character responds to her?",
      "Another character responds. A refusal, a struggle or silence counts as a response.",
      "No response is shown. Only holding a thing out, with no reaction shown, is not a response.",
    ),
    names_place: nounl(
      "Does `command` name a place for her to go to, or a place to bring or put a thing?",
      "`command` names such a place.",
      "`command` names no place.",
    ),
    reaches_place: nounl(
      "Does `narration` or `story_text` show her arriving at, clearly heading to, or putting the thing in the place `command` names?",
      "She reaches or clearly heads to that place, or puts the thing there.",
      "She does not. Driving away from somewhere does not reach a named place.",
    ),
  };
  if (hasHidden) q.hidden_shown = nounl(
    "Does `narration` show or name a thing that `hidden_canon` says is hidden, either before `command` reaches its hidden spot or somewhere other than that spot?",
    "`narration` reveals the hidden thing too early or in the wrong place.",
    "`narration` does not show the hidden thing, or shows it only because `command` reached its hidden spot.",
  );
  if (hasHidden) q.hidden_lookalike = nounl(
    "Does `narration` show a thing of the same kind as a thing `hidden_canon` says is hidden, at or near its hidden spot, before `command` reaches that spot?",
    "`narration` puts an object like the hidden one (for example another storage device when a memory card is hidden) in or near the hidden spot early.",
    "`narration` shows nothing like the hidden thing near its hidden spot, or `command` has reached the spot.",
  );
  return q;
}

function factQuestions(thing, item, phrasesForThing, protagonist) {
  const t = `\`${thing}\``;
  const q = {
    moved: thing === protagonist
      ? nounl(
        `Does \`narration\` show ${t} changing locations during this turn?`,
        `${t} ends the turn in a different location than \`before_place\`, such as another room, a vehicle, or another part of the area.`,
        `${t} stays in the same location. Small steps within the same room or area, like walking over to a desk or turning to someone, are not a change of location.`,
      )
      : nounl(
        `Does \`narration\` show ${t} moving to a new place or into someone else's hands during this turn?`,
        "It moves or changes hands.",
        "It stays put. An attempt that fails, or a hand-over that nobody takes, is not a move.",
      ),
    condition_changed: nounl(
      `Does \`narration\` show a condition of ${t} changing during this turn, such as opening, closing, cracking or switching on?`,
      "A condition changes.",
      "No condition changes.",
    ),
  };
  if (item.trackedAfter) {
    q.after_place_right = nounl(
      `Is \`after_place\` where \`narration\` leaves ${t} at the end of this turn?`,
      "Yes. If `narration` never moves it, its earlier place is still right. A more specific or more general place that fits is right.",
      "No, `narration` leaves it somewhere else, or never shows it there.",
    );
    q.place_is_condition = nounl(
      `Is \`after_place\` a condition, such as open, cracked or charging, instead of a place or a person holding ${t}?`,
      "`after_place` is a condition.",
      "`after_place` is a place or a holder.",
    );
  }
  if (item.trackedBefore) {
    q.before_conflict = nounl(
      `Does \`narration\` describe ${t} in a way that conflicts with \`before_place\` or \`before_conditions\`, without showing it change during this turn?`,
      "`narration` conflicts with the given facts.",
      "No conflict. A more specific place or state that fits inside the given one is not a conflict.",
    );
    q.start_conflict = nounl(
      `Does \`narration\` say or imply that ${t} was somewhere else at the start of this turn than \`before_place\`?`,
      "`narration` shows it taken from, found in, or used from a place or holder that differs from `before_place`, for example picked up from a table while `before_place` says in her hands.",
      "`narration` takes it from `before_place`, or does not say where it was. A more specific place inside `before_place` agrees.",
    );
  }
  for (let i = 0; i < phrasesForThing.newConditions.length; i++) {
    q[`new_condition_${i}`] = nounl(
      `Does \`narration\` show ${t} being ${phrasesForThing.newConditions[i]}?`,
      "`narration` shows it.",
      "`narration` never shows it. A likely or ordinary state that is not shown does not count.",
    );
  }
  for (let i = 0; i < phrasesForThing.goneConditions.length; i++) {
    q[`gone_condition_${i}`] = nounl(
      `Does \`narration\` show ${t} stop being ${phrasesForThing.goneConditions[i]}, or does \`after_conditions\` list a phrase with the same meaning or the opposite meaning?`,
      "The condition ended in `narration`, or `after_conditions` still covers it.",
      "`after_conditions` dropped it without cause.",
    );
  }
  for (let i = 0; i < phrasesForThing.keptConditions.length; i++) {
    q[`kept_condition_${i}`] = nounl(
      `Does \`narration\` show ${t} stop being ${phrasesForThing.keptConditions[i]} during this turn?`,
      "`narration` ends that condition.",
      "It still holds.",
    );
  }
  q.command_asks = nounl(
    `Does \`command\` itself ask for a change to ${t}?`,
    "`command` asks for this change.",
    "`command` does not. Looking at, examining, searching or checking a thing does not ask for moving, taking, opening or damaging it.",
  );
  if (!item.trackedBefore && item.trackedAfter) {
    q.same_as_other = nounl(
      `Is ${t} the same object as one of \`other_things\`, recorded under a different name?`,
      "It is the same object as a thing in `other_things`, for example `laptop` and `Kristin's laptop` for the one laptop the story has.",
      "It is a different object from every thing in `other_things`, or `other_things` is empty.",
    );
  }
  return q;
}

export async function judgeInput(
  input,
  { packagePath, fetchImpl = fetch, environment = process.env, only, variant = "baseline", judges = "both", protagonist } = {},
) {
  if (!CONTINUITY_VARIANTS.includes(variant)) {
    throw new Error(`Unknown continuity variant: ${variant}`);
  }
  if (!["both", "continuity", "fact"].includes(judges)) {
    throw new Error(`Unknown judges option: ${judges}`);
  }
  if (!environment.CLOUDFLARE_ACCOUNT_ID || !environment.CLOUDFLARE_AI_TOKEN) {
    throw new Error("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_AI_TOKEN are required.");
  }
  const plot = readFileSync(resolve(packagePath, "plot.md"), "utf8");
  const raw = []; let calls = 0; let model;
  const request = async (judge, replicate, turn, thing, state, questions) => {
    const questionSize = Math.max(0, ...Object.values(questions).map((q) => JSON.stringify(q).length));
    if (Math.ceil((JSON.stringify(state).length + questionSize) / 4) > 30000) {
      throw new Error("Jev request exceeds the 30000 token estimate.");
    }
    const response = await fetchImpl(
      `https://api.cloudflare.com/client/v4/accounts/${environment.CLOUDFLARE_ACCOUNT_ID}/ai/run`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${environment.CLOUDFLARE_AI_TOKEN}`,
        },
        body: JSON.stringify({ model: "typesafe/jev", input: questionSet(state, questions) }),
      },
    );
    calls += 1;
    const parsed = parseEnvelope(response.status, await response.json(), Object.keys(questions));
    if (model && parsed.model !== model) throw new Error(`Jev model changed from ${model} to ${parsed.model}.`);
    model ||= parsed.model;
    raw.push({
      judge, replicate, turn, ...(thing === undefined ? {} : { thing }), model: parsed.model,
      variant, state, questions, answers: parsed.answers, usage: parsed.usage,
    });
    return parsed.answers;
  };
  const continuity = { judgments: [], judge_calls: 0 }; const fact = { judgments: [], judge_calls: 0 };
  for (let ri = 0; ri < input.runs.length; ri++) {
    const run = input.runs[ri]; const cTurns = []; const fTurns = [];
    for (let i = 0; i < run.turns.length; i++) {
      const turn = run.turns[i];
      const replicate = run.replicate ?? ri;
      const number = turnNumber(turn, i);
      const key = `${replicate}:${number}`;
      if (only && !only.has(key)) continue;
      const sceneId = turn.scene_id; const first = i === 0 || run.turns[i - 1].scene_id !== sceneId;
      const earlier = [];
      for (let j = i - 1; j >= 0 && earlier.length < 2; j--) {
        if (run.turns[j].scene_id === sceneId) earlier.unshift(narrationOf(run.turns[j]));
      }
      const hc = hiddenCanon(plot, sceneId);
      const firstSceneId = run.turns[0]?.scene_id;
      const state = {
        command: turn.player_input,
        narration: narrationOf(turn),
        story_text: story(turn),
        given_facts: turn.item_facts_before || {},
        opening: sceneId === firstSceneId ? run.opening : "",
        earlier_narration: earlier,
        hidden_canon: hc,
      };
      if (judges !== "fact") {
        const questions = continuityQuestions(state, Boolean(hc));
        const answers = {};
        for (const requestInput of continuityRequests(state, questions, variant)) {
          const part = await request(
            "continuity", replicate, number, undefined, requestInput.state, requestInput.questions,
          );
          Object.assign(answers, part);
          continuity.judge_calls++;
        }
        const truth = Object.fromEntries(
          Object.entries(answers).map(([name, answer]) => [name, answer?.noul > THRESHOLD]),
        );
        const reason = Object.entries(answers)
          .filter(([, answer]) => answer?.noul > THRESHOLD)
          .map(([name, answer]) => `${name} ${answer.noul.toFixed(2)}`)
          .join("; ");
        cTurns.push({
          turn: number,
          ...combineContinuity(truth, { firstTurnInScene: first, hasHiddenCanon: Boolean(hc) }),
          reason,
        });
      }
      const before = turn.item_facts_before || {};
      const after = turn.item_facts_after || {};
      const things = [...new Set([...Object.keys(before), ...Object.keys(after)])];
      const perThing = [];
      for (const thing of judges === "continuity" ? [] : things) {
        const b = before[thing];
        const a = after[thing];
        const trackedBefore = Boolean(b);
        const trackedAfter = Boolean(a);
        const pf = phrases(b, a);
        const placeChanged = trackedAfter
          && String(a.place || "").trim().toLowerCase() !== String(b?.place || "").trim().toLowerCase();
        const item = {
          thing,
          trackedBefore,
          trackedAfter,
          ...pf,
          conditionsChanged: pf.newConditions.length > 0 || pf.goneConditions.length > 0,
          placeChanged,
        };
        const otherThings = things.filter((otherThing) => otherThing !== thing);
        const fs = {
          command: turn.player_input,
          narration: turn.narration,
          story_text: story(turn),
          thing,
          other_things: otherThings,
          before_place: b?.place || "",
          before_conditions: b?.condition || [],
          after_place: a?.place || "",
          after_conditions: a?.condition || [],
          tracked_before: trackedBefore,
          tracked_after: trackedAfter,
        };
        const fq = factQuestions(thing, item, pf, protagonist);
        const fa = await request("fact", replicate, number, thing, fs, fq);
        fact.judge_calls++;
        const ft = Object.fromEntries(
          Object.entries(fa).map(([name, answer]) => [name, answer?.noul > THRESHOLD]),
        );
        perThing.push({ ...item, answersTrue: ft, answers: fa });
      }
      const combined = combineFact(perThing);
      const factReason = perThing
        .flatMap((item) => Object.entries(item.answersTrue)
          .filter(([, yes]) => yes)
          .map(([name]) => `${item.thing}:${name} ${(item.answers?.[name]?.noul ?? 0).toFixed(2)}`))
        .join("; ");
      fTurns.push({ turn: number, ...combined, reason: factReason });
    }
    continuity.judgments.push({ turns: cTurns });
    fact.judgments.push({ turns: judges === "continuity" ? [] : fTurns });
  }
  return { continuity, fact, raw };
}

function argument(name) {
  const i = process.argv.indexOf(name);
  if (i < 0 || !process.argv[i + 1]) throw new Error(`Missing ${name}.`);
  return process.argv[i + 1];
}
async function main() {
  const input = JSON.parse(readFileSync(argument("--input"), "utf8"));
  const onlyArg = process.argv.includes("--only") ? argument("--only") : "";
  const only = onlyArg ? new Set(onlyArg.split(",")) : undefined;
  const variant = process.argv.includes("--variant") ? argument("--variant") : "baseline";
  const judges = process.argv.includes("--judges") ? argument("--judges") : "both";
  const protagonist = process.argv.includes("--protagonist") ? argument("--protagonist") : undefined;
  const result = await judgeInput(input, { packagePath: argument("--package"), only, variant, judges, protagonist });
  const out = argument("--out");
  if (judges !== "fact") {
    writeFileSync(resolve(out, "continuity-judgments.json"), JSON.stringify(result.continuity, null, 2) + "\n");
  }
  if (judges !== "continuity") {
    writeFileSync(resolve(out, "fact-tracking-judgments.json"), JSON.stringify(result.fact, null, 2) + "\n");
  }
  writeFileSync(resolve(out, "jev-raw.json"), JSON.stringify(result.raw, null, 2) + "\n");
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) await main();
