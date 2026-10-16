import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const YAML = require("yaml");

function parseYaml(root, name) {
  return YAML.parse(readFileSync(resolve(root, "data/stories/continuity-initiative", name), "utf8"));
}

function parsePlot(root) {
  const source = readFileSync(resolve(root, "data/stories/continuity-initiative/plot.md"), "utf8");
  const lines = source.split(/\r?\n/);
  const scenes = new Map();
  for (let index = 0; index < lines.length; index += 1) {
    if (lines[index] !== "---") continue;
    const end = lines.indexOf("---", index + 1);
    if (end < 0) break;
    const frame = YAML.parse(lines.slice(index + 1, end).join("\n"));
    if (frame?.scene_id) scenes.set(frame.scene_id, frame);
    index = end;
  }
  return scenes;
}

export function loadAuthoredText(root = resolve(import.meta.dirname, "../..")) {
  const knowledge = parseYaml(root, "knowledge.yaml");
  const handoffs = parseYaml(root, "handoffs.yaml");
  const pacing = parseYaml(root, "pacing.yaml");
  const routes = parseYaml(root, "storylet-routes.yaml");
  const frames = parsePlot(root);
  const knowledgeDeliveryTexts = new Map(
    (knowledge.knowledge || []).filter((item) => item.delivery_text).map((item) => [item.id, item.delivery_text]),
  );
  const cueTexts = new Map();
  const handoffFallbackTexts = new Map();
  for (const item of handoffs.deliveries || []) {
    if (item.cue_text) cueTexts.set(item.fact_id, item.cue_text);
    if (item.fallback_text) handoffFallbackTexts.set(item.fact_id, item.fallback_text);
  }
  const bridgeTexts = new Map();
  const bridgeTextsByScenePair = new Map();
  for (const transition of pacing.transitions || []) {
    const text = frames.get(transition.source_scene_id)?.bridge_text?.[transition.id];
    if (!text) continue;
    bridgeTexts.set(transition.id, text);
    bridgeTextsByScenePair.set(`${transition.source_scene_id}>${transition.target_scene_id}`, text);
  }
  const entryTexts = new Map([...frames].map(([id, frame]) => [id, frame.entry_text]).filter(([, text]) => text));
  const routeFallbackTexts = new Map();
  const routeFallbacks = [];
  for (const section of ["canonical_bridge_events", "canonical_resolution_events"]) {
    for (const route of routes[section] || []) {
      if (!route.fallback_text) continue;
      const ids = new Set([route.id, ...(route.produces || []).map((item) => item.fact_id).filter(Boolean)]);
      const record = { text: route.fallback_text, ids: [...ids], event_id: route.id, fact_ids: [...ids].filter((id) => id !== route.id) };
      routeFallbacks.push(record);
      for (const id of ids) routeFallbackTexts.set(id, route.fallback_text);
    }
  }
  return {
    knowledgeDeliveryTexts,
    knowledgeDeliveryTextById: knowledgeDeliveryTexts,
    cueTexts,
    cueTextByFactId: cueTexts,
    handoffFallbackTexts,
    handoffFallbackTextByFactId: handoffFallbackTexts,
    bridgeTexts,
    bridgeTextById: bridgeTexts,
    bridgeTextsByScenePair,
    bridgeTextByScenePair: bridgeTextsByScenePair,
    entryTexts,
    entryTextBySceneId: entryTexts,
    routeFallbackTexts,
    routeFallbacks,
  };
}

function add(map, id, kind, result) {
  const text = map?.get(id);
  if (text && !result.some((item) => item.text === text)) result.push({ text, source: { kind, id } });
}

