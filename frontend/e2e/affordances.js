import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "../..");
const shownKinds = new Set(["narration", "action", "dialogue", "speech"]);

export function loadAffordanceMap(packageDir, { exec = execFileSync, cwd = repoRoot } = {}) {
  try {
    const output = exec("uv", ["run", "python", "-m", "bench.affordance_map", "--package", packageDir], {
      cwd,
      env: { ...process.env, TMPDIR: "/tmp", UV_CACHE_DIR: process.env.UV_CACHE_DIR || "/tmp/uv-cache" },
      encoding: "utf8",
    });
    return JSON.parse(output.toString());
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    throw new Error(`Could not load affordance map for ${packageDir}: ${detail}`, { cause: error });
  }
}

export function normalizeText(text) {
  return String(text ?? "")
    .replace(/[“”]/g, '"')
    .replace(/[‘’]/g, "'")
    .replace(/[–—]/g, "-")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

function termsFor(item) {
  return [item.name, ...(item.aliases || [])].filter(Boolean);
}

export function mentions(text, terms) {
  const value = normalizeText(text);
  return (terms || []).some((term) => {
    const normalized = normalizeText(term);
    if (!normalized) return false;
    return new RegExp(`(?<!\\w)${normalized.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?!\\w)`, "i").test(value);
  });
}

function sceneFor(map, sceneId) {
  return map.scenes?.find((scene) => scene.scene_id === sceneId);
}

function collectAffordances(map, sceneId, predicate) {
  const scene = sceneFor(map, sceneId);
  if (!scene) return [];
  const byEntity = new Map();
  for (const gate of scene.gates || []) {
    for (const affordance of gate.affordances || []) {
      if (!predicate(affordance)) continue;
      const current = byEntity.get(affordance.entity_id);
      if (current) {
        current.gates.push(`${gate.transition_id}:${gate.fact_id}`);
      } else {
        byEntity.set(affordance.entity_id, {
          entity_id: affordance.entity_id,
          name: affordance.name,
          aliases: [...(affordance.aliases || [])],
          kind: affordance.kind,
          gates: [`${gate.transition_id}:${gate.fact_id}`],
          terms: termsFor(affordance),
        });
      }
    }
  }
  return [...byEntity.values()];
}

export function firstStepAffordances(map, sceneId) {
  return collectAffordances(map, sceneId, (affordance) => affordance.visible_at_entry === true);
}

export function laterAffordances(map, sceneId) {
  return collectAffordances(map, sceneId, (affordance) => Boolean(affordance.revealed_by));
}

export function exploreInput(sceneEntry) {
  if (!sceneEntry?.location?.name) throw new Error("Cannot build exploration input: scene has no location.");
  const location = sceneEntry.location.name.replace(/^the\s+/i, "").trim();
  return `Search the ${location}.`;
}

function firstMatch(text, terms) {
  const normalized = normalizeText(text);
  for (const term of terms) {
    const value = normalizeText(term);
    const match = new RegExp(`(?<!\\w)${value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?!\\w)`, "i").exec(normalized);
    if (match) {
      const start = Math.max(0, match.index - 40);
      const end = Math.min(normalized.length, match.index + match[0].length + 40);
      return normalized.slice(start, end);
    }
  }
  return null;
}

function measured(affordance, shownLog, deadline) {
  const hit = shownLog.find((entry) => mentions(entry.text, affordance.terms));
  return {
    entity_id: affordance.entity_id,
    name: affordance.name,
    first_shown_turn: hit ? hit.turn : null,
    snippet: hit ? firstMatch(hit.text, affordance.terms) : null,
    ...(deadline ? { deadline_met: Boolean(hit && hit.turn <= 1) } : {}),
  };
}

export function measureScene({ sceneEntry, shownLog }) {
  const first = firstStepAffordances({ scenes: [sceneEntry] }, sceneEntry.scene_id);
  const later = laterAffordances({ scenes: [sceneEntry] }, sceneEntry.scene_id);
  const input = exploreInput(sceneEntry);
  const firstReport = first.map((item) => measured(item, shownLog, true));
  const laterReport = later.map((item) => measured(item, shownLog, false));
  return {
    scene_id: sceneEntry.scene_id,
    input,
    first_step: firstReport,
    later: laterReport,
    summary: {
      first_step_total: firstReport.length,
      shown_by_deadline: firstReport.filter((item) => item.deadline_met).length,
      never_shown: [...firstReport, ...laterReport].filter((item) => item.first_shown_turn === null).length,
    },
  };
}

export function formatMarkdown(report) {
  const scenes = report.scenes || [];
  const rows = ["| Scene | Affordance | First shown turn | Snippet |", "|---|---|---:|---|"];
  for (const scene of scenes) {
    for (const item of [...(scene.first_step || []), ...(scene.later || [])]) {
      rows.push(`| ${scene.scene_id} | ${item.name} | ${item.first_shown_turn ?? "NEVER"} | ${(item.snippet || "").replaceAll("|", "\\|")} |`);
    }
  }
  return rows.join("\n") + "\n";
}

export { shownKinds };
