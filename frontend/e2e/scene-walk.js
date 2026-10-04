import { promptFor, scenePrompts } from "./canon-journey.js";

const acceptedKinds = new Set(["narration", "action", "dialogue", "speech"]);
const MAX_STALLED_TURNS = 5;

function turnText(payload) {
  return (payload.segments || [])
    .filter((segment) => acceptedKinds.has(segment.kind))
    .map((segment) => segment.text)
    .filter(Boolean)
    .join(" ")
    .trim();
}

function milestoneFor(pacing, sceneId, turns, fired) {
  const event = (pacing.eventOrder || [])
    .map((id) => pacing.eventPoint(id))
    .find((candidate) => candidate.scene_id === sceneId && !fired.has(candidate.event_id) && candidate.target_turn >= turns);
  if (event) return event;
  for (const point of ["min", "nudge", "handoff"]) {
    const milestone = pacing.scenePoint(sceneId, point);
    if (turns < milestone.target_turn) return milestone;
  }
  if (sceneId === pacing.sceneOrder.at(-1)) return null;
  throw new Error(`Scene ${sceneId} exceeded its handoff turn.`);
}

export async function walkScenes({
  page,
  pacing,
  controller,
  sceneIds,
  onOpening,
  onTurn,
  maxTurns = 45,
  exploreFor,
  submitTurn: submit = null,
  startSession = null,
  resolveWarning = null,
}) {
  if (!sceneIds?.length) throw new Error("walkScenes requires at least one scene.");
  if (!exploreFor) throw new Error("walkScenes requires exploreFor.");
  const send = submit || (await import("./helpers.js")).submitTurn;
  const start = startSession || (await import("./helpers.js")).startSceneSession;
  const resolveWarningIfPresent = resolveWarning || (await import("./helpers.js")).resolveWarningIfPresent;
  const session = await start(page);
  let current = session?.state?.scene_id || pacing.sceneOrder[0];
  let turnsSinceEntry = 0;
  let totalTurns = 0;
  let stalled = 0;
  let committed = 0;
  const promptsUsed = new Map();
  const fired = new Set();
  const reached = new Set();
  await onOpening?.({ scene_id: current, text: (await page.locator(".entry-output").first().textContent())?.trim() || "", via: "entry-output" });
  reached.add(current);

  while (totalTurns < maxTurns) {
    const source = current;
    const used = promptsUsed.get(source) || 0;
    const input = sceneIds.includes(source) && used === 0 ? exploreFor(source) : promptFor(source, used);
    const milestone = milestoneFor(pacing, source, turnsSinceEntry, fired);
    if (milestone) controller?.arm(milestone);
    const payload = await send(page, input);
    await resolveWarningIfPresent(page);
    totalTurns += 1;
    promptsUsed.set(source, used + 1);
    const next = payload.state?.scene_id;
    const segments = (payload.segments || []).filter((segment) => acceptedKinds.has(segment.kind));
    const entered = next !== source;
    const departure = entered ? segments.slice(0, -1) : segments;
    const text = departure.map((segment) => segment.text).filter(Boolean).join(" ").trim();
    if (!next) throw new Error(`Turn ${totalTurns} returned no scene id.`);
    const fromIndex = pacing.sceneOrder.indexOf(source);
    const toIndex = pacing.sceneOrder.indexOf(next);
    if (fromIndex < 0 || toIndex < fromIndex || toIndex > fromIndex + 1) {
      throw new Error(`Scene walk moved from ${source} to ${next} outside the one-scene-at-a-time path.`);
    }
    await onTurn?.({ scene_id: source, turn: turnsSinceEntry + 1, input, text, payload });
    const committedNow = (payload.state?.fired_storylet_ids || []).length;
    stalled = committedNow === committed && next === source ? stalled + 1 : 0;
    committed = committedNow;
    if (stalled >= MAX_STALLED_TURNS) throw new Error(`Scene ${source} stalled for ${stalled} turns.`);
    for (const id of payload.state?.fired_pacing_event_ids || []) fired.add(id);
    if (entered) {
      const opening = segments.at(-1);
      if (!opening?.text) throw new Error(`Scene ${next} was entered without an opening segment.`);
      reached.add(next);
      await onOpening?.({ scene_id: next, text: opening.text.trim(), via: "entering-turn" });
      turnsSinceEntry = 0;
    } else {
      turnsSinceEntry = payload.state?.turns_since_scene_entry ?? turnsSinceEntry + 1;
    }
    current = next;
    if (reached.has(sceneIds.at(-1)) && source === sceneIds.at(-1) && used === 0) return { session, turns: totalTurns };
  }
  throw new Error(`Scene walk exceeded its ${maxTurns}-turn limit.`);
}

export { turnText, scenePrompts };
