"""Record and render proven lessons from fun-review outcomes."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from factory.tickets import Ticket

_OUTCOMES = {"delivered", "fun_exhausted"}
_RECORD_FIELDS = {
    "lesson_id",
    "ticket_id",
    "scene_id",
    "outcome",
    "fix_kind",
    "precedent",
    "failed_checks",
    "fun_round",
    "recorded_at",
}
_HEADER = "FUN REVIEW LESSONS (machine-recorded, proven across ≥2 scenes)"


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def lessons_path(payload: Mapping) -> Path | None:
    if "fun_lessons_path" not in payload:
        return _repository_root() / "factory" / "state" / "fun_lessons.jsonl"
    raw_path = payload["fun_lessons_path"]
    if not isinstance(raw_path, (str, Path)):
        return None
    path = Path(raw_path)
    return path if path.is_absolute() else _repository_root() / path


def _precedent(plan: object) -> str:
    if not isinstance(plan, dict):
        return "none"
    reason = plan.get("reason")
    if not isinstance(reason, str):
        return "none"
    marker = "Precedent: "
    start = reason.find(marker)
    if start < 0:
        return "none"
    value = reason[start + len(marker) :].lstrip()
    if value.lower().startswith("none"):
        return "none"
    delimiters = [position for delimiter in (".", ";", "\n") if (position := value.find(delimiter)) >= 0]
    value = value[: min(delimiters)] if delimiters else value
    value = value.strip()
    return value[:80] or "none"


def _plan_values(plan: object) -> tuple[str | None, str]:
    kind = plan.get("kind") if isinstance(plan, dict) else None
    return (kind if isinstance(kind, str) and kind != "unknown" else None, _precedent(plan))


def _failed_checks(entry: object) -> list[str]:
    if not isinstance(entry, dict) or not isinstance(entry.get("failed_checks"), list):
        return []
    return [check for check in entry["failed_checks"] if isinstance(check, str)]


def _candidate_records(ticket: Ticket, outcome: str, recorded_at: str) -> list[dict[str, Any]]:
    history = ticket.payload.get("fun_history")
    if not isinstance(history, list) or not history:
        return []

    records: list[dict[str, Any]] = []
    for round_number, entry in enumerate(history, start=1):
        plan = entry.get("plan") if isinstance(entry, dict) else None
        fix_kind, precedent = _plan_values(plan)
        if fix_kind is None:
            continue
        failed_checks = _failed_checks(entry)
        records.append(
            {
                "lesson_id": f"{ticket.id}:{round_number}:blocked",
                "ticket_id": ticket.id,
                "scene_id": ticket.scene,
                "outcome": "blocked",
                "fix_kind": fix_kind,
                "precedent": precedent,
                "failed_checks": failed_checks,
                "fun_round": round_number,
                "recorded_at": recorded_at,
            }
        )

    if outcome == "delivered":
        plan = ticket.payload.get("plan")
        fix_kind, precedent = _plan_values(plan)
        if fix_kind is not None:
            records.append(
                {
                    "lesson_id": f"{ticket.id}:{len(history) + 1}:won_after_block",
                    "ticket_id": ticket.id,
                    "scene_id": ticket.scene,
                    "outcome": "won_after_block",
                    "fix_kind": fix_kind,
                    "precedent": precedent,
                    "failed_checks": [],
                    "fun_round": len(history) + 1,
                    "recorded_at": recorded_at,
                }
            )
    return records


def record_lessons(ticket: Ticket, outcome: str) -> None:
    """Append new lessons for a ticket and mark the payload ids already recorded."""

    if outcome not in _OUTCOMES:
        raise ValueError(f"unknown lesson outcome: {outcome}")
    recorded = ticket.payload.get("fun_lessons_recorded")
    recorded_ids = [item for item in recorded if isinstance(item, str)] if isinstance(recorded, list) else []
    records = _candidate_records(ticket, outcome, datetime.now(UTC).isoformat())
    if not records:
        return

    path = lessons_path(ticket.payload)
    if path is None:
        return
    existing_ids: set[str] = set()
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    item = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    continue
                if isinstance(item, dict) and isinstance(item.get("lesson_id"), str):
                    existing_ids.add(item["lesson_id"])

    new_records = [
        record
        for record in records
        if record["lesson_id"] not in existing_ids and record["lesson_id"] not in recorded_ids
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in new_records:
            json.dump(record, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")

    for record in records:
        lesson_id = record["lesson_id"]
        if lesson_id not in recorded_ids:
            recorded_ids.append(lesson_id)
    ticket.payload["fun_lessons_recorded"] = recorded_ids


def _read_records(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return []
    records: list[dict[str, Any]] = []
    for line in lines:
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if (
            isinstance(record, dict)
            and _RECORD_FIELDS.issubset(record)
            and all(
                isinstance(record[field], str)
                for field in {
                    "lesson_id",
                    "ticket_id",
                    "scene_id",
                    "outcome",
                    "fix_kind",
                    "precedent",
                    "recorded_at",
                }
            )
            and record["outcome"] in {"blocked", "won_after_block"}
            and isinstance(record["failed_checks"], list)
            and all(isinstance(check, str) for check in record["failed_checks"])
            and isinstance(record["fun_round"], int)
            and not isinstance(record["fun_round"], bool)
        ):
            records.append(record)
    return records


def _proven(values: list[dict[str, Any]]) -> bool:
    return len({item["ticket_id"] for item in values}) >= 2 and len({item["scene_id"] for item in values}) >= 2


def _latest(values: list[dict[str, Any]]) -> str:
    return max((value["recorded_at"] for value in values if isinstance(value["recorded_at"], str)), default="")


def render_lessons(path: str | Path, cap: int = 4000) -> str:
    """Render only proven, grouped fun-review lessons within the character cap."""

    if cap <= 0:
        return ""
    records = _read_records(Path(path))
    blocked: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    wins: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record["fix_kind"] == "unknown":
            continue
        if record["outcome"] == "blocked":
            checks = record["failed_checks"] if isinstance(record["failed_checks"], list) else []
            for check in checks:
                if isinstance(check, str):
                    blocked[(record["fix_kind"], record["precedent"], check)].append(record)
        elif record["outcome"] == "won_after_block":
            wins[(record["fix_kind"], record["precedent"])].append(record)

    avoid: list[tuple[int, str, str]] = []
    works: list[tuple[int, str, str]] = []
    mixed: list[tuple[int, str, str]] = []
    mixed_pairs: set[tuple[str, str]] = set()
    for (fix_kind, precedent, check), values in blocked.items():
        winning = wins.get((fix_kind, precedent), [])
        if _proven(values) and _proven(winning):
            mixed_pairs.add((fix_kind, precedent))
            line = f'- Mixed: {fix_kind} via "{precedent}": {len({item["ticket_id"] for item in winning})} wins, '
            line += f"{len({item['ticket_id'] for item in values})} blocks on {check}."
            mixed.append((len({item["scene_id"] for item in values}), _latest(values + winning), line))
        elif _proven(values):
            line = f'- Avoid: {fix_kind} via "{precedent}" tends to fail {check} '
            line += f"({len({item['ticket_id'] for item in values})} tickets, "
            line += f"{len({item['scene_id'] for item in values})} scenes)."
            avoid.append((len({item["scene_id"] for item in values}), _latest(values), line))

    for (fix_kind, precedent), values in wins.items():
        if _proven(values) and (fix_kind, precedent) not in mixed_pairs:
            line = f'- Works after a block: {fix_kind} via "{precedent}" passed fun review and live playtest '
            line += f"({len({item['ticket_id'] for item in values})} tickets, "
            line += f"{len({item['scene_id'] for item in values})} scenes)."
            works.append((len({item["scene_id"] for item in values}), _latest(values), line))

    groups = []
    for group in (avoid, works, mixed):
        by_newest = sorted(group, key=lambda item: item[1], reverse=True)
        groups.append(sorted(by_newest, key=lambda item: item[0], reverse=True))
    lines = [item[2] for group in groups for item in group]
    if not lines:
        return ""

    def section(section_lines: list[str]) -> str:
        return "\n".join([_HEADER, *section_lines])

    if len(section(lines)) <= cap:
        return section(lines)
    omitted = 0
    while lines and len(section(lines + [f"- ({omitted + 1} more lessons not shown)"])) > cap:
        lines.pop()
        omitted += 1
    marker = f"- ({omitted} more lessons not shown)"
    while lines and len(section(lines + [marker])) > cap:
        lines.pop()
        omitted += 1
        marker = f"- ({omitted} more lessons not shown)"
    return section([*lines, marker])
