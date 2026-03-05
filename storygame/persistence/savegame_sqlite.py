from __future__ import annotations

import base64
import json
import pickle
import sqlite3
from pathlib import Path
from random import Random
from typing import Any

from storygame.engine.state import Event, EventLog, GameState
from storygame.engine.world import build_default_state


def _encode_rng(rng: Random) -> str:
    payload = pickle.dumps(rng.getstate(), protocol=pickle.HIGHEST_PROTOCOL)
    return base64.b64encode(payload).decode("ascii")


def _decode_rng(state_blob: str) -> Random:
    payload = base64.b64decode(state_blob.encode("ascii"))
    rng = Random()
    rng.setstate(pickle.loads(payload))
    return rng


def _encode_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True)


def serialize_event(event: Event) -> dict[str, Any]:
    return {
        "type": event.type,
        "entities": list(event.entities),
        "tags": list(event.tags),
        "delta_progress": event.delta_progress,
        "delta_tension": event.delta_tension,
        "message_key": event.message_key,
        "turn_index": event.turn_index,
        "timestamp": event.timestamp,
        "metadata": event.metadata,
    }


def deserialize_event(payload: dict[str, Any]) -> Event:
    return Event(
        type=payload["type"],
        entities=tuple(payload.get("entities", ())),
        tags=tuple(payload.get("tags", ())),
        delta_progress=float(payload.get("delta_progress", 0.0)),
        delta_tension=float(payload.get("delta_tension", 0.0)),
        message_key=payload.get("message_key", ""),
        turn_index=int(payload.get("turn_index", 0)),
        timestamp=payload.get("timestamp"),
        metadata=dict(payload.get("metadata", {})),
    )


def serialize_state(state: GameState) -> dict[str, Any]:
    return {
        "seed": state.seed,
        "progress": state.progress,
        "tension": state.tension,
        "turn_index": state.turn_index,
        "active_goal": state.active_goal,
        "beat_history": list(state.beat_history),
        "player": {
            "location": state.player.location,
            "inventory": list(state.player.inventory),
            "flags": dict(state.player.flags),
        },
        "room_items": {room_id: list(room.item_ids) for room_id, room in state.world.rooms.items()},
        "event_log": [serialize_event(event) for event in state.event_log.events],
    }


def deserialize_state(payload: dict[str, Any]) -> GameState:
    state = build_default_state(seed=int(payload["seed"]))
    state.progress = float(payload["progress"])
    state.tension = float(payload["tension"])
    state.turn_index = int(payload["turn_index"])
    state.active_goal = payload["active_goal"]
    state.beat_history = tuple(payload.get("beat_history", []))
    state.player.location = payload["player"]["location"]
    state.player.inventory = tuple(payload["player"]["inventory"])
    state.player.flags = dict(payload["player"]["flags"])

    for room_id, item_ids in payload.get("room_items", {}).items():
        if room_id in state.world.rooms:
            state.world.rooms[room_id].item_ids = tuple(item_ids)

    state.event_log = EventLog(tuple(deserialize_event(raw) for raw in payload.get("event_log", [])))
    return state


class SqliteSaveStore:
    def __init__(self, path: str | Path = "runs/storygame_saves.sqlite") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> SqliteSaveStore:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ARG001
        self.conn.close()

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                slot TEXT PRIMARY KEY,
                seed INTEGER NOT NULL,
                rng_state TEXT NOT NULL,
                updated_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
            );
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot TEXT NOT NULL,
                turn_index INTEGER NOT NULL,
                raw_command TEXT NOT NULL,
                action_kind TEXT NOT NULL,
                beat_type TEXT,
                template_key TEXT,
                created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                UNIQUE(slot, turn_index, action_kind)
            );
            CREATE TABLE IF NOT EXISTS state_snapshots (
                slot TEXT NOT NULL PRIMARY KEY,
                turn_index INTEGER NOT NULL,
                payload TEXT NOT NULL,
                created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
            );
            CREATE TABLE IF NOT EXISTS events (
                slot TEXT NOT NULL,
                turn_index INTEGER NOT NULL,
                sequence INTEGER NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY(slot, turn_index, sequence)
            );
            CREATE TABLE IF NOT EXISTS transcript_lines (
                slot TEXT NOT NULL,
                turn_index INTEGER NOT NULL,
                line_index INTEGER NOT NULL,
                line TEXT NOT NULL,
                PRIMARY KEY(slot, turn_index, line_index)
            );
            """
        )
        self.conn.commit()

    def save_run(
        self,
        slot: str,
        state: GameState,
        rng: Random,
        raw_command: str = "save",
        action_kind: str = "save",
        beat_type: str | None = None,
        template_key: str | None = None,
        transcript: list[str] | None = None,
    ) -> None:
        payload = serialize_state(state)
        event_payloads = [serialize_event(event) for event in state.event_log.events]
        with self.conn:
            self.conn.execute("DELETE FROM turns WHERE slot = ?", (slot,))
            self.conn.execute("DELETE FROM state_snapshots WHERE slot = ?", (slot,))
            self.conn.execute("DELETE FROM events WHERE slot = ?", (slot,))
            self.conn.execute("DELETE FROM transcript_lines WHERE slot = ?", (slot,))
            self.conn.execute(
                "INSERT OR REPLACE INTO runs(slot, seed, rng_state) VALUES (?, ?, ?)",
                (slot, state.seed, _encode_rng(rng)),
            )
            self.conn.execute(
                """
                INSERT OR REPLACE INTO state_snapshots(slot, turn_index, payload)
                VALUES (?, ?, ?)
                """,
                (slot, state.turn_index, _encode_json(payload)),
            )
            self.conn.execute(
                """
                INSERT INTO turns(slot, turn_index, raw_command, action_kind, beat_type, template_key)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (slot, state.turn_index, raw_command, action_kind, beat_type, template_key),
            )

            for sequence, event in enumerate(event_payloads):
                self.conn.execute(
                    """
                    INSERT INTO events(slot, turn_index, sequence, payload)
                    VALUES (?, ?, ?, ?)
                    """,
                    (slot, state.turn_index, sequence, _encode_json(event)),
                )

            if transcript:
                for line_index, line in enumerate(transcript):
                    self.conn.execute(
                        """
                        INSERT INTO transcript_lines(slot, turn_index, line_index, line)
                        VALUES (?, ?, ?, ?)
                        """,
                        (slot, state.turn_index, line_index, line),
                    )

    def load_run(self, slot: str) -> tuple[GameState, Random]:
        run_row = self.conn.execute("SELECT seed, rng_state FROM runs WHERE slot = ?", (slot,)).fetchone()
        if run_row is None:
            raise ValueError(f"No save exists for slot '{slot}'.")

        snapshot_row = self.conn.execute(
            "SELECT payload FROM state_snapshots WHERE slot = ?",
            (slot,),
        ).fetchone()
        if snapshot_row is None:
            raise ValueError(f"Save slot '{slot}' has no state snapshot.")

        payload = json.loads(snapshot_row["payload"])
        state = deserialize_state(payload)
        rng = _decode_rng(run_row["rng_state"])
        return state, rng

    def list_slots(self) -> list[str]:
        rows = self.conn.execute("SELECT slot FROM runs ORDER BY slot ASC").fetchall()
        return [row["slot"] for row in rows]
