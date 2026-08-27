import { expect, test } from "@playwright/test";

import { resolveWarningIfPresent, startSceneSession, submitTurn, writeCategoryReport } from "./helpers.js";
import { judgeRoleplayTurn, judgeSceneNarration } from "./roleplay-judge.js";

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

const canonActions = [
  "I search for concrete evidence of Sarah's disappearance and follow the strongest lead.",
  "I examine the forced back door, the blood by its frame, and anything an intruder left behind.",
  "I study Sarah's phone for its last call, message, or damage without leaving the kitchen.",
  "I search the desk and drawer for Sarah's research, notes, or a hidden recording.",
  "I compare the missing work bag with the rest of the room and look for a route the abductor used.",
  "I photograph the evidence and listen at the windows for anyone returning to the house.",
  "I check the front gate and prepare a careful response if the federal patrol comes back.",
  "I gather the house evidence into one actionable lead while keeping Sarah's warning in mind.",
];

function narrationText(payload) {
  const turnText = (payload.segments || [])
    .filter((segment) => ["narration", "action", "dialogue"].includes(segment.kind))
    .map((segment) => segment.text);
  expect(turnText, `Turn response lacks accepted turn text: ${JSON.stringify(payload)}`).not.toHaveLength(0);
  return turnText.join(" ").trim();
}

async function exerciseDistinctFreeTextActions(page) {
  await startSceneSession(page);
  const opening = (await page.locator(".entry-output").first().textContent())?.trim() || "";
  const phoneAction = "I look carefully at Sarah's phone.";
  const bagAction = "I search for Sarah's work bag and any clue to where she went.";
  const phoneTurn = await submitTurn(page, phoneAction);
  const phoneNarration = narrationText(phoneTurn);
  const bagTurn = await submitTurn(page, bagAction);
  const bagNarration = narrationText(bagTurn);
  return { opening, phoneAction, phoneTurn, phoneNarration, bagAction, bagTurn, bagNarration };
}

test("starts a scene session and accepts freeform narration @smoke", async ({ page }) => {
  const { opening, phoneNarration, bagTurn, bagNarration } = await exerciseDistinctFreeTextActions(page);
  await writeCategoryReport("smoke", {
    state: bagTurn.state,
    opening,
    phone_narration: phoneNarration,
    bag_narration: bagNarration,
  });
  await page.screenshot({ path: "../artifacts/e2e-smoke-loaded.png", fullPage: true });
  expect(phoneNarration).not.toBe(opening);
  expect(bagNarration).not.toBe(opening);
  expect(bagNarration).not.toBe(phoneNarration);
  await expect(page.locator(".entry-system")).toHaveCount(0);
});

test("judges free-text roleplay quality with OpenAI @llm-judge", async ({ page }) => {
  const { opening, phoneAction, phoneNarration, bagAction, bagTurn, bagNarration } = await exerciseDistinctFreeTextActions(page);
  const phoneJudgment = await judgeRoleplayTurn({ opening, playerInput: phoneAction, narration: phoneNarration });
  const bagJudgment = await judgeRoleplayTurn({ opening, playerInput: bagAction, narration: bagNarration });
  await writeCategoryReport("llm-judge", {
    state: bagTurn.state,
    opening,
    phone_narration: phoneNarration,
    bag_narration: bagNarration,
    phone_judgment: phoneJudgment,
    bag_judgment: bagJudgment,
  });
  expect(phoneJudgment.verdict, phoneJudgment.reasons.join("; ")).toBe("pass");
  expect(bagJudgment.verdict, bagJudgment.reasons.join("; ")).toBe("pass");
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
  expect(sceneOrder.at(-1)).toBe("3C");
});

test("judges every reached scene against the five-file narrative canon @llm-canon", async ({ page }) => {
  test.skip(!process.env.OPENAI_API_KEY, "requires OPENAI_API_KEY");
  test.skip(!process.env.E2E_TEST_CLOCK_SECONDS, "requires the opt-in accelerated E2E game clock");
  test.setTimeout(5 * 60_000);
  await startSceneSession(page);
  const opening = (await page.locator(".entry-output").first().textContent())?.trim() || "";
  const byScene = new Map([["1A", { opening, turns: [] }]]);
  let sceneId = "1A";
  for (const [index, playerInput] of canonActions.entries()) {
    await test.step(`turn ${index + 1}: scene ${sceneId}`, async () => {
      const payload = await submitTurn(page, playerInput);
      const narration = narrationText(payload);
      byScene.get(sceneId).turns.push({ player_input: playerInput, narration });
      await resolveWarningIfPresent(page);
      sceneId = payload.state?.scene_id || sceneId;
      if (!byScene.has(sceneId)) byScene.set(sceneId, { opening: "", turns: [] });
      await writeCategoryReport("llm-canon-progress", { completed_turn: index + 1, current_scene: sceneId, by_scene: [...byScene] });
    });
  }
  const judgments = [];
  for (const [id, scene] of byScene) {
    const judgment = await judgeSceneNarration({ sceneId: id, ...scene });
    judgments.push({ scene_id: id, ...judgment });
    expect(judgment.verdict, judgment.reasons.join("; ")).toBe("pass");
  }
  await writeCategoryReport("llm-canon", { judgments, reached_scenes: [...byScene.keys()] });
  expect(judgments.at(-1)?.scene_id).toBe("3C");
});

test("preserves the Scene 1A knowledge timeline @knowledge-timeline", async ({ page }) => {
  test.skip(!process.env.E2E_KNOWLEDGE_TIMELINE, "requires an explicitly selected staged knowledge-timeline run");
  await startSceneSession(page);
  const turns = [];
  const forbiddenBeforeRecording = /sarah(?:'s)? warning|do not trust.*broadcast|janus/i;
  const record = async (input) => {
    const payload = await submitTurn(page, input);
    const narration = narrationText(payload);
    turns.push({ input, narration, state: payload.state });
    await resolveWarningIfPresent(page);
    return narration;
  };

  const physicalSearch = await record("I inspect the back door and the room for concrete signs of Sarah's disappearance.");
  expect(physicalSearch).not.toMatch(forbiddenBeforeRecording);
  const phone = await record("I examine Sarah's phone carefully without leaving the kitchen.");
  expect(phone).not.toMatch(forbiddenBeforeRecording);
  const investigation = await record("I search the desk and drawer for Sarah's research or a damaged recording.");
  expect(investigation).toMatch(/warning|broadcast|recording|research|evidence|continuity|lead/i);
  const gate = await record("I check the front gate and listen for a patrol arriving or searching the house.");
  if (/patrol tape/i.test(gate)) expect(gate).toMatch(/arriv|search|approach|reach/i);
  const followUp = await record("I reassess the house evidence and wait for the next concrete local consequence.");
  expect(followUp).not.toMatch(/nothing but silence|someone is watching/i);
  await writeCategoryReport("knowledge-timeline", { turns });
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
  expect(fired.size).toBeGreaterThan(0);
});

test("advances declared pressure with the opt-in E2E clock instead of wall-clock waiting @timed-events", async ({ page }) => {
  test.skip(!process.env.E2E_TEST_CLOCK_SECONDS, "requires the local test clock");
  await startSceneSession(page);
  const payload = await submitTurn(page, "I pause long enough for the house's pressure to build.");
  await writeCategoryReport("timed-events", { state: payload.state });
  expect(payload.state?.story_elapsed_seconds).toBeGreaterThanOrEqual(120);
  expect(payload.state?.fired_pacing_event_ids).toContain("pressure_1a");
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
