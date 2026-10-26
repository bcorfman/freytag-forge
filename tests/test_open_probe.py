from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

import storygame.runtime.cloudflare as cloudflare
from scripts.ringer.transcript_1a import open_probe


def _synthetic_prompt() -> dict[str, str]:
    return {
        "system": "SYSTEM PROMPT",
        "user": (
            "SCENE:\n"
            "- Michelle's house stands behind a low gate.\n"
            "- KMS initials carved in drawer.\n\n"
            "THINGS:\n"
            "- Kristin. Place: Michelle's house.\n"
            "- drawer. Place: in Michelle's workstation.\n\n"
            "CONSTRAINTS:\n"
            "- Dr. Michelle McGehee may say this aloud: Kristin finds Michelle's memory card taped beneath the drawer "
            "and pockets it.\n\n"
            "PLAYER:\n"
            "- Kristin. Place: Michelle's house.\n"
            "- Feel under the drawer.\n"
        ),
    }


@pytest.mark.parametrize(
    ("problem", "arm", "needle", "replacement"),
    (
        ("P1", "drop", "CONSTRAINTS:\n", None),
        (
            "P1",
            "past",
            "Dr. Michelle McGehee may say this aloud: Kristin already took",
            "Kristin already took Michelle's memory card from beneath the drawer.",
        ),
        ("P2", "where", "SCENE:\n- Kristin is inside the house.", None),
        ("P2", "place", "- Kristin. Place: inside Michelle's house.", None),
        (
            "P3",
            "view",
            "From the curb she can see the gate, the front of the house, the truck, the street, and the lights "
            "on the next street.",
            None,
        ),
        ("P3", "rule", "- Describe only the things in THINGS and SCENE.", None),
    ),
)
def test_each_arm_changes_only_the_intended_user_line(
    problem: str, arm: str, needle: str, replacement: str | None
) -> None:
    control = _synthetic_prompt()
    transformed = open_probe.transform_user(problem, arm, control["user"])

    assert transformed != control["user"]
    assert control["system"] == "SYSTEM PROMPT"
    assert needle in transformed
    if replacement is not None:
        assert replacement in transformed
    if problem == "P1" and arm == "drop":
        assert "finds Michelle's memory card taped beneath the drawer and pockets it." not in transformed
    if problem == "P2" and arm == "where":
        assert transformed.split("SCENE:\n", 1)[1].startswith("- Kristin is inside the house.\n")
    if problem == "P3" and arm == "rule":
        assert transformed.count("Describe only the things in THINGS and SCENE.") == 1


def test_arm_transforms_are_exact_line_edits() -> None:
    control = _synthetic_prompt()["user"]
    control_lines = control.splitlines()
    constraints_last = control_lines.index(open_probe.P1_CARD_LINE)
    things_place = control_lines.index(open_probe.P2_OLD_PLACE_LINE)

    expected = {
        ("P1", "drop"): [line for line in control_lines if line != open_probe.P1_CARD_LINE],
        ("P1", "past"): [
            open_probe.P1_PAST_LINE if line == open_probe.P1_CARD_LINE else line for line in control_lines
        ],
        ("P2", "where"): [
            line
            for index, line in enumerate(control_lines)
            for line in ((open_probe.P2_SCENE_LINE, line) if index == 1 else (line,))
        ],
        ("P2", "place"): [
            open_probe.P2_PLACE_LINE if index == things_place else line for index, line in enumerate(control_lines)
        ],
        ("P3", "view"): [
            line + open_probe.P3_VIEW_SUFFIX if line == open_probe.P3_SCENE_PREFIX else line for line in control_lines
        ],
        ("P3", "rule"): [
            *control_lines[: constraints_last + 1],
            open_probe.P3_RULE_LINE,
            *control_lines[constraints_last + 1 :],
        ],
    }

    for key, lines in expected.items():
        problem, arm = key
        transformed = open_probe.transform_user(problem, arm, control)
        assert transformed.splitlines() == lines


