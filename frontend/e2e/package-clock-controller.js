function readState(state, description) {
  if (
    state === null ||
    typeof state !== "object" ||
    Array.isArray(state) ||
    typeof state.scene_id !== "string" ||
    state.scene_id.length === 0 ||
    !Number.isSafeInteger(state.turn_index) ||
    state.turn_index < 0 ||
    !Number.isSafeInteger(state.turns_since_scene_entry) ||
    state.turns_since_scene_entry < 0 ||
    state.turns_since_scene_entry > state.turn_index
  ) {
    throw new Error(
      `${description}: missing or malformed turn state; expected a scene ID, a non-negative integer turn index, and a non-negative integer scene-relative turn value.`,
    );
  }
  return state;
}

function milestoneIdentity(milestone) {
  const eventDescription = milestone.event_id === undefined ? "" : `, event ${String(milestone.event_id)}`;
  return `scene ${String(milestone.scene_id)}${eventDescription}`;
}

function validateMilestone(milestone) {
  if (
    milestone === null ||
    typeof milestone !== "object" ||
    Array.isArray(milestone) ||
    (milestone.kind !== "scene_point" && milestone.kind !== "pacing_event") ||
    typeof milestone.scene_id !== "string" ||
    milestone.scene_id.length === 0 ||
    !Number.isSafeInteger(milestone.target_turn) ||
    milestone.target_turn < 0 ||
    (milestone.kind === "scene_point" && !new Set(["min", "nudge", "handoff"]).has(milestone.point)) ||
    (milestone.kind === "pacing_event" && typeof milestone.event_id !== "string") ||
    Object.hasOwn(milestone, "target_seconds")
  ) {
    throw new Error("Cannot arm milestone: malformed milestone target or identity; expected target_turn.");
  }
}

export function createPackageClockController() {
  let observedState = null;
  let armedMilestone = null;
  const records = [];

  return {
    observeState(state) {
      observedState = readState(state, "Cannot observe state");
    },

    arm(milestone) {
      validateMilestone(milestone);
      if (armedMilestone !== null) {
        throw new Error(
          `Cannot arm milestone ${milestoneIdentity(milestone)}: another milestone is already armed.`,
        );
      }
      armedMilestone = milestone;
    },

    armed() {
      return armedMilestone;
    },

    turnsUntilMilestone() {
      if (observedState === null) {
        throw new Error(
          "Cannot compute turns until milestone: no session or turn state has been observed.",
        );
      }
      if (armedMilestone === null) {
        throw new Error("Cannot compute turns until milestone: no milestone is armed.");
      }
      if (observedState.scene_id !== armedMilestone.scene_id) {
        throw new Error(
          `Cannot compute turns until milestone for ${milestoneIdentity(armedMilestone)}: observed scene ${observedState.scene_id} does not match the requested scene.`,
        );
      }

      const turns = armedMilestone.target_turn - observedState.turns_since_scene_entry;
      if (turns < 0) {
        throw new Error(
          `Cannot compute turns until milestone for ${milestoneIdentity(armedMilestone)}: observed turns_since_scene_entry ${observedState.turns_since_scene_entry} is later than requested target_turn ${armedMilestone.target_turn}.`,
        );
      }
      return turns;
    },

    observeTurnResponse(payload) {
      if (payload === null || typeof payload !== "object" || Array.isArray(payload)) {
        throw new Error("Cannot observe turn response: missing or malformed turn state.");
      }
      const state = readState(payload.state, "Cannot observe turn response");
      const priorState = observedState;
      observedState = state;

      if (armedMilestone === null) {
        return {
          reached: false,
          scene_id: state.scene_id,
          turn_index: state.turn_index,
          turns_since_scene_entry: state.turns_since_scene_entry,
          requested_milestone: null,
        };
      }

      const requestedMilestone = armedMilestone;
      armedMilestone = null;
      const reached =
        state.pending_game_break !== true &&
        state.scene_id === requestedMilestone.scene_id &&
        state.turns_since_scene_entry === requestedMilestone.target_turn;
      records.push({
        requested_milestone: requestedMilestone,
        prior_scene_id: priorState?.scene_id ?? null,
        prior_turn_index: priorState?.turn_index ?? null,
        prior_turns_since_scene_entry: priorState?.turns_since_scene_entry ?? null,
        scene_id: state.scene_id,
        turn_index: state.turn_index,
        turns_since_scene_entry: state.turns_since_scene_entry,
        fired_pacing_event_ids: Array.isArray(state.fired_pacing_event_ids)
          ? [...state.fired_pacing_event_ids]
          : [],
        reached,
      });

      return {
        reached,
        scene_id: state.scene_id,
        turn_index: state.turn_index,
        turns_since_scene_entry: state.turns_since_scene_entry,
        requested_milestone: requestedMilestone,
      };
    },

    history() {
      return records.map((record) => ({
        ...record,
        requested_milestone: { ...record.requested_milestone },
        fired_pacing_event_ids: [...record.fired_pacing_event_ids],
      }));
    },
  };
}
