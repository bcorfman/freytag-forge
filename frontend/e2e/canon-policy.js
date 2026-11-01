export function requiredPacingEvents({
  pacing,
  sourceSceneId,
  reachedSceneId,
  observedTurns,
  turnsSinceSceneEntry,
}) {
  return pacing.eventOrder.filter((eventId) => {
    const event = pacing.eventPoint(eventId);
    const reachedSceneEventIsDue =
      event.scene_id === reachedSceneId && observedTurns >= event.target_turn;
    const departingSourceEventIsDue =
      event.scene_id === sourceSceneId &&
      reachedSceneId !== sourceSceneId &&
      turnsSinceSceneEntry + 1 >= event.target_turn;
    return reachedSceneEventIsDue || departingSourceEventIsDue;
  });
}

export async function answerClarifications({ payload, submit, maxRounds = 2 }) {
  if (typeof submit !== "function") {
    throw new Error("Cannot answer clarifications: submit must be a function.");
  }
  if (!Number.isSafeInteger(maxRounds) || maxRounds < 0) {
    throw new Error("Cannot answer clarifications: maxRounds must be a non-negative safe integer.");
  }

  const answers = [];
  let currentPayload = payload;
  let originalCommand;
  let noun;

  while (currentPayload?.clarification) {
    const clarification = currentPayload.clarification;
    if (originalCommand === undefined) originalCommand = clarification.original_command;
    if (noun === undefined) noun = clarification.noun;

    if (!Array.isArray(clarification.options) || clarification.options.length === 0) {
      throw new Error(
        `Cannot answer clarification for original command ${String(originalCommand)} and noun ${String(noun)}: options are empty.`,
      );
    }
    const optionName = clarification.options[0]?.name;
    if (typeof optionName !== "string" || optionName.trim().length === 0) {
      throw new Error(
        `Cannot answer clarification for original command ${String(originalCommand)} and noun ${String(noun)}: first option name must be a non-empty string.`,
      );
    }
    if (answers.length >= maxRounds) {
      throw new Error(
        `Could not resolve clarification for original command ${String(originalCommand)} and noun ${String(noun)} after ${String(maxRounds)} answers.`,
      );
    }

    answers.push(optionName);
    currentPayload = await submit(optionName);
  }

  return { payload: currentPayload, answers };
}
