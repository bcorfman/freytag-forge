from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from storygame.engine.facts import (
    active_story_goal,
    apply_fact_ops,
    beat_phase,
    beat_role,
    current_scene,
    player_approach,
    scene_pressure,
)
from storygame.engine.state import Event
from storygame.plot.dramatic_policy import infer_beat_role, pressure_bucket
from storygame.plot.freytag import get_phase

_PHASE_BEATS: dict[str, tuple[str, ...]] = {
    "exposition": ("hook", "inciting_incident", "goal_reveal"),
    "rising_action": ("complication", "revelation", "escalation", "setback"),
    "climax": ("confrontation", "irreversible_choice"),
    "falling_action": ("consequence", "escape", "unraveling"),
    "resolution": ("closure", "epilogue"),
}

_ROLE_BEATS: dict[str, tuple[str, ...]] = {
    "orientation": ("hook", "inciting_incident", "goal_reveal"),
    "pressure": ("complication", "escalation", "setback"),
    "reveal": ("revelation", "goal_reveal"),
    "confrontation": ("confrontation", "irreversible_choice"),
    "aftermath": ("consequence", "escape", "unraveling"),
    "closure": ("closure", "epilogue"),
}


@dataclass(frozen=True)
class BeatPolicyInput:
    phase: str
    beat_role: str
    scene_pressure: str
    obstacle_mode: str
    active_conflict: str
    reveal_opportunity: str
    reveal_budget: int
    npc_scene_goals: tuple[str, ...]
    active_goal: str
    player_approach: str
    recent_beats: tuple[str, ...]


@dataclass(frozen=True)
class BeatDecision:
    beat: str
    phase: str
    beat_role: str
    scene_pressure: str
    active_conflict: str
    reveal_opportunity: str
    reveal_budget: int
    npc_scene_goals: tuple[str, ...]
    legal_beats: tuple[str, ...]
    consequence_classes: tuple[str, ...]
    selection_reason: str


def _first_fact(state: Any, predicate: str, *pattern: str | None) -> str:
    facts = state.world_facts.query(predicate, *pattern)
    return facts[0][-1] if facts else ""


def _policy_input(state: Any) -> BeatPolicyInput:
    scene_id = current_scene(state)
    phase = beat_phase(state) or get_phase(state.progress)
    approach = player_approach(state) or "observe"
    pressure = scene_pressure(state, scene_id) or pressure_bucket(state.tension)
    role = beat_role(state, scene_id) or infer_beat_role(phase, approach, pressure)
    goals = tuple(fact[2] for fact in state.world_facts.query("npc_scene_goal", None, None))
    return BeatPolicyInput(
        phase=phase,
        beat_role=role,
        scene_pressure=pressure,
        obstacle_mode=_first_fact(state, "obstacle_mode", scene_id, None),
        active_conflict=_first_fact(state, "active_conflict", scene_id, None),
        reveal_opportunity=_first_fact(state, "reveal_opportunity", scene_id, None),
        reveal_budget=int(_first_fact(state, "reveal_budget", scene_id, None) or 0),
        npc_scene_goals=goals,
        active_goal=active_story_goal(state) or state.active_goal,
        player_approach=approach,
        recent_beats=state.beat_history,
    )


def build_beat_policy_input(state: Any) -> BeatPolicyInput:
    return _policy_input(state)


