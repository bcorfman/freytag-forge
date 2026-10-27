from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/ringer/transcript_1a/live_baseline.py"
CHECKER = ROOT / "scripts/ringer/transcript_1a/check_live_baseline.py"
PYTHON = ROOT / ".venv/bin/python"


def test_dry_run_and_checker(tmp_path: Path) -> None:
    out = tmp_path / "dry"
    subprocess.run(
        [str(PYTHON), str(SCRIPT), "--dry-run", "--replicates", "1", "--turns", "2", "--out", str(out)], check=True
    )
    subprocess.run([str(PYTHON), str(CHECKER), str(out), "1", "--mode", "dry", "--turns", "2"], check=True)


@pytest.mark.parametrize(
    ("route", "expected_inputs"),
    (
        (
            "reported",
            ("go in the house", "feel in the gap", "look at the fabric"),
        ),
        (
            "corrected",
            ("go in the house", "pull out the drawer", "feel in the gap"),
        ),
        (
            "witnessed",
            ("go in the house", "examine the carved initials", "wait"),
        ),
    ),
)
def test_routes_dry_run_and_checker(tmp_path: Path, route: str, expected_inputs: tuple[str, ...]) -> None:
    out = tmp_path / route
    subprocess.run(
        [
            str(PYTHON),
            str(SCRIPT),
            "--dry-run",
            "--route",
            route,
            "--replicates",
            "1",
            "--turns",
            "3",
            "--out",
            str(out),
        ],
        check=True,
    )
    summary = json.loads((out / "summary.json").read_text())
    assert summary["route"] == route
    assert summary["inputs"] == list(expected_inputs)
    rows = json.loads((out / "rows.json").read_text())
    assert rows[0]["route"] == route
    assert all(turn["route"] == route for turn in rows[0]["turns"])
    subprocess.run([str(PYTHON), str(CHECKER), str(out), "1", "--mode", "dry", "--turns", "3"], check=True)


def test_default_route_keeps_reported_inputs(tmp_path: Path) -> None:
    out = tmp_path / "default"
    subprocess.run([str(PYTHON), str(SCRIPT), "--dry-run", "--replicates", "1", "--out", str(out)], check=True)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["route"] == "reported"
    assert summary["inputs"] == [
        "go in the house",
        "feel in the gap",
        "look at the fabric",
        "pull out the drawer",
        "feel under the drawer",
        "go out to the truck",
        "get in",
        "look around",
    ]


def test_shadow_flag_off_preserves_unshadowed_schema(tmp_path: Path) -> None:
    out = tmp_path / "off"
    subprocess.run(
        [str(PYTHON), str(SCRIPT), "--dry-run", "--route", "reported", "--replicates", "1", "--out", str(out)],
        check=True,
    )
    rows = json.loads((out / "rows.json").read_text())
    summary = json.loads((out / "summary.json").read_text())
    shadow_keys = ("observation_shadow", "observation_relations", "observation_request")
    assert all(key not in turn for turn in rows[0]["turns"] for key in shadow_keys)
    assert "shadow" not in summary


def test_shadow_observe_records_schema_for_all_turns(tmp_path: Path) -> None:
    out = tmp_path / "observe"
    subprocess.run(
        [
            str(PYTHON),
            str(SCRIPT),
            "--shadow",
            "--dry-run",
            "--route",
            "observe",
            "--replicates",
            "1",
            "--out",
            str(out),
        ],
        check=True,
    )
    rows = json.loads((out / "rows.json").read_text())
    summary = json.loads((out / "summary.json").read_text())
    shadow_keys = ("observation_shadow", "observation_relations", "observation_request")
    assert len(rows[0]["turns"]) == 13
    assert all(key in turn for turn in rows[0]["turns"] for key in shadow_keys)
    assert summary["shadow"] is True
    assert summary["turns_recorded"] == 13
    assert summary["observation_turns"] == sum(turn["observation_relations"] is not None for turn in rows[0]["turns"])
    assert summary["shadow_verifier_requests"] == sum(
        len(turn["observation_shadow"]["requests"])
        for turn in rows[0]["turns"]
        if turn["observation_shadow"] is not None
    )


