from pathlib import Path

from scripts.qualification import coverage_ledger
from scripts.qualification.coverage_ledger import static_ledger
from tests.test_game_path_journeys import KNOWN_UNREACHABLE, PACKAGE

APPROVED = set(KNOWN_UNREACHABLE)


def test_static_ledger_has_nine_scenes_and_statuses() -> None:
    ledger = static_ledger(PACKAGE, KNOWN_UNREACHABLE, APPROVED)
    assert tuple(ledger["scenes"]) == ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C")
    rows = {row["id"]: row for data in ledger["scenes"].values() for row in data["storylets"]}
    assert {key for key in KNOWN_UNREACHABLE if rows[key]["status"] == "retired_or_unreachable"} == set(
        KNOWN_UNREACHABLE
    )
    player_ids = {
        item.id
        for item in PACKAGE.knowledge.knowledge
        if item.source.kind == "storylet_realization"
        and item.audience.kind == "public"
        and item.audience.player_visible
    }
    assert all(
        rows[item_id]["status"] == "reachable_by_nightly_journey" for item_id in player_ids - set(KNOWN_UNREACHABLE)
    )
    assert any(row["status"] == "observer_only" for row in rows.values())
    assert all(row["status"] != "UNACCOUNTED" for row in rows.values())


def test_missing_approved_unreachable_is_unaccounted() -> None:
    missing = next(iter(KNOWN_UNREACHABLE))
    ledger = static_ledger(
        PACKAGE,
        {key: value for key, value in KNOWN_UNREACHABLE.items() if key != missing},
        set(KNOWN_UNREACHABLE),
    )
    assert missing in ledger["unaccounted"]


def test_main_rejects_missing_retirement_pin(tmp_path, monkeypatch) -> None:
    missing = next(iter(KNOWN_UNREACHABLE))
    monkeypatch.setattr("tests.test_game_path_journeys.KNOWN_UNREACHABLE", {missing: "synthetic"})
    assert coverage_ledger.main(["--write", str(tmp_path / "ledger.md")]) != 0


def test_static_ledger_is_deterministic() -> None:
    assert static_ledger(PACKAGE, KNOWN_UNREACHABLE, APPROVED) == static_ledger(PACKAGE, KNOWN_UNREACHABLE, APPROVED)


def test_committed_header_counts_match() -> None:
    ledger = static_ledger(PACKAGE, KNOWN_UNREACHABLE, APPROVED)
    text = Path(".plans/qualification/coverage-ledger.md").read_text()
    assert all(f"{scene}: {count}" in text for scene, count in ledger["header"]["realization_counts"].items())
