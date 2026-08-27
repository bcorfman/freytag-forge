"""Versioned, integrity-checked SQLite snapshots for scene runtime sessions."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from pydantic import ValidationError

from storygame.runtime.state import RuntimeState
from storygame.story_package.models import StoryPackage


class RuntimeSaveError(ValueError):
    """Raised before an invalid or mismatched save can be rehydrated."""


class RuntimeStateSqliteStore:
    # Version 2 deliberately rejects snapshots written before package knowledge
    # semantics were versioned.  Rehydrating prose-era saves would silently
    # reinterpret their state under the new revelation contract.
    SCHEMA_VERSION = 2

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS runtime_snapshots (
                session_id TEXT PRIMARY KEY, story_id TEXT NOT NULL, version INTEGER NOT NULL,
                payload TEXT NOT NULL, payload_hash TEXT NOT NULL)"""
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    @staticmethod
    def _payload(state: RuntimeState) -> str:
        return json.dumps(state.model_dump(mode="json", exclude={"package"}), sort_keys=True, separators=(",", ":"))

    def save(self, session_id: str, state: RuntimeState) -> None:
        payload = self._payload(state)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO runtime_snapshots(session_id, story_id, version, payload, payload_hash)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET story_id=excluded.story_id, version=excluded.version,
                payload=excluded.payload, payload_hash=excluded.payload_hash""",
                (session_id, state.package.story_id, self.SCHEMA_VERSION, payload, digest),
            )

    def load(self, session_id: str, package: StoryPackage) -> RuntimeState:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT story_id, version, payload, payload_hash FROM runtime_snapshots WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise RuntimeSaveError("save does not exist")
        story_id, version, payload, digest = row
        if story_id != package.story_id or version != self.SCHEMA_VERSION:
            raise RuntimeSaveError("save is incompatible with this story package")
        if hashlib.sha256(payload.encode()).hexdigest() != digest:
            raise RuntimeSaveError("save integrity check failed")
        try:
            return RuntimeState.model_validate({**json.loads(payload), "package": package})
        except (json.JSONDecodeError, ValidationError, TypeError) as error:
            raise RuntimeSaveError("save payload is invalid") from error
