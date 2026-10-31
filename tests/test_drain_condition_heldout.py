import json
from pathlib import Path

from scripts.ringer.environment_narration import drain_condition_heldout as module


def test_build_is_deterministic_and_balanced(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    assert module.main(["--build", "--out", str(first)]) == 0
    assert module.main(["--build", "--out", str(second)]) == 0
    assert (first / "heldout.json").read_bytes() == (second / "heldout.json").read_bytes()

    rows = json.loads((first / "heldout.json").read_text(encoding="utf-8"))["rows"]
    assert len(rows) >= 40
    assert len({row["id"] for row in rows}) == len(rows)
    assert "storm drain" not in {row["thing"] for row in rows}
    assert len({row["thing"] for row in rows}) >= 3
    assert sum(row["authored"] for row in rows) <= 14
    assert all(row["source"] == row["source_file"] for row in rows)
    assert all(row["narration"] and row["source_ref"] for row in rows)
    assert all("labelable" in row and "labelable_missing_reason" in row for row in rows)


def test_declared_state_is_well_formed_and_missing_state_has_a_reason(tmp_path: Path) -> None:
    output = tmp_path / "heldout"
    module.main(["--build", "--out", str(output)])
    rows = json.loads((output / "heldout.json").read_text(encoding="utf-8"))["rows"]

    drawer = next(
        row
        for row in rows
        if row["thing"] == "drawer"
        and row["declared_state"] is not None
        and "Michelle's memory card" in row["declared_state"]["declared_contents"]
    )
    state = drawer["declared_state"]
    assert set(state) == {
        "source",
        "open_state",
        "declared_contents",
        "hidden_contents_present",
        "fixed",
        "notes",
    }
    assert state["source"].endswith("world.yaml:entity michelle_drawer")
    assert state["open_state"] == "closed"
    assert isinstance(state["declared_contents"], list)
    assert state["hidden_contents_present"] is True
    assert state["fixed"] is True
    assert state["notes"]

    missing = next(row for row in rows if row["id"] == "real-001")
    assert missing["declared_state"] is None
    assert missing["declared_state_missing_reason"]

    fixture = next(row for row in rows if row["labelable"])
    assert fixture["command"]
    assert isinstance(fixture["engine_opened"], bool)
    assert "open_state_after" in fixture
    unlabelable = next(row for row in rows if not row["labelable"])
    assert unlabelable["labelable_missing_reason"]


def test_recorded_turn_fields_are_copied_without_reading_narration() -> None:
    metadata, reason = module._turn_metadata(
        {
            "input": "inspect the drawer",
            "engine_opened": True,
            "focus_open_state_after": "open",
            "focus_open_state_committed": "open",
            "narration": "The drawer is closed.",
        }
    )
    assert reason is None
    assert metadata == {
        "command": "inspect the drawer",
        "engine_opened": True,
        "open_state_after": "open",
        "focus_open_state_committed": "open",
    }


def test_authored_rows_inherit_declared_state_from_their_source(tmp_path: Path) -> None:
    output = tmp_path / "heldout"
    module.main(["--build", "--out", str(output)])
    rows = json.loads((output / "heldout.json").read_text(encoding="utf-8"))["rows"]
    real_rows = [row for row in rows if not row["authored"]]
    for authored in (row for row in rows if row["authored"]):
        source = next(
            row
            for row in real_rows
            if (row["thing"], row["source_file"], row["source_ref"])
            == (authored["thing"], authored["source_file"], authored["source_ref"])
        )
        assert authored["declared_state"] == source["declared_state"]
        assert authored["declared_state_missing_reason"] == source["declared_state_missing_reason"]
        assert authored["command"] == source["command"]
        assert authored["engine_opened"] == source["engine_opened"]
        assert authored["open_state_after"] == source["open_state_after"]
        assert authored["focus_open_state_committed"] == source["focus_open_state_committed"]
        assert authored["labelable"] == source["labelable"]
        assert authored["labelable_missing_reason"] == source["labelable_missing_reason"]


def test_blind_sheet_is_deterministic_and_does_not_expose_metadata(tmp_path: Path) -> None:
    heldout = tmp_path / "heldout"
    first = tmp_path / "sheet-one"
    second = tmp_path / "sheet-two"
    module.main(["--build", "--out", str(heldout)])
    heldout_path = heldout / "heldout.json"
    module.main(["--blind-sheet", "--heldout", str(heldout_path), "--out", str(first)])
    module.main(["--blind-sheet", "--heldout", str(heldout_path), "--out", str(second)])

    first_sheet = (first / "blind_sheet.md").read_text(encoding="utf-8")
    heldout_rows = json.loads(heldout_path.read_text())["rows"]
    labelable_rows = [row for row in heldout_rows if row["labelable"]]
    assert first_sheet == (second / "blind_sheet.md").read_text(encoding="utf-8")
    assert first_sheet.count("Narration:") == len(labelable_rows)
    assert first_sheet.count("Command:") == len(labelable_rows)
    assert first_sheet.count("Declared:") == len(labelable_rows)
    assert "[thing]" in first_sheet
    assert "the the object" not in first_sheet
    assert "the drawer" not in first_sheet.lower()
    for forbidden in (
        "source_file",
        "source_ref",
        "bench/results",
        "data/stories",
        "drawer",
        "passenger seat",
        "truck",
        "laptop",
        "forbidden",
        "clean",
    ):
        assert forbidden not in first_sheet.lower()

    key = json.loads((first / "blind_key.json").read_text(encoding="utf-8"))
    assert {entry["row_index"] for entry in key.values()} == set(
        row_index for row_index, row in enumerate(heldout_rows, start=1) if row["labelable"]
    )
    unlabelable = json.loads((first / "unlabelable.json").read_text(encoding="utf-8"))["rows"]
    assert {row["id"] for row in unlabelable} == {row["id"] for row in heldout_rows if not row["labelable"]}
    assert all(row["reason"] for row in unlabelable)
