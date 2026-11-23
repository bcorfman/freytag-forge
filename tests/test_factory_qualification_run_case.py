from __future__ import annotations

import builtins
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from factory.guard import ProviderLimit
from factory.qualification import run_case

ROOT = Path(__file__).parents[1]
STORY_FIXTURE = ROOT / "tests/fixtures/stories/lighthouse-incident"


def _case(tmp_path: Path) -> Path:
    case = tmp_path / "case"
    story = case / "solver/repo/data/stories/lighthouse-incident"
    story.parent.mkdir(parents=True)
    shutil.copytree(STORY_FIXTURE, story)
    (case / "solver").mkdir(exist_ok=True)
    (case / "solver/records.json").write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "replicate": 1,
                        "scene": "1A",
                        "turns": [
                            {
                                "turn": 1,
                                "raw_input": "",
                                "text": "The cottage is quiet.",
                                "outcome": "committed",
                            }
                        ],
                        "stuck_turns": [1],
                        "exit_cause": "timer",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (case / "manifest.json").write_text(
        json.dumps({"case": "tiny-case", "solver_tree_sha256": "tree-hash"}), encoding="utf-8"
    )
    return case


def _isolated_controls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "controls"
    config = root / "factory/config"
    config.mkdir(parents=True)
    shutil.copy(ROOT / "factory/config/allowlist.json", config / "allowlist.json")
    factory_config = json.loads((ROOT / "factory/config/factory.json").read_text(encoding="utf-8"))
    factory_config["paths"]["allowlist"] = "factory/config/allowlist.json"
    factory_config["paths"]["ledger"] = "ledger.jsonl"
    (config / "factory.json").write_text(json.dumps(factory_config), encoding="utf-8")
    monkeypatch.setattr(run_case, "CONTROL_ROOT", root)
    return root


def _stream(reply: str, tokens: int = 2) -> str:
    return json.dumps(
        {
            "type": "result",
            "result": reply,
            "usage": {"input_tokens": 1, "output_tokens": tokens - 1},
        }
    )


def _replies() -> tuple[str, str]:
    classifier = json.dumps({"1A-r1-t1": {"cause": "no_authored_outcome", "why": "The evidence is insufficient."}})
    planner = json.dumps(
        {
            "version": 1,
            "ticket_id": "qualification-plan",
            "scene": "1A",
            "kind": "unsupported",
            "reason": "Reroute: the tiny fixture does not support a safe story-data fix.",
            "evidence_keys": ["1A-r1-t1"],
            "reroute": "adaptive_probe",
        }
    )
    return classifier, planner