export function eligibleAuthoredTexts(bundle, authored) {
  if (!bundle || bundle.outcome !== "committed" || !authored) return [];
  const result = [];
  const knowledgeTexts = authored.knowledgeDeliveryTexts || authored.knowledgeDeliveryTextById;
  const cues = authored.cueTexts || authored.cueTextByFactId;
  const fallbacks = authored.handoffFallbackTexts || authored.handoffFallbackTextByFactId;
  const bridges = authored.bridgeTextsByScenePair || authored.bridgeTextByScenePair;
  const entries = authored.entryTexts || authored.entryTextBySceneId;
  for (const id of bundle.selected_reveal?.knowledge_ids || []) add(knowledgeTexts, id, "delivery", result);
  const cue = bundle.cue_stage;
  if (cue?.delivered && cue.fact_id) add(cues, cue.fact_id, "cue", result);
  const handoffIds = new Set([
    ...(bundle.selected_reveal?.delivery_fact_ids || []),
    ...(bundle.pre_state?.staged_handoff_fact_ids || []),
  ]);
  for (const id of handoffIds) add(fallbacks, id, "handoff_fallback", result);
  for (const id of new Set(bundle.committed_delta?.fact_predicates || [])) add(fallbacks, id, "handoff_fallback", result);
  const delta = bundle.committed_delta || {};
  const changed = delta.scene_from && delta.scene_to && delta.scene_from !== delta.scene_to;
  if (changed || bundle.transition_cause !== "none") {
    const pair = `${delta.scene_from}>${delta.scene_to}`;
    add(bridges, pair, "bridge", result);
    if (delta.scene_to) add(entries, delta.scene_to, "entry", result);
  }
  if (bundle.story_complete || (bundle.committed_delta?.fact_predicates || []).some((id) => authored.routeFallbackTexts.has(id))) {
    const factPredicates = new Set(bundle.committed_delta?.fact_predicates || []);
    const seen = new Set();
    for (const route of authored.routeFallbacks || []) {
      if (!bundle.story_complete && !route.fact_ids.some((id) => factPredicates.has(id))) continue;
      if (seen.has(route.text) || result.some((item) => item.text === route.text)) continue;
      seen.add(route.text);
      result.push({ text: route.text, source: { kind: "route_fallback", id: route.event_id } });
    }
  }
  return result;
}

function normalized(value) {
  return value.replace(/[‘’‛′]/g, "'").replace(/[“”‟″]/g, '"').replace(/\s+/g, " ");
}

function normalizedWithOffsets(value) {
  const chars = [];
  let inSpace = false;
  for (let index = 0; index < value.length; index += 1) {
    const char = value[index];
    if (/\s/.test(char)) {
      if (!inSpace) chars.push({ char: " ", index });
      inSpace = true;
    } else {
      const quote = char.replace(/[‘’‛′]/g, "'").replace(/[“”‟″]/g, '"');
      chars.push({ char: quote, index });
      inSpace = false;
    }
  }
  return chars;
}

export function attributeNarration(narration, eligible) {
  if (!narration) return narration === "" ? [] : [{ text: narration, origin: "narrator" }];
  const haystack = normalizedWithOffsets(narration);
  const normalizedNarration = haystack.map((item) => item.char).join("");
  const candidates = [];
  for (const item of eligible || []) {
    const needle = normalized(item.text);
    if (!needle) continue;
    let from = 0;
    while ((from = normalizedNarration.indexOf(needle, from)) >= 0) {
      candidates.push({ from, to: from + needle.length, source: item.source });
      from += 1;
    }
  }
  candidates.sort((a, b) => (b.to - b.from) - (a.to - a.from) || a.from - b.from);
  const chosen = [];
  for (const candidate of candidates) {
    if (chosen.some((item) => candidate.from < item.to && item.from < candidate.to)) continue;
    chosen.push(candidate);
  }
  chosen.sort((a, b) => a.from - b.from);
  const spans = [];
  let normalizedCursor = 0;
  for (const item of chosen) {
    if (item.from > normalizedCursor) {
      const start = haystack[normalizedCursor]?.index ?? narration.length;
      const end = haystack[item.from]?.index ?? narration.length;
      if (end > start) spans.push({ text: narration.slice(start, end), origin: "narrator" });
    }
    const start = haystack[item.from].index;
    const last = haystack[item.to - 1];
    const end = last.index + last.char.length;
    spans.push({ text: narration.slice(start, end), origin: "authored", source: item.source });
    normalizedCursor = item.to;
  }
  if (normalizedCursor < haystack.length) {
    spans.push({ text: narration.slice(haystack[normalizedCursor].index), origin: "narrator" });
  }
  return spans.filter((span) => span.text.length > 0);
}

export function knowledgeAvailableByTurn(turnsWithBundles) {
  const available = new Set();
  return turnsWithBundles.map(({ turn, bundle }) => {
    if (bundle?.outcome === "committed") {
      for (const id of bundle.selected_reveal?.knowledge_ids || []) available.add(id);
    }
    return { turn, available: [...available].sort() };
  });
}
