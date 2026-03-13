from __future__ import annotations

from random import Random

from storygame.cli import run_turn
from storygame.engine.state import Event
from storygame.engine.world import build_default_state
from storygame.llm.context import NarrationContext
from storygame.memory import (
    SqliteVectorMemory,
    _cosine,
    _extract_event_notes,
    _short_text,
    _tokenize_text,
    _vector,
)


def test_vector_memory_store_retrieves_relevant_notes(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    with SqliteVectorMemory(db_path) as store:
        store.add_memory(
            "demo",
            "Keeper opened the archive corridors after the bell phrase.",
            "lore",
            ("npc_guide", "room_records", "lore"),
        )
        store.add_memory(
            "demo",
            "A crate of supplies is waiting at the district gate.",
            "lore",
            ("room_gate", "market"),
        )
        store.add_memory(
            "demo",
            "Artifact shards glow brighter when the alarm rings.",
            "plot",
            ("plot", "lore", "artifact", "goal"),
        )

        hits_for_keeper = store.retrieve("demo", ("npc_guide", "guide", "lore"))
        assert hits_for_keeper
        assert "Keeper opened the archive corridors after the bell phrase." in hits_for_keeper[0]

        hits_for_market = store.retrieve("demo", ("room_gate",))
        assert hits_for_market
        assert hits_for_market[0].startswith("A crate of supplies")


def test_run_turn_stores_and_retrieves_soft_memory(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    state = build_default_state(seed=77)
    rng = Random(77)
    room_id = state.player.location
    npc_id = state.world.rooms[room_id].npc_ids[0]

    captured: list[NarrationContext] = []

    class _CaptureNarrator:
        def generate(self, context: NarrationContext) -> str:
            captured.append(context)
            return ""

    with SqliteVectorMemory(db_path) as memory_store:
        memory_store.add_memory(
            "run",
            "A key ally trusts your judgment after repeated visits.",
            "relationship",
            (f"npc_{npc_id}", f"room_{room_id}", "goal"),
        )

        state, _lines, _action, _beat, _continued = run_turn(
            state,
            "look",
            rng,
            _CaptureNarrator(),
            memory_store=memory_store,
            memory_slot="run",
        )
        state, _lines, _action, _beat, _continued = run_turn(
            state,
            f"talk {npc_id}",
            rng,
            _CaptureNarrator(),
            memory_store=memory_store,
            memory_slot="run",
        )

    assert captured
    assert any("trusts your judgment" in "\n".join(context.memory_fragments) for context in captured)
    with SqliteVectorMemory(db_path) as reopened_store:
        retrieved_notes = reopened_store.retrieve("run", (f"npc_{npc_id}", "relationship"))
        assert any("spoke with" in note.lower() for note in retrieved_notes)


def test_event_extraction_tracks_progressive_memory_event_types():
    state = build_default_state(seed=88)

    notes = _extract_event_notes(
        state,
        [
            Event(type="look", message_key="you looked around", entities=("district_gate",), turn_index=1),
            Event(
                type="talk",
                message_key="",
                entities=("guide",),
                tags=("world",),
                turn_index=1,
                metadata={"dialogue": "Archive doors closed."},
            ),
            Event(
                type="take",
                entities=("sea_map",),
                tags=("world",),
                turn_index=1,
                metadata={"item_kind": "clue"},
            ),
            Event(
                type="move",
                entities=("room_a", "room_b"),
                tags=("world",),
                turn_index=1,
            ),
            Event(
                type="plot",
                message_key="plot_twist",
                entities=(),
                tags=("ledger",),
                turn_index=1,
            ),
        ],
    )
    messages = [note[0] for note in notes]
    assert any("Relationship note: spoke with guide" in message for message in messages)
    assert any("Collected sea_map" in message for message in messages)
    assert any("Moved from room_a to room_b" in message for message in messages)
    assert any("Major story memory" in message for message in messages)


def test_event_extraction_skips_junk_and_plain_use_success():
    state = build_default_state(seed=89)
    notes = _extract_event_notes(
        state,
        [
            Event(
                type="take",
                entities=("old_coin",),
                tags=("world",),
                turn_index=1,
                metadata={"item_kind": "junk"},
            ),
            Event(type="use", message_key="use_success", entities=("old_coin",), turn_index=1),
        ],
    )
    assert notes == []


def test_memory_retrieval_with_empty_query_is_noop(tmp_path):
    with SqliteVectorMemory(tmp_path / "memory.sqlite") as store:
        store.add_memory(
            "case",
            "A useful memory for testing.",
            "lore",
            ("test",),
        )
        assert store.retrieve("case", tuple()) == tuple()


def test_memory_helpers_cover_text_and_vector_paths():
    assert _short_text("abc", max_len=3) == "abc"
    assert _short_text("abcdef", max_len=4) == "a..."
    assert _tokenize_text("Bell! Ringing at the district gate.") == ("bell", "ringing", "at", "the", "district", "gate")
    assert _vector("hello hello world") == {"hello": 2.0, "world": 1.0}
    assert _cosine({"a": 1.0}, {"b": 1.0}) == 0.0


def test_ingest_events_adds_take_talk_and_move_notes(tmp_path):
    with SqliteVectorMemory(tmp_path / "ingest.sqlite") as store:
        state = build_default_state(seed=92)
        events = [
            Event(
                type="talk",
                message_key="",
                entities=("guide",),
                metadata={"dialogue": "You compared the ledgers."},
                tags=("world",),
                turn_index=1,
            ),
            Event(
                type="take",
                entities=("artifact_core",),
                metadata={"item_kind": "evidence"},
                tags=("world",),
                turn_index=1,
            ),
            Event(
                type="move",
                entities=("district_gate", "market_lane"),
                tags=("world",),
                turn_index=1,
            ),
        ]
        store.ingest_events("case", state, events)

        notes = store.retrieve("case", ("movement", "inventory", "relationship"))
    assert any("spoke with guide" in note.lower() for note in notes)
    assert any("added it to inventory" in note.lower() for note in notes)
    assert any("exploring" in note.lower() for note in notes)
