from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bench.core import load_variation, package_and_state
from scripts.ringer.stage7 import three_c_recall_replay as replay
from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.facts import Fact

ROOT = Path(__file__).resolve().parents[1]
VARIATION = ROOT / "bench/variations/stage7-3c-recall-live.json"
PACKAGE = ROOT / "data/stories/continuity-initiative"


def _hashes(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()
    }


def test_variation_replaces_c1_once_and_loads_with_real_loader() -> None:
    source = (PACKAGE / "knowledge.yaml").read_text(encoding="utf-8")
    assert source.count(replay.OLD_C1) == 1
    variation = load_variation(VARIATION)
    package, _ = package_and_state(variation, "3C")
    assert package.knowledge_indexes.by_id["k_sl_3c_c_r1"].statement == replay.NEW_C1


def test_variation_changes_only_knowledge_file() -> None:
    variation = load_variation(VARIATION)
    materialized = Path(variation["_package_path"])
    shipped = _hashes(PACKAGE)
    loaded = _hashes(materialized)
    assert {key: value for key, value in loaded.items() if key != "knowledge.yaml"} == {
        key: value for key, value in shipped.items() if key != "knowledge.yaml"
    }


def test_frozen_arms_have_three_c1_replacements_and_preserve_other_text() -> None:
    pump, recall, count = replay.build_requests()
    assert pump == replay.recorded_request()
    assert count == 3
    assert pump["system"] == recall["system"]
    assert pump["user"].split("\nTHINGS:", 1)[0].count(replay.OLD_C1) == 1
    constraints = pump["user"].split("\nCONSTRAINTS:\n", 1)[1].split("\nPLAYER:\n", 1)[0]
    assert constraints.count(replay.OLD_C1) == 2
    assert recall["user"].count(replay.NEW_C1) == 3
    assert replay.OLD_C1_TRACE not in recall["user"]
    for marker in (replay.C2_TEXT, replay.BR1_DELIVERY_TEXT, replay.PUMP_NEED_TEXT):
        assert pump["user"].count(marker) == recall["user"].count(marker)
    assert replay.OLD_C1 not in json.dumps(recall)


def test_dry_diff_changes_only_c1_lines(tmp_path: Path) -> None:
    pump, recall, _ = replay.build_requests()
    replay._write_dry(tmp_path, pump, recall, 3)
    diff = (tmp_path / "request.diff").read_text(encoding="utf-8")
    changed = [line for line in diff.splitlines() if line[:1] in {"+", "-"} and not line.startswith(("+++", "---"))]
    assert changed
    assert all(replay.OLD_C1 in line or replay.NEW_C1 in line for line in changed)


def test_c1_only_does_not_make_surface_fact_true_and_c_orders_unlock_d() -> None:
    from tests.test_3c_cue_chain import _finish_a_and_b, _reveal

    engine = _finish_a_and_b()
    _reveal(engine, "k_sl_3c_c_r1", "Restore the drainage pumps.")
    assert Fact(predicate="captives_reaching_surface", subject="story", value="true") not in engine.state.facts.asserted
    for first, second in (("k_sl_3c_c_r1", "k_sl_3c_c_r2"), ("k_sl_3c_c_r2", "k_sl_3c_c_r1")):
        engine = _finish_a_and_b()
        for knowledge_id, command in (
            (first, "Restore the drainage pumps." if first.endswith("r1") else "Open the surface gates."),
            (second, "Restore the drainage pumps." if second.endswith("r1") else "Open the surface gates."),
        ):
            _reveal(engine, knowledge_id, command)
        projection = engine.projector.project(engine.state, "player", "Check reports from other detention sites.")
        assert (
            uniquely_matched_authored_handoff("Check reports from other detention sites.", projection.reveal_universe)
            is not None
        )


def test_dry_run_never_calls_network_and_cap_is_honored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(replay, "urlopen", lambda *_args, **_kwargs: pytest.fail("network called"))
    out = tmp_path / "dry"
    monkeypatch.setattr(
        "sys.argv", ["three_c_recall_replay.py", "--n", "12", "--out", str(out), "--dry-run", "--max-requests", "1"]
    )
    replay.main()
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["network_calls"] == 0
    assert summary["replacement_occurrences"] == 3


