import { expect, test } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const policies = {
  "goal-focused": "I pursue the current objective decisively and preserve every route to Sarah and the evidence.",
  exploratory: "I investigate the current scene carefully, follow the strongest clue, and then move the mission forward.",
  social: "I build trust with the people here, ask for help, and turn what we learn into progress.",
  avoidant: "I take the safest legal option, avoid needless escalation, and still follow the current objective.",
  aggressive: "I confront the obstacle firmly but do not harm an indispensable person or destroy a required item.",
  "chaotic-but-legal": "I improvise an unexpected but lawful move that preserves the mission and advances the current objective.",
};
const expectedScenes = new Set(["1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"]);
const turnsPerPolicy = Number.parseInt(process.env.E2E_TURNS_PER_POLICY || "8", 10);

async function createSession(page) {
  await page.goto("/");
  await page.getByRole("button", { name: "New Session" }).click();
  await expect(page.locator("#transcript")).not.toBeEmpty();
}

async function runPolicy(page, policy, action) {
  const scenes = [];
  const narrations = [];
  const firedStorylets = new Set();
  const pressureTrajectory = [];
  let blockedActions = 0;
  for (let turn = 0; turn < turnsPerPolicy; turn += 1) {
    await page.locator("#command-input").fill(action);
    const response = page.waitForResponse(
      (candidate) => candidate.request().method() === "POST" && candidate.url().endsWith("/api/v1/turn"),
    );
    await page.getByRole("button", { name: "Send" }).click();
    const payload = await (await response).json();
    for (const storyletId of payload.state?.fired_storylet_ids || []) firedStorylets.add(storyletId);
    pressureTrajectory.push({
      elapsed_seconds: payload.state?.story_elapsed_seconds ?? null,
      scene_id: payload.state?.scene_id ?? null,
    });
    await expect(page.locator("#command-input")).toBeEnabled({ timeout: 90_000 });
    const warning = page.locator("#game-break-panel");
    if (await warning.isVisible()) {
      blockedActions += 1;
      await page.getByRole("button", { name: "Return to scene" }).click();
      await expect(warning).toBeHidden();
    }
    const status = (await page.locator("#status-line").textContent()) || "";
    const scene = /Scene ([0-9][A-Z])/.exec(status)?.[1];
    if (scene && scenes.at(-1) !== scene) scenes.push(scene);
    narrations.push(...(await page.locator(".entry-output").allTextContents()));
  }
  return {
    policy,
    blocked_actions: blockedActions,
    narrations,
    scene_order: scenes,
    fired_storylet_ids: [...firedStorylets],
    pressure_trajectory: pressureTrajectory,
  };
}

function summarize(results) {
  const paths = new Set(results.map((result) => result.scene_order.join(">")));
  const totalTurns = results.length * turnsPerPolicy;
  const blocked = results.reduce((sum, result) => sum + result.blocked_actions, 0);
  const endings = results.filter((result) => result.scene_order.at(-1) === "3C").length;
  const firedStorylets = results.flatMap((result) => result.fired_storylet_ids);
  const repeatedStorylets = results.flatMap((result) =>
    result.fired_storylet_ids.filter((id, index, ids) => ids.indexOf(id) !== index),
  );
  return {
    generated_at: new Date().toISOString(),
    policies: results,
    ending_reachability: { reached: endings, total: results.length, rate: endings / results.length },
    dead_ends: results.filter((result) => result.scene_order.length === 0).map((result) => result.policy),
    revelation_order: results.map((result) => ({ policy: result.policy, scene_order: result.scene_order })),
    storylet_reuse: {
      accepted: firedStorylets.length,
      unique: new Set(firedStorylets).size,
      repeated_ids: [...new Set(repeatedStorylets)],
    },
    selection_diversity: { distinct_scene_paths: paths.size, paths: [...paths] },
    pressure_trajectory: results.map((result) => ({ policy: result.policy, turns: result.pressure_trajectory })),
    blocked_action_rate: { blocked, turns: totalTurns, rate: blocked / totalTurns },
    distinct_paths_to_climax: [...paths].filter((path) => path.endsWith("3C")),
  };
}

async function writeReports(summary) {
  const root = resolve(import.meta.dirname, "../..");
  const json = resolve(root, "artifacts/policy-evaluation.json");
  const markdown = resolve(root, "artifacts/policy-evaluation.md");
  await mkdir(dirname(json), { recursive: true });
  await writeFile(json, `${JSON.stringify(summary, null, 2)}\n`);
  await writeFile(
    markdown,
    `# Manual Cloudflare policy evaluation\n\n- Policies: ${summary.policies.length}\n- Ending reachability: ${summary.ending_reachability.reached}/${summary.ending_reachability.total}\n- Blocked-action rate: ${(summary.blocked_action_rate.rate * 100).toFixed(1)}%\n- Distinct scene paths: ${summary.selection_diversity.distinct_scene_paths}\n- Paths to climax: ${summary.distinct_paths_to_climax.length}\n- Dead ends: ${summary.dead_ends.join(", ") || "none observed"}\n- Storylet reuse: ${summary.storylet_reuse.repeated_ids.join(", ") || "none observed"}\n`,
  );
}

test("manual Cloudflare policy evaluation", async ({ browser }) => {
  test.setTimeout(15 * 60_000);
  const results = [];
  for (const [policy, action] of Object.entries(policies)) {
    const page = await browser.newPage();
    await createSession(page);
    results.push(await runPolicy(page, policy, action));
    await page.close();
  }
  const summary = summarize(results);
  await writeReports(summary);
  expect(summary.policies).toHaveLength(Object.keys(policies).length);
  expect(summary.revelation_order.flatMap((item) => item.scene_order).every((scene) => expectedScenes.has(scene))).toBe(true);
  expect(summary.blocked_action_rate.rate).toBeLessThanOrEqual(1);
});
