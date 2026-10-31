from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/ringer/environment_narration/opening_condition_v2.py"


def _tool():
    specification = importlib.util.spec_from_file_location("opening_condition_v2_test_tool", SCRIPT)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _capture_document(tool, count: int = 4) -> dict:
    things = []
    for index in range(count):
        thing_id = ("back_door", "house_gate", "service_gate", "facility_gate")[index % 4]
        things.append(
            {
                "thing_id": thing_id,
                "name": thing_id.replace("_", " "),
                "scene_id": "1A",
                "place_id": "kitchen",
                "command": f"Inspect the {thing_id.replace('_', ' ')}.",
                "status": "captured",
                "error": None,
                "request": {
                    "system": "You are the narrator.",
                    "user": f"Inspect the {thing_id}.",
                    "max_tokens": 1024,
                    "response_format": {"type": "json_object"},
                },
            }
        )
    return {"schema": 1, "stage": tool.STAGE, "things": things}


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _raises_value_error():
    return pytest.raises(ValueError)


def test_capture_real_package_has_four_openings_and_turn_commands(tmp_path: Path) -> None:
    tool = _tool()
    document = tool.capture(tmp_path / "capture.json")
    rows = {row["thing_id"]: row for row in document["things"]}
    assert set(rows) == set(tool.PROMPTS)
    assert "storm_drain" not in rows
    assert all(row["status"] == "captured" for row in rows.values())
    for thing_id, (_scene, _place, command) in tool.PROMPTS.items():
        assert rows[thing_id]["command"] == command
        assert command in rows[thing_id]["request"]["user"]
        assert f"- {rows[thing_id]['name']}. Place:" in rows[thing_id]["request"]["user"]
        assert rows[thing_id]["storylets_activated"] == []


def test_offline_item_facts_stub_uses_imported_match_system() -> None:
    tool = _tool()
    from storygame.runtime.item_facts import _MATCH_SYSTEM

    match_payload = {"__freytag_request_budget": "item_facts", "system": _MATCH_SYSTEM}
    assert tool._offline_response(match_payload, "the inspected thing") == {
        "refers": ["the inspected thing"],
        "same_as": {},
        "kind": {},
    }
    other_payload = {
        "__freytag_request_budget": "item_facts",
        "system": f"{_MATCH_SYSTEM} changed",
    }
    assert tool._offline_response(other_payload, "the inspected thing") == {"item_facts": {}}


def test_capture_refuses_class_table_mismatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tool = _tool()
    package = tool._load_package()
    monkeypatch.setattr(tool, "_opening_items", lambda _package: list(package.world.items[:1]))
    with _raises_value_error() as error:
        tool.capture(tmp_path / "capture.json")
    assert "opening class" in str(error.value)
    assert not (tmp_path / "capture.json").exists()


@pytest.mark.parametrize(
    "extra, message",
    [
        ({"samples": 9, "confirm": True}, "samples are frozen"),
        ({"max_calls": 39, "confirm": True}, "planned calls"),
        ({"max_usd": 0.000000001, "confirm": True}, "USD ceiling"),
        ({"confirm": False}, "--confirm"),
    ],
)
def test_run_refuses_guards_before_writing(
    tmp_path: Path,
    extra: dict,
    message: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tool = _tool()
    capture_path = tmp_path / "capture.json"
    _write(capture_path, _capture_document(tool))
    out = tmp_path / "rows.json"
    args = ["--run", "--capture", str(capture_path), "--max-calls", "40", "--max-usd", "1", "--out", str(out)]
    if extra.get("samples") is not None:
        args.extend(["--samples", str(extra["samples"])])
    if extra.get("max_calls") is not None:
        args[args.index("40")] = str(extra["max_calls"])
    if extra.get("max_usd") is not None:
        args[args.index("1")] = str(extra["max_usd"])
    if extra.get("confirm"):
        args.append("--confirm")
    assert tool.main(args) != 0
    assert message in capsys.readouterr().err
    assert not out.exists()


def test_run_refuses_existing_out_and_missing_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tool = _tool()
    document = _capture_document(tool)
    out = tmp_path / "rows.json"
    out.write_text("keep\n", encoding="utf-8")
    with _raises_value_error() as error:
        tool.run_rows(document, samples=10, max_calls=40, max_usd=1, out=out)
    assert "already exist" in str(error.value)
    out.unlink()
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)
    with _raises_value_error() as error:
        tool.run_rows(document, samples=10, max_calls=40, max_usd=1, out=out)
    assert "CLOUDFLARE_WORKER_URL" in str(error.value)
    assert not out.exists()


