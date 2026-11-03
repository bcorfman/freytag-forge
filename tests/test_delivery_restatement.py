from __future__ import annotations

import re
import shutil
from pathlib import Path

import yaml

from storygame.audit import audit_package
from storygame.story_package.loader import load_story_package

LIVE_PACKAGE = Path("data/stories/continuity-initiative")
FROZEN_PACKAGE = Path("bench/frozen/continuity-pre-richer-1c")
RESTATEMENT_IDS = {"k_sl_1a_g_r2", "k_sl_1b_f_r1"}


def _restatement_findings(root: Path) -> list[dict[str, str]]:
    return [finding for finding in audit_package(root)["findings"] if finding["check"] == "delivery_restates_scene"]


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def test_the_check_finds_the_known_restatements_in_the_frozen_pre_1c_story() -> None:
    findings = _restatement_findings(FROZEN_PACKAGE)

    assert {
        entry_id for finding in findings for entry_id in RESTATEMENT_IDS if entry_id in finding["detail"]
    } == RESTATEMENT_IDS
    assert all(sum(entry_id in finding["detail"] for entry_id in RESTATEMENT_IDS) == 1 for finding in findings)


def test_the_check_finds_a_restating_sentence_added_to_a_copy(tmp_path: Path) -> None:
    package = tmp_path / "continuity-initiative"
    shutil.copytree(LIVE_PACKAGE, package)
    knowledge_path = package / "knowledge.yaml"
    knowledge = yaml.safe_load(knowledge_path.read_text(encoding="utf-8"))
    entry = next(item for item in knowledge["knowledge"] if item["id"] == "k_sl_1c_e_r1")
    entry["delivery_text"] = (
        "Pallets of bottled emergency water stand shrink-wrapped by the loading doors. " + entry["delivery_text"]
    )
    knowledge_path.write_text(yaml.safe_dump(knowledge, sort_keys=False), encoding="utf-8")

    findings = _restatement_findings(package)

    assert len(findings) == 1
    assert "k_sl_1c_e_r1" in findings[0]["detail"]


def test_the_live_story_has_no_restating_deliveries() -> None:
    report = audit_package(LIVE_PACKAGE)
    findings = [finding for finding in report["findings"] if finding["check"] == "delivery_restates_scene"]

    assert findings == []
    checks = {finding["check"] for finding in report["findings"]}
    assert {"beat_overprojection", "prompt_hygiene"} <= checks


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
