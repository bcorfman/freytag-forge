"""Integrity-checked projections derived from accepted runtime decisions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from storygame.runtime.state import RuntimeState

ARTIFACT_SCHEMA_VERSION = "runtime-artifacts-v1"
_JSON_ARTIFACTS = {"StoryState.json", "trace.json", "transcript.json"}


class ArtifactIntegrityError(ValueError):
    """Raised when an artifact projection or its manifest has been altered."""


def artifact_bundle(state: RuntimeState) -> dict[str, object]:
    """Build every player-facing projection from the current fact-backed state."""

    events = [_event_payload(event) for event in state.recent_events]
    signature = replay_signature(state)
    return {
        "StoryState.json": {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "compiled_story_id": state.compiled_story.id,
            "turn_index": state.turn_index,
            "location": state.world.location,
            "facts": state.facts.as_json(),
            "accepted_decisions": events,
            "replay_signature": signature,
        },
        "STORY.md": _story_markdown(state, signature),
        "trace.json": {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "replay_signature": signature,
            "events": events,
        },
        "transcript.json": events,
    }


def artifact_manifest(bundle: dict[str, object]) -> dict[str, object]:
    """Return stable hashes for a projection bundle, excluding the manifest itself."""

    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "files": {name: _sha256(_encoded(value)) for name, value in sorted(bundle.items()) if name != "manifest.json"},
    }


def write_artifacts(directory: str | Path, state: RuntimeState) -> dict[str, object]:
    """Write projections and their manifest; callers may regenerate them at any time."""

    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    bundle = artifact_bundle(state)
    manifest = artifact_manifest(bundle)
    for name, value in bundle.items():
        path = target / name
        temporary = path.with_suffix(path.suffix + ".tmp")
        if name in _JSON_ARTIFACTS:
            temporary.write_bytes(_encoded(value))
        else:
            temporary.write_text(str(value), encoding="utf-8")
        temporary.replace(path)
    manifest_path = target / "manifest.json"
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_bytes(_encoded(manifest))
    temporary.replace(manifest_path)
    return manifest


def verify_artifact_manifest(directory: str | Path, manifest: dict[str, object] | None = None) -> None:
    """Verify all projection hashes before a projection is used for diagnostics."""

    target = Path(directory)
    actual_manifest = manifest or _read_manifest(target)
    if actual_manifest.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise ArtifactIntegrityError("unsupported artifact schema version")
    files = actual_manifest.get("files")
    if not isinstance(files, dict):
        raise ArtifactIntegrityError("artifact manifest has no file hashes")
    for name, expected in files.items():
        path = target / str(name)
        if not path.is_file():
            raise ArtifactIntegrityError(f"missing artifact: {name}")
        value = json.loads(path.read_text(encoding="utf-8")) if name in _JSON_ARTIFACTS else path.read_text()
        actual = _sha256(_encoded(value))
        if actual != expected:
            raise ArtifactIntegrityError(f"artifact integrity failed: {name}")


def replay_signature(state: RuntimeState) -> str:
    """Hash accepted turn decisions, never narration or mutable projection fields."""

    decisions = [_event_payload(event, include_narration=False) for event in state.recent_events]
    return _sha256(_encoded(decisions))


def verify_replay_signature(state: RuntimeState, expected: str) -> None:
    """Reject replay evidence that no longer matches accepted runtime decisions."""

    if replay_signature(state) != expected:
        raise ArtifactIntegrityError("replay signature does not match accepted decisions")


def _event_payload(event: object, *, include_narration: bool = True) -> dict[str, Any]:
    payload = {
        "turn_index": event.turn_index,
        "player_input": event.player_input,
        "operations": list(event.operations),
        "beat_updates": list(event.beat_updates),
        "segments": list(event.segments),
        "prompt_version": event.prompt_version,
        "prompt_token_estimate": event.prompt_token_estimate,
    }
    if include_narration:
        payload["narration"] = event.narration
    return payload


def _story_markdown(state: RuntimeState, signature: str) -> str:
    active_goals = [fact.object for fact in state.facts.matching("active_goal", "player") if fact.object is not None]
    goal_line = ", ".join(active_goals) if active_goals else "none declared"
    lines = [
        f"# {state.compiled_story.title}",
        "",
        f"- Turn: {state.turn_index}",
        f"- Location: {state.world.location}",
        f"- Active goal: {goal_line}",
        f"- Replay signature: `{signature}`",
        "",
        "## Transcript",
        "",
    ]
    for event in state.recent_events:
        lines.extend((f"### Turn {event.turn_index}", "", f"**Player:** {event.player_input}", "", event.narration, ""))
        for segment in event.segments:
            if segment["kind"] == "speech":
                speaker = segment["speaker"]
                lines.extend((f"**{speaker['name']}:** “{segment['text']}”", ""))
            else:
                actor = segment["actor"]
                lines.extend((f"*{actor['name']} — {segment['text']}*", ""))
    return "\n".join(lines)


def _read_manifest(directory: Path) -> dict[str, object]:
    try:
        return json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ArtifactIntegrityError("artifact manifest is missing or invalid") from exc


def _encoded(value: object) -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
