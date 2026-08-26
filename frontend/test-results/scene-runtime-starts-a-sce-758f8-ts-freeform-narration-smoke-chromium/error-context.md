# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: scene-runtime.spec.js >> starts a scene session and accepts freeform narration @smoke
- Location: e2e/scene-runtime.spec.js:16:1

# Error details

```
Error: expect(received).toBe(expected) // Object.is equality

Expected: true
Received: undefined
```

# Page snapshot

```yaml
- main [ref=e2]:
  - generic [ref=e3]:
    - paragraph [ref=e4]: Staging — non-production
    - paragraph [ref=e5]: Hosted Demo
    - heading "Freytag Forge" [level=1] [ref=e6]
    - paragraph [ref=e7]: Freeform roleplay with consequences that hold.
  - generic [ref=e8]:
    - generic [ref=e9]:
      - generic [ref=e10]:
        - heading "Story Feed" [level=2] [ref=e11]
        - paragraph [ref=e12]: narration service rejected the turn
      - button "New Session" [ref=e14] [cursor=pointer]
    - generic [ref=e15]:
      - generic [ref=e16]: The house is too quiet. Sarah's phone lies facedown on the kitchen floor beside an overturned chair, while her laptop and work bag are gone.
      - generic [ref=e17]: I look carefully at Sarah's phone.
      - generic [ref=e18]: narration service rejected the turn
    - generic [ref=e19]:
      - generic [ref=e20]: Your action
      - textbox "Your action" [active] [ref=e21]:
        - /placeholder: What do you do?
      - button "Send" [ref=e22] [cursor=pointer]
```

# Test source

