import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";

const DEFAULT_ROOT = resolve(import.meta.dirname, "../..");

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function factIds(value) {
  return asArray(value)
    .map((item) => typeof item === "string" ? item : item?.fact_id)
    .filter((id) => typeof id === "string" && id);
}

function isPublic(entry) {
  return entry?.audience?.player_visible === true && entry.audience.kind !== "world_only";
}

function isAvailableInScene(entry, sceneId) {
  return asArray(entry?.available_in_scenes).includes(sceneId);
}

function establishedFactIds(entry) {
  return asArray(entry?.establishes)
    .map((operation) => operation?.fact_id)
    .filter((id) => typeof id === "string" && id);
}

function committedFacts(turn) {
  if (turn?.bundle?.outcome !== "committed") return [];
  return [...new Set(factIds(turn.bundle.committed_delta?.fact_predicates))];
}

function selectedKnowledgeIds(turn) {
  if (turn?.bundle?.outcome !== "committed") return [];
  return [...new Set(asArray(turn.bundle.selected_reveal?.knowledge_ids))];
}

function canonicalEventsByFact(routePackage) {
  const events = [
    ...asArray(routePackage?.canonical_bridge_events),
    ...asArray(routePackage?.canonical_resolution_events),
  ];
  const result = new Map();
  for (const event of events) {
    for (const factId of factIds(event?.produces)) {
      const factEvents = result.get(factId) || [];
      factEvents.push(event);
      result.set(factId, factEvents);
    }
  }
  return result;
}

function canonicalKnowledgeForFacts({ knowledgePackage, routePackage, sceneId, facts }) {
  const eventsByFact = canonicalEventsByFact(routePackage);
  const entries = asArray(knowledgePackage?.knowledge);
  const disclosed = [];
  const mappedFacts = new Set();
  for (const factId of facts) {
    const events = eventsByFact.get(factId) || [];
    const declaredMatches = entries.filter((entry) =>
      isAvailableInScene(entry, sceneId) &&
      establishedFactIds(entry).includes(factId) &&
      events.some((event) =>
        entry?.source?.canonical_event_id === event.id ||
        asArray(event?.realization_storylets).includes(entry?.source?.storylet_id),
      ),
    );
    if (declaredMatches.length) {
      mappedFacts.add(factId);
      disclosed.push(...declaredMatches.filter(isPublic));
    }
  }
  return { entries: disclosed, mappedFacts };
}

function entryView(entry) {
  const view = { id: entry.id, statement: entry.statement };
  if (entry?.audience?.kind === "world_only") view.world_only = true;
  return view;
}

function publicEntries(knowledgePackage) {
  return asArray(knowledgePackage?.knowledge).filter(isPublic);
}

function openingKnowledgeIds(scene) {
  return asArray(scene?.opening_knowledge_ids);
}

function scenePairs(scenes) {
  if (scenes instanceof Map) return [...scenes.entries()];
  if (Array.isArray(scenes)) {
    return scenes.map((scene) => Array.isArray(scene) ? scene : [scene.scene_id || scene.sceneId, scene]);
  }
  if (scenes && typeof scenes === "object") return Object.entries(scenes);
  return [];
}

function uniqueEntries(entries) {
  const seen = new Set();
  return entries.filter((entry) => {
    if (!entry || seen.has(entry.id)) return false;
    seen.add(entry.id);
    return true;
  });
}

export function protectedFactsForScene({ entries, sceneId, availableIds }) {
  return entries
    .filter((entry) => isAvailableInScene(entry, sceneId) && !availableIds.has(entry.id))
    .map(entryView);
}

export function loadCanonSources(root = DEFAULT_ROOT) {
  const require = createRequire(import.meta.url);
  const YAML = require("yaml");
  const storyRoot = resolve(root, "data/stories/continuity-initiative");
  return {
    knowledgePackage: YAML.parse(readFileSync(resolve(storyRoot, "knowledge.yaml"), "utf8")),
    routePackage: YAML.parse(readFileSync(resolve(storyRoot, "storylet-routes.yaml"), "utf8")),
  };
}

export function buildKnowledgeTimeline({ scenes, knowledgePackage, routePackage }) {
  const entries = asArray(knowledgePackage?.knowledge);
  const entriesById = new Map(publicEntries(knowledgePackage).map((entry) => [entry.id, entry]));
  const known = new Map();
  const unmapped = new Set();
  const byScene = new Map();

  for (const [sceneId, scene] of scenePairs(scenes)) {
    if (!sceneId || !scene) continue;
    for (const id of openingKnowledgeIds(scene)) {
      const entry = entriesById.get(id);
      if (entry && isAvailableInScene(entry, sceneId)) known.set(id, entry);
    }

    const sceneTurns = [];
    for (const turn of asArray(scene.turns)) {
      const before = [...known.values()].map(entryView);
      const beforeIds = new Set(known.keys());
      const facts = committedFacts(turn);
      const runtimeDeliveries = {
        authored_spans: asArray(turn.authored_spans)
          .map((span) => span?.text)
          .filter((text) => typeof text === "string"),
        committed_facts: facts,
      };

      const delivered = [];
      for (const id of selectedKnowledgeIds(turn)) {
        const entry = entriesById.get(id);
        if (entry && isAvailableInScene(entry, sceneId)) delivered.push(entry);
      }
      const canonical = canonicalKnowledgeForFacts({ knowledgePackage, routePackage, sceneId, facts });
      delivered.push(...canonical.entries);
      const mappedFacts = canonical.mappedFacts;
      for (const factId of facts) {
        if (!mappedFacts.has(factId) && !selectedKnowledgeIds(turn).some((id) => establishedFactIds(entriesById.get(id)).includes(factId))) {
          unmapped.add(factId);
        }
      }
      for (const entry of uniqueEntries(delivered)) known.set(entry.id, entry);

      const afterIds = new Set(known.keys());
      sceneTurns.push({
        knowledge_available_before_turn: before,
        knowledge_available: [...afterIds].sort(),
        runtime_deliveries: runtimeDeliveries,
        protected_facts: protectedFactsForScene({ entries, sceneId, availableIds: beforeIds }),
      });
    }
    byScene.set(sceneId, { ...scene, turns: sceneTurns });
  }

  return {
    byScene,
    by_scene: [...byScene],
    unmapped_committed_facts: [...unmapped].sort(),
  };
}

export function knowledgeEvidenceForScene(timeline, sceneId) {
  return timeline?.byScene?.get(sceneId) || timeline?.by_scene?.find(([id]) => id === sceneId)?.[1] || null;
}
