from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from scripts.ringer.stage7.three_c_prefix import (
    SESSION_ID,
    _canonical_dump,
    _prefix_count,
    build,
)
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.persistence import RuntimeSaveError, RuntimeStateSqliteStore
from tests._legacy_package import legacy_package
from tests.test_canon_journey import PACKAGE, UNCLOCKED_JOURNEY, _ScriptedProvider


@pytest.fixture(scope="module")
def prefix_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("three-c-prefix")
    build(output)
    return output


def _package():
    return legacy_package(PACKAGE, {"k_sl_1a_a_r1"})


def test_prefix_round_trip_and_payload_hash(prefix_dir: Path, tmp_path: Path) -> None:
    package = _package()
    store = RuntimeStateSqliteStore(prefix_dir / "checkpoint.sqlite")
    loaded = store.load(SESSION_ID, package)
    assert loaded.current_scene_id == "3B"
    assert _canonical_dump(loaded) == _canonical_dump(store.load(SESSION_ID, package))

    tampered_path = tmp_path / "tampered.sqlite"
    shutil.copy2(prefix_dir / "checkpoint.sqlite", tampered_path)
    store = RuntimeStateSqliteStore(tampered_path)
    with sqlite3.connect(tampered_path) as connection:
        connection.execute(
            "UPDATE runtime_snapshots SET payload_hash = ? WHERE session_id = ?",
            ("tampered", SESSION_ID),
        )
        connection.commit()
    with pytest.raises(RuntimeSaveError, match="integrity check failed"):
        store.load(SESSION_ID, package)


def test_prefix_loaded_state_has_real_3b_reveals_and_facts(prefix_dir: Path) -> None:
    package = _package()
    state = RuntimeStateSqliteStore(prefix_dir / "checkpoint.sqlite").load(SESSION_ID, package)
    committed = {record_id for record in state.turn_records for record_id in record.reveal_ids}
    assert state.current_scene_id == "3B"
    assert {"k_sl_3b_a_r1", "k_sl_3b_e_r1", "k_sl_3b_b_r1", "k_sl_3b_d_r1", "k_sl_3b_c_r1"} <= committed
    assert any(fact.predicate == "relay_open" and fact.value == "true" for fact in state.facts.asserted)
    assert any(fact.predicate == "scene_3b_entry_known" for fact in state.facts.asserted)


def test_one_scripted_turn_from_prefix_reaches_3c_and_renders_entry(prefix_dir: Path) -> None:
    package = _package()
    state = RuntimeStateSqliteStore(prefix_dir / "checkpoint.sqlite").load(SESSION_ID, package)
    provider = _ScriptedProvider(package)
    engine = RuntimeEngine(state, provider)
    selection = UNCLOCKED_JOURNEY[_prefix_count(package)][0]
    provider.selected = [selection] if selection else []
    result = engine.turn("Act on the strongest available lead.")
    entry_text = next(scene.metadata.entry_text for scene in package.scenes if scene.metadata.scene_id == "3C")
    assert state.current_scene_id == "3C"
    assert entry_text in {segment.text for segment in result.segments}


def test_two_builds_are_byte_identical(tmp_path: Path) -> None:
    first = tmp_path / "one"
    second = tmp_path / "two"
    build(first)
    build(second)
    assert (first / "prefix.json").read_bytes() == (second / "prefix.json").read_bytes()
    payload = json.loads((first / "prefix.json").read_text(encoding="utf-8"))
    assert payload["scene"] == "3B"
    assert payload["turn_index"] == 63
