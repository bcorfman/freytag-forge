from __future__ import annotations

from dataclasses import dataclass

from storygame.engine.facts import apply_fact_ops
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
            message_key="A forged resonance tone threads through the district toward the tower.",
            tags=("goal_reveal",),
            delta_progress=0.05,
            delta_tension=0.02,
            set_flags=("goal_revealed",),
        ),
        EventTemplate(
            key="blocked_memories",
            message_key="A saboteur jams the stair gears, forcing a slower climb.",
            tags=("complication",),
            delta_tension=0.03,
            set_flags=("stair_jammed",),
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
            message_key="The broken frame howls as the hidden resonator spikes toward overload.",
            tags=("climax", "confrontation"),
            delta_progress=0.04,
            delta_tension=0.15,
            set_flags=("climax_started",),
        ),
        EventTemplate(
            key="irreversible_choice",
            message_key="You must expose the transmitter now or lose the conspiracy trail for good.",
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
            message_key="The conflict resolves, and the district settles into clear silence.",
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


def _ambient_source_phrase(state: GameState) -> str:
    room_id = state.player.location
    sources = state.world_facts.query("ambient_source", room_id, None)
    if sources:
        return sources[0][2]
    for adjacent_room_id in state.world.rooms[room_id].exits.values():
        sources = state.world_facts.query("ambient_source", adjacent_room_id, None)
        if sources:
            return sources[0][2]
    return "outside"


def _current_room_is_outdoors(state: GameState) -> bool:
    return state.world_facts.holds("room_exposure", state.player.location, "outdoor")


def _event_message_for_state(template: EventTemplate, state: GameState) -> str:
    if template.key == "cold_wind":
        source_phrase = _ambient_source_phrase(state)
        if _current_room_is_outdoors(state):
            if source_phrase == "outside":
                return "A cold wind cuts through the open air."
            return f"A cold wind runs along {source_phrase}."
        if source_phrase == "outside":
            return "A cold draft slips in from outside."
        return f"A cold draft slips in from {source_phrase}."
    return template.message_key


def apply_event_template(
    state: GameState,
    template: EventTemplate,
    rng,
) -> tuple[GameState, list[Event]]:
    next_state = state.clone()
    fact_ops = [
        {"op": "assert", "fact": ("flag", "player", flag)}
        for flag in template.set_flags
    ] + [
        {"op": "retract", "fact": ("flag", "player", flag)}
        for flag in template.clear_flags
    ]
    if fact_ops:
        apply_fact_ops(next_state, fact_ops)

    event = Event(
        type="plot",
        message_key=_event_message_for_state(template, next_state),
        entities=(template.key,),
        tags=(template.key, *template.tags),
        delta_progress=template.delta_progress,
        delta_tension=template.delta_tension,
        turn_index=next_state.turn_index,
        metadata={"fact_ops": fact_ops, "source": "event_template"},
    )
    next_state.append_event(event)
    return next_state, [event]
