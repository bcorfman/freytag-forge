# Brief for ChatGPT Desktop: a wrong premise in your last two answers, and what to revise

You are advising on freytag-forge, an interactive-fiction engine with one shipped story ("The Continuity Initiative", nine scenes: 1A 1B 1C 2A 2B 2C 3A 3B 3C). You already have the earlier brief (`chatgpt-recurring-problems-prompt.md`) and gave two answers: a ranked list that put "repair promised actions with separate storylets" first, and a wider proposal (an enforceable contract between the world model, reveals and cues). **Both rested on a premise the story's author says is wrong.** Read this whole brief, then revise. Do not defend the earlier answers; say plainly which parts you withdraw, which survive, and why. Every claim must tie to the evidence below.

## The correction, in the author's words

Brandon (the author, who is also the owner of the repo) wrote:

> The whole point of storylets was to increase the story pressure if the user was taking too long to move onto the next scene. They were intended to reveal more information and/or create tension at the same time. Regardless, they were never meant to be blocking ... the idea was that eventually the timer would end a scene with an explanation and a story "penalty" of some sort.

The repo agrees. The design contract at the top of `data/stories/continuity-initiative/storylets.md` says: "Storylets are optional, bounded situations attached to a playable scene. They may reveal already-permitted context, change pressure, move a scene-local NPC/item, or help satisfy a scene trigger. They are **not** hidden mandatory actions and do not replace free-form LLM roleplay." Every storylet has a `non_coercion_note`. Each scene has a timer (`pacing.yaml`: `nudge_after_turns` 8 to 10, `handoff_after_turns` 11 to 16). At the timer the engine delivers the missing reveals as authored fallback text and moves on. So the scene always ends.

## What that invalidates in your earlier answers

Your answers treated "an action that can no longer be earned" as a structural defect, and proposed to find and prevent it everywhere. Specifically these assumptions were wrong for this story:

- "A reachable action becoming impossible to earn is the clearest defect." A spent sibling is by design. A scene does not need every reveal.
- "Realizations within one storylet are alternatives. Actions that must remain independently available belong to separate storylets." and "no required continuation may depend solely on a sibling that another valid alternative consumes". Nothing is required. Progress is the timer's job, not the reveals'.
- The sibling-reachability check, and the idea to promote its findings to loader errors.
- "The follow-up must not become a required step" was right, but for the wrong reason; nothing is required anyway.

## What I measured after the correction

I built a report (merged, PR 574, `scripts/ringer/affordance/sibling_reachability.py`) that fires each reveal of every multi-reveal storylet and prints which siblings are then spent and whether their facts are still obtainable another way. On the real package it flags 26 rows (13 storylets, 21 distinct facts). I traced where each of those 21 facts is used downstream (transitions, other storylets' activation, other reveals' `requires`, bridge or resolution events, handoff cues):

- 16 of 21 are used by nothing. Losing them cannot affect the story.
- 5 have a downstream use: `patrol_return_pressure` and `restricted_corridor_access` (transitions; the first is also asserted by a timer event), `national_detention_network_known` (bridge event 1C), `brandon_janus_role_known` and `brandon_claimed_reform_motive` (bridge event 2B, which needs at least 2 of 3 facts). Those events have a timer backstop that force-fires missing parts. The two `*_rebecca_observes` reveals are `world_only` and not earnable by the player at all: four report rows start from firing one of them (a state that cannot occur), and four more only say that the hidden variant is not offered to the player.

So the report is mostly noise for this story. I removed the review file I had written from it.

## What the real problem is (still real, but narrower)

The 3A failure was player-facing, not structural. The scene text and a delivery line invited an action: "Michelle points toward the medical level, where the experiment records wait." The player entered the medical level (which fired storylet SL-3A-B and spent it), then typed "Examine/Read/Open the experiment records." **nine times**. Every one logged "This turn has no candidates", the SCENE block carried no records material, and nothing happened. The narrator restated the scene each time. An 80-call probe with extra story lines in SCENE did not fix it. The player was stuck in a loop on an action the STORY had invited, with no useful response, until the timer.

