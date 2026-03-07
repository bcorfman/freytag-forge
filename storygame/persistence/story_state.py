from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from storygame.engine.state import GameState
from storygame.plot.freytag import get_phase

STORY_STATE_FILE = "StoryState.json"
STORY_MARKDOWN_FILE = "STORY.md"
ARTIFACT_SCHEMA_VERSION = 2
ORCHESTRATOR_WRITER = "sqlite_save_store_orchestrator"
LOGGER = logging.getLogger(__name__)


def _sorted_room_inventory(world_state) -> dict[str, list[str]]:
    return {room_id: list(room.item_ids) for room_id, room in sorted(world_state.rooms.items())}


def build_story_state_payload(
    state: GameState,
    trace: dict[str, object],
    story_markdown_sha256: str = "",
) -> dict[str, object]:
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "seed": state.seed,
        "turn_index": state.turn_index,
        "active_goal": state.active_goal,
        "progress": state.progress,
        "tension": state.tension,
        "phase": get_phase(state.progress),
        "beat_history": list(state.beat_history),
        "constraints": [],
        "open_threads": [],
        "player": {
            "location": state.player.location,
            "inventory": list(state.player.inventory),
            "flags": dict(state.player.flags),
        },
        "room_items": _sorted_room_inventory(state.world),
        "event_log": [event.to_summary() for event in state.event_log],
        "trace": trace,
        "story_markdown_sha256": story_markdown_sha256,
    }


def canonical_story_state_text(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, indent=2) + "\n"


def load_story_state_payload(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_story_state_payload(payload)
    return payload


def _markdown_from_payload(payload: dict[str, object]) -> str:
    player = payload["player"]
    room_items_by_room = payload["room_items"]
    event_log = payload["event_log"]
    player_location = player["location"]
    room_items = ", ".join(room_items_by_room.get(player_location, ())) or "none"
    inventory = ", ".join(player["inventory"]) or "none"
    flags = ", ".join(sorted(player["flags"].keys())) or "none"
    recent_events = event_log[-12:]

    lines = [
        "# StoryState Workspace",
        "",
        f"## Turn {payload['turn_index']}",
        f"- Seed: {payload['seed']}",
        f"- Phase: {payload['phase']}",
        f"- Progress: {float(payload['progress']):.2f}",
        f"- Tension: {float(payload['tension']):.2f}",
        f"- Active goal: {payload['active_goal']}",
        "",
        "## Canonical facts",
        f"- Location: {player_location}",
        f"- Inventory: {inventory}",
        f"- Active flags: {flags}",
        f"- Room items: {room_items}",
        "",
        "## Recent events",
    ]

    if not recent_events:
        lines.append("- None")
    else:
        for event in recent_events:
            message = event["message_key"] or event["type"]
            lines.append(f"- {message}")

    return "\n".join(lines) + "\n"


def _story_markdown_sha256(story_markdown: str) -> str:
    return hashlib.sha256(story_markdown.encode("utf-8")).hexdigest()


def _validate_story_from_payload(payload: dict[str, object], story_markdown: str) -> None:
    expected_hash = payload["story_markdown_sha256"]
    actual_hash = _story_markdown_sha256(story_markdown)
    if expected_hash != actual_hash:
        raise ValueError("Story markdown hash mismatch for canonical payload.")


def _validate_existing_artifacts(directory: Path) -> None:
    state_path = directory / STORY_STATE_FILE
    story_path = directory / STORY_MARKDOWN_FILE
    if not state_path.exists() and not story_path.exists():
        return
    if not state_path.exists() or not story_path.exists():
        LOGGER.error("Artifact integrity check failed: missing paired artifact in %s", directory)
        raise ValueError("Artifact integrity check failed: artifact pair is incomplete.")
    payload = load_story_state_payload(state_path)
    story_markdown = story_path.read_text(encoding="utf-8")
    try:
        _validate_story_from_payload(payload, story_markdown)
    except ValueError as exc:
        LOGGER.error("Artifact integrity check failed: %s", exc)
        raise ValueError("Artifact integrity check failed: STORY.md was externally mutated.") from exc


def _assert_orchestrator_writer(writer: str) -> None:
    if writer != ORCHESTRATOR_WRITER:
        LOGGER.error("Rejected non-orchestrator writer '%s' for story artifacts.", writer)
        raise ValueError("Story artifacts can only be written by orchestrator.")


def validate_story_state_payload(payload: dict[str, object]) -> None:
    try:
        int(payload["schema_version"])
        int(payload["seed"])
        int(payload["turn_index"])
        float(payload["progress"])
        float(payload["tension"])
        payload["active_goal"].strip()
        payload["phase"].strip()
        payload["player"]["location"].strip()
        payload["trace"]["raw_command"].strip()
        payload["trace"]["action_kind"].strip()
        payload["trace"]["judge_decision"]["decision_id"].strip()
        payload["trace"]["judge_decision"]["status"].strip()
        payload["story_markdown_sha256"].strip()
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ValueError("Invalid StoryState schema payload.") from exc

    if payload["trace"]["judge_decision"]["status"] != "accepted":
        raise ValueError("StoryState trace requires an accepted JudgeDecision.")

    expected_phase = get_phase(float(payload["progress"]))
    if payload["phase"] != expected_phase:
        raise ValueError("StoryState phase does not match progress.")


def write_turn_artifacts(
    state: GameState,
    directory: Path,
    trace: dict[str, object],
    writer: str = ORCHESTRATOR_WRITER,
) -> tuple[Path, Path]:
    _assert_orchestrator_writer(writer)
    directory.mkdir(parents=True, exist_ok=True)
    _validate_existing_artifacts(directory)

    payload = build_story_state_payload(state, trace=trace)
    story_markdown = _markdown_from_payload(payload)
    payload["story_markdown_sha256"] = _story_markdown_sha256(story_markdown)
    validate_story_state_payload(payload)

    state_path = directory / STORY_STATE_FILE
    state_path.write_text(canonical_story_state_text(payload), encoding="utf-8")
    story_path = directory / STORY_MARKDOWN_FILE
    story_path.write_text(story_markdown, encoding="utf-8")
    return state_path, story_path
