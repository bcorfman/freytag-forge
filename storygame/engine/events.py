from __future__ import annotations

from dataclasses import dataclass

from storygame.engine.state import Event, GameState
from storygame.plot.beat_manager import Beat


@dataclass(frozen=True)
class EventTemplate:
    key: str
    message_key: str
    tags: tuple[str, ...]
    delta_progress: float = 0.0
    delta_tension: float = 0.0
    set_flags: tuple[str, ...] = ()
    clear_flags: tuple[str, ...] = ()


def list_event_templates() -> tuple[EventTemplate, ...]:
    return (
        EventTemplate(
            key="cold_wind",
            message_key="A cold wind enters from the streets.",
            tags=("hook", "inciting_incident"),
            delta_tension=0.05,
        ),
        EventTemplate(
            key="street_whispers",
            message_key="Whispers of unrest spread among the crowd.",
            tags=("inciting_incident",),
            delta_tension=0.08,
        ),
        EventTemplate(
            key="objective_call",
            message_key="The old bell call can be traced to the tower.",
            tags=("goal_reveal",),
            delta_progress=0.05,
            delta_tension=0.02,
            set_flags=("goal_revealed",),
        ),
        EventTemplate(
            key="blocked_memories",
            message_key="A memory trap causes a pause in your resolve.",
            tags=("complication",),
            delta_tension=-0.02,
            set_flags=("memories_shaken",),
        ),
        EventTemplate(
            key="cryptic_revelation",
            message_key="A torn map reveals a hidden corridor in the inner archive.",
            tags=("revelation", "goal_reveal"),
            delta_progress=0.03,
            delta_tension=0.04,
            set_flags=("hidden_corridor",),
        ),
        EventTemplate(
            key="pressure_rising",
            message_key="The city tightens, as if holding its breath.",
            tags=("escalation",),
            delta_tension=0.06,
        ),
        EventTemplate(
            key="minor_setback",
            message_key="A lamp goes dark and the room grows quieter.",
            tags=("setback",),
            delta_tension=-0.04,
        ),
        EventTemplate(
            key="storm_warning",
            message_key="A warning bell clangs from somewhere in the sanctuary.",
            tags=("climax", "confrontation"),
            delta_progress=0.04,
            delta_tension=0.15,
            set_flags=("climax_started",),
        ),
        EventTemplate(
            key="irreversible_choice",
            message_key="A choice appears: advance the bell or retreat from the tower.",
            tags=("climax", "irreversible_choice"),
            delta_progress=0.04,
            delta_tension=0.12,
            set_flags=("choice_offered",),
        ),
        EventTemplate(
            key="echoed_repercussion",
            message_key="Consequences of your move ripple across the district.",
            tags=("consequence",),
            delta_tension=-0.03,
            delta_progress=0.06,
        ),
        EventTemplate(
            key="distant_closure",
            message_key="Distant doors open and the objective concludes.",
            tags=("closure",),
            delta_progress=0.07,
            delta_tension=-0.03,
            set_flags=("near_resolution",),
        ),
        EventTemplate(
            key="final_coda",
            message_key="The bell speaks softly, and the story reaches still water.",
            tags=("epilogue",),
            delta_progress=0.08,
            delta_tension=-0.06,
            set_flags=("finished",),
        ),
    )


def select_event(beat: Beat, state: GameState, rng) -> EventTemplate:
    templates = tuple(template for template in list_event_templates() if set(template.tags) & set(beat.tags))
    if not templates:
        templates = list_event_templates()
    index = rng.randrange(len(templates))
    return templates[index]


def apply_event_template(
    state: GameState,
    template: EventTemplate,
    rng,
) -> tuple[GameState, list[Event]]:
    next_state = state.clone()

    for flag in template.set_flags:
        next_state.player.flags[flag] = True
    for flag in template.clear_flags:
        next_state.player.flags[flag] = False

    event = Event(
        type="plot",
        message_key=template.message_key,
        entities=(template.key,),
        tags=(template.key, *template.tags),
        delta_progress=template.delta_progress,
        delta_tension=template.delta_tension,
        turn_index=next_state.turn_index,
    )
    next_state.append_event(event)
    return next_state, [event]
