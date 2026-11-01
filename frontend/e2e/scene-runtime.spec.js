import { expect, test } from "@playwright/test";

import {
  installPackageClock,
  resolveWarningIfPresent,
  startSceneSession,
  submitTurn,
  submitTurnObserved,
  writeCategoryReport,
} from "./helpers.js";
import { answerClarifications, requiredPacingEvents } from "./canon-policy.js";
import { canonTurnBudget, loadPackagePacing, nextPendingEvent } from "./package-clock.js";
import { buildKnowledgeTimelineReport, isFixedRefusalLine, recordTurnOutcome } from "./knowledge-timeline-record.js";
import { buildKnowledgeTimeline, knowledgeEvidenceForScene, loadCanonSources } from "./knowledge-available.js";
import { judgeRoleplayTurn, judgeSceneNarration } from "./roleplay-judge.js";
import { promptFor, scenePrompts } from "./canon-journey.js";
import { attributeNarration, eligibleAuthoredTexts, loadAuthoredText } from "./authored-spans.js";
import { partitionTransitionSegments } from "./scene-partition.js";
import { classifyFailure, evaluateSpine, loadExpectedReveals } from "./spine-record.js";
import { summarizeAliasSmoke } from "./alias-smoke-record.js";

const SPINE_MAX_TURNS = 120;

// The 3C resolution is route-driven: its escape, consequence and Phase Two events land around
// scene turns 13-14, so the spine keeps cycling prompts in 3C until the story completes or this cap.
const SPINE_MAX_3C_TURNS = 24;

function narrationText(payload) {
  const turnText = (payload.segments || [])
    .filter((segment) => ["narration", "action", "dialogue"].includes(segment.kind))
    .map((segment) => segment.text);
  expect(turnText, `Turn response lacks accepted turn text: ${JSON.stringify(payload)}`).not.toHaveLength(0);
  return turnText.join(" ").trim();
}

function recordRevealedKnowledge(scene, segments, bundle) {
  const ids = bundle
    ? bundle.outcome === "committed" ? bundle.selected_reveal?.knowledge_ids || [] : []
    : segments.flatMap((segment) => segment.grounding_ids || []);
  scene.revealedKnowledgeIds = [...new Set([...scene.revealedKnowledgeIds, ...ids])];
}

function bundleSummary(bundle, pacingEventIds = []) {
  return {
    outcome: bundle.outcome,
    transition_cause: bundle.transition_cause,
    story_complete: bundle.story_complete,
    selected_reveal: bundle.selected_reveal,
    cue_stage: bundle.cue_stage,
    committed_delta: bundle.committed_delta,
    pacing_event_ids: pacingEventIds,
  };
}

