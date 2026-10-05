import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { aggregate, aggregateByScene, formatMarkdown } from "./blind-player.js";

export function replicatePlan(env = process.env) {
  const indexValue = env.E2E_BLIND_REPLICATE_INDEX;
  if (indexValue !== undefined) {
    if (!/^[1-3]$/.test(indexValue)) {
      throw new Error("E2E_BLIND_REPLICATE_INDEX must be an integer between 1 and 3.");
    }
    const index = Number(indexValue);
    return { indices: [index], category: `blind-player-r${index}` };
  }

  const replicates = Number.parseInt(env.E2E_BLIND_REPLICATES || "1", 10);
  if (replicates < 1 || replicates > 3) throw new Error("E2E_BLIND_REPLICATES must be between 1 and 3.");
  return { indices: Array.from({ length: replicates }, (_, offset) => offset + 1), category: "blind-player" };
}

export function mergeReports(reports) {
  if (!reports.length) throw new Error("Cannot merge an empty list of reports.");
  const [first] = reports;
  if (!Array.isArray(first.replicates)) throw new Error("A report must have a replicates array.");
  for (const report of reports.slice(1)) {
    if (report.story_id !== first.story_id || report.scene !== first.scene) {
      throw new Error("Reports must have the same story_id and scene.");
    }
    if (!Array.isArray(report.replicates)) throw new Error("A report must have a replicates array.");
  }
  const replicates = reports.flatMap((report) => report.replicates).map((replicate, index) => ({ ...replicate, replicate: index + 1 }));
  const report = first.scene === "all"
    ? { story_id: first.story_id, scene: "all", replicates, by_scene: aggregateByScene(replicates) }
    : { story_id: first.story_id, scene: first.scene, replicates, aggregate: aggregate(replicates) };
  return { ...report, markdown: formatMarkdown(report) };
}

async function readReports(artifactsDir, count) {
  const reports = [];
  for (let index = 1; index <= count; index += 1) {
    const label = `r${index}`;
    const path = resolve(artifactsDir, `e2e-blind-player-${label}.json`);
    let contents;
    try {
      contents = await readFile(path, "utf8");
      reports.push(JSON.parse(contents));
    } catch (error) {
      throw new Error(`Could not read ${label}: ${error instanceof SyntaxError ? "invalid JSON" : "file is missing or unreadable"}.`);
    }
  }
  return reports;
}

async function main(argv) {
  const [artifactsDir, countValue] = argv;
  if (!artifactsDir || !/^[1-3]$/.test(countValue || "")) {
    throw new Error("Usage: node e2e/merge-blind-player.js <artifacts-dir> <count>, where count is 1, 2, or 3.");
  }
  const reports = await readReports(artifactsDir, Number(countValue));
  const merged = mergeReports(reports);
  const jsonPath = resolve(artifactsDir, "e2e-blind-player.json");
  const markdownPath = resolve(artifactsDir, "e2e-blind-player.md");
  await writeFile(jsonPath, `${JSON.stringify(merged, null, 2)}\n`);
  await writeFile(markdownPath, `# blind-player E2E evaluation\n\n\`\`\`json\n${JSON.stringify(merged, null, 2)}\n\`\`\`\n`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).catch((error) => {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`, () => {
      process.exitCode = 1;
    });
  });
}
