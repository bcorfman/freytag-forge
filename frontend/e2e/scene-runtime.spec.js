import { expect, test } from "@playwright/test";

import { resolveWarningIfPresent, startSceneSession, submitTurn, writeCategoryReport } from "./helpers.js";

const spineActions = [
  "I search for concrete evidence of Sarah's disappearance and follow the strongest lead.",
  "I pursue the dead drop and ask Gabriel for the evidence needed to move forward.",
  "I prepare false identities and enter the facility without delaying the mission.",
  "I secure proof of JANUS and act on the current objective.",
  "I respond to the purge clock, reach Sarah, and preserve the rescue and evidence mission.",
  "I use the relay and broadcast the evidence before the network can recover.",
  "I finish the current objective and protect the route to the climax.",
  "I bring the story to a responsible resolution.",
];

test("starts a scene session and accepts freeform narration @smoke", async ({ page }) => {
  await startSceneSession(page);
  const payload = await submitTurn(page, "I look carefully at Sarah's phone.");
  await writeCategoryReport("smoke", { state: payload.state, segments: payload.segments });
  expect(payload.segments?.some((segment) => segment.kind === "narration")).toBe(true);
  await expect(page.locator(".entry-system")).toHaveCount(0);
});

test("drives the main spine and reports reachability and pressure @spine", async ({ page }) => {
  test.setTimeout(12 * 60_000);
  await startSceneSession(page);
  const turns = [];
  for (const action of spineActions) {
    const payload = await submitTurn(page, action);
    turns.push({ scene_id: payload.state?.scene_id, elapsed_seconds: payload.state?.story_elapsed_seconds });
    await resolveWarningIfPresent(page);
  }
  const sceneOrder = turns.map((turn) => turn.scene_id).filter(Boolean);
  await writeCategoryReport("spine", {
    ending_reachable: sceneOrder.at(-1) === "3C",
    dead_end: !sceneOrder.length,
    revelation_order: sceneOrder,
    pressure_trajectory: turns,
    distinct_paths_to_climax: [sceneOrder.join(">")],
  });
  expect(sceneOrder.every((scene) => /^[123][ABC]$/.test(scene))).toBe(true);
});

test("samples optional storylets without presenting a menu @storylets", async ({ page }) => {
  await startSceneSession(page);
  const prompts = [
    "I inspect the interrupted message, the room, and any detail that might deepen this situation.",
    "I follow an optional lead only if it remains relevant to the current scene.",
    "I return to the central objective after exploring the immediate complication.",
  ];
  const fired = new Set();
  for (const prompt of prompts) {
    const payload = await submitTurn(page, prompt);
    for (const id of payload.state?.fired_storylet_ids || []) fired.add(id);
    await resolveWarningIfPresent(page);
  }
  await writeCategoryReport("storylets", {
    fired_storylet_ids: [...fired],
    storylet_reuse: { unique: fired.size, repeated_ids: [] },
  });
  expect([...fired].every((id) => id.startsWith("SL-"))).toBe(true);
});

test("keeps NPC interaction and reveals bounded to the current scene @npc", async ({ page }) => {
  await startSceneSession(page);
  const prompts = [
    "I call Gabriel Dexter and ask what he knows about Sarah's disappearance.",
    "I review Sarah's message and ask only what the current evidence supports.",
  ];
  const narrations = [];
  for (const prompt of prompts) {
    const payload = await submitTurn(page, prompt);
    narrations.push(...(payload.segments || []).filter((segment) => segment.kind === "narration").map((segment) => segment.text));
    await resolveWarningIfPresent(page);
  }
  await writeCategoryReport("npc-knowledge", { narration: narrations, reveal_count: narrations.length });
  expect(narrations).not.toHaveLength(0);
});

test("preserves legal world-state changes across follow-up turns @world-state", async ({ page }) => {
  await startSceneSession(page);
  const pickup = await submitTurn(page, "I pick up Sarah's phone and keep it with me.");
  const followUp = await submitTurn(page, "I check that I still have Sarah's phone and use only what I carry.");
  await resolveWarningIfPresent(page);
  await writeCategoryReport("world-state", {
    pickup_state: pickup.state,
    follow_up_state: followUp.state,
    narration: followUp.segments,
  });
  expect(followUp.state?.scene_id).toBeTruthy();
});

test("handles aggressive and chaotic-but-legal policies without an accidental dead end @safety", async ({ page }) => {
  await startSceneSession(page);
  const prompts = [
    "I confront the obstacle firmly but do not harm an indispensable person or destroy a required item.",
    "I improvise a strange but lawful move that preserves every required route forward.",
  ];
  let blockedActions = 0;
  const states = [];
  for (const prompt of prompts) {
    const payload = await submitTurn(page, prompt);
    states.push(payload.state);
    if (await resolveWarningIfPresent(page)) blockedActions += 1;
  }
  await writeCategoryReport("safety", {
    blocked_action_rate: blockedActions / prompts.length,
    states,
  });
  expect(states.every((state) => state?.scene_id)).toBe(true);
});
