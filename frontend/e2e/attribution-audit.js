import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { attributeNarration, eligibleAuthoredTexts, loadAuthoredText } from "./authored-spans.js";

function jsonFiles(dir, fragment) {
  return readdirSync(dir).filter((name) => name.endsWith(".json") && name.includes(fragment));
}

function records(value) {
  const result = [];
  const replicates = Array.isArray(value?.replicates) ? value.replicates : Object.entries(value || {}).map(([replicate, scenes]) => ({ replicate, scenes }));
  for (const replicateRecord of replicates) {
    const replicate = replicateRecord.replicate ?? replicateRecord.id ?? "unknown";
    const scenes = Array.isArray(replicateRecord.scenes)
      ? replicateRecord.scenes.map((scene) => [scene.scene, scene])
      : Object.entries(replicateRecord.scenes || {});
    for (const [scene, payload] of scenes) {
      for (const turn of payload?.turns || (Array.isArray(payload) ? payload : [])) result.push({ replicate, scene, turn });
    }
  }
  return result;
}

function bundleRecords(value) {
  const result = [];
  const replicates = Array.isArray(value?.replicates) ? value.replicates : Object.entries(value || {}).map(([replicate, scenes]) => ({ replicate, scenes }));
  for (const replicateRecord of replicates) {
    const replicate = replicateRecord.replicate ?? replicateRecord.id ?? "unknown";
    const scenes = Array.isArray(replicateRecord.scenes)
      ? replicateRecord.scenes.map((scene) => [scene.scene, scene])
      : Object.entries(replicateRecord.scenes || {});
    for (const [scene, payload] of scenes) {
      for (const item of payload?.bundles || []) result.push({ replicate, scene, turn: item.turn, bundle: item.attempt_bundle || item });
    }
  }
  return result;
}

function turnNumber(value) {
  return value?.turn ?? value?.turn_index ?? value?.index;
}

export function auditAttribution(dir) {
  const authored = loadAuthoredText(resolve(import.meta.dirname, "../.."));
  const turnFiles = jsonFiles(dir, "blind-player-r").filter((name) => !name.includes("bundles"));
  if (!turnFiles.length) throw new Error(`Could not find blind-player turn files in ${dir}.`);
  const turns = [];
  const bundles = [];
  const bundleFiles = new Set(jsonFiles(dir, "blind-player-bundles-r"));
  for (const turnFile of turnFiles) {
    const bundleFile = turnFile.replace("e2e-blind-player-r", "e2e-blind-player-bundles-r");
    if (!bundleFiles.has(bundleFile)) continue;
    const fileTurns = records(JSON.parse(readFileSync(resolve(dir, turnFile), "utf8")));
    const fileBundles = bundleRecords(JSON.parse(readFileSync(resolve(dir, bundleFile), "utf8")));
    for (const item of fileTurns) turns.push({ ...item, replicate: `${turnFile}:${item.replicate}` });
    for (const item of fileBundles) bundles.push({ ...item, replicate: `${turnFile}:${item.replicate}` });
  }
  const byKey = new Map(bundles.map((item) => [`${item.replicate}\0${item.scene}\0${item.turn ?? turnNumber(item.bundle)}`, item.bundle]));
  const report = [];
  const suspicious = [];
  const foundByKind = Object.create(null);
  const notFoundByKind = Object.create(null);
  let skippedTurns = 0;
  let turnsWithEligible = 0;
  let authoredChars = 0;
  let narrationChars = 0;
  for (const item of turns) {
    const bundle = byKey.get(`${item.replicate}\0${item.scene}\0${turnNumber(item.turn)}`);
    if (!bundle) {
      skippedTurns += 1;
      continue;
    }
    if (bundle.outcome !== "committed") continue;
    const eligible = eligibleAuthoredTexts(bundle, authored);
    const spans = attributeNarration(item.turn.text || "", eligible);
    const authoredSpans = spans.filter((span) => span.origin === "authored");
    const found = new Set(authoredSpans.map((span) => `${span.source.kind}\0${span.source.id}\0${span.text}`));
    const unmatched = eligible.filter((entry) => ![...found].some((key) => key.startsWith(`${entry.source.kind}\0${entry.source.id}\0`)));
    for (const entry of eligible) {
      const target = unmatched.includes(entry) ? notFoundByKind : foundByKind;
      target[entry.source.kind] = (target[entry.source.kind] || 0) + (unmatched.includes(entry) ? 1 : 0 || 0);
      if (!unmatched.includes(entry)) target[entry.source.kind] = (target[entry.source.kind] || 0) + 1;
    }
    const authoredCount = authoredSpans.reduce((sum, span) => sum + span.text.length, 0);
    const total = (item.turn.text || "").length;
    authoredChars += authoredCount;
    narrationChars += total;
    if (eligible.length) turnsWithEligible += 1;
    const row = {
      replicate: item.replicate,
      scene: item.scene,
      turn: turnNumber(item.turn),
      eligible_count: eligible.length,
      eligible_source_kinds: [...new Set(eligible.map((entry) => entry.source.kind))],
      authored_spans: authoredSpans.length,
      authored_chars: authoredCount,
      narrator_chars: total - authoredCount,
      eligible_unmatched: unmatched,
    };
    report.push(row);
    if ((bundle.transition_cause === "forced" || bundle.transition_cause === "timer" || bundle.story_complete) && !authoredSpans.length) {
      suspicious.push({ replicate: item.replicate, scene: item.scene, turn: turnNumber(item.turn) });
    }
  }
  const foundTotal = Object.values(foundByKind).reduce((sum, count) => sum + count, 0);
  const notFoundTotal = Object.values(notFoundByKind).reduce((sum, count) => sum + count, 0);
  return {
    turns: report,
    totals: {
      turns_audited: report.length,
      turns_skipped_no_bundle: skippedTurns,
      turns_with_any_eligible_text: turnsWithEligible,
      eligible_texts_found: foundTotal,
      eligible_texts_not_found: notFoundTotal,
      found_by_kind: foundByKind,
      not_found_by_kind: notFoundByKind,
      fraction_narration_characters_attributed_authored: narrationChars ? authoredChars / narrationChars : 0,
      suspicious_forced_timer_or_complete_without_authored_span: suspicious,
    },
  };
}

if (process.argv[1] && resolve(process.argv[1]) === resolve(import.meta.filename)) {
  const result = auditAttribution(process.argv[2]);
  const output = process.argv[3];
  if (output) {
    const { writeFileSync } = await import("node:fs");
    writeFileSync(output, `${JSON.stringify(result, null, 2)}\n`);
  }
  console.log(JSON.stringify(result.totals, null, 2));
}
