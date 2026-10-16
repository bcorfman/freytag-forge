const NARRATION_KINDS = new Set(["narration", "action", "dialogue"]);
const TARGET_REVEAL_ID = "k_sl_2c_c_r1";

function asIds(value) {
  return Array.isArray(value) ? value.filter((id) => typeof id === "string") : [];
}

function payloadFor(turn) {
  return turn?.payload || turn?.body || turn;
}

function sceneOutFor(turn) {
  const payload = payloadFor(turn);
  return turn?.scene_out ?? turn?.scene_id ?? payload?.state?.scene_id ?? null;
}

function groundingIdsFor(payload) {
  if (Array.isArray(payload?.grounding_ids)) return payload.grounding_ids;
  return (payload?.segments || []).flatMap((segment) => segment?.grounding_ids || []);
}

function committedRevealIds(payload) {
  const bundle = payload?.attempt_bundle;
  if (bundle) {
    if (bundle.outcome !== "committed") return [];
    return asIds(bundle.selected_reveal?.knowledge_ids);
  }
  return asIds(groundingIdsFor(payload));
}

function narrationFor(payload) {
  return (payload?.segments || [])
    .filter((segment) => NARRATION_KINDS.has(segment?.kind))
    .map((segment) => segment?.text)
    .filter((text) => typeof text === "string")
    .join(" ")
    .trim();
}

function isRejected(payload) {
  return payload?.rejected === true
    || Number(payload?.status) >= 400
    || payload?.attempt_bundle?.outcome === "rejected";
}

export function summarizeReferenceCopy({
  identity,
  walkTurns = [],
  copyPayload = {},
  targetRevealId = TARGET_REVEAL_ID,
  sceneIn = null,
} = {}) {
  const copy = copyPayload || {};
  const committedIds = committedRevealIds(copy);
  const semanticMatch = copy.semantic_match ?? null;
  const earned = committedIds.includes(targetRevealId);
  const path = !earned
    ? "none"
    : semanticMatch == null
      ? "unknown"
      : semanticMatch.ran === false
        ? "exact"
        : semanticMatch.ran === true
          ? "semantic"
          : "unknown";

  const summary = {
    identity,
    walk_turn_count: walkTurns.length,
    reached_2c: walkTurns.some((turn) => sceneOutFor(turn) === "2C"),
    input: copy.input ?? copy.player_input ?? null,
    scene_in: copy.scene_in ?? sceneIn,
    committed_reveal_ids: [...new Set(committedIds)],
    earned_target: earned,
    semantic_match: semanticMatch,
    path,
    rejected: isRejected(copy),
    narration: narrationFor(copy),
  };

  if (targetRevealId === TARGET_REVEAL_ID) {
    summary.earned_c_r1 = earned;
  } else {
    summary.target_reveal_id = targetRevealId;
  }

  return summary;
}
