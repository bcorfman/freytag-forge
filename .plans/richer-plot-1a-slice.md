# Richer plot, first slice: Scene 1A

Status: draft for Brandon's reaction, 2026-11-02. Nothing here is in `plot.md` or any story file yet.
Direction (his words): "I want the plot itself to be richer, not just embellishments ... treat the
current story as more of an outline level and just draft more to begin with, resolving any story
problems yourself as you go."

## Method

- Enrich inside each scene. Keep scene order, the 120-turn ceiling and every protected reveal.
- Author the things the narrator reaches for anyway. In 2,202 recorded turns the plain things it
  invented most were paper, lock, splinters, lantern, key. Declaring them gives the small model
  material to cover instead of a reason to invent.
- Every richer detail is optional to find, never a new required step. New optional situations are
  storylets; nothing new gates a transition.
- Every plant has a payoff later. Plants are listed at the end.

## Story problems found in 1A, and how I resolved them

1. **Who carved KMS, and why would Kristin see it?** Resolved: Michelle carved it the evening before,
   with her letter opener. It is their old signal from college, when they hid notes under desk
   drawers. The gap under the drawer is where Kristin would look because she taught Michelle the habit.
2. **Timeline of the card.** Resolved: Michelle hid the card and carved the mark around midnight, once
   she knew she was watched. She texted Kristin at 4:07 ("Come to the house. Don't call.") and began
   the recording. The recording stops when the intruders enter. They take the tablet and work bag and
   miss the card.
3. **Why the patrol arrives so fast and ignores the drawer.** Resolved: the sweep team's inventory lists
   "one removable media item, not recovered." The patrol is the second pass for it. They search
   the work area because the list says to, not because they know where the card is.
4. **"Forced" door.** Resolved: the frame splinters point outward. Someone broke it from inside to look
   like a burglary. This is a clue Kristin can read, so the staging means something.

## The richer scene

### 1A.1 — Michelle Is Gone (adds the lived-in kitchen)

The kitchen is a person's last hour, not a crime-scene checklist.

* A mug of tea on the workstation, the bag still in it, faintly warm. Michelle made it near the end.
* Her reading glasses lie folded on a stack of red-penned manuscript pages. She never goes anywhere without them.
* The wall calendar has Saturday circled in her handwriting: *K — lemon cake*. Kristin's birthday.
* On the refrigerator, a snapshot of the two of them at a lake, held by a magnet shaped like a pear.
* The back door's frame is splintered outward, and the deadbolt is thrown. Nobody forced it from outside.

Kristin has stood in this kitchen a hundred times. What is wrong is quiet: the tea, the glasses, the calendar.

### 1A.2 — Michelle's Last Investigation (unchanged in substance)

The card, the Continuity Initiative files and the sentence about choosing who remains stay as written.
One addition: the folder names on the card are in Michelle's habit of titling things after their
college dorm, so only Kristin would read them as a message.

### 1A.3 — The Interrupted Message (adds the broadcast loop)

The recording stays as written. Afterward, in the truck, Kristin tests Michelle's last whisper. She
turns on the truck radio. The emergency broadcast is the same ninety seconds of statement, word for word,
every time it comes around. She times two passes. It is a loop, not a live voice. This is optional,
costs two turns, and gives the player a way to confirm Michelle's warning with Kristin's own skills.

### 1A.4 — The First Threat (adds a neighbor and a named officer)

* **Walt Pruitt**, seventies, retired bus driver, stands at the fence between the yards. His wife is
  one of the missing. He saw "county" vans at 3:40, no markings Kristin can read, and two men with a
  clipboard who checked the addresses on the street. They skipped the house next door. He is unsure and
  says so. He does not confirm anything, and he will not say it to the patrol.
* **Officer Reyes** leads the welfare check. Young, polite, working off a printed list. He studies the
  refrigerator photograph a beat too long. He asks about Michelle's research and does not open the drawer.
  He is the one who marks the gate with reflective tape. If Kristin has shown Walt kindness, Walt
  speaks up for her when Reyes asks who she is. That costs Walt: Reyes writes his name down.

## What gets declared (world.yaml), placed in 1A

Things: mug of tea, reading glasses, manuscript pages, wall calendar, lake snapshot, back door
frame (splinters), back door deadbolt, truck radio, reflective tape (on the gate once placed).
People: Walt Pruitt (outside, at the fence), Officer Reyes (replaces the unnamed patrol officer's
label once named). Each needs aliases, scene placement text, leak-term review, and no clash with
existing names.

New optional storylets: `SL-1A-G` Walt's account; `SL-1A-H` The broadcast loop. New non-protected
knowledge: what the kitchen shows; the loop; Walt's partial account. Protected knowledge is untouched.

## Pacing impact

None. Turn ceiling stays 13. Both new storylets are optional, and the loop test costs two turns that the
current 1A window already leaves unused for most players.

## Plants and payoffs

| Plant in 1A | Payoff |
|---|---|
| Clipboard and skipped houses | 2B, the selection algorithm: the address list that chose who vanished |
| Looping broadcast | 3B and 3C, the broadcast contest and its false voice |
| Lemon cake on the calendar | 3A or 3C: Michelle's private proof it is really her |
| Outward splinters | 2B: Michelle was staged as bait; the "burglary" was written for Kristin to find |
| Reyes studying the snapshot | a possible later glimpse of him at a checkpoint, choosing not to look |
| Walt is written down | an optional consequence if Kristin passes the house again in 1B |

## Propagation after approval

1. `plot.md` 1A text (this file's beats), then `world.yaml`, `knowledge.yaml`, `storylets.md`,
   `storylet-routes.yaml`. Each through a Ringer task whose check loads the package and runs the story
   suites. Update the pinned tests that name 1A things.
2. A cheap local probe on the opening and the first turns, as for earlier 1A fixes.
3. Same method for 1B through 3C, one scene at a time: read it, draft it, resolve its problems, then
   propagate. The embellishment steps already built stay available; their prompt work is deferred.
