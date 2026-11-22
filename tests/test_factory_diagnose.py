import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from factory.guard import LimitSleep, ModelNotAllowed
from factory.stations.diagnose import (
    CAUSES,
    DIAGNOSE_BRIEF,
    ClassifierReply,
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
            '{"unclear": {"cause": "no_authored_outcome", "why": "The command has no authored result."}}', 17
        )

    result = diagnose_handler(classifier=classifier)(ticket({"failing_turns": [packet]}), NOW)
    row = result.payload_updates["diagnosis"]["rows"][0]
    assert len(prompts) == 1
    assert DIAGNOSE_BRIEF in prompts[0]
    assert '"player_input"' in prompts[0]
    assert row["cause"] == "no_authored_outcome"
    assert row["signals"]["decided_by"] == "classifier"
    assert result.tokens == 17

    for answer in ("{}", "[]", '{"unclear": {"cause": "not-a-cause", "why": "bad"}}', "garbage"):

        def stub(*_args, answer=answer) -> ClassifierReply:
            return ClassifierReply(answer, 1)

        result = diagnose_handler(classifier=stub)(ticket({"failing_turns": [packet]}), NOW)
        assert result.payload_updates["diagnosis"]["rows"][0]["cause"] == "unclear"


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
