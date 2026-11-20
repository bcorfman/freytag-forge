"""Deterministically route failed live-playtest turns to ticket classes."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from factory.line import StationHandler, StationResult
from factory.tickets import TicketClass

WORLD_FLAGS = frozenset(
    {
        "facts_after_wrong",
        "missed_change",
        "invented_change",
        "dropped_true_condition",
        "kept_ended_condition",
        "state_as_place",
    }
)
NARRATOR_FLAGS = frozenset(
    {
        "narration_contradicts_given_facts",
        "contradicts_stated_fact",
        "restarts_scene",
        "command_not_finished",
        "reveals_hidden_canon",
    }
)
RULE_ORDER = ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9")
TICKET_CLASSES = frozenset(ticket_class.value for ticket_class in TicketClass)

_DEFAULTS: dict[str, Any] = {
    "player_input": "",
    "narration": "",
    "stuck": False,
    "candidates_offered": [],
    "matched_candidate": None,
    "committed": None,
    "engine_error": None,
    "match_issues": [],
    "item_facts_issues": [],
    "item_facts_unplaced": [],
    "flags": [],
}
_LIST_FIELDS = {
    "candidates_offered",
    "match_issues",
    "item_facts_issues",
    "item_facts_unplaced",
    "flags",
}
_STRING_OR_NONE_FIELDS = {"matched_candidate", "engine_error"}


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _validation_error(field: str, message: str) -> ValueError:
    return ValueError(f"packet field {field} {message}")


def _validate_packet(packet: dict) -> dict[str, Any]:
    if not isinstance(packet, dict):
        raise ValueError("packet must be a dict")
    for field in ("key", "scene"):
        if field not in packet:
            raise ValueError(f"missing packet field: {field}")
        if not isinstance(packet[field], str):
            raise _validation_error(field, "must be a string")

    checked = {"key": packet["key"], "scene": packet["scene"]}
    for field, default in _DEFAULTS.items():
        value = packet.get(field, default)
        if field in _LIST_FIELDS:
            if not isinstance(value, list):
                raise _validation_error(field, "must be a list")
            if any(not isinstance(item, str) for item in value):
                raise _validation_error(field, "must contain only strings")
        elif field in _STRING_OR_NONE_FIELDS:
            if value is not None and not isinstance(value, str):
                raise _validation_error(field, "must be a string or null")
        elif field == "stuck":
            if not isinstance(value, bool):
                raise _validation_error(field, "must be a bool")
        elif field == "committed":
            if value is not None and not isinstance(value, bool):
                raise _validation_error(field, "must be a bool or null")
        elif not isinstance(value, str):
            raise _validation_error(field, "must be a string")
        checked[field] = list(value) if field in _LIST_FIELDS else value
    return checked


def _routed(packet: dict[str, Any], class_name: str, rule: str, reasons: list[str]) -> dict[str, Any]:
    return {
        "key": packet["key"],
        "scene": packet["scene"],
        "class": class_name,
        "rule": rule,
        "reasons": reasons,
    }


def _classify(packet: dict[str, Any]) -> dict[str, Any]:
    engine_error = packet["engine_error"]
    if engine_error:
        return _routed(packet, TicketClass.ENGINE.value, "R1", ["engine_error is non-empty"])

    if packet["stuck"] and not packet["candidates_offered"]:
        return _routed(packet, TicketClass.STORY_DATA.value, "R2", ["stuck with no candidates_offered"])

    if packet["stuck"] and packet["candidates_offered"] and packet["matched_candidate"] is None:
        if not packet["match_issues"]:
            return _routed(
                packet,
                TicketClass.STORY_DATA.value,
                "R3",
                ["stuck with candidates_offered and no matched_candidate", "no match_issues"],
            )
        return _routed(packet, TicketClass.NARRATOR_PROMPT.value, "R4", ["match_issues is non-empty"])

    if packet["stuck"] and packet["matched_candidate"] is not None and packet["committed"] is False:
        return _routed(packet, TicketClass.ENGINE.value, "R5", ["matched_candidate did not commit"])

    if packet["stuck"]:
        return _routed(packet, "unclear", "R6", ["stuck combination has no deterministic route"])

    world_signals = []
    if packet["item_facts_issues"]:
        world_signals.append("item_facts_issues")
    if packet["item_facts_unplaced"]:
        world_signals.append("item_facts_unplaced")
    world_signals.extend(f"flag:{flag}" for flag in packet["flags"] if flag in WORLD_FLAGS)
    narrator_signals = [f"flag:{flag}" for flag in packet["flags"] if flag in NARRATOR_FLAGS]
    unknown_flags = [flag for flag in packet["flags"] if flag not in WORLD_FLAGS and flag not in NARRATOR_FLAGS]

    reasons: list[str] = []
    if world_signals and narrator_signals:
        reasons.append("conflicting world_model and narrator_prompt signals")
    elif not world_signals and not narrator_signals:
        reasons.append("no world_model or narrator_prompt signal")
    if unknown_flags:
        reasons.extend(f"unknown flag: {flag}" for flag in unknown_flags)
    if reasons:
        return _routed(packet, "unclear", "R9", reasons)
    if world_signals:
        return _routed(packet, TicketClass.WORLD_MODEL.value, "R7", world_signals)
    return _routed(packet, TicketClass.NARRATOR_PROMPT.value, "R8", narrator_signals)


def classify_turn(packet: dict) -> dict:
    """Classify one validated failing-turn packet."""

    return _classify(_validate_packet(packet))


def _malformed_routed(packet: object, error: ValueError) -> dict[str, Any]:
    if isinstance(packet, dict):
        key = packet.get("key", "") if isinstance(packet.get("key", ""), str) else ""
        scene = packet.get("scene", "") if isinstance(packet.get("scene", ""), str) else ""
    else:
        key = scene = ""
    return {"key": key, "scene": scene, "class": "unclear", "rule": "R9", "reasons": [str(error)]}


def classify_turns(packets: list[dict]) -> list[dict]:
    """Classify packets in order, retaining malformed packets as unclear."""

    routed = []
    for packet in packets:
        try:
            routed.append(classify_turn(packet))
        except ValueError as error:
            routed.append(_malformed_routed(packet, error))
    return routed


def _safe_packet_fields(packet: object, routed: dict[str, Any], max_narration: int) -> dict[str, Any]:
    raw = packet if isinstance(packet, dict) else {}
    result: dict[str, Any] = {
        "key": routed.get("key", ""),
        "scene": routed.get("scene", ""),
        "player_input": raw.get("player_input", "") if isinstance(raw.get("player_input", ""), str) else "",
        "narration": raw.get("narration", "") if isinstance(raw.get("narration", ""), str) else "",
    }
    for field, default in _DEFAULTS.items():
        value = raw.get(field, default)
        if field in _LIST_FIELDS:
            result[field] = [item for item in value if isinstance(item, str)] if isinstance(value, list) else []
        elif field == "stuck":
            result[field] = value if isinstance(value, bool) else False
        elif field in _STRING_OR_NONE_FIELDS:
            result[field] = value if value is None or isinstance(value, str) else None
        elif field == "committed":
            result[field] = value if value is None or isinstance(value, bool) else None
    result["narration"] = result["narration"][:max_narration]
    result["reasons"] = list(routed.get("reasons", []))
    return result


def unclear_packet(
    packets: list[dict],
    routed: list[dict],
    *,
    max_turns: int = 20,
    max_narration: int = 600,
) -> list[dict]:
    """Reduce unclear turns to the bounded resolver contract."""

    result: list[dict] = []
    limit = max(0, max_turns)
    narration_limit = max(0, max_narration)
    by_key = {item["key"]: item for item in packets if isinstance(item, dict) and isinstance(item.get("key"), str)}
    for index, route_result in enumerate(routed):
        if len(result) >= limit or route_result.get("class") != "unclear":
            continue
        packet = by_key.get(route_result.get("key"), packets[index] if index < len(packets) else {})
        reduced = _safe_packet_fields(packet, route_result, narration_limit)
        result.append(reduced)
    return result


def _resolved_class(value: object) -> str | None:
    if isinstance(value, TicketClass):
        value = value.value
    return value if isinstance(value, str) and value in TICKET_CLASSES else None


def route(
    packets: list[dict],
    *,
    resolver: Callable[[list[dict]], dict[str, str]] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Classify turns and optionally apply a bounded resolver to unclear turns."""

    routed = classify_turns(packets)
    unclear = [item for item in routed if item["class"] == "unclear"]
    if resolver is not None and unclear:
        try:
            proposals = resolver(unclear_packet(packets, routed))
        except Exception:
            proposals = {}
        if isinstance(proposals, dict):
            for item in unclear:
                proposed = _resolved_class(proposals.get(item["key"]))
                if proposed is not None:
                    item["class"] = proposed
                    item["rule"] = "RM"
                    item["reasons"] = ["resolved by model"]
    return routed, [item for item in routed if item["class"] == "unclear"]


