# Brief for ChatGPT Desktop: make the copy-check penalty something the 2C player can actually do

You are helping with freytag-forge, an interactive-fiction engine with one shipped story ("The Continuity Initiative", nine scenes 1A to 3C). A player types free text and a small non-reasoning model narrates. Story text (plot, cue lines, delivery lines) is authored by you. I do not write it.

## Where we are

Last round you chose to ground the copy-check penalty by adding a plot sentence to 2C.4 (`plot.md`, applied byte-exact):

> Kristin can still check her copied evidence against the original files, but each moment spent on the comparison leaves less time to reach the captives.

plus the Details entry `chance to compare the copied evidence with the original files`.

The penalty line that depends on it is appended on 3C turn 10, only when the 2C timer forced the evidence delivery without the player earning it:

> `Kristin had no time to check her copied evidence against the original files.`

## What I measured (local bench, scene 2C, scripted player, 3 live replicates)

The new plot sentence never reaches the player. In 3 of 3 replicates:

- No narration mentions the original files, a comparison, or checking the copies against anything.
- The scripted command `Check the copied files for proof of the purge order.` is answered as searching the files. The narrator then appends the existing evidence line: `Kristin and Brandon have enough evidence to expose the conspiracy. Sending it now would reveal their position and seal the detention sectors. A message from Michelle is waiting.`
- Plot sentences and Details entries are background material for the narrator. They are never quoted, so they do not create an invitation by themselves.

So a player who reaches the copy-check penalty has been told they "had no time to check against the original files" and was never shown that this was an option.

## How the pieces work (so you do not guess)

2C evidence delivery, exactly as shipped (`handoffs.yaml`, fact `evidence_ready_to_transmit`):

- `cue_text`: `In the command levels, Kristin notices the copied files close at hand, yet using them could expose her and Brandon.`
- `fallback_text` (shown only when the timer forces the delivery): `Kristin and Brandon obtain enough evidence to expose the conspiracy, leaving the evidence in hand. It is ready to transmit, but sending proof will reveal their position. Time runs out before Kristin can check the copied evidence against the original files.`
- A forced delivery asserts the gap fact; an earned delivery leaves it unset.
- Earn path (`knowledge.yaml`): the player earns the evidence by an action that `checks, secures, or copies the copied files`. Words that match include copied files, proof, evidence, JANUS evidence, portable drive.
- Delivery lines the player sees on the way: `... The copied files lie close at hand.` (twice, in 2C turns 1 and 3).
- A cue line is shown to the player on the scene's first turns, pointing at the thing to act on. Cue and delivery text reach the player verbatim or near-verbatim; plot sentences and Details do not.

Design facts that limit you:

- There is no declared thing called "the original files". A name that the narrator may use as a place or object must be declared and placed (`docs/world-model-grounding.md`). I do not want a new declared thing unless you say it is the only way.
- The earn action is already "check the copied files". A player who does that earns the evidence and gets no gap. So the penalty must describe a check that goes beyond the earning action, or the player has to be able to see why the penalty is not the same as the earn.
- No progress rule may read the gap. Nothing later may depend on it.
- The penalty must read as weaker supporting evidence, never as failure, blame or a game-over. You said earlier the copy-check line is the strongest of the four because it names time pressure ("had no time to check").

## What I need (story text and a judgment, with reasons)

1. **Diagnose** in two sentences: is the problem that the invitation is missing, that the earn action already covers "checking", or both?
2. **Choose ONE** and give the exact text:
   - **A. Cue or delivery line that shows the check.** One short sentence added to the existing 2C cue or to a delivery line such as `The copied files lie close at hand.`, so the player sees the original files as something to compare against. Give the new full line (old and new), the field it goes in, and say whether it needs a Details entry. Say what the player would type to do the check, in the player's voice (imperative, e.g. `Compare the copied files with the originals.`), and what that action should earn or leave unset.
   - **B. Reword the penalty** so it describes something 2C already shows (for example the copies being untested under pressure) without naming original files. Give the exact new gap line and the matching `fallback_text` sentence. Say plainly what cost this loses compared with the current line.
   - **C. Drop the 2C.4 sentence** you added last round and the copy-check gap altogether, if neither A nor B holds. Say what would replace the cost.
3. For your pick, say which scenes and lines you checked, and what could still go wrong: for example the invitation reaching a player who already earned the evidence, or contradicting `Time runs out before Kristin can check ...` in the fallback text.
4. Give a one-line player test: the exact imperative command and the narration a reader should see if it works.

## Rules you must keep

- Existing `fallback_text`, `delivery_text`, `cue_text`, plot lines and the two default pacing lines stay byte-identical **except** the lines you change. Say plainly which existing lines you touch.
- Facts are the only truth. A line may show what is happening or what is visible. It may not reveal knowledge the player has not earned or name a hidden place.
- Cue and delivery lines are read by a small model. Keep any line you add to short sentences, one idea each, plain common words. The gap lines are emitted verbatim and may be more formal.
- Player input examples must be imperative commands in the player's voice, an active move with a verb and an object: `Compare the copied files with the originals.` Never first person, never `wait`, never a restraint.
- Say what you could not check. I have not measured 1C (the processing-numbers line is in the same state) and I will bring that back separately.

Keep it concrete and quote exact text. No new mechanism.