class BeatPolicy:
    """Pure dramatic policy; it selects only legal presentation/consequence classes."""

    def decide(self, state: Any, *, turn_index: int | None = None) -> BeatDecision:
        inputs = _policy_input(state)
        candidates = _PHASE_BEATS.get(inputs.phase, _PHASE_BEATS["exposition"])
        preferred = tuple(beat for beat in _ROLE_BEATS.get(inputs.beat_role, ()) if beat in candidates)
        legal = preferred or candidates
        if inputs.active_conflict and inputs.phase == "climax":
            legal = tuple(beat for beat in legal if beat in {"confrontation", "irreversible_choice"}) or legal
        if len(inputs.recent_beats) > 0:
            without_last = tuple(beat for beat in legal if beat != inputs.recent_beats[-1])
            legal = without_last or legal
        index_key = "|".join(
            (
                str(state.seed),
                str(state.turn_index if turn_index is None else turn_index),
                inputs.phase,
                inputs.beat_role,
                inputs.scene_pressure,
                inputs.player_approach,
                inputs.active_conflict,
                ",".join(inputs.recent_beats[-2:]),
            )
        )
        index = int.from_bytes(hashlib.sha256(index_key.encode()).digest()[:8], "big") % len(legal)
        beat = legal[index]
        consequence_classes = {
            "exposition": ("orientation", "access"),
            "rising_action": ("obstacle", "discovery", "relationship"),
            "climax": ("confrontation", "irreversible_change"),
            "falling_action": ("repercussion", "escape"),
            "resolution": ("closure", "relationship"),
        }[inputs.phase]
        return BeatDecision(
            beat=beat,
            phase=inputs.phase,
            beat_role=inputs.beat_role,
            scene_pressure=inputs.scene_pressure,
            active_conflict=inputs.active_conflict,
            reveal_opportunity=inputs.reveal_opportunity,
            reveal_budget=inputs.reveal_budget,
            npc_scene_goals=inputs.npc_scene_goals,
            legal_beats=tuple(legal),
            consequence_classes=consequence_classes,
            selection_reason=f"{inputs.phase}/{inputs.beat_role}/{inputs.scene_pressure}",
        )

    def progression_events(self, state: Any) -> list[Event]:
        """Materialize eligible fact-backed reveals and timed events once."""
        plan: dict[str, Any] = {
            "hidden_threads": tuple(
                fact[1] for fact in state.world_facts.query("story_hidden_thread", None)
            ),
            "reveal_schedule": tuple(
                {"thread_index": int(fact[1]), "min_progress": float(fact[2])}
                for fact in state.world_facts.query("story_reveal_schedule", None, None)
            ),
            "timed_events": tuple(
                {
                    "event_id": fact[1],
                    "summary": fact[2],
                    "min_turn": int(fact[3]),
                    "participants": tuple(
                        participant[2]
                        for participant in state.world_facts.query("planned_event_participant", fact[1], None)
                    ),
                }
                for fact in state.world_facts.query("planned_event", None, None, None, None)
            ),
        }
        if not any(plan.values()):
            plan = dict(state.world_package.get("story_plan", {}))
        events: list[Event] = []
        hidden_threads = tuple(str(thread).strip() for thread in plan.get("hidden_threads", ()) if str(thread).strip())
        for entry in tuple(plan.get("reveal_schedule", ())):
            if not isinstance(entry, dict):
                continue
            index = int(entry.get("thread_index", -1))
            threshold = float(entry.get("min_progress", 1.0))
            flag = f"story_reveal_{index}"
            if index < 0 or index >= len(hidden_threads) or state.progress < threshold or state.player.flags.get(flag):
                continue
            apply_fact_ops(state, [{"op": "assert", "fact": ("flag", "player", flag)}])
            events.append(Event(
                type="story_reveal", message_key=f"New lead: {hidden_threads[index]}",
                entities=(f"thread_{index}",), tags=("story_reveal",),
                turn_index=state.turn_index, delta_tension=0.02,
            ))
        for entry in tuple(plan.get("timed_events", ())):
            if not isinstance(entry, dict):
                continue
            event_id = str(entry.get("event_id", "")).strip()
            summary = str(entry.get("summary", "")).strip()
            flag = f"timed_story_event_{event_id}"
            if not event_id or not summary or state.turn_index < int(entry.get("min_turn", 9999)):
                continue
            if state.player.flags.get(flag):
                continue
            apply_fact_ops(state, [{"op": "assert", "fact": ("flag", "player", flag)}])
            participants = entry.get("participants", ())
            if not isinstance(participants, (tuple, list)):
                participants = ()
            events.append(Event(
                type="timed_story_event", message_key=summary,
                entities=tuple(str(name).strip() for name in participants if str(name).strip()),
                tags=("story", "timed_event"), turn_index=state.turn_index, delta_tension=0.03,
            ))
        return events