def escalations(log: list[dict], routed: list[dict], *, threshold: int = 3) -> list[dict]:
    """Find scene/class pairs with enough distinct failed turn keys."""

    grouped: dict[tuple[str, str], set[str]] = {}
    for entry in [*log, *routed]:
        if not isinstance(entry, dict):
            continue
        key = entry.get("key")
        scene = entry.get("scene")
        class_name = entry.get("class")
        if not all(isinstance(value, str) for value in (key, scene, class_name)) or class_name == "unclear":
            continue
        grouped.setdefault((scene, class_name), set()).add(key)
    return [
        {"scene": scene, "class": class_name, "count": len(keys), "keys": sorted(keys)}
        for (scene, class_name), keys in sorted(grouped.items())
        if len(keys) >= threshold
    ]


def read_log(path: Path) -> list[dict]:
    """Read valid JSONL log entries, tolerating missing or corrupt files."""

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    except OSError:
        return []
    entries = []
    for line in lines:
        try:
            value = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, dict):
            entries.append(value)
    return entries


def append_log(path: Path, routed: list[dict], ticket_id: str, now: datetime) -> None:
    """Append routed, non-unclear entries without duplicating key/class pairs."""

    path.parent.mkdir(parents=True, exist_ok=True)
    existing = {(entry.get("key"), entry.get("class")) for entry in read_log(path) if isinstance(entry, dict)}
    with path.open("a", encoding="utf-8") as handle:
        for item in routed:
            key = item.get("key")
            class_name = item.get("class")
            if class_name == "unclear" or not isinstance(key, str) or not isinstance(class_name, str):
                continue
            identity = (key, class_name)
            if identity in existing:
                continue
            entry = {
                "key": key,
                "scene": item.get("scene", ""),
                "class": class_name,
                "rule": item.get("rule", ""),
                "ticket": ticket_id,
                "at": now.isoformat(),
            }
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            existing.add(identity)