def test_run_stub_provider_writes_joined_narration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tool = _tool()
    document = _capture_document(tool, count=3)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "test-token")

    def stub(_provider: object, _payload: dict[str, object]) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "A"}, {"kind": "narration", "text": "B"}]}

    monkeypatch.setattr(CloudflareTurnProvider, "_request", stub)
    result = tool.run_rows(document, samples=10, max_calls=30, max_usd=1, out=tmp_path / "rows.json")
    assert result["stop_reason"] is None
    assert len(result["rows"]) == 30
    assert {row["narration"] for row in result["rows"]} == {"AB"}


def test_run_retries_timeout_after_planned_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tool = _tool()
    document = _capture_document(tool)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "secret-token")
    requests = []

    def stub(_provider: object, _payload: dict[str, object]) -> dict[str, object]:
        requests.append(_payload)
        if len(requests) == 3:
            raise TimeoutError("upstream timed out")
        return {"segments": [{"kind": "narration", "text": "ok"}]}

    monkeypatch.setattr(CloudflareTurnProvider, "_request", stub)
    result = tool.run_rows(document, samples=10, max_calls=44, max_usd=1, out=tmp_path / "rows.json")
    assert result["stop_reason"] is None
    assert len(requests) == 41
    assert len(result["rows"]) == 40
    assert result["failed_calls"] == [
        {
            "call_index": 3,
            "thing_id": "back_door",
            "sample": 3,
            "error_type": "TimeoutError",
            "error": "upstream timed out",
            "status": None,
        }
    ]
    retried = [row for row in result["rows"] if row["call_index"] == 41]
    assert len(retried) == 1 and retried[0]["attempt"] == 2
    assert [row["call_index"] for row in result["rows"]] == sorted(row["call_index"] for row in result["rows"])


def test_run_keeps_sample_missing_when_timeout_retry_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tool = _tool()
    document = _capture_document(tool)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "secret-token")
    requests = []

    def stub(_provider: object, _payload: dict[str, object]) -> dict[str, object]:
        requests.append(_payload)
        if len(requests) in {3, 41}:
            raise TimeoutError("upstream timed out")
        return {"segments": [{"kind": "narration", "text": "ok"}]}

    monkeypatch.setattr(CloudflareTurnProvider, "_request", stub)
    result = tool.run_rows(document, samples=10, max_calls=44, max_usd=1, out=tmp_path / "rows.json")
    assert result["stop_reason"] == "request_error"
    assert len(requests) == 41
    assert len(result["rows"]) == 39
    assert [failure["call_index"] for failure in result["failed_calls"]] == [3, 41]


def test_run_stops_and_records_non_timeout_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tool = _tool()
    document = _capture_document(tool)
    token = "secret-token"
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", token)

    def stub(_provider: object, _payload: dict[str, object]) -> dict[str, object]:
        raise NarrationProviderError(f"worker rejected {token}")

    monkeypatch.setattr(CloudflareTurnProvider, "_request", stub)
    result = tool.run_rows(document, samples=10, max_calls=44, max_usd=1, out=tmp_path / "rows.json")
    assert result["stop_reason"] == "http_503"
    assert len(result["failed_calls"]) == 1
    failure = result["failed_calls"][0]
    assert failure["error_type"] == "NarrationProviderError"
    assert failure["status"] == 503
    assert token not in failure["error"]
    assert "<redacted>" in failure["error"]


