const elapsedField = ["story", "elapsed", "seconds"].join("_");
const sceneField = ["scene", "id"].join("_");
const eventField = ["event", "id"].join("_");
const firedEventsField = ["fired", "pacing", "event", "ids"].join("_");

const MAX_DELTA_SECONDS = 3600;

function readElapsed(state, description) {
  if (
    state === null ||
    typeof state !== "object" ||
    Array.isArray(state) ||
    !Number.isInteger(state[elapsedField]) ||
    state[elapsedField] < 0
  ) {
    throw new Error(
      `${description}: missing or malformed elapsed time; expected a non-negative integer story elapsed value.`,
    );
  }
  return state[elapsedField];
}

function milestoneIdentity(milestone) {
  const scene = milestone[sceneField];
  const event = milestone[eventField];
  const eventDescription = event === undefined ? "" : `, event ${String(event)}`;
  return `scene ${String(scene)}${eventDescription}`;
}

function validateMilestone(milestone) {
  if (
    milestone === null ||
    typeof milestone !== "object" ||
    Array.isArray(milestone) ||
    (milestone.kind !== "scene_point" && milestone.kind !== "pacing_event") ||
    typeof milestone[sceneField] !== "string" ||
    !Number.isInteger(milestone.target_seconds) ||
    milestone.target_seconds < 0 ||
    (milestone.kind === "pacing_event" && typeof milestone[eventField] !== "string")
  ) {
    throw new Error("Cannot arm milestone: malformed milestone target or identity.");
  }
}

export function createPackageClockController() {
  let lastObservedElapsedSeconds = null;
  let armedMilestone = null;
  let sentDeltaSeconds = null;
  const records = [];

  return {
    observeState(state) {
      lastObservedElapsedSeconds = readElapsed(state, "Cannot observe state");
      sentDeltaSeconds = null;
    },

    arm(milestone) {
      validateMilestone(milestone);
      if (armedMilestone !== null) {
        throw new Error(
          `Cannot arm milestone ${milestoneIdentity(milestone)}: another milestone is already armed.`,
        );
      }
      armedMilestone = milestone;
      sentDeltaSeconds = null;
    },

    armed() {
      return armedMilestone;
    },

    deltaForRequest() {
      if (lastObservedElapsedSeconds === null) {
        throw new Error(
          "Cannot compute clock delta: no elapsed session state has been observed.",
        );
      }
      if (armedMilestone === null) {
        throw new Error("Cannot compute clock delta: no milestone is armed.");
      }

      const targetSeconds = armedMilestone.target_seconds;
      const deltaSeconds = targetSeconds - lastObservedElapsedSeconds;
      if (deltaSeconds < 0) {
        throw new Error(
          `Cannot compute clock delta for ${milestoneIdentity(armedMilestone)}: observed elapsed ${lastObservedElapsedSeconds} is later than requested target_seconds ${targetSeconds}.`,
        );
      }
      if (deltaSeconds > MAX_DELTA_SECONDS) {
        throw new Error(
          `Cannot compute clock delta for ${milestoneIdentity(armedMilestone)}: requested delta ${deltaSeconds} exceeds the 3600-second limit.`,
        );
      }

      sentDeltaSeconds = deltaSeconds;
      return deltaSeconds;
    },

    observeTurnResponse(payload) {
      if (payload === null || typeof payload !== "object" || Array.isArray(payload)) {
        throw new Error(
          "Cannot observe turn response: missing or malformed elapsed state.",
        );
      }
      const state = payload.state;
      const returnedElapsedSeconds = readElapsed(
        state,
        "Cannot observe turn response",
      );
      const priorElapsedSeconds = lastObservedElapsedSeconds;
      lastObservedElapsedSeconds = returnedElapsedSeconds;

      if (armedMilestone === null) {
        sentDeltaSeconds = null;
        return {
          reached: false,
          elapsed_seconds: returnedElapsedSeconds,
          requested_milestone: null,
        };
      }

      const requestedMilestone = armedMilestone;
      armedMilestone = null;
      const reached =
        state.pending_game_break !== true &&
        returnedElapsedSeconds === requestedMilestone.target_seconds;
      records.push({
        requested_milestone: requestedMilestone,
        prior_elapsed_seconds: priorElapsedSeconds,
        sent_delta_seconds: sentDeltaSeconds,
        returned_elapsed_seconds: returnedElapsedSeconds,
        [sceneField]: state[sceneField] ?? null,
        [firedEventsField]: Array.isArray(state[firedEventsField])
          ? [...state[firedEventsField]]
          : [],
        reached,
      });
      sentDeltaSeconds = null;

      return {
        reached,
        elapsed_seconds: returnedElapsedSeconds,
        requested_milestone: requestedMilestone,
      };
    },

    history() {
      return records.map((record) => ({
        ...record,
        requested_milestone: { ...record.requested_milestone },
        [firedEventsField]: [...record[firedEventsField]],
      }));
    },
  };
}

export function assertExclusiveClockMode(environment) {
  const packageClock = environment?.E2E_PACKAGE_CLOCK;
  const scalarClock = environment?.E2E_TEST_CLOCK_SECONDS;
  const packageClockSet = packageClock !== undefined && packageClock !== null && String(packageClock).length > 0;
  const scalarClockSet = scalarClock !== undefined && scalarClock !== null && String(scalarClock).length > 0;
  if (packageClockSet && scalarClockSet) {
    throw new Error(
      "E2E_PACKAGE_CLOCK and E2E_TEST_CLOCK_SECONDS are mutually exclusive clock modes; set only one.",
    );
  }
}
