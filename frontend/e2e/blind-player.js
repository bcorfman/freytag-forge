import { laterAffordances, firstStepAffordances, mentions, normalizeText } from "./affordances.js";

const PLAYER_SYSTEM =
  "You are a player at a text adventure. You only know what you have read on the screen. " +
  "Write one active command for the next turn. Use an imperative verb and a direct object. " +
  "Name your own things with first-person possessive words such as my laptop. " +
  "Do not write I, do not refuse or restrain an action, and do not wait or merely listen. " +
  "End the command with a period. Reply with one command.";

const PLAYER_SCHEMA = {
  type: "object",
  properties: { command: { type: "string" } },
  required: ["command"],
  additionalProperties: false,
};

export function playerPrompt({ transcript = "", status = "" } = {}) {
  return {
    system: PLAYER_SYSTEM,
    user: `Screen transcript:\n${String(transcript)}\n\nStatus line:\n${String(status)}`,
  };
}

function outputText(response) {
  if (typeof response?.output_text === "string") return response.output_text;
  for (const item of response?.output || []) {
    for (const content of item?.content || []) {
      if (content?.type === "output_text" && typeof content.text === "string") return content.text;
    }
  }
  return "";
}

export function validateCommand(command) {
  const problems = [];
  if (typeof command !== "string" || !command.trim()) return { ok: false, problems: ["command must be text"] };
  const value = command.trim();
  const words = value.match(/\S+/g) || [];
  if (/^I\b/i.test(value)) problems.push("start with an imperative, not I");
  if (/\b(do not|don't|without|avoid|never|can't|cannot)\b/i.test(value)) problems.push("do not use restraint words");
  if (/^(wait|listen|keep watch|stand still|continue waiting)\b/i.test(value.replace(/[.!?]+$/, "").trim())) {
    problems.push("use an active event, not waiting or passive listening");
  }
  if (!value.endsWith(".")) problems.push("end with a period");
  if (words.length < 2 || words.length > 25) problems.push("use 2 to 25 words");
  return { ok: problems.length === 0, problems };
}

export async function askPlayer({ transcript, status, environment = process.env, fetchImpl = fetch, cap = 20, counter = { calls: 0 } } = {}) {
  if (!environment.OPENAI_API_KEY) throw new Error("Blind player requires OPENAI_API_KEY.");
  const prompt = playerPrompt({ transcript, status });
  let retry = false;
  let problems = [];
  while (true) {
    if (counter.calls >= cap) throw new Error(`Blind player model call cap reached (${cap}).`);
    counter.calls += 1;
    const user = retry
      ? `${prompt.user}\n\nThe previous command was invalid. Fix these problems: ${problems.join("; ")}`
      : prompt.user;
    const response = await fetchImpl("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${environment.OPENAI_API_KEY}` },
      body: JSON.stringify({
        model: environment.E2E_PLAYER_MODEL || "gpt-5.6-luna",
        store: false,
        input: [{ role: "system", content: prompt.system }, { role: "user", content: user }],
        text: { format: { type: "json_schema", name: "blind_player_command", strict: true, schema: PLAYER_SCHEMA } },
      }),
    });
    if (!response.ok) throw new Error(`Blind player request failed with HTTP ${response.status}.`);
    const payload = await response.json();
    let result;
    try { result = JSON.parse(outputText(payload)); } catch (error) { throw new Error("Blind player returned invalid JSON.", { cause: error }); }
    const checked = validateCommand(result?.command);
    if (checked.ok) return result.command.trim();
    if (retry) throw new Error(`Blind player returned an invalid command twice: ${checked.problems.join("; ")}`);
    retry = true;
    problems = checked.problems;
  }
}

function allAffordances(scene) {
  const items = [...firstStepAffordances({ scenes: [scene] }, scene?.scene_id), ...laterAffordances({ scenes: [scene] }, scene?.scene_id)];
  return [...new Map(items.map((item) => [item.entity_id, item])).values()];
}

function newIds(current, previous, field) {
  const before = new Set(previous?.state?.[field] || []);
  return (current?.state?.[field] || []).filter((id) => !before.has(id));
}

function sourceForId(scene, id) {
  return (scene?.gates || []).flatMap((gate) => gate.sources || []).find((source) => source.id === id);
}

function contentWords(value) {
  return new Set((normalizeText(value).match(/[a-z]{4,}/g) || []));
}

