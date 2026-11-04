from __future__ import annotations

import re
from pathlib import Path

from scripts.ringer.phase1 import act2_probe
from storygame.runtime.validation import unconveyed_terms
from storygame.story_package.loader import load_story_package

LIVE_PACKAGE = Path("data/stories/continuity-initiative")
FROZEN_PACKAGE = Path("bench/frozen/continuity-pre-richer-2b")
ENTRY_IDS = ("k_sl_2b_b_r4", "k_sl_2b_b_r5")
REPEAT_TERMS = ("bait", "retained", "pulls her own file", "corfman as an author")


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _entries(package_path: Path) -> dict[str, object]:
    package = load_story_package(package_path)
    return {entry.id: entry for entry in package.knowledge.knowledge}


def _probe_copy(selected: str) -> str:
    payload = act2_probe._provider_payload(selected)
    return payload["segments"][0]["text"]


def test_the_two_deliveries_say_only_what_is_new() -> None:
    entries = _entries(LIVE_PACKAGE)
    expected_delivery = {
        "k_sl_2b_b_r4": (
            "The file names the system JANUS. Brandon admits that he helped write JANUS. "
            "He says he tried to stop it after he learned its purpose. Kristin keeps his name in the record. "
            "The JANUS files are copied. Kristin carries the copied files. The medical terminal prints a "
            "maintenance line that ends with the name Shelly. Only Kristin uses that name. Before the audit "
            "reaches the aisle, Kristin has time to type one reply on the medical terminal."
        ),
        "k_sl_2b_b_r5": (
            "The file names the system JANUS. Brandon admits that he helped write JANUS. "
            "He says he tried to stop it after he learned its purpose. Kristin lets him erase his name from the "
            "record. The development record now has a gap. The JANUS files are copied. Kristin carries the copied "
            "files. The medical terminal prints a maintenance line that ends with the name Shelly. Only Kristin "
            "uses that name. Before the audit reaches the aisle, Kristin has time to type one reply on the medical "
            "terminal."
        ),
    }
    expected_must_convey = {
        "k_sl_2b_b_r4": [
            ["JANUS", "JANUS build record", "Brandon Corfman", "built JANUS", "helped write JANUS"],
            ["keeps his name", "name stays", "keep Brandon's name"],
            ["JANUS files copied", "copied files", "JANUS evidence"],
        ],
        "k_sl_2b_b_r5": [
            ["JANUS", "JANUS build record", "Brandon Corfman", "built JANUS", "helped write JANUS"],
            ["erase his name", "name is gone", "delete his name"],
            ["JANUS files copied", "copied files", "JANUS evidence"],
            ["record now has a gap", "development record gap", "missing name from the development record"],
        ],
    }

    for entry_id in ENTRY_IDS:
        entry = entries[entry_id]
        assert _collapse_whitespace(entry.delivery_text) == expected_delivery[entry_id]
        assert [list(group) for group in entry.must_convey] == expected_must_convey[entry_id]
        assert entry.leak_terms is not None


def test_no_delivery_sentence_repeats_the_file_pull() -> None:
    entries = _entries(LIVE_PACKAGE)
    first_delivery = _collapse_whitespace(entries["k_sl_2b_a_r1"].delivery_text)
    first_sentences = set(re.split(r"(?<=[.!?])\s+", first_delivery))

    for entry_id in ENTRY_IDS:
        delivery = _collapse_whitespace(entries[entry_id].delivery_text)
        assert not first_sentences.intersection(re.split(r"(?<=[.!?])\s+", delivery))
        lowered = delivery.casefold()
        assert all(term not in lowered for term in REPEAT_TERMS)


def test_every_must_convey_group_is_met_by_the_entrys_own_delivery() -> None:
    entries = _entries(LIVE_PACKAGE)

    for entry_id in ENTRY_IDS:
        entry = entries[entry_id]
        assert unconveyed_terms(entry.must_convey, entry.delivery_text) == ()


def test_the_entries_still_guard_every_leak_term_they_guarded_before() -> None:
    live = load_story_package(LIVE_PACKAGE)
    frozen = load_story_package(FROZEN_PACKAGE)

    for entry_id in ENTRY_IDS:
        frozen_terms = {
            term for term, owners in frozen.knowledge_indexes.leak_term_to_knowledge.items() if entry_id in owners
        }
        live_terms = {
            term for term, owners in live.knowledge_indexes.leak_term_to_knowledge.items() if entry_id in owners
        }
        assert live_terms >= frozen_terms


def test_the_gating_of_the_two_entries_is_unchanged() -> None:
    live_entries = _entries(LIVE_PACKAGE)
    frozen_entries = _entries(FROZEN_PACKAGE)
    excluded = {"delivery_text", "must_convey", "leak_terms"}

    for entry_id in ENTRY_IDS:
        live = live_entries[entry_id].model_dump(mode="json")
        frozen = frozen_entries[entry_id].model_dump(mode="json")
        for field in excluded:
            live.pop(field, None)
            frozen.pop(field, None)
        assert live == frozen


def test_the_probe_script_copies_drop_the_repeat() -> None:
    for entry_id in ENTRY_IDS:
        copy = _probe_copy(entry_id).casefold()
        assert all(term not in copy for term in REPEAT_TERMS)
        assert "the file names the system janus." in copy
        assert "brandon admits that he helped write janus." in copy

    assert "Kristin was bait." in _probe_copy("k_sl_2b_a_r1")
