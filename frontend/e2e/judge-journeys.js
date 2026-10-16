import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

import { judgeSceneNarration } from "./roleplay-judge.js";
import { attributeNarration, eligibleAuthoredTexts, knowledgeAvailableByTurn, loadAuthoredText } from "./authored-spans.js";

const CHECKS = [
  "protected_safe",
  "exit_motivated",
  "rewards_investigation",
  "scene_local",
  "progressive",
  "canon_consistent",
  "rich",
];

function usableTurns(scene, bundlesByTurn, authored, knowledgeByTurn) {
  return (scene.turns || [])
    .filter((turn) => turn?.rejected !== true && typeof turn?.text === "string" && turn.text.trim())
    .map((turn) => {
      const attemptBundle = turn.attempt_bundle || bundlesByTurn.get(turn.turn);
      const authoredSpans = attemptBundle && authored
        ? attributeNarration(turn.text, eligibleAuthoredTexts(attemptBundle, authored))
          .filter((span) => span.origin === "authored")
          .map((span) => ({ text: span.text, source_kind: span.source.kind, source_id: span.source.id }))
        : [];
      const knowledgeAvailable = knowledgeByTurn?.get(turn.turn);
      return {
        player_input: turn.input,
        narration: turn.text,
        left_scene: turn.turn === scene.transition_turn,
        beats_projected: [],
        ...(authoredSpans.length ? { authored_spans: authoredSpans } : {}),
        ...(knowledgeAvailable ? { knowledge_available: knowledgeAvailable } : {}),
      };
    });
}

export function buildSceneJudgments(report) {
  const hasAnyBundle = (report.replicates || []).some((replicate) =>
    (replicate.scenes || []).some((scene) =>
      (scene.bundles || []).length > 0 || (scene.turns || []).some((turn) => turn?.attempt_bundle),
    ),
  );
  const authored = hasAnyBundle ? loadAuthoredText() : null;
  return (report.replicates || []).flatMap((replicate) =>
    (replicate.scenes || []).map((scene) => {
      const bundlesByTurn = new Map();
      for (const bundle of scene.bundles || []) {
        if (!bundlesByTurn.has(bundle?.turn)) bundlesByTurn.set(bundle.turn, bundle?.attempt_bundle);
      }
      const evidenceTurns = (scene.turns || [])
        .map((turn) => turn?.attempt_bundle || bundlesByTurn.get(turn?.turn) ? {
          ...turn,
          attempt_bundle: turn?.attempt_bundle || bundlesByTurn.get(turn?.turn),
        } : turn)
        .filter((turn) => turn?.rejected !== true);
      const revealedKnowledgeIds = [...new Set(evidenceTurns.flatMap((turn) => {
        if (turn?.attempt_bundle) {
          return turn.attempt_bundle.outcome === "committed" && Array.isArray(turn.attempt_bundle.selected_reveal?.knowledge_ids)
            ? turn.attempt_bundle.selected_reveal.knowledge_ids
            : [];
        }
        return Array.isArray(turn?.grounding_ids) ? turn.grounding_ids : [];
        }))].sort();
      const hasBundleEvidence = evidenceTurns.some((turn) => turn?.attempt_bundle);
      const hasGroundingFallback = evidenceTurns.some((turn) => !turn?.attempt_bundle);
      const hasSceneBundle = bundlesByTurn.size > 0 || hasBundleEvidence;
      const knowledgeByTurn = hasSceneBundle
        ? new Map(knowledgeAvailableByTurn(evidenceTurns.map((turn) => ({ turn: turn?.turn, bundle: turn?.attempt_bundle }))).map((item) => [item.turn, item.available]))
        : null;
      const turns = usableTurns(scene, bundlesByTurn, authored, knowledgeByTurn);
      return {
        replicate: replicate.replicate,
        scene_id: scene.scene,
        sceneId: scene.scene,
        opening: scene.opening_text || "",
        turns,
        revealedKnowledgeIds,
        reveal_evidence: hasBundleEvidence
          ? (hasGroundingFallback ? "mixed" : "committed_bundles")
          : "grounding_fallback",
        ...(turns.length ? {} : { skipped: true, skip_reason: "no usable turns" }),
      };
    }),
  );
}

