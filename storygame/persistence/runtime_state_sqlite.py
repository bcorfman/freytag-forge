"""Versioned, integrity-checked V2 runtime snapshots for hosted sessions."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from storygame.authoring.contracts import CompiledStory
from storygame.runtime.facts import FactStore
from storygame.runtime.state import BeatRuntime, RuntimeEvent, RuntimeState, WorldState, runtime_state_bytes

SAVE_SCHEMA_VERSION = "runtime-state-v3"


class RuntimeSaveError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class RuntimeStateSqliteStore:
    def __init__(self, path: str | Path, *, namespace: str, check_same_thread: bool = True) -> None:
        if not namespace.strip():
            raise ValueError("session namespace is required")
        self.namespace = namespace
        database_path = Path(path)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(database_path, check_same_thread=check_same_thread)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS runtime_sessions (
                namespace TEXT NOT NULL, session_id TEXT NOT NULL, schema_version TEXT NOT NULL,
                compiled_story_id TEXT NOT NULL, compiled_story_hash TEXT NOT NULL,
                snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
                PRIMARY KEY(namespace, session_id))"""
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def save(self, session_id: str, state: RuntimeState) -> None:
        snapshot = _snapshot(state)
        encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
        story_hash = _hash_json(state.compiled_story.model_dump(mode="json"))
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO runtime_sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    self.namespace,
                    session_id,
                    SAVE_SCHEMA_VERSION,
                    state.compiled_story.id,
                    story_hash,
                    encoded,
                    _sha256(encoded),
                ),
            )

    def load(self, session_id: str, story: CompiledStory) -> RuntimeState:
        row = self.conn.execute(
            "SELECT * FROM runtime_sessions WHERE namespace = ? AND session_id = ?", (self.namespace, session_id)
        ).fetchone()
        if row is None:
            foreign = self.conn.execute(
                "SELECT schema_version FROM runtime_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if foreign is not None:
                raise RuntimeSaveError("unsupported_save_version", "Save belongs to another deployment channel.")
            legacy = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'state_snapshots'"
            ).fetchone()
            if legacy is not None:
                raise RuntimeSaveError(
                    "unsupported_save_version",
                    "V1 saves cannot be loaded by the V2 runtime.",
                )
            raise RuntimeSaveError("save_not_found", "No V2 save exists for this session.")
        if row["schema_version"] != SAVE_SCHEMA_VERSION:
            raise RuntimeSaveError(
                "unsupported_save_version", "This save was created by an unsupported runtime version."
            )
        if row["compiled_story_id"] != story.id or row["compiled_story_hash"] != _hash_json(
            story.model_dump(mode="json")
        ):
            raise RuntimeSaveError("compiled_story_mismatch", "The saved story does not match this session.")
        if _sha256(row["snapshot"]) != row["snapshot_hash"]:
            raise RuntimeSaveError("save_integrity_failed", "The saved runtime state failed integrity verification.")
        try:
            payload = json.loads(row["snapshot"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise RuntimeSaveError("save_integrity_failed", "The saved runtime snapshot is not valid JSON.") from exc
        try:
            return _restore(payload, story)
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeSaveError("save_integrity_failed", "The saved runtime snapshot is malformed.") from exc


def _snapshot(state: RuntimeState) -> dict[str, object]:
    payload = json.loads(runtime_state_bytes(state))
    payload["schema_version"] = SAVE_SCHEMA_VERSION
    return payload


def _restore(payload: dict[str, object], story: CompiledStory) -> RuntimeState:
    if payload.get("schema_version") != SAVE_SCHEMA_VERSION:
        raise ValueError("unsupported runtime snapshot schema")
    world = dict(payload["world"])
    beats = dict(payload["beat_runtime"])
    events = [
        RuntimeEvent(
            turn_index=int(event["turn_index"]),
            player_input=str(event["player_input"]),
            narration=str(event["narration"]),
            operations=tuple(dict(value) for value in event.get("operations", [])),
            beat_updates=tuple(dict(value) for value in event.get("beat_updates", [])),
            prompt_version=str(event["prompt_version"]),
            prompt_token_estimate=int(event["prompt_token_estimate"]),
        )
        for event in payload.get("recent_events", [])
    ]
    return RuntimeState(
        compiled_story=story,
        world=WorldState(
            str(world["location"]),
            set(world.get("flags", [])),
            dict(world.get("attributes", {})),
            dict(world.get("items", {})),
        ),
        beat_runtime={
            beat_id: BeatRuntime(
                beat_id, set(value["completed_tags"]), int(value["turns_active"]), int(value["stagnant_turns"])
            )
            for beat_id, value in beats.items()
        },
        turn_index=int(payload["turn_index"]),
        recent_events=events,
        story_summary=str(payload.get("story_summary", "")),
        facts=FactStore.from_json(payload.get("facts", [])),
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _hash_json(value: object) -> str:
    return _sha256(json.dumps(value, sort_keys=True, separators=(",", ":")))
