from __future__ import annotations

import json
from pathlib import Path

import yaml

from storygame.audit import audit_package
from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeSnapshot, RuntimeState
from storygame.runtime.world_model import apply_scene_placements, apply_world_effects, world_for
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
OLD_A_R1_STATEMENT = (
    "Kristin reaches Michelle alive, and the two share one unhurried moment before Michelle returns to directing "
    "prisoners through stolen radios and coded announcements."
)
OLD_A_R2_STATEMENT = (
    "Michelle shares one unhurried moment with Kristin, then explains that freeing this block means little without "
    "exposing the other sites."
)
OLD_A_R1_LENGTH = 169
OLD_A_R2_LENGTH = 135
NEW_A_R1_STATEMENT = (
    "Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded "
    "announcements."
)
NEW_A_R2_STATEMENT = "Michelle has explained that freeing this block means little without exposing the other sites."
A_R1_DELIVERY = (
    "Kristin joins Michelle beside the captives. They are awake: the dose they were given is for the trip, and it "
    "wears off in the detention block. For one unhurried moment the two of them talk to each other and nobody asks "
    "anything of either. Then Michelle turns back to her coded announcements and points toward the medical level, "
    "where the experiment records wait."
)
A_R2_DELIVERY = (
    "Michelle shares one unhurried moment with Kristin. She explains that freeing this block means little without "
    "exposing the other sites. Michelle points toward the medical level, where the experiment records wait."
)


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


def _opening_prompt(monkeypatch):
    captured: list[dict[str, object]] = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps(
                {"narration": json.dumps({"segments": [{"kind": "narration", "text": "Fixture."}]})}
            ).encode()

    def open_request(request, **_kwargs):
        captured.append(json.loads(request.data))
        return _Response()

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state, _engine_instance = _engine()
    CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state).opening()
    return captured[0]["user"]


def _requirement_pairs(requirements):
    return tuple((requirement.fact_id, requirement.equals) for requirement in requirements)


def _establish_pairs(operations):
    return tuple((operation.fact_id, operation.value) for operation in operations)


def _authored_provider(*knowledge_ids: str):
    queue = list(knowledge_ids)

    def provider(_command: str):
        knowledge_id = queue.pop(0)
        entry = PACKAGE.knowledge_indexes.by_id[knowledge_id]
        return {
            "segments": [{"kind": "narration", "text": entry.delivery_text, "grounding_ids": [knowledge_id]}],
            "selected_knowledge_ids": [knowledge_id],
        }

    return provider


def _turn_text(result) -> str:
    return " ".join(segment.text for segment in result.segments)


def test_3a_a_r1_delivery_uses_the_join_wording_exactly() -> None:
    delivery = _entries()["k_sl_3a_a_r1"].delivery_text
    assert delivery == A_R1_DELIVERY
    assert "finds Michelle alive" not in delivery
    assert "the dose they were given is for the trip" in delivery
    assert "points toward the medical level" in delivery


def test_3a_a_variants_keep_their_literal_dependencies_and_a_r2_delivery() -> None:
    entries = _entries()
    assert _requirement_pairs(entries["k_sl_3a_a_r1"].requires) == ()
    assert _establish_pairs(entries["k_sl_3a_a_r1"].establishes) == (
        ("michelle_reached", True),
        ("uprising_prepared", True),
    )
    assert _requirement_pairs(entries["k_sl_3a_a_r2"].requires) == ()
    assert _establish_pairs(entries["k_sl_3a_a_r2"].establishes) == (
        ("michelle_reached", True),
        ("uprising_prepared", True),
    )
    assert entries["k_sl_3a_a_r2"].delivery_text == A_R2_DELIVERY