@pytest.mark.parametrize(
    ("problem", "arm", "missing"),
    (
        ("P1", "drop", "finds Michelle's memory card taped beneath the drawer and pockets it."),
        ("P1", "past", "finds Michelle's memory card taped beneath the drawer and pockets it."),
        ("P2", "where", "SCENE:"),
        ("P2", "place", "- Kristin. Place: Michelle's house."),
        ("P3", "view", "Michelle's house stands behind a low gate."),
        ("P3", "rule", "CONSTRAINTS:"),
    ),
)
def test_missing_expected_line_fails_loudly(problem: str, arm: str, missing: str) -> None:
    control = _synthetic_prompt()["user"].replace(missing, "MISSING")

    with pytest.raises(ValueError, match="expected|missing|section|line"):
        open_probe.transform_user(problem, arm, control)


def _sample_document() -> dict[str, object]:
    problems = []
    for problem_id, arms in (
        ("P1", ("control", "drop", "past")),
        ("P2", ("control", "where", "place")),
        ("P3", ("control", "view", "rule")),
    ):
        problems.append(
            {
                "id": problem_id,
                "control": {"system": "SYSTEM", "user": f"{problem_id} control"},
                "arms": {arm: {"system": "SYSTEM", "user": f"{problem_id} {arm}"} for arm in arms},
                "diffs": {arm: f"diff {arm}" for arm in arms if arm != "control"},
            }
        )
    return {"mode": "dry", "problems": problems}


class _Response:
    status = 200
    headers: dict[str, str] = {}

    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def test_live_refuses_without_confirm_or_worker_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[object] = []
    monkeypatch.setattr(cloudflare, "urlopen", lambda *args, **kwargs: calls.append(args))
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)

    assert open_probe.main(["--run", "--samples", "1", "--out", str(tmp_path / "rows.json")]) == 2
    assert calls == []


def test_live_refuses_over_cap_before_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(open_probe, "build_document", _sample_document)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    calls: list[object] = []
    monkeypatch.setattr(cloudflare, "urlopen", lambda *args, **kwargs: calls.append(args))

    assert (
        open_probe.main(
            ["--run", "--samples", "40", "--confirm", "--max-calls", "100", "--out", str(tmp_path / "rows.json")]
        )
        == 2
    )
    assert calls == []


def test_live_writes_partial_rows_and_parses_reply(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    calls: list[dict[str, object]] = []

    def opener(request: object, **_kwargs: object) -> _Response:
        calls.append(json.loads(request.data))
        return _Response(
            {
                "narration": json.dumps(
                    {
                        "segments": [
                            {"kind": "narration", "text": "First."},
                            {"kind": "dialogue", "text": "Second."},
                        ],
                        "item_facts": {"drawer": {"condition": ["open"]}},
                    }
                )
            }
        )

    monkeypatch.setattr(cloudflare, "urlopen", opener)
    out = tmp_path / "rows.json"
    result = open_probe.run_samples(_sample_document(), samples=1, problem="all", max_calls=100, out=out)

    assert len(calls) == 9
    assert len(result["rows"]) == 9
    assert result["rows"][0]["narration"] == "First. Second."
    assert result["rows"][0]["item_facts"] == {"drawer": {"condition": ["open"]}}
    assert json.loads(out.read_text())["rows"]
    assert all(payload["max_tokens"] == 1024 for payload in calls)


def test_live_stops_on_429_quota_and_keeps_quota_row(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    calls: list[object] = []

    def opener(request: object, **_kwargs: object) -> _Response:
        calls.append(request)
        if len(calls) == 2:
            raise HTTPError(
                request.full_url,
                429,
                "quota",
                {},
                io.BytesIO(b'{"code":"AI_DAILY_BUDGET_EXCEEDED"}'),
            )
        return _Response({"segments": [{"kind": "narration", "text": "Reply."}]})

    monkeypatch.setattr(cloudflare, "urlopen", opener)
    out = tmp_path / "rows.json"
    result = open_probe.run_samples(_sample_document(), samples=1, problem="P1", max_calls=100, out=out)

    assert len(calls) == 2
    assert result["stop_reason"] == "AI_DAILY_BUDGET_EXCEEDED"
    assert len(result["rows"]) == 2
    assert result["rows"][-1]["status"] == 429
    assert json.loads(out.read_text())["stop_reason"] == "AI_DAILY_BUDGET_EXCEEDED"
