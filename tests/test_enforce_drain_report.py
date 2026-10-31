from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ringer/environment_narration/enforce_drain_report.py"


def _module():
    module_spec = importlib.util.spec_from_file_location("enforce_drain_report", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


def _turn(*, committed=True, first=True, scene_state=False, tag=None, really_deficient=True):
    attempts = []
    if not first:
        attempts.append(
            {
                "accepted": False,
                "narration": "The drain is nowhere to be found.",
                "scene_state": scene_state,
                "verdicts": [],
            }
        )
    if committed:
        attempts.append(
            {
                "accepted": True,
                "narration": "The drain remains closed beneath the path.",
                "scene_state": scene_state,
                "verdicts": [{"score": 0.9}],
            }
        )
    return {
        "input": "inspect the storm drain",
        "narration": "The drain remains closed beneath the path." if committed else None,
        "error": None if committed else "ProposalValidationError: rejected",
        "places_before": {"storm_drain": "park_path"},
        "places_after": {"storm_drain": "park_path"},
        "enforce_attempts": attempts,
        "narration_attempts": len(attempts),
        "verifier_requests": len(attempts),
        "call_timings": [{"kind": "jev", "elapsed_s": 0.2, "keys": ["relation_0"]}],
    }


def _rows(count=20, *, on=False):
    return [
        {
            "route": "observe_storm_drain_1b",
            "turns": [_turn(first=index != 0, scene_state=on)],
        }
        for index in range(count)
    ]


def _prepare(module, tmp_path: Path, *, count=20):
    tmp_path.mkdir(parents=True, exist_ok=True)
    off = tmp_path / "off.json"
    on = tmp_path / "on.json"
    off.write_text(json.dumps(_rows(count=count)), encoding="utf-8")
    on.write_text(json.dumps(_rows(count=count, on=True)), encoding="utf-8")
    out = tmp_path / "sheets"
    assert module.main(["--sheets", "--rows-off", str(off), "--rows-on", str(on), "--out", str(out)]) == 0
    labels = out / "labels_template.json"
    return off, on, out, labels


def _write_labels(path: Path, *, mutate=None):
    labels = json.loads(path.read_text())
    for entry in labels.values():
        if isinstance(entry.get("committed"), dict):
            for tag in entry["committed"]:
                if entry["committed"][tag] is None:
                    entry["committed"][tag] = False
        for rejected in entry.get("rejected_attempts", ()):
            if rejected["really_deficient"] is None:
                rejected["really_deficient"] = True
    if mutate is not None:
        mutate(labels)
    target = path.parent / "labels.json"
    target.write_text(json.dumps(labels), encoding="utf-8")
    return target


def _report(module, tmp_path, off, on, labels, capsys):
    output = tmp_path / "report.txt"
    code = module.main(
        [
            "--report",
            "--rows-off",
            str(off),
            "--rows-on",
            str(on),
            "--labels",
            str(labels),
            "--out",
            str(output),
        ]
    )
    text = output.read_text() if output.exists() else ""
    return code, text


def test_sheets_are_blind_and_deterministic(tmp_path: Path) -> None:
    module = _module()
    _off, _on, first, labels = _prepare(module, tmp_path / "first")
    _off, _on, second, _labels = _prepare(module, tmp_path / "second")

    first_sheet = (first / "blind_sheet.md").read_text()
    second_sheet = (second / "blind_sheet.md").read_text()
    assert first_sheet == second_sheet
    assert "OFF" not in first_sheet
    assert "ON" not in first_sheet
    assert json.loads((first / "blind_key.json").read_text())
    assert "opens_drain" in labels.read_text()
    assert "moves_drain" in labels.read_text()
    assert "gives_contents" in labels.read_text()
    assert "really_deficient" in labels.read_text()


def test_report_passes_all_gates_and_prints_both_arms(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    module = _module()
    off, on, out, template = _prepare(module, tmp_path)
    labels = _write_labels(template)

    code, report = _report(module, tmp_path, off, on, labels, capsys)

    assert code == 0
    for gate in ("D1", "D2", "D3", "D4", "D5", "D6"):
        assert f"{gate}: ON PASS" in report
        assert "OFF" in report
    assert "labels sha256:" in report
    assert "call timing (OFF)" in report
    assert "call timing (ON)" in report
    assert out.joinpath("blind_key.json").is_file()


def test_report_separates_logical_attempts_from_http_prompts(tmp_path: Path, capsys) -> None:
    module = _module()
    off, on, _out, template = _prepare(module, tmp_path)
    rows = json.loads(on.read_text())
    for entry in rows:
        entry["turns"][0]["narration_attempts"] = 1
        entry["turns"][0]["narration_http_prompts"] = 4
    on.write_text(json.dumps(rows), encoding="utf-8")
    labels = _write_labels(template)

    code, report = _report(module, tmp_path, off, on, labels, capsys)

    assert code == 0
    assert "D5: ON PASS" in report
    assert "logical narration attempts ON: mean=1.000 range=1–1" in report
    assert "narration_http_prompts ON: mean=4.000 range=4–4" in report
    assert "attempts per turn" not in report


def test_logical_attempts_fall_back_to_enforce_attempt_entries(tmp_path: Path, capsys) -> None:
    module = _module()
    off, on, _out, template = _prepare(module, tmp_path)
    rows = json.loads(on.read_text())
    for entry in rows:
        del entry["turns"][0]["narration_attempts"]
    on.write_text(json.dumps(rows), encoding="utf-8")
    labels = _write_labels(template)

    code, report = _report(module, tmp_path, off, on, labels, capsys)

    assert code == 0
    assert "logical narration attempts ON: mean=1.050 range=1–2" in report


def test_none_logical_attempts_are_insufficient_evidence(tmp_path: Path, capsys) -> None:
    module = _module()
    off, on, _out, template = _prepare(module, tmp_path)
    rows = json.loads(on.read_text())
    for entry in rows:
        entry["turns"][0]["narration_attempts"] = None
    on.write_text(json.dumps(rows), encoding="utf-8")
    labels = _write_labels(template)

    code, report = _report(module, tmp_path, off, on, labels, capsys)

    assert code == 1
    assert "D5: ON insufficient evidence" in report


@pytest.mark.parametrize(
    ("gate", "mutate"),
    [
        (
            "D1",
            lambda rows, labels: [rows[index].__setitem__("turns", [_turn(committed=False)]) for index in (0, 1, 2)],
        ),
        ("D2", lambda rows, labels: [rows[index].__setitem__("turns", [_turn(first=False)]) for index in range(5)]),
        (
            "D3",
            lambda rows, labels: labels.__setitem__(
                next(iter(labels)),
                {
                    **labels[next(iter(labels))],
                    "committed": {"opens_drain": True, "moves_drain": False, "gives_contents": False},
                    "rejected_attempts": [],
                },
            ),
        ),
        ("D4", lambda rows, labels: rows[0]["turns"][0]["enforce_attempts"][0].__setitem__("scene_state", False)),
        ("D5", lambda rows, labels: rows[0]["turns"][0].__setitem__("narration_attempts", 3)),
        (
            "D6",
            lambda rows, labels: (
                [rows[index].__setitem__("turns", [_turn(first=False)]) for index in (0, 1)],
                [
                    attempt.__setitem__("really_deficient", False)
                    for entry in labels.values()
                    for attempt in entry.get("rejected_attempts", [])
                ],
            ),
        ),
    ],
)
def test_each_gate_can_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str], gate, mutate) -> None:
    module = _module()
    off, on, out, template = _prepare(module, tmp_path)
    rows = json.loads(on.read_text())
    labels = json.loads(template.read_text())
    mutate(rows, labels)
    on.write_text(json.dumps(rows), encoding="utf-8")
    template.write_text(json.dumps(labels), encoding="utf-8")
    if gate in ("D2", "D6"):
        regenerated = tmp_path / "regenerated"
        assert module.main(["--sheets", "--rows-off", str(off), "--rows-on", str(on), "--out", str(regenerated)]) == 0
        template = regenerated / "labels_template.json"
    if gate == "D3":
        key = json.loads((out / "blind_key.json").read_text())
        on_id = next(opaque_id for opaque_id, value in key.items() if value["arm"] == "on")
        labels[on_id]["committed"] = {"opens_drain": True, "moves_drain": False, "gives_contents": False}
        template.write_text(json.dumps(labels), encoding="utf-8")
    if gate == "D6":
        labels = json.loads(template.read_text())
        for entry in labels.values():
            for attempt in entry.get("rejected_attempts", ()):
                attempt["really_deficient"] = False
        template.write_text(json.dumps(labels), encoding="utf-8")
    labels_path = _write_labels(template)

    code, report = _report(module, tmp_path, off, on, labels_path, capsys)

    assert code == 1
    assert f"{gate}: ON FAIL" in report


def test_missing_labels_refuse_and_smoke_is_not_applicable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    module = _module()
    off, on, _out, template = _prepare(module, tmp_path / "smoke", count=3)
    labels = json.loads(template.read_text())
    labels.pop(next(iter(labels)))
    labels_path = tmp_path / "smoke" / "sheets" / "missing-labels.json"
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    (labels_path.parent / "blind_key.json").write_text((tmp_path / "smoke" / "sheets" / "blind_key.json").read_text())
    labels_path.write_text(json.dumps(labels), encoding="utf-8")

    code, _report_text = _report(module, tmp_path, off, on, labels_path, capsys)

    assert code == 2
    assert "MISSING LABELS" in capsys.readouterr().err

    _off, _on, _out, template = _prepare(module, tmp_path / "smoke-report", count=3)
    labels = _write_labels(template)
    code, report = _report(module, tmp_path / "smoke-report", _off, _on, labels, capsys)
    assert code == 0
    assert "not applicable (smoke)" in report
