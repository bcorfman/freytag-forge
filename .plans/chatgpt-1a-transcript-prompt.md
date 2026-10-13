# Brief for ChatGPT Desktop: fix the story material behind one bad 1A playthrough

You are advising on freytag-forge, an interactive-fiction engine with one shipped story, "The Continuity Initiative". A player types free text. A small, non-reasoning Llama-class model narrates each turn. The engine, not the model, owns the world facts and decides which authored "reveal" a command earns. You cannot run the game. If you can read the repository files named below, read them. If you cannot, use the excerpts in this brief. Do not edit files. Propose paste-ready text only.

This brief is about story material and wording only: reveal wording, aliases, cue and delivery text, plot lines, pacing text. The engine side (seating the player in the truck, showing the laptop on the passenger seat) is already being fixed in code. Do not propose code, regexes, new engine mechanisms, or new narrator rules.

## How the engine uses the material

- A reveal (a `k_sl_*` item in `data/stories/continuity-initiative/knowledge.yaml`) has `action_evidence`: a list of word groups. The exact matcher (`storygame/runtime/candidate_matcher.py`) fires a reveal only when the command contains at least one word or phrase from EVERY group, as whole words, with possessives and plurals handled. If a command matches two eligible reveals, that is a tie and nothing fires. Commands with negation words ("do", "not", "don't", "without", "instead of") never match. The reveal's `requires` facts must already be true.
- If the exact matcher finds nothing, a bounded semantic fallback asks a small model one yes/no question per shortlisted reveal, using the reveal's `earn_when` text. It is literal.
- Each scene has pacing in `pacing.yaml`. After `nudge_after_turns` the engine appends the authored cue text (`handoffs.yaml`). After `handoff_after_turns` it force-delivers the remaining reveals. A forced delivery is a backstop. The goal is that an ordinary player earns reveals by playing.
- The narrator is shown the scene facts, a THINGS list (each thing and its place) and a few rules. It improvises the rest. When two authored things share a word, the narrator picks the wrong one. Past fixes: rename one of the two things in the fiction, scope an alias to the scene it belongs to (`scoped_aliases` in `world.yaml`), widen a reveal's verbs or objects, add a handoff or cue, remove a line that pulls the wrong way. Most added narrator rules lost their probes (go-into-a-place rule 1/15 vs 4/15).
- A safety scan rejects narration that names a later-scene thing or protected term early. New words must not contain a protected or later-scene term. Check `leak_terms` in `knowledge.yaml` and the aliases in `world.yaml`.

## The scene (1A, Michelle's house)

`plot.md` Scene 1A: location `mcgehee_home`. Places: kitchen, outside the house. Things: Michelle's workstation (in the kitchen) with a drawer (KMS carved into it), the workstation chair (overturned), Michelle's phone (kitchen floor), the back door (forced, in the kitchen), Kristin's truck (outside the house) with a driver's seat and a passenger seat, Kristin's laptop (now on the passenger seat of the truck), and the hidden memory card (taped beneath the drawer).

The scene's own situation line (`knowledge.yaml` line 250): "Michelle's home is otherwise untouched, but its back door frame shows recent damage. Michelle is missing, and her tablet and work bag are gone. A drawer on Michelle's workstation has Kristin's initials, KMS, newly carved into it."