def test_run_stops_after_three_consecutive_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tool = _tool()
    document = _capture_document(tool)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "secret-token")
    requests = []

    def stub(_provider: object, _payload: dict[str, object]) -> dict[str, object]:
        requests.append(_payload)
        raise TimeoutError("upstream timed out")

    monkeypatch.setattr(CloudflareTurnProvider, "_request", stub)
    result = tool.run_rows(document, samples=10, max_calls=44, max_usd=1, out=tmp_path / "rows.json")
    assert result["stop_reason"] == "three_consecutive_failures"
    assert len(requests) == 3
    assert len(result["failed_calls"]) == 3


def test_run_never_exceeds_max_calls_while_retrying(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tool = _tool()
    document = _capture_document(tool)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "secret-token")
    requests = []

    def stub(_provider: object, _payload: dict[str, object]) -> dict[str, object]:
        requests.append(_payload)
        if len(requests) in {1, 11, 21, 31}:
            raise TimeoutError("upstream timed out")
        return {"segments": [{"kind": "narration", "text": "ok"}]}

    monkeypatch.setattr(CloudflareTurnProvider, "_request", stub)
    result = tool.run_rows(document, samples=10, max_calls=42, max_usd=1, out=tmp_path / "rows.json")
    assert len(requests) == 42
    assert result["stop_reason"] == "max_calls"
    assert len(result["rows"]) == 38


def test_blind_sheet_is_deterministic_and_has_only_narration(tmp_path: Path) -> None:
    tool = _tool()
    rows_path = tmp_path / "rows.json"
    _write(
        rows_path,
        {
            "rows": [
                {"call_index": 1, "thing_id": "back_door", "command": "Inspect the back door.", "narration": "One."},
                {"call_index": 2, "thing_id": "house_gate", "command": "Inspect the house gate.", "narration": "Two."},
            ]
        },
    )
    first = tmp_path / "sheet-one"
    second = tmp_path / "sheet-two"
    tool.blind_sheet(rows_path, first)
    tool.blind_sheet(rows_path, second)
    assert (first / "sheet.md").read_text() == (second / "sheet.md").read_text()
    sheet = (first / "sheet.md").read_text()
    assert "back_door" not in sheet and "house_gate" not in sheet
    assert "Inspect the" not in sheet and "call_index" not in sheet
    labels = json.loads((first / "labels_template.json").read_text())
    assert set(next(iter(labels.values()))) == set(tool.LABEL_NAMES)
    assert all(value is None for entry in labels.values() for value in entry.values())


def test_freeze_rejects_null_and_changed_hash(tmp_path: Path) -> None:
    tool = _tool()
    labels = tmp_path / "labels.json"
    _write(labels, {"sample-001": {name: None for name in tool.LABEL_NAMES}})
    with _raises_value_error() as error:
        tool.freeze_labels(labels)
    assert "null" in str(error.value)
    _write(labels, {"sample-001": {name: False for name in tool.LABEL_NAMES}})
    freeze = tool.freeze_labels(labels)
    assert freeze.name == "labels.freeze.json"
    labels.write_text(labels.read_text() + "\n", encoding="utf-8")
    with _raises_value_error() as error:
        tool.freeze_labels(labels)
    assert "hash" in str(error.value)


def test_build_cases_requires_freeze_and_uses_probe_fields(tmp_path: Path) -> None:
    tool = _tool()
    rows = tmp_path / "rows.json"
    labels = tmp_path / "labels.json"
    key = tmp_path / "blind_key.json"
    row = {
        "call_index": 1,
        "thing_id": "back_door",
        "command": "Inspect the back door.",
        "sample": 1,
        "narration": "It is open and contains a box.",
    }
    _write(rows, {"rows": [row]})
    _write(labels, {"sample-001": {name: False for name in tool.LABEL_NAMES} | {"opens_or_enters": True}})
    _write(key, {"sample-001": 1})
    with _raises_value_error() as error:
        tool.build_cases(rows, labels, key, tmp_path / "cases")
    assert "freeze" in str(error.value)
    tool.freeze_labels(labels)
    out = tmp_path / "cases"
    tool.build_cases(rows, labels, key, out)
    case = json.loads((out / "cases.jsonl").read_text().splitlines()[0])
    judge = tool._judge_probe()
    assert set(case) == judge.CASE_FIELDS
    assert case["forbidden"] is True
    assert case["declared"] == "the back door has no open or closed value, no declared contents, and is fixed in place."
    assert case["source_ref"] == "back_door/sample-1"


