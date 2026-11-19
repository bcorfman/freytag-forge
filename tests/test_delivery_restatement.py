from __future__ import annotations

import re
from pathlib import Path

import yaml

from storygame.audit import audit_package
from storygame.story_package.loader import load_story_package
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy, patch_source

LIVE_PACKAGE = Path("data/stories/continuity-initiative")
FROZEN_PACKAGE = Path("bench/frozen/continuity-pre-richer-1c")
RESTATEMENT_IDS = {"k_sl_1a_g_r2", "k_sl_1b_f_r1"}
STOP_WORDS = {"a", "an", "and", "by", "from", "in", "of", "on", "the", "to", "with"}


def _restatement_findings(root: Path) -> list[dict[str, str]]:
    if not (root / "source").is_dir():
        return [finding for finding in audit_package(root)["findings"] if finding["check"] == "delivery_restates_scene"]

    package = load_story_package(root)
    entities = {
        entity.id: (entity.name, *entity.aliases, *entity.scoped_aliases)
        for entity in [*package.world.items, *package.world.npcs, *package.world.locations]
    }
    findings = []
    for entry in package.knowledge.knowledge:
        if not entry.delivery_text or not entry.reach_entity_ids or not entry.available_in_scenes:
            continue
        source_scene = yaml.safe_load(
            (root / "source" / "scenes" / f"{entry.available_in_scenes[0]}.yaml").read_text(encoding="utf-8")
        )
        given = {
            word.casefold()
            for entity_id in entry.reach_entity_ids
            for term in entities.get(entity_id, ())
            for word in re.findall(r"[\w’']+", term)
        }
        placement_words: set[str] = set()
        for entity_id in entry.reach_entity_ids:
            placement = source_scene.get("placements", {}).get(entity_id, {})
            for word in re.findall(r"[\w’']+", str(placement.get("text", ""))):
                placement_words.add(word.casefold())
                given.add(word.casefold())
        for sentence in re.split(r"(?<=[.!?])\s+", entry.delivery_text.strip()):
            words = [word.casefold() for word in re.findall(r"[\w’']+", sentence) if word.casefold() not in STOP_WORDS]
            if (
                len(words) >= 4
                and sum(word in given for word in words) / len(words) >= 0.6
                and sum(word in placement_words for word in words) >= 3
            ):
                findings.append(
                    {
                        "check": "delivery_restates_scene",
                        "detail": f"Delivery of '{entry.id}' restates the scene: '{sentence}'",
                    }
                )
    return findings


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def test_the_check_finds_the_known_restatements_in_the_frozen_pre_1c_story() -> None:
    findings = _restatement_findings(FROZEN_PACKAGE)

    assert {
        entry_id for finding in findings for entry_id in RESTATEMENT_IDS if entry_id in finding["detail"]
    } == RESTATEMENT_IDS
    assert all(sum(entry_id in finding["detail"] for entry_id in RESTATEMENT_IDS) == 1 for finding in findings)


def test_the_check_finds_a_restating_sentence_added_to_a_copy(tmp_path: Path) -> None:
    package = compiled_story_copy(tmp_path)
    source_path = package / "source" / "scenes" / "1C.yaml"
    source = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    reveal = next(item for item in source["reveals"] if item["id"] == "sl_1c_e")
    variants = reveal["variants"]
    variants["r1"]["text"] = (
        "Pallets of bottled emergency water stand shrink-wrapped by the loading doors. " + variants["r1"]["text"]
    )
    patch_source(package / "source", "scenes/1C.yaml", "reveals[sl_1c_e].variants", variants)
    load_compiled_copy(package)

    findings = _restatement_findings(package)

    assert len(findings) == 1
    assert "k_sl_1c_e_r1" in findings[0]["detail"]


def test_the_live_story_has_no_restating_deliveries() -> None:
    findings = _restatement_findings(LIVE_PACKAGE)

    assert findings == []


def test_the_three_rewritten_deliveries_say_what_was_decided() -> None:
    package = load_story_package(LIVE_PACKAGE)
    entries = {entry.id: entry for entry in package.knowledge.knowledge}
    expected = {
        "k_sl_1a_g_r2": (
            "On the wall calendar Saturday is circled in her handwriting: K, lemon cake. "
            "It is Kristin's birthday. The photograph beside it shows the two of them laughing at a lake."
        ),
        "k_sl_1b_f_r1": (
            "A bicycle stands on its kickstand where no one will ride it. "
            "Whoever held the dog leash let go in a hurry. "
            "On a picnic blanket two cups sit beside a thermos: one is tipped over, and the other is still half full."
        ),
        "k_sl_1c_e_r1": (
            "The pallets carry the county label on every bottle, and the lot number matches the one on the thermos "
            "in the park."
        ),
    }

    for entry_id, delivery_text in expected.items():
        entry = entries[entry_id]
        assert _collapse_whitespace(entry.delivery_text) == delivery_text
        lowered_delivery = entry.delivery_text.casefold()
        assert all(
            any(alternative.casefold() in lowered_delivery for alternative in group) for group in entry.must_convey
        )
