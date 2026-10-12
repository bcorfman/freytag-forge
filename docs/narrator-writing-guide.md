# Narrator writing guide

The narrator is a small, non-reasoning Llama-class model. Write every
instruction it receives in plain language so it can follow the rule.

- New instructions written after 2026-10-11 target a 12th-grade reading level;
  keep existing 8th-grade strings at their current level.
- Use short, common words (`thing` or `object`, not `entity`; `say who owns
  it`, not `attribute ownership`).
- Keep sentences short, with one idea each. Do not join two demands with `and`.
- Avoid project terms such as `authored`, `grounding`, `segment`, `candidate`,
  `convey`, `durable evidence`, and `container contents` unless a JSON field
  requires the exact term.
- Name the concrete thing the model must use instead of describing a category.

Apply each narrator-instruction change to every narration path: `_turn_rules`,
`opening()`, `_system_prompt`, `_section_user_prompt`, `_scene_setting`, and
`_recover_malformed_response`. Where paths share a rule, build it in one helper
and call that helper from each path.
