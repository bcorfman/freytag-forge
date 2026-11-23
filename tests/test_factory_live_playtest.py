import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from factory.cloudflare_spend import read_worker_budget, spend_between
from factory.guard import BudgetExhausted, LimitSleep, SpendLedger, Usage
from factory.stations import build_handlers
from factory.stations.live_playtest import (
    _DEFAULTS,
    EARNED_EXIT_CAUSES,
    collect_player_usage,
    live_playtest_handler,
    load_prices,
    main,
    player_spend,
    playtest_summary,
    report_to_packets,
    usage_cost_usd,
)
from factory.stations.triage import _validate_packet, classify_turns
from factory.tickets import Station, TicketClass

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/factory/blind_player_report_small.json"
NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def no_worker_network(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)


def report() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def ticket(payload: dict, scene: str = "1A") -> SimpleNamespace:
    return SimpleNamespace(payload=payload, scene=scene, id="stage7")


def clean_report() -> dict:
    value = report()
    value["replicates"] = value["replicates"][:1]
    return value


def write_artifact(root: Path, value: dict) -> Path:
    path = root / "artifacts" / "e2e-blind-player.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    os.utime(path, (NOW.timestamp() + 1, NOW.timestamp() + 1))
    return path


def test_player_usage_cost_and_report_shapes(tmp_path: Path) -> None:
    price_path = tmp_path / "prices.json"
    price_path.write_text(
        json.dumps(
            {
                "models": {
                    "gpt-5.6-luna": {"input": 0.20, "cached_input": 0.02, "output": 1.20},
                }
            }
        ),
        encoding="utf-8",
    )
    prices = load_prices(price_path)
    usage = {
        "model": "gpt-5.6-luna",
        "calls": 3,
        "input_tokens": 1_000_000,
        "cached_input_tokens": 400_000,
        "output_tokens": 100_000,
    }
    assert usage_cost_usd(usage, prices) == pytest.approx(0.248)
    assert usage_cost_usd({**usage, "cached_input_tokens": 2_000_000}, prices) == pytest.approx(0.14)
    assert usage_cost_usd({**usage, "model": "unknown"}, prices) is None

    single = {"replicates": [{"replicate": 1, "scene": "1A", "turns": [], "player_usage": usage}]}
    all_scenes = {"replicates": [{"replicate": 1, "scenes": [{"scene": "1A", "turns": [], "player_usage": usage}]}]}
    assert collect_player_usage(single) == [usage]
    assert collect_player_usage(all_scenes) == [usage]
    spend, tokens, calls, missing = player_spend(single, prices)
    assert spend == pytest.approx(0.248)
    assert (tokens, calls, missing) == (1_100_000, 3, 0)


def test_player_spend_unknown_when_one_scene_run_is_missing() -> None:
    value = clean_report()
    value["replicates"].append({"replicate": 2, "scene": "1A", "turns": []})
    prices = {"models": {"gpt-5.6-luna": {"input": 0.2, "cached_input": 0.02, "output": 1.2}}}
    spend, tokens, calls, missing = player_spend(value, prices)
    assert spend is None
    assert (tokens, calls, missing) == (120, 1, 1)


def _ledger_rows(path: Path) -> list[Usage]:
    return SpendLedger(path)._read()


def _live_handler(tmp_path: Path, runner, ledger: SpendLedger, read_budget=lambda: None):
    return live_playtest_handler(
        tmp_path,
        runner=runner,
        fetch_version=lambda _url: {"channel": "staging", "runtime": "scene-v1", "sha": "abc"},
        now_fn=lambda: NOW,
        ledger=ledger,
        read_budget=read_budget,
    )


def test_read_worker_budget_validates_response_and_uses_origin() -> None:
    token = "secret-token"
    calls = []

    def fetch(url, received_token, timeout):
        calls.append((url, received_token, timeout))
        return 200, json.dumps(
            {
                "status": "ok",
                "day": "2026-01-01",
                "spent_micro_usd": 1200,
                "reserved_micro_usd": 300,
                "limit_micro_usd": 5000,
                "extra": "discarded",
            }
        )

    result = read_worker_budget(
        {
            "CLOUDFLARE_WORKER_URL": "https://worker.example.test/narration/v1",
            "CLOUDFLARE_WORKER_TOKEN": token,
        },
        fetch=fetch,
    )
    assert result == {
        "status": "ok",
        "day": "2026-01-01",
        "spent_micro_usd": 1200,
        "reserved_micro_usd": 300,
        "limit_micro_usd": 5000,
    }
    assert calls == [("https://worker.example.test/budget", token, 10)]
    assert token not in repr(result)


