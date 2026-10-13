# Engine-owned refusal: frozen measurement (2026-10-13, written before any run)

Design: `.plans/astra-refusal-path-forward-answer.md` (ChatGPT's 16 fresh commands; smaller experiment from my review). Code: commits 099e4e4a, 6c43c2a1.

Arms (identical settings, scene 1A start, one turn per script, 1 replicate): `fe2base` (`fixed_refusal` off) and `fe2eng` (`fixed_refusal` + `engine_refusal`). Variation files `bench/variations/astra-p4-refusal-fe2base.json`, `-fe2eng.json`. R = expected refusal, C = expected control success, M = mixed (reported, not scored against a bar).

| Script | Kind | Category | Command |
|---|---|---|---|
| g1 | R | Lift | Hoist the workstation overhead. |
| g2 | R | Lift | Lift the passenger seat briefly, then set it back. |
| g3 | R | Remove | Remove the back door from its frame. |
| g4 | R | Remove | Pull the drawer completely free of the workstation. |
| g5 | R | Destination | Carry the driver's seat into the kitchen. |
| g6 | R | Destination | Move the workstation beside the truck. |
| g7 | R | Push | Slide the workstation across the kitchen. |
| g8 | R | Push | Push the passenger seat out of the truck. |
| g9 | R | Two fixed | Carry the drawer and the passenger seat into the kitchen. |
| g10 | C | Fixed destination | Lay my laptop on the workstation. |
| g11 | C | Fixed destination | Put my laptop on the passenger seat. |
| g12 | C | Fixed source | Collect my laptop from the workstation. |
| g13 | C | Use in place | Slide the drawer closed. |
| g14 | C | Use in place | Pull the back door shut. |
| g15 | M | Mixed | Hoist the workstation, then open my laptop. |
| g16 | M | Mixed | Carry the drawer and my laptop into the truck. |

Bars (screening, not reliability): 9/9 honest refusals on R; 5/5 control successes on C; zero prohibited-success claims, false refusals or unintended mutations; zero narrator calls on refused turns (`narrator_called` false, no prompt); unanswered classifier turns counted as scheduled cases. The ChatGPT bar of 2/2 mixed clarifications is not testable: mixed handling and clarification are not built (a classifier yes refuses the whole command). Mixed turns are reported as observed; their follow-ups are deferred to a second experiment.

Before reading outcomes: inspect classifier payloads (target, source/destination role, full compound command); confirm refused turns have no narrator prompt and ordinary turns carry no refusal line. Scoring: every reply read blind from a shuffled sheet with arm labels removed. Separate target-resolution errors, classifier errors, routing failures and narrator contradictions.

Stop rule (my review, replacing ChatGPT's): classifier errors and engine-path failures are judged separately. If the path (no narrator call, no turn consumed, no mutation) holds but the yes/no classifier misses bars, the narrator is not the blocker and the classifier is the next work; if the path fails, stop refusal work for Phase 4. Passing earns the second experiment (mixed commands, cue deferral, save/load), not default adoption.
