# Prompt for ChatGPT Desktop: two scene-exit contradictions in "The Continuity Initiative"

Paste everything below the line into a fresh ChatGPT Desktop chat. It is self-contained.

---

You are helping fix two places where an interactive story's own authored files disagree about whether a player can leave a scene by earning it. You cannot see the repository, so everything you need is here. Please answer with a recommendation and the exact text to insert; do not rewrite anything beyond what is asked.

## How the story engine works (only what matters here)

- The story is a set of scenes. Each scene has **storylets**: optional or required story moments. A storylet has **realizations**: alternative ways it can play out. **A storylet fires exactly once, and exactly one of its realizations plays.** Once one has played, the others of that storylet can never play.
- Each realization asserts **facts** (for example `national_detention_network_known`). Facts are the only mutable truth.
- A scene has a **bridge event** with an activation rule. The rule lists facts that must be true before the scene's exit fact is produced, and that exit fact is what lets the player leave the scene by their own play (an "earned" exit). The rule has two parts: `all_facts_true` (every one required) and optionally `any_of` with `at_least: N` (at least N of the listed facts).
- If the player never earns the exit fact, the engine eventually forces the player out of the scene at a deadline turn using authored fallback text. That is a worse experience: the player waited, then the story moved on without their play mattering. We call it a forced exit.
- Each realization also carries `helps_transition_triggers` (which scene exit it is meant to help) and each storylet carries `completion_or_abort.complete_when` (when the storylet counts as finished).
- A "protected knowledge boundary" is a list of later secrets a realization must not reveal early. Keep every boundary listed below intact.

## The problem

A scripted full-game test plays one journey per realization. Two realizations are declared as valid, completing, exit-helping alternatives, yet if the player takes them the scene exit can never be earned. The bridge rule and the realization disagree.

### Issue N-1: Scene 1C, storylet SL-1C-C, realization SL-1C-C-R2

Plot beats in plot.md (Scene 1C, "Discovery of the Facility"):

> **1C.3 The Nationwide Network.** Brandon accesses a logistics computer and discovers that the Los Angeles site is not where all the missing people are held. It is a regional command center connected to facilities throughout the country. The missing have been divided into categories ... The conspiracy did not simply remove random citizens. It removed people who might either help control the country or resist that control.
>
> **1C.4 The Architects Revealed.** A recorded conference shows Charles and Rebecca Jenkins discussing the next phase of the Continuity Initiative. Charles intends to announce that the federal government has collapsed and establish a new emergency authority. Rebecca warns him that several facilities are overcrowded and that prisoners are beginning to resist. Charles responds that the public will accept any government that promises to restore the missing. Kristin now understands the central strategy: the conspirators created the catastrophe so they could later present themselves as the only people capable of ending it.

The scene's exit text (bridge_text) says: "The observation shaft showed them living captives in an active regional command center, but the main facility could not be reached from the service level without triggering security. Kristin and Brandon withdrew to prepare a way inside."

storylets.md says of this storylet: "Deliver the scene's scale reversal in stages: regional facility -> national network -> deliberate political strategy. Allow the player to absorb operational and ideological evidence separately." Its effects list: "May set `national_detention_network_known`. May reveal the selection categories. May set `architects_strategy_known`. May establish `facility_infiltration_needed` once Kristin understands that observation or a direct local rescue is insufficient."

Current storylet-routes.yaml for SL-1C-C (activation requires `facility_proof` and `captives_confirmed_alive`; pacing earliest 0, target 9, latest 10):

```yaml
realization_options:
- id: SL-1C-C-R1
  dramatic_intent: Read logistics categories and understand that the Los Angeles site is part of a national detention network.
  source_beats: [scene-1c3--the-nationwide-network]
  operations:
  - {op: assert, fact_id: national_detention_network_known, value: true}
  helps_transition_triggers: [t_1c_2a]
- id: SL-1C-C-R2
  dramatic_intent: Understand Charles and Rebecca's reconstruction strategy and conclude that exposing and disrupting the operation requires deeper access than a local rescue attempt can provide.
  source_beats: [scene-1c4--the-architects-revealed]
  operations:
  - {op: assert, fact_id: architects_strategy_known, value: true}
  helps_transition_triggers: [t_1c_2a]
completion_or_abort:
  complete_when:
  - any_fact_true: [national_detention_network_known, architects_strategy_known]
```

Knowledge items shown to the player (delivery_text):
- R1: "The logistics computer shows Kristin that Los Angeles is one regional hub. The detention network spans the country."
- R2: "A recording shows that Charles and Rebecca made the crisis. They plan to rule as its promised solution."

The bridge that produces the exit fact:

```yaml
- id: bridge_1c_infiltration_needed
  activation:
    all_facts_true: [facility_proof, captives_confirmed_alive, national_detention_network_known]
  produces: [{op: assert, fact_id: facility_infiltration_needed, value: true}]
  realization_storylets: [SL-1C-A, SL-1C-B, SL-1C-C]
```

The 1C-to-2A exit requires `facility_infiltration_needed`. **Contradiction:** SL-1C-C says R2 alone completes the storylet and helps the exit, and R2's own intent says it makes deeper access necessary, but the bridge demands `national_detention_network_known`, which only R1 sets. If the player plays R2 first, R1 can never play, the exit is never earned, and the engine forces them out at the deadline. Nothing later in the story reads `architects_strategy_known` or `national_detention_network_known`.

Protected-knowledge boundaries for both realizations: `janus_selection_system`, `brandon_history`, `janus_phase_two`.