def test_live_loop_stub_honors_cap_including_recovery(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[dict[str, str]] = []

    def fake_send(payload: dict[str, str], _url: str, _token: str) -> tuple[int, str]:
        calls.append(payload)
        return 200, "not json" if len(calls) == 1 else '{"segments":[{"text":"ok"}]}'

    monkeypatch.setattr(replay, "_send", fake_send)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://offline.invalid")
    pump, recall, _ = replay.build_requests()
    args = type("Args", (), {"n": 12, "max_requests": 3})()
    replay.replay(args, pump, recall, tmp_path)
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["requests"] == 3
    assert len(calls) == 3
    assert summary["stop"] == "request cap reached"
    assert (tmp_path / "failure.txt").read_text(encoding="utf-8") == "request cap reached\n"


def test_live_cli_requires_confirm_without_network_or_writes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(replay, "urlopen", lambda *_args, **_kwargs: pytest.fail("network called"))
    out = tmp_path / "refused"
    monkeypatch.setattr("sys.argv", ["three_c_recall_replay.py", "--n", "1", "--out", str(out)])
    with pytest.raises(SystemExit) as raised:
        replay.main()
    assert raised.value.code != 0
    assert not out.exists()


def test_replay_checker_accepts_dry_and_rejects_bad_artifacts(tmp_path: Path) -> None:
    from scripts.ringer.stage7 import check_three_c_recall_replay as checker

    dry = tmp_path / "dry"
    dry.mkdir()
    replay._write_dry(dry, *replay.build_requests()[:2], 3)
    assert checker.check(dry, 1, "dry") == []

    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    rows = [
        {"arm": arm, "index": index, "request_count": 1, "raw_reply_text": "{}"}
        for index in range(2)
        for arm in ("pump", "recall")
    ]
    (artifacts / "rows.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    (artifacts / "summary.json").write_text(
        json.dumps({"requests": 4, "max_requests": 4, "semantic_judge_calls": 0, "player_model_calls": 0})
    )
    assert checker.check(artifacts, 2, "artifacts") == []

    (artifacts / "summary.json").write_text(
        json.dumps({"requests": 3, "max_requests": 4, "semantic_judge_calls": 0, "player_model_calls": 0})
    )
    assert any("does not equal" in error for error in checker.check(artifacts, 2, "artifacts"))
    rows[1]["arm"] = "pump"
    (artifacts / "rows.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    assert any("alternating" in error for error in checker.check(artifacts, 2, "artifacts"))


def test_broadcast_variation_replaces_a_r1_only_and_preserves_b_r1_delivery() -> None:
    broadcast_variation = ROOT / "bench/variations/stage7-3c-broadcast-live.json"
    source = (PACKAGE / "knowledge.yaml").read_text(encoding="utf-8")
    assert source.count(replay.BROADCAST_OLD_LITERAL) == 1
    variation = load_variation(broadcast_variation)
    package, _ = package_and_state(variation, "3C")
    assert package.knowledge_indexes.by_id["k_sl_3c_a_r1"].statement == replay.BROADCAST_NEW_LITERAL
    assert {
        key: value
        for key, value in _hashes(Path(variation["_package_path"]).resolve()).items()
        if key != "knowledge.yaml"
    } == {key: value for key, value in _hashes(PACKAGE).items() if key != "knowledge.yaml"}


def test_broadcast_arms_isolate_three_replacements_and_b_r1_delivery() -> None:
    pump, broadcast, count = replay.build_requests("broadcast")
    assert count == 3
    assert pump == replay.recorded_request()
    assert pump["user"].count(replay.BROADCAST_OLD_LITERAL) == 3
    assert broadcast["user"].count(replay.BROADCAST_OLD_LITERAL) == 0
    assert broadcast["user"].count(replay.BROADCAST_NEW_LITERAL) == 3
    assert "Michelle broadcasts captives" not in broadcast["user"]
    delivery = "Michelle sends its prisoner locations to independent networks"
    assert pump["user"].count(delivery) == broadcast["user"].count(delivery)


def test_broadcast_cli_guard_and_request_cap_with_stubbed_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(replay, "urlopen", lambda *_args, **_kwargs: pytest.fail("network called"))
    refused = tmp_path / "refused"
    monkeypatch.setattr(
        "sys.argv", ["three_c_recall_replay.py", "--experiment", "broadcast", "--n", "1", "--out", str(refused)]
    )
    with pytest.raises(SystemExit):
        replay.main()
    assert not refused.exists()

    calls: list[dict[str, str]] = []

    def fake_send(payload: dict[str, str], _url: str, _token: str) -> tuple[int, str]:
        calls.append(payload)
        return 200, '{"segments":[{"text":"ok"}]}'

    monkeypatch.setattr(replay, "_send", fake_send)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://offline.invalid")
    pump, broadcast, _ = replay.build_requests("broadcast")
    args = type("Args", (), {"n": 12, "max_requests": 3})()
    out = tmp_path / "capped"
    out.mkdir()
    replay.replay(args, pump, broadcast, out, "broadcast")
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["requests"] == 3
    assert [row["arm"] for row in (json.loads(line) for line in (out / "rows.jsonl").read_text().splitlines())] == [
        "pump",
        "broadcast",
        "pump",
    ]


def test_broadcast_checker_accepts_good_artifacts_and_rejects_wrong_order(tmp_path: Path) -> None:
    from scripts.ringer.stage7 import check_three_c_recall_replay as checker

    rows = [
        {"arm": arm, "index": index, "request_count": 1, "raw_reply_text": "{}"}
        for index in range(2)
        for arm in ("pump", "broadcast")
    ]
    (tmp_path / "rows.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    (tmp_path / "summary.json").write_text(
        json.dumps({"requests": 4, "max_requests": 48, "semantic_judge_calls": 0, "player_model_calls": 0})
    )
    assert checker.check(tmp_path, 2, "artifacts", "broadcast") == []
    rows[1]["arm"] = "pump"
    (tmp_path / "rows.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    assert any("alternating" in error for error in checker.check(tmp_path, 2, "artifacts", "broadcast"))