def test_3a_a_statements_change_together_without_changing_their_contracts() -> None:
    entries = _entries()
    expected_contracts = {
        "k_sl_3a_a_r1": {
            "delivery_text": A_R1_DELIVERY,
            "must_convey": (),
            "requires": (),
            "establishes": (("michelle_reached", True), ("uprising_prepared", True)),
            "action_evidence": (
                (
                    "look",
                    "search",
                    "check",
                    "examine",
                    "inspect",
                    "read",
                    "study",
                    "find",
                    "trace",
                    "follow",
                    "enter",
                    "listen",
                    "free",
                    "help",
                    "use",
                    "organize",
                    "coordinate",
                    "rescue",
                ),
                (
                    "Michelle",
                    "Michelle's voice",
                    "radio voice",
                    "the radio voice",
                    "stolen radio",
                    "stolen radios",
                    "coded announcement",
                    "coded announcements",
                    "holding block",
                    "holding blocks",
                    "captives",
                    "the captives",
                    "prisoners",
                    "the prisoners",
                    "prisoner escape",
                    "the prisoner escape",
                    "detention block",
                ),
            ),
            "earn_when": "finds Michelle in detention, frees the captives, or helps Michelle",
        },
        "k_sl_3a_a_r2": {
            "delivery_text": A_R2_DELIVERY,
            "must_convey": (),
            "requires": (),
            "establishes": (("michelle_reached", True), ("uprising_prepared", True)),
            "action_evidence": (
                (
                    "ask",
                    "question",
                    "talk",
                    "speak",
                    "tell",
                    "press",
                    "discuss",
                    "inquire",
                    "probe",
                    "consult",
                    "listen",
                    "hear",
                ),
                (
                    "Michelle",
                    "other site",
                    "other sites",
                    "the other sites",
                    "more sites",
                    "other facility",
                    "hidden sites",
                    "the sites",
                ),
            ),
            "earn_when": "asks Michelle about other sites",
        },
    }
    for entry_id, expected in expected_contracts.items():
        entry = entries[entry_id]
        assert entry.statement == {"k_sl_3a_a_r1": NEW_A_R1_STATEMENT, "k_sl_3a_a_r2": NEW_A_R2_STATEMENT}[entry_id]
        assert len(entry.statement) < {"k_sl_3a_a_r1": OLD_A_R1_LENGTH, "k_sl_3a_a_r2": OLD_A_R2_LENGTH}[entry_id]
        assert not any(term in entry.statement for term in ("unhurried", "share", "shares", "reaches Michelle alive"))
        assert entry.delivery_text == expected["delivery_text"]
        assert entry.must_convey == expected["must_convey"]
        assert _requirement_pairs(entry.requires) == expected["requires"]
        assert _establish_pairs(entry.establishes) == expected["establishes"]
        assert entry.action_evidence == expected["action_evidence"]
        assert entry.earn_when == expected["earn_when"]


def test_3a_opening_does_not_earn_arrival_but_freeing_captives_does() -> None:
    state, engine = _engine()
    assert not any(state.facts.matching(fact_id, "story") for fact_id in ARRIVED)

    engine.provider = _authored_provider("k_sl_3a_a_r1")
    engine.turn("Free the captives.")
    assert all(state.facts.matching(fact_id, "story") for fact_id in ARRIVED)


def test_3a_authored_a_turn_does_not_repeat_the_quiet_moment() -> None:
    for command, entry_id in (
        ("Free the captives.", "k_sl_3a_a_r1"),
        ("Ask Michelle about other sites.", "k_sl_3a_a_r2"),
    ):
        state, engine = _engine()
        engine.provider = _authored_provider(entry_id)
        text = _turn_text(engine.turn(command)).casefold()
        assert text.count("unhurried moment") <= 1

    state, engine = _engine(turn_index=12)
    text = _turn_text(engine.turn("Wait and watch the block.")).casefold()
    assert "kristin reaches michelle among the holding blocks" in text
    assert text.count("unhurried moment") <= 1


def test_3a_michelle_cue_is_not_reoffered_after_save_load_and_revisit() -> None:
    state, engine = _engine()
    engine.provider = _authored_provider("k_sl_3a_a_r1")
    engine.turn("Free the captives.")

    restored = RuntimeState.bootstrap(PACKAGE)
    restored.restore_snapshot(RuntimeSnapshot.model_validate_json(state.snapshot().model_dump_json()))
    restored.current_scene_id = "3A"
    restored_engine = RuntimeEngine(
        restored,
        lambda _command: {"segments": [{"kind": "narration", "text": "The block is quiet."}]},
    )
    restored_engine._activate_pacing()
    assert restored.staged_cue_fact_id != "michelle_reached"
    assert "Michelle speaks into a stolen radio beside the captives." not in {
        segment.text for segment in restored_engine.turn("Look around.").segments
    }