def _run_with_fake(monkeypatch: pytest.MonkeyPatch, replies: tuple[str, str], *, tokens: int = 2):
    calls: list[list[str]] = []

    def fake(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
        calls.append(argv)
        reply = replies[len(calls) - 1]
        return subprocess.CompletedProcess(argv, 0, stdout=_stream(reply, tokens), stderr="")

    monkeypatch.setattr(run_case.subprocess, "run", fake)
    return calls


@pytest.mark.parametrize(
    "extra",
    [
        ["--max-calls", "0", "--max-tokens", "1"],
        ["--max-calls", "-1", "--max-tokens", "1"],
        ["--max-calls", "one", "--max-tokens", "1"],
        ["--max-calls", "1", "--max-tokens", "0"],
        ["--max-calls", "1", "--max-tokens", "-1"],
        ["--max-calls", "1", "--max-tokens", "nope"],
    ],
)
def test_refuses_invalid_or_missing_ceilings(
    tmp_path: Path, extra: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    case = _case(tmp_path)
    out = tmp_path / "out"
    assert run_case.main(["--case-dir", str(case), "--out", str(out), *extra]) == 2
    assert not out.exists()
    assert capsys.readouterr().err

    if extra[0] != "--max-calls":
        return
    missing = ["--case-dir", str(case), "--out", str(out), "--max-tokens", "1"]
    assert run_case.main(missing) == 2
    assert not out.exists()


@pytest.mark.parametrize("max_calls,max_tokens", [(1, 100), (10, 1)])
def test_ceiling_stops_before_second_model_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, max_calls: int, max_tokens: int
) -> None:
    case = _case(tmp_path)
    _isolated_controls(tmp_path, monkeypatch)
    calls = _run_with_fake(monkeypatch, _replies())
    out = tmp_path / "out"

    assert (
        run_case.main(
            [
                "--case-dir",
                str(case),
                "--out",
                str(out),
                "--max-calls",
                str(max_calls),
                "--max-tokens",
                str(max_tokens),
            ]
        )
        == 0
    )
    assert len(calls) == 1
    assert json.loads((out / "result.json").read_text())["status"] == "ceiling_reached"


def test_private_case_material_is_never_opened(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    case = _case(tmp_path)
    private = case / "private"
    private.mkdir()
    (private / "answer.json").write_text("UNIQUE_PRIVATE_SENTINEL", encoding="utf-8")
    opened: list[Path] = []
    real_open = builtins.open
    real_read_text = Path.read_text
    real_read_bytes = Path.read_bytes

    def tracking_open(file: object, *args: object, **kwargs: object):
        if isinstance(file, (str, bytes, Path)):
            opened.append(Path(file))
        return real_open(file, *args, **kwargs)

    def tracking_read_text(path: Path, *args: object, **kwargs: object) -> str:
        opened.append(path)
        return real_read_text(path, *args, **kwargs)

    def tracking_read_bytes(path: Path, *args: object, **kwargs: object) -> bytes:
        opened.append(path)
        return real_read_bytes(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", tracking_open)
    monkeypatch.setattr(Path, "read_text", tracking_read_text)
    monkeypatch.setattr(Path, "read_bytes", tracking_read_bytes)
    out = tmp_path / "out"

    assert (
        run_case.main(
            ["--case-dir", str(case), "--out", str(out), "--max-calls", "1", "--max-tokens", "100", "--dry-run"]
        )
        == 0
    )
    assert all(not path.absolute().is_relative_to(private.absolute()) for path in opened)
    assert "UNIQUE_PRIVATE_SENTINEL" not in "".join(path.read_text(encoding="utf-8") for path in out.iterdir())


def test_dry_run_writes_prompts_and_estimates_without_ledger_or_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _case(tmp_path)
    controls = _isolated_controls(tmp_path, monkeypatch)
    ledger = controls / "ledger.jsonl"

    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("dry-run attempted a model call")

    monkeypatch.setattr(run_case.subprocess, "run", fail_if_called)
    out = tmp_path / "out"
    assert (
        run_case.main(
            ["--case-dir", str(case), "--out", str(out), "--max-calls", "2", "--max-tokens", "100", "--dry-run"]
        )
        == 0
    )
    result = json.loads((out / "result.json").read_text())
    assert result["status"] == "dry_run"
    assert result["calls"] == result["tokens"] == 0
    assert result["planner_prompt"]
    assert result["estimated_tokens"]["total"] > 0
    assert not ledger.exists()


def test_full_fake_run_writes_complete_transcript_and_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    case = _case(tmp_path)
    _isolated_controls(tmp_path, monkeypatch)
    replies = _replies()
    calls = _run_with_fake(monkeypatch, replies)
    out = tmp_path / "out"
    assert run_case.main(["--case-dir", str(case), "--out", str(out), "--max-calls", "3", "--max-tokens", "100"]) == 0

    assert {path.name for path in out.iterdir()} == {
        "transcript.jsonl",
        "packets.json",
        "diagnosis.json",
        "plan.json",
        "result.json",
    }
    transcript = [json.loads(line) for line in (out / "transcript.jsonl").read_text().splitlines()]
    assert len(transcript) == 2
    assert transcript[0]["prompt"]
    assert transcript[0]["stdout"] == _stream(replies[0])
    result = json.loads((out / "result.json").read_text())
    assert result["status"] == "complete"
    assert result["ceilings"] == {"max_calls": 3, "max_tokens": 100}
    assert result["calls"] == 2
    assert result["tokens"] == 4
    assert result["solver_tree_sha256"] == "tree-hash"
    assert len(calls) == 2


def test_provider_limit_is_blocked_without_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    case = _case(tmp_path)
    _isolated_controls(tmp_path, monkeypatch)
    calls = 0

    def fake(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
        nonlocal calls
        calls += 1
        raise ProviderLimit(None)

    monkeypatch.setattr(run_case.subprocess, "run", fake)
    out = tmp_path / "out"
    assert run_case.main(["--case-dir", str(case), "--out", str(out), "--max-calls", "3", "--max-tokens", "100"]) == 0
    result = json.loads((out / "result.json").read_text())
    assert result["status"] == "blocked"
    assert result["calls"] == calls == 1
    assert "sleep" in result["error"]