### Issue N-2: Scene 2B, storylet SL-2B-B, realization SL-2B-B-R3

Plot beats (Scene 2B, "Evidence and Betrayal"):

> **2B.2 Kristin Was Bait.** ... Charles expected Kristin to seek Brandon. Security allowed portions of Michelle's evidence to remain accessible so Kristin would expose Brandon's hidden network. Kristin realizes that every step she has taken may have been anticipated.
>
> **2B.3 Brandon's Role.** Kristin finds Brandon's name in the original JANUS development records. Brandon admits that he helped write the AI software used to identify people at risk during national emergencies. When he discovered that Charles intended to use it for mass detention and political control, he attempted to destroy the project. He failed and fled. ... Kristin feels betrayed. She suspects Brandon may still be manipulating her ...

storylets.md for SL-2B-B: effects "May set `brandon_janus_role_known`. May set `brandon_claimed_reform_motive`. May set `kristin_was_bait`. May set `janus_evidence` ..." and completion "Brandon's original role and claimed break with Charles are explicit between him and Kristin, **or** Kristin learns Charles used her to expose Brandon's hidden network."

Current storylet-routes.yaml for SL-2B-B (activation requires `janus_evidence`; pacing earliest 0, target 6, latest 7):

```yaml
- id: SL-2B-B-R1   # source beat 2b3
  operations: [assert brandon_janus_role_known, assert brandon_claimed_reform_motive]
  helps_transition_triggers: [t_2b_2c]
- id: SL-2B-B-R2   # source beat 2b3, delayed confrontation
  operations: [assert brandon_janus_role_known, assert brandon_claimed_reform_motive]
  helps_transition_triggers: [t_2b_2c]
- id: SL-2B-B-R3   # source beat 2b2
  dramatic_intent: Reveal that Charles expected Kristin to seek Brandon and left Michelle's evidence accessible to expose Brandon's hidden network.
  operations: [assert kristin_was_bait]
  helps_transition_triggers: [t_2b_2c]
completion_or_abort:
  complete_when:
  - any_fact_true: [brandon_janus_role_known, kristin_was_bait]
```

R3 player-facing text: "Charles expected Kristin to seek Brandon. He left Michelle's evidence where she could find it and expose Brandon's hidden network. Corrupted files flicker on the medical terminal."

The bridge that produces the exit fact (2B-to-2C exit requires `archive_crisis_understood`):

```yaml
- id: bridge_2b_archive_crisis
  activation:
    all_facts_true: [janus_evidence]
    any_of: [brandon_janus_role_known, brandon_claimed_reform_motive, michelle_resistance_known]
    at_least: 2
  produces: [{op: assert, fact_id: archive_crisis_understood, value: true}]
  realization_storylets: [SL-2B-A, SL-2B-B, SL-2B-C]
```

The other 2B storylet SL-2B-C (Michelle's hidden resistance) supplies only `michelle_resistance_known`. **Contradiction:** SL-2B-B says R3 alone completes the storylet and helps the exit, but if R3 plays, R1/R2 can never play, so at most one of the three `any_of` facts (`michelle_resistance_known`) is ever true, `at_least: 2` is unreachable, and the exit is forced at the deadline. Nothing later in the story reads `kristin_was_bait`. `brandon_janus_role_known` and `brandon_claimed_reform_motive` are read only by this bridge and by deadline fallbacks; Brandon's JANUS role is disclosed again in Scene 3B.4, where "Brandon transmits a confession describing his role in creating JANUS. His statement authenticates Michelle's ..." (plot.md).

Protected-knowledge boundary for all three realizations: `janus_phase_two`.

## What I need from you

For **each** issue, choose one option, justify it against the plot in a few sentences, and give the exact edits. Options (add a better one if you see it):

- **A. Make the bridge accept the alternative.** For N-1 that is `all_facts_true: [facility_proof, captives_confirmed_alive]` plus `any_of: [national_detention_network_known, architects_strategy_known]` with `at_least: 1`. For N-2 that is adding `kristin_was_bait` to the existing `any_of` list with `at_least` unchanged at 2. Smallest change; the declared completion and `helps_transition_triggers` already treat the alternative as sufficient.
- **B. Make the alternative establish the missing fact too.** For example, R2 of 1C-C also conveys that the site is part of a national network and sets `national_detention_network_known`; or R3 of 2B-B also has Brandon admit his role. This changes player-facing text, so give the new `delivery_text`, `statement` and `must_convey` wording.
- **C. Split the staged beats into separate storylets** so both can play (1C.3 then 1C.4; 2B.2 then 2B.3). The plot treats them as sequential beats, but this adds storylets, windows, ids and a larger change.

Constraints:
1. Story meaning changes start in plot.md. If your choice changes what the player learns or when, give the plot.md edit first (exact old and new paragraph), then the matching edits to storylets.md, storylet-routes.yaml, knowledge.yaml and, only if a deadline fallback text or cue changes, handoffs.yaml. Name each file and the exact key.
2. Do not reveal anything in the protected-knowledge boundaries lists above earlier than the plot allows.
3. Keep the voice and length of the existing delivery texts (two to three short sentences, plain words, second-hand details only).
4. If you pick Option A, say so plainly and confirm that no plot.md change is needed, and name the one thing in the plot that supports the player leaving the scene on that evidence alone.
5. Say which option you would not choose and why, in one line each.

Finish with a short self-check: for each issue, list the facts the player can have when the exit fires under every legal combination of that scene's storylets, and confirm the exit fires in all of them.