@pytest.mark.parametrize(
    "response",
    [
        (500, "{}"),
        (200, "not json"),
        (200, json.dumps({"status": "ok", "day": "2026-01-01"})),
        (200, json.dumps({"status": "narration", "day": "2026-01-01", "spent_micro_usd": 1})),
        (
            200,
            json.dumps(
                {
                    "status": "ok",
                    "day": "2026-01-01",
                    "spent_micro_usd": -1,
                    "reserved_micro_usd": 0,
                    "limit_micro_usd": 1,
                }
            ),
        ),
        (
            200,
            json.dumps(
                {
                    "status": "ok",
                    "day": "2026-01-01",
                    "spent_micro_usd": True,
                    "reserved_micro_usd": 0,
                    "limit_micro_usd": 1,
                }
            ),
        ),
        (
            200,
            json.dumps(
                {
                    "status": "ok",
                    "day": "2026-02-30",
                    "spent_micro_usd": 0,
                    "reserved_micro_usd": 0,
                    "limit_micro_usd": 1,
                }
            ),
        ),
    ],
)
def test_read_worker_budget_returns_none_for_invalid_responses(response) -> None:
    result = read_worker_budget(
        {"CLOUDFLARE_WORKER_URL": "https://worker.example.test/path", "CLOUDFLARE_WORKER_TOKEN": "secret"},
        fetch=lambda _url, _token, _timeout: response,
    )
    assert result is None


def test_read_worker_budget_returns_none_for_missing_config_or_network_error() -> None:
    assert read_worker_budget({}, fetch=lambda _url, _token, _timeout: (200, "{}")) is None

    def fail(_url, _token, _timeout):
        raise OSError("offline")

    assert (
        read_worker_budget(
            {"CLOUDFLARE_WORKER_URL": "https://worker.example.test", "CLOUDFLARE_WORKER_TOKEN": "secret"},
            fetch=fail,
        )
        is None
    )


def test_default_fetch_sends_a_non_default_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self) -> bytes:
            return b"{}"

    def fake_urlopen(request, timeout):
        seen["agent"] = request.get_header("User-agent")
        return _Response()

    monkeypatch.setattr("factory.cloudflare_spend.urllib.request.urlopen", fake_urlopen)
    from factory.cloudflare_spend import _default_fetch

    _default_fetch("https://worker.example/budget", "t", 1)
    assert seen["agent"] and "urllib" not in seen["agent"].lower()


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        ({"day": "2026-01-01", "spent_micro_usd": 8}, {"day": "2026-01-01", "spent_micro_usd": 13}, 5),
        ({"day": "2026-01-01", "spent_micro_usd": 8}, {"day": "2026-01-02", "spent_micro_usd": 13}, None),
        ({"day": "2026-01-01", "spent_micro_usd": 8}, {"day": "2026-01-01", "spent_micro_usd": 3}, None),
        (None, {"day": "2026-01-01", "spent_micro_usd": 3}, None),
    ],
)
def test_spend_between(before, after, expected) -> None:
    assert spend_between(before, after) == expected


