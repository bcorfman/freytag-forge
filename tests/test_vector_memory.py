from __future__ import annotations

from random import Random

from storygame.cli import run_turn
from storygame.engine.parser import parse_command
from storygame.engine.world import build_default_state
from storygame.llm.context import NarrationContext
from storygame.memory import SqliteVectorMemory


def test_vector_memory_store_retrieves_relevant_notes(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    with SqliteVectorMemory(db_path) as store:
        store.add_memory(
            "demo",
            "Keeper opened the archive corridors after the bell phrase.",
            "lore",
            ("npc_keeper", "room_archives", "lore"),
        )
        store.add_memory(
            "demo",
            "A crate of fish is waiting at the harbor.",
            "lore",
            ("room_harbor", "market"),
        )
        store.add_memory(
            "demo",
            "Moonstone glows brighter when the bell rings.",
            "plot",
            ("plot", "lore", "moonstone", "goal"),
        )

        hits_for_keeper = store.retrieve("demo", ("npc_keeper", "keeper", "lore"))
        assert hits_for_keeper
        assert "Keeper opened the archive corridors after the bell phrase." in hits_for_keeper[0]

        hits_for_market = store.retrieve("demo", ("room_harbor",))
        assert hits_for_market
        assert hits_for_market[0].startswith("A crate of fish")


def test_run_turn_stores_and_retrieves_soft_memory(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    state = build_default_state(seed=77)
    rng = Random(77)

    captured: list[NarrationContext] = []

    class _CaptureNarrator:
        def generate(self, context: NarrationContext) -> str:
            captured.append(context)
            return ""

    with SqliteVectorMemory(db_path) as memory_store:
        memory_store.add_memory(
            "run",
            "The keeper trusts your judgment after repeated visits.",
            "relationship",
            ("npc_keeper", "room_archives", "goal"),
        )

        state, _lines, _action, _beat, _continued = run_turn(
            state,
            "go north",
            rng,
            _CaptureNarrator(),
            memory_store=memory_store,
            memory_slot="run",
        )
        state, _lines, _action, _beat, _continued = run_turn(
            state,
            "go east",
            rng,
            _CaptureNarrator(),
            memory_store=memory_store,
            memory_slot="run",
        )
        state, _lines, _action, _beat, _continued = run_turn(
            state,
            "talk keeper",
            rng,
            _CaptureNarrator(),
            memory_store=memory_store,
            memory_slot="run",
        )

    assert captured
    assert any(
        "keeper trusts your judgment" in "\n".join(context.memory_fragments) for context in captured
    )
    with SqliteVectorMemory(db_path) as reopened_store:
        retrieved_notes = reopened_store.retrieve("run", ("npc_keeper", "relationship"))
        assert any("spoke with keeper" in note.lower() for note in retrieved_notes)
