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
    "wrist_tags": "wrist tags",
    "checkpoint_reader": "checkpoint reader",
}
NEW_FACTS = {
    "wrist_tags_read",
    "radio_loop_known",
    "michelle_private_proof",
    "checkpoint_opened",
    "lemon_cake_calendar_read",
}
ARRIVED = ("michelle_reached", "uprising_prepared")


def _scene():
    return next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "3A").metadata


def _entries() -> dict:
    return {entry.id: entry for entry in PACKAGE.knowledge.knowledge}


def _routes() -> dict:
    data = yaml.safe_load((ROOT / "storylet-routes.yaml").read_text(encoding="utf-8"))
    return {item["id"]: item for item in data["storylets"]}


def _engine(*, true_facts: tuple[str, ...] = (), turn_index: int = 0) -> tuple[RuntimeState, RuntimeEngine]:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "3A"
    state.phase = _scene().freytag_phase
    state._assert_scene_entry_fact("3A")
    state.turn_index = turn_index
    apply_scene_placements(PACKAGE, state.facts, "3A")
    for fact_id in true_facts:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _command: {"segments": [{"kind": "narration", "text": "Kristin looks."}]})
    return state, engine


def _handoff(engine: RuntimeEngine, state: RuntimeState, command: str):
    engine._activate_pacing()
    candidates = engine.projector.project(state, "player", command).candidates
    return uniquely_matched_authored_handoff(command, candidates)


def test_the_wrist_tags_and_the_checkpoint_reader_are_declared_plainly_and_placed_in_3a():
    items = {item.id: item for item in PACKAGE.world.items}
    for item_id, name in NEW_THINGS.items():
        assert item_id in items, f"missing world item {item_id}"
        item = items[item_id]
        assert item.name == name
        assert item.fixed is True
        assert item.kind == "thing"
        assert item.owner is None and "'s " not in item.name
        assert item_id in _scene().item_ids and item_id in _scene().item_placements, item_id
    assert items["wrist_tags"].scoped_aliases == ("tags", "tag", "wrist tag")
    assert items["checkpoint_reader"].scoped_aliases == ("reader", "card reader")
    placements = _scene().item_placements
    assert all(placements[item_id].text for item_id in NEW_THINGS)
    assert all(placements[item_id].parent == "detention_level" for item_id in NEW_THINGS)
    assert set(PACKAGE.world.facts) >= NEW_FACTS


def test_the_calendar_reveal_in_1a_alone_earns_the_lemon_cake_fact():
    entries = _entries()
    earning = [
        entry.id
        for entry in entries.values()
        if any(operation.fact_id == "lemon_cake_calendar_read" for operation in entry.establishes)
    ]
    assert earning == ["k_sl_1a_g_r2"]
    facts = {(operation.fact_id, operation.value) for operation in entries["k_sl_1a_g_r2"].establishes}
    assert facts == {
        ("kitchen_last_hour_read", True),
        ("michelle_abduction_suspicion", True),
        ("lemon_cake_calendar_read", True),
    }


def test_four_new_optional_storylets_share_their_beats_windows_and_conditions():
    routes = _routes()
    expected = {
        "SL-3A-F": ({("michelle_reached", True)}, "scene-3a1--the-detention-block"),
        "SL-3A-G": ({("michelle_reached", True)}, "scene-3a1--the-detention-block"),
        "SL-3A-H": (
            {("behavioral_experiments_known", True), ("lemon_cake_calendar_read", True), ("michelle_reached", True)},
            "scene-3a2--the-experiments",
        ),
        "SL-3A-I": ({("michelle_reached", True)}, "scene-3a4--the-uprising-begins"),
    }
    for storylet_id, (conditions, source_beat) in expected.items():
        route = routes[storylet_id]
        assert route["scene_id"] == "3A"
        assert len(route["realization_options"]) == 1
        realization = route["realization_options"][0]
        pacing = route["activation"]["pacing"]
        assert (pacing["earliest_turn"], pacing["target_turn"], pacing["latest_turn"]) == (0, 8, 9)
        actual = {(item["fact_id"], item.get("equals")) for item in route["activation"].get("conditions", [])}
        assert actual == conditions
        assert realization["id"] == f"{storylet_id}-R1"
        assert realization["source_beats"] == [source_beat]
        assert realization["protected_knowledge_boundaries"] == ["janus_phase_two"]


