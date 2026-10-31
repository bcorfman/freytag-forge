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
    root.mkdir()
    (root / "world.yaml").write_text(
        yaml.safe_dump(
            {
                "story_id": "small_audit_story",
                "protagonist_id": "hero",
                "locations": [{"id": "room", "name": "quiet room"}],
                "npcs": [{"id": "hero", "name": "the hero"}],
                "items": [
                    {"id": "chest", "name": "oak chest", "fixed": True, "kind": "container"},
                    {
                        "id": "amber_bead",
                        "name": "amber bead",
                        "aliases": ["bead"],
                        "hidden": True,
                    },
                    {
                        "id": "secret_letter",
                        "name": "secret letter",
                        "aliases": ["note"],
                        "hidden": True,
                    },
                    {"id": "character_token", "name": "character token", "hidden": True},
                    {"id": "action_result", "name": "action result", "hidden": True},
                    {"id": "lost_coin", "name": "lost coin", "hidden": True},
                ],
                "facts": [
                    "scene_1a_entry_known",
                    "bead_found",
                    "letter_delivered",
                    "character_token_given",
                    "action_result_found",
                    "chest_pointed_out",
                ],
                "fact_effects": {
                    "bead_found": [
                        {"move": "amber_bead", "parent": "hero"},
                        {"reveal": "amber_bead"},
                    ],
                    "letter_delivered": [
                        {"move": "secret_letter", "parent": "hero"},
                        {"reveal": "secret_letter"},
                    ],
                    "character_token_given": [
                        {"move": "character_token", "parent": "hero"},
                        {"reveal": "character_token"},
                    ],
                    "action_result_found": [
                        {"move": "action_result", "parent": "room"},
                        {"reveal": "action_result"},
                    ],
                },
                "disclosure_guards": [{"id": "bead_guard", "terms": ["amber bead"], "unlock_fact": "bead_found"}],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (root / "plot.md").write_text(
        """# Small Audit Story

## Scene 1A — The Quiet Room

---
scene_id: 1A
location_id: room
freytag_phase: exposition
objective: Find what the room conceals
participant_ids: [hero]
item_ids: [chest, amber_bead, secret_letter, character_token, action_result, lost_coin]
item_placements:
  chest: {parent: room}
  amber_bead: {parent: chest, under: true}
  secret_letter: {parent: chest, under: true}
  character_token: {parent: hero}
  action_result: {parent: room}
  lost_coin: {parent: chest, under: true}
entry_text: "An oak chest waits in the quiet room. A sketch mentions an amber bead."
transition_ids: []
bridge_text: {}
---

### Scene 1A.1 — The Chest

**Details:** oak chest; dusty floor; amber bead sketch

The oak chest waits beneath the window.
""",
        encoding="utf-8",
    )
    (root / "storylets.md").write_text(
        """# Small Audit Storylets

### SL-1A-A — The Chest

**Source beats:** [The Chest](plot.md#scene-1a1--the-chest)

**Allowed scene:** `1A`

**Available when**
- The chest is in the room.

**Participants / items**
- The hero
- The oak chest

**Dramatic purpose**
- Make the concealed objects discoverable.

**Possible realizations**
- The hero searches the chest.

**Effects**
- The authored reveal facts may be asserted.

**Completion**
- The room has been searched.

**Abort**
- The hero leaves the room.

**Protected boundary**
- The hidden objects remain package-owned.

**Pacing window**
- earliest: `turn 0`
- target: `turn 1`
- latest: `turn 2`
""",
        encoding="utf-8",
    )
    (root / "storylet-routes.yaml").write_text(
        yaml.safe_dump(
            {
                "story_id": "small_audit_story",
                "contract": {
                    "canonical_scene_chain": ["1A"],
                    "sole_ending_scene_id": "1A",
                },
                "storylets": [
                    {
                        "id": "SL-1A-A",
                        "scene_id": "1A",
                        "title": "The Chest",
                        "activation": {
                            "conditions": [],
                            "pacing": {"earliest_turn": 0, "target_turn": 1, "latest_turn": 2},
                        },
                        "pressure_role": "discovery",
                        "realization_options": [
                            {
                                "id": "SL-1A-A-R1",
                                "dramatic_intent": "Reveal the authored room clues",
                                "operations": [
                                    {"op": "assert", "fact_id": "bead_found", "value": True},
                                    {"op": "assert", "fact_id": "letter_delivered", "value": True},
                                    {"op": "assert", "fact_id": "character_token_given", "value": True},
                                    {"op": "assert", "fact_id": "action_result_found", "value": True},
                                    {"op": "assert", "fact_id": "chest_pointed_out", "value": True},
                                ],
                            }
                        ],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (root / "knowledge.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "2.0",
                "facts": [
                    {"id": fact_id, "purpose": fact_id}
                    for fact_id in (
                        "scene_1a_entry_known",
                        "bead_found",
                        "letter_delivered",
                        "character_token_given",
                        "action_result_found",
                        "chest_pointed_out",
                    )
                ],
                "scene_frames": [{"scene_id": "1A", "pressure": "The room is quiet."}],
                "knowledge": [
                    {
                        "id": "k_entry",
                        "statement": "The room is quiet.",
                        "aliases": ["quiet room"],
                        "audience": {"kind": "public", "player_visible": True},
                        "available_in_scenes": ["1A"],
                        "establishes": [{"op": "assert", "fact_id": "scene_1a_entry_known", "value": True}],
                        "source": {"kind": "scene_entry"},
                    },
                    {
                        "id": "k_bead_search",
                        "statement": "The amber bead is found.",
                        "reach_entity_ids": ["chest"],
                        "action_evidence": [["search"], ["chest"]],
                        "earn_when": "searches beneath the chest",
                        "delivery_text": "The amber bead is under the oak chest.",
                        "aliases": ["bead found"],
                        "audience": {"kind": "public", "player_visible": True},
                        "available_in_scenes": ["1A"],
                        "establishes": [{"op": "assert", "fact_id": "bead_found", "value": True}],
                        "source": {
                            "kind": "storylet_realization",
                            "storylet_id": "SL-1A-A",
                            "realization_id": "SL-1A-A-R1",
                        },
                    },
                    {
                        "id": "k_letter_handoff",
                        "statement": "The courier has delivered the secret letter.",
                        "voiceable": False,
                        "aliases": ["letter delivered"],
                        "audience": {"kind": "public", "player_visible": True},
                        "available_in_scenes": ["1A"],
                        "establishes": [{"op": "assert", "fact_id": "letter_delivered", "value": True}],
                        "source": {
                            "kind": "storylet_realization",
                            "storylet_id": "SL-1A-A",
                            "realization_id": "SL-1A-A-R1",
                        },
                    },
                    {
                        "id": "k_chest_pointer",
                        "statement": "The chest has a shadowed underside.",
                        "reach_entity_ids": ["chest"],
                        "action_evidence": [["inspect"], ["chest"]],
                        "earn_when": "inspects the chest without searching beneath it",
                        "repeatable": True,
                        "entity_ids": ["hero", "chest"],
                        "requires": [{"fact_id": "bead_found", "equals": False}],
                        "aliases": ["chest pointed out"],
                        "audience": {"kind": "public", "player_visible": True},
                        "available_in_scenes": ["1A"],
                        "establishes": [{"op": "assert", "fact_id": "chest_pointed_out", "value": True}],
                        "source": {
                            "kind": "storylet_realization",
                            "storylet_id": "SL-1A-A",
                            "realization_id": "SL-1A-A-R1",
                        },
                    },
                    {
                        "id": "k_character_token_given",
                        "statement": "The hero receives the character token.",
                        "entity_ids": ["hero", "character_token"],
                        "aliases": ["character token given"],
                        "audience": {"kind": "public", "player_visible": True},
                        "available_in_scenes": ["1A"],
                        "establishes": [{"op": "assert", "fact_id": "character_token_given", "value": True}],
                        "source": {
                            "kind": "storylet_realization",
                            "storylet_id": "SL-1A-A",
                            "realization_id": "SL-1A-A-R1",
                        },
                    },
                    {
                        "id": "k_action_result",
                        "statement": "The action result is recorded.",
                        "entity_ids": ["action_result"],
                        "action_evidence": [["perform"], ["action"]],
                        "aliases": ["action result found"],
                        "audience": {"kind": "public", "player_visible": True},
                        "available_in_scenes": ["1A"],
                        "establishes": [{"op": "assert", "fact_id": "action_result_found", "value": True}],
                        "source": {
                            "kind": "storylet_realization",
                            "storylet_id": "SL-1A-A",
                            "realization_id": "SL-1A-A-R1",
                        },
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (root / "handoffs.yaml").write_text(
        yaml.safe_dump(
            {
                "deliveries": [
                    {
                        "fact_id": "letter_delivered",
                        "scene_id": "1A",
                        "source_kind": "message",
                        "source_entity_id": "hero",
                        "must_convey": [["courier"], ["secret letter"]],
                        "fallback_text": "The courier delivers the secret letter.",
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (root / "pacing.yaml").write_text(
        yaml.safe_dump(
            {
                "budget_seconds": 180,
                "scenes": [{"scene_id": "1A", "min_turns": 0, "nudge_after_turns": 1, "handoff_after_turns": 2}],
                "transitions": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
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
