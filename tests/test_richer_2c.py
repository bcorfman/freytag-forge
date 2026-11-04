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
    "corridor_camera": "corridor camera",
    "monitor_light": "monitor light",
    "cart_tags": "cart tags",
}


def _scene():
    return next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "2C").metadata


def _entries() -> dict:
    return {entry.id: entry for entry in PACKAGE.knowledge.knowledge}


def _routes() -> dict:
    data = yaml.safe_load((ROOT / "storylet-routes.yaml").read_text(encoding="utf-8"))
    return {item["id"]: item for item in data["storylets"]}


def _engine(*, true_facts: tuple[str, ...] = (), turn_index: int = 0) -> tuple[RuntimeState, RuntimeEngine]:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "2C"
    state.phase = _scene().freytag_phase
    state._assert_scene_entry_fact("2C")
    state.turn_index = turn_index
    apply_scene_placements(PACKAGE, state.facts, "2C")
    for fact_id in true_facts:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _command: {"segments": [{"kind": "narration", "text": "Kristin looks."}]})
    return state, engine


def _handoff(engine: RuntimeEngine, state: RuntimeState, command: str):
    engine._activate_pacing()
    candidates = engine.projector.project(state, "player", command).candidates
    return uniquely_matched_authored_handoff(command, candidates)


def test_the_camera_the_monitor_light_and_the_cart_tags_are_declared_plainly_and_placed_in_2c():
    items = {item.id: item for item in PACKAGE.world.items}
    for item_id, name in NEW_THINGS.items():
        assert item_id in items, f"missing world item {item_id}"
        item = items[item_id]
        assert item.name == name
        assert item.fixed is True
        assert item.kind == "thing"
        assert item.owner is None and "'s " not in item.name
        assert item_id in _scene().item_ids and item_id in _scene().item_placements, item_id
    assert items["corridor_camera"].scoped_aliases == ("camera",)
    assert items["monitor_light"].scoped_aliases == ("status light", "amber light", "light")
    assert items["cart_tags"].scoped_aliases == ("tags", "tag", "cart tag")
    placements = _scene().item_placements
    assert all(placements[item_id].text for item_id in NEW_THINGS)
    assert all(placements[item_id].parent == "purge_chamber" for item_id in NEW_THINGS)
    assert {"corridor_watch_lifted", "uplink_eye_seen", "held_carts_known"} <= set(PACKAGE.world.facts)


def test_three_new_optional_storylets_share_their_beats_windows_and_conditions():
    routes = _routes()
    expected = {
        "SL-2C-F": (
            {("purge_window_missed", False), ("rebecca_offer_heard", True)},
            "scene-2c2--the-purge-order",
        ),
        "SL-2C-G": (
            {("purge_window_missed", False), ("held_transfers_seen", True)},
            "scene-2c3--evidence-or-rescue",
        ),
        "SL-2C-H": (
            {("purge_window_missed", False)},
            "scene-2c3--evidence-or-rescue",
        ),
    }
    for storylet_id, (conditions, source_beat) in expected.items():
        route = routes[storylet_id]
        assert route["scene_id"] == "2C"
        assert len(route["realization_options"]) == 1
        realization = route["realization_options"][0]
        pacing = route["activation"]["pacing"]
        assert (pacing["earliest_turn"], pacing["target_turn"], pacing["latest_turn"]) == (0, 6, 6)
        actual = {(item["fact_id"], item.get("equals")) for item in route["activation"].get("conditions", [])}
        assert actual == conditions
        assert realization["id"] == f"{storylet_id}-R1"
        assert realization["source_beats"] == [source_beat]


def test_the_new_reveals_are_quiet_short_and_exact():
    entries = _entries()
    routes = _routes()
    expected = {
        "k_sl_2c_f_r1": (
            "SL-2C-F",
            "corridor_watch_lifted",
            {("purge_window_missed", False), ("rebecca_offer_heard", True)},
            (
                ["look at", "watch", "check", "examine", "study", "look up at", "glance at"],
                ["corridor camera", "camera", "lens"],
            ),
            ["corridor_camera"],
            ("kristin", "brandon", "corridor_camera"),
            ("camera", "brandon", "sweep"),
        ),
        "k_sl_2c_g_r1": (
            "SL-2C-G",
            "held_carts_known",
            {("purge_window_missed", False), ("held_transfers_seen", True)},
            (
                ["read", "look at", "check", "examine", "inspect", "study"],
                ["cart tags", "tags", "tag", "cart tag"],
            ),
            ["cart_tags"],
            ("kristin", "cart_tags", "transfer_carts"),
            ("week", "sensor fault", "held"),
        ),
        "k_sl_2c_h_r1": (
            "SL-2C-H",
            "uplink_eye_seen",
            {("purge_window_missed", False)},
            (
                ["read", "look at", "check", "examine", "inspect", "study", "watch"],
                ["monitor light", "status light", "amber light", "light", "indicator"],
            ),
            ["monitor_light"],
            ("kristin", "monitor_light", "broadcast_uplink"),
            ("one outbound channel", "amber", "seen"),
        ),
    }
    forbidden = ("michelle", "uprising", "broadcast", "phase two", "route", "emergency")
    for entry_id, (storylet_id, fact_id, required, evidence, reach_entity_ids, entity_ids, phrases) in expected.items():
        entry = entries[entry_id]
        assert entry.audience.kind == "public" and entry.audience.player_visible is True
        assert entry.available_in_scenes == ("2C",)
        assert entry.voiceable is False and entry.relevance.priority == -1
        assert {(item.fact_id, item.equals) for item in entry.requires} == required
        assert [list(group) for group in entry.action_evidence] == [*evidence]
        assert entry.reach_entity_ids == tuple(reach_entity_ids)
        assert entry.entity_ids == entity_ids
        assert entry.must_convey and len(entry.statement) <= 90
        assert not any(word in entry.delivery_text.casefold() for word in forbidden)
        assert all(phrase in entry.delivery_text.casefold() for phrase in phrases)
        assert {(operation.fact_id, operation.value) for operation in entry.establishes} == {(fact_id, True)}
        realization = routes[storylet_id]["realization_options"][0]
        assert realization["protected_knowledge_boundaries"] == ["janus_phase_two"]


