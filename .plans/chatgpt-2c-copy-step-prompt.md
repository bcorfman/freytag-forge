# Brief for ChatGPT Desktop: players cannot take the 2C copy step, so the scene runs out its timer

You are advising on freytag-forge, an interactive-fiction engine with one shipped story ("The Continuity Initiative", nine scenes). A player types free text. A small non-reasoning Llama-class model narrates each turn. The engine, not the model, owns the world facts. Read the whole brief, then answer the task at the end. Every claim you make must tie to the evidence below. Story lines and word lists are yours to write; code is not.

## How the game works (what you need to know)

- The player types an imperative command ("Copy the files to my USB drive."). Never first person.
- Each scene has **reveals** (knowledge items). A reveal fires when the command matches its `action_evidence` and its `requires` facts hold. `action_evidence` is a list of word groups. The command must contain **one phrase from each group** (case-insensitive, whole phrase). Group 1 is the verbs. Group 2 is the object. There is no other matching, no stemming, no synonyms.
- When a reveal fires, its `delivery_text` is appended to the narration and its `establishes` facts are asserted.
- The scene also has a **timer**. At turn 16 in 2C the engine forces the missing deliveries and moves on. The player then gets the reveals they did not earn.

## The problem

Scene 2C ("The Trap Closes") has a chain: c_r1 or c_r2 (the evidence step) sets `evidence_ready_to_transmit`. The Michelle reveals d_r1 and d_r2 require that fact plus `purge_clock_started`. So a player who never fires c_r1 or c_r2 never reaches the Michelle message and leaves 2C by timer.

Live blind-player runs (hosted staging, main 80f5c64c, three replicates per scene). 2C left by play in 1 of 3. Two timers at turn 16:

- **r1.** Turn 2 typed `Retrieve my copied JANUS files.` Nothing fired. The player never retried the files and chased Michelle's transfer order for 14 turns.
- **r2.** Turn 2 and turn 3 typed `Take the copied files.` Nothing fired, though the narration said "Kristin takes the copied files from the console." Turn 8 typed `Use my copied files on the purge-control console.` Nothing fired.
- **r3 (played).** Turn 1 typed `Copy Michelle's prisoner status records to my USB drive.` That matched "copy" plus "USB drive" and c_r1 fired. Scene left by play at turn 8.

On db9b9ac 2C also had one timer (r1); I did not read that player's commands. On a773378 and 41240bb 2C was 3/3 by play. Three replicates cannot say how often the gap bites; a lucky command hides it.

The player is not being sloppy. "Retrieve", "Take" and "Use" are what a person types to a file the story calls "close at hand".

## The data as it is now (`data/stories/continuity-initiative/knowledge.yaml`)

c_r1 (`k_sl_2c_c_r1`), the evidence is secured. Requires `janus_evidence`.

- Group 1 (verbs): read, check, search, study, open, inspect, review, secure, copy, finish copying, save, verify, back up, download, transfer, examine, analyze, eject, monitor
- Group 2 (objects): copied file, copied files, archive file, archive files, proof, evidence, JANUS evidence, JANUS files, copied JANUS files, portable drive, JANUS records, copied JANUS records, development records, JANUS development records, USB drive, my USB drive, USB drive transfer, USB drive's
- `earn_when` text: "checks, secures, or copies the copied files"
- Delivery: "Kristin and Brandon have enough evidence to expose the conspiracy. Sending it now would reveal their position and seal the detention sectors. A message from Michelle is waiting."

c_r2 (`k_sl_2c_c_r2`), Brandon wants to send it now. Same `requires`, same fact set.

- Group 1: argue, discuss, debate, ask, weigh, consider, decide, broadcast, send, transmit, release, upload, publish
- Group 2: send now, sending the, sending files, sending the proof, the risk, risk now, JANUS evidence, my JANUS evidence, the JANUS evidence, the evidence, copied files, the copied files

The cue text that points the player at the files (`handoffs.yaml`, fact `evidence_ready_to_transmit`): "In the command levels, Kristin notices the copied files close at hand, yet using them could expose her and Brandon." The two earlier 2C deliveries (c-chain SL-2C-A and SL-2C-B) also end "The copied files lie close at hand." So the story itself calls them "the copied files" and says "using them". But "use", "take", "retrieve", "get", "grab", "pick up", "pull up", "load", "plug in", "access", "view", "look at", "show" and "bring up" are in neither verb group. "Use my copied files" is the cue's own verb and it misses.

