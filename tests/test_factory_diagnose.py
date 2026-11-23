import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from factory.guard import LimitSleep, ModelNotAllowed
from factory.stations.diagnose import (
    CAUSES,
    DIAGNOSE_BRIEF,
    DIAGNOSE_VERSION,
    ClassifierReply,
    _counts,
    _known_word,
    _summary,
    default_classifier,
    diagnose_handler,
    diagnose_turn,
    diagnose_turns,
)
from factory.tickets import Station, Ticket
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
STORY_ROOT = ROOT / "data/stories/continuity-initiative"
FIXTURE = ROOT / "tests/fixtures/factory/stuck_packets_1a.json"
PACKAGE = load_story_package(STORY_ROOT)
NOW = datetime(2026, 11, 22, 12, tzinfo=UTC)


def packets() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def ticket(payload: dict, *, ticket_id: str = "diagnose-ticket") -> Ticket:
    stamp = NOW.isoformat()
    return Ticket(ticket_id, "1A", Station.DIAGNOSE, 1000, stamp, stamp, payload=payload)


def test_gold_diagnoses_and_every_packet_has_one_cause() -> None:
    values = {packet["key"].removeprefix("smoke18c-1A-"): diagnose_turn(packet, PACKAGE) for packet in packets()}

    assert values["r2-t11"]["cause"] == "match_miss_on_offered_candidate"
    for key in ("r1-t6", "r1-t8", "r3-t11"):
        assert values[key]["cause"] == "lead_outside_scene"
    assert values["r2-t4"]["cause"] == "claim_not_offered"
    assert "k_sl_1a_g_r2" in values["r2-t4"]["signals"]["claim_ids"]
    assert values["r2-t13"]["cause"] == "claim_not_offered"
    assert "k_sl_1a_i_r1" in values["r2-t13"]["signals"]["claim_ids"]
    assert values["r3-t3"]["cause"] == "claim_not_offered"
    assert "k_sl_1a_j_r1" in values["r3-t3"]["signals"]["claim_ids"]
    assert values["r2-t9"]["cause"] == "no_authored_outcome"
    assert values["r2-t12"]["cause"] == "claim_wording_miss"
    assert values["r1-t4"]["cause"] == "no_authored_outcome"
    assert values["r2-t6"]["cause"] == "no_authored_outcome"
    assert values["r3-t5"]["cause"] == "no_authored_outcome"
    assert values["r3-t6"]["cause"] == "claim_wording_miss"
    assert values["r3-t9"]["cause"] == "no_authored_outcome"
    assert values["r2-t12"]["signals"]["missing"] == [{"claim_id": "k_sl_1a_i_r1", "group": 0}]
    assert len(values) == 21
    assert all(row["cause"] in CAUSES for row in values.values())


def test_pure_diagnosis_is_deterministic_and_respects_unknown_words() -> None:
    packet = {"key": "synthetic", "scene": "1A", "player_input": "Examine the zarglething", "candidates_offered": []}
    first = diagnose_turn(packet, PACKAGE)
    second = diagnose_turn(packet, PACKAGE)
    assert diagnose_turns([packet], PACKAGE) == [first]
    assert first == second
    assert first["cause"] == "unknown_object"
    assert "zarglething" in first["signals"]["unknown_words"]

    assert _known_word("approaching", {"approach"})
    assert _known_word("using", {"use"})
    modifier = diagnose_turn(
        {
            "key": "modifier",
            "scene": "1A",
            "player_input": "Question the suspicious officer about Michelle.",
            "candidates_offered": [],
        },
        PACKAGE,
    )
    assert modifier["cause"] == "no_authored_outcome"
    assert "suspicious" not in modifier["signals"].get("unknown_words", [])

    for player_input in ("Go to the old warehouse.", "Take the note from the hidden compartment."):
        assert (
            diagnose_turn(
                {"key": "unknown", "scene": "1A", "player_input": player_input, "candidates_offered": []}, PACKAGE
            )["cause"]
            == "unknown_object"
        )


def _synthetic_package(*claims: SimpleNamespace) -> SimpleNamespace:
    entity = SimpleNamespace(
        id="known_entity",
        name="known entity",
        aliases=(),
        scoped_aliases=(),
        description="",
        narrator_bio="",
    )
    location = SimpleNamespace(
        id="known_place",
        name="known place",
        aliases=(),
        scoped_aliases=(),
        parent=None,
        description="",
        narrator_bio="",
    )
    metadata = SimpleNamespace(
        scene_id="scene",
        participant_ids=("known_entity",),
        item_ids=(),
        location_id="known_place",
        item_placements={},
        character_placements={},
        entry_text="",
        entry_variants=(),
    )
    by_id = {claim.id: claim for claim in claims}
    return SimpleNamespace(
        world=SimpleNamespace(locations=(location,), npcs=(entity,), items=(), groups=()),
        scenes=(SimpleNamespace(metadata=metadata),),
        knowledge=SimpleNamespace(knowledge=()),
        knowledge_indexes=SimpleNamespace(
            scene_to_candidates={"scene": tuple(claim.id for claim in claims)},
            by_id=by_id,
            entity_alias_to_entities={},
            alias_to_knowledge={},
        ),
    )


