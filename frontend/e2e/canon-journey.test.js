import assert from "node:assert/strict";
import test from "node:test";

import * as journey from "./canon-journey.js";

const expectedOneA = [
  "Search the kitchen and the back door for concrete signs of what happened here - the overturned chair, the forced lock, her phone left on the floor.",
  "Search under the drawer in her workstation.",
  "Read the remaining research fragments on Michelle's memory card.",
  "Read the files on Michelle's memory card.",
  "Play the damaged recording on Michelle's memory card.",
  "Hide what you found from the official asking questions about Michelle's work, then watch what they do at the gate as they leave.",
];

test("keeps the canon journey scene prompts available and scene-aware", () => {
  assert.deepEqual(journey.scenePrompts["1A"], expectedOneA);
  assert.equal(journey.promptFor("1A", expectedOneA.length), expectedOneA[0]);
  assert.ok(journey.scenePrompts["1A"].some((prompt) => prompt.includes("Read") && prompt.includes("memory card")));
  for (const sceneId of ["1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"]) {
    assert.ok(journey.scenePrompts[sceneId]?.length, `${sceneId} needs at least one prompt`);
  }
  assert.equal("spineJourney" in journey, false);
});
