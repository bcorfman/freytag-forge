import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import YAML from "yaml";

const PACING_POINTS = new Set(["min", "nudge", "handoff"]);

export function canonTurnBudget(pacing, margin = 5) {
  return pacing.sceneOrder.reduce((total, sceneId) => {
    let handoff;
    try {
      handoff = pacing.scenePoint(sceneId, "handoff");
    } catch {
      throw new Error(`Scene "${sceneId}" has no handoff point in package pacing.`);
    }
    if (!handoff || !Number.isSafeInteger(handoff.target_turn)) {
      throw new Error(`Scene "${sceneId}" has no handoff point in package pacing.`);
    }
    return total + handoff.target_turn + 1;
  }, margin);
}

export function nextPendingEvent(pacing, sceneId, currentTurns, firedEventIds) {
  return pacing.eventOrder
    .map((eventId) => pacing.eventPoint(eventId))
    .find(
      (event) =>
        event.scene_id === sceneId &&
        !firedEventIds.has(event.event_id) &&
        (pacing.isConditional(event.event_id)
          ? event.target_turn > currentTurns
          : event.target_turn >= currentTurns),
    );
}

function pacingError(storyId, pacingPath, identifier, detail) {
  return new Error(
    `Invalid pacing for story "${storyId}" in "${pacingPath}" (identifier "${identifier}"): ${detail}`,
  );
}

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function requiredId(entry, field, kind, storyId, pacingPath, identifier) {
  if (!isRecord(entry) || typeof entry[field] !== "string" || entry[field].length === 0) {
    throw pacingError(storyId, pacingPath, identifier, `missing ${kind} ${field} field`);
  }
  return entry[field];
}

function mappingValue(node, field) {
  if (!node || !Array.isArray(node.items)) return undefined;
  return node.items.find((pair) => pair.key?.value === field)?.value;
}

function sequenceItems(node) {
  return Array.isArray(node?.items) ? node.items : [];
}

function turnCount(entry, field, identifier, storyId, pacingPath, entryNode) {
  const valueNode = mappingValue(entryNode, field);
  const isDecimalInteger =
    valueNode == null ||
    (valueNode.type === "PLAIN" &&
      typeof valueNode.value === "number" &&
      /^[+]?[0-9]+$/.test(valueNode.source));
  if (!Number.isSafeInteger(entry[field]) || entry[field] < 0 || !isDecimalInteger) {
    throw pacingError(
      storyId,
      pacingPath,
      identifier,
      `${field} must be a non-negative integer`,
    );
  }
  return entry[field];
}

function list(value, field, storyId, pacingPath) {
  if (value === undefined) return [];
  if (!Array.isArray(value)) {
    throw pacingError(storyId, pacingPath, field, `${field} must be a list`);
  }
  return value;
}

function yamlDocument(source, storyId, pacingPath, identifier) {
  try {
    const document = YAML.parseDocument(source);
    if (document.errors.length > 0) throw document.errors[0];
    return document;
  } catch (error) {
    throw pacingError(storyId, pacingPath, identifier, `malformed YAML: ${error.message}`);
  }
}

function normalizedNode(node, fields) {
  return {
    items: fields.map(([field, sourceField]) => ({
      key: { value: field },
      value: mappingValue(node, sourceField),
    })),
  };
}

function hasWhen(value) {
  return Array.isArray(value) ? value.length > 0 : isRecord(value) ? Object.keys(value).length > 0 : false;
}

function orderSourceEvents(events, requestedOrder) {
  if (!Array.isArray(requestedOrder) || requestedOrder.length === 0) return events;
  const byId = new Map(events.map((event) => [event.entry.id, event]));
  const selected = requestedOrder.flatMap((eventId) => {
    const event = byId.get(eventId);
    return event === undefined ? [] : [event];
  });
  const requestedIds = new Set(requestedOrder);
  return selected.concat(events.filter((event) => !requestedIds.has(event.entry.id)));
}

