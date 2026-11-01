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
