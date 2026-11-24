from __future__ import annotations

import json
from pathlib import Path

from tests.test_game_path_journeys import KNOWN_UNREACHABLE, PACKAGE

APPROVED_PATH = Path(__file__).parent / "fixtures" / "known_unreachable_approved.json"


def _approved() -> dict[str, object]:
    return json.loads(APPROVED_PATH.read_text(encoding="utf-8"))


def test_known_unreachable_is_subset_of_owner_approved_ids() -> None:
    approved = _approved()
    assert set(KNOWN_UNREACHABLE) <= set(approved["ids"]), (
        "new unreachable story content: make it reachable or get an owner decision, never add it to the pin"
    )


def test_approved_ids_are_player_visible_storylet_realizations() -> None:
    approved = _approved()
    player_ids = {
        item.id
        for item in PACKAGE.knowledge.knowledge
        if item.source.kind == "storylet_realization"
        and item.audience.kind == "public"
        and item.audience.player_visible
    }
    assert set(approved["ids"]) <= player_ids


def test_approval_manifest_is_sorted_unique_and_bounded() -> None:
    approved = _approved()
    ids = approved["ids"]
    assert approved["max_count"] == len(ids)
    assert len(ids) == len(set(ids))
    assert ids == sorted(ids)


def test_known_unreachable_reasons_are_non_empty_strings() -> None:
    assert all(isinstance(reason, str) and reason.strip() for reason in KNOWN_UNREACHABLE.values())