def test_the_new_reveals_are_quiet_short_and_exact():
    entries = _entries()
    expected = {
        "k_sl_3a_f_r1": (
            "wrist_tags_read",
            {("michelle_reached", True)},
            (
                ["read", "look at", "check", "examine", "inspect", "study"],
                ["wrist tags", "wrist tag", "tags", "tag"],
            ),
            ["wrist_tags"],
            ("kristin", "wrist_tags", "captives", "michelle"),
            ("michelle", "held", "tag"),
        ),
        "k_sl_3a_g_r1": (
            "radio_loop_known",
            {("michelle_reached", True)},
            (
                ["listen to", "listen", "hear", "tune", "study", "check", "examine", "trace"],
                [
                    "stolen radio",
                    "the stolen radio",
                    "radio",
                    "radios",
                    "announcement",
                    "announcements",
                    "coded announcement",
                    "coded announcements",
                    "loop",
                ],
            ),
            ["stolen_radio"],
            ("kristin", "stolen_radio", "michelle"),
            ("one word", "guards", "stops"),
        ),
        "k_sl_3a_h_r1": (
            "michelle_private_proof",
            {
                ("michelle_reached", True),
                ("behavioral_experiments_known", True),
                ("lemon_cake_calendar_read", True),
            },
            (
                ["ask", "test", "question", "quiz", "press", "probe"],
                ["lemon cake", "the lemon cake", "calendar", "the calendar", "kitchen calendar", "birthday"],
            ),
            [],
            ("kristin", "michelle"),
            ("lemon cake", "saturday", "birthday"),
        ),
        "k_sl_3a_i_r1": (
            "checkpoint_opened",
            {("michelle_reached", True)},
            (
                ["watch", "check", "examine", "study", "look at", "inspect"],
                ["checkpoint reader", "the checkpoint reader", "reader", "card reader", "checkpoint door"],
            ),
            ["checkpoint_reader"],
            ("kristin", "brandon", "checkpoint_reader"),
            ("first pass", "brandon", "watch"),
        ),
    }
    forbidden = ("phase two", "uprising", "broadcast", "sensor fault", "ticket header", "ninety seconds")
    for entry_id, (fact_id, required, evidence, reach_entity_ids, entity_ids, phrases) in expected.items():
        entry = entries[entry_id]
        assert entry.audience.kind == "public" and entry.audience.player_visible is True
        assert entry.available_in_scenes == ("3A",)
        assert entry.voiceable is False and entry.relevance.priority == -1
        assert {(item.fact_id, item.equals) for item in entry.requires} == required
        assert [list(group) for group in entry.action_evidence] == [*evidence]
        assert entry.reach_entity_ids == tuple(reach_entity_ids)
        assert entry.entity_ids == entity_ids
        assert entry.must_convey and len(entry.statement) <= 90
        text = entry.delivery_text.casefold()
        assert not any(word in text for word in forbidden), entry_id
        assert all(phrase in text for phrase in phrases), entry_id
        assert {(operation.fact_id, operation.value) for operation in entry.establishes} == {(fact_id, True)}


def test_the_probe_defects_are_cured_at_the_source():
    entries = _entries()
    placements = _scene().item_placements
    # Echo: what the narrator would write before the delivery lives in the thing's placement text, so the
    # delivery says only what is new (the 1C door and 2B badge technique).
    assert "same transfer date" in placements["wrist_tags"].text and "week" in placements["wrist_tags"].text
    assert "repeat" in placements["stolen_radio"].text
    tags = entries["k_sl_3a_f_r1"]
    assert "week" not in tags.delivery_text.casefold()
    assert all("week" not in variant.text.casefold() for variant in tags.delivery_variants)
    assert [list(group) for group in tags.must_convey] == [["tag", "wrist tag"], ["held"]]
    loop = entries["k_sl_3a_g_r1"]
    assert "on repeat" not in loop.delivery_text.casefold()
    assert [list(group) for group in loop.must_convey] == [["coded words", "coded announcements"], ["one word"]]
    assert "coded words" in loop.delivery_text.casefold()
    assert all("coded words" in variant.text.casefold() for variant in loop.delivery_variants)
    proof = entries["k_sl_3a_h_r1"]
    assert "Saturday, circled, K, lemon cake" not in proof.delivery_text
    # Rejected turn: the narrator must carry the cake and one of the day or the birthday, not all three words.
    assert [list(group) for group in proof.must_convey] == [["lemon cake"], ["Saturday", "birthday"]]
    # Contradiction: the narrator invents a keypad stare, so the reveal must not name the keypad at all.
    reader = entries["k_sl_3a_i_r1"]
    texts = [reader.statement, reader.delivery_text, *(variant.text for variant in reader.delivery_variants)]
    assert not any("keypad" in text.casefold() for text in texts)
    assert not any("keypad" in term.casefold() for group in reader.must_convey for term in group)
    assert [list(group) for group in reader.must_convey] == [["checkpoint reader", "reader"], ["first pass"]]
    assert "reader" in reader.delivery_text.casefold()


