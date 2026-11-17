from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

from scripts.hidden_thing_audit import _markdown, audit_package
from storygame.story_package.loader import load_story_package

PACKAGE = Path("data/stories/continuity-initiative")
SCRIPT = Path("scripts/hidden_thing_audit.py")


def _write_package(root: Path) -> Path:
    source = root / "source"
    scenes = source / "scenes"
    scenes.mkdir(parents=True)

    def write(path: Path, document: object) -> None:
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    write(
        source / "story.yaml",
        {
            "schema": 1,
            "story": "small_audit_story",
            "genre": "",
            "protagonist": "hero",
            "budget_seconds": 180,
            "scenes": ["1A"],
            "principal_characters": ["hero"],
        },
    )
    write(
        source / "catalog.yaml",
        {
            "schema": 1,
            "places": {"room": {"name": "quiet room"}},
            "characters": {"hero": {"name": "the hero", "bio": "The hero."}},
            "items": {
                "chest": {"name": "oak chest", "fixed": True, "kind": "container"},
                "amber_bead": {"name": "amber bead", "aliases": ["bead"], "hidden": True},
                "secret_letter": {"name": "secret letter", "aliases": ["note"], "hidden": True},
                "character_token": {"name": "character token", "hidden": True},
                "action_result": {"name": "action result", "hidden": True},
                "lost_coin": {"name": "lost coin", "hidden": True},
            },
            "groups": {},
            "kinds": {},
            "props": {},
            "connections": {},
            "protected_knowledge": [],
            "disclosure_guards": {"bead_guard": {"terms": ["amber bead"], "unlock_fact": "bead_found"}},
            "unplaced_facts": {},
        },
    )
    write(
        scenes / "1A.yaml",
        {
            "schema": 1,
            "scene": "1A",
            "location": "room",
            "objective": "Find what the room conceals",
            "freytag_phase": "exposition",
            "pressure": "The room is quiet.",
            "turns": {"min": 0, "nudge": 1, "handoff": 2},
            "participants": ["hero"],
            "items": ["chest", "amber_bead", "secret_letter", "character_token", "action_result", "lost_coin"],
            "entry": "An oak chest waits in the quiet room. A sketch mentions an amber bead.",
            "entry_claims": [{"claim_id": "k_entry", "says": "The room is quiet.", "audience": "public"}],
            "brief": "",
            "outline": [
                {
                    "id": "1A.1",
                    "anchor": "scene-1a1--the-chest",
                    "title": "The Chest",
                    "details": ["oak chest", "dusty floor", "amber bead sketch"],
                    "prose": "The oak chest waits beneath the window.",
                }
            ],
            "facts": {
                "bead_found": {
                    "purpose": "The amber bead is found.",
                    "on_assert": [{"move": "amber_bead", "parent": "hero"}, {"reveal": "amber_bead"}],
                },
                "letter_delivered": {
                    "purpose": "The secret letter is delivered.",
                    "delivery": {
                        "source_kind": "message",
                        "source_entity": "hero",
                        "fallback_text": "The courier delivers the secret letter.",
                        "costs": {},
                    },
                    "on_assert": [{"move": "secret_letter", "parent": "hero"}, {"reveal": "secret_letter"}],
                },
                "character_token_given": {
                    "purpose": "The hero receives the character token.",
                    "on_assert": [{"move": "character_token", "parent": "hero"}, {"reveal": "character_token"}],
                },
                "action_result_found": {
                    "purpose": "The action result is recorded.",
                    "on_assert": [{"move": "action_result", "parent": "room"}, {"reveal": "action_result"}],
                },
                "chest_pointed_out": {"purpose": "The chest is pointed out."},
            },
            "placements": {
                "chest": {"parent": "room"},
                "amber_bead": {"parent": "chest", "under": True},
                "secret_letter": {"parent": "chest", "under": True},
                "character_token": {"parent": "hero"},
                "action_result": {"parent": "room"},
                "lost_coin": {"parent": "chest", "under": True},
            },
            "reveals": [
                {
                    "id": "chest_search",
                    "storylet_id": "SL-1A-A",
                    "title": "The Chest",
                    "guidance": {
                        "pressure_role": "discovery",
                        "window": {"earliest_turn": 0, "target_turn": 1, "latest_turn": 2},
                    },
                    "from_outline": ["1A.1"],
                    "variants": {
                        "search": {
                            "realization_id": "SL-1A-A-R1",
                            "intent": "Reveal the authored room clues",
                            "commits": {
                                "bead_found": True,
                                "letter_delivered": True,
                                "character_token_given": True,
                                "action_result_found": True,
                                "chest_pointed_out": True,
                            },
                            "claim_id": "k_bead_search",
                            "says": "The amber bead is found.",
                            "reach": ["chest"],
                            "earn_when": "searches beneath the chest",
                            "text": "The amber bead is under the oak chest.",
                            "audience": "public",
                            "extra_claims": [
                                {
                                    "claim_id": "k_chest_pointer",
                                    "says": "The chest has a shadowed underside.",
                                    "text": "The chest has a shadowed underside.",
                                    "commits_subset": {"chest_pointed_out": True},
                                    "when": {"bead_found": False},
                                    "entities": ["hero", "chest"],
                                    "reach": ["chest"],
                                    "repeatable": True,
                                    "audience": "public",
                                },
                                {
                                    "claim_id": "k_letter_handoff",
                                    "says": "The courier has delivered the secret letter.",
                                    "text": "The courier delivers the secret letter.",
                                    "commits_subset": {"letter_delivered": True},
                                    "reach": [],
                                    "voiceable": False,
                                    "audience": "public",
                                },
                                {
                                    "claim_id": "k_character_token_given",
                                    "says": "The hero receives the character token.",
                                    "text": "The hero receives the character token.",
                                    "commits_subset": {"character_token_given": True},
                                    "entities": ["hero", "character_token"],
                                    "audience": "public",
                                },
                                {
                                    "claim_id": "k_action_result",
                                    "says": "The action result is recorded.",
                                    "text": "The action result is recorded.",
                                    "commits_subset": {"action_result_found": True},
                                    "entities": ["action_result"],
                                    "audience": "public",
                                },
                            ],
                        }
                    },
                }
            ],
        },
    )
    write(
        scenes / "1A.match.yaml",
        {
            "schema": 1,
            "scene": "1A",
            "claims": {
                "k_entry": {"aliases": ["quiet room"]},
                "k_bead_search": {"aliases": ["bead found"], "action_evidence": [["search"], ["chest"]]},
                "k_letter_handoff": {
                    "aliases": ["letter delivered"],
                    "action_evidence": [["deliver"]],
                },
                "k_chest_pointer": {"aliases": ["chest pointed out"], "action_evidence": [["inspect"], ["chest"]]},
                "k_character_token_given": {
                    "aliases": ["character token given"],
                    "action_evidence": [["receive"]],
                },
                "k_action_result": {"aliases": ["action result found"], "action_evidence": [["perform"], ["action"]]},
            },
            "deliveries": {"letter_delivered": {"must_convey": [["courier"], ["secret letter"]]}},
        },
    )
    (root / "ownership.yaml").write_text("schema: 1\ncatalog: compiled\nscenes:\n  1A: compiled\n", encoding="utf-8")
    return root