def test_the_cart_tags_wait_for_the_held_transfers():
    command = "Read the cart tags."
    state, engine = _engine(true_facts=("held_transfers_seen",))
    handoff = _handoff(engine, state, command)
    assert handoff is not None and handoff.candidate.id == "k_sl_2c_g_r1"
    state, engine = _engine()
    handoff = _handoff(engine, state, command)
    assert handoff is None or handoff.candidate.id != "k_sl_2c_g_r1"
    state, engine = _engine(true_facts=("held_transfers_seen", "purge_window_missed"))
    handoff = _handoff(engine, state, command)
    assert handoff is None or handoff.candidate.id != "k_sl_2c_g_r1"


def test_the_camera_lets_go_only_after_brandon_has_said_yes():
    command = "Look at the camera."
    state, engine = _engine(true_facts=("rebecca_offer_heard",))
    handoff = _handoff(engine, state, command)
    assert handoff is not None and handoff.candidate.id == "k_sl_2c_f_r1"
    state, engine = _engine()
    handoff = _handoff(engine, state, command)
    assert handoff is None or handoff.candidate.id != "k_sl_2c_f_r1"


def test_the_monitor_light_can_be_read_before_the_choice():
    state, engine = _engine()
    handoff = _handoff(engine, state, "Check the monitor light.")
    assert handoff is not None and handoff.candidate.id == "k_sl_2c_h_r1"
    state, engine = _engine(true_facts=("purge_window_missed",))
    handoff = _handoff(engine, state, "Check the monitor light.")
    assert handoff is None or handoff.candidate.id != "k_sl_2c_h_r1"


def test_michelles_second_message_travels_as_a_maintenance_ticket():
    entries = _entries()
    for entry_id, place in (("k_sl_2c_d_r3", "uplink"), ("k_sl_2c_d_r4", "cart")):
        entry = entries[entry_id]
        text = entry.delivery_text.casefold()
        # "sensor fault" and "ticket header" are guarded terms first earned in 2A and 2B: only the variant for a
        # player who matched the header may say them, or narration is rejected as unavailable knowledge.
        assert "maintenance ticket" in text and place in text, entry_id
        assert "sensor fault" not in text and "ticket header" not in text, entry_id
        variants = [variant for variant in entry.delivery_variants if "ticket_header_matched" in variant.requires]
        assert len(variants) == 1, entry_id
        variant = variants[0].text.casefold()
        assert "maintenance ticket" in variant and "sensor fault" in variant and "archive" in variant, entry_id
        assert "michelle" in text or "michelle" in variant
        assert [list(group) for group in entry.must_convey][-2:] == [
            ["Rebecca's secured office", "Rebecca's office"],
            ["broadcast the evidence", "open the detention cells", "combined plan"],
        ]
    pacing = {event.id: event for event in PACKAGE.pacing.events}
    first = pacing["purge_window_2c"].realizations[0].text.casefold()
    assert "maintenance ticket" in first and "sensor fault" not in first


def test_existing_2c_commands_still_reach_their_reveals():
    checks = (
        ((), "Tell Rebecca nothing.", "k_sl_2c_c_r1", 0),
        (("rebecca_offer_heard",), "Head to the uplink and start sending the copied files.", "k_sl_2c_d_r3", 1),
        (("rebecca_offer_heard",), "Head to the transfer carts and free a cart of captives.", "k_sl_2c_d_r4", 1),
    )
    for facts, command, entry_id, turn_index in checks:
        state, engine = _engine(true_facts=facts, turn_index=turn_index)
        handoff = _handoff(engine, state, command)
        assert handoff is not None and handoff.candidate.id == entry_id, command


def test_the_richer_scene_adds_no_beat_overprojection():
    findings = audit_package(ROOT)["findings"]
    overprojection = [
        finding for finding in findings if finding["check"] == "beat_overprojection" and finding.get("scene_id") == "2C"
    ]
    # The 1A findings are known and older; use them to prove this filter is non-vacuous.
    assert any(finding.get("scene_id") == "1A" for finding in findings if finding["check"] == "beat_overprojection")
    # Measured before the richer 2C data change: there were four such findings.
    assert len(overprojection) <= 4