def test_claim_wording_miss_requires_exactly_one_missing_group() -> None:
    wording = SimpleNamespace(id="claim_wording", action_evidence=(("inspect",), ("known entity",)))
    row = diagnose_turn(
        {"key": "wording", "scene": "scene", "player_input": "Question known entity", "candidates_offered": []},
        _synthetic_package(wording),
    )
    assert row["cause"] == "claim_wording_miss"
    assert row["signals"] == {
        "claim_ids": ["claim_wording"],
        "missing": [{"claim_id": "claim_wording", "group": 0}],
        "hypothesis": True,
        "decided_by": "rule",
    }
    assert "claim_wording" in row["why"]

    all_groups = SimpleNamespace(id="claim_all", action_evidence=(("inspect",), ("known entity",)))
    assert (
        diagnose_turn(
            {"key": "all", "scene": "scene", "player_input": "Inspect known entity", "candidates_offered": []},
            _synthetic_package(all_groups),
        )["cause"]
        == "claim_not_offered"
    )

    two_missing = SimpleNamespace(id="claim_two", action_evidence=(("inspect",), ("known entity",), ("detail",)))
    assert (
        diagnose_turn(
            {"key": "two", "scene": "scene", "player_input": "Inspect", "candidates_offered": []},
            _synthetic_package(two_missing),
        )["cause"]
        != "claim_wording_miss"
    )

    single_group = SimpleNamespace(id="claim_single", action_evidence=(("inspect",),))
    assert (
        diagnose_turn(
            {"key": "single", "scene": "scene", "player_input": "Inspect", "candidates_offered": []},
            _synthetic_package(single_group),
        )["cause"]
        == "claim_not_offered"
    )

    unoffered = SimpleNamespace(id="claim_unoffered", action_evidence=(("inspect",), ("known entity",)))
    assert (
        diagnose_turn(
            {"key": "unoffered", "scene": "scene", "player_input": "Inspect known entity", "candidates_offered": []},
            _synthetic_package(unoffered),
        )["cause"]
        == "claim_not_offered"
    )


def test_actor_mismatch_is_not_a_wording_miss() -> None:
    row = diagnose_turn(
        {
            "key": "actor",
            "scene": "1A",
            "player_input": "Ask Officer Reyes about his orders",
            "candidates_offered": [],
        },
        PACKAGE,
    )
    assert row["cause"] == "no_authored_outcome"
    assert row["cause"] != "claim_wording_miss"


def test_scoped_alias_does_not_make_scene_name_outside_scene() -> None:
    row = diagnose_turn(
        {
            "key": "scope",
            "scene": "1A",
            "player_input": "Inspect Officer Reyes's badge",
            "candidates_offered": [],
        },
        PACKAGE,
    )
    assert row["cause"] == "no_authored_outcome"
    assert "inspector badges" not in row["signals"].get("entities", [])


def test_prior_narration_proves_unknown_referent() -> None:
    row = diagnose_turn(
        {
            "key": "prior",
            "scene": "1A",
            "player_input": "Open the notebook",
            "previous_narration": "Kristin finds a small notebook belonging to Michelle.",
            "candidates_offered": [],
        },
        PACKAGE,
    )
    assert row["cause"] == "follows_prior_narration"
    assert row["signals"]["introduced_words"] == ["notebook"]
    assert "notebook" in row["signals"]["previous_narration"]


def test_missing_prior_narration_is_not_prior_provenance() -> None:
    packets = [
        {"key": "missing", "scene": "1A", "player_input": "Open the notebook", "candidates_offered": []},
        {
            "key": "none",
            "scene": "1A",
            "player_input": "Open the notebook",
            "previous_narration": None,
            "candidates_offered": [],
        },
        {
            "key": "irrelevant",
            "scene": "1A",
            "player_input": "Open the notebook",
            "previous_narration": "Nothing relevant happens here.",
            "candidates_offered": [],
        },
    ]

    for packet in packets:
        row = diagnose_turn(packet, PACKAGE)
        assert row["cause"] == "unknown_object"
        assert row["cause"] != "follows_prior_narration"
        assert "previous_narration" not in row["signals"]
        assert "introduced_words" not in row["signals"]

    sibling = diagnose_turn(
        {
            "key": "sibling",
            "scene": "1A",
            "player_input": "Open the notebook",
            "previous_narration": "Kristin finds a small notebook belonging to Michelle.",
            "candidates_offered": [],
        },
        PACKAGE,
    )
    assert sibling["cause"] == "follows_prior_narration"
    assert sibling["signals"]["introduced_words"] == ["notebook"]
    assert "notebook" in sibling["signals"]["previous_narration"]