async function exerciseDistinctFreeTextActions(page) {
  await startSceneSession(page);
  const opening = (await page.locator(".entry-output").first().textContent())?.trim() || "";
  const phoneAction = "Look carefully at Michelle's phone.";
  const bagAction = "Search for Michelle's work bag and any clue to where she went.";
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
  test.setTimeout(45 * 60_000);
  await startSceneSession(page);
  const turns = [];
  const deliveryRecords = [];
  const perTurn = [];
  const promptsUsed = new Map();
  const expected = await loadExpectedReveals();
  const identity = { sha: null, runtime: null, channel: null };
  try {
    const response = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/v1/version`);
    if (response.ok()) {
      const version = await response.json();
      identity.sha = version.sha ?? null;
      identity.runtime = version.runtime ?? null;
      identity.channel = version.channel ?? null;
    }
  } catch {
    // Identity is diagnostic metadata; a version endpoint failure must not hide the run evidence.
  }
  let sceneId = "1A";
  let attemptedTurn = 0;
  let failure = null;
  let failedError = null;
  try {
    for (let index = 0; index < SPINE_MAX_TURNS; index += 1) {
      attemptedTurn = index + 1;
      const used = promptsUsed.get(sceneId) || 0;
      const input = promptFor(sceneId, used);
      const startedAt = Date.now();
      let payload;
      try {
        payload = await submitTurn(page, input);
      } catch (error) {
        const errorPayload = error?.payload;
        if (errorPayload) {
          const latency_ms = Date.now() - startedAt;
          const sceneOut = errorPayload.state?.scene_id;
          turns.push({ scene_id: sceneOut, elapsed_seconds: errorPayload.state?.story_elapsed_seconds });
          deliveryRecords.push(errorPayload.delivery || {});
          perTurn.push({
            n: index + 1,
            scene_in: sceneId,
            input,
            scene_out: sceneOut,
            bundle: errorPayload.attempt_bundle ? bundleSummary(errorPayload.attempt_bundle) : null,
            state_story_complete: errorPayload.state?.story_complete === true,
            latency_ms,
            delivery: errorPayload.delivery || {},
          });
        }
        throw error;
      }
      const latency_ms = Date.now() - startedAt;
      const sceneOut = payload.state?.scene_id;
      const bundle = payload.attempt_bundle ? bundleSummary(payload.attempt_bundle) : null;
      turns.push({ scene_id: sceneOut, elapsed_seconds: payload.state?.story_elapsed_seconds });
      deliveryRecords.push(payload.delivery || {});
      perTurn.push({
        n: index + 1,
        scene_in: sceneId,
        input,
        scene_out: sceneOut,
        bundle,
        state_story_complete: payload.state?.story_complete === true,
        latency_ms,
        delivery: payload.delivery || {},
      });
      await resolveWarningIfPresent(page);
      promptsUsed.set(sceneId, used + 1);
      sceneId = sceneOut;
      if (payload.story_complete === true || payload.state?.story_complete === true || bundle?.story_complete === true) break;
      if (sceneId === "3C" && (promptsUsed.get(sceneId) || 0) >= SPINE_MAX_3C_TURNS) break;
    }
  } catch (error) {
    const classified = classifyFailure(error);
    failure = {
      ...classified,
      message: error instanceof Error ? error.message : String(error),
      turn: attemptedTurn || perTurn.length + 1,
      quotaStop: classified.quotaStop === true,
    };
    failedError = error;
  }
  const sceneOrder = turns.map((turn) => turn.scene_id).filter(Boolean);
  const delivery = {
    total_turns: deliveryRecords.length,
    turns_with_misses: deliveryRecords.filter((record) => (record.must_convey_misses || []).length > 0).length,
    recovery_turns: deliveryRecords.filter((record) => record.recovery_used === true).length,
    guard_retry_turns: deliveryRecords.filter((record) => record.guard_retry_used === true).length,
    fallback_turns: deliveryRecords.filter((record) => record.fallback_used === true).length,
    miss_tally: {},
  };
  for (const record of deliveryRecords) {
    for (const factId of record.must_convey_misses || []) {
      delivery.miss_tally[factId] = (delivery.miss_tally[factId] || 0) + 1;
    }
  }
  const chains = evaluateSpine({ sceneOrder, perTurn, expected });
  await writeCategoryReport("spine", {
    ending_reachable: sceneOrder.at(-1) === "3C",
    dead_end: !sceneOrder.length,
    revelation_order: sceneOrder,
    pressure_trajectory: turns,
    distinct_paths_to_climax: [sceneOrder.join(">")],
    delivery,
    per_turn: perTurn,
    story_complete: chains.story_complete,
    chains,
    identity,
    latency: chains.latency,
    attempt: { failure, turns_completed: perTurn.length },
  });
  if (failedError) throw failedError;
  expect(sceneOrder.every((scene) => /^[123][ABC]$/.test(scene))).toBe(true);
  expect(sceneOrder.at(-1)).toBe("3C");
  expect(chains.story_complete, "the story must actually complete; reaching 3C is not the ending").toBe(true);
  expect(Object.keys(chains.chain_misses), `missing expected reveal chains: ${JSON.stringify(chains.chain_misses)}`).toHaveLength(0);
  expect(chains.c_r2_committed, "2C must commit k_sl_2c_c_r2").toBe(true);
});

test("judges every reached scene against its committed knowledge canon @llm-canon", async ({ page }) => {
  test.skip(!process.env.OPENAI_API_KEY, "requires OPENAI_API_KEY");
  test.skip(!process.env.E2E_PACKAGE_CLOCK, "requires the opt-in package E2E game clock");
  test.setTimeout(45 * 60_000);
  const pacing = loadPackagePacing({ storyId: "continuity_initiative" });
  const controller = await installPackageClock(page);
  const sessionPayload = await startSceneSession(page);
  const opening = (await page.locator(".entry-output").first().textContent())?.trim() || "";
  const initialScene = {
    opening,
    turns: [],
    revealedKnowledgeIds: [],
    opening_knowledge_ids: (sessionPayload?.opening?.segments || []).flatMap((segment) => segment.grounding_ids || []),
    ...(sessionPayload?.prompt ? { opening_prompt: sessionPayload.prompt } : {}),
  };
  recordRevealedKnowledge(initialScene, sessionPayload?.opening?.segments || []);
  const byScene = new Map([
    ["1A", initialScene],
  ]);
  const sceneOrder = pacing.sceneOrder;
  let sceneId = "1A";
  let turnIndex = 0;
  let turnsSinceSceneEntry = 0;
  const promptsUsed = new Map();
  const progress = [];
  const firedPacingEventIds = new Set();
  let authoredSpanTurns = 0;
  let bundlesSeen = 0;
  let revealEvidenceFallbackTurns = 0;
  let storyCompleteSeen = false;
  const authored = loadAuthoredText();
  const { knowledgePackage, routePackage } = loadCanonSources();

  const turnMilestoneFor = (currentSceneId, currentTurns) => {
    const pendingEvent = nextPendingEvent(pacing, currentSceneId, currentTurns, firedPacingEventIds);
    if (pendingEvent) return pendingEvent;

    const min = pacing.scenePoint(currentSceneId, "min");
    const nudge = pacing.scenePoint(currentSceneId, "nudge");
    const handoff = pacing.scenePoint(currentSceneId, "handoff");
    if (currentTurns < min.target_turn) return min;
    if (currentTurns < nudge.target_turn) return nudge;
    if (currentTurns < handoff.target_turn) return handoff;
    if (currentSceneId === sceneOrder.at(-1)) return null;
    throw new Error(`Scene ${currentSceneId} exceeded its handoff turn ${String(handoff.target_turn)}.`);
  };

  for (let index = 0; index < canonTurnBudget(pacing); index += 1) {
    if (storyCompleteSeen) break;
    const sourceSceneId = sceneId;
    const used = promptsUsed.get(sourceSceneId) || 0;
    const input = promptFor(sourceSceneId, used);
    const milestone = turnMilestoneFor(sourceSceneId, turnsSinceSceneEntry);
    await test.step(`turn ${index + 1}: scene ${sourceSceneId} at turn ${turnsSinceSceneEntry}`, async () => {
      const previousFiredPacingEventIds = new Set(firedPacingEventIds);
      if (milestone) controller.arm(milestone);
      const turnsUntilMilestone = milestone ? controller.turnsUntilMilestone() : null;
      let payload = await submitTurn(page, input);
      await resolveWarningIfPresent(page);
      const { payload: resolvedPayload, answers: clarificationAnswers } = await answerClarifications({
        payload,
        submit: async (answer) => {
          if (milestone) controller.arm(milestone);
          const answerPayload = await submitTurn(page, answer);
          await resolveWarningIfPresent(page);
          return answerPayload;
        },
      });
      payload = resolvedPayload;
      const bundle = payload.attempt_bundle;
      if (bundle) bundlesSeen += 1;
      if (payload.state?.story_complete === true || bundle?.story_complete === true) storyCompleteSeen = true;
      const timing = milestone ? controller.history().at(-1) : null;
      const observedTurns = payload.state?.turns_since_scene_entry;
      const reachedSameScene = payload.state?.scene_id === sourceSceneId;
      if (milestone && reachedSameScene && observedTurns > milestone.target_turn) {
        throw new Error(
          `Turn milestone ${milestone.kind} ${milestone.event_id || `${milestone.scene_id} ${milestone.point}`} was overshot: observed scene-relative turn ${String(observedTurns)} after ${String(turnsUntilMilestone)} turns were needed.`,
        );
      }

      const narration = narrationText(payload);
      const reachedSceneId = payload.state?.scene_id;
      promptsUsed.set(sourceSceneId, used + 1);
      expect(payload.state?.turn_index).toBe(turnIndex + 1);

      // The spine may pause in a scene or step forward exactly one scene, never
      // backward and never skipping an authored scene.
      const from = sceneOrder.indexOf(sourceSceneId);
      const to = sceneOrder.indexOf(reachedSceneId);
      expect(to, `Turn ${index + 1} left the authored spine at ${String(reachedSceneId)}.`).toBeGreaterThanOrEqual(0);
      expect(to - from, `Turn ${index + 1} regressed from ${sourceSceneId} to ${String(reachedSceneId)}.`).toBeGreaterThanOrEqual(0);
      expect(to - from, `Turn ${index + 1} skipped past a scene from ${sourceSceneId} to ${String(reachedSceneId)}.`).toBeLessThanOrEqual(1);

      for (const eventId of requiredPacingEvents({
        pacing,
        sourceSceneId,
        reachedSceneId,
        observedTurns,
        turnsSinceSceneEntry,
      })) {
        if (pacing.isConditional(eventId) && !payload.state?.fired_pacing_event_ids?.includes(eventId)) {
          // The payload hides facts, so a conditional event cannot be judged missing.
          continue;
        }
        expect(payload.state?.fired_pacing_event_ids, `Turn ${index + 1} is missing pacing event ${eventId}.`).toContain(eventId);
        firedPacingEventIds.add(eventId);
      }
      for (const eventId of payload.state?.fired_pacing_event_ids || []) {
        firedPacingEventIds.add(eventId);
      }
      const pacingEventIds = (payload.state?.fired_pacing_event_ids || [])
        .filter((eventId) => !previousFiredPacingEventIds.has(eventId))
        .sort();

      // Entering a scene emits its authored bridge followed by all satisfied entry
      // segments. The departure includes the bridge; the arrival is all entry segments.
      const entered = reachedSceneId !== sourceSceneId;
      const segments = (payload.segments || []).filter((segment) =>
        ["narration", "action", "dialogue"].includes(segment.kind),
      );
      // The turn belongs to the scene the player acted in, not the one it ended in.
      // Filing a departure turn under the destination hid it from the scene that had to
      // earn it: a turn that revealed nothing could carry the player out of the house,
      // and the judge only ever read it as the park's odd first line.
      const partition = partitionTransitionSegments(segments, {
        sourceSceneId,
        targetSceneId: reachedSceneId,
        authored,
      });
      const { departure, arrival } = partition;
      const sceneNarration = departure.map((segment) => segment.text).join(" ").trim();
      recordRevealedKnowledge(byScene.get(sourceSceneId), departure, bundle);
      if (sceneNarration) {
        const eligible = eligibleAuthoredTexts(bundle, authored);
        const authoredSpans = attributeNarration(sceneNarration, eligible)
          .filter((span) => span.origin === "authored")
          .map((span) => ({ text: span.text, source_kind: span.source.kind, source_id: span.source.id }));
        if (authoredSpans.length) authoredSpanTurns += 1;
        const turn = {
          player_input: input,
          narration: sceneNarration,
          left_scene: entered,
          beats_projected: payload.delivery?.beats_projected || [],
          ...(payload.prompt ? { prompt: payload.prompt } : {}),
          segments: departure.map((segment) => ({ kind: segment.kind, text: segment.text, grounding_ids: segment.grounding_ids || [] })),
          ...(bundle ? { bundle: bundleSummary(bundle, pacingEventIds) } : {}),
          ...(authoredSpans.length ? { authored_spans: authoredSpans } : {}),
        };
        byScene.get(sourceSceneId).turns.push(turn);
        const timeline = buildKnowledgeTimeline({ scenes: byScene, knowledgePackage, routePackage });
        const sceneEvidence = knowledgeEvidenceForScene(timeline, sourceSceneId);
        Object.assign(turn, sceneEvidence?.turns.at(-1) || {});
        if (!bundle) revealEvidenceFallbackTurns += 1;
      }
      if (entered && !byScene.has(reachedSceneId)) {
        const nextScene = {
          opening: arrival.map((segment) => segment.text).join("\n\n").trim(),
          turns: [],
          revealedKnowledgeIds: [],
          opening_knowledge_ids: arrival.flatMap((segment) => segment.grounding_ids || []),
          ...(payload.prompt ? { opening_prompt: payload.prompt } : {}),
        };
        recordRevealedKnowledge(nextScene, arrival);
        byScene.set(reachedSceneId, nextScene);
      }
      sceneId = reachedSceneId;
      turnIndex = payload.state?.turn_index;
      turnsSinceSceneEntry = payload.state?.turns_since_scene_entry;
      progress.push({
        turn: index + 1,
        input,
        requested_milestone: milestone,
        observed_timing: timing,
        state: payload.state,
        ...(clarificationAnswers.length ? { clarification_answers: clarificationAnswers } : {}),
      });
      await writeCategoryReport("llm-canon-progress", {
        completed_turn: index + 1,
        current_scene: sceneId,
        by_scene: [...byScene],
        progress,
        story_complete_seen: storyCompleteSeen,
        authored_span_turns: authoredSpanTurns,
        bundles_seen: bundlesSeen,
        reveal_evidence_fallback_turns: revealEvidenceFallbackTurns,
      });
    });
  }

  expect([...byScene.keys()], "the playthrough must visit every authored scene in order").toEqual([...sceneOrder]);
  expect(sceneId, "the playthrough must end in the authored resolution scene").toBe(sceneOrder.at(-1));
  expect(storyCompleteSeen, "the story must actually complete; reaching 3C is not the ending").toBe(true);

  // Judge every scene before asserting. Failing on the first verdict hides the
  // other eight, so a single weak scene costs a whole run's worth of evidence.
  const judgments = [];
  for (const [id, scene] of byScene) {
    const judgment = await judgeSceneNarration({ sceneId: id, ...scene });
    judgments.push({ scene_id: id, ...judgment });
  }
  await writeCategoryReport("llm-canon", {
    judgments,
    reached_scenes: [...byScene.keys()],
    story_complete_seen: storyCompleteSeen,
    authored_span_turns: authoredSpanTurns,
    bundles_seen: bundlesSeen,
    reveal_evidence_fallback_turns: revealEvidenceFallbackTurns,
  });

  const failures = judgments.filter((judgment) => judgment.verdict !== "pass");
  expect(
    failures.map((judgment) => `${judgment.scene_id}: ${judgment.reasons.join("; ")}`).join("\n\n"),
    "every reached scene must satisfy the narrative canon",
  ).toBe("");
  expect(judgments.at(-1)?.scene_id).toBe("3C");
});

test("preserves the Scene 1A knowledge timeline @knowledge-timeline", async ({ page }) => {
  test.skip(!process.env.E2E_KNOWLEDGE_TIMELINE, "requires an explicitly selected staged knowledge-timeline run");
  const versionResponse = page.waitForResponse((response) => {
    try {
      return response.request().method() === "GET" && new URL(response.url()).pathname === "/api/v1/version";
    } catch {
      return false;
    }
  });
  await startSceneSession(page);
  const version = await (await versionResponse).json();
  const records = [];
  let committedState = null;
  const forbiddenBeforeRecording = /michelle(?:'s)? warning|do not trust.*broadcast|janus/i;
  const record = async (input) => {
    const outcome = await submitTurnObserved(page, input);
    expect(outcome.ok, `expected committed turn for ${input}`).toBe(true);
    const narration = narrationText(outcome.body);
    records.push(recordTurnOutcome({ input, status: outcome.status, headers: outcome.headers, body: outcome.body, version }));
    committedState = outcome.body?.state ?? null;
    await resolveWarningIfPresent(page);
    return narration;
  };

  const physicalSearch = await record("Search the back door and room for signs of Michelle's disappearance.");
  expect(physicalSearch).not.toMatch(forbiddenBeforeRecording);
  const phone = await record("Examine Michelle's phone for useful evidence.");
  expect(phone).not.toMatch(forbiddenBeforeRecording);
  const investigation = await record("Search under the drawer in her workstation.");
  expect(investigation).toMatch(/warning|broadcast|recording|research|evidence|continuity|lead/i);
  const drawerRecord = records.at(-1);
  expect(drawerRecord.provider_selected_ids).toHaveLength(1);
  expect(drawerRecord.resolved_source_ids).toHaveLength(1);
  const gate = await record("Check the front gate for an arriving patrol.");
  if (/patrol tape/i.test(gate)) expect(gate).toMatch(/arriv|search|approach|reach/i);
  const followUp = await record("Reassess the house evidence for a concrete local consequence.");
  expect(followUp).not.toMatch(/nothing but silence|someone is watching/i);
  const invalidInput = "Probe the future lead for a response.";
  const lastCommittedState = committedState;
  const invalid = await submitTurnObserved(page, invalidInput);
  const invalidRecord = recordTurnOutcome({ input: invalidInput, status: invalid.status, headers: invalid.headers, body: invalid.body, version });
  records.push(invalidRecord);
  expect(invalid.ok).toBe(false);
  expect(invalid.status).toBe(409);
  const visibleLine = (await page.locator("#transcript .entry-system").last().textContent())?.trim() || "";
  const diagnosticDetailExposed =
    Object.prototype.hasOwnProperty.call(invalid.body || {}, "attempt_bundle") ||
    !isFixedRefusalLine(visibleLine);
  expect(visibleLine).not.toBe("");
  expect(visibleLine).not.toMatch(/k_future_invalid|\bk_[a-z0-9_]+\b|janus|protected/i);
  expect(invalid.headers["x-freytag-rejection-code"]).toBe("ineligible_selection");
  expect(invalidRecord.rejection_code).toBe("ineligible_selection");
  await writeCategoryReport(
    "knowledge-timeline",
    buildKnowledgeTimelineReport(version, records, {
      status: invalid.status,
      rejection_code: invalid.headers["x-freytag-rejection-code"] || null,
      visible_line: visibleLine,
      diagnostic_detail_exposed: diagnosticDetailExposed,
      turn_index: lastCommittedState?.turn_index ?? null,
    }),
  );
});

test("samples optional storylets without presenting a menu @storylets", async ({ page }) => {
  await startSceneSession(page);
  const prompts = [
    "Inspect the interrupted message, the room, and any detail that might deepen this situation.",
    "Follow an optional lead that remains relevant to the current scene.",
    "Return to the central objective after exploring the immediate complication.",
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

test("keeps the display budget clock independent from turn-based pressure @timed-events", async ({ page }) => {
  await startSceneSession(page);
  // patrol_arrives_1a is authored at_turn 4 with no other condition.
  await submitTurn(page, "Inspect the house for signs of mounting pressure.");
  await submitTurn(page, "Investigate the pressure that follows.");
  await submitTurn(page, "Search the kitchen.");
  const payload = await submitTurn(page, "Look out the front window.");
  await writeCategoryReport("timed-events", { state: payload.state });
  expect(payload.state?.story_elapsed_seconds).toBeGreaterThanOrEqual(240);
  expect(payload.state?.turn_index).toBe(4);
  expect(payload.state?.fired_pacing_event_ids).toContain("patrol_arrives_1a");
});

test("keeps NPC interaction and reveals bounded to the current scene @npc", async ({ page }) => {
  await startSceneSession(page);
  const prompts = [
    "Call Michelle again and listen for anything her phone still tells you about where she went.",
    "Review Michelle's message and ask what the current evidence supports.",
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
  const pickup = await submitTurn(page, "Pick up Michelle's phone and put it in my pocket.");
  await resolveWarningIfPresent(page);
  const followUp = await submitTurn(page, "Go out to the truck.");
  await resolveWarningIfPresent(page);
  await writeCategoryReport("world-state", {
    pickup_state: pickup.state,
    follow_up_state: followUp.state,
    pickup_phone: pickup.state?.things?.["Michelle's phone"],
    follow_up_phone: followUp.state?.things?.["Michelle's phone"],
    narration: followUp.segments,
  });
  expect(followUp.state?.scene_id).toBeTruthy();
  expect(pickup.state?.things?.["Michelle's phone"]?.held_by).toBe("Kristin Schweitzer");
  expect(followUp.state?.things?.["Michelle's phone"]?.held_by).toBe("Kristin Schweitzer");
});

test("handles aggressive and chaotic-but-legal policies without an accidental dead end @safety", async ({ page }) => {
  await startSceneSession(page);
  const prompts = [
    "Confront the obstacle firmly.",
    "Improvise a strange move that preserves every required route forward.",
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

test("keeps ordinary photo words safe in 1A and resolving in 1B @alias-smoke", async ({ page }) => {
  test.setTimeout(20 * 60_000);
  await startSceneSession(page);
  const identity = { sha: null, runtime: null, channel: null };
  try {
    const response = await page.request.get(`${process.env.E2E_API_BASE_URL}/api/v1/version`);
    if (response.ok()) {
      const version = await response.json();
      identity.sha = version.sha ?? null;
      identity.runtime = version.runtime ?? null;
      identity.channel = version.channel ?? null;
    }
  } catch {
    // Identity is diagnostic metadata; a version endpoint failure must not hide the run evidence.
  }

  const photoTurns = [];
  const oneBTurns = [];
  let turnsTotal = 0;
  const narrationFor = (body) => (body?.segments || [])
    .filter((segment) => ["narration", "action", "dialogue"].includes(segment.kind))
    .map((segment) => segment.text)
    .join(" ")
    .trim();
  const rejectionCodeFor = (outcome) => outcome.headers["x-freytag-rejection-code"] ?? null;

  for (const input of [
    "Look through the photos on Michelle's phone.",
    "Check Michelle's phone for a recent photograph.",
  ]) {
    const outcome = await submitTurnObserved(page, input);
    turnsTotal += 1;
    photoTurns.push({
      input,
      status: outcome.status,
      rejection_code: rejectionCodeFor(outcome),
      narration: narrationFor(outcome.body),
      scene_id: outcome.body?.state?.scene_id ?? null,
    });
    if (outcome.ok) await resolveWarningIfPresent(page);
  }

  let sceneId = "1A";
  let consecutiveWalkRejections = 0;
  let walkFailure = null;
  let walkTurns = 0;
  for (let n = 0; n < 14; n += 1) {
    const outcome = await submitTurnObserved(page, promptFor("1A", n));
    turnsTotal += 1;
    walkTurns += 1;
    sceneId = outcome.body?.state?.scene_id ?? sceneId;
    if (!outcome.ok) {
      consecutiveWalkRejections += 1;
      if (consecutiveWalkRejections >= 4) {
        walkFailure = "1B was not reached because 4 consecutive 1A walk turns were rejected.";
        break;
      }
      continue;
    }
    consecutiveWalkRejections = 0;
    await resolveWarningIfPresent(page);
    if (sceneId === "1B") break;
  }
  if (sceneId !== "1B" && !walkFailure) {
    walkFailure = `1B was not reached after ${walkTurns} further 1A turns.`;
  }

  let bundlesVisible = false;
  if (sceneId === "1B") {
    bundlesVisible = true;
    for (const input of [scenePrompts["1B"][0], scenePrompts["1B"][1]]) {
      const sceneIn = sceneId;
      const outcome = await submitTurnObserved(page, input);
      turnsTotal += 1;
      const attemptBundle = outcome.body?.attempt_bundle;
      bundlesVisible = bundlesVisible && Boolean(attemptBundle);
      oneBTurns.push({
        input,
        status: outcome.status,
        rejection_code: rejectionCodeFor(outcome),
        scene_in: sceneIn,
        scene_out: outcome.body?.state?.scene_id ?? null,
        committed_knowledge_ids: attemptBundle?.outcome === "committed"
          ? attemptBundle.selected_reveal?.knowledge_ids ?? []
          : [],
      });
      sceneId = outcome.body?.state?.scene_id ?? sceneId;
      if (outcome.ok) await resolveWarningIfPresent(page);
    }
  }

  const summary = summarizeAliasSmoke({ photoTurns, oneBTurns });
  await writeCategoryReport("alias-smoke", {
    identity,
    summary,
    photo_turns: photoTurns,
    one_b_turns: oneBTurns,
    turns_total: turnsTotal,
    bundles_visible: bundlesVisible,
  });

  expect(walkFailure, walkFailure || "1A walk reached 1B").toBeNull();
  expect(photoTurns.every((turn) => turn.status < 400), "every 1A photo prompt must be accepted").toBe(true);
  expect([...photoTurns, ...oneBTurns].every((turn) => turn.rejection_code !== "narration_known_term_leak"), "photo prompts must not leak unavailable terms").toBe(true);
  expect(oneBTurns).toHaveLength(2);
  expect(oneBTurns.every((turn) => turn.status < 400), "both 1B photo turns must be accepted").toBe(true);
  if (bundlesVisible) {
    expect(summary.one_b_a_r2_committed, "1B photograph reveal must commit k_sl_1b_a_r2").toBe(true);
    expect(summary.one_b_b_r1_committed, "1B photograph reveal must commit k_sl_1b_b_r1").toBe(true);
  }
});
