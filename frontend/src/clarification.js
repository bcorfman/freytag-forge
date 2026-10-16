function validClarification(clarification) {
  return clarification && typeof clarification === "object" && !Array.isArray(clarification)
    && typeof clarification.original_command === "string" && clarification.original_command.trim()
    && typeof clarification.noun === "string" && clarification.noun.trim()
    && Array.isArray(clarification.options) && clarification.options.length > 0
    && clarification.options.every((option) => option && typeof option === "object" && !Array.isArray(option)
      && typeof option.id === "string" && option.id.trim()
      && typeof option.name === "string" && option.name.trim())
    && Number.isInteger(clarification.round) && clarification.round >= 0;
}

export function turnRequestBody(sessionId, command, pending) {
  const body = { session_id: sessionId, player_input: command };
  if (pending) {
    body.clarifies = pending.original_command;
    body.clarification_round = pending.round;
  }
  return body;
}

export function nextPending(payload) {
  const clarification = payload?.clarification;
  if (!validClarification(clarification)) return null;
  return { original_command: clarification.original_command, round: clarification.round };
}

export function isQuestionTurn(payload) {
  return nextPending(payload) !== null;
}