def test_delivered_claim_is_not_reported_as_newly_unoffered() -> None:
    row = diagnose_turn(
        {
            "key": "delivered",
            "scene": "1A",
            "player_input": "Inspect the workstation",
            "candidates_offered": [],
            "delivered_before": ["k_sl_1a_g_r1"],
            "delivered_before_turns": {"k_sl_1a_g_r1": 3},
        },
        PACKAGE,
    )
    assert row["cause"] == "already_delivered"
    assert row["signals"]["delivered_at_turn"] == 3
    assert "Claim k_sl_1a_g_r1 was delivered at turn 3." in row["why"]


def test_unmet_requirement_is_reported_for_unoffered_claim() -> None:
    row = diagnose_turn(
        {
            "key": "unmet",
            "scene": "1A",
            "player_input": "Read Michelle's text on her phone",
            "candidates_offered": [],
            "facts_before": {"patrol_in_house": True},
        },
        PACKAGE,
    )
    assert row["cause"] == "claim_not_offered"
    assert row["signals"]["unmet"] == "patrol_in_house"
    assert "patrol_in_house" in row["why"]


def test_sibling_delivery_explains_unoffered_alternative() -> None:
    row = diagnose_turn(
        {
            "key": "sibling",
            "scene": "1A",
            "player_input": "Check the front gate",
            "candidates_offered": [],
            "delivered_before": ["k_sl_1a_c_r1"],
            "delivered_before_turns": {"k_sl_1a_c_r1": 3},
        },
        PACKAGE,
    )
    assert row["cause"] == "claim_not_offered"
    assert row["signals"]["spent_by_sibling"] == "k_sl_1a_c_r1"


def test_legacy_packet_keeps_unknown_object_label() -> None:
    row = diagnose_turn(
        {"key": "legacy", "scene": "1A", "player_input": "Open the notebook", "candidates_offered": []},
        PACKAGE,
    )
    assert row["cause"] == "unknown_object"


def test_new_causes_are_counted_and_summarized() -> None:
    rows = [{"cause": cause} for cause in ("already_delivered", "follows_prior_narration", "claim_wording_miss")]
    counts = _counts(rows)
    assert counts["already_delivered"] == 1
    assert counts["follows_prior_narration"] == 1
    assert "already_delivered 1" in _summary(counts)


def test_causes_and_classifier_accept_only_non_unclear_causes() -> None:
    assert "claim_wording_miss" in CAUSES
    assert "already_delivered" in CAUSES
    assert "follows_prior_narration" in CAUSES
    assert CAUSES[-1] == "unclear"
    assert DIAGNOSE_VERSION == "diagnose-v2"


def test_handler_skips_classifier_when_rules_decide_every_turn() -> None:
    calls: list[str] = []

    def classifier(*_args) -> ClassifierReply:
        calls.append("called")
        return ClassifierReply("{}", 10)

    result = diagnose_handler(classifier=classifier)(ticket({"failing_turns": packets()}), NOW)
    assert result.passed
    assert calls == []
    assert len(result.payload_updates["diagnosis"]["rows"]) == 21


def test_handler_classifies_unclear_turn_once_and_keeps_bad_answers_unclear() -> None:
    packet = {
        "key": "unclear",
        "scene": "1A",
        "player_input": "",
        "narration": "narration",
        "candidates_offered": [],
    }
    prompts: list[str] = []

    def classifier(_ticket, prompt: str, _now: datetime) -> ClassifierReply:
        prompts.append(prompt)
        return ClassifierReply(
            '{"unclear": {"cause": "claim_wording_miss", "why": "The claim misses one phrase."}}', 17
        )

    result = diagnose_handler(classifier=classifier)(ticket({"failing_turns": [packet]}), NOW)
    row = result.payload_updates["diagnosis"]["rows"][0]
    assert len(prompts) == 1
    assert DIAGNOSE_BRIEF in prompts[0]
    assert '"player_input"' in prompts[0]
    assert row["cause"] == "claim_wording_miss"
    assert row["signals"]["decided_by"] == "classifier"
    assert result.tokens == 17

    for answer in (
        "{}",
        "[]",
        '{"unclear": {"cause": "unclear", "why": "bad"}}',
        '{"unclear": {"cause": "not-a-cause", "why": "bad"}}',
        "garbage",
    ):

        def stub(*_args, answer=answer) -> ClassifierReply:
            return ClassifierReply(answer, 1)

        result = diagnose_handler(classifier=stub)(ticket({"failing_turns": [packet]}), NOW)
        assert result.payload_updates["diagnosis"]["rows"][0]["cause"] == "unclear"