def test_judge_plan_is_variant_b_only_and_byte_identical_question() -> None:
    tool = _tool()
    judge = tool._judge_probe()
    case = {
        "id": "back_door-sample-001",
        "set": "opening",
        "thing": "back door",
        "command": "Inspect the back door.",
        "narration": "She touches the door.",
        "declared": "the back door has no open or closed value, no declared contents, and is fixed in place.",
        "forbidden": False,
        "source_ref": "back_door/sample-1",
    }
    planned = tool._planned_judge([case], 5)
    assert {item["variant"] for item in planned} == {"B"}
    assert all(tool._judge_probe().variant_b_payload(item["case"]) == judge.variant_b_payload(case) for item in planned)


def _cases_directory(tmp_path: Path, forbidden_count: int = 10, clean_count: int = 10) -> Path:
    tool = _tool()
    directory = tmp_path / "cases"
    directory.mkdir()
    cases = []
    for index in range(forbidden_count + clean_count):
        forbidden = index < forbidden_count
        cases.append(
            {
                "id": f"case-{index}",
                "set": "opening",
                "thing": "back door",
                "command": "Inspect the back door.",
                "narration": "Narration.",
                "declared": "the back door has no open or closed value, no declared contents, and is fixed in place.",
                "forbidden": forbidden,
                "source_ref": f"back_door/sample-{index}",
            }
        )
    data = "".join(json.dumps(case, separators=(",", ":")) + "\n" for case in cases).encode()
    (directory / "cases.jsonl").write_bytes(data)
    _write(directory / "lock.json", {"cases_sha256": tool._sha256_bytes(data), "case_count": len(cases)})
    return directory


def _judge_rows_for(cases: list[dict], score_for: Callable[[dict], float], samples: int = 5) -> list[dict]:
    rows = []
    for case in cases:
        for sample in range(1, samples + 1):
            rows.append({"case_id": case["id"], "variant": "B", "sample": sample, "score": score_for(case)})
    return rows


@pytest.mark.parametrize("kind", ["pass", "fail", "partial", "few_forbidden", "few_clean"])
def test_report_gate_branches(tmp_path: Path, kind: str) -> None:
    tool = _tool()
    forbidden_count = 10 if kind != "few_forbidden" else 9
    clean_count = 10 if kind != "few_clean" else 9
    cases_dir = _cases_directory(tmp_path, forbidden_count, clean_count)
    cases = [json.loads(line) for line in (cases_dir / "cases.jsonl").read_text().splitlines()]
    if kind == "fail":

        def score_for(case: dict) -> float:
            return 1.0 if case["forbidden"] else 0.0
    else:

        def score_for(case: dict) -> float:
            return 0.0 if case["forbidden"] else 1.0

    rows = _judge_rows_for(cases, score_for)
    if kind == "partial":
        rows.pop()
    rows_path = tmp_path / "rows.json"
    _write(
        rows_path,
        {
            "samples": 5,
            "calls_planned": len(cases) * 5,
            "rows": rows,
            "stop_reason": None if kind != "partial" else "request_error",
        },
    )
    verdict = tool.report_rows(cases_dir, rows_path, tmp_path / "report.md")
    expected = {
        "pass": "PASS",
        "fail": "FAIL",
        "partial": "INCONCLUSIVE",
        "few_forbidden": "INCONCLUSIVE",
        "few_clean": "INCONCLUSIVE",
    }
    assert verdict == expected[kind]
