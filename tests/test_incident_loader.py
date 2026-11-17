from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from storygame.story_package import load_story_package
from storygame.story_source.diagnostics import SourceError
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy, patch_source

ROOT = Path(__file__).resolve().parents[1] / "data" / "stories" / "continuity-initiative"


def _copy_fixture(tmp_path: Path) -> Path:
    return compiled_story_copy(tmp_path)


def _load_source(root: Path, scene: str = "2C") -> dict:
    return yaml.safe_load((root / "source" / "scenes" / f"{scene}.yaml").read_text(encoding="utf-8"))


def _write_source(root: Path, scene: str, document: dict) -> None:
    (root / "source" / "scenes" / f"{scene}.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8"
    )


def _remove_match_claim(root: Path, claim_id: str) -> None:
    path = root / "source" / "scenes" / "2C.match.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["claims"].pop(claim_id, None)
    path.write_text(yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8")


def _duplicate_scene(root: Path) -> str:
    document = _load_source(root)
    duplicate = dict(document["incidents"][0])
    duplicate["id"] = "i_2c_duplicate"
    document["incidents"].append(duplicate)
    _write_source(root, "2C", document)
    return "2C"


def _unknown_scene(root: Path) -> str:
    patch_source(root, "source/scenes/2C.yaml", "scene", "9Z")
    return "9Z"


def _unknown_outcome_storylet(root: Path) -> str:
    patch_source(root, "source/scenes/2C.yaml", "incidents[0].reveal", "sl_1b_a")
    return "SL-1B-A"


def _nonexclusive(root: Path) -> str:
    document = _load_source(root)
    reveal = next(item for item in document["reveals"] if item["storylet_id"] == "SL-2C-D")
    reveal["variants"]["r4"]["realization_id"] = reveal["variants"]["r3"]["realization_id"]
    _write_source(root, "2C", document)
    return "SL-2C-D-R3"


def _unknown_advantage(root: Path) -> str:
    patch_source(
        root, "source/scenes/2C.yaml", "reveals[sl_2c_d].variants.r3.outcome.advantages", ["unknown_advantage"]
    )
    return "unknown_advantage"


def _unasserted_fact(root: Path) -> str:
    patch_source(
        root, "source/scenes/2C.yaml", "reveals[sl_2c_d].variants.r4.outcome.advantages", ["committed_to_transmit"]
    )
    patch_source(root, "source/scenes/2C.yaml", "reveals[sl_2c_d].variants.r4.outcome.costs", ["brandon"])
    return "committed_to_transmit"


def _unknown_event(root: Path) -> str:
    patch_source(root, "source/scenes/2C.yaml", "incidents[0].missed_window", "missing_event")
    return "missing_event"


def _event_forces_successor(root: Path) -> str:
    patch_source(root, "source/scenes/2C.yaml", "beats[purge_window_2c].exit", "t_1a_1b")
    patch_source(root, "source/scenes/2C.yaml", "incidents[0].successor", "t_1a_1b")
    return "t_1a_1b"


def _unknown_transition(root: Path) -> str:
    patch_source(root, "source/scenes/2C.yaml", "incidents[0].successor", "missing_transition")
    return "missing_transition"


def _unknown_observation(root: Path) -> str:
    patch_source(root, "source/scenes/2C.yaml", "incidents[0].observed_by", ["missing_knowledge"])
    return "missing_knowledge"


def _overlapping_delivery_cost(root: Path) -> str:
    patch_source(
        root, "source/scenes/2C.yaml", "facts.committed_to_transmit.delivery.costs", {"detention_sectors_sealed": True}
    )
    return "detention_sectors_sealed"


def _unknown_recovery_storylet(root: Path) -> str:
    patch_source(root, "source/scenes/2C.yaml", "incidents[0].recovery", "SL-1A-C")
    return "SL-1A-C"


def _recovery_reuses_shared_storylet(root: Path) -> str:
    patch_source(root, "source/scenes/2C.yaml", "incidents[0].recovery", "sl_2c_d")
    return "SL-2C-D"


def _recovery_has_no_qualifying_realization(root: Path) -> str:
    document = _load_source(root)
    recovery = next(item for item in document["reveals"] if item["id"] == "sl_2c_e")
    variant = recovery["variants"]["r1"]
    variant["commits"] = {"committed_to_transmit": True}
    variant.pop("extra_claims", None)
    variant["commits_subset"] = {"committed_to_transmit": True}
    _write_source(root, "2C", document)
    _remove_match_claim(root, "k_sl_2c_e_route_effects")
    return "SL-2C-E"


def _recovery_awards_both_outcomes(root: Path) -> str:
    document = _load_source(root)
    recovery = next(item for item in document["reveals"] if item["id"] == "sl_2c_e")
    variant = recovery["variants"]["r1"]
    variant["commits"] = {"committed_to_transmit": True, "committed_to_rescue": True}
    variant.pop("extra_claims", None)
    variant["commits_subset"] = {"committed_to_transmit": True, "committed_to_rescue": True}
    _write_source(root, "2C", document)
    _remove_match_claim(root, "k_sl_2c_e_route_effects")
    return "SL-2C-E"


def _recovery_does_not_require_window(root: Path) -> str:
    patch_source(root, "source/scenes/2C.yaml", "reveals[sl_2c_e].guidance.available_while", {})
    return "purge_window_missed"


def _recovery_asserts_only_extra_fact(root: Path) -> str:
    patch_source(root, "source/scenes/2C.yaml", "reveals[sl_2c_e].guidance.window.latest_turn", 10)
    return "SL-2C-E"


REJECTIONS = [
    ("duplicate incident id", _duplicate_scene, "i_2c_duplicate"),
    ("second incident in scene", _duplicate_scene, "2C"),
    ("unknown scene", _unknown_scene, "9Z"),
    ("unknown outcome storylet", _unknown_outcome_storylet, "sl_1b_a"),
    ("non-exclusive realizations", _nonexclusive, "SL-2C-D-R3"),
    ("unknown advantage", _unknown_advantage, "unknown_advantage"),
    ("unasserted outcome fact", _unasserted_fact, "brandon"),
    ("unknown missed-window event", _unknown_event, "missing_event"),
    ("missed-window successor", _event_forces_successor, "t_1a_1b"),
    ("unknown successor transition", _unknown_transition, "missing_transition"),
    ("unknown observation knowledge", _unknown_observation, "missing_knowledge"),
    ("delivery cost overlaps outcome", _overlapping_delivery_cost, "detention_sectors_sealed"),
    ("unknown recovery storylet", _unknown_recovery_storylet, "SL-1A-C"),
    ("recovery reuses outcome storylet", _recovery_reuses_shared_storylet, "SL-2C-D"),
    ("recovery has no extra fact", _recovery_has_no_qualifying_realization, "purge_recovery_ready"),
    ("recovery awards both outcomes", _recovery_awards_both_outcomes, "purge_recovery_ready"),
    ("recovery misses window activation", _recovery_does_not_require_window, "purge_window_missed"),
]


def test_incident_fixture_loads_with_two_outcomes() -> None:
    package = load_story_package(ROOT)
    assert len(package.incidents) == 5
    assert [outcome.id for outcome in package.incidents[3].outcomes] == ["committed_to_transmit", "committed_to_rescue"]


def test_neutral_zero_match_recovery_loads_with_two_outcomes(tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    _recovery_asserts_only_extra_fact(package)

    loaded = load_compiled_copy(package)

    assert len(loaded.incidents[3].outcomes) == 2


def test_real_package_declares_the_continuity_incident() -> None:
    package = load_story_package(ROOT)
    assert [incident.id for incident in package.incidents] == [
        "i_1c_freight_transfer",
        "i_2a_real_leak",
        "i_2b_audit",
        "i_2c_rebecca_corridor",
        "i_3c_evacuation",
    ]


@pytest.mark.parametrize("case_name, mutate, offending", REJECTIONS, ids=[case[0] for case in REJECTIONS])
def test_incident_rejections_include_incident_and_offending_id(
    tmp_path: Path, case_name, mutate, offending: str
) -> None:
    package = _copy_fixture(tmp_path)
    mutate(package)
    with pytest.raises(SourceError, match=offending):
        load_compiled_copy(package)


def test_incidents_yaml_requires_an_incidents_list(tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    patch_source(package, "source/scenes/2C.yaml", "incidents", {})
    with pytest.raises(SourceError, match="incidents.*list"):
        load_compiled_copy(package)


def test_incidents_yaml_requires_a_list_value(tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    patch_source(package, "source/scenes/2C.yaml", "incidents", {"id": "i_2c_rebecca_corridor"})
    with pytest.raises(SourceError, match="incidents.*list"):
        load_compiled_copy(package)


def test_delivery_cost_without_incident_cost_overlap_is_valid(tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    patch_source(
        package, "source/scenes/2C.yaml", "facts.committed_to_transmit.delivery.costs", {"purge_clock_started": True}
    )
    assert len(load_compiled_copy(package).incidents) == 5


def test_final_incident_skips_event_transition_comparison(tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    document = _load_source(package, "3C")
    next(beat for beat in document["beats"] if beat["id"] == "collapse_3c")["exit"] = "t_1a_1b"
    _write_source(package, "3C", document)

    loaded = load_compiled_copy(package)

    assert loaded.incidents[-1].successor_transition_id is None