def test_classifier_prompt_carries_only_present_provenance() -> None:
    packet = {
        "key": "unclear",
        "scene": "1A",
        "player_input": "",
        "narration": "narration",
        "candidates_offered": [],
        "previous_narration": "A small notebook appears.",
        "delivered_before": ["k_old"],
        "rejected_code": "known_term",
        "rejected_message": "term was unavailable",
        "facts_before": {"patrol_in_house": False},
    }
    prompts: list[str] = []

    def classifier(_ticket, prompt: str, _now: datetime) -> ClassifierReply:
        prompts.append(prompt)
        return ClassifierReply("{}", 0)

    diagnose_handler(classifier=classifier)(ticket({"failing_turns": [packet]}), NOW)
    assert len(prompts) == 1
    for field in ("previous_narration", "delivered_before", "rejected_code", "rejected_message", "facts_before"):
        assert f'"{field}"' in prompts[0]


def test_handler_reuses_record_and_recomputes_when_input_changes(tmp_path: Path) -> None:
    calls: list[str] = []

    def classifier(*_args) -> ClassifierReply:
        calls.append("called")
        return ClassifierReply("{}", 3)

    payload = {"failing_turns": [{"key": "u", "scene": "1A", "player_input": ""}], "workspace": str(tmp_path)}
    handler = diagnose_handler(classifier=classifier)
    first = handler(ticket(payload, ticket_id="saved/id"), NOW)
    second = handler(ticket(payload, ticket_id="saved/id"), NOW)
    assert first.passed and second.passed
    assert len(calls) == 1
    assert (tmp_path / "saved_id" / "diagnosis.json").is_file()
    changed = {**payload, "failing_turns": [{"key": "u", "scene": "1A", "player_input": "!"}]}
    handler(ticket(changed, ticket_id="saved/id"), NOW)
    assert len(calls) == 2


def test_handler_fails_closed_and_does_not_mutate_payload() -> None:
    original = {"failing_turns": []}
    result = diagnose_handler()(ticket(original), NOW)
    assert not result.passed and result.output == "missing payload key: failing_turns"
    assert original == {"failing_turns": []}

    failing = {"failing_turns": [{"key": "x", "scene": "1A", "player_input": "look"}]}
    result = diagnose_handler(package_loader=lambda _path: (_ for _ in ()).throw(RuntimeError("bad")))(
        ticket(failing), NOW
    )
    assert not result.passed
    assert result.output == "could not load the story package for the diagnosis"
    assert failing == {"failing_turns": [{"key": "x", "scene": "1A", "player_input": "look"}]}


def _guarded_root(tmp_path: Path) -> None:
    (tmp_path / "factory/config").mkdir(parents=True)
    shutil.copy(ROOT / "factory/config/allowlist.json", tmp_path / "factory/config/allowlist.json")
    shutil.copy(ROOT / "factory/config/factory.json", tmp_path / "factory/config/factory.json")


def test_default_classifier_uses_diagnose_pin_and_records_ledger(tmp_path: Path) -> None:
    _guarded_root(tmp_path)
    stream = (ROOT / "tests/fixtures/factory/claude_planner_stream.jsonl").read_text(encoding="utf-8")
    calls: list[list[str]] = []

    def run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stream, "")

    classifier = default_classifier(tmp_path, run=run)
    result = classifier(ticket({}), "prompt", NOW)
    assert result.tokens > 0
    ledger = (tmp_path / "factory/state/ledger.jsonl").read_text(encoding="utf-8")
    assert '"station":"diagnose"' in ledger
    assert calls

    with pytest.raises(ModelNotAllowed):
        default_classifier(tmp_path, run=run, model_id="claude-opus-5-5")(ticket({}), "prompt", NOW)
    assert len(calls) == 1


def test_default_classifier_propagates_limit_sleep_without_saving(tmp_path: Path) -> None:
    _guarded_root(tmp_path)
    called = False

    def classifier(*_args) -> ClassifierReply:
        nonlocal called
        called = True
        raise LimitSleep("claude_code", None)

    payload = {"failing_turns": [{"key": "u", "scene": "1A", "player_input": ""}], "workspace": str(tmp_path)}
    with pytest.raises(LimitSleep):
        diagnose_handler(classifier=classifier)(ticket(payload), NOW)
    assert called
    assert not list(tmp_path.rglob("diagnosis.json"))