def test_3a_wording_and_runtime_contracts_are_unchanged_except_for_the_requested_objective() -> None:
    frame = next(item for item in PACKAGE.knowledge.scene_frames if item.scene_id == "3A")
    assert frame.pressure == "Join the uprising"
    assert frame.situation.endswith("Michelle is beside the captives.")
    assert _entries()["k_scene_3a_entry"].statement == "Supporting the uprising is the immediate priority."
    assert _scene().objective == "Join the uprising"


def test_3a_michelle_handoff_delivery_is_unchanged() -> None:
    delivery = next(item for item in PACKAGE.deliveries if item.fact_id == "michelle_reached")
    assert delivery.cue_text == "Michelle speaks into a stolen radio beside the captives."
    assert delivery.fallback_text == (
        "Kristin reaches Michelle among the holding blocks in the detention sector. They share one unhurried moment "
        "before Michelle turns back to the radio and the rescue."
    )
    assert delivery.must_convey == (
        (
            "Kristin reaches Michelle",
            "reunion with Michelle",
            "Michelle is reached",
            "Kristin finds Michelle",
            "they are reunited",
            "Kristin reaches her",
        ),
        (
            "detention sector",
            "holding blocks",
            "Michelle's cell",
            "prisoner block",
            "detention holding block",
            "the cell block",
        ),
    )


def test_3a_reveal_ids_and_dependencies_are_unchanged() -> None:
    entries = _entries()
    assert {entry_id for entry_id in entries if entry_id.startswith("k_sl_3a_")} == {
        "k_sl_3a_a_r1",
        "k_sl_3a_a_r2",
        "k_sl_3a_b_r1",
        "k_sl_3a_b_r2",
        "k_sl_3a_c_r1",
        "k_sl_3a_c_r2",
        "k_sl_3a_d_r1",
        "k_sl_3a_d_r2",
        "k_sl_3a_e_r1",
        "k_sl_3a_f_r1",
        "k_sl_3a_g_r1",
        "k_sl_3a_h_r1",
        "k_sl_3a_i_r1",
    }
    expected = {
        "k_sl_3a_a_r1": ((), (("michelle_reached", True), ("uprising_prepared", True))),
        "k_sl_3a_a_r2": ((), (("michelle_reached", True), ("uprising_prepared", True))),
        "k_sl_3a_c_r1": (
            (("michelle_reached", True), ("uprising_prepared", True), ("military_override_codes_available", True)),
            (("detention_uprising_started", True),),
        ),
        "k_sl_3a_c_r2": (
            (
                ("michelle_reached", True),
                ("uprising_prepared", True),
                ("military_override_codes_available", True),
                ("override_codes_deadline_known", True),
            ),
            (("detention_uprising_started", True),),
        ),
    }
    for entry_id, (requires, establishes) in expected.items():
        entry = entries[entry_id]
        assert _requirement_pairs(entry.requires) == requires
        assert _establish_pairs(entry.establishes) == establishes


def test_3a_scene_entry_does_not_auto_complete_reveals() -> None:
    state, _engine_instance = _engine()
    assert not any(
        state.facts.matching(fact_id, "story")
        for fact_id in ("michelle_reached", "uprising_prepared", "detention_uprising_started")
    )


def test_3a_opening_keeps_the_recorded_character_names(monkeypatch) -> None:
    prompt = _opening_prompt(monkeypatch)
    characters = prompt.split("CHARACTERS:\n", 1)[1].split("\n\n", 1)[0]
    names = {line[2:].split(" is ", 1)[0] for line in characters.splitlines()}
    assert names == {"Kristin Schweitzer", "Dr. Michelle McGehee", "Brandon Corfman", "Imprisoned senior official"}


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
            ("lemon cake", "saturday"),
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
    # Echo: the narrator writes Michelle's feeling itself (2 of 4 replicates), so the delivery says only that the
    # details are right.
    proof_text = proof.delivery_text.casefold()
    assert not any(word in proof_text for word in ("sorry", "wall", "missed", "facility"))
    assert "never saw" in proof.statement and "kitchen calendar" in proof.statement
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


def test_the_uprising_signal_puts_the_stolen_radio_in_kristins_hands():
    state, _ = _engine()
    before = world_for(PACKAGE, state.facts)
    assert before.holder("stolen_radio") is None
    state.facts.assert_fact(Fact(predicate="detention_uprising_started", subject="story", value="true"))
    assert apply_world_effects(PACKAGE, state.facts) == ()
    after = world_for(PACKAGE, state.facts)
    assert after.holder("stolen_radio") == "kristin"


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
