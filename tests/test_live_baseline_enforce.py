from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture
from storygame.runtime.observation import ObservationContext, ObservationRequest
from storygame.runtime.observation_verifier import Relation

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ringer/transcript_1a/live_baseline.py"


def _module():
    module_spec = importlib.util.spec_from_file_location("live_baseline_enforce", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


def _run(module, tmp_path: Path, *flags: str, turns: int = 13) -> tuple[dict, list[dict]]:
    out = tmp_path / "run"
    arguments = [
        "--dry-run",
        "--route",
        "observe",
        "--replicates",
        "1",
        "--turns",
        str(turns),
        *flags,
        "--out",
        str(out),
    ]
    assert module.main(arguments) == 0
    return json.loads((out / "summary.json").read_text()), json.loads((out / "rows.json").read_text())


def test_enforce_and_shadow_are_mutually_exclusive(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    module = _module()

    with pytest.raises(SystemExit) as raised:
        module.main(["--dry-run", "--shadow", "--enforce", "--out", str(tmp_path / "invalid")])

    assert raised.value.code == 2
    assert "not allowed with argument" in capsys.readouterr().err


def test_enforce_records_observation_data_counts_and_summary(tmp_path: Path) -> None:
    module = _module()
    summary, rows = _run(module, tmp_path, "--enforce")
    turns = rows[0]["turns"]

    assert summary["enforce"] is True
    assert all("observation_enforce" in turn for turn in turns)
    assert all("narration_attempts" in turn for turn in turns)
    assert all("verifier_requests" in turn for turn in turns)
    assert all(
        value is None or set(value) <= {"observation_preview", "observation_diverged"}
        for value in (turn["observation_enforce"] for turn in turns)
    )


def test_enforce_clears_observation_for_engine_authored_moves(tmp_path: Path) -> None:
    module = _module()
    _summary, rows = _run(module, tmp_path, "--enforce")

    turns = rows[0]["turns"]
    for command in ("go outside", "go inside"):
        row = next(turn for turn in turns if turn["input"] == command)
        assert row["narrator_called"] is False
        assert row["observation_enforce"] is None


def test_enforce_records_each_verifier_attempt_and_turn_elapsed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _module()
    original = module.CallCounter.dry_urlopen
    verifier_calls = 0

    def fake_worker(self, request, timeout=None, **kwargs):
        nonlocal verifier_calls
        if str(getattr(request, "full_url", "")).endswith("/jev"):
            payload = json.loads(request.data)
            questions = payload["input"]["questions"]
            if any(key.startswith("relation_") for key in questions):
                score = 0.0 if verifier_calls == 0 else 0.9
                verifier_calls += 1
                return module._Response(
                    {"answers": {key: {"noul": score} for key in questions}},
                    self,
                )
        return original(self, request, timeout=timeout, **kwargs)

    monkeypatch.setattr(module.CallCounter, "dry_urlopen", fake_worker)

    original_before_turn = WorldCapture.before_turn

    def force_observation(self, command):
        result = original_before_turn(self, command)
        self.provider.observation_request = ObservationRequest(command, "look", "michelle_drawer")
        return result

    monkeypatch.setattr(WorldCapture, "before_turn", force_observation)
    monkeypatch.setattr(
        WorldCapture,
        "_observation_context_for_verification",
        lambda _self, entered_scene: ObservationContext(
            observer="observer",
            action="look",
            completed_actions=(),
            visible_things=(),
            contingent_things=(),
            required=("drawer",),
            omitted_optional=(),
            scope_complete=True,
        ),
    )
    monkeypatch.setattr(
        "storygame.runtime.capture.relations_from_context",
        lambda _context: (Relation(thing="drawer", place="kitchen"),),
    )
    summary, rows = _run(module, tmp_path, "--enforce", turns=1)

    attempts = rows[0]["turns"][0]["enforce_attempts"]
    assert len(attempts) == 2
    assert attempts[0]["accepted"] is False
    assert attempts[1]["accepted"] is True
    assert all(
        set(attempt)
        == {
            "narration",
            "relations",
            "outcome",
            "accepted",
            "verdicts",
            "requests",
            "failure",
            "elapsed_s",
        }
        for attempt in attempts
    )
    assert all(
        set(relation) == {"thing", "place", "holder"} for attempt in attempts for relation in attempt["relations"]
    )
    assert all(
        set(verdict) == {"thing", "place", "holder", "verdict", "score"}
        for attempt in attempts
        for verdict in attempt["verdicts"]
    )
    json.dumps(rows)
    assert isinstance(rows[0]["turns"][0]["turn_elapsed_s"], float)
    assert summary["enforce"] is True


def test_enforce_records_empty_attempts_for_a_turn_without_relations(tmp_path: Path) -> None:
    module = _module()
    _summary, rows = _run(module, tmp_path, "--enforce", turns=5)

    move = next(turn for turn in rows[0]["turns"] if turn["input"] == "go outside")
    assert move["enforce_attempts"] == []


def test_enforce_off_preserves_rows_and_sets_false_summary(tmp_path: Path) -> None:
    module = _module()
    first_summary, first_rows = _run(module, tmp_path / "first")
    second_summary, second_rows = _run(module, tmp_path / "second")

    assert first_rows == second_rows
    assert first_summary == second_summary
    assert first_summary["enforce"] is False
    assert all("observation_enforce" not in turn for turn in first_rows[0]["turns"])
    assert all("enforce_attempts" not in turn for turn in first_rows[0]["turns"])
    assert all("turn_elapsed_s" not in turn for turn in first_rows[0]["turns"])


def test_observe_under_first_route_and_enforcement_request_recording(tmp_path: Path) -> None:
    module = _module()

    assert module.ROUTES["observe_under_first"] == (
        "feel under the drawer",
        "feel under the drawer",
        "inspect the drawer",
        "pull out the drawer",
    )

    enforced_out = tmp_path / "enforced"
    assert (
        module.main(
            [
                "--dry-run",
                "--route",
                "observe_under_first",
                "--replicates",
                "1",
                "--enforce",
                "--out",
                str(enforced_out),
            ]
        )
        == 0
    )
    enforced_rows = json.loads((enforced_out / "rows.json").read_text())
    assert all("observation_request" in turn for turn in enforced_rows[0]["turns"])
    assert all(
        turn["observation_request"] is None or isinstance(turn["observation_request"], dict)
        for turn in enforced_rows[0]["turns"]
    )

    off_out = tmp_path / "off"
    assert (
        module.main(
            [
                "--dry-run",
                "--route",
                "observe_under_first",
                "--replicates",
                "1",
                "--out",
                str(off_out),
            ]
        )
        == 0
    )
    off_rows = json.loads((off_out / "rows.json").read_text())
    assert all("observation_request" not in turn for turn in off_rows[0]["turns"])


def test_enforce_observation_request_is_none_for_engine_authored_move(tmp_path: Path) -> None:
    module = _module()
    _summary, rows = _run(module, tmp_path, "--enforce")

    move = next(turn for turn in rows[0]["turns"] if turn["input"] == "go outside")
    assert move["narrator_called"] is False
    assert move["observation_request"] is None
