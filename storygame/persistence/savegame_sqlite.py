from __future__ import annotations

import base64
import json
import pickle
import re
import sqlite3
from pathlib import Path
from random import Random
from typing import Any

from storygame.engine.facts import active_story_goal, set_active_story_goal
from storygame.engine.state import Event, EventLog, GameState
from storygame.engine.world import build_default_state
from storygame.persistence.story_state import ORCHESTRATOR_WRITER, write_turn_artifacts


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
        "story_genre": state.story_genre,
        "story_tone": state.story_tone,
        "session_length": state.session_length,
        "plot_curve_id": state.plot_curve_id,
        "story_outline_id": state.story_outline_id,
        "world_package": dict(state.world_package),
        "world_facts": [list(fact) for fact in state.world_facts.all()],
        "fact_metrics": dict(state.fact_metrics),
        "progress": state.progress,
        "tension": state.tension,
        "turn_index": state.turn_index,
        "active_goal": active_story_goal(state),
        "beat_history": list(state.beat_history),
        "player": {
            "location": state.player.location,
            "inventory": list(state.player.inventory),
            "flags": dict(state.player.flags),
        },
        "room_items": {room_id: list(room.item_ids) for room_id, room in state.world.rooms.items()},
        "event_log": [serialize_event(event) for event in state.event_log.events],
        "last_judge_decision": dict(state.last_judge_decision) if state.last_judge_decision is not None else None,
        "pending_high_impact_command": state.pending_high_impact_command,
        "pending_high_impact_assessment": dict(state.pending_high_impact_assessment),
    }


def deserialize_state(payload: dict[str, Any]) -> GameState:
    state = build_default_state(
        seed=int(payload["seed"]),
        genre=str(payload.get("story_genre", "mystery")),
        session_length=str(payload.get("session_length", "medium")),
        tone=str(payload.get("story_tone", "neutral")),
    )
    state.story_tone = str(payload.get("story_tone", state.story_tone))
    state.plot_curve_id = str(payload.get("plot_curve_id", state.plot_curve_id))
    state.story_outline_id = str(payload.get("story_outline_id", state.story_outline_id))
    state.world_package = dict(payload.get("world_package", state.world_package))
    raw_facts = payload.get("world_facts", [])
    state.world_facts.replace_all(tuple(tuple(fact) for fact in raw_facts))
    state.fact_metrics = {str(key): float(value) for key, value in dict(payload.get("fact_metrics", {})).items()}
    from storygame.engine.facts import sync_legacy_views

    sync_legacy_views(state)
    state.progress = float(payload["progress"])
    state.tension = float(payload["tension"])
    state.turn_index = int(payload["turn_index"])
    state.active_goal = payload["active_goal"]
    set_active_story_goal(state, state.active_goal)
    state.beat_history = tuple(payload.get("beat_history", []))
    state.player.location = payload["player"]["location"]
    state.player.inventory = tuple(payload["player"]["inventory"])
    state.player.flags = dict(payload["player"]["flags"])

    for room_id, item_ids in payload.get("room_items", {}).items():
        if room_id in state.world.rooms:
            state.world.rooms[room_id].item_ids = tuple(item_ids)

    state.event_log = EventLog(tuple(deserialize_event(raw) for raw in payload.get("event_log", [])))
    raw_judge_decision = payload.get("last_judge_decision")
    if raw_judge_decision is None:
        state.last_judge_decision = None
    else:
        state.last_judge_decision = {
            "decision_id": str(raw_judge_decision.get("decision_id", "")),
            "status": str(raw_judge_decision.get("status", "")),
            "judge": str(raw_judge_decision.get("judge", "")),
            "rationale": str(raw_judge_decision.get("rationale", "")),
        }
    state.pending_high_impact_command = str(payload.get("pending_high_impact_command", ""))
    raw_pending_assessment = payload.get("pending_high_impact_assessment", {})
    state.pending_high_impact_assessment = (
        dict(raw_pending_assessment) if isinstance(raw_pending_assessment, dict) else {}
    )
    return state


class SqliteSaveStore:
    def __init__(
        self,
        path: str | Path = "runs/storygame_saves.sqlite",
        check_same_thread: bool = True,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=check_same_thread)
        self.conn.row_factory = sqlite3.Row
        self.artifacts_root = self.path.parent / "story_artifacts"
        self.artifacts_root.mkdir(parents=True, exist_ok=True)
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

    def _safe_slot(self, slot: str) -> str:
        safe_slot = re.sub(r"[^a-zA-Z0-9._-]", "_", slot).strip("._")
        return safe_slot or "default"

    def _slot_directory(self, slot: str) -> Path:
        return self.artifacts_root / self._safe_slot(slot)

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
        judge_decision: dict[str, str] | None = None,
    ) -> None:
        payload = serialize_state(state)
        event_payloads = [serialize_event(event) for event in state.event_log.events]
        accepted_judge_decision = self._accepted_judge_decision(judge_decision)
        trace = {
            "raw_command": raw_command,
            "action_kind": action_kind,
            "beat_type": beat_type or "",
            "template_key": template_key or "",
            "judge_decision": accepted_judge_decision,
        }
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

            write_turn_artifacts(
                state,
                self._slot_directory(slot),
                trace=trace,
                writer=ORCHESTRATOR_WRITER,
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

    def _accepted_judge_decision(self, judge_decision: dict[str, str] | None) -> dict[str, str]:
        if judge_decision is None:
            return {
                "decision_id": "legacy-accepted",
                "status": "accepted",
                "judge": "director",
                "rationale": "single-agent deterministic mode auto-accept",
            }

        decision_id = judge_decision.get("decision_id", "").strip()
        status = judge_decision.get("status", "").strip()
        judge = judge_decision.get("judge", "").strip()
        rationale = judge_decision.get("rationale", "").strip()
        if not decision_id or not status or not judge:
            raise ValueError("JudgeDecision must include decision_id, status, and judge.")
        if status != "accepted":
            raise ValueError("StoryState persistence requires an accepted JudgeDecision.")

        return {
            "decision_id": decision_id,
            "status": status,
            "judge": judge,
            "rationale": rationale,
        }
