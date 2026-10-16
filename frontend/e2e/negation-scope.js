import { summarizeReferenceCopy } from "./reference-copy.js";

const TARGET_REVEAL_ID = "k_sl_1a_f_r1";
const SCENE_ID = "1A";

export function summarizeNegationScope({ identity, turns = [] } = {}) {
  const summarizedTurns = turns.map(({ input, expect, payload }) => {
    const summary = summarizeReferenceCopy({
      identity,
      copyPayload: payload,
      targetRevealId: TARGET_REVEAL_ID,
      sceneIn: SCENE_ID,
    });
    const ok = (expect === "earned") === summary.earned_target && !summary.rejected;

    return {
      input,
      expect,
      earned_target: summary.earned_target,
      semantic_match: summary.semantic_match,
      path: summary.path,
      rejected: summary.rejected,
      ok,
    };
  });

  return {
    identity,
    turns: summarizedTurns,
    all_ok: summarizedTurns.every((turn) => turn.ok),
  };
}
