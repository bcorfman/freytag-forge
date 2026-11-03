from __future__ import annotations

from pathlib import Path

import yaml

from storygame.audit import audit_package
from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package

ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(ROOT)
NEW_THINGS = {
    "inspector_badges": "inspector badges",
    "alarm_log": "alarm log",
    "return_line": "return line",
    "security_camera": "security camera",
}


def _scene():
    return next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "2A").metadata


def _entries() -> dict:
    return {entry.id: entry for entry in PACKAGE.knowledge.knowledge}


def _routes() -> dict:
    data = yaml.safe_load((ROOT / "storylet-routes.yaml").read_text(encoding="utf-8"))
    return {item["id"]: item for item in data["storylets"]}


def _engine(*, true_facts: tuple[str, ...] = ()) -> tuple[RuntimeState, RuntimeEngine]:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "2A"
    state.phase = _scene().freytag_phase
    state._assert_scene_entry_fact("2A")
    apply_scene_placements(PACKAGE, state.facts, "2A")
    for fact_id in true_facts:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _command: {"segments": [{"kind": "narration", "text": "Kristin looks."}]})
    return state, engine


def _handoff(engine: RuntimeEngine, state: RuntimeState, command: str):
    engine._activate_pacing()
    candidates = engine.projector.project(state, "player", command).candidates
    return uniquely_matched_authored_handoff(command, candidates)


def test_the_badge_log_line_and_camera_things_are_declared_plainly_and_placed_in_2a():
    items = {item.id: item for item in PACKAGE.world.items}
    for item_id, name in NEW_THINGS.items():
        assert item_id in items, f"missing world item {item_id}"
        item = items[item_id]
        assert item.name == name
        assert item.fixed is True
        assert item.owner is None and "'s " not in item.name
        assert item_id in _scene().item_ids and item_id in _scene().item_placements, item_id
    assert items["inspector_badges"].scoped_aliases == ("badges", "badge")
    assert items["alarm_log"].scoped_aliases == ("log", "tablet")
    assert items["security_camera"].scoped_aliases == ("camera",)
    placements = _scene().item_placements
    assert placements["inspector_badges"].parent == "kristin"
    for item_id in ("alarm_log", "return_line", "security_camera"):
        assert placements[item_id].parent == "facility_perimeter"
    assert all(placements[item_id].text for item_id in NEW_THINGS)
    assert {"badge_craft_noted", "alarm_log_read", "return_line_traced", "camera_on_brandon_seen"} <= set(
        PACKAGE.world.facts
    )


def test_four_new_optional_storylets_share_their_beats_windows_and_conditions():
    routes = _routes()
    expected_conditions = {
        "SL-2A-E": {("inspection_window_missed", False)},
        "SL-2A-F": {("inspection_window_missed", False)},
        "SL-2A-G": {("inspection_window_missed", False), ("manifold_fault_found", True)},
        "SL-2A-H": {("inspection_window_missed", False), ("manifold_fault_found", True)},
    }
    for storylet_id, conditions in expected_conditions.items():
        route = routes[storylet_id]
        assert route["scene_id"] == "2A"
        assert len(route["realization_options"]) == 1
        pacing = route["activation"]["pacing"]
        assert (pacing["earliest_turn"], pacing["target_turn"], pacing["latest_turn"]) == (0, 2, 4)
        actual = {(item["fact_id"], item.get("equals")) for item in route["activation"].get("conditions", [])}
        assert actual == conditions


