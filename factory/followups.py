"""Open deterministic tickets from station 8 routing results."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from factory.tickets import Station, Status, Ticket, TicketClass, TicketQueue

FOLLOWUP_STATIONS: dict[TicketClass, Station | None] = {
    TicketClass.STORY_DATA: Station.WIRING,
    TicketClass.NARRATOR_PROMPT: Station.WIRING,
    TicketClass.WORLD_MODEL: Station.WORLD_NEED,
    TicketClass.ENGINE: None,
}
_SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]")
_REQUIRED_ROUTING_KEYS = frozenset({"routed", "escalations", "turns"})


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _safe_id(value: str) -> str:
    return _SAFE_ID.sub("_", value)


def _ticket_class(value: object) -> TicketClass | None:
    try:
        return TicketClass(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _routing_parts(routing: dict) -> tuple[list[dict], list[dict], list[dict]] | None:
    if not isinstance(routing, dict) or not _REQUIRED_ROUTING_KEYS.issubset(routing):
        return None
    routed = routing["routed"]
    escalations = routing["escalations"]
    turns = routing["turns"]
    if not all(isinstance(value, list) for value in (routed, escalations, turns)):
        return None
    if any(not isinstance(packet, dict) for packet in turns):
        return None
    return routed, escalations, turns


def _existing(queue: TicketQueue, ticket_id: str) -> bool:
    try:
        queue.get(ticket_id)
    except KeyError:
        return False
    return True


def _packet_index(turns: list[dict]) -> dict[str, dict]:
    return {packet["key"]: packet for packet in turns if isinstance(packet.get("key"), str)}


def _new_ticket(
    *,
    ticket_id: str,
    scene: str,
    ticket_class: TicketClass,
    station: Station,
    token_budget: int,
    timestamp: str,
    payload: dict[str, Any],
    status: Status = Status.QUEUED,
) -> Ticket:
    return Ticket(
        id=ticket_id,
        scene=scene,
        station=station,
        token_budget=token_budget,
        created_at=timestamp,
        updated_at=timestamp,
        status=status,
        ticket_class=ticket_class,
        payload=payload,
    )


def open_followups(queue: TicketQueue, parent: Ticket, routing: dict, now: datetime) -> list[Ticket]:
    """Create idempotent class follow-ups and escalation tickets from triage routing."""

    parts = _routing_parts(routing)
    if parts is None:
        return []
    routed, escalation_entries, turns = parts
    timestamp = _utc_iso(now)
    packets = _packet_index(turns)
    opened: list[Ticket] = []

    valid_escalations: list[dict[str, Any]] = []
    escalation_scenes: set[str] = set()
    for entry in escalation_entries:
        if not isinstance(entry, dict):
            continue
        scene = entry.get("scene")
        class_name = _ticket_class(entry.get("class"))
        keys = entry.get("keys")
        count = entry.get("count")
        if not isinstance(scene, str) or class_name is None or not isinstance(count, int) or not isinstance(keys, list):
            continue
        if any(not isinstance(key, str) for key in keys):
            continue
        valid_escalations.append({"scene": scene, "class": class_name, "count": count, "keys": keys})
        escalation_scenes.add(scene)

    for entry in valid_escalations:
        scene = entry["scene"]
        ticket_class = entry["class"]
        ticket_id = _safe_id(f"{parent.id}-{scene}-{ticket_class.value}-escalation")
        if _existing(queue, ticket_id):
            continue
        payload = {
            "parent": parent.id,
            "scene": scene,
            "class": ticket_class.value,
            "count": entry["count"],
            "keys": entry["keys"],
            "failing_turns": [packet for packet in turns if packet.get("key") in set(entry["keys"])],
            "reason": "three failures of one class in one scene",
        }
        ticket = _new_ticket(
            ticket_id=ticket_id,
            scene=scene,
            ticket_class=ticket_class,
            station=Station.CONTRACT_REFRESH,
            token_budget=parent.token_budget,
            timestamp=timestamp,
            payload=payload,
        )
        queue.add(ticket)
        opened.append(ticket)

    groups: dict[tuple[str, TicketClass], dict[str, Any]] = {}
    for entry in routed:
        if not isinstance(entry, dict):
            continue
        scene = entry.get("scene")
        key = entry.get("key")
        ticket_class = _ticket_class(entry.get("class"))
        rule = entry.get("rule")
        if not all(isinstance(value, str) for value in (scene, key, rule)) or ticket_class is None:
            continue
        if ticket_class.value == "unclear" or key not in packets:
            continue
        group = groups.setdefault((scene, ticket_class), {"turns": [], "rules": {}})
        group["turns"].append(packets[key])
        group["rules"][key] = rule

    for (scene, ticket_class), group in groups.items():
        if scene in escalation_scenes and ticket_class in {TicketClass.STORY_DATA, TicketClass.NARRATOR_PROMPT}:
            continue
        station = FOLLOWUP_STATIONS[ticket_class]
        status = Status.QUEUED
        payload = {
            "parent": parent.id,
            "class": ticket_class.value,
            "failing_turns": group["turns"],
            "rules": group["rules"],
        }
        if station is None:
            station = Station.CONTRACT_REFRESH
            status = Status.FAILED
            payload["needs"] = "engine_plan"
        ticket_id = _safe_id(f"{parent.id}-{scene}-{ticket_class.value}")
        if _existing(queue, ticket_id):
            continue
        ticket = _new_ticket(
            ticket_id=ticket_id,
            scene=scene,
            ticket_class=ticket_class,
            station=station,
            token_budget=parent.token_budget,
            timestamp=timestamp,
            payload=payload,
            status=status,
        )
        queue.add(ticket)
        opened.append(ticket)

    return opened
