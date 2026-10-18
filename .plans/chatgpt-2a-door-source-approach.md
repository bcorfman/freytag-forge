# 2A door-source follow-up: one remaining controlled screen

Updated after the source N=12 screen. This supersedes the previous recommendations.
**Drop both location and limits. Test deletion of the completion instruction
against a fresh control.** This is a diagnostic screen, not an established fix.
No code, package, recorded evidence or live configuration was changed here.

## What the 36 exits show

I read all 36 upstream narrations in
`bench/results/stage7-door-source-n12/results.json`, separately from the
appended bridge and entry, and their commands and downstream responses.
This is my manual inventory; the missing N=12 verdict files have not been
created. Row numbers mean `stage7-door-NN-<arm>`. Each row appears once per arm.

| Arm | Invented access object or clue | Rows | Count |
| --- | --- | --- | ---: |
| control | Panel behind maintenance console | 01, 02, 08, 09 | 4 |
| control | Panel behind ventilation grille | 10, 11 | 2 |
| control | Indentation pressed to reveal panel | 03 | 1 |
| control | Grille and seam suggesting panel | 05 | 1 |
| control | Wall seam described as hidden access panel | 12 | 1 |
| control | Suspicious ventilation grille, no confirmed panel | 04, 06 | 2 |
| control | Grille removed to reveal crawl space | 07 | 1 |
| location | Panel behind ventilation grille | 02, 05, 10 | 3 |
| location | Panel behind maintenance console | 03 | 1 |
| location | Panel behind maintenance cart | 07, 12 | 2 |
| location | Unmarked panel behind air vent | 11 | 1 |
| location | Grille and hidden panel with combination lock | 08 | 1 |
| location | Seam partly hidden by maintenance panel | 06 | 1 |
| location | Wall seam described as hidden access panel | 09 | 1 |
| location | Suspicious ventilation grille, no confirmed panel | 01, 04 | 2 |
| limits | Wall seam suggesting or appearing to be hidden panel | 01, 03, 04, 08, 09, 10, 11 | 7 |
| limits | Faint seam partly hidden by ventilation grille | 05, 07 | 2 |
| limits | Wall seam alone, no panel established | 06 | 1 |
| limits | Panel behind maintenance console | 02 | 1 |
| limits | Panel behind ventilation grille | 12 | 1 |

Every arm has **12/12 invented access objects or clues; 0/12 clean exits**.
That does not mean every row establishes a route, locked door or credential
requirement. Limits-06 only says:

> After a few moments, she finds a small, almost imperceptible seam in the wall.

That is a new search clue, not proof of a panel. The player nevertheless types
“press the hidden seam to open the concealed panel,” and 2B supplies one.
Location-01 suspects the grille “might be a hidden access point”; the player
spends both commands inspecting it. Uncertain language does not make an
unsupported actionable clue harmless.

The limits arm shifts toward seams (10/12 rows), but does not remove the
problem. Limits-01 leads to an invented data drive and a note naming
“Project Erebus - Level 3”; limits-04 leads to an invented researcher,
Dr. Rachel Kim. These are downstream inventions, not additional upstream
objects in the table. Location-08's combination lock becomes an “Eclipse-12”
code and then a login prompt. Counting only doors or credentials misses this.

| Arm | Earned by command 2 | Upstream invention/clue | Decision |
| --- | ---: | ---: | --- |
| fresh control | 7/12 | 12/12 | Baseline fails the bar |
| location | 5/12 | 12/12 | Drop |
| limits | 6/12 | 12/12 | Drop |

I retract the recommendation to restore console limits as the stronger fix
for this symptom. The missing material is real, but restoring it did not
prevent invention here. Do not combine these losing edits or promote their
proposed delivery-text extensions.

The results remain consistent with a search-to-discovery bias. They **do not
establish that “Finish each action the player gives.” causes it**: that rule
was unchanged in every arm. Model habits, the request, other instructions and
their interaction remain confounded. The evidence justifies testing the rule,
not assuming it is responsible. Nor does invention alone determine reveal
success: some players ignore the invented clue and earn evidence anyway.

## One ranked next screen: delete the completion rule

Production source, only if later adoption is justified:
`storygame/runtime/cloudflare.py`,
`CloudflareTurnProvider._turn_rules_before_grounding`.

```text
OLD: Finish each action the player gives.
NEW: [delete this complete instruction; no replacement]
```

For this screen, delete exactly `Finish each action the player gives.\n`
once from the recorded **system** string. The production list entry is:

```text
            "Finish each action the player gives.",
```

Do not edit production source to run this screen: that would also change the
2B provider and confound the upstream comparison.

**Evidence:** searches repeatedly end in newly found clues; control-03 even
presses an indentation, and control-07 removes a grille, although the command
only asked to look. The instruction might turn completion of a search into
successful discovery. Deleting it tests that possibility without supplying
new facts. Existing instructions still require a response, limit action to
the player's command, and prohibit invented objects.

**Proven technique:** exact recorded-prompt ablation of competing text, the
scene-fixing guide's removal technique used for 3A's captives talk line and
2C's stale 1A recall. Those precedents support the method, not this specific
rule deletion. No earlier scene proves that deleting this instruction wins.
The deletion is story-neutral: the instruction contains no character, place,
object or plot reference. It changes narrator wording, not runtime mechanics,
guards, matching, or allowed player language.

