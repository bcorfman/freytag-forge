# End-user acceptance test plan

This is a short, human playtest for the refactored engine. Run it once in the
CLI and once through a web surface; use the same seed and story profile when
the surface allows it. Capture the transcript or screenshots—what the player
saw is the evidence.

## The opening: “I know where I am”

Start a new story. Read the opening before entering a command.

- It establishes a character, place, immediate pressure, and a doable next
  move without leaking a later twist.
- Named people, visible objects, and the room agree with later descriptions.
- It feels like story prose, not setup notes, JSON, or a command menu.

## The invitation: “Can I try that?”

Try three naturally phrased actions: examine something, speak to someone, and
attempt an unusual but plausible move (for example, offer help, conceal an
item, or propose a risky shortcut).

- The game treats each as an in-world attempt, not an “unknown command.”
- A feasible action changes the situation or yields a specific, grounded
  outcome; an impossible one explains why without rewriting what is true.
- No fixed verb list is needed to make progress.

## The world remembers: “That happened”

Move to another location, take or transfer a visible item, then return or ask
an NPC about the change.

- Location, exits, possession, and NPC availability remain consistent.
- The response does not claim that a new object, relationship, or revelation
  appeared unless the story first made that change explicit.
- If an item or clue has moved, it is not simultaneously described in its old
  place.

## Conversation: “I am talking to *them*”

Address a visible NPC by name and ask about something they could reasonably
know. Then ask about a protected detail they have not learned.

- The addressed NPC answers in character rather than the narrator summarizing
  for them.
- Their reply fits their role, location, and knowledge.
- They do not reveal hidden case/world truth merely because the player asked.

## Discovery: “A lead, not a spoiler”

Investigate one clue or environmental detail, then pursue an alternate lead or
route if one is available.

- Discovery is earned through what the character can perceive.
- The game preserves at least one fair route forward when a plausible route is
  missed, blocked, or handled imperfectly.
- Weather, lighting, traces, locks, and other conditions remain coherent when
  revisiting an adjacent scene.

## Consequences: “The scene reacts”

Make one physical, social, investigative, or technical intervention; wait or
take a follow-up action.

- The immediate outcome has a lasting, logical consequence.
- Tension or scene pressure can change, but the game does not seize control of
  the player’s approach.
- A major goal-breaking choice asks for `PROCEED` or `CANCEL` before carrying
  it out; `CANCEL` leaves the story intact.

## Durability: “Save the thread”

Save after a meaningful change, continue for one turn, then load the save.

- The restored scene, inventory, relationships, clues, and current objective
  match the moment of saving.
- Repeating the same next action produces a coherent continuation rather than
  contradictory history.

## Surface confidence: “The same story, appropriately delivered”

Try the opening and two ordinary turns on CLI/local web and hosted demo when
available.

- All surfaces support freeform story attempts and preserve the same canonical
  world behavior.
- Local and hosted presentation may use different model backends, but both are
  responsive, in-world, and fail safely: a temporary service problem is stated
  plainly without exposing credentials, stack traces, or internal prompts.

## Pass bar

Call the experience ready when a player can reach a coherent ending or a clear
next dramatic step in at least two different genres, with no hidden-information
leak, continuity break, parser-shaped refusal, or narration-only world change.
Record any failure with the command, what appeared on screen, and the last
known fact (location, item holder, NPC, clue, or goal) that the player could
verify.
