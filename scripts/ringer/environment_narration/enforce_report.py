"""Report blind labels and enforcement gates for an enforced observation run.

Label guidance: ``command_opens`` is true when command text opens the container,
pulls it open or out, or searches it.

It is also true when the command says inside, in, into or through it.
"""

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path
from typing import Any

REFIND_COMMAND = "feel under the drawer"
SEAT_COMMAND = "inspect the passenger seat"
CARD_THING = "memory_card"
PLAYER_THING = "kristin"
SHUFFLE_SEED = 917263
TAG_NAMES = ("refind", "invented_object", "leak", "wrong_custody", "unrequested_move")
LOOK_GROUP_COMMANDS = ("inspect the drawer", "examine the drawer", "check the drawer")
NUDGE_GROUP_COMMANDS = (*LOOK_GROUP_COMMANDS, "search the drawer")
SEARCH_COMMAND = "search the drawer"
LOOK_INSIDE_COMMAND = "look inside the drawer"
LOOK_UNDER_COMMAND = "look under the drawer"
FEEL_UNDER_COMMAND = "feel under the drawer"
NUDGE_HANDOFF_ID = "k_sl_1a_f_r2"


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _turn_id(replicate_index: int, turn_index: int) -> str:
    return f"r{replicate_index}t{turn_index}"


def _turns(rows: list[dict[str, Any]]):
    for replicate_index, replicate in enumerate(rows):
        for turn_index, turn in enumerate(replicate.get("turns", ())):
            yield _turn_id(replicate_index, turn_index), turn


def _route(replicate: dict[str, Any]) -> str | None:
    value = replicate.get("route")
    return value if isinstance(value, str) else None


def _request_kind(turn: dict[str, Any]) -> str | None:
    request = turn.get("observation_request")
    if not isinstance(request, dict) or not isinstance(request.get("kind"), str):
        return None
    return request["kind"]


def _scope_rows(rows: list[dict[str, Any]]) -> bool:
    return any(
        "route" in replicate or any("observation_request" in turn for turn in replicate.get("turns", ()))
        for replicate in rows
    )


