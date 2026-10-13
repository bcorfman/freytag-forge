# Engine-owned refusal, tuning round (2026-10-13, written before any tuning or run)

Why: the mixed-command run missed two bars (3 of 4 twice) on classifier misses: `names_other_action` said no to "Carry the driver's seat and my laptop into the kitchen." (one verb, two objects) and `relocates_thing` said no to "Tilt the workstation onto its side." (a repositioning verb). Frozen stop rule: tune each question once, re-measure on fresh commands.

Tuning (one pass, one Ringer task, no further rounds): `relocates_thing` gets the repositioning verbs (tilt, tip, rotate, turn around, roll, nudge, shift, reposition) in its list, and a false-side note that a hinged or sliding part used as designed (a door swung open or shut, a drawer slid open or shut) is use, not relocation. `names_other_action` gets a note that a second object joined by "and" counts even when one verb covers both. The task spec does not contain any command below.

Arm `fe4eng` (`fixed_refusal` + `engine_refusal`), scene 1A, 1 reply per command. Same bars as the mixed freeze. M = mixed or shared-verb (refusal plus the clarification sentence), S = simple refusal without it, C = control (success, no refusal; k9, k10 and k12 use fixed things in place, to catch over-refusal from the widened verbs).

| Script | Kind | Command |
|---|---|---|
| k1 | M | Drag the workstation and my laptop into the kitchen. |
| k2 | M | Lift the passenger seat and the back door, then open my laptop. |
| k3 | M | Push the driver's seat and my laptop out of the truck. |
| k4 | M | Rotate the workstation, then open my laptop. |
| k5 | S | Turn the workstation around. |
| k6 | S | Reposition the passenger seat. |
| k7 | S | Roll the workstation toward the window. |
| k8 | S | Nudge the back door a foot to the left. |
| k9 | C | Swing the back door open. |
| k10 | C | Press on the drawer to check that it is closed. |
| k11 | C | Tilt my laptop screen back. |
| k12 | C | Slide the drawer open, then close the drawer. |

Bars: M 4 of 4 refused with the clarification; S 4 of 4 refused without it; C 4 of 4 succeed with no refusal; 0 narrator calls and no prompt on refused turns; no unanswered question. Existing unit tests must pass.
Stop rule: this is the last tuning pass. If a bar is missed, the yes/no classifier route does not reach the bar with wording alone; record it, keep the path opt-in, and stop refusal work for Phase 4.