def test_shadow_clears_stale_observation_on_engine_moves(tmp_path: Path) -> None:
    out = tmp_path / "observe-engine-moves"
    subprocess.run(
        [
            str(PYTHON),
            str(SCRIPT),
            "--shadow",
            "--dry-run",
            "--route",
            "observe",
            "--replicates",
            "1",
            "--out",
            str(out),
        ],
        check=True,
    )
    rows = json.loads((out / "rows.json").read_text())
    turns = rows[0]["turns"]
    for command in ("go outside", "go inside"):
        row = next(turn for turn in turns if turn["input"] == command)
        assert row["narrator_called"] is False
        assert row["observation_shadow"] is None
        assert row["observation_request"] is None
    narrator_rows_with_request = [
        turn for turn in turns if turn["narrator_called"] and turn["observation_request"] is not None
    ]
    assert all(turn["observation_shadow"] is not None for turn in narrator_rows_with_request)


def test_shadow_observation_identity_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    module_spec = importlib.util.spec_from_file_location("live_baseline", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_observation_request", lambda _capture, _state: {"kind": "look"})

    previous_after = {"observation_shadow": {"requests": 7}}
    previous_request = object()
    same_capture = SimpleNamespace(
        last_after=previous_after,
        provider=SimpleNamespace(observation_request=previous_request),
    )
    assert module._shadow_observation_values(same_capture, object(), previous_after, previous_request) == (
        None,
        None,
    )

    new_after = {"observation_shadow": {"requests": 3}}
    new_request = object()
    new_capture = SimpleNamespace(
        last_after=new_after,
        provider=SimpleNamespace(observation_request=new_request),
    )
    assert module._shadow_observation_values(new_capture, object(), previous_after, previous_request) == (
        {"requests": 3},
        {"kind": "look"},
    )


def test_observe_route_has_exact_inputs() -> None:
    module_spec = importlib.util.spec_from_file_location("live_baseline", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    assert module.ROUTES["observe"] == (
        "inspect the drawer",
        "pull out the drawer",
        "feel under the drawer",
        "feel under the drawer",
        "go outside",
        "inspect the truck",
        "enter the truck",
        "inspect the passenger seat",
        "examine my laptop",
        "get out of the truck",
        "examine the truck",
        "go inside",
        "inspect the drawer",
    )


def test_observe_look_inside_under_route_has_exact_inputs() -> None:
    module_spec = importlib.util.spec_from_file_location("live_baseline", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    assert module.ROUTES["observe_look_inside_under"] == (
        "inspect the drawer",
        "examine the drawer",
        "search the drawer",
        "check the drawer",
        "look inside the drawer",
        "look under the drawer",
    )


def test_new_turn_fields_have_defaults_when_capture_record_is_absent() -> None:
    module_spec = importlib.util.spec_from_file_location("live_baseline", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    capture = SimpleNamespace(last_before=None, provider=SimpleNamespace(observation_request=None))
    assert module._turn_telemetry(capture, SimpleNamespace()) == {
        "engine_opened": False,
        "focus_open_state_after": None,
        "focus_open_state_committed": None,
        "handoff_id": None,
        "delivered_text": None,
    }


def test_new_turn_fields_are_written_on_stubbed_turn(tmp_path: Path) -> None:
    out = tmp_path / "telemetry"
    subprocess.run(
        [
            str(PYTHON),
            str(SCRIPT),
            "--dry-run",
            "--route",
            "observe_look_inside_under",
            "--replicates",
            "1",
            "--turns",
            "1",
            "--out",
            str(out),
        ],
        check=True,
    )
    rows = json.loads((out / "rows.json").read_text())
    turn = rows[0]["turns"][0]
    assert turn["engine_opened"] is False
    assert turn["focus_open_state_after"] is None
    assert turn["focus_open_state_committed"] is None
    assert turn["handoff_id"] == "k_sl_1a_f_r2"
    assert turn["delivered_text"] == (
        "The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers."
    )


def test_shadow_restores_relations_wrapper_when_run_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module_spec = importlib.util.spec_from_file_location("live_baseline", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    import storygame.runtime.capture as capture_module

    original = capture_module.relations_from_context

    def fail(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("forced test failure")

    monkeypatch.setattr(module, "_replicate", fail)
    with pytest.raises(RuntimeError) as exc_info:
        module.main(
            [
                "--shadow",
                "--dry-run",
                "--replicates",
                "1",
                "--turns",
                "0",
                "--out",
                str(tmp_path / "raises"),
            ]
        )
    assert str(exc_info.value) == "forced test failure"
    assert capture_module.relations_from_context is original


def test_shadow_preserves_corrected_narration_rows(tmp_path: Path) -> None:
    plain_out = tmp_path / "plain"
    shadow_out = tmp_path / "shadow"
    common = [str(PYTHON), str(SCRIPT), "--dry-run", "--route", "corrected", "--replicates", "1"]
    subprocess.run([*common, "--out", str(plain_out)], check=True)
    subprocess.run([*common, "--shadow", "--out", str(shadow_out)], check=True)
    plain_rows = json.loads((plain_out / "rows.json").read_text())
    shadow_rows = json.loads((shadow_out / "rows.json").read_text())
    assert [turn["narration"] for turn in plain_rows[0]["turns"]] == [
        turn["narration"] for turn in shadow_rows[0]["turns"]
    ]


def test_movement_route_records_places_and_narrator_calls(tmp_path: Path) -> None:
    out = tmp_path / "movement"
    subprocess.run(
        [str(PYTHON), str(SCRIPT), "--dry-run", "--route", "movement", "--replicates", "1", "--out", str(out)],
        check=True,
    )
    summary = json.loads((out / "summary.json").read_text())
    assert summary["route"] == "movement"
    assert summary["inputs"] == [
        "look around",
        "go outside",
        "look around",
        "go out to the truck",
        "look around",
        "get out of the truck",
        "look around",
        "go inside",
        "look around",
        "go out to the truck",
        "go inside",
        "look around",
    ]
    rows = json.loads((out / "rows.json").read_text())
    turns = rows[0]["turns"]
    assert turns[0]["input"] == "look around"
    assert turns[0]["narrator_called"] is True
    outside = next(turn for turn in turns if turn["input"] == "go outside")
    assert outside["narrator_called"] is False
    assert outside["places_after"]["kristin"] == "outside_house"
    subprocess.run([str(PYTHON), str(CHECKER), str(out), "1", "--mode", "dry"], check=True)


def test_call_cap_keeps_partial_rows(tmp_path: Path) -> None:
    out = tmp_path / "cap"
    subprocess.run(
        [str(PYTHON), str(SCRIPT), "--dry-run", "--replicates", "1", "--out", str(out), "--max-calls", "1"], check=True
    )
    summary = json.loads((out / "summary.json").read_text())
    assert summary["stopped_reason"] == "MAX_CALLS_EXCEEDED"
    rows = json.loads((out / "rows.json").read_text())
    assert rows and rows[0]["turns"]


def test_live_quota_http_error_is_inspected_and_readable(monkeypatch: object) -> None:
    module_spec = importlib.util.spec_from_file_location("live_baseline", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    body = b'{"error":"quota"}'

    def fail(*_args: object, **_kwargs: object) -> None:
        raise urllib.error.HTTPError(
            "https://worker.example/turn",
            429,
            "Too Many Requests",
            {"X-Narration-Error-Code": "AI_QUOTA_EXCEEDED"},
            io.BytesIO(body),
        )

    monkeypatch.setattr(urllib.request, "urlopen", fail)
    counter = module.CallCounter(1, False)
    try:
        counter.live_urlopen(object())
    except urllib.error.HTTPError as error:
        assert error.read() == body
    else:
        raise AssertionError("expected HTTPError")
    assert counter.stop_reason == "AI_QUOTA_EXCEEDED"


def test_live_requires_confirmation_without_urlopen(monkeypatch: object, tmp_path: Path) -> None:
    module_spec = importlib.util.spec_from_file_location("live_baseline", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    called = False

    def fail(*_args: object, **_kwargs: object) -> None:
        nonlocal called
        called = True
        raise AssertionError("urlopen called")

    monkeypatch.setattr("urllib.request.urlopen", fail)
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    assert module.main(["--out", str(tmp_path / "live")]) != 0
    assert not called