function buildProjection({ storyId, pacingPath, scenes, sceneNodes, events, eventNodes }) {
  const sceneRecords = new Map();
  const sceneOrder = [];

  for (let index = 0; index < scenes.length; index += 1) {
    const entry = scenes[index];
    const identifier = `<scene at index ${index}>`;
    const sceneId = requiredId(entry, "scene_id", "scene", storyId, pacingPath, identifier);
    if (sceneRecords.has(sceneId)) {
      throw pacingError(storyId, pacingPath, sceneId, `duplicate scene id "${sceneId}"`);
    }

    const entryNode = sceneNodes[index];
    const min = turnCount(entry, "min_turns", sceneId, storyId, pacingPath, entryNode);
    const nudge = turnCount(entry, "nudge_after_turns", sceneId, storyId, pacingPath, entryNode);
    const handoff = turnCount(entry, "handoff_after_turns", sceneId, storyId, pacingPath, entryNode);
    if (!(min <= nudge && nudge <= handoff)) {
      throw pacingError(
        storyId,
        pacingPath,
        sceneId,
        "scene turn points must be ordered min_turns <= nudge_after_turns <= handoff_after_turns",
      );
    }
    sceneRecords.set(sceneId, { min, nudge, handoff });
    sceneOrder.push(sceneId);
  }

  const eventRecords = new Map();
  for (let index = 0; index < events.length; index += 1) {
    const entry = events[index];
    const identifier = `<event at index ${index}>`;
    const eventId = requiredId(entry, "id", "event", storyId, pacingPath, identifier);
    if (eventRecords.has(eventId)) {
      throw pacingError(storyId, pacingPath, eventId, `duplicate event id "${eventId}"`);
    }

    const sceneId = requiredId(entry, "scene_id", "event", storyId, pacingPath, eventId);
    const scene = sceneRecords.get(sceneId);
    if (!scene) {
      throw pacingError(storyId, pacingPath, eventId, `event names undeclared scene "${sceneId}"`);
    }
    const at = turnCount(entry, "at_turn", eventId, storyId, pacingPath, eventNodes[index]);
    if (at > scene.handoff) {
      throw pacingError(
        storyId,
        pacingPath,
        eventId,
        `at_turn must fall within scene "${sceneId}" 0..handoff_after_turns`,
      );
    }
    const when = list(entry.when, "when", storyId, pacingPath);
    eventRecords.set(eventId, { sceneId, at, conditional: when.length > 0 });
  }

  const frozenSceneOrder = Object.freeze(sceneOrder);
  const sceneMilestones = new Map();
  for (const [sceneId, scene] of sceneRecords) {
    sceneMilestones.set(sceneId, new Map([
      ["min", Object.freeze({ kind: "scene_point", scene_id: sceneId, point: "min", target_turn: scene.min })],
      ["nudge", Object.freeze({ kind: "scene_point", scene_id: sceneId, point: "nudge", target_turn: scene.nudge })],
      ["handoff", Object.freeze({ kind: "scene_point", scene_id: sceneId, point: "handoff", target_turn: scene.handoff })],
    ]));
  }
  const eventMilestones = new Map([...eventRecords].map(([eventId, event]) => [
    eventId,
    Object.freeze({ kind: "pacing_event", scene_id: event.sceneId, event_id: eventId, target_turn: event.at }),
  ]));
  return Object.freeze({
    storyId,
    sceneOrder: frozenSceneOrder,
    eventOrder: Object.freeze([...eventRecords.keys()]),
    scenePoint(sceneId, point) {
      if (!sceneMilestones.has(sceneId)) throw pacingError(storyId, pacingPath, sceneId, `scene "${sceneId}" is not declared`);
      if (!PACING_POINTS.has(point)) throw pacingError(storyId, pacingPath, point, `point "${point}" is not declared`);
      return sceneMilestones.get(sceneId).get(point);
    },
    eventPoint(eventId) {
      if (!eventMilestones.has(eventId)) throw pacingError(storyId, pacingPath, eventId, `event "${eventId}" is not declared`);
      return eventMilestones.get(eventId);
    },
    isConditional(eventId) {
      if (!eventMilestones.has(eventId)) throw pacingError(storyId, pacingPath, eventId, `event "${eventId}" is not declared`);
      return eventRecords.get(eventId).conditional;
    },
  });
}

