from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

import storygame.runtime.cloudflare as cloudflare
from scripts.ringer.transcript_1a import boarding_probe


def _synthetic_prompt() -> str:
    return (
        "SCENE:\n"
        "- A room.\n\n"
        "CONSTRAINTS:\n"
        "- Keep it short.\n\n"
        "PLAYER:\n"
        "- Player. Place: room.\n"
        "- Do the thing.\n"
        "- Just before this: Player opened the door.\n"
    )


def test_arm_text_transforms_keep_system_and_control_unchanged() -> None:
    control = _synthetic_prompt()
    arm0 = boarding_probe.arm_user_text(control, 0)
    arm1 = boarding_probe.arm_user_text(control, 1, "Do the thing.")
    arm2 = boarding_probe.arm_user_text(control, 2)

    assert arm0 == control
    assert "Just before this:" not in arm1
    assert "- Do the thing." not in arm1
    assert arm1.endswith("- Player opened the door.\n")
    assert arm2.count("Show every thing named in the Just before this line.") == 1
    assert arm2.count("CONSTRAINTS:\n") == 1
    assert "- Show every thing named in the Just before this line." in arm2


def test_real_dry_document_has_three_prompts_three_arms_and_no_opener_calls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[object] = []
    monkeypatch.setattr(cloudflare, "urlopen", lambda *args, **kwargs: calls.append(args) or None)
    output = tmp_path / "boarding-probe-dry.json"

    assert boarding_probe.main(["--dry", "--out", str(output)]) == 0

    document = json.loads(output.read_text())
    assert len(document["prompts"]) == 3
    assert all(set(prompt["arms"]) == {"0", "1", "2"} for prompt in document["prompts"])
    assert all(set(prompt["diffs"]) == {"1", "2"} for prompt in document["prompts"])
    assert calls == []


def test_missing_just_before_line_fails_loudly() -> None:
    with pytest.raises(ValueError, match="Just before this:"):
        boarding_probe.arm_user_text("PLAYER:\n- Player. Place: room.\n", 1)


def test_cap_refuses_before_any_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    document = boarding_probe.dry_document(boarding_probe.build_control_prompts())
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    calls: list[object] = []
    monkeypatch.setattr(cloudflare, "urlopen", lambda *args, **kwargs: calls.append(args) or None)

    with pytest.raises(boarding_probe.CallCapExceeded, match="requested 108 calls"):
        boarding_probe.run_samples(document, samples=12, max_calls=100, out=tmp_path / "rows.json")
    assert calls == []


class _Response:
    status = 200

    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def test_run_is_interleaved_and_stops_on_quota_429(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    document = boarding_probe.dry_document(boarding_probe.build_control_prompts())
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    payloads: list[dict[str, object]] = []

    def opener(request: object, **_kwargs: object) -> _Response:
        payloads.append(json.loads(request.data))
        if len(payloads) == 5:
            raise HTTPError(
                request.full_url,
                429,
                "quota",
                {},
                io.BytesIO(b'{"code":"AI_QUOTA_EXCEEDED"}'),
            )
        return _Response({"narration": json.dumps({"segments": [{"kind": "narration", "text": "A reply."}]})})

    monkeypatch.setattr(cloudflare, "urlopen", opener)
    output = tmp_path / "rows.json"
    result = boarding_probe.run_samples(document, samples=2, max_calls=100, out=output)

    assert len(payloads) == 5
    assert result["calls_made"] == 5
    assert result["stop_reason"] == "AI_QUOTA_EXCEEDED"
    assert [row["arm"] for row in result["rows"][:4]] == [0, 0, 0, 1]
    assert [row["prompt_id"] for row in result["rows"][:4]] == ["P1", "P2", "P3", "P1"]
    assert result["rows"][0]["narration"] == "A reply."
    assert json.loads(output.read_text())["stop_reason"] == "AI_QUOTA_EXCEEDED"


def test_live_without_confirm_makes_no_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[object] = []
    monkeypatch.setattr(cloudflare, "urlopen", lambda *args, **kwargs: calls.append(args))
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)

    assert boarding_probe.main(["--run", "--samples", "1", "--out", str(tmp_path / "rows.json")]) == 2
    assert calls == []