def test_synthetic_audit_reports_search_and_unreached_items(tmp_path: Path) -> None:
    package = load_story_package(_write_package(tmp_path / "synthetic"))
    rows = {row["id"]: row for row in audit_package(package)["items"]}

    assert rows["amber_bead"]["earn_kind"] == "search"
    assert rows["amber_bead"]["placements"] == [
        {
            "scene_id": "1A",
            "parent_id": "chest",
            "parent_name": "oak chest",
            "relation": "under",
            "fixed": True,
        }
    ]
    assert rows["amber_bead"]["delivery_names_item"] is True
    assert rows["amber_bead"]["has_disclosure_guard"] is True
    assert rows["amber_bead"]["pointer"] == "k_chest_pointer"
    assert rows["amber_bead"]["public_mentions_before_reveal"] == [
        {
            "scene_id": "1A",
            "source": "entry",
            "text": "An oak chest waits in the quiet room. A sketch mentions an amber bead.",
        },
        {"scene_id": "1A", "source": "details", "text": "amber bead sketch"},
    ]

    assert rows["lost_coin"]["earn_kind"] == "unreached"
    assert rows["lost_coin"]["delivery_names_item"] == "n/a"
    assert rows["lost_coin"]["reveal_path"]["facts"] == []


def test_synthetic_character_parent_is_given_by_character(tmp_path: Path) -> None:
    package = load_story_package(_write_package(tmp_path / "synthetic"))
    rows = {row["id"]: row for row in audit_package(package)["items"]}

    assert rows["character_token"]["earn_kind"] == "given_by_character"


def test_synthetic_non_character_action_result_is_action_result(tmp_path: Path) -> None:
    package = load_story_package(_write_package(tmp_path / "synthetic"))
    rows = {row["id"]: row for row in audit_package(package)["items"]}

    assert rows["action_result"]["earn_kind"] == "action_result"


def test_synthetic_handoff_is_handoff_only(tmp_path: Path) -> None:
    package = load_story_package(_write_package(tmp_path / "synthetic"))
    rows = {row["id"]: row for row in audit_package(package)["items"]}

    assert rows["secret_letter"]["earn_kind"] == "handoff_only"
    assert rows["secret_letter"]["delivery_names_item"] is True
    assert rows["secret_letter"]["has_disclosure_guard"] is False


def test_continuity_hidden_ids_are_derived_and_audit_is_read_only() -> None:
    package = load_story_package(PACKAGE)
    expected = {item.id for item in package.world.items if item.hidden}
    before = {path: path.stat().st_mtime_ns for path in PACKAGE.iterdir() if path.is_file()}

    report = audit_package(package)

    assert {item["id"] for item in report["items"]} == expected
    assert {path: path.stat().st_mtime_ns for path in PACKAGE.iterdir() if path.is_file()} == before


def test_json_output_parses_and_matches_markdown_row_count(tmp_path: Path) -> None:
    package = _write_package(tmp_path / "synthetic")
    environment = dict(os.environ, PYTHONPATH=str(Path.cwd()), TMPDIR="/tmp")
    json_result = subprocess.run(
        [sys.executable, str(SCRIPT), str(package), "--json"],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    markdown_result = subprocess.run(
        [sys.executable, str(SCRIPT), str(package)],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )

    data = json.loads(json_result.stdout)
    summary = markdown_result.stdout.split("## Details", 1)[0]
    table_rows = [line for line in summary.splitlines() if line.startswith("| ") and not line.startswith("| ---")]
    assert len(table_rows) - 1 == len(data["items"])
    assert "## Not checked" in markdown_result.stdout
    assert "Legend:" in markdown_result.stdout
    assert _markdown(data).count("## Not checked") == 1
