# Brief for ChatGPT Desktop: ground two evidence-penalty lines in what the player saw

You are helping with freytag-forge, an interactive-fiction engine with one shipped story ("The Continuity Initiative", nine scenes 1A to 3C). You judged the four timer-penalty lines last round (`.plans/chatgpt-penalty-read-prompt.md`). They now read as plain statements (no "Michelle says"). Your honesty check found two lines that name something the plot never established. I need story text from you, because plot and handoff lines are authored story text and I do not write them.

## The two lines, exactly as shipped

Both are appended verbatim to a 3C pacing turn, only when a scene timer forced a delivery the player did not earn.

1. Turn 4, `evidence_gap_processing_numbers` (earned in 1C, scene 1C.2): `Kristin could not copy the full set of prisoner numbers from the processing line.`
2. Turn 10, `evidence_gap_copy_check` (earned in 2C, scenes 2C.3 and 2C.4): `Kristin had no time to check her copied evidence against the original files.`

## What you found

- 1C.2 says Kristin sees prisoner identification numbers that match Michelle's missing-person reports. It never says she can copy a "full set", or that copying is something she attempts.
- 2C.3 and 2C.4 give the evidence ("copied evidence" in the Details) and the time pressure. Neither offers a comparison against original files, so line 2 names a check the player was never invited to do.

## What I need (story text and a judgment, with reasons)

For each line, choose ONE of these and justify it in two sentences:

- **A. Reword the gap line** so it claims only what the plot already shows. Give the exact new sentence.
- **B. Add one plot sentence** (to 1C.2, or to 2C.4) that makes the line true, copied-style so it can be pasted into `plot.md`. Give the exact sentence, the scene it goes in, and where in the scene. Remember the player only sees what the narrator is handed, so say whether a Details entry is also needed.

Prefer A when it works: it changes one pacing line and no plot. Choose B only if A would lose the cost entirely. The cost must still read as weaker supporting evidence, never as failure, blame or a game-over.

## Rules you must keep

- Existing `fallback_text`, `delivery_text`, `cue_text`, plot lines and the two default pacing lines stay byte-identical except the lines you change; say plainly which you touch.
- Facts are the only truth. A pacing line may show what is happening or what is visible. It may not reveal knowledge the player has not earned or name a hidden place.
- No progress rule reads a gap. Nothing later may depend on a gap.
- The gap lines are emitted verbatim, not written by the small narrator, so they need not use its eighth-grade register. Keep them plain and in the voice of the story.
- Player-facing wording for a player who played 1C and 2C thoroughly and never hit a timer: the line must never confuse them, because they never see it.
- Say what you could not check.

Keep it concrete and quote exact text. No new mechanism.