**Risk:** legitimate searches or moves may stop at attempts; multi-action
requests may remain unfinished. Invention may persist because this rule is
not its driver. A shorter or vaguer answer is not automatically better. Review
whether the search is answered meaningfully and verify ordinary completed
actions before adoption.

I recommend no second knowledge-line edit and no new search-specific rule in
this round. A replacement rule would test removal and addition together. If
deletion loses, drop it rather than treating different clue vocabulary as a win.

The 2B responses expose separate issues: location-03 and limits-09 say no
matching file was found immediately before the appended JANUS delivery;
terminal ambiguity and guard rejection also occur. Record them for their own
diagnosis if they become the next target. They do not justify widening
`action_evidence`, weakening guards, declaring invented objects, or granting
unearned evidence. Another cue rewrite is not supported after its prior losses.

## Additions to the existing experiment configuration

Add `--experiment completion`; preserve `door` and `source` for reproducibility.

| Arm | Package variation | Recorded system | Recorded user |
| --- | --- | --- | --- |
| control | `stage7-door-control.json` | Unchanged | Unchanged |
| no-finish | Same control variation | Delete exact instruction above | Unchanged |

Both arms replay original replicate 1, scene 2A, turn 7. Preserve the command,
bridge, entry, raw player and real two-command 2B continuation, with semantic
fallback disabled. No fixed-output arm or new story variation is needed.
Both downstream providers retain the shipped rule. This isolates an upstream
effect, not the consequences of deleting the rule globally.

Only these harness additions are needed:

1. In `scripts/ringer/stage7/door_prompt.py`, add the completion arms and an
   exact system-replacement specification. `patch_prompt` currently edits user
   sections and returns `selection.system` unchanged. Add a system-only path,
   require exactly one occurrence, preserve all other bytes, and record
   original/patched system hashes and a system diff. Preserve the unchanged
   user hash/diff. Scope the existing perimeter/corridor assertions to
   `source`, not every non-`door` experiment.
2. In `scripts/ringer/stage7/door_probe.py`, add the experiment, both mappings
   to the control variation, and caps below. Reuse generated-arm scheduling
   and transport. Do not alter `_continue` or the installed narrator rule.
3. Extend `check_door_probe.py` to validate the system-only diff and unchanged
   user/bridge/entry for this experiment. Reuse verdict and summary checks.
   Add corresponding dry, smoke, review and N=12 Ringer manifests. No new
   transport, matcher or player machinery is required.

| Run | Rows | Raw 2A request cap | Total Cloudflare cap | Raw-player cap |
| --- | ---: | ---: | ---: | ---: |
| Smoke, N=1 | 2 | 2 | 10 | 4 |
| Full, N=12 | 24 | 24 | 120 | 48 |

Each row allows one upstream request and up to two downstream turns with two
narration requests each. Preserve failures and spend accounting. Do not
replace samples, silently rerun, or pool smoke with N=12.

**Review order:** dry integrity check → smoke → review both smoke rows → N=12
→ review all 24 rows, even if reveal counts already fail. The source screen
could rule out adoption without object review, but that omission left the
causal question unanswered. Do not repeat it in this diagnostic screen.

Write one hash-bound verdict per row with exact quotes and separate judgments
for upstream invention, downstream invention, player pursuit, premature
disclosure and contradictory delivery. Count suspicious seams and hinted
routes when they are unsupported actionable clues; do not require a confirmed
panel or lock. Distinguish suspicion from an established object. Review meaning
against the supplied material, never keyword/regex gates. Count the union of
unsupported access invention or pursuit once per row from the verdict files.
Record broader invented evidence separately so a note cannot replace a door
and pass unnoticed.

**Win:** at least 10/12 rows earn an eligible reveal by command 2; at most
2/12 contain unsupported access invention or pursuit; no premature disclosure,
contradictory delivery or weakened guard; and clear improvement over the new
contemporaneous control. Report per-arm counts and deltas. A one-row advantage
is inconclusive. Earned means an eligible match actually committed, not merely
plausible prose. Lower invention alone is diagnostic benefit, not a winning
fix under this bar.

If the screen passes, test the actual shared-rule deletion across the paths
in `docs/narrator-writing-guide.md`: turn rules, opening, system/section
prompts, scene setting and malformed-response recovery. The current rule is
in the shared helper used by `_turn_rules` and `_constant_turn_rules`; inspect
resulting payloads rather than assuming replay success proves path coverage.
Run three live scene replicates and targeted regressions for ordinary searches,
movement, handovers and multi-action commands before adoption, following the
existing runbook and staging workflow. Budget those later runs separately.

## New limits and corrections

- This document supplies manual upstream counts. The historical N=12 directory
  still lacks 36 full verdict files. Do not represent this table as a completed
  hash-bound disclosure/guard audit.
- Limits often invents a clue to a possible object rather than the object
  itself. Counting only confirmed routes would overstate progress.
- Both source edits lose this screen; small reveal differences do not prove a
  population-level ranking or that those lines never matter.
- The prior limits variation required YAML quoting because of the colon.
  That was an error in my supplied text, not a reason to discount the correctly
  quoted experiment that ran.
- The upstream-only ablation cannot establish the safety or effect of global
  deletion. The unchanged downstream narrator may invent independently.
- Earlier limits remain: one recorded prompt, one scene, temperature zero,
  correlated outputs, bare-state continuation, missing hosted pre-turn facts
  and bounded player history. No causal winner or hosted fix is established.

Only this recommendation document was regenerated. No live calls were made.