Plot (`plot.md`, 2C.3): "Kristin and Brandon obtain enough evidence to expose the conspiracy, but transmitting it will reveal their position and seal the detention sectors." The files are the "copied conspiracy evidence" and "copied evidence". Where the files were copied is not checked here; the story and the cue both call them "the copied files", so the phrase is natural.

## What we already tried (proven techniques)

- **Widening `action_evidence` verb groups** on a reveal when blind players type a natural verb that misses. This has been done several times in this story (1A drawer words, PR 569; 3C d_r2 and e_r2 phrases, PR 568). Each was probed against the real matcher and then measured live. It is the proven technique for this class of miss. The risk each time was a verb that also fires an unrelated reveal.
- **Cue text change** so the cue names the verb the data accepts (the 2C frame names the detention level, PR 545).
- **Rejected:** a matcher that guesses synonyms, a runtime verb table, a narrator rule telling it to name the action. The grounding guide and our own probes say no to these.

## What I think (challenge it)

- The fix is story data only. Add the missing verbs to c_r1 group 1 and decide which of them also belong in c_r2 group 1. "Take", "retrieve", "get", "grab", "pick up", "pull up", "load", "plug in", "access", "bring up", "view", "look at" read as holding or opening the evidence, so they belong with c_r1 (secure the evidence). "Use" is the cue's own verb and is ambiguous: opening the files (c_r1) or sending them (c_r2).
- Two commands could match both c_r1 and c_r2 (for example "Send the copied files" matches only c_r2 today, but "Take the evidence" would then match c_r1 and "evidence" already in both groups). I do not know which reveal the engine prefers when both match. The code check will tell us; assume I have to prove no new overlap.
- The cue may need the verb. If group 1 gets "use", the cue's "using them" works. If it does not, the cue should say "check" or "copy".

## Task

Write the smallest set of story lines that lets a natural command reach c_r1 (or c_r2) when the player acts on the copied files. For each answer, say whether it is a proven technique above or new, and name what you checked.

1. **Verb list for c_r1 group 1.** Give the final list (existing verbs kept, new verbs added). State your rule for what belongs ("a verb that means the player gets, holds or opens the evidence") and show how it sorts take, retrieve, get, grab, pick up, pull up, use, access, view, look at, load, plug in, bring up, show, compare, send. Do not add a verb that also fires an unrelated 2C reveal; the other 2C reveals are the purge-order items (SL-2C-A), the broadcast-schedule items (SL-2C-B; verbs read/check/search/study/open/inspect/review) and Michelle's message (d_r1, d_r2; verbs decode/read/check/study/open/search/inspect/decrypt/examine/analyze/compare). Read the SL-2C-A and SL-2C-B verb lists from the repo if you can; I have not pasted them. List any collision you find.
2. **Verb list for c_r2 group 1.** Same rule. Say whether "use" belongs in c_r1, c_r2, or neither, and why.
3. **Object phrases.** Are the c_r1 and c_r2 object groups enough? The failing commands used "my copied JANUS files" and "the copied files" and "my copied files". Check that every one contains an existing object phrase (it does: "copied files" and "JANUS files" are in both) and name any phrase the player is likely to type that is missing (for example "the files", "my files", "the drive", "the data").
4. **Cue.** Should the cue text change so it names a verb the data accepts? Give the exact new cue line, or say no change.
5. **Collision check.** Say which commands from the failing runs (listed above) would match after your change, and which reveal each would fire. Also name two plausible commands that must NOT fire c_r1 or c_r2 (for example `Open the purge-control console.`).
6. **Honest limits.** Say what this does not fix: the 2C r1 player also chased Michelle's transfer order for 14 turns without seeing the files again, and r2's opening put Kristin in the command levels, not at the files. State whether widening the verbs alone is expected to move the 2C play exit rate, or whether the cue also has to fire again after turn 3.

Format: a short diagnosis (at most 8 lines), then the verb lists and the cue as paste-ready YAML for the two items (`action_evidence` blocks and the cue line), then the collision table. Keep sentences short. Do not propose engine changes, matcher changes, a new reveal, or a narrator rule. If you think the verbs are not the real cause, say what is, and name the evidence.
