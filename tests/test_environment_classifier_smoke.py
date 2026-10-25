from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from scripts.ringer.environment_narration import classifier_smoke


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_network(*_args: object, **_kwargs: object) -> None:
        pytest.fail("network access in classifier smoke test")

    monkeypatch.setattr(classifier_smoke, "urlopen", fail_network)
    monkeypatch.setattr(socket, "socket", fail_network)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_plan_has_35_calls_and_stays_under_five_cents(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "plan.json"

    assert classifier_smoke.main(["--dry", "--out", str(out)]) == 0
    plan = _read(out)

    assert len(plan["calls"]) == 35
    assert plan["ceiling_usd"] < 0.05
    assert sum(call["kind"] == "matcher" for call in plan["calls"]) == 20
    assert sum(call["kind"] == "second_call" for call in plan["calls"]) == 15
    assert "35 calls" in capsys.readouterr().out


def test_request_body_is_the_nojson_worker_profile(tmp_path: Path) -> None:
    plan_out = tmp_path / "plan.json"
    classifier_smoke.main(["--dry", "--out", str(plan_out)])
    call = _read(plan_out)["calls"][0]

    body = classifier_smoke._request_body(call)

    assert body["messages"] == [
        {"role": "system", "content": call["system"]},
        {"role": "user", "content": call["user"]},
    ]
    assert body["max_tokens"] == call["max_tokens"]
    assert "response_format" not in body
    assert "temperature" not in body


@pytest.mark.parametrize(
    ("kind", "text", "expected", "strict", "decoded"),
    [
        (
            "matcher",
            '{"refers":["truck"],"same_as":{}}',
            {"offered_names": ["truck"], "must_include": "truck"},
            True,
            True,
        ),
        (
            "matcher",
            '```json\n{"refers":[],"same_as":{}}\n```',
            {"offered_names": [], "must_include": None},
            False,
            False,
        ),
        (
            "matcher",
            '{"refers":["truck"],"same_as":{"truck":"the "truck"}}',
            {"offered_names": ["truck"], "must_include": "truck"},
            False,
            True,
        ),
        (
            "matcher",
            '{"refers":["truck"],"same_as":{}',
            {"offered_names": ["truck"], "must_include": "truck"},
            False,
            True,
        ),
        ("matcher", "not json", {"offered_names": [], "must_include": None}, False, False),
    ],
)
def test_scoring_distinguishes_strict_and_product_decoding(
    kind: str, text: str, expected: dict, strict: bool, decoded: bool
) -> None:
    result = classifier_smoke.score_reply(kind, text, expected)

    assert result["strict_valid"] is strict
    assert result["product_decoded"] is decoded


def test_run_requires_all_live_guards_without_touching_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "rows.json"
    monkeypatch.setattr(classifier_smoke, "_call", lambda *_args: pytest.fail("network call"))

    assert classifier_smoke.main(["--run", "--out", str(out)]) == 2
    assert classifier_smoke.main(["--run", "--out", str(out), "--confirm", "--max-calls", "35"]) == 2
    assert classifier_smoke.main(["--run", "--out", str(out), "--confirm", "--max-calls", "35", "--max-usd", "0"]) == 2
    assert not out.exists()


def test_report_prints_raw_reply_for_every_row(tmp_path: Path) -> None:
    rows = tmp_path / "rows.json"
    report = tmp_path / "report.md"
    rows.write_text(
        json.dumps(
            {
                "ceiling_usd": 0.01,
                "rows": [
                    {
                        "call_index": 1,
                        "kind": "matcher",
                        "command": "Enter the truck.",
                        "expected": {"must_include": "truck"},
                        "raw_reply": '{"refers":["truck"],"same_as":{}}',
                        "strict_valid": True,
                        "product_decoded": True,
                        "shape_valid": True,
                        "correct": True,
                        "latency_ms": 4,
                        "status": 200,
                    },
                    {
                        "call_index": 2,
                        "kind": "second_call",
                        "narration": "The drawer opens.",
                        "expected": {"changed": "drawer"},
                        "raw_reply": "not json",
                        "strict_valid": False,
                        "product_decoded": False,
                        "shape_valid": False,
                        "correct": False,
                        "latency_ms": 5,
                        "status": 200,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    assert classifier_smoke.main(["--report", "--rows", str(rows), "--out", str(report)]) == 0
    text = report.read_text(encoding="utf-8")
    assert '{"refers":["truck"],"same_as":{}}' in text
    assert "not json" in text
    assert "strict-valid" in text
    assert "product-decoded" in text
    assert "shape-valid" in text
    assert "correct" in text


def test_run_writes_each_answered_row_and_stops_on_401(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "rows.json"
    calls = 0

    def fake_call(_account: str, _token: str, call: dict) -> dict:
        nonlocal calls
        calls += 1
        if calls == 1:
            return {
                "status": 401,
                "latency_ms": 1.5,
                "raw_response": '{"errors":[{"message":"bad auth"}]}',
                "raw_reply": None,
                "usage": None,
                "response_model": None,
            }
        raise AssertionError("call after auth stop")

    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account-example")
    monkeypatch.setenv("CLOUDFLARE_AI_TOKEN", "secret-token-value")
    monkeypatch.setattr(classifier_smoke, "_call", fake_call)

    assert (
        classifier_smoke.main(["--run", "--out", str(out), "--confirm", "--max-calls", "35", "--max-usd", "0.05"]) == 0
    )
    result = _read(out)
    assert calls == 1
    assert len(result["rows"]) == 1
    assert result["stop_reason"] == "AUTH"
    assert "secret-token-value" not in out.read_text(encoding="utf-8")
