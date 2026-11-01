import { readFileSync } from "node:fs";

const QUOTA_CODE = /\b(AI_QUOTA_EXCEEDED|AI_DAILY_BUDGET_EXCEEDED|BUDGET_UNAVAILABLE)\b/;
const HTTP_CODE = /\bHTTP\s+(5\d{2}|429)\b/i;

function errorMessage(error) {
  return error instanceof Error ? error.message : String(error);
}

export function classifyFailure(error) {
  const message = errorMessage(error);
  const quota = message.match(QUOTA_CODE);
  if (quota) return { class: "infrastructure", code: quota[1], quotaStop: true };

  const http = message.match(HTTP_CODE);
  if (http) return { class: "infrastructure", code: `HTTP ${http[1]}` };
  if (/did not produce a response/i.test(message)) return { class: "infrastructure", code: "turn_timeout" };
  if (/request failed/i.test(message)) return { class: "infrastructure", code: "request_failed" };
  if (/failed to fetch/i.test(message)) return { class: "infrastructure", code: "fetch_failed" };
  if (/(?:cors|net::(?:ERR_|FAILED|ABORTED)|network error)/i.test(message)) {
    return { class: "infrastructure", code: "network_error" };
  }

  return { class: "gameplay", code: "other" };
}

function committedKnowledge(perTurn) {
  const byScene = new Map();
  for (const turn of perTurn) {
    const scene = turn.scene_in;
    if (!scene) continue;
    const ids = byScene.get(scene) || new Set();
    byScene.set(scene, ids);
    const bundle = turn?.bundle;
    if (bundle?.outcome !== "committed") continue;
    for (const id of bundle.selected_reveal?.knowledge_ids || []) ids.add(id);
  }
  return byScene;
}

function reachedSceneIds(sceneOrder, expected) {
  const expectedScenes = Object.keys(expected);
  const sceneIndexes = sceneOrder.map((scene) => expectedScenes.indexOf(scene)).filter((index) => index >= 0);
  if (!sceneIndexes.length) return new Set();
  return new Set(expectedScenes.slice(0, Math.max(...sceneIndexes) + 1));
}

function latencySummary(perTurn) {
  const values = perTurn.map((turn) => turn?.latency_ms).filter((value) => Number.isFinite(value));
  if (!values.length) return { min: null, median: null, max: null, total: 0 };
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  const median = sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
  return { min: sorted[0], median, max: sorted.at(-1), total: values.reduce((sum, value) => sum + value, 0) };
}

function deliverySummary(perTurn) {
  const summary = {
    total_turns: perTurn.length,
    turns_with_misses: 0,
    recovery_turns: 0,
    guard_retry_turns: 0,
    fallback_turns: 0,
    miss_tally: {},
    no_bundle_turns: 0,
  };
  for (const turn of perTurn) {
    const delivery = turn?.delivery || {};
    const misses = delivery.must_convey_misses || [];
    if (misses.length) summary.turns_with_misses += 1;
    if (delivery.recovery_used === true) summary.recovery_turns += 1;
    if (delivery.guard_retry_used === true) summary.guard_retry_turns += 1;
    if (delivery.fallback_used === true) summary.fallback_turns += 1;
    if (!turn?.bundle) summary.no_bundle_turns += 1;
    for (const factId of misses) summary.miss_tally[factId] = (summary.miss_tally[factId] || 0) + 1;
  }
  return summary;
}

export function evaluateSpine({ sceneOrder = [], perTurn = [], expected = {} } = {}) {
  const committedByScene = committedKnowledge(perTurn);
  const reached = reachedSceneIds(sceneOrder, expected);
  const committed_by_scene = Object.fromEntries(
    [...committedByScene.entries()].map(([scene, ids]) => [scene, [...ids].sort()]),
  );
  const chain_misses = {};
  for (const scene of reached) {
    const committed = new Set(committedByScene.get(scene) || []);
    const misses = (expected[scene] || []).filter((id) => !committed.has(id));
    if (misses.length) chain_misses[scene] = misses;
  }

  const exits = {};
  for (const turn of perTurn) {
    if (!turn?.bundle) continue;
    const cause = turn.bundle.transition_cause ?? "none";
    exits[cause] = (exits[cause] || 0) + 1;
  }
  const delivery = deliverySummary(perTurn);
  return {
    committed_by_scene,
    chain_misses,
    exits,
    story_complete: perTurn.some((turn) => turn?.state_story_complete === true || turn?.bundle?.story_complete === true),
    observation_committed: (committedByScene.get("2C") || new Set()).has("k_sl_2c_c_r1"),
    turns: perTurn.length,
    latency: latencySummary(perTurn),
    delivery,
    no_bundle_turns: delivery.no_bundle_turns,
  };
}

export function loadExpectedReveals() {
  const source = readFileSync(new URL("./spine-expected-reveals.json", import.meta.url), "utf8");
  return JSON.parse(source);
}