def test_the_new_reveals_are_quiet_short_and_exact():
    entries = _entries()
    expected_evidence = {
        "k_sl_2a_e_r1": (["ask", "check", "look at", "examine", "inspect", "study"], ["badges", "badge", "readers"]),
        "k_sl_2a_f_r1": (
            ["read", "look at", "check", "examine", "inspect", "study"],
            ["alarm log", "log", "tablet", "alarms", "alarm"],
        ),
        "k_sl_2a_g_r1": (["trace", "follow", "check", "inspect", "examine", "study"], ["return line", "line"]),
        "k_sl_2a_h_r1": (["look at", "watch", "study", "check", "examine", "notice"], ["camera", "security camera"]),
    }
    expected_requires = {
        "k_sl_2a_e_r1": {("inspection_window_missed", False)},
        "k_sl_2a_f_r1": {("inspection_window_missed", False)},
        "k_sl_2a_g_r1": {("inspection_window_missed", False), ("manifold_fault_found", True)},
        "k_sl_2a_h_r1": {("inspection_window_missed", False), ("manifold_fault_found", True)},
    }
    expected_establishes = {
        "k_sl_2a_e_r1": "badge_craft_noted",
        "k_sl_2a_f_r1": "alarm_log_read",
        "k_sl_2a_g_r1": "return_line_traced",
        "k_sl_2a_h_r1": "camera_on_brandon_seen",
    }
    required_phrases = {
        "k_sl_2a_e_r1": ("three things",),
        "k_sl_2a_f_r1": ("forty", "sensor fault", "upstairs"),
        "k_sl_2a_g_r1": ("pumps", "heavy door"),
        "k_sl_2a_h_r1": ("camera", "brandon"),
    }
    forbidden = ("rebecca", "janus", "recogni", "alert", "selection", "barrier", "drainage")
    for entry_id, groups in expected_evidence.items():
        entry = entries[entry_id]
        assert entry.audience.kind == "public" and entry.audience.player_visible is True
        assert entry.available_in_scenes == ("2A",)
        assert entry.voiceable is False
        assert entry.relevance.priority == -1
        assert {(requirement.fact_id, requirement.equals) for requirement in entry.requires} == expected_requires[
            entry_id
        ]
        assert [list(group) for group in entry.action_evidence] == [*groups]
        assert entry.must_convey
        assert len(entry.statement) <= 90
        assert not any(word in entry.delivery_text.casefold() for word in forbidden)
        assert all(phrase in entry.delivery_text.casefold() for phrase in required_phrases[entry_id])
        establishes = {(operation.fact_id, operation.value) for operation in entry.establishes}
        assert establishes == {(expected_establishes[entry_id], True)}
        assert "rebecca_observing_infiltrators" not in {fact_id for fact_id, _value in establishes}


def test_the_badges_and_the_alarm_log_are_reachable_from_the_start():
    for command, entry_id in (
        ("Ask Brandon about the badges.", "k_sl_2a_e_r1"),
        ("Read the alarm log.", "k_sl_2a_f_r1"),
    ):
        state, engine = _engine()
        handoff = _handoff(engine, state, command)
        assert handoff is not None and handoff.candidate.id == entry_id, command
        state, engine = _engine(true_facts=("inspection_window_missed",))
        handoff = _handoff(engine, state, command)
        assert handoff is None or handoff.candidate.id != entry_id, command


def test_the_return_line_and_the_camera_wait_for_the_manifold_fault():
    checks = (("Trace the return line.", "k_sl_2a_g_r1"), ("Look at the camera.", "k_sl_2a_h_r1"))
    for command, entry_id in checks:
        state, engine = _engine(true_facts=("manifold_fault_found",))
        handoff = _handoff(engine, state, command)
        assert handoff is not None and handoff.candidate.id == entry_id, command
        for facts in ((), ("inspection_window_missed",)):
            state, engine = _engine(true_facts=facts)
            handoff = _handoff(engine, state, command)
            assert handoff is None or handoff.candidate.id != entry_id, command


def test_existing_2a_commands_still_reach_their_reveals():
    new_reveals = ("badge_craft_noted", "alarm_log_read", "return_line_traced", "camera_on_brandon_seen")
    checks = (
        ((), "Feel the cooling lines at the manifold.", "k_sl_2a_b_r1"),
        (
            ("manifold_fault_found",),
            "Diagnose the genuine cooling-water pressure fault and the real ventilation fault to the shift supervisor.",
            "k_sl_2a_c_r5",
        ),
        (new_reveals, "Feel the cooling lines at the manifold.", "k_sl_2a_b_r1"),
        (
            ("manifold_fault_found", *new_reveals),
            "Diagnose the genuine cooling-water pressure fault and the real ventilation fault to the shift supervisor.",
            "k_sl_2a_c_r5",
        ),
    )
    for facts, command, entry_id in checks:
        state, engine = _engine(true_facts=facts)
        handoff = _handoff(engine, state, command)
        assert handoff is not None and handoff.candidate.id == entry_id, command


def test_the_richer_scene_adds_no_beat_overprojection():
    findings = audit_package(ROOT)["findings"]
    overprojection = [
        finding for finding in findings if finding["check"] == "beat_overprojection" and finding.get("scene_id") == "2A"
    ]
    # The 1A findings are known and older; use them to prove this filter is non-vacuous.
    assert any(finding.get("scene_id") == "1A" for finding in findings if finding["check"] == "beat_overprojection")
    # Measured before the richer 2A data change: there were two such findings.
    assert len(overprojection) <= 2
