# Player input guide

Player input is what a person types at the game. Tests, probes, bench scripts,
and examples must use that voice. These strings are matched against world
entity names to recall knowledge and are sent to the narrator as the action to
answer.

- Write an imperative action, never first person: `Search the kitchen for signs
  of a struggle.`, not `I search the kitchen...`.
- Name the player's own things in first person (`my laptop`, `my pocket`), and
  use a plain article when ownership need not be said (`Go out to the truck.`).
- Describe an active move; remove any `do not`, `without`, or `avoid` restraint
  and keep the action that remains.
- Use a verb with a direct object: `Pursue the agent.`, `Park the truck.`, or
  `Listen to the recording.`
- Do not use non-events such as `Wait.`, `Keep watch.`, or `Think back to the
  memory card.`

Whether an action changes the world depends on its scene. `Listen.` is a move
when something is there to hear and it commits a fact; it is a non-event when
nothing happens. A Freytag beat or timed pacing event that would happen anyway
does not count as an effect, and narrative color that commits no fact does not
count either. Judge each input in its scene. To measure effects at scale,
compare a turn with a deliberate null control in `bench`, or ask the LLM judge.

## Supported player language is wider than probe style

The rules above are for probes, benches and examples: they keep tests in one
voice so results compare. They do not say what the game must accept. Real
players type polite requests, `I` forms, pronouns, corrections, commands with
several acts, and `listen` when something can be heard.

- The raw-language corpus (`tests/fixtures/raw_language_corpus.json`) records
  how the exact matcher treats that input today. Update it when the matcher
  changes. An entry that is a known gap says so in its note.
- The blind player has two profiles. `canonical` (the default) follows the
  rules above. `raw` (`BLIND_PLAYER_PROFILE=raw`) writes as a person types,
  and keeps the exact text beside what was sent. Compare profiles only on
  matched scene starts.
- Do not widen the matcher to make a raw entry pass. A phrasing the matcher
  misses gets an author-reviewed alias. Input that a person would have to
  clarify is labelled `clarification_needed`, not fixed.
- A bench or test still uses the canonical voice unless it is deliberately
  measuring raw language.