```ts
  1   | import { expect, test } from "@playwright/test";
  2   | 
  3   | import { resolveWarningIfPresent, startSceneSession, submitTurn, writeCategoryReport } from "./helpers.js";
  4   | 
  5   | const spineActions = [
  6   |   "I search for concrete evidence of Sarah's disappearance and follow the strongest lead.",
  7   |   "I pursue the dead drop and ask Gabriel for the evidence needed to move forward.",
  8   |   "I prepare false identities and enter the facility without delaying the mission.",
  9   |   "I secure proof of JANUS and act on the current objective.",
  10  |   "I respond to the purge clock, reach Sarah, and preserve the rescue and evidence mission.",
  11  |   "I use the relay and broadcast the evidence before the network can recover.",
  12  |   "I finish the current objective and protect the route to the climax.",
  13  |   "I bring the story to a responsible resolution.",
  14  | ];
  15  | 
  16  | test("starts a scene session and accepts freeform narration @smoke", async ({ page }) => {
  17  |   await startSceneSession(page);
  18  |   const payload = await submitTurn(page, "I look carefully at Sarah's phone.");
  19  |   await writeCategoryReport("smoke", { state: payload.state, segments: payload.segments });
  20  |   await page.screenshot({ path: "../artifacts/e2e-smoke-loaded.png", fullPage: true });
> 21  |   expect(payload.segments?.some((segment) => segment.kind === "narration")).toBe(true);
      |                                                                             ^ Error: expect(received).toBe(expected) // Object.is equality
  22  |   await expect(page.locator(".entry-system")).toHaveCount(0);
  23  | });
  24  | 
  25  | test("drives the main spine and reports reachability and pressure @spine", async ({ page }) => {
  26  |   test.setTimeout(12 * 60_000);
  27  |   await startSceneSession(page);
  28  |   const turns = [];
  29  |   for (const action of spineActions) {
  30  |     const payload = await submitTurn(page, action);
  31  |     turns.push({ scene_id: payload.state?.scene_id, elapsed_seconds: payload.state?.story_elapsed_seconds });
  32  |     await resolveWarningIfPresent(page);
  33  |   }
  34  |   const sceneOrder = turns.map((turn) => turn.scene_id).filter(Boolean);
  35  |   await writeCategoryReport("spine", {
  36  |     ending_reachable: sceneOrder.at(-1) === "3C",
  37  |     dead_end: !sceneOrder.length,
  38  |     revelation_order: sceneOrder,
  39  |     pressure_trajectory: turns,
  40  |     distinct_paths_to_climax: [sceneOrder.join(">")],
  41  |   });
  42  |   expect(sceneOrder.every((scene) => /^[123][ABC]$/.test(scene))).toBe(true);
  43  | });
  44  | 
  45  | test("samples optional storylets without presenting a menu @storylets", async ({ page }) => {
  46  |   await startSceneSession(page);
  47  |   const prompts = [
  48  |     "I inspect the interrupted message, the room, and any detail that might deepen this situation.",
  49  |     "I follow an optional lead only if it remains relevant to the current scene.",
  50  |     "I return to the central objective after exploring the immediate complication.",
  51  |   ];
  52  |   const fired = new Set();
  53  |   for (const prompt of prompts) {
  54  |     const payload = await submitTurn(page, prompt);
  55  |     for (const id of payload.state?.fired_storylet_ids || []) fired.add(id);
  56  |     await resolveWarningIfPresent(page);
  57  |   }
  58  |   await writeCategoryReport("storylets", {
  59  |     fired_storylet_ids: [...fired],
  60  |     storylet_reuse: { unique: fired.size, repeated_ids: [] },
  61  |   });
  62  |   expect([...fired].every((id) => id.startsWith("SL-"))).toBe(true);
  63  | });
  64  | 
  65  | test("keeps NPC interaction and reveals bounded to the current scene @npc", async ({ page }) => {
  66  |   await startSceneSession(page);
  67  |   const prompts = [
  68  |     "I call Gabriel Dexter and ask what he knows about Sarah's disappearance.",
  69  |     "I review Sarah's message and ask only what the current evidence supports.",
  70  |   ];
  71  |   const narrations = [];
  72  |   for (const prompt of prompts) {
  73  |     const payload = await submitTurn(page, prompt);
  74  |     narrations.push(...(payload.segments || []).filter((segment) => segment.kind === "narration").map((segment) => segment.text));
  75  |     await resolveWarningIfPresent(page);
  76  |   }
  77  |   await writeCategoryReport("npc-knowledge", { narration: narrations, reveal_count: narrations.length });
  78  |   expect(narrations).not.toHaveLength(0);
  79  | });
  80  | 
  81  | test("preserves legal world-state changes across follow-up turns @world-state", async ({ page }) => {
  82  |   await startSceneSession(page);
  83  |   const pickup = await submitTurn(page, "I pick up Sarah's phone and keep it with me.");
  84  |   const followUp = await submitTurn(page, "I check that I still have Sarah's phone and use only what I carry.");
  85  |   await resolveWarningIfPresent(page);
  86  |   await writeCategoryReport("world-state", {
  87  |     pickup_state: pickup.state,
  88  |     follow_up_state: followUp.state,
  89  |     narration: followUp.segments,
  90  |   });
  91  |   expect(followUp.state?.scene_id).toBeTruthy();
  92  | });
  93  | 
  94  | test("handles aggressive and chaotic-but-legal policies without an accidental dead end @safety", async ({ page }) => {
  95  |   await startSceneSession(page);
  96  |   const prompts = [
  97  |     "I confront the obstacle firmly but do not harm an indispensable person or destroy a required item.",
  98  |     "I improvise a strange but lawful move that preserves every required route forward.",
  99  |   ];
  100 |   let blockedActions = 0;
  101 |   const states = [];
  102 |   for (const prompt of prompts) {
  103 |     const payload = await submitTurn(page, prompt);
  104 |     states.push(payload.state);
  105 |     if (await resolveWarningIfPresent(page)) blockedActions += 1;
  106 |   }
  107 |   await writeCategoryReport("safety", {
  108 |     blocked_action_rate: blockedActions / prompts.length,
  109 |     states,
  110 |   });
  111 |   expect(states.every((state) => state?.scene_id)).toBe(true);
  112 | });
  113 | 
```