def _card_prose_turns(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for replicate_index, replicate in enumerate(rows):
        for turn_index, turn in enumerate(replicate.get("turns", ())):
            if _route(replicate) == "observe_under_first" and turn_index > 1:
                break
            is_route_c = _route(replicate) == "observe_look_inside_under"
            if is_route_c and _normalise_command(turn.get("input")) != LOOK_UNDER_COMMAND:
                continue
            if _route(replicate) not in ("observe_under_first", "observe_look_inside_under"):
                continue
            before = turn.get("places_before")
            after = turn.get("places_after")
            before_place = before.get(CARD_THING) if isinstance(before, dict) else None
            after_place = after.get(CARD_THING) if isinstance(after, dict) else None
            if after_place == PLAYER_THING and before_place != PLAYER_THING:
                turn_id = _turn_id(replicate_index, turn_index)
                result[turn_id] = turn
                break
    return result


def _attempts(turn: dict[str, Any]) -> list[dict[str, Any]]:
    attempts = turn.get("enforce_attempts")
    return attempts if isinstance(attempts, list) else []


def _narration_attempts(turn: dict[str, Any]) -> int:
    value = turn.get("narration_attempts", 0)
    return int(value) if isinstance(value, (int, float)) else 0


def _is_observation(turn: dict[str, Any]) -> bool:
    return bool(_attempts(turn)) or turn.get("observation_enforce") is not None


def _is_failed(turn: dict[str, Any]) -> bool:
    return turn.get("error") is not None and turn.get("narration") is None


def _is_recovered(turn: dict[str, Any]) -> bool:
    return _narration_attempts(turn) >= 2 and turn.get("narration") is not None


def _rejected_attempts(turn: dict[str, Any]) -> list[dict[str, Any]]:
    return [attempt for attempt in _attempts(turn) if attempt.get("accepted") is not True]


def _raw_reply_text(reply: Any) -> str:
    if not isinstance(reply, str):
        return str(reply)
    try:
        parsed = json.loads(reply)
    except (TypeError, ValueError):
        return reply
    if not isinstance(parsed, dict):
        return reply
    segments = parsed.get("segments")
    if isinstance(segments, str):
        return segments
    if isinstance(segments, list):
        text = []
        for segment in segments:
            if isinstance(segment, str):
                text.append(segment)
            elif isinstance(segment, dict) and segment.get("text") is not None:
                text.append(str(segment["text"]))
        if text:
            return "\n".join(text)
    return reply


def _extra_raw_replies(turn: dict[str, Any]) -> list[str]:
    extra_count = max(0, _narration_attempts(turn) - len(_attempts(turn)))
    replies = turn.get("provider_responses")
    if extra_count == 0 or not isinstance(replies, list):
        return []
    start = min(len(replies), len(_attempts(turn)))
    selected = replies[start : start + extra_count]
    if len(selected) < extra_count:
        selected = replies[-extra_count:]
    return [_raw_reply_text(reply) for reply in selected]


def _earlier_items(turn: dict[str, Any]) -> list[tuple[str, str]]:
    items = [("earlier attempt", str(attempt.get("narration") or "")) for attempt in _rejected_attempts(turn)]
    items.extend(("earlier raw reply", reply) for reply in _extra_raw_replies(turn))
    return items


def _needs_recovery(turn: dict[str, Any]) -> bool:
    return _narration_attempts(turn) >= 2 or (_is_failed(turn) and bool(_attempts(turn)))


def _last_relations(turn: dict[str, Any]) -> list[dict[str, Any]]:
    attempts = _attempts(turn)
    if not attempts or not isinstance(attempts[-1], dict):
        return []
    relations = attempts[-1].get("relations")
    return relations if isinstance(relations, list) else []


def _required_things(turn: dict[str, Any]) -> list[str]:
    result = []
    seen = set()
    for relation in _last_relations(turn):
        if not isinstance(relation, dict) or relation.get("thing") in (None, ""):
            continue
        parts = [str(relation["thing"])]
        if relation.get("place") not in (None, ""):
            parts.append(str(relation["place"]))
        if relation.get("holder") not in (None, ""):
            parts.append("held")
        value = " | ".join(parts)
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _sheet_block(turn_id: str, turn: dict[str, Any]) -> str:
    lines = [f"## {turn_id}", "", f"Command: {turn.get('input', '')}", "", "THINGS:", ""]
    things = _required_things(turn)
    lines.extend(f"- {thing}" for thing in things) if things else lines.append("- (none)")
    lines.extend(["", "Narration:", ""])
    if turn.get("narration") is None:
        lines.append("no narration: the turn did not complete")
    else:
        lines.append(str(turn["narration"]))
    if _needs_recovery(turn):
        earlier = _earlier_items(turn)
        if earlier:
            lines.extend(["", "Earlier:", ""])
            for number, (label, text) in enumerate(earlier, start=1):
                if label == "earlier attempt":
                    lines.extend([f"earlier attempt {number}:", str(text), ""])
                else:
                    lines.extend(["earlier raw reply:", str(text), ""])
            lines.pop()
    return "\n".join(lines)


def _sheet(rows: list[dict[str, Any]]) -> str:
    blocks = [_sheet_block(turn_id, turn) for turn_id, turn in _turns(rows)]
    random.Random(SHUFFLE_SEED).shuffle(blocks)
    return "\n".join(["# Blind observation sheet", "", f"Shuffle seed: {SHUFFLE_SEED}", "", *blocks, ""])


def _labels_template(rows: list[dict[str, Any]]) -> str:
    template = {}
    scope_rows = _scope_rows(rows)
    for turn_id, turn in _turns(rows):
        entry = {
            "presents_required": None,
            "acceptable": None,
            "tags": {name: None for name in TAG_NAMES},
            "earlier": [None for _ in _earlier_items(turn)],
        }
        if scope_rows:
            entry["underside_search"] = None
            entry["card_found_in_prose"] = None
        if scope_rows:
            entry["gap_restated"] = None
            entry["contents_shown"] = None
            entry["command_opens"] = None
        template[turn_id] = entry
    return json.dumps(template, indent=2) + "\n"


def _label_entry(labels: dict[str, Any], turn_id: str) -> dict[str, Any]:
    value = labels.get(turn_id)
    return value if isinstance(value, dict) else {}


def _bool_label(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _tag_label(labels: dict[str, Any], turn_id: str, tag: str) -> bool | None:
    entry = _label_entry(labels, turn_id)
    tags = entry.get("tags")
    if not isinstance(tags, dict):
        return None
    return _bool_label(tags.get(tag))


def _earlier_labels(labels: dict[str, Any], turn_id: str) -> list[Any]:
    value = _label_entry(labels, turn_id).get("earlier")
    return value if isinstance(value, list) else []


def _missing_labels(rows: list[dict[str, Any]], labels: Any) -> list[str]:
    labels = labels if isinstance(labels, dict) else {}
    missing = []
    card_prose_turns = _card_prose_turns(rows)
    t9c_scope = _t9c_scope(rows)
    for turn_id, turn in _turns(rows):
        if not _is_observation(turn):
            pass
        else:
            entry = _label_entry(labels, turn_id)
            if not _is_failed(turn):
                if _bool_label(entry.get("presents_required")) is None:
                    missing.append(f"{turn_id} presents_required")
                if _bool_label(entry.get("acceptable")) is None:
                    missing.append(f"{turn_id} acceptable")
            earlier = _earlier_labels(labels, turn_id)
            for index in range(len(_earlier_items(turn))):
                if index >= len(earlier) or _bool_label(earlier[index]) is None:
                    missing.append(f"{turn_id} earlier {index + 1}")
        underside_label = _label_entry(labels, turn_id).get("underside_search")
        if _request_kind(turn) == "under" and _bool_label(underside_label) is None:
            missing.append(f"{turn_id} underside_search")
        card_prose_label = _label_entry(labels, turn_id).get("card_found_in_prose")
        if turn_id in card_prose_turns and _bool_label(card_prose_label) is None:
            missing.append(f"{turn_id} card_found_in_prose")
        if t9c_scope and _is_observation(turn):
            entry = _label_entry(labels, turn_id)
            if _bool_label(entry.get("command_opens")) is None:
                missing.append(f"{turn_id} command_opens")
            if _committed(turn):
                if _bool_label(entry.get("gap_restated")) is None:
                    missing.append(f"{turn_id} gap_restated")
                if _bool_label(entry.get("contents_shown")) is None:
                    missing.append(f"{turn_id} contents_shown")
    return missing


def _sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _number(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}" if isinstance(value, float) else str(value)


def _nearest_rank(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[rank - 1]


def _wilson_upper(successes: int, total: int) -> float | None:
    if total == 0:
        return None
    z = 1.6448536269514722
    proportion = successes / total
    denominator = 1 + z * z / total
    numerator = (
        proportion
        + z * z / (2 * total)
        + z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total))
    )
    return numerator / denominator


def _rate(numerator: int, denominator: int) -> str:
    return "n/a" if denominator == 0 else f"{numerator}/{denominator} = {numerator / denominator:.6f}"


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _normalise_command(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    command = value.casefold().strip()
    if command.endswith("."):
        command = command[:-1].rstrip()
    return command


def _outcome(turn: dict[str, Any]) -> str:
    if _is_failed(turn):
        return "FAILED"
    if _is_recovered(turn):
        return "recovered"
    return "committed"


def _next_turns(rows: list[dict[str, Any]]):
    for replicate_index, replicate in enumerate(rows):
        turns = replicate.get("turns", ())
        for turn_index, turn in enumerate(turns):
            next_turn = turns[turn_index + 1] if turn_index + 1 < len(turns) else None
            yield _turn_id(replicate_index, turn_index), turn, next_turn


def _route_names(rows: list[dict[str, Any]]) -> list[str]:
    result = []
    for replicate in rows:
        route = _route(replicate)
        if route is not None and route not in result:
            result.append(route)
    return result


def _t9c_scope(rows: list[dict[str, Any]]) -> bool:
    return "observe_look_inside_under" in _route_names(rows)


def _look_group(turn: dict[str, Any]) -> bool:
    return _normalise_command(turn.get("input")) in LOOK_GROUP_COMMANDS


def _look_group_turns(rows: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    return [(turn_id, turn) for turn_id, turn in _turns(rows) if _look_group(turn)]


def _route_c_turns(rows: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    return [
        (turn_id, turn)
        for replicate_index, replicate in enumerate(rows)
        if _route(replicate) == "observe_look_inside_under"
        for turn_index, turn in enumerate(replicate.get("turns", ()))
        for turn_id in (_turn_id(replicate_index, turn_index),)
    ]


def _route_c_look_group_turns(rows: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    return [(turn_id, turn) for turn_id, turn in _route_c_turns(rows) if _look_group(turn)]


def _route_c_search_turns(rows: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    return [
        (turn_id, turn)
        for turn_id, turn in _route_c_turns(rows)
        if _normalise_command(turn.get("input")) == SEARCH_COMMAND
    ]


def _route_a_inspect_turns(rows: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    return [
        (turn_id, turn)
        for replicate_index, replicate in enumerate(rows)
        if _route(replicate) == "observe_topup"
        for turn_index, turn in enumerate(replicate.get("turns", ()))
        if _normalise_command(turn.get("input")) == "inspect the drawer"
        for turn_id in (_turn_id(replicate_index, turn_index),)
    ]


def _committed(turn: dict[str, Any]) -> bool:
    return not _is_failed(turn) and turn.get("narration") is not None


def _card_found_turn(
    replicate_index: int, replicate: dict[str, Any], command: str
) -> tuple[str, dict[str, Any]] | None:
    for turn_index, turn in enumerate(replicate.get("turns", ())):
        if _normalise_command(turn.get("input")) != command:
            continue
        before = turn.get("places_before")
        after = turn.get("places_after")
        before_place = before.get(CARD_THING) if isinstance(before, dict) else None
        after_place = after.get(CARD_THING) if isinstance(after, dict) else None
        if after_place == PLAYER_THING and before_place != PLAYER_THING:
            return _turn_id(replicate_index, turn_index), turn
    return None


def _card_was_mentioned_before(replicate: dict[str, Any], found_turn_index: int) -> bool:
    for turn in replicate.get("turns", ())[:found_turn_index]:
        if _committed(turn) and "card" in str(turn.get("narration", "")).casefold():
            return True
    return False


def _scope_s1(rows: list[dict[str, Any]], labels: dict[str, Any]) -> tuple[str, list[str], int]:
    under_turns = [(turn_id, turn) for turn_id, turn in _turns(rows) if _request_kind(turn) == "under"]
    violations = [
        turn_id
        for turn_id, turn in under_turns
        if _bool_label(_label_entry(labels, turn_id).get("underside_search")) is not True
    ]
    return ("PASS" if not violations else "FAIL"), violations, len(under_turns)


def _scope_s2(rows: list[dict[str, Any]]) -> tuple[str, int | None, int | None]:
    topup_turns = [
        turn for replicate in rows if _route(replicate) == "observe_topup" for turn in replicate.get("turns", ())
    ]
    if not topup_turns:
        return "INCONCLUSIVE", None, None
    under_count = sum(_request_kind(turn) == "under" for turn in topup_turns)
    relations_count = sum(bool(_last_relations(turn)) for turn in topup_turns)
    status = "PASS" if under_count >= 10 and relations_count >= 20 else "INCONCLUSIVE"
    return status, under_count, relations_count


def _card_target_for_replicate(replicate_index: int, replicate: dict[str, Any]) -> str | None:
    for turn_index, turn in enumerate(replicate.get("turns", ())):
        if turn_index > 1:
            break
        before = turn.get("places_before")
        after = turn.get("places_after")
        before_place = before.get(CARD_THING) if isinstance(before, dict) else None
        after_place = after.get(CARD_THING) if isinstance(after, dict) else None
        if after_place == PLAYER_THING and before_place != PLAYER_THING:
            return _turn_id(replicate_index, turn_index)
    return None


def _scope_s3(rows: list[dict[str, Any]], labels: dict[str, Any]) -> tuple[str, int, int, list[str], int]:
    replicates = [
        (index, replicate) for index, replicate in enumerate(rows) if _route(replicate) == "observe_under_first"
    ]
    passed = 0
    details = []
    for replicate_index, replicate in replicates:
        turns = replicate.get("turns", ())
        second = turns[1] if len(turns) > 1 else {}
        after = second.get("places_after") if isinstance(second, dict) else None
        held = isinstance(after, dict) and after.get(CARD_THING) == PLAYER_THING
        target_id = _card_target_for_replicate(replicate_index, replicate)
        prose = (
            target_id is not None and _bool_label(_label_entry(labels, target_id).get("card_found_in_prose")) is True
        )
        failures = []
        if not held:
            failures.append("held by player after second command")
        if not prose:
            failures.append("card_found_in_prose")
        if failures:
            details.append(f"S3 {replicate_index}: failed " + "; failed ".join(failures))
        else:
            passed += 1
    leak_count = sum(
        _tag_label(labels, turn_id, "leak") is True
        for replicate_index, replicate in replicates
        for turn_index, turn in enumerate(replicate.get("turns", ()))
        if not _is_failed(turn) and turn.get("narration") is not None
        for turn_id in (_turn_id(replicate_index, turn_index),)
    )
    if leak_count:
        status = "FAIL"
    elif len(replicates) < 5:
        status = "INCONCLUSIVE"
    else:
        status = "PASS" if passed / len(replicates) >= 0.8 else "FAIL"
    return status, passed, len(replicates), details, leak_count


def _t9c_n1(rows: list[dict[str, Any]]) -> tuple[str, int, int, list[str]]:
    look_turns = _route_c_look_group_turns(rows)
    failures = []
    for turn_id, turn in look_turns:
        if not _committed(turn):
            reason = "unsuccessful" if _is_failed(turn) else "no committed narration"
            failures.append(f"{turn_id} ({reason})")
    status = "PASS" if len(look_turns) - len(failures) >= len(look_turns) - 2 else "FAIL"
    return status, len(look_turns) - len(failures), len(look_turns), failures


def _t9d_n1s(rows: list[dict[str, Any]], labels: dict[str, Any]) -> tuple[str, int, int, list[str]]:
    search_turns = _route_c_search_turns(rows)
    misses = []
    for turn_id, turn in search_turns:
        reasons = []
        if not _committed(turn):
            reasons.append("unsuccessful")
        if turn.get("focus_open_state_committed") != "open":
            reasons.append("closed after commit")
        if _bool_label(_label_entry(labels, turn_id).get("contents_shown")) is not True:
            reasons.append("contents_shown false")
        if reasons:
            misses.append(f"{turn_id} ({'; '.join(reasons)})")
    passed = len(search_turns) - len(misses)
    status = "PASS" if search_turns and len(misses) <= 1 else "FAIL"
    return status, passed, len(search_turns), misses


def _t9c_n2(rows: list[dict[str, Any]], labels: dict[str, Any]) -> tuple[str, int, int, list[str]]:
    route_c_turns = [
        (turn_id, turn)
        for turn_id, turn in _route_c_turns(rows)
        if _normalise_command(turn.get("input")) in NUDGE_GROUP_COMMANDS
    ]
    misses = [
        f"{turn_id} (handoff_id={turn.get('handoff_id')})"
        for turn_id, turn in route_c_turns
        if _bool_label(_label_entry(labels, turn_id).get("gap_restated")) is not True
    ]
    passed = len(route_c_turns) - len(misses)
    status = "PASS" if passed >= len(route_c_turns) - 2 else "FAIL"
    return status, passed, len(route_c_turns), misses


def _t9d_n2a(rows: list[dict[str, Any]], labels: dict[str, Any]) -> tuple[str, int, int]:
    inspect_turns = _route_a_inspect_turns(rows)
    misses = sum(
        _bool_label(_label_entry(labels, turn_id).get("gap_restated")) is not True for turn_id, _ in inspect_turns
    )
    passed = len(inspect_turns) - misses
    status = "PASS" if inspect_turns and misses <= 1 else "FAIL"
    return status, passed, len(inspect_turns)


def _t9c_n3(rows: list[dict[str, Any]], labels: dict[str, Any]) -> tuple[str, list[str]]:
    failures = []
    route_c_replicates = [
        (index, replicate) for index, replicate in enumerate(rows) if _route(replicate) == "observe_look_inside_under"
    ]
    route_b_replicates = [
        (index, replicate) for index, replicate in enumerate(rows) if _route(replicate) == "observe_under_first"
    ]
    route_c_passed = 0
    for replicate_index, replicate in route_c_replicates:
        found = _card_found_turn(replicate_index, replicate, LOOK_UNDER_COMMAND)
        if found is None:
            failures.append(f"r{replicate_index} (look under did not hold the card)")
            continue
        turn_id, turn = found
        entry = _label_entry(labels, turn_id)
        if _bool_label(entry.get("card_found_in_prose")) is not True:
            failures.append(f"{turn_id} (card_found_in_prose)")
            continue
        if _bool_label(entry.get("gap_restated")) is True:
            failures.append(f"{turn_id} (gap_restated on card find)")
            continue
        if turn.get("handoff_id") == NUDGE_HANDOFF_ID:
            failures.append(f"{turn_id} (nudge handoff_id={turn.get('handoff_id')})")
            continue
        found_index = replicate.get("turns", ()).index(turn)
        if _card_was_mentioned_before(replicate, found_index):
            failures.append(f"{turn_id} (card mentioned before found)")
            continue
        route_c_passed += 1
    route_b_passed = 0
    for replicate_index, replicate in route_b_replicates:
        found = _card_found_turn(replicate_index, replicate, FEEL_UNDER_COMMAND)
        if found is None:
            failures.append(f"r{replicate_index} (first feel under did not hold the card)")
            continue
        turn_id, turn = found
        entry = _label_entry(labels, turn_id)
        if _bool_label(entry.get("card_found_in_prose")) is not True:
            failures.append(f"{turn_id} (card_found_in_prose)")
            continue
        if _bool_label(entry.get("gap_restated")) is True:
            failures.append(f"{turn_id} (gap_restated on card find)")
            continue
        if turn.get("handoff_id") == NUDGE_HANDOFF_ID:
            failures.append(f"{turn_id} (nudge handoff_id={turn.get('handoff_id')})")
            continue
        found_index = replicate.get("turns", ()).index(turn)
        if _card_was_mentioned_before(replicate, found_index):
            failures.append(f"{turn_id} (card mentioned before found)")
            continue
        route_b_passed += 1
    route_c_ok = not route_c_replicates or route_c_passed >= 14
    route_b_ok = not route_b_replicates or route_b_passed >= 4
    if not route_c_replicates and not route_b_replicates:
        return "INCONCLUSIVE", failures
    return ("PASS" if route_c_ok and route_b_ok else "FAIL"), failures


def _t9c_n4(rows: list[dict[str, Any]], labels: dict[str, Any]) -> tuple[str, int, int, list[str]]:
    turns = [
        (turn_id, turn)
        for replicate_index, replicate in enumerate(rows)
        if _route(replicate) == "observe_look_inside_under"
        for turn_index, turn in enumerate(replicate.get("turns", ()))
        if _normalise_command(turn.get("input")) == LOOK_INSIDE_COMMAND
        for turn_id in (_turn_id(replicate_index, turn_index),)
    ]
    failures = []
    for turn_id, turn in turns:
        reasons = []
        if not _committed(turn):
            reasons.append("unsuccessful")
        if turn.get("focus_open_state_committed") != "open":
            reasons.append("closed after commit")
        if _bool_label(_label_entry(labels, turn_id).get("contents_shown")) is not True:
            reasons.append("contents_shown false")
        if reasons:
            failures.append(f"{turn_id} ({'; '.join(reasons)})")
    status = "PASS" if len(turns) - len(failures) >= 14 else "FAIL"
    return status, len(turns) - len(failures), len(turns), failures


def _t9c_n5(rows: list[dict[str, Any]], labels: dict[str, Any]) -> tuple[str, list[str]]:
    failures = []
    for turn_id, turn in _route_c_turns(rows):
        command_opens = _bool_label(_label_entry(labels, turn_id).get("command_opens"))
        if turn.get("engine_opened") is True and command_opens is not True:
            failures.append(f"{turn_id} (engine_opened with command_opens false)")
        if turn.get("engine_opened") is True and _look_group(turn):
            failures.append(f"{turn_id} (engine_opened on look-group turn)")
    return ("PASS" if not failures else "FAIL"), failures


def _t9c_n6(rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    failures = []
    for turn_id, turn in _turns(rows):
        if not _is_failed(turn) or turn.get("engine_opened") is not True:
            continue
        if turn.get("focus_open_state_committed") != "closed":
            failures.append(f"{turn_id} (open state not rolled back)")
        if turn.get("places_after") != turn.get("places_before"):
            failures.append(f"{turn_id} (places not rolled back)")
    return ("PASS" if not failures else "FAIL"), failures


def _prompts(replicate: dict[str, Any]) -> list[dict[str, Any]]:
    prompts = []
    opening = replicate.get("opening")
    if isinstance(opening, dict) and isinstance(opening.get("prompts"), list):
        prompts.extend(opening["prompts"])
    for turn in replicate.get("turns", ()):
        if isinstance(turn.get("prompts"), list):
            prompts.extend(turn["prompts"])
    return [prompt for prompt in prompts if isinstance(prompt, dict)]


def _prompt_search_count(replicate: dict[str, Any]) -> int | None:
    prompts = _prompts(replicate)
    if not prompts:
        return None
    matching = sum(
        any("searches_underneath" in value for value in prompt.values() if isinstance(value, str)) for prompt in prompts
    )
    return matching if matching else None


def _kind_counts(replicate: dict[str, Any]) -> dict[str, int]:
    counts = {kind: 0 for kind in ("look", "open", "enter", "under", "none")}
    for turn in replicate.get("turns", ()):
        kind = _request_kind(turn)
        counts[kind if kind in counts else "none"] += 1
    return counts


def _request_kind_text(turns: list[tuple[str, dict[str, Any]]]) -> str:
    counts = {kind: 0 for kind in ("look", "open", "under")}
    for _, turn in turns:
        kind = _request_kind(turn)
        if kind in counts:
            counts[kind] += 1
    total = len(turns)
    return ", ".join(f"{kind}={counts[kind]}/{total}" for kind in ("look", "open", "under"))


def _engine_open_counts(turns: list[tuple[str, dict[str, Any]]]) -> str:
    counts = {}
    for _, turn in turns:
        if turn.get("engine_opened") is not True:
            continue
        command = _normalise_command(turn.get("input")) or "(missing command)"
        counts[command] = counts.get(command, 0) + 1
    if not counts:
        return "none"
    return ", ".join(f"{command}={counts[command]}" for command in sorted(counts))


def _delivered_statement_count(turns: list[tuple[str, dict[str, Any]]]) -> int:
    statement = "Kristin looks over the drawer and is pointed toward the thin gap beneath its lower edge."
    look_under_turns = [turn for _, turn in turns if _normalise_command(turn.get("input")) == LOOK_UNDER_COMMAND]
    delivered = sum(_committed(turn) and statement in str(turn.get("narration", "")) for turn in look_under_turns)
    return delivered


def _scope_information(rows: list[dict[str, Any]], labels: dict[str, Any]) -> list[str]:
    lines = []
    routes = _route_names(rows)
    for route in routes:
        route_turns = []
        for replicate_index, replicate in enumerate(rows):
            if _route(replicate) != route:
                continue
            route_turns.extend(
                (_turn_id(replicate_index, turn_index), turn)
                for turn_index, turn in enumerate(replicate.get("turns", ()))
            )
        counts = {kind: 0 for kind in ("look", "open", "enter", "under", "none")}
        for _, turn in route_turns:
            kind = _request_kind(turn)
            counts[kind if kind in counts else "none"] += 1
        lines.append(
            f"kind distribution ({route}): "
            + ", ".join(f"{kind}={counts[kind]}" for kind in ("look", "open", "enter", "under", "none"))
        )
        misses = [
            turn_id
            for turn_id, turn in route_turns
            if _bool_label(_label_entry(labels, turn_id).get("underside_search")) is True
            and _request_kind(turn) != "under"
        ]
        lines.append(f"underside_search misses ({route}): {', '.join(misses) if misses else 'none'}")
        openings = [(turn_id, turn) for turn_id, turn in route_turns if _request_kind(turn) == "open"]
        presented = sum(
            _bool_label(_label_entry(labels, turn_id).get("presents_required")) is True
            for turn_id, turn in openings
            if not _is_failed(turn) and turn.get("narration") is not None
        )
        committed_openings = sum(not _is_failed(turn) and turn.get("narration") is not None for _, turn in openings)
        lines.append(f"opening turns ({route}): presents_required {_rate(presented, committed_openings)}")
    for replicate_index, replicate in enumerate(rows):
        route = _route(replicate) or "none"
        count = _prompt_search_count(replicate)
        value = "n/a (recorded prompt text has no searches_underneath key)" if count is None else str(count)
        lines.append(f"searches_underneath prompts ({route} r{replicate_index}): {value}")
    return lines


CALL_TIMING_KINDS = ("jev", "narration", "worker")


def _timing_elapsed(value: Any) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return float(value)


def _timing_entry(entry: Any) -> tuple[str, float, list[str]] | None:
    if not isinstance(entry, dict):
        return None
    kind = entry.get("kind")
    elapsed = _timing_elapsed(entry.get("elapsed_s"))
    if kind not in CALL_TIMING_KINDS or elapsed is None:
        return None
    keys = entry.get("keys")
    keys = [key for key in keys if isinstance(key, str)] if isinstance(keys, list) else []
    return kind, elapsed, keys


def _call_timing_turn(turn_id: str, turn: dict[str, Any]) -> dict[str, Any] | None:
    call_timings = turn.get("call_timings")
    if not isinstance(call_timings, list):
        return None
    entries = []
    for entry in call_timings:
        timing = _timing_entry(entry)
        if timing is not None:
            entries.append(timing)
    sums = {kind: 0.0 for kind in CALL_TIMING_KINDS}
    for kind, elapsed, _keys in entries:
        sums[kind] += elapsed
    return {"turn_id": turn_id, "turn": turn, "entries": entries, "sums": sums}


def _call_timing_information(route_turns: list[tuple[str, dict[str, Any]]]) -> list[str]:
    timed_turns = [
        timed_turn for turn_id, turn in route_turns if (timed_turn := _call_timing_turn(turn_id, turn)) is not None
    ]
    total_turns = len(route_turns)
    if not timed_turns:
        return ["call timing: n/a (rows have no call_timings)"]

    calls = {kind: [] for kind in CALL_TIMING_KINDS}
    for timed_turn in timed_turns:
        for kind, elapsed, keys in timed_turn["entries"]:
            calls[kind].append((elapsed, timed_turn["turn_id"], keys))

    lines = [f"call timing (turns with call_timings: {len(timed_turns)} of {total_turns}):"]
    for kind in CALL_TIMING_KINDS:
        elapsed_values = [elapsed for elapsed, _turn_id, _keys in calls[kind]]
        if not elapsed_values:
            continue
        per_turn_sums = [timed_turn["sums"][kind] for timed_turn in timed_turns]
        lines.append(
            f"  {kind} calls: n={len(elapsed_values)}, per turn mean "
            f"{_number(len(elapsed_values) / len(timed_turns))}, "
            f"call p50 {_number(_nearest_rank(elapsed_values, 0.50))}, "
            f"p95 {_number(_nearest_rank(elapsed_values, 0.95))}, "
            f"max {_number(max(elapsed_values))}; per turn sum mean {_number(_mean(per_turn_sums))}"
        )

    outside_values = []
    for timed_turn in timed_turns:
        elapsed = _timing_elapsed(timed_turn["turn"].get("turn_elapsed_s"))
        if elapsed is not None:
            call_sum = sum(entry[1] for entry in timed_turn["entries"])
            outside_values.append(elapsed - call_sum)
    lines.append(f"  turn time outside calls (engine and waiting): mean {_number(_mean(outside_values))}")

    slow_turns = [
        timed_turn
        for timed_turn in timed_turns
        if _timing_elapsed(timed_turn["turn"].get("turn_elapsed_s")) is not None
    ]
    slow_turns.sort(key=lambda timed_turn: timed_turn["turn"]["turn_elapsed_s"], reverse=True)
    lines.append("  slowest 5 turns:")
    for timed_turn in slow_turns[:5]:
        turn = timed_turn["turn"]
        lines.append(
            f"    {timed_turn['turn_id']} | {turn.get('input', '')} | "
            f"total {_number(float(turn['turn_elapsed_s']))} | "
            + " | ".join(f"{kind} {_number(timed_turn['sums'][kind])}" for kind in CALL_TIMING_KINDS)
            + f" | narration attempts {_narration_attempts(turn)}"
        )

    jev_calls = sorted(calls["jev"], key=lambda call: call[0], reverse=True)
    lines.append("  slowest 5 jev calls:")
    for elapsed, turn_id, keys in jev_calls[:5]:
        lines.append(f"    {turn_id} | {'+'.join(keys)} | {_number(elapsed)}")
    return lines


def _call_timing_blocks(rows: list[dict[str, Any]]) -> list[str]:
    lines = []
    for route in _route_names(rows):
        route_turns = []
        for replicate_index, replicate in enumerate(rows):
            if _route(replicate) != route:
                continue
            route_turns.extend(
                (_turn_id(replicate_index, turn_index), turn)
                for turn_index, turn in enumerate(replicate.get("turns", ()))
            )
        lines.extend(["", *_call_timing_information(route_turns)])
    return lines


def _join(
    rows: list[dict[str, Any]],
    labels: dict[str, Any],
    *,
    rows_sha256: str = "",
    labels_sha256: str = "",
) -> tuple[str, list[str]]:
    missing = _missing_labels(rows, labels)
    if missing:
        return "", missing

    all_turns = list(_turns(rows))
    observations = [(turn_id, turn) for turn_id, turn in all_turns if _is_observation(turn)]
    failed_observations = [(turn_id, turn) for turn_id, turn in observations if _is_failed(turn)]
    committed_observations = [
        (turn_id, turn) for turn_id, turn in observations if not _is_failed(turn) and turn.get("narration") is not None
    ]

    failed_count = len(failed_observations)
    observation_count = len(observations)
    upper_bound = _wilson_upper(failed_count, observation_count)
    routes = _route_names(rows)
    route_b = "observe_under_first" in routes
    clause_one = (
        "INCONCLUSIVE"
        if route_b
        else ("INCONCLUSIVE" if observation_count == 0 else ("PASS" if failed_count <= 1 else "FAIL"))
    )

    deficient = sum(
        _bool_label(_label_entry(labels, turn_id).get("presents_required")) is False
        for turn_id, _ in committed_observations
    )
    clause_two = "PASS" if deficient == 0 else "FAIL"

    tag_counts = {}
    tag_statuses = {}
    for tag in TAG_NAMES:
        count = sum(_tag_label(labels, turn_id, tag) is True for turn_id, _ in committed_observations)
        tag_counts[tag] = count
        tag_statuses[tag] = (
            "PASS" if count <= (0 if tag in ("leak", "wrong_custody", "unrequested_move") else 1) else "FAIL"
        )
    clause_three = "PASS" if all(status == "PASS" for status in tag_statuses.values()) else "FAIL"

    rollback_violations = []
    next_exists = 0
    next_ran = 0
    for turn_id, turn, next_turn in _next_turns(rows):
        if not _is_failed(turn):
            continue
        if next_turn is not None:
            next_exists += 1
            if next_turn.get("error") is None:
                next_ran += 1
            else:
                rollback_violations.append(f"{turn_id} next turn")
        if turn.get("places_after") != turn.get("places_before"):
            rollback_violations.append(f"{turn_id} places")
        if turn.get("narration") is not None:
            rollback_violations.append(f"{turn_id} narration")
        if turn.get("error") is None:
            rollback_violations.append(f"{turn_id} error")
    clause_four = "PASS" if not rollback_violations else "FAIL"

    budget_violations = [
        turn_id
        for turn_id, turn in all_turns
        if _narration_attempts(turn) > 2
        or (isinstance(turn.get("verifier_requests"), (int, float)) and turn["verifier_requests"] > 2)
    ]
    clause_five = "PASS" if not budget_violations else "FAIL"

    latency_values = [
        float(turn["turn_elapsed_s"])
        for _, turn in all_turns
        if _narration_attempts(turn) == 1
        and turn.get("error") is None
        and isinstance(turn.get("turn_elapsed_s"), (int, float))
    ]
    recovered_values = [
        float(turn["turn_elapsed_s"])
        for _, turn in all_turns
        if _is_recovered(turn) and isinstance(turn.get("turn_elapsed_s"), (int, float))
    ]
    latency_p50 = _nearest_rank(latency_values, 0.50)
    latency_p95 = _nearest_rank(latency_values, 0.95)
    recovered_p50 = _nearest_rank(recovered_values, 0.50)
    recovered_max = max(recovered_values) if recovered_values else None
    clause_six = (
        "INCONCLUSIVE"
        if route_b
        else ("INCONCLUSIVE" if len(latency_values) < 20 else ("PASS" if latency_p95 <= 10.0 else "FAIL"))
    )

    false_rejects = 0
    rejected_total = 0
    for turn_id, turn in all_turns:
        earlier = _earlier_labels(labels, turn_id)
        earlier_index = 0
        for earlier_index, _attempt in enumerate(_rejected_attempts(turn)):
            rejected_total += 1
            if earlier_index < len(earlier) and earlier[earlier_index] is False:
                false_rejects += 1
    clause_seven = (
        "INCONCLUSIVE"
        if route_b
        else ("INCONCLUSIVE" if rejected_total < 5 else ("PASS" if false_rejects <= 1 else "FAIL"))
    )

    s1_status, s1_violations, s1_under_count = _scope_s1(rows, labels)
    s2_status, s2_under_count, s2_relations_count = _scope_s2(rows)
    s3_status, s3_passed, s3_replicates, s3_details, s3_leaks = _scope_s3(rows, labels)
    t9c_scope = _t9c_scope(rows)
    n2a_status = None
    n2a_passed = None
    n2a_total = None
    if t9c_scope:
        n1_status, n1_committed, n1_total, n1_failures = _t9c_n1(rows)
        n1s_status, n1s_passed, n1s_total, n1s_failures = _t9d_n1s(rows, labels)
        n2_status, n2_gap, n2_total, n2_failures = _t9c_n2(rows, labels)
        n3_status, n3_failures = _t9c_n3(rows, labels)
        n4_status, n4_open, n4_total, n4_failures = _t9c_n4(rows, labels)
        n5_status, n5_failures = _t9c_n5(rows, labels)
        n6_status, n6_failures = _t9c_n6(rows)
    if "observe_topup" in routes and _route_a_inspect_turns(rows):
        n2a_status, n2a_passed, n2a_total = _t9d_n2a(rows, labels)
    s2_under_text = "n/a" if s2_under_count is None else str(s2_under_count)
    s2_relations_text = "n/a" if s2_relations_count is None else str(s2_relations_count)
    s2_note = "; n/a on other routes, ignored for verdict" if route_b else ""
    stage_design_note = "; n too small, by design" if route_b else ""

    needed_recovery = sum(_narration_attempts(turn) >= 2 or _is_failed(turn) for _, turn in observations)
    recovered_count = sum(_is_recovered(turn) for _, turn in observations)
    total_attempts = sum(_narration_attempts(turn) for _, turn in all_turns)
    total_requests = sum(
        int(turn["verifier_requests"])
        for _, turn in all_turns
        if isinstance(turn.get("verifier_requests"), (int, float))
    )
    observation_elapsed = [
        float(turn["turn_elapsed_s"])
        for _, turn in observations
        if isinstance(turn.get("turn_elapsed_s"), (int, float))
    ]
    diverged = sum(
        isinstance(turn.get("observation_enforce"), dict)
        and turn["observation_enforce"].get("observation_diverged") is True
        for _, turn in observations
    )
    refind_labels = [
        _tag_label(labels, turn_id, "refind")
        for turn_id, turn in committed_observations
        if _normalise_command(turn.get("input")) == REFIND_COMMAND
    ]
    invented_labels = [
        _tag_label(labels, turn_id, "invented_object")
        for turn_id, turn in committed_observations
        if _normalise_command(turn.get("input")) == SEAT_COMMAND and not _last_relations(turn)
    ]
    refind_known = [value for value in refind_labels if value is not None]
    invented_known = [value for value in invented_labels if value is not None]

    lines = [
        "# Joined enforcement report",
        "",
        f"rows sha256: {rows_sha256}",
        f"labels sha256: {labels_sha256}",
        "",
        "## Turn outcomes",
        "",
        "| turn id | command | attempts | verifier requests | elapsed | outcome |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for turn_id, turn in all_turns:
        lines.append(
            f"| {turn_id} | {turn.get('input', '')} | {_narration_attempts(turn)} | "
            f"{turn.get('verifier_requests', 0)} | {_number(turn.get('turn_elapsed_s'))} | {_outcome(turn)} |"
        )

    lines.extend(
        [
            "",
            "## Clauses",
            "",
            f"Clause 1: {clause_one} (failed observation turns: {failed_count}/{observation_count}; "
            f"one-sided 95% Wilson upper bound: {_number(upper_bound)}; n={observation_count}{stage_design_note})",
            f"Clause 2: {clause_two} (presents_required false: {deficient}; "
            f"committed observation turns: {len(committed_observations)})",
            f"Clause 3: {clause_three}",
            f"Clause 3 leak: {tag_statuses['leak']} ({tag_counts['leak']}; limit 0)",
            f"Clause 3 wrong_custody: {tag_statuses['wrong_custody']} ({tag_counts['wrong_custody']}; limit 0)",
            f"Clause 3 unrequested_move: {tag_statuses['unrequested_move']} "
            f"({tag_counts['unrequested_move']}; limit 0)",
            f"Clause 3 refind: {tag_statuses['refind']} ({tag_counts['refind']}; limit 1)",
            f"Clause 3 invented_object: {tag_statuses['invented_object']} ({tag_counts['invented_object']}; limit 1)",
            f"Clause 4: {clause_four} (violations: {len(rollback_violations)}; "
            f"next rows: {next_exists} existed, {next_ran} ran)",
            f"Clause 5: {clause_five} (violations: {len(budget_violations)}; "
            "limit 2 narration attempts and 2 verifier requests)",
            f"Clause 6: {clause_six} (eligible n={len(latency_values)}; p50={_number(latency_p50)}; "
            f"p95={_number(latency_p95)}; nearest-rank percentile; recovered p50={_number(recovered_p50)}; "
            f"recovered max={_number(recovered_max)}{stage_design_note})",
            f"Clause 7: {clause_seven} (false rejects: {false_rejects}; rejected attempts: {rejected_total}; "
            f"limit 1{stage_design_note})",
            f"S1 classification audit: {s1_status} (under turns: {s1_under_count}; violations: {len(s1_violations)})",
            f"S2 non-vacuity: {s2_status} (under turns: {s2_under_text}; "
            f"non-empty required lists: {s2_relations_text}; limits 10 and 20{s2_note})",
            f"S3 card: {s3_status} (passing replicates: {s3_passed}/{s3_replicates}; "
            f"leak tags: {s3_leaks}; limit 80% and at least 5 replicates)",
        ]
    )
    if clause_two == "FAIL":
        lines.extend(["", "STOP: the verifier let deficient prose through"])
    if s1_violations:
        lines.extend(
            [
                "",
                "STOP: coverage was suppressed on a command that is not an underside search "
                f"({', '.join(s1_violations)})",
            ]
        )
    lines.extend(s3_details)

    if t9c_scope:
        lines.extend(
            [
                "",
                "## T9c clauses",
                "",
                f"N1: {n1_status} ({n1_committed}/{n1_total} look-group turns committed; "
                f"failures: {', '.join(n1_failures) if n1_failures else 'none'})",
                f"N1s: {n1s_status} ({n1s_passed}/{n1s_total} search turns pass; "
                f"failures: {', '.join(n1s_failures) if n1s_failures else 'none'})",
                f"N2: {n2_status} ({n2_gap}/{n2_total} route C gap labels; "
                f"misses: {', '.join(n2_failures) if n2_failures else 'none'})",
                f"N3: {n3_status} (failures: {', '.join(n3_failures) if n3_failures else 'none'})",
                f"N4: {n4_status} ({n4_open}/{n4_total} route C look-inside turns pass; "
                f"failures: {', '.join(n4_failures) if n4_failures else 'none'})",
                f"N5: {n5_status} (failures: {', '.join(n5_failures) if n5_failures else 'none'})",
                f"N6: {n6_status} (failures: {', '.join(n6_failures) if n6_failures else 'none'})",
            ]
        )
        if n2a_status is not None:
            lines.append(f"N2a: {n2a_status} ({n2a_passed}/{n2a_total} route A inspect turns restated the gap)")
    elif n2a_status is not None:
        lines.extend(
            [
                "",
                f"N2a: {n2a_status} ({n2a_passed}/{n2a_total} route A inspect turns restated the gap)",
            ]
        )

    lines.extend(
        [
            "",
            "## Information",
            "",
            f"first-attempt rejection rate: {_rate(needed_recovery, observation_count)}",
            f"recovery success rate: {_rate(recovered_count, needed_recovery)}",
            f"total narration attempts: {total_attempts}",
            f"total verifier requests: {total_requests}",
            f"mean observation turn elapsed_s: {_number(_mean(observation_elapsed))} (n={len(observation_elapsed)})",
            f"observation diverged share: {_rate(diverged, observation_count)}",
            f"refind tags on {REFIND_COMMAND}: {sum(value is True for value in refind_known)}/{len(refind_known)}",
            f"invented_object tags on {SEAT_COMMAND}: "
            f"{sum(value is True for value in invented_known)}/{len(invented_known)}",
            *_scope_information(rows, labels),
        ]
    )
    if t9c_scope:
        look_turns = _route_c_look_group_turns(rows)
        search_turns = _route_c_search_turns(rows)
        narrator_turns = look_turns + search_turns
        narrator_opened = [
            turn_id
            for turn_id, turn in narrator_turns
            if turn.get("focus_open_state_committed") == "open"
            and turn.get("focus_open_state_after") == "closed"
            and turn.get("engine_opened") is not True
        ]
        narrator_closed = [
            turn_id
            for turn_id, turn in _turns(rows)
            if _committed(turn)
            and turn.get("engine_opened") is True
            and turn.get("focus_open_state_committed") == "closed"
        ]
        handoff_counts = {}
        for _, turn in _turns(rows):
            handoff_id = str(turn.get("handoff_id"))
            handoff_counts[handoff_id] = handoff_counts.get(handoff_id, 0) + 1
        handoff_text = ", ".join(f"{handoff_id}={count}" for handoff_id, count in sorted(handoff_counts.items()))
        delivered_count = _delivered_statement_count(_route_c_turns(rows))
        lines.extend(
            [
                f"look-group request kinds: {_request_kind_text(look_turns)}",
                f"search request kinds: {_request_kind_text(search_turns)}",
                "narrator-opened look-group and search turns: "
                f"{', '.join(narrator_opened) if narrator_opened else 'none'}",
                f"narrator-closed-after-engine-open turns: {', '.join(narrator_closed) if narrator_closed else 'none'}",
                f"engine opens by command: {_engine_open_counts(_route_c_turns(rows))}",
                f"delivered statement text in prose: {delivered_count}",
                f"handoff outcomes: {handoff_text if handoff_text else 'none'}",
            ]
        )
    t9d_statuses = []
    if t9c_scope:
        t9d_statuses.extend((n1_status, n1s_status, n2_status, n3_status, n4_status, n5_status, n6_status))
    if n2a_status is not None:
        t9d_statuses.append(n2a_status)
    overall = (
        "PASS"
        if all(
            status == "PASS" for status in (clause_one, clause_two, clause_three, clause_four, clause_five, clause_six)
        )
        and clause_seven in ("PASS", "INCONCLUSIVE")
        and all(status == "PASS" for status in t9d_statuses)
        else "FAIL"
    )
    if route_b:
        t9b_statuses = (clause_two, clause_three, clause_four, clause_five, s1_status, s3_status)
    elif "observe_topup" in routes:
        t9b_statuses = (
            clause_one,
            clause_two,
            clause_three,
            clause_four,
            clause_five,
            clause_six,
            clause_seven,
            s1_status,
            s2_status,
        )
        if n2a_status is not None:
            t9b_statuses = (*t9b_statuses, n2a_status)
    else:
        t9b_statuses = (clause_one, clause_two, clause_three, clause_four, clause_five, clause_six, clause_seven)
    t9b_overall = "PASS" if all(status == "PASS" for status in t9b_statuses) else "FAIL"
    lines.extend(_call_timing_blocks(rows))
    lines.extend(["", f"enforcement screen: {overall}", f"t9b screen: {t9b_overall}", ""])
    return "\n".join(lines), []


def _write_or_print(text: str, output_path: str | None) -> None:
    if output_path is None:
        sys.stdout.write(text)
    else:
        Path(output_path).write_text(text, encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    template = subparsers.add_parser("labels-template")
    template.add_argument("rows_json")
    template.add_argument("--out")

    sheet = subparsers.add_parser("sheet")
    sheet.add_argument("rows_json")
    sheet.add_argument("--out")

    join = subparsers.add_parser("join")
    join.add_argument("rows_json")
    join.add_argument("--labels", required=True)
    join.add_argument("--out")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        rows = _load_json(args.rows_json)
        if args.command == "labels-template":
            _write_or_print(_labels_template(rows), args.out)
            return 0
        if args.command == "sheet":
            _write_or_print(_sheet(rows), args.out)
            return 0
        labels = _load_json(args.labels)
        report, missing = _join(
            rows,
            labels,
            rows_sha256=_sha256(args.rows_json),
            labels_sha256=_sha256(args.labels),
        )
        if missing:
            sys.stderr.write("MISSING LABELS: " + ", ".join(missing) + "\n")
            return 1
        _write_or_print(report, args.out)
        return 0
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"Unable to build report: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