function emptyTotals() {
  return Object.fromEntries(CHECKS.map((check) => [check, 0]));
}

function scoreVerdict(verdict, totals) {
  let score = 0;
  for (const check of CHECKS) {
    if (verdict[check] === true) {
      score += 1;
      totals[check] += 1;
    }
  }
  return score;
}

export async function judgeJourneys(report, { judge = judgeSceneNarration, scenes } = {}) {
  const wantedScenes = scenes == null ? null : new Set(scenes);
  const built = buildSceneJudgments(report).filter((scene) => wantedScenes == null || wantedScenes.has(scene.sceneId));
  const totalsByCheck = emptyTotals();
  const replicateResults = [];
  const byReplicate = new Map();

  for (const scene of built) {
    let result;
    if (scene.skipped) {
      result = { replicate: scene.replicate, scene_id: scene.sceneId, skipped: true, skip_reason: scene.skip_reason };
    } else {
      try {
        const verdict = await judge({
          sceneId: scene.sceneId,
          opening: scene.opening,
          turns: scene.turns,
          revealedKnowledgeIds: scene.revealedKnowledgeIds,
        });
        result = { replicate: scene.replicate, scene_id: scene.sceneId, ...verdict };
      } catch (error) {
        result = {
          replicate: scene.replicate,
          scene_id: scene.sceneId,
          error: error instanceof Error ? error.message : String(error),
        };
      }
    }

    const key = scene.replicate;
    let group = byReplicate.get(key);
    if (!group) {
      group = { replicate: key, scenes: [], score: 0, max_score: 0 };
      byReplicate.set(key, group);
      replicateResults.push(group);
    }
    group.scenes.push(result);
    if (!result.skipped && !result.error) {
      group.score += scoreVerdict(result, totalsByCheck);
      group.max_score += CHECKS.length;
    }
  }

  return {
    source: report.source || "e2e-blind-player.json",
    generated_at: new Date().toISOString(),
    judged_by: process.env.E2E_JUDGE_MODEL || "gpt-5.6-luna",
    replicates: replicateResults,
    totals_by_check: totalsByCheck,
    score: Object.values(totalsByCheck).reduce((sum, count) => sum + count, 0),
    max_score: replicateResults.reduce((sum, replicate) => sum + replicate.max_score, 0),
  };
}

function printTable(result) {
  for (const replicate of result.replicates) {
    for (const scene of replicate.scenes) {
      const bits = CHECKS.map((check) => scene[check] === true ? "1" : "0").join("");
      const status = scene.skipped ? "skipped" : scene.error ? `error: ${scene.error}` : scene.verdict;
      process.stdout.write(`${replicate.replicate}\t${scene.scene_id}\t${status}\t${bits}\n`);
    }
  }
  process.stdout.write(`totals\t\t${result.score}/${result.max_score}\t${CHECKS.map((check) => result.totals_by_check[check]).join(" ")}\n`);
}

async function main(argv) {
  const [inputPath, outputPath, replicateValue] = argv;
  if (!inputPath || !outputPath) throw new Error("Usage: node e2e/judge-journeys.js <e2e-blind-player.json> <out.json> [replicate numbers, comma separated]");
  const report = JSON.parse(await readFile(inputPath, "utf8"));
  const selected = replicateValue
    ? new Set(replicateValue.split(",").map((value) => Number.parseInt(value.trim(), 10)).filter(Number.isInteger))
    : null;
  const filtered = selected
    ? { ...report, source: inputPath, replicates: report.replicates.filter((replicate) => selected.has(replicate.replicate)) }
    : { ...report, source: inputPath };
  const result = await judgeJourneys(filtered);
  await writeFile(outputPath, `${JSON.stringify(result, null, 2)}\n`);
  printTable(result);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).catch((error) => {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  });
}