So the harm is: **an invited action gets no response.** A spent sibling alone is not a harm. A sibling that nothing ever invited is not a harm.

## What is built and merged so far

- PR 573 (merged): a separate optional storylet `SL-3A-E` with reveal `k_sl_3a_e_r1` (activation: michelle_reached, behavioral_experiments_known, conditioned_release_plan_known false; same words and delivery as the original records reveal) and a records item placed in the medical level. Offline: the recorded records commands now earn it; nothing else changed. Not yet measured live.
- PR 574 (merged): `explain_reveal` in `storygame/runtime/reveal_eligibility.py` (reasons: already_established, not_visible, storylet_spent, prerequisite_missing, source_inactive); `_candidates` uses it, behaviour unchanged.
- Found, not fixed: `RuntimeEngine._cue_reveal_available` checks only `requires`, not whether the source storylet is spent. So a cue can point at a reveal that is spent. Example: scene 1A after SL-1A-B fires, the cue for `continuity_initiative_known` is still available while `k_sl_1a_b_r1` is `storylet_spent`. That fits the real problem (an invitation to a spent reveal).

## How the game works (short reminder; the first brief has the full version)

Reveals have `action_evidence` (a verb group plus an object group; a command matches when it has a word from every group; exactly one reveal may match, two matches return none). A reveal belongs to a storylet; once one reveal fires, its siblings are no longer candidates. A cue (`cue_text` in `handoffs.yaml`) is one scene-description sentence that points the player at something to act on. `delivery_text` is fixed authored text appended to the narration. With no candidate, the narrator improvises from SCENE and THINGS.

Hard rules (do not break them): facts are the sole mutable truth; the shared runtime is story-agnostic and LLM-proposal-first; no story-specific runtime branches, fixed action tables, hand-edited generated artifacts or prose as canonical truth; no unvalidated provider output, protected-knowledge leak, or fact change after rendering; narrator rules must be 8th-grade, short, one idea per sentence; recommend only proven techniques first (the W decisions in `.plans/world-model.md`, `docs/world-model-grounding.md`, the fixes in earlier scenes), and say plainly when something is new. Player input is imperative commands, never first person.

## Your task

Revise your recommendations for the corrected premise. Rank them, most valuable first. For each give: the problems it addresses; the technique (proven here, or new, and say what you checked); where it lives (package data, loader, runtime, test harness); the offline check that would show it works before any live run; how matching and spending are affected; what would make you drop it.

Answer these specifically:

1. **Which parts of your earlier two answers do you withdraw, and which survive?** Name each one.
2. **Define "an invitation" for this engine.** Which things invite an action: `cue_text`, delivery lines that point ("Michelle points toward the medical level, where the experiment records wait"), scene entry text, the scene frame, narrator-invented pointers? Which of those can be checked mechanically against the package, and which cannot?
3. **What should happen when a player attempts an action the story invited and the reveal is spent, already earned, or not yet available?** The narrator today restates the scene. Options you may weigh: nothing (optional by design), an authored one-line response, a cue that stops pointing at spent reveals, or leaving the invitation out in the first place. Prefer subtractive fixes (stop inviting what cannot answer) over new narrator rules; most narrator rules tried have lost their probe. Say which options are proven here and which are new.
4. **Is the engine cue fix right?** `_cue_reveal_available` ignoring spent storylets: should cues use the shared `explain_reveal`, and what would you measure first, given that a cue change alters live behaviour?
5. **Was the 3A split (`SL-3A-E`) the right repair for an invitation case,** or would a subtractive repair (do not invite the records after the medical level spends the storylet) have been better? Say what you would change, if anything, and how to tell offline.
6. **Offline check.** Design a state-aware check for the corrected problem: for each invitation in each state it can appear, does an eligible reveal exist for the invited action, or is the invitation retracted? It must report, not assume every miss is a defect (ordinary world actions need not earn reveals).
7. **Timer-ended scenes.** The author says the timer should end a scene "with an explanation and a story penalty". Does the current fallback text carry that? You do not have the text, so only say what to check, not what it says.

Keep it short and concrete. Do not restate the earlier proposal. If your honest answer to any question is "no change needed", say so.