def _resolve_path(root: Path, value: object, field: str) -> Path:
    if not isinstance(value, (str, Path)):
        raise ValueError(f"{field} must be a path")
    path = Path(value)
    return path if path.is_absolute() else root / path


def _load_turns(root: Path, value: object) -> list[dict]:
    if isinstance(value, list):
        return value
    path = _resolve_path(root, value, "turns")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read turns file: {error}") from error
    if not isinstance(payload, list):
        raise ValueError("turns file must contain a list")
    return payload


def _summary(routed: list[dict], escalation_list: list[dict]) -> str:
    lines = [f"{item['key']} {item['class']} {item['rule']}" for item in routed]
    lines.extend(f"escalate {item['scene']} {item['class']} {item['count']}" for item in escalation_list)
    full = "\n".join(lines)
    if len(full) <= 4000:
        return full
    for shown in range(len(lines), -1, -1):
        cut = len(lines) - shown
        note = f"... {cut} lines cut"
        prefix = "\n".join(lines[:shown])
        candidate = f"{prefix}\n{note}" if prefix else note
        if len(candidate) <= 4000:
            return candidate
    return "... all lines cut"


def triage_handler(
    root: Path | None = None,
    resolver: Callable[[list[dict]], dict[str, str]] | None = None,
) -> StationHandler:
    """Return the deterministic station 8 handler."""

    repository_root = Path(root) if root is not None else _repository_root()

    def handle(ticket, now: datetime) -> StationResult:
        payload = getattr(ticket, "payload", None)
        if not isinstance(payload, dict) or "turns" not in payload:
            return StationResult(False, "triage", "missing payload key: turns")
        try:
            turns = _load_turns(repository_root, payload["turns"])
        except ValueError as error:
            return StationResult(False, "triage", str(error))
        if not turns:
            return StationResult(False, "triage", "turns must not be empty")

        routed, still_unclear = route(turns, resolver=resolver)
        escalation_list: list[dict] = []
        try:
            log_value = payload.get("log_path")
            if log_value is not None:
                log_path = _resolve_path(repository_root, log_value, "log_path")
                append_log(log_path, routed, str(getattr(ticket, "id", "")), now)
                escalation_list = escalations(read_log(log_path), routed)
            out_value = payload.get("out_path")
            summary_payload = {"routed": routed, "unclear": still_unclear, "escalations": escalation_list}
            if out_value is not None:
                out_path = _resolve_path(repository_root, out_value, "out_path")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(json.dumps(summary_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except (OSError, TypeError, ValueError) as error:
            return StationResult(False, "triage", str(error))

        if still_unclear:
            keys = ", ".join(str(item["key"]) for item in still_unclear)
            return StationResult(False, "triage", f"model resolver is needed for unclear turns: {keys}")
        return StationResult(True, "triage", _summary(routed, escalation_list), tokens=0)

    return handle


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--turns", required=True, metavar="FILE")
    parser.add_argument("--log", metavar="FILE")
    parser.add_argument("--out", metavar="FILE")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run station 8 from a JSON turns file."""

    options = _parser().parse_args(argv)
    root = _repository_root()
    try:
        _load_turns(root, options.turns)
    except ValueError as error:
        print(error)
        return 2
    payload = {"turns": options.turns}
    if options.log is not None:
        payload["log_path"] = options.log
    if options.out is not None:
        payload["out_path"] = options.out
    ticket = SimpleNamespace(id="cli", payload=payload)
    result = triage_handler(root)(ticket, datetime.now(UTC))
    print(result.output)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
