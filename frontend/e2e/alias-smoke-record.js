export const PHOTO_WORDS = /\b(photo|photograph|picture)s?\b/i;

export function usesPhotoWord(text) {
  return typeof text === "string" && PHOTO_WORDS.test(text);
}

function isRejected(status) {
  return Number(status) >= 400;
}

export function summarizeAliasSmoke({ photoTurns = [], oneBTurns = [] } = {}) {
  const photo_prompts_rejected = photoTurns.filter((turn) => isRejected(turn?.status)).length;
  const photo_rejections_term_leak = photoTurns.filter(
    (turn) => turn?.rejection_code === "narration_known_term_leak",
  ).length;
  const narrations_with_photo_word = photoTurns.filter((turn) => usesPhotoWord(turn?.narration)).length;
  const committedIds = oneBTurns.flatMap((turn) => Array.isArray(turn?.committed_knowledge_ids) ? turn.committed_knowledge_ids : []);

  return {
    photo_prompts: photoTurns.length,
    photo_prompts_rejected,
    photo_rejections_term_leak,
    narrations_with_photo_word,
    elicited: narrations_with_photo_word > 0,
    one_b_a_r2_committed: committedIds.includes("k_sl_1b_a_r2"),
    one_b_b_r1_committed: committedIds.includes("k_sl_1b_b_r1"),
    one_b_rejected: oneBTurns.filter((turn) => isRejected(turn?.status)).length,
  };
}