def test_guarded_terms_are_said_only_by_the_variants_that_require_their_facts():
    entries = _entries()
    expected = {
        "k_sl_3a_f_r1": ("held_transfers_seen", "sensor fault"),
        "k_sl_3a_g_r1": ("broadcast_loop_confirmed", "ninety seconds"),
        "k_sl_3a_i_r1": ("badge_craft_noted", "gate"),
    }
    for entry_id, (fact_id, phrase) in expected.items():
        entry = entries[entry_id]
        variants = [variant for variant in entry.delivery_variants if fact_id in variant.requires]
        assert len(variants) == 1, entry_id
        assert phrase in variants[0].text.casefold(), entry_id
        assert phrase not in entry.delivery_text.casefold(), entry_id
    assert not entries["k_sl_3a_h_r1"].delivery_variants


def test_the_wrist_tags_are_read_after_arriving_and_not_before():
    command = "Read the wrist tags."
    state, engine = _engine(true_facts=ARRIVED)
    handoff = _handoff(engine, state, command)
    assert handoff is not None and handoff.candidate.id == "k_sl_3a_f_r1"
    state, engine = _engine()
    handoff = _handoff(engine, state, command)
    assert handoff is None or handoff.candidate.id != "k_sl_3a_f_r1"


def test_the_radios_give_up_their_loop_after_arriving():
    command = "Listen to the stolen radio."
    state, engine = _engine(true_facts=ARRIVED)
    handoff = _handoff(engine, state, command)
    assert handoff is not None and handoff.candidate.id == "k_sl_3a_g_r1"
    state, engine = _engine()
    handoff = _handoff(engine, state, command)
    assert handoff is None or handoff.candidate.id != "k_sl_3a_g_r1"


def test_michelles_proof_needs_the_medical_level_and_the_kitchen_calendar():
    command = "Ask Michelle about the lemon cake."
    facts = (*ARRIVED, "behavioral_experiments_known", "lemon_cake_calendar_read")
    state, engine = _engine(true_facts=facts)
    handoff = _handoff(engine, state, command)
    assert handoff is not None and handoff.candidate.id == "k_sl_3a_h_r1"
    for missing in ("behavioral_experiments_known", "lemon_cake_calendar_read"):
        state, engine = _engine(true_facts=tuple(fact for fact in facts if fact != missing))
        handoff = _handoff(engine, state, command)
        assert handoff is None or handoff.candidate.id != "k_sl_3a_h_r1", missing


def test_the_checkpoint_reader_can_be_watched_after_arriving():
    command = "Check the checkpoint reader."
    state, engine = _engine(true_facts=ARRIVED)
    handoff = _handoff(engine, state, command)
    assert handoff is not None and handoff.candidate.id == "k_sl_3a_i_r1"
    state, engine = _engine()
    handoff = _handoff(engine, state, command)
    assert handoff is None or handoff.candidate.id != "k_sl_3a_i_r1"


def test_existing_3a_commands_still_reach_their_reveals():
    checks = (
        ((), "Free the captives.", "k_sl_3a_a_r1"),
        (ARRIVED, "Enter the medical level.", "k_sl_3a_b_r2"),
        (
            (*ARRIVED, "behavioral_experiments_known"),
            "Ask the senior official about the gate codes.",
            "k_sl_3a_d_r1",
        ),
    )
    for facts, command, entry_id in checks:
        state, engine = _engine(true_facts=facts)
        handoff = _handoff(engine, state, command)
        assert handoff is not None and handoff.candidate.id == entry_id, command


def test_the_richer_scene_adds_no_beat_overprojection():
    findings = audit_package(ROOT)["findings"]
    overprojection = [
        finding for finding in findings if finding["check"] == "beat_overprojection" and finding.get("scene_id") == "3A"
    ]
    # The 1A findings are known and older; use them to prove this filter is non-vacuous.
    assert any(finding.get("scene_id") == "1A" for finding in findings if finding["check"] == "beat_overprojection")
    # Measured before the richer 3A data change: there was one such finding.
    assert len(overprojection) <= 1
