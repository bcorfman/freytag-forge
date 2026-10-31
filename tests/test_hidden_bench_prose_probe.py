from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ringer/environment_narration/hidden_bench_prose_probe.py"
FROZEN_ROWS_FIXTURE = ROOT / "tests/fixtures/t9h_ci/probes/hidden_bench_prose_rows.json"
FROZEN_KEY_FIXTURE = ROOT / "tests/fixtures/t9h_ci/probes/hidden_bench_prose_blind_key.json"


def _module():
    specification = importlib.util.spec_from_file_location("hidden_bench_prose_probe", SCRIPT)
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module


def _labels_for_rows(module, rows_path: Path, output: Path) -> tuple[Path, Path]:
    module.sheets(rows_path, output)
    labels_template = output / "labels_template.json"
    labels = json.loads(labels_template.read_text())
    for entry in labels.values():
        for name in module.LABEL_NAMES:
            entry[name] = False
    key = json.loads((output / "blind_key.json").read_text())
    for opaque_id, value in key.items():
        if value["arm"] == "P1" and value["state"] == "find":
            labels[opaque_id]["conveys_all_three_objects_and_keeping"] = True
    labels_path = output / "labels.json"
    labels_path.write_text(json.dumps(labels, indent=2) + "\n")
    module.write_label_freeze(labels_path)
    return labels_path, output / "blind_key.json"


def _complete_rows(module) -> dict[str, object]:
    payloads = []
    for state in module.STATES:
        for arm in module.ARMS:
            payloads.append({"id": f"{arm.lower()}-{state}", "arm": arm, "state": state, "system": "", "user": ""})
    rows = []
    for payload in payloads:
        for sample in range(1, module.SAMPLES + 1):
            rows.append(
                {
                    "payload_id": payload["id"],
                    "arm": payload["arm"],
                    "state": payload["state"],
                    "sample": sample,
                    "response_text": json.dumps(
                        {
                            "segments": [{"kind": "narration", "text": "A quiet bench scene."}],
                            "selected_knowledge_ids": [],
                        }
                    ),
                }
            )
    return {
        "schema": 1,
        "stage": "t9h-hidden-prose",
        "calls_planned": 60,
        "payloads": payloads,
        "rows": rows,
        "stop_reason": None,
    }


def test_capture_builds_six_real_engine_payloads_without_http(monkeypatch) -> None:
    module = _module()
    calls = []

    def no_http(*_args, **_kwargs):
        calls.append(1)
        raise AssertionError("capture must not reach urlopen")

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", no_http)
    document = module.capture_payloads()

    assert len(document["payloads"]) == 6
    assert {(item["state"], item["arm"]) for item in document["payloads"]} == {
        (state, arm) for state in module.STATES for arm in module.ARMS
    }
    assert all(isinstance(item["composed_segments"], list) for item in document["payloads"])
    assert any("THINGS:" in item["user"] for item in document["payloads"])
    find_payload = next(item for item in document["payloads"] if item["arm"] == "P1" and item["state"] == "find")
    delivery_text = (
        "Kristin reaches beneath the park bench. She retrieves a transit token, a handwritten number sequence and "
        "Michelle's photograph. She keeps all three with her."
    )
    assert any(segment["text"] == delivery_text for segment in find_payload["composed_segments"])
    assert calls == []


def test_preflight_rejects_injected_p1_clue_word_and_real_payloads_pass() -> None:
    module = _module()
    document = module.capture_payloads()

    assert module.preflight(document) == []
    injected = json.loads(json.dumps(document))
    next(item for item in injected["payloads"] if item["arm"] == "P1" and item["state"] == "opening")["user"] += (
        " transit"
    )
    assert module.preflight(injected)


def test_world_aware_item_facts_extra_composes_the_p1_find_delivery() -> None:
    module = _module()
    from storygame.story_package.loader import load_story_package

    package = load_story_package(module.PACKAGE_ROOT)
    response = json.dumps(
        {
            "segments": [{"kind": "narration", "text": "A quiet bench scene."}],
            "selected_knowledge_ids": [],
            "item_facts": {},
        }
    )

    delivery, composable = module._inferred_delivery(package, "find", response)

    assert composable
    assert any(
        segment["text"]
        == (
            "Kristin reaches beneath the park bench. She retrieves a transit token, a handwritten number sequence "
            "and Michelle's photograph. She keeps all three with her."
        )
        for segment in delivery
    )


def test_unknown_reply_extra_is_not_composable() -> None:
    module = _module()
    from storygame.story_package.loader import load_story_package

    package = load_story_package(module.PACKAGE_ROOT)
    response = json.dumps(
        {
            "segments": [{"kind": "narration", "text": "A quiet bench scene."}],
            "selected_knowledge_ids": [],
            "unknown_extra": True,
        }
    )

    with pytest.raises(ValueError):
        module._inferred_delivery(package, "find", response)


def test_head_control_payloads_are_not_augmented_after_capture() -> None:
    module = _module()
    document = module.capture_payloads()
    old_payloads = [
        item for item in document["payloads"] if item["arm"] == "P0" and item["state"] in {"opening", "prefind"}
    ]

    assert old_payloads
    assert all("LEGACY VISIBLE BENCH OBJECTS:" not in item["user"] for item in old_payloads)