const unseenStopWords = new Set([
  "the", "a", "an", "my", "of", "for", "in", "on", "to", "and", "with", "from", "at", "it", "its", "this", "that",
  "search", "examine", "inspect", "read", "open", "take", "pull", "look", "check", "use", "go", "walk", "talk", "ask",
  "question", "investigate", "clues", "around", "into", "out", "up", "down", "off", "over",
]);

function unseenWordMatch(word, readWords) {
  if (readWords.has(word)) return true;
  if (word.endsWith("s") && word.length > 3 && readWords.has(word.slice(0, -1))) return true;
  return [...readWords].some((candidate) => candidate.endsWith("s") && candidate.length > 3 && candidate.slice(0, -1) === word);
}

export function unseenTerms({ command = "", readText = "" } = {}) {
  const words = normalizeText(command).replace(/([a-z]+)'s\b/g, "$1").match(/[a-z]{3,}/g) || [];
  const readWords = new Set(normalizeText(readText).match(/[a-z]{3,}/g) || []);
  return [...new Set(words.filter((word) => !unseenStopWords.has(word) && !unseenWordMatch(word, readWords)))];
}

export function turnRecord({ turn, input, payload = {}, text }) {
  return {
    turn,
    input,
    text,
    state: payload.state,
    grounding_ids: (payload.segments || []).flatMap((segment) => segment.grounding_ids || []),
    delivery: payload.delivery || {},
    semantic_match: payload.semantic_match || null,
    prompt: payload.prompt || null,
  };
}

export function turnLog(turns = []) {
  return turns.map(({ turn, input, text, state, grounding_ids, semantic_match, rejected, rejection }) => ({
    turn,
    input,
    text,
    rejected: Boolean(rejected),
    rejection: rejection ?? null,
    scene_id: state?.scene_id ?? null,
    semantic_match: semantic_match ?? null,
    grounding_ids: grounding_ids || [],
  }));
}

function realizationMatch(text, realization) {
  const words = contentWords(realization);
  if (!words.size) return false;
  const shown = contentWords(text);
  return [...words].filter((word) => shown.has(word)).length >= Math.ceil(words.size / 2);
}

function entryText(scene) {
  return scene?.entry_text || scene?.entry_material?.text || scene?.entry_material?.bridge_text || scene?.entry_material?.entry_text || "";
}

export function analyseRun({ sceneEntry, nextSceneEntry, turns = [], firstStep = [], later = [], sceneMapSources = [], openingText = "", stopped_on_rejections = false } = {}) {
  const affordances = [...new Map([...firstStep, ...later].map((item) => [item.entity_id, item])).values()];
  const rejectedTurns = turns.filter((turn) => turn.rejected === true).map(({ turn, input, rejection }) => ({ turn, input, rejection }));
  const committedTurns = turns.filter((turn) => turn.state != null && turn.rejected !== true);
  const transitionIndex = committedTurns.findIndex((turn) => turn.state.scene_id && turn.state.scene_id !== sceneEntry?.scene_id);
  const transitionTurn = transitionIndex < 0 ? null : committedTurns[transitionIndex].turn;
  const handoffAfterTurns = typeof sceneEntry?.handoff_after_turns === "number" ? sceneEntry.handoff_after_turns : null;
  const exitCause = transitionTurn == null
    ? "none"
    : handoffAfterTurns == null
      ? "unknown"
      : transitionTurn < handoffAfterTurns
        ? "play"
        : "timer";
  const upto = transitionTurn == null ? turns.length : turns.findIndex((turn) => turn.turn === transitionTurn) + 1;
  const shown = affordances.map((item) => {
    const entries = [{ turn: 0, text: openingText }, ...turns.slice(0, upto).filter((turn) => turn.rejected !== true)];
    const hit = entries.find((turn) => mentions(turn.text, item.terms || [item.name, ...(item.aliases || [])]));
    return {
      entity_id: item.entity_id,
      first_shown_turn: hit?.turn ?? null,
      ...(firstStep.some((candidate) => candidate.entity_id === item.entity_id) ? { deadline_met: Boolean(hit && hit.turn <= 1) } : {}),
    };
  });
  const stuckTurns = [];
  let previous = null;
  for (const turn of turns) {
    if (turn.rejected === true || turn.state == null) continue;
    const names = [...firstStep, ...later];
    const mentionsAffordance = names.some((item) => mentions(turn.input, item.terms || [item.name, ...(item.aliases || [])]));
    const addedStorylet = newIds(turn, previous, "fired_storylet_ids").length > 0;
    const addedGrounding = (turn.grounding_ids || []).some((id) => !(previous?.grounding_ids || []).includes(id));
    if (!mentionsAffordance && !addedStorylet && !addedGrounding) stuckTurns.push(turn);
    previous = turn;
  }
  const stuckRuns = [];
  for (let i = 0; i < stuckTurns.length; i += 1) {
    const run = [stuckTurns[i]];
    while (stuckTurns[i + 1]?.turn === run.at(-1).turn + 1) run.push(stuckTurns[++i]);
    if (run.length >= 3) stuckRuns.push(run.map(({ turn, input, text }) => ({ turn, input, text })));
  }
  const gateEarned = (sceneEntry?.gates || []).filter((gate) => (gate.sources || []).some((source) => source.player_earned));
  const firstStepIds = new Set(firstStep.map((item) => item.entity_id));
  const shownById = new Map(shown.map((entry) => [entry.entity_id, entry]));
  const silentTransition = transitionIndex >= 0 && gateEarned.some((gate) => (gate.affordances || []).some((item) => {
    if (!firstStepIds.has(item.entity_id)) return false;
    const entry = shownById.get(item.entity_id);
    return entry != null && entry.first_shown_turn == null;
  }));
  const unseenCommands = [];
  for (const [index, turn] of turns.entries()) {
    const readText = [openingText, ...turns.slice(0, index).filter((candidate) => candidate.rejected !== true).map((candidate) => candidate.text)].filter(Boolean).join(" ");
    const unseen = unseenTerms({ command: turn.input, readText });
    if (unseen.length) unseenCommands.push({ turn: turn.turn, input: turn.input, unseen_terms: unseen });
  }
  const semantic_matches = turns
    .filter((turn) => turn.semantic_match != null)
    .map((turn) => ({ turn: turn.turn, input: turn.input, ran: turn.semantic_match.ran, matched: turn.semantic_match.matched }));
  const delivery = [];
  const pacing = [];
  let previousTurn = null;
  for (const turn of committedTurns) {
    const newStorylets = newIds(turn, previousTurn, "fired_storylet_ids");
    const newGrounding = (turn.grounding_ids || []).filter((id) => !(previousTurn?.grounding_ids || []).includes(id));
    for (const id of [...newStorylets, ...newGrounding]) delivery.push({ source_id: id, turn: turn.turn, must_convey_misses: turn.delivery?.must_convey_misses || [] });
    for (const id of newIds(turn, previousTurn, "fired_pacing_event_ids")) {
      const source = sourceForId(sceneEntry, id) || sceneMapSources.find((candidate) => candidate.id === id);
      const realizations = source?.realizations || source?.realization_texts || [];
      for (const realization of Array.isArray(realizations) ? realizations : [realizations]) pacing.push({ source_id: id, turn: turn.turn, matched: realizationMatch(turn.text, realization), realization });
    }
    previousTurn = turn;
  }
  const nextEntry = normalizeText(entryText(nextSceneEntry));
  const transition = transitionIndex < 0 ? null : committedTurns[transitionIndex];
  const transitionText = normalizeText(transition?.text);
  const entryStart = transitionText.lastIndexOf(nextEntry);
  const finalSegmentMatches = Boolean(nextEntry && transitionText.endsWith(nextEntry));
  const transitionPrefixContainsEntry = entryStart > 0 && transitionText.slice(0, entryStart).includes(nextEntry);
  const priorContainsEntry = nextEntry ? committedTurns.slice(0, transitionIndex < 0 ? committedTurns.length : transitionIndex).some((turn) => normalizeText(turn.text).includes(nextEntry)) : false;
  const l3 = {
    delivery,
    must_convey: delivery,
    pacing,
    pacing_realizations: pacing,
    transition: { turn: transitionTurn, final_segment_matches_entry: finalSegmentMatches, prior_contains_entry: priorContainsEntry, earlier_segment_contains_entry: transitionPrefixContainsEntry, no_skip_or_restart: finalSegmentMatches && !priorContainsEntry && !transitionPrefixContainsEntry },
  };
  return { stopped_on_rejections, rejected_count: rejectedTurns.length, rejected_turns: rejectedTurns, transition_fired: transitionIndex >= 0, transition_turn: transitionTurn, handoff_after_turns: handoffAfterTurns, exit_cause: exitCause, affordances: shown, stuck_turns: stuckTurns.map((turn) => turn.turn), stuck_runs: stuckRuns, silent_transition: silentTransition, unseen_commands: unseenCommands, unseen_command_count: unseenCommands.length, semantic_matches, l3 };
}

export function aggregate(runs = []) {
  const count = runs.length || 1;
  const shown = [...new Set(runs.flatMap((run) => (run.affordances || []).map((item) => item.entity_id)))];
  const rejectedCount = runs.reduce((sum, run) => sum + (run.rejected_count ?? run.rejected_turns?.length ?? 0), 0);
  const turnCount = runs.reduce((sum, run) => sum + (run.turn_count ?? 0), 0);
  const commandCount = runs.reduce((sum, run) => sum + (run.commands?.length ?? run.turns?.length ?? run.turn_count ?? 0), 0);
  return {
    replicates: runs.length,
    transition_rate: runs.filter((run) => run.transition_fired).length / count,
    play_exit_rate: runs.filter((run) => run.exit_cause === "play").length / count,
    timer_exit_rate: runs.filter((run) => run.exit_cause === "timer").length / count,
    mean_transition_turn: runs.filter((run) => run.transition_turn != null).reduce((sum, run) => sum + run.transition_turn, 0) / (runs.filter((run) => run.transition_turn != null).length || 1),
    affordances_shown_by_deadline_rate: Object.fromEntries(shown.map((id) => [id, runs.filter((run) => run.affordances?.find((item) => item.entity_id === id)?.deadline_met).length / count])),
    stuck_run_count: runs.reduce((sum, run) => sum + (run.stuck_runs?.length || 0), 0),
    silent_transition_rate: runs.filter((run) => run.silent_transition).length / count,
    rejected_count: rejectedCount,
    rejected_turn_rate: rejectedCount / (turnCount || 1),
    stopped_on_rejections_count: runs.filter((run) => run.stopped_on_rejections).length,
    unseen_command_rate: runs.reduce((sum, run) => sum + (run.unseen_command_count || 0), 0) / (commandCount || 1),
  };
}

export function formatMarkdown(report) {
  const runs = report.replicates || [];
  const rejectedCount = report.aggregate?.rejected_count ?? runs.reduce((sum, run) => sum + (run.rejected_count ?? run.rejected_turns?.length ?? 0), 0);
  const aggregate = report.aggregate || {};
  const unseen = runs.flatMap((run) => (run.unseen_commands || []).map((item) => `- Turn ${item.turn}: ${item.input} — unseen: ${item.unseen_terms.join(", ")}`));
  const exitLines = runs.map((run, index) => `- Replicate ${run.replicate ?? index + 1}: exit=${run.exit_cause ?? "unknown"}, transition turn=${run.transition_turn ?? "none"}, timer turn=${run.handoff_after_turns ?? "unknown"}`);
  const semanticSections = runs.map((run, index) => {
    const entries = run.semantic_matches || [];
    const lines = entries.length
      ? entries.map((entry) => `- Turn ${entry.turn}: ${entry.input} — ran: ${entry.ran}, matched: ${entry.matched ?? "none"}`)
      : ["The server did not return it."];
    return `## Semantic reveal fallback — replicate ${run.replicate ?? index + 1}\n\n${lines.join("\n")}`;
  });
  const turnSections = runs.map((run, index) => {
    const lines = (run.turns || []).map((turn) => `- t${turn.turn} ${turn.input} -> ${String(turn.text || "").replace(/\s+/g, " ").slice(0, 200)}`);
    return `## Turns — replicate ${run.replicate ?? index + 1}\n\n${lines.length ? lines.join("\n") : "None"}`;
  });
  const markdownReport = {
    ...report,
    replicates: runs.map(({ prompts, ...run }) => run),
  };
  return `# blind-player E2E evaluation\n\nRejected turns: ${rejectedCount}\n\nPlay exit rate: ${aggregate.play_exit_rate ?? "unknown"}\nTimer exit rate: ${aggregate.timer_exit_rate ?? "unknown"}\n\n## Exits\n\n${exitLines.length ? exitLines.join("\n") : "None"}\n\n## Unseen commands\n\n${unseen.length ? unseen.join("\n") : "None"}\n\n${turnSections.length ? turnSections.join("\n\n") : "## Turns\n\nNone"}\n\n${semanticSections.length ? semanticSections.join("\n\n") : "## Semantic reveal fallback\n\nThe server did not return it."}\n\n${JSON.stringify(markdownReport, null, 2)}\n`;
}
