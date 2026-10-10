I need a careful review of a proposed change to a text-adventure story. You
cannot see the game's files, so everything you need is below. Do not write new
story text unless a section asks for it. Be specific, and say "I cannot tell
from this" where that is true. Do not agree with the change just because I
proposed it.

## How the game works (only what matters here)

The story is "The Continuity Initiative", in scenes 1A to 3C. A small AI
narrator writes each reply. Every turn the game sends it a SCENE block: short
sentences of story facts. Some facts are always sent for the current scene.
Facts the player earned earlier are sent every turn ONLY if their entry lists
the current scene in `available_in_scenes`. A fact from another scene is sent
only when the player's own words name it (for example, the player types
"Rebecca's office"). Earned facts are never forgotten by the game state. The
only thing that changes is whether the narrator is shown the sentence.

A scene changes when a "trigger fact" becomes true. For 2C to 3A the trigger
fact is `combined_broadcast_rescue_plan_known`. Two reveals in 2C make it
true: `k_sl_2c_d_r1` (the player decodes Michelle's message) and
`k_sl_2c_d_r2` (the player follows Michelle's maintenance route). Both also
make `rebecca_office_required_for_broadcast` true. Both belong to storylet
SL-2C-D, which is marked to abort when the scene is not 2C. My reading is that
nobody can earn them in 3A, but I have not proven that.

## The problem

In live tests, scene 3A ("Reaching Michelle") often runs out of time. Three
runs: one ended by play in 9 turns; two ended on the timer after 13 and 14
turns. In the two bad runs the player spent most of the scene trying to reach
Rebecca's office or seize the broadcast controls, and never did what 3A is
about: reach Michelle, see the experiments, talk to the senior official, and
start the uprising. Scene 3A only ends when those four things happen.

## What I found

In 3A the narrator is shown these two lines, and they are the only lines in 3A
that name something to act on:

1. (`k_sl_2c_d_r1`) "Michelle's encrypted message marks a maintenance access
   route into her holding block and reveals that Rebecca's secured office can
   broadcast the evidence and open the detention cells in the sealed sectors."
2. (`k_sl_2c_d_r2`) "Kristin traces Michelle's maintenance code route into her
   holding block, then to Rebecca's office, and learns the plan can rescue the
   captives only if they seize the controls to broadcast the evidence."

Both have `available_in_scenes: [2C, 3A]`, so they go to the narrator on every
3A turn once earned.

I replayed one recorded 3A turn with the real narrator, 12 replies per case,
and read every reply. The player's command was "Broadcast the JANUS evidence
through the seized controls."
- Both lines present: 7 of 12 replies headed for Rebecca's office or the
  broadcast; the rest followed Michelle's route.
- Both lines removed: 0 of 12 named Rebecca's office. The narration stayed on
  Brandon, the radios and the captives.
- Only line 2 removed: 6 of 12 still headed for Rebecca's office (line 1
  pulls that way).
- Only line 1 removed: 12 of 12 said to "seize the controls and broadcast"
  (line 2 pulls that way).

## The proposed change

Remove "3A" from `available_in_scenes` on both entries, so they read `[2C]`.
They would still be earned in 2C and still be true. In 3A they would reach the
narrator only if the player's words name them.

## The 3A story, as written

Objective: "Reach Michelle and join the uprising." Entry text: "A partly
unsecured detention sector opened onto rows of captives. Coded announcements
crackled through stolen radios, and the prisoners moved with a discipline no
captor had taught them - someone inside had been organizing this long before
rescue arrived."

3A.1: Kristin follows Michelle's maintenance route into one partly unsecured
detention sector. Michelle speaks into a stolen radio, coordinating prisoners
through coded announcements. Their reunion is brief because the purge
countdown has begun. Michelle explains that the facility holds only a fraction
of the missing millions, and freeing them will matter only if the broadcast
reveals the locations of the remaining sites. She points toward the medical
level.

3A.2: Michelle leads Kristin through the medical level and its experiments.
The senior official waits among the government prisoners.

3A.3: The senior official gives one-use codes for the emergency surface
gates. They expire when Charles's new authority is activated. "Michelle turns
toward the prisoners at the checkpoints."

3A.4: Michelle triggers coordinated disturbances; prisoners disable cameras and
seize checkpoints. Charles seals the primary exits and sends armed teams
downward. "Kristin, Michelle, and Brandon must fight upward toward Rebecca's
office while the prisoners hold the lower levels."

Bridge text to 3B: "Michelle's uprising disabled cameras and seized
checkpoints, while Charles sealed the primary exits and sent armed teams
downward. Kristin, Michelle, and Brandon fought upward through the security
corridors."

Scene 3B ("The Battle for the Broadcast") is set in the security corridors,
command center and Rebecca's executive office. Its objective is to overload
JANUS with false alarms.

## What I want from you

1. **Story check.** Does 3A, as written above, need the narrator to carry these
   two lines on every turn? Say what, if anything, in 3A, 3B or the ending
   would read as a continuity gap if the narrator no longer volunteers them in
   3A. Remember the lines stay true, and they still reach the narrator when the
   player names Rebecca's office, the broadcast, or the message.
2. **Consequences.** List every story consequence you can see, scene by scene
   (3A, 3B, 3C), good or bad. Include: a player who forgot the plan; Brandon
   or Michelle speaking about the plan in dialogue; whether 3A.4's "fight
   upward toward Rebecca's office" still lands; and whether the player now has
   anything to do in 3A at the start. Mark each as certain, likely or guess.
3. **Plan check.** My claim is that these two reveals cannot be earned in 3A,
   so nothing is lost for a player who skipped them in 2C. From the facts
   above, say whether that holds and what would break it.
4. **Alternatives.** Is there a better fix than removing the two lines? For
   example, keep one line, or keep both but change their wording so they point
   at Michelle first. Judge each against the test results above (each line
   pulls a different way). If you suggest new wording, give it as one or two
   short sentences at an 8th-grade reading level, using only facts already in
   this brief. Do not name Rebecca's office as a thing to do right now. Never
   use the word "phase".
5. **Verdict.** Approve, approve with changes, or reject, in one sentence, then
   the three checks you would run first to prove the change safe.

Other readers will test your answer. Do not invent story facts.