def test_live_run_records_player_spend_and_grade_path_does_not(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = SpendLedger(ledger_path)

    def runner(_env, _timeout):
        write_artifact(tmp_path, clean_report())
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")

    readings = iter(
        [
            {
                "status": "ok",
                "day": "2026-01-01",
                "spent_micro_usd": 1200,
                "reserved_micro_usd": 0,
                "limit_micro_usd": 5000,
            },
            {
                "status": "ok",
                "day": "2026-01-01",
                "spent_micro_usd": 3300,
                "reserved_micro_usd": 0,
                "limit_micro_usd": 5000,
            },
        ]
    )
    result = _live_handler(tmp_path, runner, ledger, lambda: next(readings))(ticket({"expected_sha": "abc"}), NOW)
    assert result.passed
    rows = _ledger_rows(ledger_path)
    assert len(rows) == 2
    openai_row, cloudflare_row = rows
    assert openai_row.provider == "openai"
    assert openai_row.cost_kind == "dollars"
    assert openai_row.tokens == 120
    assert openai_row.usd == pytest.approx(0.0000368)
    assert cloudflare_row.provider == "cloudflare"
    assert cloudflare_row.cost_kind == "dollars"
    assert cloudflare_row.usd == pytest.approx(0.0021)
    assert "cloudflare $0.0021" in result.output

    report_path = tmp_path / "clean.json"
    report_path.write_text(json.dumps(clean_report()), encoding="utf-8")
    reads = []
    saved = live_playtest_handler(tmp_path, ledger=ledger, read_budget=lambda: reads.append(True))(
        ticket({"report_path": report_path}), NOW
    )
    assert saved.passed
    assert len(_ledger_rows(ledger_path)) == 2
    assert reads == []


def test_day_change_between_worker_readings_records_unknown_cloudflare_spend(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")

    def runner(_env, _timeout):
        write_artifact(tmp_path, clean_report())
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")

    readings = iter(
        [
            {
                "status": "ok",
                "day": "2026-01-01",
                "spent_micro_usd": 1200,
                "reserved_micro_usd": 0,
                "limit_micro_usd": 5000,
            },
            {
                "status": "ok",
                "day": "2026-01-02",
                "spent_micro_usd": 3300,
                "reserved_micro_usd": 0,
                "limit_micro_usd": 5000,
            },
        ]
    )
    result = _live_handler(tmp_path, runner, ledger, lambda: next(readings))(ticket({"expected_sha": "abc"}), NOW)
    assert result.passed
    rows = _ledger_rows(tmp_path / "ledger.jsonl")
    assert rows[-1].provider == "cloudflare"
    assert rows[-1].cost_kind == "unknown"
    assert rows[-1].usd is None
    assert "cloudflare spend unknown" in result.output


def test_missing_player_usage_records_one_unknown_row(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = SpendLedger(ledger_path)

    def runner(_env, _timeout):
        write_artifact(tmp_path, report())
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")

    result = _live_handler(tmp_path, runner, ledger)(ticket({"expected_sha": "abc"}), NOW)
    assert not result.passed
    rows = _ledger_rows(ledger_path)
    assert len(rows) == 2
    assert rows[0].cost_kind == "unknown"
    assert rows[0].usd is None
    assert rows[0].tokens == 350
    assert rows[1].provider == "cloudflare"
    assert rows[1].cost_kind == "unknown"
    assert rows[1].usd is None


def test_runner_failure_records_unknown_spend(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = SpendLedger(ledger_path)

    def runner(_env, _timeout):
        raise RuntimeError("runner died")

    result = _live_handler(tmp_path, runner, ledger)(ticket({"expected_sha": "abc"}), NOW)
    assert not result.passed
    rows = _ledger_rows(ledger_path)
    assert len(rows) == 2
    assert rows[0].cost_kind == "unknown"
    assert rows[0].usd is None
    assert rows[0].tokens == 0
    assert rows[1].provider == "cloudflare"
    assert rows[1].cost_kind == "unknown"
    assert rows[1].usd is None


def _record_dollars(ledger: SpendLedger, provider: str, usd: float, at: datetime = NOW) -> None:
    ledger.record(
        Usage(
            at=at,
            provider=provider,
            model_id="seed",
            station="test",
            scene="1A",
            ticket_id="seed",
            tokens=1,
            usd=usd,
        )
    )


@pytest.mark.parametrize(
    ("seed_provider", "seed_usd", "expected"),
    [
        ("openai", 5.0, BudgetExhausted),
        ("openai", 1.51, BudgetExhausted),
        ("openai", 2.0, LimitSleep),
        ("cloudflare", 2.0, LimitSleep),
    ],
)
def test_live_budget_gates_refuse_before_runner(tmp_path: Path, seed_provider: str, seed_usd: float, expected) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    at = NOW - timedelta(hours=2) if seed_usd == 2.0 else NOW
    _record_dollars(ledger, seed_provider, seed_usd, at)
    calls = 0

    def runner(_env, _timeout):
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess([], 0)

    with pytest.raises(expected) as raised:
        _live_handler(tmp_path, runner, ledger)(ticket({"expected_sha": "abc"}), NOW)
    assert calls == 0
    if expected is LimitSleep:
        assert raised.value.provider == seed_provider
        assert raised.value.resume_at == datetime(2026, 1, 2, tzinfo=UTC)


def test_missing_openai_daily_cap_fails_before_runner(tmp_path: Path) -> None:
    config_path = tmp_path / "factory/config/factory.json"
    config_path.parent.mkdir(parents=True)
    config = json.loads((ROOT / "factory/config/factory.json").read_text(encoding="utf-8"))
    del config["caps"]["daily_cap_usd"]["openai"]
    config_path.write_text(json.dumps(config), encoding="utf-8")
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    calls = 0

    def runner(_env, _timeout):
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess([], 0)

    result = _live_handler(tmp_path, runner, ledger)(ticket({"expected_sha": "abc"}), NOW)
    assert not result.passed
    assert result.turns is None
    assert "missing daily cap for openai" in result.output
    assert calls == 0


def test_live_run_under_all_caps_proceeds(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl")
    calls = 0

    def runner(_env, _timeout):
        nonlocal calls
        calls += 1
        write_artifact(tmp_path, clean_report())
        return subprocess.CompletedProcess([], 0)

    result = _live_handler(tmp_path, runner, ledger)(ticket({"expected_sha": "abc"}), NOW)
    assert result.passed
    assert calls == 1


def test_packets_have_triage_shape_and_documented_routes() -> None:
    packets = report_to_packets(report())
    assert [packet["key"] for packet in packets] == ["1A-r2-t1", "1A-r3-t1", "1A-r3-t2"]
    assert set(packets[0]) == {"key", "scene", *_DEFAULTS}
    assert packets[0]["stuck"] is True
    assert packets[1]["match_issues"] == ["narration did not validate"]
    assert packets[1]["candidates_offered"] == ["panel"]
    assert packets[1]["matched_candidate"] is None
    assert packets[2]["candidates_offered"] == ["lever"]
    assert packets[2]["matched_candidate"] == "lever"
    assert packets[2]["stuck"] is False
    assert all(_validate_packet(packet) for packet in packets)
    assert [route["class"] for route in classify_turns(packets)] == [
        TicketClass.STORY_DATA.value,
        "unclear",
        "unclear",
    ]
    assert report_to_packets(clean_report()) == []


def test_packets_carry_bounded_turn_provenance() -> None:
    value = {
        "replicates": [
            {
                "replicate": 1,
                "scene": "1A",
                "turns": [
                    {
                        "turn": 1,
                        "raw_input": "Search the desk.",
                        "text": "A prior narration.",
                        "selected_knowledge_ids": ["k_old"],
                        "outcome": "committed",
                    },
                    {
                        "turn": 2,
                        "raw_input": "Open the notebook.",
                        "text": "The turn failed.",
                        "selected_knowledge_ids": [],
                        "rejected": True,
                        "guard_rejections": [{"code": "known_term", "message": "term was unavailable"}],
                        "facts_before": {"patrol_in_house": False},
                        "outcome": "rejected",
                    },
                ],
                "stuck_turns": [2],
            }
        ]
    }
    packet = report_to_packets(value)[0]
    assert packet["previous_narration"] == "A prior narration."
    assert packet["delivered_before"] == ["k_old"]
    assert packet["delivered_before_turns"] == {"k_old": 1}
    assert packet["rejected_code"] == "known_term"
    assert packet["rejected_message"] == "term was unavailable"
    assert packet["facts_before"] == {"patrol_in_house": False}


def _report_with_turn(turn: dict, *, stuck: bool = True) -> dict:
    turn.setdefault("turn", 1)
    return {
        "replicates": [
            {
                "replicate": 1,
                "scene": "1A",
                "turns": [turn],
                "stuck_turns": [1] if stuck else [],
            }
        ]
    }


def test_new_report_candidates_route_stuck_turns_through_triage() -> None:
    candidates = _report_with_turn(
        {
            "raw_input": "Search the panel.",
            "text": "The panel stays closed.",
            "outcome": "committed",
            "candidates_offered": ["a", "b"],
            "matched_candidate": None,
        }
    )
    empty = _report_with_turn(
        {
            "raw_input": "Search the panel.",
            "text": "The panel stays closed.",
            "outcome": "committed",
            "candidates_offered": [],
            "matched_candidate": None,
        }
    )

    candidate_packet = report_to_packets(candidates)[0]
    empty_packet = report_to_packets(empty)[0]
    assert candidate_packet["candidates_offered"] == ["a", "b"]
    assert candidate_packet["matched_candidate"] is None
    assert classify_turns([candidate_packet])[0]["rule"] == "R3"
    assert empty_packet["candidates_offered"] == []
    assert classify_turns([empty_packet])[0]["rule"] == "R2"


def test_new_report_matched_stuck_turn_routes_r5() -> None:
    value = _report_with_turn(
        {
            "raw_input": "Open the panel.",
            "text": "The panel remains closed.",
            "outcome": "rejected",
            "candidates_offered": ["a"],
            "matched_candidate": "b",
        }
    )
    packet = report_to_packets(value)[0]
    assert packet["candidates_offered"] == ["a", "b"]
    assert packet["matched_candidate"] == "b"
    packet["committed"] = False
    assert classify_turns([packet])[0]["rule"] == "R5"


def test_old_report_keeps_match_surrogate_and_new_report_filters_candidates() -> None:
    old = _report_with_turn(
        {
            "raw_input": "Search the panel.",
            "text": "The panel stays closed.",
            "outcome": "committed",
            "semantic_match": {"matched": "old-match"},
        }
    )
    new = _report_with_turn(
        {
            "raw_input": "Search the panel.",
            "text": "The panel stays closed.",
            "outcome": "committed",
            "semantic_match": {"matched": "new-match"},
            "candidates_offered": ["a", 3, "a", "b"],
            "matched_candidate": "new-match",
        }
    )
    old_packet = report_to_packets(old)[0]
    new_packet = report_to_packets(new)[0]
    assert old_packet["candidates_offered"] == ["old-match"]
    assert old_packet["matched_candidate"] == "old-match"
    assert new_packet["candidates_offered"] == ["a", "b", "new-match"]


def test_packets_cover_rejection_game_break_and_noncommitted_turns() -> None:
    value = clean_report()
    value["replicates"][0]["turns"].extend(
        [
            {"turn": 2, "raw_input": "bad", "text": "", "rejected": True, "rejection": "bad"},
            {"turn": 3, "raw_input": "break", "text": "", "game_break": {"outcome": "timeout"}, "outcome": "committed"},
            {"turn": 4, "raw_input": "uncommitted", "text": "", "outcome": "rejected"},
        ]
    )
    packets = report_to_packets(value, key_prefix="x-")
    assert [packet["key"] for packet in packets] == ["x-1A-r1-t2", "x-1A-r1-t3", "x-1A-r1-t4"]
    assert all(_validate_packet(packet) for packet in packets)
    assert all(route["rule"] == "R9" for route in classify_turns(packets))


def test_summary_and_gate_inputs() -> None:
    summary = playtest_summary(report())
    assert summary["scenes"] == 3
    assert summary["turns"] == 4
    assert summary["stuck_turns"] == 1
    assert summary["rejected"] == 1
    assert summary["game_breaks"] == 1
    assert summary["exit_cause"] == ["play", "none", "forced"]
    assert summary["transition_fired"] == 2
    assert summary["ending_reached"] is False
    assert playtest_summary(clean_report())["runs"][0]["exit_cause"] in EARNED_EXIT_CAUSES


def test_gate_clean_pass_timer_forced_and_empty_fail(tmp_path: Path) -> None:
    handler = live_playtest_handler(tmp_path, ledger=SpendLedger(tmp_path / "ledger.jsonl"))
    assert handler(ticket({"report_path": FIXTURE}), NOW).passed is False
    clean_path = tmp_path / "clean.json"
    clean_path.write_text(json.dumps(clean_report()), encoding="utf-8")
    try:
        assert handler(ticket({"report_path": clean_path}), NOW).passed
    finally:
        clean_path.unlink()

    for cause in ("timer", "forced"):
        value = clean_report()
        value["replicates"][0]["exit_cause"] = cause
        value["replicates"][0]["turns"][0]["transition_cause"] = cause
        path = tmp_path / f"stage7-{cause}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        try:
            result = handler(ticket({"report_path": path}), NOW)
            assert not result.passed and result.turns
        finally:
            path.unlink()

    empty = tmp_path / "stage7-empty.json"
    empty.write_text(json.dumps({"replicates": []}), encoding="utf-8")
    try:
        result = handler(ticket({"report_path": empty}), NOW)
        assert not result.passed and result.turns is None
    finally:
        empty.unlink()


def test_saved_handler_pass_failure_and_bad_file(tmp_path: Path) -> None:
    clean = tmp_path / "clean.json"
    clean.write_text(json.dumps(clean_report()), encoding="utf-8")
    failed = tmp_path / "failed.json"
    failed.write_text(json.dumps(report()), encoding="utf-8")
    handler = live_playtest_handler(tmp_path, ledger=SpendLedger(tmp_path / "ledger.jsonl"))
    passed = handler(ticket({"report_path": clean}), NOW)
    story_failed = handler(ticket({"report_path": failed}), NOW)
    bad = handler(ticket({"report_path": tmp_path / "missing.json"}), NOW)
    assert passed.passed and passed.turns is None
    assert passed.payload_updates is None
    assert not story_failed.passed and story_failed.turns
    assert story_failed.payload_updates and story_failed.payload_updates["runs"]
    assert not bad.passed and bad.turns is None


def test_saved_and_live_reports_carry_replayable_runs_on_pass_and_failure(tmp_path: Path, monkeypatch) -> None:
    replayable = clean_report()
    replayable["replicates"][0]["turns"].append(
        {
            "turn": 2,
            "raw_input": "Open the desk.",
            "text": "The desk opens.",
            "rejected": False,
            "outcome": "committed",
            "scene_id": "1A",
            "transition_cause": None,
            "grounding_ids": [],
            "game_break": None,
        }
    )
    replayable["replicates"][0]["turn_count"] = 2
    replayable_path = tmp_path / "replayable.json"
    replayable_path.write_text(json.dumps(replayable), encoding="utf-8")
    handler = live_playtest_handler(tmp_path, ledger=SpendLedger(tmp_path / "ledger.jsonl"))

    saved_pass = handler(ticket({"report_path": replayable_path}), NOW)
    saved_fail = handler(ticket({"report_path": FIXTURE}), NOW)
    assert saved_pass.passed and saved_pass.payload_updates and saved_pass.payload_updates["runs"]
    assert (
        not saved_fail.passed and saved_fail.turns and saved_fail.payload_updates and saved_fail.payload_updates["runs"]
    )

    monkeypatch.setenv("E2E_API_BASE_URL", "https://staging.example")
    reports = iter([replayable, report()])

    def runner(_env, _timeout):
        write_artifact(tmp_path, next(reports))
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")

    live = _live_handler(tmp_path, runner, SpendLedger(tmp_path / "live-ledger.jsonl"))
    live_pass = live(ticket({"expected_sha": "abc"}), NOW)
    live_fail = live(ticket({"expected_sha": "abc"}), NOW)
    assert live_pass.passed and live_pass.payload_updates and live_pass.payload_updates["runs"]
    assert not live_fail.passed and live_fail.turns and live_fail.payload_updates and live_fail.payload_updates["runs"]


def test_live_identity_failures_never_call_runner(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("E2E_API_BASE_URL", "https://staging.example")
    calls: list[tuple[dict, int]] = []

    def runner(env, timeout):
        calls.append((env, timeout))
        return subprocess.CompletedProcess([], 0)

    for version, expected in (
        ({"channel": "production", "runtime": "scene-v1", "sha": "abc"}, "abc"),
        ({"channel": "staging", "runtime": "scene-v1", "sha": "other"}, "abc"),
        ({"channel": "staging", "runtime": "scene-v1", "sha": "abc"}, None),
    ):
        handler = live_playtest_handler(
            tmp_path,
            runner=runner,
            fetch_version=lambda _url, version=version: version,
            ledger=SpendLedger(tmp_path / "ledger.jsonl"),
        )
        payload = {"expected_sha": expected}
        result = handler(ticket(payload), NOW)
        assert not result.passed and result.turns is None
    assert calls == []


def test_live_runner_called_once_and_stale_artifact_ignored(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("E2E_API_BASE_URL", "https://staging.example")
    stale = tmp_path / "artifacts/e2e-blind-player-stale.json"
    stale.parent.mkdir()
    stale.write_text("not json", encoding="utf-8")
    os.utime(stale, (NOW.timestamp() - 10, NOW.timestamp() - 10))
    calls: list[tuple[dict, int]] = []

    def runner(env, timeout):
        calls.append((env, timeout))
        write_artifact(tmp_path, clean_report())
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")

    result = live_playtest_handler(
        tmp_path,
        runner=runner,
        fetch_version=lambda url: {"channel": "staging", "runtime": "scene-v1", "sha": "abc"},
        now_fn=lambda: NOW,
        ledger=SpendLedger(tmp_path / "ledger.jsonl"),
    )(ticket({"expected_sha": "abc", "scene": "1A", "profile": "raw", "replicates": 3}), NOW)
    assert result.passed
    assert len(calls) == 1
    assert calls[0][0]["E2E_BLIND_SCENE"] == "1A"
    assert calls[0][0]["BLIND_PLAYER_PROFILE"] == "raw"
    assert calls[0][0]["E2E_BLIND_REPLICATES"] == "3"
    assert calls[0][0]["E2E_TURN_TIMEOUT_MS"] == "90000"
    assert calls[0][1] == 7200
    assert not stale.exists()


def test_live_runner_lock_exists_only_during_call_and_is_removed_on_failure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("E2E_API_BASE_URL", "https://staging.example")
    seen: list[bool] = []

    def runner(env, timeout):
        del env, timeout
        seen.append((tmp_path / "factory/state/staged_run.lock").exists())
        write_artifact(tmp_path, clean_report())
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")

    handler = _live_handler(tmp_path, runner, SpendLedger(tmp_path / "ledger.jsonl"))
    assert handler(ticket({"expected_sha": "abc"}), NOW).passed
    assert seen == [True]
    assert not (tmp_path / "factory/state/staged_run.lock").exists()

    def raising_runner(env, timeout):
        del env, timeout
        assert (tmp_path / "factory/state/staged_run.lock").exists()
        raise RuntimeError("runner failed")

    failed = _live_handler(tmp_path, raising_runner, SpendLedger(tmp_path / "ledger-2.jsonl"))(
        ticket({"expected_sha": "abc"}), NOW
    )
    assert not failed.passed
    assert not (tmp_path / "factory/state/staged_run.lock").exists()


def test_fresh_live_staged_lock_blocks_runner(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("E2E_API_BASE_URL", "https://staging.example")
    lock = tmp_path / "factory/state/staged_run.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("other\n", encoding="utf-8")
    os.utime(lock, (NOW.timestamp() - 60, NOW.timestamp() - 60))
    called = False

    def runner(env, timeout):
        nonlocal called
        del env, timeout
        called = True
        return subprocess.CompletedProcess([], 0)

    result = _live_handler(tmp_path, runner, SpendLedger(tmp_path / "ledger.jsonl"))(
        ticket({"expected_sha": "abc"}), NOW
    )
    assert not result.passed and result.output == "staged run already in progress"
    assert called is False


def test_live_missing_fresh_report_and_default_runner_approval(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("E2E_API_BASE_URL", "https://staging.example")
    handler = live_playtest_handler(
        tmp_path,
        runner=lambda _env, _timeout: subprocess.CompletedProcess([], 0),
        fetch_version=lambda _url: {"channel": "staging", "runtime": "scene-v1", "sha": "abc"},
        now_fn=lambda: NOW,
        ledger=SpendLedger(tmp_path / "ledger.jsonl"),
    )
    missing = handler(ticket({"expected_sha": "abc"}), NOW)
    assert not missing.passed and missing.turns is None
    refused = live_playtest_handler(
        tmp_path,
        fetch_version=lambda _url: {"channel": "staging", "runtime": "scene-v1", "sha": "abc"},
        ledger=SpendLedger(tmp_path / "ledger.jsonl"),
    )(ticket({"expected_sha": "abc"}), NOW)
    assert not refused.passed and "billed_run_approved" in refused.output and refused.turns is None


def test_quota_raises_provider_limit_without_station_failure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("E2E_API_BASE_URL", "https://staging.example")

    def runner(_env, _timeout):
        return subprocess.CompletedProcess([], 1, stdout="AI_QUOTA_EXCEEDED", stderr="")

    handler = live_playtest_handler(
        tmp_path,
        runner=runner,
        fetch_version=lambda _url: {"channel": "staging", "runtime": "scene-v1", "sha": "abc"},
        now_fn=lambda: NOW,
        ledger=SpendLedger(tmp_path / "ledger.jsonl"),
    )
    with pytest.raises(LimitSleep) as raised:
        handler(ticket({"expected_sha": "abc"}), NOW)
    assert raised.value.provider == "cloudflare"
    assert raised.value.resume_at == datetime(2026, 1, 2, tzinfo=UTC)


def test_nonzero_live_runner_keeps_exit_code_and_stderr_tail(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("E2E_API_BASE_URL", "https://staging.example")

    def runner(_env, _timeout):
        return subprocess.CompletedProcess([], 7, stdout="stdout detail", stderr="stderr detail")

    result = _live_handler(tmp_path, runner, SpendLedger(tmp_path / "ledger.jsonl"))(
        ticket({"expected_sha": "abc"}), NOW
    )

    assert not result.passed
    assert "exit 7" in result.output
    assert "stderr detail" in result.output


def test_nonzero_live_runner_limits_failure_output_to_last_2000_characters(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("E2E_API_BASE_URL", "https://staging.example")
    output = "a" * 2_000 + "tail"

    def runner(_env, _timeout):
        return subprocess.CompletedProcess([], 1, stdout=output, stderr="")

    result = _live_handler(tmp_path, runner, SpendLedger(tmp_path / "ledger.jsonl"))(
        ticket({"expected_sha": "abc"}), NOW
    )

    assert not result.passed
    tail = result.output.rsplit(": ", 1)[1]
    assert len(tail) == 2_000
    assert tail == output[-2_000:]


def test_nonzero_live_runner_redacts_sensitive_environment_values(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LIVE_PLAYTEST_SECRET", "runner-secret-value")
    monkeypatch.setenv("E2E_API_BASE_URL", "https://staging.example")

    def runner(_env, _timeout):
        return subprocess.CompletedProcess([], 1, stdout="runner-secret-value", stderr="")

    result = _live_handler(tmp_path, runner, SpendLedger(tmp_path / "ledger.jsonl"))(
        ticket({"expected_sha": "abc"}), NOW
    )

    assert not result.passed
    assert "runner-secret-value" not in result.output
    assert "[redacted]" in result.output


def test_nonzero_live_runner_with_empty_output_keeps_old_message(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("E2E_API_BASE_URL", "https://staging.example")

    def runner(_env, _timeout):
        return subprocess.CompletedProcess([], 1, stdout="", stderr="")

    result = _live_handler(tmp_path, runner, SpendLedger(tmp_path / "ledger.jsonl"))(
        ticket({"expected_sha": "abc"}), NOW
    )

    assert not result.passed
    assert result.output == "live playtest runner failed"


def test_cli_exit_codes_and_build_registration(tmp_path: Path, capsys) -> None:
    clean = tmp_path / "clean.json"
    clean.write_text(json.dumps(clean_report()), encoding="utf-8")
    failed = tmp_path / "failed.json"
    failed.write_text(json.dumps(report()), encoding="utf-8")
    assert main(["grade", str(clean)]) == 0
    assert json.loads(capsys.readouterr().out)["packets"] == []
    assert main(["grade", str(failed)]) == 1
    assert json.loads(capsys.readouterr().out)["packets"]
    assert main(["grade", str(tmp_path / "missing.json")]) == 2
    assert Station.LIVE_PLAYTEST in build_handlers(ROOT)


def test_packets_treat_a_committed_matched_candidate_as_delivered() -> None:
    value = {
        "replicates": [
            {
                "replicate": 1,
                "scene": "1A",
                "turns": [
                    {
                        "turn": 3,
                        "raw_input": "Examine the manuscript pages.",
                        "text": "Pages.",
                        "matched_candidate": "k_sl_1a_g_r1",
                        "outcome": "committed",
                    },
                    {"turn": 4, "raw_input": "Examine the red markings.", "text": "Marks.", "outcome": "committed"},
                ],
                "stuck_turns": [4],
            }
        ]
    }
    packet = report_to_packets(value)[0]
    assert packet["delivered_before"] == ["k_sl_1a_g_r1"]
    assert packet["delivered_before_turns"] == {"k_sl_1a_g_r1": 3}