Plot beats:
- 1A.1: the missing tablet and work bag, the overturned chair, the forced back door, the carved KMS drawer. "The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers."
- 1A.2: Kristin finds the memory card taped beneath the drawer. She takes the card out to her truck and opens it on her laptop. The card holds Michelle's research on the Continuity Initiative.
- 1A.3: the damaged voice recording on the card.
- 1A.4 (patrol): "An emergency patrol arrives at Michelle's home unusually quickly. The officers conduct a quick welfare check and a targeted look at Michelle's work area... They do not open the drawer, so the card remains undiscovered... Kristin conceals the memory card and pretends to know nothing. After the patrol leaves, she notices that one officer has quietly marked the front gate with a strip of reflective tape."
- The scene exits to 1B (the park) through transition `t_1a_1b`, bridge text: "Kristin starts the truck and heads for the park, avoiding checkpoints and emergency patrols." It needs the card recovered and a park lead (the card's files point to a dead drop at a bench in the park).

Relevant reveals in `knowledge.yaml`:
- `k_sl_1a_f_r1` (open the drawer): groups `[pull open, pull out, pull the, pull my, pull michelle, "pull michelle's", slide open, slide out, tug, yank, open the, open my, open michelle, open her]` x `[drawer]`. Delivery: "The drawer slides out. It holds a stapler, spare batteries, pens, and binder clips. A thin gap beneath its lower edge is wide enough for Kristin's fingers."
- `k_sl_1a_f_r2` (examine the initials): `[examine, inspect, study, read, look at, check, trace, run my fingers]` x `[initials, carved initials, carving, my initials]`. Delivery: "The initials are fresh, deep cuts. The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers."
- `k_sl_1a_b_r0` (find the card), `earn_when: searches the drawer, the gap in the drawer, or the space beneath it`: `[look, search, inspect, check]` x `[under, beneath, underside, gap, lower edge, bottom edge]` x `[drawer, KMS, workstation, "drawer's"]`. Statement: "Kristin finds Michelle's memory card taped beneath the drawer and takes it with her."
- `k_sl_1a_b_r1` (read the card): `[read, inspect, open, check, review, plug, insert, connect]` x `[memory card, card]` x `[file, files, saved file, saved files, card file, card files, laptop]`.
- Cue text for the nudge (`handoffs.yaml`, 1A): "Kristin's initials, KMS, are carved into a drawer of Michelle's workstation. The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers."
- `world.yaml`: `memory_card` has `name: Michelle's memory card`, `aliases: [memory card]`, `hidden: true`.

Pacing (`pacing.yaml`, scene 1A): min turns, nudge and handoff turns are in the `scenes` list. The pressure events for 1A are:
- turn 4 `pressure_1a`, three variants chosen by facts: card not yet recovered: "An officer from the patrol comes back and lingers at the drawer on Michelle's workstation without opening it."; lead actionable: "The patrol is coming back and it is time to leave."; card recovered: "The patrol is back and searching the house for something Kristin now carries."; fallback: "The patrol is returning to the house."
- turn 8 `home_search_narrows_1a`: "The patrol is checking parked vehicles and speaking to neighbors. The house is no longer the only place under watch."

The engine appends the cue and the card-found text itself ("Kristin finds Michelle's memory card taped beneath the drawer. She takes it with her. Her laptop is in her truck outside." is the delivered reveal text the player saw).

## The playthrough (verbatim; ">" lines are what the player typed)

```
Michelle's text came in a little after 4:00am, while Kristin was finishing a late-night shift. It came in during all the other emergency alerts, and Kristin had missed it by minutes. Trying to call Michelle back was hopeless - calls stopped going through. Kristin jumped in her truck to drive to Michelle's house, but police cars, ambulances, and blocked intersections turned the drive into an ordeal.

Kristin stands in the quiet living room, her eyes scanning the space for any sign of Michelle. The room is tidy, with no signs of disarray or struggle. Kristin's gaze falls on the workstation, where Michelle's chair is pushed back, as if she had just gotten up.
>examine the workstation for clues
Kristin walks over to the workstation in the kitchen, her eyes scanning the area for any signs of disturbance.
She notices that the chair at the workstation is overturned, and there are a few scattered papers on the floor.
Kristin bends down to pick up the papers, examining them for any clues.
Kristin's initials, KMS, are carved into a drawer of Michelle's workstation. The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers.
>search the gap
Kristin inspects the gap between the back door and the frame, looking for any signs of forced entry.
She notices a small splinter of wood and a faint scratch on the door frame, indicating that someone had indeed tried to pry the door open.
The scratch seems to be recent, and Kristin's eyes narrow as she takes in the evidence.
>put fingers into the drawer gap
Kristin carefully examines the gap in the back door frame, her eyes scanning for any signs of forced entry.
She notices that the wood around the gap is scratched and splintered, indicating a struggle.
Kristin's mind is racing with possibilities, but she remains focused on finding evidence of Michelle's disappearance.
Kristin finds Michelle's memory card taped beneath the drawer. She takes it with her. Her laptop is in her truck outside.
>go out to the truck
Kristin walks out to her truck, which is parked outside the house.
She gets into the driver's seat and starts the engine.
The patrol car pulls up behind her truck, and two officers get out to approach her.
>put the drive in my pocket
Kristin reaches into her pocket and takes out Michelle's memory card.
She examines the memory card, but it's not revealing any information.
>hide the memory card
Kristin carefully searches her pockets and finds a small compartment where she had stored Michelle's memory card.
She pulls it out and looks at it for a moment before deciding to hide it.
Kristin puts the memory card in her pocket, making sure it's secure.
>go outside
Kristin walks out of the house, looking around the quiet neighborhood.
She gets into her truck and starts the engine, then pulls out of the driveway.
She drives down the street, trying to clear her head.
>stop the truck
Kristin stops the truck and looks around, taking in the scene.
The patrol is checking parked vehicles and speaking to neighbors, their flashlights casting a warm glow on the quiet street.
Kristin's eyes scan the area, her mind racing with possibilities.
```

## Constraints

1. **Prior art first.** Read `docs/scene-fixing-guide.md`, `docs/world-model-grounding.md`, and `.plans/world-model.md` section 12 (W decisions). Recommend only proven techniques (see "How the engine uses the material"). If you propose something new, say so, say what you checked, and rank it last.
2. **Subtractive first.** Remove or scope a conflicting line, or rename one of two colliding things in the fiction, before adding text. The narrator is a small model. Added rules compete with each other.
3. **Material, not rules.** Give the narrator concrete things to cover (nouns, entry text, authored lines), not prohibitions.
4. **Matcher rules.** Any `action_evidence` change must be scored against the matcher: every group needs a hit, whole words, exactly one reveal may match. Check each new wording against the sibling reveals (`k_sl_1a_f_r1`, `k_sl_1a_f_r2`, `k_sl_1a_b_r0`, `k_sl_1a_b_r1`) so you do not create ties.
5. **No leaks.** Check every new alias and word against `leak_terms` and the aliases in `world.yaml`. "Drive" and "card" are common words: say whether an alias for the memory card would also collide with other uses (for example "drive the truck") and whether `scoped_aliases` or a different word solves it.
6. **Writing level.** New narrator-facing or player-facing text: 12th grade reading level or lower, short sentences, one idea each, plain words.
7. **Player input** in your examples is imperative and uses first-person possessives for the player's own things ("Check my laptop."), never "I search...".
8. **Keep the story intact.** Do not change reveal ids, `establishes`, `requires`, pacing numbers, or the plot's events. Do not change `entry_text` or `bridge_text` unless you show a sentence cannot work otherwise, and say plainly that it changes player-visible text.
9. **Prefer authored text over model generation.** Where a beat must always read the same way (concealing the card, the laptop notice), propose a fixed authored line.

## Task

Read the playthrough as a careful player and an editor would. Find every place where the narration goes wrong against the authored material, the player's command, or the story's own logic. Do not assume the list is short. Judge each turn on four questions:

- Does the narration match the authored places, things and facts?
- Does it do what the player typed, and does the engine's reply (reveal text, cue, pressure line) fit where Kristin is and what she holds?
- Does it invent things, rooms, people or events the material does not give it?
- Does the scene still move toward the card, the laptop and the park lead, or does the player get lost?

Then:

1. **Problem list, recommendation first.** One entry per problem: the turn, the quoted text, what is wrong, the root cause (which authored line, alias, evidence group, cue or missing material produced it, or whether it is the model improvising with nothing to anchor it), and whether the fix is story material, engine work (say what the engine would have to do, without writing code), or not worth fixing. Also say which problems you could not diagnose from the material alone.
2. **For each material problem, at most three ranked fixes,** each with the exact file and a paste-ready change (YAML or text), the proven technique it follows, the risk (ties, leaks, a regression in another scene), and the cheapest offline check. Where a command should earn a reveal, include a scoring table of at least 12 commands: command, expected reveal or none, your matcher verdict, including the commands the player actually typed.
3. **Review this authored line for the truck:** "Kristin's laptop sat on the passenger seat." The engine adds it when Kristin gets into the truck's driver's seat, right after "Kristin sat down in the driver's seat." Say if it reads well and propose a better line if not.
4. **Smallest live test:** which bench script or hosted run, how many replicates (10 to 15 samples per arm for a fixed-prompt probe), what to count, and what result would make you drop the proposal.
5. **An honest limit statement:** what offline scoring cannot show.

Keep sentences short. Put the recommendation first, then the evidence.
