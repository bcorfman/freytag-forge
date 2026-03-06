from __future__ import annotations

import json
import math
import re
import sqlite3
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from storygame.engine.state import Event, GameState
from storygame.plot.freytag import get_phase

MAX_MEMORY_NOTES = 4
MAX_MEMORY_SNIPPET_LEN = 220


class MemoryStore(Protocol):
    def add_memory(
        self,
        slot: str,
        summary: str,
        category: str,
        tags: Iterable[str],
    ) -> None: ...

    def retrieve(
        self,
        slot: str,
        query_tags: Iterable[str],
        limit: int = MAX_MEMORY_NOTES,
    ) -> tuple[str, ...]: ...

    def ingest_events(self, slot: str, state: GameState, events: list[Event]) -> None: ...


def normalize_tag(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.strip().lower())


def _short_text(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def _tokenize_text(value: str) -> tuple[str, ...]:
    tokens = re.findall(r"[a-z0-9_]+", value.lower())
    return tuple(token for token in tokens if token)


def _vector(value: str) -> dict[str, float]:
    tokens = _tokenize_text(value)
    return Counter(tokens)


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    denom_a = math.sqrt(sum(weight * weight for weight in a.values()))
    denom_b = math.sqrt(sum(weight * weight for weight in b.values()))
    if denom_a == 0 or denom_b == 0:
        return 0.0
    numerator = sum(weight_a * b.get(token, 0.0) for token, weight_a in a.items())
    return numerator / (denom_a * denom_b)


def _summarize_event_text(value: str) -> str:
    return _short_text(value, MAX_MEMORY_SNIPPET_LEN)


def _goal_tags(goal: str) -> tuple[str, ...]:
    return tuple(normalize_tag(word) for word in goal.split() if word)[:3]


def _extract_event_notes(state: GameState, events: list[Event]) -> list[tuple[str, str, tuple[str, ...]]]:
    phase = get_phase(state.progress)
    room_tag = f"room_{normalize_tag(state.player.location)}"
    goal_tags = _goal_tags(state.active_goal)
    notes: list[tuple[str, str, tuple[str, ...]]] = []

    for event in events:
        if event.type in {
            "look",
            "help",
            "inventory",
            "move_failed",
            "take_failed",
            "use_failed",
            "talk_failed",
            "unknown",
        }:
            continue

        base_tags = (room_tag, f"goal_{goal_tags[0]}" if goal_tags else "goal", phase)

        if event.type == "talk":
            npc_id = event.entities[0] if event.entities else "npc_unknown"
            dialogue = event.metadata.get("dialogue", "")
            relation_phrase = f"Relationship note: spoke with {npc_id}."
            if dialogue:
                relation_phrase = f"{relation_phrase} {dialogue}"
            tags = (f"npc_{normalize_tag(npc_id)}", "relationship", "lore", "npc")
            notes.append((relation_phrase, "relationship", base_tags + tags))
            continue

        if event.type == "take":
            item_id = event.entities[0] if event.entities else "an item"
            notes.append(
                (
                    f"Collected {item_id} and added it to inventory.",
                    "lore",
                    base_tags + (f"item_{normalize_tag(item_id)}", "item", "inventory"),
                )
            )
            continue

        if event.type == "move":
            from_id = event.entities[0] if event.entities else "somewhere"
            to_id = event.entities[1] if len(event.entities) > 1 else "unknown"
            notes.append(
                (
                    f"Moved from {from_id} to {to_id} while exploring.",
                    "event",
                    base_tags + (f"room_{normalize_tag(to_id)}", "movement", "location"),
                )
            )
            continue

        if event.type == "plot":
            message = event.message_key or "Story advancement"
            notes.append(
                (
                    f"Major story memory: {message}",
                    "plot",
                    base_tags + tuple(f"tag_{normalize_tag(tag)}" for tag in event.tags),
                )
            )
            continue

        if event.message_key:
            notes.append(
                (
                    _summarize_event_text(event.message_key),
                    "event",
                    base_tags,
                )
            )

    return notes


class SqliteVectorMemory:
    def __init__(self, path: str | Path = "runs/storygame_memory.sqlite") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> SqliteVectorMemory:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ARG001
        self.conn.close()

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot TEXT NOT NULL,
                category TEXT NOT NULL,
                summary TEXT NOT NULL,
                tags TEXT NOT NULL,
                vector TEXT NOT NULL,
                created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
            );
            CREATE INDEX IF NOT EXISTS idx_memories_slot ON memories(slot);
            """
        )
        self.conn.commit()

    def add_memory(
        self,
        slot: str,
        summary: str,
        category: str,
        tags: Iterable[str],
    ) -> None:
        normalized_tags = tuple(tag for tag in (normalize_tag(str(tag)) for tag in tags) if tag) or ("general",)
        vector_payload = dict(_vector(f"{category} {' '.join(normalized_tags)} {summary}"))
        self.conn.execute(
            """
            INSERT INTO memories(slot, category, summary, tags, vector)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                slot,
                category,
                _summarize_event_text(summary),
                json.dumps(sorted(set(normalized_tags))),
                json.dumps(vector_payload),
            ),
        )
        self.conn.commit()

    def retrieve(
        self,
        slot: str,
        query_tags: Iterable[str],
        limit: int = MAX_MEMORY_NOTES,
    ) -> tuple[str, ...]:
        normalized_query_tags = {normalize_tag(tag) for tag in query_tags if tag}
        if not normalized_query_tags or limit <= 0:
            return tuple()

        payload = " ".join(sorted(normalized_query_tags))
        query_vector = _vector(payload)

        rows = self.conn.execute(
            "SELECT id, summary, tags, vector, created_at FROM memories WHERE slot = ?",
            (slot,),
        ).fetchall()

        scored: list[tuple[float, int, int, str]] = []
        for row in rows:
            note_tags = set(json.loads(row["tags"]))
            if not note_tags.intersection(normalized_query_tags):
                continue
            vector = {word: float(weight) for word, weight in json.loads(row["vector"]).items()}
            score = _cosine(query_vector, vector)
            if score <= 0:
                continue
            scored.append((score, row["created_at"], row["id"], row["summary"]))

        scored.sort(key=lambda entry: (-entry[0], entry[1], entry[2]))
        return tuple(item[3] for item in scored[:limit])

    def ingest_events(self, slot: str, state: GameState, events: list[Event]) -> None:
        for summary, category, tags in _extract_event_notes(state, events):
            self.add_memory(slot, summary, category, tags)
