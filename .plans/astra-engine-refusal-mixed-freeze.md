# Engine-owned refusal, second experiment: honest mixed-command refusal (2026-10-13, written before any code or run)

Why: the first experiment (plan, "engine-owned refusal: result") refused mixed commands whole and silently lost the harmless part. Splitting compound commands was judged too brittle (Brandon, 2026-10-13), so no splitter change.

Candidate: keep the whole-command refusal, and when the command also asks for something besides the refused relocation, append one fixed sentence: "Nothing else in that command was done. Say what you want to do next." A new yes/no classifier question `names_other_action` (asked once per refused turn, with the refused things' names joined) decides it. Yes or unanswered appends the sentence (it is always true that nothing else happened); no leaves the refusal alone. Nothing is executed partially; no narrator call; no turn consumed.

Arm: `fe3eng` only (`fixed_refusal` + `engine_refusal`), 1 reply per command, scene 1A start. Baseline was measured in the first experiment. M = mixed (expect refusal plus clarification), S = simple refusal (expect refusal, no clarification), C = control (expect success, no refusal).

| Script | Kind | Command |
|---|---|---|
| h1 | M | Drag the workstation toward the door, then check my laptop. |
| h2 | M | Heave the passenger seat out of the truck and open my laptop. |
| h3 | M | Carry the driver's seat and my laptop into the kitchen. |
| h4 | M | Hoist the back door off its hinges, then open my laptop. |
| h5 | S | Tilt the workstation onto its side. |
| h6 | S | Wrench the drawer out of the workstation. |
| h7 | S | Haul the driver's seat out of the truck. |
| h8 | S | Shove the back door off its frame. |
| h9 | C | Retrieve my laptop from the passenger seat. |
| h10 | C | Close the back door. |
| h11 | C | Look at the drawer. |
| h12 | C | Put my laptop on the workstation, then open my laptop. |

Bars (screening): M 4 of 4 refused with the clarification sentence; S 4 of 4 refused without it; C 4 of 4 succeed with no refusal (h9 repeats the earlier false-positive pattern); zero narrator calls and no prompt on refused turns; no unanswered classifier question.
Deterministic unit tests (no billed call): save then load after a refused turn gives identical state; a pending cue is delivered once on the next accepted turn; unanswered `names_other_action` appends the sentence.
Stop rule: classifier errors and engine-path failures are judged separately. If the engine path holds and only `names_other_action` misses, tune that question once on the same bars with fresh commands, not these. Passing still does not adopt the path as default: it needs another story package and multi-turn play first.
