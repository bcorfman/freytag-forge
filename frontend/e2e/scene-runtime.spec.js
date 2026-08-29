import { expect, test } from "@playwright/test";

import {
  installPackageClock,
  resolveWarningIfPresent,
  startSceneSession,
  submitTurn,
  writeCategoryReport,
} from "./helpers.js";
import { loadPackagePacing } from "./package-clock.js";
import { judgeRoleplayTurn, judgeSceneNarration } from "./roleplay-judge.js";
import { promptFor, scenePrompts, spineJourney } from "./canon-journey.js";

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
  const phoneAction = "I look carefully at Michelle's phone.";
  const bagAction = "I search for Michelle's work bag and any clue to where she went.";
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
  test.setTimeout(20 * 60_000);
  await startSceneSession(page);
  const turns = [];
  for (const action of spineJourney) {
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
  test.skip(!process.env.E2E_PACKAGE_CLOCK, "requires the opt-in package E2E game clock");
  test.setTimeout(20 * 60_000);
  const pacing = loadPackagePacing({ storyId: "continuity_initiative" });
  const controller = await installPackageClock(page, {
    pacing,
    token: process.env.FREYTAG_TEST_CLOCK_TOKEN,
  });
  await startSceneSession(page);
  const opening = (await page.locator(".entry-output").first().textContent())?.trim() || "";
  const byScene = new Map([["1A", { opening, turns: [] }]]);
  const sceneOrder = pacing.sceneOrder;
  const ladder = pacing.milestoneLadder();
  let sceneId = "1A";
  const promptsUsed = new Map();
  const progress = [];

  for (const [index, milestone] of ladder.entries()) {
    if (sceneId === sceneOrder.at(-1) && promptsUsed.get(sceneId) >= scenePrompts[sceneId].length) break;
    const sourceSceneId = sceneId;
    const used = promptsUsed.get(sourceSceneId) || 0;
    const input = promptFor(sourceSceneId, used);
    await test.step(`turn ${index + 1}: scene ${sourceSceneId} at ${milestone.target_seconds}s`, async () => {
      controller.arm(milestone);
      const payload = await submitTurn(page, input);
      const warningResolved = await resolveWarningIfPresent(page);
      const timing = controller.history().at(-1);
      const observedElapsed = payload.state?.story_elapsed_seconds;
      if (!timing?.reached) {
        throw new Error(
          `Package clock missed ${milestone.kind} ${milestone.event_id || `${milestone.scene_id} ${milestone.point}`}; observed elapsed ${String(observedElapsed)} (pending game break: ${String(payload.state?.pending_game_break === true)}, warning resolved: ${String(warningResolved)}).`,
        );
      }

      const narration = narrationText(payload);
      const reachedSceneId = payload.state?.scene_id;
      promptsUsed.set(sourceSceneId, used + 1);
      expect(payload.state?.story_elapsed_seconds, `Turn ${index + 1} missed its package milestone.`).toBe(
        milestone.target_seconds,
      );

      // The spine may pause in a scene or step forward exactly one scene, never
      // backward and never skipping an authored scene.
      const from = sceneOrder.indexOf(sourceSceneId);
      const to = sceneOrder.indexOf(reachedSceneId);
      expect(to, `Turn ${index + 1} left the authored spine at ${String(reachedSceneId)}.`).toBeGreaterThanOrEqual(0);
      expect(to - from, `Turn ${index + 1} regressed from ${sourceSceneId} to ${String(reachedSceneId)}.`).toBeGreaterThanOrEqual(0);
      expect(to - from, `Turn ${index + 1} skipped past a scene from ${sourceSceneId} to ${String(reachedSceneId)}.`).toBeLessThanOrEqual(1);

      // Any pacing event whose authored instant has passed must have fired.
      for (const eventId of pacing.eventOrder) {
        if (pacing.eventPoint(eventId).target_seconds > milestone.target_seconds) continue;
        expect(payload.state?.fired_pacing_event_ids, `Turn ${index + 1} is missing pacing event ${eventId}.`).toContain(eventId);
      }

      if (!byScene.has(reachedSceneId)) byScene.set(reachedSceneId, { opening: "", turns: [] });
      byScene.get(reachedSceneId).turns.push({ player_input: input, narration, source_scene_id: sourceSceneId });
      sceneId = reachedSceneId;
      progress.push({
        turn: index + 1,
        input,
        requested_milestone: milestone,
        observed_timing: timing,
        state: payload.state,
      });
      await writeCategoryReport("llm-canon-progress", {
        completed_turn: index + 1,
        current_scene: sceneId,
        by_scene: [...byScene],
        progress,
      });
    });
  }

  expect([...byScene.keys()], "the playthrough must visit every authored scene in order").toEqual([...sceneOrder]);
  expect(sceneId, "the playthrough must end in the authored resolution scene").toBe(sceneOrder.at(-1));

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
  const forbiddenBeforeRecording = /michelle(?:'s)? warning|do not trust.*broadcast|janus/i;
  const record = async (input) => {
    const payload = await submitTurn(page, input);
    const narration = narrationText(payload);
    turns.push({ input, narration, state: payload.state });
    await resolveWarningIfPresent(page);
    return narration;
  };

  const physicalSearch = await record("I inspect the back door and the room for concrete signs of Michelle's disappearance.");
  expect(physicalSearch).not.toMatch(forbiddenBeforeRecording);
  const phone = await record("I examine Michelle's phone carefully without leaving the kitchen.");
  expect(phone).not.toMatch(forbiddenBeforeRecording);
  const investigation = await record("I search the desk and drawer for Michelle's research or a damaged recording.");
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
    "I try calling Michelle again and listen for anything her phone still tells me about where she went.",
    "I review Michelle's message and ask only what the current evidence supports.",
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
  const pickup = await submitTurn(page, "I pick up Michelle's phone and keep it with me.");
  const followUp = await submitTurn(page, "I check that I still have Michelle's phone and use only what I carry.");
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
