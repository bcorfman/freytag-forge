from __future__ import annotations

import re
from typing import TypedDict

from storygame.engine.parser import Action, ActionKind
from storygame.engine.state import GameState

_WORD_SPLIT = re.compile(r"[^a-z0-9]+")
_VIOLENCE_TERMS = {
    "kill",
    "murder",
    "shoot",
    "stab",
    "attack",
    "assault",
    "punch",
    "hit",
    "strangle",
    "poison",
    "burn",
    "bomb",
}
_SELF_HARM_TERMS = {
    "suicide",
    "selfharm",
    "self_harm",
    "jump",
    "drown",
    "overdose",
}
_CRIME_TERMS = {
    "steal",
    "rob",
    "arson",
    "vandalize",
    "graffiti",
    "spray",
    "trespass",
    "kidnap",
}
_AUTHORITY_TERMS = {"police", "officer", "deputy", "sheriff", "guard"}
_PUBLIC_SPACE_TERMS = {"school", "hospital", "church", "station", "sign", "statue"}
_IRREVERSIBLE_TERMS = {"explode", "ignite", "burn", "jump", "destroy"}
class ImpactAssessment(TypedDict):
    score: float
    impact_class: str
    dimensions: dict[str, float]
    reasons: list[str]
    consequences: list[str]


def _tokens(raw: str) -> set[str]:
    return {token for token in _WORD_SPLIT.split(raw.lower()) if token}


def _contains_phrase(raw: str, phrase: str) -> bool:
    return phrase in raw.lower()


def assess_player_command(state: GameState, raw: str, action: Action) -> ImpactAssessment:
    words = _tokens(raw)
    reasons: list[str] = []
    consequences: list[str] = []
    dimensions = {
        "safety": 0.0,
        "legal": 0.0,
        "social": 0.0,
        "goal_violation": 0.0,
        "irreversibility": 0.0,
        "timeline_disruption": 0.0,
    }
    lower_raw = raw.lower()

    violent = bool(words.intersection(_VIOLENCE_TERMS))
    self_harm = bool(words.intersection(_SELF_HARM_TERMS)) and (
        _contains_phrase(lower_raw, "jump down")
        or _contains_phrase(lower_raw, "jump into")
        or _contains_phrase(lower_raw, "kill myself")
        or _contains_phrase(lower_raw, "harm myself")
    )
    crime = bool(words.intersection(_CRIME_TERMS))
    authority_target = bool(words.intersection(_AUTHORITY_TERMS))
    public_space_target = bool(words.intersection(_PUBLIC_SPACE_TERMS))
    irreversible = bool(words.intersection(_IRREVERSIBLE_TERMS))

    if violent:
        dimensions["safety"] += 0.45
        dimensions["social"] += 0.2
        dimensions["timeline_disruption"] += 0.2
        reasons.append("violent_action")
        consequences.append("Violence will sharply escalate NPC and institutional responses.")
    if self_harm:
        dimensions["safety"] += 0.7
        dimensions["irreversibility"] += 0.45
        dimensions["timeline_disruption"] += 0.25
        reasons.append("self_harm_risk")
        consequences.append("This action can cause severe injury or death and alter available story paths.")
    if crime:
        dimensions["legal"] += 0.45
        dimensions["social"] += 0.25
        dimensions["timeline_disruption"] += 0.2
        reasons.append("criminal_behavior")
        consequences.append("Witnesses and authorities may react with investigations, hostility, or pursuit.")
    if authority_target:
        dimensions["legal"] += 0.35
        dimensions["social"] += 0.2
        dimensions["timeline_disruption"] += 0.35
        reasons.append("authority_target")
        consequences.append("Targeting authorities can trigger immediate law-enforcement escalation.")
    if public_space_target and crime:
        dimensions["legal"] += 0.15
        dimensions["social"] += 0.25
        reasons.append("public_disruption")
        consequences.append("Public misconduct can damage reputation and close off cooperative NPC routes.")
    if irreversible:
        dimensions["irreversibility"] += 0.35
        reasons.append("irreversible_risk")
        consequences.append("The consequences are difficult to undo once executed.")

    room_npcs = state.world.rooms[state.player.location].npc_ids
    if violent and any(npc_id in lower_raw for npc_id in room_npcs):
        dimensions["goal_violation"] += 0.4
        dimensions["timeline_disruption"] += 0.2
        reasons.append("violence_against_present_npc")
        consequences.append("Harming present characters can break active plan assumptions and force a replan.")

    if action.kind == ActionKind.USE and ("weapon" in words or "gun" in words):
        dimensions["safety"] += 0.2
        dimensions["legal"] += 0.15
        reasons.append("weapon_use_signal")

    score = sum(dimensions.values())
    if score >= 1.35:
        impact_class = "critical"
    elif score >= 0.7:
        impact_class = "high"
    elif score >= 0.35:
        impact_class = "moderate"
    else:
        impact_class = "low"
    if not consequences:
        consequences.append("No major disruption predicted.")
    return {
        "score": round(score, 4),
        "impact_class": impact_class,
        "dimensions": dimensions,
        "reasons": reasons,
        "consequences": consequences[:3],
    }


def requires_high_impact_confirmation(assessment: ImpactAssessment) -> bool:
    return replan_scope_for_assessment(assessment) == "goal_change"


def replan_scope_for_assessment(assessment: ImpactAssessment) -> str:
    reasons = set(assessment["reasons"])
    dimensions = assessment["dimensions"]
    impact_class = assessment["impact_class"]
    if impact_class == "critical":
        return "goal_change"
    if "self_harm_risk" in reasons or "violence_against_present_npc" in reasons:
        return "goal_change"
    if "authority_target" in reasons and dimensions.get("timeline_disruption", 0.0) >= 0.35:
        return "goal_change"
    if dimensions.get("goal_violation", 0.0) >= 0.35:
        return "goal_change"
    return "light"