def test_dry_run_has_sixty_calls_and_refuses_both_caps(monkeypatch, capsys) -> None:
    module = _module()
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)

    assert module.main(["--dry-run", "--max-calls", "60", "--max-usd", "0.06"]) == 0
    output = capsys.readouterr().out
    assert "planned calls: 60" in output
    assert "token estimate:" in output
    assert "USD ceiling:" in output
    assert module.main(["--dry-run", "--max-calls", "10", "--max-usd", "0.06"]) == 1
    assert "exceed --max-calls" in capsys.readouterr().err
    assert module.main(["--dry-run", "--max-calls", "60", "--max-usd", "0"]) == 1
    assert "exceeds --max-usd" in capsys.readouterr().err


def test_run_stops_on_429_without_replacing_a_sample(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    document = _complete_rows(module)
    output = tmp_path / "rows.json"
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid/turn")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "test-token")

    def quota(*_args, **_kwargs):
        raise HTTPError("https://worker.invalid/turn", 429, "quota", {}, None)

    monkeypatch.setattr("storygame.runtime.cloudflare.CloudflareTurnProvider._request", quota)
    result = module.run_rows(document, max_calls=60, max_usd=0.06, out=output)

    assert result["rows"] == []
    assert "429" in result["stop_reason"]
    assert json.loads(output.read_text())["stop_reason"] == result["stop_reason"]


def test_sheets_hide_arm_and_key_restores_it(tmp_path: Path) -> None:
    module = _module()
    rows_path = tmp_path / "rows.json"
    rows_path.write_text(json.dumps(_complete_rows(module)))
    labels_path, key_path = _labels_for_rows(module, rows_path, tmp_path / "sheets")

    sheet = (tmp_path / "sheets" / "blind_sheet.md").read_text()
    key = json.loads(key_path.read_text())
    assert "P0" not in sheet and "P1" not in sheet
    assert {value["arm"] for value in key.values()} == {"P0", "P1"}
    assert labels_path.is_file()


def test_blind_key_is_a_bijection_for_synthetic_and_frozen_rows(tmp_path: Path) -> None:
    module = _module()
    rows_document = _complete_rows(module)
    rows_path = tmp_path / "rows.json"
    rows_path.write_text(json.dumps(rows_document))
    output = tmp_path / "sheets"
    module.sheets(rows_path, output)
    synthetic_rows = rows_document["rows"]
    synthetic_key = json.loads((output / "blind_key.json").read_text())
    module.assert_blind_key_bijection(synthetic_rows, synthetic_key)

    frozen_rows = json.loads(FROZEN_ROWS_FIXTURE.read_text())["rows"]
    frozen_key = json.loads(FROZEN_KEY_FIXTURE.read_text())
    module.assert_blind_key_bijection(frozen_rows, frozen_key)


def test_composed_view_is_blind_and_post_hoc(tmp_path: Path) -> None:
    module = _module()
    rows_path = tmp_path / "rows.json"
    rows_path.write_text(json.dumps(_complete_rows(module)))
    before = rows_path.read_bytes()
    output = tmp_path / "views"

    assert module.main(["--composed-view", "--rows", str(rows_path), "--out", str(output)]) == 0

    raw_view = (output / "raw_view.md").read_text()
    composed_view = (output / "composed_view.md").read_text()
    assert rows_path.read_bytes() == before
    assert composed_view.startswith(
        "# Composed prose view\n\nThis is a post hoc, inferred composition, not a set of accepted game turns.\n"
    )
    assert "It does not change the recorded stage 2 FAIL." in composed_view
    assert composed_view.count("## sample-") == 60
    assert raw_view.count("## sample-") == 60
    assert all(not line.startswith(("Arm:", "Payload:")) for line in composed_view.splitlines())
    assert composed_view.count("Engine (appended by the game):") >= 20
    delivery_text = (
        "Kristin reaches beneath the park bench. She retrieves a transit token, a handwritten number sequence and "
        "Michelle's photograph. She keeps all three with her."
    )
    assert composed_view.count(delivery_text) == 20


def test_report_computes_p1a_p1b_p1c_and_requires_frozen_labels(tmp_path: Path) -> None:
    module = _module()
    rows_path = tmp_path / "rows.json"
    rows_path.write_text(json.dumps(_complete_rows(module)))
    labels_path, _key_path = _labels_for_rows(module, rows_path, tmp_path / "sheets")
    report_path = tmp_path / "report.md"

    rendered, passed = module.report(rows_path, labels_path, report_path)
    assert passed
    assert "P1a: PASS" in rendered
    assert "P1b: PASS" in rendered
    assert "P1c: PASS" in rendered

    labels = json.loads(labels_path.read_text())
    labels[next(iter(labels))]["moves_fixed_bench"] = True
    labels_path.write_text(json.dumps(labels))
    with pytest.raises(ValueError):
        module.report(rows_path, labels_path, report_path)