function loadSourcePacing({ storyId, sourcePath, scenesPath }) {
  const storyDocument = yamlDocument(readFileSync(sourcePath, "utf8"), storyId, sourcePath, "story.yaml");
  const story = storyDocument.toJS();
  if (!isRecord(story)) throw pacingError(storyId, sourcePath, "story.yaml", "the document must be a mapping");
  const sceneValues = list(story.scenes, "scenes", storyId, sourcePath);
  const sceneNodes = sequenceItems(mappingValue(storyDocument.contents, "scenes"));
  const scenes = [];
  const sourceEvents = [];
  const eventNodes = [];
  for (let index = 0; index < sceneValues.length; index += 1) {
    const sceneId = sceneValues[index];
    if (typeof sceneId !== "string" || sceneId.length === 0) {
      throw pacingError(storyId, sourcePath, `<scene at index ${index}>`, "missing scene scene_id field");
    }
    const scenePath = resolve(scenesPath, `${sceneId}.yaml`);
    let document;
    try {
      document = yamlDocument(readFileSync(scenePath, "utf8"), storyId, scenePath, `${sceneId}.yaml`);
    } catch (error) {
      throw error;
    }
    const scene = document.toJS();
    if (!isRecord(scene)) throw pacingError(storyId, scenePath, `${sceneId}.yaml`, "the document must be a mapping");
    if (!isRecord(scene.turns)) throw pacingError(storyId, scenePath, sceneId, "missing turns block");
    if (scene.scene !== sceneId) {
      throw pacingError(storyId, scenePath, sceneId, `scene file declares undeclared scene "${scene.scene}"`);
    }
    const turnsNode = mappingValue(document.contents, "turns");
    scenes.push({ scene_id: sceneId, min_turns: scene.turns.min, nudge_after_turns: scene.turns.nudge, handoff_after_turns: scene.turns.handoff });
    sceneNodes[index] = normalizedNode(turnsNode, [["min_turns", "min"], ["nudge_after_turns", "nudge"], ["handoff_after_turns", "handoff"]]);
    const sceneEvents = [];
    for (const [beatIndex, beat] of (Array.isArray(scene.beats) ? scene.beats : []).entries()) {
      sceneEvents.push({
        entry: { id: beat?.id, scene_id: sceneId, at_turn: beat?.at_turn, when: hasWhen(beat?.when) ? [beat.when] : [] },
        node: normalizedNode(sequenceItems(mappingValue(document.contents, "beats"))[beatIndex], [["at_turn", "at_turn"]]),
      });
    }
    for (const event of orderSourceEvents(sceneEvents, scene.order?.pacing_events)) {
      sourceEvents.push(event.entry);
      eventNodes.push(event.node);
    }
  }
  return buildProjection({ storyId, pacingPath: sourcePath, scenes, sceneNodes, events: sourceEvents, eventNodes });
}

export function loadPackagePacing({ storyId, repoRoot, pacingPath } = {}) {
  if (typeof storyId !== "string" || storyId.length === 0) {
    throw new Error("loadPackagePacing requires a non-empty storyId string");
  }
  const resolvedRepoRoot = resolve(repoRoot ?? resolve(import.meta.dirname, "../.."));
  const legacyPath = resolve(
    pacingPath ?? resolve(resolvedRepoRoot, "data", "stories", storyId.replaceAll("_", "-"), "pacing.yaml"),
  );
  if (pacingPath === undefined && !existsSync(legacyPath)) {
    const sourcePath = resolve(
      resolvedRepoRoot,
      "data",
      "stories",
      storyId.replaceAll("_", "-"),
      "source",
      "story.yaml",
    );
    if (existsSync(sourcePath)) {
      return loadSourcePacing({
        storyId,
        sourcePath,
        scenesPath: resolve(sourcePath, "..", "scenes"),
      });
    }
  }
  return loadLegacyPackagePacing({ storyId, repoRoot: resolvedRepoRoot, pacingPath: legacyPath });
}

function loadLegacyPackagePacing({ storyId, repoRoot, pacingPath } = {}) {
  if (typeof storyId !== "string" || storyId.length === 0) {
    throw new Error("loadPackagePacing requires a non-empty storyId string");
  }

  const resolvedRepoRoot = resolve(repoRoot ?? resolve(import.meta.dirname, "../.."));
  const resolvedPacingPath = resolve(
    pacingPath ?? resolve(resolvedRepoRoot, "data", "stories", storyId.replaceAll("_", "-"), "pacing.yaml"),
  );

  let source;
  try {
    source = readFileSync(resolvedPacingPath, "utf8");
  } catch (error) {
    throw pacingError(
      storyId,
      resolvedPacingPath,
      storyId,
      `pacing.yaml could not be read: ${error.message}`,
    );
  }

  let yamlDocument;
  let document;
  try {
    yamlDocument = YAML.parseDocument(source);
    if (yamlDocument.errors.length > 0) throw yamlDocument.errors[0];
    document = yamlDocument.toJS();
  } catch (error) {
    throw pacingError(storyId, resolvedPacingPath, "pacing.yaml", `malformed YAML: ${error.message}`);
  }

  if (!isRecord(document)) {
    throw pacingError(storyId, resolvedPacingPath, "pacing.yaml", "the document must be a mapping");
  }

  const scenes = list(document.scenes, "scenes", storyId, resolvedPacingPath);
  const events = list(document.events, "events", storyId, resolvedPacingPath);
  const scenesNode = mappingValue(yamlDocument.contents, "scenes");
  const eventsNode = mappingValue(yamlDocument.contents, "events");
  const sceneNodes = sequenceItems(scenesNode);
  const eventNodes = sequenceItems(eventsNode);
  return buildProjection({
    storyId,
    pacingPath: resolvedPacingPath,
    scenes,
    sceneNodes,
    events,
    eventNodes,
  });
}
