import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import YAML from "yaml";

const PACING_POINTS = new Set(["min", "nudge", "handoff"]);

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

export function loadPackagePacing({ storyId, repoRoot, pacingPath } = {}) {
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
  const sceneRecords = new Map();
  const sceneOrder = [];

  for (let index = 0; index < scenes.length; index += 1) {
    const entry = scenes[index];
    const identifier = `<scene at index ${index}>`;
    const sceneId = requiredId(entry, "scene_id", "scene", storyId, resolvedPacingPath, identifier);
    if (sceneRecords.has(sceneId)) {
      throw pacingError(storyId, resolvedPacingPath, sceneId, `duplicate scene id "${sceneId}"`);
    }

    const entryNode = sceneNodes[index];
    const min = turnCount(
      entry,
      "min_turns",
      sceneId,
      storyId,
      resolvedPacingPath,
      entryNode,
    );
    const nudge = turnCount(
      entry,
      "nudge_after_turns",
      sceneId,
      storyId,
      resolvedPacingPath,
      entryNode,
    );
    const handoff = turnCount(
      entry,
      "handoff_after_turns",
      sceneId,
      storyId,
      resolvedPacingPath,
      entryNode,
    );
    if (!(min <= nudge && nudge <= handoff)) {
      throw pacingError(
        storyId,
        resolvedPacingPath,
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
    const eventId = requiredId(entry, "id", "event", storyId, resolvedPacingPath, identifier);
    if (eventRecords.has(eventId)) {
      throw pacingError(storyId, resolvedPacingPath, eventId, `duplicate event id "${eventId}"`);
    }

    const sceneId = requiredId(entry, "scene_id", "event", storyId, resolvedPacingPath, eventId);
    const scene = sceneRecords.get(sceneId);
    if (!scene) {
      throw pacingError(storyId, resolvedPacingPath, eventId, `event names undeclared scene "${sceneId}"`);
    }

    const at = turnCount(
      entry,
      "at_turn",
      eventId,
      storyId,
      resolvedPacingPath,
      eventNodes[index],
    );
    if (at > scene.handoff) {
      throw pacingError(
        storyId,
        resolvedPacingPath,
        eventId,
        `at_turn must fall within scene "${sceneId}" 0..handoff_after_turns`,
      );
    }
    eventRecords.set(eventId, { sceneId, at });
  }

  const frozenSceneOrder = Object.freeze(sceneOrder);
  const sceneMilestones = new Map();
  for (const [sceneId, scene] of sceneRecords) {
    sceneMilestones.set(
      sceneId,
      new Map([
        ["min", Object.freeze({ kind: "scene_point", scene_id: sceneId, point: "min", target_turn: scene.min })],
        ["nudge", Object.freeze({ kind: "scene_point", scene_id: sceneId, point: "nudge", target_turn: scene.nudge })],
        ["handoff", Object.freeze({ kind: "scene_point", scene_id: sceneId, point: "handoff", target_turn: scene.handoff })],
      ]),
    );
  }

  const eventMilestones = new Map(
    [...eventRecords].map(([eventId, event]) => [
      eventId,
      Object.freeze({ kind: "pacing_event", scene_id: event.sceneId, event_id: eventId, target_turn: event.at }),
    ]),
  );

  const projection = {
    storyId,
    sceneOrder: frozenSceneOrder,
    eventOrder: Object.freeze([...eventRecords.keys()]),
    scenePoint(sceneId, point) {
      if (!sceneMilestones.has(sceneId)) {
        throw pacingError(storyId, resolvedPacingPath, sceneId, `scene "${sceneId}" is not declared`);
      }
      if (!PACING_POINTS.has(point)) {
        throw pacingError(storyId, resolvedPacingPath, point, `point "${point}" is not declared`);
      }
      return sceneMilestones.get(sceneId).get(point);
    },
    eventPoint(eventId) {
      if (!eventMilestones.has(eventId)) {
        throw pacingError(storyId, resolvedPacingPath, eventId, `event "${eventId}" is not declared`);
      }
      return eventMilestones.get(eventId);
    },
  };

  return Object.freeze(projection);
}
