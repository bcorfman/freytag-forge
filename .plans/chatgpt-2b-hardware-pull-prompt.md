# ChatGPT prompt: stop the 2B player chasing invented hardware instead of the archive terminals

Paste everything below the line into the ChatGPT Desktop thread used for the 2A/2B
door work. It has the repository. Bring the answer back to Claude Code, which
applies any story change through a Ringer task, re-runs the free payload diff and
tests, and proposes the next screen. Nothing here is billed until Brandon says go.

---

Brandon's acceptance bar for a scene (2026-10-18): a player may chase things in a
scene, but **at least 80% of runs must leave the scene by an earned transition,
not a timer handoff.** Only inventions that stop the story progressing matter.

## What the new screen found

`bench/results/stage7-transition-n12/` (gitignored; numbers below are from
`results.json`) ran 12 full scene-2B continuations per arm with a raw player (it
sees only the transcript), capped at 20 commands. The 2B timer handoff fires at
turn 15. Earned exits: **control 7/12, grounded 9/12**. Grounded is one row short
of the 10/12 keep rule; control (the pre-panel package) is worse. So the problem
is not the panel work. It is common to both arms.

Every one of the 8 timer exits is a row whose player never earned
`k_sl_2b_a_r1` (control 5 rows, grounded 3). The reveals need the player to
search or read the archive and name Michelle, her selection file(s), or Brandon's
development records (`knowledge.yaml`, `action_evidence`).

The telling number is the **first command**: 22 of 24 first commands go after
hardware that the generated 2A narration invented ("hidden panel", "seam",
"ventilation grille", "maintenance console"). All 8 stalled rows began that way.
Only 2 rows began at the terminals, and both earned. Of the 22 hardware-first
rows, 14 still earned and 8 stalled.

Stalled players then spend 4 to 10 commands on hardware the 2B narrator keeps
elaborating, and when they finally reach the terminals they search for a door
code, not for Michelle. Example (grounded rep 5, first three commands and the
narrator's answers):

1. "Examine the hidden panel closely, then try to open it." The 2B narration finds
   "a small indentation ... a hidden catch" and appends the authored cue line
   "Selection files fill the archive terminals. Government and financial records
   sit open beside them."
2. "Press the small indentation to release the hidden panel, then open it." The
   narration: "a hidden panel slides open ... wires and circuit boards, with a
   small keypad and a screen displaying cryptic error messages."
3. "Examine the keypad and screen, and read the cryptic error messages." The
   narration invents "Unauthorized access detected. System lockdown imminent."

Other stalled rows chase a maintenance console, a junction box, a keycard reader,
or an invented username and password. The 2A screen goal is the same in stalled
and earned rows ("a concealed route or access panel leading to the detention
area" is in 24 of 24), so the goal alone does not decide who stalls. What decides
it is whether the first command and the next two stay on hardware.

## What has already been tried (do not repeat, and do not recommend again)

- 2B cue wording (current, B, C): hits 0/12, 0/12, 2/12; the cue was visible every
  time. Weak lever (`.plans/implementation_plan.md`, "2B CUE PROBE").
- 2A turn-7 prompt wording (review, stale-scene, wording arms) and the source
  screen (location, limits): none beat the generated control; every generated arm
  invented the door or panel. Dropped.
- The panel work (declared `cooling_service_archive_panel`, route-neutral bridge,
  slotted face, "opens with a push"): lowers nothing for this failure; control with
  no panel facts stalls the same way.
- A literal instruction in the 2B entry to start with Michelle's selection files and
  then check Brandon's development records: rejected, it names a protected reveal
  target and reads as an order.

## Hard constraints

- The engine's "Do you mean the archive terminals or the medical terminal?"
  clarification for ambiguous nouns is intended behavior. Do not touch it.
- No regex or keyword gates, no matcher changes, no new narrator rule unless
  material fixes cannot work (and then say why). Subtractive fixes first.
- No text that discloses a reveal (JANUS contents, Brandon's role, Michelle's
  status) before the player earns it; no instruction to the player; no
  "not X" or "no X" sentences (they prime contrast; see the earlier panel
  sentence round).
- Anything a narrator or match call may mention about places or things follows
  `docs/world-model-grounding.md`; narrator wording follows
  `docs/narrator-writing-guide.md`; 12th grade, one idea per sentence.
- The runtime stays story-agnostic; the fix lives in story material
  (`plot.md`, `world.yaml`, `knowledge.yaml` text) at the 2B side. The 2A exit text is
  generated and cannot be edited directly.

## What I need

Read `docs/narrator-writing-guide.md`, `docs/world-model-grounding.md`,
`docs/scene-fixing-guide.md`, the 2B block of `data/stories/continuity-initiative/plot.md`,
and the 2B reveals in `knowledge.yaml`. Then weigh these hypotheses (do not assume any
is right) and say which the evidence supports:

1. **Nothing declared to chase.** The 2B narrator invents a console, keypad or
   screen for a command about a thing the world model does not contain, so each hardware
   command gets fresh hardware. A declared, finished version of the thing the player
   goes after might end the chase in one turn.
2. **The last thing read is vivid hardware.** The screen the player reads ends with
   2A's hardware paragraph, then the bridge, then the 2B entry. The entry names the
   terminals in its second sentence, but 22 of 24 players still go for the hardware.
3. **"Finish each action the player gives" turns a chase into a scene.** The plan's
   remaining untested lead; it makes the narrator complete and elaborate any chase.
4. **The appended cue arrives too late or too quietly.** It lands after the hardware
   paragraph on command 1 and reads as scenery.
5. **Something else you find in the 2B material.**

Give exact old/new text for the smallest change at the 2B side, in this order of
preference: (1) subtract or merge material that gives the narrator something to
elaborate; (2) reword surviving 2B material (entry, bridge, setting facts, item
descriptions) so a hardware command resolves briefly and the terminals stay the
obvious next place; (3) only if both fail, one story-neutral narrator rule, with the
reason no material fix is enough.

For each proposal state: which lines in which files you touch; what each could break
(the normal 2B exit, `t_2b_2c`, the cue and nudge staging, the affordance map, the
control package's frozen text); what you could not establish; and the measurement
that would show it works, which should be the same N=12 transition screen with the
keep rule "earned exits at least 10/12 in the changed arm". Say plainly if you think
no 2B-side material change will move this and the fix belongs in 2A or in the
semantic fallback instead.
